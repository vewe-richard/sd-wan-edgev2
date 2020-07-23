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
import traceback

class Http(HttpBase):
    def __init__(self, logger, cfgfile=None):
        super().__init__(logger)
        if cfgfile is None:
            self._configpath = self.configpath() + "/cloud.json"
        else:
            self._configpath = cfgfile
        try:
            with open(self._configpath) as json_file:
                self._data = json.load(json_file)
        except Exception as e:
            self._logger.warning(traceback.format_exc())
            self._data = dict()

    def start(self):
        self._logger.info(str(self._data))
        pass

    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))

    def term(self):
        pass

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

    h = Http(logger)
    h.start()
    try:
        raise Exception("Break")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Break")
    except:
        pass
    pass