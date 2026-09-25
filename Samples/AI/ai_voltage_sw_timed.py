import pprint
import artdaq

pp = pprint.PrettyPrinter(indent=4)

with artdaq.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    print('1 Channel 1 Sample Read: ')
    data = task.read()
    pp.pprint(data)

with artdaq.Task("a") as task1:
    task1.ai_channels.add_ai_voltage_chan("Dev1/ai1:3")
    print('N Channel 1 Sample Read: ')
    data1 = task1.read()
    pp.pprint(data1)
