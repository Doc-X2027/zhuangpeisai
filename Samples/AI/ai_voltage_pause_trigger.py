import pprint
import artdaq
from artdaq.constants import AcquisitionType, TaskMode, ActiveLevel, WindowTriggerCondition2, Level

pp = pprint.PrettyPrinter(indent=4)
# 暂停触发_模拟电平
with artdaq.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0:1")
    task.timing.cfg_samp_clk_timing(
        rate=1000, sample_mode=AcquisitionType.CONTINUOUS)
    task.triggers.pause_trigger.cfg_anlg_lvl_pause_trig("Dev1/ai0", ActiveLevel.ABOVE, 0.1)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)


# 暂停触发_模拟窗
with artdaq.Task("a") as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai2")
    task.timing.cfg_samp_clk_timing(
        rate=1000, sample_mode=AcquisitionType.CONTINUOUS)
    task.triggers.pause_trigger.cfg_anlg_window_pause_trig(0.5, 0, "Dev1/ai2", WindowTriggerCondition2.INSIDE_WINDOW)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)


# 暂停触发_数字电平
with artdaq.Task("b") as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai3")
    task.timing.cfg_samp_clk_timing(
        rate=1000, sample_mode=AcquisitionType.CONTINUOUS)
    task.triggers.pause_trigger.cfg_dig_lvl_pause_trig("/Dev1/PFI0", Level.HIGH)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)
