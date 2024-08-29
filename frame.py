from abc import ABC, abstractmethod
from dataclasses import dataclass

from constants import Constants


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
        values = [self.stream_id.to_bytes(Constants.STREAM_ID_LENGTH, 'big')]
        type_field = Constants.MIN_TYPE_FIELD
        if self.offset != 0:
            type_field = type_field | Constants.OFF_BIT
            values.append(self.offset.to_bytes(Constants.OFFSET_LENGTH, 'big'))
        if self.length != 0:
            type_field = type_field | Constants.LEN_BIT
            values.append(self.length.to_bytes(Constants.LEN_LENGTH, 'big'))
        if self.fin:
            type_field = type_field | Constants.FIN_BIT
        values.append(self.data)
        encoded_frame = type_field.to_bytes(Constants.FRAME_TYPE_FIELD_LENGTH, 'big')  # type is byte[0]
        for v in values:
            encoded_frame += v
        return encoded_frame

    @classmethod
    def decode(cls, frame: bytes):
        offset, length, fin, stream_id, index, stream_data = FrameStream._decode(frame)
        return FrameStream(stream_id=stream_id, offset=offset, length=length, fin=fin, data=stream_data)

    @classmethod
    def _decode(cls, frame: bytes):
        offset = Constants.ZERO
        length = Constants.ZERO
        fin = False
        type_field = int.from_bytes(frame[:Constants.FRAME_TYPE_FIELD_LENGTH], 'big')
        index = Constants.FRAME_TYPE_FIELD_LENGTH
        stream_id = int.from_bytes(frame[index:index+Constants.STREAM_ID_LENGTH], 'big')
        index += Constants.STREAM_ID_LENGTH
        if type_field & Constants.OFF_BIT:
            offset = int.from_bytes(frame[index:index + Constants.OFFSET_LENGTH], 'big')
            index += Constants.OFFSET_LENGTH

        # Check if the length is present
        if type_field & Constants.LEN_BIT:
            length = int.from_bytes(frame[index:index + Constants.LEN_LENGTH], 'big')
            index += Constants.LEN_LENGTH

        # Check if the FIN bit is set
        if type_field & Constants.FIN_BIT:
            fin = True
        return offset, length, fin, stream_id, index, frame[index:]

    @staticmethod
    def end_of_attrs(frame: bytes) -> int:
        end_of_data = Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH
        type_field = int.from_bytes(frame[:Constants.FRAME_TYPE_FIELD_LENGTH], 'big')
        if type_field & Constants.OFF_BIT:
            end_of_data += Constants.OFFSET_LENGTH
        if type_field & Constants.LEN_BIT:
            end_of_data += Constants.LEN_LENGTH
        return end_of_data

    @staticmethod
    def length_from_attrs(frame: bytes, end_of_attrs: int):
        if end_of_attrs <= Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH:
            return Constants.ZERO
        index = Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH
        if end_of_attrs <= index + Constants.OFFSET_LENGTH:  # offset is not present, len "took" its room
            return int.from_bytes(frame[index:index + Constants.LEN_LENGTH], "big")
        index += Constants.OFFSET_LENGTH
        return int.from_bytes(frame[index:index + Constants.LEN_LENGTH], "big")
