import json.decoder
import zipfile
import pathlib
import time
import string

WORDCHARS = string.ascii_letters + string.digits + '._'

# So apparently Minecraft modders are
# to put it mildly
# a bit new to the concept of JSON.
# * many, MANY mods list 'mod_MinecraftForge' as a dependency
# * Several mods mods list "@VERSION@" as their version.
# * ambientsounds's mcmod.info doesn't have a version line at all
# * jecalculation's has the line
#       "dependencies": [jei],
# * LevelUp has the line:
#       "mcversion": 1.7.10,
#   which Python's JSON parser will try to interpret as a number
# * The customized version of xreliquary used in TPPI tries to use newlines instead of commas as array delimiters

# So I had to get creative.

# This is a straight copy of json/scanner.py, except that I removed the StopIteration raise and instead implemented
# a bare string parser.


import re

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))


# Modified JSON scanner to interpret bare words as JSON strings.

def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    strict = False
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    memo = context.memo

    def _scan_once(string, idx, *, WORDCHARS=WORDCHARS):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration(idx)

        if nextchar == '"':
            return parse_string(string, idx + 1, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), strict,
                                _scan_once, object_hook, object_pairs_hook, memo)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        # I somehow doubt mcversion will have any numbers.
        # Also we need it to not try to parse numbers because there are a few imbeciles who try to write
        # "mcversion":1.7.10
        # and the below code will try to interpret that as a float.

        # m = match_number(string, idx)
        # if m is not None:
        #     integer, frac, exp = m.groups()
        #     if frac or exp:
        #         res = parse_float(integer + (frac or '') + (exp or ''))
        #     else:
        #         res = parse_int(integer)
        #     return res, m.end()
        # elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
        #     return parse_constant('NaN'), idx + 3
        # elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
        #     return parse_constant('Infinity'), idx + 8
        # elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
        #     return parse_constant('-Infinity'), idx + 9
        else:
            # it is a name, but those incompetent monkeys can't be bothered to make it a string
            stopidx = idx + 1
            while string[stopidx] in WORDCHARS:
                stopidx += 1
            return string[idx:stopidx], stopidx

    def scan_once(string, idx):
        try:
            return _scan_once(string, idx)
        finally:
            memo.clear()

    return scan_once


# Modified JSON array parser to allow f***ing newlines as array delimiters.
WHITESPACE = re.compile(r'[ \t\n\r]*', re.VERBOSE | re.MULTILINE | re.DOTALL)
WHITESPACE_STR = ' \t\n\r'


def JSONArray(s_and_end, scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    s, end = s_and_end
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    _append = values.append
    while True:
        try:
            value, end = scan_once(s, end)
        except StopIteration as err:
            raise json.decoder.JSONDecodeError("Expecting value", s, err.value) from None
        _append(value)
        nextchar = s[end:end + 1]
        found_whitespace = nextchar in _ws
        if found_whitespace:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            if found_whitespace:
                # enable using whitespace as delimiter because they can't be bothered to proofread.
                end -= 1
            else:
                raise json.decoder.JSONDecodeError("Expecting ',' delimiter or whitespace", s, end - 1)
        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

json_parser = json.decoder.JSONDecoder(strict=False)
json_parser.parse_array = JSONArray
json_parser.scan_once = py_make_scanner(json_parser)


def index_mods(path: pathlib.Path):
    times = []
    index = {}
    for jarfile in path.rglob('*.jar'):
        t1 = time.perf_counter()
        data = get_info(jarfile)
        if data is None:
            print(jarfile.name, 'does not HAVE an mcmod.info')
            continue
        if 'modList' in data:
            data = data['modList']
        elif 'modlist' in data:
            data = data['modlist']
        if not data:
            print(jarfile.name, 'does not list ANY mods in its mcmod.info')
        elif len(data) > 1:
            print(jarfile.name, [mod['modid'] for mod in data])
        for mod in data:
            index.setdefault(mod['modid'], {})[mod.get('version', None)] = jarfile.name
        t2 = time.perf_counter()
        times.append(t2 - t1)
    print('Indexed', len(times), 'mods in', sum(times), 'seconds; avg', sum(times) / len(times) if times else 0,
          'per mod')
    return index


def get_info(jarfile):
    try:
        with zipfile.ZipFile(jarfile) as zf:
            if 'mcmod.info' not in zf.namelist():
                return None
            data = zf.read('mcmod.info').decode('cp1252')
    except Exception as e:
        print(jarfile, 'broke our thingy because',e)
        return None
    try:
        return json_parser.decode(data)
    except json.decoder.JSONDecodeError as e:
        print(jarfile)  # DOX that mf
        print(data)
        lines = data.splitlines()
        print(lines[e.lineno - 1])
        print(' ' * (e.colno - 1) + '^')
        raise


def index_mods_by_class(path: pathlib.Path):
    times = []
    index = {}
    from swordfish_launcher.moddb.class_parser import get_info
    for jarfile in path.rglob('*.jar'):
        t1 = time.perf_counter()
        data = get_info(jarfile)
        if not data:
            print(jarfile.name, 'does not have ANY @Mod annotations')
        elif len(data) > 1:
            print(jarfile.name, [mod['modid'] for mod in data])
        else:
            print(data[0]['modid'])
        for mod in data:
            index.setdefault(mod['modid'], {})[mod.get('version', None)] = jarfile.name
        t2 = time.perf_counter()
        times.append(t2 - t1)
    print('Indexed', len(times), 'mods in', sum(times), 'seconds; avg', sum(times) / len(times) if times else 0,
          'per mod')
    return index


if __name__ == '__main__':
    #p=pathlib.Path(r'../../../../MultiMC/instances/Eternal-1.3.5.3/minecraft')
    p=pathlib.Path('/srv/mc/eternal37/mods')
    #p = pathlib.Path("/tank/home/seanw/Documents/Backups/homedir from dad's silver laptop/AppData/Roaming/.technic")
    #index={}
    #for mods_dir in p.rglob('mods'):
    #    index.update(index_mods(mods_dir))
    index = index_mods_by_class(p)
    # index.update(index_mods(pathlib.Path(r'C:\Users\sawor.000\MultiMC\instances\Eternal-1.3.5.3\minecraft\coremods')))
    from swordfish_launcher.mod_processor.server_ping import server_list_ping
    print(index)
    server_ver, mods = server_list_ping('192.168.191.50')
    jarfiles_required = set()
    missing_mods = []
    misversioned_mods = []
    perfect_mods = []
    for modid, ver in mods.items():
        available_versions = index.get(modid)
        if available_versions is None:
            print(f'no jarfiles at all found for {modid} (server needs version {ver})')
            if 'core' not in modid:
                missing_mods.append(modid)
            continue
        if ver.upper() == 'ANY':
            ver = max(
                available_versions.keys())  # i do not think this is wise, as it will sort 0.9 before 0.10 but I have no other proposal.
        jarfile = available_versions.get(ver)
        if jarfile is not None:
            perfect_mods.append(modid)
        else:
            if None in available_versions:
                jarfile = available_versions[None]
                print(f"{jarfile}'s mcmod.info does not list a version; assuming it matches {ver} specified by server")
            else:
                print(
                    f'none of our versions of {modid} ({", ".join(available_versions)}) match the version on the server ({ver})')
                misversioned_mods.append(modid)
        jarfiles_required.add(jarfile)
    unused_mods = []
    total_jars = 0
    for jarfile in p.rglob('*.jar'):
        total_jars += 1
        if jarfile.name not in jarfiles_required:
            print('Did not use', jarfile.name)
            with zipfile.ZipFile(jarfile) as zf:
                if 'mcmod.info' not in zf.namelist():
                    print("no mcmod.info, so it's forgivable")
                else:
                    with zf.open('mcmod.info') as f:
                        data = json_parser.decode(f.read().decode('utf8'))
                        if 'modList' in data:
                            data = data['modList']
                        unused_mods.extend(mod['modid'] for mod in data if mod['modid'] not in misversioned_mods)
    print(len(perfect_mods), 'mods matched perfectly', len(perfect_mods)*100/len(mods), '%')
    perfect_mods += misversioned_mods
    print(len(perfect_mods), 'mods names matched', len(perfect_mods) * 100 / len(mods), '%')
    print('detected', len(jarfiles_required), 'out of', total_jars, 'jars', len(jarfiles_required) * 100 / total_jars, '%')
    for mod in missing_mods:
        print(mod, 'is only on the server')
    for mod in unused_mods:
        print(mod, 'is only on the client')
