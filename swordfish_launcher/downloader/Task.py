import abc
from abc import abstractmethod
import queue

PENDING = 0
PROCESSING = 1
COMPLETE = 2
FAILED = 3

class TaskQueue:
    @abstractmethod
    def __init__(self):
        self._queue = queue.Queue()

    @staticmethod
    @abstractmethod
    def _create_task():
        return Task()

    def add_task(self):


class Task:
    def __init__(self):
        self.status = PENDING