import json
import zipfile
import pathlib

def generate_cache(directory):
    path = pathlib.Path(directory)
    assert path.is_dir()
    cache = {}
    for jar_path in path.rglob('*.jar'):
        try:
            zf = zipfile.ZipFile(jar_path)
        except zipfile.BadZipFile:
            print(jar_path.relative_to(path), "isn't a valid zip file!?")
            continue
        with zf:
            manifest = frozenset((x.filename, x.file_size, x.CRC) for x in zf.infolist())
        if manifest in cache:
            cache[manifest].add(jar_path)
        else:
            cache[manifest] = {jar_path}
    return cache