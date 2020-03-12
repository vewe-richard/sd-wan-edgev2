import _thread
import socket

from edgeinit.base import HttpBase
from pathlib import Path
import json
import traceback

def serverthread(threadName, port):
    print(threadName, port)

    # create a socket object
    serversocket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM)
    # serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind(("0.0.0.0", port))

    while True:
        serversocket.listen(5)
        # establish a connection
        clientsocket, addr = serversocket.accept()
        print(clientsocket, addr)

    pass

class Http(HttpBase):
    def __init__(self, logger):
        super().__init__(logger)
        self._datapath = str(Path.home()) + "/.sdwan/edgepoll/"
        self._configpath = self._datapath + "stun.json"
        self._data = []

    def start(self):
        try:
            with open(self._configpath) as json_file:
                self._data = json.load(json_file)
        except FileNotFoundError:
            Path(self._datapath).mkdir(parents=True, exist_ok=True)

            with open(self._configpath, 'w') as json_file:
                json.dump(self._data, json_file)
        except:
            self._logger.warn(traceback.format_exc())
        for node in self._data:
            self._logger.info("stun start node: %s", str(node))
            self.startnode(node)
        pass

    def startnode(self, node):
        _thread.start_new_thread(serverthread, ("serverthread", int(node["port"]),))
        return "TODO"

    def addclient(self, msg):
        return "TODO"

    #{"entry": "http", "module": "stun", "cmd": "add", "node": "server", "port": "1299",
    #            "tunortap": "tap", "tunnelip": "192.168.23.19", "tunneltype": "ipsec"}
    def addserver(self, msg):
        tunnelip = msg["tunnelip"]
        port = msg["port"]
        tunneltype = msg["tunneltype"]
        tunortap = msg["tunortap"]

        #check if server is already there
        for n in self._data:
            if n["node"] == "server":
                if n["tunnelip"] == tunnelip:
                    if n["port"] == port and n["tunneltype"] == tunneltype and n["tunortap"] == tunortap:
                        self._logger.info("this server is already there")
                        return "OK"
                if n["port"] == port:
                    return "NOK, port conflict with previous server"
                ip = n["tunnelip"]
            elif n["node"] == "client":
                ip = n["ptunnelip"]

            #if same subnet, then return error
            if self.samesubnet(ip, tunnelip):
                return "NOK, subnet conlict"

        node = dict()
        node["node"] = "server"
        node["port"] = port
        node["tunnelip"] = tunnelip
        node["tunortap"] = tunortap
        node["tunneltype"] = tunneltype

        rlt = self.startnode(node)
        if rlt != "OK":
            return rlt

        #add to config file
        self.appendnode(node)
        return "OK"

    def addnode(self, node, msg):
        if node == "client":
            result = self.addclient(msg)
        elif node == "server":
            result = self.addserver(msg)
        else:
            result = "Unknown node: " + node
        return result

    def post(self, msg):
        self._logger.debug("stun post handler: %s", str(msg))
        result = "NOK"
        try:
            cmd = msg["cmd"]
            if cmd == "add":
                node = msg["node"]
                result = self.addnode(node, msg)
            elif msg["cmd"] == "delete":
                result = "TODO"
            else:
                result = "Unknown command: " + cmd
        except:
            self._logger.warn(traceback.format_exc())
            result = traceback.format_exc()

        return result

    def appendnode(self, node):
        self._data.append(node)
        with open(self._configpath, 'w') as json_file:
            json.dump(self._data, json_file)

    def samesubnet(self, ip1, ip2):
        ip1s = ip1.split(".")
        ip2s = ip2.split(".")
        if ip1s[0] == ip1s[0] and ip1s[1] == ip2s[1] and ip1s[2] == ip2s[2]:
            return True
        else:
            return False







