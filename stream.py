import threading


class Stream:
    def __init__(self, stream_id, initiated_by, bidirectional=True):
        """
        Initialize a Stream instance.

        Args:
            stream_id (int): Unique identifier for the stream. 2MSB are 11, 62 usable bits, 8-bytes total.
            initiated_by (str): Indicates whether the stream was initiated by client(0) or server(1).
            bidirectional (bool): Indicates if the stream is bidirectional(0) or unidirectional(1)
        """
        self.stream_id = stream_id
        self.initiated_by = initiated_by  # 'client' or 'server'
        self.bidirectional = bidirectional
        self.data = ""
        self.offset = 0
        self.lock = threading.Lock()

    def add_data(self, data):
        """
        Add data to the stream.

        Args:
            data (bytes): Data to be added to the stream.
        """
        with self.lock:
            self.data += data

    def get_chunk(self, size):
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

    def create_stream(self, stream_id, initiated_by, bidirectional=True):
        """
        Create a new stream.

        Args:
            stream_id (int): Unique identifier for the stream.
            initiated_by (str): Indicates whether the stream was initiated by 'client' or 'server'.
            bidirectional (bool): Indicates if the stream is bidirectional. Default is True.

        Returns:
            Stream: The created stream instance.
        """
        with self.lock:
            if stream_id not in self.streams:
                self.streams[stream_id] = Stream(stream_id, initiated_by, bidirectional)
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


# Example usage
if __name__ == "__main__":
    stream_manager = StreamManager()

    # Client-initiated, bidirectional stream
    stream_manager.create_stream(1, 'client', bidirectional=True)
    stream_manager.add_data_to_stream(1, b"client initiated bidirectional stream data")

    # Server-initiated, unidirectional stream
    stream_manager.create_stream(2, 'server', bidirectional=False)
    stream_manager.add_data_to_stream(2, b"server initiated unidirectional stream data")

    print(stream_manager.get_next_frame(1, 10))  # Fetch a chunk from the client-initiated stream
    print(stream_manager.get_next_frame(2, 10))  # Fetch a chunk from the server-initiated stream
