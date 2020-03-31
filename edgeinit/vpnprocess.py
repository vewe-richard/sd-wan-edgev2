#https://stackoverflow.com/questions/20476555/non-blocking-connect
import binascii
import json
import multiprocessing
import struct
from struct import pack
import traceback
import signal
import subprocess
import time
import os
import socket
import errno
import select
from pathlib import Path

from tuntap import TunTap
from edgeinit.stunsocket import stunsocket

class Kill2Exception(Exception):
    pass

def signal_kill2_handler(signum, frame):
    raise Kill2Exception("Kill2")

class VpnProcess(multiprocessing.Process):
    def __init__(self, node, logger, mgrdict, **kwargs):
        super().__init__(**kwargs)
        self._node = node
        self._logger = logger
        self._mgrdict = mgrdict
        self._mgrdict["status"] = "INIT"
        self._ip = self._node["tunnelip"]
        items = self._ip.split(".")
        self._subnet3rd = items[2]
        self._subnet4th = items[3]

        #create default tap
        self.shell(["ip", "tuntap", "add", "mode", "tap", self.tuntapname()])
        rlt = self.shell(["ip", "link", "set", self.tuntapname(), "up"])
        if rlt != 0:
            self._mgrdict["status"] = "CAN NOT CREATE TAP"
            raise Exception("VpnProcess: can not create tap")
        pass

    def loadvpncfg(self, server):
        try:
            vpncfgpath = server["allowips"]
        except:
            return None, None

        if not vpncfgpath[0] == "/":
            p = os.getcwd() + "/" + vpncfgpath
            if not os.path.exists(p):
                p = str(Path.home()) + "/.sdwan/edgepoll/" + vpncfgpath
            vpncfgpath = p

        try:
            with open(vpncfgpath) as json_file:
                obj = json.load(json_file)
        except:
            return vpncfgpath, []

        vpncfgobj = []
        for i in obj:
            vpncfgobj.append(socket.inet_aton(i))
        return vpncfgpath, vpncfgobj

    def run2(self):
        self._macinfo = dict()
        infod = dict()
        self._vpncfglist = []
        for s in self._node["server"]:
            try:
                port = int(s["port"])
            except:
                port = int(self._node["port"])
            pair = (s["ip"], port)
            infod[pair] = None

            try:
                vpntunnelip = s["tunnelip"]
            except:
                vpntunnelip = None
            vpncfgpath, vpncfgobj = self.loadvpncfg(s)
            self._vpncfglist.append((pair, vpntunnelip, vpncfgpath, vpncfgobj))
        self._logger.debug(str(self._vpncfglist))
        self._logger.info("run2 servers: %s", str(infod))
        dev = TunTap(nic_type="Tap", nic_name=self.tuntapname())
        dev.config(self._ip, "255.255.255.0")
        self._dev = dev

        while True:
            rda = []
            wra = []
            for  k, v in infod.items():
                create = False
                if v is None: #create socket
                    create = True
                else:
                    sock = v[0]
                    if v[1]: #recreate the socket
                        if time.time() > v[2] + 3:  #recreate after 3 seconds
                            create = True
                        else:
                            continue
                if create:
                    self._logger.debug("create socket")
                    sock = stunsocket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setblocking(0)
                    sock.connect_ex(k)
                    sock.init2()
                    sock.setpair(k)
                    infod[k] = (sock, False, 0)

                err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err == 0:
                    rda.append(sock)
                else:
                    wra.append(sock)

            rda.append(dev.handle)

            #self._logger.debug("select read %s;  write %s", self.listbrief(rda), self.listbrief(wra))
            rfd, wfd, xfd = select.select(rda, wra, [], 3)
            for f in rfd:
                if f == dev.handle:
                    data = dev.read(2048)
                    #self._logger.debug("tap %d got data %d", f, len(data))
                    l = len(data)
                    self.devdataprocess(infod, data, l)
                    continue

                reconnect = False
                try:
                    if f.left() <= 0:
                        data = bytearray(2)
                        l = f.recv_into(data, 2, socket.MSG_WAITALL)
                        if l < 2:
                            reconnect = True
                            self._logger.info("socket %d got interrupt, len should be 2 but %d", f.fileno(), l)
                        else:
                            leninpkt = data[0] * 256 + data[1]
                            self._logger.debug("need read leninpkt %d", leninpkt)
                            if leninpkt < 14 or leninpkt > 1600:
                                self._logger.info("socket %d got incorrect data, len %d", f.fileno(), leninpkt)
                                reconnect = True
                            else:
                                f.beginread(leninpkt)
                    else:
                        if f.readleft():
                            self.netdataprocess(dev, f.getpair(), f.data(), f.readsize())
                except:
                    self._logger.debug(traceback.format_exc())  #TODO, we may recreate socket?
                    reconnect = True

                if reconnect:
                    f.close()
                    infod[f.getpair()] = (f, True, time.time())

    def devdataprocess(self, infod, data, l):
        if l < 14:
            self._logger.debug("incomplete packet, %d", l)
            raise Exception("TODO") #to uncomment
            return
        #self._logger.debug(str(self.eth_header(data[0:14])))
        storeobj = struct.unpack("!6s6sH", data[0:14])

        eth_protocol = storeobj[2]
        #self._logger.debug("protocol, %s", hex(eth_protocol))
        sock = None
        if eth_protocol == 0x0806: #ARP and
            if storeobj[0].find(b'\xff\xff\xff\xff\xff\xff') == 0:
                self._logger.debug("ARP broadcast")
                # we should send through all connected tunnels
                for k, v in infod.items():
                    c = len(data)
                    buf = bytearray(c.to_bytes(2, "big"))
                    sock = v[0]
                    if sock is None:
                        continue
                    r1 = sock.send(buf)
                    r2 = sock.send(data)
                return
        elif eth_protocol == 0x0800: #  IP packet
            dstip = data[14+16:34]
            sock, data =  self.vpnroute(infod, dstip, data)
        elif eth_protocol == 0x86dd: #IPV6
            #self._logger.debug("netdataprocess IPV6, discard it")
            return
        else:
            self._logger.debug("unprocessed protocol %s", hex(eth_protocol))
            return

        #self._logger.debug("send back packet, dst mac: %s", binascii.hexlify(storeobj[0]))

        if sock is None:
            # find socket from mac
            sock = self.querymactable(self._macinfo, infod, storeobj[0])

        if sock is None:
            self._logger.debug("socket is None, can not reply packet")
            return

        c = len(data)
        buf = bytearray(c.to_bytes(2, "big"))

        r1 = sock.send(buf)
        r2 = sock.send(data)

        pass

    def findpair(self, ip):
        for l in self._vpncfglist:
            if l[3] is None:
                continue
            if ip in l[3]:
                return l[0], l[1]
        return None, None

    def broadcast(self, infod, source_mac, targetip):
        bcast_mac = pack('!6B', *(0xFF,) * 6)
        zero_mac = pack('!6B', *(0x00,) * 6)
        ARPOP_REQUEST = pack('!H', 0x0001)
        ARPOP_REPLY = pack('!H', 0x0002)
        # Ethernet protocol type (=ARP)
        ETHERNET_PROTOCOL_TYPE_ARP = pack('!H', 0x0806)
        # ARP logical protocol type (Ethernet/IP)
        ARP_PROTOCOL_TYPE_ETHERNET_IP = pack('!HHBB', 0x0001, 0x0800, 0x0006, 0x0004)
        #self._logger.debug("%s %s", str(source_mac), binascii.hexlify(source_mac))
        #self._logger.debug("target ip %s, source ip %s", targetip, self._node["tunnelip"])

        sender_ip = pack('!4B', *[int(x) for x in self._node["tunnelip"].split('.')])
        target_ip = pack('!4B', *[int(x) for x in targetip.split('.')])

        arpframe = [
            # ## ETHERNET
            # destination MAC addr
            bcast_mac,
            # source MAC addr
            source_mac,
            ETHERNET_PROTOCOL_TYPE_ARP,

            # ## ARP
            ARP_PROTOCOL_TYPE_ETHERNET_IP,
            # operation type
            ARPOP_REQUEST,
            # sender MAC addr
            source_mac,
            # sender IP addr
            sender_ip,
            # target hardware addr
            zero_mac,
            # target IP addr
            target_ip
        ]

        data = b''.join(arpframe)
        for k, v in infod.items():
            c = len(data)
            buf = bytearray(c.to_bytes(2, "big"))
            sock = v[0]
            if sock is None:
                continue
            r1 = sock.send(buf)
            r2 = sock.send(data)

    def vpnroute(self, infod, dstip, data):
        pair, tunnelip = self.findpair(dstip)
        if pair is None:    #just pass the packet according its mac address
            return None, data

        try:
            sock = infod[pair][0]
        except:
            self._logger.debug("can not find socket to route this packet, use default")
            return None, data

        self._logger.debug("try to route this packet through %s", pair)

        try:
            macinfo = self._macinfo[pair]
        except:
            self._logger.debug("need request arp")
            self.broadcast(infod, data[6:12], tunnelip)
            return None, data

        newd = macinfo[0] + data[6:]
        return sock, newd

    def querymactable(self, macinfo, infod, mac):
        for k, v in macinfo.items():
            if v[0] == mac:
                break
        else:
            self._logger.info("Can not find socket form mac %s", binascii.hexlify(mac))
            return None
        try:
            return infod[k][0]
        except:
            self._logger.info("!Can not find socket form mac %s, %s", binascii.hexlify(mac), str(k))
            self._logger.info(traceback.format_exc())
            return None

    #http://www.bitforestinfo.com/2017/01/how-to-write-simple-packet-sniffer.html
    #query: cn.bing.com => wiki wireshark arp
    def netdataprocess(self, dev, pair, data, l):
        #self._logger.debug("%s data in, len %d: %s", str(pair), l, str(data[0:14].hex()))
        if l < 14:
            self._logger.debug("incomplete packet, %d", l)
            raise Exception("TODO") #to uncomment
            return

        #self._logger.debug(str(self.eth_header(data[0:14])))
        storeobj = struct.unpack("!6s6sH", data[0:14])

        eth_protocol = storeobj[2]
        if eth_protocol == 0x0806:  #ARP packet
            #https://www.educba.com/arp-packet-format/
            storeobj = struct.unpack("!HHccH", data[14:22])
            hrd = storeobj[0]
            if hrd == 1:  #ethernet
                pro = storeobj[1]
                if pro != 2048:
                    self._logger.debug("unknown ARP Pro %d", pro)
                    return
                op = storeobj[4]
                if op == 1 or op == 2: #Arp Request and Arp Reply
                    storeobj = struct.unpack("!6s4s6s4s", data[22:42])
                    s = (storeobj[0], storeobj[1])
                    self._macinfo[pair] = s
                    #self._logger.debug(str(storeobj))
                    self._logger.debug("Mac record for %s, mac: %s, ip: %s", pair, binascii.hexlify(s[0]), binascii.hexlify(s[1]))
                else:
                    self._logger.debug("ARP op unprocessed %d", op)
        elif eth_protocol == 0x0800: #IP packet
            pass
        elif eth_protocol == 0x86dd: #IPV6
            #self._logger.debug("netdataprocess IPV6, discard it")
            return
        else:
            self._logger.debug("unprocessed protocol %s", hex(eth_protocol))
            return

        r = dev.write(data)
        if r != l:
            self._logger.warning("Warning: write to tap (%d) is smaller than request (%d)", r, l)
        return

    def eth_header(self, data):
        storeobj = data[0:14]
        storeobj = struct.unpack("!6s6sH", storeobj)
        destination_mac = binascii.hexlify(storeobj[0])
        source_mac = binascii.hexlify(storeobj[1])
        eth_protocol = storeobj[2]
        return {"Destination Mac": destination_mac,
                "Source Mac": source_mac,
                "Protocol": eth_protocol}

    def listbrief(self, rda):
        brief = ""
        for o in rda:
            if isinstance(o, (int, )):
                brief += "tap: " + str(o) + ","
            else:
                brief += str(id(o)) + ":" + str(o.fileno()) + ","
        return brief

    def getk(self, infod, sock):
        for k, v in infod.items():
            if sock == v[0]:
                return k
        else:
            return None

    def run(self):
        self._mgrdict["pid"] = self.pid
        signal.signal(signal.SIGUSR1, signal_kill2_handler)
        self._dev = None

        try:
            self.run2()
        except KeyboardInterrupt:
            self._logger.warning("VpnProcess Loop exception, KeyboardInterrupt")
        except Kill2Exception:
            self._logger.warning("VpnProcess Kill2Exception")
            self._mgrdict["status"] = "Exit"
        finally:
            if not self._dev is None:
                self._dev.close()
                pass
            self.shell(["ip", "tuntap", "del", "mode", "tap", "name", self.tuntapname()])
        self._logger.warning("VpnProcess Exit")

    def shell(self, args, ignoreerror = True):
        self._logger.info("VpnProcess run %s", str(args))
        sp = subprocess.run(args)
        return sp.returncode

    def status(self):
        try:
            status = self._mgrdict["status"]
        except:
            status = "Unaccessable"
        return status

    def kill2(self):
        try:
            pid = self._mgrdict["pid"]
            os.kill(pid, signal.SIGUSR1)
        except:
            pass

    def dpstatus(self):
        return dict()

    def tuntapname(self):
        prefix = "v." + self._ip
        return prefix

