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
    sp = subprocess.run(["ps", "-ef"], stdout=subprocess.PIPE)
    out = "list edgepoll and simpletun processes\n"
    for l in sp.stdout.splitlines():
        dl = l.decode()
        if "simpletun" in dl or "edgepoll" in dl:
            out += dl + "\n"

    sp = subprocess.run(["ip", "route", "list"], stdout=subprocess.PIPE)
    out += "\nip route list\n" + sp.stdout.decode()

    sp = subprocess.run(["ip", "address", "show"], stdout=subprocess.PIPE)
    out += "\nip address show\n" + sp.stdout.decode()

    try:
        sp = subprocess.run(["brctl", "show"], stdout=subprocess.PIPE)
        out += "\nbrctl show\n" + sp.stdout.decode()
    except:
        out += "\nbrctl is not exist\n"

    doreport(0, out, "")