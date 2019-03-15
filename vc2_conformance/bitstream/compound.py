"""
General-purpose compound :py:class:`BitstreamValue` types for building
composite types.
"""

from vc2_conformance.bitstream import BitstreamValue

from vc2_conformance.bitstream._util import indent, concat_strings


__all__ = [
    "Concatenation",
    "LabelledConcatenation",
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
    
    def _validate(self, value):
        if not isinstance(value, tuple):
            raise ValueError(
                "Concatenation expects a tuple of BitstreamValues.")
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
    
    @value.setter
    def value(self, value):
        self._validate(value)
        self._value = value
    
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
        self._offset = reader.tell()
        for v in self._value:
            v.read(reader)
    
    def write(self, writer):
        self._offset = writer.tell()
        for v in self._value:
            v.write(writer)
    
    def __getitem__(self, key):
        """Shorthand for ``concatenation.value[key]``"""
        return self._value[key]
    
    def __repr__(self):
        return "<{} {}>".format(
            self.__class__.__name__,
            " ".join(repr(v) for v in self._value)
        )
    
    def __str__(self):
        return concat_strings([str(v) for v in self.value])


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
        
        super(LabelledConcatenation, self).__init__(
            *self._names_values_to_values(names_values))
    
    def _names_values_to_values(self, names_values):
        """
        Internal method. Extract just the list of :py:class:`BitstreamValue`
        from a names and values list.
        """
        return tuple(
            nv if isinstance(nv, BitstreamValue) else nv[1]
            for nv in names_values
            if nv is not None and not isinstance(nv, str)
        )
    
    @property
    def value(self):
        """The values in the concatenation (see constructor arguments)."""
        return self._names_values
    
    @value.setter
    def value(self, names_values):
        value = self._names_values_to_values(names_values)
        self._validate(value, self.length)
        
        self._value = value
        self._names_values = _names_values
    
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
        return "<{} {}>".format(
            self.__class__.__name__,
            " ".join(
                (
                    repr(nv)
                    if isinstance(nv, BitstreamValue) else
                    "{}={!r}".format(nv[0], nv[1])
                )
                for nv in self._names_values
                if nv is not None and not isinstance(nv, str)
            )
        )
    
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
                    string = "{}: {}".format(name, string)
                    body.append(indent(string, space*indent_level))
        
        return "\n".join(body)
