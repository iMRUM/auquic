from quic import (QuicConnection)

CONNECTION_ID = 0  # Client
LOOP_BACK_ADDR = '127.0.0.1'
LOCAL_PORT = 33336
REMOTE_PORT = 3492
LOCAL_ADDRESS = (LOOP_BACK_ADDR, LOCAL_PORT)
REMOTE_ADDRESS = (LOOP_BACK_ADDR, REMOTE_PORT)
STREAMS = 10
FILE_A = 'img.gif'
FILE_B = 'img2.gif'


def main():
    quic_connection = QuicConnection(CONNECTION_ID, LOCAL_ADDRESS, REMOTE_ADDRESS)
    # Add streams for the files
    streams = []
    for i in range(STREAMS):
        streams.append(quic_connection.get_stream(CONNECTION_ID, 0).get_stream_id())
    # Add files to the streams
    for stream in streams:
        quic_connection.add_file_to_stream(stream, FILE_A)
    # Start sending
    quic_connection.send_packets()


if __name__ == '__main__':
    main()
