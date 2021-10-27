"""Package up SwordfishLauncher/SwordMC into a portable installation on a flash drive.
"""

try:
    import psutil
except ImportError:
    psutil=None

import os

def find_flashdrives():
    for drive in psutil.disk_partitions():
        mount_options = drive.opts.split(',')
        if 'rw' not in mount_options:
            continue
        if psutil.WINDOWS:
            if 'removable' in mount_options and drive.mountpoint:
                # NT only.  mount_options will always contain one of 'fixed', 'removable', or 'cdrom'
                # 'fixed' for ATA/SCSI disks, 'removable' for USB mass storage and SD cards,
                # and 'cdrom' for any and all optical media
                # (possibly others idk)
                yield drive.mountpoint
        else:
            # POSIX doesn't tell you whether a disk is removable or fixed or whatever because it doesn't make the
            # distinction.  How then do we distinguish between removable media and other types?
            # We could check for FAT filesystems, but some removable disks are NTFS, and /boot/efi is FAT32.
            # We could check if it's FAT or NTFS, that its mountpoint doesn't start with /boot, and that it doesn't have
            # a folder named Windows (to rule out mounted Windows partitions), but NTFS is handled by FUSE and lists
            # its filesystem type as fusefs, and so do a lot of other things.  We can't discriminate based on filesystem
            # size or free space because then there would be no way to distinguish between a laptop's 1TB internal data
            # HDD and a 1TB USB3.0 WD Passport.  I *suppose* we could discriminate based on transfer speed, but that
            # seems like a horrible idea for a number of reasons.

            # I could simply not distinguish and present all mounted volumes as options for the user to choose from.
            # This is a bad idea for several reasons.  Firstly,

            # I would love to be able to assume that anyone savvy enough to be using Linux would know which mountpoint
            # is their flashdrive.  Unfortunately, I know firsthand that this is not the case, both from myself at age
            # 12 and from my sisters.  And that's leaving MacOS completely out of the picture.
            pass

