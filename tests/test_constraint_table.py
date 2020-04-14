import pytest

import os

from vc2_conformance._constraint_table import (
    ValueSet,
    AnyValue,
    filter_allowed_values,
    is_allowed_combination,
    allowed_values_for,
    read_constraints_from_csv,
)


class TestValueSet(object):
    def test_constructor_empty(self):
        vs = ValueSet()
        assert vs._values == set()
        assert vs._ranges == set()

    def test_add_value(self):
        vs = ValueSet()

        # Duplicate values not allowed
        vs.add_value(123)
        vs.add_value(123)
        assert list(vs) == [123]

        # Values already in a range not allowed
        vs.add_range(10, 20)
        vs.add_value(10)
        vs.add_value(15)
        vs.add_value(20)
        assert list(vs) == [123, (10, 20)]

    def test_add_range_non_overlapping(self):
        vs = ValueSet()
        vs.add_range(10, 20)
        vs.add_range(30, 40)
        vs.add_range(22, 27)
        assert sorted(vs) == [(10, 20), (22, 27), (30, 40)]

    def test_add_range_overlap_single_values(self):
        vs = ValueSet()
        vs.add_value(5)
        vs.add_value(10)
        vs.add_value(15)
        vs.add_value(20)
        vs.add_value(25)
        vs.add_range(10, 20)
        assert vs._values == set([5, 25])
        assert vs._ranges == set([(10, 20)])

    @pytest.mark.parametrize(
        "ranges",
        [
            # Touching
            [(10, 20), (20, 30)],
            [(20, 30), (10, 20)],
            # Overlapping
            [(10, 25), (15, 30)],
            [(15, 30), (10, 25)],
            # Super/subset
            [(10, 30), (15, 25)],
            [(15, 25), (10, 30)],
            # Many combined
            [(10, 15), (17, 22), (25, 30), (14, 26)],
        ],
    )
    def test_add_range_overlap_existing_ranges(self, ranges):
        vs = ValueSet()
        for r in ranges:
            vs.add_range(*r)
        assert vs._ranges == set([(10, 30)])

    def test_constructor_works(self):
        vs = ValueSet(5, 10, 15, 20, 25, (10, 15), (15, 21))
        assert vs._values == set([5, 25])
        assert vs._ranges == set([(10, 21)])

    def test_empty(self):
        empty = ValueSet()
        assert None not in empty
        assert 123 not in empty
        assert "foo" not in empty

    def test_individual_values(self):
        vs = ValueSet()

        vs.add_value(123)
        assert 123 in vs
        assert 321 not in vs

        vs.add_value("foo")
        assert 123 in vs
        assert "foo" in vs
        assert 321 not in vs
        assert "bar" not in vs

    def test_ranges(self):
        vs = ValueSet()

        vs.add_range(10, 20)
        assert 9 not in vs
        assert 9.9999 not in vs
        assert 10 in vs
        assert 15 in vs
        assert 20 in vs
        assert 20.0001 not in vs
        assert 21 not in vs

        vs.add_range(30, 40)
        assert 9 not in vs
        assert 9.9999 not in vs
        assert 10 in vs
        assert 15 in vs
        assert 20 in vs
        assert 20.0001 not in vs
        assert 21 not in vs
        assert 29 not in vs
        assert 29.9999 not in vs
        assert 30 in vs
        assert 35 in vs
        assert 40 in vs
        assert 40.0001 not in vs
        assert 41 not in vs

    def test_combination(self):
        vs = ValueSet()
        vs.add_value(1)
        vs.add_range(10, 20)

        assert 0 not in vs
        assert 1 in vs
        assert 2 not in vs
        assert 9 not in vs
        assert 10 in vs
        assert 15 in vs
        assert 20 in vs
        assert 21 not in vs

    def test_combine_value_sets(self):
        vs1 = ValueSet()
        vs1.add_value(1)
        vs1.add_range(10, 20)

        vs2 = ValueSet()
        vs2.add_value(2)
        vs2.add_range(20, 30)

        vs = vs1 + vs2

        assert 0 not in vs
        assert 1 in vs
        assert 2 in vs
        assert 3 not in vs
        assert 9 not in vs
        assert 10 in vs
        assert 15 in vs
        assert 20 in vs
        assert 25 in vs
        assert 30 in vs
        assert 31 not in vs

    def test_iter(self):
        vs = ValueSet()

        assert set(vs) == set()

        vs.add_value(1)
        vs.add_value(2)
        vs.add_value(3)
        assert set(vs) == set([1, 2, 3])

        vs.add_range(10, 20)
        vs.add_range(30, 40)
        assert set(vs) == set([1, 2, 3, (10, 20), (30, 40)])

    def test_compare(self):
        assert ValueSet() == ValueSet()
        assert ValueSet(1, 2, (3, 4)) == ValueSet((3, 4), 2, 1)

        assert ValueSet(1) != ValueSet(2)
        assert ValueSet(1, 2) != ValueSet(1, 2, 3)
        assert ValueSet(1, 2) != ValueSet(1, (2, 3))
        assert ValueSet((2, 3)) != ValueSet((3, 2))

    def test_repr(self):
        vs = ValueSet()
        assert repr(vs) == "ValueSet()"

        vs.add_value(123)
        vs.add_range(10, 20)
        assert repr(vs) == "ValueSet(123, (10, 20))"

    def test_str(self):
        vs = ValueSet()

        assert str(vs) == "{<no values>}"

        vs.add_value(10)
        vs.add_value(20)
        vs.add_value(30)
        assert str(vs) == "{10, 20, 30}"

        vs.add_range(3, 7)
        vs.add_range(13, 17)
        vs.add_range(20, 25)
        vs.add_range(33, 37)
        assert str(vs) == "{3-7, 10, 13-17, 20-25, 30, 33-37}"

    def test_str_uses_repr(self):
        vs = ValueSet()
        vs.add_value("foo")
        assert str(vs) == "{'foo'}"


class TestAnyValue(object):
    def test_contains_everything(self):
        a = AnyValue()

        assert None in a
        assert 123 in a
        assert "foo" in a

    def test_combine(self):
        a1 = AnyValue()
        a2 = AnyValue()
        vs = ValueSet()

        for a in [a1, a2, vs]:
            for b in [a1, a2, vs]:
                if not (a == b == vs):
                    assert isinstance(a + b, AnyValue)

    def test_compare(self):
        assert AnyValue() == AnyValue()

        assert AnyValue() != ValueSet()
        assert ValueSet() != AnyValue()

    def test_repr(self):
        assert repr(AnyValue()) == "AnyValue()"

    def test_str(self):
        assert str(AnyValue()) == "{<any value>}"


class TestFilterAllowedValues(object):
    def test_empty(self):
        assert filter_allowed_values([], {}) == []

    def test_allow_subset(self):
        allowed_values = [{"foo": ValueSet(123), "bar": ValueSet()}]
        assert filter_allowed_values(allowed_values, {"foo": 123}) == allowed_values

    def test_disallow_superset(self):
        allowed_values = [{"foo": ValueSet(123)}]
        assert filter_allowed_values(allowed_values, {"foo": 123, "bar": 321}) == []

    def test_allow_matching(self):
        allowed_values = [{"foo": ValueSet(123), "bar": ValueSet(321)}]
        assert (
            filter_allowed_values(allowed_values, {"foo": 123, "bar": 321})
            == allowed_values
        )

    def test_disallow_mismatching(self):
        allowed_values = [{"foo": ValueSet(321)}]
        assert filter_allowed_values(allowed_values, {"foo": 123}) == []

    def test_disallow_no_completely_matching_set(self):
        allowed_values = [{"foo": ValueSet(123)}, {"bar": ValueSet(321)}]
        assert filter_allowed_values(allowed_values, {"foo": 123, "bar": 321}) == []

    def test_remove_non_matching_combinations(self):
        allowed_values = [
            {},
            {"foo": ValueSet(123)},
            {"foo": ValueSet(123), "bar": ValueSet(321)},
            {"foo": ValueSet(321)},
            {"bar": ValueSet(321)},
        ]
        assert filter_allowed_values(allowed_values, {"foo": 123}) == allowed_values[:3]


class TestIsAllowedCombination(object):
    def test_empty(self):
        assert is_allowed_combination([], {}) is False
        assert is_allowed_combination([{}], {}) is True
        assert is_allowed_combination([{"foo": ValueSet()}], {}) is True

    def test_allow_subset(self):
        assert (
            is_allowed_combination(
                [{"foo": ValueSet(123), "bar": ValueSet()}], {"foo": 123},
            )
            is True
        )

    def test_disallow_superset(self):
        assert (
            is_allowed_combination([{"foo": ValueSet(123)}], {"foo": 123, "bar": 321},)
            is False
        )

    def test_allow_matching(self):
        assert (
            is_allowed_combination(
                [{"foo": ValueSet(123), "bar": ValueSet(321)}],
                {"foo": 123, "bar": 321},
            )
            is True
        )

    def test_disallow_mismatching(self):
        assert is_allowed_combination([{"foo": ValueSet(321)}], {"foo": 123},) is False

    def test_disallow_no_completely_matching_set(self):
        assert (
            is_allowed_combination(
                [{"foo": ValueSet(123)}, {"bar": ValueSet(321)}],
                {"foo": 123, "bar": 321},
            )
            is False
        )


class TestAllowedValuesFor(object):
    def test_empty(self):
        assert allowed_values_for([], "foo") == ValueSet()
        assert allowed_values_for([], "foo", {"bar": 123}) == ValueSet()

    def test_unfiltered(self):
        assert allowed_values_for(
            [{"foo": ValueSet(1)}, {"foo": ValueSet(2)}, {"foo": ValueSet(3)}], "foo",
        ) == ValueSet(1, 2, 3)

    def test_filtered(self):
        assert allowed_values_for(
            [
                {"foo": ValueSet(1), "bar": ValueSet(123)},
                {"foo": ValueSet(2), "bar": ValueSet(321)},
                {"foo": ValueSet(3), "bar": ValueSet(123)},
            ],
            "foo",
            {"bar": 123},
        ) == ValueSet(1, 3)


def test_read_constraints_from_csv():
    constraints = read_constraints_from_csv(
        os.path.join(os.path.dirname(__file__), "sample_constraint_table.csv")
    )

    # Every column included (incl. empty column!)
    assert len(constraints) == 4

    # All columns should have all row names
    assert all(set(c) == set(["foo", "bar", "baz", "quo", "qux"]) for c in constraints)

    # Plain integers in 'foo'
    assert constraints[0]["foo"] == ValueSet(1)
    assert constraints[1]["foo"] == ValueSet(2)
    assert constraints[2]["foo"] == ValueSet()  # Empty
    assert constraints[3]["foo"] == ValueSet(3)

    # Multiple integers in 'bar'
    assert constraints[0]["bar"] == ValueSet(10, 100)
    assert constraints[1]["bar"] == ValueSet(20, 200)
    assert constraints[2]["bar"] == ValueSet()  # Empty
    assert constraints[3]["bar"] == ValueSet(30, 300)

    # 'Ditto' used in 'baz'
    assert constraints[0]["baz"] == ValueSet(12)
    assert constraints[1]["baz"] == ValueSet(12)  # Ditto'd
    assert constraints[2]["baz"] == ValueSet()  # Empty
    assert constraints[3]["baz"] == ValueSet(3)

    # 'any', ranges and empty values used in 'quo'
    assert constraints[0]["quo"] == AnyValue()
    assert constraints[1]["quo"] == ValueSet((2, 200), (300, 3000))
    assert constraints[2]["quo"] == ValueSet()  # Empty
    assert constraints[3]["quo"] == ValueSet()

    # Booleans in 'qux'
    assert constraints[0]["qux"] == ValueSet(False)
    assert constraints[1]["qux"] == ValueSet(True)
    assert constraints[2]["qux"] == ValueSet()  # Empty
    assert constraints[3]["qux"] == ValueSet(True, False)
