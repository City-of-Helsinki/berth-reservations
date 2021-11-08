import functools
import pdb
import traceback


def debug_on_exception(func):
    """
    launch debugger on exception. Useful while debugging.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            pdb.post_mortem()
            raise

    return wrapper
