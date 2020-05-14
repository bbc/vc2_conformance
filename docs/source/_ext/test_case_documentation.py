"""
Sphinx extension which automatically extracts VC-2 conformance test case
documentation from the VC-2 source code.

Usage::

    To insert all the docs for decoders:

    .. test-case-documentation:: decoder

    To insert all the docs for encoders:

    .. test-case-documentation:: encoder

    To create a reference to a documented test case:

    * :encoder-test-case:`signal_range`
    * :decoder-test-case:`signal_range`
"""

import inspect

from textwrap import dedent

from docutils import nodes
from docutils.statemachine import ViewList


from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

from vc2_conformance.test_cases import (
    ENCODER_TEST_CASE_GENERATOR_REGISTRY,
    DECODER_TEST_CASE_GENERATOR_REGISTRY,
)

TEST_CASE_REGISTRIES = {
    "encoder": ENCODER_TEST_CASE_GENERATOR_REGISTRY,
    "decoder": DECODER_TEST_CASE_GENERATOR_REGISTRY,
}


class TestCaseDocumentation(SphinxDirective):

    required_arguments = 1  # 'encoder' or 'decoder'

    def run(self):
        tc_type = self.arguments[0]
        try:
            registry = TEST_CASE_REGISTRIES[tc_type]
        except KeyError:
            raise Exception(
                "test-case-documentation first argument must be {}".format(
                    " or ".join(TEST_CASE_REGISTRIES.keys())
                )
            )

        test_cases = [
            (
                tc_function.__name__,
                dedent(inspect.getdoc(tc_function)),
                inspect.getsourcefile(tc_function),
            )
            for tc_function in registry.iter_registered_functions()
        ]

        out = []
        for tc_name, tc_docs, tc_file in sorted(test_cases):
            title = nodes.title(text="{} test case: ".format(tc_type.title()))
            title += nodes.literal(text=tc_name)

            # This is a crude hack (i.e. creating the directive by adding some
            # RST to a string...) but docutils/sphinx are sufficiently
            # poorly documented to make this the only viable option after
            # several hours of searching...
            tc_docs = ".. {}-test-case:: {}\n\n{}".format(tc_type, tc_name, tc_docs,)

            section = nodes.section(ids=["test-case-{}-{}".format(tc_type, tc_name)])
            section += title
            nested_parse_with_titles(
                self.state, ViewList(tc_docs.splitlines(), tc_file), section,
            )
            out.append(section)

        return out


def setup(app):
    app.add_directive("test-case-documentation", TestCaseDocumentation)
    app.add_crossref_type("encoder-test-case", "encoder-test-case")
    app.add_crossref_type("decoder-test-case", "decoder-test-case")

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
