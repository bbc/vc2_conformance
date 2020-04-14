"""
:py:mod:`vc2_conformance._py2x_compat`: Python 2.x backward compatibility
=========================================================================

This module contains backported or renamed implementations of Python 3.x
standard library routines which are not available in Python 2.x.
"""

__all__ = [
    "zip_longest",  # itertools.zip_longest
    "get_terminal_size",  # shutil.get_terminal_size
    "wraps",  # functools.wraps
    "unwrap",  # inspect.unwrap
    "quote",  # shlex.quote
    "string_types",  # (str, ) in Python 3.x or (str, unicode) in Python 2.x
    "gcd",  # math.gcd
    "zip",  # zip in Python 3.x or itertools.izip in Python 2.x
    "makedirs",  # Adds 'exist_ok' argument to Python 2.x version
]

import os

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


try:
    from shlex import quote
except ImportError:
    from pipes import quote


try:
    string_types = (str, unicode)
except NameError:
    string_types = (str,)

try:
    from math import gcd  # Python >= 3.5
except ImportError:
    from fractions import gcd  # Python < 3.5

try:
    from itertools import izip as zip  # Python 2.x
except ImportError:
    zip = zip

try:
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    makedirs = os.makedirs
except TypeError:

    def makedirs(name, mode=0o777, exist_ok=False):
        if exist_ok and os.path.isdir(name):
            return
        else:
            os.makedirs(name, mode)
