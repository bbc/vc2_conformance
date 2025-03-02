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

project = "SMPTE VC-2 Conformance Software"
copyright = "2021, BBC"
author = "BBC"

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
    "sphinxcontrib.intertex",
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
    "vc2_data_tables": ("https://bbc.github.io/vc2_data_tables/", None),
    "vc2_bit_widths": ("https://bbc.github.io/vc2_bit_widths/", None),
    "vc2_conformance_data": ("https://bbc.github.io/vc2_conformance_data/", None),
}


# -- Options for intertex ----------------------------------------------------

intertex_mapping = {
    "vc2_data_tables": [
        "{vc2_data_tables}/../docs/build/latex/*.aux",
        "https://bbc.github.io/vc2_data_tables/vc2_data_tables_manual.aux",
    ],
    "vc2_bit_widths": [
        "{vc2_bit_widths}/../docs/build/latex/*.aux",
        "https://bbc.github.io/vc2_bit_widths/vc2_bit_widths_manual.aux",
    ],
    "vc2_conformance_data": [
        "{vc2_conformance_data}/../docs/build/latex/*.aux",
        "https://bbc.github.io/vc2_conformance_data/vc2_conformance_data_manual.aux",
    ],
}


# -- Options for HTML output -------------------------------------------------

html_theme = "nature"

html_static_path = ["_static"]


# -- Options for PDF output --------------------------------------------------

# Show page numbers in references
latex_show_pagerefs = True

# Show hyperlink URLs in footnotes
latex_show_urls = "footnote"

# Divide the document into parts, then chapters, then sections
latex_toplevel_sectioning = "part"

# Don't include a module index (the main index should be sufficient)
latex_domain_indices = False

latex_elements = {
    "papersize": "a4paper",
    # Allow deeply nested bullets etc.
    "maxlistdepth": "10",
    # Add an 'Introduction' chapter heading to the content which appears before
    # all of the main chapters.
    "tableofcontents": r"""
        \sphinxtableofcontents
        \chapter{Introduction}
    """,
    # Make index entries smaller since some are quite long
    "printindex": r"\footnotesize\raggedright\printindex",
    # Override ToC depth to include sections
    "preamble": r"\setcounter{tocdepth}{1}",
}
