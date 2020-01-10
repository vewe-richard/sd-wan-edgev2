import os

def runningUnderGitProjectRootDirectory(cwd):
    return os.path.isfile(os.path.join(cwd, "LICENSE"))
