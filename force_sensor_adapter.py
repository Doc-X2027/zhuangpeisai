# 新增文件: force_sensor_adapter.py
import numpy as np
import time
from typing import Tuple, Optional


class ForceSensorAdapter:
    """三维力传感器适配器 - 将三维力数据适配为导纳控制所需格式"""

    def __init__(self, sensor_instance):
        self.sensor = sensor_instance
        self.zero_offset = [0.0, 0.0, 0.0]
        self.gravity_compensation_enabled = False
        self.gravity_params = {'mass': 0.0, 'com': [0.0, 0.0, 0.0]}

    def set_zero_offset(self, fx_zero: float, fy_zero: float, fz_zero: float):
        """设置零点偏移"""
        self.zero_offset = [fx_zero, fy_zero, fz_zero]

    def enable_gravity_compensation(self, mass: float, com_x: float, com_y: float, com_z: float):
        """启用重力补偿"""
        self.gravity_compensation_enabled = True
        self.gravity_params = {'mass': mass, 'com': [com_x, com_y, com_z]}

    def get_force(self, current_pose: Optional[list] = None) -> Tuple[float, float, float, float, float, float]:
        """
        获取六维力数据（三维传感器返回的力矩始终为0）
        返回格式: (Fx, Fy, Fz, Tx, Ty, Tz)
        """
        # 读取三维力数据
        fx, fy, fz = self.sensor.read_one()

        # 减去零点偏移
        fx -= self.zero_offset[0]
        fy -= self.zero_offset[1]
        fz -= self.zero_offset[2]

        # 重力补偿（如果有当前姿态）
        if self.gravity_compensation_enabled and current_pose:
            # 根据当前姿态计算重力分量并扣除
            gravity_comp = self._calculate_gravity_component(current_pose)
            fx -= gravity_comp[0]
            fy -= gravity_comp[1]
            fz -= gravity_comp[2]

        # 三维传感器返回的力矩为0
        return (fx, fy, fz, 0.0, 0.0, 0.0)

    def _calculate_gravity_component(self, pose: list) -> Tuple[float, float, float]:
        """根据当前姿态计算重力分量（简化实现）"""
        # 这里需要根据实际机械臂姿态计算重力在不同方向的分量
        # 简化：假设工具垂直向下时重力完全在Z方向
        mass = self.gravity_params['mass']
        g = 9.8
        return (0.0, 0.0, mass * g)