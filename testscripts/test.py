from edgeutils import utils
from edgepoll import edgeconfig
import os
from multiprocessing import Process
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
import time

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b'OK')
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
    servertask = Process(target=servertask, args=(ec,))
    servertask.start()
    time.sleep(1)
    opts = {"cmd": "pollnotify"}
    resp = utils.http_post("127.0.0.1", ec.inputport(), "/", opts)

