from dataclasses import dataclass, field
from sys import getsizeof

from constants import Constants
from frame import FrameStream

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
    packet_number_length: int  # 2 bits, one less than the length of the Packet Number field in bytes
    header_form: bool = False  # 1 bit
    fixed_bit: bool = False  # 1 bit
    spin_bit: bool = False  # 1 bit
    key_phase: bool = False  # 1 bit
    reserved_bits: int = Constants.ZERO  # 2 bits

    def pack(self) -> bytes:
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
        # total 1 byte
        header_form = int.from_bytes(header, "big") & Constants.FORM_MASK  # 1 bit
        fixed_bit = int.from_bytes(header, "big") & Constants.FIXED_MASK  # 1 bit
        spin_bit = int.from_bytes(header, "big") & Constants.SPIN_MASK  # 1 bit
        reserved_bits = int.from_bytes(header, "big") & Constants.RES_MASK  # 2 bits
        key_phase = int.from_bytes(header, "big") & Constants.KEY_MASK  # 1 bit
        packet_number_length = int.from_bytes(header,
                                              'big') & Constants.PACKET_NUMBER_LENGTH_MASK  # 2 bits, one less than the length of
        # the Packet Number field in bytes
        return PacketHeader(header_form=bool(header_form), fixed_bit=bool(fixed_bit), spin_bit=bool(spin_bit),
                            reserved_bits=reserved_bits, key_phase=bool(key_phase),
                            packet_number_length=packet_number_length)


@dataclass
class Packet:
    destination_connection_id: int  # 8 bytes in this implementation
    packet_number: int  # 4 bytes in this implementation
    payload: list[FrameStream] = field(default_factory=list)

    def pack(self) -> bytes:
        # Pack the header
        packet_number_length = (self.packet_number.bit_length() + Constants.SEVEN) // Constants.EIGHT
        packed_header = PacketHeader(packet_number_length).pack()
        # Assume Destination Connection ID is 8 bytes
        dest_connection_id_bytes = self.destination_connection_id.to_bytes(Constants.DEST_CONNECTION_ID_LENGTH, 'big')
        # Pack the Packet Number based on its length
        packet_number_bytes = self.packet_number.to_bytes(packet_number_length, 'big')
        packed_packet: bytes = packed_header + dest_connection_id_bytes + packet_number_bytes
        for frame in self.payload:
            packed_packet += frame.encode()
        return packed_packet

    @classmethod
    def unpack(cls, packet_bytes: bytes) -> 'Packet':
        # ignore the header
        packet_number_length = PacketHeader.unpack(packet_bytes[:Constants.HEADER_LENGTH]).packet_number_length
        index = Constants.HEADER_LENGTH
        destination_connection_id = int.from_bytes(packet_bytes[index:index + Constants.DEST_CONNECTION_ID_LENGTH], 'big')
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
        # print(f'payload_bytes: {payload_bytes}')
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
        self.payload.append(frame)
