import artdaq
import time
import pprint
import numpy
from numpy import uint32
pp = pprint.PrettyPrinter(indent=4)
position = uint32(numpy.zeros(1000))
pulseWidth = uint32(numpy.zeros(1000))
with artdaq.Task() as task:
    # 演示单点采样
    for i in range(10) :
        position[i] = 1000 * (i+1)
        pulseWidth[i] = 1000 * (i+1)
    task.cio_channels.add_ci_lin_encoder_chan("Dev9/ctr0")
    task.export_signals.export_ctrComparsionEvent("/Dev9/PFI11")
    task.write_position_comparsion_data(position, pulseWidth)
    task.start()
    print('1 Channel 1 Sample Read: ')
    for _ in range(1000):
        data = task.read()
        pp.pprint(data)
        time.sleep(0.1)
    task.stop()
