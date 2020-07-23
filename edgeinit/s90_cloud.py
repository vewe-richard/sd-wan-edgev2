# test environment
# cat /home/richard/.sdwan/edgepoll/network.json
# {"enable": true, "bridges": [{"name": "br0", "intfs": "enp1s0 enp3s0", "ip": "10.100.0.30/24"}], "nat": "enp1s0 usb0"}
# export PYTHONPATH=$PWD && python3 edgeinit/s10_network.py
# or
# run edgepoll/__main__.py
# and run testhttppost.py to test post a command to network
#
from edgeinit.base import MainBase, HttpBase
import subprocess
import json
import time
import traceback
from edgeinit.vdevs.docker import Docker
from edgeinit.vdevs.gw import GW

class Http(HttpBase):
    def __init__(self, logger, cfgfile=None):
        super().__init__(logger)
        if cfgfile is None:
            self._configpath = self.configpath() + "/cloud.json"
        else:
            self._configpath = cfgfile
        try:
            with open(self._configpath) as json_file:
                self._data = json.load(json_file)
        except Exception as e:
            self._logger.warning(traceback.format_exc())
            self._data = dict()
        self._nodes = dict()

    def start(self):
        self._logger.info(str(self._data))
        try:
            nodes = self._data["nodes"]
        except:
            nodes = []
            pass
        self.start_nodes(nodes)
        self.link_nodes(nodes)
        self.bridge2_nodes(nodes)
        pass

    def start_nodes(self, nodes):
        for node in nodes:
            try:
                t = node["type"].lower()
                name = node["name"]
            except:
                continue

            dev = None
            self._logger.info(str(node))
            if t == "docker":
                dev = self.start_docker(node)
            elif t == "gw":
                dev = self.start_gw(node)
            if dev is None:
                continue

            self._nodes[name] = dev
        pass

    def start_docker(self, node):
        try:
            docker = Docker(self._logger, node["name"], image=node["image"], privileged=True)
            docker.start()
            return docker
        except:
            pass
        return None

    def start_gw(self, node):
        try:
            gw = GW(self._logger, node["name"])
            try:
                gw.enablegw(node["ip"])
            except Exception as e:
                self._logger.warning(str(e))
                pass
            gw.start()
            return gw
        except Exception as e:
            self._logger.warning(str(e))
            pass
        return None

    def link_nodes(self, nodes):
        for node in nodes:
            try:
                nets = node["net"]
                name = node["name"]
                dev = self._nodes[name]
            except:
                continue
            if dev is None:
                continue
            for net in nets:
                try:
                    gw = self._nodes[net]
                    if gw.type() == "GW":
                        gw.adddocker(dev)
                except:
                    pass

    def bridge2_nodes(self, nodes):
        for node in nodes:
            try:
                nets = node["bridgeto"]
                name = node["name"]
                dev = self._nodes[name]
            except:
                continue
            if dev is None:
                continue
            for net in nets:
                try:
                    gw = self._nodes[net]
                    if gw.type() == "GW":
                        gw.bridge2(dev)
                except:
                    pass

        pass

    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))

    def term(self):
        for n, handle in self._nodes.items():
            handle.remove()
        time.sleep(0.1)
        pass

class Main(MainBase):
    def start(self):
        pass

    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))
        pass

if __name__ == "__main__":
    import logging
    import sys
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    logger.debug("%s", str(sys.argv))

    h = Http(logger)
    h.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except:
        pass
    finally:
        h.term()
    time.sleep(2)
    logger.debug("end")
    pass