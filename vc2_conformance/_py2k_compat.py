"""
:py:mod:`vc2_conformance._py2k_compat`: Python 2.x backward compatibility
=========================================================================

This module contains backported or renamed implementations of Python 3.x
standard library routines which are not available in Python 2.x.
"""

__all__ = [
    "zip_longest",  # itertools.zip_longest
    "get_terminal_size",  # shutil.get_terminal_size
    "wraps",  # functools.wraps
    "unwrap",  # inspect.unwrap
]

import sys


try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest


try:
    from shutil import get_terminal_size
except ImportError:
    # Crude fallback implementation (fixed assumed size)
    def get_terminal_size(fallback=(80, 20)):
        return fallback


if sys.version_info[0] >= 3:
    from functools import wraps
else:
    # In Python 2.x the 'functoos.wraps' function does not set the __wrapped__
    # attribute of wrapped functions. This means introspection tools are unable
    # to find the originally wrapped function.
    from functools import wraps as _wraps
    
    def wraps(wrapped, *args, **kwargs):
        def wrapper(f):
            f = _wraps(wrapped, *args, **kwargs)(f)
            f.__wrapped__ = wrapped
            return f
        return wrapper
    
    wraps = wraps(_wraps)(wraps)


try:
    from inspect import unwrap
except ImportError:
    def unwrap(func, stop=None):
        if stop is None:
            stop = lambda f: False
        
        while hasattr(func, "__wrapped__") and not stop(func):
            func = func.__wrapped__
        
        return func
