---
paths:
  - "models/**/*.json"
---

# Modelli JSON

- Gli schemi in `models/schemas/` sono versionati nel campo `$id`. Una modifica incompatibile alza la versione e aggiorna tutte le istanze.
- Ogni modifica va applicata sia a waterfall sia a Scrum, quando ha senso per entrambi.
- Identificativi in kebab-case e in inglese. Nomi e descrizioni in italiano.
- I nomi dei compiti pianificati sono standard e legati al ruolo (es. «Verifica validità requisiti»): riusa quelli esistenti prima di crearne di nuovi.
- Dopo ogni modifica esegui `python scripts/validate_models.py`: deve terminare senza errori.
