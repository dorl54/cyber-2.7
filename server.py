# Author - Dor levek
# Date   - 11/22/25
# Server

import socket
import threading
import os
import logging
import function as handlers
import protocol_utils as protocol

SERVER_IP = '0.0.0.0'
PORT = 12345
TEMP_DIR = "server_temp"

COMMAND_HANDLERS = {
    'DIR': handlers.handle_dir,
    'DELETE': handlers.handle_delete,
    'COPY': handlers.handle_copy,
    'EXECUTE': handlers.handle_execute,
    'SCREENSHOT': handlers.handle_screenshot,
    'SEND_PHOTO': handlers.handle_send_photo,
    'EXIT': handlers.handle_exit
}


def handle_client(client_socket: socket.socket):
    """Handles the communication with a single client.

    Args:
        client_socket (socket.socket): The connected client socket.
    """
    try:
        addr = client_socket.getpeername()
        print(f"--- New client connected from {addr} ---")
        logging.info(f"New connection from {addr}")

        while True:
            raw_message = protocol.receive_message(client_socket)

            if not raw_message:
                logging.info(f"Client {addr} disconnected.")
                break

            parsed_data = protocol.parse_message(raw_message)
            command = parsed_data['command'].upper()
            params = parsed_data['params']

            logging.debug(f"Command: {command}, Params: {params}")

            if command in COMMAND_HANDLERS:
                status, dtype, data = COMMAND_HANDLERS[command](params, client_socket)
            else:
                logging.warning(f"Unknown command: {command}")
                status, dtype, data = 'ERROR', 'TEXT', f"Unknown command: {command}"

            if status != 'COMPLETED_RESPONSE':
                response = protocol.create_response_message(status, dtype, data)
                protocol.send_message(client_socket, response)

            if command == 'EXIT':
                break

    except Exception as e:
        logging.error(f"Error handling client: {e}")
    finally:
        if client_socket:
            client_socket.close()
        logging.info("Client socket closed.")


def setup_server(ip: str, port: int) -> socket.socket:
    """Initializes the server socket.

    Args:
        ip (str): Server IP.
        port (int): Server Port.

    Returns:
        socket.socket: The listening socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((ip, port))
    sock.listen(5)
    return sock


def accept_connections(server_socket: socket.socket):
    """Main loop to accept incoming clients.

    Args:
        server_socket (socket.socket): The listening socket.
    """
    print(f"Server listening at {SERVER_IP}:{PORT}")
    logging.info(f"Server started on {SERVER_IP}:{PORT}")

    while True:
        client_socket, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()


def main():
    """Main entry point for the server."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    server_socket = None
    try:
        server_socket = setup_server(SERVER_IP, PORT)
        accept_connections(server_socket)
    except Exception as e:
        print(f"Server fatal error: {e}")
        logging.critical(f"Server crashed: {e}")
    finally:
        if server_socket:
            server_socket.close()


if __name__ == "__main__":
    logging.basicConfig(filename='server.log', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    main()
