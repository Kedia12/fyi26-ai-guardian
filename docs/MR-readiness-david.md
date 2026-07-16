# Manual Review — Readiness Sheet (David · DB · Dashboard · QA)

One-page prep for the Technical Manual Review. The MR is oral: repo + app must be ready, and you must *explain* your work. Tick each box, then rehearse the Q&A.

---

## Readiness checklist

**Before the review**
- [ ] Root `README.md` exists with architecture diagram + database diagram (MR requires it at repo root, not just `docs/`).
- [ ] Application architecture diagram renders on GitHub.
- [ ] Database diagram renders on GitHub.
- [ ] All work committed; clean commit history; stray files (`=3.0`, `=3.5`) removed.
- [ ] `pytest` passes locally — capture output as evidence (`pytest -v`).
- [ ] Demo rehearsed end-to-end 2–3 times.
- [ ] Backup screenshots of a working demo (in case the live sim glitches).

**Demo flow to show**
- [ ] Launch plane in Mission Planner (SITL) → arm → AUTO → it flies the mission.
- [ ] Guardian MAVLink listener ingests the live telemetry.
- [ ] Dashboard shows live telemetry + an alert appearing.
- [ ] Acknowledge / escalate / resolve an alert (human-in-the-loop).
- [ ] Show the alert is stored (DB) and that the action was recorded.

---

## Likely questions + model answers (your area)

**Q: Walk me through your database design.**
Four main tables: telemetry, alerts, operator actions, and users. Every alert is linked back to the exact telemetry packet that triggered it, so any alert is fully traceable to the moment in the data that caused it. Operator actions (acknowledge/escalate/resolve) are recorded so there's a full audit trail of who decided what.

**Q: Why SQLite, and why WAL mode?**
SQLite is a single portable file with zero server setup — ideal for a prototype and easy to demo/deploy. WAL (write-ahead logging) lets the detection engine keep writing new alerts while the dashboard reads at the same time, without them blocking each other. We'd move to PostgreSQL if this went to real scale.

**Q: How does the dashboard work?**
Flask REST API in Python reads from the database; a React front end polls that API every few seconds and refreshes. So it's near real time — new alerts appear on the next refresh. Guiding principle is human-in-the-loop: the system flags and recommends, a person makes the final call.

**Q: How is authentication handled? Are passwords secure?**
Username/password login using Flask's signed-cookie sessions. Passwords are **hashed** with werkzeug's password hashing — never stored in plain text. Two roles (RBAC): **admin** can act on alerts and create users; **user** is view-only. Roles are enforced **server-side** (admin-only routes return 403), not just hidden in the UI.

**Q: What is RBAC and how did you implement it?**
Role-Based Access Control — permissions attached to a role, not an individual. `login_required` gates every dashboard route; `role_required("admin")` gates the action/report/create-user routes. A view-only user literally cannot call an admin endpoint even by hitting the API directly.

**Q: How did you test the application?**
162 automated tests (pytest) across detection rules, database, and every dashboard route, run automatically on GitHub Actions on every push. For the dashboard I used Flask's test client against a test database, so I can prove a click changes the right DB record without clicking through by hand. We also measured detection quality — ~86.4% precision, ~90.9% recall across 11 fault scenarios — with recall tuned higher because missing a real hazard is worse than a false alarm.

**Q: What does 86.4% precision / 90.9% recall mean?**
Of the alerts raised, ~86% were real (precision); of the actual faults present, ~91% were caught (recall). We favour recall for a safety tool.

**Q: What was the hardest part of your work?**
Reliably recording operator actions and letting the engine and dashboard read/write the database at the same time — which is exactly why WAL mode mattered.

---

## General questions (know these too)

**Q: How does the whole application work, end to end?**
Telemetry comes off the aircraft (CSV replay, UDP, serial, or MAVLink). The Guardian engine runs it through deterministic rule checks plus an Isolation Forest ML model and builds structured alerts (severity, plain-language reason, recommended action). Alerts are stored in SQLite and exported as JSONL. The Flask + React dashboard shows telemetry and alerts, and the operator acknowledges/escalates/resolves them.

**Q: Why rules AND machine learning?**
Rules give explainable, deterministic catches for known faults; the Isolation Forest catches anomalies we didn't write a rule for. Together you get coverage plus traceability — essential in aerospace.

**Q: How did the team collaborate?**
Agile, three sprints. Kedia (PM/SCM) led detection rules, ML, live ingestion, MAVLink, and CI. I owned the database, dashboard, operator API, and QA. Work split by feature branches with code review before merging to `main`; progress tracked through the sprint plan and commit history.

**Q: Git/GitHub practices?**
Feature branches, reviewed pull requests before merge, meaningful commit messages, and CI (GitHub Actions) running the full test suite on every push.

---

## If you get stuck
Be honest, reason out loud, and tie it back to a design decision. "We chose X because Y, and the tradeoff was Z" scores better than a memorised fact. You built the data and operations side — own it.
