import urllib.request
import urllib.parse
import json
from ...modpack import AbstractModpack


def download_technicpack(slug):
    with urllib.request.urlopen('https://api.technicpack.net/modpack/%s?build=999' % urllib.parse.quote(slug)) as resp:
        data = json.load(resp)
    with urllib.request.urlopen(data['solder'] + 'modpack/' + slug) as resp:
        version_list = json.load(resp)
    with urllib.request.urlopen(data['solder'] + 'modpack/' + slug + '/' + version_list['recommended']) as resp:
        pack = json.load(resp)
    return pack

_SENTINEL = object()

class TechnicModpack(AbstractModpack):
    def __init__(self, slug, title=None, icon_url=_SENTINEL):

        super().__init__(slug, title, None, None)
        self.solder = _SENTINEL
        self.url = _SENTINEL
        self.recommended_version = _SENTINEL
        self.icon_url = icon_url
        self.bg_url = _SENTINEL
        self._query_solder() # TODO remvoe this

    def _init(self):
        with urllib.request.urlopen(
                'https://api.technicpack.net/modpack/%s?build=minefish' % urllib.parse.quote(self.slug)) as resp:
            data = json.load(resp)
        self.solder = data['solder']
        self.summary = data['description']
        self.url = data['url']
        self.recommended_version = data['version']  # only valid if solder is absent.
        self.icon_url = data['icon']['url'] or self.icon_url
        self.bg_url = data['background']['url']

    def _query_solder(self):
        if self.solder is _SENTINEL:
            self._init()
        if self.solder is None:
            return
        with urllib.request.urlopen(self.solder + 'modpack/' + self.slug) as f:
            data = json.load(f)
        self.versions = data['builds']
        self.latest_version = data['latest']
        self.recommended_version = data['recommended']
        self.minecraft = data['minecraft']

    @classmethod
    def search(cls, search_term):
        with urllib.request.urlopen('https://api.technicpack.net/search?build=minefish&q='+urllib.parse.quote(search_term)) as resp:
            if resp.code != 200:
                raise ValueError('Technicpack search: server returned error', resp.code)
            data = json.load(resp)
        return [cls(mp['slug'], mp['name'], mp['iconUrl']) for mp in data['modpacks']]

    def _download(self, version: str = None):
        if version is None or version == 'recommended':
            version = self.recommended_version
        if self.solder is None:
            assert version == self.recommended_version
            yield 'Zipfile', self.url
            return
        if version == 'latest':
            version = self.latest_version
        with urllib.request.urlopen('{}modpack/{}/{}'.format(self.solder, self.slug, version)) as resp:
            assert resp.code == 200  # TODO handle this error more gracefully
            data = json.load(resp)
        yield 'Minecraft', data['minecraft']
        yield 'Modloader', 'Forge', data['forge']


    def getVersions(self):
        if self.solder is None:
            return [self.advertised_version]
        else:
            if self.versions is None:
                with urllib.request.urlopen(self.solder + 'modpack/' + self.slug) as f:
                    data = json.load(f)
                self.versions = data['builds']
                self.latest_version = data['latest']
                self.recommended_version = data['recommended']
            return self.versions

    def _get_image_bytes(self, image_type):
        if image_type == 'icon':
            url = self.icon_url
        elif image_type == 'background':
            url = self.bg_url
            if url is _SENTINEL:
                self._init()
                url = self.bg_url
        else:
            return None
        if url:
            with urllib.request.urlopen(self.icon_url) as f:
                return f.read(), 'png'
        else:
            return None, None
