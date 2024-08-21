import threading
import socket
import random
from packet import Packet, PacketHeader
from stream import Stream
from sys import getsizeof

PACKET_SIZE = 1024
CONNECTION_ID = 256


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
        self.lock = threading.Lock()
        self._pending_packets = []
        self._packets_counter = 0
        self._pending_frames = []
        self._retrieved_packets = []

    def add_stream(self, initiated_by, direction):
        """
        Add a new stream to the connection.

        Args:
            stream_id (int): Unique identifier for the stream.
            initiated_by (int): Indicates whether the stream was initiated by 'client'(0) or 'server'(1).
            direction (int): Indicates if the stream is bidirectional(0) or unidirectional(1).
        """
        with self.lock:
            stream_id = self._stream_id_generator(initiated_by, direction)
            if not self._is_stream_in_dict(stream_id):
                self.streams[stream_id] = Stream(stream_id, initiated_by, direction)
                self._streams_counter += 1

        print(f"Stream: {stream_id} was added successfully.")

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
        if self._is_stream_in_dict(stream_id):
            self.streams[stream_id].write(data=data)

    def _generate_streams_frames(self):
        with self.lock:
            for stream in list(self.streams.values()):
                stream.generate_stream_frames(max_size=PACKET_SIZE // 5)

    def _get_random_stream_from_streams(self):
        return random.choice(list(self.streams.values()))

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
        with self.lock:
            packet_header = PacketHeader(
                (self._packets_counter - 1).bit_length())  # as of rfc9000.html#name-1-rtt-packet
            remaining_space = PACKET_SIZE
            # p = Packet(packet_header, CONNECTION_ID, self._packets_counter)
            if packet := Packet(packet_header, CONNECTION_ID, self._packets_counter):
                remaining_space -= getsizeof(packet)
                for i in range(5):  # arbitrary amount of iterations
                    if stream := self._get_random_stream_from_streams():
                        if frame := stream.send_next_frame():
                            size_of_frame = getsizeof(frame)
                            if size_of_frame <= remaining_space:
                                packet.add_frame(frame)
                                remaining_space -= size_of_frame
                            else:
                                self._pending_frames.append(frame)
                return packet
            else:
                raise ValueError("Packet couldn't be created")

    def _is_stream_in_dict(self, stream_id: int) -> bool:
        return stream_id in self.streams.keys()

    def send_packets(self):
        """
        Continuously create and send packets until all streams are done.
        """
        while self.streams:
            packet = self.create_packet()
            if not getsizeof(packet.payload) == getsizeof(b''):
                self.send_packet(packet)

    def send_packet(self, packet: Packet):
        with self.lock:
            if self.socket.sendto(packet.pack(), self.remote_addr):
                print(f"Sending packet {packet}")

    def receive_packets(self):
        while self.socket.fileno() >= 0:  # while socket is not closed
            self.receive_packet()

    def receive_packet(self):
        with self.lock:
            packet, addr = self.socket.recvfrom(PACKET_SIZE)
            if packet:
                self.handle_received_packet(packet)

    def handle_received_packet(self, packet: bytes):
        unpacked_packet = Packet.unpack(packet)
        frames_in_packet_dict = unpacked_packet.get_payload_frames_dict()
        for stream_id in frames_in_packet_dict.keys():
            if self._is_stream_in_dict(stream_id):
                self.streams[stream_id].receive_frame(frames_in_packet_dict.get(stream_id))


# Example usage
if __name__ == "__main__":
    pass
