from typing import Optional


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


class STREAM:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-stream-frames
    def __init__(self, stream_id: int, data, offset=0, length=0, is_off=False, is_len=False, is_fin=False,
                 type=0b00001):
        if (is_off):
            type = type + 0x04
        if (is_len):
            type = type + 0x02
        if (is_fin):
            type = type + 0x01
        _type_byte_representation = type.to_bytes(1, byteorder='big')
        _stream_id_byte_representation = stream_id.to_bytes(8, byteorder='big')
        _offset_byte_representation = offset.to_bytes(1, byteorder='big')
        _length_byte_representation = length.to_bytes(1, byteorder='big')
        self._frame_bytearray_representation = bytearray()
        self._frame_bytearray_representation += _type_byte_representation
        self._frame_bytearray_representation += _stream_id_byte_representation
        self._frame_bytearray_representation += _error_code_byte_representation
        self._frame = ''.join(format(byte, '08b') for byte in self._frame_bytearray_representation)

    @property
    def frame(self):
        return self._frame
