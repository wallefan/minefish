import http.client
from ...modpack import AbstractModpack
import time
from threading import Lock
import json
from PIL import Image

CDN_CLIENT = http.client.HTTPSConnection('download.nodecdn.net')
CDN_CLIENT_LOCK = Lock()

def _clean_string(string:str):
    out=''
    for c in string:
        if c.isalnum(): out+=c
    return out


# TODO hardcoded path!
with open(r'C:\Users\sawor.000\Downloads\folder atlauncher can vomit into\configs\json\packsnew.json') as f:
    _PACKSNEW = json.load(f)

_PACKSNEW_REFRESHED = None


def _refresh_packsnew():
    global _PACKSNEW, _PACKSNEW_REFRESHED
    # If we have never refreshed packsnew, or if it has been at least one hour since we last refreshed packsnew,
    # attempt to acquire the lock.  Only block on acquiring the lock if we have never refreshed packsnew, otherwise
    # (if we have *something* and the lock is held by another thread) just go with what we have.
    if (_PACKSNEW is None or _PACKSNEW_REFRESHED >= time.time() + 3600) \
            and CDN_CLIENT_LOCK.acquire(blocking=_PACKSNEW is None):
        try:
            CDN_CLIENT.request('/containers/atl/launcher/json/packsnew.json')
            with CDN_CLIENT.getresponse() as resp:
                assert resp.code == 200, resp.code
                _PACKSNEW = json.load(resp)
        finally:
            CDN_CLIENT_LOCK.release()


class ATLPack(AbstractModpack):
    def __init__(self, json_data):
        super().__init__(_clean_string(json_data['name']), json_data['name'], None, json_data['description'])
        self._info = json_data

    def getVersions(self):
        return [version['version'] for version in self._info['versions']]

    @classmethod
    def search(cls, query):
        for pack in _PACKSNEW:
            if query in pack['name']:
                yield cls(pack)

    def _download(self, version:str=None):
        # TODO IMPLEMENT THIS
        yield 'Zip', f''

    def _getimage(self, imagetype):
        if imagetype != 'icon':
            return None
        try:
            with open('C:\\Users\\sawor.000\\Downloads\\folder atlauncher can vomit into\\configs\\images\\'+self.slug.lower()+'.png','rb') as f:
                im=Image.open(f)
                im.load()
                return im
        except FileNotFoundError:
            return None

    def _get_image_bytes(self, image_type):
        pass # TODO download from CDN
