import artdaq

with artdaq.Task() as task:
    task.ao_channels.add_ao_voltage_chan('Dev2/ao0')

    print('1 Channel 1 Sample Write: ')
    print(task.write(1.0))
    task.stop()

with artdaq.Task('1') as task:
    task.ao_channels.add_ao_voltage_chan('Dev2/ao0:1')
    print('N Channel 1 Sample Write: ')
    print(task.write([1.1, 2.2]))
    task.stop()
