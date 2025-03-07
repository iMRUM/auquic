"""
@file packet.py
@brief Implementation of QUIC packet data structures.
@details Contains classes for QUIC packet headers and packet assembly,
         with methods for encoding and decoding packets.
"""

from dataclasses import dataclass, field

from constants import Constants
from frame import FrameStream


@dataclass
class PacketHeader:
    """
    @brief Represents the header of a QUIC packet.

    @details Contains fields specified in QUIC protocol for packet headers.
    """

    packet_number_length: int  # !< The length of the packet number field in bytes (2 bits)
    header_form: bool = False  # !< The header form bit (1 bit)
    fixed_bit: bool = False  # !< The fixed bit (1 bit)
    spin_bit: bool = False  # !< The spin bit (1 bit)
    key_phase: bool = False  # !< The key phase bit (1 bit)
    reserved_bits: int = Constants.ZERO  # !< The reserved bits (2 bits)

    def pack(self) -> bytes:
        """
        @brief Packs the PacketHeader into bytes.

        @details Shifts and combines the header attributes into a single byte.

        @return The packed header as bytes.
        """
        first_byte = (
                (int(self.header_form) << Constants.FORM_SHIFT) |
                (int(self.fixed_bit) << Constants.FIXED_SHIFT) |
                (int(self.spin_bit) << Constants.SPIN_SHIFT) |
                (self.reserved_bits << Constants.RES_SHIFT) |
                (int(self.key_phase) << Constants.KEY_SHIFT) |
                self.packet_number_length
        )
        return first_byte.to_bytes(Constants.HEADER_LENGTH, 'big')

    @classmethod
    def unpack(cls, header: bytes) -> 'PacketHeader':
        """
        @brief Unpacks bytes into a PacketHeader.

        @details Extracts each field from the header byte using bitwise operations.

        @param header The packed header as bytes.
        @return The unpacked PacketHeader object.
        """
        header_form = int.from_bytes(header, "big") & Constants.FORM_MASK  # 1 bit
        fixed_bit = int.from_bytes(header, "big") & Constants.FIXED_MASK  # 1 bit
        spin_bit = int.from_bytes(header, "big") & Constants.SPIN_MASK  # 1 bit
        reserved_bits = int.from_bytes(header, "big") & Constants.RES_MASK  # 2 bits
        key_phase = int.from_bytes(header, "big") & Constants.KEY_MASK  # 1 bit
        packet_number_length = int.from_bytes(header, 'big') & Constants.PACKET_NUMBER_LENGTH_MASK
        return PacketHeader(header_form=bool(header_form), fixed_bit=bool(fixed_bit), spin_bit=bool(spin_bit),
                            reserved_bits=reserved_bits, key_phase=bool(key_phase),
                            packet_number_length=packet_number_length)


@dataclass
class Packet:
    """
    @brief Represents a QUIC packet.

    @details Contains a destination connection ID, packet number, 
             and payload as list of frames.
    """

    destination_connection_id: int  # !< The destination connection ID (8 bytes in this implementation)
    packet_number: int  # !< The packet number (4 bytes in this implementation)
    payload: list[FrameStream] = field(default_factory=list)  # !< The payload containing a list of FrameStream objects

    def pack(self) -> bytes:
        """
        @brief Packs the packet into bytes.

        @details The process includes:
                - Packing the header.
                - Converting the destination connection ID to bytes.
                - Converting the packet number to bytes based on its length.
                - Encoding each frame in the payload and appending it to the packed packet.

        @return The packed packet as bytes.
        """
        packet_number_length = (self.packet_number.bit_length() + Constants.SEVEN) // Constants.EIGHT
        packed_header = PacketHeader(packet_number_length).pack()
        dest_connection_id_bytes = self.destination_connection_id.to_bytes(Constants.DEST_CONNECTION_ID_LENGTH, 'big')
        packet_number_bytes = self.packet_number.to_bytes(packet_number_length, 'big')
        packed_packet: bytes = packed_header + dest_connection_id_bytes + packet_number_bytes
        for frame in self.payload:
            packed_packet += frame.encode()
        return packed_packet

    @classmethod
    def unpack(cls, packet_bytes: bytes) -> 'Packet':
        """
        @brief Unpacks bytes into a Packet object.

        @details The process includes:
                - Unpacking the header to get the packet number length.
                - Extracting the destination connection ID from the bytes.
                - Extracting the packet number from the bytes.
                - Extracting the payload frames from the remaining bytes.

        @param packet_bytes The packed packet as bytes.
        @return The unpacked Packet object.
        """
        packet_number_length = PacketHeader.unpack(packet_bytes[:Constants.HEADER_LENGTH]).packet_number_length
        index = Constants.HEADER_LENGTH
        destination_connection_id = int.from_bytes(packet_bytes[index:index + Constants.DEST_CONNECTION_ID_LENGTH],
                                                   'big')
        index += Constants.DEST_CONNECTION_ID_LENGTH
        packet_number = int.from_bytes(packet_bytes[index:index + Constants.PACKET_NUMBER_LENGTH], 'big')
        index += packet_number_length
        payload_frames = Packet.get_frames_from_payload_bytes(packet_bytes[index:])
        return Packet(
            destination_connection_id=destination_connection_id,
            packet_number=packet_number,
            payload=payload_frames
        )

    @staticmethod
    def get_frames_from_payload_bytes(payload_bytes: bytes) -> list[FrameStream]:
        """
        @brief Extracts frames from the payload bytes.

        @details The process includes:
                - Iterating through the payload bytes.
                - Determining the end of attributes for each frame.
                - Determining the length of the frame data.
                - Decoding each frame and appending it to the list of frames.

        @param payload_bytes The payload bytes.
        @return The list of decoded FrameStream objects.
        """
        index = Constants.START
        frames: list[FrameStream] = []
        while index < len(payload_bytes):
            end_of_attrs = FrameStream.end_of_attrs(payload_bytes[index:index + Constants.FRAME_TYPE_FIELD_LENGTH])
            length_of_frame_data = FrameStream.length_from_attrs(payload_bytes[index:index + end_of_attrs],
                                                                 end_of_attrs)
            frames.append(FrameStream.decode(payload_bytes[index:index + end_of_attrs + length_of_frame_data]))
            index += end_of_attrs + length_of_frame_data
        return frames

    def add_frame(self, frame: 'FrameStream'):
        """
        @brief Adds a frame to the packet's payload.

        @param frame The frame to be added.
        """
        self.payload.append(frame)