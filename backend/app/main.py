"""API HTTP della console. Avvio: uvicorn app.main:app"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import insert, select

from .db import artifacts, engine, evidence_packs, gate_decisions, reviews, gateway_syncs, init_db, task_runs, utcnow
from .services import (active_config, active_llm_catalog, catalog, get_project, list_projects, queue_run, save_config,
                       save_llm_catalog, validate_llm_catalog_change)
from .settings import settings
from .validation import validate_bundle, validate_llm_catalog, validate_process_and_topology
from .views import gate_view, persona_detail, raci_view, stage_list


@asynccontextmanager
async def lifespan(_: FastAPI):
    cat = catalog()
    for name, b in cat.bundles.items():
        errs = validate_process_and_topology(b, cat.schemas)
        if errs:
            raise RuntimeError(f"Modelli {name} non validi: {errs[:5]}")
    errs = validate_llm_catalog(cat.llm_catalog, cat.schemas)
    if errs:
        raise RuntimeError(f"Catalogo LLM non valido: {errs[:5]}")
    await init_db()
    async with engine().connect() as conn:
        llm, _ = await active_llm_catalog(conn)
        errs = await validate_llm_catalog_change(conn, llm)
    if errs:
        log.warning("Catalogo LLM e configurazioni attive non coerenti, correggili da Configurazione: %s", errs[:5])
    yield


log = logging.getLogger("api")

app = FastAPI(title="Ananke API", version="0.1.0", lifespan=lifespan)


class RunRequest(BaseModel):
    slot: str
    taskId: str


class GateDecisionRequest(BaseModel):
    outcome: Literal["approved", "rejected"]
    personaId: str
    targetStage: str | None = None
    note: str | None = None


async def _project_or_404(conn, pid: str) -> dict[str, Any]:
    p = await get_project(conn, pid)
    if p is None:
        raise HTTPException(404, "Progetto inesistente")
    return p


def _iso(dt) -> str:
    """SQLite non conserva il fuso: i valori sono salvati in UTC."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def _project_out(p: dict[str, Any]) -> dict[str, Any]:
    b = catalog().bundle(p["methodology"])
    return {"id": p["id"], "name": p["name"], "client": p["client"], "methodology": p["methodology"],
            "methodologyLabel": "Waterfall" if p["methodology"] == "waterfall" else "Agile · Scrum",
            "currentStage": p["current_stage"], "currentStageName": b.stages[p["current_stage"]]["name"],
            "stageStartedAt": _iso(p["stage_started_at"]), "sprint": p["sprint"]}


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "llmMode": settings.llm_mode, "methodologies": list(catalog().bundles)}


@app.get("/api/projects")
async def projects_list() -> list[dict[str, Any]]:
    async with engine().connect() as conn:
        return [_project_out(p) for p in await list_projects(conn)]


@app.get("/api/projects/{pid}")
async def project_get(pid: str) -> dict[str, Any]:
    async with engine().connect() as conn:
        p = await _project_or_404(conn, pid)
        b = catalog().bundle(p["methodology"])
        config, _ = await active_config(conn, p["methodology"])
        return {**_project_out(p), "stages": stage_list(b, p), "gate": gate_view(b, config, p)}


@app.get("/api/projects/{pid}/stages/{sid}/raci")
async def project_raci(pid: str, sid: str) -> list[dict[str, Any]]:
    async with engine().connect() as conn:
        p = await _project_or_404(conn, pid)
        b = catalog().bundle(p["methodology"])
        if sid not in b.stages:
            raise HTTPException(404, "Stadio inesistente")
        config, _ = await active_config(conn, p["methodology"])
        return raci_view(b, config, sid)


@app.get("/api/projects/{pid}/stages/{sid}/work")
async def project_stage_work(pid: str, sid: str) -> dict[str, Any]:
    """Artefatti (tutte le versioni), revisioni e ultimo pacchetto di evidenze dello stadio."""
    async with engine().connect() as conn:
        p = await _project_or_404(conn, pid)
        b = catalog().bundle(p["methodology"])
        if sid not in b.stages:
            raise HTTPException(404, "Stadio inesistente")
        arts = (await conn.execute(select(artifacts).where(artifacts.c.project_id == pid, artifacts.c.stage == sid)
                                   .order_by(artifacts.c.artifact_type, artifacts.c.version.desc()))).mappings().all()
        ids = [a["id"] for a in arts]
        revs = (await conn.execute(select(reviews).where(reviews.c.artifact_id.in_(ids)).order_by(reviews.c.id.desc()))).mappings().all() if ids else []
        pack = (await conn.execute(select(evidence_packs).where(evidence_packs.c.project_id == pid, evidence_packs.c.stage == sid)
                                   .order_by(evidence_packs.c.id.desc()).limit(1))).mappings().first()
        return {
            "artifacts": [{"id": a["id"], "type": a["artifact_type"], "name": next((x["name"] for x in b.process["artifacts"] if x["id"] == a["artifact_type"]), a["artifact_type"]),
                           "version": a["version"], "slot": a["slot"], "content": a["content"], "createdAt": _iso(a["created_at"])} for a in arts],
            "reviews": [{"id": r["id"], "artifactId": r["artifact_id"], "artifactVersion": r["artifact_version"], "reviewer": r["reviewer_slot"],
                         "taskId": r["task_id"], "verdict": r["verdict"], "findings": r["findings"], "createdAt": _iso(r["created_at"])} for r in revs],
            "evidence": {"criteria": pack["criteria"], "createdAt": _iso(pack["created_at"])} if pack else None,
        }


@app.get("/api/projects/{pid}/personas/{persona_id}")
async def project_persona(pid: str, persona_id: str) -> dict[str, Any]:
    async with engine().connect() as conn:
        p = await _project_or_404(conn, pid)
        b = catalog().bundle(p["methodology"])
        config, _ = await active_config(conn, p["methodology"])
        if persona_id not in {x["id"] for x in config["personas"]}:
            raise HTTPException(404, "Persona inesistente")
        detail = persona_detail(b, config, p, persona_id)
        runs = (await conn.execute(select(task_runs).where(
            task_runs.c.project_id == pid, task_runs.c.persona_id == persona_id)
            .order_by(task_runs.c.id.desc()).limit(20))).mappings().all()
        detail["runs"] = [{"id": r["id"], "slot": r["slot"], "taskId": r["task_id"], "taskName": r["task_name"],
                           "trigger": r["trigger"], "status": r["status"], "output": r["output"],
                           "createdAt": _iso(r["created_at"])} for r in runs]
        return detail


@app.post("/api/projects/{pid}/runs", status_code=202)
async def project_run(pid: str, req: RunRequest) -> dict[str, Any]:
    async with engine().begin() as conn:
        p = await _project_or_404(conn, pid)
        try:
            run_id = await queue_run(conn, p, req.slot, req.taskId, "manual")
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    return {"id": run_id, "status": "queued",
            "message": f"In coda: il worker la esegue entro {settings.poll_seconds} secondi, fuori dalla pianificazione."}


@app.post("/api/projects/{pid}/gate-decisions", status_code=201)
async def project_gate_decision(pid: str, req: GateDecisionRequest) -> dict[str, Any]:
    async with engine().begin() as conn:
        p = await _project_or_404(conn, pid)
        b = catalog().bundle(p["methodology"])
        config, _ = await active_config(conn, p["methodology"])
        gate = gate_view(b, config, p)
        if gate is None:
            raise HTTPException(422, "La fase corrente non ha un gate")
        if req.personaId not in {a["id"] for a in gate["approvers"]}:
            raise HTTPException(403, "Questa persona non approva il gate della fase corrente")
        if req.targetStage and req.targetStage not in {t["id"] for t in gate["targets"]}:
            raise HTTPException(422, "Destinazione non ammessa dal processo")
        res = await conn.execute(insert(gate_decisions).values(
            project_id=pid, stage=p["current_stage"], outcome=req.outcome, target_stage=req.targetStage,
            persona_id=req.personaId, note=req.note, created_at=utcnow()))
    return {"id": res.inserted_primary_key[0],
            "message": "Decisione registrata: il Coordinatore la applica alla sua prossima esecuzione pianificata."}


@app.get("/api/methodologies")
async def methodologies() -> list[dict[str, Any]]:
    return [{"id": m, "processName": b.process["name"], "stages": len(b.stages), "slots": len(b.agents)}
            for m, b in catalog().bundles.items()]


@app.get("/api/methodologies/{m}/model")
async def methodology_model(m: str) -> dict[str, Any]:
    try:
        b = catalog().bundle(m)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"process": b.process, "topology": b.topology}


@app.get("/api/methodologies/{m}/config")
async def config_get(m: str) -> dict[str, Any]:
    if m not in catalog().bundles:
        raise HTTPException(404, "Metodologia sconosciuta")
    async with engine().connect() as conn:
        config, version = await active_config(conn, m)
    return {"version": version, "config": config}


@app.post("/api/methodologies/{m}/config/validate")
async def config_validate(m: str, config: dict[str, Any]) -> dict[str, Any]:
    if m not in catalog().bundles:
        raise HTTPException(404, "Metodologia sconosciuta")
    async with engine().connect() as conn:
        llm, _ = await active_llm_catalog(conn)
    errs = validate_bundle(catalog().bundle(m), config, catalog().schemas, llm)
    return {"valid": not errs, "errors": errs}


@app.put("/api/methodologies/{m}/config")
async def config_put(m: str, config: dict[str, Any]) -> dict[str, Any]:
    if m not in catalog().bundles:
        raise HTTPException(404, "Metodologia sconosciuta")
    async with engine().begin() as conn:
        llm, _ = await active_llm_catalog(conn)
        errs = validate_bundle(catalog().bundle(m), config, catalog().schemas, llm)
        if errs:
            raise HTTPException(422, {"errors": errs})
        version = await save_config(conn, m, config)
    return {"version": version, "message": "Configurazione salvata: il worker la applica al prossimo ricaricamento."}


@app.get("/api/llm/catalog")
async def llm_catalog_get() -> dict[str, Any]:
    async with engine().connect() as conn:
        llm, version = await active_llm_catalog(conn)
    return {"version": version, "catalog": llm}


@app.post("/api/llm/catalog/validate")
async def llm_catalog_validate(llm: dict[str, Any]) -> dict[str, Any]:
    async with engine().connect() as conn:
        errs = await validate_llm_catalog_change(conn, llm)
    return {"valid": not errs, "errors": errs}


@app.put("/api/llm/catalog")
async def llm_catalog_put(llm: dict[str, Any]) -> dict[str, Any]:
    async with engine().begin() as conn:
        errs = await validate_llm_catalog_change(conn, llm)
        if errs:
            raise HTTPException(422, {"errors": errs})
        version = await save_llm_catalog(conn, llm)
    return {"version": version,
            "message": f"Modelli salvati: il worker li applica al gateway entro {settings.reload_minutes} minuti."}


@app.get("/api/llm/gateway-status")
async def gateway_status() -> dict[str, Any]:
    async with engine().connect() as conn:
        _, version = await active_llm_catalog(conn)
        last = (await conn.execute(select(gateway_syncs).order_by(gateway_syncs.c.id.desc()).limit(1))).mappings().first()
    return {"llmMode": settings.llm_mode, "catalogVersion": version, "syncMinutes": settings.reload_minutes,
            "lastSync": None if last is None else {
                "status": last["status"], "detail": last["detail"], "catalogVersion": last["catalog_version"],
                "checkedAt": _iso(last["created_at"])}}
