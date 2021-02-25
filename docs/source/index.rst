VC-2 Conformance Software
=========================

This is the manual for the VC-2 conformance testing software. This software is
used to test implementations of the SMPTE 2042-1 (VC-2) video codec.

.. note::

    Throughout this software and documentation, perenthesised references of the
    form '(1.2.3)' refer to section numbers within the SMPTE 2042-1:2017
    specification unless otherwise indicated.

This manual is split into two parts.

The first (shorter) part, :ref:`user-documentation`, is aimed at codec
developers who wish to test their video codec implementations. It includes more
detailed guides and references on using the tools provided by the conformance
testing software.

The second (longer) part, :ref:`maintainer-documentation`, is aimed at
developers tasked with maintaining this software; codec developers may
disregard this part. This section includes a general overview of the
conformance software internals followed by detailed reference documentation on
its various components.

.. toctree::
   :hidden:

   bibliography.rst


.. _user-documentation:

User's manual
-------------

.. toctree::
   :maxdepth: 2
   
   user_guide/index.rst
   cli/index.rst


.. _maintainer-documentation:

Maintainer's manual
-------------------

.. toctree::
   :maxdepth: 2
   
   developer_guide/index.rst
   test_case_generation/index.rst
   decoder.rst
   encoder.rst
   bitstream.rst
   picture_generation/index.rst
   level_constraints/index.rst
   pseudocode.rst
   verification.rst
   utility_modules/index.rst



