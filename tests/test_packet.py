#!/usr/bin/env python3
"""
@file test_packet.py
@brief Unit tests for the packet module.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add the parent directory to sys.path to import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packet import PacketHeader, Packet
from frame import FrameStream
from constants import Constants


class TestPacketHeader(unittest.TestCase):
    """
    @brief Test cases for the PacketHeader class.
    """

    def setUp(self):
        self.header = PacketHeader(packet_number_length=1)
        self.header_all_fields = PacketHeader(
            packet_number_length=3,
            header_form=True,
            fixed_bit=True,
            spin_bit=True,
            key_phase=True,
            reserved_bits=3
        )

    def test_init_default(self):
        """Test initialization with default values"""
        self.assertEqual(self.header.packet_number_length, 1)
        self.assertFalse(self.header.header_form)
        self.assertFalse(self.header.fixed_bit)
        self.assertFalse(self.header.spin_bit)
        self.assertFalse(self.header.key_phase)
        self.assertEqual(self.header.reserved_bits, Constants.ZERO)

    def test_init_custom(self):
        """Test initialization with custom values"""
        self.assertEqual(self.header_all_fields.packet_number_length, 3)
        self.assertTrue(self.header_all_fields.header_form)
        self.assertTrue(self.header_all_fields.fixed_bit)
        self.assertTrue(self.header_all_fields.spin_bit)
        self.assertTrue(self.header_all_fields.key_phase)
        self.assertEqual(self.header_all_fields.reserved_bits, 3)

    def test_pack(self):
        """Test packing header to bytes"""
        packed_header = self.header.pack()
        self.assertEqual(len(packed_header), Constants.HEADER_LENGTH)
        self.assertEqual(packed_header, bytes([0x01]))  # Just packet_number_length=1

    def test_pack_all_fields(self):
        """Test packing header with all fields set"""
        packed_header = self.header_all_fields.pack()
        self.assertEqual(len(packed_header), Constants.HEADER_LENGTH)

        expected_byte = (
                (int(self.header_all_fields.header_form) << Constants.FORM_SHIFT) |
                (int(self.header_all_fields.fixed_bit) << Constants.FIXED_SHIFT) |
                (int(self.header_all_fields.spin_bit) << Constants.SPIN_SHIFT) |
                (self.header_all_fields.reserved_bits << Constants.RES_SHIFT) |
                (int(self.header_all_fields.key_phase) << Constants.KEY_SHIFT) |
                self.header_all_fields.packet_number_length
        )
        self.assertEqual(packed_header, bytes([expected_byte]))

    def test_unpack(self):
        """Test unpacking header from bytes"""
        packed_header = self.header.pack()
        unpacked_header = PacketHeader.unpack(packed_header)

        self.assertEqual(unpacked_header.packet_number_length, self.header.packet_number_length)
        self.assertEqual(unpacked_header.header_form, self.header.header_form)
        self.assertEqual(unpacked_header.fixed_bit, self.header.fixed_bit)
        self.assertEqual(unpacked_header.spin_bit, self.header.spin_bit)
        self.assertEqual(unpacked_header.key_phase, self.header.key_phase)
        self.assertEqual(unpacked_header.reserved_bits, self.header.reserved_bits)

    def test_unpack_all_fields(self):
        """Test unpacking header with all fields set"""
        packed_header = self.header_all_fields.pack()
        unpacked_header = PacketHeader.unpack(packed_header)

        self.assertEqual(unpacked_header.packet_number_length, self.header_all_fields.packet_number_length)
        self.assertEqual(unpacked_header.header_form, self.header_all_fields.header_form)
        self.assertEqual(unpacked_header.fixed_bit, self.header_all_fields.fixed_bit)
        self.assertEqual(unpacked_header.spin_bit, self.header_all_fields.spin_bit)
        self.assertEqual(unpacked_header.key_phase, self.header_all_fields.key_phase)

        if self.header_all_fields.reserved_bits:
            self.assertNotEqual(unpacked_header.reserved_bits, 0)


class TestPacket(unittest.TestCase):
    """
    @brief Test cases for the Packet class.
    """

    def setUp(self):
        self.destination_connection_id = 38
        self.packet_number = 1
        self.packet = Packet(self.destination_connection_id, self.packet_number)

        # Create test frames
        self.test_frames = [
            FrameStream(
                stream_id=10,
                offset=0,
                length=len(b'Frame 1'),
                fin=False,
                data=b'Frame 1'
            ),
            FrameStream(
                stream_id=20,
                offset=0,
                length=len(b'Frame 2'),
                fin=True,
                data=b'Frame 2'
            )
        ]

    def test_init(self):
        """Test initialization"""
        self.assertEqual(self.packet.destination_connection_id, self.destination_connection_id)
        self.assertEqual(self.packet.packet_number, self.packet_number)
        self.assertEqual(self.packet.payload, [])

    def test_add_frame(self):
        """Test adding a frame to the packet"""
        self.packet.add_frame(self.test_frames[0])
        self.assertEqual(len(self.packet.payload), 1)
        self.assertEqual(self.packet.payload[0], self.test_frames[0])

        self.packet.add_frame(self.test_frames[1])
        self.assertEqual(len(self.packet.payload), 2)
        self.assertEqual(self.packet.payload[1], self.test_frames[1])

    def test_pack_empty(self):
        """Test packing an empty packet"""
        packed_packet = self.packet.pack()

        # Header (1) + Dest Connection ID (8) + Packet Number (variable, but at least 1)
        min_expected_length = Constants.HEADER_LENGTH + Constants.DEST_CONNECTION_ID_LENGTH + 1
        self.assertGreaterEqual(len(packed_packet), min_expected_length)

    def test_pack_with_frames(self):
        """Test packing a packet with frames"""
        for frame in self.test_frames:
            self.packet.add_frame(frame)

        packed_packet = self.packet.pack()

        # Header + Dest Connection ID + Packet Number + Encoded frames
        min_expected_length = (Constants.HEADER_LENGTH +
                               Constants.DEST_CONNECTION_ID_LENGTH +
                               1 +  # Minimum packet number length
                               sum(len(frame.encode()) for frame in self.test_frames))

        self.assertGreaterEqual(len(packed_packet), min_expected_length)

    def test_unpack(self):
        """Test unpacking a packet"""
        for frame in self.test_frames:
            self.packet.add_frame(frame)

        packed_packet = self.packet.pack()
        unpacked_packet = Packet.unpack(packed_packet)

        self.assertEqual(unpacked_packet.destination_connection_id, self.packet.destination_connection_id)
        self.assertEqual(len(unpacked_packet.payload), len(self.packet.payload))

        for i, frame in enumerate(unpacked_packet.payload):
            self.assertEqual(frame.stream_id, self.test_frames[i].stream_id)
            self.assertEqual(frame.offset, self.test_frames[i].offset)
            self.assertEqual(frame.length, self.test_frames[i].length)
            self.assertEqual(frame.fin, self.test_frames[i].fin)
            self.assertEqual(frame.data, self.test_frames[i].data)

    def test_get_frames_from_payload_bytes(self):
        """Test extracting frames from payload bytes"""
        encoded_frames = b''
        for frame in self.test_frames:
            encoded_frames += frame.encode()

        decoded_frames = Packet.get_frames_from_payload_bytes(encoded_frames)

        self.assertEqual(len(decoded_frames), len(self.test_frames))
        for i, frame in enumerate(decoded_frames):
            self.assertEqual(frame.stream_id, self.test_frames[i].stream_id)
            self.assertEqual(frame.offset, self.test_frames[i].offset)
            self.assertEqual(frame.length, self.test_frames[i].length)
            self.assertEqual(frame.fin, self.test_frames[i].fin)
            self.assertEqual(frame.data, self.test_frames[i].data)

    def test_large_values(self):
        """Test with large values for destination_connection_id and packet_number"""
        large_dest_id = 2 ** 64 - 1  # Max value for 8 bytes
        large_packet_number = 2 ** 32 - 1  # Max value for 4 bytes

        packet = Packet(large_dest_id, large_packet_number)
        packed_packet = packet.pack()
        unpacked_packet = Packet.unpack(packed_packet)

        self.assertEqual(unpacked_packet.destination_connection_id, large_dest_id)
        self.assertEqual(unpacked_packet.packet_number, large_packet_number)


if __name__ == '__main__':
    unittest.main()