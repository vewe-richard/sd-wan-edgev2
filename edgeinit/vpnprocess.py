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
                    self._logger.debug("tap %d got data %d", f, len(data))
                    self.devdataprocess(infod, data)
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
                            r = self.netdataprocess(dev, self.getk(infod, f), data[2:], l-2)
                        else:
                            r = self.netdataprocess(dev, self.getk(infod, f), data, l)

                except:
                    self._logger.debug(traceback.format_exc())  #TODO, we may recreate socket?
                    reconnect = True

                if reconnect:
                    f.close()
                    pair = self.getk(infod, f)
                    infod[pair] = (f, True, time.time())

    def devdataprocess(self, infod, data):
        pass

    #http://www.bitforestinfo.com/2017/01/how-to-write-simple-packet-sniffer.html
    def netdataprocess(self, dev, pair, data, l):
        self._logger.debug("%s len %d: %s", str(pair), l, str(data[0:14].hex()))
        if l < 14:
            self._logger.debug("incomplete packet, %d", l)
            return
        self._logger.debug(str(self.eth_header(data)))
        return 0

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

