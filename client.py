# Author - Dor levek
# Date   - 12/2/25
# Client

import socket
import logging
import os
import protocol_utils as protocol

SERVER_IP = '127.0.0.1'
PORT = 12345
DEFAULT_FILE_NAME = "default_received_screenshot.jpg"


def display_response(raw_response: str):
    """Parses and prints the server response.

    Args:
        raw_response (str): The raw message from server.
    """
    try:
        parsed_response = protocol.parse_message(raw_response)
        status = parsed_response['command']
        data_type = parsed_response['type']
        data = parsed_response['params']

        print("-" * 30)
        print(f"Status: {status} | Data Type: {data_type}")

        if status == 'ERROR':
            print(f" Server Error: {data[0]}")
        elif data_type == 'LIST':
            print(" Directory Content:")
            for item in data:
                print(f"  - {item}")
        elif data_type == 'TEXT':
            print(f"Message: {data[0]}")

    except Exception as e:
        print(f" Error decoding: {e}")
        logging.error(f"Decoding error: {e}")


def handle_file_transfer(sock: socket.socket, file_size: int, dest_path: str):
    """Receives binary data and saves to file.

    Args:
        sock (socket.socket): Connected socket.
        file_size (int): Bytes to receive.
        dest_path (str): Save path.

    Returns:
        bool: Success status.
    """
    print(f"Receiving {file_size} bytes...")
    logging.info(f"Downloading file to {dest_path}")

    bytes_recd = 0
    chunks = []

    while bytes_recd < file_size:
        chunk = sock.recv(min(file_size - bytes_recd, 4096))
        if not chunk:
            logging.error("Connection lost during transfer")
            return False
        chunks.append(chunk)
        bytes_recd += len(chunk)

    file_content = b"".join(chunks)

    try:
        os.makedirs(os.path.dirname(dest_path) or '.', exist_ok=True)
        with open(dest_path, 'wb') as f:
            f.write(file_content)
        print(f" File saved: {dest_path}")
        return True
    except Exception as e:
        logging.error(f"File save error: {e}")
        return False


def validate_environment():
    """Checks basic configuration before running."""
    assert isinstance(SERVER_IP, str), "IP must be string"
    assert len(SERVER_IP.split('.')) == 4, "Invalid IP format"
    assert isinstance(PORT, int), "Port must be int"
    assert hasattr(protocol, 'create_command_message'), "Protocol missing methods"
    logging.info("Environment validation passed.")


def main():
    """Main client loop."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_IP, PORT))
        print(f" Successfully connected to server at {SERVER_IP}:{PORT}")
        logging.info("Connected to server")

        print("\nExample Commands:")
        print("EXECUTE C:\\Windows\\System32\\notepad.exe")
        print("EXECUTE C:\\Program Files\\MyProgram\\app.exe")
        print("COPY C:\\a.txt/C:\\b.txt")
        print("DIR C:\\Users\\public\\")
        print("DELETE C:\\temp\\file.txt")
        print("SCREENSHOT")
        print("SEND_PHOTO C:\\temp\\my_new_screenshot.jpg")
        print("EXIT")

        while True:

            user_input = input("\n (COMMAND PARAM1/PARAM2): ").strip()
            if not user_input:
                continue

            parts = user_input.split(' ', 1)
            command = parts[0].upper()
            params = parts[1].split(protocol.PARAM_SEPARATOR) if len(parts) > 1 else []

            msg = protocol.create_command_message(command, params)
            protocol.send_message(client_socket, msg)

            raw_resp = protocol.receive_message(client_socket)
            if not raw_resp:
                print("Server closed the connection.")
                break

            if 'FILE' in raw_resp:
                dest = params[0] if (command == 'SEND_PHOTO' and params) else DEFAULT_FILE_NAME
                file_info = protocol.parse_message(raw_resp)
                size = int(file_info['params'][0])

                handle_file_transfer(client_socket, size, dest)
                raw_resp = protocol.receive_message(client_socket)
                if not raw_resp:
                    break

            display_response(raw_resp)

            if command == 'EXIT':
                break

    except ConnectionRefusedError:
        print(f" Connection failed. Ensure the server is running at {SERVER_IP}:{PORT}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        client_socket.close()
        logging.info("Socket closed")


if __name__ == "__main__":
    logging.basicConfig(filename='client.log', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    validate_environment()
    main()
