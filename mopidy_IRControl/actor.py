import pykka
import pylirc
import logging
import tempfile

from time import sleep

from mopidy.core import PlaybackState
from mopidy.utils import process

logger = logging.getLogger('mopidy_IRControl')

LIRC_PROG_NAME = "mopidyIRControl"


class CommandDispatcher(object):
    def __init__(self, core):
        self.core = core
        self._handlers = {}
        self.registerHandler('playpause', self._playpauseHandler)

    def handleCommand(self, cmd):
        handler = self._handlers[cmd]
        if handler:
            handler(self.core)

    def registerHandler(self, cmd, handler):
        self._handlers[cmd] = handler

    def _playpauseHandler(self, core):
        state = core.playback.state.get()
        if(state == PlaybackState.PAUSED):
            core.playback.resume().get()
        elif (state == PlaybackState.PLAYING):
            core.playback.pause().get()
        elif (state == PlaybackState.STOPPED):
            core.playback.play().get()


class LircThread(process.BaseThread):
    def __init__(self, core, configFile):
        super(LircThread, self).__init__()
        self.name = 'Lirc worker thread'
        self.core = core
        self.configFile = configFile
        self.dispatcher = CommandDispatcher(core)

    def run_inside_try(self):
        self.startPyLirc()

    def startPyLirc(self):
        if(pylirc.init(LIRC_PROG_NAME, self.configFile, 0)):
            while(True):
                s = pylirc.nextcode(1)
                self.handleNextCode(s)
                sleep(0.1)
            pylirc.exit()

    def handleNextCode(self, s):
        if s:
            self.handleLircCode(s)

    def handleLircCode(self, s):
        for code in s:
            self.handleCommand(code['config'])

    def handleCommand(self, cmd):
        logger.debug('Command: {0}'.format(cmd))
        self.dispatcher.handleCommand(cmd)


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
        except Exception:
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
