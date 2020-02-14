# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller

import subprocess
import os
import sys

def doreport(ret, out, err):
    try:
        from edgeutils import utils
        report = utils.reportactionresult(os.environ["SN"], os.environ["ACTIONID"], os.environ["ACTIONTYPE"],
                                      ret, out, err)
        utils.http_post(os.environ["SMS"], os.environ["SMSPORT"], "/north/actionresult/", report)
    except:
        print("returncode: ", ret)
        print("stdout: ", out)
        print("stderr: ", err)


# tunnelstatus.py client|server port
if __name__ == "__main__":
    try:
        port = sys.argv[2]
        if "client" in sys.argv[1]:
            isclient = True
            service = "simpletun.c." + port
        else:
            isclient = False
            service = "simpletun.s." + port
    except:
        doreport(-1, str(sys.argv), "Error Parameters")
        sys.exit(-1)

    out = ""

    sp = subprocess.run(["systemctl", "status", service], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tout = sp.stdout.decode()
    terr = sp.stderr.decode()
    tret = sp.returncode
    if tret != 0:
        doreport(tret, tout, terr)
        sys.exit(-1)

    tap = None
    for l in tout.splitlines():
        if "Loaded:" in l:
            out += l + "\n"
        elif "Active:" in l:
            out += l + "\n"
        elif "scripts/tunnels" in l:
            out += l + "\n"
            if "-i" in l:
                items = l.split("-i")
                if "tap" in items[1]:
                    its = items[1].split()
                    tap = its[0]

    if tap is None:
        doreport(-1, out, "Can not find tap in systemctl status output")
        sys.exit(-1)

    if not isclient:
        doreport(0, out, "")
        sys.exit(0)

    sp = subprocess.run(["ping", "-I", tap, "-c", "3", "-W", "3", "10.139.37.1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tout = sp.stdout.decode()
    terr = sp.stderr.decode()
    tret = sp.returncode

    out += tout
    if tret != 0:
        doreport(-1, out, terr)
        sys.exit(-1)

    doreport(0, out, "")






