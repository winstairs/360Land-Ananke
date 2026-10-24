import copy

from app.services import catalog
from app.validation import validate_bundle, validate_llm_catalog


def _wf():
    cat = catalog()
    b = cat.bundle("waterfall")
    return cat, b, copy.deepcopy(b.default_config)


def test_default_models_are_valid():
    cat = catalog()
    for name, b in cat.bundles.items():
        assert validate_bundle(b, b.default_config, cat.schemas, cat.llm_catalog) == [], name


def test_approver_role_cannot_be_agent_only():
    cat, b, cfg = _wf()
    for r in cfg["roleAssignments"]:
        if r["role"] == "sponsor":
            r["mode"] = "agent"
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("Sponsor" in e and "solo da agenti" in e for e in errs)


def test_process_roles_accept_only_human_personas():
    cat, b, cfg = _wf()
    for r in cfg["roleAssignments"]:
        if r["role"] == "pm":
            r["personas"] = ["ada"]
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("avatar" in e for e in errs)


def test_avatar_can_have_technical_email():
    cat, b, cfg = _wf()
    for p in cfg["personas"]:
        if p["id"] == "ada":
            p["email"] = "ada.agente@azienda.it"
    assert validate_bundle(b, cfg, cat.schemas, cat.llm_catalog) == []


def test_malformed_email_is_rejected():
    cat, b, cfg = _wf()
    for p in cfg["personas"]:
        if p["id"] == "ada":
            p["email"] = "ada-senza-dominio"
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("email non valida" in e for e in errs)


def test_cross_family_review_is_enforced():
    cat, b, cfg = _wf()
    for s in cfg["slotAssignments"]:
        if s["slot"] == "requirements-validator-agent":
            s["preset"] = "claude-worker"
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("stessa famiglia" in e for e in errs)


def test_invalid_cron_override_is_rejected():
    cat, b, cfg = _wf()
    for s in cfg["slotAssignments"]:
        if s["slot"] == "requirements-validator-agent":
            s["taskOverrides"] = {"validity": {"cron": "ogni lunedì"}}
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("cron non valido" in e for e in errs)


def test_email_does_not_make_an_avatar_human():
    # L'email dell'utente tecnico non conta per la governance: decide solo kind
    cat, b, cfg = _wf()
    for p in cfg["personas"]:
        if p["id"] == "ada":
            p["email"] = "ada.agente@azienda.it"
    for r in cfg["roleAssignments"]:
        if r["role"] == "pm":
            r["personas"] = ["ada"]
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("è un avatar" in e for e in errs)


def _llm():
    cat = catalog()
    return cat, copy.deepcopy(cat.llm_catalog)


def _provider(llm, pid):
    return next(p for p in llm["providers"] if p["id"] == pid)


def test_default_llm_catalog_is_valid():
    cat, llm = _llm()
    assert validate_llm_catalog(llm, cat.schemas) == []


def test_llm_alias_must_be_unique():
    cat, llm = _llm()
    _provider(llm, "openai")["models"][0]["alias"] = "claude-opus"
    assert any("claude-opus" in e and "più volte" in e for e in validate_llm_catalog(llm, cat.schemas))


def test_llm_api_key_env_name_is_checked():
    cat, llm = _llm()
    _provider(llm, "openai")["apiKeyEnv"] = "sk-1234 chiave"
    assert any("nome di variabile" in e for e in validate_llm_catalog(llm, cat.schemas))


def test_self_hosted_provider_needs_base_url():
    cat, llm = _llm()
    del _provider(llm, "hetzner-gpu")["baseUrl"]
    assert any("baseUrl" in e for e in validate_llm_catalog(llm, cat.schemas))


def test_preset_on_disabled_model_is_rejected():
    cat, b, cfg = _wf()
    llm = copy.deepcopy(cat.llm_catalog)
    _provider(llm, "ollama-local")["enabled"] = False
    errs = validate_bundle(b, cfg, cat.schemas, llm)
    assert any("ollama-local/oss-generalist" in e and "non è attivo" in e for e in errs)


def test_cross_family_uses_catalog_families():
    # Se il modello open diventa della famiglia claude, il revisore dei requisiti viola la regola
    cat, b, cfg = _wf()
    llm = copy.deepcopy(cat.llm_catalog)
    for m in _provider(llm, "ollama-local")["models"]:
        m["family"] = "claude"
    errs = validate_bundle(b, cfg, cat.schemas, llm)
    assert any("stessa famiglia" in e for e in errs)


def test_config_saved_with_schema_1_1_is_upgraded():
    from app.services import upgrade_config
    cat, b, cfg = _wf()
    old = copy.deepcopy(cfg)
    old["llmProviders"] = [{"id": "vllm-local"}]
    for p in old["agentPresets"]:
        if p["id"] == "open-generalist":
            p["model"], p["fallbackModel"] = "vllm-local/oss-generalist", "open-cloud/oss-generalist-cloud"
    new = upgrade_config(old)
    assert "llmProviders" not in new
    assert validate_bundle(b, new, cat.schemas, cat.llm_catalog) == []


def test_cross_family_considers_fallback_model():
    # Il redattore usa Claude con riserva Qwen, il validatore usa Qwen: se Claude non risponde, stessa famiglia
    cat, b, cfg = _wf()
    for p in cfg["agentPresets"]:
        if p["id"] == "claude-worker":
            p["fallbackModel"] = "ollama-local/oss-generalist"
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("requirements-writer-agent" in e and "riserva" in e for e in errs)


def test_platform_secrets_cannot_be_used_as_provider_keys():
    cat, llm = _llm()
    for name in ("LITELLM_MASTER_KEY", "POSTGRES_PASSWORD", "DATABASE_URL", "LLM_API_KEY"):
        _provider(llm, "openai")["apiKeyEnv"] = name
        errs = validate_llm_catalog(llm, cat.schemas)
        assert errs, name
    _provider(llm, "openai")["apiKeyEnv"] = "MY_SECRET"
    assert any("_API_KEY" in e for e in validate_llm_catalog(llm, cat.schemas))


def _connector(cfg, cid):
    return next(c for c in cfg["connectors"] if c["id"] == cid)


def test_connector_settings_accept_env_names():
    cat, b, cfg = _wf()
    _connector(cfg, "github")["settings"] = {"auth": "github-app", "appId": "123", "privateKeyEnv": "GITHUB_APP_PRIVATE_KEY"}
    _connector(cfg, "atlassian-jira")["transport"] = "mcp-local"
    _connector(cfg, "atlassian-jira")["settings"] = {"command": "uvx", "args": ["mcp-atlassian"], "envVars": ["JIRA_URL", "JIRA_API_TOKEN"]}
    assert validate_bundle(b, cfg, cat.schemas, cat.llm_catalog) == []


def test_connector_secrets_are_not_stored():
    cat, b, cfg = _wf()
    _connector(cfg, "atlassian-jira")["settings"]["token"] = "ATATT3x..."
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("segreti non si salvano" in e for e in errs)


def test_connector_env_names_are_checked():
    cat, b, cfg = _wf()
    _connector(cfg, "plane")["settings"]["tokenEnv"] = "plane-key-123"
    _connector(cfg, "github")["settings"]["envVars"] = ["POSTGRES_PASSWORD"]
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("plane" in e and "variabile d'ambiente" in e for e in errs)
    assert any("riservata" in e for e in errs)


def test_connector_ids_are_unique():
    cat, b, cfg = _wf()
    cfg["connectors"].append(copy.deepcopy(_connector(cfg, "plane")))
    errs = validate_bundle(b, cfg, cat.schemas, cat.llm_catalog)
    assert any("connettori duplicati" in e for e in errs)
