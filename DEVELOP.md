Maintainer/Developer Notes
==========================

The following notes are intended as instructions for developers of this
software.


Developer Installation
----------------------

It is recommended that this software be used under a
[virtualenv](https://docs.python.org/3/tutorial/venv.html) like so:

    $ # Setup virtualenv
    $ cd path/to/cloned/repo
    $ virtualenv .
    $ source bin/activate

    $ # Install development version (changes to source will be reflected in
    $ # installed version.
    $ python setup.py develop
    
    $ # Install test suite dependencies
    $ pip install -r requirements-test.txt


Test suite
----------

The test suite is based on [pytest](https://docs.pytest.org/en/latest/). It can
be executed like so:

    $ py.test tests/

Alternatively, you can use [tox](https://tox.readthedocs.io/en/latest/) to
automatically run the test suite against several versions of Python (since this
library is designed to run under many different Python versions).

    $ pip install tox
    $ tox


Documentation
-------------

The documentation can be built using [Sphinx](www.sphinx-doc.org/) as follows::

    $ pip install -r requirements-docs.txt
    $ cd docs
    $ make html
