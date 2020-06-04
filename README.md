SMPTE RP 2042-3: VC-2 Conformance Testing Software
==================================================

This repository contains the software tools for checking the conformance of
[SMPTE ST 2042-1 (VC-2) professional video
codec](https://www.bbc.co.uk/rd/projects/vc-2) implementations.


Work in progress...
-------------------

This software is being produced as part of an effort to update the (currently
out-of-date) RP 2042-3 (VC-2 Conformance) document. When complete, these tools
and the associated document will allow codec implementers to verify the
conformance of their implementations with the SMPTE ST 2042-1 (VC-2) standard.

This software is currently a work in progress.  Contact [Jonathan
Heathcote](mailto:jonathan.heathcote@bbc.co.uk) or [John
Fletcher](mailto:john.fletcher@bbc.co.uk) for more information.


Developers
----------

For details on setting up a developer's installation of this software,
including instructions on building the associated documentation, see the
[developer installation
instructions](./docs/source/developer_guide/developer_installation.rst).


See also
--------

* [`vc2_conformance_data`](https://github.com/bbc/vc2_conformance_data): Data
  files (e.g. test pictures) used in the conformance testing process.

* [`vc2_data_tables`](https://github.com/bbc/vc2_data_tables): Data tables and
  constant definitions from the VC-2 standard.

* [`vc2_bit_widths`](https://github.com/bbc/vc2_bit_widths) Mathematical
  routines for computing near worst case signals for VC-2 codecs.
