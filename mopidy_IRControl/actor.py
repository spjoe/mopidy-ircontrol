import pykka
import pylirc
import logging
import tempfile
import threading
import select

from mopidy.core import PlaybackState
from mopidy.core import CoreListener

logger = logging.getLogger('mopidy_IRControl')

LIRC_PROG_NAME = "mopidyIRControl"


class Event(list):
    """Event subscription.

    A list of callable objects. Calling an instance of this will cause a
    call to each item in the list in ascending order by index."""
    def __call__(self, *args, **kwargs):
        for f in self:
            f(*args, **kwargs)

    def __repr__(self):
        return "Event(%s)" % list.__repr__(self)


class CommandDispatcher(object):
    def __init__(self, core, config, buttonPressEvent):
        self.core = core
        self.config = config
        self._handlers = {}
        self.registerHandler('playpause', self._playpauseHandler)
        self.registerHandler('mute', self._muteHandler)
        self.registerHandler('stop', lambda: self.core.playback.stop().get())
        self.registerHandler('next', lambda: self.core.playback.next().get())
        self.registerHandler('previous',
                             lambda: self.core.playback.previous().get())
        self.registerHandler('volumedown',
                             self._volumeFunction(lambda vol: vol - 5))
        self.registerHandler('volumeup',
                             self._volumeFunction(lambda vol: vol + 5))

        for i in range(10):
            self.registerHandler('num{0}'.format(i), self._playlistFunction(i))

        buttonPressEvent.append(self.handleCommand)

    def handleCommand(self, cmd):
        if cmd in self._handlers:
            logger.debug("Command {0} was handled".format(cmd))
            self._handlers[cmd]()
        else:
            logger.debug("Command {0} was not handled".format(cmd))

    def registerHandler(self, cmd, handler):
        self._handlers[cmd] = handler

    def _playpauseHandler(self):
        state = self.core.playback.get_state().get()
        if(state == PlaybackState.PAUSED):
            self.core.playback.resume().get()
        elif (state == PlaybackState.PLAYING):
            self.core.playback.pause().get()
        elif (state == PlaybackState.STOPPED):
            self.core.playback.play().get()

    def _muteHandler(self):
        self.core.mixer.set_mute(not self.core.mixer.get_mute().get())

    def _volumeFunction(self, changeFct):
        def volumeChange():
            vol = self.core.mixer.get_volume().get()
            self.core.mixer.set_volume(min(max(0, changeFct(vol)), 100))
        return volumeChange

    def _playPlaylist(self, uri):
        refs = self.core.playlists.get_items(uri).get()
        if not refs:
            logger.warn("Playlist '%s' does not exist", uri)
            return
        self.core.tracklist.clear()
        uris = map(lambda ref: ref.uri, refs)
        self.core.tracklist.add(uris=uris)
        self.core.tracklist.set_consume(False)
        self.core.tracklist.set_repeat(True)
        self.core.playback.play()

    def _playlistFunction(self, num):
        return lambda: self._playPlaylist(self.config['playlist_uri_template'].format(num))

class LircThread(threading.Thread):
    def __init__(self, configFile):
        threading.Thread.__init__(self)
        self.name = 'Lirc worker thread'
        self.configFile = configFile
        self.frontendActive = True
        self.ButtonPressed = Event()

    def run(self):
        try:
            self.run_inside_try()
        except Exception as e:
            logger.warning('IRControl has problems starting pylirc: ' + str(e))

    def run_inside_try(self):
        self.startPyLirc()

    def startPyLirc(self):
        lircHandle = pylirc.init(LIRC_PROG_NAME, self.configFile, 0)
        if(lircHandle != 0):
            while(self.frontendActive):
                self.consumePylirc(lircHandle)
            pylirc.exit()

    def consumePylirc(self, lircHandle):
        try:
            if(select.select([lircHandle], [], [], 1) == ([], [], [])):
                pass
            else:
                s = pylirc.nextcode(1)
                self.handleNextCode(s)
        except Exception as e:
            logger.warning('Exception during handling a command: ' + str(e))

    def handleNextCode(self, s):
        if s:
            self.handleLircCode(s)

    def handleLircCode(self, s):
        for code in s:
            self.handleCommand(code['config'])

    def handleCommand(self, cmd):
        logger.debug('Command: {0}'.format(cmd))
        self.ButtonPressed(cmd)


class IRControlFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super(IRControlFrontend, self).__init__()
        self.core = core
        self.config = config['IRControl']
        self.configFile = self.generateLircConfigFile(config['IRControl'])
        logger.debug('lircrc file:{0}'.format(self.configFile))

    def on_start(self):
        try:
            logger.debug('IRControl starting')
            self.thread = LircThread(self.configFile)
            self.dispatcher = CommandDispatcher(
                self.core,
                self.config,
                self.thread.ButtonPressed)
            self.thread.ButtonPressed.append(self.handleButtonPress)
            self.thread.start()
            logger.debug('IRControl started')
        except Exception as e:
            logger.warning('IRControl has not started: ' + str(e))
            self.stop()

    def on_stop(self):
        logger.info('IRControl stopped')
        self.thread.frontendActive = False
        self.thread.join()

    def on_failure(self):
        logger.warning('IRControl failing')
        self.thread.frontendActive = False
        self.thread.join()

    def handleButtonPress(self, cmd):
        pass
        # CoreListener.send("IRButtonPressed", button=cmd)

    def generateLircConfigFile(self, config):
        '''Returns file name of generate config file for pylirc'''
        f = tempfile.NamedTemporaryFile(delete=False)
        skeleton = 'begin\n   prog={2}\n   button={0}\n   config={1}\nend\n'
        for action in config:
            entry = skeleton.format(config[action], action, LIRC_PROG_NAME)
            f.write(entry)
        f.close()
        return f.name
