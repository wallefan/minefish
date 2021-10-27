import ctypes
import os

everything = ctypes.CDLL(os.path.join(os.path.dirname(__file__), 'Everything64.dll'))


class _NoEverything(RuntimeError):
    pass


def _EverythingQuery(filename, strict=True):
    everything.Everything_SetSearchW(filename)
    everything.Everything_SetRequestFlags(4)  # EVERYTHING_GET_FULL_PATH_AND_FILE_NAME
    if not everything.Everything_QueryW(1):
        error = everything.Everything_GetLastError()
        if error == 2:
            # EVERYTHING_ERROR_IPC = Everything.exe is not running.
            # Most likely means Everything is not installed
            raise _NoEverything
        else:
            raise RuntimeError("Everything_QueryW() returned error code {}".format(error))
    path_buf = ctypes.create_unicode_buffer(1024)  # 1024 character paths are highly unlikely but why take the chance?
    for i in range(everything.Everything_GetNumResults()):
        length = everything.Everything_GetResultFullPathNameW(i, path_buf, 1024)
        s = ctypes.wstring_at(path_buf, length)
        if not strict or os.path.basename(s) == filename:
            yield s


def look_for_java_everywhere():
    return _EverythingQuery('java.exe')

def find_multimc():
    for path in _EverythingQuery('MultiMC.exe'):
        inst_path = os.path.join(os.path.dirname(path, 'instances'))
        if os.path.isdir(inst_path):
            for instance in os.listdir(inst_path):

