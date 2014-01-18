import pykka
import pylirc
import logging
import tempfile

from threading import Thread

from mopidy.core import PlaybackState
from mopidy.utils import process

logger = logging.getLogger('mopidy_IRControl')

LIRC_PROG_NAME = "mopidyIRControl"

class IRControlFrontend(pykka.ThreadingActor):
    def __init__(self, config, core):
        super(IRControlFrontend, self).__init__()
        self.core = core
        self.configFile = self.generateLircConfigFile(config['IRControl'])
        logger.debug(self.configFile)
        logger.debug(core)

    def on_start(self):
        logger.debug('IRControl starting')
        self.started = True
        self.thread = process.BaseThread(target = self.startPyLirc, args = ())
        self.thread.start()
        logger.debug('IRControl started')

    def on_stop(self):
        logger.info('IRControl stopped')
        self.thread.join(1)
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
                logger.debug('get next code from pylirc')
                s = pylirc.nextcode(1)
                self.handleNextCode(s)
            pylirc.exit()

    def handleNextCode(self, s):
        if s:
            self.handleLircCommand(s)

    def handleLircCommand(self, s):
        for code in s:
            state = self.core.playback.state.get()
            if(code['config'] == 'playpause' and state == PlaybackState.PAUSED):
                self.core.resume()
            elif (code['config'] == 'playpause' and state == PlaybackState.PLAYING):
                self.core.pause()
            logger.debug('Command: {0}'.format(code['config']))
