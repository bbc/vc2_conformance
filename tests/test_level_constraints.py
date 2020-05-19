from vc2_data_tables import Levels

from vc2_conformance.level_constraints import (
    LEVEL_CONSTRAINTS,
    LEVEL_CONSTRAINT_ANY_VALUES,
)

from vc2_conformance.constraint_table import allowed_values_for


def test_all_levels_have_constraint_table_entries():
    assert set(Levels) == set(allowed_values_for(LEVEL_CONSTRAINTS, "level"))


def test_all_level_constraint_any_values_are_valid_level_constraints():
    all_keys = set()
    for table in LEVEL_CONSTRAINTS:
        all_keys.update(table)

    for key in LEVEL_CONSTRAINT_ANY_VALUES:
        assert key in all_keys
