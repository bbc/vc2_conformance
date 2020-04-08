"""
Test utility which swaps the large, pictures in
:py:data:`vc2_conformance_data.NATURAL_PICTURES_FILENAMES` with tiny test
pictures to speed up testing.
"""

import pytest

import os

from contextlib import contextmanager

from vc2_conformance_data import (
    NATURAL_PICTURES_FILENAMES,
)

# All of these contain a 16x16 pixel white square on a black background.
TEST_PICTURES_PATHS = [
    os.path.join(
        os.path.dirname(__file__),
        "test_images",
        filename,
    )
    for filename in [
        "square.raw",
        "wide.raw",
        "tall.raw",
    ]
]

@contextmanager
def alternative_real_pictures(alternative_paths=TEST_PICTURES_PATHS):
    """
    Replace the (very large) real pictures the provided alternative images for
    the purposes of these tests to reduce testing overhead.
    
    Use as a context manager::
    
        >>> from vc2_conformance.picture_generators import NATURAL_PICTURES_FILENAMES
        
        >>> with alternative_real_pictures():
        ...     do_something(NATURAL_PICTURES_FILENAMES)
    """
    orig_paths = list(NATURAL_PICTURES_FILENAMES)
    
    del NATURAL_PICTURES_FILENAMES[:]
    NATURAL_PICTURES_FILENAMES.extend(alternative_paths)
    
    try:
        yield NATURAL_PICTURES_FILENAMES
    finally:
        del NATURAL_PICTURES_FILENAMES[:]
        NATURAL_PICTURES_FILENAMES.extend(orig_paths)


@pytest.yield_fixture
def replace_real_pictures_with_test_pictures():
    """
    Pytext fixture for alternative_real_pictures.
    """
    with alternative_real_pictures() as paths:
        yield paths
