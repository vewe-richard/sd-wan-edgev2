from multiprocessing import Process
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from edgepoll.edgeconfig import EdgeConfig
import traceback

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    _inputQueue = None

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Hello, world!')

    def do_POST(self):
        try:
            logger = EdgeConfig.getInstance().logger()
            logger.info("Begin input httpserver process ...")

            self.mypost()
        except Exception as e:
            logger = EdgeConfig.getInstance().logger()
            logger.error(traceback.format_exc())


    def mypost(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b'This is POST request. ')
        response.write(b'Received: ')
        response.write(body)
        self._inputQueue.put(body)
        self.wfile.write(response.getvalue())


def httpInput(inputQueue, mainQueue):
    try:
        logger = EdgeConfig.getInstance().logger()
        logger.info("Begin input httpserver process ...")

        SimpleHTTPRequestHandler._inputQueue = inputQueue
        httpd = HTTPServer(('', EdgeConfig.getInstance().inputport()), SimpleHTTPRequestHandler)
        httpd.serve_forever()
    except Exception as e:
        logger = EdgeConfig.getInstance().logger()
        logger.error(traceback.format_exc())
        traceback.print_exc()
    finally:
        mainQueue.put("kill")


def inputInit(inputQueue, mainQueue):
    p1 = Process(target=httpInput, args=(inputQueue, mainQueue))
    p1.start()
    return [p1]

