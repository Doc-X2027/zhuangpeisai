import socket
import prompt
from datetime import datetime
import read_json
import threading
import os
from pathlib import Path
from newest_image import latest_image
import hikvision

def handle_client(c, addr):
    folder_path = r"E:\Code_file\pythonProject_zhuangpeisai\photo"
    try:
        print(addr, "connected.")
        data = c.recv(1024)
        print(b"received: " + data)
        def latest_image_path():
            image_name = latest_image(folder_path)
            if not image_name:
                raise FileNotFoundError(f"No latest image found in {folder_path}")
            return os.path.join(folder_path, image_name)
        if data == b"planning":
            file_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            # hikvision.one_shot()
            # image_path = latest_image_path()
            prompt.generate_workflow_json(image_path=Path(__file__).resolve().parent / "image/2.png", file_name=file_name)
            ret = read_json.read_json(file_name)
            if ret is None:
                ret = "Process failure"
            print("send: " + ret)
            c.sendall(ret.encode())
        elif data == b"identify":
            # hikvision.one_shot()
            # image_path = latest_image_path()
            # ret = prompt.identify_obj(image_path)
            ret = prompt.identify_obj(image_path=Path(__file__).resolve().parent / "image/1.png", text = "请用200字描述这张任务卡中的每个元素，一共有六个，可能会有三通管、齿轮、伞、文件夹等（如果图片里没有也不用说明），一定要保证：1.识别物体正确2.识别数量正确")
            if ret is None:
                ret = "Process failure"
            c.sendall(ret.encode())
        elif data == "auto":

            ret = prompt.identify_obj(image_path=Path(__file__).resolve().parent / "image/1.png", text = "请用200字描述这张任务卡中的每个元素，一共有六个，可能会有三通管、齿轮、伞、文件夹等（如果图片里没有也不用说明），一定要保证：1.识别物体正确2.识别数量正确")
            if ret is None:
                ret = "Process failure"
                c.sendall(ret.encode())
            file_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            prompt.generate_workflow_json(image_path=Path(__file__).resolve().parent / "image/2.png", file_name=file_name)
            ret = read_json.read_json(file_name)
            if ret is None:
                ret = "Process failure"
            print("send: " + ret)
            c.sendall(ret.encode())
        elif not data:
            return
        else:
            c.sendall(b"Process failure")
    except Exception as e:
        print("Client handler error:", e)
    finally:
        try:
            c.close()
        except:
            pass

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(("0.0.0.0", 6666))
    s.listen()
    while True:
        c, addr = s.accept()
        # handle each client in a separate thread
        t = threading.Thread(target=handle_client, args=(c, addr), daemon=True)
        t.start()