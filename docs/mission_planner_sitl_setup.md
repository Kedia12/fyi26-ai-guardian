# Mission Planner + ArduPilot SITL Setup (Windows)

How to get a live, simulated ArduCopter streaming real MAVLink telemetry into Guardian on Windows, without WSL or compiling ArduPilot from source. This is the setup validated end-to-end against `guardian/ingestion/mavlink_listener.py`.

---

## 1. Install Mission Planner

Download and run the Windows installer: https://ardupilot.org/planner/docs/mission-planner-installation.html

This bundles a precompiled Windows SITL binary — no separate ArduPilot source checkout or build tools needed.

**Use the Stable firmware channel, not "Latest (Dev)".** The bundled dev build has a boot bug where it hangs forever at `Waiting for internal clock bits to be set (current=0x00)` — a DDS/ROS2 clock-init issue specific to that dev build. To pick the channel: Mission Planner's **Simulation** tab → **Options** panel → the version dropdown (defaults to "Latest (Dev)") → change to **Stable** → click **Multirotor** to trigger the download.

The downloaded binary ends up at:
```
Documents\Mission Planner\sitl\ArduCopter.exe
```

---

## 2. Launch SITL directly from a terminal

Mission Planner's own "Simulation" tab GUI launcher is unreliable for this workflow — its "extra output" UDP relay feature is buggy (binds ports it shouldn't, crashes with `Invalid device path` on some device strings) and prone to silent disconnects. Launch the binary directly instead, which gives full control and is far more stable:

```bash
cd "C:\Users\<you>\Documents\Mission Planner\sitl"
./ArduCopter.exe --model quad --home -35.363261,149.165230,584,353 --speedup 1 -I0 --wipe
```

- `--home lat,lon,alt,heading` — the default ArduPilot SITL home (CMAC field, Canberra AU). Guardian's geofence config should be centered on this (see §5).
- `--wipe` — clears eeprom/parameter state. Use on first launch or after things get into a bad state; omit on subsequent launches if you want saved parameters (battery/frame/arming settings, see §4) to persist.

**Important behavior:** this binary blocks on `Waiting for connection ....` and does **not** proceed with the rest of its boot sequence (or open its secondary ports) until a MAVLink client connects to its primary port. It also **exits entirely** if that primary connection is ever closed — even briefly. Whichever process holds the primary connection needs to be long-running.

Once a client connects to the primary port, it also opens two more TCP ports for additional simultaneous clients:

| Port | Role |
|---|---|
| `5760` | SERIAL0 — primary connection, unblocks the rest of boot |
| `5762` | SERIAL1 — secondary connection |
| `5763` | SERIAL2 — tertiary connection |

All three serve the same live vehicle simultaneously — e.g. Guardian can hold one while Mission Planner's GUI holds another, with neither disturbing the other.

---

## 3. Point Guardian at it

In `config/guardian_config.yaml`:

```yaml
ingestion:
  mode: mavlink
  mavlink_connection: tcp:127.0.0.1:5762   # or 5760/5763 — whichever port is free
  mavlink_system_id: 1
```

Then run:

```bash
python -m guardian.main --live mavlink
```

If Guardian is the *first* thing to connect (before Mission Planner), point it at **5760** — this is what unblocks SITL's boot and keeps it alive. If Mission Planner connects first (or already holds 5760), point Guardian at **5762** instead so it doesn't compete for the same port.

**Connecting Mission Planner's own GUI on a secondary port:** top-right toolbar → connection type dropdown → **TCP** → click **CONNECT** → it prompts for host (`127.0.0.1`) and port (`5762` or `5763`, whichever Guardian isn't using).

---

## 4. Common PreArm blockers and fixes

A freshly wiped SITL vehicle fails several of ArduPilot's real arming checks, because the minimal bundled default parameter file doesn't fully configure a "real" vehicle the way Mission Planner's setup wizard normally would. These can all be fixed by sending `PARAM_SET` over MAVLink (via pymavlink, or Mission Planner's Config → Full Parameter List):

| PreArm error | Fix |
|---|---|
| `PreArm: Motors: Check frame class and type` | Set `FRAME_CLASS=1` (Quad), `FRAME_TYPE=1` (X). **Requires a reboot to take effect** (see below). |
| `PreArm: Battery 1 unhealthy` | Either leave `BATT_MONITOR=0` (disabled — battery just reads 0V, but this doesn't block arming), or fully configure a real analog monitor (`BATT_MONITOR=4` + valid pin/multiplier params — we could not get this working reliably on this build; not worth chasing for pure ingestion testing). |
| `PreArm: 3D Accel calibration needed` | Full 6-orientation accel cal doesn't translate to a simulator. Easiest fix: disable arming checks entirely with `ARMING_CHECK=0` — this is ArduPilot's own supported mechanism for bench/SITL testing, not a hack. |
| Auto-disarms ~10s after arming with no error | Normal safety behavior (no throttle/climb command issued in time). Either act fast, or raise `DISARM_DELAY` (e.g. to `127`, its max) for more breathing room. |

**Rebooting after a parameter change:** some params (`FRAME_CLASS`, `BATT_MONITOR`) only take effect after an autopilot reboot. Send:

```python
conn.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN, 0, 1, 0, 0, 0, 0, 0, 0)
```

This can occasionally spawn a duplicate/orphaned `ArduCopter.exe` process on this Windows build. After rebooting, always confirm which process actually owns the listening ports before killing anything:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 5760,5762,5763 | Select-Object LocalPort, OwningProcess
```

Don't guess by PID or start time — check port ownership directly.

---

## 5. Geofence config alignment

Guardian's `geofence.polygon` in `config/guardian_config.yaml` must actually surround wherever the SITL vehicle's home position is, or every single packet will trip `GEOFENCE_BREACH` immediately. For the default CMAC home used above:

```yaml
geofence:
  enabled: true
  polygon:
    - [-35.3933, 149.1352]
    - [-35.3933, 149.1952]
    - [-35.3333, 149.1952]
    - [-35.3333, 149.1352]
```

---

## 6. Triggering a live fault for testing

To exercise Guardian's rule engine against genuinely live (not replayed) fault data without needing to fly:

```python
conn.mav.param_set_send(1, 1, b'SIM_BATT_VOLTAGE', 9.5, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
```

This overrides the simulated battery voltage directly and should trigger a real-time `LOW_BATTERY` alert in Guardian within a few packets, matching the same thresholds validated against `data/scenarios/low_battery.csv`.

---

## 7. Known limitations

- **Battery voltage often reads 0V** on this Windows SITL build even with `BATT_MONITOR` configured — the standard analog pin parameters (`BATT_VOLT_PIN`, `BATT_CURR_PIN`, etc.) aren't valid parameter names on this particular build/version, and we didn't find a working alternative. This is a simulator display quirk, not a bug in Guardian's ingestion — Guardian correctly reports whatever SYS_STATUS value the simulator actually sends.
- **The SITL process dies if left running across a machine sleep/long idle gap**, along with Guardian's connection to it. If telemetry looks frozen/stale, check the `inserted_at` timestamp on the latest `Telemetry` row — if it's old, SITL and/or Guardian's live ingestion need restarting.
- Existing SITL integration tests (`tests/test_mavlink_listener.py`) default to expecting a MAVProxy-bridged UDP connection (`udpin:0.0.0.0:14550`), matching the original documented architecture. Override with the `MAVLINK_SIM_CONNECTION` env var to point at a direct TCP port instead, e.g.:
  ```bash
  MAVLINK_SIM=1 MAVLINK_SIM_CONNECTION="tcp:127.0.0.1:5763" pytest tests/test_mavlink_listener.py -v
  ```
