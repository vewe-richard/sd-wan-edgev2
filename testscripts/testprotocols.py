from edgeutils import utils
from edgepoll import edgeconfig
import os
from multiprocessing import Process
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import traceback

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def poststr2dict(self, poststr):
        items = poststr.split("&")
        mydict = dict()
        for item in items:
            ii = item.split("=")
            mydict[ii[0]] = ii[1]
        return mydict

    def actionxmlmissingargs(self, sn, actionid, actiontype, args):
        xml = '<xml>'
        xml += '<head version="1.0" sn="' + sn + '" actionid="' + actionid + '" actiontype="' + actiontype + '"/>'
        xml += '<subprocess>'
        xml += '<argswrong>' + args + '</argswrong>'
        xml += '</subprocess>'
        xml += '</xml>'
        return xml

    def north(self, body):
        mydict = self.poststr2dict(body.decode())
        print(__file__, ":post to /north: ", mydict)

        try:
            cmd = mydict["CMD"]
            if cmd == "poll":
#                xml = utils.oneactionxml("00010001", "100", "testprotocols", '["python3", "scripts/testprotocols.py"]')
                xml = self.actionxmlmissingargs("00010001", "100", "testprotocols", '["python3", "scripts/testprotocols.py"]') #test case, missing args, edge need report
                return str.encode(xml)
            else:
                return str.encode("UNKNOWN COMMAND: " + cmd)
        except:
            print(__file__, traceback.format_exc())
            return str.encode("NO COMMAND")

    def actionresult(self, body):
        print(__file__, "report action result")
        return str.encode("OK")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        path = self.path.rstrip("/")
        if path == "/north":
            resp = self.north(body)
        elif path == "/north/actionresult":
            resp = self.actionresult(body)
        else:
            resp = str.encode("NONE RESPONSE")

        self.send_response(200)
        self.end_headers()

        response = BytesIO()
        response.write(resp)
        self.wfile.write(response.getvalue())

def servertask(ec):
    httpd = HTTPServer(('', ec.smsport()), SimpleHTTPRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    cwd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    assert utils.runningUnderGitProjectRootDirectory(cwd)
    os.chdir(cwd)

    ec = edgeconfig.EdgeConfig.getInstance()
    ec.loadconfig("./config.json")

    #start http server
    pservertask = Process(target=servertask, args=(ec,))
    pservertask.start()

    time.sleep(1)
    # we can send pollnotify, if we know edge's ip address to fasten the polling
    print(__file__, ": send pollnotify")
    opts = {"cmd": "pollnotify"}
    resp = utils.http_post("127.0.0.1", ec.inputport(), "/", opts)
    pservertask.join()

