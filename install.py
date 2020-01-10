# !/usr/bin/python3
# Description: install sd-wan edge-poll service
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
    with open("./edge-poll/edge-poll.service") as f:
        serviceFile = f.read().replace("{GITROOT}", os.getcwd())
    #write to /lib/systemd/system
    with open("/lib/systemd/system/edge-poll.service", "w") as f:
        f.write(serviceFile)
    subprocess.run(["systemctl", "disable", "edge-poll.service"])
    subprocess.run(["systemctl", "stop", "edge-poll.service"])
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "start", "edge-poll.service"])
    subprocess.run(["systemctl", "enable", "edge-poll.service"])
    print("Install Complete")
    print("Please run 'systemctl status edge-poll' to check service status")
