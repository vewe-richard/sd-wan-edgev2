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