"""quicklink 自动化测试：登录、生成、跳转、停用、统计、搜索排序、删除、改密。"""

import hashlib
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# 用临时数据库，必须在 import app 之前设置
_TMP = tempfile.mkdtemp(prefix="quicklink-test-")
os.environ["QL_DB_PATH"] = str(Path(_TMP) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module  # noqa: E402


@pytest.fixture(scope="module")
def client():
    app_module.init_db()
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_wrong_password(client):
    r = client.post("/api/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_login_ok_must_change_flag(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True


def test_auth_required(client):
    r = client.get("/api/links")
    assert r.status_code == 401


def test_create_auto_code_and_redirect(client, auth):
    r = client.post("/api/links", json={"url": "https://example.com/some/long/path"}, headers=auth)
    assert r.status_code == 201
    code = r.json()["code"]
    assert len(code) == 6
    resp = client.get(f"/{code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/some/long/path"


def test_create_custom_code_and_conflict(client, auth):
    r = client.post(
        "/api/links",
        json={"url": "https://example.org/doc", "custom_code": "mydoc"},
        headers=auth,
    )
    assert r.status_code == 201
    assert r.json()["code"] == "mydoc"
    r2 = client.post(
        "/api/links",
        json={"url": "https://example.org/other", "custom_code": "mydoc"},
        headers=auth,
    )
    assert r2.status_code == 409


def test_custom_code_invalid_and_reserved(client, auth):
    r = client.post(
        "/api/links",
        json={"url": "https://example.org/x", "custom_code": "bad code!"},
        headers=auth,
    )
    assert r.status_code == 400
    r2 = client.post(
        "/api/links",
        json={"url": "https://example.org/x", "custom_code": "api"},
        headers=auth,
    )
    assert r2.status_code == 400


def test_create_invalid_url(client, auth):
    r = client.post("/api/links", json={"url": "not-a-url"}, headers=auth)
    assert r.status_code == 400
    r2 = client.post("/api/links", json={"url": "ftp://example.com/f"}, headers=auth)
    assert r2.status_code == 400


def test_redirect_missing_code(client):
    r = client.get("/zzzzzz", follow_redirects=False)
    assert r.status_code == 404


def test_disable_gone_and_reenable(client, auth):
    r = client.post(
        "/api/links",
        json={"url": "https://example.net/toggle", "custom_code": "toggle1"},
        headers=auth,
    )
    link_id = r.json()["id"]
    resp = client.get("/toggle1", follow_redirects=False)
    assert resp.status_code == 302
    r2 = client.patch(f"/api/links/{link_id}", json={"active": False}, headers=auth)
    assert r2.status_code == 200
    assert r2.json()["active"] is False
    resp2 = client.get("/toggle1", follow_redirects=False)
    assert resp2.status_code == 410
    # 停用期间的访问不计点击：总数应仍为 1
    stats = client.get(f"/api/links/{link_id}/clicks", headers=auth).json()
    assert stats["total_clicks"] == 1
    client.patch(f"/api/links/{link_id}", json={"active": True}, headers=auth)
    resp3 = client.get("/toggle1", follow_redirects=False)
    assert resp3.status_code == 302


def test_click_counting_and_records(client, auth):
    r = client.post(
        "/api/links",
        json={"url": "https://example.com/popular", "custom_code": "pop1"},
        headers=auth,
    )
    link_id = r.json()["id"]
    headers = {
        "Referer": "https://news.site/article",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    }
    for _ in range(3):
        resp = client.get("/pop1", follow_redirects=False, headers=headers)
        assert resp.status_code == 302
    stats = client.get(f"/api/links/{link_id}/clicks", headers=auth).json()
    assert stats["total_clicks"] == 3
    assert len(stats["recent"]) == 3
    assert stats["recent"][0]["referer"] == "https://news.site/article"
    assert stats["recent"][0]["ua_class"] == "移动端"


def test_search_and_sort_by_clicks(client, auth):
    client.post(
        "/api/links",
        json={"url": "https://alpha.example.com/page", "custom_code": "alpha1"},
        headers=auth,
    )
    client.post(
        "/api/links",
        json={"url": "https://beta.example.com/page", "custom_code": "beta1"},
        headers=auth,
    )
    for _ in range(2):
        client.get("/beta1", follow_redirects=False)
    r = client.get("/api/links", params={"q": "alpha"}, headers=auth)
    assert r.status_code == 200
    codes = [x["code"] for x in r.json()]
    assert codes == ["alpha1"]
    r2 = client.get("/api/links", params={"sort": "clicks"}, headers=auth)
    click_codes = [x["code"] for x in r2.json()]
    assert click_codes.index("beta1") < click_codes.index("alpha1")
    # 点击量最大的应是 pop1（3 次）
    assert r2.json()[0]["code"] == "pop1"


def test_delete_link(client, auth):
    r = client.post(
        "/api/links",
        json={"url": "https://example.com/temp", "custom_code": "temp1"},
        headers=auth,
    )
    link_id = r.json()["id"]
    rd = client.delete(f"/api/links/{link_id}", headers=auth)
    assert rd.status_code == 200
    resp = client.get("/temp1", follow_redirects=False)
    assert resp.status_code == 404
    r2 = client.get("/api/links", params={"q": "temp1"}, headers=auth)
    assert r2.json() == []


def test_patch_missing_link_404(client, auth):
    r = client.patch("/api/links/999999", json={"active": False}, headers=auth)
    assert r.status_code == 404


def test_change_password_flow(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    rc = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "newpass456"},
        headers=h,
    )
    assert rc.status_code == 200
    rold = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert rold.status_code == 401
    rnew = client.post("/api/login", json={"username": "admin", "password": "newpass456"})
    assert rnew.status_code == 200
    assert rnew.json()["must_change_password"] is False
    # 改回默认密码，避免影响其他用例（本用例放最后执行）
    token2 = rnew.json()["token"]
    client.post(
        "/api/change-password",
        json={"old_password": "newpass456", "new_password": "admin123"},
        headers={"Authorization": f"Bearer {token2}"},
    )


def test_change_password_revokes_other_sessions(client):
    ra = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    rb = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    ha = {"Authorization": f"Bearer {ra.json()['token']}"}
    hb = {"Authorization": f"Bearer {rb.json()['token']}"}
    rc = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "revoke123"},
        headers=ha,
    )
    assert rc.status_code == 200
    assert client.get("/api/me", headers=ha).status_code == 200  # 本次会话保留
    assert client.get("/api/me", headers=hb).status_code == 401  # 其他会话被吊销
    # 恢复默认密码
    client.post(
        "/api/change-password",
        json={"old_password": "revoke123", "new_password": "admin123"},
        headers=ha,
    )


def test_change_password_same_rejected(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    me_before = client.get("/api/me", headers=h).json()
    rc = client.post(
        "/api/change-password",
        json={"old_password": "admin123", "new_password": "admin123"},
        headers=h,
    )
    assert rc.status_code == 400
    # 什么都没发生：token 仍有效，改密标志原样
    me_after = client.get("/api/me", headers=h).json()
    assert me_after["must_change_password"] == me_before["must_change_password"]


def test_docs_endpoints_disabled(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        r = client.get(path)
        assert r.status_code == 404
    # 健康检查与首页不受影响
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_search_wildcard_escaped(client):
    # 前面的改密测试吊销过会话，这里自己重新登录，不依赖 module 级 fixture
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    # "%" 未转义时会匹配全部；转义后应只匹配字面含 % 的链接（这里没有）
    r2 = client.get("/api/links", params={"q": "%"}, headers=h)
    assert r2.status_code == 200
    assert r2.json() == []
    # "_" 未转义时会命中 pop1；转义后应只匹配字面含 pop_ 的链接（这里没有）
    r3 = client.get("/api/links", params={"q": "pop_"}, headers=h)
    assert r3.status_code == 200
    assert r3.json() == []


def _fresh_token(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_validate_url_rejects_control_chars_and_backslash(client):
    h = _fresh_token(client)
    r = client.post(
        "/api/links", json={"url": "http://example.com/\x01abc"}, headers=h
    )
    assert r.status_code == 400
    r2 = client.post(
        "/api/links", json={"url": "https://example.com/a\\b"}, headers=h
    )
    assert r2.status_code == 400
    # 正常网址不受影响
    r3 = client.post(
        "/api/links",
        json={"url": "https://example.com/ok-path?a=1&b=2", "custom_code": "clean1"},
        headers=h,
    )
    assert r3.status_code == 201


def test_sessions_store_token_hash(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    raw = r.json()["token"]
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    conn = sqlite3.connect(os.environ["QL_DB_PATH"])
    try:
        stored = conn.execute(
            "SELECT 1 FROM sessions WHERE token = ?", (expected,)
        ).fetchone()
        plaintext = conn.execute(
            "SELECT 1 FROM sessions WHERE token = ?", (raw,)
        ).fetchone()
    finally:
        conn.close()
    assert stored is not None
    assert plaintext is None


def test_code_case_insensitive_conflict(client):
    h = _fresh_token(client)
    r = client.post(
        "/api/links",
        json={"url": "https://example.com/case", "custom_code": "CaseMix1"},
        headers=h,
    )
    assert r.status_code == 201
    r2 = client.post(
        "/api/links",
        json={"url": "https://example.com/other", "custom_code": "casemix1"},
        headers=h,
    )
    assert r2.status_code == 409
    # 大小写不同写法跳转到同一条
    resp = client.get("/CASEMIX1", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/case"


def test_reserved_code_html_404(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    assert "这个短链不存在" in r.text


def test_security_headers(client):
    r = client.get("/")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Content-Security-Policy") == "frame-ancestors 'none'"


def test_insert_link_row_conflict_409(client):
    h = _fresh_token(client)
    r = client.post(
        "/api/links",
        json={"url": "https://example.com/race", "custom_code": "race1"},
        headers=h,
    )
    assert r.status_code == 201
    conn = app_module.get_db()
    try:
        user_id = conn.execute(
            "SELECT id FROM users WHERE username = 'admin'"
        ).fetchone()["id"]
        with pytest.raises(HTTPException) as exc:
            app_module._insert_link_row(
                conn, "race1", "https://example.com/other", user_id
            )
        assert exc.value.status_code == 409
    finally:
        conn.close()
