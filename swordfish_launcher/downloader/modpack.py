from abc import ABC, abstractmethod
import os
import urllib.request
import io
import os

class AbstractModpack(ABC):
    __slots__=('title','description')
    @abstractmethod
    def __init__(self, slug, title, summary, description):
        self.slug = slug
        self.title = title
        self.summary = summary
        self.description = description
        self._on_disk_path = os.path.expanduser('~/.local/share/minefish/'+slug)
        os.makedirs(self._on_disk_path, exist_ok=True)

    def _getimage(self, imagetype):
        """
        Read from disk and return an image.
        :param imagetype: should be one of either 'icon' or 'background', but may be any legal filename
        :return: a PIL.Image, if we are able, or None if we are not
        """
        try:
            from PIL import Image
        except ImportError:
            return None
        candidates = [x for x in os.listdir(self._on_disk_path) if x.startswith(imagetype+os.path.extsep)]
        if candidates:
            return Image.open(os.path.join(self._on_disk_path, candidates[0]))
        else:
            image_bytes, image_extension = self._get_image_bytes(imagetype)
            if not image_bytes:
                return None
            image = Image.open(io.BytesIO(image_bytes))  # if this fails we shouldn't be saving it to disk anyway.
            if image_extension:
                with open(os.path.join(self._on_disk_path, imagetype+os.path.extsep+image_extension), 'wb') as f:
                    f.write(image_bytes)
            return image

    @abstractmethod
    def _get_image_bytes(self, image_type):
        """Return a 2-tuple of a bytes object containing the contents of an image file, which will be written to disk
        by the caller, and a file extension without the leading dot.  image_type will be one of either "icon",
        in which case you should return a small image suitable for displaying next to the modpack name and details in
        the pack list, or "background", in which case return a larger image suitable for displaying behind the
        modpack's detailedinfo. In case you cannot return an image, return a 2-tuple (None, None).
        If you do not want the file to be cached to disk (for example, because it was sourced from the executable),
        return a bytes object and None as the extension.

        It is up to the implementation to make sense (or not) of alternate values for image_type; the stock UI will
        never call get_image() with anything other than those two values, although third party code may.  If you don't
        know what to do, return (None,None).
        """
        return (None, None)


    def download(self, version:str=None):
        """
        Download the modpack from whatever server using whatever means you find most suitable.
        :param version: Optional parameter specifying one element from the list returned by getVersionList(),
        or None (or omitted) for the latest version.
        :return: None
        """
        pass

    @abstractmethod
    def _download(self, version:str=None):
        """
        Take a version string and return an iterator in Swordfish CSV format specifying to the downloader what to do.
        The Swordfish CSV format is highly flexible but in case it is insufficient this method may have side effects.

        :param version:
        :return: An iterator following the sfpds CSV format.
        """

    @abstractmethod
    def getVersions(self):
        return []


