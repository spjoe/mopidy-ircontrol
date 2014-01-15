import pykka

from mopidy.core import CoreListener


class IRControlFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, core):
        super(IRControlFrontend, self).__init__()
        self.core = core

    # Your frontend implementation
