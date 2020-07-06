.. _generating-static-analyses:

.. _guide-generating-static-analyses:


Generating static wavelet filter analyses
=========================================

The generation of certain test cases requires a mathematical analysis of the
wavelet filter used by the codec under test. The VC-2 conformance software is
supplied with analyses for all wavelet filter configurations for which a
default quantisation matrix is available. To enable testing of other codec
configurations using other wavelets, suitable mathematical analyses must be
generated, as described below.

.. note::

    The following steps are only necessary if one or more of your codec feature
    sets use a wavelet transform for which no default quantisation matrix is
    available.


Step 1: Generating static analyses
----------------------------------

Static analyses must be created for every wavelet transform used by your codec
(including those with a default quantisation matrix).

The ``vc2-static-filter-analysis`` command (provided by the
:py:mod:`vc2_bit_widths` package) may be used to generate a mathematical
analysis of arbitrary VC-2 filter configurations.

For example, to analyse a filter which:

* Uses the Haar (with shift) filter (wavelet index 4) vertically
* Uses the Le Gall (5, 3) filter (wavelet index 1) horizontally
* With a 2 level 2D transform depth
* And 1 level horizontal-only transform depth

The following command may be used::

    $ vc2-static-filter-analysis \
        --wavelet-index 4 \
        --wavelet-index-ho 1 \
        --dwt-depth 2 \
        --dwt-depth-ho 1 \
        --output filter_analysis.json

This command will compute the static analysis and write them to
``filter_analysis.json``.

For modest transform depths, this process should take a few seconds. For larger
transforms, this command can take several minutes or even hours to execute so
the ``--verbose`` option may be added to track progress. For extremely large
filters, see the :mod:`vc2_bit_widths` package's user guide for further
guidance.


Step 2: Bundling static analyses
--------------------------------

Once static analyses have been produced for all required wavelets, these must
be combined into an analysis bundle file as follows::

    $ vc2-bundle create bundle.zip \
          --static-filter-analysis path/to/analyses/*.json


Step 3: Run test case generation
--------------------------------

Finally, to use the generated filter analyses during test case generation, the
``VC2_BIT_WIDTHS_BUNDLE`` environment variale must be set to the location of
the bundle file generated in step 2. For example::

    $ export VC2_BIT_WIDTHS_BUNDLE="path/to/bundle.zip"
    $ vc2-test-case-generator path/to/codec_features.csv

