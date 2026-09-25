import os
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    host = os.environ.get("SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("SERVER_PORT", "8888"))
    s.settimeout(10)
    s.connect((host, port))
    s.sendall(input("输入发送字符（planning;identify）：\n").encode())
    data = s.recv(1024)
    print("Received:", repr(data))
