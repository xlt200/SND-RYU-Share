
from scapy.all import *
from multiprocessing import Pool
from multiprocessing import Process
import time

class Flow:
    
    def __init__(self, dst, src = '10.0.0.5', src_mac = "00:00:00:00:00:05", iface = "server-eth1", time_intv = 1, tos = 0):
        self.src = src
        self.dst = dst
        self.time_intv = time_intv
        self.tos = tos
        self.src_mac = src_mac
        self.ether_type = 2048
        self.iface = iface

        self.__AF3 = [104, 112, 120]
        self.__EF = [184]

    def __packet_init(self):
        self.__packet = Ether(src = self.src_mac, type = self.ether_type)/IP(src = self.src, dst = self.dst)
        self.__packet.tos = self.tos
    
    def __send_Video(self):
        time_end = time.time() + 10*self.time_intv
        while time.time() < time_end:
            sendp(self.__packet, count=800, iface=self.iface)

    def __send_Voice(self):
        time_end = time.time() + 10*self.time_intv
        while time.time() < time_end:
            sendp(self.__packet, count=10, iface=self.iface)
    
    def __send_Ndef(self):
        time_end = time.time() + 10*self.time_intv
        while time.time() < time_end:
            sendp(self.__packet, count=100, iface=self.iface)
           
    def send_flow(self):
        self.__packet_init()

        if self.__packet.tos in self.__EF:
            self.__send_Voice()
        elif self.__packet.tos in self.__AF3:
            self.__send_Video()
        else:
            self.__send_Ndef()

def sending_flow(flow):
    print('start sending flow')
    flow.send_flow()


if __name__ == "__main__":
    pro = Pool(processes = 6)
    
    flow1_voice = Flow(dst = '10.0.0.1', tos = 184)
    flow1_video = Flow(dst = '10.0.0.1', tos = 104)
    flow2_voice = Flow(dst = '10.0.0.2', tos = 184)
    flow2_video = Flow(dst = '10.0.0.2', tos = 104)
    flow3_voice = Flow(dst = '10.0.0.3', tos = 184)
    flow3_video = Flow(dst = '10.0.0.3', tos = 104)
    
    pro.apply_async(sending_flow, args = (flow1_video,))
    pro.apply_async(sending_flow, args = (flow1_voice,))
    pro.apply_async(sending_flow, args = (flow2_video,))
    pro.apply_async(sending_flow, args = (flow2_voice,))
    pro.apply_async(sending_flow, args = (flow3_video,))
    pro.apply_async(sending_flow, args = (flow3_voice,))
    
    pro.close()
    pro.join()

    print("send completely")
