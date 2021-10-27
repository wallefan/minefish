import os

def look_for_multimc_in_process_list():
    """Look for a MultiMC install by looking for multimc.exe in the process list,
    querying the image path, and assuming the install dir is in the same place."""
    if os.name != 'nt':
        # no point looking for multimc in the process list on POSIX.
        # it's always installed to the same place (/usr/bin) separate from its files.
        # besides, on POSIX, multimc always puts its files in the same place.  no point looking around at all.
        print("no point, we're on POSIX.")
        return []
    try:
        import psutil
    except ImportError:
        print("psutil isn't installed and I can't read the process list without it.")
        return []
    results = [os.path.dirname(path) for name, path in psutil.process_iter('name', 'exe') if name == 'MultiMC']
    if not results:
        print("no dice. MultiMC isn't open.")
    return results

def look_for_multimc_in_predefined_locations():
    USERPROFILE = os.environ['USERPROFILE']
    from swordfish_launcher.misc import knownpaths
    downloads = os.path.expandvars(knownpaths.get_path(knownpaths.FOLDERID.Downloads))
    return [USERPROFILE+r'\Desktop\multimc', downloads+r'\mmc-stable-win32']

def look_for_multimc():
    s=set()
    for func in (look_for_multimc_in_predefined_locations, look_for_multimc_in_process_list):
        print(func.__name__.replace('_', ' ')+'...')
