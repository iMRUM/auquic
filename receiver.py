from quic import QuicConnection

LOOP_BACK_ADDR = '127.0.0.1'
LOCAL_PORT = 3492
REMOTE_PORT = 33336
LOCAL_ADDRESS = (LOOP_BACK_ADDR, LOCAL_PORT)
REMOTE_ADDRESS = (LOOP_BACK_ADDR, REMOTE_PORT)


def main():
    connection_id = 1  # Server
    quic_connection = QuicConnection(connection_id, LOCAL_ADDRESS, REMOTE_ADDRESS)
    quic_connection.receive_packets()


if __name__ == '__main__':
    main()
