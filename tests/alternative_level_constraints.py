import os

from copy import deepcopy

from contextlib import contextmanager

from vc2_data_tables import Levels

from vc2_conformance.constraint_table import read_constraints_from_csv

from vc2_conformance.level_constraints import (
    LEVEL_CONSTRAINTS,
    LEVEL_SEQUENCE_RESTRICTIONS,
    LevelSequenceRestrictions,
)


@contextmanager
def temporary_level_override():
    """
    Reverse any changes made to
    :py:data:`~vc2_conformance.level_constraints.LEVEL_CONSTRAINTS` and
    :py:data:`~vc2_conformance.level_constraints.LEVEL_SEQUENCE_RESTRICTIONS`
    within this context manager when the context ends.
    """
    orig_constraints = deepcopy(LEVEL_CONSTRAINTS)
    orig_sequence_restrictions = deepcopy(LEVEL_SEQUENCE_RESTRICTIONS)

    try:
        yield
    finally:
        del LEVEL_CONSTRAINTS[:]
        LEVEL_CONSTRAINTS.extend(orig_constraints)

        LEVEL_SEQUENCE_RESTRICTIONS.clear()
        LEVEL_SEQUENCE_RESTRICTIONS.update(orig_sequence_restrictions)


@contextmanager
def alternative_level_1():
    """
    Replace level '1' in the
    :py:data:`~vc2_conformance.level_constraints.LEVEL_CONSTRAINTS` and
    :py:data:`~vc2_conformance.level_constraints.LEVEL_SEQUENCE_RESTRICTIONS`
    tables with a new level which defines a format equivalent to the
    ``MINIMAL_CODEC_FEATURES`` set which allows only interleaved pictures and
    sequence headers followed by an auxiliary and padding block at the end of
    the sequence.

    Use as a context manager::

        >>> from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

        >>> with alternative_level_1():
        ...     do_something(LEVEL_CONSTRAINTS)
    """
    with temporary_level_override():
        # Remove existing level 1 constraints
        del LEVEL_SEQUENCE_RESTRICTIONS[Levels(1)]
        for i in reversed(range(len(LEVEL_CONSTRAINTS))):
            if Levels(1) in LEVEL_CONSTRAINTS[i]["level"]:
                del LEVEL_CONSTRAINTS[i]

        # Add alternative constraints
        LEVEL_SEQUENCE_RESTRICTIONS[Levels(1)] = LevelSequenceRestrictions(
            sequence_restriction_explanation=(
                "Interleaved pictures and sequence headers followed by "
                "padding and auxiliary data at the end of the stream."
            ),
            sequence_restriction_regex=(
                "(sequence_header high_quality_picture)+ "
                "padding_data auxiliary_data end_of_sequence"
            ),
        )
        LEVEL_CONSTRAINTS.extend(
            read_constraints_from_csv(
                os.path.join(
                    os.path.dirname(__file__),
                    "alternative_level_constraints.csv",
                )
            )
        )

        yield (LEVEL_CONSTRAINTS, LEVEL_SEQUENCE_RESTRICTIONS)
