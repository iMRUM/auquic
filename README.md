# QUIC Protocol Implementation in Python

Python implementation of the QUIC (Quick UDP Internet Connections) protocol.
It includes classes and modules to handle streams, frames, packets, and connections following the QUIC protocol as described in the relevant RFCs.

## Overview
This implementation simulates the core functionalities of QUIC, including the management of streams, the encoding and decoding of frames, the construction and parsing of packets, and the establishment of connections. The codebase is structured to allow easy extension and adaptation for different use cases.

## Project Structure
- `constants.py`: Contains various constants used throughout the project.
- `frame.py`: Defines the classes for different types of frames, including methods to encode and decode them.
- `packet.py`: Handles the construction and parsing of QUIC packets, including the packet header and payload.
- `stream.py`: Manages stream operations, including sending and receiving data, generating frames, and handling stream states.
- `quic.py`: Manages the QUIC connection, including stream management, packet sending and receiving, and showing connection statistics.
- `sender.py`: A script to initiate the sender-side QUIC connection.
- `receiver.py`: A script to initiate the receiver-side QUIC connection.

## Features
- **Stream Management**: Supports multiple streams per connection, with each stream capable of bi-directional or unidirectional data flow.
- **Frame Encoding/Decoding**: Implements the encoding and decoding of stream frames, allowing data to be packaged into QUIC packets.
- **Packet Handling**: Constructs and parses packets, managing headers and payloads.
- **Connection Management**: Simulates the establishment of a QUIC connection, managing the sending and receiving of packets and streams.
- **Efficient Data Transfer**: Optimized for high-throughput data transfer with configurable packet sizes.
- **Statistics Tracking**: Detailed statistics on throughput, packet counts, and transfer rates.

## Installation

### Prerequisites
- Python 3.6 or higher
- Network access for UDP communication

### Clone the Repository
```bash
git clone https://github.com/iMRUM/auquic.git
cd auquic
```

No additional dependencies are required as the implementation uses standard Python libraries.

## Usage
To use the implementation, run the `receiver.py` and `sender.py` scripts in separate terminal windows or on separate machines. The sender will transmit the file, and the receiver will output the statistics of the transfer.

### Receiver
The receiver script listens for incoming packets and processes the received data.

```bash
python receiver.py
```

### Sender
The sender script initializes a QUIC connection and sends a file over one or more streams.

```bash
python sender.py
```

### Example Output
When running the implementation, you'll see output similar to:

```
Packet size received: 1500
STREAM #1:
---------------- 477000 bytes total
---------------- 318 packets total
---------------- at rate 1591800.0 bytes/second
---------------- at rate 1060.0 packets/second
Statistics for all active streams:
------- rate 1591800.0 bytes/second, 477000 bytes total
------- rate 1060.0 packets/second, 318 packets total
total time elapsed: 0.3 seconds
```

## Customization
You can customize the implementation by modifying the constants in `constants.py`. Key configuration options include:

```python
# Network settings
PORT_RECEIVER = 3492        # Receiver port
PORT_SENDER = 33336         # Sender port
MAX_STREAMS = 5             # Maximum number of concurrent streams

# Packet settings
MIN_PACKET_SIZE = 1000      # Minimum packet payload size
MAX_PACKET_SIZE = 2000      # Maximum packet payload size
TIMEOUT = 100               # Socket timeout in seconds
```

## License
This project is licensed under the MIT License.