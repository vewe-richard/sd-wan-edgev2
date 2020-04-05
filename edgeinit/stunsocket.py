import socket

class stunsocket(socket.socket):
    def init2(self):
        self._pair = None
        self._data = bytearray(1600)
        self._left = 0

    def left(self):
        return self._left

    def setpair(self, pair):
        self._pair = pair

    def getpair(self):
        return self._pair

    def beginread(self, l):
        self._toread = l
        self._left = l
        self._view = memoryview(self._data)

    def readsize(self):
        return self._toread

    def readleft(self):
        try:
            cnt = self.recv_into(self._view, self._left)
        except BlockingIOError:
            #self._logger.debug("blocking io error, to read %d, left %d", self._toread, self._left)
            self._logger.info("blocking io error,", self._toread, self._left)
            return False
        self._left -= cnt
        self._view = self._view[cnt:]
        if self._left > 0:
            return False
        return True

    def data(self):
        return self._data[0:self._toread]

if __name__ == "__main__":
    ss = stunsocket(socket.AF_INET, socket.SOCK_STREAM)
    ss.setblocking(0)
    ss.connect_ex(("127.0.0.1", 10000))

    ss.init2()
    ss.beginread(10)
    while True:
        if ss.readleft():
            break
    print(ss.data())