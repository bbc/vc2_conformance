r"""

bitstreams described by 'token-emitting generators'.

A token-emitting generator is a Python generator function which generates a
series of :py:class:`Token` tuples which represent primitive I/O operations.  A
single generator can be used to drive both the bitstream serialisation and
deserialisation process. This means that once a bitstream format has been
described once (in token-emitting generator form) the serialiser, deserialiser
and inspection tools come 'for free'.

The introduction below explains how the VC-2 specification can be easily
transformed into token-emitting generators while also introducing the
underlying concepts used in this module in detail.


Turning reading in to writing
-----------------------------

The VC-2 standard describes the bitstream via a series of pseudo-code
descriptions of a program which *reads* it. One such pseudo-code listing is
shown below::

    frame_size(video_parameters):
        custom_dimensions_flag = read_bool()
        if(custom_dimensions_flag == True)
            video_parameters[frame_width] = read_uint()
            video_parameters[frame_height] = read_uint()

If we wish to modify this program to instead *generate* a bitstream we could
start by replacing all of the read operations with corresponding write
operations (which we'll define here as returning the value written)::

    frame_size(video_parameters):
        custom_dimensions_flag = write_bool(???)
        if(custom_dimensions_flag == True)
            video_parameters[frame_width] = write_uint(???)
            video_parameters[frame_height] = write_uint(???)

But where do all of the ``???`` arguments for our writing functions come from?
Lets replace these with a set of new global variables to hold the values we'd
like to write in our generated bitstream::

    new_custom_dimensions_flag = True
    new_frame_width = 1920
    new_frame_height = 1080
    
    frame_size(video_parameters):
        custom_dimensions_flag = write_bool(new_custom_dimensions_flag)
        if(custom_dimensions_flag == True)
            video_parameters[frame_width] = write_uint(new_frame_width)
            video_parameters[frame_height] = write_uint(new_frame_height)

We now have a usable pseudo code program for *writing* bitstreams which is
straight-forwardly verifiable as being equivalent to the program in the
specification.

This simple transformation may be used to turn *any* VC-2 bitstream reader
pseudo-code specification into a corresponding bitstream writer. This ability
to 'trivially' convert a reader-program into a writer-program is at the core of
what this module does.

Before getting too carried away, however, while the two pseudo-code programs
above both work but they are not particularly useful as general-purpose
bitstream manipulation routines:

* The reader and writer have insconsistent interfaces: The reader reads
  values into one set of variables while the writer writes values taken from
  another, differrent set of variables.

* The reader program doesn't retain all of the values it reads. For
  example ``custom_dimensions_flag`` is just a local variable and therefore
  cannot be inspected later.


Token-emitting Generators
-------------------------

Lets go back to our original reader pseudo code and turn it into a
valid Python function::

    def frame_size(video_parameters):
        custom_dimensions_flag = read_bool()
        if custom_dimensions_flag:
            video_parameters["frame_width"] = read_uint()
            video_parameters["frame_height"] = read_uint()

.. note::

    We presume that ``video_parameters`` is some suitable dict-like
    datastructure in this example.

Now, lets turn this into a generator which generates a :py:class:`Token`
whenever read takes place::

    def frame_size(video_parameters):
        custom_dimensions_flag = yield Token(TokenTypes.bool, None, None)
        if custom_dimensions_flag:
            video_parameters["frame_width"] = yield Token(TokenTypes.uint, None, None)
            video_parameters["frame_height"] = yield Token(TokenTypes.uint, None, None)

.. note::
    
    Generators are a Python feature normally used to implement simple
    iterators. This application, however, makes use of some of the more
    advanced features. If the idea of ``yield`` returning a value is
    unfamilliar, see Python PEP 342.

:py:class:`Token` is a :py:class:`collections.namedtuple` which holds three
values. The first of these is a :py:class:`TokenTypes` which specifies a type
of value. The second argument defines the length of the value. In the case of
both of the types in this example, the size is fixed ('1' for bool) or
variable (for uint) and so this is None. We'll see what the third argument is
used for in the next section.

To see how this token-emiting generator works lets
try executing it 'by hand' and, each time we get a :py:class:`Token`,
we'll pretend to read a value of whatever type it is asking for::

    >>> video_parameters = {}
    >>> gen = frame_size(video_parameters)
    
    >>> # Get the generator started
    >>> next(gen)
    (<TokenTypes.bool>, None, None)
    
    >>> # The generator asked for a bool; lets give it one
    >>> gen.send(True)
    (<TokenTypes.uint>, None, None)
    
    >>> # Now its asking for a uint; lets give it one of those, too
    >>> gen.send(1920)
    (<TokenTypes.uint>, None, None)
    >>> # And again
    >>> gen.send(1080)
    Traceback (most recent call last):
      ...
    StopIteration
    
    >>> # The generator has finished, lets look inside video_parameters and see
    >>> # what it did
    >>> video_parameters
    {"frame_width": 1920, "frame_height": 1080}

In the example above we can see that our token-emitting generator produces a
simple series of :py:class:`Token`\ s which, when treated as 'read' operations,
reads a simple bitstream.

To see why the token-emitting generator representation is useful (and how it
can be used for *writing* bitstreams) we need to introduce 'targets'.


Targets
-------

One of the problems we identified with using the VC-2 pseudo code bitstream
reading descriptions was that not every value that is read is captured in a
variable and, if it is, the variable may be somewhere deep in the VC-2 pseudo
code decoder's data structures.

The last of the three values in the :py;class:`Token` is the *target*: a string
identifier for the value associated with that token. Lets update our pseudo
code definition to add suitable targets to each :py:class:`Token` like so::

    def frame_size(video_parameters):
        custom_dimensions_flag = yield Token(TokenTypes.bool, None, "custom_dimensions_flag")
        if custom_dimensions_flag:
            video_parameters["frame_width"] = yield Token(TokenTypes.uint, None, "frame_width")
            video_parameters["frame_height"] = yield Token(TokenTypes.uint, None, "frame_height")

Now, lets run the generator by hand again. This time, however, as well as
pretending to read requested types of values we'll also keep a copy of the read
value we read in a *context* dictionary against the target name::
    
    >>> # A dictionary to hold the values we read in
    >>> context = {}
    
    >>> video_parameters = {}
    >>> gen = frame_size(video_parameters)
    
    >>> # Get the generator started
    >>> next(gen)
    (<TokenTypes.bool>, None, "custom_dimensions_flag")
    
    >>> # The generator asked for a bool and has given us the target name
    >>> # "custom_dimensions_flag"; lets give it a bool but also store it
    >>> context["custom_dimensions_flag"] = True
    >>> gen.send(True)
    (<TokenTypes.uint>, None, "frame_width")
    
    >>> # Now its asking for a uint and has given the target "frame_height";
    >>> # lets give it one of those and store it too
    >>> context["frame_width"] = 1920
    >>> gen.send(1920)
    (<TokenTypes.uint>, None, "frame_height")
    >>> # And again
    >>> context["frame_height"] = 1920
    >>> gen.send(1080)
    Traceback (most recent call last):
      ...
    StopIteration
    
    >>> # The generator has finished. As before, we can see its internal state
    >>> # has been updated accordingly
    >>> video_parameters
    {"frame_width": 1920, "frame_height": 1080}
    
    >>> # The context now contains a complete log of the values read
    >>> context
    {"custom_dimensions_flag": True, "frame_width": 1920, "frame_height": 1080}

By using the target name to log every value we read in the context dictionary
we no-longer need to unpick the VC-2 data structures to determine what was
contained in the bitstream.

The same mechanism also enables us to *generate* an arbitrary bitstream by
creating an arbitrary 'context' dictionary and for each each token generated
*writing* the value associated with a particular target name into the
bitstream. Running this process by hand::

    >>> # Choosing a new set of values to generate in the bitstream
    >>> context = {"custom_dimensions_flag": True, "frame_width": 1280, >>> "frame_height": 720}
    
    >>> video_parameters = {}
    >>> gen = frame_size(video_parameters)
    
    >>> # Get the generator started
    >>> next(gen)
    (<TokenTypes.bool>, None, "custom_dimensions_flag")
    
    >>> # The generator wants us to write the bool with the target name
    >>> # "custom_dimensions_flag". We can see in 'context' that this is True,
    >>> # so lets pretend we've written that and also send it back up to the
    >>> # generator
    >>> gen.send(context["custom_dimensions_flag"])  # True
    (<TokenTypes.uint>, None, "frame_width")
    
    >>> # Now its asking us to write a uint from the target name "frame_width".
    >>> # Again lets pretend we've written that and pass the value back up
    >>> gen.send(context["frame_width"])  # 1920
    (<TokenTypes.uint>, None, "frame_height")
    >>> # And likewise, but this time for frame_height
    >>> gen.send(context["frame_height"])  # 1080
    Traceback (most recent call last):
      ...
    StopIteration

The notion of targets allows us to interpret the series of :py:class:`Token`\ s
produced by the generator as instructions for reading or writing values to or
from a context dictionary. The resulting set of operations may be used to
completely deserialise or serialise the bitstream specified by the generator.

The :py:func:`read` and :py:func:`write` functions in this module implement the
procedure we carried out manually above. As a consequence we could read and
write a 'real' bitstreams like so::

    >>> from vc2_conformance.bitstream import BitstreamReader, BitstreamWriter
    
    >>> with open("bitstream_fragment.bin", "rb") as f:
    ...     reader = BitstreamReader(f)
    ...     video_parameters = {}
    ...     context = read(frame_size(video_parameters), reader)
    >>> # Actual values obviously depend on what you've read...
    >>> context
    {"custom_dimensions_flag": True, "frame_width": 1920, "frame_height": 1080}
    
    >>> context = {"custom_dimensions_flag": True, "frame_width": 1280, >>> "frame_height": 720}
    >>> with open("bitstream_fragment.bin", "wb") as f:
    ...     writer = BitstreamWriter(f)
    ...     video_parameters = {}
    ...     write(frame_size(video_parameters), writer, context)
    ...     writer.flush()


List Targets
------------

Sometimes a bitstream may contain a number of values, for example picture
slices contain many transform coefficients each. Though it would be possible to
generate unique target names for each slice, this can quickly become tiresome
and wastes memory. Instead it would be preferable to keep those values in a
:py:class:`list`.

By emitting a :py:class:`Token` with a :py:data:`TokenTypes.declare_list` type,
a particular target may be defined as containing a :py:class:`list` of values.
Once declared as a list, any subsequent tokens with this target name will
correspond to consecutive values in that list. For example::

    >>> def ten_numbers():
    ...     yield Token(TokenTypes.declare_list, None, "numbers")
    ...     for _ in range(10):
    ...         yield Token(TokenTypes.uint, None, "numbers")
    
    >>> context = read(ten_numbers(), reader)
    >>> # In this example the bitstream contained the numbers one through to
    >>> # nine in ascending order context
    {"numbers": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
    
    >>> # Lets generate a bitstream the numbers nine to zero, in descending
    >>> # order this time.
    >>> context = {"numbers": [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]}
    >>> write(ten_numbers(), writer, context)



Nested contexts
---------------

So far we've only considered generating bitstreams generated by a single
function and relating to targets in a single context. By contrast, the VC-2
pseudo-code is expressed spit across as a hierarchy of functions.  To make
relating between values in context dictionaries to the those in the
specification more straight-forward, it can be helpful to create matching
nested structures in the context dictionary.

Lets take the ``source_parameters()`` function from section (11.4) as an
example. This function is defined in terms of a nine other functions
(``frame_size``, ``color_diff_sampling_format`` and so on). Using only the
techniques seen so far, a greatly cut-down token-emitting generator translation
of the ``source_parameters()`` specification is shown below::

    def source_parameters():
        video_parameters = {}
        yield from frame_size(video_parameters)
        yield from color_diff_sampling_format(video_parameters)
    
    def frame_size(video_parameters):
        custom_dimensions_flag = yield Token(TokenTypes.bool, None, "custom_dimensions_flag")
        if custom_dimensions_flag is True:
            video_parameters["frame_width"] = yield Token(TokenTypes.uint, None, "frame_width")
            video_parameters["frame_height"] = yield Token(TokenTypes.uint, None, "frame_height")
    
    def color_diff_sampling_format(video_parameters):
        custom_color_diff_format_flag = yield Token(TokenTypes.bool, None, "custom_color_diff_format_flag")
        if custom_color_diff_format_flag is True:
            video_parameters["color_diff_format_index"] = yield Token(TokenTypes.uint, None, "color_diff_format_index")

.. note::

    The ``yield from`` syntax is a new piece of Python 3 syntactic sugar. It
    effectively makes ``source_parameters()`` pass-through the
    :py:class:`Token`\ s generated by ``frame_size()`` and
    ``color_diff_sampling_format()`` while also forwarding on the associated
    values sent back to the generator.
    
    If you're using Python 2, don't worry, we won't be using ``yield from``,
    nor its verbose equivalent, for very long.

In this example performing a read will produce something like the following
with all values being placed into the same context dictionary::
    
    >>> context = read(source_parameters(), reader)
    >>> from pprint import pprint
    >>> pprint(context)
    {
        "custom_dimensions_flag": True,
        "frame_width": 1920,
        "frame_height": 1080,
        "custom_color_diff_format_flag": True,
        "color_diff_format_index": 1,
    }

To introduce some hierarchy into the context dictionary we can use the
:py:data:`TokenTypes.nest` token type to modify ``source_parameters()`` like
so::

    def source_parameters():
        video_parameters = {}
        yield Token(TokenTypes.nest, frame_size(video_parameters), "frame_size")
        yield Token(TokenTypes.nest, color_diff_sampling_format(video_parameters), "color_diff_sampling_format")

When using :py:data:`TokenTypes.nest`, the second value in the
:py;class:`Token` should be a token-emitting generator. This generator will be
executed with its own private context dictionary which will be included in the
current context dictionary under the target name supplied.

Now when we re-run the reading process we get something like::

    >>> context = read(source_parameters(), reader)
    >>> pprint(context)
    {
        "frame_size": {
            "custom_dimensions_flag": True,
            "frame_width": 1920,
            "frame_height": 1080,
        },
        "color_diff_sampling_format": {
            "custom_color_diff_format_flag": True,
            "color_diff_format_index": 1,
        },
    }


Return Values
-------------

In the VC-2 specification, bitstream-parsing pseudo code functions sometimes
return values and ``source_parameters()`` is an example of such a function. In
Python 3, the ``return`` statement may be used as usual as follows:

    def source_parameters():
        video_parameters = {}
        yield Token(TokenTypes.nest, frame_size(video_parameters), "frame_size")
        yield Token(TokenTypes.nest, color_diff_sampling_format(video_parameters), "color_diff_sampling_format")
        return video_parameters

In Python 2, however, generators cannot return a value. As a work-around for
use in Python 2 and backwards-compatible Python 3 code, the special
:py:exc:`Return` exception should be raised::

    def source_parameters():
        video_parameters = {}
        yield Token(TokenTypes.nest, frame_size(video_parameters), "frame_size")
        yield Token(TokenTypes.nest, color_diff_sampling_format(video_parameters), "color_diff_sampling_format")
        raise Return(video_parameters)

When a function which returns a value is used via a :py:data:`TokenTypes.nest`
token, the returned value is sent back in response. For example, in the VC-2
specification ``source_parameters()`` is called from ``sequence_header()``
which could be translated like so::

    def sequence_header():
        # ...
        video_parameters = yield Token(TokenTypes.nest, source_parameters(), "source_parameters")
        # ...

Safety features
---------------

When generating new bitstreams by hand it is possible to inadvertently make
mistakes resulting in bitstreams not being generated as expected. For example
consider the following example::

    >>> # What happens next?
    >>> context = {"custom_dimensions_flag": False, "frame_width": 1920, "frame_height": 1080}
    >>> write(frame_size(), writer, context)

In this case we might expect a bitstream with three values in it: the boolean
and two numbers but in reality, because "custom_dimensions_flag" is False, the
bitstream only the flag boolean. To prevent this class of mistake going
unnoticed, the various functions provided by this module such as
:py:func:`write` check for unused targets in the context dictionary and throw
an exception accordingly::

    >>> context = {"custom_dimensions_flag": False, "frame_width": 1920, "frame_height": 1080}
    >>> write(frame_size(), writer, context)
    Traceback (most recent call last):
      ...
    UnusedContextValueError: frame_width, frame_height

In a similar way, list targets (declared with
:py:data:`TokenTypes.declare_list`) are also checked to ensure that every value
in the list was used up.

The inverse error of omitting required targets from the context also triggers an error.

    >>> context = {"custom_dimensions_flag": True}
    >>> write(frame_size(), writer, context)
    Traceback (most recent call last):
      ...
    MissingContextValueError: frame_width, frame_height

Sanity checks are also performed on the generator functions, for example making
sure the same target isn't used more than once (unless it is a list target).

These checks ensure that anything placed into a context dictionary *always*
have a corresponding representation in a generated bitstream and also that
anything which ends up in the bitstream must come from the context dictionary.


Structured Dictionaries
-----------------------

In previous sections we've seen how bitstreams can be deserialised and
serialised to and from nested hierarchies of context dictionaries. Though it is
possible to view, manipulate and define bitstreams from scratch in this form,
it can be tedious and laborious.

As an example, consider the ``parse_info()`` (10.5.1) header. In token-emitting
generator form it might be written as::

    def parse_info(state):
        yield Token(TokenTypes.nbits, 32, "parse_info_prefix")
        state["parse_code"] = yield Token(TokenTypes.nbits, 8, "parse_code")
        state["next_parse_offset"] = yield Token(TokenTypes.nbits, 32, "next_parse_offset")
        state["previous_parse_offset"] = yield Token(TokenTypes.nbits, 32, "previous_parse_offset")

This might yield a context dictionary as follows which, even pretty printed,
makes for difficult viewing::

    >>> context = read(parse_info(), reader)
    >>> pprint(context)
    {
        "parse_info_prefix": 1111638852,
        "parse_code": 200,
        "next_parse_offset": 0,
        "previous_parse_offset": 0,
    }

For example, both the ``parse_info_prefix`` and ``parse_code`` would be better
represented in hexadecimal (e.g. 0x42424344 and 0xC8, respectively). Further,
the ``parse_code`` is an enumerated value and would be better expressed still
by its human-readable name 'Low Delay Picture'.

As well as viewing the dictionary, constructing one by hand is fairly tedious,
requiring, for example, targets such as 'parse_info_prefix' to be filled out
every time. Further, mistakes such as misspelled target names will only show up
later when a :py:func:`read` or :py:func:`write` fails.

The :py:module:`vc2_conformance.structured_dict` module provides an alternative
to the standard Python :py:class:`dict` type providing numerous useful
features:

* **Default values can be provided.** This can save time populating many
  structures (e.g. by setting 'parse_info_prefix' read by parse_info() to the
  correct value).
* **Improved string representation.** Including changing the base numbers are
  printed in or showing the names of enumerated values.
* **The allowed entries are fixed ahead of time.** This ensures that no
  unexpected or misspelled target names can be used by accident.

We might define a structured dictionary to go with our ``parse_info`` generator
like so::

    from vc2_conformance.structured_dict import structured_dict, Value
    from vc2_conformance.formatters import Hex
    from vc2_conformance.tables import ParseCodes
    
    @structured_dict
    class ParseInfo(object):
        parse_info_prefix = Value(default=0x42424344, formatter=Hex(8))
        parse_code = Value(default=ParseCodes.end_of_sequence, enum=ParseCodes)
        next_parse_offset = Value(default=0)
        previous_parse_offset = Value(default=0)

We can demonstrate the key features like so::

    >>> # Values we don't pass to the constructor are assigned default values
    >>> pi = ParseInfo(previous_parse_offset=1234)
    
    >>> # Rich string representation
    >>> str(pi)
    ParseInfo:
      parse_info_prefix: 0x42424344
      parse_code: end_of_sequence (0x10)
      next_parse_offset: 0
      previous_parse_offset: 1234
    
    >>> # Spots mistakes
    >>> pi["parse-code"] = 123  # Should be pi["parse_code"] = 123
    Traceback (most recent call last):
      ...
    KeyError: parse-code

Because structured dictionaries are still dictionaries, you can pass them as
context dictionaries to :py:func:`write` and everything will work correctly::

    >>> write(parse_info(), writer, pi)  # Works!

However, when reading a bitstream with :py:func:`read`, the returned context
dictionaries will just be plain Python dictionaries. This behaviour can be
changed by emitting a :py:data:`TokenTypes.declare_context_type` token before
any targets in the context are used. For example::

    def parse_info(state):
        yield Token(TokenTypes.declare_context_type, ParseInfo, None)
        yield Token(TokenTypes.nbits, 32, "parse_info_prefix")
        state["parse_code"] = yield Token(TokenTypes.nbits, 8, "parse_code")
        state["next_parse_offset"] = yield Token(TokenTypes.nbits, 32, "next_parse_offset")
        state["previous_parse_offset"] = yield Token(TokenTypes.nbits, 32, "previous_parse_offset")

Alternatively the more concise :py:func:`context_type` decorator may be used
with identical effect::

    @context_type(ParseInfo)
    def parse_info(state):
        yield Token(TokenTypes.nbits, 32, "parse_info_prefix")
        state["parse_code"] = yield Token(TokenTypes.nbits, 8, "parse_code")
        state["next_parse_offset"] = yield Token(TokenTypes.nbits, 32, "next_parse_offset")
        state["previous_parse_offset"] = yield Token(TokenTypes.nbits, 32, "previous_parse_offset")

Now when reading the context dictionary will be an instance of our
``ParseInfo`` structured dict type::

    >>> context = read(parse_info(), reader)
    >>> str(context)
    ParseInfo:
      parse_info_prefix: 0x42424344
      parse_code: low_delay_picture (0xC8)
      next_parse_offset: 0
      previous_parse_offset: 0



Computed Values
---------------

Certain VC-2 bitstream structures are sized according to values defined over
the course of several earlier stream structures. For example, the number of
coefficients contained in a single picture slice is a function of earlier
headers in the stream. Typically these values are computed by the VC-2 pseudo
code and stored in various state variables which might not be easily
accessible.

:py:data:`TokenTypes.computed_value` tokens type may be used to write computed
values into the current context, for example the computed dimensions in a
picture slice. These targets are *always* written and never read -- even during
:py;func:`write`. The :py:func:`update_computed_values` function may be used to
update the computed values in a context dictionary hierarchy without reading or
writing the bitstream. This might be useful when hand-assembling bitstreams.

As an example::

    def hq_slice(state, sx, sy):
        # All of the following are necessary to work out the number of
        # coefficients in each subband slice...
        yield Token(TokenTypes.computed_value, sx, "sx_")
        yield Token(TokenTypes.computed_value, sy, "sy_")
        yield Token(TokenTypes.computed_value, state["slices_y"], "slices_y_")
        yield Token(TokenTypes.computed_value, state["slices_x"], "slices_x_")
        yield Token(TokenTypes.computed_value, state["slices_y"], "slices_y_")
        yield Token(TokenTypes.computed_value, state["luma_width"], "luma_width_")
        yield Token(TokenTypes.computed_value, state["luma_height"], "luma_height")
        yield Token(TokenTypes.computed_value, state["color_diff_width"], "color_diff_width_")
        yield Token(TokenTypes.computed_value, state["color_diff_height"], "color_diff_height_")
        yield Token(TokenTypes.computed_value, state["dwt_depth"], "dwt_depth_")
        yield Token(TokenTypes.computed_value, state["dwt_depth_ho"], "dwt_depth_ho_")
        # ...

.. warning::

    Computed values should be used sparingly and only in cases where it would
    otherwise be difficult to interpret the values in a deserialised bitstream.

.. note::

    It is recommended that computed value target names are suffixed or prefixed
    with an underscore to differentiate them from actual bitstream values.

.. note::

    Values *prefixed* with an underscore are hidden in the string
    representation of structured dictionaries.

"""

from collections import namedtuple

from enum import Enum

try:
    # Python 3.6+
    from enum import auto
except ImportError:
    # Crude fall-back for 'auto' in Python 2 and older versions of Python 3.x.
    from itertools import count
    from functools import partial
    auto = partial(next, count())

from functools import wraps

from vc2_conformance.bitstream import (
    BoundedReader,
    BoundedWriter,
)

from vc2_conformance.bitstream._integer_io import (
    read_bits,
    write_bits,
    read_bytes,
    write_bytes,
    exp_golomb_length,
    read_exp_golomb,
    write_exp_golomb,
    signed_exp_golomb_length,
    read_signed_exp_golomb,
    write_signed_exp_golomb,
)


Token = namedtuple("Token", "type,argument,target")
"""
A token to be generated by a token generator function.

.. note::
    
    All of the functions in this module will accept a standard python 3-tuple
    in place of this type. Using native Python tuples has a slightly lower
    performance overhead than the :py:class:`Token` type. For particularly
    dense parts of the bitstream (e.g. transform components), a 20-30%
    performance improvement is obtained by using native tuples.

Parameters
----------
type : :py:class:`TokenTypes`
    The token type which defines the meaning of this token.
argument
    The argument to the token. This may be None for some token types. See
    :py:class:`TokenTypes` for the expected argument for each type of token.
target : str or None
    The name of the target value associated with this token in the current
    context dictionary. See :py:class:`TokenTypes` to determine if a target
    must be specified for a given token type.
"""


class TokenTypes(Enum):
    """
    The complete set of token types.
    """
    
    ###########################################################################
    # Value tokens
    #
    # The following token types correspond to read/write operations of
    # primitive values in the bitstream.
    ###########################################################################
    
    nop = auto()
    """
    ``yield Token(TokenTypes.nop, None, None) -> None``
    
    A 'no operation' token which has no effect. Intended for internal use:
    there is little reason to emit this in a generator.
    
    * **Argument:** The argument must always be None.
    * **Target:** The argument must always be None.
    * **Sent value:** Will always be None.
    """
    
    bool = auto()
    """
    ``yield Token(TokenTypes.bool, None, target) -> bool``
    
    Reads or writes a boolean in a bitstream (as per (A.3.2) read_bool()).
    
    * **Argument:** The argument must always be None.
    * **Target:** Stores or uses the value in the specified context entry.
    * **Sent value:** The read/written bool will be sent to the generator.
    """
    
    nbits = auto()
    """
    ``yield Token(TokenTypes.nbits, num_bits, target) -> int``
    
    Reads or writes an fixed-length unsigned integer in a bitstream (as per
    (A.3.3) read_nbits()).
    
    * **Argument:** The argument must be the length of the integer in bits.
    * **Target:** Stores or uses the value in the specified context entry. If a
      value which does not fit in the length specified is encountered an
      :py:exc:`OutOfRangeError` will be thrown.
    * **Sent value:** The read/written int will be sent to the generator.
    """
    
    bitarray = auto()
    """
    ``yield Token(TokenTypes.bitarray, num_bits, target) -> bitarray()``
    
    Reads or writes an fixed-length string of bits from the bitstream as a
    :py:class:`bitarray.bitarray`. This may be a more sensible type for holding
    unpredictably sized non-integer binary values such as padding bits.
    
    * **Argument:** The argument must be number of bits to read.
    * **Target:** Stores or uses the value in the specified context entry. If a
      value which does not fit in the length specified is encountered an
      :py:exc:`OutOfRangeError` will be thrown.
    * **Sent value:** The read/written :py:class:`bitarray.bitarray` will be
      sent to the generator.
    """
    
    bytes = auto()
    """
    ``yield Token(TokenTypes.bytes, num_bytes, target) -> bytes()``
    
    Reads or writes an fixed-length :py:class:`bytes` string from the
    bitstream. This is a more convenient alternative to
    :py:data:`TokenTypes.nbits` or :py:data:`TokenTypes.bitarray` when large
    blocks of data are to be read but not treated as integers.
    
    * **Argument:** The argument must be the length of the byte string in bytes
      (not bits).
    * **Target:** Stores or uses the value in the specified context entry. If a
      value which does not fit in the length specified is encountered an
      :py:exc:`OutOfRangeError` will be thrown.
    * **Sent value:** The read/written :py:class:`bytes` string will be sent to
      the generator.
    """
    
    uint = auto()
    """
    ``yield Token(TokenTypes.uint, None, target) -> int``
    
    A variable-length, unsigned exp-golomb integer in a bitstream (as per
    (A.4.3) read_uint()).
    
    * **Argument:** The argument must always be None.
    * **Target:** Stores or uses the value in the specified context entry. If a
      negative value encountered an :py:exc:`OutOfRangeError` will be thrown.
    * **Sent value:** The read/written int will be sent to the generator.
    """
    
    sint = auto()
    """
    ``yield Token(TokenTypes.sint, None, target) -> int``
    
    A variable-length, signed exp-golomb integer in a bitstream (as per (A.4.4)
    read_sint()).
    
    * **Argument:** The argument must always be None.
    * **Target:** Stores or uses the value in the specified context entry.
    * **Sent value:** The read/written int will be sent to the generator.
    """
    
    ###########################################################################
    # I/O Control Tokens
    #
    # The following token types enact low-level I/O control operations during
    # stream reading/writing.
    ###########################################################################
    
    byte_align = auto()
    """
    ``yield Token(TokenTypes.byte_align, None, target) -> bitarray``
    
    Advance in the bitstream to the next whole byte boundary, if not already on
    one (as per (A.2.4) byte_align()).
    
    * **Argument:** The argument must always be None.
    * **Target:** Stores or uses the padding bits in the specified context
      entry. If a value stored in the context is of the wrong length, it will
      be silently truncated or zero-padded on the left-hand side.
    * **Sent value:** The read/written padding bits will be sent to the
      generator in a :py:class:`bitarray.bitarray`.
    """
    
    bounded_block_begin = auto()
    """
    ``yield Token(TokenTypes.bounded_block_begin, length_bits, None) -> None``
    
    Defines the start of a bounded block (as per (A.4.2)). Must be followed
    by a matching :py:data:`TokenTypes.bounded_block_end`.
    
    Bits 'read' beyond the end of the block will be treated as '1'. Bits
    'written' past the end of the block must be '1' and a :py:exc:`ValueError`
    will be thrown if not.
    
    * **Argument:** The argument must be the length of the block, in bits.
    * **Target:** Must always be None.
    * **Sent value:** Will always be None.
    """
    
    bounded_block_end = auto()
    """
    ``yield Token(TokenTypes.bounded_block_end, None, target) -> bitarray``
    
    Defines the end of a bounded block and flushes any unused bits (as per
    (A.4.2) flush_inputb()). Must be proceeded by a matching
    :py:data:`TokenTypes.bounded_block_begin`.
    
    * **Argument:** The argument must always be None.
    * **Target:** Stores or uses any unused bits at the end of the block in the
      specified context entry. If a value stored in the context is of the
      wrong length, it will be silently truncated or zero-padded on the
      left-hand side.
    * **Sent value:** The read/written unused bits will be sent to the
      generator in a :py:class:`bitarray.bitarray`.
    """
    
    ###########################################################################
    # Structure Control Tokens
    #
    # The following token types are used to influence the structure of the
    # context dictionary.
    ###########################################################################
    
    declare_list = auto()
    """
    ``yield Token(TokenTypes.declare_list, None, target) -> None``
    
    Declares that the specified target should be treated as a :py:class:`list`.
    Whenever this target is used by future tokens, values will be read/written
    sequentially from the list it contains.
    
    * **Argument:** Must always be None.
    * **Target:** The name of the target to treat as a list.
    * **Sent value:** Will always be None.
    """
    
    declare_context_type = auto()
    """
    ``yield Token(TokenTypes.declare_context_type, dict_type, None) -> None``
    
    When reading a bitstream, :py:func:`read` must initially create an empty
    context dictionary to use. By default a native Python :py:class:`dict` will
    be used but, by producing a :py:data:`TokenTypes.declare_context_type`
    token an alternative type may be used. During other operations, this token
    has no effect.
    
    * **Argument:** Must be a :py:class:`dict`-like type.
    * **Target:** Must always be None.
    * **Sent value:** Will always be None.
    """
    
    nested_context_enter = auto()
    """
    ``yield Token(TokenTypes.nested_context_enter, None, target) -> None``
    
    Creates and/or enters the nested context dictionary inside a specified
    target of the current context dictionary. Must be followed later by a
    matching :py:data:`TokenTypes.nested_context_leave`.
    
    * **Argument:** Must always be None.
    * **Target:** Must be the name of the target in the current context in
      which the new nested context is/will be stored.
    * **Sent value:** Will always be None.
    """
    
    nested_context_leave = auto()
    """
    ``yield Token(TokenTypes.nested_context_leave, None, None) -> None``
    
    Leaves a nested context dictionary. Must be proceeded by a matching
    :py:data:`TokenTypes.nested_context_enter`.
    
    * **Argument:** Must always be None.
    * **Target:** Must always be None.
    * **Sent value:** Will always be None.
    """
    
    ###########################################################################
    # Execution Control Tokens
    #
    # The following token types may be used to temporarily use tokens produced
    # by another Token-emitting generator.
    ###########################################################################
    
    use = auto()
    """
    ``yield Token(TokenTypes.use, generator, None) -> return_value``
    
    Processes all of the tokens emitted by the supplied generator before
    continuing.
    
    This is equivalent to writing ``yield from generator`` in Python 3 but has
    significantly lower runtime overhead and is also compatible with Python 2.
    
    * **Argument:** Must be a :py:class:`Token`-emitting generator.
    * **Target:** Must always be None.
    * **Sent value:** The value returned by the supplied generator will be
      sent. (See also: :py:exc:`Return`.)
    """
    
    nest = auto()
    """
    ``yield Token(TokenTypes.nest, generator, target) -> return_value``
    
    Processes the tokens emitted by the supplied generator inside a nested
    context dictionary.
    
    A shorthand for the following sequence of tokens::
    
        yield Token(TokenTypes.nested_context_enter, None, target)
        return_value = yield Token(TokenTypes.use, generator, None)
        yield Token(TokenTypes.nested_context_leave, None, None)
    
    * **Argument:** Must be a :py:class:`Token`-emitting generator.
    * **Target:** The name of the target in which to create/use the nested
      context dictionary.
    * **Sent value:** The value returned by the supplied generator will be
      sent. (See also: :py:exc:`Return`.)
    """
    
    ###########################################################################
    # Computed Value Token
    #
    # Used to allow fixed, non-bitstream values to be set in targets in the
    # current context based on values computed in the generator.
    ###########################################################################
    
    computed_value = auto()
    """
    ``yield Token(TokenTypes.computed_value, value, target) -> None``
    
    Places a value computed by the token-emitting generator function into the
    named target in the current context, without reading or writing anything
    into the bitstream. Any existing value in the context will be overwritten.
    
    This operation always results in the target being overwritten in the
    context, even during :py:func:`write`.
    
    This token type should be used sparingly. It is recommended that target
    names used with this token type have either an underscore prefix or suffix.
    
    * **Argument:** A value to set in the context.
    * **Target:** The target to set the value to in the context.
    * **Sent value:** Will always be None.
    """

class Return(StopIteration):
    """
    An exception intended for use in returning values from a generator in a
    manner which is backward compatible with Python 2.
    
    The generator should use this exception in the same way as the return
    statement might be used in Python 3::
    
        >>> # In Python 2 and backward-compatible Python 3 code:
        >>> def generator():
        ...     for n in range(5):
        ...         yield n
        ...     raise Return("The End")
        
        >>> # In Python 3 only
        >>> def generator():
        ...     for n in range(5):
        ...         yield n
        ...     return "The End"

    The code which is driving the generator should use the following pattern to
    support generators which raise this :py:exc:`Return` exception and
    generators which use a Python 3 return statement::

        >>> try:
        ...     g = generator()
        ...     while True:
        ...         print("Generated: {!r}".format(next(g)))
        ... except StopIteration as r:   # Except on StopIteration, not Return
        ...     # Use 'getattr' with a default value of None in case the
        ...     # 'value' field is not present (i.e. Python 2 StopIteration).
        ...     print("Returned: {!r}".format(getattr(r, "value", None)))
        Generated: 0
        Generated: 1
        Generated: 2
        Generated: 3
        Generated: 4
        Returned: 'The End'
    """
    
    def __init__(self, value=None):
        self.value = value
    
    def __str__(self):
        return str(self.value)

def read(generator, reader, return_generator_return_value=False):
    """
    Read a bitstream described by the specified token-emitting generator,
    returning the populated context dictionary.
    
    Parameters
    ==========
    generator : generator -> :py:class:`Token`
        A generator function which emits :py:class:`Token` tuples (or native
        3-tuples) which describe how the bitstream should be formatted.
    reader : :py:class:`BitstreamReader`
    return_generator_value : bool
        If False, the default, this function will return only the final context
        dictionary. If set to True, this generator will return both the final
        context and the generator's final return value in a 2-tuple.
    """
    try:
        next(read_interruptable(
            generator,
            reader,
            return_generator_return_value=return_generator_return_value,
        ))
        assert False, "read_interruptable should not have paused"
    except StopIteration as r:
        return getattr(r, "value", None)


def read_interruptable(generator, reader, interrupt=None,
                       return_generator_return_value=False):
    """
    A generator which reads a bitstream described by the specified
    token-emitting generator, pausing when required.
    
    Parameters
    ==========
    generator : generator -> :py:class:`Token`
    reader : :py:class:`BitstreamReader`
    interrupt : None or function(:py;class:`TokenParserStateMachine`, :py:class:`Token`) -> bool
        If provided, this function will be called after every read operation
        and, if the function returns True, the :py:func:`read_interruptable`
        generator will yield. If false, the generator wlil move onto the next
        value without yielding.
        
        The :py:class:`TokenParserStateMachine` and token passed to the
        interrupt function reveal the current internal state and token which
        has just been processed. These values should be treated as strictly
        read-only.
        
        As an example, the following lambda function could be used to interrupt
        parsing once a certain bitstream offset is reached::
        
            # Interrupt after 100 bytes
            lambda fsm, token: fsm.io.tell() >= (100, 7)
        
    return_generator_value : bool
    
    Generates
    =========
    (:py:class:`TokenParserStateMachine`, :py:class:`Token`)
        When this generator yields, it produces a
        2-tuple describing with the same values as the interrupt argument.
        These values may be used (in a strictly read-only fashion) to inspect
        the current partially read data, for example::
        
            >>> g = yield read_interruptable(...)
            >>> fsm, token = next(g)
            
            >>> # Print the token we just generated
            >>> str(token)
            
            >>> # Print the partially populated context dictionary
            >>> str(fsm.root_context)
            ...
    
    Raises
    ======
    :py:exc:`Return`
        When the token generator is exhausted. :py:exc:`Return` is raised with
        ``value`` set to the (top-level) context dictionary populated during
        reading or, if return_generator_value argument is True, a 2-tuple
        (context, generator_return_value).
    """
    fsm = TokenParserStateMachine(generator, reader)
    
    try:
        # The value to be sent to the generator upon the next iteration.
        # Usually the last value to have been read from the stream.
        latest_value = None
        
        while True:
            try:
                # Get the next token
                original_token, token_type, token_argument, token_target = fsm.generator_send(latest_value)
                
                # Read values according to the value type
                if token_type is TokenTypes.nop:
                    assert token_argument is None
                    assert token_target is None
                    latest_value = None
                elif token_type is TokenTypes.bool:
                    assert token_argument is None
                    assert token_target is not None
                    latest_value = bool(fsm.io.read_bit())
                elif token_type is TokenTypes.nbits:
                    assert token_target is not None
                    latest_value = fsm.io.read_nbits(token_argument)
                elif token_type is TokenTypes.bitarray:
                    assert token_target is not None
                    latest_value = fsm.io.read_bitarray(token_argument)
                elif token_type is TokenTypes.bytes:
                    assert token_target is not None
                    latest_value = fsm.io.read_bytes(token_argument)
                elif token_type is TokenTypes.uint:
                    assert token_argument is None
                    assert token_target is not None
                    latest_value = fsm.io.read_uint()
                elif token_type is TokenTypes.sint:
                    assert token_argument is None
                    assert token_target is not None
                    latest_value = fsm.io.read_sint()
                else:
                    raise UnknownTokenTypeError(token_type)
                
                # Store the new value in the context
                if token_target is not None:
                    fsm.set_context_value(token_target, latest_value)
                
                # Pause if requested
                if interrupt is not None and interrupt(fsm, original_token):
                    yield (fsm, original_token)
            
            except StopIteration as r:
                # Capture the return value of the final generator -- it may be
                # returned here.
                return_value = getattr(r, "value", None)
                break
            except Exception as e:
                # The processes above may produce exceptions if a validation
                # step fails. Send these up into the generator to produce more
                # helpful stack traces for users.
                fsm.generator_throw(e)
    finally:
        fsm.generator_close()
    
    fsm.verify_complete()
    
    if return_generator_return_value:
        raise Return((token_generator.context, return_value))
    else:
        raise Return(context)


def write(generator, writer, context, return_generator_return_value=False):
    """
    Generate a bitstream described by the specified token-emitting generator
    and context dictionary and write to the the specified
    :py:class:`BitstreamWriter`.
    
    Returns the context dictionary. This may actually be a modified copy of the
    original context dictionary if the generator required this dictionary to
    change type (via a :py:data:`TokenTypes.declare_context_type` token.).
    
    Parameters
    ==========
    generator : generator -> :py:class:`Token`
        A generator function which emits :py:class:`Token` tuples (or native
        3-tuples) which describe how the bitstream should be formatted.
    writer : :py:class:`BitstreamWriter`
    return_generator_value : bool
        If False, the default, this function will return only the final context
        dictionary. If set to True, this generator will return both the final
        context and the generator's final return value in a 2-tuple.
    """
    try:
        next(write_interruptable(
            generator,
            writer,
            return_generator_return_value=return_generator_return_value,
        ))
        assert False, "write_interruptable should not have paused"
    except StopIteration as r:
        return getattr(r, "value", None)


def write_interruptable(generator, writer, context, interrupt=None,
                        return_generator_return_value=False):
    """
    A generator which writes a bitstream described by the specified
    token-emitting generator and context dictionary, pausing when required.
    
    Parameters
    ==========
    generator : generator -> :py:class:`Token`
    writer : :py:class:`BitstreamWriter`
    interrupt : None or function(:py;class:`TokenParserStateMachine`, :py:class:`Token`) -> bool
        If provided, this function will be called after every write operation
        and, if the function returns True, the :py:func:`write_interruptable`
        generator will yield. If false, the generator wlil move onto the next
        value without yielding.
        
        The :py:class:`TokenParserStateMachine` and token passed to the
        interrupt function reveal the current internal state and token which
        has just been processed. These values should be treated as strictly
        read-only.
        
        As an example, the following lambda function could be used to interrupt
        parsing once a certain bitstream offset is reached::
        
            # Interrupt after 100 bytes
            lambda fsm, token: fsm.io.tell() >= (100, 7)
        
    return_generator_value : bool
    
    Generates
    =========
    (:py:class:`TokenParserStateMachine`, :py:class:`Token`)
        When this generator yields, it produces a
        2-tuple describing with the same values as the interrupt argument.
        These values may be used (in a strictly read-only fashion) to inspect
        write progress::
        
            >>> g = yield write_interruptable(...)
            >>> fsm, token = next(g)
            
            >>> # Print out the field we've got up to
            >>> fsm.describe_path(token.target)
            SequenceHeader['source_parameters']['frame_size']['frame_width']
    
    Raises
    ======
    :py:exc:`Return`
        When the token generator is exhausted. :py:exc:`Return` is raised with
        ``value`` set to the (top-level) context dictionary used during
        generation (which  may have been replaced with one of a different
        type). If return_generator_value argument is True, a 2-tuple (context,
        generator_return_value).
    """
    fsm = TokenParserStateMachine(generator, writer)
    
    try:
        # The value to be written and sent to the generator upon the
        # next iteration.
        latest_value = None
        
        while True:
            try:
                # Get the next token
                original_token, token_type, token_argument, token_target = fsm.generator_send(latest_value)
                
                # Get the value to be written
                if token_target is not None:
                    latest_value = fsm.get_context_value(token_target)
                else:
                    latest_value = None
                
                # Write values according to the value type
                if token_type is TokenTypes.nop:
                    assert token_argument is None
                    assert token_target is None
                elif token_type is TokenTypes.bool:
                    assert token_argument is None
                    assert token_target is not None
                    fsm.io.write_bit(latest_value)
                elif token_type is TokenTypes.nbits:
                    assert token_target is not None
                    fsm.io.write_nbits(token_argument, latest_value)
                elif token_type is TokenTypes.bitarray:
                    assert token_target is not None
                    fsm.io.write_bitarray(token_argument, latest_value)
                elif token_type is TokenTypes.bytes:
                    assert token_target is not None
                    fsm.io.write_bytes(token_argument, latest_value)
                elif token_type is TokenTypes.uint:
                    assert token_argument is None
                    assert token_target is not None
                    fsm.io.write_uint(latest_value)
                elif token_type is TokenTypes.sint:
                    assert token_argument is None
                    assert token_target is not None
                    fsm.io.write_sint(latest_value)
                else:
                    raise UnknownTokenTypeError(token_type)
                
                # Pause if requested
                if interrupt is not None and interrupt(fsm, original_token):
                    yield (fsm, original_token)
            
            except StopIteration as r:
                # Capture the return value of the final generator -- it may be
                # returned here.
                return_value = getattr(r, "value", None)
                break
            except Exception as e:
                # The processes above may produce exceptions if a validation
                # step fails. Send these up into the generator to produce more
                # helpful stack traces for users.
                fsm.generator_throw(e)
    finally:
        fsm.generator_close()
    
    fsm.verify_complete()
    
    if return_generator_return_value:
        raise Return((token_generator.context, return_value))
    else:
        raise Return(context)


class TokenParserStateMachine(object):
    """
    The procedures for reading, writing and otherwise manipulating bitstreams
    described by :py:class:`Token`-emitting generators are largely the same
    with the exception of the read and write operations. This class implements
    the basic components required to parse a :py:class:`Token` stream.
    
    Attributes
    ==========
    generator : generator function
        The current token-emitting generator function.
    io : :py:class:`BitstreamReader` or :py:class:`BitstreamWriter`
        The current I/O interface in use.
    context : dict
        The current context dictionary.
    
    Internal Attributes
    ===================
    context_indices : {token: True or int, ...}
        Logs which context targets have been referenced by a token. Initially
        empty.
        
        When a non-list target is used, a corresponding entry is set to True in
        this dictionary. Re-use of a target is prevented by checking that the
        required target does not already appear in this dictionary.
        
        When a :py:data:`TokenTypes.declare_list` token is encountered, the
        corresponding entry in context_indices is set to to 0. Subsequent uses
        of that target should increment the counter.
    generator_stack : [generator, ...]
        A stack of token-emitting generators which have been suspended.
        Generators are suspended when they emit a :py:data:`TokenTypes.use`
        token and are popped off the stack and resumed when the new generator
        expires.
    io_stack : [IO, ...]
        A stack of :py:class:`BitstreamReader` and py:class:`BoundedReader` or
        :py:class:`BitstreamWriter` and py:class:`BoundedWriter` objects.  The
        current IO interface is pushed onto the stack when a
        :py:data:`TokenTypes.bounded_block_begin` token is encountered and
        popped off again when :py:data:`TokenTypes.bounded_block_end`  is
        emitted.
    context_stack : [<context dict>, ...]
    context_indices_stack : [<context_indices dict>, ...]
    target_stack : [str, ...]
        Whenever a :py:data:`TokenTypes.nested_context_enter` token is
        encountered, the current context and context_indices dictionaries and
        the specified target name are pushed onto their respective stacks. The
        :py:data:`TokenTypes.nested_context_leave` token pops these values
        again.
    """
    
    def __init__(self, generator, io, context=None):
        """
        Parameters
        ==========
        generator : generator
            The token-emitting generator function in use initially.
        io : :py:class:`BitstreamReader` or :py:class:`BitstreamWriter`
            The current I/O interface to use initially.
        context : dict
            The initial context dictionary.
        """
        self.generator = generator
        self.io = io
        self.context = context if context is not None else {}
        self.context_indices = {}
        
        self.generator_stack = []
        self.io_stack = []
        self.context_stack = []
        self.context_indices_stack = []
        self.target_stack = []
    
    @property
    def root_context(self):
        """
        Get the top-level context dictionary.
        
        See also: :py:attr:`context` which contains the currently active
        context dictionary.
        """
        if self.context_stack:
            return self.context_stack[0]
        else:
            return self.context
    
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
        full_context_stack = self.context_stack
        full_context_indices_stack = self.context_indices_stack
        full_target_stack = self.target_stack
        if target is not None:
            full_context_stack += [self.context]
            full_context_indices_stack += [self.context_indices]
            full_target_stack += [target]
        
        root_type = self.root_context.__class__.__name__
        
        return "{}{}".format(
            root_type,
            "".join(
                (
                    "[{!r}]".format(target)
                    if context_indices[target] is True else
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
    
    def _replace_context_in_parent(self):
        """
        When :py:data:`TokenTypes.declare_context_type` is used, the new
        context dictionary must be substituted in place of the old context
        dictionary in any parent context. This method should be called to carry
        this out after the 'context' dictionary has been replaced.
        """
        if self.context_stack:
            parent_context = self.context_stack[-1]
            parent_target = self.target_stack[-1]
            parent_target_index = self.context_indices_stack[-1][parent_target]
            
            if parent_target_index is True:
                # The child context is in a normal target in the parent context
                # dict
                parent_context[parent_target] = self.context
            else:
                # The child context is in a list target in the parent context dict
                # (NB: The parent_target_index value is the *next* index in the
                # list, hence being decremented by one here).
                parent_context[parent_target][parent_target_index-1] = self.context
        else:
            # Context stack is empty so there must be no parent to update!
            pass

    def _verify_context_is_complete(self):
        """
        Verify that the current context is 'complete'. That is, every entry in
        the context dict has been used and that every element in any lists has
        been used too.
        """
        for target, value in self.context.items():
            if target not in self.context_indices:
                # Target not used
                raise UnusedTargetError(target)
            else:
                index = self.context_indices[target]
                if index is True:
                    # Target was used and it was not a list
                    pass
                elif index != len(value):
                    # Target was used and was a list, but not all entries were
                    # used!
                    raise UnusedTargetError("{}[{}:{}]".format(
                        target, len(value), index))

    def verify_complete(self):
        """
        Verify that all values in the current context have been used and that
        no bounded blocks or nested contexts have been left over.
        """
        self._verify_context_is_complete()
        
        if self.context_stack:
            raise UnclosedNestedContextError(", ".join(
                (
                    target
                    if self.context_indices[target] is True else
                    "{}[{}]".format(target, self.context_indices[target])
                )
                for target in self.target_stack
            ))
        
        if self.io_stack:
            raise UnclosedBoundedBlockError("{} block{} left unclosed".format(
                len(self.io_stack),
                "s" if len(self.io_stack) != 1 else "",
            ))

    def _declare_context_value_is_list(self, target):
        """
        Declares a value in the current target to be a list. Throws an error if
        this target has already been used or declared as a list. If the value
        does not exist yet in the context, it will be initialised with an empty
        list. If the value does exist, it will be checked to ensure that it is
        a list.
        """
        # Has the target already been used or delcared?
        if target in self.context_indices:
            raise ReusedTargetError(target)
        
        if target not in self.context:
            # Target not yet defined in context; create a new empty list
            self.context[target] = []
        else:
            # The target already exists in the context; make sure it is a list
            if not isinstance(self.context[target], list):
                raise ListTargetContainsNonListError(
                    "{} contains {!r} (which is not a list)".format(
                        target, self.context[target]))
        
        context_indices[target] = 0

    def set_context_value(self, target, value):
        """
        Add a value to a context dictionary, checking that the value has not
        already been set and extending list targets if necessary.
        
        Do not use this method and :py:attr:`get_context_value` on the same
        target!
        """
        if target not in self.context_indices:
            # Case: This target has not been declared as a list and this is the
            # first time it has been accessed.
            self.context[target] = value
            self.context_indices[target] = True
        elif self.context_indices[target] is True:
            # Case: This target has not been declared as a list and has already
            # been accessed.
            raise ReusedTargetError(target)
        else:
            # Case: This target has been declared as a list.
            i = self.context_indices[target]
            self.context_indices[target] += 1
            
            target_list = self.context[target]
            if len(target_list) == i:
                # List is being filled for the first time
                target_list.append(value)
            else:
                # List already exists and we're updating it.
                target_list[i] = value

    def get_context_value(self, target):
        """
        Get a value from the context dictionary, checking that the value has not
        already been accessed and moving on to the next list item for list
        targets.
        
        Do not use this method and :py:attr:`set_context_value` on the same
        target!
        """
        if target not in self.context_indices:
            # Case: This target is not a list and has not been used before
            self.context_indices[target] = True
            return self.context[target]
        elif self.context_indices[target] is True:
            # Case: This target is not a list but has already been used
            raise ReusedTargetError(target)
        else:
            # Case: This target has been declared as a list.
            i = self.context_indices[target]
            self.context_indices[target] += 1
            
            return self.context[target][i]

    def generator_send(self, value):
        """
        Send a value to the current generator and return the next value-only
        token. Other token types will be handled internally and converted into
        a simple value-only token and returned.
        
        Raises a :py:exc:`StopIteration` exception when all generators are
        exhausted.
        
        Returns a 4-tuple (original_token, new_token_type, new_token_argument,
        new_token_target).
        """
        # If the current generator completes, we must turn to the next
        # available generator on the generator_stack. We must work our way down
        # the stack until either we find a generator which produces a token or
        # we use up all of the generators.
        while True:
            try:
                # Try to get the next token
                original_token = self.generator.send(latest_value)
                break
            except StopIteration as r:
                # The generator has ended, capture the returned value
                latest_value = getattr(r, "value", None)
                
                # Move on to the next generator in the stack
                if self.generator_stack:
                    self.generator = self.generator_stack.pop()
                    continue
                else:
                    # The final generator has been exhausted, allow the
                    # StopIteration to propagate
                    raise
        
        token_type, token_argument, token_target = original_token
        
        # The various 'special' (non value reading token types) may be handled
        # in two steps. First whatever special state-machine affecting action
        # is performed next a value may (or more usually, may not) be
        # written/read in the bitstream. This function implements the first of
        # these two jobs and emits a new token (of value type only) which is
        # responsible for any bitstream reads/writes.
        if token_type is TokenTypes.byte_align:
            # byte_align -> bitarray with implied size
            assert token_argument is None
            assert token_target is not None
            _, bits = self.io.tell()
            token_type = TokenTypes.bitarray
            token_argument = 0 if bits == 7 else (bits + 1)
        elif token_type is TokenTypes.bounded_block_begin:
            # bounded_block_begin -> nop, wrapping the IO in a
            # Bounded equivalent
            assert token_argument is not None
            assert token_target is None
            
            self.io_stack.append(self.io)
            if isinstance(self.io, BitstreamReader):
                self.io = BoundedReader(self.io, token_argument)
            else:
                self.io = BoundedWriter(self.io, token_argument)
            
            token_type = TokenTypes.nop
            token_argument = None
            token_target = None
        elif token_type is TokenTypes.bounded_block_end:
            # bounded_block_end -> bitarray with padding bits with implied
            # length, restoring the original IO
            assert token_argument is None
            assert token_target is not None
            
            token_type = TokenTypes.bitarray
            token_argument = self.io.bits_remaining
            
            self.io = self.io_stack.pop()
        elif token_type is TokenTypes.declare_list:
            # declare_list -> nop, setting the target to an empty list and
            # initialising the counter
            assert token_argument is None
            assert token_target is not None
            
            self._declare_context_value_is_list(token_target)
            
            token_type = TokenTypes.nop
            token_target = None
        elif token_type is TokenTypes.declare_context_type:
            # declare_context_type -> nop, replacing the context dictionary with
            # one of the new type (if necessary)
            assert token_argument is not None
            assert token_target is None
            
            # Only replace the type if necessary to avoid unnecessary copying.
            if type(self.context) is not token_argument:
                self.context = token_argument(self.context)
                self._replace_context_in_parent()
            
            token_type = TokenTypes.nop
            token_argument = None
        elif token_type is TokenTypes.nested_context_enter:
            # nested_context_enter -> nop, creating a new context
            # dictionary and inserting it onto the context stack
            assert token_argument is None
            assert token_target is not None
            
            new_context = {}
            
            # Insert the new context into the current context at the
            # specified token
            self.set_context_value(token_target, new_context)
            
            # Push the old context onto the stack
            self.context_stack.append(self.context)
            self.context_indices_stack.append(self.context_indices)
            self.target_stack.append(token_target)
            
            self.context = new_context
            self.context_indices = {}
            
            token_type = TokenTypes.nop
            token_target = None
        elif token_type is TokenTypes.nested_context_leave:
            # nested_context_leave -> nop, pop the old context off the
            # stack.
            assert token_argument is None
            assert token_target is None
            
            self._verify_context_is_complete()
            
            self.context = self.context_stack.pop()
            self.context_indices = self.context_indices_stack.pop()
            self.target_stack.pop()
            
            token_type = TokenTypes.nop
        elif token_type is TokenTypes.use:
            # use -> nop, pushing the current generator onto the stack
            assert token_argument is not None
            assert token_target is None
            
            self.generator_stack.push(self.generator)
            self.generator = token_argument
            
            token_type = TokenTypes.nop
            token_argument = None
        elif token_type is TokenTypes.nest:
            # use -> nop, pushing the current generator onto the stack
            assert token_argument is not None
            assert token_target is not None
            
            self.generator_stack.push(self.generator)
            self.generator = nest_generator(token_argument, token_target)
            
            token_type = TokenTypes.nop
            token_argument = None
            token_target = None
        elif token_type is TokenTypes.computed_value:
            # computed_value -> nop, writing the value into the context
            assert token_argument is not None
            assert token_target is not None
            
            self._set_context_value(token_target, token_argument)
            
            token_type = TokenTypes.nop
            token_argument = None
            token_target = None
        
        return (original_token, token_type, token_argument, token_target)
    
    def generator_throw(self, exception):
        """
        Throw an exception up into the current generator. If this generator
        tries to catch the exception, the exception will be re-thrown
        immediately afterwards.
        """
        try:
            self.generator.throw(exception)
        except StopIteration:
            pass
        
        # Generator absorbed the error (either by continuing or exiting
        # cleanly), re-throw it here
        raise exception
    
    def generator_close(self):
        """
        Close-down the current generator (and any stacked generators. Use this
        when execution should be halted early.
        """
        self.generator.close()
        for generator in self.generator_stack:
            generator.close()


def nest_generator(generator, target):
    """
    Intended for internal use but could be used externally in principle.
    
    A token-emitting generator which, given another token-emitting generator
    implements the behaviour of :py:data:`TokenTypes.nest` using other token
    types.
    """
    yield Token(TokenTypes.nested_context_enter, None, target)
    return_value = yield Token(TokenTypes.use, generator, None)
    yield Token(TokenTypes.nested_context_leave, None, None)
    
    raise Return(return_value)


def context_type(dict_type):
    """
    A decorator for token-emitting generators which prefixes the values yielded
    with a :py:data:`TokenTypes.declare_context_type` declaring the current
    context dict to be of the specified type.
    
    Essentially the following::
    
        @context_type(FrameSize)
        def frame_size():
            # ...
    
    Is syntactic sugar equivalent to::
    
        def frame_size():
            yield Token(TokenTypes.declare_context_type, FrameSize, None)
            # ...
    """
    def wrap(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            yield Token(TokenTypes.declare_context_type, dict_type, None)
            yield Token(TokenTypes.use, f(*args, **kwargs), None)
        return wrapper
    return wrap
