from vc2_conformance._py2x_compat import *


def test_zip_longest():
    # Sanity check as only renamed in Py 2.x
    assert list(zip_longest([1, 2, 3], [10, 20, 30, 40])) == [
        (1, 10),
        (2, 20),
        (3, 30),
        (None, 40),
    ]


def test_get_terminal_size():
    # Sanity check as fallback is crude
    rows, cols = get_terminal_size()
    assert isinstance(rows, int)
    assert isinstance(cols, int)


def test_wraps():
    def f():
        pass
    
    @wraps(f)
    def f_wrapper():
        pass
    
    assert f_wrapper.__wrapped__ is f


def test_unwrap():
    def f():
        pass
    
    @wraps(f)
    def f_wrapper():
        pass
    
    @wraps(f_wrapper)
    def f_wrapper_wrapper():
        pass
    
    assert unwrap(f_wrapper_wrapper) is f
    
    assert unwrap(
        f_wrapper_wrapper,
        stop=lambda f: f is f_wrapper,
    ) is f_wrapper
