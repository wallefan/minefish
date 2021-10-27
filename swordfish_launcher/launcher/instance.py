import pathlib
import json
import subprocess

class Instance:
    def __init__(self, diskpath:pathlib.Path):
        if not diskpath.exists():
            diskpath.mkdir()
        assert diskpath.is_dir()
        self.diskpath = diskpath
        self.json_file = diskpath/'multimc.json'
        if self.json_file.exists():
            try:
                self.config = json.loads(self.json_file.read_text())
            except json.JSONDecodeError:
                self.config=DEFAULT_CONFIG
        else:
            self.config = DEFAULT_CONFIG


    def