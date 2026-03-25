from guardian.replay import replay_csv


def test_replay_csv_yields_rows(tmp_path):
    csv_path = tmp_path / "scenario.csv"
    csv_path.write_text(
        "timestamp_ms,packet_id,node_id\n"
        "1000,1,aircraft_01\n"
        "1100,2,aircraft_01\n"
    )

    rows = list(replay_csv(csv_path, sleep_enabled=False))

    assert len(rows) == 2
    assert rows[0]["packet_id"] == "1"
    assert rows[1]["packet_id"] == "2"


def test_replay_csv_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.csv"

    try:
        list(replay_csv(missing_path, sleep_enabled=False))
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        assert True
        