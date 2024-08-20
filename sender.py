import threading
import os
from quic import (QuicConnection)

LOCAL_ADDRESS = ('localhost', 12345)
REMOTE_ADDRESS = ('localhost', 54321)
STREAM_ID_1 = 1
STREAM_ID_2 = 2
FILE_A = 'a.txt'
FILE_B = 'b.txt'


def send_file(quic: 'QuicConnection'):
    quic.send_packets()


def main():
    connection_id = 0  # Client
    quic_connection = QuicConnection(connection_id, LOCAL_ADDRESS, REMOTE_ADDRESS)
    # Add two streams for the files
    quic_connection.add_stream(STREAM_ID_1, initiated_by=connection_id, direction=0)
    quic_connection.add_stream(STREAM_ID_2, initiated_by=connection_id, direction=0)
    send_file(quic_connection)
'''

    # Create threads to send files simultaneously
    thread1 = threading.Thread(target=send_file, args=(quic_connection,))
    thread2 = threading.Thread(target=send_file, args=(quic_connection,))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()'''


if __name__ == '__main__':
    main()
