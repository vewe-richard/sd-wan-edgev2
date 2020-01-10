from multiprocessing import Process
import time



def pipeInput(inputQueue):
    while True:
        inputQueue.put("hello")
        time.sleep(1)

def inputInit(inputQueue):
    p1 = Process(target=pipeInput, args=(inputQueue,))
    p1.start()
    return [p1]

