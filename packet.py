from dataclasses import dataclass
from typing import Optional
import struct
from _frame import FrameStream

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
                                              'big') & PACKET_NUMBER_LENGTH  # 2 bits, one less than the length of the Packet Number field in bytes
        return PacketHeader(header_form=header_form, fixed_bit=fixed_bit, spin_bit=spin_bit,
                            reserved_bits=reserved_bits, key_phase=key_phase, packet_number_length=packet_number_length)


@dataclass
class Packet:
    header: PacketHeader
    destination_connection_id: int  # Variable length (let's assume 8 bytes in this example)
    packet_number: int  # Variable length
    payload: bytes  # Payload (variable length)

    def pack(self) -> bytes:
        # Pack the header
        packed_header = self.header.pack()
        # Assume Destination Connection ID is 8 bytes(according to RFC it's 0-20bytes)
        dest_connection_id_bytes = self.destination_connection_id.to_bytes(8, 'big')
        # Pack the Packet Number based on its length field+1
        packet_number_bytes = self.packet_number.to_bytes(self.header.packet_number_length + 1, 'big')
        return packed_header + dest_connection_id_bytes + packet_number_bytes + self.payload

    @staticmethod
    def unpack(packet_bytes: bytes) -> 'Packet':
        # Unpack the header
        header = PacketHeader.unpack(packet_bytes[0:1])
        destination_connection_id = int.from_bytes(packet_bytes[1:9], 'big')
        packet_number = int.from_bytes(packet_bytes[9:9 + header.packet_number_length + 1], 'big')
        payload = packet_bytes[9 + header.packet_number_length + 1:]

        return Packet(
            header=header,
            destination_connection_id=destination_connection_id,
            packet_number=packet_number,
            payload=payload
        )

    def get_payload_frames_dict(self) -> dict:
        index = 0
        frames_dict = {}
        while index < len(self.payload):
            frame_total_length = 9  # in bytes
            type_byte_int = int.from_bytes(self.payload[index:index + 1], 'big')  # type of first frame
            stream_id_int = int.from_bytes(self.payload[index + 1:index + 9], 'big')  # stream_id of first frame
            if type_byte_int & OFF_BIT:  # off bit is 1 [9:17]
                frame_total_length += 8
            if type_byte_int & LEN_BIT:  # len bit is 1 [17:25]
                frame_total_length += 8 + int.from_bytes(self.payload[17:25])  # len field + data
            curr_frame = self.payload[index: index + frame_total_length]
            frames_dict[stream_id_int] = curr_frame
            index += frame_total_length
        return frames_dict

    def add_frame(self, frame: bytes):
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
        self.payload += frame
