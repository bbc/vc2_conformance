.. _guide-bitstream-testing:

Testing additional bitstreams' conformance
==========================================

the :ref:`vc2-bitstream-validator` tool can be used to test any VC-2
bitstreams, including those produced outside of the conformance testing
procedures. For example, you might wish to test how an encoder behaves with
your own test materials. Alternatively you might have existing bitstreams which
you would like to validate, perhaps because a decoder you're testing is having
trouble with them.


Bitstream validation
--------------------

Any existing bitstream can be validated following a similar manner to the
:ref:`guide-encoder-testing` using the :ref:`vc2-bitstream-validator` command
like so::

    $ vc2-bitstream-validator \
        my_bitstream.vc2 \
        --output my_decoded_picture_%d.raw

.. note::

    The bitstream validator always produces a decoded output. If ``--output``
    is not given, the decoded pictures will still be produced but given the
    default name ``picture_%d.raw``.

If the bitstream is valid, the following message will be produced:

.. code-block:: text

    No errors found in bitstream. Verify decoded pictures to confirm conformance.

Otherwise, if a conformance error is found, processing will stop and a detailed
error message will be produced explaining the problem.

Once a bitstream has been validated by :ref:`vc2-bitstream-validator`, you can
view the decoded pictures to verify that the bitstream contained the pictures
and metadata you expected.  You might wish to use :ref:`vc2-picture-explain` to
produce an ffmpeg or ImageMagick command to do this.


Decoded picture validation
--------------------------

The :ref:`vc2-bitstream-validator` tool will correctly decode any valid VC-2
bitstream. You can therefore use its output to validate that a decoder has
correctly decoded a given bitstream. The :ref:`vc2-bitstream-compare` command
can be used to compare a decoder's output with that of the bitstream validator
in a manner similar to the :ref:`guide-decoder-testing`::

    $ vc2-picture-compare expected/ actual/
    Comparing expected/picture_0.raw and actual/picture_0.raw
      Pictures are identical
    Comparing expected/picture_1.raw and actual/picture_1.raw
      Pictures are identical
    Comparing expected/picture_2.raw and actual/picture_2.raw
      Pictures are identical
    Summary: 3 identical, 0 different

A conformant decoder must produce identical results to the
:ref:`vc2-bitstream-validator` command.
