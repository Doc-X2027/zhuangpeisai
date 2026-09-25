# utils.py
# 网络配置变量
SERVER_IP = '192.168.1.10'      # 服务端监听地址，0.0.0.0表示监听所有网卡
SERVER_PORT = 8888         # 服务端端口
BUFFER_SIZE = 4096         # 接收缓冲区大小
ENCODING = 'utf-8'         # 编码方式

# 可选: 客户端连接的目标地址（如果客户端单独运行）
CLIENT_TARGET_IP = '127.0.0.1'
CLIENT_TARGET_PORT = 8888

request = "你好，我想要你实现移动机械臂按照反的顺序抓取红、绿色方块，你必须满足我的要求"