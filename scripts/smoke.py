"""Read-only smoke test. Pass the actual HTTPS Railway URL after deployment."""

import argparse, json, time
import httpx

p = argparse.ArgumentParser()
p.add_argument("url")
a = p.parse_args()
base = a.url.rstrip("/")
if not base.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
    p.error("Se requiere HTTPS o localhost de desarrollo")
results = []
with httpx.Client(base_url=base, timeout=15, follow_redirects=False) as c:
    for path, expected in [
        ("/healthz", 200),
        ("/readyz", 200),
        ("/api/suppliers", 200),
        ("/proveedores/S001", 200),
        ("/api/sources", 200),
        ("/.env", 404),
        ("/inputs/supplier_training.xlsx", 404),
    ]:
        start = time.monotonic()
        r = c.get(path)
        results.append(
            {
                "path": path,
                "http": r.status_code,
                "expected": expected,
                "seconds": round(time.monotonic() - start, 3),
            }
        )
    r = c.post("/api/sources/sync")
    results.append(
        {
            "path": "POST /api/sources/sync (sin sesión)",
            "http": r.status_code,
            "expected": 401,
        }
    )
print(json.dumps({"url": base, "results": results}, indent=2))
if any(r["http"] != r["expected"] for r in results):
    raise SystemExit(1)
