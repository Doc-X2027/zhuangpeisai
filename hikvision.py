import os
import socket
import time


def one_shot(host, port=6000, timeout=10.0):
    """Send the capture command to the photo service on the App host."""
    if not host or host == "未检测到":
        raise ValueError("无法读取 App 本机 IP，不能发送拍照指令")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect((host, port))
        connection.sendall(b"123")
        time.sleep(3)


if __name__ == "__main__":
    one_shot("127.0.0.1")
