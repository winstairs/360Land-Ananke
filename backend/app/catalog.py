"""Caricamento dei modelli JSON: processo, topologia agenti e configurazione per ogni metodologia, catalogo LLM di piattaforma."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

METHODOLOGIES = ("waterfall", "scrum")


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class Bundle:
    """Processo, topologia e configurazione di default di una metodologia."""

    methodology: str
    process: dict[str, Any]
    topology: dict[str, Any]
    default_config: dict[str, Any]

    @cached_property
    def stages(self) -> dict[str, dict[str, Any]]:
        return {s["id"]: s for s in sorted(self.process["stages"], key=lambda s: s["order"])}

    @cached_property
    def roles(self) -> dict[str, dict[str, Any]]:
        return {r["id"]: r for r in self.process["roles"]}

    @cached_property
    def agents(self) -> dict[str, dict[str, Any]]:
        """Tutti gli slot agente, con lo stadio dell'orchestratore (None per il supervisore)."""
        out: dict[str, dict[str, Any]] = {}
        for a in self.topology["supervisor"]["agents"]:
            out[a["id"]] = {**a, "stage": None}
        for o in self.topology["orchestrators"]:
            for a in o["agents"]:
                out[a["id"]] = {**a, "stage": o["stage"]}
        return out

    @cached_property
    def activity_stage(self) -> dict[str, str]:
        return {ac["id"]: s["id"] for s in self.process["stages"] for ac in s["activities"]}

    def transitions_from(self, stage_id: str, trigger: str) -> list[dict[str, Any]]:
        return [t for t in self.process["transitions"] if t["from"] == stage_id and t["trigger"] == trigger]


@dataclass
class Catalog:
    models_dir: Path
    bundles: dict[str, Bundle] = field(default_factory=dict)
    schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Catalogo LLM di default della piattaforma (versione 0), condiviso da tutte le metodologie
    llm_catalog: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, models_dir: Path) -> "Catalog":
        cat = cls(models_dir=models_dir)
        sd = models_dir / "schemas"
        cat.schemas = {
            "process": _load(sd / "process-model.schema.json"),
            "topology": _load(sd / "agent-topology.schema.json"),
            "config": _load(sd / "platform-config.schema.json"),
            "llm": _load(sd / "llm-catalog.schema.json"),
        }
        cat.llm_catalog = _load(models_dir / "platform" / "llm-catalog.json")
        for m in METHODOLOGIES:
            d = models_dir / m
            if not d.exists():
                continue
            cat.bundles[m] = Bundle(
                methodology=m,
                process=_load(d / f"{m}.process.json"),
                topology=_load(d / f"{m}.agents.json"),
                default_config=_load(d / f"{m}.config.json"),
            )
        return cat

    def bundle(self, methodology: str) -> Bundle:
        if methodology not in self.bundles:
            raise KeyError(f"Metodologia sconosciuta: {methodology}")
        return self.bundles[methodology]
