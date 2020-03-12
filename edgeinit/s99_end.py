from edgeinit.base import MainBase, HttpBase


class Http(HttpBase):
    def start(self):
        self._logger.info(__file__ + "  http start()")
        pass

    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))
        pass

class Main(MainBase):
    def start(self):
        self._logger.info(__file__ + "   main start()")
        pass

    def post(self, msg):
        self._logger.info(__file__ + " msg " + str(msg))
        pass