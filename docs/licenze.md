# Licenze

Politica: dipendenze incorporate solo Apache-2.0 o MIT; BSD, ISC e PostgreSQL License ammesse come permissive e dichiarate qui; copyleft solo come servizi esterni. Verifica fatta il 2026-10-19 sui metadati dei pacchetti installati.

## Backend (dipendenze dirette)

| Pacchetto | Versione | Licenza |
| --- | --- | --- |
| fastapi | 0.149.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause (permissiva, dichiarata) |
| SQLAlchemy | 2.1.5 | MIT |
| asyncpg | 0.32.0 | Apache-2.0 |
| aiosqlite | 0.22.1 | MIT |
| jsonschema | 4.26.0 | MIT |
| APScheduler | 3.11.3 | MIT |
| langgraph | 1.2.16 | MIT |
| openai | 3.35.1 | Apache-2.0 |
| pytest (sviluppo) | 9.1.1 | MIT |
| httpx (diretta: sincronizzazione del gateway; anche transitiva di openai) | 0.28.1 | BSD-3-Clause (permissiva, dichiarata). Porta httpcore e idna (BSD-3-Clause), h11 e anyio (MIT), certifi (MPL-2.0, vedi decisioni aperte) |
| anyio (sviluppo) | 4.15.1 | MIT |

Transitive con licenza da decidere (MPL-2.0, copyleft debole a livello di file, usate senza modifiche): `certifi` (da httpx e openai), `orjson` (da langgraph-sdk e langsmith). Vedi le decisioni aperte.

## Frontend

| Pacchetto | Licenza |
| --- | --- |
| react, react-dom | MIT |
| vite, @vitejs/plugin-react | MIT |
| typescript | Apache-2.0 |
| @types/react, @types/react-dom | MIT |

Transitive: 17 MIT, 2 Apache-2.0, 1 ISC, 1 BSD-3-Clause, 2 MPL-2.0 (`lightningcss`, usato solo in fase di build da Vite e non distribuito nell'applicazione).

## Servizi e immagini

| Componente | Licenza | Uso |
| --- | --- | --- |
| PostgreSQL (`postgres:17-alpine`) | PostgreSQL License | servizio |
| Python (`python:3.12-slim`) | PSF | runtime |
| Node.js (`node:22-alpine`) | MIT | solo build |
| nginx (`nginx:stable-alpine`) | BSD-2-Clause | servizio |
| LiteLLM Proxy | MIT, esclusa la cartella `enterprise` (commerciale, non usata). Funzioni usate: `store_model_in_db`, `/model/new`, `/model/delete`, `/model/info`, tutte nel core MIT (verificato il 2026-10-19). Non usare modelli di team, auto-router né altre funzioni riservate a `premium_user`; non impostare `LITELLM_LICENSE` | servizio |
| Prisma (client Python e motori, dentro l'immagine LiteLLM) | Apache-2.0 | interno al servizio gateway, richiesto da `store_model_in_db` |
| psycopg (dentro l'immagine LiteLLM, extra `proxy`) | LGPL-3.0 | solo dentro il servizio gateway, non incorporato in Ananke |
| Ollama | MIT | servizio opzionale |
| Pesi dei modelli open | per modello | verificare sulla model card prima dell'uso |
| Jira, Confluence, ClickUp, Google Drive | servizi commerciali | solo tramite connettori |
| Plane (AGPL-3.0), OpenProject (GPLv3) | copyleft | solo come servizi esterni |
