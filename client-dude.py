from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import STRING,INT, BOOL, UINT32, ListFieldType, UINT16, UINT8, UINT64, BUFFER
import asyncio
import playground
from playground.network.common.Protocol import StackingTransport, StackingProtocolFactory, StackingProtocol
from playground.network.packet.fieldtypes.attributes import Optional
import sys
from io import StringIO
from playground.asyncio_lib.testing import TestLoopEx
from playground.network.testing import MockTransportToStorageStream
from playground.network.testing import MockTransportToProtocol
from playground.common import logging as p_logging
import zlib
import random

#Call Start Message
class startcall(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.start"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ('flag', BOOL)]

#Call Response Packet Class Definition
class response(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.response"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("name", STRING),
               ("available", BOOL),
               ("location", STRING),
               ("ip", STRING),
               ("port", UINT32),
               ("xccpv", INT),
               ("codec", ListFieldType(STRING)),
               ]
#BYE Message to disconnect the call
class bye(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.bye"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("flag", BOOL)
               ]

#Calling INVITE Packet Class Definition
class invite(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.invite"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("name", STRING),
               ('available', BOOL),
               ("location", STRING),
               ("ip", STRING),
               ("port", UINT32),
               ("xccpv", INT),
               ("codec", ListFieldType(STRING)),
               ]
#Session Start Packet Class Definition
class session(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.session"
    DEFINITION_VERSION = "1.0"
    FIELDS = [ ("callingip", STRING),
               ("callingport", UINT32),
               ("calledip", STRING),
               ("calledport", UINT32),
               ("codec", STRING),
               ("payload", INT)]
# Busy pakcet class
class busy(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.calling.busy"
    DEFINITION_VERSION = "1.0"
    FIELDS = [  ]

class PEEPPacket(PacketType):

    DEFINITION_IDENTIFIER = "PEEP.Packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: True})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", BUFFER({Optional: True}))
    ]

#Client Protocol Class
class EchoClientProtocol(asyncio.Protocol):
    name='sequence'
    available=1
    location='sequence'
    xccpv='1'
    ip='sequence'
    port=23
    codec=['testlist']
    state=0

    def response(self, name, available, location, xccpv, ip, port, codec):
        self.name = name
        self.location = location
        self.xccpv = xccpv
        self.ip = ip
        self.port = port
        self.codec = codec
        self.available = available

    def __init__(self, loop):
        self.transport = None
        self.loop = loop
        '''pkx = startcall()
        pkx.flag=1
        pkx1 = pkx.__serialize__()
        self.transport.write(pkx1)'''
        self._deserializer = PacketType.Deserializer()

    def connection_made(self, transport):
        print("\nEchoClient is now Connected to the Server\n")
        self.response('Alice', 'WashingtonDC', 1, 1, '192.168.1.254', 45532, ["G722a", "G729"])
        self.transport = transport
        pkx = startcall()
        pkx.flag=1
        pkx1 = pkx.__serialize__()
        #peeptransport = PeepClientTransport(self.transport)
        #peeptransport.write(pkx1)
        #peeptransport.transport.write(pkx1)
        self.transport.write(pkx1)

    def data_received(self, data):
        self._deserializer.update(data)
        for pkt in self._deserializer.nextPackets():
            if(pkt.DEFINITION_IDENTIFIER == "lab1b.calling.busy") and self.state==0:
                print('CLIENT -> SERVER: Call start request\n')
                print('SERVER -> CLIENT: Server is busy currently. Please try again later.')
                self.transport.close()
            elif(pkt.DEFINITION_IDENTIFIER=='lab1b.calling.invite') and self.state==0:
                print('Packet 2 SERVER -> CLIENT: Call Invite from {}'.format(pkt.name))
                print('\t\t\t\t ',pkt)
                self.state +=1
                res = response()
                res.name = self.name; res.location = self.location; res.xccpv = self.xccpv; res.ip = self.ip; res.port = self.port; res.codec = self.codec; res.available = self.available
                pky = res.__serialize__()
                self.transport.write(pky)

            elif(pkt.DEFINITION_IDENTIFIER=='lab1b.calling.session') and self.state==1:
                print('\nPacket 4 SERVER -> CLIENT: Call session start from Bob.(Server)')
                print('\t\t\t\t ', pkt)
                print('')
                print('SESSION PACKET DETAILS:\t\tSession Established with below details:')
                print('\t\t\t\t\tCaller IP address:{}'.format(pkt.callingip))
                print('\t\t\t\t\tCaller Port:{}'.format(pkt.callingport))
                print('\t\t\t\t\tCalled User IP address:{}'.format(pkt.calledip))
                print('\t\t\t\t\tCalled User port:{}'.format(pkt.calledport))
                print('\t\t\t\t\tCodec elected for the session:{}'.format(pkt.codec))
                print('\t\t\t\t\tPayload size for the codec:{}Kb\n'.format(pkt.payload))
                byepkt = bye()
                byepkt.flag = 0
                byep = byepkt.__serialize__()
                self.transport.write(byep)
                self.loop.stop()
            else:
                print('Incorrect packet received. Please check the protocol on server side.')
                self.transport.close()

    def connection_lost(self, exc):
        self.transport = None
        print("\nEchoClient Connection was Lost with Server because: {}".format(exc))
        self.transport.close()
        self.loop.stop()

#First Packet Calling Class
class initiate():

    def __init__(self, loop):
        self.loop = loop

    def send_first_packet(self):
        self.loop = loop
        return EchoClientProtocol(self.loop)

'''class PassThrough1(StackingProtocol, StackingTransport):

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        print("\nConnection made. Once data is received by PassThrough1, will be sent to higher layer")
        self.transport = transport
        higherTransport = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        print("\nData Received at PassThrough1. Sending it to higher layer.\n")
        self.higherProtocol().data_received(data)

    def connection_lost(self, exc):
        self.transport = None
        print("\nPassThrough1 Connection was Lost with Server because: {}".format(exc))
        self.transport.close()'''


class PeepClientTransport(StackingTransport):

    def __init__(self,protocol, transport):
        self.transport = transport
        super().__init__(self.transport)
        self.protocol = protocol

    def write(self, data):
        packet = PacketType.Deserialize(data)
        print("Packet in TCP Tranport is",packet, packet.DEFINITION_IDENTIFIER)
        print("\nCalling PEEPClientTransport write\n")
        packetz = packet.__serialize__()
        self.protocol.write(packetz)
        #peepdude = PEEPClient()
        #peepdude.write(packetz)

class PEEPClient(StackingProtocol, StackingTransport):

    def __init__(self):
        self.transport = None
        self.state = 0
        self.length = 10
        super().__init__(self.transport)

    def calculateChecksum(self, c):
        self.c = c
        self.c.Checksum = 0        #self.protocol=protocol

        #print(self.c)
        bitch = self.c.__serialize__()
        return zlib.adler32(bitch) & 0xffff

    def checkChecksum(self, instance):
        self.instance = instance
        pullChecksum = self.instance.Checksum
        instance.Checksum = 0
        bytes = self.instance.__serialize__()
        if pullChecksum == zlib.adler32(bytes) & 0xffff:
            return True
        else:
            return False

    def connection_made(self, transport):
        self.transport = transport
        if self.state == 0:
            packet = PEEPPacket()
            packet.Type = 0
            packet.SequenceNumber = random.randrange(1, 1000, 1)
            packet.Acknowledgement = 0
            # packet.data = b'sequence'
            self.state += 1
            dude = self.calculateChecksum(packet)
            print("checksum is", dude)
            packet.Checksum = self.calculateChecksum(packet)
            packs = packet.__serialize__()
            self.transport.write(packs)
            #peeptransport = PeepClientTransport(self.transport)
            #peeptransport.write(packs)

    def data_received(self, data):
        self.deserializer = PacketType.Deserializer()
        self.deserializer.update(data)
        for packet in self.deserializer.nextPackets():
            print("Packet in TCP is", packet, packet.Type)
            checkvalue = self.checkChecksum(packet)
            if self.state == 1 and packet.Type == 1 and checkvalue:
                print("\nSYN-ACK Received. Seqno=", packet.SequenceNumber, " Ackno=", packet.Acknowledgement)
                Clientpacket = PEEPPacket()
                Clientpacket.Type = 2
                Clientpacket.SequenceNumber = packet.Acknowledgement
                Clientpacket.Acknowledgement = packet.SequenceNumber + sys.getsizeof(packet) + 1
                self.state += 1
                Clientpacket.Checksum = self.calculateChecksum(Clientpacket)
                clientpacketbytes = Clientpacket.__serialize__()
                higherTransport = PeepClientTransport(self, self.transport)
                self.higherProtocol().connection_made(higherTransport)
                self.transport.write(clientpacketbytes)
                #self.higherProtocol().data_received(data)
            else:
                print("Incorrect packet received. Closing connection!")
                self.transport.close()
    def write(self,data):
        packet = PacketType.Deserialize(data)
        print("Packet in TCP Protocol is",packet, packet.DEFINITION_IDENTIFIER)


class PassThrough2(StackingProtocol, StackingTransport):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        print("\nConnection made. Once data is received by PassThrough2, will be sent to higher layer")
        self.transport = transport
        higherTransport = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport)

    def data_received(self, data):
        print("\nData Received at PassThrough2. Sending it to higher layer.\n")
        self.higherProtocol().data_received(data)

    def connection_lost(self, exc):
        self.transport = None
        print("\nPassThrough2 Connection was Lost with Server because: {}".format(exc))
        self.transport.close()

if __name__ == "__main__":

    p_logging.EnablePresetLogging(p_logging.PRESET_TEST)
    loop = asyncio.get_event_loop()
    lux = initiate(loop)
    f = StackingProtocolFactory(lambda: PEEPClient(), lambda: PassThrough2())
    ptConnector = playground.Connector(protocolStack=f)
    playground.setConnector("passthrough", ptConnector)
    loop.set_debug(enabled=True)
    #alice = EchoClientProtocol(loop)
    #alice.response('Alice', 'WashingtonDC', 1, 1, '192.168.1.254', 45532, ["G722a", "G729"])
    conn = playground.getConnector('passthrough').create_playground_connection(lux.send_first_packet, '20174.1.1.1' , 8888)
    #conn = loop.create_connection(lambda: EchoClientProtocol(), '127.0.0.1', port=8000)
    loop.run_until_complete(conn)
    print('\nPress Ctrl+C to terminate the process\n')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    loop.close()
