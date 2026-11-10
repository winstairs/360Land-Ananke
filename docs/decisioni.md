# Decisioni

Registro delle decisioni di progetto. Ogni voce: data, decisione, motivo. Le decisioni aperte sono in fondo.

| Data | Decisione | Motivo |
| --- | --- | --- |
| 2026-10-19 | Il prodotto si chiama **Ananke** | Nome scelto dal committente |
| 2026-10-19 | Il processo è descritto da modelli JSON con schema (processo, topologia agenti, configurazione), per waterfall e Scrum | Una sola fonte di verità per GUI, orchestrazione e validazione |
| 2026-10-19 | Ogni fase ha un orchestratore che coordina agenti specialisti; un supervisore agentico (PM Office per il waterfall, Agile Office per Scrum) governa le transizioni | Separare il lavoro di fase dal controllo del processo |
| 2026-10-19 | I ruoli si assegnano a **persone** di un catalogo: umani o avatar composti da agenti. La persona di un ruolo si può cambiare dalla configurazione | Rendere sostituibile chi svolge un ruolo senza toccare il processo |
| 2026-10-19 | Approvatori di gate e ruoli Accountable restano sempre a persone umane; la regola è nel validatore | Responsabilità finale umana |
| 2026-10-19 | Chi revisiona usa una famiglia di modelli diversa da chi produce (`crossFamilyReview`) | Evitare che un modello approvi i propri errori |
| 2026-10-19 | Gli agenti lavorano solo su compiti pianificati con cron; nessuna architettura a eventi. Le richieste manuali «Esegui ora» e le decisioni umane si leggono a intervalli | Scelta di prodotto: comportamento prevedibile e ispezionabile |
| 2026-10-19 | Scrum: lo Scrum Master non è Accountable di nessuna attività; le responsabilità finali sono di Product Owner e tech lead, così lo Scrum Master può essere un avatar | Rispettare la regola sugli approvatori umani |
| 2026-10-19 | Componenti incorporati solo Apache-2.0 o MIT (BSD e PostgreSQL License ammesse e dichiarate); copyleft solo come servizi esterni | Vincolo di licenza del progetto |
| 2026-10-19 | Stack: FastAPI, SQLAlchemy async, APScheduler, LangGraph, LiteLLM come gateway, PostgreSQL, React + Vite | Licenze compatibili e maturità |
| 2026-10-19 | Il bus di eventi NATS previsto nell'architettura iniziale non è incluso | Superfluo con un modello solo cron |
| 2026-10-19 | Gli agenti accedono ai connettori come utente tecnico dedicato | Azioni attribuibili all'agente nell'audit, permessi limitati |
| 2026-10-19 | Work tracker di riferimento: Jira (via Rovo MCP); repository: GitHub | Strumenti già in uso |
| 2026-10-19 | Pilota dell'MVP sulla fase Requisiti | Solo documenti: collauda orchestrazione e gate senza accesso a codice o produzione |
| 2026-10-19 | Modalità `mock` di default: lo stack parte senza chiavi API | Demo e sviluppo senza costi |
| 2026-10-19 | Demo locali con Qwen3.6 35B-A3B su Ollama; vLLM su GPU dedicate rimandato a dopo il pilota | Hardware disponibile (GPU da 12 GB) e dati reali per il dimensionamento |
| 2026-10-19 | Gli avatar possono avere un'email: è l'utente tecnico con cui i loro agenti accedono ai connettori | Rendere configurabile l'identità prevista dalla decisione sull'utente tecnico |
| 2026-10-19 | Provider e modelli LLM stanno in un catalogo unico di piattaforma (`models/platform/llm-catalog.json`), modificabile dalla GUI; la configurazione delle metodologie passa allo schema 1.2 senza `llmProviders` | Il gateway è unico: due copie per metodologia divergevano, e le famiglie usate dalla regola cross-family devono corrispondere ai modelli reali |
| 2026-10-19 | Il worker sincronizza a cron il gateway LiteLLM con il catalogo tramite l'API di gestione modelli; LiteLLM salva i modelli in un database `litellm` sullo stesso Postgres | Modelli configurabili dalla GUI senza riavvii né eventi; il file del gateway non è più la fonte |
| 2026-10-19 | Le chiavi dei provider stanno solo nelle variabili d'ambiente del gateway; il catalogo ne indica il nome | Nessun segreto nel database o nelle API di Ananke, che non ha ancora autenticazione |
| 2026-10-19 | Il modello di riserva dei preset (`fallbackModel`) è gestito dal runner, non dal router del gateway | Il fallback segue la configurazione di ogni preset |
| 2026-11-09 | Due modalità di deploy con compose sovrapponibili: **standalone** (`docker-compose.yml`, solo Ananke, default) ed **ecosistema** (`docker-compose.ecosystem.yml`, Ananke più i servizi collegati) | Demo e sviluppo restano leggeri e senza chiavi; l'ecosistema completo si definisce senza toccare lo standalone |
| 2026-11-10 | Artefatti, revisioni e pacchetti di evidenze stanno in tabelle dedicate (`artifacts`, `reviews`, `evidence_packs`), solo inserimenti. La revisione è registrata quando gira il compito dell'agente `reviewedBy` (cron); il pacchetto di evidenze del gatekeeper è informativo per chi approva e non blocca il gate, che resta una decisione umana | Nessun evento: revisione e gatekeeper seguono i compiti pianificati; responsabilità finale umana |

## Decisioni aperte

- [ ] **Servizi dell'ecosistema**: quali includere in `docker-compose.ecosystem.yml` (work tracker, repository, osservabilità, ecc.). Oggi il file è uno scheletro senza servizi.
- [ ] **OpenProject come opzione di work tracker**: da aggiungere a connettori e configurazione (GPLv3, solo come servizio esterno; MCP ufficiale solo nell'edizione Enterprise, per la Community esiste `openproject-ce-mcp` con licenza MIT).
- [ ] **Persistenza dei grafi LangGraph**: il checkpointer PostgreSQL ufficiale usa `psycopg` (LGPL-3.0). Alternative: accettarlo come libreria non modificata, oppure scrivere un checkpointer su `asyncpg` (Apache-2.0).
- [ ] **Dipendenze transitive MPL-2.0**: `certifi` e `orjson` (backend), `lightningcss` (solo strumento di build del frontend). Copyleft debole a livello di file, usate senza modifiche: confermare se accettabili.
- [ ] **Identità e autenticazione**: fuori ambito per ora; i connettori ufficiali (ClickUp, Google Drive, Rovo A2A) richiedono OAuth.
- [ ] **Osservabilità**: Langfuse self-hosted (MIT, escluse le cartelle `/ee`) richiede ClickHouse, Redis e storage S3: valutare se introdurlo nella fase 4.
