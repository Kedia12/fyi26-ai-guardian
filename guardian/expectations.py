EXPECTED_REASON_CODES = {
    "normal_flight.csv": [],
    "packet_loss.csv": ["PACKET_LOSS"],
    "sensor_dropout.csv": ["IMU_DROPOUT"],
    "gps_jump.csv": ["GPS_JUMP"],
    "low_battery.csv": ["LOW_BATTERY"],
    "out_of_order_packets.csv": ["OUT_OF_ORDER_PACKET"],
    "duplicate_packet.csv": ["DUPLICATE_PACKET"],
    "frozen_imu.csv": ["IMU_FROZEN"],
    "gps_fix_loss.csv": ["GPS_FIX_LOSS"],
    "gps_imu_inconsistency.csv": ["GPS_IMU_INCONSISTENCY"],
    "combined_fault.csv": [
        "LOW_BATTERY",
        "PACKET_LOSS",
        "IMU_DROPOUT",
        "GPS_FIX_LOSS",
        "GPS_JUMP",
    ],
}
