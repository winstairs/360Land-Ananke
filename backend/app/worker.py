"""Worker: esegue i compiti degli avatar secondo la loro pianificazione cron. Nessun evento.

- un job cron per ogni compito abilitato di ogni progetto;
- un job a intervallo che esegue le richieste manuali "Esegui ora" messe in coda dalla console;
- un job a intervallo che ricarica la configurazione e ripianifica;
- un job a intervallo che sincronizza il gateway LiteLLM con il catalogo LLM (solo in modalità live).
Avvio: python -m app.worker
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import engine, init_db
from .gateway import sync_gateway
from .scheduling import effective_tasks
from .services import active_config, active_llm_catalog, catalog, execute_queued, list_projects, run_scheduled
from .settings import settings

log = logging.getLogger("worker")
TZ = ZoneInfo(settings.timezone)


async def _job(project_id: str, slot: str, task_id: str) -> None:
    try:
        result = await run_scheduled(project_id, slot, task_id)
        log.info("%s %s/%s: %s", project_id, slot, task_id, result)
    except Exception:
        log.exception("Errore nel compito %s %s/%s", project_id, slot, task_id)


async def _poll() -> None:
    n = await execute_queued()
    if n:
        log.info("Eseguite %d richieste manuali", n)


async def _sync_gateway() -> None:
    try:
        async with engine().connect() as conn:
            llm, version = await active_llm_catalog(conn)
        log.info("Gateway: %s", await sync_gateway(llm, version))
    except Exception:
        log.exception("Errore nella sincronizzazione del gateway")


async def reschedule(sched: AsyncIOScheduler) -> None:
    for job in sched.get_jobs():
        if job.id.startswith("task:"):
            job.remove()
    count = 0
    async with engine().connect() as conn:
        for p in await list_projects(conn):
            bundle = catalog().bundle(p["methodology"])
            config, version = await active_config(conn, p["methodology"])
            for t in effective_tasks(bundle, config):
                if not t.enabled or t.persona_kind != "avatar":
                    continue
                sched.add_job(_job, CronTrigger.from_crontab(t.cron, timezone=TZ), args=[p["id"], t.slot, t.task_id],
                              id=f"task:{p['id']}:{t.slot}:{t.task_id}", replace_existing=True,
                              misfire_grace_time=300, coalesce=True, max_instances=1)
                count += 1
    log.info("Pianificati %d compiti", count)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    await init_db()
    sched = AsyncIOScheduler(timezone=TZ)
    await reschedule(sched)
    sched.add_job(_poll, "interval", seconds=settings.poll_seconds, id="poll-manual-runs", max_instances=1, coalesce=True)
    sched.add_job(reschedule, "interval", minutes=settings.reload_minutes, args=[sched], id="reload", max_instances=1)
    sched.add_job(_sync_gateway, "interval", minutes=settings.reload_minutes, id="sync-gateway", max_instances=1,
                  coalesce=True, next_run_time=datetime.now(TZ))
    sched.start()
    log.info("Worker avviato (LLM_MODE=%s, fuso %s)", settings.llm_mode, settings.timezone)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
