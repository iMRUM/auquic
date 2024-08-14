import struct
from typing import Optional

TYPE_FIELD_STREAM = 0x08
OFF_BIT = 0x04
LEN_BIT = 0x02
FIN_BIT = 0x01


def get_stream_frame(stream_id: int, data, offset=0, length=0, is_fin=False):
    stream_type = TYPE_FIELD_STREAM
    values = [stream_id]
    if offset != 0:
        stream_type = stream_type | OFF_BIT
        values.append(offset)
    if length != 0:
        stream_type = stream_type | LEN_BIT
        values.append(length)
    if is_fin:
        stream_type = stream_type | FIN_BIT
    values.insert(0, stream_type)
    values.append(data)
    values_len = len(values) - 1
    struct_format = f'>{values_len}I{8 - values_len}s'
    # struct format is
    # |00001XXX-4-byte-type|4-byte-StreamI|Optional-4-byte-Offset|Optional-4-byte-Length|Payload(data)
    return struct.pack(struct_format, values)
