# Feature 5: Public Landing Page — Implementation To-Do List

## Context

AI Guardian currently has no public-facing page — visiting `/` while logged out
renders a bare `Login` form (`dashboard/ui/src/components/Login.tsx`) with no
explanation of what the product is or does. The product isn't public to market
yet, but may be soon, so we want a real landing page a first-time visitor can
land on: what AI Guardian is (About) and what it can do (Feature), with Sign In
tucked behind the nav rather than being the entire page.

Reference: a nav bar with logo left, center links, hamburger right, over a
full-bleed hero with a rotating background and bold headline overlay text.

## Design decisions

1. **New default view for logged-out visitors.** `App.tsx` currently does
   `if (!user) return <Login />;`. This becomes
   `if (!user) return <LandingPage />;`, and `LandingPage` is what renders
   `Login` (see #5).
2. **Nav layout**: logo left ("AI Guardian" + "FYI26" badge, matching the
   existing brand mark already used in `Login.tsx`/the dashboard header),
   "About" and "Feature" links centered, "Sign In" button + hamburger on the
   right. Hamburger only collapses About/Feature into a dropdown on narrow
   screens (same off-canvas pattern already used for the dashboard
   `Sidebar.tsx`) — it does **not** hide the Sign In button, per the earlier
   decision that hiding the only real CTA behind an extra tap adds friction
   with no benefit for this audience.
3. **About / Feature as tabs, not scroll-anchors.** Clicking "About" or
   "Feature" swaps the content region, reusing the same `activeView`-style
   state pattern already established in `App.tsx`/`Sidebar.tsx` for the
   dashboard — no new navigation paradigm introduced to the codebase.
4. **Hero background carousel**: no real photography exists in this repo, so
   the hero uses 3 auto-rotating full-bleed panels built from CSS
   gradients + a subtle grid/circuit-pattern overlay, in the existing
   `guardian-bg`/`guardian-accent` palette (`tailwind.config.js`) — visually
   on-brand with the rest of the app, no external assets. Panels crossfade
   every ~3s (`setInterval` + opacity transition, mirroring the interval
   pattern already used in `usePolling.ts`). Swapping in real photography
   later only means replacing the panel `background` values — the rotation
   mechanism doesn't change.
5. **Sign In stays the existing `Login` component**, unchanged. Clicking
   "Sign In" in the landing nav opens it inline (nav bar area collapses out,
   `Login`'s existing centered-card form takes over the page) — no separate
   login route/page, no changes to `Login.tsx`, `AuthContext.tsx`, or any
   backend auth code.
6. **Content is drawn from real app capabilities**, not placeholder marketing
   copy:
   - **About**: autonomous flight monitoring & anomaly detection for drone
     telemetry, combining rule-based checks with ML scoring (matches the
     tagline already in `Login.tsx`).
   - **Feature** grid, sourced from what's actually implemented:
     - Live telemetry dashboard (`TelemetryPanel.tsx`)
     - Rule-based alerts — packet loss, out-of-order/duplicate packets, IMU
       dropout/frozen IMU, low battery, GPS fix loss, GPS jump, geofence
       breach, GPS/IMU inconsistency (`guardian/rules.py`)
     - ML anomaly scoring via Isolation Forest (`guardian/predictor.py`)
     - Predictive/forecasting alerts (`PREDICTED_*` codes, `guardian/predictor.py`)
     - Live aircraft map with ADS-B Exchange overlay (`AircraftMap.tsx`)
     - AI-generated post-flight reports via Claude (`ReportPanel.tsx`,
       `guardian/report_generator.py`)
     - Role-based access control — admin/user (`dashboard/auth.py`)

## To-Do List

### 1. Hero background carousel
- [x] New `dashboard/ui/src/components/HeroCarousel.tsx` — 3 gradient/pattern
      panels, `setInterval`-driven crossfade every 3s, `prefers-reduced-motion`
      respected (freeze on first panel if set).

### 2. Landing nav
- [x] New `dashboard/ui/src/components/LandingNav.tsx` — logo, About/Feature
      tab buttons, Sign In button, hamburger (mobile-only, collapses
      About/Feature into a dropdown; reuse the transform/backdrop pattern from
      `Sidebar.tsx`).

### 3. About / Feature content
- [x] New `dashboard/ui/src/components/AboutSection.tsx` — what AI Guardian is.
- [x] New `dashboard/ui/src/components/FeatureSection.tsx` — feature grid
      (icons reused/adapted from `Sidebar.tsx`'s existing icon set where they
      overlap, e.g. activity/bell/map-pin/file).

### 4. Assemble the page
- [x] New `dashboard/ui/src/components/LandingPage.tsx` — composes
      `HeroCarousel` + `LandingNav` + active tab content (`about` | `feature`)
      + renders `Login` in place of the nav/hero when "Sign In" is clicked.

### 5. Wire into App
- [x] `App.tsx` — `if (!user) return <Login />;` → `if (!user) return <LandingPage />;`.
      No other changes to auth flow, `AuthContext.tsx`, or backend.

### 6. Responsive check
- [x] Verify at mobile (375px), tablet (768–1024px), and desktop widths —
      same Playwright-driven verification approach used for the dashboard
      sidebar (screenshot + `document.body.scrollWidth` vs `window.innerWidth`
      overflow check at each breakpoint).

### 7. Manual verification
- [x] Confirm logged-out `/` shows the landing page, not the bare login form.
- [x] Confirm About/Feature tab-switching works and only one is visible at a time.
- [x] Confirm hamburger collapses About/Feature on narrow screens without
      hiding Sign In.
- [x] Confirm clicking Sign In reveals the existing, unmodified `Login` form
      and that a successful login still lands on the dashboard as today.
- [x] Run `tsc --noEmit` and `npm run build`.

## Files to create
- `dashboard/ui/src/components/HeroCarousel.tsx`
- `dashboard/ui/src/components/LandingNav.tsx`
- `dashboard/ui/src/components/AboutSection.tsx`
- `dashboard/ui/src/components/FeatureSection.tsx`
- `dashboard/ui/src/components/LandingPage.tsx`

## Files to modify
- `dashboard/ui/src/App.tsx`
