# QUIC Protocol Implementation in Python

This repository contains a Python implementation of the QUIC (Quick UDP Internet Connections) protocol. It includes classes and modules to handle streams, frames, packets, and connections following the QUIC protocol as described in the relevant RFCs.

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Sender](#sender)
  - [Receiver](#receiver)
- [Customization](#customization)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Overview
This implementation simulates the core functionalities of QUIC, including the management of streams, the encoding and decoding of frames, the construction and parsing of packets, and the establishment of connections. The codebase is structured to allow easy extension and adaptation for different use cases.

## Project Structure
- `constants.py`: Contains various constants used throughout the project.
- `frame.py`: Defines the classes for different types of frames, including methods to encode and decode them.
- `packet.py`: Handles the construction and parsing of QUIC packets, including the packet header and payload.
- `stream.py`: Manages stream operations, including sending and receiving data, generating frames, and handling stream states.
- `quic.py`: Manages the QUIC connection, including stream management, packet sending and receiving, and connection statistics.
- `sender.py`: A script to initiate the sender-side QUIC connection and handle file transfers.
- `receiver.py`: A script to initiate the receiver-side QUIC connection and process incoming packets.

## Features
- **Stream Management**: Supports multiple streams per connection, with each stream capable of bi-directional or unidirectional data flow.
- **Frame Encoding/Decoding**: Implements the encoding and decoding of stream frames, allowing data to be packaged into QUIC packets.
- **Packet Handling**: Constructs and parses packets, managing headers and payloads.
- **Connection Management**: Simulates the establishment of a QUIC connection, managing the sending and receiving of packets and streams.

## Installation
You can clone the repository and its dependencies using git clone.

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

## Customization
You can customize the implementation by modifying the constants in `constants.py` or by extending the classes in the other modules. For example, you can change the packet size, the number of streams, or the file size to be transferred.


## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

