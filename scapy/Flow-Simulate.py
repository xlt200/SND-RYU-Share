from scapy.all import *
from multiprocessing import Pool
from multiprocessing import Process
import time

#建立Flow類
class Flow:
    
    def __init__(self, dst, src = '10.0.0.5', time_intv = 3, tos = 0):
        self.src = src
        self.dst = dst
        self.time_intv = time_intv
        self.tos = tos

        self.AF3 = [104, 112, 120]
        self.EF = [184]

    def __packet_init(self):
        self.__packet = IP()
        self.__packet.src = self.src
        self.__packet.dst = self.dst
        self.__packet.tos = self.tos
    
    #傳送視頻流量
    def __send_Video(self):
        time_end = time.time() + 10*self.time_intv
        while time.time() < time_end:
            send(self.__packet, count=800)

    #傳送音訊流量
    def __send_Voice(self):
        time_end = time.time() + 10*self.time_intv
        while time.time() < time_end:
            send(self.__packet, count=10)
    
    def __send_Ndef(self):
        time_end = time.time() + 10*self.time_intv
        while time.time() < time_end:
            send(self.__packet, count=100)
           
    def send_flow(self):
        self.__packet_init()

        if self.__packet.tos in self.EF:
            self.__send_Voice()
        elif self.__packet.tos in self.AF3:
            self.__send_Video()
        else:
            self.__send_Ndef()

def sending_flow(flow):
    print('start sending flow')
    flow.send_flow()


if __name__ == "__main__":
    pro = Pool(processes = 6) # 建立6個進程
    
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
