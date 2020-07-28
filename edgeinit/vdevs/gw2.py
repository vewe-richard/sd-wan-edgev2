# Usage:
# export PYTHONPATH=$PWD && python3 edgeinit/vdevs/gw2.py
from edgeinit.vdevs.docker import Docker
from edgeinit.vdevs.gw import GW
import subprocess
import time
import random

class GW2(GW):
    def __init__(self, logger, name):
        super().__init__(logger, name)
        self._type = "GW2"
        self._brname = ""
        pass

    def runcmd(self, cmd):
        self._logger.info(str(cmd))
        sp = subprocess.run(cmd)
        return sp.returncode

    def start(self):
        super(GW2, self).start()
        self._brname = f'br-{self.name()}'
        ret = self.runcmd(["ovs-vsctl", "add-br", self._brname])
        if ret != 0:
            self._logger.error("Can not add bridge using openvswitch")
            return
        rd = random.randint(100,999)
        iname = f'e-{rd}'
        pname = f'ep-{rd}'
        ret = self.runcmd(["ip", "link", "add", iname, "type", "veth", "peer", "name", pname])
        ret = self.runcmd(["ovs-vsctl", "add-port", self._brname, iname])
        ret = self.runcmd(["ip", "link", "set", iname, "up"])

        self.addintf(pname)
        ret = self.runcmd(["ip", "netns", "exec", self.name(), "ip", "link", "set", pname, "master", "br0"])
        if ret != 0:
            self._logger.error("Can not add link to docker bridge")
            return
        subprocess.run(["ip", "netns", "exec", self.name(), "ip", "link", "set", pname, "up"])

        pass

    def remove(self):
        super(GW2, self).remove()
        self.runcmd(["ovs-vsctl", "del-br", self._brname])

    def adddocker(self, docker):
        rd = random.randint(100,999)
        iname = f'e{docker.name()[0:6]}-{rd}'
        pname = f'e{self.name()[0:6]}-{rd}'
        sp = subprocess.run(["ip", "link", "add", iname, "type", "veth", "peer", "name", pname])
        ret = self.runcmd(["ovs-vsctl", "add-port", self._brname, iname])
        ret = self.runcmd(["ip", "link", "set", iname, "up"])

        docker.addintf(pname)
        return (iname, pname)

    def bridge2(self, peer_gw):
        pass

    def vxlan(self, cfg):
        pass

if __name__ == "__main__":
    import logging
    import sys
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    logger.debug("%s", str(sys.argv))

    gw = GW2(logger, "gw-test")
    logger.info(gw.name())
    logger.info(gw.type())
    logger.info(gw.mem())
    logger.info(gw.image())
    gw.enablegw("10.10.101.1/24")
    gw.start()

    docker = Docker(logger, "ubuntu-test", image="jiangjqian/edgegate:ubuntu-net", privileged=True)
    docker.start()

    gw.adddocker(docker)

    try:
        while True:
            time.sleep(1)
            logger.info("sleep")
    except KeyboardInterrupt:
        docker.remove()
        gw.remove()
        pass
    time.sleep(2)
    logger.info("end")

