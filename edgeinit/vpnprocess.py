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

    def bindport(self, sock, port):
        # try to use a specific source port according to the server port
        # then in server part, can judge whether it should accept connection from a source port
        start = 10000 + port%1000
        for p in range(start, start + 10):
            try:
                sock.bind(("0.0.0.0", p))
                self._logger.info("use source port %d for connection to port %d", p, port)
                break
            except:
                continue
        else:
            self._logger.warning("Can not bind source port for connection to port %d", port)

    def run2(self):
        self._macinfo = dict()
        infod = dict()
        self._vpncfglist = []
        gateway = None
        for s in self._node["server"]:
            try:
                port = int(s["port"])
            except:
                port = int(self._node["port"])
            pair = (s["ip"], port)
            infod[pair] = None

            try:
                vpntunnelip = s["tunnelip"]
                if vpntunnelip[-2] == "." and vpntunnelip[-1] == "1":
                    gateway = vpntunnelip
            except:
                vpntunnelip = None

            vpncfgpath, vpncfgobj = self.loadvpncfg(s)

            self._vpncfglist.append((pair, vpntunnelip, vpncfgpath, vpncfgobj, 0 if vpncfgobj is None else len(vpncfgobj)))
            status = dict()
            status["reconnect"] = 0
            status["bytes"] = 0
            status["status"] = "INIT"
            self._mgrdict[pair] = status
        self._logger.info("run2 servers: %s", str(infod))
        dev = TunTap(nic_type="Tap", nic_name=self.tuntapname())
        dev.config(self._ip, "255.255.255.0")
        self._dev = dev

        self._mgrdict["status"] = "In Loop"
        try:
            if not gateway is None:
                self.router_iptable_setup(infod, gateway, self.tuntapname())
        except:
            self._logger.info("Warning %s", traceback.format_exc())
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
                    sock = stunsocket(socket.AF_INET, socket.SOCK_STREAM)
                    self.bindport(sock, int(k[1]))
                    sock.setblocking(0)
                    err = sock.connect_ex(k)
                    sock.init2()
                    sock.setpair(k)
                    infod[k] = (sock, False, 0)

                err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err == 0:
                    rda.append(sock)
                    #if the tunnel is not in connect, we need get notify from write list on connected
                    status = self._mgrdict[k]
                    if status is None or status["status"] == "CONNECT":
                        pass
                    else:
                        wra.append(sock)
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
                reason = ""
                try:
                    if f.left() <= 0:
                        data = bytearray(2)
                        l = f.recv_into(data, 2, socket.MSG_WAITALL)
                        if l < 2:
                            reconnect = True
                            reason = "socket receive zero data"
                            self._logger.info("socket %s got interrupt, len should be 2 but %d", str(f.getpair()), l)
                        else:
                            leninpkt = data[0] * 256 + data[1]
                            self._logger.debug("need read leninpkt %d", leninpkt)
                            if leninpkt < 14 or leninpkt > 1600:
                                self._logger.info("socket %s got incorrect data, len %d", str(f.getpair()), leninpkt)
                                reconnect = True
                                reason = "socket receive incorrect packet length " + str(leninpkt)
                            else:
                                f.beginread(leninpkt)
                                status = self._mgrdict[f.getpair()]
                                status["recv"] = time.time() #recent receive time
                                status["bytes"] += (leninpkt + 2)
                                self._mgrdict[f.getpair()] = status
                    else:
                        if f.readleft():
                            self.netdataprocess(dev, f.getpair(), f.data(), f.readsize())
                except Exception as e:
                    self._logger.info("%s %s", f.getpair(), traceback.format_exc())
                    reconnect = True
                    reason = str(e)

                if reconnect:
                    f.close()
                    infod[f.getpair()] = (f, True, time.time())
                    status = self._mgrdict[f.getpair()]
                    if not status["status"] == "LOST":
                        status["lost"] = time.time()  # recent receive time
                        status["reason"] = reason
                        status["reconnect"] = 0
                        status["status"] = "LOST"
                    status["reconnect"] += 1
                    status["rereason"] = reason
                    self._mgrdict[f.getpair()] = status

            for f in wfd:
                pair = f.getpair()
                status = self._mgrdict[pair]
                reconnect = infod[pair][1]
                #self._logger.info("%s: reconnect %s, status %s", str(pair), str(reconnect), status["status"])
                if not reconnect and not status["status"] == "CONNECT":
                    try:
                        f.send(bytearray(b'\x13\x56'))
                        status["status"] = "CONNECT"
                        status["connect"] = time.time()
                        status["bytes"] = 0
                        self._mgrdict[f.getpair()] = status
                    except:
                        self._logger.info("patch, fault connect event, %s, %s", str(pair), traceback.format_exc())
                        pass


    def devdataprocess(self, infod, data, l):
        if l < 14:
            self._logger.warning("incomplete packet, %d", l)
            raise Exception("TODO") #to uncomment
            return
        #self._logger.debug(str(self.eth_header(data[0:14])))
        storeobj = struct.unpack("!6s6sH", data[0:14])

        if storeobj[0].find(b'\x01\x00\x5e') == 0: #multicast, it maybe dropped for simplfying
            dstip = data[14 + 16:34]
            if dstip.find(b'\xe0\x00\x00\xfb') == 0: #224.0.0.251 MDNS
                pass
            elif dstip.find(b'\xef\xff\xff\xfa') == 0: #239.255.255.250 upnp
                pass
            elif dstip.find(b'\xe0\x00\x00\x16') == 0: #group multicast
                pass
            else:
                self._logger.warning("Discard multicast packet from tap, unknown ip %s", str(dstip))
            return

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
                    try:
                        r1 = sock.send(buf)
                        r2 = sock.send(data)
                    except:
                        self._logger.warning("sock send broadcast error, maybe tunnel[%s] is not connected, should we reconnect? %s", str(k), traceback.format_exc())
                return
        elif eth_protocol == 0x0800: #  IP packet
            dstip = data[14+16:34]
            sock, data =  self.vpnroute(infod, dstip, data)
        elif eth_protocol == 0x86dd: #IPV6
            #self._logger.debug("netdataprocess IPV6, discard it")
            return
        else:
            self._logger.warning("unprocessed protocol %s", hex(eth_protocol))
            return

        #self._logger.debug("send back packet, dst mac: %s", binascii.hexlify(storeobj[0]))

        if sock is None:
            # find socket from mac
            sock = self.querymactable(self._macinfo, infod, storeobj[0])

        if sock is None:
            self._logger.warning("socket is None, can not reply packet")
            return

        c = len(data)
        buf = bytearray(c.to_bytes(2, "big"))
        try:
            r1 = sock.send(buf)
            r2 = sock.send(data)
        except:
            self._logger.warning("dev data process, lost connection on (%s) %s", str(sock.getpair()), traceback.format_exc())

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
            try:
                r1 = sock.send(buf)
                r2 = sock.send(data)
            except:
                self._logger.info("broadcast but can not send, maybe tunnel is not connected")

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
            self._logger.info("Can not find socket from mac %s in %s", binascii.hexlify(mac), str(macinfo))
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
            self._logger.warning("incomplete packet, %d", l)
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
                    self._logger.warning("unknown ARP Pro %d", pro)
                    return
                op = storeobj[4]
                if op == 1 or op == 2: #Arp Request and Arp Reply
                    storeobj = struct.unpack("!6s4s6s4s", data[22:42])
                    s = (storeobj[0], storeobj[1])
                    self._macinfo[pair] = s
                    #self._logger.debug(str(storeobj))
                    self._logger.info("Mac record for %s, mac: %s, ip: %s", pair, binascii.hexlify(s[0]), binascii.hexlify(s[1]))
                else:
                    self._logger.warning("ARP op unprocessed %d", op)
        elif eth_protocol == 0x0800: #IP packet
            #storeobj = struct.unpack("!BBHHHBBH4s4s", data[14:34])
            #_protocol = storeobj[6]
            #_source_address = socket.inet_ntoa(storeobj[8])
            #_destination_address = socket.inet_ntoa(storeobj[9])
            #self._logger.debug("%s, %s, %s, %s", str(_protocol), _source_address, _destination_address, str(data[14+9]))
            if data[14+9] == 17: #UDP
                #storeobj = struct.unpack('!HHHH', data[34:42])
                #source_port = storeobj[0]
                #dest_port = storeobj[1]
                #self._logger.debug("port: %d, %d, %d, %d", source_port, dest_port, data[34], data[35])
                if data[34] == 0 and data[35] == 53:
                    sip = bytes(data[26:30])
                    p, tunnelip = self.findpair(sip)
                    if not p is None:  #it means the reponse from dns server, the dns server is in vpn ip list
                        self.dnsprocess(data[42:], p)
                    else:
                        #self._logger.debug("default dns routine")
                        #self.dnsprocess(data[42:], p)
                        pass
        elif eth_protocol == 0x86dd: #IPV6
            #self._logger.debug("netdataprocess IPV6, discard it")
            return
        else:
            self._logger.warning("unprocessed protocol %s, smac %s, dmac %s", hex(eth_protocol), str(storeobj[0]), str(storeobj[1]))
            return

        r = dev.write(data)
        if r != l:
            self._logger.warning("Warning: write to tap (%d) is smaller than request (%d)", r, l)
        return

    # https://www.zytrax.com/books/dns/ch15/#answer
    def dnsprocess(self, data, pair):
        HEADER = '!HBBHHHH'
        HEADER_SIZE = struct.calcsize(HEADER)
        storeobj = struct.unpack(HEADER, data[:HEADER_SIZE])
        #self._logger.debug("dns data %s", binascii.hexlify(data[:20]))
        #self._logger.debug("%x, %x ,%x, %d, %d, %d, %d", storeobj[0], storeobj[1], storeobj[2], storeobj[3], storeobj[4], storeobj[5], storeobj[6])
        if (storeobj[1] & 0xf8) != 0x80: #dns response message for standard query
            self._logger.info("not dns response message for standard query")
            return
        if (storeobj[2] & 0x0f) != 0x00: #error exist
            self._logger.info("dns error response")
            return
        if storeobj[5] != 0 or storeobj[6] != 0:
            self._logger.warning("Warning, dns parsing, name server field and additional is not processed")

        self._logger.debug("questions %d, answers %d", storeobj[3], storeobj[4])
        data = data[HEADER_SIZE:]
        off = 0
        for cnt in range(0, storeobj[3]):
            off += data.find(b'\0') #skip name
            #self._logger.debug(str(data[1:off]))
            #self._logger.debug(binascii.hexlify(data[off:off+5]))
            off += 5  #skip \0, QTYPE, QCLASS
        data = data[off:]
        off = 0
        for cnt in range(0, storeobj[4]):
            if (data[0] & 0xc0) == 0xc0: #name label
                off += 2
            else:
                off += data.find(b'\0') + 1 #skip name
            self._logger.debug(binascii.hexlify(data[off:off + 10]))
            typ = data[off+1]  #TYPE
            rdlen = data[off + 8] * 256 + data[off + 9]
            if typ == 1: # A record
                #self._logger.debug(binascii.hexlify(data[off+10:off+10+rdlen]))
                for i in range(off+10, off+10+rdlen, 4):
                    #self._logger.debug("%s, %s", type(data[i:i+4]), binascii.hexlify(data[i:i+4]))
                    self.appendtovpn(pair, data[i:i+4])
            off += (10 + rdlen)

    def appendtovpn(self, pair, ip):
        for l in self._vpncfglist:  #TODO, we should comparing pair with ...
            if not l[3] is None:
                break
        else:
            return

        if not ip in l[3]:
            l[3].append(bytes(ip))

        self._logger.debug("new vpn ip list %s", str(l[3]))
        pass



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
            self.router_iptable_destroy(self.tuntapname())
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
        dps = dict()
        try:
            for k,v in self._mgrdict.items():
                dps[k] = v
        except:
            self._logger.warning(traceback.format_exc())
            pass
        dps["tapname"] = self.tuntapname()
        return dps

    def tuntapname(self):
        prefix = "v." + self._ip
        return prefix

    def routinefordns(self, default):
        with open("/etc/dnsmasq.conf", "r") as f:
            for l in f.readlines():
                if l.find("server=") == 0:
                    a = l.split("=")
                    items = a[1].split(".")
                    if not len(items) == 4:
                        continue
                    self.shell(["ip", "route", "add", a[1].strip(), "via", default])
                    break
        pass

    #tapname: self.tuntapname()
    #
    def router_iptable_setup(self, infod, gateway, tapname):
        d = dict()
        for k, v in infod.items():
            d[k[0]] = True        #should this ip use default router
        sp = subprocess.run(["ip", "route", "list"], stdout=subprocess.PIPE)
        for l in sp.stdout.decode().splitlines():
            items = l.split()
            if "default via" in l:
                default = items[2]
                continue
            a = items[0].split('.')
            if len(a) != 4:
                continue
            subnet = ".".join(a[0:3])
            for ip in d.keys():
                if subnet in ip:
                    d[ip] = False
        for ip, v in d.items():
            if not v:
                continue
            self.shell(["ip", "route", "add", ip+"/32", "via", default])
        self.shell(["ip", "route", "delete", "default"])
        self.shell(["ip", "route", "add", "default", "via", gateway])
        try:
            self.routinefordns(default)
        except:
            self._logger.info("Warning can not set route for dns, %s", traceback.format_exc())
        #self.shell(["systemctl", "restart", "dnsmasq"])  #restart dnsmasq to clear dns cache
        ''' TODO, as dynamic change iptable always block, we may find the way in iptable config file
        sp = subprocess.run(["iptables", "-t", "nat", "-v", "-L", "POSTROUTING"], stdout=subprocess.PIPE)
        for l in sp.stdout.decode().splitlines():
            items = l.split()
            if len(items) < 7:
                continue
            if tapname in items[6]:
                break
        else:
            self.shell(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", tapname, "-j", "MASQUERADE"])
        '''
        pass

    def router_iptable_destroy(self, tapname):
        ''' TODO, as dynamic change iptable always block, we may find the way in iptable config file
        sp = subprocess.run(["iptables", "-t", "nat", "-v", "-L", "POSTROUTING", "--line-number"], stdout=subprocess.PIPE)
        for l in sp.stdout.decode().splitlines():
            items = l.split()
            if len(items) < 8:
                continue
            if tapname in items[7]:
                self.shell(["iptables", "-t", "nat", "-D", "POSTROUTING", items[0]])
                pass
            pass
        '''
        self.shell(["/usr/sbin/netplan", "apply"])