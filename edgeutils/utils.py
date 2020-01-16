import os
import http.client, urllib.parse

def runningUnderGitProjectRootDirectory(cwd):
    return os.path.isfile(os.path.join(cwd, "LICENSE"))


def http_post(ip, port, url, opts):
    params = urllib.parse.urlencode(opts)
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/xml"}
    conn = http.client.HTTPConnection(ip, port=port)
    conn.request("POST", url, params, headers)
    response = conn.getresponse()
    return response


def oneactionxml(sn, actionid, actiontype, args):
    xml = '<xml>'
    xml += '<head version="1.0" sn="' + sn + '" actionid="' + actionid + '" actiontype="' + actiontype + '"/>'
    xml += '<subprocess>'
    xml += '<args>' + args + '</args>'
    xml += '</subprocess>'
    xml += '</xml>'
    return xml

def istest(ec):
    if "5676" in ec.sn():
        return True
    else:
        return False

def reportactionresult(sn, actionid, actiontype, returncode, astdout, astderr):
    mydict = dict()
    mydict["sn"] = sn
    mydict["actionid"] = actionid
    mydict["actiontype"] = actiontype
    mydict["returncode"] = returncode
    mydict["stdout"] = astdout
    mydict["stderr"] = astderr
    return mydict