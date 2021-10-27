from . import Task, TaskQueue


class DownloadTask(Task):
    pass

class Downloader(TaskQueue):
    def __int