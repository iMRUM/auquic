from quic import (QuicConnection)

CONNECTION_ID = 0 # Client
LOOP_BACK_ADDR = '127.0.0.1'
LOCAL_PORT = 33336
REMOTE_PORT = 3492
LOCAL_ADDRESS = (LOOP_BACK_ADDR, LOCAL_PORT)
REMOTE_ADDRESS = (LOOP_BACK_ADDR, REMOTE_PORT)
STREAM_ID_1 = 1
STREAM_ID_2 = 2
FILE_A = 'img.gif'


def main():
    quic_connection = QuicConnection(CONNECTION_ID, LOCAL_ADDRESS, REMOTE_ADDRESS)
    # Add streams for the files
    stream1 = quic_connection.get_stream(initiated_by=CONNECTION_ID, direction=0).get_stream_id()
    stream2 = quic_connection.get_stream(initiated_by=CONNECTION_ID, direction=1).get_stream_id()
    stream3 = quic_connection.get_stream(initiated_by=CONNECTION_ID, direction=0).get_stream_id()
    # Add files to the streams
    quic_connection.add_file_to_stream(stream1, FILE_A)
    quic_connection.add_file_to_stream(stream2, FILE_A)
    quic_connection.add_file_to_stream(stream3, FILE_A)
    # Start sending
    quic_connection.send_packets()


if __name__ == '__main__':
    main()
