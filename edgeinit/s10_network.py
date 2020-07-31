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
from pathlib import Path
import os

class Http(HttpBase):
    def __init__(self, logger, cfgfile=None):
        super().__init__(logger)

        try:
            ip = os.environ["GWIP"]
            self.writeconfig(ip)
        except:
            pass

        if cfgfile is None:
            self._configpath = self.configpath() + "/network.json"
        else:
            self._configpath = cfgfile
        try:
            with open(self._configpath) as json_file:
                self._data = json.load(json_file)
        except:
            self._data = dict()

    def start(self):
        try:
            if not self._data["enable"]:
                raise Exception("network not enable")
        except:
            self._logger.info(self._configpath)
            self._logger.info("network is not enabled, skip")
            return
        try:
            bridges = self._data["bridges"]
        except Exception as e:
            bridges = []
        for bridge in bridges:
            self.setup_bridge(bridge)

        try:
            nats = self._data["nat"].split()
            self.setup_nats(nats)
        except Exception as e:
            import traceback
            self._logger.info(traceback.format_exc())
            pass

        try:
            if self._data["dnsmasq"]:
                self.setup_dnsmasq()
        except:
            pass

    def setup_dnsmasq(self):
        sp = self.popencmd(["/usr/sbin/dnsmasq", "-k"])
        self._dnsmasq = sp
        pass

    def setup_nats(self, nats):
        if len(nats) < 1:
            return
        sp = self.runcmd(["iptables", "-t", "nat", "-L", "POSTROUTING", "--line-numbers", "-v"], stdout=subprocess.PIPE)
        lines = sp.stdout.decode().splitlines()
        for nat in nats:
            for l in lines:
                if "MASQUERADE" in l and nat in l:
                    self._logger.info(f"exist: {l}")
                    break
            else: #
                self.runcmd(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", nat, "-j", "MASQUERADE"])

    def setup_bridge(self, bridge):
        try:
            brname = bridge["name"]
        except:
            self._logger.info("Invalid bridge format")
            return

        try:
            intfs = bridge["intfs"].split()
        except:
            intfs = []

        sp = self.runcmd(["ip", "link", "show", brname])
        if sp.returncode != 0:
            self._logger.info(brname + " is not exist")
            sp = self.runcmd(["ip", "link", "add", brname, "type", "bridge"])
            if sp.returncode != 0:
                self._logger.error("Can not create bridge")
                return
        for intf in intfs:
            sp = self.runcmd(["ip", "link", "set", intf, "master", brname])
            sp = self.runcmd(["ip", "link", "set", intf, "up"])

        try:
            ip = bridge["ip"]
            sp = self.runcmd(["ip", "address", "add", ip, "dev", brname])
        except:
            pass

        sp = self.runcmd(["ip", "link", "set", brname, "up"])


    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))
        try:
            cmd = msg["cmd"]
            if cmd == "bridgeadd":
                brname = msg["brname"]
                intf = msg["intf"]
                return self.bridgeadd(brname, intf)
            elif cmd == "bridgedel":
                brname = msg["brname"]
                intf = msg["intf"]
                return self.bridgedel(brname, intf)
            elif cmd == "newgateway":
                ip = msg["ip"].replace("%2F", "/")
                return self.newgateway(ip)
            else:
                return "Unknown Command"
        except Exception as e:
            return str(e)

    def writeconfig(self, ip):
        data = {"enable": True, "bridges": [{"name": "br0", "ip": ip}],
                "nat": "eth0", "dnsmasq": True}
        with open(f'{Path.home()}/.sdwan/edgepoll/network.json', 'w') as json_file:
            json.dump(data, json_file)

        # dnsmasq config
        '''        
        interface=br0
        dhcp-range = 192.168.1.100,192.168.1.150,24h
        '''
        items = ip.rsplit(".", maxsplit=1)
        with open("/etc/dnsmasq.conf", "w") as f:
            f.write("interface=br0\n")
            range = f'dhcp-range={items[0]}.100,{items[0]}.150,24h\n'
            self._logger.info(range)
            f.write(range)
            f.close()

    def newgateway(self, ip):
        self.writeconfig(ip)

        sp = self.runcmd(["ip", "address", "flush", "dev", "br0"])
        sp = self.runcmd(["ip", "address", "add", ip, "dev", "br0"])
        try:
            self._dnsmasq.terminate()
        except:
            pass
        sp = self.popencmd(["/usr/sbin/dnsmasq", "-k"])
        self._dnsmasq = sp
        self.setup_nats(["eth0"])
        return "OK"

    def bridgeadd(self, brname, intf):
        sp = self.runcmd(["ip", "link", "set", intf, "master", brname])
        if sp.returncode == 0:
            return "OK"
        else:
            return "NOK"

    def bridgedel(self, brname, intf):
        sp = self.runcmd(["ip", "link", "set", intf, "nomaster"])
        if sp.returncode == 0:
            return "OK"
        else:
            return "NOK"

    def status(self):
        return "Status"

    def name(self):
        return "Network"

    def term(self):
        try:
            self._dnsmasq.terminate()
        except:
            pass

    def runcmd(self, cmd, stdout=None):
        self._logger.info(str(cmd))
        sp = subprocess.run(cmd, stdout=stdout)
        #sp = subprocess.run(["echo"], stdout=stdout)
        return sp

    def popencmd(self, cmd, stdout=None):
        self._logger.info(str(cmd))
        sp = subprocess.Popen(cmd, stdout=stdout)
        #sp = subprocess.run(["echo"], stdout=stdout)
        return sp

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

    #m = Main(logger)
    #m.start()
    h = Http(logger, cfgfile="/home/richard/PycharmProjects/sd-wan-edgev2/configs/network.json")
    h.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Break")
    pass