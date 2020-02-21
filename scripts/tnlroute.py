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
    except Exception as e:
        print("returncode: ", ret)
        print("stdout: ", out)
        print("stderr: ", err)

def validip(ip):
    items = ip.split(".")
    if not len(items) == 4:
        return False
    return True

def add(ip, subnets):
    if not validip(ip):
        return "invalid ip " + ip
    sp = subprocess.run(["ip", "route", "list"], stdout=subprocess.PIPE)
    rlt = sp.stdout.decode()
    existroute = ""
    for l in rlt.splitlines():
        items = l.split()
        if "default" in items[0]:
            continue
        existroute += items[0] + " "

    for sn in subnets:
        items = sn.split("/")
        if not validip(items[0]):
            continue
        its = items[0].split(".")
        cmp = its[0]+"."+its[1] + "." + its[2]
        if cmp in existroute:
            continue
        subprocess.run(["ip", "route", "add", sn, "via", ip])

    return "OK"

def delete(ip, subnets):
    sp = subprocess.run(["ip", "route", "list"], stdout=subprocess.PIPE)
    rlt = sp.stdout.decode()
    for l in rlt.splitlines():
        items = l.split()
        if len(items) < 5:
            continue
        if "default" == items[0]:
            continue
        if ip == items[2]:
            subprocess.run(["ip", "route", "delete", items[0], "via", ip])

    return "OK"

if __name__ == "__main__":
    z = len(sys.argv)
    if z < 4:
        doreport(-1, "too less arguments", "")
        sys.exit()
    if sys.argv[1] == "add":
        out = add(sys.argv[2], sys.argv[3:])
    else:
        out = delete(sys.argv[2], sys.argv[3:])

    doreport(0, out, "")


