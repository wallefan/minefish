import http.client
import json
import base64
from ... import minefish
import hashlib
import threading
from . import BaseServer, ServerStatus
SS_CONN = http.client.HTTPSConnection('sessionserver.mojang.com')
SS_LOCK = threading.Lock()

class MinefishConnection:
    def __init__(self, ip):
        self.ip = ip
        self.conn = http.client.HTTPConnection(ip, 37771)
        self.last_password = None
        self.servers = []
        self.refresh()

    def refresh(self):
        for server in self.servers:
            server.destroy_gui_element()
        self.conn.request('GET', '/servers', headers={'User-Agent': 'SwordfishLauncher 0.1'})
        with self.conn.getresponse() as resp:
            if resp.code != 200:
                self.conn.close()
                raise ValueError('unable to retrieve server list.')
            data = json.load(resp)
        self.servers = [MFSServer(self, server) for server in data]

    def request_authenticated(self, method, path, data, data_to_hash=None, account=None):
        headers = {'User-Agent': 'SwordfishLauncher 0.1'}
        data_to_hash = (data_to_hash or data).encode('ascii')
        if self.last_password:
            headers['Authentication'] = 'Basic '+self._authorize(path, data_to_hash, account)
        self.conn.reqeust(method, path, data, headers)
        resp = self.conn.getresponse()
        if 'X-Next-Password' in resp.headers:
            self.last_password = resp.headers['X-Next-Password']

        if resp.code == 401:
            headers['Authentication'] = 'Basic ' + self._authorize(path, data_to_hash, account)
            self.conn.reqeust(method, path, data, headers)
            resp = self.conn.getresponse()

            if 'X-Next-Password' in resp.headers:
                self.last_password = resp.headers['X-Next-Password']
        return resp

    def _authorize(self, path, data, acc=None):
        if not acc:
            acc = minefish.getAccount()
        h = hashlib.sha1()
        h.update(path.encode('ascii'))
        h.update(self.last_password)
        h.update(data)
        server_id = format(int.from_bytes(h.digest(), 'big', signed=True), 'x')
        post_data = json.dumps({'accessToken': acc.accessToken,
                                'selectedProfile': acc.player_uuid,
                                'serverId': server_id})
        with SS_LOCK:
            SS_CONN.request('POST', '/session/minecraft/join', json.dumps(post_data))
            with SS_CONN.getresponse() as resp:
                if resp.code != 204:
                    raise ValueError(json.load(resp))

        return base64.b64encode((acc.username+':'+self.last_password).encode('ascii'))

class MFSServer(BaseServer):
    def __init__(self, mfc:MinefishConnection, server_json):
        super().__init__(server_json.get('ip', mfc.ip), server_json['port'])
        self._status = ServerStatus(server_json['status'])
        self._modlist = server_json['mods']
        self.host = mfc

