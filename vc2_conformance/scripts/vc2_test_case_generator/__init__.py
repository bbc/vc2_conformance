"""
See `cli.py`. NB: This is a submodule to ensure that when this is executed as a
script, everything in that module is pickleable.
"""

import sys

from vc2_conformance.scripts.vc2_test_case_generator.cli import main


if __name__ == "__main__":
    sys.exit(main())
