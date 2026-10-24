---
name: prossima-fase
description: Implementa la prossima fase della roadmap in docs/roadmap.md, oppure la fase indicata.
argument-hint: "[numero-fase]"
disable-model-invocation: true
---

Implementa la fase $ARGUMENTS di `docs/roadmap.md`. Se non è indicata, usa la prima fase non spuntata.

1. Leggi la fase con obiettivo, attività e criteri di accettazione, poi rileggi CLAUDE.md e `docs/decisioni.md`.
2. Prepara un piano: file da creare o modificare, dipendenze nuove (ciascuna verificata con `/licenza`), test da scrivere, eventuali decisioni aperte. Mostra il piano e attendi conferma.
3. Implementa a piccoli passi, con i test insieme al codice.
4. Verifica: `python scripts/validate_models.py`, `cd backend && python -m pytest -q`, `cd frontend && npm run build`, e se la fase tocca Docker anche `docker compose up --build`.
5. Spunta i criteri soddisfatti in `docs/roadmap.md` e registra in `docs/decisioni.md` le decisioni prese.
6. Chiudi con un riepilogo: cosa è cambiato, come provarlo, cosa resta aperto.
