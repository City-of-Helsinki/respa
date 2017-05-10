import time


class TimedOut(Exception):
    pass


class Timeout:
    """
    A simple timeout class.

    Usage example:

    >>> t = Timeout(0.05)
    >>> assert not t.timed_out
    >>> time.sleep(0.1)
    >>> assert t.timed_out
    """

    def __init__(self, seconds):
        self.seconds = float(seconds)
        self.start = None
        self.reset()

    def reset(self):
        """
        Reset the timeout to the current instant.
        """
        self.start = time.time()

    @property
    def timed_out(self):
        return (time.time() - self.start) >= self.seconds


class EventedTimeout(Timeout):
    def __init__(self, seconds, on_timeout):
        super().__init__(seconds)
        assert callable(on_timeout)
        self.on_timeout = on_timeout

    def check(self, reset=True):
        """
        Check if we're timed out; if we are, call the `on_timeout`
        callback and reset the timeout (if `reset` is set).

        :param reset: Whether to reset the timeout when ticking.
        :type reset: bool

        :return: A tuple of a boolean and the retval of `on_timeout`.
        :rtype: tuple[bool, object]
        """
        if self.timed_out:
            if reset:
                self.reset()
            return (True, self.on_timeout())
        return (False, None)
