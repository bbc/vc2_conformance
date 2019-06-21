SMPTE ST 2042-2: VC-2 Conformance Testing Software
==================================================

This repository contains the software tools for checking the conformance of
[SMPTE ST 2042-1 (VC-2) professional video
codec](https://www.bbc.co.uk/rd/projects/vc-2) implementations.

This software is being produced as part of an effort to update the (currently
out-of-date) ST 2042-2 (VC-2 Conformance) document. When complete, these tools
and the associated document will allow codec implementers to verify the
conformance of their implementations with the SMPTE ST 2042-1 (VC-2) standard.

Work in progress...
-------------------

This software is currently a work in progress. Things are still missing and the
documentation is currently not organised in a manner conducive to understanding
(although it probably does exist, somewhere...).

Contact [Jonathan Heathcote](mailto:jonathan.heathcote@bbc.co.uk) for more
information.


Setup
-----

This software can be installed locally using::

    $ python setup.py install --user


Tools
-----

This Python package installs the following applications:

* `vc2-bitstream-validator`: VC-2 bitstream validator and decoder which
  checks that all values fall within the expected ranges allowed by the VC-2
  specification. The decoded picture frames should then be compared with the
  expected values to confirm conformance.

* `vc2-bitstream-viewer`: A VC-2 bitstream viewer which unpacks and displays
  the raw values encoded in the bitstream. A diagnostic tool.


Developers
----------

For developers of this software, see [``DEVELOP.md``](./DEVELOP.md).
