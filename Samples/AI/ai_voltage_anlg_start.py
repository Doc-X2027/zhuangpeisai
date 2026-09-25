import pprint
import artdaq
from artdaq.constants import AcquisitionType, TaskMode

pp = pprint.PrettyPrinter(indent=4)

# 开始触发_模拟边沿
with artdaq.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0:1")
    task.timing.cfg_samp_clk_timing(
        1000, sample_mode=AcquisitionType.CONTINUOUS)
    task.triggers.start_trigger.cfg_anlg_edge_start_trig("Dev1/ai0")
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)
# 开始触发_数字边沿
with artdaq.Task("a") as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai2")
    task.timing.cfg_samp_clk_timing(
        1000, sample_mode=AcquisitionType.CONTINUOUS)
    task.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev1/PFI1")
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)
# 开始触发_模拟窗
with artdaq.Task("b") as task:
    task.ai_channels.add_ai_voltage_chan("Dev2/ai3")
    task.timing.cfg_samp_clk_timing(
        1000, sample_mode=AcquisitionType.CONTINUOUS)
    task.triggers.start_trigger.cfg_anlg_window_start_trig(0.5, 0, "Dev2/ai3")
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)