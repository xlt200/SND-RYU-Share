from scapy.all import *
import threading
from multiprocessing import Pool
from multiprocessing import Process
import time

time_intv = 3

packet1 = IP()
packet1.src = "10.0.0.5"
packet1.dst = "10.0.0.1"
packet1.tos = 184

packet2 = IP()
packet2.src = "10.0.0.5"
packet2.dst = "10.0.0.2"
packet2.tos = 104

def flow1():
    time_end = time.time() + 10*time_intv
    
    while time.time() < time_end:
        send(packet1, count = 800)

def flow2():
    time_end = time.time() + 10*time_intv

    while time.time() < time_end:
        send(packet2, count = 800)

if __name__ == "__main__":
    pro = Pool(processes = 6)
    
    for i in range(1):
        pro.apply_async(flow1)
    for i in range(5):
        pro.apply_async(flow2)
    
    pro.close()
    pro.join()

    printf("send completely")
