import json
import subprocess

class EdgeConfig:
    __instance = None

    @staticmethod
    def getInstance():
        if EdgeConfig.__instance == None:
            EdgeConfig()
        return EdgeConfig.__instance

    def __init__(self):
        if EdgeConfig.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            EdgeConfig.__instance = self

    def loadconfig(self, configfile):
        self._configfile = configfile
        with open(configfile) as json_file:
            self._config = json.load(json_file)

        try:
            self._config["sn"]
            self._config["type"]
            self._config["name"]
            self._config["spec"]
            self._config["sw"]
            self._config["sms"]
            self._config["smsport"]
            self._config["publicip"]
            self._config["inputport"]
            self._config["timeout"]
        except Exception as e:
            raise Exception("Wrong edge config file: " + configfile)

    def init_completed(self):
        try:
            return self._init_completed
        except:
            return False

    def set_init_completed(self):
        self._init_completed = True

    def loadedgeversion(self):
        with open("./version.json") as json_file:
            self._edgeversion = json.load(json_file)

        try:
            self._edgeversion["major"]
            self._edgeversion["minor"]
        except Exception as e:
            raise Exception("Wrong edge version file: ./version.json")

        #find git commit number
        sp = subprocess.run(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE)
        commit = sp.stdout.decode()[:7]
        try:
            int(commit, base=16)
        except Exception as e:
            raise Exception("Can not get git commit number")
        self._edgeversion["commit"] = commit

    def inputport(self):
        return self._config["inputport"]

    def timeout(self):
        return self._config["timeout"]

    def sms(self):
        return self._config["sms"]

    def smsport(self):
        return self._config["smsport"]

    def sn(self):
        return self._config["sn"]

    def config(self):
        return self._config

    def edgeversion(self):
        return self._edgeversion

    def configfile(self):
        return self._configfile