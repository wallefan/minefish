from ...modpack import AbstractModpack
import zipfile
import tempfile
from ...http_api import API
import urllib.parse
import os
import json
from ....minefish import USER_AGENT

CURSEFORGE_API = API('https://addons-ecs.forgesvc.net/api/v2', {'User-Agent': USER_AGENT})


class CurseBase:
    def __init__(self, info):
        self._project_id = info['id']
        self._latest_files = info['latestFiles']
    @classmethod
    def search(cls, searchQuery, gameVersion=None, index=0, count=25):
        path = ('/addon/search?gameId=432&'  # 432 = Minecraft
                'sectionId=%d&'
                'index=%d&count=%d&searchFilter=%s'
                ) % (cls._curse_section_id, index, count, urllib.parse.quote(searchQuery))
        if gameVersion:
            path += '&gameVersion='+gameVersion
        # For whatever reason, the Curseforge API straight up ignores all but the first word of the search query.
        searchQuery = searchQuery.casefold()
        return [cls(info) for info in CURSEFORGE_API.get_json(path)]# if searchQuery in info['name'].casefold()]

    @classmethod
    def from_project_id(cls, project_id):
        info = CURSEFORGE_API.get_json('/addon/%s' % project_id)
        assert info['categorySection']['gameCategoryId'] == cls._curse_section_id
        return cls(info)


class CurseModpack(AbstractModpack, CurseBase):
    _curse_section_id = 4471   # 4471 = Minecraft modpacks
    def __init__(self, info):
        CurseBase.__init__(self, info)
        AbstractModpack.__init__(self, info['slug'], info['name'], info['summary'], None)
        self._background_image_url = None
        self._icon_url = None
        if info['attachments']:
            for att in info['attachments']:
                if att['isDefault']:
                    if self._icon_url is None:
                        self._icon_url = att['url']
                        if self._background_image_url is not None:
                            break
                elif self._background_image_url is not None:
                    self._background_image_url = att['url']
                    if self._icon_url is not None:
                        break
        self._all_files = None

    def _get_image_bytes(self, image_type):
        if image_type == 'icon':
            with urllib.request.urlopen(self._icon_url) as req:
                return (req.read(), req.headers.get_content_subtype())
        elif image_type == 'background':
            with urllib.request.urlopen(self._icon_url) as req:
                return (req.read(), req.headers.get_content_subtype())
        else:
            return None

    def _download(self, version:str=None, download_optional_mods=[]):
        if version is None:
            download_url = next(file['downloadUrl'] for file in self._latest_files if file['releaseType'] == 1)
        else:
            self.getVersions()
            download_url = self._all_files[version]
        with tempfile.TemporaryFile() as f:
            with urllib.request.urlopen(download_url) as fin:
                import shutil
                shutil.copyfileobj(fin,f)
            with zipfile.ZipFile(f) as zf:
                # I would love to use zf.extract() or zf.extractall() here, but for whatever reason, those two methods
                # simply *insist* on extracting the full file path, and I have to extract everything from overrides/
                # into the modpack dir, not the modpack dir/overrides.
                for file in zf.infolist():
                    if file.filename.startswith('overrides/'):
                        fspath = os.path.join(self._on_disk_path, file.filename[10:].replace('/',os.path.sep))
                        if file.isdir():
                            os.mkdir(fspath)
                        else:
                            with zf.open(file) as fin, open(fspath, 'w') as fout:
                                shutil.copyfileobj(fin, fout)
                with zf.open('manifest.json') as f:
                    manifest=json.load(f)
        yield 'Minecraft', manifest['version']
        for loader in manifest['modLoaders']:
            yield 'Loader', loader['id']
        optional_mods = []
        for mod in manifest['files']:
            if not mod['required']:
                optional_mods.append((mod['projectID'], mod['fileID']))
                continue
            else:
                yield 'Curse', mod['projectID'], mod['fileID']


    def getVersions(self):
        if self._all_files is None:
            files = CURSEFORGE_API.get_json('/addon/%d/files'%self._project_id)
            self._all_files = {file['displayName']: file['downloadUrl'] for file in files}
        return self._all_files.keys()


class CurseMod(CurseBase):
    def __init__(self, info):
        super().__init__(info)