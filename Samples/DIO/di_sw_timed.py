import artdaq
import pprint

from artdaq.constants import (
    LineGrouping)

pp = pprint.PrettyPrinter(indent=4)

# 演示line通道单点采集
with artdaq.Task() as task:
    task.di_channels.add_di_chan('Dev1/port0/line0:1', line_grouping=LineGrouping.CHAN_PER_LINE)
    print('1 Channel 1 Sample Read: ')
    data = task.read()
    pp.pprint(data)

# 演示port通道单点采集
with artdaq.Task("1") as task:
    task.di_channels.add_di_chan("Dev1/port0:1",
                                 line_grouping=LineGrouping.CHAN_FOR_ALL_LINES)
    print('1 Channel 1 Sample Read: ')
    data = task.read()
    pp.pprint(data)

