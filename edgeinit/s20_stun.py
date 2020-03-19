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

class Kill2Exception(Exception):
    pass

def signal_kill2_handler(signum, frame):
    raise Kill2Exception("Kill2")

class DataProcess(multiprocessing.Process):
    def __init__(self, logger, devname, sock, mgrdict, bridge = None, ip = None, **kwargs):
        super().__init__(**kwargs)
        self._logger = logger
        self._devname = devname
        self._bridge = bridge
        self._socket = sock
        self._mgrdict = mgrdict
        self._dev = None
        self._mgrdict["status"] = "INIT"
        self._mgrdict["recv"] = 0
        self._mgrdict["send"] = 0
        self._ip = ip

    def prepareenv(self):
        # create devname
        if "sdtap" in self._devname:
            self.shell(["ip", "tuntap", "add", "mode", "tap", self._devname])
            dev = TunTap(nic_type="Tap", nic_name=self._devname)
        else:
            self.shell(["ip", "tuntap", "add", "mode", "tun", self._devname])
            dev = TunTap(nic_type="Tun", nic_name=self._devname)
        if not self._ip is None:
            dev.config(self._ip, "255.255.255.0")
        self._dev = dev
        self.shell(["ip", "link", "set", self._devname, "up"])

        if not self._bridge is None:
            ret = self.shell(["brctl", "addif", self._bridge, self._devname])
            if ret != 0:
                raise Exception("Can not add tap dev to bridge")

        self._mgrdict["pid"] = self.pid
        pass

    def kill2(self):
        try:
            pid = self._mgrdict["pid"]
            os.kill(pid, signal.SIGUSR1)
        except:
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
                        self._mgrdict["status"] = "lost"
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
                    self._mgrdict["recv"] += r

                if fd == dev.handle:
                    data = dev.read(2048)
                    l = len(data)
                    buf = bytearray(l.to_bytes(2, "big"))

                    r1 = self._socket.send(buf)
                    r2 = self._socket.send(data)
                    self._mgrdict["send"] += r2
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
            self._mgrdict["status"] = type(e).__name__ + ":" + str(e)
            return

        self._mgrdict["status"] = "Running"
        signal.signal(signal.SIGUSR1, signal_kill2_handler)
        try:
            self.loop()
        except KeyboardInterrupt:
            self._logger.warn("DataProcess KeyboardInterrupt")
        except Kill2Exception as e:
            self._logger.warn("DataProcess Kill2Exception")
            self._mgrdict["status"] = "Exit"
        except Exception as e:
            self._logger.warn("DataProcess %s", traceback.format_exc())
            self._mgrdict["status"] = type(e).__name__ + ":" + str(e)
        finally:
            self._dev.close()
            if "sdtap" in self._devname:
                self.shell(["ip", "tuntap", "del", "mode", "tap", "name", self._devname])
            else:
                self.shell(["ip", "tuntap", "del", "mode", "tun", "name", self._devname])
            self._logger.info("DataProcess(%s) exit", self._devname)

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

        self._ip = self._node["tunnelip"]
        items = self._ip.split(".")
        self._subnet3rd = items[2]
        self._subnet4th = items[3]
        self._port = int(self._node["port"])
        pass

    def run(self):
        self._mgrdict["pid"] = self.pid
        signal.signal(signal.SIGUSR1, signal_kill2_handler)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self._logger.warning("NodeProcess Loop exception, KeyboardInterrupt")
        except Kill2Exception:
            self._logger.warning("NodeProcess Kill2Exception")
            self._mgrdict["status"] = "Exit"
        self._logger.warning("NodeProcess Exit")

    def shell(self, args, ignoreerror = True):
        self._logger.info("NodeProcess run %s", str(args))
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

class ClientProcess(NodeProcess):
    def __init__(self, node, logger, mgrdict, **kwargs):
        super().__init__(node, logger, mgrdict, **kwargs)
        self._server = self._node["server"]
        self._socket = None
        self._dp = None

    def tuntapname(self):
        if self._node["tunortap"] == "tun":
            prefix = "sdtun-" + self._subnet3rd + "." + self._subnet4th
        else:
            prefix = "sdtap-" + self._subnet3rd + "." + self._subnet4th
        return prefix

    def run(self):
        self._mgrdict["pid"] = self.pid
        signal.signal(signal.SIGUSR1, signal_kill2_handler)
        try:
            while True:
                self.run2()
                time.sleep(6)
        except KeyboardInterrupt:
            self._logger.warning("ClientProcess Loop exception, KeyboardInterrupt")
        except Kill2Exception:
            try:
                self._dp.kill2()
            except Exception as e:
                self._logger.warning("ClientProcess kill dataprocess failed: %s", str(e))

            self._logger.warning("ClientProcess Kill2Exception")
            self._mgrdict["status"] = "Exit"
        except Exception as e:
            self._logger.warning("ClientProcess Loop exception, %s", traceback.format_exc())
            self._mgrdict["status"] = type(e).__name__ + ":" + str(e)
        finally:
            try:
                self._dp.join(timeout=0.1)
            except Exception as e:
                self._logger.warning("ClientProcess join dataprocess failed: %s", str(e))

            if not self._socket is None:
                self._socket.close()

            try:
                self._dp.terminate()
            except Exception as e:
                self._logger.warning("ClientProcess terminate dataprocess failed: %s", str(e))
        self._logger.warning("ClientProcess Exit")



    def run2(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket = s
            self._mgrdict["status"] = "Connecting"
            s.connect((self._server, self._port))
        except Exception as e:
            self._logger.warning("ClientProcess %s", traceback.format_exc())
            self._mgrdict["status"] = type(e).__name__ + ":" + str(e) + "-> Reconnecting"
            return

        mgrdict = multiprocessing.Manager().dict()
        dp = DataProcess(self._logger, self.tuntapname(), s, mgrdict, ip=self._ip)
        self._mgrdict["status"] = "Connecting"
        self._mgrdict["dp"] = mgrdict
        self._dp = dp
        dp.start()
        dp.join()
        self._dp = None
        self._mgrdict["status"] = "DataProcess Break -> Reconnecting"

class ServerProcess(NodeProcess):
    def __init__(self, node, logger, mgrdict, **kwargs):
        super().__init__(node, logger, mgrdict, **kwargs)
        self._tuntapid = 100
        self._connections = dict()
        self._reconnecttimes = multiprocessing.Manager().dict()
        if self._node["tunortap"] == "tap":  #need create bridge
            br = self.bridgename()
            self.releasebridge(br)
            self.shell(["brctl", "addbr", br])
            self.shell(["ip", "link", "set", br, "up"])
            ret = self.shell(["ip", "addr", "add", self._ip + "/24", "dev", br])
            if ret != 0:
                raise Exception("Can not create bridge")
                pass

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
            serversocket.bind(("0.0.0.0", self._port))
            serversocket.listen(5)
        except Exception as e:
            serversocket.close()
            self.release()
            self._logger.warning("NodeProcess %s", traceback.format_exc())
            self._mgrdict["status"] = type(e).__name__ + ":" + str(e)
            return

        self._mgrdict["status"] = "Running"
        self._mgrdict["pid"] = self.pid
        signal.signal(signal.SIGUSR1, signal_kill2_handler)
        try:
            self.loop(serversocket)
        except KeyboardInterrupt:
            self._logger.warning("NodeProcess Loop exception, KeyboardInterrupt")
        except Kill2Exception:
            self._logger.warning("NodeProcess Kill2Exception")
            self._mgrdict["status"] = "EXIT"
            for key, dp in self._connections.items():
                dp.kill2()
        except Exception as e:
            self._logger.warning("NodeProcess Loop exception, %s", traceback.format_exc())
            self._mgrdict["status"] = type(e).__name__ + ":" + str(e)
        finally:
            for key, dp in self._connections.items():
                dp.join(timeout=0.1)
            serversocket.close()
            self.release()
            for key, dp in self._connections.items():
                dp.terminate()

            self._logger.info("ServerProcess(%s) Exit", self._ip)
            pass

    def loop(self, serversocket):
        while True:
            clientsocket, addr = serversocket.accept()
            self._logger.info("NodeProcess Accept: %s, %s", str(clientsocket), str(addr))
            try:
                pre = self._connections[addr[0]]
                pre.terminate()
                pre.join(timeout=0.1)
                devname = pre.devname()
                self._reconnecttimes[addr[0]] += 1
            except: #create it self
                devname = self.tuntapname()
                self._reconnecttimes[addr[0]] = 0

            mgrdict = multiprocessing.Manager().dict()
            dp = DataProcess(self._logger, devname, clientsocket, mgrdict, bridge = self.bridgename())
            self._connections[addr[0]] = dp
            self._mgrdict[addr[0]] = mgrdict
            dp.start()

    def dpstatus(self):
        dps = dict()
        try:
            for k, v in self._mgrdict.items():
                if not "." in k:
                    continue
                try:
                    status = dict()
                    status["status"] = v["status"]
                    status["reconnect"] = self._reconnecttimes[k]
                    status["recv"] = v["recv"]
                    status["send"] = v["send"]
                    dps[k] = status
                except:
                    self._logger.warning(traceback.format_exc())
                    pass
        except:
            pass
        return dps

class Http(HttpBase):
    #external functions, init, term, join, start, post
    def __init__(self, logger):
        super().__init__(logger)
        self._datapath = str(Path.home()) + "/.sdwan/edgepoll/"
        self._configpath = self._datapath + "stun.json"
        self._nodes = dict()

    def start(self):
        data = []
        try:
            with open(self._configpath) as json_file:
                data = json.load(json_file)
        except FileNotFoundError:
            Path(self._datapath).mkdir(parents=True, exist_ok=True)
            with open(self._configpath, 'w') as json_file:
                json.dump(data, json_file)
        except:
            self._logger.warn(traceback.format_exc())
        for node in data:
            #self._logger.info("stun start node: %s", str(node))
            if not self.validnode(node):
                self._logger.info("stun start, invalid node %s", str(node))
                continue
            try:
                self.startnode(node)
            except:
                self._logger.info("stun start, %s", traceback.format_exc())

    def validnode(self, node):
        try:
            p = int(node["port"])
            ip = node["tunnelip"]
            st = self.subnet(ip)
            if node["node"] == "server":
                pass
            elif node["node"] == "client":
                server = node["server"]
            else:
                raise Exception("Unknown node type")

            if not (node["tunortap"] in ["tap", "tun"]):
                raise Exception("Invalid tunortap field")
            if not (node["tunneltype"] in ["ipsec",]):
                raise Exception("Invalid tunneltype")

            return True
        except:
            self._logger.warning("Invalid stun node, %s", traceback.format_exc())
            return False

    def subnet(self, ip):
        items = ip.split(".")
        st = items[0] + "." + items[1] + "." + items[2]
        return st

    def startnode(self, node):
        snt = self.subnet(node["tunnelip"])
        self._logger.info("s20 stun start node[%s]: %s", snt, str(node))
        try:
            self._nodes[snt]
            self._logger.info("s20 stun node[%s] is exist", snt)
            return
        except:
            pass

        mgrdict = multiprocessing.Manager().dict()
        if node["node"] == "server":
            np = ServerProcess(node, logger, mgrdict)
        else:
            np = ClientProcess(node, logger, mgrdict)
        np.start()
        self._nodes[snt] = np

    def stopnode(self, node):
        raise Exception("TODO")

    def post(self, msg):
        self._logger.debug("stun post handler: %s", str(msg))
        result = "NOK"
        try:
            cmd = msg["cmd"]
            if cmd == "add":
                result = self.addnode(msg)
            elif msg["cmd"] == "delete":
                result = self.delnode(msg)
            else:
                result = "Unknown command: " + cmd
        except Exception as e:
            self._logger.warn("stun %s", traceback.format_exc())
            result = "Exception " + type(e).__name__ + ":" + str(e)

        return result

    def addnode(self, msg):
        if not self.validnode(msg):
            return "Invalid node"
        try:
            self.startnode(msg)
            raise Exception("add to json file")
            return "OK"
        except Exception as e:
            return "Exception " + type(e).__name__ + ":" + str(e)

    def delnode(self, msg):
        try:
            ip = msg["tunnelip"]
            st = self.subnet(ip)
            if not msg["node"] in ["server", "client"]:
                return "Invalid node type"
        except:
            return "Invalid node"

        try:
            self.stopnode(msg)
            raise Exception("remove from json file")
            return "OK"
        except Exception as e:
            return "Exception " + type(e).__name__ + ":" + str(e)

    def term(self):
        for k, v in self._nodes.items():
            v.kill2()

    def join(self):
        for k, v in self._nodes.items():
            self._logger.info("stun join node %s", k)
            v.join()

    def appendnode(self, node):
        self._data.append(node)
        with open(self._configpath, 'w') as json_file:
            json.dump(self._data, json_file)

# Test every module
if __name__ == "__main__":
    import logging
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    http = Http(logger)
    http.start()

    opts = {"entry": "http", "module": "stun", "cmd": "delete", "node": "server", "port": "55556",
            "tunortap": "tap", "tunnelip": "192.168.2.29", "tunneltype": "ipsec", "remoteip": "10.129.101.99"}
    #resp = http.post(opts)
    #logger.info("resp: %s", resp)

    while True:
        try:
            cmd = input("Enter cmd:")
        except:
            break
        logger.info("cmd: %s, len %d", cmd, len(cmd))
        if cmd == "info":
            pass
        elif cmd == "exit":
            http.term()
            break
        elif cmd == "status":
            pass

    http.join()
    logger.warning("Exit Http")



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

if __name__ == "__main__2":
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
            node["server"] = sys.argv[3]
            np = ClientProcess(node, logger, mgrdict)
    except:
        logger.info(traceback.format_exc())
        logger.info("Usage: s20_tun.py server|client [tunnelip] [serverip]")
        sys.exit(-1)

    np.start()
    while True:
        try:
            cmd = input("Enter cmd:")
        except:
            break
        logger.info("cmd: %s, len %d", cmd, len(cmd))
        if cmd == "info":
            if sys.argv[1] == "server":
                logger.info("bridge name: %s, tuntap name: %s", np.bridgename(), np.tuntapname())
            else:
                logger.info("tuntap name: %s", np.tuntapname())
        elif cmd == "exit":
            np.kill2()
            logger.info("kill nodeprocess")
            break
        elif cmd == "status":
            logger.info("status: %s", np.status())
            dps = np.dpstatus()
            for k, v in dps.items():
                logger.info("\t%s: %s, reconnect %d, recv %d, send %d", k, v["status"], v["reconnect"], v["recv"], v["send"])


    np.join()
    status = np.status()

    logger.warning("Exit, NodeProcess status: %s", status)