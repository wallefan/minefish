import http.client
import urllib.parse
import os
import json
import csv
import threading
from . import Downloader
import sys

if sys.platform == 'win32' or sys.platform == 'cygwin':
    OS_NAME = 'windows'
elif sys.platform.startswith('freebsd'):
    OS_NAME = 'freebsd'
elif sys.platform.startswith('linux'):
    OS_NAME = 'linux'
elif sys.platform.startswith('aix'):
    OS_NAME = 'aix'
elif sys.platform.startswith('darwin'):
    OS_NAME = 'osx'


class MinecraftDownloader:
    """
    This class does a lot of things.
     - Download the version list from the server, and save it as a CSV file.
     -
    """
    def __init__(self, launcher_dir):
        self._cache_dir = os.path.join(launcher_dir, 'cache')
        os.makedirs(self._cache_dir, exist_ok=True)
        self._version_manifest=None
        self.client = http.client.HTTPSConnection('launchermeta.mojang.com')
        self._version_manifest_last_refresh = None

    def get_version_url(self, versionid):
        manifest_file = os.path.join(self._cache_dir, 'version_manifest.csv')
        if self._version_manifest is None and os.path.exists(manifest_file):
            with open(manifest_file) as f:
                self._version_manifest_last_refresh = f.readline().strip()
                self._version_manifest = dict(csv.reader(f))

        if self._version_manifest is None or versionid not in self._version_manifest:
            headers = {'User-Agent': 'SwordfishLauncher 0.1'}
            if self._version_manifest_last_refresh is not None:
                headers['If-Modified-Since'] = self._version_manifest_last_refresh
            self.client.request('GET','/mc/game/version_manifest.json', headers=headers)
            with self.client.getresponse() as f:
                if f.code == 304:
                    # we're up to date.
                    return None
                elif f.code != 200:
                    raise ValueError(f.code, f.reason)
                response = json.load(f)
                self._version_manifest_last_refresh = f.getheader('Last-Modified',None)
            if self._version_manifest is None:
                self._version_manifest = {}
            for ver in response['versions']:
                self._version_manifest[ver['id']] = ver['url']
            with open(manifest_file, 'w') as f:
                f.write(self._version_manifest_last_refresh+'\n')
                csv.writer(f).writerows(self._version_manifest.items())

        return self._version_manifest.get(versionid)


    def download_minecraft(self, versionid, outputdir):
        path = urllib.parse.urlsplit(self.get_version_url(versionid)).path
        self.client.request('GET', path, headers={'User-Agent': 'SwordfishLauncher 1.0'})
        with self.client.getresponse() as f:
            data=json.load(f)
        queue=[]
        library_downloader = Downloader('libraries.minecraft.net', '{filename}', queue, os.path.join(outputdir, 'libraries'))
        library_downloader.start()
        for library in data['libraries']:


    def download_assets(self, assetlist, destdir):
        for asset in assetlist:
            for rule in asset['rules']:
                if rule['action'] == 'allow':
                    if 'os' in rule and rule['os']['name'] != OS_NAME:
                        break
                    if
            else:
                asset['']



