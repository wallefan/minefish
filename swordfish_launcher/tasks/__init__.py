from abc import ABC, abstractmethod
import enum
import threading
import queue

class TaskStatus(enum.Enum):
    NOT_STARTED = 'Not Started'
    PENDING_PREREQUISITES = 'Pending'
    RUNNING = 'Running'
    COMPLETED = 'Completed'
    CANCELLED = 'Cancelled'

class Task:
    def __init__(self, prereqs=[]):
        self._prereqs = prereqs
        self._status = TaskStatus.NOT_STARTED
        self._done_callbacks = set()
        self._error = (None, None, None)
        self._result = None

    @abstractmethod
    def execute_task(self):
        """Put self into some task queue or other."""
        pass

    def __enter__(self):
        assert self._status == TaskStatus.PENDING_PREREQUISITES, "__enter__ called while status was %s" % self._status
        self._status = TaskStatus.RUNNING
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._error = (exc_type, exc_val, exc_tb)
        self._mark_completed()

    def set_result(self, result=None):
        self._result = result
        self._mark_completed()

    def _mark_completed(self):
        self._status = TaskStatus.COMPLETED
        cbs = self._done_callbacks
        self._done_callbacks = None
        if cbs:
            for callback in cbs:
                callback(self)

    def add_done_callback(self, callback):
        if self._done_callbacks is None:
            # we've already finished.
            callback(self)
        else:
            self._done_callbacks.add(callback)

    def start_task(self):
        if self._status != TaskStatus.NOT_STARTED:
            return

    def _on_vital_prereq_completed(self, task):
        if task._error != (None, None, None):
            self.__exit__(*task._error)
            return
        self._on_prereq_completed(task)

    def _on_prereq_completed(self, task):
        self._prereqs.remove(task)
        if not self._prereqs:
            self.execute_task()

    def cancel(self):
        if self._status == TaskStatus.PENDING_PREREQUISITES:
            for prereq in self._prereqs:
                prereq.cancel()
        if self._status != TaskStatus.COMPLETED:
            self._status = TaskStatus.CANCELLED

    def is_cancelled(self):
        return self._status ==  TaskStatus.CANCELLED


class TaskQueue(ABC, threading.Thread):
    def __init__(self):
        super().__init__()
        self._bg_queue = queue.Queue()
        self._priority_queue = queue.Queue()
        self._priority_interrupt = False

    def _get_task(self, block=True):
        while True:
            if self._priority_interrupt:
                try:
                    task = self._priority_queue.get_nowait()
                    assert task is not None, "Threads should be shut down from the main queue, not the priority queue."
                except queue.Empty:
                    self._priority_interrupt = False
                    task = self._bg_queue.get(block)
            else:
                task = self._bg_queue.get(block)
            if task is None:
                return None
            if task.is_cancelled():
                continue
            return task

    def run(self):
        while True:
            task = self._get_task()
            if task is None:
                return


            with task:
                self.process_task(task)

    @abstractmethod
    def process_task(self, task):
        pass


