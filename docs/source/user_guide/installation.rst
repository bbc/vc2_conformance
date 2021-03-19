.. _guide-installation:

Conformance Software Installation
=================================

These steps will help you install the VC-2 conformance software, along with its
dependencies. The VC-2 conformance software is cross platform and should run on
any system with a Python interpreter, however these instructions will only
cover the process under Linux.


Python interpreter
------------------

The VC-2 conformance software is compatible with both Python 2.7 and Python 3.6
and later. If in doubt, you should prefer Python 3.x. You should also make sure
that the ``pip`` Python package manager is also installed.

Under Debian-like Linux distributions (e.g. Ubuntu), Python and ``pip`` can be
installed using::

    # apt install python3 python3-pip

.. note::

    We strongly recommend running the VC-2 conformance software under the
    standard Python interpreter ('CPython') as opposed to `other Python
    implementations <https://www.python.org/download/alternatives/>`_ (such as
    `PyPy <https://www.pypy.org/>`_). These alternative implementations are
    often less stable and we have not tested this software running under them.
    If you're not sure which Python interpreter you've got on your system
    you'll almost certainly have the (correct) standard Python interpreter so
    there is no need to take any action.


Installation
------------

You can install the VC-2 conformance software using any of the methods
below.


Via ``pip`` (recommended)
`````````````````````````

The VC-2 conformance software, along with all its dependencies, can be
installed using ``pip``::

    $ python -m pip install --user vc2_conformance

The ``--user`` argument can be omitted for a system-wide installation (strongly
*not* recommended) or when installing in a `Python virtual environment
<https://docs.python.org/3/tutorial/venv.html>`_.


From ``.tar.gz.`` packages (advanced)
`````````````````````````````````````

The VC-2 conformance software can be installed from Python packages. The
following packages are required:

* ``vc2_data_tables-X.Y.Z.tar.gz``
* ``vc2_bit_widths-X.Y.Z.tar.gz``
* ``vc2_conformance_data-X.Y.Z.tar.gz``
* ``vc2_conformance-X.Y.Z.tar.gz``

All other dependencies will be downloaded automatically during installation.

The packages must then be installed as follows, in the order shown::

    $ python -m pip install --user vc2_data_tables-X.Y.Z.tar.gz
    $ python -m pip install --user vc2_bit_widths-X.Y.Z.tar.gz
    $ python -m pip install --user vc2_conformance_data-X.Y.Z.tar.gz
    $ python -m pip install --user vc2_conformance-X.Y.Z.tar.gz

The ``--user`` argument can be omitted for a system-wide installation (not
recommended).

If installation fails (requiring online download) on Debian and Ubuntu systems,
you might need to execute the following line prior to the above::

    $ export PIP_IGNORE_INSTALLED=0

From source (advanced)
``````````````````````

The latest VC-2 conformance software can be installed from the source as
follows.

First, you must checkout (or download a snapshot of) the following
repositories:

* `<https://github.com/bbc/vc2_data_tables>`_
* `<https://github.com/bbc/vc2_bit_widths>`_
* `<https://github.com/bbc/vc2_conformance_data>`_
* `<https://github.com/bbc/vc2_conformance>`_

Next, each package should be installed (in the order shown above) using the
following steps::

    $ cd path/to/repo/
    $ python setup.py install --user

The ``--user`` argument can be omitted for a system-wide installation (not
recommended).

All other dependencies will be downloaded automatically during the installation
of these packages.


Verifying installation
----------------------

To verify installation was successful, try running::

    $ vc2-test-case-generator --version

This command should print a version number and then exit immediately. If the
command cannot be found, check your ``PATH`` includes the directory the
conformance software was installed into.

.. tip::

    Under Linux, Python usually installs programmes into ``$HOME/.local/bin``.
    This can be temporarily added to your path using::

        $ export PATH="$HOME/.local/bin:$PATH"

Next, lets move on to :ref:`guide-file-format`...
