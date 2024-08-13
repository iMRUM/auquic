from dataclasses import dataclass
from typing import Optional
import struct


@dataclass
class PacketHeader:  # total 1 byte
    header_form: int  # 1 bit
    fixed_bit: int  # 1 bit
    spin_bit: int  # 1 bit
    reserved_bits: int  # 2 bits
    key_phase: int  # 1 bit
    packet_number_length: int  # 2 bits

    def pack(self) -> bytes:
        # Pack these into a single byte
        first_byte = (
                (self.header_form << 7) |
                (self.fixed_bit << 6) |
                (self.spin_bit << 5) |
                (self.reserved_bits << 3) |
                (self.key_phase << 2) |
                (self.packet_number_length)
        )
        return struct.pack("B", first_byte)  # "B" is for a single unsigned byte

    @staticmethod
    def unpack(data: bytes):
        first_byte = struct.unpack("B", data[:1])[0]
        return PacketHeader(
            header_form=(first_byte >> 7) & 0x01,
            fixed_bit=(first_byte >> 6) & 0x01,
            spin_bit=(first_byte >> 5) & 0x01,
            reserved_bits=(first_byte >> 3) & 0x03,
            key_phase=(first_byte >> 2) & 0x01,
            packet_number_length=first_byte & 0x03
        )


@dataclass
class Packet:
    header: PacketHeader
    destination_connection_id: int  # Variable length (let's assume 8 bytes in this example)
    packet_number: int  # Variable length (e.g., 2 bytes here)
    payload: bytes  # Payload (variable length)

    def pack(self) -> bytes:
        # Pack the header
        packed_header = self.header.pack()

        # Assume Destination Connection ID is 8 bytes
        packed_connection_id = struct.pack(">Q",
                                           self.destination_connection_id)  # ">Q" is for 8-byte unsigned integer in big-endian

        # Pack the Packet Number based on its length
        packet_number_format = {1: "B", 2: ">H", 3: ">I", 4: ">I"}[self.header.packet_number_length]
        if self.header.packet_number_length == 3:
            packet_number_bytes = struct.pack(packet_number_format, self.packet_number)[1:]
        else:
            packet_number_bytes = struct.pack(packet_number_format, self.packet_number)

        # Combine everything
        return packed_header + packed_connection_id + packet_number_bytes + self.payload

    @staticmethod
    def unpack(data: bytes) -> 'Packet':
        # Unpack the header
        header = PacketHeader.unpack(data[:1])

        # Unpack the Destination Connection ID (assume 8 bytes)
        destination_connection_id = struct.unpack(">Q", data[1:9])[0]

        # Unpack the Packet Number based on the header's Packet Number Length
        packet_number_format = {1: "B", 2: ">H", 3: ">I", 4: ">I"}[header.packet_number_length]
        start_index = 9
        if header.packet_number_length == 3:
            packet_number = struct.unpack(packet_number_format, b'\x00' + data[start_index:start_index + 3])[0]
        else:
            packet_number = \
                struct.unpack(packet_number_format, data[start_index:start_index + header.packet_number_length])[0]

        # The rest is the payload
        payload = data[start_index + header.packet_number_length:]

        return Packet(
            header=header,
            destination_connection_id=destination_connection_id,
            packet_number=packet_number,
            payload=payload
        )

    def add_frame(self, stream_id, data):
        """
        Add a frame to the packet.

        Args:
            stream_id (int): Unique identifier for the stream.
            data (bytes): The data to be added as a frame.
        """
        frame = {
            'stream_id': stream_id,
            'data': data
        }
        self.frames.append(frame)
