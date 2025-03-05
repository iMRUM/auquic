"""
@file receiver.py
@brief Receiver implementation for QUIC protocol.
@details Sets up a QUIC connection as a receiver and waits for incoming packets.
"""

from constants import Constants
from quic import QuicConnection


def main():
    """
    @brief Main function that initializes and runs the receiver.

    @details Creates a QUIC connection and starts listening for packets.
    """
    QuicConnection(Constants.CONNECTION_ID_RECEIVER, Constants.ADDR_RECEIVER, Constants.ADDR_SENDER).receive_packets()


if __name__ == '__main__':
    main()