import json
from datetime import datetime, timezone
from pathlib import Path


class AlertExporter:
    """Writes alert dictionaries to a newline-delimited JSON (.jsonl) file.

    Each line in the output file is a self-contained JSON object with three
    top-level keys:
        - "alert"      : the alert dict produced by build_alert()
        - "telemetry"  : the raw telemetry row that triggered the alert
        - "exported_at": ISO 8601 UTC timestamp of when the line was written

    The file is opened in append mode so multiple runs accumulate.
    Call close() or use as a context manager to flush and close.

    Parameters
    ----------
    path : str or Path
        Destination file path. Parent directories are created automatically.
    enabled : bool
        When False, all write methods are no-ops and no file is created.
    """

    def __init__(self, path, enabled=True):
        self.enabled = enabled
        self._handle = None

        if not enabled:
            return

        resolved = Path(path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._handle = resolved.open("a", encoding="utf-8")

    def write_alert(self, alert, telemetry_row=None):
        """Write one alert as a single JSON line.

        Parameters
        ----------
        alert : dict
            An alert dict produced by build_alert().
        telemetry_row : dict, optional
            The telemetry row that triggered the alert.
        """
        if not self.enabled or self._handle is None:
            return

        record = {
            "alert": alert,
            "telemetry": telemetry_row,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        self._handle.write(json.dumps(record, default=str) + "\n")

    def write_batch(self, alerts, telemetry_row=None):
        """Write multiple alerts, each as its own JSON line.

        Parameters
        ----------
        alerts : list[dict]
            List of alert dicts.
        telemetry_row : dict, optional
            The telemetry row shared by all alerts in this batch.
        """
        for alert in alerts:
            self.write_alert(alert, telemetry_row)

    def flush(self):
        """Force buffered data to disk."""
        if self._handle is not None:
            self._handle.flush()

    def close(self):
        """Flush and close the file handle."""
        if self._handle is not None:
            self._handle.flush()
            self._handle.close()
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
