import time

from frame import FrameStream, FrameReset_Stream, FrameStop_Sending

READY = RECV = BIDIRECTIONAL = CLIENT_ID = 0
SEND = SIZE_KNOWN = UNIDIRECTIONAL = SERVER_ID = 1
DATA_SENT = DATA_READ = 2
DATA_RECVD = 3
RESET_SENT = RESET_READ = 4
RESET_RECVD = 5
FILE = 'a.txt'


class Stream:
    def __init__(self, stream_id):
        """
        Initialize a Stream instance.

        Args:
            stream_id (int): Unique identifier for the stream. 2MSB are 11(???), 62 usable bits, 8-bytes total."""
        self.stream_id = stream_id
        self._sender = StreamSender(stream_id)
        self._receiver = StreamReceiver(stream_id)
        self._total_bytes_recvd = 0

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

    def end_stream(self):
        return self._sender.generate_fin_frame()

    def reset_stream(self):  # TODO
        pass

    def receive_frame(self, frame: FrameStream):  # receiving part
        self._total_bytes_recvd += len(frame.encode())
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


class StreamSender:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-operations-on-streams

    """READY = 0
    SEND = 1
    DATA_SENT = 2
    DATA_RECVD = 3
    RESET_SENT = 4
    RESET_RECVD = 5"""

    def __init__(self, stream_id: int):
        self._stream_id = stream_id
        self._buffer_offset = 0
        self._send_buffer = b""
        self._state = READY
        self._stream_frames: list[FrameStream] = []

    def set_state(self, state: int):
        self._state = state

    def is_terminal_state(self) -> bool:
        return self._state == DATA_RECVD or self._state == RESET_RECVD

    def add_data_to_buffer(self, data: bytes):
        if self._state == READY:
            self._send_buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not Ready.")

    def generate_stream_frames(self, max_size: int):  # max_size for frame(payload allocated)
        total_stream_frames = len(self._send_buffer) // max_size
        for i in range(total_stream_frames):
            self._stream_frames.append(
                FrameStream(stream_id=self._stream_id, offset=self._buffer_offset, length=max_size, fin=False,
                            data=self._send_buffer[self._buffer_offset:self._buffer_offset + max_size]))
            self._buffer_offset += max_size
        self._stream_frames.append(self.generate_fin_frame())

    def generate_fin_frame(self) -> FrameStream:
        self._state = DATA_SENT
        return FrameStream(stream_id=self._stream_id, offset=self._buffer_offset,
                           length=len(self._send_buffer[self._buffer_offset:]),
                           fin=True,
                           data=self._send_buffer[
                                self._buffer_offset:])  # last frame is the rest of the buffer with FIN bit

    def generate_reset_stream_frame(self) -> FrameReset_Stream:
        if self._buffer_offset == 0:
            return FrameReset_Stream(stream_id=self._stream_id, application_protocol_error_code=1, final_size=0)
        return FrameReset_Stream(stream_id=self._stream_id, application_protocol_error_code=1,
                                 final_size=self._buffer_offset + 1)

    def send_next_frame(self) -> 'FrameStream':
        if self._stream_frames:
            frame = self._stream_frames.pop(0)
            self.set_state(SEND)
            if frame.fin:
                self._state = DATA_RECVD
            return frame


class StreamReceiver:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-operations-on-streams

    """RECV = 0
    SIZE_KNOWN = 1
    DATA_READ = 2
    DATA_RECVD = 3
    RESET_READ = 4
    RESET_RECVD = 5"""

    def __init__(self, stream_id: int):
        self._stream_id: int = stream_id
        self._curr_offset: int = 0
        self._recv_buffer: bytes = b""
        self._state: int = RECV
        self._recv_frame_dict: dict[int:bytes] = {}  # such that K = offset, V = data

    def _set_state(self, state: int) -> bool:
        try:
            self._state = state
            return True
        except Exception as e:
            print(f'ERROR: Cannot set state to {state}. {e}')
            return False

    def is_terminal_state(self) -> bool:
        return self._state == DATA_RECVD or self._state == RESET_RECVD

    def stream_frame_recvd(self, frame: FrameStream):
        if frame.fin:
            self._fin_recvd(frame)
        self._add_frame_to_recv_dict(frame)

    def _add_frame_to_recv_dict(self, frame: FrameStream):
        self._recv_frame_dict[frame.offset] = frame.data
        self._curr_offset += len(frame.data)
        if self._state == SIZE_KNOWN:
            self._convert_dict_to_buffer()

    def _fin_recvd(self, frame: FrameStream):
        self._set_state(SIZE_KNOWN)

    def _generate_stop_sending_frame(self) -> FrameStop_Sending:  # will return STOP_SENDING frame
        return FrameStop_Sending(stream_id=self._stream_id, application_protocol_error_code=1)

    def send_stop_sending_frame(self):  # TODO: finish according to 2.4
        frame = self._generate_stop_sending_frame()

    def _convert_dict_to_buffer(self):  # sort the dict according to their offset and add to the buffer tandem
        self._recv_frame_dict = dict(sorted(self._recv_frame_dict.items()))  # sort existing frames by their offset
        for data in self._recv_frame_dict.values():
            self._recv_buffer += data
        self._set_state(DATA_RECVD)

    def get_data_from_buffer(self) -> bytes:

        if self._state == DATA_RECVD:
            try:
                return self._recv_buffer
            finally:
                self._set_state(DATA_READ)
        else:
            raise ValueError("ERROR: cannot read. stream is closed.")
