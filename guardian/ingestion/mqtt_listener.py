import threading

try:
    import paho.mqtt.client as _mqtt
    _MQTT_AVAILABLE = True
except ImportError:
    _MQTT_AVAILABLE = False

from guardian.ingestion.udp_listener import parse_json_packet


class MQTTListener:
    """Subscribe to an MQTT topic and invoke a callback for each message.

    Requires ``paho-mqtt`` to be installed. Raises ``RuntimeError`` at
    instantiation time if the package is missing.

    Parameters
    ----------
    broker : str
        MQTT broker hostname or IP.
    port : int
        MQTT broker port (default 1883).
    topic : str
        Topic to subscribe to (default ``"guardian/telemetry"``).
    parser : callable, optional
        Function ``(bytes) -> dict | None`` to parse each message payload.
        Defaults to :func:`parse_json_packet`.
    """

    def __init__(self, broker="localhost", port=1883,
                 topic="guardian/telemetry", parser=None):
        if not _MQTT_AVAILABLE:
            raise RuntimeError(
                "paho-mqtt is not installed. Run: pip install paho-mqtt>=1.6"
            )
        self.broker = broker
        self.port = port
        self.topic = topic
        self.parser = parser or parse_json_packet
        self._client = None
        self._callback = None

    def start(self, callback):
        """Connect to the broker, subscribe, and start the network loop."""
        self._callback = callback
        self._client = _mqtt.Client()
        self._client.on_message = self._on_message
        self._client.connect(self.broker, self.port)
        self._client.subscribe(self.topic)
        self._client.loop_start()

    def _on_message(self, client, userdata, message):
        row = self.parser(message.payload)
        if row is not None and self._callback is not None:
            self._callback(row)

    def stop(self):
        """Stop the network loop and disconnect from the broker."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
