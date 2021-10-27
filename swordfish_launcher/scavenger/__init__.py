import os

import configparser
import hashlib
import logging

logger = logging.getLogger('swordfish_launcher.scavenger')

config : configparser.SectionProxy = None

def scavenge_instance(instance):
    mods_dir = os.path.join(instance, 'mods')
    if os.path.exists(mods_dir):
        for root, dirs, files in os.walk(mods_dir):
            for file in files:
                if file.endswith('.jar'):
                    from ..downloader.cache import learn_about_mod
                    learn_about_mod(os.path.join(root, file))
    assets_dir = os.path.join(instance, 'assets')
    if os.path.isdir(assets_dir):
        scavenge_assets(assets_dir)



ASSET_CACHE = {}

def scavenge_assets(assets_dir):
    objects_dir = os.path.join(assets_dir, 'objects')
    invalid_files = []
    if os.path.isdir(objects_dir):
        for root, dirs, files in os.walk(objects_dir):
            for filename in files:
                file=os.path.join(root,filename)
                if config.getboolean('do sha1 validation'):
                    h=hashlib.sha1()
                    with open(file,'rb') as f:
                        data=f.read(8192)
                        while data:
                            h.update(data)
                            data=f.read(8192)
                    if h.hexdigest() != filename:
                        logger.warning('SHA-1 mismatch: %s' % file)
                        invalid_behavior = config.get('sha1 mismatch behavior', fallback='delete').lower()
                        if invalid_behavior == 'delete':
                            # assume the file is corrupt and delete it.
                            # missing files will be redownloaded by the game the next time it tries to start.
                            os.unlink(file)
                        elif invalid_behavior == 'ignore':
                            # asset files may have been deliberately modified and/or replaced by the user
                            # to change the experience without using a resource pack.  This is not recommended,
                            # but some people do it.
                            invalid_files.append(file)
                        continue
                if config.getboolean('do deduplication'):
                    for existing_file in ASSET_CACHE.setdefault(filename, []):
                        if os.path.samefile(file, existing_file):
                            # file has already been deduplicated
                            break
                        else:
                            try:
                                os.link(existing_file, file+'.tmp')
                            except (OSError, PermissionError):
                                # probably ended up here because we attempted a cross-device hardlink.
                                # Windows sometimes raises a PermissionError for operations it doesn't want you to do
                                # because they are impossible.  This obviously makes no sense, but :shrug:
                                continue
                            else:
                                os.replace(file+'.tmp', file)
                                logger.info('Successfully deduplicated %s -> %s', existing_file, file)
                                break
                    else:
                        # all deduplication attempts failed
                        ASSET_CACHE[filename].append(file)
                else:
                    ASSET_CACHE.setdefault(filename, []).append(file)

