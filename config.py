# config.py
# 机器人导纳控制配置文件

# 机械臂配置
ROBOT_IP = "127.0.0.1"          # 机械臂IP地址
ROBOT_PORT = 30004               # 端口号
ROBOT_USER = "aubo"
ROBOT_PASSWORD = "123456"

# 导纳控制器参数
# Md: 质量矩阵(kg), Bd: 阻尼矩阵(N·s/m), Kd: 刚度矩阵(N/m)
ADMITTANCE_PARAMS = {
    "Md": [2.0, 2.0, 2.0],      # X, Y, Z方向虚拟质量
    "Bd": [50.0, 50.0, 100.0],  # X, Y, Z方向阻尼
    "Kd": [500.0, 500.0, 1000.0] # X, Y, Z方向刚度
}

# 期望接触力(N) - 根据任务需求调整
DESIRED_FORCE = [0.0, 0.0, 10.0]   # 例如：Z方向期望10N接触力
# DESIRED_FORCE = [5.0, 0.0, 5.0]   # 斜向接触力示例

# 控制周期(s)
CONTROL_DT = 0.004      # 250Hz

# 运动限制
MAX_POSITION_CORRECTION = 0.02      # 最大位置修正量(m)
MAX_VELOCITY = 0.5                   # 最大速度(m/s)
MAX_FORCE = 50.0                     # 最大接触力保护(N)

# 运动参数
MOVE_SPEED = 0.3        # 直线运动速度(m/s)
MOVE_ACC = 0.2          # 直线运动加速度(m/s²)
JOINT_SPEED = 0.5       # 关节运动速度(rad/s)

# 调试模式
DEBUG_MODE = True