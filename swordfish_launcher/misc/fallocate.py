import os

if os.name == 'nt':
    import ctypes
    import msvcrt
    set_file_information = ctypes.windll.kernel32.SetFileInformationByHandle

    class AllocationInfo(ctypes.Structure):
        _fields_ = [('AllocationSize', ctypes.c_longlong)]

    def prealloc(file, length):
        """Tell the filesystem to preallocate `length` bytes on disk for the specified `file` without increasing the
        file's length.
        In other words, advise the filesystem that you intend to write at least `length` bytes to the file.
        """
        allocation_info = AllocationInfo(length)
        retval = set_file_information(ctypes.c_long(msvcrt.get_osfhandle(file.fileno())),
                                      ctypes.c_long(5),  # constant for FileAllocationInfo
                                      ctypes.pointer(allocation_info),
                                      ctypes.sizeof(allocation_info)
                                      )
        if retval != 1:
            raise OSError('SetFileInformationByHandle failed')

else:
    # I've looked and looked for a way to do this on POSIX, and haven't found one.
    # fallocate() actually does the opposite of what I want: it sets the file's apparent size
    # by allocating a sparse extent.  The only thing it does that I want it to do is check for
    # available disk space and fail if there isn't enough.
    def prealloc(file, length):
        pass
