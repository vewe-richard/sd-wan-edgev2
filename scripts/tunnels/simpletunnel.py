# !/usr/bin/python3
# Description: entry of simpletunnel service
# Note: three ways on calling this script
# 1. As Service
#   ExecStart=/usr/bin/python3 {GITROOT}/scripts/tunnels/simpletunnel.py [-s|-d|-c serverip] [-p port] [-l locaip] [-h|--help]
#   Environment=PYTHONPATH="{GITROOT}"
# 2. On shell
#   sudo su
#   export PYTHONPATH="$GITROOT" &&  python3 scripts/tunnels/simpletunnel.py [-s|-d|-c serverip] [-p port] [-l locaip] [-h|--help]
# 3. On Pycharm
#   add Environment PYTHONPATH
#   -s -p 5555
# test in shell
# sudo su
# export PYTHONPATH="$PWD" &&  python3 scripts/tunnels/simpletunnel.py -s -p 5555
# export PYTHONPATH="$PWD" &&  python3 scripts/tunnels/simpletunnel.py -s -p 5556
# export PYTHONPATH="$PWD" &&  python3 scripts/tunnels/simpletunnel.py -c 127.0.0.1 -p 5555 -l 10.139.37.2
# export PYTHONPATH="$PWD" &&  python3 scripts/tunnels/simpletunnel.py -c 127.0.0.1 -p 5556 -l 10.139.37.3
# By vewe-richard@github, 2020/01/10
#
#

import os
from edgeutils import utils
import sys
from getopt import getopt
import subprocess
import time

class SimpleTunnel():
    def __init__(self):
        self._serverbr = "br-stunnel"
        self._tapname = None
        self._brip = "10.139.37.1/24"
        pass

    def tapname(self):
        return self._tapname

    def selecttap(self):
        for i in range(20, 1000):
            tap = "tap" + str(i)
            sp = subprocess.run(["ip", "link", "show", tap])
            if sp.returncode == 0:
                continue
            self._tapname = tap
            return

    def usage(self):
        print("python3 scripts/tunnels/simpletunnel.py [-s|-d|-c serverip] [-p port] [-l locaip] [-h|--help]")
        pass

    def clear(self):
        sp = subprocess.run(["ps", "-C", "simpletun", "-f"], stdout=subprocess.PIPE)
        running = sp.stdout.decode()
        sp = subprocess.run(["brctl", "show", "br-stunnel"], stdout=subprocess.PIPE)
        for l in sp.stdout.splitlines():
            items = l.decode().split()
            if len(items) < 1:
                continue
            last = items[-1]
            if len(last) < 4:
                continue
            if "tap" not in last[0:3]:
                continue
            if last in running:
                continue
            subprocess.run(["brctl", "delif", self._serverbr, items[-1]])
            subprocess.run(["ip", "tuntap", "del", "mode", "tap", last])
        sp = subprocess.run(["ip", "link", "show"], stdout=subprocess.PIPE)
        for l in sp.stdout.splitlines():
            items = l.decode().split(":")
            if len(items) < 2:
                continue
            nic = items[1].strip()
            if len(nic) < 5:
                continue
            if "tap" not in nic[0:3]:
                continue
            subprocess.run(["ip", "tuntap", "del", "mode", "tap", nic])
        pass

    def server(self, port):
        self.clear()
        sp = subprocess.run(["ip", "address", "show", self._serverbr])
        if sp.returncode != 0:
            print("Create bridge", self._serverbr)
            subprocess.run(["brctl", "addbr", self._serverbr])
            subprocess.run(["ip", "link", "set", self._serverbr, "up"])
            subprocess.run(["ip", "addr", "add", self._brip, "dev", self._serverbr])
            pass

        #select a tap device
        self.selecttap()
        print("")
        print("Select tapname:", self.tapname())
        subprocess.run(["ip", "tuntap", "add", "mode", "tap", self.tapname()])
        subprocess.run(["ip", "link", "set", self.tapname(), "up"])
        sp = subprocess.run(["brctl", "addif", self._serverbr, self.tapname()])
        if sp.returncode != 0:
            subprocess.run(["ip", "tuntap", "del", "mode", "tap", self.tapname()])
            print("Can not add", self.tapname(), "to", self._serverbr)
            sys.exit(-1)

        while True:
            subprocess.run(["./scripts/tunnels/simpletun", "-a", "-i", self.tapname(), "-s", "-p", str(port), "-d"])
            print("restart simpletun as it quit.")
            time.sleep(10)
        pass

    def client(self, ip, port, localip):
        self.clear()
        # if correct localip
        if localip == self._brip:
            print("Wrong localip, same as bridge ip")
            sys.exit(-1)
        litems = localip.split(".")
        bitems = self._brip.split(".")
        if litems[0] != bitems[0] or litems[1] != bitems[1] or litems[2] != bitems[2]:
            print("Wrong localip", localip)
            sys.exit(-1)

        self.selecttap()
        print("")
        print("Select tapname:", self.tapname())
        subprocess.run(["ip", "tuntap", "add", "mode", "tap", self.tapname()])
        subprocess.run(["ip", "addr", "add", localip + "/24", "dev", self.tapname()])
        subprocess.run(["ip", "link", "set", self.tapname(), "up"])
        while True:
            subprocess.run(["./scripts/tunnels/simpletun", "-a", "-i", self.tapname(), "-c", ip, "-p", str(port), "-d"])
            print("restart simpletun as it quit.")
            time.sleep(10)
        pass

    def run(self, argv):
        opts, args = getopt(argv, "hsdc:p:l:", ["help"])
        port = None
        localip = None
        for o, v in opts:
            if o in "-h" or o in "--help":
                self.usage()
                sys.exit(-1)
            elif o in "-p":
                port = int(v)
                pass
            elif o in "-l":
                localip = v
                pass

        if port == None:
            self.usage()
            sys.exit(-1)

        for o, v in opts:
            if o in "-s":
                print("simpletunnel server, port: ", port)
                self.server(port)
                pass
            elif o in '-c':
                ip = v
                if localip == None:
                    self.usage()
                    sys.exit(-1)
                self.client(ip, port, localip)
                pass
            elif o in "-d":
                pass


if __name__ == "__main__":
    # to be sure current working directory is root of git project
    print("Checking working directory ...")
    cwd = os.environ["PYTHONPATH"]
    assert utils.runningUnderGitProjectRootDirectory(cwd)
    os.chdir(cwd)

    #TODO, We should have self logging system, temporlary use system log
    st = SimpleTunnel()
    st.run(sys.argv[1:])