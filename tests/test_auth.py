import json

from conftest import TEST_ADMIN_USER, TEST_ADMIN_PASS


# ── login / logout ───────────────────────────────────────────────────────────

def test_login_success_returns_user(anon_client):
    response = anon_client.post(
        "/api/login", json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["username"] == TEST_ADMIN_USER
    assert data["role"] == "admin"


def test_login_wrong_password_returns_401(anon_client):
    response = anon_client.post(
        "/api/login", json={"username": TEST_ADMIN_USER, "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_unknown_user_returns_401(anon_client):
    response = anon_client.post(
        "/api/login", json={"username": "nobody", "password": "whatever"}
    )
    assert response.status_code == 401


def test_me_without_login_returns_401(anon_client):
    response = anon_client.get("/api/me")
    assert response.status_code == 401


def test_me_after_login_returns_user(client):
    response = client.get("/api/me")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["username"] == TEST_ADMIN_USER


def test_logout_clears_session(client):
    assert client.get("/api/me").status_code == 200
    response = client.post("/api/logout")
    assert response.status_code == 200
    assert client.get("/api/me").status_code == 401


# ── unauthenticated access to protected routes ───────────────────────────────

def test_anon_cannot_read_alerts(anon_client):
    assert anon_client.get("/api/alerts").status_code == 401


def test_anon_cannot_confirm_alert(anon_client):
    response = anon_client.post("/api/alerts/1/confirm")
    assert response.status_code == 401


# ── admin-only user management ───────────────────────────────────────────────

def test_admin_can_create_user(client):
    response = client.post(
        "/api/users",
        json={"username": "viewer1", "password": "viewerpass1", "role": "user"},
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["username"] == "viewer1"
    assert data["role"] == "user"


def test_create_user_duplicate_username_returns_409(client):
    client.post(
        "/api/users",
        json={"username": "dupe", "password": "duppassword", "role": "user"},
    )
    response = client.post(
        "/api/users",
        json={"username": "dupe", "password": "anotherpass", "role": "user"},
    )
    assert response.status_code == 409


def test_create_user_short_password_returns_400(client):
    response = client.post(
        "/api/users",
        json={"username": "shortpw", "password": "short", "role": "user"},
    )
    assert response.status_code == 400


def test_create_user_invalid_role_returns_400(client):
    response = client.post(
        "/api/users",
        json={"username": "badrole", "password": "goodpassword", "role": "superuser"},
    )
    assert response.status_code == 400


def test_list_users_excludes_password_hash(client):
    response = client.get("/api/users")
    assert response.status_code == 200
    users = json.loads(response.data)
    assert len(users) >= 1
    for u in users:
        assert "password_hash" not in u


# ── role-gating for the "user" (view-only) role ──────────────────────────────

def test_user_role_cannot_create_users(client):
    client.post(
        "/api/users",
        json={"username": "viewer2", "password": "viewerpass2", "role": "user"},
    )
    client.post("/api/logout")
    client.post(
        "/api/login", json={"username": "viewer2", "password": "viewerpass2"}
    )
    response = client.post(
        "/api/users",
        json={"username": "viewer3", "password": "viewerpass3", "role": "user"},
    )
    assert response.status_code == 403


def test_user_role_cannot_confirm_alerts(client):
    alerts = json.loads(client.get("/api/alerts").data)
    alert_id = alerts[0]["id"]

    client.post(
        "/api/users",
        json={"username": "viewer4", "password": "viewerpass4", "role": "user"},
    )
    client.post("/api/logout")
    client.post(
        "/api/login", json={"username": "viewer4", "password": "viewerpass4"}
    )
    response = client.post(f"/api/alerts/{alert_id}/confirm")
    assert response.status_code == 403


# ── self-service password change ─────────────────────────────────────────────

def test_change_password_success(client):
    response = client.post(
        "/api/me/password",
        json={"current_password": TEST_ADMIN_PASS, "new_password": "newpassword1"},
    )
    assert response.status_code == 200

    client.post("/api/logout")
    relogin_old = client.post(
        "/api/login", json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS}
    )
    assert relogin_old.status_code == 401

    relogin_new = client.post(
        "/api/login", json={"username": TEST_ADMIN_USER, "password": "newpassword1"}
    )
    assert relogin_new.status_code == 200


def test_change_password_records_timestamp_for_admin_visibility(client):
    users_before = json.loads(client.get("/api/users").data)
    admin_before = next(u for u in users_before if u["username"] == TEST_ADMIN_USER)
    assert admin_before["password_changed_at"] is None

    client.post(
        "/api/me/password",
        json={"current_password": TEST_ADMIN_PASS, "new_password": "newpassword1"},
    )

    users_after = json.loads(client.get("/api/users").data)
    admin_after = next(u for u in users_after if u["username"] == TEST_ADMIN_USER)
    assert admin_after["password_changed_at"] is not None


def test_change_password_wrong_current_returns_401(client):
    response = client.post(
        "/api/me/password",
        json={"current_password": "wrongpassword", "new_password": "newpassword1"},
    )
    assert response.status_code == 401


def test_change_password_short_new_returns_400(client):
    response = client.post(
        "/api/me/password",
        json={"current_password": TEST_ADMIN_PASS, "new_password": "short"},
    )
    assert response.status_code == 400


def test_change_password_requires_login(anon_client):
    response = anon_client.post(
        "/api/me/password",
        json={"current_password": "whatever", "new_password": "newpassword1"},
    )
    assert response.status_code == 401


# ── disable / delete users ────────────────────────────────────────────────────

def test_admin_can_disable_user(client):
    client.post(
        "/api/users",
        json={"username": "todisable1", "password": "disablepass1", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "todisable1")

    response = client.post(f"/api/users/{target['id']}/disabled", json={"disabled": True})
    assert response.status_code == 200
    assert json.loads(response.data)["disabled"] is True

    login = client.post(
        "/api/login", json={"username": "todisable1", "password": "disablepass1"}
    )
    assert login.status_code == 403


def test_admin_can_reenable_user(client):
    client.post(
        "/api/users",
        json={"username": "toreenable1", "password": "reenablepass1", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "toreenable1")

    client.post(f"/api/users/{target['id']}/disabled", json={"disabled": True})
    response = client.post(f"/api/users/{target['id']}/disabled", json={"disabled": False})
    assert response.status_code == 200
    assert json.loads(response.data)["disabled"] is False


def test_admin_cannot_disable_self(client):
    me = json.loads(client.get("/api/me").data)
    response = client.post(f"/api/users/{me['id']}/disabled", json={"disabled": True})
    assert response.status_code == 400


def test_admin_cannot_disable_last_admin(client):
    me = json.loads(client.get("/api/me").data)
    client.post(
        "/api/users",
        json={"username": "otherviewer1", "password": "otherviewerpass1", "role": "user"},
    )
    client.post("/api/logout")
    client.post("/api/login", json={"username": TEST_ADMIN_USER, "password": TEST_ADMIN_PASS})

    users = json.loads(client.get("/api/users").data)
    admins = [u for u in users if u["role"] == "admin"]
    assert len(admins) == 1

    response = client.post(f"/api/users/{me['id']}/disabled", json={"disabled": True})
    assert response.status_code == 400


def test_admin_can_delete_user(client):
    client.post(
        "/api/users",
        json={"username": "todelete1", "password": "deletepass1", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "todelete1")

    response = client.delete(f"/api/users/{target['id']}")
    assert response.status_code == 200

    users_after = json.loads(client.get("/api/users").data)
    assert all(u["id"] != target["id"] for u in users_after)


def test_admin_cannot_delete_self(client):
    me = json.loads(client.get("/api/me").data)
    response = client.delete(f"/api/users/{me['id']}")
    assert response.status_code == 400


def test_disable_unknown_user_returns_404(client):
    response = client.post("/api/users/999999/disabled", json={"disabled": True})
    assert response.status_code == 404


def test_delete_unknown_user_returns_404(client):
    response = client.delete("/api/users/999999")
    assert response.status_code == 404


def test_user_role_cannot_disable_users(client):
    client.post(
        "/api/users",
        json={"username": "viewer6", "password": "viewerpass6", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "viewer6")

    client.post("/api/logout")
    client.post("/api/login", json={"username": "viewer6", "password": "viewerpass6"})
    response = client.post(f"/api/users/{target['id']}/disabled", json={"disabled": True})
    assert response.status_code == 403


# ── admin modify (username / email / role / password reset) ────────────────

def test_admin_can_modify_user_profile(client):
    client.post(
        "/api/users",
        json={"username": "tomodify1", "password": "modifypass1", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "tomodify1")

    response = client.patch(
        f"/api/users/{target['id']}",
        json={"username": "modified1", "email": "modified1@example.com", "role": "admin"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["username"] == "modified1"
    assert data["email"] == "modified1@example.com"
    assert data["role"] == "admin"


def test_modify_user_invalid_email_returns_400(client):
    client.post(
        "/api/users",
        json={"username": "tomodify2", "password": "modifypass2", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "tomodify2")

    response = client.patch(f"/api/users/{target['id']}", json={"email": "not-an-email"})
    assert response.status_code == 400


def test_modify_user_duplicate_username_returns_409(client):
    client.post(
        "/api/users",
        json={"username": "tomodify3", "password": "modifypass3", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "tomodify3")

    response = client.patch(f"/api/users/{target['id']}", json={"username": TEST_ADMIN_USER})
    assert response.status_code == 409


def test_admin_cannot_demote_last_admin(client):
    me = json.loads(client.get("/api/me").data)
    response = client.patch(f"/api/users/{me['id']}", json={"role": "user"})
    assert response.status_code == 400


def test_admin_can_reset_user_password(client):
    client.post(
        "/api/users",
        json={"username": "resetme1", "password": "originalpass1", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "resetme1")

    response = client.post(
        f"/api/users/{target['id']}/password", json={"new_password": "brandnewpass1"}
    )
    assert response.status_code == 200

    client.post("/api/logout")
    login_new = client.post(
        "/api/login", json={"username": "resetme1", "password": "brandnewpass1"}
    )
    assert login_new.status_code == 200


def test_admin_reset_password_short_returns_400(client):
    client.post(
        "/api/users",
        json={"username": "resetme2", "password": "originalpass2", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "resetme2")

    response = client.post(f"/api/users/{target['id']}/password", json={"new_password": "short"})
    assert response.status_code == 400


def test_user_role_cannot_modify_users(client):
    client.post(
        "/api/users",
        json={"username": "viewer7", "password": "viewerpass7", "role": "user"},
    )
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "viewer7")

    client.post("/api/logout")
    client.post("/api/login", json={"username": "viewer7", "password": "viewerpass7"})
    response = client.patch(f"/api/users/{target['id']}", json={"role": "admin"})
    assert response.status_code == 403


def test_modify_unknown_user_returns_404(client):
    response = client.patch("/api/users/999999", json={"username": "ghost"})
    assert response.status_code == 404


def test_create_user_with_email(client):
    response = client.post(
        "/api/users",
        json={
            "username": "hasemail1",
            "password": "hasemailpass1",
            "role": "user",
            "email": "hasemail1@example.com",
        },
    )
    assert response.status_code == 201
    users = json.loads(client.get("/api/users").data)
    target = next(u for u in users if u["username"] == "hasemail1")
    assert target["email"] == "hasemail1@example.com"


def test_user_role_can_still_read_alerts(client):
    client.post(
        "/api/users",
        json={"username": "viewer5", "password": "viewerpass5", "role": "user"},
    )
    client.post("/api/logout")
    client.post(
        "/api/login", json={"username": "viewer5", "password": "viewerpass5"}
    )
    response = client.get("/api/alerts")
    assert response.status_code == 200
