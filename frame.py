from abc import ABC, abstractmethod
from dataclasses import dataclass

TYPE_FIELD = 0x08
OFF_BIT = 0x04
LEN_BIT = 0x02
FIN_BIT = 0x01


@dataclass
class StreamFrameABC(ABC):
    stream_id: int

    @abstractmethod
    def encode(self) -> bytes:
        pass

    @classmethod
    @abstractmethod
    def decode(cls, frame: bytes):
        pass


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
        offset, length, fin, stream_id, index, stream_data = FrameStream._decode(frame)
        return FrameStream(stream_id=stream_id, offset=offset, length=length, fin=fin, data=stream_data)

    @classmethod
    def _decode(cls, frame: bytes):
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
        return offset, length, fin, stream_id, index, frame[index:]

    @staticmethod
    def end_of_attrs(frame: bytes) -> int:
        end_of_data = 9
        type_field = int.from_bytes(frame[0:1], 'big')
        if type_field & OFF_BIT:
            end_of_data += 8
        if type_field & LEN_BIT:
            end_of_data += 8
        return end_of_data

    @staticmethod
    def length_from_attrs(frame: bytes, end_of_attrs: int):
        if end_of_attrs <= 9:
            return 0
        if end_of_attrs <= 17:
            return int.from_bytes(frame[9:17], "big")
        return int.from_bytes(frame[17:25], "big")
