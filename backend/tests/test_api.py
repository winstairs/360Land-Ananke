import copy
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app.db import engine, init_db, projects, utcnow
from app.main import app
from app.services import catalog, execute_queued, run_scheduled

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client():
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_and_projects(client):
    r = await client.get("/api/health")
    assert r.json()["status"] == "ok"
    r = await client.get("/api/projects")
    ids = {p["id"] for p in r.json()}
    assert {"p1", "p2", "p3"} <= ids


async def test_raci_and_manual_run(client):
    r = await client.get("/api/projects/p1")
    body = r.json()
    assert body["currentStage"] == "requirements"
    assert body["gate"]["approvers"]

    raci = (await client.get("/api/projects/p1/stages/requirements/raci")).json()
    r_names = {p["name"] for p in raci[0]["people"]}
    assert {"Elio", "Nora"} <= r_names

    elio = (await client.get("/api/projects/p1/personas/elio")).json()
    task = elio["slots"][0]["tasks"][0]
    r = await client.post("/api/projects/p1/runs", json={"slot": elio["slots"][0]["slot"], "taskId": task["id"]})
    assert r.status_code == 202
    assert await execute_queued() >= 1
    elio = (await client.get("/api/projects/p1/personas/elio")).json()
    assert elio["runs"][0]["status"] == "done"
    assert "[simulazione]" in elio["runs"][0]["output"]


async def test_human_tasks_cannot_be_queued(client):
    r = await client.post("/api/projects/p1/runs", json={"slot": "nope", "taskId": "x"})
    assert r.status_code == 422


async def test_gate_decision_is_applied_by_coordinator_cron(client):
    gate = (await client.get("/api/projects/p1")).json()["gate"]
    approver = gate["approvers"][0]["id"]
    r = await client.post("/api/projects/p1/gate-decisions", json={"outcome": "approved", "personaId": approver})
    assert r.status_code == 201
    r = await client.post("/api/projects/p1/gate-decisions", json={"outcome": "approved", "personaId": "elio"})
    assert r.status_code == 403
    msg = await run_scheduled("p1", "pm-lead-agent", "read-gate-decisions")
    assert "Gate approvato" in msg
    assert (await client.get("/api/projects/p1")).json()["currentStage"] == "design"


async def test_scrum_timebox_closes_sprint(client):
    async with engine().begin() as conn:
        await conn.execute(update(projects).where(projects.c.id == "p2").values(
            current_stage="sprint", stage_started_at=utcnow() - timedelta(days=15)))
    msg = await run_scheduled("p2", "agile-lead-agent", "timebox")
    assert "scaduto" in msg
    async with engine().connect() as conn:
        stage = (await conn.execute(select(projects.c.current_stage).where(projects.c.id == "p2"))).scalar_one()
    assert stage == "sprint-review"


async def test_config_put_validates(client):
    cfg = copy.deepcopy(catalog().bundle("scrum").default_config)
    for r in cfg["roleAssignments"]:
        if r["role"] == "product-owner":
            r["mode"] = "agent"
    r = await client.put("/api/methodologies/scrum/config", json=cfg)
    assert r.status_code == 422
    cfg = copy.deepcopy(catalog().bundle("scrum").default_config)
    cfg["slotAssignments"][0]["taskOverrides"] = {"read-decisions": {"cron": "*/15 8-19 * * 1-5"}}
    r = await client.put("/api/methodologies/scrum/config", json=cfg)
    assert r.status_code == 200 and r.json()["version"] >= 1
    got = (await client.get("/api/methodologies/scrum/config")).json()
    assert got["version"] == r.json()["version"]


async def test_llm_catalog_roundtrip_and_shared_validation(client):
    got = (await client.get("/api/llm/catalog")).json()
    llm = got["catalog"]
    assert any(p["id"] == "anthropic" for p in llm["providers"])

    # Disattivare il provider usato dai preset rompe le configurazioni di entrambe le metodologie
    broken = copy.deepcopy(llm)
    next(p for p in broken["providers"] if p["id"] == "anthropic")["enabled"] = False
    r = await client.put("/api/llm/catalog", json=broken)
    assert r.status_code == 422
    errs = r.json()["detail"]["errors"]
    assert any(e.startswith("waterfall:") for e in errs) and any(e.startswith("scrum:") for e in errs)

    ok = copy.deepcopy(llm)
    next(p for p in ok["providers"] if p["id"] == "openai")["enabled"] = True
    r = await client.put("/api/llm/catalog", json=ok)
    assert r.status_code == 200 and r.json()["version"] >= 1
    assert (await client.get("/api/llm/catalog")).json()["version"] == r.json()["version"]


async def test_gateway_status(client):
    body = (await client.get("/api/llm/gateway-status")).json()
    assert body["llmMode"] == "mock"
    assert "catalogVersion" in body
