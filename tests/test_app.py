"""quicklink 自动化测试：登录、生成、跳转、停用、统计、搜索排序、删除、改密。"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
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


def test_docs_endpoints_disabled(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        r = client.get(path)
        assert r.status_code == 404
    # 健康检查与首页不受影响
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


