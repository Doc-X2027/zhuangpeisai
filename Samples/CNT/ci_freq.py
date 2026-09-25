import artdaq
import time
import pprint
from artdaq.constants import AcquisitionType, CounterFrequencyMethod

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    # 演示单点采样
    task.cio_channels.add_ci_freq_chan("Dev1/ctr0", meas_method=CounterFrequencyMethod.LOW_FREQUENCY_1_COUNTER)
    print('1 Channel 1 Sample Read: ')
    for _ in range(10):
        data = task.read()
        pp.pprint(data)
        time.sleep(0.1)
