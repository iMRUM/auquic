from constants import Constants
from quic import (QuicConnection)
import os


def set_file():
    """
    Checks if a file exists at the current directory and creates it if necessary.
    (so the code complies with submission guideline #3)
    """
    if not os.path.exists(Constants.FILE_PATH):
        with open(Constants.FILE_PATH, 'wb') as file:
            file.write(b'I'*(Constants.FILE_SIZE*Constants.KILO))


def main():
    set_file()
    quic_connection = QuicConnection(Constants.CONNECTION_ID_SENDER, Constants.ADDR_SENDER, Constants.ADDR_RECEIVER)
    # Add streams for the files
    streams = []
    for i in range(Constants.MAX_STREAMS):
        streams.append(quic_connection.get_stream(Constants.CONNECTION_ID_SENDER, Constants.UNIDI).get_stream_id())
    # Add files to the streams
    for stream in streams:
        quic_connection.add_file_to_stream(stream, Constants.FILE_PATH)
    # Start sending
    quic_connection.send_packets()


if __name__ == '__main__':
    main()
