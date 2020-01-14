import sys
import subprocess

class VM():
    def __init__(self, id, istap=False):
        self._id = id
        if istap:
            self._mode = "tap"
            self._nic = "tap13"
        else:
            self._mode = "tun"
            self._nic = "tun13"

    def nic(self):
        return self._nic

    def mode(self):
        if self._mode == "tap":
            return "-a"
        else:
            return "-u"

    def id(self):
        return self._id

    def name(self):
        return "vm" + str(self._id)

    def destroy(self):
        subprocess.run(["ip", "netns", "exec", self.name(), "ip", "tuntap", "del", "mode", self._mode, self._nic])
        subprocess.run(["ip", "netns", "del", self.name()])
        pass

    def setup(self):
        self.destroy()
        tunip = "10.10.0." + str(self._id) + "/24"
        # add namespace
        subprocess.run(["ip", "netns", "add", self.name()])
        subprocess.run(["ip", "netns", "exec", self.name(), "ip", "tuntap", "add", "mode", self._mode, self._nic])
        subprocess.run(["ip", "netns", "exec", self.name(), "ip", "addr", "add", tunip, "dev", self._nic])
        subprocess.run(["ip", "netns", "exec", self.name(), "ip", "link", "set", self._nic, "up"])
        pass


def link(vm1, vm2):
    vname = "veth" + str(vm1.id()) + str(vm2.id())
    pname = "p" + vname
    unlink(vm1, vm2)
    subprocess.run(["ip", "link", "add", vname, "type", "veth", "peer", "name", pname])
    subprocess.run(["ip", "link", "set", vname, "netns", vm1.name()])
    subprocess.run(["ip", "link", "set", pname, "netns", vm2.name()])

    ip = "10.20.0." + str(vm1.id()) + "/24"
    pip = "10.20.0." + str(vm2.id()) + "/24"
    subprocess.run(["ip", "netns", "exec", vm1.name(), "ip", "addr", "add", ip, "dev", vname])
    subprocess.run(["ip", "netns", "exec", vm1.name(), "ip", "link", "set", vname, "up"])

    subprocess.run(["ip", "netns", "exec", vm2.name(), "ip", "addr", "add", pip, "dev", pname])
    subprocess.run(["ip", "netns", "exec", vm2.name(), "ip", "link", "set", pname, "up"])
    pass

def unlink(vm1, vm2):
    vname = "veth" + str(vm1.id()) + str(vm2.id())
    subprocess.run(["ip", "link", "delete", vname, "type", "veth"])
    pass



def start():
    vm1 = VM(1, istap=True)
    vm1.setup()
    vm2 = VM(2, istap=True)
    vm2.setup()
    link(vm1, vm2)
    nic = vm1.nic()
    mode = vm1.mode()
    print("Usage: sudo ip netns exec vm1 /home/richard/diyvpn/simpletun", mode, "-i", nic, "-s -p 5555 -d")
    print(" sudo ip netns exec vm2 /home/richard/diyvpn/simpletun", mode, "-i", nic, "-c 10.20.0.1 -p 5555 -d")
    pass

def stop():
    vm1 = VM(1)
    vm1.destroy()
    vm2 = VM(2)
    vm2.destroy()
    unlink(vm1, vm2)
    pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: debugtunnel.py start|stop")
        sys.exit(-1)
    if sys.argv[1] == "start":
        print("start")
        start()
    elif sys.argv[1] == "stop":
        print("stop")
        stop()
    else:
        print("unknown command")