from abc import ABC, abstractmethod

from frame import FrameStream

INIT_BY = 0x01
DIRECTION = 0x02
READY = RECV = BIDIRECTIONAL = CLIENT_ID = 0
ONE = SEND = SIZE_KNOWN = UNIDIRECTIONAL = SERVER_ID = 1
TWO = DATA_SENT = DATA_READ = 2
DATA_RECVD = 3
RESET_SENT = RESET_READ = 4
RESET_RECVD = 5
FILE = 'a.txt'


class Stream:
    def __init__(self, stream_id, is_uni: bool, is_s_initiated: bool):
        """
        Initialize a Stream instance.

        Args:
            stream_id (int): Unique identifier for the stream. 2MSB are 11(???), 62 usable bits, 8-bytes total."""
        self._stream_id = stream_id
        self._is_uni = is_uni
        self._is_s_initiated = is_s_initiated
        self._sender = StreamSender(stream_id)
        self._receiver = StreamReceiver(stream_id)

    def has_data(self) -> bool:
        return self._sender.has_data() or self._receiver.has_data()

    def get_stream_id(self):
        return self._stream_id

    def add_data_to_stream(self, data: bytes):  # sending part
        """
        Add data to the stream by delegation.

        Args:
            data (bytes): Data to be added to the stream.
        """
        self._sender.add_data_to_buffer(data)

    def generate_stream_frames(self, max_size: int):
        """
       Retrieve a list of all frames required for the data, depends on size of the data and size of a packet.

       Args: max_size (int): The size of the payload_size is determined by size of payload-packet/num of streams on
       that packet. calculation will be in quic.py

        Delegates stream frames generation to StreamSender"""
        self._sender.generate_stream_frames(max_size)

    def send_next_frame(self) -> 'FrameStream':
        """Delegates next frame sending to StreamSender"""
        return self._sender.send_next_frame()

    def receive_frame(self, frame: FrameStream):  # receiving part
        self._receiver.stream_frame_recvd(frame)

    def get_data_received(self) -> bytes:
        return self._receiver.get_data_from_buffer()

    def is_finished(self) -> bool:
        """
        Check if the stream has finished transmitting data.

        Returns:
            bool: True if the stream has no more data to transmit, False otherwise.
        """
        return self._receiver.is_terminal_state() or self._sender.is_terminal_state()

    @staticmethod
    def is_uni_by_sid(stream_id: int) -> bool:  # bidi for bidirectional
        return bool(stream_id & DIRECTION)

    @staticmethod
    def is_s_init_by_sid(stream_id: int) -> bool:  # s for server
        return bool(stream_id & INIT_BY)


class StreamEndpointABC(ABC):
    def __init__(self, stream_id: int):
        self._stream_id: int = stream_id
        self._curr_offset: int = 0
        self._buffer: bytes = b""
        self._state: int = READY  # READY = RECV so it applies for both endpoints

    def _set_state(self, state: int):
        try:
            self._state = state
            return True
        except Exception as e:
            print(f'ERROR: Cannot set state to {state}. {e}')
            return False

    @abstractmethod
    def _add_data_to_buffer(self, data: bytes):
        pass

    def has_data(self) -> bool:
        return bool(self._buffer)

    def is_terminal_state(self) -> bool:
        return self._state == DATA_RECVD or self._state == RESET_RECVD


class StreamSender(StreamEndpointABC):  # according to rfc9000.html#name-operations-on-streams

    """READY = 0
    SEND = 1
    DATA_SENT = 2
    DATA_RECVD = 3
    RESET_SENT = 4
    RESET_RECVD = 5"""

    def __init__(self, stream_id: int):
        super().__init__(stream_id)
        self._stream_frames: list[FrameStream] = []

    def add_data_to_buffer(self, data: bytes):
        self._add_data_to_buffer(data)

    def _add_data_to_buffer(self, data: bytes):
        if self._state == READY:
            self._buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not READY.")

    def generate_stream_frames(self, max_size: int):  # max_size for frame(payload allocated)
        total_stream_frames = self._get_total_stream_frames_amount(max_size)
        if total_stream_frames > ONE:
            for i in range(total_stream_frames):
                self._stream_frames.append(
                    FrameStream(stream_id=self._stream_id, offset=self._curr_offset, length=max_size, fin=False,
                                data=self._buffer[self._curr_offset:self._curr_offset + max_size]))
                self._curr_offset += max_size
        self._stream_frames.append(self.generate_fin_frame())

    def _get_total_stream_frames_amount(self, max_size: int) -> int:
        if len(self._buffer) < max_size:
            return ONE
        else:
            return len(self._buffer) // max_size

    def generate_fin_frame(self) -> FrameStream:
        self._set_state(DATA_SENT)
        return FrameStream(stream_id=self._stream_id, offset=self._curr_offset,
                           length=len(self._buffer[self._curr_offset:]),
                           fin=True,
                           data=self._buffer[
                                self._curr_offset:])  # last frame is the rest of the buffer with FIN bit

    def send_next_frame(self) -> 'FrameStream':
        if self._stream_frames:
            frame = self._stream_frames.pop(0)
            self._set_state(SEND)
            if frame.fin:
                self._set_state(DATA_RECVD)
            return frame


class StreamReceiver(StreamEndpointABC):  # according to www.rfc-editor.org/rfc/rfc9000.html#name-operations-on-streams

    """RECV = 0
    SIZE_KNOWN = 1
    DATA_READ = 2
    DATA_RECVD = 3
    RESET_READ = 4
    RESET_RECVD = 5"""

    def __init__(self, stream_id: int):
        super().__init__(stream_id)
        self._recv_frame_dict: dict[int:bytes] = {}  # such that K = offset, V = data

    def stream_frame_recvd(self, frame: FrameStream):
        if frame.fin:
            self._fin_recvd()
        self._add_frame_to_recv_dict(frame)

    def _add_frame_to_recv_dict(self, frame: FrameStream):
        self._recv_frame_dict[frame.offset] = frame.data
        self._curr_offset += len(frame.data)
        if self._state == SIZE_KNOWN:
            self._convert_dict_to_buffer()

    def _fin_recvd(self):
        self._set_state(SIZE_KNOWN)

    def _convert_dict_to_buffer(self):  # sort the dict according to their offset and add to the buffer tandem
        self._recv_frame_dict = dict(sorted(self._recv_frame_dict.items()))  # sort existing frames by their offset
        for data in self._recv_frame_dict.values():
            self._add_data_to_buffer(data)
        self._set_state(DATA_RECVD)

    def _add_data_to_buffer(self, data: bytes):
        if self._state == SIZE_KNOWN:
            self._buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not READY.")

    def get_data_from_buffer(self) -> bytes:

        if self._state == DATA_RECVD:
            try:
                return self._buffer
            finally:
                self._set_state(DATA_READ)
        else:
            raise ValueError("ERROR: cannot read. stream is closed.")
