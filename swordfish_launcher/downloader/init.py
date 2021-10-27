import os
import tempfile
import threading
import contextlib
import warnings

class ZipExtractor(threading.Thread):
    def enqueue(self, zf, subdir, outputdir):
        # TODO stub
        pass
    def blocking(self, zf, subdir, outputdir):
        # TODO stub
        pass

class UrllibDownloader(threading.Thread):
    def enqueue(self, url, outfile):
        # TODO stub
        pass
    def blocking(self, url):
        """
        Put the URL into the priority queue so it will be downloaded first, and block until the download finishes.

        :param url:
        :return:  A file object, which will either be a tempfile.TemporaryFile or a disk file from the URL cache
        """
        # TODO stub
        pass

from .cache import Cache

class Job:
    def __init__(self):
        self.zipextractor = ZipExtractor()
        self.urllib_downloader = UrllibDownloader()

    def parsecsv(self, csv):
        try:
            op, *args = next(csv)
        except StopIteration:
            warnings.warn("Empty iterator passed to parsecsv()")
            return
        while True:
            if op == 'unzip':
                zf, subdir, outdir = args
                tempdir = None
                if outdir == 'WAIT':
                    tempdir = tempfile.TemporaryDirectory()
                    outdir = tempdir.name
                if isinstance(zf, str) and '://' in zf:
                    if tempdir:
                        zf = self.urllib_downloader.blocking(zf)
                    else:
                        # pass urllibdownloader a callback instead of an output file -- this will cause it to download
                        # to a temp file, which will then be passed as a file object to the callback.  then put the
                        # file object in the zip extractor's queue, so that, with one method call, we can chain
                        # two asynchronous events.
                        self.urllib_downloader.enqueue(zf, lambda f: self.zipextractor.enqueue(f, subdir, outdir))
                        continue
                if tempdir:
                    self.zipextractor.blocking(zf, subdir, outdir)
                    try:
                        op, *args = csv.send(outdir)
                        continue
                    except StopIteration:
                        break
                else:
                    self.zipextractor.enqueue(zf, subdir, outdir)
            elif op == 'Curse':
                projid, fileid, outpath = args
                projid = int(projid)
                fileid = int(fileid)
                rec = moddb.get_record(curse_projid=projid, curse_fileid = fileid):
                if rec:
                    if outpath == 'WAIT':
                        try:
                            op, *args = self.
                    for f in moddb.get_file_locations(rec):
                        try:
                            os.link(f, os.path.join(self.outputdir, outpath, rec.canonical_filename))
