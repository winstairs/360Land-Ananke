"""Validazione dei modelli: schema JSON + coerenza dei riferimenti + regole di governance.

Le regole di governance sono il cuore della piattaforma e non vanno indebolite:
- chi approva un gate o è Accountable in una RACI deve essere coperto da almeno una persona umana;
- chi revisiona usa una famiglia di modelli diversa da chi produce (se la policy lo chiede);
- ogni attività e ogni artefatto del processo è coperto da almeno uno slot agente.
"""
from __future__ import annotations

import re
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from jsonschema import Draft202012Validator

from .catalog import Bundle

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ENV_VAR = re.compile(r"^[A-Z][A-Z0-9_]*_(API_KEY|KEY|TOKEN)$")
# Variabili della piattaforma che il gateway conosce ma che non devono mai essere inviate a un provider
RESERVED_ENV_PREFIXES = ("LITELLM_", "POSTGRES_", "DATABASE_", "LLM_", "PG")
# I connettori indicano i segreti solo col nome della variabile d'ambiente (chiavi *Env, lista envVars)
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
SECRET_SETTING_KEYS = {"password", "token", "secret", "apikey", "clientsecret", "privatekey", "accesstoken"}
NEEDS_BASE_URL = {"openai-compatible", "vllm", "ollama"}
NEEDS_API_KEY = {"anthropic", "openai"}


def cron_is_valid(expr: str) -> bool:
    try:
        CronTrigger.from_crontab(expr)
        return True
    except (ValueError, TypeError):
        return False


def _schema_errors(schema: dict[str, Any], doc: dict[str, Any], label: str) -> list[str]:
    v = Draft202012Validator(schema)
    return [f"{label}: {'/'.join(str(p) for p in e.absolute_path) or '(radice)'}: {e.message}" for e in v.iter_errors(doc)]


def validate_process_and_topology(bundle: Bundle, schemas: dict[str, dict[str, Any]]) -> list[str]:
    P, T = bundle.process, bundle.topology
    errs = _schema_errors(schemas["process"], P, "processo") + _schema_errors(schemas["topology"], T, "topologia")
    if errs:
        return errs
    roles = set(bundle.roles)
    arts = {a["id"] for a in P["artifacts"]}
    stages = bundle.stages
    cc = {c["id"] for c in P.get("crossCuttingProcesses", [])}

    acts: list[str] = []
    for st in P["stages"]:
        for x in st.get("inputs", []) + st["outputs"]:
            if x not in arts:
                errs.append(f"processo: lo stadio {st['id']} cita l'artefatto inesistente {x}")
        for ac in st["activities"]:
            acts.append(ac["id"])
            r = ac["raci"]
            for x in r["R"] + [r["A"]] + r.get("C", []) + r.get("I", []):
                if x not in roles:
                    errs.append(f"processo: l'attività {ac['id']} cita il ruolo inesistente {x}")
        for x in st.get("gate", {}).get("approvers", []):
            if x not in roles:
                errs.append(f"processo: il gate di {st['id']} cita il ruolo inesistente {x}")
    if len(acts) != len(set(acts)):
        errs.append("processo: id di attività duplicati")
    for t in P["transitions"]:
        for k in ("from", "to"):
            if t[k] not in stages:
                errs.append(f"processo: transizione verso lo stadio inesistente {t[k]}")

    if T["processModel"] != P["id"]:
        errs.append("topologia: processModel non corrisponde al processo")
    sup_ids = {a["id"] for a in T["supervisor"]["agents"]}
    if T["supervisor"]["lead"] not in sup_ids:
        errs.append("topologia: il lead del supervisore non è tra i suoi agenti")
    seen_stages: set[str] = set()
    for o in T["orchestrators"]:
        if o["stage"] in seen_stages:
            errs.append(f"topologia: due orchestratori per lo stadio {o['stage']}")
        seen_stages.add(o["stage"])
        if o["escalatesTo"] not in sup_ids or o["gateReviewer"] not in sup_ids:
            errs.append(f"topologia: {o['id']} scala o fa verificare il gate a un agente fuori dal supervisore")
    for s in set(stages) - seen_stages:
        errs.append(f"topologia: lo stadio {s} non ha un orchestratore")

    agents = bundle.agents
    all_ids = [a["id"] for a in T["supervisor"]["agents"]] + [a["id"] for o in T["orchestrators"] for a in o["agents"]]
    if len(all_ids) != len(set(all_ids)):
        errs.append("topologia: id di agenti duplicati")
    covered: set[str] = set()
    produced: set[str] = set()
    for a in agents.values():
        if a["supportsRole"] not in roles:
            errs.append(f"topologia: {a['id']} supporta il ruolo inesistente {a['supportsRole']}")
        for x in a.get("consumes", []) + a.get("produces", []):
            if x not in arts:
                errs.append(f"topologia: {a['id']} cita l'artefatto inesistente {x}")
        for x in a.get("activities", []):
            if x not in bundle.activity_stage:
                errs.append(f"topologia: {a['id']} cita l'attività inesistente {x}")
            elif a["stage"] is not None and bundle.activity_stage[x] != a["stage"]:
                errs.append(f"topologia: {a['id']} svolge {x}, che appartiene a un altro stadio")
        covered |= set(a.get("activities", []))
        produced |= set(a.get("produces", []))
        rb = a.get("reviewedBy")
        if rb and (rb not in agents or rb == a["id"]):
            errs.append(f"topologia: revisore non valido per {a['id']}")
        if a.get("crossCutting") and a["crossCutting"] not in cc:
            errs.append(f"topologia: {a['id']} cita il processo trasversale inesistente {a['crossCutting']}")
        task_ids = [t["id"] for t in a.get("scheduledTasks", [])]
        if not task_ids:
            errs.append(f"topologia: {a['id']} non ha compiti pianificati")
        if len(task_ids) != len(set(task_ids)):
            errs.append(f"topologia: compiti duplicati in {a['id']}")
        for t in a.get("scheduledTasks", []):
            if not cron_is_valid(t["cron"]):
                errs.append(f"topologia: cron non valido per {a['id']}/{t['id']}: {t['cron']}")
            if t.get("activity") and t["activity"] not in bundle.activity_stage:
                errs.append(f"topologia: il compito {a['id']}/{t['id']} cita un'attività inesistente")
    for x in sorted(set(bundle.activity_stage) - covered):
        errs.append(f"topologia: l'attività {x} non è coperta da nessun agente")
    needed = set().union(*[set(s["outputs"]) for s in P["stages"]])
    for x in sorted(needed - produced):
        errs.append(f"topologia: l'artefatto {x} non è prodotto da nessun agente")
    sup_cc = {a.get("crossCutting") for a in T["supervisor"]["agents"]}
    for x in sorted(cc - sup_cc):
        errs.append(f"topologia: il processo trasversale {x} non ha un agente responsabile")
    for h in T.get("humanCheckpoints", []):
        for r in h["roles"]:
            if r not in roles:
                errs.append(f"topologia: il checkpoint {h['id']} cita il ruolo inesistente {r}")
    return errs


def roles_needing_human(bundle: Bundle) -> dict[str, list[str]]:
    """Ruolo -> elenco di motivi per cui deve restare a una persona umana."""
    out: dict[str, list[str]] = {}
    for st in bundle.process["stages"]:
        for r in st.get("gate", {}).get("approvers", []):
            out.setdefault(r, []).append(f"approva il gate di {st['name']}")
        for ac in st["activities"]:
            out.setdefault(ac["raci"]["A"], []).append(f"è Accountable di «{ac['name']}»")
    return out


def validate_llm_catalog(catalog: dict[str, Any], schemas: dict[str, dict[str, Any]]) -> list[str]:
    """Catalogo LLM di piattaforma: è la fonte del gateway, quindi gli alias devono essere univoci."""
    errs = _schema_errors(schemas["llm"], catalog, "catalogo LLM")
    if errs:
        return errs
    ids = [p["id"] for p in catalog["providers"]]
    for x in sorted({i for i in ids if ids.count(i) > 1}):
        errs.append(f"catalogo LLM: provider duplicato {x}")
    aliases = [m["alias"] for p in catalog["providers"] for m in p["models"]]
    for x in sorted({a for a in aliases if aliases.count(a) > 1}):
        errs.append(f"catalogo LLM: l'alias {x} è usato più volte; ogni modello deve avere un nome unico nel gateway")
    for p in catalog["providers"]:
        if p["kind"] in NEEDS_BASE_URL and not p.get("baseUrl"):
            errs.append(f"provider {p['name']}: serve l'indirizzo dell'API (baseUrl)")
        if p["kind"] in NEEDS_API_KEY and not p.get("apiKeyEnv"):
            errs.append(f"provider {p['name']}: serve il nome della variabile con la chiave API")
        env = p.get("apiKeyEnv")
        if env and env.startswith(RESERVED_ENV_PREFIXES):
            errs.append(f"provider {p['name']}: {env} è una variabile riservata della piattaforma e non può essere inviata a un provider")
        elif env and not ENV_VAR.match(env):
            errs.append(f"provider {p['name']}: {env} non è un nome di variabile valido; deve finire con _API_KEY, _KEY o _TOKEN (es. OPENAI_API_KEY)")
    return errs


def model_families(catalog: dict[str, Any]) -> dict[str, str]:
    """provider/alias -> famiglia, solo per i modelli attivi di provider attivi."""
    return {f"{p['id']}/{m['alias']}": m["family"] for p in catalog["providers"] if p.get("enabled", True)
            for m in p["models"] if m.get("enabled", True)}


def validate_config(bundle: Bundle, config: dict[str, Any], schemas: dict[str, dict[str, Any]],
                    llm_catalog: dict[str, Any]) -> list[str]:
    errs = _schema_errors(schemas["config"], config, "configurazione")
    if errs:
        return errs
    if config["processModel"] != bundle.process["id"] or config["agentTopology"] != bundle.topology["id"]:
        errs.append("configurazione: processModel o agentTopology non corrispondono alla metodologia")

    personas = {p["id"]: p for p in config["personas"]}
    if len(personas) != len(config["personas"]):
        errs.append("configurazione: id di persone duplicati")
    families = model_families(llm_catalog)
    presets = {p["id"]: p for p in config["agentPresets"]}
    connectors = {c["id"] for c in config["connectors"]}

    for p in presets.values():
        for k in ("model", "fallbackModel"):
            if p.get(k) and p[k] not in families:
                errs.append(f"preset {p['id']}: il modello {p[k]} non esiste o non è attivo nel catalogo LLM")
        for c in p.get("allowedConnectors", []):
            if c not in connectors:
                errs.append(f"preset {p['id']}: connettore sconosciuto {c}")
    for p in personas.values():
        for d in p.get("delegates", []):
            if presets.get(d, {}).get("kind") != "external-agent":
                errs.append(f"persona {p['id']}: il delegato {d} non è un agente esterno")
        # Anche gli avatar possono avere un'email: è l'utente tecnico con cui gli agenti usano i connettori
        if p.get("email") and not EMAIL.match(p["email"]):
            errs.append(f"persona {p['id']}: email non valida ({p['email']})")

    if len(connectors) != len(config["connectors"]):
        errs.append("configurazione: id di connettori duplicati")
    for c in config["connectors"]:
        for k, v in c.get("settings", {}).items():
            names = v if k == "envVars" else [v] if k.endswith("Env") else None
            if k.lower() in SECRET_SETTING_KEYS:
                errs.append(f"connettore {c['id']}: i segreti non si salvano nella configurazione ({k}); indica il nome della variabile d'ambiente")
            elif names is not None:
                for n in names if isinstance(names, list) else [names]:
                    if not isinstance(n, str) or not ENV_NAME.match(n):
                        errs.append(f"connettore {c['id']}: {k} deve essere il nome di una variabile d'ambiente (es. JIRA_API_TOKEN), non {n!r}")
                    elif n.startswith(RESERVED_ENV_PREFIXES):
                        errs.append(f"connettore {c['id']}: la variabile {n} è riservata alla piattaforma")

    b = config["bindings"]
    for k in ("workTracking", "knowledgeBase", "fileStorage", "codeHosting"):
        if b.get(k) and b[k] not in connectors:
            errs.append(f"binding {k}: connettore sconosciuto {b[k]}")
    arts = {a["id"] for a in bundle.process["artifacts"]}
    storage = b.get("artifactStorage", {})
    for a in sorted(arts - set(storage)):
        errs.append(f"binding: l'artefatto {a} non ha un connettore di destinazione")
    for a, c in storage.items():
        if a not in arts:
            errs.append(f"binding: artefatto sconosciuto {a}")
        if c not in connectors:
            errs.append(f"binding: connettore sconosciuto {c} per {a}")

    # Ruoli del processo
    ra = {r["role"]: r for r in config["roleAssignments"]}
    for r in sorted(set(bundle.roles) - set(ra)):
        errs.append(f"ruolo {r}: nessuna assegnazione")
    for r, a in ra.items():
        if r not in bundle.roles:
            errs.append(f"ruolo sconosciuto {r}")
        for pid in a.get("personas", []):
            if pid not in personas:
                errs.append(f"ruolo {r}: persona sconosciuta {pid}")
            elif personas[pid]["kind"] != "human":
                errs.append(f"ruolo {r}: {personas[pid]['name']} è un avatar; i ruoli del processo si assegnano a persone umane")
    policy = config.get("policy", {})
    if policy.get("requireHumanApprovers", True) or policy.get("requireHumanAccountable", True):
        for r, reasons in roles_needing_human(bundle).items():
            a = ra.get(r)
            name = bundle.roles[r]["name"]
            if a is None:
                continue
            if a["mode"] == "agent":
                errs.append(f"ruolo {name}: {reasons[0]}, quindi non può essere svolto solo da agenti")
            elif not a.get("personas"):
                errs.append(f"ruolo {name}: {reasons[0]}, serve almeno una persona umana assegnata")

    # Slot agenti
    sa = {s["slot"]: s for s in config["slotAssignments"]}
    for s in sorted(set(bundle.agents) - set(sa)):
        errs.append(f"slot {s}: nessuna persona assegnata")
    for slot, s in sa.items():
        agent = bundle.agents.get(slot)
        if agent is None:
            errs.append(f"slot sconosciuto {slot}")
            continue
        p = personas.get(s["persona"])
        if p is None:
            errs.append(f"slot {slot}: persona sconosciuta {s['persona']}")
            continue
        if p["kind"] == "avatar":
            pr = presets.get(s.get("preset", ""))
            if pr is None:
                errs.append(f"slot {slot}: l'avatar {p['name']} richiede un preset di agente")
            elif pr["kind"] != "llm-agent":
                errs.append(f"slot {slot}: il preset {pr['id']} non è un agente eseguibile dalla piattaforma")
        for c in s.get("connectors", []):
            if c not in connectors:
                errs.append(f"slot {slot}: connettore sconosciuto {c}")
        task_ids = {t["id"] for t in agent.get("scheduledTasks", [])}
        for tid, ov in s.get("taskOverrides", {}).items():
            if tid not in task_ids:
                errs.append(f"slot {slot}: compito sconosciuto {tid}")
            if "cron" in ov and not cron_is_valid(ov["cron"]):
                errs.append(f"slot {slot}: cron non valido per {tid}: {ov['cron']}")

    # Revisione da famiglia di modelli diversa. Contano tutte le famiglie che lo slot può usare:
    # il runner passa al modello di riserva se il principale non risponde.
    if policy.get("crossFamilyReview"):
        def slot_families(slot: str) -> set[str]:
            s = sa.get(slot)
            if not s or personas.get(s["persona"], {}).get("kind") != "avatar":
                return set()
            pr = presets.get(s.get("preset", ""))
            if not pr:
                return set()
            return {families[pr[k]] for k in ("model", "fallbackModel") if pr.get(k) in families}

        for a in bundle.agents.values():
            rb = a.get("reviewedBy")
            if rb:
                shared = slot_families(a["id"]) & slot_families(rb)
                if shared:
                    errs.append(f"slot {a['id']}: il revisore {rb} usa la stessa famiglia di modelli ({', '.join(sorted(shared))}), "
                                "contando anche i modelli di riserva")
    return errs


def validate_bundle(bundle: Bundle, config: dict[str, Any], schemas: dict[str, dict[str, Any]],
                    llm_catalog: dict[str, Any]) -> list[str]:
    errs = validate_process_and_topology(bundle, schemas)
    return errs if errs else validate_config(bundle, config, schemas, llm_catalog)
