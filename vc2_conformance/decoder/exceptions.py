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


class SequenceHeaderChangedMidSequence(ConformanceError):
    """
    This exception is thrown when a sequence_header (11.1) appears in the
    stream which does not match the previous sequence header byte-for-byte.
    
    Parameters
    ==========
    last_sequence_header_offset : int
    last_sequence_header_bytes : :py:class:`bytearray`
        The bitstream byte-offset and raw bytes for the previous
        sequence_header in the stream.
    this_sequence_header_offset : int
    this_sequence_header_bytes : :py:class:`bytearray`
        The bitstream byte-offset and raw bytes for the offending
        sequence_header in the stream.
    """
    
    def __init__(self,
                 last_sequence_header_offset,
                 last_sequence_header_bytes,
                 this_sequence_header_offset,
                 this_sequence_header_bytes):
        self.last_sequence_header_offset = last_sequence_header_offset
        self.last_sequence_header_bytes = last_sequence_header_bytes
        self.this_sequence_header_offset = this_sequence_header_offset
        self.this_sequence_header_bytes = this_sequence_header_bytes
        super(SequenceHeaderChangedMidSequence, self).__init__()


class ProfileChanged(ConformanceError):
    """
    This exception is thrown when a parse_parameters (11.2) appears in the
    stream which contains a profile which differs from a previous
    parse_parameters header in the stream.
    
    Parameters
    ==========
    last_parse_parameters_offset : int
    last_profile : int
    this_parse_parameters_offset : int
    this_profile : int
    """
    
    def __init__(self,
                 last_parse_parameters_offset,
                 last_profile,
                 this_parse_parameters_offset,
                 this_profile):
        self.last_parse_parameters_offset = last_parse_parameters_offset
        self.last_profile = last_profile
        self.this_parse_parameters_offset = this_parse_parameters_offset
        self.this_profile = this_profile
        super(ProfileChanged, self).__init__()


class LevelChanged(ConformanceError):
    """
    This exception is thrown when a parse_parameters (11.2) appears in the
    stream which contains a level which differs from a previous
    parse_parameters header in the stream.
    
    Parameters
    ==========
    last_parse_parameters_offset : int
    last_level : int
    this_parse_parameters_offset : int
    this_level : int
    """
    
    def __init__(self,
                 last_parse_parameters_offset,
                 last_level,
                 this_parse_parameters_offset,
                 this_level):
        self.last_parse_parameters_offset = last_parse_parameters_offset
        self.last_level = last_level
        self.this_parse_parameters_offset = this_parse_parameters_offset
        self.this_level = this_level
        super(LevelChanged, self).__init__()


class BadProfile(ConformanceError):
    """
    parse_parameters (11.2.1) has been given an unrecognised profile number.
    
    The exception argument will contain the received profile number.
    """
    
    def __init__(self, profile):
        self.profile = profile
        super(BadProfile, self).__init__()


class BadLevel(ConformanceError):
    """
    parse_parameters (11.2.1) has been given an unrecognised level number.
    
    The exception argument will contain the received level number.
    """
    
    def __init__(self, level):
        self.level = level
        super(BadLevel, self).__init__()


class GenericInvalidSequence(ConformanceError):
    """
    The sequence of data units in the VC-2 sequence does not match the generic
    sequence structure specified in (10.4.1) 
    
    The offending parse code will be given in :py:attr:`parse_code` if it does
    not match the expected sequence structure. If the sequence ends prematurely
    ``None`` will be passed instead.
    
    :py:attr:`expected_parse_codes` enumerates the parse codes which would have
    been allowed.  This may be ``None`` if any parse code would be permitted.
    
    :py:attr:`expected_end` is True if it would have been acceptable for the
    sequence to have ended at this point.
    """
    
    def __init__(self, parse_code, expected_parse_codes, expected_end):
        self.parse_code = parse_code
        self.expected_parse_codes = expected_parse_codes
        self.expected_end = expected_end
        super(GenericInvalidSequence, self).__init__()


class LevelInvalidSequence(ConformanceError):
    """
    The sequence of data units in the VC-2 sequence does not match the
    sequence structure specified for the current level (C.3).
    
    The offending parse code will be given in :py:attr:`parse_code` if it does
    not match the expected sequence structure. If the sequence ends prematurely
    ``None`` will be passed instead.
    
    :py:attr:`expected_parse_codes` enumerates the parse codes which would have
    been allowed.  This may be ``None`` if any parse code would be permitted.
    
    :py:attr:`expected_end` is True if it would have been acceptable for the
    sequence to have ended at this point.
    """
    
    def __init__(self, parse_code, expected_parse_codes, expected_end):
        self.parse_code = parse_code
        self.expected_parse_codes = expected_parse_codes
        self.expected_end = expected_end
        super(LevelInvalidSequence, self).__init__()


class ParseCodeNotAllowedInProfile(ConformanceError):
    """
    The parse code encountered is not allowed in the current profile (C.2).
    
    The offending parse_code and profile combination will be provided in
    :py:attr:`parse_code` and :py;attr:`profile`.
    """
    
    def __init__(self, parse_code, profile):
        self.parse_code = parse_code
        self.profile = profile
        super(ParseCodeNotAllowedInProfile, self).__init__()
