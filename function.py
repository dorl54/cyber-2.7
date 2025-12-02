# Author - Dor levek
# Date   - 11/22/25
# Function

import os
import shutil
import subprocess
import glob
import socket
import logging
import pyautogui
import protocol_utils as protocol

SCREENSHOT_FILENAME = "screenshot.jpg"
TEMP_DIR = "server_temp"


def handle_dir(params: list, sock: socket.socket):
    """Handles the DIR command to list files.

    Args:
        params (list): Path or glob pattern.
        sock (socket.socket): Client socket.

    Returns:
        tuple: (Status, Type, Data)
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

    except Exception as e:
        logging.error(f"DIR Exception: {e}")
        return 'ERROR', 'TEXT', f"Error accessing directory: {e}"


def handle_delete(params: list, sock: socket.socket):
    """Handles the DELETE command.

    Args:
        params (list): File path to delete.
        sock (socket.socket): Client socket.

    Returns:
        tuple: (Status, Type, Data)
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
    except Exception as e:
        logging.error(f"DELETE error: {e}")
        return 'ERROR', 'TEXT', f"Error deleting file: {e}"


def handle_copy(params: list, sock: socket.socket):
    """Handles the COPY command.

    Args:
        params (list): [source, destination].
        sock (socket.socket): Client socket.

    Returns:
        tuple: (Status, Type, Data)
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
    except Exception as e:
        logging.error(f"COPY error: {e}")
        return 'ERROR', 'TEXT', f"Error copying file: {e}"


def handle_execute(params: list, sock: socket.socket):
    """Handles the EXECUTE command.

    Args:
        params (list): Program path.
        sock (socket.socket): Client socket.

    Returns:
        tuple: (Status, Type, Data)
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
    except Exception as e:
        logging.error(f"EXECUTE error: {e}")
        return 'ERROR', 'TEXT', f"Error executing program: {e}"


def handle_screenshot(params: list, sock: socket.socket):
    """Handles the SCREENSHOT command.

    Args:
        params (list): Ignored.
        sock (socket.socket): Client socket.

    Returns:
        tuple: (Status, Type, Data)
    """
    logging.info("Handling SCREENSHOT")
    try:
        image = pyautogui.screenshot()
        os.makedirs(TEMP_DIR, exist_ok=True)
        image.save(os.path.join(TEMP_DIR, SCREENSHOT_FILENAME))
        logging.info("SCREENSHOT saved")
        return 'OK', 'TEXT', f"Screenshot saved in {TEMP_DIR}."
    except Exception as e:
        logging.error(f"SCREENSHOT error: {e}")
        return 'ERROR', 'TEXT', f"Error taking screenshot: {e}"


def handle_send_photo(params: list, sock: socket.socket):
    """Handles sending the screenshot file to the client.

    Args:
        params (list): Ignored.
        sock (socket.socket): Client socket.

    Returns:
        tuple: (Status, Type, Data) - Returns COMPLETED_RESPONSE.
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

        with open(file_path, 'rb') as f:
            sock.sendall(f.read())

        logging.info("SEND_PHOTO: Data sent")
        final_msg = protocol.create_response_message(
            'OK', 'TEXT', f"File {SCREENSHOT_FILENAME} sent successfully."
        )
        protocol.send_message(sock, final_msg)

        return 'COMPLETED_RESPONSE', 'TEXT', 'N/A'

    except Exception as e:
        logging.error(f"SEND_PHOTO error: {e}")
        err_msg = protocol.create_response_message('ERROR', 'TEXT', f"Error: {e}")
        protocol.send_message(sock, err_msg)
        return 'COMPLETED_RESPONSE', 'TEXT', 'N/A'


def handle_exit(params: list, sock: socket.socket):
    """Handles the EXIT command."""
    logging.info("Handling EXIT")
    return 'OK', 'TEXT', 'Connection closing.'


if __name__ == "__main__":

    logging.basicConfig(filename='functions.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    print("--- Running Logic Tests (server_handlers.py) ---")
    logging.info("Starting Logic Tests for function.py handlers.")


    class MockSocket:

        def send(self, data): pass

        def sendall(self, data): pass

        def recv(self, size): return b''


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
        with open(TEST_FILE_ORIG, 'w') as f:
            f.write("Test content for copy.")
        assert os.path.exists(TEST_FILE_ORIG), "I/O Setup Failed: Original file not created."
        logging.info("Original file created.")

        # ב. COPY
        status_copy, _, data_copy = handle_copy([TEST_FILE_ORIG, TEST_FILE_COPY], mock_sock)
        assert status_copy == 'OK', f"I/O Test Failed: COPY command failed. Status: {status_copy}. Data: {data_copy}"
        assert os.path.exists(TEST_FILE_COPY), "I/O Test Failed: Copied file does not exist after command."
        logging.info("COPY successful.")

        # ג.  DELETE
        status_del_orig, _, data_del_orig = handle_delete([TEST_FILE_ORIG], mock_sock)
        assert status_del_orig == 'OK', (f"I/O Test Failed: DELETE (Original) command failed. Status: {status_del_orig}"
                                         f". Data: {data_del_orig}")
        assert not os.path.exists(TEST_FILE_ORIG), "I/O Test Failed: Original file still exists after delete."
        logging.info("DELETE (Original) successful.")

        # ד.  DELETE
        status_del_copy, _, data_del_copy = handle_delete([TEST_FILE_COPY], mock_sock)
        assert status_del_copy == 'OK', (f"I/O Test Failed: DELETE (Copy) command failed. Status: {status_del_copy}"
                                         f". Data: {data_del_copy}")
        assert not os.path.exists(TEST_FILE_COPY), "I/O Test Failed: Copied file still exists after delete."
        logging.info("DELETE (Copy) successful.")

    except Exception as e:
        # ERROR
        logging.error(f"CRITICAL FAIL:  Test failed - {e}", exc_info=True)
        raise

    finally:
        cleanup_io_test_files()
        logging.info("Temporary files removed.")

    # 1. DIR: Test default behavior
    logging.info("Testing DIR (Format Check)...")
    status, dtype, data = handle_dir([os.getcwd()], mock_sock)
    assert status == 'OK', "DIR: Failed to return OK status for valid path."
    assert dtype == 'LIST', "DIR: Failed to return LIST data type."
    assert isinstance(data, list), "DIR: Data must be a list."
    logging.info("DIR Test: Passed format and content type check.")

    # 2. EXECUTE: Test for missing parameter
    logging.info("Testing EXECUTE (Missing Param)...")
    status, dtype, data = handle_execute([], mock_sock)
    assert status == 'ERROR', "EXECUTE: Must return ERROR when missing program path."
    assert "Missing program path" in data, "EXECUTE: Wrong error message for missing path."
    logging.info("EXECUTE Test: Passed missing parameter check.")

    # 3. DELETE: Test for missing parameter
    logging.info("Testing DELETE (Missing Param)...")
    status, dtype, data = handle_delete([], mock_sock)
    assert status == 'ERROR', "DELETE: Must return ERROR when missing file path."
    assert "Missing file path" in data, "DELETE: Wrong error message for missing path."
    logging.info("DELETE Test: Passed missing parameter check.")

    # 4. COPY: Test for missing parameters
    logging.info("Testing COPY (Missing Param)...")
    status, dtype, data = handle_copy([], mock_sock)
    assert status == 'ERROR', "COPY: Must return ERROR when missing parameters (0)."
    status, dtype, data = handle_copy(["source.txt"], mock_sock)
    assert status == 'ERROR', "COPY: Must return ERROR when missing one parameter."
    logging.info("COPY Test: Passed missing parameters check.")

    # 5. SCREENSHOT: Testing the return format
    logging.info("Testing SCREENSHOT (Format Check)...")
    status, dtype, data = handle_screenshot([], mock_sock)
    assert status in ('OK', 'ERROR'), "SCREENSHOT: Must return OK or ERROR, but not unknown status."
    assert dtype == 'TEXT', "SCREENSHOT: Must return TEXT data type."
    logging.info("SCREENSHOT Test: Passed format check (Status: %s, Type: %s)", status, dtype)

    # 6. SEND_PHOTO: Check return format
    logging.info("Testing SEND_PHOTO (Format Check)...")
    status, dtype, data = handle_send_photo([], mock_sock)
    assert status == 'COMPLETED_RESPONSE', "SEND_PHOTO: Must return COMPLETED_RESPONSE to signal end of transfer."
    logging.info("SEND_PHOTO Test: Passed COMPLETED_RESPONSE check.")

    # 7. EXIT: Check closing status
    logging.info("Testing EXIT (Status Check)...")
    status, dtype, data = handle_exit([], mock_sock)
    assert status == 'OK', "EXIT: Must return OK status."
    logging.info("EXIT Test: Passed OK status check.")
    logging.info("All Command Asserts Passed Successfully!")
