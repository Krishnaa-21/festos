"""Export OpenAPI schema from FastAPI app."""
import json
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def export():
    from app.main import app
    openapi_schema = app.openapi()
    
    out_path = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"
    if len(sys.argv) > 2 and sys.argv[1] == "--output":
        out_path = Path(sys.argv[2])
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"OpenAPI schema successfully written to {out_path}")

if __name__ == "__main__":
    export()
