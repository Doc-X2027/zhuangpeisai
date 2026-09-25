import ctypes
import pprint
import artdaq
from artdaq.constants import Dev_Node, DAQ
pp = pprint.PrettyPrinter(indent=4)

count = ctypes.c_int32(0)
buffer0 = ctypes.c_void_p
deviceNode = Dev_Node()
artdaq.get_device_list(DAQ, buffer0, 0, count)