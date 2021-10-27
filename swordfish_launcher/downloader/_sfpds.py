"""
This file is copy pasted from the original SwordfishPDS.
"""

import http.client
import http.cookiejar
import atexit
import os
import sys
import threading
import time
import urllib.request
import tempfile
import zipfile


ZIP_THREADS = 5
THREADS = 3
SERVER_MODE = False  # set to True by __main__
NO_COOKIE = False  # ditto


def init_cookies():
    cookiejar = http.cookiejar.MozillaCookieJar('_swordfishpds_cookies.txt')
    try:
        cookiejar.load()
    except (FileNotFoundError, http.cookiejar.LoadError):
        pass
    atexit.register(cookiejar.save)

    opener = urllib.request.build_opener()
    opener.add_handler(urllib.request.HTTPCookieProcessor(cookiejar))
    urllib.request.install_opener(opener)

# This global variable becomes true when we are done prompting the user about things,
# and other threads are now free to start writing to stdout.
allow_other_threads_to_print = False

#######################################################
#######          DOWNLOAD MACHINERY           #########
#######################################################


def extract_filename(resp, fallback=None):
    content_disposition = resp.headers.get('Content-Disposition')
    if content_disposition:
        for part in content_disposition.split(';'):
            part = part.strip()
            if part.startswith('filename='):
                return part[9:].strip('"')
                break
    return fallback or filename_from_url(resp.geturl())


def filename_from_url(url):
    if '?' in url:
        return url
    path = urllib.parse.urlsplit(url).path
    return path[path.rfind('/') + 1:]


def get_content_length(resp, default=0):
    length = resp.getheader('Content-Length', default)
    try:
        return int(length)
    except ValueError:
        return 0


def copyfileobj(fin, fout, filename='', sz=0):
    buffer = bytearray(64 * 1024)
    bufsz = 64 * 1024
    t = time.perf_counter()
    total = 0
    while True:
        n = fin.readinto(buffer)
        if n == bufsz:
            fout.write(buffer)
        elif n == 0:
            return
        else:
            with memoryview(buffer)[:n] as view:
                fout.write(view)
        total += n
        if time.perf_counter() >= t + 1:
            # Calls to sys.stdout.write() are atomic.  Calls to print() are not.
            if sz:
                sys.stdout.write('Downloading %s (%.1f%% complete)\n' % (filename, (total * 100) / sz))
            else:
                sys.stdout.write('Downloading %s (%d bytes transferred)\n' % (filename, total))
            t = time.perf_counter()


def download(url, failed_downloads):
    try:
        resp = urllib.request.urlopen(url)
    except Exception as e:
        if isinstance(url, urllib.request.Request):
            url = url.get_full_url()
        failed_downloads[filename_from_url(url)] = e
        return None
    return resp


def sanitize_path(filename):
    if SERVER_MODE:
        if filename.startswith('.minecraft'):
            filename = filename[10:]
            if filename.startswith('/'):
                filename = filename[1:]
    return filename.replace('/', os.path.sep)

class Downloader:
    def __init__(self, host, urlformat, tag=''):
        """


        :param host: The FQDN of the host to connect to. (Everything before the first slash in the url.)
        :param urlformat: Everything after (and including) the first slash in the URL.  Should contain str.format()
        paramters (i.e. {0}) that will be substituted with values passed to put().
        :param dir: Path to the local directory we should dump our files in.
        :param tag: Human readable string of what this downloader is for.  Returned by str(downloader).
        """
        self.host=host
        self.urltemplate=urlformat
        self.queue=queue.Queue()
        # can't use a stopping boolean because of a race condition -- what if one thread is already blocked on get()
        # when self.stopping becomes true?
        self.threads = []
        self.failed_downloads = {}
        self.tag = tag

    def __str__(self):
        return str(self.tag)

    def _worker(self):
        self.threads.append(threading.current_thread())
        connection = http.client.HTTPSConnection(self.host)
        while True:
            item = self.queue.get()
            if item is None:
                connection.close()
                return
            # item will be a tuple that gets formatted into our template, except for the last element,
            # which is the output directory.
            # we assume that the second last element in this tuple is some sort of human readable filename,
            # or at least one we can fall back on if the server doesn't tell us what the actual filename is.
            output_dir = item[-1]
            item = item[:-1]

            urlpath = self.urltemplate.format(*item).replace(' ', '+')
            maybe_filename = urllib.parse.unquote(item[-1])
            if maybe_filename.endswith('.jar'):
                # then it is definitely a filename
                filename = maybe_filename
            else:
                # we can't be absolutely certain that it's a filename.  Best to double check.
                connection.request('HEAD', urlpath, headers={'User-Agent': 'SwordfishPDS-1.0'})
                with connection.getresponse() as resp:
                    if resp.code != 200:
                        # Single writes to sys.stdout are atomic.  Calls to print(), which make multiple writes to
                        # sys.stdout, are not.
                        sys.stdout.write(f'Error {resp.code} on {maybe_filename}')
                        self.failed_downloads[maybe_filename] = '%d %s' % (resp.code, resp.reason)
                        if resp.headers['Connection'] == 'keep-alive':
                            resp.read()  # known bug in http library.
                        continue
                    filename = extract_filename(resp) or maybe_filename
            # Now we know for certain what the filename is.
            # Why do we need to know what the local filename is before we make the request? To resume downloads,
            # of course!
            output_path = os.path.join(output_dir, filename)
            if os.path.exists(output_path):
                fout = open(output_path, 'ab')
                my_length=fout.tell()
                connection.request('GET', urlpath, headers={
                    'User-Agent': 'SwordfishPDS-1.0',
                    'Range': f'bytes={my_length}-'
                })
            else:
                fout=open(output_path, 'wb')
                connection.request('GET', urlpath, headers={'User-Agent': 'SwordfishPDS-1.0'})
            with fout, connection.getresponse() as resp:
                if resp.code == 416:  # 416 Range Not Satisfiable
                    # We've already got the whole file.
                    sys.stdout.write('%s is already up to date.\n'%filename)
                    if resp.headers.get('Connection') == 'keep-alive':
                        resp.read()  # work around bug in http.client.
                    continue
                elif resp.code != 200 and resp.code != 206:  # 200 OK, or 206 Partial Response for Range header
                    self.failed_downloads[filename] = '%d %s' % (resp.code, resp.reason)
                    print(resp.headers['Connection'])
                    if resp.headers['Connection'] == 'keep-alive':
                        resp.read()
                    continue
                copyfileobj(resp, fout, filename, get_content_length(resp))

    def start(self, nthreads):
        if self.threads:
            # No-op if we're already running.
            return
        for _ in range(nthreads):
            threading.Thread(target=self._worker).start()

    def stop(self):
        if not self.threads:
            return
        for _ in self.threads:
            self.queue.put(None)
        for thread in self.threads:
            thread.join()
        # Clear out the queue.
        while not self.queue.empty():
            item = self.queue.get_nowait()
            assert item is None, "Entry %s still in queue when join() was called!" % (item,)
        self.threads.clear()

    def put(self, *task):
        assert self.threads, "attempt to put a task in the queue while the thread pool was halted"
        self.queue.put(task)

class ArbitraryURLDownloader(Downloader):
    def __init__(self):
        super().__init__(None, None, 'files')
    def _worker(self):
        self.threads.append(threading.current_thread())
        while True:
            item = self.queue.get()
            if item is None:
                return
            url, dest = item
            if os.path.isfile(dest):
                # the path we have been passed is a file path, not a directory path,
                # and it points to a file that already exists on disk.
                # Resume download if possible.
                fout = open(dest, 'ab')
                filename = dest
                req = urllib.request.Request(url, headers={'User-Agent': 'SwordfishPDS-1.0',
                                                           'Range': 'bytes=%d-' % fout.tell()})
            else:
                # Don't trust that the last part of the URL is the filename.  It almost never is.
                fout = None
                filename = None
                req = urllib.request.Request(url, headers={'User-Agent': 'SwordfishPDS-1.0'})
            resp = download(req, self.failed_downloads)
            if resp is None:
                continue
            with resp:
                if os.path.isdir(dest):
                    filename = extract_filename(resp)
                    fout = open(os.path.join(dest, filename), 'wb')
                elif fout is None:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    fout = open(dest, 'wb')
                with fout:
                    copyfileobj(resp, fout, filename, get_content_length(resp))


class ZipDownloader(Downloader):
    def __init__(self):
        super().__init__(None, None, 'ZIP files')

    def _worker(self):
        self.threads.append(threading.current_thread())
        while True:
            item = self.queue.get()
            if item is None:
                return
            url, dest = item
            with tempfile.TemporaryFile() as f:
                resp = download(urllib.request.Request(url, headers={'User-Agent': 'SwordfishPDS-1.0'}),
                                self.failed_downloads)
                if not resp:
                    continue
                copyfileobj(resp, f, extract_filename(resp), get_content_length(resp))
                try:
                    with zipfile.ZipFile(f) as zf:
                        zf.extractall(dest)
                except Exception as e:
                    self.failed_downloads[extract_filename(resp)] = e


