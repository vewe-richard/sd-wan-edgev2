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
        xml = utils.oneactionxml("00010001", '["python3", "scripts/test.py"]')
        response = BytesIO()
        response.write(str.encode(xml))
        self.wfile.write(response.getvalue())
        os.kill(os.getpid(), 9)

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
    print("testtmp.py: send pollnotify")
    opts = {"cmd": "pollnotify"}
    resp = utils.http_post("127.0.0.1", ec.inputport(), "/", opts)

