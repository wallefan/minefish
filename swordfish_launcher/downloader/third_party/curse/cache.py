from . import CURSEFORGE_API
import io
import zipfile
import urllib.request
import os
import shutil
from ....minefish import Minefish, USER_AGENT


class CurseModCache:
    def __init__(self, master_cache):
        self._master_cache = master_cache
        self._cache = {}  # TODO actually load the cache

    def procure_mod(self, projectID, fileID, disk_directory):
        signature, filename = self._cache.get((projectID, fileID))
        if signature is None:
            file_info = CURSEFORGE_API.get_json('/addon/%d/file/%d' % (projectID, fileID))
            # Now this next section may get a little confusing.  Let me explain.
            # You see, JAR files are actually ZIP files, and all of the information about the contents of a ZIP file
            # is encoded in the End Central Directory record, which, unless the file uses the ZIP64 extension of the
            # format (which I'm fairly certain no Minecraft mod is big enough to need), is guaranteed to be
            # contained entirely within the last 64K.  Since all of the file offsets saying where the various files in
            # the zip file start are relative to the start of the EndCentDir, and (more importantly) since Python's zipfile
            # module doesn't sanity check them, this means that if you download only the last 64K of a JAR fie,
            # you can create a zipfile.ZipFile() of it and list its contents.  Of course, you can't do much more than
            # that, unless the files you want to extract happen to be in the last 64K, but all we're interested in is
            # the table of contents.

            # Now.  Why would we want to do this?  Under what circumstances would this code run?  Why would we want
            # to know a zip file's table of contents but not the rest of the data?  It is my assumption that when
            # someone installs Minefish/SwordfishLauncher/whatever I end up deciding to call it in the end, they will
            # have played modded at least once prior and will have some mods already on their hard drive.  If possible,
            # I'd like to avoid wasting both disk space and the user's time and bandwidth redownloading them.  TO this
            # end, I use a fingerprinting system.  Since JAR files are ZIP files and can be recompressed, signed, and
            # otherwise made not byte-for-byte identical without changing their contents, hashing is out of the question
            # (even though in the context of minecraft mods it would probably work).  Besides, hashing is slow; even
            # if the processor can hash data just as fast as the disk can supply it, which it usually can't, reading an
            # entire file is always going to be slower than reading the last 64K and closing it again.

            # Some minecraft mods are very small and the entire file is less than 64K.  The server would complain if we
            # passed it a negative number
            if file_info['fileLength'] <= 65536:
                have_entire_file = True
                request = urllib.request.Request(file_info['downloadUrl'], headers={'User-Agent': USER_AGENT})
            else:
                have_entire_file = False
                request = urllib.request.Request(file_info['downloadUrl'],
                                                 headers={'User-Agent': USER_AGENT,
                                                          'Range': 'bytes=-65536'})
            with urllib.request.urlopen(request) as resp:
                partial_file = io.BytesIO(resp.read())

            with zipfile.ZipFile(partial_file) as zf:
                signature = frozenset((info.filename, info.file_size, info.CRC) for info in zf.infolist())
            self._cache[(projectID, fileID)] = signature, filename
        else:
            partial_file = None
        procured_file = self._master_cache.procure_mod(signature, disk_directory)
        if procured_file:
            return procured_file
        output_path = os.path.join(disk_directory, filename)
        with open(output_path, 'wb') as fout:
            if partial_file:
                request = None if have_entire_file else urllib.request.Request(-
                    file_info['downloadUrl'],
                    headers={'User-Agent': USER_AGENT,
                             'Range': 'bytes=0-%d' % (file_info['fileLength'] - 65536)}
                )
            else:
                request = urllib.request.Request(file_info['downloadUrl'], headers={'User-Agent': USER_AGENT})
            if request:
                with urllib.request.urlopen(request) as fin:
                    shutil.copyfileobj(fin, fout)
            if partial_file:
                fout.write(partial_file.getbuffer())
        self._master_cache.add_entry(output_path, signature)
        return output_path

    def save(self):

