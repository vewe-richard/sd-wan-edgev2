# Usage:
# export PYTHONPATH=$PWD && python3 edgeinit/vdevs/vm.py
# then, we can locate the guest from "ssh -p 10008 127.0.0.1"
# to stop this, if control +c does not work, use kill -s SIGINT "pid of vm.py"
from edgeinit.vdevs.basevdev import BasevDev
import socket
import random
import subprocess
import time
import os
import signal


class VM(BasevDev):
    def __init__(self, logger, name, memory=512, image=None, fwdport=-1):
        super().__init__(logger, name)
        self._type = "VM"
        self._mem = memory
        self._image = image
        if fwdport == -1:
            self._fwdport = self.getfreeport()
        else:
            self._fwdport = fwdport
        self._proc = None
        self._net2tap = dict()
        pass

    def fwdport(self):
        return self._fwdport

    def getfreeport(self):
        while True:
            port = random.randint(20000, 60000)
            if self.is_port_in_use(port):
                continue
            return port

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def exist(self):
        sp = subprocess.run(["ps", "-f", "-C", "qemu-system-x86_64"], stdout=subprocess.PIPE)
        lines = sp.stdout.decode().splitlines()
        for line in lines:
            if not "-name" in line:
                continue
            its = line.split("-name")
            name = its[1].split()[0].strip()
            try:
                id = int(its[0].split()[1])
            except:
                id = -1

            if name == self.name():
                return True, id
        return False, -1

    def start(self):
        exist, self._id = self.exist()
        if exist:
            self._logger.warning("VM {} already exist".format(self.name()))
            return
        self._start()
        pass

    def stop(self):
        pass

    def remove(self):
        if not self._proc is None:
            self._proc.terminate()
            return
        if self._id == -1:
            self._logger.warning("can not remove as vm id is not exist")
            return
        os.kill(self._id, signal.SIGTERM)
        pass

    def forwardport_params(self):
        netdev = f'user,id=net_{self.name()},hostfwd=tcp::{self.fwdport()}-:22'
        device = f'e1000,netdev=net_{self.name()}'
        return ["-netdev", netdev, "-device", device]

    def _start(self):
        cmd = []
        cmd.extend(["qemu-system-x86_64", "-enable-kvm", "-nographic"])
        cmd.extend(["-m", str(self._mem)])
        cmd.extend(self.forwardport_params())
        cmd.extend(["-name", self.name()])
        cmd.append(self._image)
        for net in self.nets():
            rand = random.randint(100, 999)
            tapname = f't{self.name()[0:6]}-{net[0:1]}{rand}'
            id = f'n{net[0:1]}{rand}'
            self._net2tap[net] = tapname
            extcmd = ["-netdev", f'tap,id={id},ifname={tapname}', "-device", f'e1000,netdev={id}']
            self._logger.info(extcmd)
            cmd.extend(extcmd)

        sp = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self._proc = sp
        self._id = sp.pid
        pass

    def declarenet(self, nets):
        for net in nets:
            self.addnet(net)

    def nettotap(self, netname):
        try:
            return self._net2tap[netname]
        except:
            return None


if __name__ == "__main__":
    import logging
    import sys
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    logger.debug("%s", str(sys.argv))

    vm = VM(logger, "ubuntu", image="/var/lib/libvirt/images/ubuntu16.04-20190514-install-nested-kvm.qcow2", fwdport=10008)
    print(vm.name())
    print(vm.type())
    print(vm.mem())
    print(vm.image())
    print("port", vm.fwdport())
    print("exist", vm.exist())
    vm.declarenet(["vSW", "Good"])
    vm.start()

    try:
        while True:
            time.sleep(1)
            print("sleep")
    except KeyboardInterrupt:
        vm.remove()
        pass

    print("end")

