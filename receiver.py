import threading
from quic import QuicConnection

LOOP_BACK_ADDR = '127.0.0.1'
LOCAL_PORT = 3492
REMOTE_PORT = 33336
LOCAL_ADDRESS = (LOOP_BACK_ADDR, LOCAL_PORT)
REMOTE_ADDRESS = (LOOP_BACK_ADDR, REMOTE_PORT)
STREAM_ID_1 = 1
STREAM_ID_2 = 2
OUTPUT_FILE_A = 'received_a.txt'
OUTPUT_FILE_B = 'received_b.txt'


def start(quic: 'QuicConnection'):
    quic.receive_packets()


def main():
    connection_id = 1  # Server
    quic_connection = QuicConnection(connection_id, LOCAL_ADDRESS, REMOTE_ADDRESS)
    # Add two streams to receive the files
    start(quic_connection)

if __name__ == '__main__':
    main()
