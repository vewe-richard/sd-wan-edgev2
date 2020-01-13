import os
import sys

if __name__ == "__main__":
    print(os.environ["SN"], os.environ["ACTIONID"])
    sys.exit(-1)