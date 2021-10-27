import tkinter
import tkinter.ttk
import time
import collections

if hasattr(time, 'perf_counter'):
    gettime = time.perf_counter
elif hasattr(time, 'monotonic'):
    gettime = time.monotonic
else:
    print("WARNING: time.monotonic() not present, falling back on time.time()")
    print(
        "WARNING: please do not change the system time while there is progress indicator, otherwise it will get confused")
    gettime = time.time

MAX = 300

PROGRESSBAR_STYLE = [
    ('trough', {'sticky': 'nswe', 'children': [
        ('pbar', {'side': 'left', 'sticky': 'ns'}),
        ('label', {'side': 'top', 'sticky': 'ns'}),
    ]}),
]


def format_hms(seconds_remaining):
    seconds = int(seconds_remaining) % 60
    if seconds_remaining > 60:
        minutes = int(seconds_remaining // 60) # for some reason floordiv returns a float.
        if minutes > 60:
            hours = int(minutes // 60)
            minutes %= 60
            if hours > 24:
                days = int(hours // 24)
                hours = hours % 24
                # I'm not gonna go past days.  If we get up into months or years, the user can do
                # the math themselves before posting on r/softwaregore and blaming me for their internet
                # connection.
                formatted_time_remaining = '{}d {}h {}m {}s'.format(days, hours, minutes, seconds)
            else:
                formatted_time_remaining = '{}h {}m {}s'.format(hours, minutes, seconds)
        else:
            formatted_time_remaining = '{}m {}s'.format(minutes, seconds)
    else:
        formatted_time_remaining = '{0:.2f}s'.format(seconds_remaining)
    # Could I just use four return statements?  Yes, but I think it's more literate this way.
    return formatted_time_remaining


RUNNING_AVERAGE_TIME = 15
PROGRESS_UPDATE_INTERVAL = 0


class TimestampedRunningAverage:
    def __init__(self, max_age):
        self.max_age = max_age
        self._queue = collections.deque()
        self._running_total = 0

    def update(self, entry, timestamp):
        """Add a sample to the pool and return the new average rate.
        CPython's performance is so bad that this actually appreciably impacts transfer rate.
        Maybe I should just learn Cython.  Or C++.
        """
        self._queue.append((entry, timestamp))
        self._running_total += entry
        expiry_time = timestamp - self.max_age
        while self._queue[0][1] <= expiry_time:
            self._running_total -= self._queue.popleft()[0]
        #return (sum(x[0] for x in self._queue)/(timestamp - self._queue[0][1])) if len(self._queue) >= 2 else None
        return (self._running_total / (timestamp - self._queue[0][1])) if len(self._queue) >= 2 else None


class ProgressFrame(tkinter.Frame):
    def __init__(self, parent, determinate_progress_str, indeterminate_progress_str, task_progress_str):
        super().__init__(parent)
        self._determinate_str = determinate_progress_str
        self._indeterminate_str = indeterminate_progress_str
        self._progress_str = task_progress_str
        self._style = tkinter.ttk.Style(self)
        self._style.layout('Horizontal.OverallProgressbar', PROGRESSBAR_STYLE)
        self._style.layout('Horizontal.TaskProgressbar', PROGRESSBAR_STYLE)
        self.overall_label = tkinter.Label(self, text='Current Task: Doing Absolutely Nothing, Quite Slowly')
        self.overall_label.pack(side='top', anchor='w')
        self.overall_var = tkinter.IntVar()
        self.overall_pbar = tkinter.ttk.Progressbar(self, style='OverallProgressbar', max=MAX,
                                                    variable=self.overall_var)
        self.overall_pbar.pack(side='top', fill='x')
        self.task_var = tkinter.IntVar()
        self.task_pbar = tkinter.ttk.Progressbar(self, style='TaskProgressbar', variable=self.task_var,
                                                 mode='indeterminate')
        self.task_pbar.pack(side='top', fill='x')
        # these seem like sane defaults at the time of writing
        # if experience has taught me one thing, it's that that will change very quickly once I start writing the rest
        # I wiill probably make them into parameters later.
        self.overall_determinate = False
        self.overall_total = 50
        self.configure_task(False, 1024*1024)
        self._progress_running_average = TimestampedRunningAverage(RUNNING_AVERAGE_TIME)
        self._next_progress_update_time = None
        self._progress_since_last_update = 0
        # These are instance variables because I want to cache their values, to avoid slowing down the loop
        # by recomputing them all the time.
        self._progress_per_second = ''
        self._estimated_time_remaining = ''

    def configure(self, determinate, max_):
        self.overall_total = max_
        self.overall_determinate = determinate
        self.overall_pbar.configure(mode='determinate' if determinate else 'indeterminate', max=max_)

    def task_complete(self):
        self.overall_pbar.step()
        self._update_overall_pbar()

    def _update_overall_pbar(self):
        val = self.overall_var.get()
        self._style.configure('Horizontal.OverallProgressbar',
                              text=(
                                  self._determinate_str if self.overall_determinate else self._indeterminate_str).format(
                                  current=val, max=self.overall_total, percentage=val * 100 / self.overall_total))

    def progress(self, progress, replace_progress_text=None):
        self.task_pbar.step(progress)
        if replace_progress_text:
            self._progress_str = replace_progress_text
        current_time = gettime()
        progress_thus_far = self.task_var.get()
        self._progress_since_last_update += progress
        if self._next_progress_update_time is None or current_time >= self._next_progress_update_time:
            self._next_progress_update_time = current_time + PROGRESS_UPDATE_INTERVAL
            progress_per_sec = self._progress_running_average.update(self._progress_since_last_update, current_time)
            self._progress_since_last_update = 0
            if progress_per_sec:
                if progress_per_sec > 1_800_000_000:  # TODO remove the underscores for pre-Python 3.8 compatibility
                    self._progress_per_second = '%.2fG' % (progress_per_sec / 1_000_000_000)
                elif progress_per_sec > 1_800_000:
                    self._progress_per_second = '%.2fM' % (progress_per_sec / 1_000_000)
                elif progress_per_sec > 1_800:
                    self._progress_per_second = '%.2fk' % (progress_per_sec / 1_000)
                else:
                    per_sec_formatted = str(progress_per_sec)
                if self.task_determinate:
                    seconds_remaining = (self.task_total - progress_thus_far) / progress_per_sec
                    self._estimated_time_remaining = format_hms(seconds_remaining)
                else:
                    self._estimated_time_remaining = '???'
            else:
                # just use a blinking indicator.
                per_sec_formatted = time_remaining_formatted = ' --- ' if current_time % 2 > 1 else '     '
        if self.task_determinate:
            percentage = progress_thus_far * 100 / self.task_total
        else:
            percentage = 0
        # self._last_progress_time = current_time
        self._style.configure('Horizontal.TaskProgressbar', text=self._progress_str.format(
            progress=progress_thus_far, total=self.task_total, percentage=percentage, rate=self._progress_per_second,
            remaining=self._estimated_time_remaining))

    def configure_task(self, determinate, max_):
        self.task_determinate = determinate
        self.task_total = max_
        self.task_pbar.configure(mode='determinate' if determinate else 'indeterminate', max=max_)


import random


def simulate_download(pframe):
    # add randomness to the download speed to simulate an unstable internet connection
    #pframe.progress(random.randint(2048, 4096))
    t1=time.perf_counter()
    pframe.progress(10000)
    t2=time.perf_counter()
    print(t2-t1)
    pframe.after(1, simulate_download, pframe)
 


if __name__ == '__main__':
    root = tkinter.Tk()
    f = ProgressFrame(root, '{current}/{max} ({percentage:.1f}%)', '{current} tasks processed; unknown remaining',
                      '{progress}/{total} ({percentage:.1f}%) {rate}/s ETA: {remaining}')
    f.pack(expand=1, fill='both')
    root.after(5000, f.configure_task, True, 1024 * 1024 * 32)
    root.after_idle(simulate_download, f)
    root.mainloop()
