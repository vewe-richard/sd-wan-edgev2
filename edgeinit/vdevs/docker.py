# Usage:
# export PYTHONPATH=$PWD && python3 edgeinit/vdevs/vm.py
# then, we can locate the guest from "ssh -p 10008 127.0.0.1"
# to stop this, if control +c does not work, use kill -s SIGINT "pid of vm.py"
from edgeinit.vdevs.basevdev import BasevDev
import subprocess
import time
import pathlib
import os
import traceback


class Docker(BasevDev):
    def __init__(self, logger, name, memory=512, image=None, privileged=False):
        super().__init__(logger, name)
        self._type = "Docker"
        self._mem = memory
        self._image = image
        self._privileged = privileged
        self._envs = []
        self._volumns = []
        self._ip = None
        pass

    def exist(self):
        sp = subprocess.run(["docker", "inspect", self.name()], stdout=subprocess.DEVNULL)
        if sp.returncode == 0:
            return True
        return False

    def start(self):
        self.netns_remove()
        if self.exist():
            self._logger.warning(f'Docker {self.name()} is already exist')
            return
        self._start()
        pass

    def _start(self):
        cmd = []
        cmd.extend(["docker", "run", "--rm", "--name", self.name()])
        if self._privileged:
            cmd.append("--privileged")
        for env in self._envs:
            cmd.extend(["--env", env])
        for v in self._volumns:
            cmd.extend(["-v", v])
        cmd.append(self._image)
        self._logger.info(cmd)
        sp = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)

        self._proc = sp
        self._id = sp.pid

    def addenv(self, envstr):
        self._envs.append(envstr)

    def addvolumn(self, volumn):
        self._volumns.append(volumn)

    def envs(self):
        return self._envs

    def stop(self):
        pass

    def remove(self):
        self.netns_remove()
        sp = subprocess.Popen(["docker", "stop", self.name()])
        pass

    def addintf(self, intf):
        if not self.netns_exist():
            self.netns_add()
        if not self.netns_exist():
            return
        self._logger.info(f"add intf {intf}")
        sp = subprocess.run(["ip", "link", "set", intf, "up"])
        sp = subprocess.run(["ip", "link", "set", intf, "netns", self.name()])

    def netns_exist(self):
        if os.path.islink(f'/var/run/netns/{self.name()}'):
            return True
        return False

    def netns_remove(self):
        try:
            os.unlink(f'/var/run/netns/{self.name()}')
        except:
            pass

    def netns_add(self):
        # add this docker to network namespace
        pathlib.Path("/var/run/netns").mkdir(parents=True, exist_ok=True)
        for i in range(0, 30):
            sp = subprocess.run(["docker", "inspect", "--format", "'{{.State.Pid}}'", self.name()], stdout=subprocess.PIPE)
            pidstr = sp.stdout.decode().strip().strip("'")
            try:
                pid = int(pidstr)
                os.symlink(f'/proc/{pid}/ns/net', f'/var/run/netns/{self.name()}')
                break
            except Exception as e:
                #self._logger.warning(traceback.format_exc())
                self._logger.warning(f"Can not create network namespace for {self.name()}, waiting ...")
                time.sleep(2)
                continue
        pass

    def ip(self):
        if not self._ip is None:
            return self._ip
        sp = subprocess.run(["docker", "inspect", "--format", "'{{.NetworkSettings.IPAddress}}'", self.name()], stdout=subprocess.PIPE)
        if sp.returncode != 0:
            return
        self._ip = sp.stdout.decode().strip().strip("'")

if __name__ == "__main__":
    import logging
    import sys
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    logger.debug("%s", str(sys.argv))

    docker = Docker(logger, "ubuntu-test", image="jiangjqian/edgegate:common")
    print(docker.name())
    print(docker.type())
    print(docker.mem())
    print(docker.image())
    print("exist", docker.exist())
    docker.start()

    try:
        while True:
            time.sleep(1)
            print("sleep")
    except KeyboardInterrupt:
        docker.remove()
        pass

    print("end")

