from __future__ import unicode_literals

import os

# TODO: Comment in if you need to register GStreamer elements below, else
# remove entirely
#import pygst
#pygst.require('0.10')
#import gst
#import gobject

from mopidy import config, ext


__version__ = '0.1.0'


class Extension(ext.Extension):

    dist_name = 'Mopidy-IRControl'
    ext_name = 'IRControl'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['mute'] = config.String()
        schema['next'] = config.String()
        schema['previous'] = config.String()
        schema['playpause'] = config.String()
        schema['stop'] = config.String()
        schema['volumeup'] = config.String()
        schema['volumedown'] = config.String()
        schema['power'] = config.String()
        schema['menu'] = config.String()
        schema['favorites'] = config.String()
        schema['search'] = config.String()
        schema['num0'] = config.String()
        schema['num1'] = config.String()
        schema['num2'] = config.String()
        schema['num3'] = config.String()
        schema['num4'] = config.String()
        schema['num5'] = config.String()
        schema['num6'] = config.String()
        schema['num7'] = config.String()
        schema['num8'] = config.String()
        schema['num9'] = config.String()
        return schema

    def setup(self, registry):
        from .actor import IRControlFrontend
        registry.add('frontend', IRControlFrontend)

    # TODO: Comment in and edit, or remove entirely
    #def get_backend_classes(self):
    #    from .backend import FoobarBackend
    #    return [FoobarBackend]

    # TODO: Comment in and edit, or remove entirely.
    #def get_command(self):
    #    from .commands import FoobarCommand
    #    return FoobarCommand()

    # TODO: Comment in and edit, or remove entirely
    #def register_gstreamer_elements(self):
    #    from .mixer import FoobarMixer
    #    gobject.type_register(FoobarMixer)
    #    gst.element_register(
    #        FoobarMixer, 'foobarmixer', gst.RANK_MARGINAL)
