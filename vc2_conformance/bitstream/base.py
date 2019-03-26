"""
Base class definition for :py:class:`BitstreamValue`, the generic interface
implemented by all bitstream interfaces.
"""

from weakref import WeakSet

from contextlib import contextmanager

__all__ = [
    "BitstreamValue",
]

class BitstreamValue(object):
    """
    The various subclasses of this class represent values which may be
    deserialised-from/seriallised-to a VC-2 bitstream (using :py:meth:`read`
    and :py:meth:`write` respectively).
    
    This class does not contain a useful implementation and mostly serves to
    defines the required API.
    """
    
    def __init__(self):
        # The (bytes, bits) tuple describing the starting offset of the last
        # read/write operation. Implementors should change this as required.
        self._offset = None
        
        # The number of bits read/written past the end of the file.
        # Implementors should change this as required.
        self._bits_past_eof = None
        
        # A WeakSet of BitstreamValue references, registered using
        # '_notify_on_change()', which will be notified whenever this value
        # changed.
        self._dependent_values = WeakSet()
        
        # A simple counting semaphore which, when non-zero, causes changed() to
        # be a no-op.
        self._suppress_change_notifications_semaphore = 0
        
        # The number of calls to 'changed()' while
        # _suppress_change_notifications_semaphore has been non-zero.
        self._suppressed_change_notifications = 0
    
    @property
    def value(self):
        """The value repersented by this object in a native Python type."""
        raise NotImplementedError()
    
    @property
    def length(self):
        """The number of bits used to represent this value in the bitstream."""
        raise NotImplementedError()
    
    @property
    def offset(self):
        """
        If this value has been seriallised/deseriallised, this will contain the
        offset into the stream where the first bit was read/written as a
        (bytes, bits) tuple (see :py:meth:`BitstreamReader.tell`). None
        otherwise.
        
        This value is set to None whenever :py:attr:`value` is chagned.
        """
        return self._offset
    
    @property
    def bits_past_eof(self):
        """
        If this value has been seriallised/deseriallised from a bitstream but
        all or part of the value was located past the end of the file (or past
        the end of a :py:class:`BoundedBlock`), gives the number of bits beyond
        the end which were read/written. Set to None otherwise.
        
        This value is set to None whenever :py:attr:`value` is chagned.
        """
        return self._bits_past_eof
    
    def read(self, reader):
        """
        Read and deserialise this value from the next bits read by the provided
        :py:class:`BitstreamReader`.
        
        Sets the :py:attr:`offset` and :py:attr:`bits_past_eof` parameters.
        """
        raise NotImplementedError()
    
    def write(self, writer):
        """
        Serialise and write this value to the provided
        :py:class:`BitstreamWriter`.
        
        Sets the :py:attr:`offset` and :py:attr:`bits_past_eof` parameters.
        """
        raise NotImplementedError()
    
    def _changed(self):
        r"""
        For internal use by :py:class:`BitstreamValue` subclasses.
        
        Call this method whenever this :py:class:`BitstreamValue` (may) have
        changed in some material way, for example its value or length has
        changed. Immediately notifies any other :py:class:`BitstreamValue`\ s
        registered using :py:meth:`_notify_on_change`.
        """
        if not self._suppress_change_notifications_semaphore:
            # NB: Iterate over a copy of the set in case any entries are garbage
            # collected as a result of '_dependency_changed' being called.
            for dependent in list(self._dependent_values):
                dependent._dependency_changed(self)
        else:
            self._suppressed_change_notifications += 1
    
    @contextmanager
    def _coalesce_change_notifications(self):
        """
        For internal use by :py:class:`BitstreamValue` subclasses.
        
        A context manager which will coalesce any calls to :py:meth:`_changed`
        within the block into a single call when the block exits.
        """
        self._suppress_change_notifications_semaphore += 1
        try:
            yield
        finally:
            self._suppress_change_notifications_semaphore -= 1
            
            if self._suppress_change_notifications_semaphore == 0:
                if self._suppressed_change_notifications:
                    self._suppressed_change_notifications = 0
                    self._changed()
    
    def _notify_on_change(self, dependent):
        """
        For internal use by :py:class:`BitstreamValue` subclasses.
        
        When :py:meth:`_changed` is called on this :py:class:`BitstreamValue`,
        call :py:meth:`_dependency_changed` will be called on the passed
        :py:class:`BitstreamValue`. The method will be passed a reference to
        this object as its argument.
        
        .. note::
            
            The passed :py:class:`BitstreamValue` will be kept as a weak
            reference ensuring that it is not kept alive by this callback
            registration.
        
        .. warning::
            
            Dependencies must be created in a purely hierarchical fashion with
            no cycles.
        """
        # NB: The reason we keep references to BitstreamValue classes rather
        # than arbitrary functions is that Python's weak references can behave
        # surprisingly with references to functions and bound-methods in
        # particular.
        self._dependent_values.add(dependent)
    
    def _cancel_notify_on_change(self, dependent):
        """
        For internal use by :py:class:`BitstreamValue` subclasses.
        
        Cancel all future notifications to 'dependent' when this value is
        changed.
        """
        try:
            self._dependent_values.remove(dependent)
        except KeyError:
            pass
    
    def _dependency_changed(self, dependency):
        """
        To be overridden by :py:class:`BitstreamValue` subclasses which wish to
        pass themselves to other :py:class:`BitstreamValue` instances'
        :py:meth:`_notify_on_change` method.
        
        The single argument will be the :py:class:`BitstreamValue` instance
        which produced the change notification using :py:meth:`_changed`.
        """
        raise NotImplementedError()
    
    def __repr__(self):
        return "<{} value={!r} length={!r} offset={!r} bits_past_eof={!r}>".format(
            self.__class__.__name__,
            self.value,
            self.length,
            self.offset,
            self.bits_past_eof,
        )
    
    def __str__(self):
        """
        The string representation used for human-readable representations of a
        value. By convention values which contain any bits past the EOF (or end
        of a bounded block) are shown with an asterisk afterwards.
        """
        if self.bits_past_eof:
            return "{}*".format(str(self.value))
        else:
            return str(self.value)
