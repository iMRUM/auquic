import threading
from _frame import FrameStream


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
        self.sender = StreamSender(stream_id)
        self.receiver = StreamReceiver(stream_id)
        self.lock = threading.Lock()

    def write(self, data: bytes):  # sending part
        """
        Add data to the stream by delegation.

        Args:
            data (bytes): Data to be added to the stream.
        """
        self.sender.write_data(data)

    def end_stream(self):
        return self.sender.generate_fin_frame()

    def reset_stream(self):  # TODO
        pass

    def read(self) -> bytes:  # receiving part
        return self.receiver.read_data()

    def get_stream_frames_to_send(self, payload_size):
        """
        Retrieve a list of all frames required for the data, depends on size of the data and size of a packet..

        Args:
            payload_size (int): The size of the payload_size is determined by size of payload-packet/num of streams on that packet
                calculation will be in quic.py
        Returns:
             The retrieved list of all frames required for the data or a single fin frame.
            """
        with self.lock:
            stream_frames = self.sender.generate_stream_frames(payload_size)
        return stream_frames

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
            stream.write(data)

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
            chunk = stream.get_stream_frames_to_send(frame_size)
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
        self.stream_frames = []
        self.lock = threading.Lock()

    def write_data(self, data: bytes):
        if not self.fin_sent:
            with self.lock:
                self.send_buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is closed.")

    def generate_stream_frames(self, max_size: int) -> list[FrameStream]:  # max_size for frame(payload allocated)
        total_stream_frames = len(self.send_buffer) // max_size
        for i in range(total_stream_frames):
            self.stream_frames.append(
                FrameStream(stream_id=self.stream_id, offset=self.send_offset, length=max_size, fin=False,
                            data=self.send_buffer[self.send_offset:self.send_offset + max_size]))
            self.send_offset += max_size
        self.stream_frames.append(self.generate_fin_frame())
        return self.stream_frames

    def generate_fin_frame(self) -> FrameStream:
        return FrameStream(stream_id=self.stream_id, offset=self.send_offset,
                           length=len(self.send_buffer) - self.send_offset,
                           fin=True,
                           data=self.send_buffer[
                                self.send_offset:])  # last frame is the rest of the buffer with FIN bit

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

    def read_data(self) -> bytes:
        if self.is_ready:
            return self.recv_buffer
        else:
            raise ValueError("ERROR: cannot read. stream is closed.")

    def stream_frame_recvd(self, frame: FrameStream):
        if not self.recv_buffer_dict[frame.offset]:  # this frame wasn't already received
            self.recv_buffer_dict[frame.offset] = frame.data
            self.curr_offset += len(frame.data)
            self.recv_buffer_dict = dict(sorted(self.recv_buffer_dict.items()))  # sort existing frames by their offset
            if frame.fin:
                self._fin_recvd(frame)

    def _fin_recvd(self, frame: FrameStream):
        self.fin_recvd = True
        if self.curr_offset == frame.offset + len(frame.data):  # it is indeed the last frame
            self.is_ready = False
            self._convert_dict_to_buffer()

    def _generate_stop_sending_frame(self):  # will return STOP_SENDING frame
        return self

    def send_stop_sending_frame(self):  # TODO: finish according to 2.4
        frame = self._generate_stop_sending_frame()

    def _convert_dict_to_buffer(self):  # the dict is already sorted by offsets so just add them tandem
        for data in self.recv_buffer_dict.values():
            with self.lock:
                self.recv_buffer += data
