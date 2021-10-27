from . import Downloader, DownloadJob, ZipDownloader


class SwordfishCSVDownloader:
    def __init__(self):
        self.download_jobs = {} # mapping hostnames to DownloadJobs

    def download(self, csv, priority, dest_dir):
        # iterate over the rows of the csv
        for lineno, (directive, *args) in enumerate(csv):
            if directive == 'MOD':
                assert len(args) == 2, 'Line %d: MOD directive takes two arguments, file ID and filename' % lineno + 1
                fileid, filename = args
                fileid = int(fileid)
                self._get_job('forgesvc.net').

    def _get_downloader(self, host):
        job = self.download_jobs.get(host)
        if job is None:
            job = self.download_jobs[host] = DownloadJob(dest_dir, priority, )
        return job
