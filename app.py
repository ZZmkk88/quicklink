"""quicklink - 自托管短链接服务（单用户）。

后端：FastAPI + SQLite。功能：登录、生成短链（自动短码 / 自定义后缀）、
302 跳转、停用/删除、点击统计（时间 / 来源 / UA 大类）、搜索与排序。
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import string
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("QL_DB_PATH", str(BASE_DIR / "data" / "quicklink.db"))
TOKEN_TTL_SECONDS = 24 * 60 * 60
INITIAL_USERNAME = os.environ.get("QL_INITIAL_USERNAME", "admin")
INITIAL_PASSWORD = os.environ.get("QL_INITIAL_PASSWORD", "admin123")

CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
CUSTOM_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$")
RESERVED_CODES = {
    "api", "static", "health", "login", "logout", "docs", "redoc",
    "openapi.json", "favicon.ico",
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


def hash_token(token: str) -> str:
    """会话表只存 token 的 SHA-256。token 本身是 256 位随机值，校验时对请求值做同样哈希。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def init_db() -> None:
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
                clicked_at TEXT NOT NULL,
                referer TEXT NOT NULL DEFAULT '',
                ua_class TEXT NOT NULL DEFAULT '未知'
            );
            """
        )
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", (INITIAL_USERNAME,)
        ).fetchone()
        if row is None:
            salt = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, must_change_password)"
                " VALUES (?, ?, ?, 1)",
                (INITIAL_USERNAME, hash_password(INITIAL_PASSWORD, salt), salt),
            )
        conn.commit()
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="quicklink",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# ---------- 工具函数 ----------

def validate_url(url: str) -> str:
    url = (url or "").strip()
    # ASCII 控制字符（含 CR/LF/NUL）和反斜杠不进跳转目标，避免写进 Location
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in url) or "\\" in url:
        raise HTTPException(status_code=400, detail="网址含有非法字符")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="网址不合法，需要以 http:// 或 https:// 开头")
    return url


def validate_custom_code(code: str) -> str:
    code = (code or "").strip()
    if not CUSTOM_CODE_RE.match(code):
        raise HTTPException(
            status_code=400,
            detail="自定义后缀需为 2-32 位字母、数字、- 或 _，且以字母或数字开头",
        )
    if code.lower() in RESERVED_CODES:
        raise HTTPException(status_code=400, detail="这个后缀是系统保留字，换一个")
    return code


def generate_code(conn: sqlite3.Connection) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if code.lower() in RESERVED_CODES:
            continue
        exists = conn.execute(
            "SELECT 1 FROM links WHERE code = ? COLLATE NOCASE", (code,)
        ).fetchone()
        if exists is None:
            return code
    raise HTTPException(status_code=500, detail="短码生成失败，请重试")


def escape_like(s: str) -> str:
    r"""转义 LIKE 通配符：搜索词里的 %、_、\ 只按字面匹配。"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def classify_ua(ua: str) -> str:
    """把 User-Agent 粗分成几类，只存大类不存原文。"""
    if not ua:
        return "未知"
    low = ua.lower()
    if any(k in low for k in ("bot", "crawler", "spider", "curl", "wget", "python")):
        return "机器人/脚本"
    if any(k in low for k in ("mobile", "android", "iphone", "ipad")):
        return "移动端"
    if any(k in low for k in ("mozilla", "chrome", "safari", "firefox", "edge")):
        return "桌面浏览器"
    return "其他"


def current_user(request: Request) -> sqlite3.Row:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth[len("Bearer "):].strip()
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > ?",
            (hash_token(token), time.time()),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return row


def link_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "code": row["code"],
        "short_path": "/" + row["code"],
        "url": row["url"],
        "active": bool(row["active"]),
        "clicks": row["clicks"],
        "created_at": row["created_at"],
    }


# ---------- 请求体 ----------

class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class LinkIn(BaseModel):
    url: str
    custom_code: str | None = None


class LinkPatchIn(BaseModel):
    active: bool


# ---------- 账号接口 ----------

@app.post("/api/login")
def login(body: LoginIn):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (body.username.strip(),)
        ).fetchone()
        if user is None or user["password_hash"] != hash_password(body.password, user["salt"]):
            raise HTTPException(status_code=401, detail="用户名或密码不对")
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (hash_token(token), user["id"], time.time() + TOKEN_TTL_SECONDS),
        )
        conn.commit()
        return {
            "token": token,
            "username": user["username"],
            "must_change_password": bool(user["must_change_password"]),
        }
    finally:
        conn.close()


@app.post("/api/logout")
def logout(request: Request, user: sqlite3.Row = Depends(current_user)):
    token = request.headers.get("Authorization", "")[len("Bearer "):].strip()
    conn = get_db()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (hash_token(token),))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.post("/api/change-password")
def change_password(
    body: ChangePasswordIn,
    request: Request,
    user: sqlite3.Row = Depends(current_user),
):
    if hash_password(body.old_password, user["salt"]) != user["password_hash"]:
        raise HTTPException(status_code=400, detail="旧密码不对")
    if body.new_password == body.old_password:
        raise HTTPException(status_code=400, detail="新密码不能和旧密码相同")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    salt = secrets.token_hex(16)
    token = request.headers.get("Authorization", "")[len("Bearer "):].strip()
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0"
            " WHERE id = ?",
            (hash_password(body.new_password, salt), salt, user["id"]),
        )
        # 口令已更换：作废其他会话，只留本次请求使用的 token
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token != ?",
            (user["id"], hash_token(token)),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.get("/api/me")
def me(user: sqlite3.Row = Depends(current_user)):
    return {
        "username": user["username"],
        "must_change_password": bool(user["must_change_password"]),
    }


# ---------- 短链接口 ----------

@app.post("/api/links", status_code=201)
def create_link(body: LinkIn, user: sqlite3.Row = Depends(current_user)):
    url = validate_url(body.url)
    conn = get_db()
    try:
        if body.custom_code:
            code = validate_custom_code(body.custom_code)
            exists = conn.execute(
                "SELECT 1 FROM links WHERE code = ? COLLATE NOCASE", (code,)
            ).fetchone()
            if exists is not None:
                raise HTTPException(status_code=409, detail="这个后缀已被占用，换一个")
        else:
            code = generate_code(conn)
        link_id = _insert_link_row(conn, code, url, user["id"])
        conn.commit()
        row = conn.execute(
            "SELECT * FROM links WHERE id = ?", (link_id,)
        ).fetchone()
        return link_to_dict(row)
    finally:
        conn.close()


@app.get("/api/links")
def list_links(
    q: str = "",
    sort: str = "recent",
    user: sqlite3.Row = Depends(current_user),
):
    if sort not in ("recent", "clicks"):
        raise HTTPException(status_code=400, detail="sort 只能是 recent 或 clicks")
    order = "id DESC" if sort == "recent" else "clicks DESC, id DESC"
    conn = get_db()
    try:
        if q:
            like = f"%{escape_like(q)}%"
            rows = conn.execute(
                f"SELECT * FROM links WHERE user_id = ? AND (url LIKE ? ESCAPE '\\'"
                f" OR code LIKE ? ESCAPE '\\')"
                f" ORDER BY {order}",
                (user["id"], like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM links WHERE user_id = ? ORDER BY {order}",
                (user["id"],),
            ).fetchall()
        return [link_to_dict(r) for r in rows]
    finally:
        conn.close()


def _load_link(conn: sqlite3.Connection, user_id: int, link_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM links WHERE id = ? AND user_id = ?", (link_id, user_id)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="短链不存在")
    return row


def _insert_link_row(conn: sqlite3.Connection, code: str, url: str, user_id: int) -> int:
    """插入短链行。并发竞态下短码撞车（唯一约束）时返回 409 而不是 500。"""
    try:
        cur = conn.execute(
            "INSERT INTO links (code, url, created_at, user_id) VALUES (?, ?, ?, ?)",
            (code, url, utcnow_iso(), user_id),
        )
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="这个后缀刚刚被别人占用了，换一个")


@app.patch("/api/links/{link_id}")
def patch_link(link_id: int, body: LinkPatchIn, user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        _load_link(conn, user["id"], link_id)
        conn.execute(
            "UPDATE links SET active = ? WHERE id = ?", (1 if body.active else 0, link_id)
        )
        conn.commit()
        return link_to_dict(_load_link(conn, user["id"], link_id))
    finally:
        conn.close()


@app.delete("/api/links/{link_id}")
def delete_link(link_id: int, user: sqlite3.Row = Depends(current_user)):
    conn = get_db()
    try:
        _load_link(conn, user["id"], link_id)
        conn.execute("DELETE FROM clicks WHERE link_id = ?", (link_id,))
        conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.get("/api/links/{link_id}/clicks")
def list_clicks(link_id: int, limit: int = 20, user: sqlite3.Row = Depends(current_user)):
    limit = max(1, min(limit, 100))
    conn = get_db()
    try:
        link = _load_link(conn, user["id"], link_id)
        rows = conn.execute(
            "SELECT * FROM clicks WHERE link_id = ? ORDER BY id DESC LIMIT ?",
            (link_id, limit),
        ).fetchall()
        return {
            "code": link["code"],
            "total_clicks": link["clicks"],
            "recent": [
                {
                    "clicked_at": r["clicked_at"],
                    "referer": r["referer"],
                    "ua_class": r["ua_class"],
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


# ---------- 页面与跳转 ----------

@app.get("/health")
def health():
    try:
        conn = get_db()
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    except Exception:
        return JSONResponse(
            {"status": "error", "app": "quicklink"}, status_code=503
        )
    return {"status": "ok", "app": "quicklink"}


STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{code}")
def redirect_code(code: str, request: Request):
    if code.lower() in RESERVED_CODES:
        return HTMLResponse(
            "<h1>404</h1><p>这个短链不存在。</p>", status_code=404
        )
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM links WHERE code = ? COLLATE NOCASE", (code,)
        ).fetchone()
        if row is None:
            return HTMLResponse(
                "<h1>404</h1><p>这个短链不存在。</p>", status_code=404
            )
        if not row["active"]:
            return HTMLResponse(
                "<h1>410</h1><p>这个短链已被停用。</p>", status_code=410
            )
        conn.execute(
            "INSERT INTO clicks (link_id, clicked_at, referer, ua_class)"
            " VALUES (?, ?, ?, ?)",
            (
                row["id"],
                utcnow_iso(),
                request.headers.get("referer", ""),
                classify_ua(request.headers.get("user-agent", "")),
            ),
        )
        conn.execute(
            "UPDATE links SET clicks = clicks + 1 WHERE id = ?", (row["id"],)
        )
        conn.commit()
        return RedirectResponse(url=row["url"], status_code=302)
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("QL_PORT", "8000")))
