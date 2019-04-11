"""
"""

from vc2_conformance.math import intlog2

from vc2_conformance.structured_dict import structured_dict, Value

from vc2_conformance.subband_indexing import index_to_subband, subband_to_index

from vc2_conformance._string_utils import indent, table, ellipsise

from vc2_conformance.exp_golomb import signed_exp_golomb_length

__all__ = [
    "SliceArrayParameters",
    "BaseSliceView",
    "ComponentView",
    "ComponentSubbandView",
    "LDSliceView",
    "HQSliceView",
]


@structured_dict
class SliceArrayParameters(object):
    """
    The set of computed parameters which are required to be able to sensibly
    interact with arrays of slice data, along with various methods to compute
    further information (e.g. indices) based on these.
    """
    
    slices_x = Value(default=1)
    slices_y = Value(default=1)
    
    start_sx = Value(default=0)
    start_sy = Value(default=0)
    slice_count = Value(default=1)
    
    dwt_depth = Value(default=0)
    dwt_depth_ho = Value(default=0)
    
    luma_width = Value(default=1)
    luma_height = Value(default=1)
    
    color_diff_width = Value(default=1)
    color_diff_height = Value(default=1)
    
    
    def to_slice_index(self, sx, sy):
        """
        Given a slice coordinate, return the index into this slice array of
        that coordinate.
        """
        index = sx + (sy * self.slices_x)
        
        offset = self.start_sx + (self.start_sy * self.slices_x)
        index -= offset
        
        return index
    
    def from_slice_index(self, slice_index):
        """
        Given an index into this slice array, return the (sx, sy) tuple.
        """
        offset = self.start_sx + (self.start_sy * self.slices_x)
        slice_index += offset
        
        x = slice_index % self.slices_x
        y = slice_index // self.slices_x
        
        return (x, y)
    
    def subband_dimensions(self, w, h, level):
        """
        Compute the width and height of a component subband as defined by
        subband_width() and subband_height() (13.2.3).
        
        Parameters
        ==========
        w, h : int
            The picture component dimensions
        level : int
            The transform level to compute this value for
        """
        scale_w = 1 << (self.dwt_depth_ho + self.dwt_depth)
        scale_h = 1 << self.dwt_depth
        
        pw = scale_w * ( (w+scale_w-1) // scale_w)
        ph = scale_h * ( (h+scale_h-1) // scale_h)
        
        if level == 0:
            subband_width = pw // (1 << (self.dwt_depth_ho + self.dwt_depth))
        else:
            subband_width = pw // (1 << (self.dwt_depth_ho + self.dwt_depth - level + 1))
        
        if level <= self.dwt_depth_ho:
            subband_height = ph // (1 << self.dwt_depth)
        else:
            subband_height = ph // (1 << (self.dwt_depth_ho + self.dwt_depth - level + 1))
        
        return (subband_width, subband_height)
    
    def slice_subband_bounds(self, sx, sy, subband_width, subband_height):
        """
        (13.5.6.2) Compute the (x1, y1, x2, y2) of a slice subband (as found
        using :py:meth:`subband_dimensions`.
        """
        return (
            (subband_width * sx) // self.slices_x,
            (subband_height * sy) // self.slices_y,
            (subband_width * (sx + 1)) // self.slices_x,
            (subband_height * (sy + 1)) // self.slices_y,
        )
    
    def to_coeff_index(self, subband_dimensions,
                       sx, sy,
                       subband_index=0,
                       x=0, y=0):
        """
        Compute the index of the start of a slice's data in a 1D array which stores
        a whole picture's worth of a single component's transform coefficients in
        bitstream order. This is conceptually equivalent to an array with the
        following indices::
        
            component_coeffs[sy][sx][subband_index][y][x]
        
        Where 'sy' and 'sx' are slice coordinates and 'subband_index' is an
        index according to the indexing scheme defined by
        :py:module:`subband_indexing`, and 'y' and 'x' are coordinates within
        the slice and subband selected.
        
        Throws an :py:exc:`IndexError` if any value with the exception of
        slices_y is out of range. This singular exception is allowed to
        accommodate situations where a bitstream (invalidly) contains slices
        past the end of the picture.
        """
        if not (0 <= sx < self.slices_x):
            raise IndexError("slice x-coordinate out of range")
        
        # NB: Explicitly *don't* check range of 'sy'
        
        if not (0 <= subband_index < len(subband_dimensions)):
            raise IndexError("subband index out of range")
        
        offset = 0
        
        # The width/height of the target subband in this slice
        subband_slice_width = None
        subband_slice_height = None
        
        # Offset to current slice and subband (and while we're at it, get the
        # subband slice width/height)
        for cur_subband_index, (subband_width, subband_height) in enumerate(
                subband_dimensions):
            # Top-left ('origin') slice bounds in full picture
            ox1, oy1, ox2, oy2 = self.slice_subband_bounds(
                self.start_sx, self.start_sy,
                subband_width, subband_height,
            )
            
            # Target slice bounds in full picture
            x1, y1, x2, y2 = self.slice_subband_bounds(
                sx, sy,
                subband_width, subband_height,
            )
            # Say we're in slice sx=3, sy=2, then the slice out of the current
            # subband will look like:
            #
            #     +---+---+---+---+---+---+
            #     |   |   |   |   |   |   |
            #     +---+---+---+---+---+---+
            #     |   |   |   |   |   |   |
            #     +---+---+---+---+---+---+
            #     |   |   |   |3,2|   |   |
            #     +---+---+---+---+ - + - +
            #     |   |   |   |   |   |   |
            #     +---+---+---+---+---+---+
            #     |   |   |   |   |   |   |
            #     +---+---+---+---+---+---+
            #
            # The offset beforehand, therefore is
            #
            #              |<--- subband_width --->|
            #              |                       |
            #
            #              +-----------------------+  ------------
            #              |#######################|   A        A
            #              |#######################|   | y1     |
            #              |#######################|   V        |
            #         -+-  +-----------+---+---+---+  ---       |
            #    y2-y1 |   |@@@@@@@@@@@|3,2'   '   '            subband_height
            #         -+-  +---+---+---+ - + - + - +            |
            #              '   '   '   '   '   '   '            |
            #              + - + - + - + - + - + - +            |
            #              '   '   '   '   '   '   '            V
            #              + - + - + - + - + - + - +  ------------
            #
            #              |           |
            #              |<--- x1 -->|
            #
            # Which consists of all of the slices above the current slice:
            #
            #    area '#' = subband_width * y1
            #
            # Plus all of the area to the left of the slice in the same row
            #
            #    area '@' = x1 * (y2 - y1)
            #
            # Using the above we get the offset to the top-left corner of the
            # current subband slice as:
            #
            #     (subband_width * y1) + (x1 * (y2 - y1))
            #
            # Likewise, the next offset after the bottom-right corner of the
            # current subband slice will be
            #
            #     (subband_width * y1) + (x2 * (y2 - y1))
            
            # Compensate for offset start slice coordinates
            offset -= (oy1 * subband_width) + (ox1 * (oy2 - oy1))
            
            if cur_subband_index >= subband_index:
                offset += (y1 * subband_width) + (x1 * (y2 - y1))
            else:
                offset += (y1 * subband_width) + (x2 * (y2 - y1))
            
            if cur_subband_index == subband_index:
                subband_slice_width = x2 - x1
                subband_slice_height = y2 - y1
        
        # NB: When large numbers of slices and/or transform levels are used, some
        # subbands may have zero width/height in some slices.
        if not (subband_slice_width == x == 0 or 0 <= x < subband_slice_width):
            raise IndexError("slice value x-coordinate index out of range")
        if not (subband_slice_height == y == 0 or 0 <= y < subband_slice_height):
            raise IndexError("slice value y-coordinate index out of range")
        
        # Offset to required coordinate within selected slice and subband
        offset += (y * subband_slice_width) + x
        
        return offset
    
    @property
    def num_subband_levels(self):
        """The number of subband levels."""
        return 1 + self.dwt_depth_ho + self.dwt_depth
    
    @property
    def num_subbands(self):
        """The total number of subbands."""
        return 1 + self.dwt_depth_ho + (self.dwt_depth * 3)
    
    @property
    def luma_subband_dimensions(self):
        """
        A tuple ((w, h), ...) of subband dimensions for the luminance picture
        component.
        """
        return tuple(
            self.subband_dimensions(
                w=self.luma_width,
                h=self.luma_height,
                level=level,
            )
            for level in range(self.num_subband_levels)
            for _ in range(1 if level < (1 + self.dwt_depth_ho) else 3)
        )
    
    @property
    def color_diff_subband_dimensions(self):
        """
        A tuple ((w, h), ...) of subband dimensions for the color difference
        picture components.
        """
        return tuple(
            self.subband_dimensions(
                w=self.color_diff_width,
                h=self.color_diff_height,
                level=level,
            )
            for level in range(self.num_subband_levels)
            for _ in range(1 if level < (1 + self.dwt_depth_ho) else 3)
        )


class SliceValueView(object):
    """A descriptor for accessing values from a slice."""
    
    def __init__(self, name):
        self._name = name
    
    def __get__(self, obj, type=None):
        return getattr(obj._slice_array, self._name)[
            obj._slice_array._parameters.to_slice_index(obj._sx, obj._sy)
        ]
    
    def __set__(self, obj, value):
        getattr(obj._slice_array, self._name)[
            obj._slice_array._parameters.to_slice_index(obj._sx, obj._sy)
        ] = value


class BaseSliceView(object):
    """
    A view for accessing the values of a single slice.
    """
    
    def __init__(self, slice_array, sx, sy):
        self._slice_array = slice_array
        self._sx = sx
        self._sy = sy
    
    @property
    def sx(self):
        return self._sx
    
    @property
    def sy(self):
        return self._sy
    
    @property
    def slice_index(self):
        return self._slice_array._parameters.to_slice_index(self._sx, self._sy)
    
    qindex = SliceValueView("qindex")
    
    @property
    def y_transform(self):
        return ComponentView(self._slice_array, "y", self._sx, self._sy)
    
    @property
    def c1_transform(self):
        return ComponentView(self._slice_array, "c1", self._sx, self._sy)
    
    @property
    def c2_transform(self):
        return ComponentView(self._slice_array, "c2", self._sx, self._sy)
    
    def __repr__(self):
        return "<{} sx={} sy={}>".format(
            self.__class__.__name__,
            self._sx,
            self._sy,
        )


class LDSliceView(BaseSliceView):
    """
    A view for accessing the values of a single low-delay slice.
    """
    
    slice_y_length = SliceValueView("slice_y_length")
    
    y_block_padding = SliceValueView("y_block_padding")
    c_block_padding = SliceValueView("c_block_padding")
    
    @property
    def length(self):
        """The total length of this slice in bits."""
        # Based on (13.5.3.2) slice_bytes. Return the length of a low-delay
        # picture slice.
        slice_number = (
            self._sy *
            self._slice_array._parameters.slices_x
        ) + self._sx
        slice_bytes = (
            ((slice_number + 1) * self._slice_array._slice_bytes_numerator) //
            self._slice_array._slice_bytes_denominator
        )
        slice_bytes -= (
            (slice_number * self._slice_array._slice_bytes_numerator) //
            self._slice_array._slice_bytes_denominator
        )
        return 8 * slice_bytes
    
    @property
    def header_length(self):
        """The total length of the qindex and slice_y_length fields."""
        return 7 + intlog2(self.length - 7)
    
    @property
    def true_slice_y_length(self):
        """
        The length of the luminance bounded block in this slice (in
        bits).
        
        May differ from :py:attr:`slice_y_length` if the specified length is
        (erroneously) larger than the slice.
        """
        max_slice_y_length = self.length - self.header_length
        return min(max_slice_y_length, self.slice_y_length)
    
    @property
    def slice_c_length(self):
        """
        The computed length of the color-difference bounded block in this slice
        (in bits).
        """
        return self.length - self.header_length - self.true_slice_y_length
    
    def __str__(self):
        out = [
            "qindex: {}".format(self.qindex),
            "slice_y_length: {}".format(self.slice_y_length),
            "y_transform:",
            indent(component_views_str(
                self.true_slice_y_length,
                str(self.y_block_padding),
                self.y_transform,
            )),
            "c1_transform & c2_transform:",
            indent(component_views_str(
                self.slice_c_length,
                str(self.c_block_padding),
                self.c1_transform,
                self.c2_transform,
            )),
        ]
        
        return "ld_slice(sx={}, sy={}):\n{}".format(
            self._sx,
            self._sy,
            indent("\n".join(out)),
        )


class HQSliceView(BaseSliceView):
    """
    A view for accessing the values of a single high-quality slice.
    """
    
    prefix_bytes = SliceValueView("prefix_bytes")
    
    slice_y_length = SliceValueView("slice_y_length")
    slice_c1_length = SliceValueView("slice_c1_length")
    slice_c2_length = SliceValueView("slice_c2_length")
    
    y_block_padding = SliceValueView("y_block_padding")
    c1_block_padding = SliceValueView("c1_block_padding")
    c2_block_padding = SliceValueView("c2_block_padding")
    
    def __str__(self):
        out = (
            [
                "prefix_bytes: {}".format(
                    " ".join(map(Hex(2), bytearray(self.prefix_bytes))))
            ]
            if self._slice_array._parameters.slice_prefix_bytes != 0 else
            []
        ) + [
            "qindex: {}".format(self.qindex),
            "slice_y_length: {}".format(self.slice_y_length),
            "y_transform:",
            indent(component_views_str(
                self.true_slice_y_length,
                self.y_block_padding,
                self.y_transform,
            )),
            "slice_c1_length: {}".format(self.slice_c1_length),
            "c1_transform:",
            indent(component_views_str(
                self.true_slice_c1_length,
                self.c1_block_padding,
                self.c1_transform,
            )),
            "slice_c2_length: {}".format(self.slice_c2_length),
            "c2_transform:",
            indent(component_views_str(
                self.true_slice_c2_length,
                self.c2_block_padding,
                self.c2_transform,
            )),
        ]
        
        return "hq_slice(sx={}, sy={}):\n{}".format(
            self._sx,
            self._sy,
            indent("\n".join(out)),
        )


class ComponentView(object):
    """
    A view for accessing the component transform values of a slice in a
    slice array.
    """
    
    def __init__(self, slice_array, component, sx, sy):
        """
        Parameters
        ==========
        slice_array : :py:class:`LDSliceArray` or :py:class:`HQSliceArray`
        component : "y", "c1" or "c2"
        sx, sy : int
        """
        self._slice_array = slice_array
        self._component = component
        self._sx = sx
        self._sy = sy
    
    @property
    def component(self):
        return self._component
    
    def __getitem__(self, key):
        """
        Access the subband data for this component. Indices should be either
        subband indices (a single integer) or a two-part index consisting of a
        level (int) and subband name (e.g. "HL") as accepted by
        :py:func:`SubbandArray.subband_to_index`.
        
        The following indexing styles are supported:
        * ``v[subband_index]``
        * ``v[level, subband_name]`` (e.g. ``v[2, "HL"]``)
        """
        if isinstance(key, tuple):
            level, subband = key
            key = subband_to_index(
                level,
                subband,
                self._slice_array._parameters.dwt_depth,
                self._slice_array._parameters.dwt_depth_ho,
            )
        
        return ComponentSubbandView(
            self._slice_array,
            self._component,
            self._sx,
            self._sy,
            key,
        )
    
    def __len__(self):
        return self._slice_array._parameters.num_subbands
    
    def __iter__(self):
        """
        Iterate over :py:class:`ComponentSubbandView` views of the subbands for
        this component.
        """
        for subband_index in range(self._slice_array._parameters.num_subbands):
            yield self[subband_index]
    
    def items(self):
        """
        Iterator producing (level, subband_name, component_subband_view) tuples
        for each :py:class:`ComponentSubbandView` instance.
        """
        for i, transform_value in enumerate(self):
            level, subband = index_to_subband(
                i,
                self._slice_array._parameters.dwt_depth,
                self._slice_array._parameters.dwt_depth_ho,
            )
            yield (level, subband, transform_value)
    
    def __repr__(self):
        return "<{} sx={} sy={} slice_index={}>".format(
            self.__class__.__name__,
            self._sx,
            self._sy,
            self._slice_index,
        )


class ComponentSubbandView(object):
    """
    A view for accessing the transform values of a particular subband and slice
    in a slice array.
    """
    
    def __init__(self, slice_array, component, sx, sy, subband_index):
        """
        Parameters
        ==========
        slice_array : :py:class:`LDSliceArray` or :py:class:`HQSliceArray`
        component : "y", "c1" or "c2"
        sx, sy : int
        subband_index : int
        """
        self._slice_array = slice_array
        self._component = component
        self._sx = sx
        self._sy = sy
        self._subband_index = subband_index
        
        if self._component == "y":
            self._data = self._slice_array.y_transform
            self._subband_dimensions = self._slice_array._parameters.luma_subband_dimensions
        elif self._component == "c1":
            self._data = self._slice_array.c1_transform
            self._subband_dimensions = self._slice_array._parameters.color_diff_subband_dimensions
        elif self._component == "c2":
            self._data = self._slice_array.c2_transform
            self._subband_dimensions = self._slice_array._parameters.color_diff_subband_dimensions
        else:
            raise ValueError("Invalid component.")
    
    @property
    def subband(self):
        return index_to_subband(
            self._subband_index,
            self._slice_array._parameters.dwt_depth,
            self._slice_array._parameters.dwt_depth_ho,
        )
    
    @property
    def subband_index(self):
        return self._subband_index
    
    @property
    def bounds(self):
        """
        The (x1, y1, x2, y2) bounds (within its component) of this subband's
        coefficient data.
        """
        return self._slice_array._parameters.slice_subband_bounds(
            self._sx, self._sy,
            *self._subband_dimensions[self._subband_index]
        )
    
    @property
    def dimensions(self):
        """The (width, height) of this slice's subband data."""
        x1, y1, x2, y2 = self.bounds
        return (x2 - x1, y2 - y1)
    
    def __len__(self):
        w, h = self.dimensions
        return w * h
    
    def _normalise_key(self, key):
        if isinstance(key, tuple):
            x, y = key
        else:
            width, height = self.dimensions
            x = key % width
            y = key // width
            
        return self._slice_array._parameters.to_coeff_index(
            self._subband_dimensions,
            self._sx,
            self._sy,
            self._subband_index,
            x,
            y,
        )
    
    @property
    def start_index(self):
        """
        The starting index of the coefficient values for this component, slice
        and subband.
        """
        return self._normalise_key((0, 0))
    
    @property
    def end_index(self):
        """
        The ending index (exclusive) of the coefficient values for this
        component, slice and subband.
        """
        return self.start_index + len(self)
    
    def __getitem__(self, key):
        """
        Index into the individual transform values within the subband.
        
        The following indexing styles are supported:
        * ``v[x, y]``
        * ``v[index]``
        """
        key = self._normalise_key(key)
        return self._data[key]
    
    def __setitem__(self, key, value):
        key = self._normalise_key(key)
        self._data[key] = value
    
    def __iter__(self):
        """Iterate over the individual transform values."""
        return iter(self._data[self.start_index:self.end_index])
    
    def items(self):
        """
        Iterator producing (x, y, transform_value) tuples for individual
        transform values.
        """
        width = self.dimensions[0]
        for i, transform_value in enumerate(self):
            yield (i%width, i//width, transform_value)
    
    def __repr__(self):
        try:
            x1, y1, x2, y2 = self.bounds
        except:
            # In case of out-of-range parameters
            x1 = y1 = x2 = y2 = "?"
        
        return "<{} sx={} sy={} slice_index={} x=[{}, {}) y=[{}, {})>".format(
            self.__class__.__name__,
            self._sx,
            self._sy,
            self._slice_index,
            x1, y1,
            x2, y2,
        )


def component_views_str(block_length, block_padding, *component_views):
    r"""
    Generate a string representation of a set of interleaved
    :py:class:`ComponentView`\ s. For use as a basis for producing string
    representations of slice views.
    
    Parameters
    ==========
    block_length : int
        The length of the bounded block these component values reside in
    block_padding : bitarray
        The padding value for any unused bits in the block.
    component_views : :py:class:`ComponentView`
        The components whose coefficients are interleaved. If multiple
        views are provided, these must have exactly the same number of
        subbands and have the same subband dimensions.
    """
    out = []
    
    # Create table of coefficients
    bits_remaining = block_length
    for component_subband_views in zip(*component_views):
        w, h = component_subband_views[0].dimensions
        
        # Skip slices without any coefficients
        if w*h == 0:
            continue
        
        level, subband = component_subband_views[0].subband
        out.append("Level {}, {}:".format(level, subband))
        
        table_values = [[None]*w for _ in range(h)]
        for i, values in enumerate(zip(*component_subband_views)):
            # Add a '*' to any values past the end of the bounded block
            strings = []
            for value in values:
                bits_remaining -= signed_exp_golomb_length(value)
                if bits_remaining >= 0:
                    strings.append(str(value))
                else:
                    strings.append("{}*".format(value))
            
            # Combine the values into a single string
            if len(strings) == 1:
                string = strings[0]
            else:
                string = "({})".format(", ".join(strings))
            
            table_values[i//w][i%w] = string
        out.append(indent(table(table_values)))
    
    # Add padding bits
    if bits_remaining > 0:
        out.append("{} unused bit{}: 0b{}".format(
            bits_remaining,
            "s" if bits_remaining != 1 else "",
            # Mask off only the bits actually used
            ellipsise(block_padding.to01()),
        ))
    
    return "\n".join(out)
