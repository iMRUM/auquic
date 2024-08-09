import threading
from packet import Packet
from stream import StreamManager

class Connection:
    def __init__(self):
        """
        Initialize a Connection instance.
        """
        self.stream_manager = StreamManager()
        self.lock = threading.Lock()
        self.packet_size = 1000  # Fixed packet size in bytes

    def add_stream(self, stream_id, initiated_by, bidirectional=True):
        """
        Add a new stream to the connection.

        Args:
            stream_id (int): Unique identifier for the stream.
            initiated_by (str): Indicates whether the stream was initiated by 'client' or 'server'.
            bidirectional (bool): Indicates if the stream is bidirectional. Default is True.
        """
        self.stream_manager.create_stream(stream_id, initiated_by, bidirectional)

    def add_data_to_stream(self, stream_id, data):
        """
        Add data to a specific stream.

        Args:
            stream_id (int): Unique identifier for the stream.
            data (bytes): Data to be added to the stream.
        """
        self.stream_manager.add_data_to_stream(stream_id, data)

    def create_packet(self):
        """
        Create a packet containing frames from the streams.

        Returns:
            Packet: The created packet with frames from different streams.
        """
        with self.lock:
            packet = Packet()
            remaining_space = self.packet_size
            stream_ids = list(self.stream_manager.streams.keys())

            for stream_id in stream_ids:
                frame = self.stream_manager.get_next_frame(stream_id, remaining_space)
                if frame:
                    stream_id, chunk = frame
                    packet.add_frame(stream_id, chunk)
                    remaining_space -= len(chunk)
                    if remaining_space <= 0:
                        break

            return packet

    def send_packets(self):
        """
        Continuously create and send packets until all streams are exhausted.
        """
        while self.stream_manager.streams:
            packet = self.create_packet()
            if packet.frames:
                self.send_packet(packet)

    def send_packet(self, packet):
        """
        Placeholder for actual packet sending logic.

        Args:
            packet (Packet): The packet to send.
        """
        print(f"Sending packet with {len(packet.frames)} frames")

# Example usage
if __name__ == "__main__":
    conn = Connection()
    conn.add_stream(1, 'client', bidirectional=True)
    conn.add_data_to_stream(1, b"client initiated bidirectional stream data" * 10)
    conn.add_stream(2, 'server', bidirectional=False)
    conn.add_data_to_stream(2, b"server initiated unidirectional stream data" * 8)
    conn.add_stream(3, 'client', bidirectional=True)
    conn.add_data_to_stream(3, b"client initiated bidirectional stream data" * 6)

    sender_thread = threading.Thread(target=conn.send_packets)
    sender_thread.start()
    sender_thread.join()
