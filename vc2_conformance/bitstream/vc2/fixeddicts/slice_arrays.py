"""
Slices make up the vast majority of a VC-2 bitstream and contain regular
repeated data-structures. Though it is possible to replicate these
data structures in the deserialised format, this is wasteful of memory and CPU
time to the point of making this library unusable. Instead, for any consecutive
sequence of slices in the bitstream, values are accumulated into the various
flat arrays below.

See also :py:module:`slice_arrays_views` for user-friendly view APIs.
"""

from vc2_conformance.fixeddict import fixeddict, Entry

from vc2_conformance.bitstream.vc2.fixeddicts.slice_arrays_views import (
    SliceArrayParameters,
    LDSliceView,
    HQSliceView,
)

__all__ = [
    "LDSliceArray",
    "HQSliceArray",
]

_LDSliceArray = fixeddict(
    "_LDSliceArray",
    Entry("qindex", default_factory=list),
    
    Entry("slice_y_length", default_factory=list),
    
    Entry("y_transform", default_factory=list),
    Entry("y_block_padding", default_factory=list),
    
    Entry("c1_transform", default_factory=list),
    Entry("c2_transform", default_factory=list),
    Entry("c_block_padding", default_factory=list),
    
    # Computed values (used only for view interfaces)
    Entry("_parameters", default_factory=SliceArrayParameters),
    Entry("_slice_bytes_numerator", default=0),
    Entry("_slice_bytes_denominator", default=1),
)

class LDSliceArray(_LDSliceArray):
    """
    An array of consecutive coded low-delay picture slices (13.5.3.1).
    
    Values in the contained lists are always flat lists of values in bitstream
    order.
    """
    
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
            sx, sy = self["_parameters"].from_slice_index(key)
        return LDSliceView(self, sx, sy)
    
    def __str__(self):
        return "<{} with {} slice{}>".format(
            self.__class__.__name__,
            len(self["qindex"]),
            "s" if len(self["qindex"]) != 1 else "",
        )

_HQSliceArray = fixeddict(
    "_HQSliceArray",
    Entry("prefix_bytes", default_factory=list),
    
    Entry("qindex", default_factory=list),
    
    Entry("slice_y_length", default_factory=list),
    Entry("slice_c1_length", default_factory=list),
    Entry("slice_c2_length", default_factory=list),
    
    Entry("y_transform", default_factory=list),
    Entry("c1_transform", default_factory=list),
    Entry("c2_transform", default_factory=list),
    
    Entry("y_block_padding", default_factory=list),
    Entry("c1_block_padding", default_factory=list),
    Entry("c2_block_padding", default_factory=list),
    
    # Computed values (used only for view interfaces)
    Entry("_parameters", default_factory=SliceArrayParameters),
    Entry("_slice_prefix_bytes", default=0),
    Entry("_slice_size_scaler", default=1),
)

class HQSliceArray(_HQSliceArray):
    """
    An array of consecutive coded high-quality picture slices (13.5.4).
    
    Values in the contained lists are always flat lists of values in bitstream
    order.
    """
    
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
            sx, sy = self["_parameters"].from_slice_index(key)
        return HQSliceView(self, sx, sy)
    
    def __str__(self):
        return "<{} with {} slice{}>".format(
            self.__class__.__name__,
            len(self["qindex"]),
            "s" if len(self["qindex"]) != 1 else "",
        )
