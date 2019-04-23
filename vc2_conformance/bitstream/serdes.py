r"""
A module which can be used to transform a set of functions designed to process
a bitstream (as in VC-2 specification) into general-purpose bitstream
serialisers, deserialisers and analysers.


Underlying idea and motivation
==============================

In addition to providing a VC-2 conformance-checking decoder, this library is
also required to perform the following tasks:

* Display conforming and non-conforming bitstreams in a human readable fashion
  to facilitate debugging of encoders.
* Generate arbitrary conforming and non-conforming bitstreams.

As a consequence, it is important to be able to both serialise and deserialise
VC-2 bitstreams, including bit streams containing non-conforming values. In
order to minimise the chances of inconsistencies between the VC-2 specification
and any serialiser/deserialiser, this module implements a framework for
transforming the VC-2 specification pseudocode into robust, general purpose
serialisers/deserialisers.

A basic bitstream serialiser
----------------------------

The VC-2 specification describes the bitstream and decoding process in a series
of pseudocode functions such as the following::

    frame_size(video_parameters):
        custom_dimensions_flag = read_bool()
        if(custom_dimensions_flag == True)
            video_parameters[frame_width] = read_uint()
            video_parameters[frame_height] = read_uint()

To see how this definition might be transformed into a general purpose
bitstream serialiser we must transform this definition of a program which
*reads* a VC-2 bitstream into one which *writes* one.

We start by replacing all of the ``read_*`` functions with equivalent
``write_*`` functions (which we define here as returning the value that they
write)::

    frame_size(video_parameters):
        custom_dimensions_flag = write_bool(???)
        if(custom_dimensions_flag == True)
            video_parameters[frame_width] = write_uint(???)
            video_parameters[frame_height] = write_uint(???)

Next we need to define what values we'd like writing by replacing the ``???``
placeholders with a suitable global variables like so::

    new_custom_dimensions_flag = True
    new_frame_width = 1920
    new_frame_height = 1080
    
    frame_size(video_parameters):
        custom_dimensions_flag = write_bool(new_custom_dimensions_flag)
        if(custom_dimensions_flag == True)
            video_parameters[frame_width] = write_uint(new_frame_width)
            video_parameters[frame_height] = write_uint(new_frame_height)

We have now transformed the VC-2 pseudocode bitstream *reader* function into a
*writer* function. What's more by setting the global variables appropriately it
is possible to use this function as a general-purpose bitstream serialiser.


A basic deserialiser
--------------------

Unfortunately, the original bitstream reader pseudo code from the VC-2
specification is not quite usable as a general-purpose bitstream deserialiser:

* The reader does not capture every value read from the bitstream in a variable
  we can later examine (e.g. the ``custom_dimensions_flag`` is kept in a local
  variable and not returned).
* The values which are captured are stored in a structure designed to aid
  decoding and not necessarily to faithfully describe a bitstream.

Lets create a new version of the reader function which overcomes these
limitations. We redefine the ``read_*`` functions to take an additional
argument naming a global variable where the read values will be stored, in
addition to being returned, giving the following pseudocode::

    got_custom_dimensions_flag = None
    got_frame_width = None
    got_frame_height = None
    
    frame_size(video_parameters):
        custom_dimensions_flag = read_bool(got_custom_dimensions_flag)
        if(custom_dimensions_flag == True)
            video_parameters[frame_width] = read_uint(got_frame_width)
            video_parameters[frame_height] = read_uint(got_frame_height)

This small change ensures that every value read from the bitstream is captured
in a global variable which we can later examine and which is orthogonal to
whatever data structures the VC-2 pseudocode might otherwise use.


An introduction to the :py:class:`SerDes` interface
===================================================

The similarities between the transformations required to turn the VC-2
pseudocode into general purpose serialisers and deserialisers should be fairly
clear. In fact, the only difference between the two is that in one the
functions are called ``read_*`` and in the other they're called ``write_*``. In
both cases, the ``read_*`` and ``write_*`` functions take essentially the same
arguments: a name of a global variable.

This module defines the :py:class:`SerDes` interface which can be used by the
VC-2 pseudocode specifications to drive both bitstream serialisation and
deserialisation.

Translating the ``frame_size`` function into valid Python which takes a
:py:class:`SerDes` instance as an argument we arrive at the following code::

    def frame_size(serdes, video_parameters):
        custom_dimensions_flag = serdes.bool("custom_dimensions_flag")
        if(custom_dimensions_flag == True)
            video_parameters["frame_width"] = serdes.uint("got_frame_width")
            video_parameters["frame_height"] = serdes.uint("got_frame_height")

To deserialise (read) a bitstream we use the :py:class:`Deserialiser`
implementation of :py:class:`SerDes` like so::

    >>> from vc2_conformance.bitstream import BitstreamReader, Deserialiser
    >>> reader = BitstreamReader(open("frame_size_snippet.bin", "rb"))
   
    >>> with Deserialiser(reader) as serdes:
    ...     frame_size(serdes, {})
    >>> serdes.context
    {"custom_dimensions_flag": True, "frame_width": 1920, "frame_height": 1080}

The :py:attr:`SerDes.context` property is a :py:class:`dict` which contains
each of the values read from the bitstream (named as per the calls to the
various :py:class:`SerDes` methods).

In the nomenclature of this module, this *context* dictionary holds values for
each of the *target names* specified by :py:meth:`SerDes.bool`,
:py:meth:`SerDes.uint` etc.

Values to be serialised should be structured into a context dictionary of
similar shape and passed to a :py:class:`Serialiser`::

    >>> from vc2_conformance.bitstream import BitstreamWriter, Serialiser
    >>> writer = BitstreamWriter(open("frame_size_snippet.bin", "wb"))
    
    >>> context = {"custom_dimensions_flag": True, "frame_width": 1920, "frame_height": 1080}
    >>> with Serialiser(writer, context) as serdes:
    ...     frame_size(serdes, {})

In this example a bitstream containing a '1' followed by the variable-length
integers '1920' and '1080' would be written to the bitstream.


Verification
------------

The :py:class:`SerDes` implementations perform various 'sanity checks' during
serialisation and deserialisation to ensure that the values passed in or
returned have a 1:1 correspondence with values in the bitstream.

* When values are read during deserialisation, :py:class:`Deserialiser` checks
  that names are not re-used, guaranteeing that if a value appears in the
  bitstream it also appears in the output context dictionary.
* When values are written during serialisation, :py:class:`Serialiser` checks
  that every value in the context dictionary is used exactly once, ensuring
  that every value provided is represented in the bitstream.
* During serialisation, values are also checked to ensure they can be
  correctly represented by the bitstream encoding.


Representing hierarchy
----------------------

The VC-2 bitstream does not represent a flat collection of values but rather a
hierarchy. The :py:class:`SerDes` interface provides a additional facilities to
allow this structure to be recreated in the deserialised representation, making
it easier to inspect and describes bitstreams in their deserialised form.

For example, in the VC-2 specification, the ``source_parameters`` function
(11.4) is defined by a series of functions which each read the values
relating to a particular video feature such as the ``frame_size`` function
we've seen above. To collect together related values we can use
:py:meth:`SerDes.subcontext` to create nested context dictionaries::

    def source_parameters(serdes):
        video_parameters = {}
        with serdes.subcontext("video_parameters"):
            frame_size(serdes, video_parameters)
        with serdes.subcontext("color_diff_sampling_format"):
            color_diff_sampling_format(serdes, video_parameters)
        # ...
        return video_parameters

This results in a nested dictionary structure::

    >>> with Deserialiser(reader) as serdes:
    ...     video_parameters = source_parameters(serdes)
    
    >>> from pprint import pprint
    >>> pprint(serdes.context)
    {
        "video_parameters": {
            "custom_dimensions_flag": True,
            "frame_width": 1920,
            "frame_height": 1080,
        },
        "color_diff_sampling_format": {
            "custom_color_diff_format_flag": False,
        },
        # ...
    }

When used with :py:module:`vc2_conformance.fixeddict`, :py:class:`SerDes` also
makes it possible to define custom dictionary types for each part of the
hierarchy using the :py:func:`context_type` decorator. Benefits include:

* Improved 'pretty-printed' string representations.
* Supporting default values when defining bitstreams 'by hand'
* Additional checks that unexpected values are not used accidentally in the bitstream.

For example, here's how the ``parse_info`` header (10.5.1) might be represented::

    from vc2_conformance.fixeddict import fixeddict, Entry
    from vc2_conformance.formatters import Hex
    from vc2_conformance.tables import ParseCodes
    ParseInfo = fixeddict(
        "ParseInfo",
        Entry("parse_info_prefix", default=0x42424344, formatter=Hex(8)),
        Entry("parse_code", default=ParseCodes.end_of_sequence, enum=ParseCodes),
        Entry("next_parse_offset", default=0),
        Entry("previous_parse_offset", default=0),
    )
    
    @context_type(ParseInfo)
    def parse_info(serdes, state):
        serdes.nbits(4*8, "parse_info_prefix")
        state["parse_code"] = serdes.nbits(8, "parse_code")
        state["next_parse_offset"] = serdes.nbits(32, "next_parse_offset")
        state["previous_parse_offset"] = serdes.nbits(32, "previous_parse_offset")

Using the above we can quickly create structures ready for serialisation::

    >>> context = ParseInfo(previous_parse_offset=1234)
    >>> with Deserialiser(writer, context) as serdes:
    ...     parse_info(serdes, {})

We also benefit from improved string formatting when deserialising values::
    
    >>> with Deserialiser(reader) as serdes:
    ...     parse_info(serdes, {})
    >>> str(serdes.context)
    ParseInfo:
      parse_info_prefix: 0x42424344
      parse_code: end_of_sequence (0x10)
      next_parse_offset: 0
      previous_parse_offset: 1234

Representing arrays
-------------------

The VC-2 bitstream format includes a number of array-like fields, for example
arrays of transform coefficients within slices. Rather than defining unique
names for every array value, :py:class:`SerDes` allows values to be declared as
lists. For example::

    def list_example(serdes):
        serdes.declare_list("three_values")
        serdes.uint("three_values")
        serdes.uint("three_values")
        serdes.uint("three_values")

When deserialising, the result will look like::
    
    >>> with Deserialiser(reader) as serdes:
    ...     list_example(serdes)
    >>> serdes.context
    {"three_values": [100, 200, 300]}

Likewise, when serialising, a list of values (of the correct length) should
also be provided:

    >>> context = {"three_values": [10, 20, 30]}
    >>> with Deserialiser(writer, context) as serdes:
    ...     list_example(serdes)

As usual, the :py:class:`SerDes` classes will verify that the correct number of
values is present and will throw exceptions when too many or too few are
provided.


Computed values
---------------

In some circumstances, when interpreting a deserialised bitstream it may be
necessary to know information computed by an earlier part of the bitstream. For
example, the dimensions of a slice depend on numerous video formatting options.
To avoid error-prone reimplementation of these calculations it is possible to
use :py:meth:`SerDes.computed_value` to add values to the context dictionary
which do not appear in the bitstream. For example::

    def ld_slice(serdes, state, sx, sy):
        serdes.computed_value("_slices_x", state["slices_x"])
        serdes.computed_value("_slices_y", state["slices_y"])
        # ...

The computed value will be set in the context dictionary regardless of whether
serialisation or deserialisation is taking place and any existing value is
always ignored.

.. note::
    
    It is recommended that by convention computed value target names are
    prefixed or suffixed with an underscore.
"""

from functools import wraps

from contextlib import contextmanager

from vc2_conformance.exceptions import (
    UnusedTargetError,
    ReusedTargetError,
    ListTargetExhaustedError,
    ListTargetContainsNonListError,
    UnclosedBoundedBlockError,
    UnclosedNestedContextError,
)


__all__ = [
    "SerDes",
    "Serialiser",
    "Deserialiser",
    "MonitoredSerialiser",
    "MonitoredDeserialiser",
    "context_type",
]


class SerDes(object):
    """
    The base serialiser/deserialiser interface and implementation.
    
    This base implementation includes all but the value writing/reading
    features of the serialisation and deserialisation process.
    
    Attributes
    ==========
    io : :py:class:`BitstreamReader` or :py:class:`BitstreamWriter`
        The I/O interface in use.
    context : dict or None
        The (top-level) context dictionary.
    """
    
    def __init__(self, io, context=None):
        """
        Parameters
        ==========
        io : :py:class:`BitstreamReader` or :py:class:`BitstreamWriter`
            The current I/O interface to use initially.
        context : dict
            The initial context dictionary.
        """
        self.io = io
        
        # The current context dictionary.
        # {target_name: value, ...}
        self._context = context if context is not None else {}
        
        # Logs which target names have already been used. Initially an empty
        # dictionary.
        # 
        # When a non-list target is used, a corresponding entry is set to True in
        # this dictionary. Re-use of a target is prevented by checking that the
        # required target does not already appear in this dictionary.
        # 
        # When :py:attr:`declare_list` is used, the corresponding entry in
        # context_indices is set to to 0. Subsequent uses of that target should
        # increment the counter.
        #
        # {target_name: True or int, ...}
        self._context_indices = {}
        
        # Whenever :py:meth:`subcontext_enter` is used, the current
        # self._context and self._context_indices dictionaries and the
        # specified target name are pushed onto their respective stacks. The
        # :py:meth:`subcontext_leave` method pops these values again.
        self._context_stack = []  # [<context dict>, ...]
        self._context_indices_stack = []  # [<context_indices dict>, ...]
        self._target_stack = []  # [str, ...]
    
    def _set_context_value(self, target, value):
        """
        Add a value to a context dictionary, checking that the value has not
        already been set and extending list targets if necessary.
        """
        if target not in self._context_indices:
            # Case: This target has not been declared as a list and this is the
            # first time it has been accessed.
            self._context[target] = value
            self._context_indices[target] = True
        elif self._context_indices[target] is True:
            # Case: This target has not been declared as a list and has already
            # been accessed.
            raise ReusedTargetError(self.describe_path(target))
        else:
            # Case: This target has been declared as a list.
            i = self._context_indices[target]
            self._context_indices[target] += 1
            
            target_list = self._context[target]
            if len(target_list) == i:
                # List is being filled for the first time
                target_list.append(value)
            else:
                # List already exists and we're updating it.
                target_list[i] = value
    
    def _get_context_value(self, target):
        """
        Get a value from the context dictionary, checking that the value has not
        already been accessed and moving on to the next list item for list
        targets.
        """
        if target not in self._context_indices:
            # Case: This target is not a list and has not been used before
            self._context_indices[target] = True
            return self._context[target]
        elif self._context_indices[target] is True:
            # Case: This target is not a list but has already been used
            raise ReusedTargetError(self.describe_path(target))
        else:
            # Case: This target has been declared as a list.
            i = self._context_indices[target]
            if i < len(self._context[target]):
                self._context_indices[target] += 1
                return self._context[target][i]
            else:
                raise ListTargetExhaustedError(self.describe_path(target))
    
    def _setdefault_context_value(self, target, default):
        """
        Attempt to get a value (or next value, for lists) for a particular
        target. If the value does not exist, sets it to the supplied default.
        """
        if target not in self._context_indices:
            # Case: This target is not a list and has not been used before
            self._context_indices[target] = True
            return self._context.setdefault(target, default)
        elif self._context_indices[target] is True:
            # Case: This target is not a list but has already been used. Fail.
            raise ReusedTargetError(self.describe_path(target))
        else:
            # Case: This target has been declared as a list.
            i = self._context_indices[target]
            self._context_indices[target] += 1
            if i == len(self._context[target]):
                self._context[target].append(default)
            return self._context[target][i]
        
    def bool(self, target):
        """
        Reads or writes a boolean (single bit) in a bitstream (as per (A.3.2)
        read_bool()).
        
        Parameters
        ==========
        target : str
            The target for the bit (as a :py:class:`bool`).
        
        Returns
        =======
        value : bool
        """
        raise NotImplementedError()
    
    def nbits(self, target, num_bits):
        """
        Reads or writes an fixed-length unsigned integer in a bitstream (as
        per (A.3.3) read_nbits()).
        
        Parameters
        ==========
        target : str
            The target for the value (as a :py:class:`int`).
        num_bits : int
            The number of bits in the value.
        
        Returns
        =======
        value : int
        """
        raise NotImplementedError()
    
    def uint_lit(self, target, num_bytes):
        """
        Reads or writes an fixed-length unsigned integer in a bitstream (as
        per (A.3.4) read_uint_lit()). Not to be confused with :py:meth:`uint`.
        
        Parameters
        ==========
        target : str
            The target for the value (as a :py:class:`int`).
        num_bytes : int
            The number of bytes in the value.
        
        Returns
        =======
        value : int
        """
        raise NotImplementedError()
    
    def bitarray(self, target, num_bits):
        """
        Reads or writes an fixed-length string of bits from the bitstream as a
        :py:class:`bitarray.bitarray`. This may be a more sensible type for
        holding unpredictably sized non-integer binary values such as padding
        bits.
        
        Parameters
        ==========
        target : str
            The target for the value (as a :py:class:`bitarray.bitarray`).
        num_bits : int
            The number of bits in the value.
        
        Returns
        =======
        value : :py:class:`bitarray.bitarray`
        """
        raise NotImplementedError()
    
    def bytes(self, target, num_bytes):
        """
        Reads or writes an fixed-length :py:class:`bytes` string from the
        bitstream. This is a more convenient alternative to
        :py:data:`TokenTypes.nbits` or :py:data:`TokenTypes.bitarray` when
        large blocks of data are to be read but not treated as integers.
        
        Parameters
        ==========
        target : str
            The target for the value (as a :py:class:`bytes`).
        num_bits : int
            The number of *bytes* (not bits) in the value.
        
        Returns
        =======
        value : :py:class:`bytes`
        """
        raise NotImplementedError()
    
    def uint(self, target):
        """
        A variable-length, unsigned exp-golomb integer in a bitstream (as per
        (A.4.3) read_uint()).
        
        Parameters
        ==========
        target : str
            The target for the value (as a :py:class:`int`).
        
        Returns
        =======
        value : int
        """
        raise NotImplementedError()
    
    def sint(self, target, num_bits):
        """
        A variable-length, signed exp-golomb integer in a bitstream (as per (A.4.4)
        read_sint()).
        
        Parameters
        ==========
        target : str
            The target for the value (as a :py:class:`int`).
        
        Returns
        =======
        value : int
        """
        raise NotImplementedError()
    
    def byte_align(self, target):
        """
        Advance in the bitstream to the next whole byte boundary, if not already on
        one (as per (A.2.4) byte_align()).
        
        Parameters
        ==========
        target : str
            The target for the padding bits (as a
            :py:class:`bitarray.bitarray`).
        """
        _, bits = self.io.tell()
        num_bits = 0 if bits == 7 else (bits + 1)
        self.bitarray(target, num_bits)
        
    def bounded_block_begin(self, length):
        """
        Defines the start of a bounded block (as per (A.4.2)). Must be followed
        by a matching :py:meth:`bounded_block_end`.
        
        See also: :py:meth:`bounded_block`.
        
        Bits beyond the end of the block are always '1'. If a '0' is written
        past the end of the block a :py:exc:`ValueError` will be thrown.
        
        Parameters
        ==========
        length : int
            The length of the bounded block in bits
        """
        self.io.bounded_block_begin(length)
        
    def bounded_block_end(self, target):
        """
        Defines the end of a bounded block (as per (A.4.2)). Must be proceeded
        by a matching :py:meth:`bounded_block_begin`.
        
        Parameters
        ==========
        target : str
            The target name for any unused bits (as a
            :py:class:`bitarray.bitarray`).
        """
        num_bits = self.io.bounded_block_end()
        self.bitarray(target, num_bits)
    
    @contextmanager
    def bounded_block(self, target, length):
        """
        A context manager defining a bounded block (as per (A.4.2)).
        
        See also: :py:meth:`bounded_block_begin`.
        
        Example usage::
        
            with serdes.bounded_block("unused_bits", 100):
                # ...
        
        Parameters
        ==========
        target : str
            The target name for any unused bits (as a
            :py:class:`bitarray.bitarray`).
        length : int
            The length of the bounded block in bits
        """
        self.bounded_block_begin(length)
        yield
        self.bounded_block_end(target)
    
    def declare_list(self, target):
        """
        Declares that the specified target should be treated as a
        :py:class:`list`.  Whenever this target is used in the future, values
        will be read/written sequentially from the list.
        
        This method has no impact on the bitstream.
        
        Parameters
        ==========
        target : str
            The target name to be declared as a list.
        """
        if target in self._context_indices:
            # Target has already been used or delcared
            raise ReusedTargetError(self.describe_path(target))
        
        if target not in self._context:
            # Target not yet defined in context; create a new empty list
            self._context[target] = []
        else:
            # The target already exists in the context; make sure it is a list
            if not isinstance(self._context[target], list):
                raise ListTargetContainsNonListError(
                    "{} contains {!r} (which is not a list)".format(
                        self.describe_path(target), self._context[target]))
        
        self._context_indices[target] = 0
    
    def set_context_type(self, context_type):
        """
        Set (or change) the type of the type of the current context dictionary.
        
        This method has no impact on the bitstream.
        
        Parameters
        ==========
        context_type : :py:class:`dict`-like type
            The desired type. If the context is already of the required type,
            no change will be made. If the context is currently of a different
            type, it will be passed to the ``context_type`` constructor and the
            new type used in its place.
        """
        # Only replace the type if necessary to avoid unnecessary copying.
        if type(self._context) is not context_type:
            self._context = context_type(self._context)
            
            # Replace the reference to this context in its parent context
            if self._context_stack:
                parent_context = self._context_stack[-1]
                parent_target = self._target_stack[-1]
                parent_target_index = self._context_indices_stack[-1][parent_target]
                
                if parent_target_index is True:
                    # The child context is in a normal target in the parent context
                    # dict
                    parent_context[parent_target] = self._context
                else:
                    # The child context is in a list target in the parent context dict
                    # (NB: The parent_target_index value is the *next* index in the
                    # list, hence being decremented by one here).
                    parent_context[parent_target][parent_target_index-1] = self._context
            else:
                # Context stack is empty so there must be no parent to update!
                pass
    
    def subcontext_enter(self, target):
        """
        Creates and/or enters a context dictionary within the specified
        target of the current context dictionary. Must be followed later by a
        matching :py:meth:`subcontext_leave`.
        
        Parameters
        ==========
        target : str
            The name of the target in the current context in which the new
            subcontext is/will be stored.
        """
        # Insert the new context into the current context at the
        # specified token
        new_context = self._setdefault_context_value(target, {})
        
        # Push the old context onto the stack
        self._context_stack.append(self._context)
        self._context_indices_stack.append(self._context_indices)
        self._target_stack.append(target)
        
        self._context = new_context
        self._context_indices = {}
    
    def subcontext_leave(self):
        """
        Leaves the current nested context dictionary entered by
        :py:meth:`subcontext_enter`. Verifies that the closed dictionary has no
        unused entries, throwing an appropriate exception if not.
        """
        self._verify_context_is_complete()
        
        self._context = self._context_stack.pop()
        self._context_indices = self._context_indices_stack.pop()
        self._target_stack.pop()
    
    @contextmanager
    def subcontext(self, target):
        """
        A Python context manager alternative to ;py:meth:`subcontext_enter` and
        ;py:meth:`subcontext_leave`.
        
        Example usage::
        
            >>> with serdes.subcontext("target"):
            ...     # ...
        
        Exactly equivalent to::
        
            >>> serdes.subcontext_enter("target"):
            >>> # ...
            >>> serdes.subcontext_leave():
        
        (But without the possibility of forgetting the
        :py:meth:`subcontext_leave` call).
        
        Parameters
        ==========
        target : str
            The name of the target in the current context in which the new
            subcontext is/will be stored.
        """
        self.subcontext_enter(target)
        yield
        self.subcontext_leave()
    
    def computed_value(self, target, value):
        """
        Places a value into the named target in the current context, without
        reading or writing anything into the bitstream. Any existing value in
        the context will be overwritten.
        
        This operation should be used sparingly to embed additional information
        in a context dictionary which might be required to sensibly interpret
        its contents and which cannot be trivially computed from the context
        dictionary. For example, the number of transform coefficients in a
        coded picture depends on numerous computations and table lookups using
        earlier bitstream values.
        
        Parameters
        ==========
        target : str
            The name of the target in the current context to store the value in.
        value : any
            The value to be stored.
        """
        self._set_context_value(target, value)
    
    def _verify_context_is_complete(self):
        """
        Verify that the current context is 'complete'. That is, every entry in
        the context dict has been used and that every element in any lists has
        been used too.
        
        Raises
        ======
        :py:exc:`UnusedTargetError`
        """
        for target, value in self._context.items():
            if target not in self._context_indices:
                # Target not used
                raise UnusedTargetError(self.describe_path(target))
            else:
                index = self._context_indices[target]
                if index is True:
                    # Target was used (and it is not a list)
                    pass
                elif index != len(value):
                    # Target was used and was a list, but not all entries were
                    # used!
                    raise UnusedTargetError("{}[{!r}][{}:{}]".format(
                        self.describe_path(), target, index, len(value)))
    
    def verify_complete(self):
        """
        Verify that all values in the current context have been used and that
        no bounded blocks or nested contexts have been left over.
        
        Raises
        ======
        :py:exc:`UnusedTargetError`
        :py:exc:`UnclosedNestedContextError`
        :py:exc:`UnclosedBoundedBlockError`
        """
        self._verify_context_is_complete()
        
        if self._context_stack:
            raise UnclosedNestedContextError(self.describe_path())
        
        if self.io.bits_remaining is not None:
            raise UnclosedBoundedBlockError()
    
    def __enter__(self):
        """
        When used as a context manager, 'verify_complete' is automatically
        called.
        
        Example usage::
            
            >>> with Deserialiser(reader) as serdes:
            ...     frame_size(serdes)
            >>> serdes.context
        
        Exactly equivalent to::
            
            >>> serdes = Deserialiser(reader)
            >>> frame_size(serdes)
            >>> serdes.verify_complete()
            >>> serdes.context
        
        (But without the possibility of foregoing the
        :py:meth:`verify_complete` call.)
        """
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        # Don't bother checking validity if an exception was thrown anyway
        if exc_type is None:
            self.verify_complete()
    
    @property
    def context(self):
        """Get the top-level context dictionary."""
        if self._context_stack:
            return self._context_stack[0]
        else:
            return self._context
    
    def describe_path(self, target=None):
        """
        Produce a human-readable description of the part of the bitstream the
        parser is currently processing.
        
        If 'target' is None, prints only the path of the current nested context
        dictionary. If 'target' is a target name in the current target
        dictionary, this will be included in the string.
        
        As a sample, a path might look like the following::
        
            SequenceHeader['source_parameters']['frame_size']['frame_width']
        
        """
        full_context_stack = list(self._context_stack)
        full_context_indices_stack = list(self._context_indices_stack)
        full_target_stack = list(self._target_stack)
        if target is not None:
            full_context_stack += [self._context]
            full_context_indices_stack += [self._context_indices]
            full_target_stack += [target]
        
        root_type = self.context.__class__.__name__
        
        return "{}{}".format(
            root_type,
            "".join(
                (
                    "[{!r}]".format(target)
                    if (
                        context_indices.get(target, True) is True or
                        context_indices.get(target, True) == 0
                    ) else
                    "[{!r}][{}]".format(
                        target,
                        # NB: context_indices includes the index of the first
                        # unused index, hence being decremented by one here.
                        context_indices[target]-1,
                    )
                )
                for context, context_indices, target in zip(
                    full_context_stack,
                    full_context_indices_stack,
                    full_target_stack,
                )
            )
        )


class Deserialiser(SerDes):
    """
    A bitstream deserialiser which creates a context dictionary based on a
    bitstream.
    
    Parameters
    ==========
    io : :py:class:`BitstreamReader`
    """
    
    def bool(self, target):
        value = bool(self.io.read_bit())
        self._set_context_value(target, value)
        return value
    
    def nbits(self, target, num_bits):
        value = self.io.read_nbits(num_bits)
        self._set_context_value(target, value)
        return value
    
    def uint_lit(self, target, num_bytes):
        value = self.io.read_uint_lit(num_bytes)
        self._set_context_value(target, value)
        return value
    
    def bitarray(self, target, num_bits):
        value = self.io.read_bitarray(num_bits)
        self._set_context_value(target, value)
        return value
    
    def bytes(self, target, num_bytes):
        value = self.io.read_bytes(num_bytes)
        self._set_context_value(target, value)
        return value
    
    def uint(self, target):
        value = self.io.read_uint()
        self._set_context_value(target, value)
        return value
    
    def sint(self, target):
        value = self.io.read_sint()
        self._set_context_value(target, value)
        return value


class Serialiser(SerDes):
    """
    A bitstream serialiser which, given a populated context dictionary, writes
    the corresponding bitstream.
    
    Parameters
    ==========
    io : :py:class:`BitstreamWriter`
    context : dict
    """
    
    def bool(self, target):
        value = self._get_context_value(target)
        self.io.write_bit(value)
        return bool(value)
    
    def nbits(self, target, num_bits):
        value = self._get_context_value(target)
        self.io.write_nbits(num_bits, value)
        return value
    
    def uint_lit(self, target, num_bytes):
        value = self._get_context_value(target)
        self.io.write_uint_lit(num_bytes, value)
        return value
    
    def bitarray(self, target, num_bits):
        value = self._get_context_value(target)
        self.io.write_bitarray(num_bits, value)
        return value
    
    def bytes(self, target, num_bytes):
        value = self._get_context_value(target)
        self.io.write_bytes(num_bytes, value)
        return value
    
    def uint(self, target):
        value = self._get_context_value(target)
        self.io.write_uint(value)
        return value
    
    def sint(self, target):
        value = self._get_context_value(target)
        self.io.write_sint(value)
        return value


class MonitoredMixin(object):
    """
    A mixin for :py:class:`SerDes` classes which allows a 'monitor' function to
    be provided which will be called after each primitive I/O operation
    completes. This allows the intermediate progress of bistream
    serialisation/deserialisation to be monitored or even terminated early
    (with an exception).
    """
    
    def __init__(self, monitor, io, context=None):
        """
        Parameters
        ==========
        monitor : callable(serdes, target)
            A function which will be called after every primitive I/O operation
            completes. This function is passed the :py:class:`SerDes` instance
            and the target name of the target just used.
        io : :py:class:`BitstreamReader` or :py:class:`BitstreamWriter`
        context : dict
        """
        super(MonitoredMixin, self).__init__(io, context)
        self.monitor = monitor
    
    def bool(self, target):
        value = super(MonitoredMixin, self).bool(target)
        self.monitor(self, target)
        return value
    
    def nbits(self, target, num_bits):
        value = super(MonitoredMixin, self).nbits(target, num_bits)
        self.monitor(self, target)
        return value
    
    def uint_lit(self, target, num_bytes):
        value = super(MonitoredMixin, self).uint_lit(target, num_bytes)
        self.monitor(self, target)
        return value
    
    def bitarray(self, target, num_bits):
        value = super(MonitoredMixin, self).bitarray(target, num_bits)
        self.monitor(self, target)
        return value
    
    def bytes(self, target, num_bytes):
        value = super(MonitoredMixin, self).bytes(target, num_bytes)
        self.monitor(self, target)
        return value
    
    def uint(self, target):
        value = super(MonitoredMixin, self).uint(target)
        self.monitor(self, target)
        return value
    
    def sint(self, target):
        value = super(MonitoredMixin, self).sint(target)
        self.monitor(self, target)
        return value


class MonitoredSerialiser(MonitoredMixin, Serialiser):
    """
    Like :py:class:`Serialiser` but takes a 'monitor' function as the first
    constructor argument. This function will be called every time bitstream
    value has been serialised (written).
    
    Parameters
    ==========
    monitor : callable(serdes, target)
        A function which will be called after every primitive I/O operation
        completes. This function is passed this :py:class:`MonitoredSerialiser`
        instance and the target name of the target just serialised.
        
        This function may be used to inform a user of the current progress of
        serialisation (e.g. using :py:meth:`SerDes.describe_path` or
        :py:data:`SerDes.io`) or to terminate serialisation early (by throwing
        an exception).
    io : :py:class:`BitstreamWriter`
    context : dict
    """


class MonitoredDeserialiser(MonitoredMixin, Deserialiser):
    """
    Like :py:class:`Deserialiser` but takes a 'monitor' function as the first
    constructor argument. This function will be called every time bitstream
    value has been deserialised (read).
    
    Parameters
    ==========
    monitor : callable(serdes, target)
        A function which will be called after every primitive I/O operation
        completes. This function is passed this
        :py:class:`MonitoredDeserialiser` instance and the target name of the
        target just serialised.
        
        This function may be used to inform a user of the current progress of
        deserialisation (e.g. using :py:meth:`SerDes.context`,
        :py:meth:`SerDes.describe_path` or :py:data:`SerDes.io`) or to
        terminate deserialisation early (by throwing an exception).
    io : :py:class:`BitstreamReader`
    """


def context_type(dict_type):
    """
    Syntactic sugar. A decorator for :py:class:`SerDes` which uses
    :py:meth:`SerDes.set_context_type` to set the type of the current context
    dict:
    
    Example usage::
    
        @context_type(FrameSize)
        def frame_size(serdes):
            # ...
    
    Exactly equivalent to::
    
        def frame_size(serdes):
            serdes.set_context_type(FrameSize)
            # ...
    
    The wrapped function must take a :py:class:`SerDes` as its first argument.
    """
    def wrap(f):
        @wraps(f)
        def wrapper(serdes, *args, **kwargs):
            serdes.set_context_type(dict_type)
            return f(serdes, *args, **kwargs)
        return wrapper
    return wrap
