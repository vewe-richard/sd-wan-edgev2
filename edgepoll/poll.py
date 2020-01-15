from multiprocessing import Process, Lock
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from edgepoll.edgeconfig import EdgeConfig
import traceback
from edgeutils import utils
from edgepoll.execute import Execute
import subprocess

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

    if utils.istest(EdgeConfig.getInstance()):
        logger.info("In test environment, start simple controller from testscripts")
        subprocess.Popen(["python3", "./testscripts/test.py"])

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
        try:
            resp = utils.http_post(ec.sms(), ec.smsport(), "/north/", {"CMD": "poll", "SN": EdgeConfig.getInstance().sn()})
            xmlstr = resp.read().decode()
            logger.debug("edge polling get response: %s", xmlstr)
            exec.run(xmlstr)
        except ConnectionRefusedError as e:
            logger.warning(e)
        except Exception as e:
            logger.error(traceback.format_exc())

        break

        if utils.istest(EdgeConfig.getInstance()):
            sp = subprocess.run(["ps", "-ef"], stdout=subprocess.PIPE)
            for line in sp.stdout.splitlines():
                l = line.decode()
                if "python3" in l and "testscripts" in l:
                    items = l.split()
                    subprocess.run(["kill", "-9", items[1]])

            logger.warning("In test environment, Exit loop for debug purpose, it's developing environment")
            break

        released = lock.acquire(block=True, timeout=timeout)
        if released:
            logger.debug("got edge pollnotify")
        else:
            logger.debug("timeout, polling ...")



