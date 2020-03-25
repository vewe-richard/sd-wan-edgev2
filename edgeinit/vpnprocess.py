#https://stackoverflow.com/questions/20476555/non-blocking-connect

import multiprocessing
import traceback
import signal
import subprocess
import time
import os

class Kill2Exception(Exception):
    pass

def signal_kill2_handler(signum, frame):
    raise Kill2Exception("Kill2")

class VpnProcess(multiprocessing.Process):
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

        #create default tap
        self.shell(["ip", "tuntap", "add", "mode", "tap", self.tuntapname()])
        rlt = self.shell(["ip", "link", "set", self.tuntapname(), "up"])
        if rlt != 0:
            self._mgrdict["status"] = "CAN NOT CREATE TAP"
            raise Exception("VpnProcess: can not create tap")
        pass
    def run2(self):
        while True:
            time.sleep(1)


    def run(self):
        self._mgrdict["pid"] = self.pid
        signal.signal(signal.SIGUSR1, signal_kill2_handler)

        try:
            self.run2()
        except KeyboardInterrupt:
            self._logger.warning("VpnProcess Loop exception, KeyboardInterrupt")
        except Kill2Exception:
            self._logger.warning("VpnProcess Kill2Exception")
            self._mgrdict["status"] = "Exit"
        finally:
            self.shell(["ip", "tuntap", "del", "mode", "tap", "name", self.tuntapname()])
        self._logger.warning("VpnProcess Exit")

    def shell(self, args, ignoreerror = True):
        self._logger.info("VpnProcess run %s", str(args))
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

    def tuntapname(self):
        prefix = "sdtap-" + self._subnet3rd + "." + self._subnet4th
        return prefix

