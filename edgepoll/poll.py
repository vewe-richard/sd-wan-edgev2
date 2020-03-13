from multiprocessing import Process, Queue
from queue import Empty
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from edgepoll.edgeconfig import EdgeConfig
import traceback
from edgeutils import utils
from edgepoll.execute import Execute
import subprocess
from edgepoll.inithandler import InitHandler

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    _queue = None
    _logger = None
    _inithandler = None
    def poststr2dict(self, poststr):
        items = poststr.split("&")
        mydict = dict()
        for item in items:
            ii = item.split("=")
            mydict[ii[0]] = ii[1]
        return mydict

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        try:
            mydict = self.poststr2dict(body.decode())
            # this is the message to poll process, such as pollnotify message
            if mydict["entry"] == "mainself":
                self._queue.put(mydict)
                self.send_response(200)
                self.end_headers()
                return
            # this is the message to Main class in init scripts
            elif mydict["entry"] == "main":
                self._queue.put(mydict)
                self.send_response(200)
                self.end_headers()
                return
            # this is the message to this process self
            elif mydict["entry"] == "httpself":
                pass
            # this is the message to Http class in init scripts
            elif mydict["entry"] == "http":
                obj = self._inithandler.obj(mydict["module"])
                rlt = obj.post(mydict)
                self.send_response(200)
                self.end_headers()
                response = BytesIO()
                response.write(rlt.encode())
                self.wfile.write(response.getvalue())
                return
        except:
            self._logger.info(traceback.format_exc())
            self.send_response(400)
            self.end_headers()
            return

        self.send_response(400)
        self.end_headers()
#        response = BytesIO()
#        response.write(b'OK')
#        self.wfile.write(response.getvalue())


def notifypoll(logger, myqueue):
    logger.info("Begin httpserver to wait poll notify ...")
    ih = InitHandler("http", logger)
    SimpleHTTPRequestHandler._queue = myqueue
    SimpleHTTPRequestHandler._logger = logger
    SimpleHTTPRequestHandler._inithandler = ih
    try:
        httpd = HTTPServer(('', EdgeConfig.getInstance().inputport()), SimpleHTTPRequestHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
        time.sleep(2)  # wait a bit time before terminate those task force
        for k, v in ih.objs().items():
            logger.info("exit 2: terminate inithandlers, %s, %s", str(k), str(v))
            v.term()

        for k, v in ih.objs().items():
            logger.info("exit 2: wait for join of inithandlers, %s, %s", str(k), str(v))
            v.join()
        logger.warn("exit 3: notifytask is break due to keyboardinterrupt")


def poll(logger):
    ih = InitHandler("main", logger)

    myqueue = Queue()
    notifytask = Process(target=notifypoll, args=(logger, myqueue))
    notifytask.start()

    try:
        _poll(logger, myqueue, ih)
    except Exception as e:
        logger.error(traceback.format_exc())
        traceback.print_exc()
    finally:
        time.sleep(3) # wait a bit time before terminate those task force
        notifytask.terminate()
        logger.warning("exit 4: wait for notifytask terminate")
        notifytask.join()

def _poll(logger, myqueue, initHandler):
    subprocess.Popen(["python3", "./testscripts/test.py"])

    ec = EdgeConfig.getInstance()
    timeout = ec.timeout()
    exec = Execute(logger)
    while True:
        try:
            resp = utils.http_post(ec.sms(), ec.smsport(), "/north/", {"CMD": "poll", "SN": ec.sn()})
            xmlstr = resp.read().decode()
            logger.debug("edge polling get response: %s", xmlstr)
            exec.run(xmlstr)
        except ConnectionRefusedError as e:
            logger.warning(e)
        except Exception as e:
            logger.error(traceback.format_exc())

        # todo wait queue timeout
        try:
            msg = myqueue.get(timeout=timeout)
            logger.debug("msg: %s", str(msg))
            entry = msg["entry"]
            if entry == "mainself":
                if msg["cmd"] == "pollnotify":
                    logger.debug("poll notifying")
            elif entry == "main":
                obj = initHandler.obj(msg["module"])
                obj.post(msg)
        except Empty:
            logger.debug("timeout wait for queue")
            #break
        except KeyboardInterrupt:
            logger.warn("break poll thread due to keyboard interrupt")
            break
        except:
            logger.warn(traceback.format_exc())
            break


