from edgepoll import edgeconfig
import traceback
import xml.etree.ElementTree as ET
import json
import os
import subprocess
from edgepoll.edgeconfig import EdgeConfig
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

        if version == "1.0":
            if sn != EdgeConfig.getInstance().sn():
                raise Exception("serial number mismatched")
            if actionid == None or atype == None:
                raise Exception("no action id or action type exist")
            try:
                self.doactions(actionid, atype, actions)
            except Exception as e:
                self._logger.error(traceback.format_exc())
                astderr = type(e).__name__ + ": " + str(e).strip("'")
                report = utils.reportactionresult(sn, actionid, atype, -1, "", astderr)
                utils.http_post(EdgeConfig.getInstance().sms(), EdgeConfig.getInstance().smsport(), "/north/actionresult/", report)


    def doactions(self, aid, atype, actions):
        self._logger.info("doactions ...")
        for a in actions:
            self._logger.info("action: %s", a)
            if a["type"] == "subprocess":
                self.subprocess(aid, atype, a["params"])
        pass

    def subprocess(self, aid, atype, params):
        env = dict()
        env["SN"] = EdgeConfig.getInstance().sn()
        env["ACTIONID"] = aid
        env["ACTIONTYPE"] = atype
        env["SMS"] = EdgeConfig.getInstance().sms()
        env["SMSPORT"] = str(EdgeConfig.getInstance().smsport())
        env["PYTHONPATH"] = os.environ["PYTHONPATH"]
        env["CONFIGFILE"] = EdgeConfig.getInstance().configfile()
        env["INPUTPORT"] = str(EdgeConfig.getInstance().inputport())
#        try:
#            env.append(params["env"])
#        except:
#            pass

        sp = subprocess.run(params["args"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        astdout = sp.stdout.decode()
        astderr = sp.stderr.decode()
        self._logger.info("action stdout: \n%s", astdout)
        self._logger.info("action stderr: \n%s", astderr)
        if sp.returncode != 0:

            report = utils.reportactionresult(env["SN"], aid, atype, sp.returncode, astdout[-100:-1], astderr[-200:-1])
            utils.http_post(EdgeConfig.getInstance().sms(), EdgeConfig.getInstance().smsport(), "/north/actionresult/",
                            report)







