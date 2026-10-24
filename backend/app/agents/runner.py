"""Esecuzione di un compito di agente con LangGraph.

Grafo minimo: prepare -> act. In modalità mock produce un esito simulato (nessuna chiave richiesta);
in modalità live chiama il modello tramite il gateway LiteLLM usando l'alias del preset.
Fase 2 della roadmap: strumenti MCP, revisione incrociata, checkpoint persistenti.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..settings import settings


class RunState(TypedDict, total=False):
    context: dict[str, Any]
    system: str
    prompt: str
    output: str


def _prepare(state: RunState) -> RunState:
    c = state["context"]
    system = (
        f"Sei «{c['agentName']}», un agente dell'avatar {c['personaName']} nella fase «{c['stageName']}» "
        f"del progetto «{c['projectName']}».\n"
        f"Responsabilità: {'; '.join(c['responsibilities'])}.\n"
        f"Livello di autonomia: {c['autonomy']}. Non prendere decisioni riservate alle persone che approvano i gate.\n"
        f"{c.get('instructions') or ''}"
    ).strip()
    prompt = (
        f"Esegui il compito standard «{c['taskName']}».\n"
        "Restituisci: 1) cosa hai fatto, 2) risultati principali, 3) segnalazioni per il Coordinatore."
    )
    return {"system": system, "prompt": prompt}


async def _act(state: RunState) -> RunState:
    c = state["context"]
    if settings.llm_mode != "live":
        return {"output": (
            f"[simulazione] {c['agentName']} ha eseguito «{c['taskName']}» nella fase {c['stageName']}. "
            "Nessuna chiamata a modelli: imposta LLM_MODE=live e le chiavi nel file .env per l'esecuzione reale.")}
    from openai import AsyncOpenAI  # import pigro: non serve in modalità mock

    client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
    # Il preset cita provider/alias; nel gateway il modello si chiama con l'alias, unico nel catalogo LLM
    models = [m.split("/")[-1] for m in (c.get("model") or "anthropic/claude-sonnet", c.get("fallbackModel")) if m]
    for i, alias in enumerate(models):
        try:
            resp = await client.chat.completions.create(
                model=alias,
                temperature=c.get("temperature", 0.2),
                max_tokens=1500,
                messages=[{"role": "system", "content": state["system"]}, {"role": "user", "content": state["prompt"]}],
            )
        except Exception:
            if i == len(models) - 1:
                raise
            continue  # si passa al modello di riserva del preset
        note = f"[eseguito con il modello di riserva {alias}]\n" if i else ""
        return {"output": note + (resp.choices[0].message.content or "")}
    return {"output": ""}


def _build():
    g = StateGraph(RunState)
    g.add_node("prepare", _prepare)
    g.add_node("act", _act)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "act")
    g.add_edge("act", END)
    return g.compile()


_graph = _build()


async def run_task(context: dict[str, Any]) -> str:
    result = await _graph.ainvoke({"context": context})
    return result["output"]
