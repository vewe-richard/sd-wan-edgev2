# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller
# Hints:
# Need test with edgepoll:testscripts/test.py
# xml = utils.oneactionxml("00010001", "100", "tunnel", '["python3", "scripts/tunnel.py", "-d", "-p", "5556"]')
# python3 scripts/tunnel.py -s -p 5555 -l 10.139.27.1
# python3 scripts/tunnel.py -c 10.129.101.100 -p 5555 -l 10.139.27.3

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


if __name__ == "__main__":
    opts, args = getopt(sys.argv[1:], "hvsdc:p:l:", ["help"])
    port = ""
    localip = None
    verbose = ""
    remove = False

    for o, v in opts:
        if o in "-h" or o in "--help":
            usage()
            sys.exit(-1)
        elif o in "-p":
            port = v
        elif o in "-l":
            localip = v
        elif o in "-v":
            verbose = "-v"
        elif o in "-d":
            remove = True
            pass

    int(port)
    inputport = os.environ["INPUTPORT"]  #notifyport
    if remove:
        opts = {"entry": "http", "module": "stun", "cmd": "delete", "port": port}
        resp = utils.http_post("127.0.0.1", inputport, "/", opts)
        result = ""
        if resp.getcode() == 200:
            result = resp.read().decode("utf-8")
            if result == "OK":
                doreport(0, "OK", "")
                sys.exit(0)
        else:
            result = "post to notifytask fail"
        doreport(0, "NOK", result)
        sys.exit(0)

    if localip == None:
        print("Localip is not provided", file=sys.stderr)
        usage()
        sys.exit(-1)

    cmdline = None
    for o, v in opts:
        if o in "-s":
            opts = {"entry": "http", "module": "stun", "cmd": "add", "node": "server", "tunortap": "tap", "tunneltype": "ipsec", "port": port, "tunnelip": localip, }
            resp = utils.http_post("127.0.0.1", inputport, "/", opts)
            break
        elif o in '-c':
            ip = v
            opts = {"entry": "http", "module": "stun", "cmd": "add", "node": "client", "tunortap": "tap", "tunneltype": "ipsec", "port": port, "tunnelip": localip, "server": ip}
            resp = utils.http_post("127.0.0.1", inputport, "/", opts)
            break
    else:
        doreport(0, "NOK", "Invalid Command")
        sys.exit(0)

    if resp.getcode() == 200:
        result = resp.read().decode("utf-8")
        if result == "OK":
            doreport(0, "OK", "")
            sys.exit(0)
    else:
        result = "post to notifytask fail"

    doreport(0, "NOK", result)