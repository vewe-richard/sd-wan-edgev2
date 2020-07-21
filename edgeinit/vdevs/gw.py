# Usage:
# export PYTHONPATH=$PWD && python3 edgeinit/vdevs/vm.py
# then, we can locate the guest from "ssh -p 10008 127.0.0.1"
# to stop this, if control +c does not work, use kill -s SIGINT "pid of vm.py"
from edgeinit.vdevs.docker import Docker
import subprocess
import time

class GW(Docker):
    def __init__(self, logger, name, memory=512, image=None):
        super().__init__(logger, name, image="jiangjqian/edgegate:common", privileged=True)
        self._type = "GW"
        pass

    def adddocker(self, docker):
        sp = subprocess.run(["ip", "link", "add", "veth100", "type", "veth", "peer", "name", "pveth100"])
        self.addintf("veth100")
        docker.addintf("pveth100")

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
    gw.start()

    #gw.addintf("enp1s0")
    docker = Docker(logger, "ubuntu-test", image="jiangjqian/edgegate:common", privileged=True)
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

