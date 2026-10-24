#!/usr/bin/env python3
"""Valida tutti i modelli in models/ (schema, riferimenti, regole di governance).

Uso: python scripts/validate_models.py   (dalla radice del repository)
Esce con codice 1 se trova errori.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.catalog import Catalog  # noqa: E402
from app.validation import validate_bundle, validate_llm_catalog  # noqa: E402


def main() -> int:
    cat = Catalog.load(ROOT / "models")
    llm_errs = validate_llm_catalog(cat.llm_catalog, cat.schemas)
    providers = cat.llm_catalog.get("providers", [])
    status = "OK" if not llm_errs else f"{len(llm_errs)} errori"
    print(f"catalogo LLM: {len(providers)} provider, {sum(len(p['models']) for p in providers)} modelli -> {status}")
    for e in llm_errs:
        print(f"  - {e}")
    failed = bool(llm_errs)
    for name, bundle in cat.bundles.items():
        errs = validate_bundle(bundle, bundle.default_config, cat.schemas, cat.llm_catalog)
        tasks = sum(len(a.get("scheduledTasks", [])) for a in bundle.agents.values())
        status = "OK" if not errs else f"{len(errs)} errori"
        print(f"{name}: {len(bundle.stages)} stadi, {len(bundle.agents)} slot agente, {tasks} compiti pianificati -> {status}")
        for e in errs:
            print(f"  - {e}")
        failed |= bool(errs)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
