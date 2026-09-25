import artdaq
import time
import pprint

from artdaq.constants import CounterFrequencyMethod
from artdaq._task_modules.channels.channel import Channel
pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    # 演示单点采样
    ci_channel = task.cio_channels.add_ci_freq_chan("Dev10/ctr0", meas_method=CounterFrequencyMethod.LOW_FREQUENCY_1_COUNTER)
    ci_channel.ci_gate_dig_fltr_min_pulse_width = 0.00
    print('1 Channel 1 Sample Read: ')
    task.start()
    for _ in range(10):
        data = task.read()
        pp.pprint(data)
        time.sleep(0.1)

    task.stop()
    task.close()

