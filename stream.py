"""
@file stream.py
@brief Implementation of QUIC stream handling classes.
@details Contains Stream, StreamEndpointABC, StreamSender, and StreamReceiver classes
         for managing data flow in QUIC connections.
"""

from abc import ABC, abstractmethod
from frame import FrameStream
from constants import Constants


class Stream:
    """
    @brief Represents a QUIC stream that handles data transfer.

    @details A Stream can be unidirectional or bidirectional, and handles
             both sending and receiving data through dedicated endpoints.
    """

    def __init__(self, stream_id: int, is_uni: bool, is_s_initiated: bool):
        """
        @brief Initialize a Stream instance.

        @param stream_id Unique identifier for the stream, generated already.
        @param is_uni Specifies if the stream is unidirectional.
        @param is_s_initiated Specifies if the stream was initiated by the server (receiver).
        """
        self._stream_id = stream_id
        self._is_uni = is_uni
        self._is_s_initiated = is_s_initiated
        self._sender = StreamSender(stream_id, (
                    is_uni and not is_s_initiated) or not is_uni)  # if uni and not s-initiated it's a send only stream, or it's a bidi stream
        self._receiver = StreamReceiver(stream_id, (
                    is_uni and is_s_initiated) or not is_uni)  # if uni and s-initiated it's a receive only stream, or it's a bidi stream

    def has_data(self) -> bool:
        """
        @brief Check if there is any data to send or receive.

        @return True if there is data in the sender or receiver buffer, False otherwise.
        """
        return self._sender.has_data() or self._receiver.has_data()

    def get_stream_id(self) -> int:
        """
        @brief Getter for stream ID.

        @return The stream ID.
        """
        return self._stream_id

    def add_data_to_stream(self, data: bytes):
        """
        @brief Add data to the stream by delegation to StreamSender.

        @param data Data to be added to the send buffer.
        """
        self._sender.add_data_to_buffer(data)

    def generate_stream_frames(self, max_size: int):
        """
        @brief Stream frames generation by delegation to StreamSender.

        @details Generate stream frames for sending based on the maximum frame size.

        @param max_size The size of the payload_size which is determined by size of 
                      payload-packet/num of streams on that packet.
        """
        self._sender.generate_stream_frames(max_size)

    def send_next_frame(self) -> FrameStream:
        """
        @brief Retrieve the next frame to be sent from the sender's list.

        @return The next frame to be sent.
        """
        return self._sender.send_next_frame()

    def receive_frame(self, frame: FrameStream):
        """
        @brief Process a received frame by delegating it to the receiver.

        @param frame The received frame.
        """
        self._receiver.stream_frame_recvd(frame)

    def get_data_received(self) -> bytes:
        """
        @brief Retrieve the data received on the stream.

        @return The data received on the stream.
        """
        return self._receiver.get_data_from_buffer()

    def is_finished(self) -> bool:
        """
        @brief Check if the stream has finished sending and receiving data.

        @return True if the stream is in a terminal state, False otherwise.
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
        @brief Determine if a stream is unidirectional based on stream ID.

        @param stream_id The stream ID.
        @return True if the stream is unidirectional, False otherwise.
        """
        return bool(stream_id & Constants.DIRECTION_MASK)

    @staticmethod
    def is_s_init_by_sid(stream_id: int) -> bool:
        """
        @brief Determine if a stream was initiated by a server based on its stream ID.

        @param stream_id The stream ID.
        @return True if the stream was initiated by a server, False otherwise.
        """
        return bool(stream_id & Constants.INIT_BY_MASK)


class StreamEndpointABC(ABC):
    """
    @brief Abstract base class for stream endpoints.

    @details Provides common functionality for sending and receiving endpoints
             of a QUIC stream.
    """

    def __init__(self, stream_id: int, is_usable: bool):
        """
        @brief Abstract Constructor for StreamEndpointABC abstract class.

        @param stream_id The stream ID of this endpoint.
        @param is_usable Specifies if the stream endpoint is 'usable'.
        """
        self._stream_id: int = stream_id
        self._curr_offset: int = Constants.ZERO
        self._buffer: bytes = b""
        self._state: int = Constants.START  # READY = RECV so it's applicable for both endpoints
        self._is_usable: bool = is_usable

    def _set_state(self, state: int) -> bool:
        """
        @brief Set the state of the endpoint.

        @param state New state.
        @return True if _state was set successfully, False otherwise.
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
        @brief Add data to the buffer.

        @param data The data to add to the buffer.
        """
        pass

    def has_data(self) -> bool:
        """
        @brief Check if the buffer contains data.

        @return True if the buffer has data, False otherwise.
        """
        return bool(self._buffer)

    def is_terminal_state(self) -> bool:
        """
        @brief Check if the endpoint has reached a terminal state.

        @return True if the state is DATA_RECVD, False otherwise.
        """
        return self._state == Constants.DATA_RECVD or not self._is_usable


class StreamSender(StreamEndpointABC):
    """
    @brief Represents the sending endpoint of a QUIC stream.

    @details Handles buffering of data to send, generation of stream frames,
             and sending frames over the network.
    """

    def __init__(self, stream_id: int, is_usable: bool):
        """
        @brief Initialize a StreamSender instance.

        @param stream_id The stream ID associated with this sender.
        @param is_usable Whether this sender can be used for sending data.
        """
        super().__init__(stream_id, is_usable)
        self._stream_frames = []

    def add_data_to_buffer(self, data: bytes):
        """
        @brief Add data to the sender's buffer.

        @param data The data to add.
        """
        self._add_data_to_buffer(data)

    def _add_data_to_buffer(self, data: bytes):
        """
        @brief Internal method to add data to the buffer.

        @details Only adds data if the stream is in READY state.

        @param data The data to add.
        @throws ValueError If the stream is not in READY state.
        """
        if self._state == Constants.READY:
            self._buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not READY.")

    def generate_stream_frames(self, max_size: int):
        """
        @brief Generate frames for the data in the buffer.

        @details Splits data into chunks if necessary.

        @param max_size The maximum size of each frame.
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
        @brief Calculate the number of frames required for the data in the buffer.

        @param max_size The maximum size of each frame.
        @return The total number of frames.
        """
        if len(self._buffer) < max_size:
            return Constants.ONE
        else:
            return len(self._buffer) // max_size

    def generate_fin_frame(self) -> FrameStream:
        """
        @brief Generate a frame with the FIN bit set.

        @details This indicates the end of the stream.

        @return The final frame for the stream.
        """
        self._set_state(Constants.DATA_SENT)
        return FrameStream(stream_id=self._stream_id, offset=self._curr_offset,
                           length=len(self._buffer[self._curr_offset:]),
                           fin=True,
                           data=self._buffer[
                                self._curr_offset:])

    def send_next_frame(self) -> FrameStream:
        """
        @brief Send the next frame in the queue.

        @return The next frame to be sent.
        """
        if self._stream_frames:
            frame = self._stream_frames.pop(Constants.ZERO)
            self._set_state(Constants.SEND)
            if frame.fin:
                self._set_state(Constants.DATA_RECVD)
            return frame


class StreamReceiver(StreamEndpointABC):
    """
    @brief Represents the receiving endpoint of a QUIC stream.

    @details Handles reception of stream frames, ordering them by offset,
             and assembling the complete stream data.
    """

    def __init__(self, stream_id: int, is_usable: bool):
        """
        @brief Initialize a StreamReceiver instance.

        @param stream_id The stream ID associated with this receiver.
        @param is_usable Whether this receiver can be used for receiving data.
        """
        super().__init__(stream_id, is_usable)
        self._recv_frame_dict: dict[int:bytes] = {}  # such that K = offset, V = data

    def stream_frame_recvd(self, frame: FrameStream):
        """
        @brief Process a received frame and add it to the receiver's buffer.

        @param frame The received frame.
        """
        if frame.fin:
            self._fin_recvd()
        self._add_frame_to_recv_dict(frame)

    def _add_frame_to_recv_dict(self, frame: FrameStream):
        """
        @brief Add a received frame to the receiver's dictionary.

        @details Updates the current offset.

        @param frame The received frame.
        """
        self._recv_frame_dict[frame.offset] = frame.data
        self._curr_offset += len(frame.data)
        if self._state == Constants.SIZE_KNOWN:
            self._convert_dict_to_buffer()

    def _fin_recvd(self):
        """
        @brief Handle the reception of a FIN frame.

        @details Indicates that all data has been received.
        """
        self._set_state(Constants.SIZE_KNOWN)

    def _convert_dict_to_buffer(self):
        """
        @brief Convert the received frames in the dictionary to a single buffer.

        @details Sorts frames by offset.
        """
        self._recv_frame_dict = dict(sorted(self._recv_frame_dict.items()))  # Sort frames by their offset.
        for data in self._recv_frame_dict.values():
            self._add_data_to_buffer(data)
        self._set_state(Constants.DATA_RECVD)

    def _add_data_to_buffer(self, data: bytes):
        """
        @brief Add data to the buffer if the size is known.

        @param data The data to add.
        @throws ValueError If the stream size is not known.
        """
        if self._state == Constants.SIZE_KNOWN:
            self._buffer += data
        else:
            raise ValueError("ERROR: cannot write. stream is not READY.")

    def get_data_from_buffer(self) -> bytes:
        """
        @brief Retrieve the data from the buffer.

        @return The data in the buffer.
        @throws ValueError If the stream is closed.
        """
        if self._state == Constants.DATA_RECVD:
            try:
                return self._buffer
            finally:
                self._set_state(Constants.DATA_READ)
        else:
            raise ValueError("ERROR: cannot read. stream is closed.")