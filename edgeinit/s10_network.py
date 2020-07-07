from edgeinit.base import MainBase, HttpBase
import subprocess
from pathlib import Path
import json

class Http(HttpBase):
    def start(self):
        self._logger.info(__file__ + "  http start()")
        pass

    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))
        pass

    def status(self):
        return "Status"

    def name(self):
        return "Network"

class Main(MainBase):
    def __init__(self, logger, cfgfile=None):
        super().__init__(logger)
        if cfgfile is None:
            sp = subprocess.run(["ip", "netns", "identify"], stdout=subprocess.PIPE)
            for l in sp.stdout.splitlines():
                ns = l.decode().strip()
                if len(ns) > 0:
                    self._configpath = str(Path.home()) + "/.sdwan/edgepoll/" + ns + "/network.json"
                    break
            else:
                self._configpath = str(Path.home()) + "/.sdwan/edgepoll/network.json"
        else:
            self._configpath = cfgfile

        try:
            with open(self._configpath) as json_file:
                self._data = json.load(json_file)
        except:
            self._data = dict()
            return

    def start(self):
        try:
            if not self._data["enable"]:
                raise Exception("network not enable")
        except:
            self._logger.info(self._configpath)
            self._logger.info("network is not enabled, skip")
            return

        self._logger.info(__file__ + "   main start()")
        brname = "epbr1"
        sp = subprocess.run(["ip", "link", "add", brname, "type", "bridge"])
        sp = subprocess.run(["ip", "link", "show", brname])
        if sp.returncode != 0:
            self._logger.info(brname + " is not exist")
            return
        subif = ["fm1-mac2", "fm1-mac3", "fm1-mac5", "fm1-mac6"]
        subif.extend(["fm1-mac4", "fm1-mac10"])  #these two interface can  not be used, however
        for si in subif:
            sp = subprocess.run(["ip", "link", "set", si, "master", brname])
            if sp.returncode != 0:
                self._logger.error("Can not add interface to bridge")
            sp = subprocess.run(["ip", "link", "set", si, "up"])
        sp = subprocess.run(["ip", "link", "set", brname, "up"])
        sp = subprocess.run(["ip", "address", "add", "192.168.2.1/24", "dev", brname])
        sp = subprocess.run(["systemctl", "restart", "isc-dhcp-server"])
        sp = subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "usb0", "-j", "MASQUERADE"])
        sp = subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "fm1-mac9", "-j", "MASQUERADE"])
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

    m = Main(logger)
    m.start()
    pass