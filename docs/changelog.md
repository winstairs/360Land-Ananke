# Changelog

Registro delle modifiche da passare al Claude che lavora sul prodotto. Ogni voce: data, cosa è cambiato, file toccati, cosa deve fare chi riprende il lavoro.

## 2026-10-25

### Scheda «Connettori»: «Strumenti per fase» e popup di configurazione dei connettori

- **Cosa**:
  - La scheda «Strumenti esterni» di Configurazione si chiama ora **«Connettori»**.
  - La card «Collegamenti» è spostata in alto e si chiama **«Strumenti per fase»**: in testa il connettore per ogni funzione (gestione del lavoro, documentazione, archivio file, codice), sotto la destinazione di ogni artefatto **raggruppata per la fase che lo produce** (`stage.outputs` del processo; gli artefatti non prodotti da nessuna fase finiscono in «Altri artefatti»).
  - La card «Strumenti esterni» diventa **«Connettori»**: righe compatte con «Configura» e «Rimuovi». Il dettaglio espandibile è sostituito da un **popup modale** (`<dialog>` nativo) che lavora su una bozza e modifica la configurazione solo con «Applica»; resta poi da premere «Salva configurazione».
  - Nel popup si sceglie tra **Connettore standard (API REST)** e **Server MCP**, con sotto-scelta remoto (HTTP) o locale (processo avviato dal worker). I campi cambiano per strumento e modalità:
    - *Jira / Confluence*: REST con URL del sito, Cloud o Data Center, versione API, autenticazione email + API token, PAT Data Center oppure OAuth 2.0; MCP remoto Rovo con sito Atlassian, OAuth 2.1 o API token; MCP locale `uvx mcp-atlassian`. Ambito: chiave del progetto, tipo di issue, filtro JQL / chiave dello spazio, pagina padre;
    - *ClickUp*: REST con token personale o OAuth; MCP remoto solo OAuth. Ambito: workspace, space, lista;
    - *Plane*: REST con chiave API (`X-API-Key`); MCP locale `@makeplane/plane-mcp-server`. Ambito: workspace, progetto;
    - *Google Drive*: REST con service account con delega di dominio (utente da impersonare, ambito `drive.file` o `drive`) o OAuth; MCP remoto OAuth. Ambito: drive condiviso, cartella radice;
    - *GitHub*: REST con GitHub App (App ID, Installation ID, chiave privata) o token fine-grained; MCP remoto con toolset e OAuth o token; MCP locale in container `ghcr.io/github/github-mcp-server`. Ambito: organizzazione, repository, branch;
    - *GitLab*, *Slack*, *Altro*: parametri equivalenti (token, OAuth, canali, intestazione della chiave API…);
    - per MCP remoto anche strumenti consentiti e timeout; per MCP locale comando, argomenti e nomi delle variabili d'ambiente passate al processo.
  - **Nessun segreto salvato**: i campi delle credenziali contengono solo il nome della variabile d'ambiente. La regola è anche nel validatore.
  - **Schema** (compatibile, resta 1.2): nuova proprietà opzionale `connector.settings`. I connettori di default di waterfall e Scrum hanno ora `settings` valorizzati con segnaposto (`azienda`, `ANANKE`) e GitHub ha l'endpoint MCP ufficiale.
  - **Validazione** (`validation.py`): id di connettori unici; in `settings` rifiutate le chiavi di segreti (`token`, `password`, `secret`, `apiKey`, `clientSecret`, `privateKey`, `accessToken`); le chiavi `*Env` e `envVars` devono essere nomi di variabili d'ambiente e non usare i prefissi riservati della piattaforma. Le regole di governance non sono state toccate.
- **File**:
  - backend: `app/validation.py`, `tests/test_models.py` (4 test nuovi);
  - modelli: `models/schemas/platform-config.schema.json`, `models/waterfall/waterfall.config.json`, `models/scrum/scrum.config.json`;
  - frontend: `src/connectorSpecs.ts` (nuovo), `src/components/ConnectorDialog.tsx` (nuovo), `src/pages/Config.tsx`, `src/types.ts`, `src/styles.css`;
  - documentazione: `docs/architettura.md`, `docs/modello-dati.md`.
- **Verifica**: `pytest` 33/33, `validate_models.py` OK su catalogo, waterfall e Scrum, `npm run build` OK. Prova nel browser sullo stack Docker: ordine e nomi delle card, popup su Jira con passaggio MCP ↔ REST, errori inline sui campi obbligatori di GitHub App, chiusura con Esc.
- **Per chi riprende**:
  - I parametri per strumento sono dichiarati in `frontend/src/connectorSpecs.ts`: per un nuovo strumento aggiungi lì la voce e il valore all'enum `system` dello schema.
  - Nella fase 2 il runner dovrà leggere `connector.transport` e `connector.settings` (ambito e nome delle variabili delle credenziali) e rispettare `readOnly`. Il flusso OAuth resta una decisione aperta («Identità e autenticazione»).
  - Le configurazioni salvate prima di questa modifica non hanno `settings`: il popup propone i default dello strumento alla prima apertura.
  - Gli URL dei server MCP proposti di default (Rovo, ClickUp, GitHub, Google Drive, GitLab, Slack) vanno verificati al momento del collaudo dei connettori.

## 2026-10-19

### Documentazione dell'architettura riscritta

- **Cosa**: `docs/architettura.md` passa da una sintesi a una descrizione completa di ciò che è implementato. Contiene principi, servizi Docker e variabili d'ambiente, modelli JSON e configurazione versionata, moduli del backend, tabelle, API, viste RACI, regole di validazione, pianificazione e worker, grafo LangGraph, gate e timebox, gateway, frontend, flussi end-to-end e limiti noti.
- **File**: `docs/architettura.md`. Nessuna modifica al codice o ai modelli.
- **Per chi riprende**: leggi la sezione 9 «Limiti noti e punti aperti» prima di iniziare la fase 1. Elenca i campi dei modelli validati ma non usati a runtime (`consumes`/`produces`, `reviewedBy`, connettori, autonomia, `maxIterations`, `fallbackModel`). Segnala inoltre due rischi da valutare:
  - il runner scarta il prefisso del provider, quindi la famiglia dichiarata in `llmProviders` può non coincidere con il modello reale dietro l'alias del gateway, e il controllo cross-family si basa sulla dichiarazione;
  - il passaggio `queued` → `running` dei run non è atomico.

  Aggiorna `docs/architettura.md` alla fine di ogni fase.

### Email per gli avatar, colori umani/avatar, scheda «Strumenti esterni»

- **Cosa**:
  - **Email anche per gli avatar.** Rappresenta l'utente tecnico con cui gli agenti dell'avatar accedono ai connettori, coerente con la decisione «Gli agenti accedono ai connettori come utente tecnico dedicato». È stata rimossa la regola di validazione «un avatar non ha email». Al suo posto c'è un controllo di formato che vale per tutte le persone. Le regole di governance protette (approvatori e Accountable umani, revisione cross-family) non sono state toccate.
  - **Card della scheda «Persone e avatar» distinguibili a colpo d'occhio.** Gli umani hanno fondo blu tenue (`--accent-soft`) e bordo pieno, gli avatar fondo verde tenue (`--avatar-soft`) e bordo tratteggiato. Le persone umane sono elencate per prime.
  - **Nuova scheda «Strumenti esterni» in Configurazione.** Permette di aggiungere, modificare e rimuovere i connettori: nome, sistema, uso, collegamento MCP/REST, endpoint, maturità, sola lettura, note. Permette anche di scegliere i collegamenti: quale strumento per gestione del lavoro, documentazione, file e codice, e dove vive ogni artefatto. Le credenziali non si salvano: l'autenticazione resta una decisione aperta.
- **File**:
  - `backend/app/validation.py`, `backend/tests/test_models.py` (2 test nuovi);
  - `models/schemas/platform-config.schema.json` (solo la descrizione di `persona.email`, compatibile);
  - `frontend/src/pages/Config.tsx`, `frontend/src/types.ts`, `frontend/src/styles.css`;
  - `docs/modello-dati.md`, `docs/architettura.md`.
- **Verifica**: `pytest` 13/13, `validate_models.py` OK su waterfall e Scrum, `npm run build` OK.
- **Per chi riprende**:
  - Le email degli avatar nei file di configurazione di default non sono ancora valorizzate.
  - Nella fase 2, quando il runner userà i connettori, usa `persona.email` come identità dell'utente tecnico e rispetta `connector.readOnly`.
  - La rimozione di un connettore ancora usato non è bloccata dalla GUI: la segnala la validazione lato server.

### Configurazione dei modelli AI dalla GUI (catalogo LLM di piattaforma)

- **Cosa**:
  - **Nuovo catalogo LLM unico di piattaforma**: `models/platform/llm-catalog.json`, con schema `llm-catalog.schema.json` 1.0. Contiene provider cloud (Claude, OpenAI, API compatibili) e self-hosted (vLLM, ad esempio su Hetzner, e Ollama), ciascuno con indirizzo e **nome** della variabile della chiave, più i modelli con alias, id presso il provider e famiglia. Di default sono attivi Claude e Ollama locale; OpenAI, il server GPU Hetzner e il provider cloud compatibile sono esempi disattivati.
  - **Schema di configurazione 1.2**: rimosso `llmProviders` dalle configurazioni di waterfall e Scrum. I preset puntano ora a `anthropic/...` e `ollama-local/...`. Le versioni salvate con lo schema 1.1 vengono migrate in lettura (`services.upgrade_config`).
  - **Validazione**: le famiglie per la regola cross-family si leggono dal catalogo; i preset devono puntare a modelli attivi; gli alias devono essere unici. Un catalogo si salva solo se tutte le metodologie restano valide. La regola cross-family è invariata nella logica.
  - **Gateway sincronizzato dal worker** con il nuovo job `sync-gateway`, attivo solo in modalità live, tramite l'API di gestione modelli di LiteLLM (`/model/info`, `/model/new`, `/model/delete`):
    - LiteLLM salva i modelli nel database `litellm` sullo stesso Postgres, creato dal servizio `gateway-db-init`;
    - `gateway/litellm.config.yaml` non contiene più modelli né fallback;
    - le chiavi arrivano al gateway dal file `.env` (`env_file`).
  - **Modello di riserva nel runner**: se il modello del preset fallisce, il runner riprova sul `fallbackModel`. Prima questo campo era ignorato.
  - **API nuove**: `GET/PUT /api/llm/catalog`, `POST /api/llm/catalog/validate`, `GET /api/llm/gateway-status`.
  - **GUI**: nuova scheda «Modelli AI» in Configurazione con:
    - editor di provider e modelli, condiviso tra le metodologie e con il proprio salvataggio. «Nuovo provider» offre modelli già compilati: Claude, OpenAI, server proprio con vLLM come Hetzner, Ollama, API compatibile OpenAI;
    - preset degli agenti della metodologia: modello, modello di riserva, temperatura;
    - stato della sincronizzazione del gateway.
  - **Dipendenze**: `httpx==0.28.1` diventa dipendenza diretta. È BSD-3-Clause ed era già transitiva di `openai`.
- **File**:
  - backend: `app/catalog.py`, `app/validation.py`, `app/services.py`, `app/gateway.py` (nuovo), `app/worker.py`, `app/main.py`, `app/db.py` (tabelle `llm_catalog_versions` e `gateway_syncs`), `app/settings.py` (`LLM_ADMIN_URL`), `app/agents/runner.py`, `requirements.txt`, test in `tests/test_models.py`, `tests/test_gateway.py` (nuovo) e `tests/test_api.py`;
  - modelli: `models/schemas/llm-catalog.schema.json`, `models/platform/llm-catalog.json`, `models/schemas/platform-config.schema.json`, `models/*/*.config.json`;
  - infrastruttura: `scripts/validate_models.py`, `gateway/litellm.config.yaml`, `docker-compose.yml`, `.env.example`;
  - frontend: `frontend/src/pages/LlmCatalogEditor.tsx` (nuovo), `pages/Config.tsx`, `types.ts`, `api.ts`, `styles.css`;
  - documentazione: `docs/architettura.md`, `docs/modello-dati.md`, `docs/sviluppo.md`, `docs/decisioni.md`, `docs/licenze.md`.
- **Verifica**:
  - `pytest` 27/27, `validate_models.py` OK (catalogo, waterfall, Scrum), `npm run build` OK;
  - prova reale contro LiteLLM `main-stable`: prima sincronizzazione con 7 modelli pubblicati, seconda «allineato»; con un modello cambiato e un provider disattivato vengono rimossi e ripubblicati quelli giusti; i marcatori `ananke_managed` e l'hash restano nel gateway.
- **Per chi riprende**:
  - Una chiave nuova va scritta in `.env` e richiede il riavvio del gateway.
  - Gli alias `oss-*` girano oggi tutti su Qwen3.6 (famiglia `qwen`): quando arriverà vLLM su GPU dedicate, aggiorna il catalogo e non il file del gateway.
  - Il `governance-reviewer` ha segnalato un punto preesistente, non introdotto qui, da decidere con il committente: `policy.requireHumanApprovers`, `requireHumanAccountable` e `crossFamilyReview` sono booleani impostabili a `false` dalla configurazione, quindi le regole si possono spegnere. Per chiuderlo servirebbero `"const": true` nello schema e un test.

### Correzioni dopo la revisione di governance del catalogo LLM

- **Cosa**:
  - **La revisione cross-family conta anche il modello di riserva.** Il runner ora usa davvero `fallbackModel`, quindi uno slot può girare su due famiglie: l'errore scatta se produttore e revisore ne condividono anche una sola.
  - **Configurazioni di default corrette.** Dai preset `claude-reasoning` e `claude-worker` è stata tolta la riserva `ollama-local/oss-generalist`, perché i revisori open usano la stessa famiglia `qwen`. La migrazione 1.1 → 1.2 toglie la stessa riserva dalle versioni salvate.
  - **Nomi delle variabili delle chiavi vincolati.** Devono finire con `_API_KEY`, `_KEY` o `_TOKEN` e non possono iniziare con `LITELLM_`, `POSTGRES_`, `DATABASE_`, `LLM_` o `PG`. Senza autenticazione, chiunque raggiunga l'API avrebbe potuto far inviare dal gateway la master key o la password del database a un indirizzo esterno.
  - **Controllo all'avvio dell'API.** Se il catalogo attivo rende invalida una configurazione salvata, viene scritto nel log.
  - **Dettaglio degli errori del gateway** troncato a 160 caratteri.
- **File**: `backend/app/validation.py`, `backend/app/services.py`, `backend/app/main.py`, `backend/app/gateway.py`, `backend/tests/test_models.py` (2 test nuovi), `models/*/*.config.json`, `docs/architettura.md`.
- **Verifica**: `pytest` 29/29, `validate_models.py` OK.
- **Per chi riprende**:
  - I preset Claude oggi non hanno un modello di riserva. Per dargliene uno serve una famiglia diversa sia da `claude` sia da quella dei revisori: per esempio `gpt-oss` sul server Hetzner, una volta attivato.
  - Il gateway riceve ancora tutto il file `.env`. Il vincolo sui nomi impedisce di usare quelle variabili come chiavi, ma passare al gateway solo le chiavi dei provider resta un miglioramento possibile.
  - Le licenze di Prisma e di psycopg (quest'ultimo LGPL, solo dentro il servizio gateway) sono state aggiunte a `docs/licenze.md`, insieme al vincolo di non usare funzioni enterprise di LiteLLM.
