import pprint
import time

import artdaq
import math
from artdaq.constants import AcquisitionType, Slope

pp = pprint.PrettyPrinter(indent=4)
PI = 3.1415926535

data = []
for i in range(1000):
   data.insert(i, 0.02 * math.sin(i * 2.0 * PI / 1000.0))

with artdaq.Task() as task:

   task.ao_channels.add_ao_current_chan("Dev1/ao16")
   task.timing.cfg_samp_clk_timing(rate=40000, sample_mode=AcquisitionType.CONTINUOUS)

   def callback(task_handle, status, callback_data):
      return 0
   task.register_done_event(callback_method=callback)
   task.write(data)
   task.start()
   input("Generating voltage continuously. Press Enter to interrupt\n")
   task.stop()
   task.close()

