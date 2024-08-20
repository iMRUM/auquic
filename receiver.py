import threading
from quic import QuicConnection

LOCAL_ADDRESS = ('localhost', 54321)
REMOTE_ADDRESS = ('localhost', 12345)
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
    quic_connection.add_stream(STREAM_ID_1, initiated_by=connection_id, direction=0)
    quic_connection.add_stream(STREAM_ID_2, initiated_by=connection_id, direction=0)
    start(quic_connection)
    '''
    # Create threads to receive files simultaneously
    thread1 = threading.Thread(target=start, args=(quic_connection,))
    thread2 = threading.Thread(target=start, args=(quic_connection,))

    thread1.start()
    thread2.start()

    # Start receiving packets
    quic_connection.receive_packets()

    thread1.join()
    thread2.join()
    '''

if __name__ == '__main__':
    main()
