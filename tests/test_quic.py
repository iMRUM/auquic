#!/usr/bin/env python3
"""
@file test_quic.py
@brief Unit tests for the quic module.
"""

import unittest
import sys
import os
import socket
import time
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to sys.path to import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quic import QuicConnection
from stream import Stream
from frame import FrameStream
from packet import Packet
from constants import Constants


class TestQuicConnection(unittest.TestCase):
    """
    @brief Test cases for the QuicConnection class.
    """

    def setUp(self):
        with patch('socket.socket'):
            self.connection_id = Constants.CONNECTION_ID_SENDER
            self.local_addr = Constants.ADDR_SENDER
            self.remote_addr = Constants.ADDR_RECEIVER
            self.quic_connection = QuicConnection(self.connection_id, self.local_addr, self.remote_addr)

    def test_initialization(self):
        """Test initialization of QuicConnection"""
        self.assertEqual(self.quic_connection._connection_id, self.connection_id)
        self.assertEqual(self.quic_connection._local_addr, self.local_addr)
        self.assertEqual(self.quic_connection._remote_addr, self.remote_addr)
        self.assertEqual(self.quic_connection._streams, {})
        self.assertEqual(self.quic_connection._active_streams_ids, [])
        self.assertEqual(self.quic_connection._streams_counter, Constants.ZERO)
        self.assertEqual(self.quic_connection._sent_packets_counter, Constants.ZERO)
        self.assertEqual(self.quic_connection._received_packets_counter, Constants.ZERO)
        self.assertEqual(self.quic_connection._packet_size, Constants.ZERO)
        self.assertTrue(self.quic_connection._idle)

    def test_get_stream_new(self):
        """Test getting a new stream"""
        initiated_by = Constants.CONNECTION_ID_SENDER
        direction = Constants.BIDI
        stream_id = 38
        mock_stream_instance = Mock()

        # First, make sure _stream_id_generator returns our expected ID
        with patch.object(self.quic_connection, '_stream_id_generator', return_value=stream_id):
            # Then, patch the internal get_stream_by_id method to return our mock stream
            with patch.object(self.quic_connection, '_get_stream_by_id', return_value=mock_stream_instance):
                # Now test get_stream
                result = self.quic_connection.get_stream(initiated_by, direction)

                # Verify the result is our mock stream
                self.assertEqual(result, mock_stream_instance)

    @patch('quic.Stream')
    def test_add_stream(self, mock_stream):
        """Test adding a stream"""
        mock_stream_instance = Mock()
        mock_stream.return_value = mock_stream_instance

        stream_id = 38
        initiated_by = True
        direction = False

        with patch('quic.QuicConnection._add_stream_to_stats_dict') as mock_add_stats:
            self.quic_connection._add_stream(stream_id, initiated_by, direction)

            # Check stream was added to streams dict
            self.assertIn(stream_id, self.quic_connection._streams)

            # Check stats were updated
            mock_add_stats.assert_called_once_with(stream_id)

            # Check streams counter was incremented
            self.assertEqual(self.quic_connection._streams_counter, Constants.ONE)

    def test_stream_id_generator(self):
        """Test stream ID generation"""
        # Test client-initiated bidirectional stream
        self.quic_connection._streams_counter = 1
        stream_id = self.quic_connection._stream_id_generator(Constants.CONNECTION_ID_SENDER, Constants.BIDI)
        self.assertEqual(stream_id, 4)  # 1 in binary (001) + '00' = 00100 = 4

        # Test client-initiated unidirectional stream
        self.quic_connection._streams_counter = 2
        stream_id = self.quic_connection._stream_id_generator(Constants.CONNECTION_ID_SENDER, Constants.UNIDI)
        self.assertEqual(stream_id, 10)  # 2 in binary (010) + '10' = 01010 = 10

        # Test server-initiated bidirectional stream
        self.quic_connection._streams_counter = 3
        stream_id = self.quic_connection._stream_id_generator(Constants.CONNECTION_ID_RECEIVER, Constants.BIDI)
        self.assertEqual(stream_id, 13)  # 3 in binary (011) + '01' = 01101 = 13

    def test_add_stream_to_stats_dict(self):
        """Test adding a stream to the stats dictionary"""
        stream_id = 38

        with patch('time.time', return_value=12345):
            self.quic_connection._add_stream_to_stats_dict(stream_id)

            self.assertIn(stream_id, self.quic_connection._stats_dict)
            self.assertEqual(self.quic_connection._stats_dict[stream_id]['total_bytes'], Constants.ZERO)
            self.assertEqual(self.quic_connection._stats_dict[stream_id]['total_time'], 12345)
            self.assertEqual(self.quic_connection._stats_dict[stream_id]['total_packets'], set())

    @patch('quic.Stream')
    def test_get_stream_by_id_existing(self, mock_stream):
        """Test getting an existing stream by ID"""
        stream_id = 38
        mock_stream_instance = Mock()
        self.quic_connection._streams[stream_id] = mock_stream_instance

        result = self.quic_connection._get_stream_by_id(stream_id)
        self.assertEqual(result, mock_stream_instance)

    def test_get_stream_by_id_new(self):
        """Test getting a new stream by ID"""
        stream_id = 38
        mock_stream_instance = Mock()

        # First mock is_stream_id_in_dict to return False
        with patch('quic.QuicConnection._is_stream_id_in_dict', return_value=False):
            # Then mock _add_stream to add the mock_stream to the streams dict
            def mock_add_stream(sid, init, dir):
                self.quic_connection._streams[sid] = mock_stream_instance

            with patch('quic.Stream.is_s_init_by_sid', return_value=True):
                with patch('quic.Stream.is_uni_by_sid', return_value=False):
                    with patch('quic.QuicConnection._add_stream', side_effect=mock_add_stream) as mock_add:
                        result = self.quic_connection._get_stream_by_id(stream_id)

                        self.assertEqual(result, mock_stream_instance)
                        mock_add.assert_called_once_with(stream_id, True, False)

    def test_remove_stream(self):
        """Test removing a stream"""
        stream_id = 38
        mock_stream = Mock()
        self.quic_connection._streams[stream_id] = mock_stream
        self.quic_connection._active_streams_ids.append(stream_id)

        result = self.quic_connection._remove_stream(stream_id)

        self.assertEqual(result, mock_stream)
        self.assertNotIn(stream_id, self.quic_connection._active_streams_ids)
        self.assertNotIn(stream_id, self.quic_connection._streams)

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b'Test file data')
    def test_add_file_to_stream(self, mock_open):
        """Test adding a file to a stream"""
        stream_id = 38
        path = "test_file.txt"

        with patch('quic.QuicConnection._add_data_to_stream') as mock_add_data:
            self.quic_connection.add_file_to_stream(stream_id, path)

            mock_open.assert_called_once_with(path, 'rb')
            mock_add_data.assert_called_once_with(stream_id, b'Test file data')

    def test_add_data_to_stream(self):
        """Test adding data to a stream"""
        stream_id = 38
        data = b'Test data'
        mock_stream = Mock()

        with patch('quic.QuicConnection._get_stream_by_id', return_value=mock_stream) as mock_get:
            with patch('quic.QuicConnection._add_active_stream_id') as mock_add_active:
                self.quic_connection._add_data_to_stream(stream_id, data)

                mock_get.assert_called_once_with(stream_id)
                mock_stream.add_data_to_stream.assert_called_once_with(data=data)
                mock_add_active.assert_called_once_with(stream_id)

    def test_add_active_stream_id(self):
        """Test adding an active stream ID"""
        stream_id = 38

        # Test adding a new active stream ID
        self.quic_connection._add_active_stream_id(stream_id)
        self.assertIn(stream_id, self.quic_connection._active_streams_ids)

        # Test adding an already active stream ID (should not duplicate)
        initial_length = len(self.quic_connection._active_streams_ids)
        self.quic_connection._add_active_stream_id(stream_id)
        self.assertEqual(len(self.quic_connection._active_streams_ids), initial_length)

    def test_is_stream_id_in_dict(self):
        """Test checking if a stream ID is in the dictionary"""
        stream_id = 38

        # Test with stream not in dictionary
        self.assertFalse(self.quic_connection._is_stream_id_in_dict(stream_id))

        # Test with stream in dictionary
        self.quic_connection._streams[stream_id] = Mock()
        self.assertTrue(self.quic_connection._is_stream_id_in_dict(stream_id))

    @patch('time.time', return_value=12345)
    def test_set_start_time(self, mock_time):
        """Test setting the start time for all streams"""
        self.quic_connection._stats_dict = {
            1: {'total_time': 0},
            2: {'total_time': 0}
        }

        self.quic_connection._set_start_time()

        for stream in self.quic_connection._stats_dict.values():
            self.assertEqual(stream['total_time'], 12345)

    @patch('quic.QuicConnection._send_packet_size')
    @patch('quic.QuicConnection._create_packet')
    @patch('quic.QuicConnection._send_packet')
    @patch('quic.QuicConnection._close_connection')
    def test_send_packets(self, mock_close, mock_send, mock_create, mock_send_size):
        """Test sending packets"""
        mock_packet = Mock()
        mock_create.return_value = mock_packet
        mock_packet.pack.return_value = b'packed packet'

        # Setup to run the loop once then exit
        self.quic_connection._active_streams_ids = [38]

        def side_effect(*args, **kwargs):
            self.quic_connection._active_streams_ids = []
            return True

        mock_send.side_effect = side_effect

        with patch('time.time', return_value=12345):
            self.quic_connection.send_packets()

            mock_send_size.assert_called_once()
            mock_create.assert_called_once()
            mock_send.assert_called_once_with(b'packed packet')
            mock_close.assert_called_once()

    def test_send_packet_size(self):
        """Test sending the packet size"""
        with patch('quic.PACKET_SIZE', 1500):
            with patch('quic.QuicConnection._send_packet', return_value=True) as mock_send:
                result = self.quic_connection._send_packet_size()

                self.assertEqual(self.quic_connection._packet_size, 1500)
                mock_send.assert_called_once_with((1500).to_bytes(Constants.PACKET_SIZE_BYTES, 'big'))
                self.assertTrue(result)

    @patch('sys.getsizeof', side_effect=lambda x: 10 if isinstance(x, Packet) else 5)
    def test_create_packet(self, mock_getsizeof):
        """Test creating a packet"""
        self.quic_connection._packet_size = 30

        with patch('quic.Packet') as mock_packet_class:
            mock_packet = Mock()
            mock_packet_class.return_value = mock_packet

            with patch('quic.QuicConnection._generate_streams_frames'):
                with patch('quic.QuicConnection._get_stream_from_active_streams', return_value=None):
                    result = self.quic_connection._create_packet()

                    expected_dest_conn_id = 1  # Based on connection_id=0 in setup
                    mock_packet_class.assert_called_once_with(expected_dest_conn_id, Constants.ZERO)
                    self.assertEqual(self.quic_connection._sent_packets_counter, 1)

    def test_generate_streams_frames(self):
        """Test generating frames for all active streams"""
        stream_id1, stream_id2 = 38, 43
        self.quic_connection._active_streams_ids = [stream_id1, stream_id2]

        mock_stream1, mock_stream2 = Mock(), Mock()

        with patch('quic.PACKET_SIZE', 1500):
            with patch('quic.QuicConnection._get_stream_by_id', side_effect=[mock_stream1, mock_stream2]) as mock_get:
                self.quic_connection._generate_streams_frames()

                self.assertEqual(mock_get.call_count, 2)
                mock_stream1.generate_stream_frames.assert_called_once_with(1500 // Constants.FRAMES_IN_PACKET)
                mock_stream2.generate_stream_frames.assert_called_once_with(1500 // Constants.FRAMES_IN_PACKET)

    def test_get_stream_from_active_streams_empty(self):
        """Test getting a stream from active streams when empty"""
        self.quic_connection._active_streams_ids = []

        result = self.quic_connection._get_stream_from_active_streams()

        self.assertIsNone(result)
        self.assertFalse(self.quic_connection._idle)

    @patch('random.choice', return_value=38)
    def test_get_stream_from_active_streams(self, mock_choice):
        """Test getting a stream from active streams"""
        stream_id = 38
        mock_stream = Mock()
        self.quic_connection._streams[stream_id] = mock_stream
        self.quic_connection._active_streams_ids = [stream_id]

        result = self.quic_connection._get_stream_from_active_streams()

        self.assertEqual(result, mock_stream)

    def test_send_packet(self):
        """Test sending a packet"""
        packet = b'test packet'

        self.quic_connection._socket.sendto.return_value = len(packet)

        result = self.quic_connection._send_packet(packet)

        self.quic_connection._socket.sendto.assert_called_once_with(packet, self.remote_addr)
        self.assertTrue(result)

    @patch('quic.QuicConnection._receive_packet')
    def test_receive_packets(self, mock_receive):
        """Test receiving packets"""
        # Setup to run the loop once then exit
        self.quic_connection._idle = True

        def side_effect(*args, **kwargs):
            self.quic_connection._idle = False

        mock_receive.side_effect = side_effect

        self.quic_connection.receive_packets()

        self.quic_connection._socket.settimeout.assert_called_once_with(Constants.TIMEOUT)
        mock_receive.assert_called_once()

    @patch('quic.QuicConnection._handle_received_packet_size')
    def test_receive_packet_size(self, mock_handle):
        """Test receiving a packet size"""
        packet = b'size packet'
        addr = ('127.0.0.1', 1234)

        self.quic_connection._socket.recvfrom.return_value = (packet, addr)

        with patch('time.time', return_value=12345):
            with patch('quic.QuicConnection._increment_received_packets_counter') as mock_increment:
                self.quic_connection._receive_packet()

                mock_handle.assert_called_once_with(packet)
                mock_increment.assert_called_once()

    @patch('quic.QuicConnection._handle_received_packet')
    def test_receive_packet_data(self, mock_handle):
        """Test receiving a data packet"""
        self.quic_connection._packet_size = 1500
        packet = b'data packet'
        addr = ('127.0.0.1', 1234)

        self.quic_connection._socket.recvfrom.return_value = (packet, addr)

        with patch('quic.QuicConnection._increment_received_packets_counter') as mock_increment:
            self.quic_connection._receive_packet()

            mock_handle.assert_called_once_with(packet)
            self.assertTrue(mock_increment.called)

    def test_increment_received_packets_counter(self):
        """Test incrementing the received packets counter"""
        initial = self.quic_connection._received_packets_counter

        self.quic_connection._increment_received_packets_counter()

        self.assertEqual(self.quic_connection._received_packets_counter, initial + 1)

    def test_handle_received_packet_size(self):
        """Test handling a received packet size"""
        packet_size = (1500).to_bytes(Constants.PACKET_SIZE_BYTES, 'big')

        with patch('builtins.print') as mock_print:
            self.quic_connection._handle_received_packet_size(packet_size)

            mock_print.assert_called_once()
            self.assertEqual(self.quic_connection._packet_size, 1500)


if __name__ == '__main__':
    unittest.main()