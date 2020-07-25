import subprocess
from pathlib import Path

class HttpBase:
    def __init__(self, logger):
        self._logger = logger
        pass

    def start(self):
        pass

    def post(self, msg):
        pass

    def status(self):
        return ""

    def name(self):
        return ""

    def term(self):
        pass

    def join(self, timeout=None):
        pass

    def configpath(self):
        sp = subprocess.run(["ip", "netns", "identify"], stdout=subprocess.PIPE)
        for l in sp.stdout.splitlines():
            ns = l.decode().strip()
            if len(ns) > 0:
                return f'{Path.home()}/.sdwan/edgepoll/{ns}/'
        else:
            return f'{Path.home()}/.sdwan/edgepoll/'


class MainBase:
    def __init__(self, logger):
        self._logger = logger
        pass

    def start(self):
        pass

    def post(self, msg):
        pass

    def term(self):
        pass

    def join(self, timeout=None):
        pass

    def configpath(self):
        sp = subprocess.run(["ip", "netns", "identify"], stdout=subprocess.PIPE)
        for l in sp.stdout.splitlines():
            ns = l.decode().strip()
            if len(ns) > 0:
                return f'{Path.home()}/.sdwan/edgepoll/{ns}/'
        else:
            return f'{Path.home()}/.sdwan/edgepoll/'