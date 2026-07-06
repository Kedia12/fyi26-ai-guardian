# Why the Login Screen Has No Sign Up Button

Good question — that's actually intentional, not an oversight. Here's the reasoning:

Our login screen and a typical consumer-style reference design are built for two different kinds of app. The consumer pattern (self-service Sign Up, "Remember me", public registration) is appropriate for apps where anyone can create their own account. Our dashboard is an internal ops tool: accounts carry real operational permissions (Admin can acknowledge/escalate/resolve safety alerts on live aircraft telemetry), and earlier in this project we specifically decided accounts should be admin-provisioned only via the "Manage Users" screen — not self-registered. That's why there's no Sign Up button: it's by design, not missing.

The tradeoff: adding a public Sign Up would mean anyone who can reach the login page could create their own account, which undermines the point of gating the dashboard behind login at all (you'd need extra guardrails like invite-only tokens, domain restrictions, or admin-approval-before-activation to make it safe). The recommendation is to keep it admin-provisioned as-is — it's simpler and matches how this kind of tool is normally run.

If self-service signup is ever needed for a specific reason, the right guardrails (invite-only tokens, domain restrictions, or admin-approval-before-activation) would need to be designed in alongside it.
