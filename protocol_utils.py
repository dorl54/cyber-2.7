# Author - Dor levek
# Date   - 11/22/25
# Protocol

import time
import socket
import logging

# Protocol Constants
LENGTH_FIELD_SIZE = 4
DELIMITER = "#@"
PARAM_SEPARATOR = "/"
ENCODING = 'utf-8'


def send_message(sock: socket.socket, raw_data: str) -> bool:
    """Encodes and sends a message with a length prefix.

    Args:
        sock (socket.socket): The connected socket.
        raw_data (str): The string message to send.

    Returns:
        bool: True if sent successfully, False otherwise.
    """
    try:
        encoded_data = raw_data.encode(ENCODING)
        data_length = len(encoded_data)

        length_prefix = str(data_length).zfill(LENGTH_FIELD_SIZE)
        full_message = length_prefix.encode(ENCODING) + encoded_data

        sock.sendall(full_message)
        logging.debug(f"Message sent: {raw_data}")
        return True
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
        return False


def receive_message(sock: socket.socket) -> str | None:
    """Receives a message by reading the length prefix first.

    Args:
        sock (socket.socket): The connected socket.

    Returns:
        str | None: The decoded message or None if failed.
    """
    try:
        length_prefix_bytes = sock.recv(LENGTH_FIELD_SIZE)

        if not length_prefix_bytes:
            return None

        length_prefix = length_prefix_bytes.decode(ENCODING)
        expected_length = int(length_prefix)

        chunks = []
        bytes_recd = 0

        while bytes_recd < expected_length:
            chunk = sock.recv(expected_length - bytes_recd)
            if not chunk:
                return None

            chunks.append(chunk)
            bytes_recd += len(chunk)

        raw_data = b"".join(chunks).decode(ENCODING)
        logging.debug(f"Message received: {raw_data}")
        return raw_data

    except Exception as e:
        logging.error(f"Error receiving message: {e}")
        return None


def parse_message(message: str) -> dict:
    """Parses a raw protocol message into a dictionary.

    Args:
        message (str): The raw string message.

    Returns:
        dict: Contains 'command', 'type', and 'params'.
    """
    try:
        parts = message.split(DELIMITER, 2)

        command_or_status = parts[0]
        timestamp_or_type = parts[1]
        data_string = parts[2]

        params = data_string.split(PARAM_SEPARATOR)

        return {
            'command': command_or_status,
            'type': timestamp_or_type,
            'params': params
        }
    except Exception as e:
        logging.error(f"Error parsing message: {e}")
        return {
            'command': 'ERROR',
            'type': 'TEXT',
            'params': ['Invalid protocol format.']
        }


def create_command_message(command: str, params: list) -> str:
    """Creates a formatted command message.

    Args:
        command (str): The command name.
        params (list): List of parameters.

    Returns:
        str: The formatted message.
    """
    timestamp = str(int(time.time()))
    data_string = PARAM_SEPARATOR.join(params)
    return f"{command}{DELIMITER}{timestamp}{DELIMITER}{data_string}"


def create_response_message(status: str, data_type: str, data: str | list) -> str:
    """Creates a formatted response message.

    Args:
        status (str): Status code (OK/ERROR).
        data_type (str): Type of data (TEXT/LIST/SIZE).
        data (str | list): The content.

    Returns:
        str: The formatted message.
    """
    if isinstance(data, list):
        data_string = PARAM_SEPARATOR.join(data)
    else:
        data_string = str(data)

    return f"{status}{DELIMITER}{data_type}{DELIMITER}{data_string}"


def run_diagnostics():
    """Runs self-tests before execution."""
    print("--- Running Protocol Self-Tests ---")
    logging.info("Starting Protocol Tests")

    # 1. Test command message creation
    cmd_msg = create_command_message("TEST", ["param1", "param2"])
    assert "TEST" in cmd_msg, "Command name missing"
    assert DELIMITER in cmd_msg, "Delimiter missing"
    assert "param1/param2" in cmd_msg, "Params failed"

    # 2. Test response message creation
    resp_msg = create_response_message("OK", "TEXT", "Success")
    assert resp_msg.startswith("OK#@TEXT#@Success"), "Response construction failed"

    # 3. Test message parsing
    parsed = parse_message("DIR#@123456#@C:\\Windows")
    assert parsed['command'] == 'DIR', "Command parsing failed"
    assert parsed['params'][0] == 'C:\\Windows', "Param parsing failed"

    logging.info("Protocol Tests Finished Successfully")


if __name__ == "__main__":
    logging.basicConfig(filename='protocol.log', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    run_diagnostics()
