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
    except:
        print("returncode: ", ret)
        print("stdout: ", out)
        print("stderr: ", err)


if __name__ == "__main__":
    sp = subprocess.run(["echo", "helloworld"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = sp.stdout.decode()
    err = sp.stderr.decode()
    ret = sp.returncode

    doreport(ret, out, err)