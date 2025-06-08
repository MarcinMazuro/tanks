import json
import socket
import struct
import time

# Message types
MSG_TYPE_JOIN = 1
MSG_TYPE_LEAVE = 2
MSG_TYPE_ACTION = 3
MSG_TYPE_STATE = 4
MSG_TYPE_START = 5
MSG_TYPE_END = 6
MSG_TYPE_READY = 7
MSG_TYPE_RESTART = 8

class NetworkMessage:
    """
    Represents a network message for communication between client and server.
    """
    def __init__(self, msg_type, data=None):
        """
        Initialize a new network message.

        Args:
            msg_type (int): The type of message.
            data (dict): The message data.
        """
        self.msg_type = msg_type
        self.data = data or {}
        self.timestamp = time.time()

    def to_bytes(self):
        """
        Convert the message to bytes for network transmission.

        Returns:
            bytes: The message as bytes.
        """
        # Convert data to JSON string
        json_data = json.dumps(self.data)

        # Create message header (message type and data length)
        header = struct.pack('!BI', self.msg_type, len(json_data))

        # Combine header and data
        return header + json_data.encode('utf-8')

    @staticmethod
    def from_bytes(data):
        """
        Create a NetworkMessage from bytes.

        Args:
            data (bytes): The message bytes.

        Returns:
            NetworkMessage: The created message, or None if the data is invalid.
        """
        try:
            # Extract header (message type and data length)
            header_size = struct.calcsize('!BI')
            if len(data) < header_size:
                return None

            msg_type, data_length = struct.unpack('!BI', data[:header_size])

            # Extract and parse JSON data
            json_data = data[header_size:header_size + data_length].decode('utf-8')
            message_data = json.loads(json_data)

            return NetworkMessage(msg_type, message_data)
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None

class NetworkManager:
    """
    Manages network communication for the game.
    """
    def __init__(self, is_server, host='0.0.0.0', port=12345):
        """
        Initialize the network manager.

        Args:
            is_server (bool): True if this is the server, False for client.
            host (str): The host address to bind to.
            port (int): The port to use.
        """
        self.is_server = is_server
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clients = {}  # Maps client address to player ID (server only)

        # Set socket options
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind socket
        if is_server:
            self.socket.bind((host, port))
            self.socket.setblocking(False)

    def send_message(self, message, address=None):
        """
        Send a message to a client or the server.

        Args:
            message (NetworkMessage): The message to send.
            address (tuple): The address to send to (client only).
        """
        if self.is_server:
            if address is None:
                # Broadcast to all clients
                for client_address in self.clients:
                    self.socket.sendto(message.to_bytes(), client_address)
            else:
                # Send to specific client
                self.socket.sendto(message.to_bytes(), address)
        else:
            # Client sends to server
            if address is None:
                address = (self.host, self.port)
            self.socket.sendto(message.to_bytes(), address)

    def receive_message(self):
        """
        Receive a message from the network.

        Returns:
            tuple: (NetworkMessage, address) or (None, None) if no message is available.
        """
        try:
            data, address = self.socket.recvfrom(4096)
            message = NetworkMessage.from_bytes(data)
            return message, address
        except BlockingIOError:
            # No data available
            return None, None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None, None

    def connect_to_server(self, server_host, server_port):
        """
        Connect to the game server (client only).

        Args:
            server_host (str): The server host address.
            server_port (int): The server port.

        Returns:
            bool: True if connected successfully, False otherwise.
        """
        if self.is_server:
            return False

        self.host = server_host
        self.port = server_port

        # Set socket to non-blocking mode
        self.socket.setblocking(False)

        # Send join message
        join_message = NetworkMessage(MSG_TYPE_JOIN, {
            'name': 'Player'  # This should be set by the client
        })
        self.send_message(join_message)

        return True

    def add_client(self, address, player_id):
        """
        Add a client to the server's client list (server only).

        Args:
            address (tuple): The client's address.
            player_id (int): The player ID assigned to the client.
        """
        if self.is_server:
            self.clients[address] = player_id

    def remove_client(self, address):
        """
        Remove a client from the server's client list (server only).

        Args:
            address (tuple): The client's address.

        Returns:
            int: The player ID of the removed client, or None if not found.
        """
        if self.is_server and address in self.clients:
            player_id = self.clients[address]
            del self.clients[address]
            return player_id
        return None

    def close(self):
        """
        Close the network connection.
        """
        self.socket.close()
