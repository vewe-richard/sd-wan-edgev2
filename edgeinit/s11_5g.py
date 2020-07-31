from edgeinit.base import MainBase, HttpBase
import subprocess
from pathlib import Path
import json
import multiprocessing
import time
import serial
from edgeutils import utils

class Fail5GException(Exception):
    pass

class S5GProcess(multiprocessing.Process):
    def __init__(self, logger, mgrdict, **kwargs):
        super().__init__(**kwargs)
        self._logger = logger
        self._mgrdict = mgrdict
        self._mgrdict["status"] = "INIT"
        self._mgrdict["log"] = ""
        pass

    def run(self):
        while True:
            h5g = serial.Serial("/dev/ttyUSB2", 115200)
            try:
                self._logger.info(self._mgrdict["status"])

                log = self._mgrdict["log"]
                idx = log.rfind("#")
                if idx >= 0:
                    self._mgrdict["log"] = log[idx:] + "#"
                else:
                    self._mgrdict["log"] += "#"

                if self._mgrdict["status"] == "INIT":
                    self.connecting(h5g)
                    self._mgrdict["status"] = "CONNECTED"
                else:
                    self.monitoring(h5g)
            except Fail5GException as e:
                self._logger.info(str(e))
                self.status5g(h5g)
            finally:
                self._logger.info("at command log:")
                self._logger.info(self._mgrdict["log"])
                h5g.close()
                time.sleep(2)

        return

    def connecting(self, h5g):
        h5g.write(b'AT$QCRMCALL=1,1\r')
        time.sleep(1)
        out = self.read(h5g)

        h5g.write(b'AT+CREG?\r')
        out += self.read(h5g)

        h5g.write(b'AT\r')
        out += self.read(h5g)

        ostr = out.decode()

        self._mgrdict["log"] += ostr
        self._logger.info(ostr)

        #check dhcclient return
        if self.checkConnected(ostr):
            self._logger.info("5G connected")
            subprocess.run(["systemctl", "restart", "systemd-networkd"])
            return
        self._logger.info("5G not connected")
        raise Fail5GException("Connecting failed")

    def checkConnected(self, resp):
        i = resp.find("+CREG:")
        if i < 0:
            self._logger.info("Can not find creg in response")
            return False

        lstr = resp[(i + len("+CREG:")):]
        v = lstr.split("\r")
        u = v[0].split(",")
        if len(u) < 2:
            self._logger.info("Wrong CREG Response")
            return False

        stat = int(u[1].strip())

        self._logger.info("stat: " + str(stat))
        if stat == 1:
            return True
        return False

    def monitoring(self, h5g):
        h5g.write(b'AT+CREG?\r')
        out = self.read(h5g)

        h5g.write(b'AT\r')
        out += self.read(h5g)

        ostr = out.decode()

        self._mgrdict["log"] += ostr

        if self.checkConnected(ostr):
            self._logger.info("5G keeping connected")
        else:
            self._logger.info("5G lost connected")
            self._mgrdict["status"] = "INIT"
        pass

    def read(self, h5g):
        out = h5g.read()
        time.sleep(0.1) #Sleep 1 (or inWaiting() may return incorrect value)
        while h5g.inWaiting() > 0:
            out += h5g.read()
        return out

    def status5g(self, h5g):
        h5g.write(b'AT\r')
        out = self.read(h5g)
        h5g.write(b'AT+CPIN?\r')
        out += self.read(h5g)
        h5g.write(b'AT+CSQ\r')
        out += self.read(h5g)
        self._mgrdict["log"] += out.decode()

class Http(HttpBase):
    def __init__(self, logger, cfgfile=None):
        super().__init__(logger)
        if cfgfile is None:
            self._configpath = self.configpath() + "/5g.json"
        else:
            self._configpath = cfgfile
        try:
            with open(self._configpath) as json_file:
                self._data = json.load(json_file)
        except:
            self._data = dict()

        self._mgrdict = multiprocessing.Manager().dict()
        self._mgrdict["status"] = "Not Enabled"

    def start(self):
        try:
            if not self._data["enable"]:
                raise Exception("5g not enable")
        except:
            self._logger.info(self._configpath)
            self._logger.info("5g is not enabled, skip")
            return
        dev = Path("/dev/ttyUSB2")
        if not dev.is_char_device():
            self._logger.warn("/dev/ttyUSB2 is not exist")
            return
        self._logger.info(__file__ + "   http start()")
        p = S5GProcess(self._logger, self._mgrdict)
        p.start()
        pass

    def status(self):
        try:
            log = self._mgrdict["log"]
        except:
            log = ""

        try:
            return self._mgrdict["status"] + "\n" + log
        except Exception as e:
            return "Exception: " + str(e)

    def name(self):
        return "5G"

    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))
        pass

if __name__ == "__main__":
    import logging
    import sys
    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")
    logger.debug("%s", str(sys.argv))

    h = Http(logger, cfgfile="/home/richard/PycharmProjects/sd-wan-edgev2/configs/5g.json")
    h.start()
    while True:
        logger.info("main loop ")
        time.sleep(2)
    pass