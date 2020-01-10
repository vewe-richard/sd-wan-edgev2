# !/usr/bin/python3
# Description: entry of sd-wan edge-poll service
# Note: Once call this file from shell, need set PYTHONPATH to root of git project, For example:
# export PYTHONPATH="$PWD" &&  python3 edge-poll/__main__.py 
# By vewe-richard@github, 2020/01/10
#

import sys
import os
from edgeutils import utils

if __name__ == "__main__":
    # to be sure current working directory is root of git project
    cwd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    assert utils.runningUnderGitProjectRootDirectory(cwd)
    os.chdir(cwd)

