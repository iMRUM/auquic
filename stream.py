from abc import ABC, abstractmethod
from frame import FrameStream
from constants import Constants


class Stream:
    def __init__(self, stream_id: int, is_uni: bool, is_s_initiated: bool):
        """
        Initialize a Stream instance.

        Args:
            stream_id (int): Unique identifier for the stream, generated already.
            is_uni (bool): Specifies if the stream is unidirectional.
            is_s_initiated (bool): Specifies if the stream was initiated by the server (receiver).
        """
        self._stream_id = stream_id
        self._is_uni = is_uni
        self._is_s_initiated = is_s_initiated
        self._sender = StreamSender(stream_id, (is_uni and not is_s_initiated) or not is_uni) # if uni and not s-initiated it's a send only stream, or it's a bidi stream
        self._receiver = StreamReceiver(stream_id, (is_uni and is_s_initiated) or not is_uni) # if uni and s-initiated it's a receive only stream, or it's a bidi stream

    def has_data(self) -> bool:
        """
        Check if there is any data to send or receive.

        Returns:
            bool: True if there is data in the sender or receiver buffer, False otherwise.
        """
        return self._sender.has_data() or self._receiver.has_data()

    def get_stream_id(self) -> int:
        """
        Getter for stream ID.

        Returns:
            int: stream ID.
        """
        return self._stream_id

    def add_data_to_stream(self, data: bytes):
        """
        Add data to the stream by delegation to StreamSender.

        Args:
            data (bytes): Data to be added to the send buffer.
        """
        self._sender.add_data_to_buffer(data)

    def generate_stream_frames(self, max_size: int):
        """
       Stream frames generation by delegation to StreamSender.
       Generate stream frames for sending based on the maximum frame size.

       Args: max_size (int): The size of the payload_size which is determined by size of payload-packet/num of streams on
       that packet.

        """
        self._sender.generate_stream_frames(max_size)

    def send_next_frame(self) -> FrameStream:
        """
        Retrieve the next frame to be sent from the sender's list.

        Returns:
            FrameStream: The next frame to be sent.
        """
        return self._sender.send_next_frame()

    def receive_frame(self, frame: FrameStream):  # receiving part
        """
        Process a received frame by delegating it to the receiver.

        Args:
            frame (FrameStream): The received frame.
        """
        self._receiver.stream_frame_recvd(frame)

    def get_data_received(self) -> bytes:
        """
        Retrieve the data received on the stream.

        Returns:
            bytes: The data received on the stream.
        """
        return self._receiver.get_data_from_buffer()

    def is_finished(self) -> bool:
        """
        Check if the stream has finished sending and receiving data.

        Returns:
            bool: True if the stream is in a terminal state, False otherwise.
        """
        if not self._is_uni:
            return self._receiver.is_terminal_state() or self._sender.is_terminal_state()
        if self._is_s_initiated:
            return self._receiver.is_terminal_state()
        else:
            return self._sender.is_terminal_state()

    @staticmethod
    def is_uni_by_sid(stream_id: int) -> bool:
        """
        Determine if a stream is unidirectional based on stream ID.

        Args:
            stream_id (int): stream ID.

        Returns:
            bool: True if the stream is unidirectional, False otherwise.
        """
        return bool(stream_id & Constants.DIRECTION_MASK)

    @staticmethod
    def is_s_init_by_sid(stream_id: int) -> bool:
        """
        Determine if a stream was initiated by a server based on its stream ID.

        Args:
            stream_id (int): stream ID.

        Returns:
            bool: True if the stream was initiated by a server, False otherwise.
        """
        return bool(stream_id & Constants.INIT_BY_MASK)


class StreamEndpointABC(ABC):
    def __init__(self, stream_id: int, is_usable: bool):
        """
        Abstract Constructor for StreamEndpointABC abstract class.

        Args:
            stream_id (int): The stream ID of this endpoint.
            is_usable (bool): Specifies if the stream endpoint is 'usable'."""
        self._stream_id: int = stream_id
        self._curr_offset: int = Constants.ZERO
        self._buffer: bytes = b""
        self._state: int = Constants.START  # READY = RECV so it's applicable for both endpoints
        self._is_usable: bool = is_usable

    def _set_state(self, state: int) -> bool:
        """
        Set the state of the endpoint.

        Args:
            state (int): new state.

        Returns:
            bool: True if _state was set successfully, False otherwise.
        """
        try:
            self._state = state
            return True
        except Exception as e:
            print(f'ERROR: Cannot set state to {state}. {e}')
            return False

    @abstractmethod
    def _add_data_to_buffer(self, data: bytes):
        """
        Add data to the buffer.

        Args:
            data (bytes): The data to add to the buffer.
        """
        pass

    def has_data(self) -> bool:
        """
        Check if the buffer contains data.

        Returns:
            bool: True if the buffer has data, False otherwise.
        """
        return bool(self._buffer)

    def is_terminal_state(self) -> bool:
        """
        Check if the endpoint has reached a terminal state.

        Returns:
            bool: True if the state is DATA_RECVD, False otherwise.
        """
        return self._state == Constants.DATA_RECVD or not self._is_usable


class StreamSender(StreamEndpointABC):
    def __init__(self, stream_id: int, is_usable: bool):
        """
        Initialize a StreamSender instance.

        Args:
            stream_id (int): The stream ID associated with this sender.
            @param is_usable:
        """
        super().__init__(stream_id, is_usable)
        self._stream_frames = []

    def add_data_to_buffer(self, data: bytes):
        """
        Add data to the sender's buffer.

        Args:
            data (bytes): The data to add.
        """
        self._add_data_to_buffer(data)

    def _add_data_to_buffer(self, data: bytes):
        """
        Internal method to add data to the buffer, only if the stream is in READY state.

        Args:
            data (bytes): The data to add.
        """
        if self._state == Constants.READY:
            self._buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not READY.")

    def generate_stream_frames(self, max_size: int):
        """
        Generate frames for the data in the buffer, splitting it into chunks if necessary.

        Args:
            max_size (int): The maximum size of each frame.
        """
        total_stream_frames = self._get_total_stream_frames_amount(max_size)
        if total_stream_frames > Constants.ONE:
            for i in range(total_stream_frames):
                self._stream_frames.append(
                    FrameStream(stream_id=self._stream_id, offset=self._curr_offset, length=max_size, fin=False,
                                data=self._buffer[self._curr_offset:self._curr_offset + max_size]))
                self._curr_offset += max_size
        self._stream_frames.append(self.generate_fin_frame())

    def _get_total_stream_frames_amount(self, max_size: int) -> int:
        """
        Calculate the number of frames required for the data in the buffer.

        Args:
            max_size (int): The maximum size of each frame.

        Returns:
            int: The total number of frames.
        """
        if len(self._buffer) < max_size:
            return Constants.ONE
        else:
            return len(self._buffer) // max_size

    def generate_fin_frame(self) -> FrameStream:
        """
        Generate a frame with the FIN bit set, indicating the end of the stream.

        Returns:
            FrameStream: The final frame for the stream.
        """
        self._set_state(Constants.DATA_SENT)
        return FrameStream(stream_id=self._stream_id, offset=self._curr_offset,
                           length=len(self._buffer[self._curr_offset:]),
                           fin=True,
                           data=self._buffer[
                                self._curr_offset:])

    def send_next_frame(self) -> FrameStream:
        """
        Send the next frame in the queue.

        Returns:
            FrameStream: The next frame to be sent.
        """
        if self._stream_frames:
            frame = self._stream_frames.pop(Constants.ZERO)
            self._set_state(Constants.SEND)
            if frame.fin:
                self._set_state(Constants.DATA_RECVD)
            return frame


class StreamReceiver(StreamEndpointABC):
    def __init__(self, stream_id: int, is_usable: bool):
        """
        Initialize a StreamReceiver instance.

        Args:
            stream_id (int): The stream ID associated with this receiver.
            @param is_usable:
        """
        super().__init__(stream_id, is_usable)
        self._recv_frame_dict: dict[int:bytes] = {}  # such that K = offset, V = data

    def stream_frame_recvd(self, frame: FrameStream):
        """
        Process a received frame and add it to the receiver's buffer.

        Args:
            frame (FrameStream): The received frame.
        """
        if frame.fin:
            self._fin_recvd()
        self._add_frame_to_recv_dict(frame)

    def _add_frame_to_recv_dict(self, frame: FrameStream):
        """
        Add a received frame to the receiver's dictionary and update the current offset.

        Args:
            frame (FrameStream): The received frame.
        """
        self._recv_frame_dict[frame.offset] = frame.data
        self._curr_offset += len(frame.data)
        if self._state == Constants.SIZE_KNOWN:
            self._convert_dict_to_buffer()

    def _fin_recvd(self):
        """
        Handle the reception of a FIN frame, indicating that all data has been received.
        """
        self._set_state(Constants.SIZE_KNOWN)

    def _convert_dict_to_buffer(self):
        """
        Convert the received frames in the dictionary to a single buffer, sorted by offset.
        """
        self._recv_frame_dict = dict(sorted(self._recv_frame_dict.items()))  # Sort frames by their offset.
        for data in self._recv_frame_dict.values():
            self._add_data_to_buffer(data)
        self._set_state(Constants.DATA_RECVD)

    def _add_data_to_buffer(self, data: bytes):
        """
        Add data to the buffer if the size is known.

        Args:
            data (bytes): The data to add.
        """
        if self._state == Constants.SIZE_KNOWN:
            self._buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not READY.")

    def get_data_from_buffer(self) -> bytes:
        """
        Retrieve the data from the buffer.

        Returns:
            bytes: The data in the buffer.
        """
        if self._state == Constants.DATA_RECVD:
            try:
                return self._buffer
            finally:
                self._set_state(Constants.DATA_READ)
        else:
            raise ValueError("ERROR: cannot read. stream is closed.")
