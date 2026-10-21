"""真实流程自测：真起一个 uvicorn 服务进程，走完整流程并逐项打勾。

运行：python tests/live_selftest.py
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent.parent
PORT = 8931
ROOT = f"http://127.0.0.1:{PORT}"

checks = []


def check(name: str, ok: bool, extra: str = ""):
    checks.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {extra}")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="quicklink-live-")
    env = dict(os.environ)
    env["QL_DB_PATH"] = str(Path(tmp) / "live.db")
    env["QL_PORT"] = str(PORT)
    # 云端 shell 可能有代理变量，自测客户端不读环境代理，避免被干扰
    python = sys.executable
    proc = subprocess.Popen(
        [python, str(BASE / "app.py")],
        cwd=str(BASE),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        client = httpx.Client(base_url=ROOT, trust_env=False, timeout=10)
        up = False
        for _ in range(50):
            try:
                if client.get("/health").status_code == 200:
                    up = True
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        check("服务启动 /health", up)
        if not up:
            return 1

        r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
        check("登录成功", r.status_code == 200)
        h = {"Authorization": f"Bearer {r.json()['token']}"}

        r = client.post(
            "/api/links",
            json={"url": "https://example.com/landing", "custom_code": "selftest"},
            headers=h,
        )
        check("生成自定义短链", r.status_code == 201, f"code={r.json().get('code')}")
        link_id = r.json()["id"]

        r = client.get("/selftest", follow_redirects=False)
        check(
            "跳转 302 到原网址",
            r.status_code == 302
            and r.headers.get("location") == "https://example.com/landing",
        )
        client.get("/selftest", follow_redirects=False)

        r = client.get(f"/api/links/{link_id}/clicks", headers=h)
        check("点击统计为 2", r.status_code == 200 and r.json()["total_clicks"] == 2)

        r = client.patch(f"/api/links/{link_id}", json={"active": False}, headers=h)
        check("停用短链", r.status_code == 200 and r.json()["active"] is False)
        r = client.get("/selftest", follow_redirects=False)
        check("停用后跳转返回 410", r.status_code == 410)

        r = client.get("/notexist", follow_redirects=False)
        check("不存在短码返回 404", r.status_code == 404)

        print(f"\n共 {len(checks)} 项，通过 {sum(checks)} 项")
        return 0 if all(checks) else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
