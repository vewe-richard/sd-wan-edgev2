# !/usr/bin/python3
# Description: install sd-wan edgepoll service
# By vewe-richard@github, 2020/01/10
#

import sys
import os
from edgeutils import utils
import subprocess

if __name__ == "__main__":
    assert sys.version_info >= (3, 0)
    assert utils.runningUnderGitProjectRootDirectory(os.getcwd())
    #check if systemd is support
    assert os.path.isdir("/lib/systemd/system/")
    with open("./edgepoll/edgepoll.service") as f:
        serviceFile = f.read().replace("{GITROOT}", os.getcwd())
    #write to /lib/systemd/system
    with open("/lib/systemd/system/edgepoll.service", "w") as f:
        f.write(serviceFile)
    subprocess.run(["mkdir", "-p", "/etc/sdwan/edge/"])
    subprocess.run(["cp", "config.json", "/etc/sdwan/edge/"])
    subprocess.run(["systemctl", "disable", "edgepoll.service"])
    subprocess.run(["systemctl", "stop", "edgepoll.service"])
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "start", "edgepoll.service"])
    subprocess.run(["systemctl", "enable", "edgepoll.service"])
    print("Install Complete")
    print("Please run 'systemctl status edgepoll' to check service status")
