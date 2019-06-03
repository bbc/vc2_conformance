from vc2_conformance.tables import Levels, LEVEL_CONSTRAINTS
from vc2_conformance._constraint_table import allowed_values_for


def test_all_levels_have_constraint_table_entries():
    assert set(Levels) == set(allowed_values_for(LEVEL_CONSTRAINTS, "level"))
