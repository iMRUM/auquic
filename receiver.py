from constants import Constants
from quic import QuicConnection


def main():
    QuicConnection(Constants.CONNECTION_ID_RECEIVER, Constants.ADDR_RECEIVER, Constants.ADDR_SENDER).receive_packets()


if __name__ == '__main__':
    main()
