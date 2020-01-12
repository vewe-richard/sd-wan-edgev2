from multiprocessing import Process, Lock
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from edgepoll.edgeconfig import EdgeConfig
import traceback
from edgeutils import utils
from edgepoll.execute import Execute

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    _lock = None

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        if "pollnotify" in body.decode():
            self.send_response(200)
        self.end_headers()
        self._lock.release()
#        response = BytesIO()
#        response.write(b'OK')
#        self.wfile.write(response.getvalue())


def notifypoll(logger, lock):
    logger.info("Begin httpserver to wait poll notify ...")

    SimpleHTTPRequestHandler._lock = lock
    httpd = HTTPServer(('', EdgeConfig.getInstance().inputport()), SimpleHTTPRequestHandler)
    httpd.serve_forever()


def poll(logger):
    lock = Lock()
    lock.acquire()
    notifytask = Process(target=notifypoll, args=(logger, lock))
    notifytask.start()

    try:
        _poll(logger, lock)
    except Exception as e:
        logger.error(traceback.format_exc())
        traceback.print_exc()
    finally:
        notifytask.terminate()

def _poll(logger, lock):
    timeout = EdgeConfig.getInstance().timeout()
    ec = EdgeConfig.getInstance()
    exec = Execute(logger)
    while True:
        released = lock.acquire(block=True, timeout=timeout)
        if released:
            logger.debug("got edge pollnotify")
        else:
            logger.debug("timeout, polling ...")
        try:
            resp = utils.http_post(ec.sms(), ec.smsport(), "/", {"cmd": "good"})
            xmlstr = resp.read().decode()
            logger.debug(xmlstr)
            exec.run(xmlstr)
        except ConnectionRefusedError as e:
            logger.warning(e)
        except Exception as e:
            logger.warning(e)

        if "127.0.0.1" in EdgeConfig.getInstance().sms():
            logger.warning("Exit loop for debug purpose, it's developing environment")
            break




