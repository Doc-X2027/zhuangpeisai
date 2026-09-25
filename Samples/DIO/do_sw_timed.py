import artdaq
from artdaq.constants import (
    LineGrouping)

# Example 1
with artdaq.Task() as task:
    task.do_channels.add_do_chan(
        'Dev1/port0/line0:3',
        line_grouping=LineGrouping.CHAN_PER_LINE)
    try:
        print('N Lines 1 Sample Boolean Write (Error Expected): ')
        print(task.write([1, 0, 1, 0]))
    except artdaq.DaqError as e:
        print(e)

# Example 2
with artdaq.Task("1") as task:
    task.do_channels.add_do_chan(
        'Dev1/port0/line0:3',
        line_grouping=LineGrouping.CHAN_FOR_ALL_LINES)
    print('1 Channel N Lines 1 Sample Unsigned Integer Write: ')
    print(task.write(4))

