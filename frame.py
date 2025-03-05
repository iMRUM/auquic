"""
@file frame.py
@brief Implementation of QUIC stream frame handling.
@details Contains abstract and concrete classes for QUIC stream frames,
         with methods for encoding and decoding them.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from constants import Constants


@dataclass
class StreamFrameABC(ABC):
    """
    @brief Abstract base class for stream frames.

    @details Defines the interface for stream frame classes.
    """

    stream_id: int  # !< Unique identifier for the stream

    @abstractmethod
    def encode(self) -> bytes:
        """
        @brief Encode the frame into bytes.

        @return The encoded frame as bytes.
        """
        pass

    @classmethod
    @abstractmethod
    def decode(cls, frame: bytes):
        """
        @brief Decode bytes into a frame object.

        @param frame The encoded frame as bytes.
        @return A new frame instance with the decoded values.
        """
        pass


@dataclass
class FrameStream(StreamFrameABC):
    """
    @brief Concrete implementation of a QUIC stream frame.

    @details Contains data for a single frame within a stream,
             with methods to encode and decode the frame.
    """

    offset: int  # !< The offset of this frame in the stream
    length: int  # !< The length of the data in this frame
    fin: bool  # !< Flag indicating if this is the final frame
    data: bytes  # !< The payload data of this frame

    def encode(self) -> bytes:
        """
        @brief Encodes the frame into bytes.

        @details The encoding process includes:
                - Converting the stream ID to bytes.
                - Setting the type field based on the presence of offset, length, and fin attributes.
                - Appending the offset, length, and data to the values list if they are present.
                - Combining all parts into a single bytes object.

        @return The encoded frame as bytes.
        """
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
        """
        @brief Decodes a frame encoded in bytes into a FrameStream instance.

        @details Delegates to _decode for the actual decoding.

        @param frame The encoded frame as bytes.
        @return A new FrameStream instance with the decoded values.
        """
        return FrameStream._decode(frame)

    @classmethod
    def _decode(cls, frame: bytes):
        """
        @brief Decodes a frame encoded in bytes into a FrameStream instance.

        @details The decoding process includes:
                - Extracting the offset, length, fin flag, stream ID, and stream data from the frame.
                - Creating a new FrameStream instance with the extracted values.

        @param frame The encoded frame as bytes.
        @return A new FrameStream instance with the decoded values.
        """
        offset = Constants.ZERO
        length = Constants.ZERO
        fin = False
        type_field = int.from_bytes(frame[:Constants.FRAME_TYPE_FIELD_LENGTH], 'big')
        index = Constants.FRAME_TYPE_FIELD_LENGTH
        stream_id = int.from_bytes(frame[index:index + Constants.STREAM_ID_LENGTH], 'big')
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

        return FrameStream(stream_id=stream_id, offset=offset, length=length, fin=fin, data=frame[index:])

    @staticmethod
    def end_of_attrs(frame: bytes) -> int:
        """
        @brief Determines the end position of the attributes in the frame.

        @details The process includes:
                - Calculating the initial end position based on the frame type field length and stream ID length.
                - Checking if the offset bit is set in the type field and adjusting the end position accordingly.
                - Checking if the length bit is set in the type field and adjusting the end position accordingly.

        @param frame The encoded frame as bytes.
        @return The end position of the attributes in the frame.
        """
        end_of_data = Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH
        type_field = int.from_bytes(frame[:Constants.FRAME_TYPE_FIELD_LENGTH], 'big')
        if type_field & Constants.OFF_BIT:
            end_of_data += Constants.OFFSET_LENGTH
        if type_field & Constants.LEN_BIT:
            end_of_data += Constants.LEN_LENGTH
        return end_of_data

    @staticmethod
    def length_from_attrs(frame: bytes, end_of_attrs: int):
        """
        @brief Determines the length of the data in the frame.

        @details The process includes:
                - Checking if the end of attributes is less than or equal to the sum of the frame type 
                  field length and stream ID length.
                - If the end of attributes is less than or equal to the sum of the frame type field 
                  length and stream ID length plus the offset length.
                - Otherwise, the length is extracted from the frame after the offset length.

        @param frame The encoded frame as bytes.
        @param end_of_attrs The end position of the attributes in the frame.
        @return The length of the data in the frame.
        """
        if end_of_attrs <= Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH:
            return Constants.ZERO
        index = Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH
        if end_of_attrs <= index + Constants.OFFSET_LENGTH:  # offset is not present, len "took" its room
            return int.from_bytes(frame[index:index + Constants.LEN_LENGTH], "big")
        index += Constants.OFFSET_LENGTH
        return int.from_bytes(frame[index:index + Constants.LEN_LENGTH], "big")