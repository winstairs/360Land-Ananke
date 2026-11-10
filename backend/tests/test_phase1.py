"""Fase 1: artefatti versionati, revisione prima del gate, pacchetto di evidenze (modalità mock)."""
import httpx
import pytest
from sqlalchemy import update

from app.db import engine, init_db, projects, utcnow
from app.main import app
from app.services import run_scheduled

pytestmark = pytest.mark.anyio

PID, STAGE = "p1", "requirements"


@pytest.fixture
async def client():
    await init_db()
    async with engine().begin() as conn:  # altri test spostano p1 di stadio: si riparte dai requisiti
        await conn.execute(update(projects).where(projects.c.id == PID).values(current_stage=STAGE, stage_started_at=utcnow()))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _work(client):
    return (await client.get(f"/api/projects/{PID}/stages/{STAGE}/work")).json()


async def test_artifacts_reviews_and_evidence_pack(client):
    before = await _work(client)
    n_srs = len([a for a in before["artifacts"] if a["type"] == "srs"])

    # Il writer produce la SRS: ogni esecuzione crea una nuova versione
    await run_scheduled(PID, "requirements-writer-agent", "srs-update")
    await run_scheduled(PID, "requirements-writer-agent", "srs-update")
    work = await _work(client)
    srs = [a for a in work["artifacts"] if a["type"] == "srs"]
    assert [a["version"] for a in srs][:2] == [n_srs + 2, n_srs + 1]

    # Il validatore riceve la SRS in ingresso e registra una revisione sulla versione più recente
    await run_scheduled(PID, "requirements-validator-agent", "validity")
    work = await _work(client)
    rev = work["reviews"][0]
    assert rev["artifactId"] == srs[0]["id"] and rev["artifactVersion"] == srs[0]["version"]
    assert rev["verdict"] == "approved" and "Artefatti ricevuti" in rev["findings"]

    # Il gatekeeper produce un pacchetto con un'entry per ogni criterio del gate
    await run_scheduled(PID, "gatekeeper-agent", "evidence-pack")
    work = await _work(client)
    gate = (await client.get(f"/api/projects/{PID}")).json()["gate"]
    criteria = work["evidence"]["criteria"]
    assert [c["criterion"] for c in criteria] == gate["criteria"]
    assert {c["status"] for c in criteria} <= {"met", "unmet", "unknown"}
    # La piattaforma non attesta l'approvazione del cliente: resta a una persona
    assert next(c for c in criteria if "approvat" in c["criterion"].lower())["status"] == "unknown"
    assert any(c["status"] == "met" for c in criteria)


async def test_gate_evidence_without_review_is_unmet(client):
    await run_scheduled(PID, "requirements-writer-agent", "srs-update")  # nuova versione non ancora revisionata
    await run_scheduled(PID, "gatekeeper-agent", "evidence-pack")
    criteria = (await _work(client))["evidence"]["criteria"]
    assert not any(c["status"] == "met" for c in criteria)
