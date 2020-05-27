# Configuration file for the Sphinx documentation builder.

import os
import sys


# -- Path setup --------------------------------------------------------------

# To find the vc2_conformance module
sys.path.insert(0, os.path.abspath("../.."))

# To find the verification module
sys.path.insert(0, os.path.abspath("../../tests/"))

# To find custom sphinx extensions
sys.path.insert(0, os.path.abspath("_ext/"))


# -- Project information -----------------------------------------------------

project = "SMPTE VC-2 Conformance"
copyright = "2019, SMPTE"
author = "SMPTE"

from vc2_conformance import __version__ as version

release = version

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.doctest",
    "sphinx.ext.mathjax",
    "numpydoc",
    "sphinxcontrib.inkscapeconverter",
    "sphinxcontrib.programoutput",
    # Local extensions (in _ext/ directory)
    "test_case_documentation",
    "enum_table",
    "fixeddict",
    "bitstream_fixeddicts",
]

# -- Options for numpydoc/autodoc --------------------------------------------

# Fixes autosummary errors
numpydoc_show_class_members = False

autodoc_member_order = "bysource"

add_module_names = False

# -- Options for intersphinx -------------------------------------------------

intersphinx_mapping = {
    "python": ("http://docs.python.org/3", None),
    "ast": ("https://greentreesnakes.readthedocs.io/en/latest/", None),
    "sympy": ("https://docs.sympy.org/latest/", None),
}


# -- Options for HTML output -------------------------------------------------

html_theme = "nature"

html_static_path = ["_static"]


# -- Options for PDF output --------------------------------------------------

latex_elements = {
    "papersize": "a4paper",
}
