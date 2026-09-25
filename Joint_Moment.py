#! /usr/bin/env python
# coding=utf-8

"""
获取机械臂状态信息

步骤:
第一步: 连接到 RPC 服务
第二步: 机械臂登录
第三步: 获取机械臂状态信息
"""

import pyaubo_sdk

import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import time
import matplotlib
matplotlib.use('TkAgg')

# 设置中文字体，解决乱码问题
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'KaiTi']
# 解决负号显示异常的问题
matplotlib.rcParams['axes.unicode_minus'] = False

robot_ip = "192.168.1.50"  # 服务器 IP 地址
robot_port = 30004  # 端口号
M_PI = 3.14159265358979323846
robot_rpc_client = pyaubo_sdk.RpcClient()


def realtime_plot(data_source_func, joint_index=0, max_points=1000, update_interval=0.1):
    """
    实时绘制持续更新的变量

    参数:
        data_source_func: 可调用对象，每次调用返回新的数据点（数值列表或单个数值）
        joint_index: 要绘制的关节索引（0-5），默认为0
        max_points: 图表显示的最大数据点数
        update_interval: 更新间隔（秒）
    """
    plt.ion()  # 开启交互模式
    fig, ax = plt.subplots()

    # 使用双端队列存储数据，自动移除旧数据
    data_queue = deque(maxlen=max_points)

    # 初始化绘图对象
    line, = ax.plot([], [], 'b-', linewidth=2)
    ax.set_xlim(0, max_points)
    ax.set_ylim(-50, 50)  # 力矩范围根据实际情况调整
    ax.set_xlabel('时间点')
    ax.set_ylabel(f'关节{joint_index + 1} 力矩 (Nm)')
    ax.set_title(f'机械臂关节{joint_index + 1} 实时力矩监控')
    ax.grid(True)

    try:
        while True:
            # 获取新数据
            result = data_source_func()

            # 处理返回值：如果是列表则取指定关节，否则直接使用
            if isinstance(result, (list, tuple)):
                new_value = result[joint_index] if len(result) > joint_index else result[0]
            else:
                new_value = result

            print(f"关节{joint_index + 1}力矩: {new_value:.3f} Nm")
            data_queue.append(new_value)

            # 更新图形数据
            x_data = list(range(len(data_queue)))
            y_data = list(data_queue)
            line.set_data(x_data, y_data)

            # 动态调整y轴范围（可选）
            if y_data:
                y_min, y_max = min(y_data), max(y_data)
                margin = (y_max - y_min) * 0.1 if y_max != y_min else 1
                ax.set_ylim(y_min - margin, y_max + margin)

            # 调整x轴范围
            if len(data_queue) == max_points:
                ax.set_xlim(len(data_queue) - max_points, len(data_queue))
            else:
                ax.set_xlim(0, max_points)

            # 重绘
            fig.canvas.draw()
            fig.canvas.flush_events()

            time.sleep(update_interval)

    except KeyboardInterrupt:
        print("\n绘图已停止")
    finally:
        plt.ioff()
        plt.show()


if __name__ == '__main__':
    robot_rpc_client.connect(robot_ip, robot_port)  # 接口调用: 连接 RPC 服务
    if robot_rpc_client.hasConnected():
        print("Robot rpc_client connected successfully!")
        robot_rpc_client.login("aubo", "123456")  # 接口调用: 机械臂登录
        if robot_rpc_client.hasLogined():
            print("Robot rpc_client logined successfully!")
            robot_name = robot_rpc_client.getRobotNames()[0]  # 接口调用: 获取机器人的名字

            # 创建一个lambda函数来获取关节力矩列表
            robot_interface = robot_rpc_client.getRobotInterface(robot_name)

            # 绘制关节1的力矩（索引0），可以修改为0-5之间的任意值
            realtime_plot(
                lambda: robot_interface.getRobotState().getJointTorqueSensors(),
                joint_index=3,  # 选择要绘制的关节（0-5）
                max_points=1000,
                update_interval=0.01
            )
            # joint_torque_sensors = robot_rpc_client.getRobotInterface(robot_name).getRobotState().getJointTorqueSensors()
            # print("机械臂关节力矩:", joint_torque_sensors)
            # joint_target_torques = robot_rpc_client.getRobotInterface(robot_name).getRobotState().getJointTargetTorques()
            # print("机械臂关节目标力矩:", joint_target_torques)
            # tcp_force = robot_rpc_client.getRobotInterface(robot_name).getRobotState().getTcpForce()
            # print("TCP的力 / 力矩:", tcp_force)