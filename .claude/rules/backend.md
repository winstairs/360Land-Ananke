---
paths:
  - "backend/**/*.py"
---

# Backend

- Python 3.12, FastAPI, SQLAlchemy 2 Core in modalità async (`asyncpg` in produzione, `aiosqlite` nei test). Niente ORM dichiarativo: le tabelle sono in `app/db.py`.
- La logica condivisa tra API e worker sta in `app/services.py`. Le rotte in `app/main.py` restano sottili.
- Ogni nuova regola sui modelli va in `app/validation.py`, con messaggio in italiano comprensibile all'utente e un test in `tests/test_models.py`.
- I compiti degli agenti passano da `services.queue_run` ed `execute_run`. L'esecuzione LLM sta solo in `app/agents/`.
- I timestamp si salvano in UTC. La conversione al fuso dell'utente si fa in output.
- Test con pytest e `anyio`: database SQLite temporaneo configurato in `tests/conftest.py`, `LLM_MODE=mock`.
- Nessuna nuova dipendenza in `requirements.txt` senza la skill `/licenza`.
