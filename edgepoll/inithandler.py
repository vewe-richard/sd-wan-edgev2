import importlib
from os import listdir
import os
from edgeutils import utils
import traceback
import logging

class InitHandler:
    def __init__(self, entry, logger):
        self._logger = logger
        self._objs = dict()
        self._entry = entry

        tree = listdir('edgeinit')
        ls = []
        for f in tree:
            if self.isscript(f):
                ls.append(f)
        # sort the list
        sls = sorted(ls)

        # for each script, import module, and create mapping
        for f in sls:
            try:
                items = f.split("_")
                its = items[1].split(".")
                module = "edgeinit." + items[0]+"_"+items[1][:-3]
                mod = importlib.import_module(module)
                self.storeobj(its[0], mod)
            except:
                logger.warn(traceback.format_exc())
                continue

    def isscript(self, f):
        if f[0] != 's':
            return False
        items = f[1:].split("_")
        try:
            num = int(items[0])
            return True
        except:
            return False

    def objs(self):
        return self._objs

    def obj(self, name): #for exmaple stun
        try:
            return self._objs[name]
        except:
            self._logger.warn("module %s is not exist, try to load it", name)

        tree = listdir('edgeinit')
        for f in tree:
            if not self.isscript(f):
                continue
            if ("_" + name + ".py") in f:
                break
        else:
            return None

        mod = importlib.import_module("edgeinit." + f[:-3])
        self.storeobj(name, mod)
        return self._objs[name]

    def storeobj(self, name, mod):
        entry = self._entry
        if entry == "http":
            try:
                cls = getattr(mod, "Http")
                obj = cls(self._logger)
                obj.start()
                self._objs[name] = obj
            except:
                self._logger.warn(traceback.format_exc())
                pass
        elif entry == "main":
            try:
                cls = getattr(mod, "Main")
                obj = cls(self._logger)
                obj.start()
                self._objs[name] = obj
            except AttributeError as e:
                self._logger.info("%s", str(e))
            except:
                self._logger.warn(traceback.format_exc())
                pass
            pass


    def post(self, msg):
        pass






if __name__ == "__main__":
    print("Checking working directory ...")
    cwd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    assert utils.runningUnderGitProjectRootDirectory(cwd)
    os.chdir(cwd)

    logger = logging.getLogger("edgepoll")
    logging.basicConfig(level=10, format="%(asctime)s - %(levelname)s: %(name)s{%(filename)s:%(lineno)s}\t%(message)s")

    ih = InitHandler("http", logger)

    for k, v in ih.objs().items():
        print(k, v)

    obj = ih.obj("xxxx")
    print(obj)

    ih = InitHandler("main", logger)

    for k, v in ih.objs().items():
        print(k, v)

    obj = ih.obj("xxxx")
    print(obj)
    pass