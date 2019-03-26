import pytest

from mock import Mock

from vc2_conformance import bitstream


def test_constant_value():
    c = bitstream.ConstantValue(123)
    assert c.value == 123
    
    notify = Mock()
    c._notify_on_change(notify)
    
    c.value = 321
    assert c.value == 321
    assert notify._dependency_changed.call_count == 1
    
    ve = ValueError()
    c.exception = ve
    assert c.exception is ve
    assert notify._dependency_changed.call_count == 2
    with pytest.raises(ValueError):
        c.value
    
    c.value = 123
    assert c.value == 123
    assert c.exception is None
    assert notify._dependency_changed.call_count == 3


def test_function_value():
    c1 = bitstream.ConstantValue(1)
    c2 = bitstream.ConstantValue(2)

    f = bitstream.FunctionValue(lambda a, b, c: a.value - b.value + c.value, c1, c2, 3)
    assert f.value == 2
    
    notify = Mock()
    f._notify_on_change(notify)
    
    c1.value = 0
    assert f.value == 1
    assert notify._dependency_changed.call_count == 1
    
    c2.value = 0
    assert f.value == 3
    assert notify._dependency_changed.call_count == 2

def test_function_value_exception():
    c1 = bitstream.ConstantValue(1.0)
    c2 = bitstream.ConstantValue(2.0)

    f = bitstream.FunctionValue(lambda a, b: a.value / b.value, c1, c2)
    assert f.value == 0.5
    
    notify = Mock()
    f._notify_on_change(notify)
    
    c1.value = 0.0
    assert f.value == 0.0
    assert notify._dependency_changed.call_count == 1
    
    # Error doesn't appear when value changes...
    c2.value = 0.0
    
    # ...but does when read
    with pytest.raises(ZeroDivisionError):
        f.value
    with pytest.raises(ZeroDivisionError):
        f.value
    assert notify._dependency_changed.call_count == 2
    
    c2.value = 1.0
    assert f.value == 0.0
    assert notify._dependency_changed.call_count == 3
