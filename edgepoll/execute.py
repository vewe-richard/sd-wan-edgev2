from edgepoll import edgeconfig
import traceback
import xml.etree.ElementTree as ET

class Execute():
    def __init__(self, logger):
        self._logger = logger
        pass

    def run(self, xmlstr):
        root = ET.fromstring(xmlstr)
        for x in root:
            print(x.tag, x.attrib, x.text)
            if x.tag == "subprocess":
                for y in x:
                    print(y.tag, y.text)
        pass

