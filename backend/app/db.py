"""Persistenza: progetti, versioni di configurazione e del catalogo LLM, esecuzioni dei compiti, decisioni sui gate, sincronizzazioni del gateway."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, Text, UniqueConstraint, func, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .settings import settings

metadata = MetaData()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


projects = Table(
    "projects", metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(200), nullable=False),
    Column("client", String(200), nullable=False, default=""),
    Column("methodology", String(32), nullable=False),
    Column("current_stage", String(64), nullable=False),
    Column("stage_started_at", DateTime(timezone=True), nullable=False, default=utcnow),
    Column("sprint", Integer, nullable=True),
)

config_versions = Table(
    "config_versions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("methodology", String(32), nullable=False, index=True),
    Column("content", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
)

task_runs = Table(
    "task_runs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("slot", String(64), nullable=False),
    Column("task_id", String(64), nullable=False),
    Column("task_name", String(200), nullable=False),
    Column("persona_id", String(64), nullable=False, index=True),
    Column("trigger", String(16), nullable=False),  # cron | manual
    Column("status", String(16), nullable=False),  # queued | running | done | failed | skipped
    Column("output", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("finished_at", DateTime(timezone=True), nullable=True),
)

gate_decisions = Table(
    "gate_decisions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("stage", String(64), nullable=False),
    Column("outcome", String(16), nullable=False),  # approved | rejected
    Column("target_stage", String(64), nullable=True),
    Column("persona_id", String(64), nullable=False),
    Column("note", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
    Column("applied_at", DateTime(timezone=True), nullable=True),
)

# Artefatti prodotti dagli agenti: solo inserimenti, ogni esecuzione crea una nuova versione per (progetto, tipo)
artifacts = Table(
    "artifacts", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("stage", String(64), nullable=False),
    Column("artifact_type", String(64), nullable=False),  # id in process.artifacts
    Column("slot", String(64), nullable=False),
    Column("version", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("run_id", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
    UniqueConstraint("project_id", "artifact_type", "version"),
)

# Revisioni di una versione di artefatto fatte dall'agente indicato in `reviewedBy`
reviews = Table(
    "reviews", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("artifact_id", Integer, nullable=False, index=True),
    Column("artifact_type", String(64), nullable=False),
    Column("artifact_version", Integer, nullable=False),
    Column("reviewer_slot", String(64), nullable=False),
    Column("task_id", String(64), nullable=False),
    Column("run_id", Integer, nullable=True),
    Column("verdict", String(24), nullable=False),  # approved | changes_requested
    Column("findings", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
)

# Pacchetto di evidenze del gatekeeper: stato di ogni criterio del gate dello stadio
evidence_packs = Table(
    "evidence_packs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String(64), nullable=False, index=True),
    Column("stage", String(64), nullable=False),
    Column("run_id", Integer, nullable=True),
    Column("criteria", JSON, nullable=False),  # [{criterion, status: met|unmet|unknown, evidence}]
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
)

# Catalogo LLM di piattaforma: solo inserimenti, l'ultima riga è quella attiva (versione 0 = file del repository)
llm_catalog_versions = Table(
    "llm_catalog_versions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("content", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
)

# Esito delle sincronizzazioni del gateway LiteLLM eseguite dal worker
gateway_syncs = Table(
    "gateway_syncs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("catalog_version", Integer, nullable=False),
    Column("status", String(16), nullable=False),  # ok | error | skipped
    Column("detail", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=utcnow),
)

_engine: AsyncEngine | None = None


def engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def set_engine(e: AsyncEngine) -> None:
    """Usato dai test per puntare a un database temporaneo."""
    global _engine
    _engine = e


async def init_db() -> None:
    async with engine().begin() as conn:
        await conn.run_sync(metadata.create_all)
        count = (await conn.execute(select(func.count()).select_from(projects))).scalar_one()
        if count == 0:
            seed = settings.data_dir / "projects.json"
            if seed.exists():
                rows: list[dict[str, Any]] = json.loads(seed.read_text(encoding="utf-8"))
                for r in rows:
                    await conn.execute(insert(projects).values(
                        id=r["id"], name=r["name"], client=r.get("client", ""), methodology=r["methodology"],
                        current_stage=r["currentStage"], stage_started_at=utcnow(), sprint=r.get("sprint")))
