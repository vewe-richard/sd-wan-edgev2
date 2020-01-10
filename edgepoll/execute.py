from multiprocessing import Process


def execute(inputQueue):
    while True:
        v = inputQueue.get()
        print(v)


def executeInit(inputQueue):
    p = Process(target=execute, args=(inputQueue,))
    p.start()
    return p
