"""
The :py:mod:`vc2_conformance.pseudocode` module contains implementations of
many of the VC-2 pseudocode functions and associated data structures. In
particular, it includes everything which can be used as-is in the construction
of encoders, decoders and so on without any alterations.

The VC-2 pseudocode is augmented by a modest number of additional functions or
data structure fields. For instance, additional fields are added to
:py:class:`~vc2_conformance.pseudocode.state.State` which are used by
conformance checking routines and forward wavelet transform routines.


:py:mod:`vc2_conformance.pseudocode.arrays`
-------------------------------------------

.. automodule:: vc2_conformance.pseudocode.arrays
    :members:

:py:mod:`vc2_conformance.pseudocode.offsetting`
-----------------------------------------------

.. automodule:: vc2_conformance.pseudocode.offsetting
    :members:


:py:mod:`vc2_conformance.pseudocode.parse_code_functions`
---------------------------------------------------------

.. automodule:: vc2_conformance.pseudocode.parse_code_functions
    :members:


:py:mod:`vc2_conformance.pseudocode.picture_decoding`
-----------------------------------------------------

.. automodule:: vc2_conformance.pseudocode.picture_decoding
    :members:
    :exclude-members: SYNTHESIS_LIFTING_FUNCTION_TYPES

.. autodata:: vc2_conformance.pseudocode.picture_decoding.SYNTHESIS_LIFTING_FUNCTION_TYPES
    :annotation: = {...}


:py:mod:`vc2_conformance.pseudocode.picture_encoding`
-----------------------------------------------------

.. automodule:: vc2_conformance.pseudocode.picture_encoding
    :members:
    :exclude-members: ANALYSIS_LIFTING_FUNCTION_TYPES

.. autodata:: vc2_conformance.pseudocode.picture_encoding.ANALYSIS_LIFTING_FUNCTION_TYPES
    :annotation: = {...}


:py:mod:`vc2_conformance.pseudocode.quantization`
-------------------------------------------------

.. automodule:: vc2_conformance.pseudocode.quantization
    :members:


:py:mod:`vc2_conformance.pseudocode.slice_sizes`
------------------------------------------------

.. automodule:: vc2_conformance.pseudocode.slice_sizes
    :members:


:py:mod:`vc2_conformance.pseudocode.state`
------------------------------------------

.. automodule:: vc2_conformance.pseudocode.state
    :members:


:py:mod:`vc2_conformance.pseudocode.vc2_math`
---------------------------------------------

.. automodule:: vc2_conformance.pseudocode.vc2_math
    :members:


:py:mod:`vc2_conformance.pseudocode.video_parameters`
-----------------------------------------------------

.. automodule:: vc2_conformance.pseudocode.video_parameters
    :members:

:py:mod:`vc2_conformance.pseudocode.metadata`
---------------------------------------------

.. automodule:: vc2_conformance.pseudocode.metadata

"""

from vc2_conformance.pseudocode.arrays import *
from vc2_conformance.pseudocode.offsetting import *
from vc2_conformance.pseudocode.parse_code_functions import *
from vc2_conformance.pseudocode.picture_decoding import *
from vc2_conformance.pseudocode.picture_encoding import *
from vc2_conformance.pseudocode.quantization import *
from vc2_conformance.pseudocode.slice_sizes import *
from vc2_conformance.pseudocode.state import *
from vc2_conformance.pseudocode.vc2_math import *
from vc2_conformance.pseudocode.video_parameters import *

from vc2_conformance.pseudocode.metadata import *
