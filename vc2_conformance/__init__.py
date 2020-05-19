"""
:py:mod:`vc2_conformance`: VC-2 conformance testing tools
=========================================================

These tools are intended to be used to verify the conformance of VC-2 encoder
and decoder designs to the VC-2 specifications. A normative statement of their
use is prescribed in SMPTE Recommended Practice RP2042-3 (VC-2 Conformance
Specification ).

This Python package includes the following key components:

* A conformance checking VC-2 decoder which validates VC-2 bitstream
  conformance and produces reference decoded pictures.
* Tools for displaying VC-2 bitstreams in a human-readable form as a debugging
  aid for codec implementers.
* Tools for generating VC-2 bitstreams to test VC-2 decoder implementations.
* Tools for generating reference pictures to test VC-2 encoder implementations.
"""

from vc2_conformance.version import __version__
