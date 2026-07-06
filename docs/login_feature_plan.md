# Feature 4: Admin/User Login — Implementation To-Do List

## Context

The dashboard (`dashboard/app.py`, `dashboard/routes.py`, `dashboard/ui/`) currently has **zero authentication** — every route including operator actions (confirm, acknowledge/escalate/resolve, AI report generation) is fully public, and `app.secret_key` is a hardcoded string. This plan adds username/password login with two roles:

- **Admin** — full control: view everything, confirm/acknowledge/escalate/resolve alerts, generate AI reports, create new user accounts.
- **User** — view-only: sees the same telemetry/alerts/map/history, but action buttons are hidden and the underlying API endpoints reject non-admin requests server-side.

Approach: Flask's built-in signed-cookie session + `werkzeug.security` for password hashing (already available via the Flask dependency) — no new auth library, consistent with this repo's minimal-dependency style.

## Design decisions

1. **Bootstrap admin** — on first run, if the `Users` table is empty, auto-create an admin from `GUARDIAN_ADMIN_USERNAME`/`GUARDIAN_ADMIN_PASSWORD` env vars, or generate a random password (`secrets.token_urlsafe(12)`) and print it once to stdout. Solves the chicken-and-egg problem of an admin-only "create user" page with no existing admin.
2. **Session cookie** — browser-session-only (no extended `PERMANENT_SESSION_LIFETIME`) for now.
3. **All dashboard routes require login** (not just the write/action ones) — the point of this feature is to gate the dashboard itself, not just mutations.
4. **Password policy** — minimal (non-empty, length >= 8). Not a production-grade policy, acceptable for this project's stage.
5. **`disabled` column** included in schema for future use, but no enable/disable endpoint yet — deferred.
6. **CSRF protection** — out of scope for now (same-origin app, no CSRF library added). Flagged as a known gap if this ever moves beyond prototype stage.

## To-Do List

### 1. DB schema — `guardian/db.py`
- [x] Add `Users` table to `_SCHEMA`: `id, username UNIQUE, password_hash, role, disabled, created_at`.
- [x] Add methods following existing conventions (parameterized SQL, `commit()` after writes, `dict(row)` reads): `insert_user`, `get_user_by_username`, `get_user_by_id`, `list_users` (must exclude `password_hash` from its projection).

### 2. Bootstrap first admin
- [x] New `dashboard/auth.py`: `_bootstrap_admin(db)` — called from `create_app()` right after `GuardianDB` construction. If `Users` table is empty, create the admin from env vars or a random password printed once. Idempotent on every restart.

### 3. Backend auth routes/decorators — `dashboard/auth.py`
- [x] `login_required` and `role_required(*roles)` decorators (session-based, no new dependency).
- [x] `build_auth_blueprint(db)` with:
  - `POST /api/login` (open)
  - `POST /api/logout` (open)
  - `GET /api/me` (open — returns 401 if not logged in)
  - `POST /api/users` (admin-only — create user)
  - `GET /api/users` (admin-only — list users)

### 4. Gate existing routes — `dashboard/routes.py`
- [x] `@login_required` on all read routes (`/`, `/api/alerts`, `/api/telemetry`, `/api/aircraft-positions`, `/api/flight-trail`, `/api/geofence`, `/api/live-traffic`, `/api/alerts/<id>`).
- [x] `@role_required("admin")` on `/api/report`, `/api/alerts/<id>/confirm`, `/api/alerts/<id>/action`.

### 5. Secret key — `dashboard/app.py`
- [x] Line 19: replace hardcoded `"guardian-dashboard-secret"` with `os.environ.get("GUARDIAN_SECRET_KEY", "guardian-dashboard-secret-dev-only")`, mirroring the existing `ANTHROPIC_API_KEY` env-var convention. No signature change to `create_app()`.

### 6. Frontend types & auth context
- [x] Add `User` interface to `dashboard/ui/src/types/index.ts` (snake_case fields, matching existing convention).
- [x] New `dashboard/ui/src/context/AuthContext.tsx` — first Context in this codebase — `AuthProvider` + `useAuth()` hook (login/logout/current user/loading state).
- [x] Wrap `<App />` with `<AuthProvider>` in `main.tsx`.

### 7. Frontend components
- [x] New `Login.tsx` — username + password only (no role picker; role is server-assigned).
- [x] New `CreateUser.tsx` — admin-only, calls `POST /api/users`.
- [x] `App.tsx` — branch logged-out (show only `Login`) vs. logged-in (dashboard); add a simple view-toggle state for a "Manage Users" screen (no router dependency needed for one extra screen).
- [x] `Header.tsx` — add logged-in user badge, logout button, and (admin-only) "Manage Users" button.
- [x] `ActiveAlerts.tsx` and `ReportPanel.tsx` — accept an `isAdmin` prop and **hide** (not just disable) action buttons for the User role.

### 8. Testing
- [x] Update `tests/test_dashboard.py` fixtures to log in before hitting now-gated routes (existing tests will break once routes require auth — fix in the same change).
- [x] New `tests/test_auth.py`: login success/failure, `/api/me`, logout, 401 when logged out, 403 for User role on admin-only routes, create-user flow incl. duplicate-username rejection. Use `monkeypatch.setenv` for deterministic bootstrap admin credentials in tests.

### 9. Manual end-to-end verification
- [x] Run Flask + Vite dev servers.
- [x] Confirm login gate blocks all dashboard views when logged out.
- [x] Log in as Admin — confirm all controls visible and functional (confirm/ack/escalate/resolve/report/create user).
- [x] Create a User-role account via the Admin UI, log in as that user — confirm read-only view (no action buttons) and that direct API calls to admin-only endpoints return 403.
- [x] Run full `pytest` suite.

## Files to create
- `dashboard/auth.py`
- `dashboard/ui/src/context/AuthContext.tsx`
- `dashboard/ui/src/components/Login.tsx`
- `dashboard/ui/src/components/CreateUser.tsx`
- `tests/test_auth.py`

## Files to modify
- `guardian/db.py`
- `dashboard/app.py`
- `dashboard/routes.py`
- `dashboard/ui/src/types/index.ts`
- `dashboard/ui/src/main.tsx`
- `dashboard/ui/src/App.tsx`
- `dashboard/ui/src/components/Header.tsx`
- `dashboard/ui/src/components/ActiveAlerts.tsx`
- `dashboard/ui/src/components/ReportPanel.tsx`
- `tests/test_dashboard.py`
