"""
Slices make up the vast majority of a VC-2 bitstream and contain regular
repeated data-structures. Though it is possible to replicate these
data structures in the deserialised format, this is wasteful of memory and CPU
time to the point of making this library unusable. Instead, for any consecutive
sequence of slices in the bitstream, values are accumulated into the various
flat arrays below.

See also :py:module:`slice_arrays_views` for user-friendly view APIs.
"""

from bitarray import bitarray

from vc2_conformance.structured_dict import structured_dict, Value

from vc2_conformance.bitstream.vc2.structured_dicts.slice_arrays_views import (
    SliceArrayParameters,
    LDSliceView,
    HQSliceView,
)

__all__ = [
    "LDSliceArray",
    "HQSliceArray",
]


@structured_dict
class LDSliceArray(object):
    """
    An array of consecutive coded low-delay picture slices (13.5.3.1).
    
    Values in the contained lists are always flat lists of values in bitstream
    order.
    """
    qindex = Value(default_factory=list)
    
    slice_y_length = Value(default_factory=list)
    
    y_transform = Value(default_factory=list)
    y_block_padding = Value(default_factory=list)
    
    c1_transform = Value(default_factory=list)
    c2_transform = Value(default_factory=list)
    c_block_padding = Value(default_factory=list)
    
    # Computed values (used only for view interfaces)
    _parameters = Value(default_factory=SliceArrayParameters)
    _slice_bytes_numerator = Value(default=0)
    _slice_bytes_denominator = Value(default=1)
    
    def iter_slices(self):
        """Iterate over views of all slices."""
        for n in range(len(self.qindex)):
            return self[n]
    
    def __missing__(self, key):
        """
        Get a :py:class:`LDSliceView` of a particular slice. Usage:
        
        * ``a[slice_index]``
        * ``a[sx, sy]``
        """
        if isinstance(key, tuple):
            sx, sy = key
        else:
            sx, sy = self._parameters.from_slice_index(key)
        return LDSliceView(self, sx, sy)


@structured_dict
class HQSliceArray(object):
    """
    An array of consecutive coded high-quality picture slices (13.5.4).
    
    Values in the contained lists are always flat lists of values in bitstream
    order.
    """
    prefix_bytes = Value(default_factory=list)
    
    qindex = Value(default_factory=list)
    
    slice_y_length = Value(default_factory=list)
    y_transform = Value(default_factory=list)
    y_block_padding = Value(default_factory=list)
    
    slice_c1_length = Value(default_factory=list)
    c1_transform = Value(default_factory=list)
    c1_block_padding = Value(default_factory=list)
    
    slice_c2_length = Value(default_factory=list)
    c2_transform = Value(default_factory=list)
    c2_block_padding = Value(default_factory=list)
    
    # Computed values (used only for view interfaces)
    _parameters = Value(default_factory=SliceArrayParameters)
    _slice_prefix_bytes = Value(default=0)
    _slice_size_scaler = Value(default=1)
    
    def iter_slices(self):
        """Iterate over views of all slices."""
        for n in range(len(self.qindex)):
            return self[n]
    
    def __missing__(self, key):
        """
        Get a :py:class:`HQSliceView` of a particular slice. Usage:
        
        * ``a[slice_index]``
        * ``a[sx, sy]``
        """
        if isinstance(key, tuple):
            sx, sy = key
        else:
            sx, sy = self._parameters.from_slice_index(key)
        return HQSliceView(self, sx, sy)
