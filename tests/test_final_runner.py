"""The final runner is exercised only against a labeled synthetic HTTP transport."""

import hashlib
from io import BytesIO
import json
import runpy
import sys
from pathlib import Path
import httpx
from openpyxl import Workbook
from app import settings as configuration


def test_final_runner_orders_validation_before_test_and_liveday(
    monkeypatch, tmp_path, capsys
):
    (tmp_path / "reports").mkdir()
    (tmp_path / "evidence").mkdir()
    (tmp_path / "inputs").mkdir()
    phases = [
        ("validation", "News_Validation", 10),
        ("test", "News_Test", 20),
        ("liveday", "News_Feed", 14),
    ]
    originals = {}
    files = []
    for split, sheet, count in phases:
        w = Workbook()
        w.active.title = sheet
        w.active.append(["News_ID", "Headline", "Summary", "Source", "Published_Date"])
        ids = [f"MOCK-{split}-{i:02}" for i in range(count)]
        originals[split] = ids
        for nid in ids:
            w.active.append(
                [nid, "MOCK IDENTIFICADO", "Synthetic input", "MOCK", "2026-10-17"]
            )
        path = tmp_path / "inputs" / f"supplier_{split}.xlsx"
        w.save(path)
        files.append(
            {
                "path": str(path.relative_to(tmp_path)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    (tmp_path / "evidence/input_manifest.json").write_text(json.dumps({"files": files}))
    (tmp_path / "reports/prompt-freeze.json").write_text(
        json.dumps(
            {
                "files": {},
                "question_version": "1.0.0",
                "policy_version": "1.0.0",
                "model": "jev-1.13.0",
            }
        )
    )
    monkeypatch.setattr(configuration, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["final_rehearsal", "--start"])
    analyzed = set()
    events = []

    def transport(request):
        path = request.url.path
        events.append((request.method, path))
        if path == "/api/config":
            return httpx.Response(
                200,
                json={
                    "model": "jev-1.13.0",
                    "policy_version": "1.0.0",
                    "question_version": "1.0.0",
                    "rss_paid_analysis": False,
                },
            )
        if path == "/api/worker":
            return httpx.Response(200, json={"online": True})
        if path == "/api/suppliers":
            return httpx.Response(
                200, json={"items": [{"supplier_id": f"S{i:03}"} for i in range(1, 41)]}
            )
        if path == "/api/session":
            return httpx.Response(200, json={"csrf": "MOCK"})
        if path == "/healthz":
            return httpx.Response(200, json={"revision": "MOCK-SCRIPT-TEST"})
        if path == "/api/admin/budgets":
            return httpx.Response(
                200,
                json={
                    "budgets": [
                        {
                            "id": "demo-final-200-20261017",
                            "request_limit": 200,
                            "requests_used": sum(len(originals[s]) for s in analyzed),
                            "remaining_requests": 200
                            - sum(len(originals[s]) for s in analyzed),
                        }
                    ]
                },
            )
        if path == "/api/imports":
            split = next(
                s
                for s, _, _ in phases
                if f"supplier_{s}.xlsx".encode() in request.content
            )
            return httpx.Response(200, json={"batch_id": split})
        if path == "/api/batches":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": s,
                        "done": n if s in analyzed else 0,
                        "errors": 0,
                        "started_at": "2026-10-17T00:00:00Z" if s in analyzed else None,
                    }
                    for s, _, n in phases
                ],
            )
        if path.startswith("/api/batches/"):
            split = path.split("/")[3]
            if path.endswith("/analyze"):
                analyzed.add(split)
                return httpx.Response(202, json={"job_ids": ["MOCK"]})
            if path.endswith("/execution"):
                return httpx.Response(
                    200,
                    json={
                        "calls": [
                            {
                                "news_id": nid,
                                "model": "jev-1.13.0",
                                "stage": "a",
                                "attempt": 1,
                                "http_status": 200,
                                "usage": {"input_tokens": 1, "output_tokens": 1},
                            }
                            for nid in originals[split]
                        ]
                    },
                )
            if path.endswith("/export.xlsx"):
                w = Workbook()
                headers = ["News_ID", "Is_Risk", "Urgent", "Affected_Supplier_IDs"]
                if split == "test":
                    headers += ["Headline", "Summary", "Source", "Published_Date"]
                w.active.append(headers)
                for nid in originals[split]:
                    w.active.append(
                        [nid, "N", "N", ""]
                        + (
                            ["MOCK", "MOCK", "MOCK", "2026-10-17"]
                            if split == "test"
                            else []
                        )
                    )
                content = BytesIO()
                w.save(content)
                return httpx.Response(200, content=content.getvalue())
        if path == "/api/evaluations/validation":
            return httpx.Response(200, json={"n": 10, "mock": True})
        raise AssertionError("Ruta inesperada en transporte sintético")

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *a, **kw: original_client(
            *a, **kw, transport=httpx.MockTransport(transport)
        ),
    )
    runpy.run_module("scripts.final_rehearsal", run_name="__main__")
    r = json.loads((tmp_path / "reports/private/final-rehearsal.json").read_text())
    assert all(p["completed"] for p in r["phases"].values())
    assert r["phases"]["liveday"]["export_checks"]["rows"] == 14
    assert r["budget_after"]["requests_used"] == 44
    assert (
        events.index(("POST", "/api/evaluations/validation"))
        < events.index(("POST", "/api/batches/test/analyze"))
        < events.index(("POST", "/api/batches/liveday/analyze"))
    )
    assert r["phases"]["validation"]["metrics"]["mock"] is True
