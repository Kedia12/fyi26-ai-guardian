# FYI26 AI Guardian — Stage 4 & 5 Completion TODO

**Team:** Kedia Ihogoza (PM / AI-ML / SCM) · David Roset (DB / Dashboard / QA)
**Goal:** Finish Stage 4 deliverables, complete Stage 5 (Project Closure), and pass the Technical Manual Review (MR).
**Status legend:** ✅ done · 🔲 to do · ⚠️ needs check

---

## 0. Blockers to fix first

- 🔲 **Add a root `README.md`.** The MR explicitly requires a clean README **at the repo root** with the application architecture and the database diagram. Right now the README only lives in `docs/`. Copy/adapt `docs/README.md` to `/README.md` and embed both diagrams.
- ⚠️ **Remove stray junk files** from repo root (`=3.0`, `=3.5` — these look like accidental `pip install >=3.0` redirects). Delete and commit.

---

## 1. Stage 4 — MVP & Execution (mostly done, verify)

- ✅ MVP implemented — 5 features complete (geofencing, post-flight report, predictive alerts, login, landing page).
- ✅ Sprints planned & documented (`docs/stage-4-mvp-development-and-execution.md`, 3 sprints).
- ✅ Test suite exists (25 test files under `tests/`).
- 🔲 **Run the full test suite and capture output** as testing evidence: `pytest -v > docs/test-results.txt`. The MR asks *how you tested* — have proof.
- 🔲 **Confirm sprint reviews + retrospectives are written down.** Stage 4 doc mentions them but there's no standalone retro. Add a short `docs/sprint-retrospectives.md` (what went well / challenges / improvements per sprint).
- 🔲 **Bug tracking link.** Stage 4 deliverables list "Bug tracking" — link your GitHub Issues (or Trello/Jira board) in the README/report.
- 🔲 **Verify diagrams render** — architecture diagram (`docs/architecture.md`) and DB diagram. Confirm the Mermaid charts display correctly on GitHub.

---

## 2. Stage 5 — Project Closure (main remaining work)

### 2a. Final Report (`docs/stage-5-closure-report.md`)
- 🔲 **Results summary** — core MVP functionalities; compare outcomes vs. the Project Charter objectives; include metrics (features delivered %, precision/recall numbers, test pass rate, bug count).
- 🔲 **Lessons learned** — what went well & why; challenges + how you solved them; improvements for next time.
- 🔲 **Team retrospective highlights** — pull key points from the retro meeting.

### 2b. Presentation slide deck (`.pptx` or Google Slides)
Suggested structure (7 slides):
- 🔲 Title + team intro
- 🔲 Project overview / charter + MVP concept
- 🔲 Process summary across Stages 1–4
- 🔲 Technical showcase — architecture, DB design, tech choices
- 🔲 Demo slide (screenshots + live demo plan)
- 🔲 Results & metrics
- 🔲 Lessons learned + closing/next steps

### 2c. Live presentation
- 🔲 Assign sections per team member (Kedia: architecture/ML/ingestion; David: DB/dashboard/QA).
- 🔲 Practice the demo end-to-end so it runs clean.
- 🔲 Prep answers to likely audience/tutor questions.

---

## 3. Technical Manual Review (MR) prep — must be ready to *explain*

The MR is an oral eval. Repo + app must be demo-ready and each of you should be able to explain:

- 🔲 **Live demo** — MVP runs without crashing (SITL/MAVLink ingestion → alerts → dashboard).
- 🔲 **Architecture** — how frontend (dashboard), backend (engine/listener), and DB fit together.
- 🔲 **Database** — schema, table relations, why you designed it that way (walk the DB diagram).
- 🔲 **Tech choices** — why Flask, why the ML approach, why MAVLink/UDP ingestion.
- 🔲 **Feature deep-dives** — geofencing logic, predictive alerts, post-flight report.
- 🔲 **Security concepts** — authentication, password hashing, RBAC (admin vs user), session handling.
- 🔲 **Testing** — what's covered, how you ran it, precision/recall validation.
- 🔲 **Collaboration** — Git workflow, branches, PR reviews, who did what.
- 🔲 **Git/GitHub best practices** — clean commit history, feature branches, meaningful messages.

---

## 4. Deliverable links checklist (fill these in before MR)

- 🔲 Source repository (GitHub URL)
- 🔲 Sprint planning doc
- 🔲 Sprint reviews
- 🔲 Retrospectives
- 🔲 Bug tracking (Issues/board)
- 🔲 Testing evidence & results
- 🔲 Production environment / deployment
- 🔲 Final report
- 🔲 Presentation slide deck

---

*Generated to close out Stages 4 & 5. Update the boxes as you go.*
