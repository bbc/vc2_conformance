r"""
Utility functions for reading the values of :py:class:`BitstreamValue`\ s which
might be out-of-range or throw exceptions.

Useful internally for implementing parameters for higher-order
:py:class:`BitstreamValue`\ s which don't produce crashes if an input parameter
holds an invalid value.
"""

def safe_get_non_negative_integer_value(bitstream_value):
    """
    Returns ``bitstream_value.value`` from the provided
    :py:class:`BitstreamValue`, if the value can be cast to a non-negative
    integer.
    
    Returns 0 if the value is negative, cannot be cast to an integer or if
    reading the value raises an exception.
    """
    try:
        value = int(bitstream_value.value)
        if value >= 0:
            return value
        else:
            return 0
    except:
        return 0


def safe_get_bool(bitstream_value):
    """
    Returns ``bitstream_value.value`` from the provided
    :py:class:`BitstreamValue`, if the value can be cast to a boolean.
    
    Returns False if reading the value raises an exception.
    """
    try:
        return bool(bitstream_value.value)
    except:
        return False


