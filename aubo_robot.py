# aubo_robot.py
# AUBO-E5 机械臂接口封装

import time
import math
import numpy as np
from typing import List, Tuple, Optional
import pyaubo_sdk


class AuboRobot:
    """
    AUBO-E5 机械臂接口类
    封装SDK的基本运动指令
    """
    
    def __init__(self, ip: str, port: int, username: str, password: str):
        """
        初始化机械臂连接
        
        Args:
            ip: 机械臂IP地址
            port: 端口号
            username: 用户名
            password: 密码
        """
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        
        self.rpc_client = None
        self.robot_interface = None
        self.robot_name = None
        
        self.is_connected = False
        self.is_logined = False
        
        # TCP偏移(法兰到工具坐标系)
        self.tcp_offset = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        
        # 速度比率(0~1)
        self.speed_fraction = 0.75
    
    def connect(self) -> bool:
        """连接机械臂"""
        try:
            self.rpc_client = pyaubo_sdk.RpcClient()
            self.rpc_client.setRequestTimeout(1000)
            self.rpc_client.connect(self.ip, self.port)
            
            if self.rpc_client.hasConnected():
                print(f"RPC客户端连接成功: {self.ip}:{self.port}")
                self.is_connected = True
                return True
            else:
                print("RPC客户端连接失败")
                return False
        except Exception as e:
            print(f"连接异常: {e}")
            return False
    
    def login(self) -> bool:
        """登录机械臂"""
        if not self.is_connected:
            print("请先连接机械臂")
            return False
        
        try:
            self.rpc_client.login(self.username, self.password)
            if self.rpc_client.hasLogined():
                print("登录成功")
                self.is_logined = True
                
                # 获取机械臂名称
                self.robot_name = self.rpc_client.getRobotNames()[0]
                self.robot_interface = self.rpc_client.getRobotInterface(self.robot_name)
                
                # 设置TCP偏移
                self.robot_interface.getRobotConfig().setTcpOffset(self.tcp_offset)
                # 设置速度比率
                self.robot_interface.getMotionControl().setSpeedFraction(self.speed_fraction)
                
                return True
            else:
                print("登录失败")
                return False
        except Exception as e:
            print(f"登录异常: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        if self.is_logined:
            self.rpc_client.logout()
        if self.is_connected:
            self.rpc_client.disconnect()
        self.is_connected = False
        self.is_logined = False
        print("机械臂连接已断开")
    
    def set_speed_fraction(self, fraction: float) -> None:
        """设置速度比率(0~1)"""
        self.speed_fraction = max(0.0, min(1.0, fraction))
        if self.robot_interface:
            self.robot_interface.getMotionControl().setSpeedFraction(self.speed_fraction)
    
    def set_tcp_offset(self, offset: List[float]) -> None:
        """设置TCP偏移 [x, y, z, rx, ry, rz]"""
        self.tcp_offset = offset
        if self.robot_interface:
            self.robot_interface.getRobotConfig().setTcpOffset(offset)
    
    def _wait_arrival(self, timeout: float = 10.0) -> bool:
        """等待运动完成"""
        start_time = time.time()
        max_retry = 5
        cnt = 0
        
        try:
            # 等待开始运动
            exec_id = self.robot_interface.getMotionControl().getExecId()
            while exec_id == -1:
                if cnt > max_retry:
                    return False
                if time.time() - start_time > timeout:
                    return False
                time.sleep(0.05)
                cnt += 1
                exec_id = self.robot_interface.getMotionControl().getExecId()
            
            # 等待运动完成
            while self.robot_interface.getMotionControl().getExecId() != -1:
                if time.time() - start_time > timeout:
                    return False
                time.sleep(0.05)
            
            return True
        except Exception as e:
            print(f"等待运动异常: {e}")
            return False
    
    def move_joint(self, q: List[float], speed: float = 0.5, 
                   acc: float = 0.5, wait: bool = True) -> bool:
        """
        关节运动
        
        Args:
            q: 关节角度(弧度)
            speed: 速度(rad/s)
            acc: 加速度(rad/s²)
            wait: 是否等待运动完成
        """
        if not self.robot_interface:
            return False
        
        try:
            self.robot_interface.getMotionControl().moveJoint(q, speed, acc, 0, 0)
            
            if wait:
                return self._wait_arrival()
            return True
        except Exception as e:
            print(f"关节运动异常: {e}")
            return False
    
    def move_line(self, pose: List[float], speed: float = 0.3, 
                  acc: float = 0.2, wait: bool = True) -> bool:
        """
        直线运动
        
        Args:
            pose: 位姿 [x, y, z, rx, ry, rz] (位置:米, 姿态:弧度)
            speed: 速度(m/s)
            acc: 加速度(m/s²)
            wait: 是否等待运动完成
        """
        if not self.robot_interface:
            return False
        
        try:
            self.robot_interface.getMotionControl().moveLine(pose, speed, acc, 0, 0)
            
            if wait:
                return self._wait_arrival()
            return True
        except Exception as e:
            print(f"直线运动异常: {e}")
            return False
    
    def move_pose(self, pose: List[float], speed: float = 0.3,
                  acc: float = 0.2, wait: bool = True) -> bool:
        """位姿运动"""
        return self.move_line(pose, speed, acc, wait)
    
    def move_pose_corrected(self, target_pose: List[float], 
                            correction: np.ndarray,
                            speed: float = 0.3, acc: float = 0.2,
                            wait: bool = True) -> List[float]:
        """
        应用位置修正后的位姿运动
        姿态保持不变(旋转自由度不参与导纳控制)
        
        Args:
            target_pose: 原始目标位姿 [x, y, z, rx, ry, rz]
            correction: 位置修正量 [dx, dy, dz]
            speed: 速度(m/s)
            acc: 加速度(m/s²)
            wait: 是否等待
            
        Returns:
            corrected_pose: 修正后的位姿
        """
        corrected_pose = target_pose.copy()
        corrected_pose[0] += correction[0]  # x
        corrected_pose[1] += correction[1]  # y
        corrected_pose[2] += correction[2]  # z
        # 姿态保持不变: rx, ry, rz 不修正
        
        self.move_line(corrected_pose, speed, acc, wait)
        return corrected_pose
    
    def get_current_joint_positions(self) -> List[float]:
        """获取当前关节角度(弧度)"""
        if self.robot_interface:
            return self.robot_interface.getRobotState().getJointsPosition()
        return [0.0] * 6
    
    def get_current_pose(self) -> List[float]:
        """获取当前末端位姿 [x, y, z, rx, ry, rz]"""
        if self.robot_interface:
            return self.robot_interface.getRobotState().getTcpPose()
        return [0.0] * 6
    
    def get_current_position(self) -> Tuple[float, float, float]:
        """获取当前位置(x, y, z)"""
        pose = self.get_current_pose()
        return (pose[0], pose[1], pose[2])
    
    def get_current_orientation(self) -> Tuple[float, float, float]:
        """获取当前末端姿态(rx, ry, rz)"""
        pose = self.get_current_pose()
        return (pose[3], pose[4], pose[5])
    
    def stop(self) -> None:
        """急停"""
        if self.robot_interface:
            self.robot_interface.getMotionControl().stop()
    
    def is_moving(self) -> bool:
        """检查机械臂是否正在运动"""
        if self.robot_interface:
            return self.robot_interface.getMotionControl().getExecId() != -1
        return False