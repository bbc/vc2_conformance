"""
General-purpose compound :py:class:`BitstreamValue` types for building
composite types.
"""

from vc2_conformance.bitstream import (
    BitstreamValue,
    ensure_bitstream_value,
    FunctionValue,
)

from vc2_conformance.bitstream._util import (
    indent,
    concat_strings,
    concat_labelled_strings,
    concat_tabular_strings,
)

from vc2_conformance.bitstream._safe_get import (
    safe_get_non_negative_integer_value,
)


__all__ = [
    "Concatenation",
    "LabelledConcatenation",
    "Array",
    "RectangularArray",
    "SubbandArray",
]


class Concatenation(BitstreamValue):
    r"""
    Compound value. A concatenation of a tuple of :py:class:`BitstreamValue`\
    s.
    
    The contained :py:class:`BitstreamValue` objects can be accessed either
    using :py:attr:`value` (as usual) or by indexing into this object. That is,
    the following are equivalent::
    
        c = Concatenation(b1, b2, b3)
        asssert c.value[0] is b1
        asssert c.value[1] is b2
        asssert c.value[2] is b3
        
        c = Concatenation(b1, b2, b3)
        asssert c[0] is b1
        asssert c[1] is b2
        asssert c[2] is b3
    
    In practice, :py:class:`LabelledConcatenation` may be preferable to this
    basic class.
    """
    
    def __init__(self, *values):
        """
        Parameters
        ==========
        values : :py:class:`BitstreamValue`
            The bitstream values to be concatenated (in order).
        """
        self._value = values
        super(Concatenation, self).__init__()
        
        # NB: Validation is done last, so that internal members are populated
        # allowing __repr__ work (which may be printed in tracebacks).
        self._validate(self._value)
        
        # If the contained values change, this container will notify a change
        # too
        for value in self._value:
            value._notify_on_change(self)
    
    def _dependency_changed(self, _):
        self._changed()
    
    def _validate(self, value):
        if not all(isinstance(v, BitstreamValue) for v in value):
            raise ValueError(
                "All concatenation components must be BitstreamValues.")
    
    @property
    def value(self):
        r"""
        A tuple of :py:class:`BitstreamValue`\ s contained by this
        :py:class:`Concatenation`.
        """
        return self._value
    
    @property
    def length(self):
        if any(v.length is None for v in self._value):
            return None
        else:
            return sum(v.length for v in self._value)
    
    @property
    def bits_past_eof(self):
        if any(v.bits_past_eof is None for v in self._value):
            return None
        else:
            return sum(v.bits_past_eof for v in self._value)
    
    def read(self, reader):
        with self._coalesce_change_notifications():
            self._offset = reader.tell()
            for v in self._value:
                v.read(reader)
    
    def write(self, writer):
        with self._coalesce_change_notifications():
            self._offset = writer.tell()
            for v in self._value:
                v.write(writer)
    
    def __getitem__(self, key):
        """Shorthand for ``concatenation.value[key]``"""
        return self._value[key]
    
    def __repr__(self):
        return "<{}>".format(self.__class__.__name__)
    
    def __str__(self):
        s = concat_strings([str(v) for v in self._value], ", ")
        if "\n" in s:
            return s
        else:
            return "({})".format(s)


class LabelledConcatenation(Concatenation):
    """
    Like :py:class:`Concatenation` except with labelled entries.
    
    In terms of its bitstream formatting/behaviour, this is identical to
    Concatenation. The principle difference are:
    
    * The ability to look-up values by name (not just index), e.g.
      ``concat["foo"]``
    * A richer str() representation with headings and labels.
    """
    
    def __init__(self, *names_values):
        """
        Parameters
        ==========
        names_values : (str, :py:class:`BitstreamValue`) or :py:class:`BitstreamValue` or str or None
            A series of entries to include in this concatenation.

            * If a (str, :py:class:`BitstreamValue`) tuple, this gives a value
              and its corresponding label string (which must be unique).
            
            * If just a :py:class:`BitstreamValue`, this gives a value to include
              without a label.
            
            * If a string, this specifies a heading to include in the ``str()``
              representation. Also increases the indent level for all following
              values in the string.
            
            * If None, reduces the indentation level for all following levels in
              the ``str`` representation..
        """
        self._names_values = names_values
        
        # NB: Pass-on just the non-label parts as the concatenation values
        super(LabelledConcatenation, self).__init__(*(
            nv if isinstance(nv, BitstreamValue) else nv[1]
            for nv in names_values
            if nv is not None and not isinstance(nv, str)
        ))
    
    @property
    def value(self):
        """The values in the concatenation (see constructor arguments)."""
        return self._names_values
    
    def __getitem__(self, key):
        r"""
        Get a :py:class:`BitstreamValue` by either index or name.
        
        If an (numerical) index is given, this will be looked up according to
        the order the :py:class:`BitstreamValue`\ s appear in the bitstream. If
        a (string) name is given, the value with the specified name will be
        returned.
        """
        if isinstance(key, str):
            # Get by name
            for nv in self._names_values:
                if nv is None:
                    continue  # An empty line
                elif isinstance(nv, str):
                    continue  # A heading
                elif isinstance(nv, BitstreamValue):
                    continue  # An unlabelled value
                else:
                    name, value = nv
                    if name == key:
                        return value
            raise KeyError(key)
        else:
            # Get by index
            return self._value[key]
    
    def __repr__(self):
        return "<{}>".format(self.__class__.__name__)
    
    def __str__(self):
        body = []
        
        space = "  "
        
        indent_level = 0
        for nv in self._names_values:
            if nv is None:
                indent_level = max(0, indent_level - 1)
            elif isinstance(nv, str):
                body.append(indent(nv, space*indent_level))
                indent_level += 1
            elif isinstance(nv, BitstreamValue):
                string = str(nv)
                if string:
                    body.append(indent(string, space*indent_level))
            else:
                name, value = nv
                string = str(value)
                if string:
                    if string.startswith("{}:".format(name)):
                        # Special case: if the contained string is
                        # self-identifying, don't add another copy of the
                        # label!
                        body.append(indent(string, space*indent_level))
                    elif "\n" in string:
                        # Case: multi-line string (show indented below label)
                        string = "{}:\n{}".format(name, indent(string, space))
                        body.append(indent(string, space*indent_level))
                    else:
                        # Case: single-line string
                        string = "{}: {}".format(name, string)
                        body.append(indent(string, space*indent_level))
        
        return "\n".join(body)


class Array(Concatenation):
    r"""
    Compound value. An array of :py:class:`BitstreamValue`\ s.
    
    The contained :py:class:`BitstreamValue` objects can be accessed either
    using :py:attr:`value[index]` or by indexing into this object. The
    :py:attr:`value` of this object will be a :py:class:`tuple` of
    :py:class:`BitstreamValue`\ s.
    
    Example usage:
        
        >>> a = Array(UInt, 4)
        
        >>> # Array values are set like so
        >>> a[0].value = 10
        >>> a[1].value = 20
        >>> a[2].value = 30
        >>> a[3].value = 40
        >>> str(a)
        10 20 30 40
        
        >>> # The number of values in the array is changed using the num_values
        >>> # property
        >>> a.num_values = 10
        >>> str(a)
        10 20 30 40 0 0 0 0 0 0
        >>> a.num_values = 2
        >>> str(a)
        10 20
    """
    
    def __init__(self, value_constructor, num_values=0, pass_index=False):
        r"""
        Parameters
        ==========
        value_constructor : function() -> :py:class:`BitstreamValue`
            A function which returns new :py:class:`BitstreamValue`\ s. Used to
            populate new entries in the array when ``num_values`` is enlarged
            or during initial construction. (See also: ``pass_index``.)
        num_values : int or :py:class:`BitstreamValue`
            The number of :py:class:`BitstreamValue`\ s in the array.
            
            If a :py:class:`BitstreamValue` is passed, whenever this value
            changes, the length of the array will be changed. Excess values
            will be dropped and new values will be constructed as required,
            retaining as many of the existing array elments as possible.
        pass_index : bool
            If True, the value_constructor function will be passed the index of
            the array element being constructed. If False (the default) no
            argument will be passed.
        """
        self.value_constructor = value_constructor
        self.pass_index = pass_index
        
        self._num_values_bitstream_value = ensure_bitstream_value(num_values)
        self._num_values_bitstream_value._notify_on_change(self)
        
        super(Array, self).__init__()
        
        # Trigger the initial population of this array
        self._dependency_changed(self.num_values_bitstream_value)
    
    @property
    def num_values(self):
        """
        The length of this :py:class:`Array`. See also
        :py:attr:`num_values_bitstream_value`.
        """
        return safe_get_non_negative_integer_value(self._num_values_bitstream_value)
    
    @property
    def num_values_bitstream_value(self):
        """
        A :py:class:`BitstreamValue` defining the length of this
        :py:class:`Array`.
        
        If reading the value raises an exception or the returned value cannot
        be interpreted as a non-negative integer then the :py:attr:`num_values`
        will be treated as 0.
        """
        return self._num_values_bitstream_value
    
    def _dependency_changed(self, value_changed):
        if value_changed is self.num_values_bitstream_value:
            # Adjust the length of the internal `_value` tuple to match the
            # current num_values.
            if len(self._value) < self.num_values:
                # Extend
                new_values = tuple(
                    (self.value_constructor(i) if self.pass_index else self.value_constructor())
                    for i in range(len(self._value), self.num_values)
                )
                for value in new_values:
                    value._notify_on_change(self)
                self._value = self._value + new_values
            elif len(self._value) > self.num_values:
                # Truncate
                for value in self._value[self.num_values:]:
                    value._cancel_notify_on_change(self)
                self._value = self._value[:self.num_values]
        
        self._changed()
    
    def __str__(self):
        return concat_strings([str(v) for v in self._value])


class RectangularArray(Array):
    r"""
    An :py:class:`Array`-like for holding a 2D array of of values.
    
    By contrast with a regular :py:class:`Array`, a :py:class:`RectangularArray`:
    
    * Defines its :py:attr:`num_values` in terms of :py:attr:`width` and
      :py:attr:`height`.
    * Values are stored in row-major order.
    * Can be indexed using 2D indices, e.g. ``a[y, x]`` (note 'y' is given
      first)
    * Has a tabular string representation.
    
    The array order and 2D indexing scheme match the convention used by the
    VC-2 spec. Specifically:
    
    * (13.4) ``dc_prediction()``
    * (13.5.6.3) ``slice_band()``
    * (13.5.6.4) ``color_diff_slice_band()``
    * (15.5) ``clip_component()`` and ``offset_component()``
    
    An example of the indexing scheme is shown below:
    
        >>> q = RectangularArray(UInt, height=2, width=3)
        
        >>> assert q[0] is q[0, 0]
        >>> assert q[1] is q[0, 1]
        >>> assert q[2] is q[0, 2]
        >>> assert q[3] is q[1, 0]
        >>> assert q[4] is q[1, 1]
        >>> assert q[5] is q[1, 2]
    """
    
    def __init__(self, value_constructor, height=0, width=0,
                 *args, **kwargs):
        # NB: No need to notify on these changing since these in turn will
        # change num_values which finally notifies this array of a change in
        # size.
        self._height_bitstream_value = ensure_bitstream_value(height)
        self._width_bitstream_value = ensure_bitstream_value(width)
        
        num_values = FunctionValue(
            lambda hv, wv: (
                safe_get_non_negative_integer_value(hv)
                *
                safe_get_non_negative_integer_value(wv)
            ),
            self._height_bitstream_value,
            self._width_bitstream_value,
        )
        
        super(RectangularArray, self).__init__(
            value_constructor, num_values, *args, **kwargs)
    
    @property
    def height(self):
        return safe_get_non_negative_integer_value(self._height_bitstream_value)
    
    @property
    def width(self):
        return safe_get_non_negative_integer_value(self._width_bitstream_value)
    
    @property
    def height_bitstream_value(self):
        return self._height_bitstream_value
    
    @property
    def width_bitstream_value(self):
        return self._width_bitstream_value
    
    def __getitem__(self, key):
        # Normalise key to index
        if isinstance(key, tuple):
            y, x = key
            
            if not (0 <= y < self.height):
                raise IndexError(key)
            elif not (0 <= x < self.width):
                raise IndexError(key)
            
            key = (y*self.width) + x
        
        return super(RectangularArray, self).__getitem__(key)
    
    def __str__(self):
        return concat_tabular_strings([
            [str(self[y, x]) for x in range(self.width)]
            for y in range(self.height)
        ])


class SubbandArray(Array):
    r"""
    An :py:class:`Array`-like for holding values associated one-per-subband of
    a wavelet transform.
    
    By contrast with a regular :py:class:`Array`, a :py:class:`SubbandArray`:
    
    * Defines its :py:attr:`num_values` in terms of :py:attr:`dwt_depth` and
      :py:attr:`dwt_depth_ho`.
    * Can be indexed using the 2D notation ``a[level, subband]`` (see example
      below).
    * Has string representation which explicitly labels the levels and subbands
      of each entry.
    
    The array order is defined as being DC/L/LL followed by the 2D H bands
    followed by the 2D HL, LH and HH bands (in that order). This ordering is
    the same ordering used for subband components used in:
    
    * (12.4.5.3) ``quant_matrix()``
    * (13.5.3.1) ``ld_slice()``
    * (13.5.4) ``hq_slice()``
    * (13.5.5) ``slice_quantizers()``
    
    In addition to the usual array indexing scheme, :py:class:`SubbandArray`\ s
    can be indexed either directly (in bitstream order) or using level-subband
    keys like so::
    
        >>> q = SubbandArray(UInt, 2, 1)
        
        >>> # Level 0: DC Component (i.e. horizontal-only LF-component)
        >>> assert q[0] is q[0, "L"]
        
        >>> # Level 1: Horizontal-only HF-component
        >>> assert q[1] is q[1, "H"]
        
        >>> # Level 2: 2D HF-components
        >>> assert q[2] is q[2, "HL"]
        >>> assert q[3] is q[2, "LH"]
        >>> assert q[4] is q[2, "HH"]
        
        >>> # Level 3: 2D HF-components
        >>> assert q[5] is q[3, "HL"]
        >>> assert q[6] is q[3, "LH"]
        >>> assert q[7] is q[3, "HH"]
    
    Note that the name of the DC component is "DC" when no transforms are used,
    "LL" when only a 2D transform is used and "L" when a horizontal-only
    transform is used.
    """
    
    def __init__(self, value_constructor, dwt_depth=0, dwt_depth_ho=0,
                 *args, **kwargs):
        """
        The dimensions of this matrix are determined by the depth of the 2D and
        horizontal-only wavelet transforms used.
        """
        # NB: No need to notify on these changing since these in turn will
        # change num_values which finally notifies this array of a change in
        # size.
        self._dwt_depth_bitstream_value = ensure_bitstream_value(dwt_depth)
        self._dwt_depth_ho_bitstream_value = ensure_bitstream_value(dwt_depth_ho)
        
        num_values = FunctionValue(
            lambda dwt_depth, dwt_depth_ho: (
                # DC Band
                1 +
                # Horizontal-only components
                safe_get_non_negative_integer_value(dwt_depth_ho) +
                # 2D components
                (3 * safe_get_non_negative_integer_value(dwt_depth))
            ),
            self.dwt_depth_bitstream_value,
            self.dwt_depth_ho_bitstream_value,
        )
        
        super(SubbandArray, self).__init__(
            value_constructor, num_values, *args, **kwargs)
    
    @property
    def dwt_depth(self):
        return safe_get_non_negative_integer_value(self._dwt_depth_bitstream_value)
    
    @property
    def dwt_depth_ho(self):
        return safe_get_non_negative_integer_value(self._dwt_depth_ho_bitstream_value)
    
    @property
    def dwt_depth_bitstream_value(self):
        return self._dwt_depth_bitstream_value
    
    @property
    def dwt_depth_ho_bitstream_value(self):
        return self._dwt_depth_ho_bitstream_value
    
    def __getitem__(self, key):
        # Normalise key to index
        if isinstance(key, tuple):
            level, subband = key
            try:
                key = SubbandArray.subband_to_index(
                    level, subband, self.dwt_depth, self.dwt_depth_ho)
            except ValueError:
                raise KeyError(key)
        
        return super(SubbandArray, self).__getitem__(key)
    
    def __str__(self):
        level_strings = [("Level 0", [])]
        
        for index, value in enumerate(self._value):
            level, subband = SubbandArray.index_to_subband(
                index, self.dwt_depth, self.dwt_depth_ho)
            
            level_label = "Level {}".format(level)
            if level_strings[-1][0] != level_label:
                level_strings.append((level_label, []))
            
            level_strings[-1][1].append((subband, str(value)))
        
        return "\n".join(
            filter(None, (
                concat_labelled_strings([(label, concat_labelled_strings(strings))])
                for label, strings in level_strings
            ))
        )

    @staticmethod
    def index_to_subband(index, dwt_depth=0, dwt_depth_ho=0):
        """
        Static method. Convert from an index into a :py:class:`SubbandArray`
        to the corresponding (level, subband) tuple where level is an int and
        subband is one of "DC", "L", "LL", "H", "HL", "LH" and "HH".
        """
        if index == 0:
            level = 0
            if dwt_depth == 0 and dwt_depth_ho == 0:
                subband = "DC"
            elif dwt_depth_ho != 0:
                subband = "L"
            else:
                subband = "LL"
        elif index < dwt_depth_ho + 1:
            level = index
            subband = "H"
        else:
            offset_index = (index - dwt_depth_ho - 1)
            level = 1 + dwt_depth_ho + (offset_index // 3)
            subband = {
                0: "HL",
                1: "LH",
                2: "HH",
            }[offset_index % 3]
        
        if level > dwt_depth + dwt_depth_ho:
            raise ValueError(level)
        
        return (level, subband)

    @staticmethod
    def subband_to_index(level, subband, dwt_depth=0, dwt_depth_ho=0):
        """
        Static method. Convert from a (level, subband) tuple into an index in a
        :py:class:`SubbandArray`.
        """
        if level == 0:
            if dwt_depth_ho == 0 and dwt_depth == 0:
                if subband != "DC":
                    raise ValueError((level, subband))
            elif dwt_depth_ho > 0:
                if subband != "L":
                    raise ValueError((level, subband))
            elif dwt_depth > 0:
                if subband != "LL":
                    raise ValueError((level, subband))
            return 0
        elif level < 1 + dwt_depth_ho:
            if subband != "H":
                raise ValueError((level, subband))
            return level
        elif level < 1 + dwt_depth_ho + dwt_depth:
            if subband not in ("HL", "LH", "HH"):
                raise ValueError((level, subband))
            return (
                1 +
                dwt_depth_ho +
                ((level - dwt_depth_ho - 1) * 3)
            ) + {
                "HL": 0,
                "LH": 1,
                "HH": 2,
            }[subband]
        else:
            raise ValueError((level, subband))
