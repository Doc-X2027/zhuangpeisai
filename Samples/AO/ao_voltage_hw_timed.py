import artdaq
import time
from artdaq.constants import (AcquisitionType, Edge, RegenerationMode)

# # 单通道多采样
with artdaq.Task() as task:
    task.ao_channels.add_ao_voltage_chan('Dev1/ao0')
    task.timing.cfg_samp_clk_timing(1000)
    print('1 Channel N Samples Write: ')
    print(task.write([1.1, 2.2, 3.3, 4.4, 5.5], auto_start=True))
    task.stop()

# 多通道多采样
with artdaq.Task("a") as task:
    task.ao_channels.add_ao_voltage_chan('Dev1/ao1:2')
    task.timing.cfg_samp_clk_timing(1000)
    print('N Channel N Samples Write: ')
    print(task.write([[1.1, 2.2, 3.3], [1.1, 2.2, 4.4]],
                     auto_start=False))
    task.start()
    task.wait_until_done()
    task.stop()

# 连续采样-可重生成模式
with artdaq.Task("b") as task:
    task.ao_channels.add_ao_voltage_chan('Dev1/ao3')
    task.out_stream.regen_mode = RegenerationMode.ALLOW_REGENERATION
    task.timing.cfg_samp_clk_timing(1000.0, active_edge=Edge.RISING, sample_mode=AcquisitionType.CONTINUOUS)
    print('N Channel N Samples Write: ')
    print(task.write([1.1, 2.2, 3.3], auto_start=False))
    task.start()
    for _ in range(50):
        task.is_task_done()
        time.sleep(0.1)
    task.stop()

# # 连续采样-可重生成模式-开始触发
with artdaq.Task("c") as task:
    task.ao_channels.add_ao_voltage_chan('Dev1/ao0:1')
    task.out_stream.regen_mode = RegenerationMode.ALLOW_REGENERATION
    task.timing.cfg_samp_clk_timing(1000.0, active_edge=Edge.RISING, sample_mode=AcquisitionType.CONTINUOUS)
    task.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev1/PFI1")
    print('N Channel N Samples Write: ')
    print(task.write([[1.1, 2.2, 3.3], [1.1, 2.2, 4.4]],
                     auto_start=False))
    task.start()
    for _ in range(50):
        task.is_task_done()
        time.sleep(0.1)
    task.stop()
