from mininet.topo import Topo
from mininet.link import TCLink

class MyTopo(Topo):
    def __init__(self):

        Topo.__init__(self)

        host1 = self.addHost('h1',ip='10.0.0.1')
        host2 = self.addHost('h2',ip='10.0.0.2')
        
        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')
        switch3 = self.addSwitch('s3')

        self.addLink(host1,switch1,port1=1,port2=1,cls=TCLink)
        self.addLink(host2,switch3,port1=1,port2=1,cls=TCLink)

        # switch to switch
        self.addLink(switch1,switch2,port1=2,port2=1,cls=TCLink,delay="20ms")
        self.addLink(switch2,switch3,port1=2,port2=2,cls=TCLink,delay="10ms")

topos = {'mytopo':(lambda:MyTopo())}
