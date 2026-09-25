import artdaq
import time
import pprint
from artdaq.constants import (EncoderZIndexPhase,
                              LengthUnits, EncoderType)

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    # 演示单点采样
    task.cio_channels.add_ci_lin_encoder_chan("Dev1/ctr0", decoding_type=EncoderType.X_1, zidx_enable=False, zidx_val=0,
                                              zidx_phase=EncoderZIndexPhase.AHIGH_BHIGH,
                                              units=LengthUnits.METERS, dist_per_pulse=0.0001, initial_pos=0.0,)
    print('1 Channel 1 Sample Read: ')
    for _ in range(10):
        data = task.read()
        pp.pprint(data)



