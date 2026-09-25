import artdaq
import time
from artdaq.types import (CtrTime)
from artdaq.constants import (TimeUnits, Level, AcquisitionType)

with artdaq.Task() as task:
    task.cio_channels.add_co_pulse_chan_time("Dev2/ctr0",
                                             units=TimeUnits.SECONDS, idle_state=Level.LOW, initial_delay=0.0,
                                             low_time=0.01, high_time=0.01)
    task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=10)
    task.start()
    for _ in range(100):
        task.is_task_done()
        time.sleep(0.1)
    task.stop()

