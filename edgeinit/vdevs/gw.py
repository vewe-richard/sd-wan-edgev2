# Usage:
# export PYTHONPATH=$PWD && python3 edgeinit/vdevs/vm.py
# then, we can locate the guest from "ssh -p 10008 127.0.0.1"
# to stop this, if control +c does not work, use kill -s SIGINT "pid of vm.py"
# History:
# 1. Can not work with kernel vxlan
# Environment: two dockers in two different host, let's them link using kernel vxlan,
# and through map to host, however, this only work on ping packet.
# After,
# echo 0 > /proc/sys/net/netfilter/nf_conntrack_checksum
# it makes more udp packets pass through
# it's suspected that the udp checksum error cause these issue
# 2. Can not work with socketplane/openvswitch
from edgeinit.vdevs.docker import Docker
import subprocess
import time
from edgeutils import utils
import random
import traceback

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
        for i in range(0, 40):
            if self.ready(i):
                self._logger.info("Gateway get ready!")
                break
            time.sleep(2)
        rd = random.randint(100,999)
        iname = f'e{docker.name()[0:6]}-{rd}'
        pname = f'e{self.name()[0:6]}-{rd}'
        sp = subprocess.run(["ip", "link", "add", iname, "type", "veth", "peer", "name", pname])
        self.addintf(iname)
        docker.addintf(pname)
        sp = subprocess.run(["ip", "netns", "exec", self.name(), "ip", "link", "set", iname, "master", "br0"])
        if sp.returncode != 0:
            self._logger.warning("Can not add to br0")
        subprocess.run(["ip", "netns", "exec", self.name(), "ip", "link", "set", iname, "up"])
        return (iname, pname)

    def bridge2(self, peer_gw):
        #need wait peer_gw ready
        for i in range(0, 40):
            if peer_gw.ready(i):
                self._logger.info("Gateway get ready")
                break
            time.sleep(2)

        iname, pname = self.adddocker(peer_gw)
        sp = subprocess.run(["ip", "netns", "exec", peer_gw.name(), "ip", "link", "set", pname, "master", "br0"])
        if sp.returncode != 0:
            self._logger.warning("Can not add to br0")
        subprocess.run(["ip", "netns", "exec", peer_gw.name(), "ip", "link", "set", pname, "up"])
        pass

    def enablegw(self, ip):
        self.addenv(f'GWIP={ip}')

    def ready(self, count):
        ip = self.ip()
        if ip is None:
            return False

        opts = {"entry": "httpself", "cmd": "readycheck"}
        try:
            resp = utils.http_post(ip, 11112, "/", opts)
            if resp.getcode() == 200 and resp.read().decode("utf-8") == "OK":
                return True
        except Exception as e:
            self._logger.info(f'docker is not ready({ip}:{count}), exceptin {str(e)}')
            #self._logger.info(traceback.format_exc())
            return False
        self._logger.info(f'docker is not ready({ip}:{count}), {resp.getcode()}, {resp.read().decode("utf-8")}')
        return False

    def vxlan(self, cfg):
        env = "VXLAN="
        for vxlan in cfg:
            try:
                remote = vxlan["remote"]
                dstport = vxlan["dstport"]
            except Exception as e:
                self._logger.warning(f'Can not enable vxlan for exception {e}')
                continue
            try:
                vni = vxlan["vni"]
            except:
                vni = 42

            try:
                map = vxlan["map"]
                self.portsmap(f'{map}:{dstport}/udp')
                env += f'{remote}:{dstport}:{vni}:{map},'
            except:
                env += f'{remote}:{dstport}:{vni},'
                pass
        self.addenv(env[0:-1])

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
    time.sleep(2)
    print("end")

