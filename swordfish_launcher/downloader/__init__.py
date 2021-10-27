import http.client
import threading
import tempfile
import zipfile

import swordfish_launcher.gui.progressbar
from ..minefish import USER_AGENT
import queue
import os


# NOTE: The original SwordfishPDS had a rather different thread system. Downloader objects were simply frontends to a
# queue which was serviced by multiple simultaneous download threads pointed at the same server.  Even at the time I
# knew this was a bad idea -- if the server isn't throttled per connection (none of the servers I'm connecting to are
# throttled at all), multiple download threads at best fight for bandwidth and end up going slower than a single thread,
# and at worst, get you an IP ban.  I'm opting instead to use HTTP pipelining, which gives a better performance
# benefit than simply pointing multiple threads at the same server for small downloads (e.g. HEAD requests,
# which SwordfishPDS used a lot of but that SwordfishLauncher hopefully won't need to use at all)
#

class DownloadJob:
    """A collection of URLs and output files that are passed to the Downloader as a set and can be queried and cancelled
    as a unit.
    """

    def __init__(self, outputdir, priority=0, progressbar: 'swordfish_launcher.gui.progressbar.ProgressFrame' = None,
                 download_progressbar: 'swordfish_launcher.gui.progressbar.ProgressFrame' = None,
                 total_filesize: int = None):
        """

        :param outputdir:
        :param priority: Download priority that will be passed to the Downloader.  Higher number means higher priority.
        Downloaders always service the highest priority job in their queue first.
        :param progressbar: Progressbar to report overall progress of the job.
        :param download_progressbar: Progressbar displaying how much of each individual file has been downloaded.
        :param total_filesize: The sum of the sizes of all the files this job will download, if known in advance.  If
        specified, the progress bar will increase linearly with every byte downloaded up to a maximum of the specified
        value -- this allows the system to display an accurate ETA.  If set to None, or left unspecified, the overall
        progress will increase by the same amount for each file downloaded.
        """
        self.failures = {}
        self.queue = queue.Queue()
        self.outputdir = outputdir
        self.priority = priority
        self._total = 0
        self._cut_off = False
        self.cancelled = False
        self.progressbar_overall = progressbar
        self.progressbar_download = download_progressbar
        self.done = threading.Event()
        self.failed_downloads = {}
        self.determinate = total_filesize is not None
        if progressbar:
            progressbar.reset()
            # Note about these two arguments: if the first argument is True, the progress bar will be linear, and the
            # number is the number of completed jobs needed to fill it all the way up.  If you go past this, it will
            # wrap around to zero.  If the first argument is false, it becomes the kind of progress bar that bounces
            # side to side, and the number is the number of completed jobs needed for it to move from one end to the
            # other.
            # We will on average be downloading many more than 25 files, but 25 seems a sane number for the user to see
            # that progress is happening (each job may take seconds to minutes
            if total_filesize is not None:
                progressbar.configure(True, total_filesize)
            else:
                progressbar.configure(False, 25)

    def add(self, outputpath, url_args):
        assert not self._cut_off, "attempt to add an item to the queue after join"
        if self.cancelled:
            # XXX should this just be a no-op?
            raise RuntimeError('Attempt to add item to queue after operation cancelled')
        self.queue.put((os.path.join(self.outputdir, outputpath), *url_args))
        self._total += 1  # TODO incrementing integers is not thread safe.

    def join(self):
        self.finalize()
        self.done.wait()
        return self.failures

    def finalize(self):
        """
        Signal to this object that no more calls to add() will be made.   join() calls this method implicitly.
        This sets the progress point.
        If this method is never called, the downloader thread will hang.
        :return: None
        """
        if self._cut_off:
            return
        self._cut_off = True
        self.queue.put((None,))
        if self.progressbar_overall and not self.determinate:
            self.progressbar_overall.set_max(True, self._total)

    def _progress(self, progress):
        self.progressbar_download.progress(progress)
        if self.determinate:
            self.progressbar_overall.progress(progress)

    def _task_done(self):
        self.queue.task_done()
        if not self.determinate:
            self.progressbar_overall.progress(1)

    def cancel(self):
        self.finalize()
        self.cancelled = True
        # TODO maybe reset the progressbars somehow?

    def __gt__(self, other):
        return self.priority > other.priority if isinstance(other, DownloadJob) else NotImplemented

    def __lt__(self, other):
        return self.priority < other.priority if isinstance(other, DownloadJob) else NotImplemented

    def __ge__(self, other):
        return self.priority >= other.priority if isinstance(other, DownloadJob) else NotImplemented

    def __le__(self, other):
        return self.priority <= other.priority if isinstance(other, DownloadJob) else NotImplemented


def download(resp: http.client.HTTPResponse, fout, job: DownloadJob, stop=lambda: False, blocksize=1024 * 1024):
    if job.progressbar_download:
        filesize = resp.getheader('Content-Length').strip()
        if filesize:
            try:
                filesize = int(filesize)
            except ValueError:
                filesize = None
        if filesize:
            job.progressbar_download.configure(value=0, mode='determinate', max=filesize)
        else:
            job.progressbar_download.configure(value=0, mode='indeterminate', max=blocksize)
    # I don't know why, but writing to a memoryview of a bytearray is almost 50x faster than writing directly to the
    # bytearray.  On my mahchine, overwriting an entire 1MB bytearray takes an entire millisecond.  Overwriting a
    # memoryview of the same bytearray takes 43 microseconds.  Which is still pathetic, considering today's memory
    # speeds, but it's not half bad for Python.
    with memoryview(bytearray(blocksize)) as buffer:
        while not stop():
            count = resp.readinto1(buffer)
            if not count:
                return True
            if count == blocksize:
                fout.write(buffer)
            else:
                fout.write(buffer[:count])
            # Subtle: advance the progressbar after writing to the output file.  This does a fair amount to alleviate
            # the age-old problem of the progress bar getting stuck at 100%.
            # I'm using the underscore in the name here to signify that this should be the only place that _progress()
            # is called from.  However, Python doesn't really have a way to denote package visibility, so Pycharm
            # will complain.
            job._progress(count)
        return False


class Downloader(threading.Thread):
    def __init__(self, server, urlformat, server_supports_range=True, server_supports_request_pipelining=True):
        """

        :param server: Hostname of the server, e.g. 'forgesvc.net'
        :param urlformat: Path format of the server, e.g. '/files/{}/{}/{}'.
        :param server_supports_range: Set this to False if the server doesn't support the Range: HTTP header.
        :param server_supports_request_pipelining: Submitting a second request on the same connection before you
        finish reading the last one isn't officially part of the HTTP spec, and some HTTP daemons behave oddly
        when you try, and do dumb things like aborting the connection or dispensing random binary data in lieu of
        headers (I have observed both of these).  Set this to False if :param server: is such a server, to disable
        request pipelining.
        """
        self.client = http.client.HTTPSConnection(server)
        self.queue = {}  # dict mapping integer priorities to actionable DownloadJobs.
        self.active_job: DownloadJob = None
        self.queue_lock = threading.Lock()
        self._shutting_down = False
        self.interrupting = False
        self.urlformat = urlformat
        self.supports_pipelining = server_supports_request_pipelining
        self.supports_resumption = server_supports_range

    def interrupt(self):
        """Abort the current download, if one is in progress, and recheck the queue for a new highest priority.
        Use when you absolutely cannot afford to wait for the previous job to finish.
        """
        self.interrupting = True

    # I'm considering habving the download queue be a dict mapping priority numbers to lists of jobs, and I'm not
    # sure whether that would give better or worse performance than just putting all the jobs in a PriorityQueue
    # and letting heapq do its thing.

    # I don't suppose it matters much.  But I know which one will be easier to debug.

    def _get_job(self) -> DownloadJob:
        with self.queue_lock:
            if not self.queue: return None
            highest_priority = max(self.queue)
            jobs = self.queue[highest_priority]
            while not jobs and self.queue:
                del self.queue[highest_priority]
                highest_priority = max(self.queue)
                jobs = self.queue[highest_priority]
            if not self.queue: return None
            return jobs.pop()

    def _send_download_request(self):
        """

        :return: 5-tuple ultimate destination path, output file object, expected HTTP response code (either 200 or 206),
        URL path we sent to the server, and an optional callback to invoke with the
        """
        if self.interrupting:
            # Put the current job back in the queue, because one with a higher priority has just been added.

            # I'm not sure I absolutely *need* to do this, given that it's only being called from one thread,
            # or even if it would help anything if I weren't, but I'd rather just be safe.
            active_job = self.active_job
            self.active_job = None
            self.enqueue_job(active_job)
            self.interrupting = False

        if self.active_job is None:
            self.active_job = self._get_job()

        # we still don't have a job, we're done.
        if self.active_job is None:
            return None, None, None, None, None

        outfile, *fmt = self.active_job.queue.get()
        while outfile is None:
            self.active_job.done.set()
            self.active_job = self._get_job()
            if self.active_job is None:
                # cave johnson, we're done here
                return None, None, None, None, None
            outfile, *fmt = self.active_job.queue.get()

        # outfile may be a callable, in which case the file will be downloaded to a temporary file, or to cache,
        # after which the callable will be invoked from the downloader thread with the resulting file object as an
        # argument.  This is used for zip file downloads, in which case the callable will put the file object into the
        # zip extractor's queue.
        if isinstance(outfile, str):
            outpath = os.path.join(self.outputdir, outfile.replace('/', os.path.sep))
            fout = open(outpath + '.part', 'ab')
            callback = None
        elif callable(outfile):
            # TODO implement a config option for caching.
            fout = tempfile.TemporaryFile()
            callback = outfile
            outpath = None
        else:
            assert False, "outfile must either be a path or a callback"
        headers = {'User-Agent': USER_AGENT}
        if fout.tell() != 0 and self.supports_resumption:
            headers['Range'] = 'bytes=%d-' % fout.tell()
            expected_code = 206
        else:
            fout.seek(0)
            expected_code = 200
        urlpath = self.urlformat.format(*fmt, filename=outfile)
        self.client.request('GET', urlpath, headers=headers)
        return outpath, fout, expected_code, urlpath, callback

    def enqueue_job(self, job):
        assert isinstance(job, DownloadJob)
        self.queue.put(job)

    def run(self):
        outfile, fout, expected_code, urlpath, callback = self._send_download_request()

        while fout is not None:
            # send our next request (if any) to the server while we're working on the current one, to elimiate
            # the lookup delay between request and response.  Pipelining is good.  Doesn't increase performance much
            # when all you're making is GET requests, but there's no reason NOT to do it.
            with self.client.getresponse() as resp:
                # can't call putrequest() until we've gotten the last response, otherwise I'd put this outside the with
                # cache active_job both for speed and because _pipeline_download() may change it.
                active_job = self.active_job

                # So HTTP request pipelining is really cool.  Look it up if you haven't already.  Basically it's
                # when you send another request to the server on the same connection while you're still downloading the
                # response from the last one.  It can at times be a huge speedup since you don't have to wait for the
                # server to process your request and get a response ready (which usually takes about a second).  Thing
                # is, not all servers support it, and sometimes do odd things like aborting the connection or dispensing
                # apparently random binary data in lieu of headers.  So we have an option in the constructor to turn
                # request pipelining off.
                if self.supports_pipelining:
                    next_entry = self._send_download_request()
                if resp.code != expected_code:
                    active_job.failed_downloads[urlpath] = resp.code
                    if resp.getheader('Connection', '').lower() == 'keep-alive':
                        resp.read()
                    continue
                try:
                    download(resp, fout, active_job, lambda: self.interrupting or active_job.cancelled)
                except Exception as e:
                    active_job.failed_downloads[urlpath] = e
                    fout.close()
                    # XXX if the download failed due to an unexpected response code from the server, should the file
                    # XXX be deleted from disk?
                    # On the one hand, the obvious answer is yes.  On the other, the file may have simply moved,
                    # and since our code can't handle 301 redirects *at all*, it may be beneficial to keep any partially
                    # downloaded files around, since having part of a file is better than nothing.
                    # In addition, the file may have been deleted from the server, as sometimes happens with old
                    # versions of mods vital for playing older packs, in which case a partial archive on the user's
                    # machine is at least better than nothing.
                else:
                    if callback:
                        # it is up to the callback to close the output file once they are done with it.
                        # the callback usually simply puts the object passed to it into a queue to be processed
                        # by a different thread to avoid holding up the downloader thread with e.g. decompression.
                        callback(fout)
                    else:
                        fout.close()
                        if outfile:
                            # outfile is the expected output path, which we are expected to rename the file we produce
                            # to after it is downloaded successfully.  the above code passes us a file object named
                            # filename.ext.part along with the string filename.ext.
                            os.rename(fout.name, outfile)
            active_job._task_done()
            outfile, fout, expected_code = next_entry if self.supports_pipelining else self._send_download_request()


class ZipExtractor(threading.Thread):
    def __init__(self, progressbar):
        self.queue = threading.Queue()
        self.progressbar = progressbar
    def run(self):
        while True:
            file, subdir, outputdir = self.queue.get()
            if subdir and not subdir.endswith('/'):
                subdir += '/'
            if not file:
                break
            with file, zipfile.ZipFile(file) as zf:
                # I would just use zf.extractall() but I wanted the progress bar.
                files = [zi for zi in zf.infolist() if zi.filename.startswith(subdir)] if subdir else zf.infolist()

                self.progressbar.config(mode='determinate', value=0, max=sum(zi.file_size for zi in files))
                for member in files:

                    ### THIS PORTION COPY PASTED FROM zipfile.py ###

                    # build the destination pathname, replacing
                    # forward slashes to platform specific separators.
                    arcname = member.filename
                    if subdir:
                        assert arcname.startswith(subdir)
                        arcname = arcname[len(subdir):]
                    if os.path.sep != '/':
                        arcname = arcname.replace('/', os.path.sep)

                    if os.path.altsep:
                        arcname = arcname.replace(os.path.altsep, os.path.sep)
                    # interpret absolute pathname as relative, remove drive letter or
                    # UNC path, redundant separators, "." and ".." components.
                    arcname = os.path.splitdrive(arcname)[1]
                    invalid_path_parts = ('', os.path.curdir, os.path.pardir)
                    arcname = os.path.sep.join(x for x in arcname.split(os.path.sep)
                                               if x not in invalid_path_parts)
                    if os.path.sep == '\\':
                        # filter illegal characters on Windows
                        arcname = zf._sanitize_windows_name(arcname, os.path.sep)

                    targetpath = os.path.join(outputdir, arcname)
                    targetpath = os.path.normpath(targetpath)

                    ### END COPY PASTE FROM zipfile.py ###

                    os.makedirs(os.path.dirname(targetpath), exist_ok=True)
                    with open(targetpath, 'wb') as fout, zf.open(member) as fin:
                        data = fin.read(65536)
                        fout.write(data)
                        self.progressbar.step(len(data))
