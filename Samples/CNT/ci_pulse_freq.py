import artdaq
import pprint
from artdaq.constants import AcquisitionType


pp = pprint.PrettyPrinter(indent=4)

# 脉冲测量-基于频率
with artdaq.Task() as task:
    task.cio_channels.add_ci_pulse_chan_freq("Dev1/ctr0")
    data = task.read()
    pp.pprint(data)

# 脉冲测量-连续
with artdaq.Task("a") as task:
    task.cio_channels.add_ci_pulse_chan_freq("Dev1/ctr0")
    task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=10)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)
