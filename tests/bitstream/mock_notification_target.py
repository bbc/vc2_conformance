from vc2_conformance.bitstream import BitstreamValue


class MockNotificationTarget(BitstreamValue):
    """
    For use in tests. A BitstreamValue which logs how many times its
    dependencies change.
    """
    
    def __init__(self):
        self.notifications = []
        super(MockNotificationTarget, self).__init__()
    
    def _dependency_changed(self, value):
        self.notifications.append(value)
    
    def reset(self):
        self.notifications = []
    
    @property
    def notification_count(self):
        return len(self.notifications)
