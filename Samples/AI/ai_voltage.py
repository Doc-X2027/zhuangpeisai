import pprint
import artdaq
from artdaq.constants import AcquisitionType
pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    task.timing.cfg_samp_clk_timing(
        rate=1000, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=5)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=5)
        print('Task Data: ')
        pp.pprint(data)
    task.stop()
    task.close()
