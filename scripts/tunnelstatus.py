# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller

import subprocess
import os
import sys
from edgeutils import utils

def doreport(ret, out, err):
    try:
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
            opts = {"entry": "http", "module": "stun", "cmd": "query", "node": "client", "port": port}
        else:
            isclient = False
            opts = {"entry": "http", "module": "stun", "cmd": "query", "node": "server", "port": port}
    except:
        doreport(-1, str(sys.argv), "Error Parameters")
        sys.exit(-1)

    out = ""
    resp = utils.http_post("127.0.0.1", 11112, "/", opts)
    out += resp.read().decode("utf-8")

    doreport(0, out, "")
    '''
    sp = subprocess.run(["ping", "-I", tap, "-c", "3", "-W", "3", ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tout = sp.stdout.decode()
    terr = sp.stderr.decode()
    tret = sp.returncode

    out += tout
    if tret != 0:
        doreport(-1, out, terr)
        sys.exit(-1)

    doreport(0, out, "")
    '''





