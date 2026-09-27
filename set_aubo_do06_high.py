#!/usr/bin/env python3
"""在 AUBO 仿真控制器中执行 DI06 的“启动工程”等效动作。

DI06 是输入点，只能读取，不能通过 SDK 写高。真实控制柜需要外部电路驱动
DI06；仿真控制器则通过 RuntimeMachine.runProgram() 启动已加载工程。
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time


DEFAULT_IP = "192.168.34.10"
DEFAULT_PORT = 30004
DEFAULT_USERNAME = "aubo"
DEFAULT_PASSWORD = "123456"
DI_INDEX = 6


class AuboJsonRpcClient:
    """Minimal client for the JSON-RPC protocol documented by AUBO SDK."""

    def __init__(self, ip: str, port: int, timeout: float = 5.0) -> None:
        try:
            self.connection = socket.create_connection((ip, port), timeout=timeout)
        except (TimeoutError, OSError) as exc:
            raise ConnectionError(
                f"无法连接 AUBO RPC {ip}:{port}；请确认虚拟机已启动，且宿主机与机械臂处于同一网段"
            ) from exc
        self.connection.settimeout(timeout)
        self._next_id = 1
        self._buffer = ""

    def close(self) -> None:
        self.connection.close()

    def call(self, method: str, params: list | None = None):
        request_id = self._next_id
        self._next_id += 1
        request = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": request_id}
        self.connection.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
        decoder = json.JSONDecoder()
        while True:
            candidate = self._buffer.lstrip()
            try:
                response, end = decoder.raw_decode(candidate)
                self._buffer = candidate[end:]
                break
            except json.JSONDecodeError:
                chunk = self.connection.recv(4096)
                if not chunk:
                    raise ConnectionError("AUBO RPC 服务在返回完整 JSON 前关闭了连接")
                self._buffer += chunk.decode("utf-8")
        if response.get("id") != request_id:
            raise RuntimeError(f"AUBO RPC 响应 ID 不匹配：{response}")
        if response.get("error"):
            raise RuntimeError(f"AUBO RPC {method} 失败：{response['error']}")
        return response.get("result")


def start_program_from_di06(ip: str, port: int, username: str, password: str) -> None:
    """Validate DI06 and start the loaded project in the simulator."""
    client = AuboJsonRpcClient(ip, port)
    try:
        try:
            login_result = client.call("login", [username, password])
            if login_result not in (None, 0, True):
                raise PermissionError("机器人登录失败，请检查用户名和密码")
        except RuntimeError as exc:
            # ARCS simulation exposes the documented robot JSON-RPC methods
            # directly; login is a pyaubo_sdk client operation, not an RPC
            # method, and therefore legitimately returns -32601.
            if "-32601" not in str(exc):
                raise
        robot_names = client.call("getRobotNames")
        if not robot_names:
            raise RuntimeError("控制器未返回机器人名称")
        io_method = f"{robot_names[0]}.IoControl."
        input_count = client.call(io_method + "getStandardDigitalInputNum")
        if DI_INDEX >= input_count:
            raise IndexError(f"控制器只有 {input_count} 路标准数字输入，DI06 不存在")
        di_state = bool(client.call(io_method + "getStandardDigitalInput", [DI_INDEX]))
        status = client.call("RuntimeMachine.getStatus")
        # A project left in Running may actually be blocked in its previous
        # socket receive/connect call.  Task 2 needs a fresh execution so the
        # Lua program reconnects and sends a new `read` every time.
        if status != "Stopped":
            stop_result = client.call("RuntimeMachine.stop")
            if stop_result not in (None, 0):
                raise RuntimeError(f"停止旧工程失败，控制器返回码：{stop_result}")
            for _attempt in range(50):
                status = client.call("RuntimeMachine.getStatus")
                if status == "Stopped":
                    break
                time.sleep(0.1)
            if status != "Stopped":
                raise RuntimeError(f"旧工程未停止，运行时状态为 {status}")
        result = client.call("RuntimeMachine.runProgram")
        if result not in (None, 0):
            raise RuntimeError(f"启动机械臂工程失败，控制器返回码：{result}")
        final_status = status
        for _attempt in range(40):
            final_status = client.call("RuntimeMachine.getStatus")
            if final_status == "Running":
                break
            time.sleep(0.05)
        if final_status != "Running":
            raise RuntimeError(f"已发送启动指令，但运行时状态为 {final_status}")
        print(f"成功：{ip} 的机械臂工程已运行（DI06 当前为 {'高' if di_state else '低'}电平）")
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行 AUBO 仿真 DI06 的启动工程等效动作")
    parser.add_argument("--ip", default=DEFAULT_IP, help="机器人控制器 IP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="RPC 端口")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="登录用户名")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="登录密码")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        start_program_from_di06(args.ip, args.port, args.username, args.password)
        return 0
    except Exception as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
