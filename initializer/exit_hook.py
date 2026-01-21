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
        # Skip REPL and terminals
        if sys.flags.interactive or hasattr(sys, "ps1"):
            return
        self._orig_exit = sys.exit
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc
