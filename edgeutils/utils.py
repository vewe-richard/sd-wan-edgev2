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


def oneactionxml(sn, args):
    xml = '</xml>'
    xml += '<sn>' + sn + '</sn>'
    xml += '<subprocess>'
    xml += '<args>' + args + '</args>'
    xml += '</subprocess>'
    xml += '</xml>'
    return xml

