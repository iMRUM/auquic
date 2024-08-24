import threading
import socket
import random
import time
from typing import Optional

from packet import Packet, PacketHeader
from stream import Stream
from sys import getsizeof
from _frame import FrameStream

PACKET_SIZE = 1024


class QuicConnection:
    def __init__(self, connection_id: int, local_addr: tuple, remote_addr: tuple):
        """
        Initialize a Connection instance.
        We will use connection_id 0 for client and 1 for server
        """
        self.connection_id = connection_id
        self.local_addr = local_addr
        self.remote_addr = remote_addr
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(local_addr)
        self.streams: dict[int, Stream] = {}
        self._streams_counter = 0
        self._pending_packets = []
        self._packets_counter = 0
        self._pending_frames: list['FrameStream'] = []
        self._retrieved_packets = []

    def close_connection(self):
        self.socket.close()
        print("socket is closed")

    def get_stream(self, initiated_by, direction) -> 'Stream':
        """
        Add a new stream to the connection.

        Args:
            initiated_by (int): Indicates whether the stream was initiated by 'client'(0) or 'server'(1).
            direction (int): Indicates if the stream is bidirectional(0) or unidirectional(1).
        """
        stream_id = self._stream_id_generator(initiated_by, direction)
        return self._get_stream_by_id(stream_id)

    def _get_stream_by_id(self, stream_id):
        if not self._is_stream_id_in_dict(stream_id):
            self.streams[stream_id] = Stream(stream_id)
            self._streams_counter += 1
        print(f"Stream: {stream_id} was added successfully.")
        return self.streams[stream_id]

    def _stream_id_generator(self, initiated_by, direction):  # 62-bit
        str_binary = bin(self._streams_counter)[2:]  # convert to binary string without prefix
        str_binary += str(direction) + str(initiated_by)
        padded_int = int(str_binary, 2)
        return padded_int

    def add_data_to_stream(self, stream_id, data):
        """
        Add data to a specific stream.

        Args:
            stream_id (int): Unique identifier for the stream.
            data (bytes): Data to be added to the stream.
        """
        if self._is_stream_id_in_dict(stream_id):
            self.streams[stream_id].add_data_to_stream(data=data)
        else:
            raise ValueError("ERROR: STREAM WAS NOT FOUND")

    def _generate_streams_frames(self):
        for stream in list(self.streams.values()):
            stream.generate_stream_frames(max_size=PACKET_SIZE // 5)

    def _get_random_stream_from_streams(self) -> 'Stream':
        try:
            return random.choice(list(self.streams.values()))
        except IndexError:
            print("No more streams!")

    def create_packet2(self):
        self._generate_streams_frames()

    def create_packet(self):
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
        if packet := Packet(int(not self.connection_id), self._packets_counter):
            remaining_space -= getsizeof(packet)
            while remaining_space > 0:
                if self._pending_frames:
                    frame = self._pending_frames.pop(0)
                else:
                    if stream := self._get_random_stream_from_streams():
                        frame = stream.send_next_frame()
                        if stream.is_finished():
                            print(f"{self.streams.pop(stream.stream_id)} was popped!")
                    else:
                        break
                size_of_frame = getsizeof(frame.encode())
                if size_of_frame <= remaining_space:
                    packet.add_frame(frame)
                    remaining_space -= size_of_frame
                else:
                    self._pending_frames.append(frame)
                    remaining_space = 0
                self._packets_counter += 1
                return packet
            else:
                raise ValueError("Packet couldn't be created")

    def _is_stream_id_in_dict(self, stream_id: int) -> bool:
        return stream_id in self.streams.keys()

    def send_packets(self):
        """
        Continuously create and send packets until all streams are done.
        """
        while self.streams:
            packet = self.create_packet()
            if not getsizeof(packet.payload) == getsizeof(b''):
                self.send_packet(packet)
        self.close_connection()
        print('closing connection')

    def send_packet(self, packet: Packet):
        if self.socket.sendto(packet.pack(), self.remote_addr):
            print(f"Sending packet {packet}")

    def receive_packets(self):
        self.socket.settimeout(10)  # 60-second timeout
        while self.socket.fileno():
            try:
                self._receive_packets()
            except OSError as e:
                print(f"An error occurred receive_packets: {e}")
                break
        print('OUT')

    def _receive_packets(self):
        try:
            packet, addr = self.socket.recvfrom(PACKET_SIZE)
            # print(':L148: packet is true')
            self.handle_received_packet(packet)
            # print('receive_packet')
        except socket.timeout:
            print("TIMEOUT")

    def handle_received_packet(self, packet: bytes):
        unpacked_packet = Packet.unpack(packet)
        print(f':L154: unpacked_packet: {unpacked_packet}')
        frames_in_packet = unpacked_packet.payload
        for frame in frames_in_packet:
            stream_id = frame.stream_id
            try:
                self._get_stream_by_id(stream_id).receive_frame(frame)
                if self._get_stream_by_id(stream_id).is_finished():
                    self.write_stream(stream_id)
            except Exception as e:
                print(f"An error occurred handle_received_packet: {e}")

    def write_stream(self, stream_id: int):
        # print(f'writing stream{stream.stream_id}')
        stream = self.streams.pop(stream_id)
        data = stream.get_data_received()
        try:
            with open(f'{stream_id}', 'wb') as file:
                file.write(data)
            return True
        except Exception as e:
            print(f"An error occurred write_stream: {e}")
            return False

    @staticmethod
    def read_file(path):
        with open(path, 'rb') as file:
            data = file.read()
        file.close()
        return data


# Example usage
if __name__ == "__main__":
    pass
