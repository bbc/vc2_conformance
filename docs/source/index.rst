VC-2 Conformance Software Documentation
=======================================

For codec developers
--------------------

For codec developers, your starting point should be SMPTE RP 2042-3 'VC-2
Conformance Specification'.

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   user_guide/index.rst
   cli/index.rst


For maintainers
---------------

This section of the documentation provides a guide to the VC-2 conformance
software internals. This documentation is aimed at maintainers of the VC-2
conformance software. Users of the VC-2 conformance software need not read
this.

Broadly the maintainer documentation is split into three parts:

The first part of the maintainer guide gives an overview of the general design,
structure and operation of the conformance software.

The second part provides advice on adopting changes from future VC-2 revisions
into the conformance software.

The final part consists of a detailed reference on each part of the software in
turn.

.. toctree::
   :maxdepth: 3
   :caption: Contents:
   
   maintainer/developer_installation.rst
   maintainer/overview.rst
   maintainer/decoder.rst
   maintainer/encoder.rst
   maintainer/bitstream.rst
   maintainer/bitstream_internals.rst
