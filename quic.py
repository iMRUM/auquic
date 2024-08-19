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
        self.streams = {}
        self.lock = threading.Lock()
        self._pending_packets = []
        self._packets_counter = 0
        self._pending_frames = []
        self._retrieved_packets = []

    def add_stream(self, stream_id, initiated_by, direction):
        """
        Add a new stream to the connection.

        Args:
            stream_id (int): Unique identifier for the stream.
            initiated_by (int): Indicates whether the stream was initiated by 'client' or 'server'.
            direction (int): Indicates if the stream is bidirectional. Default is True.
        """
        with self.lock:
            if not self._is_stream_in_dict(stream_id):
                self.streams[stream_id] = Stream(stream_id, initiated_by, direction)

        print(f"Stream: {stream_id} was added successfully.")

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
        for stream in list(self.streams.keys()):
            with self.lock:
                stream.generate_stream_frames(max_size=PACKET_SIZE // 5)

    def _get_random_stream_from_streams(self):
        return random.choice(list(self.streams.keys()))

    def create_packet(self):
        """
        Create a packet containing frames from the streams.
        1. generate frames for each stream
        2. assemble SOME of them and add to packet payload
        3. add packet to pending packets
        TODO: REMOVE ANY STREAM_MANAGER REFERENCE
        Returns:
            Packet: The created packet with frames from different streams.
        """
        self._generate_streams_frames()
        with self.lock:
            packet_header = PacketHeader(getsizeof(self._packets_counter) - 1)  # as of rfc9000.html#name-1-rtt-packet
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

    def _is_stream_in_dict(self, stream_id: int):
        return stream_id in self.streams

    def send_packets(self):
        """
        Continuously create and send packets until all streams are exhausted.
        """
        while self.streams:
            packet = self.create_packet()
            if not getsizeof(packet.payload) == getsizeof(b''):
                self.send_packet(packet)

    def send_packet(self, packet):
        with self.lock:
            if self.socket.sendto(packet, self.remote_addr):
                print(f"Sending packet {packet} with {len(packet.frames)} frames")

    def receive_packets(self):
        while self.socket.fileno() >= 0: # while socket is not closed
            self.receive_packet()

    def receive_packet(self):
        with self.lock:
            packet, addr= self.socket.recvfrom(PACKET_SIZE)
            if packet:
                self.handle_received_packet(packet)

    def handle_received_packet(self, packet: bytes):
        unpacked_packet = Packet.unpack(packet)
        packed_payload = unpacked_packet.payload

# Example usage
if __name__ == "__main__":
    conn = QuicConnection()
    conn.add_stream(1, 'client', direction=True)
    conn.add_data_to_stream(1, b"client initiated bidirectional stream data" * 10)
    conn.add_stream(2, 'server', direction=False)
    conn.add_data_to_stream(2, b"server initiated unidirectional stream data" * 8)
    conn.add_stream(3, 'client', direction=True)
    conn.add_data_to_stream(3, b"client initiated bidirectional stream data" * 6)

    sender_thread = threading.Thread(target=conn.send_packets)
    sender_thread.start()
    sender_thread.join()
