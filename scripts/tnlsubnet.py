# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller

import subprocess
import os
import sys
import traceback

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

def validipaddress(ip):
    try:
        items = ip.split(".")
        for i in range(0, 4):
            v = int(items[i])
            if v > 255:
                return False
        return True
    except:
        return False

if __name__ == "__main__":
    print(sys.argv)
    try:
        cmd = sys.argv[1]
        subnet = sys.argv[2]

        if cmd not in ["add", "del"]:
            doreport(-1, "", "Invalid command " + str(sys.argv))
            sys.exit(-1)
        items = subnet.split("/")

        if not validipaddress(items[0]):
            doreport(-1, "", "Invalid subnet " + str(sys.argv))
            sys.exit(-1)

        if int(items[1]) > 32:
            doreport(-1, "", "Invalid subnet " + str(sys.argv))
            sys.exit(-1)

        if cmd == "add":
            peerip = sys.argv[3]
            if not validipaddress(peerip):
                doreport(-1, "", "Invalid peer ip " + str(sys.argv))
                sys.exit(-1)
            addsubnet(subnet, peerip)

        else:
            removesubnet(subnet)

    except Exception as e:
        doreport(-1, "", traceback.format_exc())
        sys.exit(-1)


    sp = subprocess.run(["journalctl", "-p", "6", "-u", "edgepoll", "-o", "cat", "-n", "50"], stdout=subprocess.PIPE)
    out = "syslog\n\n" + sp.stdout.decode()


    doreport(0, out, "")