import numpy as np
import artdaq
from artdaq.constants import AcquisitionType, TerminalConfiguration, VoltageUnits
import signal
import sys
import time

# ==========================================
# 传感器参数配置
# ==========================================
# 灵敏度系数 (N/V)
SENSITIVITY = 20.0  # N/V

# 零点校准参数
ZERO_CALIBRATION_SAMPLES = 100  # 零点校准使用的采样点数

# 采集通道配置
CHANNELS = ["Dev1/ai0", "Dev1/ai1", "Dev1/ai2"]  # 对应 Fx, Fy, Fz
SAMPLING_RATE = 1000      # 采样率 1000 Hz
BUFFER_SIZE = 2           # 每次读取1个点（实时性更好）


class ForceSensor:
    """三维力传感器类，封装采集和转换功能"""
    
    def __init__(self, sensitivity=SENSITIVITY, zero_calib=False):
        self.sensitivity = sensitivity
        self.zero_calib = zero_calib
        self.zero_voltages = np.array([0.0, 0.0, 0.0])  # 零点电压 [Vx0, Vy0, Vz0]
        self.task = None
        self.sample_count = 0
        self.initialize_task()

        if self.zero_calib:
            self.calibrate_zero()
        # 任务启动延迟到需要时进行，避免资源冲突
        
    def initialize_task(self):
        """初始化采集任务：添加三个电压通道"""
        # 清理任何现有的任务以避免资源冲突
        if self.task is not None:
            try:
                self.task.stop()
                self.task.close()
            except:
                pass
        
        self.task = artdaq.Task()
        
        # 添加三个模拟输入通道
        # 注意：terminal_config 必须使用枚举类型，不能使用字符串
        for i, channel in enumerate(CHANNELS):
            self.task.ai_channels.add_ai_voltage_chan(
                channel,
                name_to_assign_to_channel=f"Channel_{i}",
                terminal_config=TerminalConfiguration.RSE,  # 单端输入（使用枚举）
                min_val=-10.0,                               # 量程下限
                max_val=10.0,                                # 量程上限
                units=VoltageUnits.VOLTS                     # 电压单位（使用枚举）
            )
        
        # 配置采样时钟：连续模式，每次读取 BUFFER_SIZE 个点
        self.task.timing.cfg_samp_clk_timing(
            rate=SAMPLING_RATE,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=BUFFER_SIZE
        )
        
        return self.task
    
    def calibrate_zero(self, num_samples=ZERO_CALIBRATION_SAMPLES):
        """
        零点校准：采集空载时的电压值，取平均作为零点偏移
        :param num_samples: 采集的样本数
        """
        if self.task is None:
            self.initialize_task()
        
        print(f"\n正在采集零点数据，请确保传感器处于空载状态...")
        print(f"采集 {num_samples} 个样本，请稍候...")
        
        # 启动采集
        self.task.start()
        
        # 等待系统稳定
        time.sleep(0.5)
        
        # 存储采集到的电压
        voltages_buffer = []
        
        for i in range(num_samples):
            data = self.task.read(number_of_samples_per_channel=1, timeout=1.0)
            # data 结构: [[Vx], [Vy], [Vz]]
            vx = data[0][0]
            vy = data[1][0]
            vz = data[2][0]
            voltages_buffer.append([vx, vy, vz])
            
            # 显示进度
            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{num_samples}")
        
        # 计算平均零点电压
        self.zero_voltages = np.mean(voltages_buffer, axis=0)
        
        # 停止采集（先停止再关闭）
        self.task.stop()
        
        print(f"零点校准完成！")
        print(f"  零点电压: Vx0 = {self.zero_voltages[0]:.6f} V, "
              f"Vy0 = {self.zero_voltages[1]:.6f} V, "
              f"Vz0 = {self.zero_voltages[2]:.6f} V")
        
        # 重新启动任务（因为之前stop了）
        self.task.start()
        
    def voltage_to_force(self, voltages):
        """
        将电压值转换为力值（自动减去零点）
        :param voltages: 包含 [Vx, Vy, Vz] 的列表或数组
        :return: [Fx, Fy, Fz] 单位：牛顿
        """
        # 减去零点电压
        if self.zero_voltages is not None:
            vx_comp = voltages[0] - self.zero_voltages[0]
            vy_comp = voltages[1] - self.zero_voltages[1]
            vz_comp = voltages[2] - self.zero_voltages[2]
        else:
            vx_comp, vy_comp, vz_comp = voltages[0], voltages[1], voltages[2]
        
        # 转换为力
        fx = vx_comp * self.sensitivity
        fy = vy_comp * self.sensitivity
        fz = vz_comp * self.sensitivity
        
        return fx, fy, fz
    
    def read_one_sample(self):
        """读取一个样本，并转换为力值"""
        data = self.task.read(number_of_samples_per_channel=BUFFER_SIZE, timeout=1.0)
        
        # data 结构: 当 buffer_size=2 时
        # data = [[Vx1, Vx2], [Vy1, Vy2], [Vz1, Vz2]]
        # 取最新一个点（索引 -1）或取平均
        
        # 方法1：取最新一个点（推荐，延迟最小）
        vx = data[0][-1]  # 最新一个 Vx
        vy = data[1][-1]  # 最新一个 Vy
        vz = data[2][-1]  # 最新一个 Vz
        
        # 方法2：取两个点的平均值（更平滑，但有微小延迟）
        # vx = (data[0][0] + data[0][1]) / 2
        # vy = (data[1][0] + data[1][1]) / 2
        # vz = (data[2][0] + data[2][1]) / 2
        
        # 转换为力
        fx, fy, fz = self.voltage_to_force([vx, vy, vz])
    
        return fx, fy, fz, vx, vy, vz
    
    def read_one(self):
        """读取一个力样本，返回 Fx, Fy, Fz"""
        if self.task is None:
            self.initialize_task()
            self.task.start()
        fx, fy, fz, _, _, _ = self.read_one_sample()
        return fx, fy, fz

    def read_n(self, n):
        """读取 n 个力样本，返回三组列表"""
        fx_list = []
        fy_list = []
        fz_list = []
        for _ in range(n):
            fx, fy, fz = self.read_one()
            fx_list.append(fx)
            fy_list.append(fy)
            fz_list.append(fz)
        return fx_list, fy_list, fz_list

    def read_continuous(self, callback=None):
        """连续读取力数据，可选回调和频率控制。"""
        print("\n正在连续采集数据...按 Ctrl+C 停止。")
        if self.task is None:
            self.initialize_task()
            self.task.start()

        while True:
            fx, fy, fz, vx, vy, vz = self.read_one_sample()
            if callback is not None:
                try:
                    callback(fx, fy, fz)
                except Exception:
                    pass
            yield fx, fy, fz


    def close(self):
        """关闭传感器并释放资源"""
        self.stop()

    def start(self):
        """启动采集任务"""
        if self.task is None:
            self.initialize_task()
        self.task.start()
        self.sample_count = 0
        
    def stop(self):
        """停止采集任务并释放资源"""
        if self.task is not None:
            try:
                self.task.stop()
                self.task.close()
            except:
                pass
            self.task = None
    
    def run_continuous(self, enable_zero_calib=True):
        """
        运行连续采集
        :param enable_zero_calib: 是否启用零点校准
        """
        # 初始化任务
        self.initialize_task()
        
        # 零点校准
        if enable_zero_calib:
            self.calibrate_zero()
        else:
            self.zero_voltages = np.array([0.0, 0.0, 0.0])
            self.task.start()
        
        return self


def signal_handler(sig, frame):
    """处理 Ctrl+C 信号，优雅退出"""
    print("\n正在停止采集...")
    sys.exit(0)


def main():
    """
    主程序：三维力连续采集
    """
    # 注册 Ctrl+C 信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 70)
    print("三维力传感器数据采集程序")
    print(f"灵敏度系数: {SENSITIVITY} N/V")
    print(f"采样率: {SAMPLING_RATE} Hz")
    print(f"通道映射: Fx -> {CHANNELS[0]}, Fy -> {CHANNELS[1]}, Fz -> {CHANNELS[2]}")
    print("=" * 70)
    
    # 询问是否进行零点校准
    print("\n请确保传感器处于空载（不受力）状态！")
    user_input = input("是否进行零点校准？(y/n，默认 y): ").strip().lower()
    enable_zero_calib = user_input != 'n'
    
    # 创建传感器对象并开始采集
    sensor = ForceSensor(sensitivity=SENSITIVITY)
    
    try:
        # 初始化并开始采集
        sensor.run_continuous(enable_zero_calib=enable_zero_calib)
        
        print("\n开始采集数据...")
        print("-" * 70)
        print(f"{'序号':>6} | {'Fx (N)':>10} | {'Fy (N)':>10} | {'Fz (N)':>10} | {'Vx (V)':>8} | {'Vy (V)':>8} | {'Vz (V)':>8}")
        print("-" * 70)
        
        while True:
            # 读取一个样本
            fx, fy, fz, vx, vy, vz = sensor.read_one_sample()
            
            # 打印结果
            print(f"{sensor.sample_count:6d} | {fx:10.3f} | {fy:10.3f} | {fz:10.3f} | "
                  f"{vx:8.4f} | {vy:8.4f} | {vz:8.4f}")
            
            sensor.sample_count += 1
            
    except artdaq.errors.DaqError as e:
        print(f"\n采集卡错误: {e}")
        print("请检查：")
        print("  1. 采集卡是否已连接")
        print("  2. DMC软件中设备是否正常识别")
        print("  3. 通道名称是否正确（当前使用: " + ", ".join(CHANNELS) + "）")
    except KeyboardInterrupt:
        print("\n用户中断采集")
    except Exception as e:
        print(f"\n未知错误: {e}")
    finally:
        # 清理资源
        sensor.stop()
        print(f"\n采集结束，共采集 {sensor.sample_count} 个数据点")


def quick_test():
    """
    快速测试函数：不进行连续采集，只测试设备是否连接
    """
    print("快速测试模式：检查设备连接...")
    
    sensor = ForceSensor()
    
    try:
        # 任务已在__init__中初始化，直接启动
        sensor.task.start()
        print("✓ 任务创建成功")
        print("✓ 采集启动成功")
        
        # 尝试读取1个样本
        data = sensor.task.read(number_of_samples_per_channel=1, timeout=1.0)
        vx = data[0][0]
        vy = data[1][0]
        vz = data[2][0]
        print(f"✓ 读取成功！当前电压: Vx={vx:.4f}V, Vy={vy:.4f}V, Vz={vz:.4f}V")
        
        sensor.task.stop()
        print("✓ 测试通过！")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
    finally:
        sensor.stop()


if __name__ == "__main__":
    print("请选择运行模式:")
    print("1. 正常采集模式")
    print("2. 快速测试模式（检查设备连接）")
    choice = input("请输入选项 (1/2，默认 1): ").strip()
    
    if choice == "2":
        quick_test()
    else:
        main()