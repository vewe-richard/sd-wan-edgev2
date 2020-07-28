class BasevDev():
    def __init__(self, logger, name):
        self._type = "BasevDev"
        self._name = name
        self._nets = []
        self._mem = 512
        self._image = None
        self._id = -1
        self._logger = logger

    def type(self):
        return self._type

    def name(self):
        return self._name

    def nets(self):
        return self._nets

    def mem(self):
        return self._mem

    def image(self):
        return self._image

    def id(self):
        return self._id

    def start(self):
        self._logger.info("TODO")

    def stop(self):
        self._logger.info("TODO")

    def remove(self):
        self._logger.info("TODO")

    def addnet(self, net):
        self._nets.append(net)


class ExceptionNotExist(Exception):
    pass

