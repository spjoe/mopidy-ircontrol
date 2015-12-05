from __future__ import unicode_literals

import unittest
import mopidy
import pylirc
import time

from mock import Mock, patch, MagicMock
from mopidy_IRControl import Extension, actor as lib
from mopidy.models import Ref
from pykka.threading import ThreadingFuture

import sys
import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class ExtensionTest(unittest.TestCase):
    def test_get_default_config(self):
        ext = Extension()

        config = ext.get_default_config()

        self.assertIn('[IRControl]', config)
        self.assertIn('enabled = true', config)
        self.assertIn('playlist_uri_template = m3u:playlist{0}.m3u', config)

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

        self.assertIn('playlist_uri_template', schema)
        for i in range(10):
            self.assertIn('num{0}'.format(i), schema)


class FrontendTest(unittest.TestCase):

    def setUp(self):
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
        actor.on_stop()

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

            def __call__(self):
                return self

    def setUp(self):
        self.coreMock = mopidy.core.Core(None, None, [], None)
        self.buttonPressEvent = lib.Event()
        playback = Mock()
        playback.get_state = self.WithGet(mopidy.core.PlaybackState.STOPPED)

        mixer = Mock()
        mixer.get_mute = self.WithGet(False)
        mixer.get_volume = self.WithGet(50)
        mixer.set_mute = MagicMock()
        mixer.set_volume = MagicMock()

        self.coreMock.playback = playback
        self.coreMock.mixer = mixer
        self.coreMock.playlists = Mock()
        self.coreMock.tracklist = Mock()

        self.dispatcher = lib.CommandDispatcher(self.coreMock,
                                                {'playlist_uri_template': 'local:playlist:playlist{0}.m3u'},
                                                self.buttonPressEvent)

    def commandXYZHandler(self):
        self.executed = True

    def test_registerHandler(self):
        self.executed = False
        self.dispatcher.registerHandler('commandXYZ', self.commandXYZHandler)

        self.dispatcher.handleCommand('commandXYZ')
        assert self.executed

    def test_handleCommand(self):
        self.executed = False

        self.dispatcher.handleCommand('commandXYZ')
        assert not self.executed

    def test_default_registered_handler(self):
        self.assertIn('mute', self.dispatcher._handlers)
        self.assertIn('playpause', self.dispatcher._handlers)
        self.assertIn('next', self.dispatcher._handlers)
        self.assertIn('previous', self.dispatcher._handlers)
        self.assertIn('stop', self.dispatcher._handlers)
        self.assertIn('volumedown', self.dispatcher._handlers)
        self.assertIn('volumeup', self.dispatcher._handlers)

        for i in range(10):
            self.assertIn('num{0}'.format(i), self.dispatcher._handlers)

    def test_stop_handler(self):
        self.dispatcher.handleCommand('stop')
        self.coreMock.playback.stop.assert_called_with()

    def test_mute_handler(self):
        self.dispatcher.handleCommand('mute')
        self.coreMock.mixer.set_mute.assert_called_with(True)

    def test_next_handler(self):
        self.dispatcher.handleCommand('next')
        self.coreMock.playback.next.assert_called_with()

    def test_previous_handler(self):
        self.dispatcher.handleCommand('previous')
        self.coreMock.playback.previous.assert_called_with()

    def test_playpause_play_handler(self):
        self.dispatcher.handleCommand('playpause')
        self.coreMock.playback.play.assert_called_with()

    def test_playpause_resume_handler(self):
        self.coreMock.playback.get_state = \
            self.WithGet(mopidy.core.PlaybackState.PAUSED)

        self.dispatcher.handleCommand('playpause')
        self.coreMock.playback.resume.assert_called_with()

    def test_playpause_pause_handler(self):
        self.coreMock.playback.get_state = \
            self.WithGet(mopidy.core.PlaybackState.PLAYING)

        self.dispatcher.handleCommand('playpause')
        self.coreMock.playback.pause.assert_called_with()

    def test_volumedown_handler(self):
        self.dispatcher.handleCommand('volumedown')
        self.coreMock.mixer.set_volume.assert_called_with(45)

    def test_volumeup_handler(self):
        self.dispatcher.handleCommand('volumeup')
        self.coreMock.mixer.set_volume.assert_called_with(55)

    def test_num_handler_no_playlist(self):
        refs = ThreadingFuture()
        refs.set(None)
        self.coreMock.playlists.get_items = MagicMock(return_value=refs)

        self.dispatcher.handleCommand('num0')
        self.coreMock.playlists.get_items.assert_called_with('local:playlist:playlist0.m3u')
        self.assertEqual(0, len(self.coreMock.playback.mock_calls))
        self.assertFalse(0, len(self.coreMock.tracklist.mock_calls))

    def test_num_handler_add_items(self):
        refs = ThreadingFuture()
        refs.set([Ref(uri='track1'), Ref(uri='track2')])
        self.coreMock.playlists.get_items = MagicMock(return_value=refs)

        self.dispatcher.handleCommand('num9')

        self.coreMock.playlists.get_items.assert_called_with('local:playlist:playlist9.m3u')
        self.coreMock.tracklist.add.assert_called_with(uris=['track1', 'track2'])
        self.coreMock.playback.play.assert_called_with()


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

        with patch('select.select') as MockClass:
            MockClass.return_value = ([1], [], [])
            thread = lib.LircThread(None)
            thread.start()
            time.sleep(0.1)
            thread.frontendActive = False
            thread.join()

        assert mock_logger.debug.called
