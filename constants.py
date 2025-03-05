"""
@file constants.py
@brief Constants used throughout the QUIC protocol implementation.
@details Defines numerical constants, bit masks, and configuration values
         used by the various components of the QUIC implementation.
"""


class Constants:
    """
    @brief Constants used throughout the QUIC protocol implementation.

    @details Constants are grouped by category for better organization.
    """

    # -------------------
    # General constants
    # -------------------
    ZERO = 0  # !< Constant for zero value
    ONE = 1  # !< Constant for one value
    TWO = 2  # !< Constant for two value
    THREE = 3  # !< Constant for three value
    FOUR = 4  # !< Constant for four value
    FIVE = 5  # !< Constant for five value
    SIX = 6  # !< Constant for six value
    SEVEN = 7  # !< Constant for seven value
    EIGHT = 8  # !< Constant for eight value
    START = ZERO  # !< Alias for zero, used as index start
    KILO = 1024  # !< Number of bytes in a kilobyte

    # -------------------
    # Frame-related constants
    # -------------------
    OFFSET_LENGTH = EIGHT  # !< Length of the offset field in bytes
    LEN_LENGTH = EIGHT  # !< Length of the length field in bytes
    FRAME_TYPE_FIELD_LENGTH = ONE  # !< Length of the frame type field in bytes
    MIN_TYPE_FIELD = 0x08  # !< Minimum value for the type field
    OFF_BIT = 0x04  # !< Bit flag indicating offset presence
    LEN_BIT = 0x02  # !< Bit flag indicating length presence
    FIN_BIT = 0x01  # !< Bit flag indicating final frame

    # -------------------
    # Packet-related constants
    # -------------------
    HEADER_LENGTH = ONE  # !< Length of the packet header in bytes
    PACKET_NUMBER_LENGTH = FOUR  # !< Length of the packet number in bytes
    DEST_CONNECTION_ID_LENGTH = EIGHT  # !< Length of the destination connection ID in bytes

    # Packet-header pack shifts
    FORM_SHIFT = SEVEN  # !< Shift for header form bit
    FIXED_SHIFT = SIX  # !< Shift for fixed bit
    SPIN_SHIFT = FIVE  # !< Shift for spin bit
    RES_SHIFT = THREE  # !< Shift for reserved bits
    KEY_SHIFT = TWO  # !< Shift for key phase bit

    # Packet-header unpack masks
    FORM_MASK = 0b10000000  # !< Mask for header form bit
    FIXED_MASK = 0b01000000  # !< Mask for fixed bit
    SPIN_MASK = 0b00100000  # !< Mask for spin bit
    RES_MASK = 0b00011000  # !< Mask for reserved bits
    KEY_MASK = 0b00000100  # !< Mask for key phase bit
    PACKET_NUMBER_LENGTH_MASK = 0b00000011  # !< Mask for packet number length

    # -------------------
    # Stream-related constants
    # -------------------
    STREAM_ID_LENGTH = EIGHT  # !< Length of the stream ID in bytes
    INIT_BY_MASK = 0x01  # !< Mask for stream initiated by bit
    DIRECTION_MASK = 0x02  # !< Mask for stream direction bit

    # Both endpoints state-related constants
    DATA_RECVD = 3  # !< State indicating data received

    # StreamSender state-related constants
    READY = START  # !< State indicating ready to send
    SEND = ONE  # !< State indicating sending
    DATA_SENT = TWO  # !< State indicating data sent

    # StreamReceiver state-related constants
    RECV = START  # !< State indicating ready to receive
    SIZE_KNOWN = ONE  # !< State indicating size known
    DATA_READ = TWO  # !< State indicating data read

    # -------------------
    # QuicConnection-related constants
    # -------------------
    MIN_PACKET_SIZE = 1000  # !< Minimum size of a packet
    MAX_PACKET_SIZE = 2000  # !< Maximum size of a packet
    PACKET_SIZE_BYTES = TWO  # !< Size of the packet size field in bytes
    FRAMES_IN_PACKET = FIVE  # !< Number of frames in a packet
    BASE_TWO = TWO  # !< Base for binary conversions
    TIMEOUT = 100  # !< Timeout value for socket operations
    BIDI = ZERO  # !< Flag for bidirectional stream
    UNIDI = ONE  # !< Flag for unidirectional stream

    # -------------------
    # Network-related constants
    # -------------------
    CONNECTION_ID_SENDER = ZERO  # !< Connection ID for sender
    CONNECTION_ID_RECEIVER = ONE  # !< Connection ID for receiver
    LOOP_BACK_ADDR = '127.0.0.1'  # !< Loopback address
    PORT_RECEIVER = 3492  # !< Port for receiver
    PORT_SENDER = 33336  # !< Port for sender
    ADDR_RECEIVER = (LOOP_BACK_ADDR, PORT_RECEIVER)  # !< Address tuple for receiver
    ADDR_SENDER = (LOOP_BACK_ADDR, PORT_SENDER)  # !< Address tuple for sender
    MAX_STREAMS = 5  # !< Maximum number of streams
    FILE_PATH = 'img.gif'  # !< Path to the file to be sent
    FILE_SIZE = 477  # !< Size of the file in kilobytes