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
    '''
    sp = subprocess.run(["tail", "-c", "2048", "/var/log/sdwan/edge/edge.log"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = "edge.log\n\n" + sp.stdout.decode()
    err = sp.stderr.decode()
    ret = sp.returncode
    '''

    sp = subprocess.run(["journalctl", "-p", "6", "-u", "edgepoll", "-o", "cat", "-n", "50"], stdout=subprocess.PIPE)
    out = "syslog\n\n" + sp.stdout.decode()


    doreport(0, out, "")