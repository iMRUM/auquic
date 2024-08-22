from dataclasses import dataclass, field
from typing import Optional
import struct
from _frame import FrameStream, StreamFrameABC
from sys import getsizeof

PACKET_NUMBER_LENGTH = 0x03
FORM = 0b10000000
FIXED = 0b01000000
SPIN = 0b00100000
RES = 0b00011000
KEY = 0b00000100
ONE = 0x01
TWO = 0x03
# consts for payload handling:
TYPE_FIELD = 0x08
OFF_BIT = 0x04
LEN_BIT = 0x02
FIN_BIT = 0x01


@dataclass
class PacketHeader:  # total 1 byte
    packet_number_length: int
    header_form: int = 0  # 1 bit
    fixed_bit: int = 0  # 1 bit
    spin_bit: int = 0  # 1 bit
    reserved_bits: int = 2  # 2 bits
    key_phase: int = 0  # 1 bit

    # 2 bits, one less than the length of the Packet Number field in bytes

    def pack(self) -> bytes:
        first_byte = (
                (self.header_form << 7) |
                (self.fixed_bit << 6) |
                (self.spin_bit << 5) |
                (self.reserved_bits << 3) |
                (self.key_phase << 2) |
                self.packet_number_length
        )
        return first_byte.to_bytes(1, 'big')

    @classmethod
    def unpack(cls, header: bytes) -> 'PacketHeader':
        # total 1 byte
        header_form = int.from_bytes(header, "big") >> 7 & ONE  # 1 bit
        fixed_bit = int.from_bytes(header, "big") >> 6 & ONE  # 1 bit
        spin_bit = int.from_bytes(header, "big") >> 5 & ONE  # 1 bit
        reserved_bits = int.from_bytes(header, "big") >> 3 & TWO  # 2 bits
        key_phase = int.from_bytes(header, "big") >> 2 & ONE  # 1 bit
        packet_number_length = int.from_bytes(header,
                                              'big') & PACKET_NUMBER_LENGTH  # 2 bits, one less than the length of
        # the Packet Number field in bytes
        return PacketHeader(header_form=header_form, fixed_bit=fixed_bit, spin_bit=spin_bit,
                            reserved_bits=reserved_bits, key_phase=key_phase, packet_number_length=packet_number_length)


@dataclass
class Packet:
    destination_connection_id: int  # Variable length (let's assume 8 bytes in this example)
    packet_number: int  # Variable length
    # payload: bytes = b''  # Payload (variable length)
    payload: list[FrameStream] = field(default_factory=list)

    def pack(self) -> bytes:
        # Pack the header
        packed_header = PacketHeader(getsizeof(self.packet_number) - 1).pack()
        # Assume Destination Connection ID is 8 bytes(according to RFC it's 0-20bytes)
        dest_connection_id_bytes = self.destination_connection_id.to_bytes(8, 'big')
        # Pack the Packet Number based on its length field+1
        packet_number_bytes = self.packet_number.to_bytes(getsizeof(self.packet_number), 'big')
        packed_packet: bytes = packed_header + dest_connection_id_bytes + packet_number_bytes
        for frame in self.payload:
            packed_packet += frame.encode()
        return packed_packet

    @classmethod
    def unpack(cls, packet_bytes: bytes) -> 'Packet':
        print(':L79: unpacking')
        # ignore the header
        packet_number_length = PacketHeader.unpack(packet_bytes[0:1]).packet_number_length
        print(f'Packet Number Length: {packet_number_length}')
        destination_connection_id = int.from_bytes(packet_bytes[1:9], 'big')
        print(f'Destination Connection ID: {destination_connection_id}')
        packet_number = int.from_bytes(packet_bytes[9:9 + packet_number_length + 1], 'big')
        print(f'Packet Number: {packet_number}')
        payload_frames = Packet.get_frames_from_payload_bytes(packet_bytes[9 + packet_number_length + 1:])
        print(f'{payload_frames}')
        print(f'Expected Payload Start: {9 + packet_number_length + 1}')
        return Packet(
            destination_connection_id=destination_connection_id,
            packet_number=packet_number,
            payload=payload_frames
        )

    @staticmethod
    def get_frames_from_payload_bytes(payload_bytes: bytes) -> list[FrameStream]:
        print(f'payload_bytes: {payload_bytes}')
        index = 0
        frames: list[FrameStream] = []
        while index < len(payload_bytes):
            # print(f'index is {index}') maybe cast type to int????
            length_to_add = FrameStream.end_of_data_index(payload_bytes[index:index + 1])
            frames.append(FrameStream.decode(payload_bytes[index:index+length_to_add]))
            index += length_to_add
        return frames

    @staticmethod
    def stream_frame_min_length_by_type(type_frame: bytes) -> int:
        type_int = int.from_bytes(type_frame, 'big')
        length = 9
        if type_int & OFF_BIT:
            length += 8
        # Check if the length is present
        if type_int & LEN_BIT:
            length += 8
        return length

    def add_frame(self, frame: 'FrameStream'):
        """
        Add a frame to the packet.
        while index < len(self.payload):
            frame_total_length = 9  # in bytes
            first_byte_int = int.from_bytes(self.payload[0:1], 'big')  # type of first frame
            second_byte_int = int.from_bytes(self.payload[1:9], 'big')  # stream_id of first frame
            if first_byte_int & OFF_BIT:  # off bit is 1 [9:17]
                frame_total_length += 8
            if first_byte_int & LEN_BIT:  # len bit is 1 [17:25]
                frame_total_length += 8 + int.from_bytes(self.payload[17:25])
        Args:
            frame (bytes): The frame to be added as bytes.
        """
        self.payload.append(frame)
