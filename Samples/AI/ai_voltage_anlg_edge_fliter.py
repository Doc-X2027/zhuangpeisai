import pprint
import artdaq
from artdaq.constants import AcquisitionType, Slope

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:

   task.ai_channels.add_ai_voltage_chan("Dev10/ai0")
   task.timing.cfg_samp_clk_timing(rate=20000, sample_mode=AcquisitionType.FINITE)
   task.triggers.start_trigger.cfg_anlg_edge_start_trig("APFI0", trigger_slope=Slope.RISING, trigger_level=2)
   task.triggers.start_trigger.dig_fltr_min_pulse_width = 0.0001
   task.start()
   for _ in range(2):
      data = task.read(number_of_samples_per_channel=10)
      print('Task Data: ')
      pp.pprint(data)
   task.stop()
   task.close()