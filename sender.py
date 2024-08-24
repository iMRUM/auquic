import threading
import os
from quic import (QuicConnection)

LOOP_BACK_ADDR = '127.0.0.1'
LOCAL_PORT = 33336
REMOTE_PORT = 3492
LOCAL_ADDRESS = (LOOP_BACK_ADDR, LOCAL_PORT)
REMOTE_ADDRESS = (LOOP_BACK_ADDR, REMOTE_PORT)
STREAM_ID_1 = 1
STREAM_ID_2 = 2
FILE_A = 'a.txt'
FILE_B = 'b.txt'


def main():
    connection_id = 0  # Client
    quic_connection = QuicConnection(connection_id, LOCAL_ADDRESS, REMOTE_ADDRESS)
    # Add two streams for the files
    stream1 = quic_connection.add_stream(initiated_by=connection_id, direction=0).stream_id
    stream2 = quic_connection.add_stream(initiated_by=connection_id, direction=1).stream_id
    quic_connection.add_data_to_stream(stream1, QuicConnection.read_file(FILE_A))
    quic_connection.add_data_to_stream(stream2, b'123456789123456789')
    quic_connection.send_packets()


if __name__ == '__main__':
    main()
