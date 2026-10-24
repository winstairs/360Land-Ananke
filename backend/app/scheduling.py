"""Compiti pianificati: unione tra i compiti standard della topologia e gli override della configurazione."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger

from .catalog import Bundle
from .settings import settings


@dataclass(frozen=True)
class EffectiveTask:
    slot: str
    task_id: str
    name: str
    cron: str
    enabled: bool
    action: str
    stage: str | None  # None: slot del supervisore, sempre attivo
    persona_id: str
    persona_kind: str


def effective_tasks(bundle: Bundle, config: dict[str, Any]) -> list[EffectiveTask]:
    personas = {p["id"]: p for p in config["personas"]}
    sa = {s["slot"]: s for s in config["slotAssignments"]}
    out: list[EffectiveTask] = []
    for slot, agent in bundle.agents.items():
        s = sa.get(slot)
        if s is None:
            continue
        persona = personas.get(s["persona"], {"kind": "human"})
        slot_enabled = s.get("enabled", True)
        for t in agent.get("scheduledTasks", []):
            ov = s.get("taskOverrides", {}).get(t["id"], {})
            out.append(EffectiveTask(
                slot=slot, task_id=t["id"], name=t["name"], cron=ov.get("cron", t["cron"]),
                enabled=slot_enabled and ov.get("enabled", True), action=t.get("action", "agent"),
                stage=agent["stage"], persona_id=s["persona"], persona_kind=persona["kind"]))
    return out


def stage_is_active(bundle: Bundle, task_stage: str | None, current_stage: str) -> bool:
    """Un compito di orchestratore gira solo nella sua fase, salvo stadi continui (es. product backlog)."""
    if task_stage is None:
        return True
    if task_stage == current_stage:
        return True
    return bool(bundle.stages.get(task_stage, {}).get("continuous"))


def next_fire(cron: str, now: datetime | None = None) -> datetime | None:
    tz = ZoneInfo(settings.timezone)
    try:
        trig = CronTrigger.from_crontab(cron, timezone=tz)
    except ValueError:
        return None
    now = now or datetime.now(tz)
    return trig.get_next_fire_time(None, now)


_DUR = re.compile(r"^P(?:(?P<w>\d+)W)?(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?)?$")


def parse_duration(iso: str) -> timedelta | None:
    """Durate ISO 8601 usate nei timebox: P2W, P1D, PT4H, PT1H30M."""
    m = _DUR.match(iso or "")
    if not m or not any(m.groupdict().values()):
        return None
    g = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return timedelta(weeks=g["w"], days=g["d"], hours=g["h"], minutes=g["m"])
