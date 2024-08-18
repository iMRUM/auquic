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
class _StreamFrame(_Frame, ABC):
    stream_id: int


@dataclass
class FrameStream(_StreamFrame):
    type = TYPE_FIELD
    offset: int  # "The largest offset delivered on a stream -- the sum of the offset and data length -- cannot exceed
    # 2^62-1" (RFC),so we will use 8-byte
    length: int  # same as offset
    fin: bool
    data: bytes

    def encode(self) -> bytes:  #DONE: adjust to type from inheritacne(_type to self.type)
        values = []
        if self.offset != 0:
            self.type = self.type | OFF_BIT
            values.append(self.offset)
        if self.length != 0:
            self.type = self.type | LEN_BIT
            values.append(self.length)
        if self.fin:
            self.type = self.type | FIN_BIT
        values_len = len(values)
        struct_format = f'!BB{values_len}Q'
        # struct format is
        # |00001XXX-1-byte-type|1-byte-StreamID|Optional-8-byte-Offset|Optional-8-byte-Length|Payload(data)
        return struct.pack(struct_format, self.type, self.stream_id, values) + self.data

    def get_stream_frame(self):
        return self.encode()

    @classmethod
    def decode(cls, frame: bytes):
        # Unpack the first 2 bytes (type and stream_id)
        _type, stream_id = struct.unpack('!BB', frame[:2])

        offset = 0
        length = 0
        fin = False

        # Set the index after the initial fixed fields
        index = 2

        # Check if the offset is present
        if _type & OFF_BIT:
            offset, = struct.unpack('!Q', frame[index:index + 8])
            index += 8

        # Check if the length is present
        if _type & LEN_BIT:
            length, = struct.unpack('!Q', frame[index:index + 8])
            index += 8

        # Check if the FIN bit is set
        if _type & FIN_BIT:
            fin = True

        # The rest is data
        data, = frame[index:]
        # Create and return the object with the decoded values
        return cls(stream_id=stream_id, offset=offset, length=length, fin=fin, data=data)


@dataclass
class FrameReset_Stream(_StreamFrame):
    application_protocol_error_code: int
    final_size: int
    type = 0x04

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameStop_Sending(_StreamFrame):
    application_protocol_error_code: int
    type = 0x05

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameMax_Stream_Data(_StreamFrame):
    maximum_stream_data: int
    type = 0x11

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass


@dataclass
class FrameStream_Data_Blocked(_StreamFrame):
    maximum_stream_data: int
    type = 0x15

    def encode(self) -> bytes:
        pass

    @classmethod
    def decode(cls, frame: bytes):
        pass
