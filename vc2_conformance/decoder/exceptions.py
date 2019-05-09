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


class TrailingBytesAfterEndOfSequence(ConformanceError):
    """
    Reached an end of sequence marker but there are bytes still remaining in
    the stream.
    """


class BadParseCode(ConformanceError):
    """
    parse_info (10.5.1) has been given an unrecognised parse code.
    
    The exception argument will contain the received parse code.
    """
    
    def __init__(self, parse_code):
        self.parse_code = parse_code
        super(BadParseCode, self).__init__()


class BadParseInfoPrefix(ConformanceError):
    """
    This exception is thrown when the parse_info (10.5.1) prefix value read
    from the bitstream doesn't match the expected value:
    
        The parse info prefix shall be 0x42 0x42 0x43 0x44
    
    The exception argument will contain the read prefix value.
    """
    
    def __init__(self, parse_info_prefix):
        self.parse_info_prefix = parse_info_prefix
        super(BadParseInfoPrefix, self).__init__()


class InconsistentNextParseOffset(ConformanceError):
    """
    This exception is thrown when a ``next_parse_offset`` value encoded in a
    parse_info (10.5.1) block does not match the offset of the next parse_info
    in the stream.
    
    Parameters
    ==========
    parse_info_offset : int
        The bitstream byte offset of the start of the parse_info block
        containing the bad next_parse_offset value.
    next_parse_offset : int
        The offending next_parse_offset value
    true_parse_offset : int
        The actual offset from parse_info_offset of the next parse_info block
        in the stream.
    """
    
    def __init__(self, parse_info_offset, next_parse_offset, true_parse_offset):
        self.parse_info_offset = parse_info_offset
        self.next_parse_offset = next_parse_offset
        self.true_parse_offset = true_parse_offset
        super(InconsistentNextParseOffset, self).__init__()


class MissingNextParseOffset(ConformanceError):
    """
    This exception is thrown when a ``next_parse_offset`` value is given as
    zero but is not optional and must be provided.
    """


class InvalidNextParseOffset(ConformanceError):
    """
    This exception is thrown when a ``next_parse_offset`` value contains a
    value between 1 and 12 (inclusive). All of these byte offsets refer to an
    offset in the stream which is still within the current parse_info block.
    
    The exception argument will contain the offending next_parse_offset value.
    """
    
    def __init__(self, next_parse_offset):
        self.next_parse_offset = next_parse_offset
        super(InvalidNextParseOffset, self).__init__()


class NonZeroNextParseOffsetAtEndOfSequence(ConformanceError):
    """
    This exception is thrown when an end-of-sequence defining parse_info
    (10.5.1) has a non-zero next_parse_offset.
    
    The exception argument will contain the offending next_parse_offset value.
    """
    
    def __init__(self, next_parse_offset):
        self.next_parse_offset = next_parse_offset
        super(NonZeroNextParseOffsetAtEndOfSequence, self).__init__()


class InconsistentPreviousParseOffset(ConformanceError):
    """
    This exception is thrown when the ``previous_parse_offset`` value encoded
    in a parse_info (10.5.1) block does not match the offset of the previous
    parse_info in the stream.
    
    Parameters
    ==========
    last_parse_info_offset : int
        The bitstream byte offset of the start of the previous parse_info
        block.
    previous_parse_offset : int
        The offending previous_parse_offset value
    true_parse_offset : int
        The actual byte offset from the last parse_info to the current one in
        the stream.
    """
    
    def __init__(self, last_parse_info_offset, previous_parse_offset, true_parse_offset):
        self.last_parse_info_offset = last_parse_info_offset
        self.previous_parse_offset = previous_parse_offset
        self.true_parse_offset = true_parse_offset
        super(InconsistentPreviousParseOffset, self).__init__()


class NonZeroPreviousParseOffsetAtStartOfSequence(ConformanceError):
    """
    This exception is thrown when the first parse_info (10.5.1) has a non-zero
    previous_parse_offset.
    
    The exception argument will contain the offending previous_parse_offset value.
    """
    
    def __init__(self, previous_parse_offset):
        self.previous_parse_offset = previous_parse_offset
        super(NonZeroPreviousParseOffsetAtStartOfSequence, self).__init__()
