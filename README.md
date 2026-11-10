# Ananke

Ananke è una console per orchestrare persone e agenti AI lungo il ciclo di vita del software, con processi waterfall e Scrum. Ogni fase ha una matrice RACI. I responsabili sono persone umane o avatar composti da agenti, e gli agenti lavorano su compiti pianificati con cron. Le persone umane approvano i gate.

## Avvio rapido

Prerequisiti: Docker Desktop (o Docker Engine con Compose v2).

```bash
cp .env.example .env
docker compose up --build
```

Poi apri http://localhost:8080. L'API è su http://localhost:8000/docs.

Di default gli agenti girano in **modalità simulata**: non serve nessuna chiave e non parte nessuna chiamata ai modelli. Per i modelli reali vedi `docs/sviluppo.md`.

## Modalità di deploy

Ananke si può avviare in due modalità, con file compose sovrapponibili:

| Modalità | Cosa avvia | Comando |
| --- | --- | --- |
| **Standalone** (default) | Solo Ananke: database, API, worker, console web (più gateway e Ollama con i profili `live` e `local-llm`) | `docker compose up --build` |
| **Ecosistema** | Ananke più i servizi esterni a cui si collega (work tracker, repository, osservabilità...) | `docker compose -f docker-compose.yml -f docker-compose.ecosystem.yml up --build` |

Per usare sempre l'ecosistema senza ripetere i file, decommenta `COMPOSE_FILE` in `.env`. I profili `live` e `local-llm` si combinano con entrambe le modalità.

Usa lo **standalone** per demo, sviluppo e prove con agenti simulati: non servono chiavi né altri servizi. L'**ecosistema** serve per provare Ananke insieme agli strumenti con cui lavora.

> **Stato**: i servizi dell'ecosistema sono ancora da definire. Oggi `docker-compose.ecosystem.yml` è uno scheletro senza servizi, con le convenzioni da seguire; avviarlo equivale allo standalone. Le scelte aperte sono in `docs/decisioni.md`.

## Cosa puoi provare

1. **Console**: scegli un progetto dal menu, seleziona una fase e un responsabile, poi premi «Esegui ora» su un compito. Il worker lo esegue entro 30 secondi.
2. **Gate**: seleziona un approvatore umano della fase corrente (per esempio Laura B. nei requisiti del «Portale prenotazioni») e approva. Il Coordinatore applica la decisione alla sua esecuzione pianificata: ogni 30 minuti, dalle 8 alle 19 nei giorni feriali. Per provarlo subito, accorcia quel cron dalla configurazione.
3. **Configurazione**: cambia la persona di uno slot, modifica un cron o assegna un ruolo. La validazione è immediata e il salvataggio si blocca se violi una regola di governance, per esempio se assegni un approvatore solo ad agenti.

## Lavorare con Claude Code in VS Code

1. Installa VS Code (1.94 o successivo) e l'estensione **Claude Code** di Anthropic. VS Code la propone automaticamente all'apertura della cartella, insieme alle altre estensioni consigliate.
2. Apri la cartella del repository e accedi con il tuo account Claude. Se la cartella non è ancora un repository git, inizializzalo (`git init`, poi un primo commit): i revisori usano `git diff` per vedere le modifiche.
3. Claude Code legge automaticamente:
   - `CLAUDE.md`: contesto, comandi e regole non negoziabili;
   - `.claude/rules/`: regole specifiche per backend, frontend e modelli, caricate quando si lavora su quei file;
   - `.claude/skills/`: comandi di progetto;
   - `.claude/agents/`: revisori indipendenti;
   - `.claude/settings.json`: permessi (per esempio, il file `.env` non è leggibile).
4. Comandi di progetto:
   - `/prossima-fase`: implementa la fase successiva di `docs/roadmap.md`, con piano, test e verifiche;
   - `/valida-modelli`: validazione dei modelli e test del backend;
   - `/licenza <pacchetto>`: verifica di licenza prima di aggiungere una dipendenza;
   - `/nuovo-compito <slot> "<nome>" "<cron>"`: aggiunge un compito standard pianificato.
5. Prima di chiudere una fase chiedi a Claude di far revisionare le modifiche dal subagent `governance-reviewer`.

Le attività più comuni (avvio dello stack, test, validazione, build) sono anche nei task di VS Code: *Terminal → Run Task*.

## Struttura

```
models/      schemi e modelli JSON (waterfall, scrum): la fonte di verità
backend/     API FastAPI, validazione, worker cron, agenti LangGraph, test
frontend/    React + Vite: console e configurazione
gateway/     configurazione LiteLLM (alias dei modelli)
docker-compose.yml            modalità standalone (solo Ananke)
docker-compose.ecosystem.yml  modalità ecosistema (servizi collegati, da definire)
scripts/     validazione dei modelli da riga di comando
data/        progetti di esempio caricati al primo avvio
docs/        architettura, decisioni, roadmap, modello dati, licenze, mockup
```

## Licenze

Le dipendenze incorporate sono Apache-2.0 o MIT, più alcune permissive dichiarate (BSD, PostgreSQL License). Il dettaglio e le decisioni aperte sono in `docs/licenze.md` e `docs/decisioni.md`.
