import copy

import pytest

from app.gateway import desired_models, litellm_params, plan_sync, sync_gateway
from app.services import catalog


def test_litellm_params_per_kind():
    m = {"alias": "x", "upstream": "model-1", "family": "f"}
    assert litellm_params({"kind": "anthropic", "apiKeyEnv": "ANTHROPIC_API_KEY"}, m) == {
        "model": "anthropic/model-1", "api_key": "os.environ/ANTHROPIC_API_KEY"}
    assert litellm_params({"kind": "openai", "apiKeyEnv": "OPENAI_API_KEY"}, m)["model"] == "openai/model-1"
    p = litellm_params({"kind": "openai-compatible", "baseUrl": "https://h/v1", "apiKeyEnv": "K"}, m)
    assert p == {"model": "openai/model-1", "api_base": "https://h/v1", "api_key": "os.environ/K"}
    assert litellm_params({"kind": "vllm", "baseUrl": "https://gpu/v1"}, m)["model"] == "hosted_vllm/model-1"
    assert litellm_params({"kind": "ollama", "baseUrl": "http://ollama:11434"}, m) == {
        "model": "ollama_chat/model-1", "api_base": "http://ollama:11434"}


def test_desired_models_skip_disabled():
    llm = copy.deepcopy(catalog().llm_catalog)
    names = set(desired_models(llm))
    assert {"claude-opus", "oss-generalist"} <= names
    assert "openai-gpt" not in names and "hetzner-generalist" not in names


def _have(name, mid, hash_, managed=True):
    info = {"id": mid, "db_model": True, "ananke_hash": hash_}
    if managed:
        info["ananke_managed"] = True
    return {"model_name": name, "model_info": info}


def test_plan_sync_adds_updates_removes():
    desired = desired_models(catalog().llm_catalog)
    same = desired["claude-opus"]["model_info"]["ananke_hash"]
    current = [
        _have("claude-opus", "1", same),                 # invariato
        _have("claude-sonnet", "2", "vecchio"),          # cambiato: si rimuove e si ripubblica
        _have("modello-tolto", "3", "x"),                # non più nel catalogo
        _have("claude-haiku", "4", "x", managed=False),  # stesso nome ma senza marcatore: si sostituisce
        {"model_name": "da-file", "model_info": {"id": "5"}},  # dal file del gateway: non si tocca
    ]
    plan = plan_sync(desired, current)
    assert "claude-opus" in plan.unchanged
    assert set(plan.delete) == {"2", "3", "4"}
    added = {m["model_name"] for m in plan.add}
    assert {"claude-sonnet", "claude-haiku", "oss-generalist"} <= added and "claude-opus" not in added


@pytest.mark.anyio
async def test_sync_is_skipped_in_mock_mode():
    from app.db import init_db
    await init_db()
    assert "simulazione" in await sync_gateway(catalog().llm_catalog, 0)
