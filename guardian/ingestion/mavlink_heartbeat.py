"""
MAVLink heartbeat monitor.

Runs a daemon timer that restarts on every received HEARTBEAT message.
If no heartbeat arrives within *timeout_s* seconds, the *on_timeout*
callback is invoked (and the timer restarts so monitoring continues).
"""

import threading


class HeartbeatMonitor:
    """Monitor for MAVLink HEARTBEAT messages.

    Parameters
    ----------
    timeout_s : float
        Seconds without a heartbeat before ``on_timeout`` is called.
    on_timeout : callable, optional
        Zero-argument callable invoked on each timeout event.
    """

    def __init__(self, timeout_s=3.0, on_timeout=None):
        self.timeout_s = timeout_s
        self.on_timeout = on_timeout
        self._timer = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Arm the monitor and start the first timeout interval."""
        self._running = True
        self._schedule()

    def heartbeat_received(self):
        """Reset the timer; call this on every received HEARTBEAT message."""
        if self._running:
            self._schedule()

    def stop(self):
        """Disarm the monitor and cancel any pending timer."""
        with self._lock:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _schedule(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            if not self._running:
                return
            self._timer = threading.Timer(self.timeout_s, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self):
        if not self._running:
            return
        if self.on_timeout is not None:
            self.on_timeout()
        # Restart the interval so monitoring continues after timeout
        self._schedule()
