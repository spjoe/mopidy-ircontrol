import pykka
import pylirc
import logging
import tempfile

from mopidy.core import PlaybackState
from mopidy.utils import process

logger = logging.getLogger('mopidy_IRControl')

LIRC_PROG_NAME = "mopidyIRControl"


class LircThread(process.BaseThread):
    def __init__(self, core, configFile):
        super(LircThread, self).__init__()
        self.core = core
        self.configFile = configFile

    def run_inside_try(self):
        self.startPyLirc()

    def startPyLirc(self):
        if(pylirc.init(LIRC_PROG_NAME, self.configFile, 1)):
            while(True):
                s = pylirc.nextcode(1)
                self.handleNextCode(s)
            pylirc.exit()

    def handleNextCode(self, s):
        if s:
            self.handleLircCommand(s)

    def handleLircCommand(self, s):
        for code in s:
            state = self.core.playback.state.get()
            if(code['config'] == 'playpause' and
                    state == PlaybackState.PAUSED):
                self.core.resume().get()
            elif (code['config'] == 'playpause' and
                    state == PlaybackState.PLAYING):
                self.core.pause().get()
            logger.debug('Command: {0}'.format(code['config']))


class IRControlFrontend(pykka.ThreadingActor):
    def __init__(self, config, core):
        super(IRControlFrontend, self).__init__()
        self.core = core
        self.configFile = self.generateLircConfigFile(config['IRControl'])
        logger.debug('lircrc file:{0}'.format(self.configFile))

    def on_start(self):
        try:
            logger.debug('IRControl starting')
            self.started = True
            self.thread = LircThread(self.core, self.configFile)
            self.thread.start()
            logger.debug('IRControl started')
        except Exception as e:
            logger.warning('IRControl has not started')
            self.stop()

    def on_stop(self):
        logger.info('IRControl stopped')
        self.thread.join(1)
        self.started = False

    def generateLircConfigFile(self, config):
        '''Returns file name of generate config file for pylirc'''
        f = tempfile.NamedTemporaryFile(delete=False)
        skeleton = 'begin\n   prog={2}\n   button={0}\n   config={1}\nend\n'
        for action in config:
            entry = skeleton.format(config[action], action, LIRC_PROG_NAME)
            f.write(entry)
        f.close()
        return f.name
