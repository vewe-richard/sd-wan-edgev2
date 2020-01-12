from edgepoll import edgeconfig
import traceback
import xml.etree.ElementTree as ET
import json
from edgepoll.edgeconfig import EdgeConfig
import subprocess

class Execute():
    def __init__(self, logger):
        self._logger = logger
        pass

    def run(self, xmlstr):
        root = ET.fromstring(xmlstr)
        version = None
        sn = None
        actions = list()
        self._logger.info(__file__ + ":  parsing xml ...")
        for x in root:
            if x.tag == "head":
                version = x.attrib["version"]
                sn = x.attrib["sn"]
            elif x.tag == "subprocess":
                params = dict()
                for y in x:
                    if y.tag == "args":
                        params[y.tag] = json.loads(y.text)
                    else:
                        params[y.tag] = y.text
                actions.append({"type": x.tag, "params": params})

        if version == None:
            self._logger("Old version compability, todo ...")
        elif version == "1.0":
            if sn != EdgeConfig.getInstance().sn():
                raise Exception("serial number mismatched")
            try:
                self.doactions(actions)
            except Exception as e:
                self._logger.error(traceback.format_exc())
                # TODO: we may report to controller


    def doactions(self, actions):
        self._logger.info("doactions ...")
        for a in actions:
            self._logger.info("action:", a)
            if a["type"] == "subprocess":
                self.subprocess(a["params"])
        pass

    def subprocess(self, params):
        env = dict()
        env["SN"] = EdgeConfig.getInstance().sn()
#        try:
#            env.append(params["env"])
#        except:
#            pass

        subprocess.run(params["args"], env=env)
        #TODO, we may report to controller if subprocess returncode is not zero







