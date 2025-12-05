# Author - Dor levek
# Date   - 11/22/25
# Function

import os
import shutil
import subprocess
import glob
import logging
import pyautogui
import protocol_utils as protocol

SCREENSHOT_FILENAME = "screenshot.jpg"
TEMP_DIR = "server_temp"


def handle_dir(params: list, _sock):
    """Handles the DIR command to list files and directories on the server.

    Args:
        params (list): A list containing the path or glob pattern to search (e.g., ['C:\\temp\\*']).
        _sock: The client socket object (unused in this function).

    Returns:
        tuple: (Status: str, Type: str, Data: str or list)
               Status can be 'OK' or 'ERROR'.
               Type can be 'LIST' (for file names) or 'TEXT'.
    """
    path_or_pattern = params[0] if params and params[0] else os.getcwd()
    logging.info(f"Handling DIR command for: {path_or_pattern}")

    is_dir_no_wildcards = os.path.isdir(path_or_pattern) and not any(
        char in path_or_pattern for char in ['*', '?'])

    if is_dir_no_wildcards:
        search_pattern = os.path.join(path_or_pattern, "*")
    else:
        search_pattern = path_or_pattern

    try:
        full_path_list = glob.glob(search_pattern, recursive=False)
        content = []

        for item_path in full_path_list:
            item_name = os.path.basename(item_path)
            if os.path.isdir(item_path) and not item_name.endswith('/'):
                display_name = item_name + '/'
            else:
                display_name = item_name
            content.append(display_name)

        if not content:
            if os.path.exists(path_or_pattern):
                logging.warning("DIR: Directory exists but is empty/no match.")
                return 'OK', 'TEXT', f"No matches found for: {search_pattern}"
            else:
                logging.error("DIR: Path does not exist.")
                return 'ERROR', 'TEXT', f"Path does not exist: {path_or_pattern}"

        logging.info(f"DIR success. Found {len(content)} items.")
        return 'OK', 'LIST', content

    except Exception as err:
        logging.error(f"DIR Exception: {err}")
        return 'ERROR', 'TEXT', f"Error accessing directory: {err}"


def handle_delete(params: list, _sock):
    """Handles the DELETE command to remove a specified file.

    Args:
        params (list): A list containing the full path to the file to be deleted.
        _sock: The client socket object (unused in this function).

    Returns:
        tuple: (Status: str, Type: str, Data: str)
               Status can be 'OK' or 'ERROR'.
               Type is always 'TEXT'.
    """
    if not params or not params[0]:
        logging.error("DELETE: Missing file path")
        return 'ERROR', 'TEXT', 'Missing file path.'

    file_path = params[0]
    logging.info(f"Handling DELETE for: {file_path}")
    try:
        os.remove(file_path)
        logging.info("DELETE success")
        return 'OK', 'TEXT', f"File {file_path} deleted successfully."
    except Exception as err:
        logging.error(f"DELETE error: {err}")
        return 'ERROR', 'TEXT', f"Error deleting file: {err}"


def handle_copy(params: list, _sock):
    """Handles the COPY command to duplicate a file on the server.

    Args:
        params (list): A list containing [Source Path, Destination Path].
        _sock: The client socket object (unused in this function).

    Returns:
        tuple: (Status: str, Type: str, Data: str)
               Status can be 'OK' or 'ERROR'.
               Type is always 'TEXT'.
    """
    if len(params) < 2:
        logging.error("COPY: Missing source or dest")
        return 'ERROR', 'TEXT', 'Missing source or destination path.'

    src, dst = params[0], params[1]
    logging.info(f"Handling COPY from {src} to {dst}")
    try:
        shutil.copy2(src, dst)
        logging.info("COPY success")
        return 'OK', 'TEXT', f"File copied from {src} to {dst}."
    except Exception as err:
        logging.error(f"COPY error: {err}")
        return 'ERROR', 'TEXT', f"Error copying file: {err}"


def handle_execute(params: list, _sock):
    """Handles the EXECUTE command, launching a program or opening a file on the server.

    Args:
        params (list): A list containing the path to the executable or document.
        _sock: The client socket object (unused in this function).

    Returns:
        tuple: (Status: str, Type: str, Data: str)
               Status can be 'OK' or 'ERROR'.
               Type is always 'TEXT'.
    """
    if not params or not params[0]:
        logging.error("EXECUTE: Missing program path")
        return 'ERROR', 'TEXT', 'Missing program path.'

    program_path = params[0]
    logging.info(f"Handling EXECUTE for: {program_path}")
    try:
        subprocess.Popen(program_path)
        logging.info("EXECUTE success")
        return 'OK', 'TEXT', f"Program {program_path} launched successfully."
    except Exception as err:
        logging.error(f"EXECUTE error: {err}")
        return 'ERROR', 'TEXT', f"Error executing program: {err}"


def handle_screenshot(_params, _sock):
    """Handles the SCREENSHOT command, capturing the server's desktop and saving it locally.

    Args:
        _params: Command parameters (unused).
        _sock: The client socket object (unused).

    Returns:
        tuple: (Status: str, Type: str, Data: str)
               Status can be 'OK' or 'ERROR'.
               Type is always 'TEXT'.
    """
    logging.info("Handling SCREENSHOT")
    try:
        image = pyautogui.screenshot()
        os.makedirs(TEMP_DIR, exist_ok=True)
        image.save(os.path.join(TEMP_DIR, SCREENSHOT_FILENAME))
        logging.info("SCREENSHOT saved")
        return 'OK', 'TEXT', f"Screenshot saved in {TEMP_DIR}."
    except Exception as err:
        logging.error(f"SCREENSHOT error: {err}")
        return 'ERROR', 'TEXT', f"Error taking screenshot: {err}"


def handle_send_photo(_params, sock):
    """Handles the SEND_PHOTO command, transferring the saved screenshot file to the client.

    This function manages the file size prefix and sends raw binary data, communicating the
    transfer status directly over the socket.

    Args:
        _params: Command parameters (unused).
        sock: The connected socket (required for data transfer).

    Returns:
        tuple: ('COMPLETED_RESPONSE', 'TEXT', 'N/A').
               This special return value signals the main loop that the full response was sent
               directly via the socket.
    """
    logging.info("Handling SEND_PHOTO")
    file_path = os.path.join(TEMP_DIR, SCREENSHOT_FILENAME)

    if not os.path.exists(file_path):
        logging.error("SEND_PHOTO: File not found")
        msg = protocol.create_response_message(
            'ERROR', 'TEXT', 'Screenshot not found. Run SCREENSHOT first.'
        )
        protocol.send_message(sock, msg)
        return 'COMPLETED_RESPONSE', 'TEXT', 'N/A'

    try:
        file_size = os.path.getsize(file_path)
        size_msg = protocol.create_response_message('FILE', 'SIZE', str(file_size))
        protocol.send_message(sock, size_msg)

        with open(file_path, 'rb') as file_obj:
            sock.sendall(file_obj.read())

        logging.info("SEND_PHOTO: Data sent")
        final_msg = protocol.create_response_message(
            'OK', 'TEXT', f"File {SCREENSHOT_FILENAME} sent successfully."
        )
        protocol.send_message(sock, final_msg)

        return 'COMPLETED_RESPONSE', 'TEXT', 'N/A'

    except Exception as err:
        logging.error(f"SEND_PHOTO error: {err}")
        err_msg = protocol.create_response_message('ERROR', 'TEXT', f"Error: {err}")
        protocol.send_message(sock, err_msg)
        return 'COMPLETED_RESPONSE', 'TEXT', 'N/A'


def handle_exit(_params, _sock):
    """Handles the EXIT command, signaling the intent to close the connection.

    Args:
        _params: Command parameters (unused).
        _sock: The client socket object (unused).

    Returns:
        tuple: ('OK', 'TEXT', 'Connection closing.').
               Signals a successful client-requested termination.
    """
    logging.info("Handling EXIT")
    return 'OK', 'TEXT', 'Connection closing.'


if __name__ == "__main__":

    logging.basicConfig(filename='functions.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    print("--- Running Logic Tests (server_handlers.py) ---")
    logging.info("Starting Logic Tests for function.py handlers.")


    class MockSocket:

        @staticmethod
        def send(_data):
            pass

        @staticmethod
        def sendall(_data):
            pass

        @staticmethod
        def recv(_size):
            return b''


    mock_sock = MockSocket()

    logging.info("Testing COPY and DELETE (Full I/O Test)...")

    TEST_DIR_NAME = "test_temp_dir_for_io_assert"
    TEST_FILE_ORIG = os.path.join(TEST_DIR_NAME, "file_original.tmp")
    TEST_FILE_COPY = os.path.join(TEST_DIR_NAME, "file_copy.tmp")


    def cleanup_io_test_files():
        if os.path.exists(TEST_FILE_ORIG):
            os.remove(TEST_FILE_ORIG)
        if os.path.exists(TEST_FILE_COPY):
            os.remove(TEST_FILE_COPY)
        if os.path.exists(TEST_DIR_NAME):
            try:
                os.rmdir(TEST_DIR_NAME)
            except OSError:
                pass


    cleanup_io_test_files()

    try:
        os.makedirs(TEST_DIR_NAME, exist_ok=True)
        with open(TEST_FILE_ORIG, 'w') as f_test:
            f_test.write("Test content for copy.")
        assert os.path.exists(TEST_FILE_ORIG), "I/O Setup Failed"
        logging.info("Original file created.")

        status_copy, _, data_copy = handle_copy([TEST_FILE_ORIG, TEST_FILE_COPY], mock_sock)
        assert status_copy == 'OK', "I/O Test Failed: COPY"
        assert os.path.exists(TEST_FILE_COPY), "I/O Test Failed: Copy missing"
        logging.info("COPY successful.")

        status_del_orig, _, data_del_orig = handle_delete([TEST_FILE_ORIG], mock_sock)
        assert status_del_orig == 'OK', "I/O Test Failed: DELETE Orig"
        assert not os.path.exists(TEST_FILE_ORIG), "I/O Test Failed: Orig still exists"
        logging.info("DELETE (Original) successful.")

        status_del_copy, _, data_del_copy = handle_delete([TEST_FILE_COPY], mock_sock)
        assert status_del_copy == 'OK', "I/O Test Failed: DELETE Copy"
        assert not os.path.exists(TEST_FILE_COPY), "I/O Test Failed: Copy still exists"
        logging.info("DELETE (Copy) successful.")

    except Exception as test_err:
        logging.error(f"CRITICAL FAIL: Test failed - {test_err}", exc_info=True)
        raise

    finally:
        cleanup_io_test_files()
        logging.info("Temporary files removed.")

    logging.info("Testing DIR...")
    dir_status, dir_type, dir_content = handle_dir([os.getcwd()], mock_sock)
    assert dir_status == 'OK', "DIR Failed"
    assert dir_type == 'LIST', "DIR Type Failed"

    logging.info("Testing EXECUTE...")
    exec_status, exec_type, exec_data = handle_execute([], mock_sock)
    assert exec_status == 'ERROR', "EXECUTE Failed"

    logging.info("Testing DELETE (Missing)...")
    del_status, del_type, del_data = handle_delete([], mock_sock)
    assert del_status == 'ERROR', "DELETE Failed"

    logging.info("Testing COPY (Missing)...")
    copy_status, copy_type, copy_data = handle_copy([], mock_sock)
    assert copy_status == 'ERROR', "COPY Failed"

    logging.info("Testing SCREENSHOT...")
    scr_status, scr_type, scr_data = handle_screenshot([], mock_sock)
    assert scr_status in ('OK', 'ERROR'), "SCREENSHOT Failed"

    logging.info("Testing SEND_PHOTO...")
    send_status, send_type, send_data = handle_send_photo([], mock_sock)
    assert send_status == 'COMPLETED_RESPONSE', "SEND_PHOTO Failed"

    logging.info("Testing EXIT...")
    exit_status, exit_type, exit_data = handle_exit([], mock_sock)
    assert exit_status == 'OK', "EXIT Failed"

    logging.info("All Command Asserts Passed Successfully!")
