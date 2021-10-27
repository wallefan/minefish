
import os

def look_for_JAVA_HOME():
    return (os.environ.get('JAVA_HOME'), 0)

def look_for_java_in_windows_registry():
    try:
        import winreg
    except ImportError:
        print("we're not on windows")
        return
    if hasattr(winreg, 'KEY_WOW64_64KEY'):
        keytypes=((winreg.KEY_WOW64_64KEY, 64), (winreg.KEY_WOW64_32KEY, 32), (0, 0))
    else:
        keytypes=(0,0)
    for keytype, width in keytypes:
        for registry_key, isjdk in ((r'SOFTWARE\JavaSoft\Java Runtime Environment', False),
                                    (r'SOFTWARE\JavaSoft\Java Development Kit', True)):
            try:
                hkey=winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, registry_key, winreg.KEY_READ | keytype)
            except OSError as e:
                print('unable to open key', e)
                continue
            i=0
            try:
                recommended = winreg.QueryValueEx(hkey, 'CurrentVersion')[0]
            except OSError:
                recommended = ''
            else:
                try:
                    yield _read_java_regkey(hkey, recommended), recommended, True, width, isjdk
                except FileNotFoundError:
                    pass
            while True:
                try:
                    subkey = winreg.EnumKey(hkey, i)
                except OSError:
                    break
                if subkey != recommended:
                    try:
                        yield _read_java_regkey(hkey, subkey), subkey, False, width, isjdk
                    except FileNotFoundError:
                        # this JRE has been incompletely uninstalled
                        pass
                i += 1


def _read_java_regkey(hkey, subkey):
    import winreg
    key = winreg.OpenKeyEx(hkey, subkey)
    result = winreg.QueryValueEx(key, 'JavaHome')[0]
    key.Close()
    return result


def test_java(path):
    import subprocess
    return subprocess.Popen([path, '-version'], stderr=subprocess.PIPE).communicate()[1].decode('ascii').splitlines()
