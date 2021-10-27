import urllib.parse
import http.client
import json

class API:
    def __init__(self, baseurl, default_headers):
        scheme, host, path, _, _, _ = urllib.parse.urlparse(baseurl)
        self._basepath = path
        assert scheme in ('http','https')
        self._client = {'http': http.client.HTTPConnection, 'https': http.client.HTTPSConnection}[scheme](host)
        self._default_headers = default_headers

    def post_json(self, path, data, headers={}):
        _headers = self._default_headers.copy()
        _headers['Content-Type'] = 'application/json'
        _headers.update(headers)
        self._client.request('POST', self._basepath+path, json.dumps(data), _headers)
        return self._client.getresponse()

    def get_json(self, path):
        self._client.request('GET', self._basepath+path, headers=self._default_headers)
        with self._client.getresponse() as resp:
            if resp.code != 200:
                raise ValueError(resp.code)
            return json.load(resp)

    def get_raw(self, path):
        self._client.request('GET', self._basepath+path, headers=self._default_headers)
        with self._client.getresponse() as resp:
            if resp.code != 200:
                raise ValueError(resp.code)
            return resp.read()

