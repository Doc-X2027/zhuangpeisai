import pprint
import artdaq
from artdaq.constants import AcquisitionType, TaskMode, Slope

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0:1")
    task.timing.cfg_samp_clk_timing(
        rate=1000, sample_mode=AcquisitionType.FINITE)
    task.triggers.reference_trigger.cfg_anlg_edge_ref_trig("Dev1/ai0", 500, Slope.RISING, 0.0)
    task.start()
    for _ in range(10):
        data = task.read(number_of_samples_per_channel=10)
        print('Task Data: ')
        pp.pprint(data)
