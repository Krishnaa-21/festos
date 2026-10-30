import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

foo_path = backend_dir / "app" / "api" / "v1" / "foo.py"

try:
    with open(foo_path, "w", encoding="utf-8") as f:
        f.write('from fastapi import APIRouter\nrouter = APIRouter()\n@router.get("/test")\ndef test_foo(): return {"foo": "bar"}\n')

    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    res = client.get("/api/v1/foo/test")
    assert res.status_code == 200
    assert res.json() == {"foo": "bar"}
    print("Zero-edit router auto-mount verified: GET /api/v1/foo/test returned 200 OK")
finally:
    if os.path.exists(foo_path):
        os.remove(foo_path)
