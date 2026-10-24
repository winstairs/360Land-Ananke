"""Viste per la console: stadi del progetto, matrice RACI a livello di persone, dettaglio di una persona."""
from __future__ import annotations

from typing import Any

from .catalog import Bundle
from .scheduling import effective_tasks, next_fire, stage_is_active

LETTERS = [("R", "Responsabile"), ("A", "Approva e risponde"), ("C", "Consultato"), ("I", "Informato")]


def persona_card(p: dict[str, Any]) -> dict[str, Any]:
    return {"id": p["id"], "kind": p["kind"], "name": p["name"], "title": p.get("title", ""), "face": p.get("face", {})}


def stage_list(bundle: Bundle, project: dict[str, Any]) -> list[dict[str, Any]]:
    order = list(bundle.stages)
    cur = order.index(project["current_stage"]) if project["current_stage"] in order else 0
    out = []
    for i, (sid, st) in enumerate(bundle.stages.items()):
        status = "active" if i == cur else ("done" if i < cur else "future")
        if st.get("continuous") and i != cur:
            status = "continuous"
        out.append({"id": sid, "name": st["name"], "kind": st["kind"], "status": status,
                    "timebox": st.get("timebox"), "iterative": st.get("iterative", False),
                    "gate": st.get("gate", {}).get("name")})
    return out


def raci_view(bundle: Bundle, config: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    stage = bundle.stages[stage_id]
    personas = {p["id"]: p for p in config["personas"]}
    ra = {r["role"]: r for r in config["roleAssignments"]}
    sa = {s["slot"]: s for s in config["slotAssignments"]}

    letter_roles: dict[str, list[str]] = {"R": [], "A": [], "C": [], "I": []}
    for ac in stage["activities"]:
        r = ac["raci"]
        for L, roles in (("R", r["R"]), ("A", [r["A"]]), ("C", r.get("C", [])), ("I", r.get("I", []))):
            for role in roles:
                if role not in letter_roles[L]:
                    letter_roles[L].append(role)

    columns: dict[str, dict[str, dict[str, Any]]] = {L: {} for L, _ in LETTERS}

    def add(L: str, pid: str, role_label: str | None = None, slot: str | None = None) -> None:
        p = personas.get(pid)
        if p is None:
            return
        entry = columns[L].setdefault(pid, {**persona_card(p), "roles": [], "slots": []})
        if role_label and role_label not in entry["roles"]:
            entry["roles"].append(role_label)
        if slot and slot not in entry["slots"]:
            entry["slots"].append(slot)

    # Persone umane dai ruoli del processo
    for L, roles in letter_roles.items():
        for role in roles:
            a = ra.get(role)
            if a and a["mode"] != "agent":
                for pid in a.get("personas", []):
                    add(L, pid, bundle.roles[role]["name"])
    # Avatar e persone che eseguono gli slot attivi in questo stadio
    for slot, agent in bundle.agents.items():
        in_stage = agent["stage"] == stage_id or (
            agent["stage"] is None and any(bundle.activity_stage.get(x) == stage_id for x in agent.get("activities", [])))
        if in_stage and slot in sa:
            add("R", sa[slot]["persona"], agent["name"], slot)
    # Chi è già R o A non si ripete tra i consultati e gli informati
    for later, earlier in (("C", ("R", "A")), ("I", ("R", "A", "C"))):
        for pid in [p for p in columns[later] if any(p in columns[e] for e in earlier)]:
            del columns[later][pid]
    return [{"letter": L, "label": label, "people": list(columns[L].values())} for L, label in LETTERS]


def persona_detail(bundle: Bundle, config: dict[str, Any], project: dict[str, Any], persona_id: str) -> dict[str, Any]:
    personas = {p["id"]: p for p in config["personas"]}
    p = personas[persona_id]
    presets = {x["id"]: x for x in config["agentPresets"]}
    sa = {s["slot"]: s for s in config["slotAssignments"]}
    tasks_by_slot: dict[str, list[dict[str, Any]]] = {}
    for t in effective_tasks(bundle, config):
        if t.persona_id != persona_id:
            continue
        active = stage_is_active(bundle, t.stage, project["current_stage"])
        nf = next_fire(t.cron) if (t.enabled and active) else None
        tasks_by_slot.setdefault(t.slot, []).append({
            "id": t.task_id, "name": t.name, "cron": t.cron, "enabled": t.enabled, "action": t.action,
            "activeInCurrentStage": active, "nextRun": nf.isoformat() if nf else None})
    slots = []
    for slot, tasks in tasks_by_slot.items():
        agent = bundle.agents[slot]
        s = sa[slot]
        pr = presets.get(s.get("preset", ""), {})
        slots.append({
            "slot": slot, "agentName": s.get("agentName", agent["name"]),
            "stage": agent["stage"], "stageName": bundle.stages[agent["stage"]]["name"] if agent["stage"] else "Supervisione",
            "preset": pr.get("id"), "presetName": pr.get("name"), "model": pr.get("model"),
            "autonomy": s.get("autonomy", agent["autonomy"]), "responsibilities": agent["responsibilities"], "tasks": tasks})
    roles = [bundle.roles[r["role"]]["name"] for r in config["roleAssignments"] if persona_id in r.get("personas", [])]
    gate = bundle.stages[project["current_stage"]].get("gate")
    approves_now = False
    if gate and p["kind"] == "human":
        ra = {r["role"]: r for r in config["roleAssignments"]}
        approves_now = any(persona_id in ra.get(role, {}).get("personas", []) for role in gate["approvers"])
    return {**persona_card(p), "email": p.get("email"), "delegates": p.get("delegates", []),
            "processRoles": roles, "slots": slots, "approvesCurrentGate": approves_now}


def gate_view(bundle: Bundle, config: dict[str, Any], project: dict[str, Any]) -> dict[str, Any] | None:
    st = bundle.stages[project["current_stage"]]
    gate = st.get("gate")
    if not gate:
        return None
    personas = {p["id"]: p for p in config["personas"]}
    ra = {r["role"]: r for r in config["roleAssignments"]}
    approvers = []
    for role in gate["approvers"]:
        for pid in ra.get(role, {}).get("personas", []):
            if pid in personas:
                approvers.append({**persona_card(personas[pid]), "role": bundle.roles[role]["name"]})
    targets = [{"id": t["to"], "name": bundle.stages[t["to"]]["name"]} for t in bundle.transitions_from(st["id"], "gate_approved")]
    return {"stage": st["id"], "stageName": st["name"], "id": gate["id"], "name": gate["name"],
            "criteria": gate["criteria"], "approvers": approvers, "targets": targets}
