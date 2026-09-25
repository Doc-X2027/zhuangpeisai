import artdaq
import time
import pprint
from artdaq.constants import AcquisitionType


pp = pprint.PrettyPrinter(indent=4)
# 演示单点采样
with artdaq.Task() as task:
    task.cio_channels.add_ci_count_edges_chan("Dev1/ctr0")
    print('1 Channel 1 Sample Read: ')
    for _ in range(10):
        data = task.read()
        pp.pprint(data)
        time.sleep(0.1)

# 演示连续采样-外时钟
with artdaq.Task("a") as task:
    task.cio_channels.add_ci_count_edges_chan("Dev1/ctr0")
    task.timing.cfg_samp_clk_timing(
        1000, "/Dev1/PFI3", sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=100)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)


