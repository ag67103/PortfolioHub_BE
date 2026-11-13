import uuid

import pytest


def register(client, username, password="password123", **extra):
    r = client.post("/auth/register", json={"username": username, "email": f"{username}@example.com",
                                            "password": password, "first_name": username.title(), **extra})
    return r


def login(client, username, password="password123"):
    r = client.post("/auth/token", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def alice(client):
    r = register(client, "alice")
    assert r.status_code == 200, r.text
    return {"id": r.json()["id"], "headers": login(client, "alice")}


@pytest.fixture(scope="module")
def bob(client):
    r = register(client, "bob")
    assert r.status_code == 200, r.text
    return {"id": r.json()["id"], "headers": login(client, "bob")}


# ---------- auth ----------

def test_root(client):
    assert client.get("/").json() == {"message": "Hello World"}


def test_register_shape_and_duplicates(client, alice):
    r = register(client, "alice")
    assert r.status_code == 400 and "already" in r.json()["detail"].lower()
    r = client.post("/auth/register", json={"username": "other", "email": "alice@example.com", "password": "password123"})
    assert r.status_code == 400
    r = register(client, "shortpw", password="short")
    assert r.status_code == 422


def test_register_response_has_no_password(client):
    r = register(client, "carol")
    body = r.json()
    assert "hashed_password" not in body and "password" not in body
    assert body["role"] == "viewer" and body["is_active"] == "active"
    uuid.UUID(body["id"])


def test_login_variants(client, alice):
    assert client.post("/auth/token", data={"username": "alice@example.com", "password": "password123"}).status_code == 200
    assert client.post("/auth/token", data={"username": "alice", "password": "wrong"}).status_code == 401
    assert client.post("/auth/token", data={"username": "nobody", "password": "x"}).status_code == 401


def test_me_refresh_logout(client):
    register(client, "dave")
    h = login(client, "dave")
    me = client.get("/auth/me", headers=h).json()
    assert me["username"] == "dave"

    new = client.post("/auth/refresh", headers=h)
    assert new.status_code == 200
    # old token is revoked, new one works
    assert client.get("/auth/me", headers=h).status_code == 401
    h2 = {"Authorization": f"Bearer {new.json()['access_token']}"}
    assert client.get("/auth/me", headers=h2).status_code == 200

    assert client.post("/auth/logout", headers=h2).json() == {"message": "Successfully logged out"}
    assert client.get("/auth/me", headers=h2).status_code == 401


def test_requires_auth(client):
    assert client.get("/auth/me").status_code == 401
    assert client.post("/projects", json={}).status_code == 401


def test_admin_endpoints_forbidden_for_viewer(client, alice):
    assert client.get("/auth/token-stats", headers=alice["headers"]).status_code == 403


def test_admin_endpoints_for_admin(client):
    import asyncio
    from sqlalchemy import update
    from app.db.database import engine
    from app.models.user import User
    from app.enums.user import UserRole

    register(client, "root")

    async def promote():
        async with engine.begin() as conn:
            await conn.execute(update(User).where(User.username == "root").values(role=UserRole.admin))

    client.portal.call(promote)
    h = login(client, "root")
    stats = client.get("/auth/token-stats", headers=h)
    assert stats.status_code == 200 and stats.json()["total_tokens"] >= 1
    assert client.post("/auth/cleanup-tokens", headers=h).status_code == 200


# ---------- portfolio items ----------

PROJECT = {"title": "P1", "description": "d", "technologies": ["py", "react"], "start_date": "2024-01-01",
           "live_url": "https://x.dev"}


def test_project_crud_and_ownership(client, alice, bob):
    r = client.post("/projects", json=PROJECT, headers=alice["headers"])
    assert r.status_code == 200, r.text
    p = r.json()
    assert "_id" in p and "id" not in p            # frontend expects `_id`
    assert p["user_id"] == alice["id"] and p["technologies"] == ["py", "react"]

    # public listing by user
    listed = client.get(f"/projects/user/{alice['id']}").json()
    assert [x["_id"] for x in listed] == [p["_id"]]

    # not owner -> 403, unknown -> 404, bad uuid -> 422
    assert client.put(f"/projects/{p['_id']}", json={"title": "x"}, headers=bob["headers"]).status_code == 403
    assert client.delete(f"/projects/{p['_id']}", headers=bob["headers"]).status_code == 403
    assert client.put(f"/projects/{uuid.uuid4()}", json={"title": "x"}, headers=alice["headers"]).status_code == 404
    assert client.put("/projects/not-a-uuid", json={"title": "x"}, headers=alice["headers"]).status_code == 422

    # partial update only touches given fields
    u = client.put(f"/projects/{p['_id']}", json={"title": "P1b"}, headers=alice["headers"]).json()
    assert u["title"] == "P1b" and u["description"] == "d" and u["updated_at"] >= p["updated_at"]

    assert client.delete(f"/projects/{p['_id']}", headers=alice["headers"]).json() == {"message": "Project deleted successfully"}
    assert client.get(f"/projects/user/{alice['id']}").json() == []


def test_projects_sorted_newest_first(client, alice):
    for title, start, end in [("old", "2020-01-01", "2020-06-01"), ("new", "2024-01-01", None), ("mid", "2022-01-01", "2022-12-01")]:
        body = {**PROJECT, "title": title, "start_date": start, **({"end_date": end} if end else {})}
        assert client.post("/projects", json=body, headers=alice["headers"]).status_code == 200
    titles = [p["title"] for p in client.get(f"/projects/user/{alice['id']}").json()]
    assert titles == ["new", "mid", "old"]


def test_project_url_validation(client, alice):
    r = client.post("/projects", json={**PROJECT, "live_url": "ftp://bad"}, headers=alice["headers"])
    assert r.status_code == 422


def test_skills(client, alice, bob):
    s = client.post("/skills", json={"name": "Python", "category": "lang", "proficiency": 90}, headers=alice["headers"])
    assert s.status_code == 200 and "_id" in s.json()
    dup = client.post("/skills", json={"name": "Python", "category": "lang", "proficiency": 50}, headers=alice["headers"])
    assert dup.status_code == 400
    # another user can have the same skill name
    assert client.post("/skills", json={"name": "Python", "category": "lang", "proficiency": 50}, headers=bob["headers"]).status_code == 200
    assert client.post("/skills", json={"name": "X", "category": "c", "proficiency": 101}, headers=alice["headers"]).status_code == 422
    sid = s.json()["_id"]
    assert client.put(f"/skills/{sid}", json={"proficiency": 95}, headers=alice["headers"]).json()["proficiency"] == 95
    assert client.delete(f"/skills/{sid}", headers=bob["headers"]).status_code == 403
    assert client.delete(f"/skills/{sid}", headers=alice["headers"]).status_code == 200


def test_experience(client, alice):
    body = {"title": "Dev", "company": "ACME", "description": "d", "technologies": ["go"], "start_date": "2022-01-01"}
    e = client.post("/experiences", json=body, headers=alice["headers"]).json()
    assert e["company"] == "ACME" and e["end_date"] is None
    assert client.put(f"/experiences/{e['_id']}", json={"end_date": "2023-01-01"}, headers=alice["headers"]).json()["end_date"] == "2023-01-01"
    assert len(client.get(f"/experiences/user/{alice['id']}").json()) == 1
    assert client.delete(f"/experiences/{e['_id']}", headers=alice["headers"]).status_code == 200


def test_education(client, alice, bob):
    body = {"institution": "MIT", "degree": "BSc", "start_date": "2016-01-01"}
    e = client.post("/educations", json=body, headers=alice["headers"]).json()
    assert "_id" in e
    mine = client.get("/educations", headers=alice["headers"]).json()
    assert [x["_id"] for x in mine] == [e["_id"]]
    assert client.get("/educations", headers=bob["headers"]).json() == []
    assert len(client.get(f"/educations/user/{alice['id']}").json()) == 1
    assert client.put(f"/educations/{e['_id']}", json={"degree": "MSc"}, headers=alice["headers"]).json()["degree"] == "MSc"
    assert client.delete(f"/educations/{e['_id']}", headers=bob["headers"]).status_code == 403
    assert client.delete(f"/educations/{e['_id']}", headers=alice["headers"]).status_code == 200


def test_certifications_and_awards(client, alice):
    c = client.post("/certifications", json={"name": "AWS", "issuer": "Amazon", "issue_date": "2023-05-01",
                                             "description": "d", "credential_url": "https://a.b"}, headers=alice["headers"])
    assert c.status_code == 200 and c.json()["credential_id"] is None
    assert client.get(f"/certifications/user/{alice['id']}").json()[0]["_id"] == c.json()["_id"]
    assert client.delete(f"/certifications/{c.json()['_id']}", headers=alice["headers"]).status_code == 200

    a = client.post("/awards", json={"name": "Best", "issuer": "Org", "issue_date": "2023-05-01",
                                     "description": "d", "category": "x"}, headers=alice["headers"])
    assert a.status_code == 200
    assert client.put(f"/awards/{a.json()['_id']}", json={"name": "Best2"}, headers=alice["headers"]).json()["name"] == "Best2"
    assert client.delete(f"/awards/{a.json()['_id']}", headers=alice["headers"]).status_code == 200


# ---------- portfolio / user ----------

def test_portfolio(client, alice):
    r = client.put("/portfolio/", json={"portfolio_title": "Hi", "portfolio_education": ["a", "b"],
                                         "github_url": "https://github.com/a"}, headers=alice["headers"])
    assert r.status_code == 200
    got = client.get("/portfolio/", headers=alice["headers"]).json()
    assert got["portfolio_title"] == "Hi" and got["portfolio_education"] == ["a", "b"]
    pub = client.get(f"/portfolio/user/{alice['id']}").json()
    assert pub["github_url"] == "https://github.com/a" and pub["portfolio_awards"] == []
    assert client.put("/portfolio/", json={"github_url": "nope"}, headers=alice["headers"]).status_code == 422
    assert client.get(f"/portfolio/user/{uuid.uuid4()}").status_code == 404


def test_user_and_visitor_count(client, alice):
    u = client.get(f"/user/{alice['id']}").json()
    assert u["id"] == alice["id"] and "hashed_password" not in u
    r = client.post(f"/user/{alice['id']}/increment-visitor")
    assert r.json() == {"visitor_count": 1}
    assert client.post(f"/user/{alice['id']}/increment-visitor").status_code == 429  # rate limited
    assert client.post(f"/user/{uuid.uuid4()}/increment-visitor").status_code == 404
    assert client.get(f"/user/{uuid.uuid4()}").status_code == 404


# ---------- messages ----------

def test_messages_flow(client, alice, bob):
    # alice -> bob (authenticated), with a websocket open for bob
    token = bob["headers"]["Authorization"].split()[1]
    with client.websocket_connect(f"/ws/messages?token={token}") as ws:
        r = client.post("/message/send", json={"messageContent": "hi bob", "messageSubject": "Hello",
                                               "recipientEmail": "bob@example.com"}, headers=alice["headers"])
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        evt = ws.receive_json()
        assert evt["event"] == "message:new"
        assert evt["payload"]["id"] == mid and evt["payload"]["messageContent"] == "hi bob"

    assert client.post("/message/send", json={"messageContent": "x", "recipientEmail": "alice@example.com"},
                       headers=alice["headers"]).status_code == 400            # to self
    assert client.post("/message/send", json={"messageContent": "x", "recipientEmail": "ghost@example.com"},
                       headers=alice["headers"]).status_code == 404

    # bob replies -> same conversation
    client.post("/message/send", json={"messageContent": "hi alice", "recipientEmail": "alice@example.com"}, headers=bob["headers"])
    msgs = client.get("/message", headers=bob["headers"]).json()
    assert len(msgs) == 2 and msgs[0]["messageContent"] == "hi bob"             # oldest first
    assert msgs[0]["conversationId"] == msgs[1]["conversationId"]
    conv = msgs[0]["conversationId"]
    assert msgs[1]["isRead"] is True                                            # own sent message counts as read
    assert msgs[0]["isRead"] is False

    assert client.get("/message/count", headers=bob["headers"]).json() == {"read": 1, "unread": 1, "total": 2}

    # mark read (only recipient's messages are updated)
    assert client.put("/message/read", json={"messageIds": [mid]}, headers=alice["headers"]).status_code == 200
    assert client.get("/message/count", headers=bob["headers"]).json()["unread"] == 1  # alice isn't the recipient of `mid`
    assert client.put("/message/read", json={"messageIds": [mid]}, headers=bob["headers"]).status_code == 200
    assert client.get("/message/count", headers=bob["headers"]).json() == {"read": 2, "unread": 0, "total": 2}

    # delete: single message, then whole conversation
    assert client.delete(f"/message/{mid}", headers=bob["headers"]).status_code == 200
    assert client.delete(f"/message/{mid}", headers=bob["headers"]).status_code == 400   # already deleted for bob
    assert len(client.get("/message", headers=bob["headers"]).json()) == 1
    assert len(client.get("/message", headers=alice["headers"]).json()) == 2             # still visible to alice
    r = client.delete(f"/message/conversation/{conv}", headers=alice["headers"])
    assert r.status_code == 200 and r.json()["deleted_count"] == 2
    assert client.get("/message", headers=alice["headers"]).json() == []
    again = client.delete(f"/message/conversation/{conv}", headers=alice["headers"])
    assert again.status_code == 200 and again.json()["deleted_count"] == 0       # nothing left to delete for alice
    assert client.delete(f"/message/conversation/{uuid.uuid4()}", headers=alice["headers"]).status_code == 404


def test_unauthenticated_message_and_conversation_reuse(client, alice):
    body = {"senderName": "Visitor", "senderEmail": "v@example.com", "messageContent": "hello", "recipientUserId": alice["id"]}
    a = client.post("/message/send/unauthenticated", json=body)
    b = client.post("/message/send/unauthenticated", json={**body, "messageContent": "again"})
    assert a.status_code == b.status_code == 200
    msgs = client.get("/message", headers=alice["headers"]).json()
    assert len(msgs) == 2 and msgs[0]["conversationId"] == msgs[1]["conversationId"]
    assert msgs[0]["senderUserId"] is None and msgs[0]["isRead"] is False
    assert client.post("/message/send/unauthenticated", json={**body, "recipientUserId": str(uuid.uuid4())}).status_code == 404


def test_websocket_rejects_bad_token(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/messages?token=garbage"):
            pass


# ---------- resume ----------

def test_resume_unknown_user(client):
    assert client.get(f"/resume/latex?user_id={uuid.uuid4()}").status_code == 404


def test_resume_pdf(client, alice):
    client.post("/experiences", json={"title": "Dev & Ops", "company": "ACME <Inc>", "description": "Did 100% of $things\nSecond line",
                                      "technologies": ["go"], "start_date": "2022-01-01"}, headers=alice["headers"])
    client.post("/skills", json={"name": "Rust", "category": "Languages", "proficiency": 80}, headers=alice["headers"])
    r = client.get(f"/resume/latex?user_id={alice['id']}")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and "Resume.pdf" in r.headers["content-disposition"]
