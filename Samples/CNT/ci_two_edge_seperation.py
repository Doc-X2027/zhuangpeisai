import artdaq
import time
import pprint
from artdaq.constants import AcquisitionType


pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    # 演示单点采样
    task.cio_channels.add_ci_two_edge_sep_chan("Dev2/ctr0")
    print('1 Channel 1 Sample Read: ')
    for _ in range(10):
        data = task.read()
        pp.pprint(data)
        time.sleep(0.1)

    # 演示连续采样-隐式时钟
with artdaq.Task("1") as task:
    task.cio_channels.add_ci_two_edge_sep_chan("Dev2/ctr0")
    task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=10)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)
