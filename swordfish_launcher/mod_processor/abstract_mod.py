from abc import ABC, abstractmethod
import json
import zipfile

class AbstractMod(ABC):
    @abstractmethod
    def get_jarfile(self):
        """Returns a JarfileMod representing self."""

class JarfileMod(AbstractMod):
    def __init__(self, jarfile):
        self.file = zipfile.ZipFile(jarfile)

    def get_jarfile(self):
        return self

    def get_zip_signature(self):