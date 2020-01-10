from multiprocessing import Process
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from edgepoll.edgeconfig import EdgeConfig

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Hello, world!')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b'This is POST request. ')
        response.write(b'Received: ')
        response.write(body)
        self.wfile.write(response.getvalue())

def httpInput(inputQueue):
    httpd = HTTPServer(('', EdgeConfig.getInstance().inputport()), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def inputInit(inputQueue):
    p1 = Process(target=httpInput, args=(inputQueue,))
    p1.start()
    return [p1]

