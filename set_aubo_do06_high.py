#!/usr/bin/env python3
"""将 AUBO 控制柜的标准数字输出 DO06 置为高电平。

说明：DI06 是物理输入，只能读取，不能通过 AUBO SDK 写入。如果确实需要让
DI06 变为高电平，需要由外部电路驱动；也可以按控制柜接线规范将某个 DO
回接到 DI06，再控制该 DO。
"""

from __future__ import annotations

import argparse
import sys

import pyaubo_sdk


DEFAULT_IP = "192.168.34.200"
DEFAULT_PORT = 30004
DEFAULT_USERNAME = "aubo"
DEFAULT_PASSWORD = "123456"
DO_INDEX = 6  # DO06；AUBO SDK 的标准数字 IO 编号从 0 开始


def set_do06_high(ip: str, port: int, username: str, password: str) -> None:
    """连接控制器，将 DO06 置高，并回读确认。"""
    client = pyaubo_sdk.RpcClient()
    client.setRequestTimeout(1000)

    try:
        client.connect(ip, port)
        if not client.hasConnected():
            raise ConnectionError(f"无法连接机器人：{ip}:{port}")

        client.login(username, password)
        if not client.hasLogined():
            raise PermissionError("机器人登录失败，请检查用户名和密码")

        robot_names = client.getRobotNames()
        if not robot_names:
            raise RuntimeError("控制器未返回机器人名称")

        robot = client.getRobotInterface(robot_names[0])
        io = robot.getIoControl()

        output_count = io.getStandardDigitalOutputNum()
        if DO_INDEX >= output_count:
            raise IndexError(
                f"控制器只有 {output_count} 路标准数字输出，DO06 不存在"
            )

        result = io.setStandardDigitalOutput(DO_INDEX, True)
        if result not in (None, 0):
            raise RuntimeError(f"设置 DO06 失败，SDK 返回码：{result}")

        actual = bool(io.getStandardDigitalOutput(DO_INDEX))
        if not actual:
            raise RuntimeError("DO06 写入后回读仍为低电平")

        print(f"成功：{ip} 的 DO06 已置为高电平")
    finally:
        if client.hasLogined():
            client.logout()
        if client.hasConnected():
            client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 AUBO 机器人的 DO06 置为高电平")
    parser.add_argument("--ip", default=DEFAULT_IP, help="机器人控制器 IP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="RPC 端口")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="登录用户名")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="登录密码")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        set_do06_high(args.ip, args.port, args.username, args.password)
        return 0
    except Exception as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
