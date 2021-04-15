import time
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether
from ryu.lib import hub

# packet
from ryu.lib.packet import packet, ethernet, arp

# topo
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.topology import api as topo_api

import networkx as nx

class shortest_path(app_manager.RyuApp):
        OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

        def __init__(self, *args, **kwargs):
                super(shortest_path, self).__init__(*args, **kwargs)
                self.topology_api_app = self
                self.net = nx.DiGraph()#創建圖
                self.switch_map = {}#記錄dpid以及其對應的dp實體
                self.mac_to_port = {}#用來記錄
                self.idport_to_id = {}#以dpid以及其port去對應到屬於這個link的另外一個dpid，主要用處為將所測的BW放進net的圖裡 
                self.port_infos = {}
                hub.spawn(self.port_request_loop)
        
        @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
        def switch_features_handler(self, ev):
                dp = ev.msg.datapath
                ofp = dp.ofproto
                ofp_parser =dp.ofproto_parser

                self.switch_map.update({dp.id: dp}) 
                match = ofp_parser.OFPMatch()
                action = ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [ofp_parser.OFPActionOutput(ofp.OFPP_CONTROLLER)])
                inst=[action]
                self.add_flow(dp=dp, match=match, inst=inst, table=0, priority=1)#下發flooding流表(table miss)

        
        @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
        def packet_in_handler(self, ev):
                msg= ev.msg
                dp = msg.datapath
                ofp = dp.ofproto
                ofp_parser = dp.ofproto_parser

                port = msg.match['in_port']
                
                ## parses the packet
                pkt = packet.Packet(data=msg.data)
                # ethernet
                pkt_ethernet = pkt.get_protocol(ethernet.ethernet)
                
                if not pkt_ethernet:
                        return

                # 過濾 LLDP packet
                if pkt_ethernet.ethertype == 35020:
                        return
                if msg.buffer_id == ofp.OFP_NO_BUFFER:
                        data = msg.data


                # arp封包处理
                if pkt_ethernet.dst == 'ff:ff:ff:ff:ff:ff':
                        if self.mac_learning(dp,pkt_ethernet.src,port) is False: #判断是否会造成广播风暴，False代表為是會造成
                                out_port = ofp.OFPPC_NO_RECV #将封包丢掉
                        else:
                                out_port = ofp.OFPP_FLOOD #做flooding
                                if not self.net.has_node(pkt_ethernet.src): #若arp封包源沒有包含在圖裡面，則將它加入進圖中
                                        self.net.add_node(pkt_ethernet.src)
                                        self.net.add_edge(pkt_ethernet.src,dp.id,bw=0) #添加雙向的邊
                                        self.net.add_edge(dp.id,pkt_ethernet.src,port=port,bw=0)
                                        self.idport_to_id.update({(dp.id,port):pkt_ethernet.src})
                                        print(self.idport_to_id)
                                        print(self.net.nodes())
                                        print(self.net.edges())

                        actions = [ofp_parser.OFPActionOutput(out_port)]
                        #inst = [actions]
                        out = ofp_parser.OFPPacketOut(datapath=dp,buffer_id=msg.buffer_id,in_port=port,actions=actions,data=data)
                        dp.send_msg(out)
                        return
                
                if pkt_ethernet.ethertype != 34525:
                        if not self.net.has_node(pkt_ethernet.src): #如果不在图里则新增
                                print("add %s in self.net" % pkt_ethernet.src)
                                #print(pkt_ethernet.ethertype)
                                self.net.add_node(pkt_ethernet.src)
                                self.net.add_edge(pkt_ethernet.src, dp.id, bw=0)
                                #self.net.add_edge(dp.id, pkt_ethernet.src, {'port':port})
                                self.net.add_edge(dp.id, pkt_ethernet.src, port=port, bw=0)
                                self.idport_to_id.update({(dp.id,port):pkt_ethernet.src})
                                print(self.idport_to_id)
                                print(self.net.nodes())
                                print(self.net.edges.data())

                
                if self.net.has_node(pkt_ethernet.dst):
                        print("%s in self.net" % pkt_ethernet.dst)
                        path = nx.dijkstra_path(self.net, pkt_ethernet.src, pkt_ethernet.dst, weight='bw') #以当前bw作最短路徑轉發
                        next_match = ofp_parser.OFPMatch(eth_dst=pkt_ethernet.dst,eth_src=pkt_ethernet.src)
                        back_match = ofp_parser.OFPMatch(eth_dst=pkt_ethernet.src,eth_src=pkt_ethernet.dst)
                        print(path)
                        #依照計算后算出的路徑下發流表
                        for on_path_switch in range(1, len(path)-1):
                                now_switch = path[on_path_switch] #这里需要知道現在，之前以及之後的switch
                                next_switch = path[on_path_switch+1]
                                back_switch = path[on_path_switch-1]
                                next_port = self.net[now_switch][next_switch]['port']
                                back_port = self.net[now_switch][back_switch]['port']
                                action = ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [ofp_parser.OFPActionOutput(next_port)])
                                inst = [action]
                                self.add_flow(dp=self.switch_map[now_switch], match=next_match, inst=inst, table=0, idle_timeout=5)
                                
                                action = ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [ofp_parser.OFPActionOutput(back_port)])
                                inst = [action]
                                self.add_flow(dp=self.switch_map[now_switch], match=back_match, inst=inst, table=0, idle_timeout=5)
                                print("now switch:%s" % now_switch)
                        
                        now_switch = path[1]
                        next_switch = path[2]
                        out_port = self.net[now_switch][next_switch]['port']
                        actions = [ofp_parser.OFPActionOutput(out_port)]
                        out = ofp_parser.OFPPacketOut(datapath=dp,buffer_id=msg.buffer_id,in_port=port,actions=actions,data=data)
                        dp.send_msg(out)
                else:
                        return
                   

        #獲得拓撲信息，初始化圖
        @set_ev_cls(event.EventSwitchEnter)
        def get_topology_data(self, ev):
                switch_list = get_switch(self.topology_api_app, None)
                switches =[switch.dp.id for switch in switch_list]
                links_list = get_link(self.topology_api_app, None)
                links=[(link.src.dpid,link.dst.dpid,{'port':link.src.port_no,'bw':0}) for link in links_list] 
                self.net.add_nodes_from(switches)
                self.net.add_edges_from(links)
                print(self.net.nodes())
                print(links)
                for link in links_list:
                        self.idport_to_id.update({(link.src.dpid,link.src.port_no):link.dst.dpid})
                        
                print(self.net.nodes())
                print(self.idport_to_id)
                #print(links)
                #print(self.net.edges.data())
                #print(self.net.nodes())
                #print(self.net.edges())

        def add_flow(self, dp, cookie=0, match=None, inst=[], table=0, priority=10, idle_timeout=10000):
                ofp = dp.ofproto
                ofp_parser = dp.ofproto_parser
                
                buffer_id = ofp.OFP_NO_BUFFER

                mod = ofp_parser.OFPFlowMod(
                                datapath=dp, cookie=cookie, table_id=table,
                                command=ofp.OFPFC_ADD, priority=priority, buffer_id=buffer_id,
                                out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                                match=match, instructions=inst,idle_timeout=idle_timeout
                )
                dp.send_msg(mod)

        def send_packet(self, dp, port, pkt):
                ofproto = dp.ofproto
                parser = dp.ofproto_parser
                pkt.serialize()
                data = pkt.data
                action = [parser.OFPActionOutput(port=port)]

                out = parser.OFPPacketOut(
                                datapath=dp, buffer_id = ofproto.OFP_NO_BUFFER,
                                in_port = ofproto.OFPP_CONTROLLER,
                                actions=action, data=data)

                dp.send_msg(out)
        
        #c處理arp廣播风暴，以dpid以及src-mac当作key，value为inport，若傳進来的inport没被記錄，则代表
        #是会造成廣播风暴的arp封包
        def mac_learning(self,datapath,src,in_port):
                self.mac_to_port.setdefault((datapath,datapath.id),{})

                if src in self.mac_to_port[(datapath,datapath.id)]:
                        if in_port != self.mac_to_port[(datapath,datapath.id)][src]:
                                return False
                else:
                        self.mac_to_port[(datapath,datapath.id)][src] = in_port
                        return True

        def port_request_loop(self):
                time.sleep(5)

                while True:
                        switches = topo_api.get_all_switch(self)
                        dps = [switch.dp for switch in switches]
                        for dp in dps:
                                parser = dp.ofproto_parser
                                ofproto = dp.ofproto
                                msg = parser.OFPPortStatsRequest(dp, 0, ofproto.OFPP_ANY)
                                dp.send_msg(msg)

                        time.sleep(1) #每秒獲得信息

        #獲取傳回的link信息
        @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
        def port_stats_event_handler(self, ev):

                print("Handling port stats event")

                for stat in ev.msg.body:
                        dpid = ev.msg.datapath.id
                        port_no = stat.port_no
                        name = "%X-%d" % (dpid, port_no, )
                        current_time = time.time() #記錄現在時間

                        self.port_infos.setdefault(name, {"last_update":current_time, "rx_bytes": 0, "tx_bytes": 0, "rx_band": 0, "tx_band": 0})
                        port_info = self.port_infos[name]

                        if port_info["last_update"] == current_time:
                                port_info["rx_bytes"] = stat.rx_bytes
                                port_info["tx_bytes"] = stat.tx_bytes

                        else:
                                delta_time = current_time - port_info["last_update"]
                                #算出频宽，注意單位是Mbit
                                port_info["rx_band"] = (stat.rx_bytes - port_info["rx_bytes"]) / delta_time
                                port_info["tx_band"] = (stat.tx_bytes - port_info["tx_bytes"]) / delta_time
                                port_info["rx_bytes"] = stat.rx_bytes
                                port_info["tx_bytes"] = stat.tx_bytes
                                port_info["last_update"] = current_time

                        dst_dpid = self.idport_to_id.get((dpid,port_no))

                        if dst_dpid != None:
                                #記錄link的頻寬
                                BW = port_info["rx_band"]+port_info["tx_band"]
                                self.net[dst_dpid][dpid]["bw"] = (BW/1000000)*8
                                self.net[dpid][dst_dpid]["bw"] = (BW/1000000)*8
                                #print("link {} -> {} bw: {}".format(dpid,dst_dpid,self.net[dpid][dst_dpid]["bw"]))
    
                for name in self.port_infos:
                        port_info = self.port_infos[name]
                        print ("[%s] rxband: %.4fMB, txband: %.4fMB" % (name, (port_info["rx_band"]/1000000)*8, (port_info["tx_band"]/1000000)*8)) #打印port的频宽信息
                print(self.net.edges.data())
                edgels = self.net.edges()
                length = len(edgels)
                print(length)
                #print(edgels[0])
                print(type(edgels))
                for l in range(length):
                    #print(edgels[l])
                    src_dpid = (edgels[l])[0]
                    dst_dpid = (edgels[l])[1]
                    print("(link {} -> {} bw: {})".format(src_dpid,dst_dpid,self.net[src_dpid][dst_dpid]["bw"]))


                print("------------------------------------------------------------------------------------")
