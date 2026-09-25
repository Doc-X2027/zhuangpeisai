import pprint
import artdaq
from artdaq.constants import AcquisitionType, Slope

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    task.ai_channels.add_ai_bridge_chan("Dev6/ai0")
    task.timing.cfg_samp_clk_timing(rate=10000.0, sample_mode=AcquisitionType.CONTINUOUS)

    def callback(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
        samples = task.read(number_of_samples_per_channel=10)
        pp.pprint(samples)
        return 0
    task.register_every_n_samples_acquired_into_buffer_event(sample_interval=10, callback_method=callback)

    def callback_done(task_handle, status, callback_data):
        return 0
    task.register_done_event(callback_method=callback_done)
    task.start()
    data = task.read(number_of_samples_per_channel=10)
    print(data)
    input("Acquiring samples continuously. Press Enter to interrupt\n")
    task.stop()
    task.close()



