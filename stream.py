import threading
from typing import Optional

from _frame import FrameStream, FrameReset_Stream, FrameStop_Sending

READY = RECV = 0
SEND = SIZE_KNOWN = 1
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

    def generate_stream_frames(self, max_size: int):
        """
       Retrieve a list of all frames required for the data, depends on size of the data and size of a packet.

       Args: max_size (int): The size of the payload_size is determined by size of payload-packet/num of streams on
       that packet calculation will be in quic.py

        Delegates stream frames generation to StreamSender"""
        self.sender.generate_stream_frames(max_size)

    def send_next_frame(self):
        """Delegates next frame sending to StreamSender"""
        return self.sender.send_next_frame()

    def end_stream(self):
        return self.sender.generate_fin_frame()

    def reset_stream(self):  # TODO
        pass

    def read(self) -> bytes:  # receiving part
        return self.receiver.read_data()

    def receive_frame(self, frame):
        print("processing received frame")
        self.receiver.stream_frame_recvd(frame)

    def is_finished(self):
        """
        Check if the stream has finished transmitting data.

        Returns:
            bool: True if the stream has no more data to transmit, False otherwise.
        """
        pass


class StreamSender:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-operations-on-streams

    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.send_offset = 0
        self.send_buffer = b""
        self.fin_sent = False
        self._state = READY
        self.stream_frames: list[FrameStream] = []
        self.lock = threading.Lock()

    def is_ready_state(self) -> bool:
        return self._state == READY

    def is_data_sent_state(self) -> bool:
        return self._state == DATA_SENT

    def write_data(self, data: bytes):
        if self._state == READY:
            with self.lock:
                self.send_buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not Ready.")

    def generate_stream_frames(self, max_size: int):  # max_size for frame(payload allocated)
        total_stream_frames = len(self.send_buffer) // max_size
        for i in range(total_stream_frames):
            self.stream_frames.append(
                FrameStream(stream_id=self.stream_id, offset=self.send_offset, length=max_size, fin=False,
                            data=self.send_buffer[self.send_offset:self.send_offset + max_size]))
            self.send_offset += max_size
        self.stream_frames.append(self.generate_fin_frame())

    def generate_fin_frame(self) -> FrameStream:
        self._state = DATA_SENT
        return FrameStream(stream_id=self.stream_id, offset=self.send_offset,
                           length=len(self.send_buffer[self.send_offset:]),
                           fin=True,
                           data=self.send_buffer[
                                self.send_offset:])  # last frame is the rest of the buffer with FIN bit

    def generate_reset_stream_frame(self) -> FrameReset_Stream:
        if self.send_offset == 0:
            return FrameReset_Stream(stream_id=self.stream_id, application_protocol_error_code=1, final_size=0)
        return FrameReset_Stream(stream_id=self.stream_id, application_protocol_error_code=1,
                                 final_size=self.send_offset + 1)

    def send_next_frame(self) -> 'FrameStream':
        with self.lock:
            self._state = SEND
        if self.stream_frames:
            frame = self.stream_frames.pop(0)
            if frame.fin:
                with self.lock:
                    self._state = DATA_SENT
            return frame


class StreamReceiver:  # according to https://www.rfc-editor.org/rfc/rfc9000.html#name-operations-on-streams
    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        self.curr_offset = 0
        self.recv_buffer_dict = {}  # such that K = offset, V = data
        self.recv_buffer = b""
        self._state = RECV
        self.fin_recvd = False
        self._is_ready = True
        self.lock = threading.Lock()

    def read_data(self) -> bytes:
        if self._is_ready:
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
        self._state = DATA_RECVD
        self._convert_dict_to_buffer()

    def _generate_stop_sending_frame(self) -> FrameStop_Sending:  # will return STOP_SENDING frame
        return FrameStop_Sending(stream_id=self.stream_id, application_protocol_error_code=1)

    def send_stop_sending_frame(self):  # TODO: finish according to 2.4
        frame = self._generate_stop_sending_frame()

    def _convert_dict_to_buffer(self):  # the dict is already sorted by offsets so just add them tandem
        for data in self.recv_buffer_dict.values():
            with self.lock:
                self.recv_buffer += data
        self._write_file()

    def _write_file(self):
        print("writing the file")
        with open(r'C:\Users\rodki\recv', 'wb') as file:
            while not self.fin_recvd:
                if self._state == DATA_RECVD:
                    break
            file.write(self.recv_buffer)
            file.close()
        self._state = DATA_READ
