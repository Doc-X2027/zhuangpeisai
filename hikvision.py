import os
import socket
import time


def one_shot():
    host = os.getenv("CAMERA_HOST", "192.168.32.100")
    port = int(os.getenv("CAMERA_PORT", "6000"))
    timeout = float(os.getenv("CAMERA_TIMEOUT", "10"))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect((host, port))
        connection.sendall(b"123")
        time.sleep(3)


if __name__ == "__main__":
    one_shot()
