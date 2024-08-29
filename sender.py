from constants import Constants
from quic import (QuicConnection)


def main():
    quic_connection = QuicConnection(Constants.CONNECTION_ID_SENDER, Constants.ADDR_SENDER, Constants.ADDR_RECEIVER)
    # Add streams for the files
    streams = []
    for i in range(Constants.STREAMS):
        streams.append(quic_connection.get_stream(Constants.CONNECTION_ID_SENDER, Constants.UNIDI).get_stream_id())
        streams.append(quic_connection.get_stream(Constants.CONNECTION_ID_SENDER, Constants.BIDI).get_stream_id())
    # Add files to the streams
    for stream in streams:
        quic_connection.add_file_to_stream(stream, Constants.FILE_PATH)
    # Start sending
    quic_connection.send_packets()


if __name__ == '__main__':
    main()
