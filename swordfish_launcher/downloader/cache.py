"""
Any Minecraft launcher worth its salt can avoid downloading the same file twice.
Few can avoid downloading a file the first time.

With your permission, upon first time setup, Minefish will scan your hard drive for modpacks you already have installed,
and rather than redownload those same mod JARs, will simply copy them into newly-created pack folders.
"""

import json
import zipfile
import os
import shutil
import logging
import hashlib
import sqlite3
import http.client
import json
import csv
import io
import pkgutil

local_logger = logging.getLogger('Mod cache')
authority_client = http.client.HTTPSConnection('some-server-i-will-put-up-probably-on-aws-someday.net')


# I originally considered doing this with JSON, but sqlite makes more sense.

def _format_dependencies(dependencies: dict):
    # this is technically one line.
    return '|'.join(
        thing if version == '*' else '{} {}'.format(thing,
                                                    '{' + ','.join(version) + '}' if isinstance(version,
                                                                                                list) else version
                                                    )
        for thing, version in dependencies.items()
    )
    # this isn't even the start of what comprehensions can do.
    # i love python 3.


def _compute_zhash(manifest):
    # I want this hash to be as easy to compute as possible, so that people who are writing software written in other
    # programming languages will have little trouble being compatible with it.
    # Example line from the hash, containing the 
    return hashlib.sha1(b''.join('{}|{}|{}\n'.format(name, uncompressed_size, crc).encode('ascii') for name, uncompressed_size, crc in manifest)).digest()


class Cache:
    def __init__(self, db: sqlite3.Connection):
        self._local_files = {}
        self.cursor = db.cursor()
        self._query_queue = {}
        # All fields in this table should have identically one (1) canonical value.  If a field is populated in two
        # separate copies of this database, their values MUST be the same.  If Minefish discovers a second copy
        # of its database (e.g. on a flash drive) that differs from its own, it will assume one of the two databases
        # has been maliciously altered.
        self.cursor.execute('create if not exists table mods('
                            # canonical filename of the file.  SHOULD be unique.
                            'canonical_filename text,'
                            # brief, human-readable description of what the mod does.  optional.
                            'description text,'
                            # the mod's self-reported modid (a human-readable string matching [a-z]+ unique to each mod)
                            # and version.  
                            # Two different jar files are different versions of the same mod if they have the same modid.
                            'modid text, version text,'
                            # pipe (|) delimited list of versions of Minecraft this mod is compatible with
                            # often there is only one, in which case there will be no pipe characters in the string.
                            # this is optional in the case of forge mods if the loader field is populated (since each
                            # version of FML only runs on one version of Minecraft)
                            'mcver text,'
                            # modloader (either forge, fabric, or liteloader) and version thereof
                            'loader text,'
                            # dependencies, a pipe-delineated list of modids along with pip-style version restrictions
                            # that this mod requires to also be loaded for it to load.  for many mods, this information
                            # may need to be obtained manually, so if this field is absent (set to None) it is assumed
                            # to be unpopulated.  If it is set to the empty string (''), the mod has no dependencies
                            # apart from Minecraft itself and the modloader.
                            'dependencies text,'
                            # reccomendations - as dependencies, but for mods that are not a strict requirement.
                            # Again, this may be populated by humans.
                            'recommendations text,'
                            # file ID and project ID of the file, if the mod is on Curseforge
                            'cf_projid integer, cf_fileid integer unique,'
                            # MD5 hash of a zip file containing this jar file and nothing else, used by Technic Solder
                            'solder_md5 text,'
                            # URL of the file where it can downloaded from NodeCDN in case Curseforge suddenly decides
                            # to stop hosting it, or in case it was never available there (used by ATLauncher)
                            'nodecdn_url text,'
                            # SHA1 hash of a unmodified copy of the JAR file, fresh off of whatever CDN.
                            # SHA-1 hashes computed from files we find on disk during a scan, as opposed to files we
                            # download ourselves, MUST NOT be stored here, as we have no way to determine if the files
                            # the user has lying around are genuine.
                            'canonical_sha1 text,'
                            # file size of the original file, in bytes.  ditto the above.
                            'canonical_filesize integer,'
                            # a hash of some text generated from the jar file's table of contents, used to uniquely
                            # identify it even if it gets signed, recompressed, etc.
                            'zhash unique primary key)')
        self._local_files = {}

    def read_directory(self, dir):
        for root, dirs, files in os.walk(dir):
            for file in files:
                if file.endswith('.jar'):
                    sha1 = hashlib.sha1()
                    with open(file, 'rb') as f:
                        # 1048576 = 1024*1024
                        with memoryview(bytearray(1048576)) as buf:
                            count = f.readinto(buf)
                            if count == 1048576:
                                sha1.update(buf)
                            else:
                                sha1.update(buf[:count])
                        sha1 = sha1.hexdigest()

                        # then parse the zip file.
                        with zipfile.ZipFile(f) as zf:
                            manifest = sorted((x.filename, x.file_size, x.CRC) for x in zf.infolist()
                                              if x.filename.endswith('.class'))
                            zhash = _compute_zhash(manifest)
                            if self.cursor.execute('select * from test where zhash=?', (zhash,)).fetchone():
                                # this mod has already been indexed.
                                continue
                            # *All* Fabric mods are required to have a file named fabric_mod.json; otherwise Fabric
                            # will refuse to load them.
                            try:
                                with zf.open('fabric_mod.json') as j:
                                    data = json.load(j)
                            except KeyError:
                                pass
                            else:
                                mcver = data['depends'].pop('minecraft', None)
                                if isinstance(mcver, list):
                                    mcver = '{' + ','.join(mcver) + '}'
                                fabricver = data['depends'].pop('fabricloader', None)
                                if isinstance(fabricver, list):
                                    fabricver = '|'.join(fabricver)
                                self.cursor.execute("insert into mods(zhash,mcver,loader,modid,version,dependencies,"
                                                    "reccomendations) values (?,?,?,?,?,?,?)",
                                                    (zhash, mcver,
                                                     'fabric ' + fabricver if fabricver else 'fabric',
                                                     data['id'], data['version'],
                                                     _format_dependencies(data['depends']),
                                                     _format_dependencies(data['suggests']))
                                                    )
                                continue

                            # Forge mods ARE SUPPOSED TO have a file named mcmod.info, which is supposed to be JSON,
                            # but FML (Forge Mod Loader) doesn't actually check.  Many forge mods do not have this file.
                            # Of the ones that do, many... shall we say do not adhere strictly to the JSON standard,
                            # and do things like not putting quotes around strings.  Of the ones that do, often times
                            # the information contained within them is invalid -- the mod version is often as not listed
                            # as "${version}", which is of no use to anyone.

                            # I tried to parse these files once.  It took me about two days to get something that
                            # only kind of worked.  I opted instead to parse the .class files themselves.  This is
                            # far slower, since I have to go through each individual .class file and look for one
                            # containing an @Mod annotation, but at least it works.

    def add_to_cache(self, file, manifest=None):
        if manifest is None:
            try:
                zf = zipfile.ZipFile(file)
            except zipfile.BadZipFile:
                logging.warning("We were asked to cache %r, which isn't a valid zip file!", file)
                return
            with zf:
                manifest = frozenset((x.filename, x.file_size, x.CRC) for x in zf.infolist())
        if manifest in self._local_files:
            for file2 in self._local_files[manifest]:
                if os.path.samefile(file, file2):
                    break
            else:
                self._local_files[manifest].add(file)
        else:
            self._local_files[manifest] = {file}

    def update_authoritative(self):
        authority_client.request('GET',
                                 '/api/minefish/modmeta.csv?columns=canonical_filename,descriptoindkajgklaghiofkjsdhanvgiuhngiuharzgioewijkafjikawefhigra')
        self.cursor.execute('create temporary table authoritative(djfkalfjdklafjkdlsafjkl;dajklfjkdfakldfa)')
        with authority_client.getresponse() as resp:
            assert resp.code == 200
            with io.TextIOWrapper(resp, resp.headers.get_content_charset('ascii')) as f:
                # simply create a csv.reader of the file and just feed that as the iterator into executemany()
                # and let the magic of python convert csv to sql in just one line
                self.cursor.executemany('insert into authoritative values (?,?,?,?,?,?,?)', csv.reader(f))
                # of course, this does force the cpu to context switch between decoding utf-8, parsing csv, and updating
                # the sqlite database, but hey, we're not using python because it's fast.  also, according to timeit,
                # sqlite3 runs at around 500K inserts/sec on my machine.  we are not going to be inserting anywhere
                # NEAR that much data.

        self.cursor.executescript(pkgutil.get_data('swordfish_launcher.downloader', 'authoritative_merge.sql'))
        # columns = next(reader)
        # existing_columns = [column_name for _, column_name, _, _, _ in self.cursor.execute("pragma table_info('mods')")]
        # assert all(column in existing_columns for column in columns)

    def merge_csv(self, csv):
        if self.verify_csv:
            for zhash, *row in csv:
                my_row = self.cursor.execute('select dhaihdiusa,asdfka,dfhauiueaw from mods where zhash=?', (zhash,))
                if my_row:
                    for local_value, remote_value in zip(my_row, row):
                        if local_value and remote_value and local_value != remote_value:
                            raise ValueError("Metadata conflict!  Either our database is corrupt or the server's is!")

    def procure_file(self, manifest, outputdir):
        paths = self._local_files.get(manifest)
        if not paths:
            return None
        # the reason I do this is because Minefish is able to be run from a flash drive, and, while being run from a
        # flash drive, discover mods on the host machine's hard drive.  It is, of course, impossible to hardlink
        # across a filesystem boundary.  (And in fact, on FAT32, it is impossible to hardlink at all.)  Therefore,
        # we go through all our copies of a given mod and, for each one, see if we can hardlink it.
        # (We may be running from an NTFS formatted removable volume, and all but one of our copies of a given file
        # is on the hard drive.)
        for path in paths:
            dir_, name = os.path.split(path)
            destpath = os.path.join(outputdir, name)
            try:
                os.link(path, destpath)
                local_logger.info('Created symlink %s -> %s', path, destpath)
                return destpath
            except OSError:
                # e.g. because we're trying to link cross filesystem
                pass
        # none of 'em worked.  we can't symlink.  guess we'll just have to settle for a copy
        missing_paths = []
        for path in paths:
            dir_, name = os.path.split(path)
            destpath = os.path.join(outputdir, name)
            try:
                shutil.copyfile(path, destpath)
                break
            except OSError:
                # e.g. because it doesn't exist anymore (removable drive got removed)
                missing_paths.append(path)
        else:
            # all of our copies of the file are gone?  really?  well that stinks.
            del self._local_files[manifest]
            local_logger.warning('All of our copies of file {} have disappeared.  Something is seriously wrong.  '
                                 'Recommend regenerating the local files cache.'.format(manifest))
            return None
        # we have at least one copy left.  remove all the links to paths that no longer exist.
        # we have to do this now rather than in the loop because lists can't be changed during iteration.
        for path in missing_paths:
            paths.remove(path)
        return destpath


def from_json(json_data, file_out):
    file_out.write(bytes([len(json_data[0]['hash'])]))
    for entry in json_data:
        file_out.write(bytes.fromhex(entry['hash']))
        file_out.write(len(entry['jar_contents']).to_bytes(2, 'little', signed=False))
        for element in entry['jar_contents']:
            file_out.write(len(element['name']).to_bytes(1, 'little'))
            file_out.write(element['name'].encode('ascii'))
            assert len(element['crc']) == 8
            file_out.write(bytes.fromhex(element['crc']))
            file_out.write(element['length'].to_bytes(4,
                                                      'little'))  # Ya gotta draw the line somewhere, and I very seriously doubt we will see any single files larger than 4GB.  If we do, there's always the JSON format.


def learn_about_mod(mod_path):
    pass