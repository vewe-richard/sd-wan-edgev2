from edgeinit.base import MainBase, HttpBase
import subprocess
from pathlib import Path
import json
import multiprocessing
import time
import serial

class S5GProcess(multiprocessing.Process):
    def __init__(self, logger, mgrdict, **kwargs):
        super().__init__(**kwargs)
        self._logger = logger
        self._mgrdict = mgrdict
        self._mgrdict["status"] = "INIT"
        pass

    def run(self):
        phone = serial.Serial("/dev/ttyUSB2", 115200, timeout=5)
        phone.write(b'AT\r')
        time.sleep(0.5)
        data = phone.readline()
        self._logger.info("get at command response: ", data)
        phone.close()
        while True:
            self._logger.info(self._mgrdict["status"])
            time.sleep(1)
        return

class Http(HttpBase):
    def __init__(self, logger, cfgfile=None):
        super().__init__(logger)
        if cfgfile is None:
            sp = subprocess.run(["ip", "netns", "identify"], stdout=subprocess.PIPE)
            for l in sp.stdout.splitlines():
                ns = l.decode().strip()
                if len(ns) > 0:
                    self._configpath = str(Path.home()) + "/.sdwan/edgepoll/" + ns + "/5g.json"
                    break
            else:
                self._configpath = str(Path.home()) + "/.sdwan/edgepoll/5g.json"
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
                raise Exception("5g not enable")
        except:
            self._logger.warning(self._configpath)
            self._logger.warning("5g is not enabled, skip")
            return

        self._logger.info(__file__ + "   http start()")
        mgrdict = multiprocessing.Manager().dict()
        p = S5GProcess(self._logger, mgrdict)
        p.start()
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
    while True:
        time.sleep(2)
    pass