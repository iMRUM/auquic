# constants.py

class Constants:
    # -------------------
    # General constants
    # -------------------
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    TEN = 10
    START = ZERO
    # -------------------
    # Frame-related constants
    # -------------------
    OFFSET_LENGTH = EIGHT
    LEN_LENGTH = EIGHT
    FRAME_TYPE_FIELD_LENGTH = ONE
    MIN_TYPE_FIELD = 0x08
    OFF_BIT = 0x04
    LEN_BIT = 0x02
    FIN_BIT = 0x01
    # -------------------
    # Packet-related constants
    # -------------------
    HEADER_LENGTH = ONE
    PACKET_NUMBER_LENGTH = FOUR
    DEST_CONNECTION_ID_LENGTH = EIGHT
    # Packet-header pack shifts
    FORM_SHIFT = SEVEN
    FIXED_SHIFT = SIX
    SPIN_SHIFT = FIVE
    RES_SHIFT = THREE
    KEY_SHIFT = TWO
    # Packet-header unpack masks
    FORM_MASK = 0b10000000
    FIXED_MASK = 0b01000000
    SPIN_MASK = 0b00100000
    RES_MASK = 0b00011000
    KEY_MASK = 0b00000100
    PACKET_NUMBER_LENGTH_MASK = 0b00000011
    # -------------------
    # Stream-related constants
    # -------------------
    STREAM_ID_LENGTH = EIGHT
    INIT_BY_MASK = 0x01
    DIRECTION_MASK = 0x02
    # Both endpoints state-related constants
    DATA_RECVD = 3
    RESET_RECVD = 5
    # StreamSender state-related constants
    READY = START
    SEND = ONE
    DATA_SENT = TWO
    RESET_SENT = FOUR
    # StreamReceiver state-related constants
    RECV = START
    SIZE_KNOWN = ONE
    DATA_READ = TWO
    RESET_READ = FOUR
    # -------------------
    # QuicConnection-related constants
    # -------------------
    MIN_PACKET_SIZE = 1000
    MAX_PACKET_SIZE = 2000
    PACKET_SIZE_BYTES = TWO
    FRAMES_IN_PACKET = FIVE
    BASE_TWO = TWO
    TIMEOUT = 60
    UDP_HEADER_SIZE = 16
    BIDIRECTIONAL = ZERO
    CLIENT_ID = ZERO

    UNIDIRECTIONAL = ONE
    SERVER_ID = ONE

    FILE_PATH = 'img.gif'

    # Network-related constants
    CONNECTION_ID_SERVER = 1
    CONNECTION_ID_CLIENT = 0
    LOOP_BACK_ADDR = '127.0.0.1'
    LOCAL_PORT_RECEIVER = 3492
    REMOTE_PORT_RECEIVER = 33336
    LOCAL_PORT_SENDER = 33336
    REMOTE_PORT_SENDER = 3492
    STREAMS = 10
    FILE_A = 'img.gif'
    FILE_B = 'img2.gif'
    TIMEOUT = 10
