.. _guide-installation:

Conformance Software Installation
=================================

These steps will help you install the VC-2 conformance software, along with its
dependencies. The VC-2 conformance software is cross platform and should run on
any system with a Python interpreter, however these instructions will only
cover the process under Linux.


Python interpreter
------------------

The VC-2 conformance software is compatible with both Python 2 and Python 3. If
in doubt, you should prefer Python 3. You should also make sure that the
``pip`` Python package manager is also installed.

Under Debian-like Linux distributions (e.g. Ubuntu), Python and ``pip`` can be
installed using::

    # apt install python3 python3-pip

.. note::

    It is recommended that you use 'CPython' -- the reference Python
    interpreter. Other Python interpreters are available, such as `PyPy
    <https://www.pypy.org/>`_, however these tend not to be as stable and have
    not been tested with this software.


Installation
------------


Via ``pip``
```````````

.. warning::
    
    The VC-2 conformance software has not yet been publicly released so the
    following install instructions do not work yet.

The VC-2 conformance software, along with all its dependencies, may be
installed using ``pip``::

    $ python -m pip install --user vc2_conformance

The ``--user`` argument may be omitted for a system-wide installation (not
recommended).


From ``.tar.gz.`` packages
``````````````````````````

The VC-2 conformance software may be installed from Python packages. The
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

The ``--user`` argument may be omitted for a system-wide installation (not
recommended).

If installation fails (requiring online download) on Debian and Ubuntu systems,
you may need to execute the following line prior to the above::

    $ export PIP_IGNORE_INSTALLED=0

From source
```````````

The latest VC-2 conformance software may be installed from the source as
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

The ``--user`` argument may be omitted for a system-wide installation (not
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
    This may be temporarily added to your path using::

        $ export PATH="$HOME/.local/bin:$PATH"

Next, lets move on to :ref:`guide-file-format`...
