import pprint
import artdaq
from artdaq.constants import AcquisitionType, TaskMode, Signal, Edge

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task("master") as m, artdaq.Task("slave") as s:
    m.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    s.ai_channels.add_ai_voltage_chan("Dev2/ai0")

    m.timing.cfg_samp_clk_timing(
        rate=10000.00, sample_mode=AcquisitionType.FINITE, samps_per_chan=10000)
    s.timing.cfg_samp_clk_timing(
        rate=10000.00, sample_mode=AcquisitionType.FINITE, samps_per_chan=10000)

    m.timing.ref_clk_src(val="PXI_Clk10")
    s.timing.ref_clk_src(val="PXI_Clk10")

    #开始触发
    m.export_signals.export_signal(signal_id=Signal.START_TRIGGER, output_terminal="PXI_Trig0")
    s.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source="PXI_Trig0", trigger_edge=Edge.RISING)

    s.start()
    m.start()

    print("Acquiring samples continuously. Press Enter to interrupt\n")
    print("\nRead:\tMaster\tSlave\tTotal:\tMaster\tSlave\n")

    for _ in range(10):
        master_data = m.read(number_of_samples_per_channel=10)
        slave_data = s.read(number_of_samples_per_channel=10)

        print('Master Task Data: ')
        pp.pprint(master_data)
        print('Slave Task Data: ')
        pp.pprint(slave_data)
