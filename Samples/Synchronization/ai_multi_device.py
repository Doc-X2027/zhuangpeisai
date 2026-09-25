import pprint
import artdaq
from artdaq.constants import AcquisitionType, TaskMode, Signal

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task("master") as m, artdaq.Task("slave") as s:
    m.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    s.ai_channels.add_ai_voltage_chan("Dev2/ai0")

    m.timing.cfg_samp_clk_timing(
        10000.00, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000)
    m.export_signals.export_signal(signal_id=Signal.AI_CONVERT_CLOCK, output_terminal="PFI3")

    s.timing.cfg_samp_clk_timing(
        10000.00, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000)
    s.timing.ai_conv_src("PFI2")

    print('2 Channels 1 Sample Read Loop 10: ')
    s.start()
    m.start()

    for _ in range(10):
        master_data = m.read(number_of_samples_per_channel=10)
        slave_data = s.read(number_of_samples_per_channel=10)

        print('Master Task Data: ')
        pp.pprint(master_data)
        print('Slave Task Data: ')
        pp.pprint(slave_data)
