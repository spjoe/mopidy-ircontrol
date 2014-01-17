import pykka
import pylirc
import logging

from mopidy.core import CoreListener
from mopidy.utils import encoding, network, process

logger = logging.getLogger(__name__)

class IRControlFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super(IRControlFrontend, self).__init__()
        self.core = core
        self.configFile = generateLircConfigFile(config)

    def on_start(self):
        logger.info('IRControl started')

    def on_stop(self):
        logger.info('IRControl stopped')
     
    def generateLircConfig(self, config):
        '''Returns file name of generate config file for pylirc'''
        return "/tmp/123165.lircrc"
