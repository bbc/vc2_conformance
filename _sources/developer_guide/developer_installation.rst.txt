Development setup
=================

The following instructions outline the process for setting up a development
environment for the VC-2 conformance software and the procedures for running
tests and generating documentation.


Checking out repositories
-------------------------

The VC-2 conformance software is split across in the following `Git
<https://git-scm.com/>`_ repositories, each containing a Python package of the
same name:

`<https://github.com/bbc/vc2_conformance>`_ (:py:mod:`vc2_conformance`)
    The main conformance software repository on which this documentation
    focuses.

`<https://github.com/bbc/vc2_conformance_data>`_ (:py:mod:`vc2_conformance_data`)
    Data files (e.g. test pictures) used in the conformance testing process.

`<https://github.com/bbc/vc2_data_tables>`_ (:py:mod:`vc2_data_tables`)
    Data tables and constant definitions from the VC-2 standard.

`<https://github.com/bbc/vc2_bit_widths>`_ (:py:mod:`vc2_bit_widths`)
    Mathematical routines for computing near worst case signals for VC-2
    codecs.

The above repositories should be cloned into local directories, e.g. using::

    $ git clone git@github.com:bbc/vc2_conformance.git
    $ git clone git@github.com:bbc/vc2_conformance_data.git
    $ git clone git@github.com:bbc/vc2_data_tables.git
    $ git clone git@github.com:bbc/vc2_bit_widths.git

`Pre-commit hooks <https://pre-commit.com/>`_ are used to enforce certain code
standards in these repositories. These should be installed as follows::

    $ # For each cloned repository...
    $ cd path/to/repo/
    $ pre-commit install


Virtual environment
-------------------

It is strongly recommended that development is carried out in a `Python virtual
environment <https://virtualenv.pypa.io/en/stable/>`_ (see warning below). This
can be setup using::

    $ python -m virtualenv --python <PYTHON INTERPRETER> venv

This will create a virtual environment in the directory ``venv`` which uses the
python interpreter ``<PYTHON INTERPRETER>``, which should generally be one of
``python2`` or ``python3``.

Once created, the virtual environment must be activated in any shell you use
using::

    $ source venv/bin/activate

.. note::

    Python virtual environment provides an isolated environment in which
    packages can be installed without impacting on the rest of the system.
    Once activated, the ``python`` and ``pip`` commands will use the python
    version and packages setup within the virtual environment.

.. warning::

    When working outside a virtual environment, Python packages included by
    some operating systems (e.g. Ubuntu) can be very out of date leading to
    problems during development. This is the result of certain development
    dependencies not correctly specifiying their version requirements and is
    outside of our control. By using a virtual environment, up-to-date versions
    of all dependencies will be installed which avoids these problems.

    .. note::

        The VC-2 conformance software itself *does* correctly specify its
        dependencies so these problems only apply during development and should
        not affect end users.


Development installation
------------------------

A development installation of the conformance software can be performed
directly from each of the cloned repositories as follows::

    $ # Each repo should be installed as follows, in the following order:
    $ # * vc2_data_tables
    $ # * vc2_bit_widths
    $ # * vc2_conformance_data
    $ # * vc2_conformance
    $ cd path/to/repo/
    
    $ # Install in editable/development mode (so edits take effect immediately)
    $ pip install -e .
    
    $ # Install test suite dependencies
    $ pip install -r requirements-test.txt
    
    $ # Install documentation building dependencies (not present for all
    $ # repositories)
    $ pip install -r requirements-docs.txt


After installation, the various ``vc2-*`` commands will be made available in
your ``$PATH`` and the various ``vc2_*`` Python modules in your
``$PYTHONPATH``.  These will point directly to the cloned source code and so
changes will take effect immediately.


Running tests
-------------

Test routines relating to the code in each repository can be found in the
``tests/`` directory of each repository. The test suites are built on `pytest
<https://docs.pytest.org/en/latest/>`_ and, once a development install has been
completed, can be executed as follows::

    $ py.test path/to/vc2_data_tables/tests/
    $ py.test path/to/vc2_bit_widths/tests/
    $ py.test path/to/vc2_conformance_data/tests/
    $ py.test path/to/vc2_conformance/tests/


Building documentation
----------------------

HTML documentation (including the documentation you're reading now) is built as
follows (after a development install has been performed)::

    $ make -C path/to/vc2_data_tables/docs html
    $ make -C path/to/vc2_bit_widths/docs html
    $ make -C path/to/vc2_conformance_data/docs html
    $ make -C path/to/vc2_conformance/docs html


HTML documentation will be written to the ``docs/build/html/`` directory (open
the ``index.html`` file in a web browser to read it).

Alternatively, PDF documentation can be built by replacing ``html`` with
``latexpdf`` in the above commands. This will require a working installation of
`LaTeX <https://www.latex-project.org/>`_ and `Inkscape
<https://inkscape.org/>`_ to build. In addition, for cross-references between
PDFs to be created correctly, the documentation must be built within the Python
virtual environment where the various ``vc2_*`` Python packages are installed
in development/editable mode.
