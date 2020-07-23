from edgeutils import utils
import os
import time


# test new simpletun service version
if __name__ == "__main__":
    cwd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    assert utils.runningUnderGitProjectRootDirectory(cwd)
    os.chdir(cwd)

    #opts = {"entry": "mainself", "cmd": "pollnotify"}
    #opts = {"entry": "http", "module": "stun", "cmd": "add", "node": "client", "server": "127.0.0.1", "port": "1299",
    #        "tunortap": "tap", "ptunnelip": "192.168.23.19", "tunneltype": "ipsec"}
    #opts = {"entry": "http", "module": "stun", "cmd": "add", "node": "server", "port": "55556",
    #        "tunortap": "tap", "tunnelip": "192.168.2.29", "tunneltype": "ipsec"}
    #opts = {"entry": "http", "module": "stun", "cmd": "delete", "node": "server", "port": "55556",
    #        "tunortap": "tap", "tunnelip": "10.139.47.1", "tunneltype": "ipsec", "remoteip": "10.129.101.99"}

    #opts = {"entry": "http", "module": "network", "cmd": "bridgeadd", "brname": "br0", "intf": "enp1s0"}
    #opts = {"entry": "http", "module": "network", "cmd": "newgateway", "ip": "10.100.20.1/24"}
    opts = {"entry": "httpself", "cmd": "readycheck"}

    #resp = utils.http_post("127.0.0.1", 11112, "/", opts)
    resp = utils.http_post("172.17.0.6", 11112, "/", opts)
    print(__file__, resp.getcode(), resp.read().decode("utf-8"))
    print("end")
