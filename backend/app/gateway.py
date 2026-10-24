"""Sincronizzazione del gateway LiteLLM con il catalogo LLM di piattaforma.

Il worker la esegue a intervalli (nessun evento): legge i modelli presenti nel gateway tramite la sua API di
gestione (`/model/info`) e aggiunge, sostituisce o rimuove quelli gestiti da Ananke. I modelli definiti a mano
nel file di configurazione del gateway non vengono toccati. Le chiavi non passano mai di qui: il gateway le legge
dalle proprie variabili d'ambiente tramite i riferimenti `os.environ/NOME`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy import select, update

from .db import engine, gateway_syncs, utcnow
from .settings import settings

# Prefisso del modello in LiteLLM per ogni tipo di provider del catalogo
_PREFIX = {"anthropic": "anthropic", "openai": "openai", "openai-compatible": "openai", "vllm": "hosted_vllm", "ollama": "ollama_chat"}


def litellm_params(provider: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {"model": f"{_PREFIX[provider['kind']]}/{model['upstream']}"}
    if provider.get("baseUrl"):
        params["api_base"] = provider["baseUrl"]
    if provider.get("apiKeyEnv"):
        params["api_key"] = f"os.environ/{provider['apiKeyEnv']}"
    return params


def _hash(params: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


def desired_models(llm_catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """alias -> modello da pubblicare nel gateway (solo provider e modelli attivi)."""
    out: dict[str, dict[str, Any]] = {}
    for p in llm_catalog["providers"]:
        if not p.get("enabled", True):
            continue
        for m in p["models"]:
            if not m.get("enabled", True):
                continue
            params = litellm_params(p, m)
            out[m["alias"]] = {"model_name": m["alias"], "litellm_params": params,
                               "model_info": {"ananke_managed": True, "ananke_hash": _hash(params),
                                              "ananke_provider": p["id"], "ananke_family": m["family"]}}
    return out


@dataclass
class SyncPlan:
    add: list[dict[str, Any]] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)  # id dei modelli nel gateway
    unchanged: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.add and not self.delete


def plan_sync(desired: dict[str, dict[str, Any]], current: list[dict[str, Any]]) -> SyncPlan:
    """Confronta i modelli voluti con quelli del gateway. Un modello cambiato si rimuove e si aggiunge di nuovo.

    Si toccano solo i modelli salvati nel database del gateway che sono marcati come gestiti da Ananke oppure che
    hanno lo stesso nome di un modello del catalogo (così un marcatore perso non crea duplicati).
    """
    plan = SyncPlan()
    by_name: dict[str, list[dict[str, Any]]] = {}
    for c in current:
        info = c.get("model_info") or {}
        if not info.get("db_model") and not info.get("ananke_managed"):
            continue  # definito nel file del gateway: non è nostro
        if info.get("ananke_managed") or c.get("model_name") in desired:
            by_name.setdefault(c.get("model_name", ""), []).append(c)
    for name, want in desired.items():
        have = by_name.pop(name, [])
        if len(have) == 1 and (have[0].get("model_info") or {}).get("ananke_hash") == want["model_info"]["ananke_hash"]:
            plan.unchanged.append(name)
            continue
        plan.delete += [h["model_info"]["id"] for h in have if (h.get("model_info") or {}).get("id")]
        plan.add.append(want)
    for rest in by_name.values():
        plan.delete += [h["model_info"]["id"] for h in rest if (h.get("model_info") or {}).get("id")]
    return plan


async def _apply(llm_catalog: dict[str, Any]) -> str:
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    async with httpx.AsyncClient(base_url=settings.llm_admin_url, headers=headers, timeout=30) as client:
        r = await client.get("/model/info")
        r.raise_for_status()
        plan = plan_sync(desired_models(llm_catalog), r.json().get("data", []))
        for model_id in plan.delete:
            (await client.post("/model/delete", json={"id": model_id})).raise_for_status()
        for m in plan.add:
            (await client.post("/model/new", json=m)).raise_for_status()
    if plan.empty:
        return f"Gateway allineato: {len(plan.unchanged)} modelli"
    return f"Gateway aggiornato: {len(plan.add)} modelli pubblicati, {len(plan.delete)} rimossi, {len(plan.unchanged)} invariati"


async def _record(version: int, status: str, detail: str) -> None:
    """Una riga per esito diverso; se l'esito non cambia si aggiorna solo l'ora dell'ultimo controllo."""
    async with engine().begin() as conn:
        last = (await conn.execute(select(gateway_syncs).order_by(gateway_syncs.c.id.desc()).limit(1))).mappings().first()
        if last and (last["catalog_version"], last["status"], last["detail"]) == (version, status, detail):
            await conn.execute(update(gateway_syncs).where(gateway_syncs.c.id == last["id"]).values(created_at=utcnow()))
        else:
            await conn.execute(gateway_syncs.insert().values(catalog_version=version, status=status, detail=detail, created_at=utcnow()))


async def sync_gateway(llm_catalog: dict[str, Any], version: int) -> str:
    if settings.llm_mode != "live":
        status, detail = "skipped", "Modalità simulazione: nessun gateway da aggiornare"
    else:
        try:
            status, detail = "ok", await _apply(llm_catalog)
        except httpx.HTTPStatusError as exc:
            status, detail = "error", f"Il gateway ha risposto {exc.response.status_code}: {exc.response.text[:160]}"
        except httpx.HTTPError as exc:
            status, detail = "error", f"Gateway non raggiungibile ({settings.llm_admin_url}): {exc}"
    await _record(version, status, detail)
    return detail
