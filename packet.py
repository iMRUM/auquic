class Packet:
    def __init__(self):
        """
        Initialize a Packet instance.
        """
        self.frames = []

    def add_frame(self, stream_id, data):
        """
        Add a frame to the packet.

        Args:
            stream_id (int): Unique identifier for the stream.
            data (bytes): The data to be added as a frame.
        """
        frame = {
            'stream_id': stream_id,
            'data': data
        }
        self.frames.append(frame)
