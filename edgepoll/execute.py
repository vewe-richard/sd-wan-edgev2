from edgepoll import edgeconfig
import traceback
import xml.etree.ElementTree as ET
import json
from edgepoll.edgeconfig import EdgeConfig
import subprocess
from edgeutils import utils

class Execute():
    def __init__(self, logger):
        self._logger = logger
        pass

    def run(self, xmlstr):
        root = ET.fromstring(xmlstr)
        version = None
        sn = None
        actionid = None
        actions = list()
        atype = None
        self._logger.info(__file__ + ":  parsing xml ...")
        for x in root:
            if x.tag == "head":
                version = x.attrib["version"]
                sn = x.attrib["sn"]
                actionid = x.attrib["actionid"]
                atype = x.attrib["actiontype"]
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
            if actionid == None or atype == None:
                raise Exception("no action id or action type exist")
            try:
                self.doactions(actionid, actions)
            except Exception as e:
                self._logger.error(traceback.format_exc())
                print(sn, actionid, atype, "-1", "Exception")
                utils.http_post(EdgeConfig.getInstance().sms(), EdgeConfig.getInstance().smsport(), "/north/actionresult/", {"cmd": "actionresult"})


    def doactions(self, aid, actions):
        self._logger.info("doactions ...")
        for a in actions:
            self._logger.info("action: %s", a)
            if a["type"] == "subprocess":
                self.subprocess(aid, a["params"])
        pass

    def subprocess(self, aid, params):
        env = dict()
        env["SN"] = EdgeConfig.getInstance().sn()
        env["ACTIONID"] = aid
#        try:
#            env.append(params["env"])
#        except:
#            pass

        sp = subprocess.run(params["args"], env=env)
        #TODO, we may report to controller if subprocess returncode is not zero
        if sp.returncode != 0:
            utils.http_post(EdgeConfig.getInstance().sms(), EdgeConfig.getInstance().smsport(), "/north/actionresult/",
                            {"cmd": "actionresult"})







