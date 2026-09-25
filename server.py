import socket
import prompt
from datetime import datetime
import read_json
import threading

file_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
# text = voice.run()
request = "你好，我想要你实现移动机械臂按照顺序抓取橙、蓝、黄、红、绿、紫色方块，你必须满足我的要求，分别放入红、绿、蓝、黄、紫、橙色盘中"


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(("0.0.0.0", 8888))
    s.listen()
    c, addr = s.accept()
    with c:
        print(addr, "connected.")
        while True:
            data = c.recv(1024)
            print(data)
            if data == b"planning":
                prompt.generate_workflow_json(request, file_name)
                ret = read_json.read_json(file_name)
                # ret = read_json.read_json("workflow_20260530_191723.json")
                print("send: " + ret)
                c.sendall(ret.encode())
                break
            if not data:
                break
            c.sendall(b"Process failure")