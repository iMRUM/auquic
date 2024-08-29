import socket
import time
import random
from sys import getsizeof

from constants import Constants
from frame import FrameStream
from packet import Packet
from stream import Stream

PACKET_SIZE = random.randint(Constants.MIN_PACKET_SIZE, Constants.MAX_PACKET_SIZE)


class QuicConnection:
    def __init__(self, connection_id: int, local_addr: tuple, remote_addr: tuple):
        """
        Initialize a Connection instance.
        We will use connection_id 0 for client and 1 for server
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

    def get_stream(self, initiated_by, direction) -> 'Stream':
        """
        Add a new stream to the connection.

        Args:
            initiated_by (int): Indicates whether the stream was initiated by 'client'(0) or 'server'(1).
            direction (int): Indicates if the stream is bidirectional(0) or unidirectional(1).
        """
        stream_id = self._stream_id_generator(initiated_by, direction)
        if not self._is_stream_id_in_dict(stream_id):
            self._add_stream(stream_id, bool(initiated_by), bool(direction))
        return self._get_stream_by_id(stream_id)

    def _stream_id_generator(self, initiated_by, direction):  # 62-bit
        str_binary = bin(self._streams_counter)[Constants.TWO:]  # convert to binary string without prefix (index=2)
        str_binary += str(direction) + str(initiated_by)
        padded_int = int(str_binary, Constants.BASE_TWO)
        return padded_int

    def _add_stream(self, stream_id: int, initiated_by: bool, direction: bool):
        self._streams[stream_id] = Stream(stream_id, initiated_by, direction)
        self._add_stream_to_stats_dict(stream_id)
        self._streams_counter += Constants.ONE

    def _add_stream_to_stats_dict(self, stream_id: int):
        self._stats_dict[stream_id] = {'total_bytes': Constants.ZERO, 'total_time': time.time(), 'total_packets': set()}

    def _get_stream_by_id(self, stream_id: int):
        if not self._is_stream_id_in_dict(stream_id):
            self._add_stream(stream_id, Stream.is_s_init_by_sid(stream_id), Stream.is_uni_by_sid(stream_id))
        return self._streams[stream_id]

    def _remove_stream(self, stream_id: int):
        self._active_streams_ids.remove(stream_id)
        return self._streams.pop(stream_id)

    def add_file_to_stream(self, stream_id: int, path: str):
        with open(path, 'rb') as file:
            data = file.read()
        self._add_data_to_stream(stream_id, data)

    def _add_data_to_stream(self, stream_id: int, data: bytes):
        """
        Add data to a specific stream.

        Args:
            stream_id (int): Unique identifier for the stream.
            data (bytes): Data to be added to the stream.
        """
        stream = self._get_stream_by_id(stream_id)
        stream.add_data_to_stream(data=data)
        self._add_active_stream_id(stream_id)

    def _add_active_stream_id(self, stream_id: int):
        if stream_id not in self._active_streams_ids:
            self._active_streams_ids.append(stream_id)

    def _is_stream_id_in_dict(self, stream_id: int) -> bool:
        return stream_id in self._streams.keys()

    def _set_start_time(self):
        start_time = time.time()
        for stream in self._stats_dict.values():
            stream['total_time'] = start_time

    def send_packets(self):
        """
        Continuously create and send packets until all streams are done.
        """
        self._send_packet_size()
        start_time = time.time()
        for stream in self._stats_dict.values():
            stream['total_time'] = start_time
        while self._active_streams_ids:
            packet = self._create_packet()
            self._send_packet(packet)
        self._close_connection()
        print('closing connection')

    def _send_packet_size(self):
        self._packet_size = PACKET_SIZE
        packet_size_bytes = self._packet_size.to_bytes(Constants.PACKET_SIZE_BYTES, 'big')
        if self._socket.sendto(packet_size_bytes, self._remote_addr):
            print(f'Sent Packet Size {self._packet_size}')
            return True
        return False

    def _create_packet(self):
        """
        Create a packet containing frames from the streams.
        1. generate frames for each stream
        2. assemble SOME of them and add to packet payload
        3. add packet to pending packets
        Returns:
            Packet: The created packet with frames from different streams.
        """
        self._generate_streams_frames()
        remaining_space = PACKET_SIZE
        if packet := Packet(int(not self._connection_id), self._sent_packets_counter):
            remaining_space -= getsizeof(packet)
            while remaining_space > Constants.ZERO:
                if self._pending_frames:
                    frame = self._pending_frames.pop(Constants.START)
                else:
                    if stream := self._get_stream_from_active_streams():
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
                    remaining_space = Constants.ZERO
            self._sent_packets_counter += Constants.ONE
            return packet
        else:
            raise ValueError("Packet couldn't be created")

    def _generate_streams_frames(self):
        for stream_id in self._active_streams_ids:
            self._get_stream_by_id(stream_id).generate_stream_frames(PACKET_SIZE // Constants.FRAMES_IN_PACKET)

    def _get_stream_from_active_streams(self):
        if not self._active_streams_ids:
            self._idle = False
            return
        try:
            return self._streams[random.choice(self._active_streams_ids)]  # return the first stream to be activated
        except IndexError:
            print("No more streams!")

    def _send_packet(self, packet: Packet):
        if self._socket.sendto(packet.pack(), self._remote_addr):
            pass

    def receive_packets(self):

        self._socket.settimeout(Constants.TIMEOUT)  # 60-second timeout
        while self._idle:
            try:
                self._receive_packet()
            except OSError as e:
                print(f"An error occurred receive_packets: {e}")
                break

    def _receive_packet(self):
        try:
            if self._packet_size == Constants.ZERO:
                packet, addr = self._socket.recvfrom(Constants.PACKET_SIZE_BYTES)
                self._handle_received_packet_size(packet)
            else:
                packet, addr = self._socket.recvfrom(self._packet_size)
                self._handle_received_packet(packet)
        except socket.timeout:
            self._close_connection()

    def _handle_received_packet_size(self, packet_size: bytes):
        self._packet_size = int.from_bytes(packet_size, 'big')
        print(f'RECEIVED Packet Size {self._packet_size}')

    def _handle_received_packet(self, packet: bytes):
        self._received_packets_counter += Constants.ONE
        self._total_time = time.time()
        unpacked_packet = Packet.unpack(packet)
        frames_in_packet = unpacked_packet.payload
        for frame in frames_in_packet:
            stream_id = frame.stream_id
            self._add_active_stream_id(stream_id)
            try:
                self._get_stream_by_id(stream_id).receive_frame(frame)
                self._stats_dict[stream_id]['total_bytes'] += len(frame.encode())
                self._stats_dict[stream_id]['total_packets'].add(unpacked_packet.packet_number)
                # self.streams_packets_dict[stream_id].add(unpacked_packet.packet_number)
                if self._get_stream_by_id(stream_id).is_finished():
                    self._write_stream(stream_id)
            except Exception as e:
                print(f"An error occurred handle_received_packet: {e}")

    def _write_stream(self, stream_id: int):
        stream = self._remove_stream(stream_id)
        data = stream.get_data_received()
        curr_time = time.time()
        self._stats_dict[stream_id]['total_time'] -= curr_time
        try:
            with open(f'{stream_id}.gif', 'wb') as file:
                file.write(data)

            return True
        except Exception as e:
            print(f"An error occurred write_stream: {e}")
            return False

    def _close_connection(self):
        self._idle = False
        self._socket.close()
        self._print_stats()

    def _print_stats(self):
        _bytes = 0
        _elapsed_time = time.time() - self._total_time
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
                print(
                    f'---------------- at rate {float(total_packets) / elapsed_time} packets/second')
        print(f'Statistics for all active streams:')
        print(f'------- rate {float(_bytes) / _elapsed_time} bytes/second, {_bytes} bytes total')
        print(
            f'---------------- rate {float(self._received_packets_counter) / _elapsed_time} packets/second, {self._received_packets_counter} packets total')


# Example usage
if __name__ == "__main__":
    pass
