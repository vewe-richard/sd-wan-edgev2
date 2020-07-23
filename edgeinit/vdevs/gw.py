# Usage:
# export PYTHONPATH=$PWD && python3 edgeinit/vdevs/vm.py
# then, we can locate the guest from "ssh -p 10008 127.0.0.1"
# to stop this, if control +c does not work, use kill -s SIGINT "pid of vm.py"
from edgeinit.vdevs.docker import Docker
import subprocess
import time
from edgeutils import utils

class GW(Docker):
    def __init__(self, logger, name, memory=512, image=None):
        super().__init__(logger, name, image="jiangjqian/edgegate:gatewaybase", privileged=True)
        self._type = "GW"
        self._linkid = 1
        pass

    def nextlinkid(self):
        lid = self._linkid
        self._linkid += 1
        return lid

    def adddocker(self, docker):
        for i in range(0, 20):
            if self.ready():
                break
            time.sleep(2)
        iname = f'e{self.id()}-{self.nextlinkid()}'
        pname = "p" + iname
        sp = subprocess.run(["ip", "link", "add", iname, "type", "veth", "peer", "name", pname])
        self.addintf(iname)
        docker.addintf(pname)
        sp = subprocess.run(["ip", "netns", "exec", self.name(), "ip", "link", "set", iname, "master", "br0"])
        if sp.returncode != 0:
            self._logger.warning("Can not add to br0")
        subprocess.run(["ip", "netns", "exec", self.name(), "ip", "link", "set", iname, "up"])

    def enablegw(self, ip):
        self.addenv(f'GWIP={ip}')

    def ready(self):
        ip = self.ip()
        if ip is None:
            return False

        opts = {"entry": "httpself", "cmd": "readycheck"}
        try:
            resp = utils.http_post(ip, 11112, "/", opts)
            if resp.getcode() == 200 and resp.read().decode("utf-8") == "OK":
                return True
        except Exception as e:
            self._logger.info(f'docker is not ready, exceptin {str(e)}')
            return False
        self._logger.info(f'docker is not ready, {resp.getcode()}, {resp.read().decode("utf-8")}')
        return False

if __name__ == "__main__":
    import logging
    import sys
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    logger.debug("%s", str(sys.argv))

    gw = GW(logger, "gw-test")
    print(gw.name())
    print(gw.type())
    print(gw.mem())
    print(gw.image())
    gw.enablegw("10.10.101.1/24")
    print(gw.envs())
    gw.addvolumn("/home/richard/PycharmProjects/sd-wan-edgev2:/root/sd-wan-edgev2")
    gw.start()
    #gw.addintf("enp1s0")
    docker = Docker(logger, "ubuntu-test", image="jiangjqian/edgegate:ubuntu-net", privileged=True)
    docker.start()

    gw.adddocker(docker)

    try:
        while True:
            time.sleep(1)
            print("sleep")
    except KeyboardInterrupt:
        docker.remove()
        gw.remove()
        pass

    print("end")

