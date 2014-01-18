import pykka
import pylirc
import logging
import thread
import tempfile

from mopidy.core import CoreListener
from mopidy.utils import encoding, network, process

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

LIRC_PROG_NAME = "mopidyIRControl"

class IRControlFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super(IRControlFrontend, self).__init__()
        self.core = core
        self.configFile = self.generateLircConfigFile(config['IRControl'])
        logger.info(self.configFile)
        logger.debug('test debug')

    def on_start(self):
        logger.info('IRControl started')
        self.started = True
        self.startPyLirc()

    def on_stop(self):
        logger.info('IRControl stopped')
        self.started = False
     
    def generateLircConfigFile(self, config):
        '''Returns file name of generate config file for pylirc'''
        f = tempfile.NamedTemporaryFile(delete=False)
        for action in config:
            entry = 'begin\n    prog={2}\n    button={0}\n    config={1}\nend\n'.format(config[action], action, LIRC_PROG_NAME)
            f.write(entry)
        f.close()
        return f.name

    def startPyLirc(self):
        if(pylirc.init(LIRC_PROG_NAME, self.configFile, 1)):
            while(self.started):
                logger.info('get next code from pylirc')
                s = pylirc.nextcode(1)
                logger.info(s)
                self.handleNextCode(s)
            pylirc.exit()

    def handleNextCode(self, s):
        if s:
            self.handleLircCommand(s)

    def handleLircCommand(self, s):
        for code in s:
            if(code['config'] == 'playpause' and self.core.state == self.core.PlaybackState.PAUSED):
                self.core.resume()
            elif (code['config'] == 'playpause' and self.core.state == self.core.PlaybackState.PLAYING):
                self.core.pause()
            logger.info('Command: {0}'.format(code['config']))
