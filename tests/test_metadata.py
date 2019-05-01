from vc2_conformance import metadata


# Sample values added to the metadata during testing only

referenced_none_value_line = 7
referenced_none_value = metadata.ref_value(None, "XXX 1.0")

referenced_unnamed_value_line = 10
referenced_unnamed_value = metadata.ref_value(None, "XXX 1.1", name=None)

example1_line = 13
@metadata.ref_pseudocode
def example1(a, b):
    """
    (XXX 1.2) Example function. Adds a and b.
    """
    return a + b

example2_line = 21
@metadata.ref_pseudocode(deviation="alternative_implementation")
def example2(a, b):
    """
    (TestDoc: XXX 1.3) Example function. Subtracts b from a.
    """
    return a - b


def test_non_functions_and_lookup_by_name():
    ref = metadata.lookup_by_name("referenced_none_value", __file__)
    
    assert ref.value is None
    assert ref.section == "XXX 1.0"
    assert ref.name == "referenced_none_value"
    assert ref.filename == __file__
    assert ref.lineno == referenced_none_value_line

def test_functions_no_decorator_args_and_lookup_by_value():
    example_ref = metadata.lookup_by_value(example1)
    
    assert example_ref.value is example1
    assert example_ref.section == "XXX 1.2"
    assert example_ref.name == "example1"
    assert example_ref.filename == __file__
    assert example_ref.lineno == example1_line
    
    # Decorated function still works
    assert example1(1, 2) == 3

def test_functions_with_decorator_args_and_lookup_by_value():
    example_ref = metadata.lookup_by_value(example2)
    
    assert example_ref.value is example2
    assert example_ref.section == "XXX 1.3"
    assert example_ref.document == "TestDoc"
    assert example_ref.name == "example2"
    assert example_ref.filename == __file__
    assert example_ref.lineno == example2_line
    
    # Decorated function still works
    assert example2(1, 2) == -1

def test_format_citation():
    unnamed = metadata.lookup_by_name(None, __file__)
    assert metadata.format_citation(unnamed) == "(XXX 1.1)"
    
    named = metadata.lookup_by_name("example1", __file__)
    assert metadata.format_citation(named) == "example1 (XXX 1.2)"
    
    custom_document = metadata.lookup_by_name("example2", __file__)
    assert metadata.format_citation(custom_document) == "example2 (TestDoc: XXX 1.3)"
