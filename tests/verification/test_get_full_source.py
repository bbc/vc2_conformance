import sys
import inspect

from verification.get_full_source import get_full_source


# fmt: off

def f():
    return \
        123

    # Comment afterwards
# Comment not in function
pass  # noqa: E305 First non-function line

# fmt: on

# Filename of this script (not its *.pyc file)
_test_script_filename = inspect.getsourcefile(sys.modules[__name__])


def test_get_full_source():
    filename, lineno, full_source_lines = get_full_source(f)

    assert filename == _test_script_filename
    assert lineno == 9
    assert full_source_lines == [
        "def f():\n",
        "    return \\\n",
        "        123\n",
        "\n",
        "    # Comment afterwards\n",
    ]
