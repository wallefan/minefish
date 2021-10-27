import socket
import pprint
import json

STATUS = 1
LOGIN = 2


def encode_varint(i):
    if i==0: return b'\x00'
    b=[]
    while i:
        b.append((i & 0x7f) | 0x80)
        i >>= 7
    b[-1] &= 0x7f
    return bytes(b)

def decode_varint(b):
    result=0
    for i, c in enumerate(b):
        result |= ((c & 0x7f) << (i*7))
        if not (c & 0x80):
            return result, b[i+1:]
    raise ValueError('unterminated varint: '+' '.join(map(hex, b)))


def encode_string(s):
    b=s.encode('utf8')
    return encode_varint(len(b))+b


def encode_packet_uncompressed(packet_id, packet):
    # For SOME reason, the length field of packets going TO the server does NOT include the length of the packet ID,
    # but the length field of packets coming FROM the server does
    return encode_varint(len(packet))+encode_varint(packet_id)+packet


NEGATIVE_ONE = 4294967295


def receive_packet_uncompressed(sock):
    sock.settimeout(5)
    data = sock.recv(16)
    packet_length, data = decode_varint(data)
    packet_id, _ = decode_varint(data)
    bytes_received = len(data)
    buf = memoryview(bytearray(packet_length))
    buf[:bytes_received] = data
    while bytes_received < packet_length:
        try:
            bytes_received += sock.recv_into(buf[bytes_received:])
        except socket.timeout:
            raise ValueError(f'Received packet was {packet_length-bytes_received} bytes too short')
    return packet_id, bytes(buf[1:])


def handshake(host, port=25565, next_action = LOGIN):
    s = socket.create_connection((host, port))

    # Anatomy of a handshake packet (Python won't let me put my comments mid-line):
    # NEGATIVE_ONE = the protocol version.  -1 should be used if we are pinging to determine
    # what protocol version to use, which we are.  The constant NEGATIVE_ONE defined at the top of the file
    # in fact has a value of 2^32-1, which is because the Minecraft server, being written in Java,
    # rather naively treats varints as 32-bit signed integers.  Python, on the other hand, as you know,
    # treats integers as infinitely wide, so
    # Anways, moving on.
    # Second filed is the hostname.  Forge servers will immediately drop the connection unless you tack
    # '\x00FML\x00' onto the hostname -- vanilla servers ignore it.
    # (It stands for Forge Mod Loader although I think we all know it really stands
    # for someting else -- really?  straight up the connection after ONE protocol violation?  Not even an error
    # message!?)
    # Last two fields are self explanatory.

    handshake_packet = (
        encode_varint(NEGATIVE_ONE) +    # protocol version (-1 to query server what version to use)
        encode_string(host+'\0FML\0') +  # host field; forge servers will instant kick you unless you put
                                         # \0FML\0 on the end; vanilla servers don't care.
        encode_varint(port) +            # port
        encode_varint(next_action)       # 1 for status, 2 for login.
    )

    # packet ID 0 = handshake
    s.sendall(encode_packet_uncompressed(0, handshake_packet))
    return s


def server_list_ping(host, port=25565):
    s = handshake(host, port, STATUS)
    s.sendall(encode_packet_uncompressed(0, b''))  # packet ID 0 in Status state = server info.
    response_packetid, response = receive_packet_uncompressed(s)
    assert response_packetid == 0, f'Server responded with packet ID %d' % response_packetid
    length_of_json, response = decode_varint(response)
    assert length_of_json == len(response)
    respj = json.loads(response.decode('utf8'))
    pprint.pprint(respj)
    if 'forgeData' in respj:
        print('1.13 or later')
        mods={m['modId']: m['modmarker'] for m in respj['forgeData']['mods']}
    elif 'modinfo' in respj:
        print('1.12.2 or earlier')
        print('modloader:', respj['modinfo']['type'])
        mods = {m['modid']: m['version'] for m in respj['modinfo']['modList']}
    else:
        print('Vanilla', respj['version']['name'])
        mods=None

    return respj['version']['name'], mods

