# reference: https://pypi.org/project/python-pytuntap/
# apt-get install python3-pip
# pip3 install python-pytuntap
# https://docs.python.org/3/library/select.html
import select
import signal
import socket
import time
from edgeinit.base import HttpBase
from pathlib import Path
import json
import traceback
import multiprocessing
import subprocess
from tuntap import TunTap
import os

class DataProcess(multiprocessing.Process):
    def __init__(self, logger, devname, sock, mgrdict, bridge = None, **kwargs):
        super().__init__(**kwargs)
        self._logger = logger
        self._devname = devname
        self._bridge = bridge
        self._socket = sock
        self._mgrdict = mgrdict
        self._dev = None
        self._mgrdict["status"] = "INIT"

    def prepareenv(self):
        # create devname
        if "sdtap" in self._devname:
            self.shell(["ip", "tuntap", "add", "mode", "tap", self._devname])
            dev = TunTap(nic_type="Tap", nic_name=self._devname)
        else:
            self.shell(["ip", "tuntap", "add", "mode", "tun", self._devname])
            dev = TunTap(nic_type="Tun", nic_name=self._devname)
        self._dev = dev
        self.shell(["ip", "link", "set", self._devname, "up"])

        if not self._bridge is None:
            ret = self.shell(["brctl", "addif", self._bridge, self._devname])
            if ret != 0:
                raise Exception("Can not add tap dev to bridge")

        self._mgrdict["pid"] = self.pid
        pass

    def loop(self):
        dev = self._dev
        inputs = [self._socket, dev.handle]
        while True:
            rfd, wfd, xfd = select.select(inputs, [], [])
            exit = False
            for fd in rfd:
                if fd == self._socket:
                    data = self._socket.recv(2048)
                    l = len(data)
                    if l == 0:
                        exit = True
                        break
                    if l < 3:
                        #self._logger.debug("net2tap: discard length %d", l)
                        continue

                    leninpkt = data[0]*256 + data[1] + 2
                    if l == leninpkt:
                        r = dev.write(data[2:])
                        self._logger.debug("net2tap %s: towrite %d realout %d", self._devname, l-2, r)
                    else:
                        r = dev.write(data)
                        self._logger.debug("net2tap2 %s: towrite %d realout %d", self._devname, l, r)

                if fd == dev.handle:
                    data = dev.read(2048)
                    l = len(data)
                    buf = bytearray(l.to_bytes(2, "big"))

                    r1 = self._socket.send(buf)
                    r2 = self._socket.send(data)
                    #self._logger.debug("tap2net %s: len %d real out %d %d", self._devname, l, r1, r2)
            if exit:
                break

    def run(self):
        self._logger.info("DataProcess run: tuntap %s bridge %s <=> sock %d", self._devname, self._bridge, self._socket.fileno())
        try:
            self.prepareenv()
        except Exception as e:
            if not self._dev is None:
                self._dev.close()
            if "sdtap" in self._devname:
                self.shell(["ip", "tuntap", "del", "mode", "tap", "name", self._devname])
            else:
                self.shell(["ip", "tuntap", "del", "mode", "tun", "name", self._devname])

            self._logger.warn("DataProcess %s", traceback.format_exc())
            self._mgrdict["status"] = str(e)
            return

        self._mgrdict["status"] = "Enter Loop"
        try:
            self.loop()
        except KeyboardInterrupt:
            self._logger.warn("DataProcess KeyboardInterrupt")
        except Exception as e:
            self._logger.warn("DataProcess %s", traceback.format_exc())
            self._mgrdict["status"] = str(e)
        finally:
            self._dev.close()
            if "sdtap" in self._devname:
                self.shell(["ip", "tuntap", "del", "mode", "tap", "name", self._devname])
            else:
                self.shell(["ip", "tuntap", "del", "mode", "tun", "name", self._devname])

    def devname(self):
        return self._devname

    def shell(self, args, ignoreerror = True):
        self._logger.info("DataProcess: run %s", str(args))
        sp = subprocess.run(args)
        return sp.returncode

class NodeProcess(multiprocessing.Process):
    def __init__(self, node, logger, mgrdict, **kwargs):
        super().__init__(**kwargs)
        self._node = node
        self._logger = logger
        self._mgrdict = mgrdict
        self._mgrdict["status"] = "INIT"
        pass

    def run(self):
        while True:
            time.sleep(1)
            #self._logger.debug("NodeProcess loop")

    def shell(self, args, ignoreerror = True):
        self._logger.info("NodeProcess run %s", str(args))
        sp = subprocess.run(args)
        return sp.returncode

    def bridgename(self):
        return "sdtunnel-" + self._subnet3rd

    def tuntapname(self):
        if self._node["tunortap"] == "tun":
            prefix = "sdtun-" + self._subnet3rd
        else:
            prefix = "sdtap-" + self._subnet3rd
        name = prefix + "-" + str(self._tuntapid)
        self._tuntapid += 1
        return name

class ClientProcess(NodeProcess):
    def __init__(self, node, logger, mgrdict, **kwargs):
        super().__init__(node, logger, mgrdict, **kwargs)
        self._ip = self._node["ptunnelip"]
        items = self._ip.split(".")
        self._subnet3rd = items[2]
        self._tuntapid = 10


class ServerProcess(NodeProcess):
    def __init__(self, node, logger, mgrdict, **kwargs):
        super().__init__(node, logger, mgrdict, **kwargs)
        self._ip = self._node["tunnelip"]
        items = self._ip.split(".")
        self._subnet3rd = items[2]
        self._tuntapid = 100
        if self._node["tunortap"] == "tap":  #need create bridge
            br = self.bridgename()
            self.releasebridge(br)
            self.shell(["brctl", "addbr", br])
            self.shell(["ip", "link", "set", br, "up"])
            ret = self.shell(["ip", "addr", "add", self._ip + "/24", "dev", br])
            if ret != 0:
                #raise Exception("Can not create bridge")  TODO uncomment
                pass

    def releasebridge(self, br):
        ret = self.shell(["ip", "link", "show", br])
        if ret == 0:
            self.shell(["ip", "link", "set", br, "down"])
            self.shell(["brctl", "delbr", br])

    def release(self):
        if self._node["tunortap"] == "tap":  #need create bridge
            br = self.bridgename()
            self.releasebridge(br)

    def run(self):
        # create a socket object
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            serversocket.bind(("0.0.0.0", int(self._node["port"])))
            serversocket.listen(5)
        except Exception as e:
            serversocket.close()
            self.release()
            self._logger.warning("NodeProcess %s", traceback.format_exc())
            self._mgrdict["status"] = str(e)
            return

        self._mgrdict["status"] = "Enter Loop"

        try:
            self.loop(serversocket)
        except KeyboardInterrupt:
            self._logger.warning("NodeProcess Loop exception, KeyboardInterrupt")
        except Exception as e:
            self._logger.warning("NodeProcess Loop exception, %s", traceback.format_exc())
            self._mgrdict["status"] = str(e)
        finally:
            # TODO close dataprocesses, and close serversocket, release bridge
            serversocket.close()
            self.release()
            pass

    def loop(self, serversocket):
        while True:
            clientsocket, addr = serversocket.accept()
            self._logger.info("NodeProcess Accept: %s, %s", str(clientsocket), str(addr))
            #TODO
            '''
            mgrdict = self._mgr.dict()
            try:
                pre = self._connections[addr[0]]
                dp = DataProcess(self._logger, pre.devname(), clientsocket, mgrdict, bridge = self.bridgename())
            except: #create it self
                devname = self.tuntapname()
                dp = DataProcess(self._logger, devname, clientsocket, mgrdict, bridge = self.bridgename())
    
            dp.start()
            self._connections[addr[0]] = dp
            '''

class Http(HttpBase):
    def __init__(self, logger):
        super().__init__(logger)
        self._datapath = str(Path.home()) + "/.sdwan/edgepoll/"
        self._configpath = self._datapath + "stun.json"
        self._data = []
        self._nodes = dict()

    def term(self):
        for k, v in self._nodes.items():
            v.terminate()

    def join(self):
        for k, v in self._nodes.items():
            self._logger.info("join node %s: counter %d", k, v.counter())
            v.join()

    def start(self):
        try:
            with open(self._configpath) as json_file:
                self._data = json.load(json_file)
        except FileNotFoundError:
            Path(self._datapath).mkdir(parents=True, exist_ok=True)

            with open(self._configpath, 'w') as json_file:
                json.dump(self._data, json_file)
        except:
            self._logger.warn(traceback.format_exc())
        for node in self._data:
            self._logger.info("stun start node: %s", str(node))
            self.startnode(node)
        pass

    def startnode(self, node):
        try:
            ip = node["ptunnelip"]
        except:
            ip = node["tunnelip"]

        try:
            self._nodes[ip]
            return "OK"
        except:
            if node["node"] == "server":
                np = ServerProcess(node, self._logger)
            else:
                np = ClientProcess(node, self._logger)
        np.start()
        self._nodes[ip] = np
        return "OK"

    def addclient(self, msg):
        return "TODO"

    #{"entry": "http", "module": "stun", "cmd": "add", "node": "server", "port": "1299",
    #            "tunortap": "tap", "tunnelip": "192.168.23.19", "tunneltype": "ipsec"}
    def addserver(self, msg):
        tunnelip = msg["tunnelip"]
        port = msg["port"]
        tunneltype = msg["tunneltype"]
        tunortap = msg["tunortap"]

        #check if server is already there
        for n in self._data:
            if n["node"] == "server":
                if n["tunnelip"] == tunnelip:
                    if n["port"] == port and n["tunneltype"] == tunneltype and n["tunortap"] == tunortap:
                        self._logger.info("this server is already there")
                        return "OK"
                if n["port"] == port:
                    return "NOK, port conflict with previous server"
                ip = n["tunnelip"]
            elif n["node"] == "client":
                ip = n["ptunnelip"]

            #if same subnet, then return error
            if self.samesubnet(ip, tunnelip):
                return "NOK, subnet conlict"

        node = dict()
        node["node"] = "server"
        node["port"] = port
        node["tunnelip"] = tunnelip
        node["tunortap"] = tunortap
        node["tunneltype"] = tunneltype

        rlt = self.startnode(node)
        if rlt != "OK":
            return rlt

        #add to config file
        self.appendnode(node)
        return "OK"

    def addnode(self, node, msg):
        if node == "client":
            result = self.addclient(msg)
        elif node == "server":
            result = self.addserver(msg)
        else:
            result = "Unknown node: " + node
        return result

    def delnode(self, node, msg):
        if node == "client":
            result = self.delclient(msg)
        elif node == "server":
            result = self.delserver(msg)
        else:
            result = "Unknown node: " + node
        return result

    def delserver(self, msg):
        ip = msg["tunnelip"]
        self._logger.info("nodes %s", str(self._nodes))

        try:
            np = self._nodes[ip]
            self._logger.info("delserver: np %s", str(np))
            cnts = np.connections()
            self._logger.info("connections: %s", str(cnts))
            fileno = cnts["10.129.101.99"]
            self._logger.info("fileno: %s", fileno)
            os.kill(fileno, signal.SIGINT)

        except:
            self._logger.info(traceback.format_exc())
            self._logger.info("delserver: can not find server %s", ip)
            pass
        return "OK"

    def delclient(self, msg):
        return "OK"

    def post(self, msg):
        self._logger.debug("stun post handler: %s", str(msg))
        result = "NOK"
        try:
            cmd = msg["cmd"]
            if cmd == "add":
                node = msg["node"]
                result = self.addnode(node, msg)
            elif msg["cmd"] == "delete":
                node = msg["node"]
                result = self.delnode(node, msg)
            else:
                result = "Unknown command: " + cmd
        except:
            self._logger.warn(traceback.format_exc())
            result = traceback.format_exc()

        return result

    def appendnode(self, node):
        self._data.append(node)
        with open(self._configpath, 'w') as json_file:
            json.dump(self._data, json_file)

    def samesubnet(self, ip1, ip2):
        ip1s = ip1.split(".")
        ip2s = ip2.split(".")
        if ip1s[0] == ip1s[0] and ip1s[1] == ip2s[1] and ip1s[2] == ip2s[2]:
            return True
        else:
            return False
# Test every module


if __name__ == "__main__1":
    import logging
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")

    mgrdict = multiprocessing.Manager().dict()

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind(("0.0.0.0", 55556))
    serversocket.listen(5)
    clientsocket, addr = serversocket.accept()
    logger.info("%s, %s", str(clientsocket), str(addr))

    dp = DataProcess(logger, "sdtaptest", clientsocket, mgrdict, bridge="bridge999")
    dp.start()

    '''
    input("Enter to test kill function")
    pid = mgrdict["pid"]
    logger.info("pid of DataProcess %d")
    os.kill(pid, signal.SIGINT)
    input("Enter to continue")
    '''

    try:
        dp.join()
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt in Main")
    finally:
        clientsocket.close()
        serversocket.close()
        logger.warning("Close server socket and client socket")

    try:
        status = mgrdict["status"]
    except Exception as e:
        logger.warning("Can not access mgrdict due to %s", str(e))
        status = "Unaccessable"
    dp.join()
    logger.warning("Exit, Dataprocess status: %s", status)

if __name__ == "__main__":
    import logging
    import sys
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    logger.debug("%s", str(sys.argv))

    node = dict()
    node["port"] = "55556"
    node["tunortap"] = "tap"
    node["tunneltype"] = "ipsec"
    mgrdict = multiprocessing.Manager().dict()

    try:
        if sys.argv[1] == "server":
            node["node"] = "server"
            node["tunnelip"] = "10.139.47.1"
            np = ServerProcess(node, logger, mgrdict)
        else:
            node["node"] = "client"
            node["tunnelip"] = sys.argv[2]
            np = ClientProcess(node, logger, mgrdict)
    except:
        logger.info(traceback.format_exc())
        logger.info("Usage: s20_tun.py server|client [ptunnelip]")
        sys.exit(-1)

    np.start()
    while True:
        cmd = input("Enter cmd:")
        logger.info("cmd: %s, len %d", cmd, len(cmd))
        if len(cmd) == 0:
            break
        if cmd == "info":
            logger.debug("bridge name: %s, tuntap name: %s", np.bridgename(), np.tuntapname())

    try:
        np.join()
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt in Main")

    try:
        status = mgrdict["status"]
    except Exception as e:
        logger.warning("Can not access mgrdict due to %s", str(e))
        status = "Unaccessable"

    np.join()
    logger.warning("Exit, NodeProcess status: %s", status)