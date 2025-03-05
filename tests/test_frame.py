#!/usr/bin/env python3
"""
@file test_frame.py
@brief Unit tests for the frame module.
"""

import unittest
import sys
import os

# Add the parent directory to sys.path to import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from frame import FrameStream
from constants import Constants


class TestFrameStream(unittest.TestCase):
    """
    @brief Test cases for the FrameStream class.
    """

    def setUp(self):
        self.stream_id = 38
        self.offset = 100
        self.length = 10
        self.test_data = b'Test data!'
        self.frame = FrameStream(
            stream_id=self.stream_id,
            offset=self.offset,
            length=self.length,
            fin=False,
            data=self.test_data
        )
        self.fin_frame = FrameStream(
            stream_id=self.stream_id,
            offset=self.offset,
            length=self.length,
            fin=True,
            data=self.test_data
        )

    def test_init(self):
        """Test initialization of FrameStream"""
        self.assertEqual(self.frame.stream_id, self.stream_id)
        self.assertEqual(self.frame.offset, self.offset)
        self.assertEqual(self.frame.length, self.length)
        self.assertFalse(self.frame.fin)
        self.assertEqual(self.frame.data, self.test_data)

    def test_encode_decode(self):
        """Test encoding and decoding of frames"""
        encoded_frame = self.frame.encode()
        decoded_frame = FrameStream.decode(encoded_frame)

        self.assertEqual(decoded_frame.stream_id, self.stream_id)
        self.assertEqual(decoded_frame.offset, self.offset)
        self.assertEqual(decoded_frame.length, self.length)
        self.assertFalse(decoded_frame.fin)
        self.assertEqual(decoded_frame.data, self.test_data)

    def test_encode_decode_with_fin(self):
        """Test encoding and decoding of frames with FIN flag"""
        encoded_frame = self.fin_frame.encode()
        decoded_frame = FrameStream.decode(encoded_frame)

        self.assertEqual(decoded_frame.stream_id, self.stream_id)
        self.assertEqual(decoded_frame.offset, self.offset)
        self.assertEqual(decoded_frame.length, self.length)
        self.assertTrue(decoded_frame.fin)
        self.assertEqual(decoded_frame.data, self.test_data)

    def test_zero_offset(self):
        """Test frame with zero offset"""
        frame = FrameStream(
            stream_id=self.stream_id,
            offset=0,
            length=self.length,
            fin=False,
            data=self.test_data
        )

        encoded_frame = frame.encode()
        decoded_frame = FrameStream.decode(encoded_frame)

        self.assertEqual(decoded_frame.offset, 0)

    def test_zero_length(self):
        """Test frame with zero length"""
        frame = FrameStream(
            stream_id=self.stream_id,
            offset=self.offset,
            length=0,
            fin=False,
            data=self.test_data
        )

        encoded_frame = frame.encode()
        decoded_frame = FrameStream.decode(encoded_frame)

        self.assertEqual(decoded_frame.length, 0)

    def test_end_of_attrs(self):
        """Test end_of_attrs method"""
        encoded_frame = self.frame.encode()
        end_attrs = FrameStream.end_of_attrs(encoded_frame[:Constants.FRAME_TYPE_FIELD_LENGTH])

        # For a frame with offset and length, the end of attributes should be:
        # type field (1) + stream_id (8) + offset (8) + length (8)
        expected_end = Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH + Constants.OFFSET_LENGTH + Constants.LEN_LENGTH
        self.assertEqual(end_attrs, expected_end)

    def test_end_of_attrs_no_offset_no_length(self):
        """Test end_of_attrs method with no offset and no length"""
        frame = FrameStream(
            stream_id=self.stream_id,
            offset=0,
            length=0,
            fin=False,
            data=self.test_data
        )

        encoded_frame = frame.encode()
        end_attrs = FrameStream.end_of_attrs(encoded_frame[:Constants.FRAME_TYPE_FIELD_LENGTH])

        # For a frame with no offset and no length, the end of attributes should be:
        # type field (1) + stream_id (8)
        expected_end = Constants.FRAME_TYPE_FIELD_LENGTH + Constants.STREAM_ID_LENGTH
        self.assertEqual(end_attrs, expected_end)

    def test_length_from_attrs(self):
        """Test length_from_attrs method"""
        encoded_frame = self.frame.encode()
        end_attrs = FrameStream.end_of_attrs(encoded_frame[:Constants.FRAME_TYPE_FIELD_LENGTH])
        length = FrameStream.length_from_attrs(encoded_frame[:end_attrs], end_attrs)

        self.assertEqual(length, self.length)

    def test_length_from_attrs_zero_length(self):
        """Test length_from_attrs method with zero length"""
        test_frame_header = bytes([0x08])  # MIN_TYPE_FIELD without LEN_BIT
        test_frame_header += bytes([0] * Constants.STREAM_ID_LENGTH)

        end_attrs = FrameStream.end_of_attrs(test_frame_header)
        length = FrameStream.length_from_attrs(test_frame_header, end_attrs)

        self.assertEqual(length, 0)

    def test_all_combinations(self):
        """Test all combinations of offset, length, and fin flags"""
        combinations = [
            # (offset, length, fin)
            (0, 0, False),
            (0, 0, True),
            (0, 10, False),
            (0, 10, True),
            (100, 0, False),
            (100, 0, True),
            (100, 10, False),
            (100, 10, True),
        ]

        for offset, length, fin in combinations:
            frame = FrameStream(
                stream_id=self.stream_id,
                offset=offset,
                length=length,
                fin=fin,
                data=self.test_data
            )

            encoded_frame = frame.encode()
            decoded_frame = FrameStream.decode(encoded_frame)

            self.assertEqual(decoded_frame.stream_id, self.stream_id)
            self.assertEqual(decoded_frame.offset, offset)
            self.assertEqual(decoded_frame.length, length)
            self.assertEqual(decoded_frame.fin, fin)
            self.assertEqual(decoded_frame.data, self.test_data)

    def test_large_values(self):
        """Test with large values for stream_id, offset, and length"""
        large_stream_id = 2 ** 63 - 1  # Max value for 8 bytes
        large_offset = 2 ** 63 - 1
        large_length = 2 ** 63 - 1

        frame = FrameStream(
            stream_id=large_stream_id,
            offset=large_offset,
            length=large_length,
            fin=True,
            data=self.test_data
        )

        encoded_frame = frame.encode()
        decoded_frame = FrameStream.decode(encoded_frame)

        self.assertEqual(decoded_frame.stream_id, large_stream_id)
        self.assertEqual(decoded_frame.offset, large_offset)
        self.assertEqual(decoded_frame.length, large_length)
        self.assertTrue(decoded_frame.fin)
        self.assertEqual(decoded_frame.data, self.test_data)


if __name__ == '__main__':
    unittest.main()