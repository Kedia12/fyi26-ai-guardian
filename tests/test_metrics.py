from guardian.metrics import collect_metrics_for_scenario


def test_collect_metrics_for_scenario_returns_expected_keys(tmp_path):
    csv_path = tmp_path / "scenario.csv"
    csv_path.write_text(
        "timestamp_ms,packet_id,node_id,accel_x_g,accel_y_g,accel_z_g,"
        "gyro_x_dps,gyro_y_dps,gyro_z_dps,temperature_c,pressure_hpa,"
        "altitude_est_m,battery_voltage_v,low_power_flag,gps_lat_deg,"
        "gps_lon_deg,gps_alt_m,gps_speed_mps,gps_fix_status,"
        "satellite_count,link_status,mode_state\n"
        "1000,1,aircraft_01,0.01,0.02,1.0,0.5,0.4,0.3,25.0,1013.2,120.0,11.1,0,-1.95,30.06,121.0,10.0,1,8,connected,normal\n"
        "1100,3,aircraft_01,0.01,0.02,1.0,0.5,0.4,0.3,25.0,1013.2,120.0,11.1,0,-1.95,30.06,121.0,10.0,1,8,connected,normal\n"
    )

    metrics = collect_metrics_for_scenario(csv_path)

    assert metrics["scenario"] == "scenario.csv"
    assert metrics["rows_processed"] == 2
    assert metrics["alerts_generated"] >= 1
    assert "PACKET_LOSS" in metrics["observed_reason_codes"]
