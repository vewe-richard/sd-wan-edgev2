#https://stackoverflow.com/questions/20476555/non-blocking-connect
import binascii
import multiprocessing
import struct
import traceback
import signal
import subprocess
import time
import os
import socket
import errno
import select
from tuntap import TunTap

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

    def run2(self):
        self._macinfo = dict()
        infod = dict()
        for s in self._node["server"]:
            items = s.split(":")
            ip = items[0]
            if len(items) > 1:
                port = int(items[1])
            else:
                port = int(self._node["port"])
            pair = (ip, port)
            infod[pair] = None
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
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setblocking(0)
                    sock.connect_ex(k)
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
                    data = f.recv(2048)
                    l = len(data)
                    if l == 0:
                        reconnect = True
                        self._logger.debug("socket %d got data: 0", f.fileno())
                    elif l < 3:
                        continue
                    else:
                        leninpkt = data[0] * 256 + data[1] + 2
                        if l == leninpkt:
                            self.netdataprocess(dev, self.getk(infod, f), data[2:], l-2)
                        else:
                            self.netdataprocess(dev, self.getk(infod, f), data, l)

                except:
                    self._logger.debug(traceback.format_exc())  #TODO, we may recreate socket?
                    reconnect = True

                if reconnect:
                    f.close()
                    pair = self.getk(infod, f)
                    infod[pair] = (f, True, time.time())

    def devdataprocess(self, infod, data, l):
        if l < 14:
            self._logger.debug("incomplete packet, %d", l)
            raise Exception("TODO") #to uncomment
            return
        #self._logger.debug(str(self.eth_header(data[0:14])))
        storeobj = struct.unpack("!6s6sH", data[0:14])

        eth_protocol = storeobj[2]
        #self._logger.debug("protocol, %s", hex(eth_protocol))
        if eth_protocol == 0x0806 or eth_protocol == 0x0800: # ARP and IP packet
            pass
        elif eth_protocol == 0x86dd: #IPV6
            #self._logger.debug("netdataprocess IPV6, discard it")
            return
        else:
            self._logger.debug("unprocessed protocol %s", hex(eth_protocol))
            return
        self._logger.debug("send back packet, dst mac: %s", binascii.hexlify(storeobj[0]))
        # find socket from mac
        sock = self.querymactable(self._macinfo, infod, storeobj[0])
        if sock is None:
            return

        c = len(data)
        buf = bytearray(c.to_bytes(2, "big"))

        r1 = sock.send(buf)
        r2 = sock.send(data)

        pass

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
            self._logger.info("!Can not find socket form mac %s", binascii.hexlify(mac))
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
                if op == 1: #Arp Request
                    storeobj = struct.unpack("!6s4s6s4s", data[22:42])
                    s = (storeobj[0], storeobj[1])
                    self._macinfo[pair] = s
                    #self._logger.debug(str(storeobj))
                    self._logger.debug("Mac record for %s, mac: %s, ip: %s", pair, binascii.hexlify(s[0]), binascii.hexlify(s[1]))
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

