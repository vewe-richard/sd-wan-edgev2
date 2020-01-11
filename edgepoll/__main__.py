# !/usr/bin/python3
# Description: entry of sd-wan edgepoll service
# Note: three ways on calling this script
# 1. As Service
#   ExecStart=/usr/bin/python3 {GITROOT}/edgepoll/__main__.py --log=/var/log/sdwan/edge/edge.log
#   Environment=PYTHONPATH="{GITROOT}"
# 2. On shell
#   export PYTHONPATH="$GITROOT" &&  python3 edgepoll/__main__.py --config="./config.json" --loglevel=10
# 3. On Pycharm
#   --config="./config.json"
# By vewe-richard@github, 2020/01/10
#

import sys
import os
from edgeutils import utils
from getopt import getopt
import logging
from edgepoll.edgeconfig import EdgeConfig
import subprocess
from edgepoll import poll

def usage():
    print("")
    print("python3 edgepoll/__main__.py [-h|--help] [--log=logfile] [--loglevel=loglevel] [--config=config]")
    print("")
    print("\tlogfile: default is stdout if not specified. Run as service, normally logfile is /var/log/sdwan/edge/log")
    print("")
    print("\tloglevel: default is 30, [CRITICAL:50 ERROR:40 WARNING:30 INFO:20 DEBUG:10]")
    print("")
    print("\tconfig: configfile, default is /etc/sdwan/edge/config.json if not specified")
    print("")

def logsetup(logfile, loglevel):
    logger = logging.getLogger("edgepoll")

    if logfile == None:
        logging.basicConfig(level=loglevel, format="%(levelname)s:\t%(message)s")
    else:
        subprocess.run(["mkdir", "-p", os.path.dirname(logfile)])
        handler = logging.FileHandler(logfile)
        logging.basicConfig(level=loglevel)
        handler.setLevel(loglevel)
        formater = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formater)
        logger.addHandler(handler)
    return logger

if __name__ == "__main__":
    # to be sure current working directory is root of git project
    print("Checking working directory ...")
    cwd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    assert utils.runningUnderGitProjectRootDirectory(cwd)
    os.chdir(cwd)

    #input parameters
    print("Parse input parameters ...")
    opts, args = getopt(sys.argv[1:], "-h", ["log=", "loglevel=", "config=", "help"])

    logfile = None #default is stdout
    configfile = "/etc/sdwan/edge/config.json"
    loglevel = logging.WARNING

    for o, v in opts:
        if o in "-h" or o in "--help":
            usage()
            sys.exit(-1)
        elif o in "--log":
            logfile = v
        elif o in "--loglevel":
            loglevel = int(v)
        elif o in "--config":
            configfile = v

    #check parameters
    #! configfile
    print("Load config and edgeversion ...")
    EdgeConfig.getInstance().loadconfig(configfile)
    EdgeConfig.getInstance().loadedgeversion()
    # Any more pre-run environment checking can be add here

    #logfile
    print("Setup logger ...")
    logger = logsetup(logfile, loglevel)

    #
    print("Main Block ...")
    poll.poll(logger)
    print("Exit edgepoll")









