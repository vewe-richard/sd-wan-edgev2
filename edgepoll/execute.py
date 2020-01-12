from edgepoll import edgeconfig
import traceback

class Execute():
    def __init__(self, logger):
        self._logger = logger
        pass

    def run(self, xmlstr):
        self._logger.debug(xmlstr)
        pass

