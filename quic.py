"""
@file quic.py
@brief Implementation of QUIC connection handling.
@details Contains the QuicConnection class which manages QUIC connections,
         including stream creation, packet sending/receiving, and statistics tracking.
"""

import socket
import time
import random
from sys import getsizeof

from constants import Constants
from frame import FrameStream
from packet import Packet
from stream import Stream

# Define the packet size randomly within the given range
PACKET_SIZE = random.randint(Constants.MIN_PACKET_SIZE, Constants.MAX_PACKET_SIZE)


class QuicConnection:
    """
    @brief Manages a QUIC connection.

    @details Handles stream creation, packet assembly, sending/receiving data,
             and tracking connection statistics.
    """

    def __init__(self, connection_id: int, local_addr: tuple, remote_addr: tuple):
        """
        @brief Initialize a QuicConnection instance.

        @param connection_id The ID of the connection (0 for client, 1 for server).
        @param local_addr The local address for the connection (IP, port).
        @param remote_addr The remote address for the connection (IP, port).
        """
        self._connection_id = connection_id
        self._local_addr = local_addr
        self._remote_addr = remote_addr
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(local_addr)
        self._streams: dict[int, Stream] = {}
        self._active_streams_ids: list[int] = []
        self._stats_dict = {}  # stream_id: {total_bytes: , total_packets: , total_time:}
        self._streams_counter = Constants.ZERO
        self._sent_packets_counter = Constants.ZERO
        self._received_packets_counter = Constants.ZERO
        self._pending_frames: list['FrameStream'] = []
        self._total_time: float = Constants.ZERO
        self._packet_size: int = Constants.ZERO  # 2 bytes
        self._idle = True

    def get_stream(self, initiated_by: int, direction: int) -> 'Stream':
        """
        @brief Retrieve or create a new stream for the connection.

        @param initiated_by Indicates whether the stream was initiated by 'client'(0) or 'server'(1).
        @param direction Indicates if the stream is bidirectional(0) or unidirectional(1).
        @return The created or retrieved stream.
        """
        stream_id = self._stream_id_generator(initiated_by, direction)
        if not self._is_stream_id_in_dict(stream_id):
            self._add_stream(stream_id, bool(initiated_by), bool(direction))
        return self._get_stream_by_id(stream_id)

    def _stream_id_generator(self, initiated_by: int, direction: int) -> int:
        """
        @brief Generate a unique stream ID.

        @details Generates ID based on stream counter, initiator, and direction.

        @param initiated_by Indicates whether the stream was initiated by 'client'(0) or 'server'(1).
        @param direction Indicates whether the stream is bidirectional(0) or unidirectional(1).
        @return The generated stream ID.
        """
        str_binary = bin(self._streams_counter)[Constants.TWO:]  # convert to binary string without prefix (index=2)
        str_binary += str(direction) + str(initiated_by)
        padded_int = int(str_binary, Constants.BASE_TWO)
        return padded_int

    def _add_stream(self, stream_id: int, initiated_by: bool, direction: bool):
        """
        @brief Add a new stream to the connection.

        @details Initializes the stream's statistics.

        @param stream_id The ID of the stream to add.
        @param initiated_by Indicates if the stream was initiated by the server.
        @param direction Indicates if the stream is unidirectional.
        """
        self._streams[stream_id] = Stream(stream_id, initiated_by, direction)
        self._add_stream_to_stats_dict(stream_id)
        self._streams_counter += Constants.ONE

    def _add_stream_to_stats_dict(self, stream_id: int):
        """
        @brief Initialize statistics for a new stream.

        @param stream_id The ID of the stream.
        """
        self._stats_dict[stream_id] = {'total_bytes': Constants.ZERO, 'total_time': time.time(), 'total_packets': set()}

    def _get_stream_by_id(self, stream_id: int) -> 'Stream':
        """
        @brief Retrieve a stream by its ID.

        @details Creates the stream if necessary.

        @param stream_id The ID of the stream to retrieve.
        @return The retrieved or newly created stream.
        """
        if not self._is_stream_id_in_dict(stream_id):
            self._add_stream(stream_id, Stream.is_s_init_by_sid(stream_id), Stream.is_uni_by_sid(stream_id))
        return self._streams[stream_id]

    def _remove_stream(self, stream_id: int) -> 'Stream':
        """
        @brief Remove a stream from the active streams list and the streams dictionary.

        @param stream_id The ID of the stream to remove.
        @return The removed stream.
        """
        self._active_streams_ids.remove(stream_id)
        return self._streams.pop(stream_id)

    def add_file_to_stream(self, stream_id: int, path: str):
        """
        @brief Add a file's content to a stream.

        @param stream_id The ID of the stream to add the file to.
        @param path The file path.
        """
        with open(path, 'rb') as file:
            data = file.read()
        self._add_data_to_stream(stream_id, data)

    def _add_data_to_stream(self, stream_id: int, data: bytes):
        """
        @brief Add data to a specific stream's buffer.

        @param stream_id The ID of the stream.
        @param data The data to add.
        """
        stream = self._get_stream_by_id(stream_id)
        stream.add_data_to_stream(data=data)
        self._add_active_stream_id(stream_id)

    def _add_active_stream_id(self, stream_id: int):
        """
        @brief Mark a stream as active.

        @details Adds stream ID to the active streams list.

        @param stream_id The ID of the stream to mark as active.
        """
        if stream_id not in self._active_streams_ids:
            self._active_streams_ids.append(stream_id)

    def _is_stream_id_in_dict(self, stream_id: int) -> bool:
        """
        @brief Check if a stream ID exists in the streams dict.

        @param stream_id The ID of the stream to check.
        @return True if the stream ID exists, False otherwise.
        """
        return stream_id in self._streams.keys()

    def _set_start_time(self):
        """
        @brief Set the start time for all streams in the connection.
        """
        start_time = time.time()
        for stream in self._stats_dict.values():
            stream['total_time'] = start_time

    def send_packets(self):
        """
        @brief Continuously create and send packets until all streams are finished.
        """
        self._send_packet_size()
        start_time = time.time()
        for stream in self._stats_dict.values():
            stream['total_time'] = start_time
        while self._active_streams_ids:
            packet = self._create_packet()
            self._send_packet(packet.pack())
        self._close_connection()

    def _send_packet_size(self):
        """
        @brief Send the packet size to the remote peer.

        @return True if the packet size was sent successfully, False otherwise.
        """
        self._packet_size = PACKET_SIZE
        packet_size_bytes = self._packet_size.to_bytes(Constants.PACKET_SIZE_BYTES, 'big')
        return self._send_packet(packet_size_bytes)

    def _create_packet(self) -> Packet:
        """
        @brief Create a packet containing frames from the streams.

        @details 1. Generate frames for each stream
                 2. Assemble SOME of them and add to packet payload
                 3. Add packet to pending packets

        @return The created packet with frames from different streams.
        """
        self._generate_streams_frames()
        remaining_space = self._packet_size
        packet = Packet(int(not self._connection_id), self._sent_packets_counter)
        remaining_space -= getsizeof(packet)
        while remaining_space > Constants.ZERO:
            if self._pending_frames:
                frame = self._pending_frames.pop(Constants.START)
            else:
                stream = self._get_stream_from_active_streams()
                if stream:
                    frame = stream.send_next_frame()
                    if stream.is_finished():
                        self._remove_stream(stream.get_stream_id())
                else:
                    break
            size_of_frame = getsizeof(frame.encode())
            if size_of_frame <= remaining_space:
                packet.add_frame(frame)
                remaining_space -= size_of_frame
            else:
                self._pending_frames.append(frame)
                break
        self._sent_packets_counter += Constants.ONE
        return packet

    def _generate_streams_frames(self):
        """
        @brief Generate frames for each active stream.
        """
        for stream_id in self._active_streams_ids:
            self._get_stream_by_id(stream_id).generate_stream_frames(PACKET_SIZE // Constants.FRAMES_IN_PACKET)

    def _get_stream_from_active_streams(self) -> Stream | None:
        """
        @brief Retrieve a stream from the list of active streams.

        @return The retrieved stream, or None if no active streams.
        """
        if not self._active_streams_ids:
            self._idle = False
            return None
        try:
            return self._streams[random.choice(self._active_streams_ids)]  # return a random stream
        except IndexError:
            print("No more streams!")
            return None

    def _send_packet(self, packet: bytes):
        """
        @brief Send a packet to the remote address.

        @param packet The packet to send.
        @return True if the packet was sent successfully, False otherwise.
        """
        return self._socket.sendto(packet, self._remote_addr) > 0

    def receive_packets(self):
        """
        @brief Continuously receive packets until the connection is closed or a timeout occurs.
        """
        self._socket.settimeout(Constants.TIMEOUT)
        while self._idle:
            try:
                self._receive_packet()
            except OSError as e:
                print(f"An error occurred in receive_packets: {e}")
                break

    def _receive_packet(self):
        """
        @brief Receive a packet and process it.

        @details If socket times out, the connection will be closed.
        """
        try:
            if self._packet_size == Constants.ZERO:
                packet, addr = self._socket.recvfrom(Constants.PACKET_SIZE_BYTES)
                self._total_time = time.time()
                self._handle_received_packet_size(packet)
            else:
                packet, addr = self._socket.recvfrom(self._packet_size)
                self._handle_received_packet(packet)
                if not self._active_streams_ids:
                    self._increment_received_packets_counter()
                    self._close_connection()
            self._increment_received_packets_counter()
        except socket.timeout:
            self._close_connection()

    def _increment_received_packets_counter(self):
        """
        @brief Increment the counter for received packets.
        """
        self._received_packets_counter += Constants.ONE

    def _handle_received_packet_size(self, packet_size: bytes):
        """
        @brief Handle the reception of the packet size from the peer.

        @param packet_size The received packet size in bytes.
        """
        print(f'Packet size received: {int.from_bytes(packet_size, "big")}')
        self._packet_size = int.from_bytes(packet_size, 'big')

    def _handle_received_packet(self, packet: bytes):
        """
        @brief Handle the reception of a packet and its frames.

        @param packet The received packet in bytes.
        """
        unpacked_packet = Packet.unpack(packet)
        frames_in_packet = unpacked_packet.payload
        for frame in frames_in_packet:
            stream_id = frame.stream_id
            self._add_active_stream_id(stream_id)
            try:
                self._get_stream_by_id(stream_id).receive_frame(frame)
                self._stats_dict[stream_id]['total_bytes'] += len(frame.encode())
                self._stats_dict[stream_id]['total_packets'].add(unpacked_packet.packet_number)
                if self._get_stream_by_id(stream_id).is_finished():
                    self._write_stream(stream_id)
            except Exception as e:
                print(f"An error occurred handle_received_packet: {e}")

    def _write_stream(self, stream_id: int) -> bool:
        """
        @brief Write the received data of a stream to a file.

        @param stream_id The ID of the stream whose data should be written.
        @return True if the data was written successfully, False otherwise.
        """
        stream = self._remove_stream(stream_id)
        data = stream.get_data_received()
        curr_time = time.time()
        self._stats_dict[stream_id]['total_time'] -= curr_time
        try:
            with open(f'{stream_id}.gif', 'wb') as file:
                file.write(data)
            return True
        except Exception as e:
            print(f"An error occurred in _write_stream: {e}")
            return False

    def _close_connection(self):
        """
        @brief Close the connection, socket, and print the statistics.
        """
        self._total_time -= time.time()
        self._idle = False
        self._socket.close()
        self._print_stats()

    def _print_stats(self):
        """
        @brief Print the statistics for all active streams in the connection.
        """
        self._total_time = abs(self._total_time)
        _bytes = 0
        for stream_id, stats in self._stats_dict.items():
            elapsed_time = abs(stats['total_time'])
            if elapsed_time > 0:
                total_bytes = stats['total_bytes']
                _bytes += total_bytes
                total_packets = len(stats['total_packets'])
                print(f'STREAM #{stream_id}:')
                print(f'---------------- {total_bytes} bytes total')
                print(f'---------------- {total_packets} packets total')
                print(f'---------------- at rate {float(total_bytes) / elapsed_time} bytes/second')
                print(f'---------------- at rate {float(total_packets) / elapsed_time} packets/second')
        print(f'Statistics for all active streams:')
        print(f'------- rate {float(_bytes) / self._total_time} bytes/second, {_bytes} bytes total')
        print(
            f'------- rate {float(self._received_packets_counter) / self._total_time} packets/second, {self._received_packets_counter} packets total')
        print(f'total time elapsed: {self._total_time} seconds')