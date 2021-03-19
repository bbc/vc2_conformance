VC-2 Conformance Software
=========================

This is the manual for the VC-2 conformance testing software. This software is
used to test implementations of the VC-2 video codec.

Specifically, this software tests conformance with the following SMPTE
standards and recommended practices:

* `SMPTE ST 2042-1:2017 <ST2042-1_>`_ (VC-2)
* `SMPTE ST 2042-2:2017 <ST2042-2_>`_ (VC-2 Level Definitions)
* `SMPTE RP 2047-1:2009 <RP2047-1_>`_ (VC-2 Mezzanine Compression of 1080P High Definition Video Sources)
* `SMPTE RP 2047-3:2016 <RP2047-3_>`_ (VC-2 Level 65 Compression of High Definition Video Sources for Use with a Standard Definition Infrastructure)
* `SMPTE RP 2047-5:2017 <RP2047-5_>`_ (VC-2 Level 66 Compression of Ultra High Definition Video Sources for use with a High Definition Infrastructure)

.. _ST2042-1: https://ieeexplore.ieee.org/document/7967896
.. _ST2042-2: https://ieeexplore.ieee.org/document/8187792
.. _RP2047-1: https://ieeexplore.ieee.org/document/7290342
.. _RP2047-3: https://ieeexplore.ieee.org/document/7565453
.. _RP2047-5: https://ieeexplore.ieee.org/document/8019813

.. note::

    Throughout this software and documentation, perenthesised references of the
    form '(1.2.3)' refer to section numbers within the SMPTE ST 2042-1:2017
    specification unless otherwise indicated.

This manual is split into two parts.

The first (shorter) part, :ref:`user-documentation`, is aimed at codec
developers who wish to test their video codec implementations. It includes more
detailed guides and references on using the tools provided by the conformance
testing software.

The second (longer) part, :ref:`maintainer-documentation`, is aimed at
developers tasked with maintaining this software; codec developers can
disregard this part. This section includes a general overview of the
conformance software internals followed by detailed reference documentation on
its various components.

Finally, you can find the source code for
:py:mod:`vc2_conformance` `on GitHub
<https://github.com/bbc/vc2_conformance/>`_.

.. only:: not latex

    .. note::
    
        This documentation is also `available in PDF format
        <https://bbc.github.io/vc2_conformance/vc2_conformance_manual.pdf>`_.

.. only:: not html

    .. note::
    
        This documentation is also `available to browse online in HTML format
        <https://bbc.github.io/vc2_conformance/>`_.


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



