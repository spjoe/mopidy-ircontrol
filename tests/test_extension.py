from __future__ import unicode_literals

import unittest

from mopidy_IRControl import Extension, actor as lib


class ExtensionTest(unittest.TestCase):
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
        self.config = {'IRControl' : IRconfig}

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
        
    def test_on_start_should_spawn_thread(self):
        ext = Extension()

        actor = lib.IRControlFrontend(self.config, None)
        actor.on_start()
        assert actor.thread != None


class CommandDispatcherTest(unittest.TestCase):
    def setup(self):
        print(__name__, ': TestClass.setup()  - - - - - - - -')

    def teardown(self):
        print(__name__, ': TestClass.teardown() - - - - - - -')
        
    def commandXYZHandler(self):
        self.executed = True

    def test_registerHandler(self):
        self.executed = False
        dispatcher = lib.CommandDispatcher(None)
        
        dispatcher.registerHandler('commandXYZ', self.commandXYZHandler)
        dispatcher.handleCommand('commandXYZ')
        assert self.executed
        
    def test_handleCommand(self):
        self.executed = False
        dispatcher = lib.CommandDispatcher(None)
        dispatcher.handleCommand('commandXYZ')
        assert not self.executed

    def test_default_registered_handler(self):
        dispatcher = lib.CommandDispatcher(None)
        self.assertIn('mute', dispatcher._handlers)
        self.assertIn('playpause', dispatcher._handlers)
        self.assertIn('next', dispatcher._handlers)
        self.assertIn('previous', dispatcher._handlers)
        self.assertIn('stop', dispatcher._handlers)
        self.assertIn('volumedown', dispatcher._handlers)
        self.assertIn('volumeup', dispatcher._handlers)

 
class LircThreadTest(unittest.TestCase):
    def setup(self):
        pass
    
    def test_run(self):
        pass
