"""
:py:mod:`vc2_conformance.decoder.exceptions`
============================================

The following exception types, all inheriting from :py:exc:`ConformanceError`,
are thrown by this module when the provided bitstream is found not to conform
to the standard.
"""


class ConformanceError(Exception):
    """
    Base class for all bitstream conformance failiure exceptions.
    """


class UnexpectedEndOfStream(ConformanceError):
    """
    Reached the end of the stream while attempting to perform read operation.
    """
