"""
The :py:mod:`vc2_conformance.py2x_compat` module provides backported
implementations of various functions from Python 3 which are used by this
software.


.. py:function:: zip_longest

    In Python 3.x an alias for :py:func:`itertools.zip_longest`, in Python
    2.x, an alias for ``itertools.izip_longest``.


.. py:function:: get_terminal_size

    In Python 3.x an alias for :py:func:`shutil.get_terminal_size`, in Python
    2.x, a dummy function always returning ``(80, 20)``.


.. py:function:: wraps

    In Python 3.x an alias for :py:func:`functools.wraps`. In Python 2.x, an
    alternative implementation of ``functools.wraps`` which includes the Python
    3.x behaviour of setting the ``__wrapped__`` attribute to allow
    introspection of wrapped functions (see :py:func:`unwrap`).


.. py:function:: unwrap

    In Python 3.x an alias for :py:func:`inspect.unwrap`. In Python 2.x a
    backported implementation of that function. Relies on the backported
    :py:func:`wraps` implementation provided by this module.


.. py:function:: quote

    In Python 3.x an alias for :py:func:`shlex.quote`, in Python
    2.x, an alias for ``pipes.quote``.


.. py:data:: string_types

    A tuple enumerating the native string-like types.  In Python 3.x, ``(str,
    )``, in Python 2.x, ``(str, unicode)``.


.. py:function:: gcd

    In Python 3.x an alias for :py:func:`math.gcd`, in Python
    2.x, an alias for ``fractions.gcd``.


.. py:function:: zip

    In Python 3.x an alias for :py:func:`zip`, in Python
    2.x, an alias for ``itertools.izip``.


.. py:function:: makedirs

    In Python 3.x an alias for :py:func:`os.makedirs`. In Python 2.x, a
    backport of this function which includes the ``exist_ok`` argument.


.. py:function:: FileType

    In Python 3.x an alias for :py:class:`argparse.FileType`. In Python 2.x, a
    wrapper around :py:class:`argparse.FileType` adding support for the
    'encoding' keyword argument when opening with mode "r".

"""

__all__ = [
    "zip_longest",
    "get_terminal_size",
    "wraps",
    "unwrap",
    "quote",
    "string_types",
    "gcd",
    "zip",
    "makedirs",
    "FileType",
]

import os

import sys

import io


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

            def stop(f):
                return False

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


if sys.version_info[0] >= 3:
    from argparse import FileType
else:
    # In Python 2.x, the FileType class does not accept an 'encoding' argument.
    # We reimplement this feature here.
    from argparse import FileType as _FileType

    class FileType(_FileType):
        def __init__(self, mode, *args, **kwargs):
            if mode == "r" and "encoding" in kwargs:
                self._encoding = kwargs.pop("encoding")
            else:
                self._encoding = None
            super(FileType, self).__init__(mode, *args, **kwargs)

        def __call__(self, filename):
            file_obj = super(FileType, self).__call__(filename)
            if self._encoding is None:
                return file_obj
            else:
                # Special case backported for Python 2.x
                return io.open(filename, "r", encoding=self._encoding)
