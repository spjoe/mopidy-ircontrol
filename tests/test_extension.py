from __future__ import unicode_literals

import unittest
import mopidy
import pylirc
import time

from mock import Mock, patch
from mopidy_IRControl import Extension, actor as lib


class ExtensionTest(unittest.TestCase):
    def test_get_default_config(self):
        ext = Extension()

        config = ext.get_default_config()

        self.assertIn('[IRControl]', config)
        self.assertIn('enabled = true', config)

    def test_get_config_schema(self):
        ext = Extension()

        schema = ext.get_config_schema()
        self.assertIn('mute', schema)
        self.assertIn('playpause', schema)
        self.assertIn('next', schema)
        self.assertIn('previous', schema)
        self.assertIn('stop', schema)
        self.assertIn('volumedown', schema)
        self.assertIn('volumeup', schema)


class FrontendTest(unittest.TestCase):
    @classmethod
    def setup_class(self):
        IRconfig = {}
        IRconfig['next'] = 'KEY_NEXT'
        IRconfig['previous'] = 'KEY_PREVIOUS'
        IRconfig['playpause'] = 'KEY_PLAYPAUSE'
        IRconfig['stop'] = 'KEY_STOP'
        IRconfig['volumeup'] = 'KEY_VOLUMEUP'
        IRconfig['volumedown'] = 'KEY_VOLUMEDOWN'
        IRconfig['enabled'] = True
        self.config = {'IRControl': IRconfig}

    def test_on_start_should_spawn_thread(self):
        actor = lib.IRControlFrontend(self.config, None)
        actor.on_start()
        assert actor.thread is not None

    def test_on_stop(self):
        actor = lib.IRControlFrontend(self.config, None)
        actor.on_start()
        actor.on_stop()
        assert not actor.thread.isAlive()

    def test_on_failure(self):
        actor = lib.IRControlFrontend(self.config, None)
        actor.on_start()

        actor.on_failure()
        assert not actor.thread.isAlive()

    @patch('mopidy_IRControl.actor.logger')
    def test_on_start_log_exception(self, mock_logger):
        actor = lib.IRControlFrontend(self.config, None)
        with patch('mopidy_IRControl.actor.LircThread.start') as MockMethod:
            MockMethod.side_effect = Exception('Boom!')
            actor.on_start()
            self.assertTrue(mock_logger.warning.called)


class CommandDispatcherTest(unittest.TestCase):
    class WithGet:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

    def setUp(self):
        self.coreMock = mopidy.core.Core(None, [])
        self.buttonPressEvent = lib.Event()
        playback = Mock()
        playback.mute = self.WithGet(False)
        playback.volume = self.WithGet(50)
        playback.state = self.WithGet(mopidy.core.PlaybackState.STOPPED)
        self.coreMock.playback = playback

    def commandXYZHandler(self):
        self.executed = True

    def test_registerHandler(self):
        self.executed = False
        dispatcher = lib.CommandDispatcher(None, self.buttonPressEvent)
        dispatcher.registerHandler('commandXYZ', self.commandXYZHandler)
        dispatcher.handleCommand('commandXYZ')
        assert self.executed

    def test_handleCommand(self):
        self.executed = False
        dispatcher = lib.CommandDispatcher(None, self.buttonPressEvent)
        dispatcher.handleCommand('commandXYZ')
        assert not self.executed

    def test_default_registered_handler(self):
        dispatcher = lib.CommandDispatcher(None, self.buttonPressEvent)
        self.assertIn('mute', dispatcher._handlers)
        self.assertIn('playpause', dispatcher._handlers)
        self.assertIn('next', dispatcher._handlers)
        self.assertIn('previous', dispatcher._handlers)
        self.assertIn('stop', dispatcher._handlers)
        self.assertIn('volumedown', dispatcher._handlers)
        self.assertIn('volumeup', dispatcher._handlers)

    def test_stop_handler(self):
        dispatcher = lib.CommandDispatcher(self.coreMock,
                                           self.buttonPressEvent)
        dispatcher.handleCommand('stop')
        self.coreMock.playback.stop.assert_called_with()

    def test_mute_handler(self):
        dispatcher = lib.CommandDispatcher(self.coreMock,
                                           self.buttonPressEvent)
        dispatcher.handleCommand('mute')
        assert self.coreMock.playback.mute

    def test_next_handler(self):
        dispatcher = lib.CommandDispatcher(self.coreMock,
                                           self.buttonPressEvent)
        dispatcher.handleCommand('next')
        self.coreMock.playback.next.assert_called_with()

    def test_previous_handler(self):
        dispatcher = lib.CommandDispatcher(self.coreMock,
                                           self.buttonPressEvent)
        dispatcher.handleCommand('previous')
        self.coreMock.playback.previous.assert_called_with()

    def test_playpause_handler(self):
        dispatcher = lib.CommandDispatcher(self.coreMock,
                                           self.buttonPressEvent)
        dispatcher.handleCommand('playpause')
        self.coreMock.playback.play.assert_called_with()

        self.coreMock.playback.state = \
            self.WithGet(mopidy.core.PlaybackState.PAUSED)
        dispatcher.handleCommand('playpause')
        self.coreMock.playback.resume.assert_called_with()

        self.coreMock.playback.state = \
            self.WithGet(mopidy.core.PlaybackState.PLAYING)
        dispatcher.handleCommand('playpause')
        self.coreMock.playback.pause.assert_called_with()

    def test_volumedown_handler(self):
        dispatcher = lib.CommandDispatcher(self.coreMock,
                                           self.buttonPressEvent)
        dispatcher.handleCommand('volumedown')
        assert self.coreMock.playback.volume == 45

    def test_volumeup_handler(self):
        dispatcher = lib.CommandDispatcher(self.coreMock,
                                           self.buttonPressEvent)
        dispatcher.handleCommand('volumeup')
        assert self.coreMock.playback.volume == 55


class LircThreadTest(unittest.TestCase):
    def setUp(self):
        pylirc.init = Mock(return_value=True)
        pylirc.nextcode = Mock(return_value=[])
        pylirc.exit = Mock(return_value=True)

    def test_startPyLirc(self):
        thread = lib.LircThread(None)
        thread.start()
        thread.frontendActive = False
        thread.join()

        pylirc.init.assert_called_with('mopidyIRControl', None, 0)

    @patch('mopidy_IRControl.actor.logger')
    def test_handleCommand(self, mock_logger):
        pylirc.nextcode = Mock(return_value=[{'config': 'commandXYZ'}])

        thread = lib.LircThread(None)
        thread.start()
        time.sleep(0.1)
        thread.frontendActive = False
        thread.join()

        assert mock_logger.debug.called
