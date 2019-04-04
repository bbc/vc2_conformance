import pytest

from vc2_conformance import bitstream


def test_notifications():
    class MyValue(bitstream.BitstreamValue):
        
        def __init__(self):
            self.deps_changed = []
            super(MyValue, self).__init__()
        
        def _dependency_changed(self, value):
            self.deps_changed.append(value)
    
    a = MyValue()
    b = MyValue()
    
    b._notify_on_change(a)
    
    # Single listener
    assert a.deps_changed == []
    b._changed()
    assert a.deps_changed == [b]
    assert b.deps_changed == []
    
    # Listen to multiple values
    c = MyValue()
    c._notify_on_change(a)
    c._changed()
    assert a.deps_changed == [b, c]
    assert b.deps_changed == []
    assert c.deps_changed == []
    
    # Coalesce change notifications
    with c._coalesce_change_notifications():
        with c._coalesce_change_notifications():
            c._changed()
            c._changed()
            assert a.deps_changed == [b, c]
        c._changed()
        c._changed()
        assert a.deps_changed == [b, c]
    assert a.deps_changed == [b, c, c]
    c._changed()
    assert a.deps_changed == [b, c, c, c]
    
    # Don't create notifications if none to coalesce...
    with c._coalesce_change_notifications():
        with c._coalesce_change_notifications():
            pass
    assert a.deps_changed == [b, c, c, c]
    
    # Cancel notifications
    c._cancel_notify_on_change(a)
    c._changed()
    assert a.deps_changed == [b, c, c, c]
    b._changed()
    assert a.deps_changed == [b, c, c, c, b]
    
    # Repeating the cancellation should have no effect...
    c._cancel_notify_on_change(a)
    
    c._changed()
    assert a.deps_changed == [b, c, c, c, b]
    b._changed()
    assert a.deps_changed == [b, c, c, c, b, b]


def test_wait_for_all_changes_before_cascading():
    # A tree of dependencies
    a = bitstream.ConstantValue(0)
    a1 = bitstream.FunctionValue(lambda v: v.value, a)
    a2 = bitstream.FunctionValue(lambda v: v.value, a)
    a11 = bitstream.FunctionValue(lambda v: v.value, a1)
    a12 = bitstream.FunctionValue(lambda v: v.value, a1)
    a21 = bitstream.FunctionValue(lambda v: v.value, a2)
    a22 = bitstream.FunctionValue(lambda v: v.value, a2)
    
    log = []
    logger = bitstream.FunctionValue(
        lambda *values: log.append(tuple(v.value for v in values)),
        a,
        a1,
        a2,
        a11,
        a12,
        a21,
        a22,
    )
    
    # Make a change
    a.value = 1
    
    # In every logged set of values, things at the same branch of the hierarchy
    # should be consistent
    assert len(log) == 8
    for a_v, a1_v, a2_v, a11_v, a12_v, a21_v, a22_v in log:
        assert a1_v == a2_v
        assert a11_v == a12_v
        assert a21_v == a22_v
