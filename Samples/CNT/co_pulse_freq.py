import artdaq
import time
from artdaq.types import CtrTime
from artdaq.constants import (FrequencyUnits, Level, AcquisitionType)

with artdaq.Task() as task:
    task.cio_channels.add_co_pulse_chan_freq("Dev1/ctr0",
                                             units=FrequencyUnits.HZ, idle_state=Level.LOW, initial_delay=0.0,
                                             freq=100.0, duty_cycle=0.5)
    task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=10)
    task.start()
    for _ in range(100):
        task.is_task_done()
        time.sleep(0.1)
    task.stop()

