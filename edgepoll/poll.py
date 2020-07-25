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

class InvalidSMSException(Exception):
    pass

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

    def do_GET(self):
        self._logger.info("get http: " + self.path)
        if "status" in self.path:
            self.send_response(200)
            self.send_header("Content-type", "text/html;charset=utf-8")
            self.end_headers()
            response = BytesIO()

            for name, obj in self._inithandler.objs().items():
                status = obj.status()
                if len(status) < 1:
                    continue
                n = obj.name()
                if len(n) < 1:
                    n = name
                headline = "<h1>" + n + "</h1><pre>"
                response.write(headline.encode())
                response.write(obj.status().encode())
                response.write("</pre>".encode())


            self.wfile.write(response.getvalue())
            #self.wfile.write("hello world!!!".encode())
        else:
            self.send_response(400)
            self.end_headers()

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
                if mydict["cmd"] == "readycheck":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(bytearray(b'OK'))
                    return
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
    mydict = {"entry": "mainself", "cmd": "initquery", "completed": True}
    myqueue.put(mydict)
    try:
        httpd = HTTPServer(('', EdgeConfig.getInstance().inputport()), SimpleHTTPRequestHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("break notifypoll thread due to keyboard interrupt")
    except Exception as e:
        logger.info(traceback.format_exc())
    finally:
        httpd.server_close()
        for k, v in ih.objs().items():
            logger.info("join of inithandlers.Http, %s, %s", str(k), str(v))
            v.join(timeout=1)
        for k, v in ih.objs().items():
            logger.info("terminate of inithandlers.Http, %s, %s", str(k), str(v))
            v.term()

        logger.warn("exit 8: notifytask thread")


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
        notifytask.join(timeout=1)
        logger.info("join of notifytask")
        for k, v in ih.objs().items():
            v.join(timeout=1)
            logger.info("join of inithandlers.Main, %s, %s", str(k), str(v))

        notifytask.terminate()
        logger.info("terminate of notifytask")
        for k, v in ih.objs().items():
            logger.info("terminate of inithandlers.Main, %s, %s", str(k), str(v))
            v.term()
        logger.warning("exit 9: poll thread")

def _poll(logger, myqueue, initHandler):
    #subprocess.Popen(["python3", "./testscripts/test.py"])

    ec = EdgeConfig.getInstance()
    timeout = ec.timeout()
    exec = Execute(logger)
    while True:
        try:
            if len(ec.sms().strip()) < 5:
                raise InvalidSMSException("")
            resp = utils.http_post(ec.sms(), ec.smsport(), "/north/", {"CMD": "poll", "SN": ec.sn()})
            xmlstr = resp.read().decode()
            logger.debug("edge polling get response: %s", xmlstr)
            exec.run(xmlstr)
        except ConnectionRefusedError as e:
            logger.warning(e)
        except InvalidSMSException:
            pass
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
                elif msg["cmd"] == "initquery":
                    ec.set_init_completed()
                    for i in range(0, 4):
                        utils.led_set_value(0)
                        time.sleep(0.5)
                        utils.led_set_value(7)
                        time.sleep(0.5)
                    utils.led_set_value(0)

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


