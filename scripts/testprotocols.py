# Rules:
# 1. script need send report by itself to controller
# 2. if script call sys.exit(nozero) to exit, edge will generate a error report to controller
# 3. on exception, it means system exit with nozero, edge will generate an error report to controller

import os
import sys

if __name__ == "__main__":
    print(os.environ["SN"], os.environ["ACTIONID"], os.environ["ACTIONTYPE"])
    print("stdout message")
    print("error message", file=sys.stderr)
#    sys.exit(-1)
    raise Exception("Bad messsge")