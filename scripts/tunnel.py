# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller
# Hints:
# 1. when run independly, from run=>edit configurations
#    set environment, PYTHONPATH=/home/richard/PycharmProjects/sd-wan-edgev2, CONFIGFILE=config.json
#    and working directory, /home/richard/PycharmProjects/sd-wan-edgev2
# 2. run in shell:
#    sudo su
#    export PYTHONPATH="$PWD" &&  python3 scripts/tunnel.py -s -p 5555
#    export PYTHONPATH="$PWD" &&  python3 scripts/tunnel.py -c 127.0.0.1 -p 5555 -l 10.139.37.2
#   export PYTHONPATH="$PWD" &&  python3 scripts/tunnel.py -d -p 5555
from getopt import getopt
import sys
import socket
import os
import subprocess
from edgeutils import utils

def usage():
    print("python3 scripts/tunnel.py [-s|-d|-c serverip] [-p port] [-l locaip] [-h|--help]", file=sys.stderr)
    pass

def server(port):
    # check parameters
    # if port is available, if port is used, it will raise exception socket.error
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))

    cmdline = "/usr/bin/python3 " + os.getcwd() + "/scripts/tunnels/simpletunnel.py -s -p " + str(port)

    # install service
    with open("./scripts/tunnels/simpletun.service") as f:
        tmp = f.read().replace("{GITROOT}", os.getcwd())
        serviceFile = tmp.replace("{CMDLINE}", cmdline)
    svcname = "simpletun.s." + str(port) + ".service"
    print("install service: ", svcname)
    with open("/lib/systemd/system/"+svcname, "w") as f:
        f.write(serviceFile)
    subprocess.run(["systemctl", "disable", svcname])
    subprocess.run(["systemctl", "stop", svcname])
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "start", svcname])
    subprocess.run(["systemctl", "enable", svcname])
    pass

def client(ip, port, localip):
    #TODO: check if localip is belong to "10.139.37.1/24"
    iprange = "10.139.37."
    slen = len(iprange)
    if len(localip) < slen or localip[:slen] not in iprange:
        print("Wrong local ip, is not in range", file=sys.stderr)
        sys.exit(-1)
    cmdline = "/usr/bin/python3 " + os.getcwd() + "/scripts/tunnels/simpletunnel.py -c " + ip + " -p " + str(port) + " -l " + localip

    # install service
    with open("./scripts/tunnels/simpletun.service") as f:
        tmp = f.read().replace("{GITROOT}", os.getcwd())
        serviceFile = tmp.replace("{CMDLINE}", cmdline)
    svcname = "simpletun.c." + str(port) + ".service"
    print("install service: ", svcname)
    with open("/lib/systemd/system/"+svcname, "w") as f:
        f.write(serviceFile)
    subprocess.run(["systemctl", "disable", svcname])
    subprocess.run(["systemctl", "stop", svcname])
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "start", svcname])
    subprocess.run(["systemctl", "enable", svcname])
    pass

def delete(port):
    svcnames = ["simpletun.s."+str(port)+".service", "simpletun.c."+str(port)+".service"]
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
    pass


if __name__ == "__main__":
    opts, args = getopt(sys.argv[1:], "hsdc:p:l:", ["help"])
    port = None
    localip = None

    for o, v in opts:
        if o in "-h" or o in "--help":
            usage()
            sys.exit(-1)
        elif o in "-p":
            port = int(v)
            pass
        elif o in "-l":
            localip = v
            pass

    if port == None:
        print("Port is not provided", file=sys.stderr)
        usage()
        sys.exit(-1)

    for o, v in opts:
        if o in "-s":
            print("simpletunnel server, port: ", port)
            server(port)
            pass
        elif o in '-c':
            ip = v
            if localip == None:
                usage()
                sys.exit(-1)
            client(ip, port, localip)
            pass
        elif o in "-d":
            delete(port)
            pass

    try:
        os.environ["SN"]
    except:
        # in test environment, just exit, do not report
        print("test environment", file=sys.stderr)
        sys.exit(-1)

    report = utils.reportactionresult(os.environ["SN"], os.environ["ACTIONID"], os.environ["ACTIONTYPE"],
                                          0, "OK", "")
    utils.http_post(os.environ["SMS"], os.environ["SMSPORT"], "/north/actionresult/", report)
    sys.exit(0)
    pass