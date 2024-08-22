import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass

TYPE_FIELD = 0x08
OFF_BIT = 0x04
LEN_BIT = 0x02
FIN_BIT = 0x01


@dataclass
class _Frame(ABC):
    type: int

    @abstractmethod
    def encode(self) -> bytes:
        pass

    @classmethod
    @abstractmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameMax_Data(_Frame):
    maximum_data: int
    type = 0x10

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameMax_Streams(_Frame):  # Type (i) = 0x12..0x13 (from RFC-9000)
    maximum_streams: int

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class StreamFrameABC(ABC):
    stream_id: int


@dataclass
class FrameStream(StreamFrameABC):
    offset: int  # "The largest offset delivered on a stream -- the sum of the offset and data length -- cannot exceed
    # 2^62-1" (RFC),so we will use 8-byte
    length: int  # same as offset
    fin: bool
    data: bytes

    def encode(self) -> bytes:
        values = [self.stream_id.to_bytes(8, 'big')]
        type_field = TYPE_FIELD
        if self.offset != 0:
            type_field = type_field | OFF_BIT
            values.append(self.offset.to_bytes(8, 'big'))
        if self.length != 0:
            type_field = type_field | LEN_BIT
            values.append(self.length.to_bytes(8, 'big'))
        if self.fin:
            type_field = type_field | FIN_BIT
        values.append(self.data)
        encoded_frame = type_field.to_bytes(1, 'big')  # type is byte[0]
        for v in values:
            encoded_frame += v
        return encoded_frame

    @classmethod
    def decode(cls, frame: bytes):
        offset, length, fin, stream_id, index = FrameStream.decode_first_part(frame)
        stream_data = frame[index:]
        return FrameStream(stream_id=stream_id, offset=offset, length=length, fin=fin, data=stream_data)

    @classmethod
    def decode_first_part(cls, frame: bytes):
        offset = 0
        length = 0
        fin = False
        type_field = int.from_bytes(frame[0:1], 'big')
        stream_id = int.from_bytes(frame[1:9], 'big')
        index = 9
        if type_field & OFF_BIT:
            offset = int.from_bytes(frame[index:index + 8], 'big')
            index += 8

        # Check if the length is present
        if type_field & LEN_BIT:
            length = int.from_bytes(frame[index:index + 8], 'big')
            index += 8

        # Check if the FIN bit is set
        if type_field & FIN_BIT:
            fin = True
        return offset, length, fin, stream_id, index


@dataclass
class FrameReset_Stream(StreamFrameABC):
    application_protocol_error_code: int
    final_size: int
    type = 0x04

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameStop_Sending(StreamFrameABC):
    application_protocol_error_code: int
    type = 0x05

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameMax_Stream_Data(StreamFrameABC):
    maximum_stream_data: int
    type = 0x11

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameStream_Data_Blocked(StreamFrameABC):
    maximum_stream_data: int
    type = 0x15

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass
