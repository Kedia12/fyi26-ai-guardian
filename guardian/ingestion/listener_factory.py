from guardian.ingestion.udp_listener import UDPListener
from guardian.ingestion.serial_listener import SerialListener
from guardian.ingestion.mqtt_listener import MQTTListener
from guardian.ingestion.mavlink_listener import MAVLinkListener


def create_listener(config):
    """Return the appropriate listener for the configured ingestion mode.

    Parameters
    ----------
    config : dict
        Full Guardian config dict (as returned by ``get_config()``).

    Returns
    -------
    UDPListener | SerialListener | MQTTListener | MAVLinkListener

    Raises
    ------
    ValueError
        If ``config["ingestion"]["mode"]`` is not a recognised value.
    """
    ingestion = config.get("ingestion", {})
    mode = ingestion.get("mode", "udp")

    if mode == "udp":
        return UDPListener(
            host=ingestion.get("udp_host", "0.0.0.0"),
            port=int(ingestion.get("udp_port", 14550)),
        )

    if mode == "serial":
        return SerialListener(
            port=ingestion.get("serial_port", "COM3"),
            baud=int(ingestion.get("serial_baud", 57600)),
        )

    if mode == "mqtt":
        return MQTTListener(
            broker=ingestion.get("mqtt_broker", "localhost"),
            port=int(ingestion.get("mqtt_port", 1883)),
            topic=ingestion.get("mqtt_topic", "guardian/telemetry"),
        )

    if mode == "mavlink":
        return MAVLinkListener(
            connection_string=ingestion.get(
                "mavlink_connection",
                f"udp:{ingestion.get('udp_host', '0.0.0.0')}:{ingestion.get('udp_port', 14550)}",
            ),
            system_id=int(ingestion.get("mavlink_system_id", 1)),
        )

    raise ValueError(
        f"Unknown ingestion mode: {mode!r}. "
        "Valid options: udp, serial, mqtt, mavlink."
    )
