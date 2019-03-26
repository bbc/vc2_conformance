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
