import threading
from frame import StreamFrame


class Stream:
    def __init__(self, stream_id, initiated_by, direction):
        """
        Initialize a Stream instance.

        Args:
            stream_id (int): Unique identifier for the stream. 2MSB are 11, 62 usable bits, 8-bytes total.
            initiated_by (int): Indicates whether the stream was initiated by client(0) or server(1).
            direction (int): Indicates if the stream is bidirectional(0) or unidirectional(1)
        """
        self.stream_id = stream_id
        self.initiated_by = initiated_by  # 'client' or 'server'
        self.direction = direction
        self.data = b""
        self.offset = 0
        self.lock = threading.Lock()

    def add_data(self, data: bytes):  # user-initiated
        """
        Add data to the stream.

        Args:
            data (bytes): Data to be added to the stream.
        """
        with self.lock:
            self.data += data

    def get_chunk(self, size):  # quic-initiated, size is determined by size of packet/num of streams
        """
        Retrieve a chunk of data from the stream.

        Args:
            size (int): The size of the chunk to retrieve.

        Returns:
            bytes: The retrieved chunk of data.
        """
        with self.lock:
            chunk = self.data[self.offset:self.offset + size]
            self.offset += len(chunk)
            return chunk

    def is_finished(self):
        """
        Check if the stream has finished transmitting data.

        Returns:
            bool: True if the stream has no more data to transmit, False otherwise.
        """
        with self.lock:
            return self.offset >= len(self.data)

    def reset(self):
        """
        Reset the stream data and offset.
        """
        with self.lock:
            self.data = b""
            self.offset = 0


class StreamManager:
    def __init__(self):
        """
        Initialize a StreamManager instance.
        """
        self.streams = {}
        self.lock = threading.Lock()

    def create_stream(self, stream_id, initiated_by, direction):
        """
        Create a new stream.

        Args:
            stream_id (int): Unique identifier for the stream.
            initiated_by (int): Indicates whether the stream was initiated by 'client' or 'server'.
            direction (int): Indicates if the stream is bidirectional. Default is True.

        Returns:
            Stream: The created stream instance.
        """
        with self.lock:
            if stream_id not in self.streams:
                self.streams[stream_id] = Stream(stream_id, initiated_by, direction)
            return self.streams[stream_id]

    def get_stream(self, stream_id):
        """
        Retrieve a stream by its identifier.

        Args:
            stream_id (int): Unique identifier for the stream.

        Returns:
            Stream: The retrieved stream instance or None if not found.
        """
        with self.lock:
            return self.streams.get(stream_id, None)

    def add_data_to_stream(self, stream_id, data):
        """
        Add data to a specific stream.

        Args:
            stream_id (int): Unique identifier for the stream.
            data (bytes): Data to be added to the stream.
        """
        stream = self.get_stream(stream_id)
        if stream:
            stream.add_data(data)

    def get_next_frame(self, stream_id, frame_size):
        """
        Retrieve the next frame of data from a specific stream.

        Args:
            stream_id (int): Unique identifier for the stream.
            frame_size (int): The size of the frame to retrieve.

        Returns:
            tuple: A tuple containing the stream ID and the retrieved frame data.
        """
        stream = self.get_stream(stream_id)
        if stream and not stream.is_finished():
            chunk = stream.get_chunk(frame_size)
            if chunk:
                return (stream_id, chunk)
        return None

    def reset_stream(self, stream_id):
        """
        Reset a specific stream.

        Args:
            stream_id (int): Unique identifier for the stream.
        """
        stream = self.get_stream(stream_id)
        if stream:
            stream.reset()


class StreamSender:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-operations-on-streams
    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.send_offset = 0
        self.send_buffer = b""
        self.fin_sent = False
        self.is_ready = True
        self.lock = threading.Lock()

    def write_data(self, data: bytes):
        if not self.fin_sent:
            with self.lock:
                self.send_buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is closed.")

    def generate_stream_frames(self, max_size: int) -> list[StreamFrame]:  # max_size of a packet-payload allocated
        stream_frames = []
        total_stream_frames = len(self.send_buffer) // max_size
        for i in range(total_stream_frames):
            stream_frames.append(
                StreamFrame(stream_id=self.stream_id, offset=self.send_offset, length=max_size, fin=False,
                            data=self.send_buffer[self.send_offset:self.send_offset + max_size]))
            self.send_offset += max_size
        stream_frames.append(
            StreamFrame(stream_id=self.stream_id, offset=self.send_offset, length=len(self.send_buffer),
                        fin=True,
                        data=self.send_buffer[self.send_offset:]))  # last frame is the rest of the buffer with FIN bit
        return stream_frames

    def sent_fin(self):
        self.fin_sent = True
        self.is_ready = False


class StreamReceiver:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-operations-on-streams
    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.curr_offset = 0
        self.recv_buffer_dict = {}  # such that K = offset, V = data
        self.recv_buffer = b""
        self.fin_recvd = False
        self.is_ready = True
        self.lock = threading.Lock()

    def stream_frame_recvd(self, frame: StreamFrame):
        if not self.recv_buffer_dict[frame.offset]:  # this frame wasn't already received
            self.recv_buffer_dict[frame.offset] = frame.data
            self.curr_offset += len(frame.data)
            self.recv_buffer_dict = dict(sorted(self.recv_buffer_dict.items()))  # sort existing frames by their offset
            if frame.fin:
                self._fin_recvd(frame)

    def _fin_recvd(self, frame: StreamFrame):
        self.fin_recvd = True
        if self.curr_offset == frame.offset + len(frame.data):  # it is indeed the last frame
            self.is_ready = False
            self._convert_dict_to_buffer()

    def _convert_dict_to_buffer(self):  # the dict is already sorted by offsets so just add the tandem
        for data in self.recv_buffer_dict.values():
            with self.lock:
                self.recv_buffer += data

