# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller

import subprocess
import os

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


if __name__ == "__main__":
    out = ""
    sp = subprocess.run(["systemctl", "list-units", "--type=service"], stdout=subprocess.PIPE)
    for l in sp.stdout.splitlines():
        dl = l.decode()
        if "simpletun" in dl:
            items = dl.split()
            try:
                if "simpletun" in items[0]:
                    svc = items[0]
                elif "simpletun" in items[1]:
                    svc = items[1]
            except:
                continue

            subprocess.run(["systemctl", "disable", svc])
            subprocess.run(["systemctl", "stop", svc])
            try:
                os.unlink("/lib/systemd/system/" + svc)
            except:
                pass

    sp = subprocess.run(["ip", "route", "list"], stdout=subprocess.PIPE)
    rlt = sp.stdout.decode()
    for l in rlt.splitlines():
        items = l.split()
        if len(items) < 5:
            continue
        if "default" == items[0]:
            continue
        if "10.139" in items[2] and "via" == items[1]:
            subprocess.run(["ip", "route", "delete", items[0], "via", items[2]])

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
        subprocess.run(["ip", "tuntap", "del", "mode", "tap", nic])
    sp = subprocess.run(["/sbin/brctl", "show"], stdout=subprocess.PIPE)
    for l in sp.stdout.decode().splitlines():
        if not "sdtunnel-" in l:
            continue
        items = l.split()
        if len(items) < 4:
            subprocess.run(["ip", "link", "set", items[0], "down"])
            subprocess.run(["/sbin/brctl", "delbr", items[0]])



    doreport(0, out, "")