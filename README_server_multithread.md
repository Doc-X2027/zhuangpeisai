# server_multithread.py 交接运行说明

## 准备环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 配置和启动

```powershell
$env:DASHSCOPE_API_KEY="你的 API Key"
$env:CAMERA_HOST="192.168.1.10"
$env:CAMERA_PORT="6000"
python server_multithread.py
```

默认读取程序旁边的 `photo` 文件夹，并把工作流写入 `output` 文件夹；目录不存在会自动创建。相机图片必须命名为 `color_<数字>.<扩展名>`，例如 `color_12.jpg`。

如需使用其他目录：

```powershell
python server_multithread.py --photo-dir "D:\camera\photo" --output-dir "D:\camera\output"
```

完整环境变量见 `.env.example`（程序不会自动加载该文件）。默认监听所有网卡的 TCP 8888 端口。客户端发送 `planning` 或 `identify`。其他电脑连接时使用服务器的局域网 IP，并确认 Windows 防火墙允许 TCP 8888 入站。
