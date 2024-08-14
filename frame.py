import struct
from typing import Optional

TYPE_FIELD_STREAM = 0x08
OFF_BIT = 0x04
LEN_BIT = 0x02
FIN_BIT = 0x01


class RESET_STREAM:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-reset_stream-frames
    def __init__(self, stream_id: int, error_code: int, final_size: int, type=0x04):
        _type_byte_representation = type.to_bytes(1, byteorder='big')
        _stream_id_byte_representation = stream_id.to_bytes(8, byteorder='big')
        _error_code_byte_representation = error_code.to_bytes(1, byteorder='big')
        _final_size_byte_representation = final_size.to_bytes(8, byteorder='big')
        self._frame_bytearray_representation = bytearray()
        self._frame_bytearray_representation += _type_byte_representation
        self._frame_bytearray_representation += _stream_id_byte_representation
        self._frame_bytearray_representation += _error_code_byte_representation
        self._frame_bytearray_representation += _final_size_byte_representation
        self._frame = ''.join(format(byte, '08b') for byte in self._frame_bytearray_representation)

    @property
    def frame(self):
        return self._frame


class STOP_SENDING:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-stop_sending-frames
    def __init__(self, stream_id: int, error_code: int, type=0x05):
        _type_byte_representation = type.to_bytes(1, byteorder='big')
        _stream_id_byte_representation = stream_id.to_bytes(8, byteorder='big')
        _error_code_byte_representation = error_code.to_bytes(1, byteorder='big')
        self._frame_bytearray_representation = bytearray()
        self._frame_bytearray_representation += _type_byte_representation
        self._frame_bytearray_representation += _stream_id_byte_representation
        self._frame_bytearray_representation += _error_code_byte_representation
        self._frame = ''.join(format(byte, '08b') for byte in self._frame_bytearray_representation)

    @property
    def frame(self):
        return self._frame


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
