# Ananke

Ananke è la piattaforma che orchestra persone e agenti AI lungo il ciclo di vita del software. Un progetto segue un modello di processo (waterfall o Scrum). Ogni fase ha una matrice RACI e ogni responsabile è una **persona**: un umano oppure un **avatar** composto da uno o più agenti. Gli agenti lavorano solo su **compiti pianificati con cron**. Le persone umane approvano i gate.

## Stato del progetto

Scheletro funzionante: avvio con Docker, console e configurazione web, validazione dei modelli, worker cron, agenti in modalità simulata o reale tramite LiteLLM. Le fasi successive sono in `docs/roadmap.md`: lavora sempre sulla prima fase non completata, salvo diversa richiesta.

## Mappa del repository

- `models/schemas/`: JSON Schema v1.1 di processo, topologia agenti e configurazione
- `models/waterfall/`, `models/scrum/`: istanze `*.process.json`, `*.agents.json`, `*.config.json` (fonte di verità)
- `backend/app/`: FastAPI (`main.py`), regole di governance (`validation.py`), viste RACI (`views.py`), logica condivisa (`services.py`), cron (`scheduling.py`, `worker.py`), esecuzione agenti LangGraph (`agents/runner.py`)
- `frontend/src/`: React 19 + TypeScript, pagine `Console` e `Config`
- `gateway/litellm.config.yaml`: alias dei modelli usati dagli agenti
- `docs/`: architettura, decisioni, roadmap, modello dati, licenze, mockup di riferimento

## Comandi

- Avvio completo: `docker compose up --build`, poi apri http://localhost:8080
- Con modelli reali: `LLM_MODE=live` in `.env`, poi `docker compose --profile live up --build`
- Test backend: `cd backend && python -m pytest -q`
- Validazione modelli: `python scripts/validate_models.py`
- Frontend in sviluppo: `cd frontend && npm run dev` (proxy verso http://localhost:8000)
- Typecheck e build frontend: `cd frontend && npm run build`

## Regole non negoziabili

1. **Licenze**: si incorporano solo dipendenze Apache-2.0 o MIT. BSD e PostgreSQL License sono ammesse come permissive equivalenti, ma vanno dichiarate in `docs/licenze.md`. GPL, AGPL e LGPL si usano solo come servizi esterni raggiunti via API. Prima di aggiungere qualunque dipendenza usa la skill `/licenza`.
2. **Governance**: chi approva un gate o è Accountable deve essere coperto da una persona umana. Chi revisiona usa una famiglia di modelli diversa da chi produce. Queste regole vivono in `backend/app/validation.py` e nei test: non vanno indebolite né aggirate. Se una richiesta lo implica, fermati e chiedi.
3. **Niente architettura a eventi**: tutto gira su cron (APScheduler) e polling. Le decisioni umane si registrano subito, ma le applica il Coordinatore alla sua esecuzione pianificata. Non introdurre bus di messaggi, webhook in ingresso o trigger a eventi senza una decisione esplicita in `docs/decisioni.md`.
4. **I modelli JSON sono la fonte di verità**: processo, ruoli, compiti standard e assegnazioni non si cablano nel codice. Dopo ogni modifica a `models/` esegui la validazione. Tieni allineate waterfall e Scrum.
5. **Gli agenti chiamano i modelli solo tramite il gateway**, usando gli alias dei preset. Non chiamare gli SDK dei provider dal codice degli agenti.
6. **La modalità mock deve restare funzionante**: `docker compose up` deve partire senza chiavi API.
7. **Lingua**: interfaccia, messaggi di errore e documentazione in italiano. Codice, identificativi e commit in inglese.

## Come lavorare

- Per modifiche che toccano più file usa la modalità piano e mostra il piano prima di scrivere.
- Scrivi o aggiorna i test insieme al codice. Una fase è finita solo quando passano `pytest`, la validazione dei modelli e `npm run build`.
- Aggiorna `docs/roadmap.md` (spunta la fase) e `docs/decisioni.md` (se hai preso una decisione) alla fine di ogni fase.
- Il mockup approvato è in `docs/mockup/`: la UI deve restarne coerente nell'aspetto e nei flussi.

Decisioni già prese:
@docs/decisioni.md
