from vc2_conformance import bitstream


def test_no_unexpected_missing_functions():
    # Sanity check: all bitstream-related VC-2 pseudo code functions are
    # listed.
    expected_missing = set(["slice_band", "color_diff_slice_band"])
    
    expected = set(bitstream.vc2.__all__)
    present = set(bitstream.pseudocode_function_to_fixeddicts)
    assert present.issubset(expected)
    assert expected - present == expected_missing


def test_no_functions_without_types():
    # If this test fails, it is likely a new function was added to the
    # 'bitstream.vc2' module without a fixeddict type declared with
    # @context_type. If this is intentional, a special case should be added to
    # the metadata module.
    assert all(
        len(types) > 0
        for types in bitstream.pseudocode_function_to_fixeddicts.values())


def test_recursive():
    # Sanity check: ensure the 'parse_sequence' type list which should
    # encompass every possible structure. If this test fails, it is likely one
    # or more fixeddicts do not correctly declare thier children using the
    # 'type' annotation.
    all_types = set([
        getattr(bitstream.vc2_fixeddicts, name)
        for name in bitstream.vc2_fixeddicts.__all__
    ])
    assert (
        set(bitstream.pseudocode_function_to_fixeddicts_recursive["parse_sequence"]) ==
        all_types
    )
