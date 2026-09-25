import pprint
import artdaq
from artdaq.constants import AcquisitionType, TaskMode, Signal

pp = pprint.PrettyPrinter(indent=4)
data0 =[0 for i in range(1000)]
data1 =[0 for i in range(1000)]
for i in range(1000):
    if i % 2 == 0:
        data0[i] = 8.0
        data1[i] = 4.0
    else:
        data0[i] = 0.0
        data1[i] = 0.0

with artdaq.Task("ai") as AITaskHandle, artdaq.Task("ao") as AOTaskHandle:
    AITaskHandle.ai_channels.add_ai_voltage_chan("Dev2/ai0:1")
    AITaskHandle.timing.cfg_samp_clk_timing(
        10000.00, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000)
    AITaskHandle.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev2/PFI1")

    AOTaskHandle.ao_channels.add_ao_voltage_chan("Dev2/ao0:1")
    AOTaskHandle.timing.cfg_samp_clk_timing(10000.00, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000)
    AOTaskHandle.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev2/PFI1")
    AOTaskHandle.write([data0, data1], auto_start=False)
    AOTaskHandle.start()
    AITaskHandle.start()

    for _ in range(100):
        data = AITaskHandle.read(number_of_samples_per_channel=1000)
        print('Task Data: ')
        pp.pprint(data)

    AITaskHandle.stop()
    AOTaskHandle.stop()
    AITaskHandle.close()
    AOTaskHandle.close()
