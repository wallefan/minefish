import struct
import zipfile

from swordfish_launcher.misc import mutf8

# HDR_STRUCT = 147.185.192.63
HDR_STRUCT_1 = struct.Struct('>IHHH')  # magic, majver, minver, constant_pool_count
# followed by constant pool (variable length), followed by
HDR_STRUCT_2 = struct.Struct('>HHHH')  # acc_flags, this_class, super_class, interfaces_count
# followed by interface list (variable length), followed by
HDR_STRUCT_3 = struct.Struct('>H')  # fields_count
# followed by fields, followed by
HDR_STRUCT_4 = struct.Struct('>H')  # methods_count
# followed by methods, followed by
HDR_STRUCT_5 = struct.Struct('>H')  # attributes_count


# followed by attributes (which is what we're after).

# Using file reads here instead of byte array indexing would make this code much
# prettier and easier to read, but I very much care about speed, so

# Also you'll note that this code completely ignores floats, ints, longs, and doubles and just skips over them.
# That's because this class parser is purpose built and just has to extract strings, but in case I need that
# functionality later, I'm keeping the definitions in.
def _parse_constant_pool(data, idx, constant_info_count):
    constant_pool = [None for _ in range(constant_info_count)]
    i = 0
    while i < constant_info_count:
        tag = data[idx]
        idx += 1
        if tag == 1:  # CONSTANT_Utf8
            length = int.from_bytes(data[idx:idx + 2], 'big')
            idx += 2
            # This is not mentioned at all in the JVM documentation, but a UTF-8 string "bytes" is always
            # followed by a rather long string of seemingly arbitrary bytes.

            constant_pool[i] = mutf8.decode(data[idx:idx + length])
            idx += length  # 2 for the length of the length field.
        elif tag in (3, 4):  # CONSTANT_Integer and CONSTANT_Float
            if tag == 3:  # bother parsing ints because they're actually useful.
                constant_pool[i], = struct.unpack('>l', data[idx:idx+4])
            idx += 4
        elif tag in (5, 6):  # CONSTANT_Long and CONSTANT_Double
            idx += 8
            i += 1  # 8 byte values take two slots for whatever reason
        elif tag == 7:  # CONSTANT_Class
            nameidx, = struct.unpack('>H', data[idx:idx + 2])
            constant_pool[i] = ('class', nameidx - 1)
            idx += 2
        elif tag == 8:  # CONSTANT_String
            value, = struct.unpack('>H', data[idx:idx + 2])
            constant_pool[i] = ('string', value - 1)
            idx += 2
        elif tag in (9, 10, 11):  # CONSTANT_Fieldref, CONSTANT_Methodref, and CONSTANT_InterfaceMethodref, respectively
            # class_idx, name_idx = struct.unpack('>HH', data[idx:idx+4])
            idx += 4  # u2 class_index, u2 name_and_type_index
        elif tag == 12:  # CONSTANT_NameAndType
            # pretty sure I don't actually need to parse tis.
            # nameidx, descidx = struct.unpack('>HH', data[idx:idx+4])
            # constant_pool[i] = constant_pool[nameidx-1], constant_pool[descidx-1]
            idx += 4
        elif tag == 15:  # CONSTANT_MethodHandle
            idx += 3  # u1 reference_kind, u2 reference_index
        elif tag == 16:  # CONSTANT_MethodType
            idx += 2  # u2 descriptor_index
        elif tag == 18:  # CONSTANT_InvokeDynamic
            idx += 4  # u2 bootstrap_method_attr_index, u2 name_and_type_index
        else:
            assert False, 'illegal constant_table tag %d' % tag
        i += 1

    return constant_pool, idx


def parse_anno(data, idx, constant_pool, verbose=False):
    type_idx, num_pairs = struct.unpack('>HH', data[idx:idx + 4])
    idx += 4
    type_name = constant_pool[type_idx - 1]
    #if verbose:
    #    print(type_name, num_pairs)
    pairs = {}
    for _ in range(num_pairs):
        name_idx, = struct.unpack('>H', data[idx:idx + 2])
        value, idx = parse_element_value(data, idx + 2, constant_pool)
        if verbose:
            print(constant_pool[name_idx - 1], value)
        pairs[constant_pool[name_idx - 1]] = value
    return type_name, pairs, idx


def parse_element_value(data, idx, constant_pool):
    tag = data[idx:idx + 1]
    idx += 1
    if tag in b'BCDFIJSZsc':
        # it is a primitive type constant (uppercase) or string (s) or class (c).
        value_idx = int.from_bytes(data[idx:idx + 2], 'big')
        if tag == b'B':
            # boolean
            return bool(constant_pool[value_idx - 1]), idx + 2
        return constant_pool[value_idx - 1], idx + 2
    elif tag == b'e':
        # it is an enum constant.
        # I don't think we need to parse enums, but i'd like to
        type_name_idx, name_idx = struct.unpack('>HH', data[idx:idx + 4])
        # not sure why the Java spec gives us the name of the type of the enum constant
        # if all enum constants are required to be the same type as their enclosing class.
        return constant_pool[name_idx - 1], idx + 4
    elif tag == b'@':
        type_name, pairs, idx = parse_anno(data, idx, constant_pool)
        return ('anno', type_name, pairs), idx
    elif tag == b'[':
        count, = struct.unpack('>H', data[idx:idx + 2])
        idx += 2
        values = []
        for _ in range(count):
            value, idx = parse_element_value(data, idx, constant_pool)
            values.append(value)
        return values, idx
    else:
        assert False, tag


def parse_attrs(data, idx, constant_pool, attr_count, care_about_annos=False, verbose=False):
    const_value = None
    annos = []
    for _ in range(attr_count):
        nameidx, length = struct.unpack('>HL', data[idx:idx + 6])
        idx += 6
        name = constant_pool[nameidx - 1]
        if name == 'ConstantValue':
            value, = struct.unpack('>H', data[idx:idx + length])
            const_value = constant_pool[value - 1]
        elif name == 'RuntimeVisibleAnnotations' and (care_about_annos or verbose):
            starting_idx = idx
            anno_count = int.from_bytes(data[idx:idx + 2], 'big')
            idx += 2
            for _ in range(anno_count):
                type_name, pairs, idx = parse_anno(data, idx, constant_pool, verbose=verbose)
                annos.append((type_name, pairs))
            assert idx == starting_idx + length
            idx = starting_idx  # so the below idx += length will work.
        # else, we don't care about it.
        idx += length
    if isinstance(const_value, tuple) and const_value[0] == 'string':
        const_value = constant_pool[const_value[1]]
    if verbose:
        print(annos)
    return idx, const_value, annos


def skip_fields(data, idx, fields_count):
    for _ in range(fields_count):
        acc_flags, name_idx, desc_idx, attr_count = struct.unpack('>HHHH', data[idx:idx + 8])
        idx += 8
        for _ in range(attr_count):
            attr_name_idx, length = struct.unpack('>HL', data[idx:idx + 6])
            idx += 6 + length
    return idx


def parse_fields(data, idx, constant_pool, fields_count, verbose=False):
    fields = {}
    for _ in range(fields_count):
        acc_flags, name_idx, desc_idx, attr_count = struct.unpack('>HHHH', data[idx:idx + 8])
        # print(convert_access_flags(acc_flags), constant_pool[desc_idx - 1], constant_pool[name_idx - 1])
        idx, const_value, annos = parse_attrs(data, idx + 8, constant_pool, attr_count)
        fields[constant_pool[name_idx - 1]] = (acc_flags, constant_pool[desc_idx - 1],
                                               const_value, annos)
    if verbose:
        print(fields)
    return fields, idx


def convert_access_flags(flags):
    l = []
    if flags & 0x01:
        l.append('public')
    if flags & 0x02:
        l.append('private')
    if flags & 0x04:
        l.append('protected')
    if flags & 0x400:
        l.append('abstract')
    if flags & 0x20:
        l.append('synchronized')
    if flags & 0x08:
        l.append('static')
    if flags & 0x10:
        l.append('final')
    if flags & 0x100:
        l.append('native')
    if flags & 0x1000:
        l.append('synthetic')
    if flags & 0x20:
        l.append('volatile')
    if flags & 0x40:
        l.append('transient')
    if flags & 0x800:
        l.append('strictfp')
    if flags & 0x2000:
        l.append('@')
    if flags & 0x4000:
        l.append('enum')
    return ' '.join(l)


def parse_class_targeted(data):
    idx = HDR_STRUCT_1.size
    magic, major_ver, minor_ver, constant_pool_count = HDR_STRUCT_1.unpack(data[:idx])
    assert magic == 0xCAFEBABE
    # Look, idk why we have to decrement constant_pool_count.  It's in the jvm spec.  We just do
    constant_pool, idx = _parse_constant_pool(data, idx, constant_pool_count - 1)
    next_idx = idx + HDR_STRUCT_2.size
    access_flags, this_class, super_class, interfaces_count = HDR_STRUCT_2.unpack(data[idx:next_idx])
    assert 0 < this_class < constant_pool_count
    assert 0 <= super_class < constant_pool_count, (super_class, constant_pool_count)
    # each interface is a 2 byte index into the constant pool.
    # We don't care about interfaces thoguh so just skip over them.
    idx = next_idx + 2 * interfaces_count
    fields_count, = struct.unpack('>H', data[idx:idx + 2])
    fields, idx = parse_fields(data, idx + 2, constant_pool, fields_count)
    # same method that parses fields can parse methods since they use the same internal structure
    if 'MODID' in fields and 'VERSION' in fields:
        return fields['MODID'][2], fields['VERSION'][2]
    elif 'MOD_ID' in fields and 'VERSION' in fields:
        return fields['MOD_ID'][2], fields['VERSION'][2]
    methods_count, = struct.unpack('>H', data[idx:idx + 2])
    idx = skip_fields(data, idx + 2, methods_count)
    attrs_count, = struct.unpack('>H', data[idx:idx + 2])
    idx, _, annos = parse_attrs(data, idx + 2, constant_pool, attrs_count, care_about_annos=True)
    # TODO iterate through annos and find @Mod
    for name, params in annos:
        if name.endswith('fml/common/Mod;'):
            return params['modid'], params.get('version')
    return None



def parse_class(data, fn, verbose=False):
    idx = HDR_STRUCT_1.size
    magic, major_ver, minor_ver, constant_pool_count = HDR_STRUCT_1.unpack(data[:idx])
    assert magic == 0xCAFEBABE
    # Look, idk why we have to decrement constant_pool_count.  It's in the jvm spec.  We just do
    constant_pool, idx = _parse_constant_pool(data, idx, constant_pool_count - 1)
    next_idx = idx + HDR_STRUCT_2.size
    access_flags, this_class, super_class, interfaces_count = HDR_STRUCT_2.unpack(data[idx:next_idx])
    assert 0 < this_class < constant_pool_count
    assert 0 <= super_class < constant_pool_count, (super_class, constant_pool_count)
    # each interface is a 2 byte index into the constant pool.
    # We don't care about interfaces thoguh so just skip over them.
    idx = next_idx + 2 * interfaces_count
    fields_count, = struct.unpack('>H', data[idx:idx + 2])
    if verbose:
        print(fn)
    fields, idx = parse_fields(data, idx + 2, constant_pool, fields_count, verbose=verbose)
    # same method that parses fields can parse methods since they use the same internal structure
    methods_count, = struct.unpack('>H', data[idx:idx + 2])
    if verbose:
        print(fn)
    methods, idx = parse_fields(data, idx + 2, constant_pool, methods_count, verbose=verbose)
    attrs_count, = struct.unpack('>H', data[idx:idx + 2])
    if verbose:
        print(fn)
    idx, _, annos = parse_attrs(data, idx + 2, constant_pool, attrs_count, care_about_annos=True, verbose=verbose)
    if idx != len(data):
        print(fn, '!!! MISMATCH !!!', idx, len(data))
    return fields, methods, annos


def main():
    import time

    times = []
    mods = {}
    start = time.perf_counter()
    import pathlib

    # p=pathlib.Path('/tank/srv/mc/sfe_full_send/backups/model/mods')
    p = pathlib.Path('/srv/mc/eternal37/mods')
    #p = pathlib.Path("~/mods").expanduser()
    for zfp in p.glob('*.jar'):
        t1 = time.perf_counter()
        try:
            mods[zfp] = get_info(zfp)
        except:
            import traceback
            import sys

            sys.stderr.write('Error parsing %s\n' % zfp.name)
            traceback.print_exc()
        t2 = time.perf_counter()
        times.append(t2 - t1)
    end = time.perf_counter()
    print('Processed', len(mods), 'mods in', end - start, 'seconds')
    print(f'Total time: {sum(times)}, Average time: {sum(times) / len(times)}, Longest time: {max(times)}, Total files: {len(times)}')
    print(sum(100 for x in mods.values() if len(x) > 1) / len(mods), '% had more than one mod')
    # matches=0
    # for mod, info in mods.items():
    #     field_modid, field_version = field_mods.get(mod, (None, None))
    #     if 'version' not in info and field_version:
    #         matches += 1
    #         print('Only the fields had a version for', field_modid, info['modid'])
    #         continue
    #     if info['modid']==field_modid and info['version']==field_version:
    #         matches += 1
    #     else:
    #         print('No match:', info['modid'], field_modid, info.get('version'), field_version)
    # print(matches*100/len(mods), '% matched')
    # import pdb
    # pdb.post_mortem(e.__traceback__)
    # parse_class(zf.read('de/ellpeck/actuallyadditions/mod/blocks/base/BlockContainerBase.class'))


    import pprint
    pprint.pprint(mods)

    for file, annos in mods.items():
        if not annos:
            print(file.name, annos)
            with zipfile.ZipFile(file) as zf:
                for f in zf.infolist():
                    if f.filename.endswith('.class'):
                        import pdb
                        #pdb.runcall(parse_class, zf.read(f), f.filename, verbose=True)
                        parse_class(zf.read(f), f.filename, verbose=True)


def get_info(zfp):
    mods = []
    import zipfile
    with zipfile.ZipFile(zfp) as zf:
        for file in zf.namelist():
            if file.endswith('.class'):# and '$' not in file and 'api' not in file:
                # fields, methods, annos = parse_class(zf.read(file), file)
                # # if 'MODID' in fields and 'VERSION' in fields:
                # #     field_mods[zfp.name] = (fields['MODID'][2], fields['VERSION'][2])
                # for type_, params in annos:
                #     # print(zfp.name, type_)
                #     if type_.endswith('fml/common/Mod;'):
                #         mods.append(params)
                #         break
                #     elif type_.endswith('fml/common/NetworkMod;'):
                #         print('NetworkMod', params)
                #     # elif 'Mod' in type_:
                #     #     print(type_)
                # #         break
                # # else:
                # #     continue
                # # break
                inf = parse_class_targeted(zf.read(file))
                if inf:
                    mods.append(inf)
    return mods


if __name__ == '__main__':
    main()
