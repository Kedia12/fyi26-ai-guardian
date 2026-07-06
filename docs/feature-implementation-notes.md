# Feature Implementation Notes

Historical implementation records for the dashboard-side features (all completed). Kept for reference on the design decisions and reasoning behind each feature.

- [Feature 4: Admin/User Login](#feature-4-adminuser-login)
- [Why the Login Screen Has No Sign-Up Button](#why-the-login-screen-has-no-sign-up-button)
- [Feature 5: Public Landing Page](#feature-5-public-landing-page)

---

## Feature 4: Admin/User Login

### Context

The dashboard (`dashboard/app.py`, `dashboard/routes.py`, `dashboard/ui/`) originally had **zero authentication** — every route including operator actions (confirm, acknowledge/escalate/resolve, AI report generation) was fully public, and `app.secret_key` was a hardcoded string. This feature added username/password login with two roles:

- **Admin** — full control: view everything, confirm/acknowledge/escalate/resolve alerts, generate AI reports, create new user accounts.
- **User** — view-only: sees the same telemetry/alerts/map/history, but action buttons are hidden and the underlying API endpoints reject non-admin requests server-side.

Approach: Flask's built-in signed-cookie session + `werkzeug.security` for password hashing (already available via the Flask dependency) — no new auth library, consistent with this repo's minimal-dependency style.

### Design decisions

1. **Bootstrap admin** — on first run, if the `Users` table is empty, auto-create an admin from `GUARDIAN_ADMIN_USERNAME`/`GUARDIAN_ADMIN_PASSWORD` env vars, or generate a random password (`secrets.token_urlsafe(12)`) and print it once to stdout. Solves the chicken-and-egg problem of an admin-only "create user" page with no existing admin.
2. **Session cookie** — browser-session-only (no extended `PERMANENT_SESSION_LIFETIME`).
3. **All dashboard routes require login** (not just the write/action ones) — the point of the feature is to gate the dashboard itself, not just mutations.
4. **Password policy** — minimal (non-empty, length >= 8). Not production-grade, acceptable for this project's stage.
5. **`disabled` column** included in schema for future use; no enable/disable endpoint yet — deferred.
6. **CSRF protection** — out of scope (same-origin app, no CSRF library added). Flagged as a known gap if this ever moves beyond prototype stage.

### Implementation checklist (completed)

**DB schema — `guardian/db.py`**
- [x] `Users` table in `_SCHEMA`: `id, username UNIQUE, password_hash, role, disabled, created_at`.
- [x] Methods following existing conventions: `insert_user`, `get_user_by_username`, `get_user_by_id`, `list_users` (excludes `password_hash`).

**Bootstrap & backend auth — `dashboard/auth.py`**
- [x] `_bootstrap_admin(db)` called from `create_app()` right after `GuardianDB` construction; idempotent on restart.
- [x] `login_required` and `role_required(*roles)` decorators (session-based, no new dependency).
- [x] `build_auth_blueprint(db)`: `POST /api/login`, `POST /api/logout`, `GET /api/me` (open), `POST /api/users`, `GET /api/users` (admin-only).

**Gate existing routes — `dashboard/routes.py`**
- [x] `@login_required` on all read routes (`/`, `/api/alerts`, `/api/telemetry`, `/api/aircraft-positions`, `/api/flight-trail`, `/api/geofence`, `/api/live-traffic`, `/api/alerts/<id>`).
- [x] `@role_required("admin")` on `/api/report`, `/api/alerts/<id>/confirm`, `/api/alerts/<id>/action`.

**Secret key — `dashboard/app.py`**
- [x] Replace hardcoded secret with `os.environ.get("GUARDIAN_SECRET_KEY", "guardian-dashboard-secret-dev-only")`, mirroring the existing `ANTHROPIC_API_KEY` convention.

**Frontend**
- [x] `User` interface in `dashboard/ui/src/types/index.ts`.
- [x] `dashboard/ui/src/context/AuthContext.tsx` — `AuthProvider` + `useAuth()`; `<App />` wrapped in `<AuthProvider>` in `main.tsx`.
- [x] `Login.tsx` (username + password, no role picker), `CreateUser.tsx` (admin-only).
- [x] `App.tsx` logged-out vs logged-in branch; `Header.tsx` user badge, logout, admin-only "Manage Users".
- [x] `ActiveAlerts.tsx` / `ReportPanel.tsx` accept `isAdmin` and **hide** action buttons for the User role.

**Testing**
- [x] Updated `tests/test_dashboard.py` fixtures to log in before hitting gated routes.
- [x] New `tests/test_auth.py`: login success/failure, `/api/me`, logout, 401 when logged out, 403 for User on admin routes, create-user incl. duplicate-username rejection.

**Manual verification**
- [x] Login gate blocks all views when logged out; Admin sees/uses all controls; User is read-only and admin-only API calls return 403; full `pytest` passes.

---

## Why the Login Screen Has No Sign-Up Button

That's intentional, not an oversight. The login screen and a typical consumer-style reference design are built for two different kinds of app. The consumer pattern (self-service Sign Up, "Remember me", public registration) suits apps where anyone can create their own account. This dashboard is an internal ops tool: accounts carry real operational permissions (Admin can acknowledge/escalate/resolve safety alerts on live aircraft telemetry), and we specifically decided accounts should be admin-provisioned only via the "Manage Users" screen — not self-registered. That's why there's no Sign Up button.

The tradeoff: a public Sign Up would let anyone who reaches the login page create their own account, which undermines the point of gating the dashboard behind login at all. Making that safe would require extra guardrails (invite-only tokens, domain restrictions, or admin-approval-before-activation). The recommendation is to keep it admin-provisioned as-is — simpler and matching how this kind of tool is normally run. If self-service signup is ever needed, those guardrails would need to be designed in alongside it.

---

## Feature 5: Public Landing Page

### Context

AI Guardian originally had no public-facing page — visiting `/` while logged out rendered a bare `Login` form with no explanation of the product. This feature added a real landing page a first-time visitor can land on: what AI Guardian is (About) and what it can do (Feature), with Sign In tucked behind the nav rather than being the entire page.

### Design decisions

1. **New default view for logged-out visitors.** `App.tsx` changes from `if (!user) return <Login />;` to `if (!user) return <LandingPage />;`, and `LandingPage` renders `Login` when Sign In is clicked.
2. **Nav layout**: logo left ("AI Guardian" + "FYI26" badge), "About"/"Feature" centered, "Sign In" + hamburger on the right. The hamburger only collapses About/Feature on narrow screens — it does **not** hide the Sign In CTA.
3. **About / Feature as tabs, not scroll-anchors** — reuses the `activeView`-style state pattern already in `App.tsx`/`Sidebar.tsx`.
4. **Hero background carousel**: 3 auto-rotating full-bleed panels built from CSS gradients + a subtle grid/circuit overlay in the existing palette (no external assets). Panels crossfade every ~3s. Swapping in real photography later only means replacing the panel `background` values.
5. **Sign In stays the existing `Login` component**, unchanged — no separate login route, no backend auth changes.
6. **Content drawn from real app capabilities**, not placeholder copy:
   - **About**: autonomous flight monitoring & anomaly detection for drone telemetry, combining rule-based checks with ML scoring.
   - **Feature grid**: live telemetry dashboard, rule-based alerts (packet loss, out-of-order/duplicate packets, IMU dropout/frozen IMU, low battery, GPS fix loss, GPS jump, geofence breach, GPS/IMU inconsistency), ML anomaly scoring via Isolation Forest, predictive/forecasting alerts, live aircraft map with ADS-B Exchange overlay, AI-generated post-flight reports via Claude, and role-based access control.

### Implementation checklist (completed)

- [x] `HeroCarousel.tsx` — 3 gradient/pattern panels, `setInterval` crossfade every 3s, `prefers-reduced-motion` respected.
- [x] `LandingNav.tsx` — logo, About/Feature tabs, Sign In, hamburger (mobile-only).
- [x] `AboutSection.tsx` and `FeatureSection.tsx` — content, icons adapted from the existing `Sidebar.tsx` icon set.
- [x] `LandingPage.tsx` — composes carousel + nav + active tab content, renders `Login` when Sign In is clicked.
- [x] `App.tsx` — logged-out route now returns `<LandingPage />`.
- [x] Responsive check at 375px / 768–1024px / desktop (screenshot + overflow check).
- [x] Manual verification: logged-out `/` shows landing page; tab switching works; hamburger keeps Sign In visible; Sign In reveals the unmodified `Login`; `tsc --noEmit` and `npm run build` pass.
