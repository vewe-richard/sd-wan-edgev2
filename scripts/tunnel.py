# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller
# Hints:
# 1. when run independly, from run=>edit configurations
#    set environment, PYTHONPATH=/home/richard/PycharmProjects/sd-wan-edgev2, CONFIGFILE=config.json
#    and working directory, /home/richard/PycharmProjects/sd-wan-edgev2
# 2. run in shell:
# sudo su
# python3 sd-wan-env/ns4tunnels.py
#
# export PYTHONPATH="$PWD" && python3 scripts/tunnel.py -s -p 5555 -l 10.139.27.1 -n main
# export PYTHONPATH="$PWD" && python3 scripts/tunnel.py -c 10.129.101.100 -p 5555 -l 10.139.27.3 -n n101
# ip netns exec n101 ping 10.139.27.1
#
# export PYTHONPATH="$PWD" && python3 scripts/tunnel.py -s -p 55556 -l 10.139.47.1 -n main
# export PYTHONPATH="$PWD" && python3 scripts/tunnel.py -c 10.129.101.100 -p 55556 -l 10.139.47.3 -n n101
# ip netns exec n101 ping 10.139.47.1
#
# export PYTHONPATH="$PWD" && python3 scripts/tunnel.py -s -p 33333 -l 10.139.27.1 -n main
# export PYTHONPATH="$PWD" && python3 scripts/tunnel.py -c 10.129.102.100 -p 33333 -l 10.139.27.8 -n n102
# ip netns exec n102 ping 10.139.27.3

from getopt import getopt
import sys
import socket
import os
import subprocess
from edgeutils import utils

def doreport(ret, out, err):
    try:
        from edgeutils import utils
        report = utils.reportactionresult(os.environ["SN"], os.environ["ACTIONID"], os.environ["ACTIONTYPE"],
                                      ret, out, err)
        utils.http_post(os.environ["SMS"], os.environ["SMSPORT"], "/north/actionresult/", report)
    except Exception as e:
        print("returncode: ", ret)
        print("stdout: ", out)
        print("stderr: ", err)

def usage():
    print("python3 scripts/tunnel.py [-s|-d|-c serverip] [-p port] [-l locaip] [-v] [-n namespace] [-h|--help]", file=sys.stderr)
    pass

def delete(port):
    svcnames = ["simpletun.s."+port+".service", "simpletun.c."+port+".service"]
    for svc in svcnames:
        sp = subprocess.run(["systemctl", "status", svc])
        if sp.returncode != 0:
            continue
        subprocess.run(["systemctl", "disable", svc])
        subprocess.run(["systemctl", "stop", svc])
        try:
            os.unlink("/lib/systemd/system/" + svc)
        except:
            pass
    from scripts.tunnels.simpletunnel import SimpleTunnel
    SimpleTunnel().clear()
    pass



def install(svcname, cmdline):
    # install service
    with open("./scripts/tunnels/simpletun.service") as f:
        tmp = f.read().replace("{GITROOT}", os.getcwd())
        serviceFile = tmp.replace("{CMDLINE}", cmdline)
    print("install service: ", svcname)
    subprocess.run(["systemctl", "disable", svcname])
    subprocess.run(["systemctl", "stop", svcname])
    with open("/lib/systemd/system/"+svcname, "w") as f:
        f.write(serviceFile)
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "start", svcname])
    subprocess.run(["systemctl", "enable", svcname])
    pass

if __name__ == "__main__":
    opts, args = getopt(sys.argv[1:], "hvsdc:p:l:n:", ["help"])
    port = ""
    localip = None
    verbose = ""
    ns = ""
    remove = False

    for o, v in opts:
        if o in "-h" or o in "--help":
            usage()
            sys.exit(-1)
        elif o in "-p":
            port = v
        elif o in "-l":
            localip = " -l " + v + " "
        elif o in "-v":
            verbose = "-v"
        elif o in "-n":
            ns = "/sbin/ip netns exec " + v + " "
        elif o in "-d":
            remove = True
            pass

    if not ns:
        pid = os.getpid()
        sp = subprocess.run(["ip", "netns", "identify", str(pid)], stdout=subprocess.PIPE)
        ns = sp.stdout.decode().strip()
        if len(ns) < 2:
            ns = ""
        else:
            ns = "/sbin/ip netns exec " + ns + " "

    print("namespace:", ns)

    int(port)
    if remove:
        delete(port)
        doreport(0, "OK", "")
        sys.exit(0)

    if localip == None:
        print("Localip is not provided", file=sys.stderr)
        usage()
        sys.exit(-1)

    cmdline = None
    for o, v in opts:
        if o in "-s":
            print("simpletunnel server, port: ", port)
            svcname = "simpletun.s." + port + ".service"
            cmdline = ns + "/usr/bin/python3 " + os.getcwd() + "/scripts/tunnels/simpletunnel.py -s -p " + port + localip + verbose
        elif o in '-c':
            ip = v
            svcname = "simpletun.c." + port + ".service"
            cmdline = ns + "/usr/bin/python3 " + os.getcwd() + "/scripts/tunnels/simpletunnel.py -c " + ip + " -p " + port + localip + verbose
    if not cmdline is None:
        install(svcname, cmdline)
        doreport(0, "OK", "")