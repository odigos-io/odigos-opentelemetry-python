import sys
class ExitHooks(object):
    """
    The ExitHooks class intercepts program exits to capture the reason for termination.
    It hooks into sys.exit to record exit codes
    """    
    def __init__(self):
        self.exit_code = None
        self.exception = None

    def hook(self):
        self._orig_exit = sys.exit
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc