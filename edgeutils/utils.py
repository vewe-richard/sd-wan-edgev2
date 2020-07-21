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

def reportactionresult(sn, actionid, actiontype, returncode, astdout, astderr):
    mydict = dict()
    mydict["sn"] = sn
    mydict["actionid"] = actionid
    mydict["actiontype"] = actiontype
    mydict["returncode"] = returncode
    mydict["stdout"] = astdout
    mydict["stderr"] = astderr
    return mydict

def led_set_value(value):
    bits = '{0:08b}'.format(value)
    for i in range(0, 3):
        if bits[(i + 1)*(-1)] == "1":
            led(i, True)
        else:
            led(i, False)

def led(pos, enable):
    gpios = ["/sys/class/gpio/gpio461/value", "/sys/class/gpio/gpio511/value", "/sys/class/gpio/gpio462/value"]
    #print(pos, enable)

    try:
        if enable:
            v = 0
        else:
            v = 1
        with open(gpios[pos], "w") as f:
            f.write(str(v))
        f.close()
    except:
        pass







