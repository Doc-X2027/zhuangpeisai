# my_main.py
from force_sensor import ForceSensor
import numpy as np

# 创建传感器实例
sensor = ForceSensor(zero_calib=True)

# 读取单次数据
fx, fy, fz = sensor.read_one()
print(f"力: Fx={fx:.2f}N, Fy={fy:.2f}N, Fz={fz:.2f}N")

# 读取10个数据
fx_list, fy_list, fz_list = sensor.read_n(10)
print(f"平均力: Fx={np.mean(fx_list):.2f}N")

# 连续采集（带回调）
def on_force_update(fx, fy, fz):
    print(f"当前力: Fx={fx:.2f}N, Fy={fy:.2f}N, Fz={fz:.2f}N")

print("开始连续采集（按 Ctrl+C 停止）...")
for fx, fy, fz in sensor.read_continuous(callback=on_force_update):
    if abs(fx) > 100 or abs(fy) > 100 or abs(fz) > 100:
        print("检测到力超过阈值，停止采集。")
        break

# 关闭
sensor.close()