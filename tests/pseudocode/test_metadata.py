import pytest

import sys

import traceback

import copy

from vc2_conformance.pseudocode.metadata import (
    PseudocodeDerivedFunction,
    pseudocode_derived_functions,
    make_pseudocode_traceback,
    ref_pseudocode,
    DEFAULT_SPECIFICATION,
)


def example1(a, b):
    """
    (XXX 1.2) Example function. Adds a and b.
    """
    return a + b


def example2(a, b):
    """
    (TestDoc:2017: 1.3) Example function. Subtracts b from a.
    """
    return example1(a, -b)


class TestPseudocodeDerivedFunction(object):
    def test_deviation(self):
        pdf1 = PseudocodeDerivedFunction(example1)
        assert pdf1.deviation is None

        pdf2 = PseudocodeDerivedFunction(example1, deviation="serdes")
        assert pdf2.deviation == "serdes"

    def test_document_and_section_extraction(self):
        pdf1 = PseudocodeDerivedFunction(example1)
        assert pdf1.document == DEFAULT_SPECIFICATION
        assert pdf1.section == "XXX 1.2"

        pdf2 = PseudocodeDerivedFunction(example2)
        assert pdf2.document == "TestDoc:2017"
        assert pdf2.section == "1.3"

        pdf3 = PseudocodeDerivedFunction(example2, document="foo", section="bar")
        assert pdf3.document == "foo"
        assert pdf3.section == "bar"

    def test_name_extraction(self):
        pdf1 = PseudocodeDerivedFunction(example1)
        assert pdf1.name == "example1"

        pdf2 = PseudocodeDerivedFunction(example1, name="foo")
        assert pdf2.name == "foo"

    @pytest.mark.parametrize(
        "document,section,exp",
        [
            (DEFAULT_SPECIFICATION, "1.2", "foo (1.2)"),
            (DEFAULT_SPECIFICATION, "XXX 1.2", "foo (XXX 1.2)"),
            ("TestDoc:2017", "XXX 1.2", "foo (TestDoc:2017: XXX 1.2)"),
        ],
    )
    def test_format_citation(self, document, section, exp):
        pdf = PseudocodeDerivedFunction(
            lambda: None, name="foo", document=document, section=section,
        )
        assert pdf.citation == exp


@pytest.yield_fixture
def restore_metadata_afterwards():
    """
    Fixture which reverts any changes made to pseudocode_derived_functions
    during this test.
    """
    old = copy.deepcopy(pseudocode_derived_functions)

    try:
        yield pseudocode_derived_functions
    finally:
        pseudocode_derived_functions.clear()
        pseudocode_derived_functions.extend(old)


def test_ref_pseudocode(restore_metadata_afterwards):
    pseudocode_derived_functions.clear()

    # Decorator without brackets
    assert ref_pseudocode(example1) is example1
    assert len(pseudocode_derived_functions) == 1
    assert pseudocode_derived_functions[0].function is example1
    assert pseudocode_derived_functions[0].deviation is None

    # Decorator with brackets
    assert ref_pseudocode(deviation="serdes")(example2) is example2
    assert len(pseudocode_derived_functions) == 2
    assert pseudocode_derived_functions[1].function is example2
    assert pseudocode_derived_functions[1].deviation == "serdes"


def test_make_pseudocode_traceback(restore_metadata_afterwards):
    ref_pseudocode(example1)
    ref_pseudocode(example2)

    try:
        # Will fail when attempting to do "foo" + -1
        example2("foo", 1)
        assert False
    except TypeError:
        tb = traceback.extract_tb(sys.exc_info()[2])

    ptb = make_pseudocode_traceback(tb)

    assert len(ptb) == 2
    assert ptb[0].function is example2
    assert ptb[1].function is example1
