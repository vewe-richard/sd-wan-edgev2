# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller
# Hints:
# 1. when run independly, from run=>edit configurations
#    set environment, PYTHONPATH=/home/richard/PycharmProjects/sd-wan-edgev2, CONFIGFILE=config.json
#    and working directory, /home/richard/PycharmProjects/sd-wan-edgev2

import os
import sys
import subprocess
from edgeutils import utils
from edgepoll.edgeconfig import EdgeConfig

def getwans():
    sp = subprocess.run(["ip", "route", "show", "default"], stdout=subprocess.PIPE)
    wans = dict()
    for line in sp.stdout.splitlines():
        l = line.decode().split()
        sp2 = subprocess.run(["ip", "address", "show", l[4]], stdout=subprocess.PIPE)
        ip = None
        for ll in sp2.stdout.splitlines():
            nl = ll.decode()
            if "inet " in nl:
                ip = nl.split()[1].split("/")[0]
                break
        if ip != None:
            wans[l[4]] =ip
    return wans

if __name__ == "__main__":
    EdgeConfig.getInstance().loadconfig(os.environ["CONFIGFILE"])
    EdgeConfig.getInstance().loadedgeversion()

    config = EdgeConfig.getInstance().config()
    config["CMD"] = "query"
    config["wans"] = getwans()
    version = EdgeConfig.getInstance().edgeversion()
    config["version"] = version["major"] + "." + version["minor"] + "." + version["commit"]
    try:
        os.environ["SN"]
    except:
        # in test environment, just exit, do not report
        print(config)
        print("test environment", file=sys.stderr)
        sys.exit(-1)
    report = utils.reportactionresult(os.environ["SN"], os.environ["ACTIONID"], os.environ["ACTIONTYPE"],
                                          0, str(config), "")
    utils.http_post(os.environ["SMS"], os.environ["SMSPORT"], "/north/actionresult/", report)
    sys.exit(0)


