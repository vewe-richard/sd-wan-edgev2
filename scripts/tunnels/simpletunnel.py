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
# 4. test in shell
#
# sudo su
# python3 sd-wan-env/ns4tunnels.py
#
# export PYTHONPATH="$PWD" && ip netns exec main python3 scripts/tunnels/simpletunnel.py -s -p 5555 -l 10.139.27.1
# export PYTHONPATH="$PWD" && ip netns exec n101 python3 scripts/tunnels/simpletunnel.py -c 10.129.101.100 -p 5555 -l 10.139.27.3
# ip netns exec n101 ping 10.139.27.1
#
# export PYTHONPATH="$PWD" && ip netns exec main python3 scripts/tunnels/simpletunnel.py -s -p 55556 -l 10.139.47.1
# export PYTHONPATH="$PWD" && ip netns exec n101 python3 scripts/tunnels/simpletunnel.py -c 10.129.101.100 -p 55556 -l 10.139.47.3
# ip netns exec n101 ping 10.139.47.1
#
# export PYTHONPATH="$PWD" && ip netns exec main python3 scripts/tunnels/simpletunnel.py -s -p 33333 -l 10.139.27.1
# export PYTHONPATH="$PWD" && ip netns exec n102 python3 scripts/tunnels/simpletunnel.py -c 10.129.102.100 -p 33333 -l 10.139.27.8
# ip netns exec n102 ping 10.139.27.3

# By vewe-richard@github, 2020/01/10
#
#

import os
from random import randint

from edgeutils import utils
import sys
from getopt import getopt
import subprocess
import time

class SimpleTunnel():
    def __init__(self):
        self._tapname = None
        pass

    def tapname(self):
        return self._tapname

    def selecttap(self):
        while True:
            i = randint(100, 999)
            tap = "sdtap" + str(i)
            sp = subprocess.run(["ip", "link", "show", tap])
            if sp.returncode == 0:
                continue
            self._tapname = tap
            break

    def usage(self):
        print("python3 scripts/tunnels/simpletunnel.py [-s|-d|-c serverip] [-v] [-p port] [-l locaip] [-h|--help]")
        pass

    def clear(self):
        sp = subprocess.run(["ps", "-C", "simpletun", "-f"], stdout=subprocess.PIPE)
        running = sp.stdout.decode()
        sp = subprocess.run(["ip", "link", "show"], stdout=subprocess.PIPE)
        for l in sp.stdout.splitlines():
            items = l.decode().split(":")
            if len(items) < 2:
                continue
            nic = items[1].strip()
            if not len(nic) == 8:
                continue
            if "sdtap" not in nic:
                continue
            if nic in running:
                continue
            subprocess.run(["ip", "tuntap", "del", "mode", "tap", nic])
        sp = subprocess.run(["/sbin/brctl", "show"], stdout=subprocess.PIPE)
        for l in sp.stdout.decode().splitlines():
            if not "sdtunnel-" in l:
                continue
            items = l.split()
            if len(items) < 4:
                subprocess.run(["ip", "link", "set", items[0], "down"])
                subprocess.run(["/sbin/brctl", "delbr", items[0]])
        pass

    def server(self, port, localip, verbose):
        self.clear()
        items = localip.split(".")
        serverbr = "sdtunnel-" + items[2]
        sp = subprocess.run(["ip", "address", "show", serverbr])
        if sp.returncode != 0:
            print("Create bridge", serverbr)
            subprocess.run(["brctl", "addbr", serverbr])
            subprocess.run(["ip", "link", "set", serverbr, "up"])
            subprocess.run(["ip", "addr", "add", localip + "/24", "dev", serverbr])
            pass

        #select a tap device
        self.selecttap()
        print("")
        print("Select tapname:", self.tapname())
        subprocess.run(["ip", "tuntap", "add", "mode", "tap", self.tapname()])
        subprocess.run(["ip", "link", "set", self.tapname(), "up"])
        sp = subprocess.run(["brctl", "addif", serverbr, self.tapname()])
        if sp.returncode != 0:
            subprocess.run(["ip", "tuntap", "del", "mode", "tap", self.tapname()])
            print("Can not add", self.tapname(), "to", serverbr)
            sys.exit(-1)

        if verbose:
            args = ["./scripts/tunnels/simpletun", "-a", "-i", self.tapname(), "-s", "-p", str(port), "-d"]
        else:
            args = ["./scripts/tunnels/simpletun", "-a", "-i", self.tapname(), "-s", "-p", str(port)]

        while True:
            subprocess.run(args)
            print("restart simpletun as it quit.")
            time.sleep(10)
        pass

    def client(self, ip, port, localip, verbose):
        self.clear()

        self.selecttap()
        print("")
        print("Select tapname:", self.tapname())
        subprocess.run(["ip", "tuntap", "add", "mode", "tap", self.tapname()])
        subprocess.run(["ip", "addr", "add", localip + "/24", "dev", self.tapname()])
        subprocess.run(["ip", "link", "set", self.tapname(), "up"])

        if verbose:
            args = ["./scripts/tunnels/simpletun", "-a", "-i", self.tapname(), "-c", ip, "-p", str(port), "-d"]
        else:
            args = ["./scripts/tunnels/simpletun", "-a", "-i", self.tapname(), "-c", ip, "-p", str(port)]
        while True:
            subprocess.run(args)
            print("restart simpletun as it quit.")
            time.sleep(10)
        pass

    def run(self, argv):
        opts, args = getopt(argv, "hsdvc:p:l:", ["help"])
        port = None
        localip = None
        verbose = False
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
            elif o in "-v":
                verbose = True
            elif o in "-d":
                self.clear()
                return

        if port == None:
            self.usage()
            sys.exit(-1)

        for o, v in opts:
            if o in "-s":
                print("simpletunnel server, port: ", port)
                self.server(port, localip, verbose)
                pass
            elif o in '-c':
                ip = v
                if localip == None:
                    self.usage()
                    sys.exit(-1)
                self.client(ip, port, localip, verbose)
                pass


if __name__ == "__main__":
    # to be sure current working directory is root of git project
    print("Checking working directory ...")
    try:
        cwd = os.environ["RUNONPYCHARM"]
    except:
        cwd = os.environ["PYTHONPATH"]
    assert utils.runningUnderGitProjectRootDirectory(cwd)
    os.chdir(cwd)

    #TODO, We should have self logging system, temporlary use system log
    st = SimpleTunnel()
    st.run(sys.argv[1:])
