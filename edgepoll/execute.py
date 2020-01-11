from multiprocessing import Process
from edgepoll import edgeconfig
import traceback

def execute(inputQueue, mainQueue):
    try:
        logger = edgeconfig.EdgeConfig.getInstance().logger()
        logger.info("Begin execute child process ...")
        while True:
            v = inputQueue.get()
            logger.debug("Got input message: {}".format(v))
    except Exception as e:
        logger = edgeconfig.EdgeConfig.getInstance().logger()
        logger.error(traceback.format_exc())
        traceback.print_exc()
    finally:
        mainQueue.put("kill")



def executeInit(inputQueue, mainQueue):
    p = Process(target=execute, args=(inputQueue, mainQueue))
    p.start()
    return p
