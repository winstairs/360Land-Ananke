"""Logica condivisa tra API e worker: configurazione attiva, coda dei compiti, transizioni di stato."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from .agents.runner import run_task
from .catalog import Bundle, Catalog
from .db import config_versions, engine, gate_decisions, llm_catalog_versions, projects, task_runs, utcnow
from .scheduling import effective_tasks, parse_duration, stage_is_active
from .settings import settings
from .validation import validate_bundle, validate_llm_catalog


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    return Catalog.load(settings.models_dir)


# Schema 1.1 -> 1.2: i provider passano al catalogo LLM di piattaforma; i preset puntano ai provider del catalogo
_MODEL_RENAMES_1_2 = {
    "vllm-local/oss-generalist": "ollama-local/oss-generalist", "vllm-local/oss-coder": "ollama-local/oss-coder",
    "ollama-edge/oss-light": "ollama-local/oss-light", "ollama-edge/oss-coder-small": "ollama-local/oss-coder-small",
}


def upgrade_config(content: dict[str, Any]) -> dict[str, Any]:
    """Porta allo schema corrente una configurazione salvata con una versione precedente."""
    if "llmProviders" not in content:
        return content
    out = {k: v for k, v in content.items() if k != "llmProviders"}
    out["agentPresets"] = [dict(p) for p in content.get("agentPresets", [])]
    for p in out["agentPresets"]:
        for k in ("model", "fallbackModel"):
            if p.get(k) in _MODEL_RENAMES_1_2:
                p[k] = _MODEL_RENAMES_1_2[p[k]]
        if str(p.get("fallbackModel", "")).startswith("open-cloud/"):
            del p["fallbackModel"]  # provider disattivato nel catalogo di default
        if str(p.get("model", "")).startswith("anthropic/") and str(p.get("fallbackModel", "")).startswith("ollama-local/"):
            del p["fallbackModel"]  # stessa famiglia dei revisori open: violerebbe la revisione cross-family
    return out


async def active_config(conn: AsyncConnection, methodology: str) -> tuple[dict[str, Any], int]:
    """Ultima versione salvata in database, altrimenti la configurazione di default (versione 0)."""
    row = (await conn.execute(
        select(config_versions).where(config_versions.c.methodology == methodology)
        .order_by(config_versions.c.id.desc()).limit(1))).mappings().first()
    if row:
        return upgrade_config(row["content"]), row["id"]
    return catalog().bundle(methodology).default_config, 0


async def save_config(conn: AsyncConnection, methodology: str, content: dict[str, Any]) -> int:
    res = await conn.execute(insert(config_versions).values(methodology=methodology, content=content, created_at=utcnow()))
    return res.inserted_primary_key[0]


async def active_llm_catalog(conn: AsyncConnection) -> tuple[dict[str, Any], int]:
    """Catalogo LLM di piattaforma: ultima versione salvata, altrimenti il file del repository (versione 0)."""
    row = (await conn.execute(
        select(llm_catalog_versions).order_by(llm_catalog_versions.c.id.desc()).limit(1))).mappings().first()
    if row:
        return row["content"], row["id"]
    return catalog().llm_catalog, 0


async def save_llm_catalog(conn: AsyncConnection, content: dict[str, Any]) -> int:
    res = await conn.execute(insert(llm_catalog_versions).values(content=content, created_at=utcnow()))
    return res.inserted_primary_key[0]


async def validate_llm_catalog_change(conn: AsyncConnection, llm: dict[str, Any]) -> list[str]:
    """Il catalogo è condiviso: un cambio valido deve lasciare valide le configurazioni attive di tutte le metodologie."""
    errs = validate_llm_catalog(llm, catalog().schemas)
    if errs:
        return errs
    for m, b in catalog().bundles.items():
        config, _ = await active_config(conn, m)
        errs += [f"{m}: {e}" for e in validate_bundle(b, config, catalog().schemas, llm)]
    return errs


async def get_project(conn: AsyncConnection, project_id: str) -> dict[str, Any] | None:
    row = (await conn.execute(select(projects).where(projects.c.id == project_id))).mappings().first()
    return dict(row) if row else None


async def list_projects(conn: AsyncConnection) -> list[dict[str, Any]]:
    return [dict(r) for r in (await conn.execute(select(projects).order_by(projects.c.id))).mappings()]


def _find_task(bundle: Bundle, config: dict[str, Any], slot: str, task_id: str):
    for t in effective_tasks(bundle, config):
        if t.slot == slot and t.task_id == task_id:
            return t
    return None


async def queue_run(conn: AsyncConnection, project: dict[str, Any], slot: str, task_id: str, trigger: str) -> int:
    bundle = catalog().bundle(project["methodology"])
    config, _ = await active_config(conn, project["methodology"])
    t = _find_task(bundle, config, slot, task_id)
    if t is None:
        raise ValueError(f"Compito {slot}/{task_id} inesistente")
    if t.persona_kind != "avatar":
        raise ValueError("Il compito è assegnato a una persona umana: si svolge fuori dalla piattaforma")
    res = await conn.execute(insert(task_runs).values(
        project_id=project["id"], slot=slot, task_id=task_id, task_name=t.name, persona_id=t.persona_id,
        trigger=trigger, status="queued", created_at=utcnow()))
    return res.inserted_primary_key[0]


async def execute_run(run_id: int) -> None:
    async with engine().begin() as conn:
        run = (await conn.execute(select(task_runs).where(task_runs.c.id == run_id))).mappings().first()
        if not run or run["status"] != "queued":
            return
        project = await get_project(conn, run["project_id"])
        bundle = catalog().bundle(project["methodology"])
        config, _ = await active_config(conn, project["methodology"])
        await conn.execute(update(task_runs).where(task_runs.c.id == run_id).values(status="running", started_at=utcnow()))
    sa = {s["slot"]: s for s in config["slotAssignments"]}[run["slot"]]
    agent = bundle.agents[run["slot"]]
    persona = {p["id"]: p for p in config["personas"]}[sa["persona"]]
    preset = {p["id"]: p for p in config["agentPresets"]}.get(sa.get("preset", ""), {})
    stage_id = agent["stage"] or project["current_stage"]
    context = {
        "projectName": project["name"], "stageName": bundle.stages[stage_id]["name"], "personaName": persona["name"],
        "agentName": sa.get("agentName", agent["name"]), "responsibilities": agent["responsibilities"],
        "autonomy": sa.get("autonomy", agent["autonomy"]), "instructions": sa.get("instructions"),
        "taskName": run["task_name"], "model": preset.get("model"), "fallbackModel": preset.get("fallbackModel"), "temperature": preset.get("temperature", 0.2),
    }
    try:
        output, status = await run_task(context), "done"
    except Exception as exc:  # l'errore resta visibile in console, il worker continua
        output, status = f"Errore: {exc}", "failed"
    async with engine().begin() as conn:
        await conn.execute(update(task_runs).where(task_runs.c.id == run_id).values(
            status=status, output=output, finished_at=utcnow()))


async def _log_action(conn: AsyncConnection, project: dict[str, Any], slot: str, task: Any, output: str) -> None:
    now = utcnow()
    await conn.execute(insert(task_runs).values(
        project_id=project["id"], slot=slot, task_id=task.task_id, task_name=task.name, persona_id=task.persona_id,
        trigger="cron", status="done", output=output, created_at=now, started_at=now, finished_at=now))


async def _move(conn: AsyncConnection, project: dict[str, Any], bundle: Bundle, target: str) -> None:
    values: dict[str, Any] = {"current_stage": target, "stage_started_at": utcnow()}
    # Scrum: tornare allo sprint planning dalla retrospettiva apre uno sprint nuovo
    if project.get("sprint") is not None and project["current_stage"] == "sprint-retrospective" and target == "sprint-planning":
        values["sprint"] = project["sprint"] + 1
    await conn.execute(update(projects).where(projects.c.id == project["id"]).values(**values))


async def apply_gate_decisions(project_id: str, slot: str, task: Any) -> str:
    """Compito del Coordinatore: legge le decisioni umane registrate e le applica (nessun evento, solo cron)."""
    async with engine().begin() as conn:
        project = await get_project(conn, project_id)
        bundle = catalog().bundle(project["methodology"])
        rows = (await conn.execute(select(gate_decisions).where(
            gate_decisions.c.project_id == project_id, gate_decisions.c.applied_at.is_(None),
            gate_decisions.c.stage == project["current_stage"]).order_by(gate_decisions.c.id))).mappings().all()
        if not rows:
            msg = "Nessuna decisione nuova"
        else:
            d = rows[-1]
            if d["outcome"] == "approved":
                options = [t["to"] for t in bundle.transitions_from(project["current_stage"], "gate_approved")]
                target = d["target_stage"] if d["target_stage"] in options else (options[0] if options else None)
                if target:
                    await _move(conn, project, bundle, target)
                    msg = f"Gate approvato: passaggio a «{bundle.stages[target]['name']}»"
                else:
                    msg = "Gate approvato: ultimo stadio del processo"
            else:
                msg = "Gate respinto: la fase resta attiva per il rework"
            await conn.execute(update(gate_decisions).where(gate_decisions.c.id.in_([r["id"] for r in rows])).values(applied_at=utcnow()))
        await _log_action(conn, project, slot, task, msg)
        return msg


async def check_timebox(project_id: str, slot: str, task: Any) -> str:
    async with engine().begin() as conn:
        project = await get_project(conn, project_id)
        bundle = catalog().bundle(project["methodology"])
        st = bundle.stages[project["current_stage"]]
        dur = parse_duration(st.get("timebox", ""))
        trans = bundle.transitions_from(st["id"], "timebox_end")
        started = project["stage_started_at"]
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if dur and trans and datetime.now(timezone.utc) - started >= dur:
            await _move(conn, project, bundle, trans[0]["to"])
            msg = f"Timebox di «{st['name']}» scaduto: passaggio a «{bundle.stages[trans[0]['to']]['name']}»"
            await _log_action(conn, project, slot, task, msg)
            return msg
        return "Timebox in corso"


async def run_scheduled(project_id: str, slot: str, task_id: str) -> str:
    """Entrata dei job cron del worker."""
    async with engine().begin() as conn:
        project = await get_project(conn, project_id)
        if project is None:
            return "progetto inesistente"
        bundle = catalog().bundle(project["methodology"])
        config, _ = await active_config(conn, project["methodology"])
        t = _find_task(bundle, config, slot, task_id)
        if t is None or not t.enabled or t.persona_kind != "avatar":
            return "compito non attivo"
        if not stage_is_active(bundle, t.stage, project["current_stage"]):
            return "fase non attiva"
        run_id = await queue_run(conn, project, slot, task_id, "cron") if t.action == "agent" else None
    if t.action == "apply-gate-decisions":
        return await apply_gate_decisions(project_id, slot, t)
    if t.action == "check-timebox":
        return await check_timebox(project_id, slot, t)
    await execute_run(run_id)
    return f"eseguito run {run_id}"


async def execute_queued() -> int:
    """Esegue le richieste manuali in coda (lette a intervalli dal worker)."""
    async with engine().begin() as conn:
        ids = [r[0] for r in (await conn.execute(
            select(task_runs.c.id).where(task_runs.c.status == "queued").order_by(task_runs.c.id).limit(20)))]
    for i in ids:
        await execute_run(i)
    return len(ids)
