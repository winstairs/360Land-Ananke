# Modello dati

Tre documenti JSON per metodologia, ciascuno con il suo schema in `models/schemas/`, più il catalogo LLM di piattaforma.

## Processo (`*.process.json`)

Descrive **cosa** succede: ruoli del processo (es. Sponsor, Product Owner), artefatti, stadi con attività e matrice RACI, gate con criteri e approvatori, transizioni (`gate_approved`, `gate_rejected`, `defect_found`, `change_request`, `timebox_end`), processi trasversali.

- `iterative`: lo stadio si ripete (sprint).
- `timebox`: durata ISO 8601 (`P2W`, `PT4H`); allo scadere il Coordinatore applica la transizione `timebox_end`.
- `continuous`: lo stadio prosegue mentre altri sono attivi (product backlog); i suoi compiti girano sempre.

## Topologia agenti (`*.agents.json`)

Descrive **chi lo fa** a livello di slot: un supervisore (PM Office o Agile Office) e un orchestratore per stadio, ciascuno con agenti specialisti. Ogni agente ha responsabilità, attività coperte, artefatti consumati e prodotti, autonomia, revisore e i **compiti standard pianificati** (`scheduledTasks`) con nome, cron e azione:

- `agent`: esecuzione LLM;
- `apply-gate-decisions`: il Coordinatore applica le decisioni umane registrate;
- `check-timebox`: il Coordinatore chiude gli stadi a timebox scaduto.

## Configurazione (`*.config.json`)

Descrive **con chi e con cosa**:

- `personas`: catalogo di persone umane e avatar, con nome, titolo, volto, email ed eventuali agenti esterni delegabili. Per un avatar l'email è quella dell'utente tecnico con cui i suoi agenti accedono ai connettori;
- `roleAssignments`: per ogni ruolo del processo, modalità (`human`, `hybrid`, `agent`) e persone umane titolari;
- `slotAssignments`: per ogni slot della topologia, la persona che lo esegue; se è un avatar anche preset, istruzioni, autonomia, connettori, limite di iterazioni e override dei compiti (cron o disattivazione);
- `connectors` (strumenti esterni come Jira, Confluence e GitHub) e `bindings` (quale strumento svolge ogni funzione e dove si salva ogni artefatto): si modificano dalla scheda «Connettori» (card «Strumenti per fase» e «Connettori»). Ogni connettore ha `transport` (`rest` = connettore standard, `mcp-remote`, `mcp-local`), `endpoint` (URL REST o del server MCP remoto) e `settings`: parametri specifici dello strumento e della modalità, ad esempio ambito (`projectKey`, `spaceKey`, `owner`, `repositories`), autenticazione (`auth` e campi collegati) e, per MCP locale, `command`, `args`, `envVars`. Le credenziali non stanno nella configurazione: si indica solo il nome della variabile d'ambiente nelle chiavi che finiscono in `Env`;
- `agentPresets`: per ogni preset il modello (`provider/alias` del catalogo LLM), l'eventuale modello di riserva, la temperatura e il runtime;
- `policy`.

Un avatar è l'insieme degli slot che gli sono assegnati: per esempio Elio copre raccolta e specifica dei requisiti. Cambiare la persona di uno slot lo fa eseguire a un altro avatar o a un umano; in quest'ultimo caso i compiti diventano manuali.

Dalla versione 1.2 dello schema la configurazione non contiene più `llmProviders`: provider e modelli stanno nel catalogo LLM di piattaforma.

## Catalogo LLM (`platform/llm-catalog.json`)

Descrive **su quali modelli** girano gli agenti. È unico per tutte le metodologie e ha lo schema `llm-catalog.schema.json`. Ogni provider ha:

- `kind`: `anthropic`, `openai`, `openai-compatible`, `vllm` oppure `ollama`;
- `deployment`: `cloud` o `self-hosted`, più un campo libero `host` (es. «Hetzner GEX44»);
- `baseUrl`: obbligatorio per i server self-hosted e per le API compatibili;
- `apiKeyEnv`: il **nome** della variabile d'ambiente del gateway che contiene la chiave. La chiave non si salva in Ananke;
- `enabled` e i `models`, ciascuno con `alias` (unico in tutta la piattaforma, è il nome nel gateway), `upstream` (id presso il provider), `family` (per la regola cross-family), licenza ed `enabled`.

Si modifica dalla scheda «Modelli AI». Il worker pubblica sul gateway LiteLLM i modelli attivi.

## Regole verificate da `validation.py`

- schemi rispettati e riferimenti coerenti tra i tre documenti;
- ogni attività coperta da almeno uno slot, ogni artefatto prodotto da qualcuno, ogni processo trasversale con un responsabile;
- approvatori di gate e ruoli Accountable con almeno una persona umana e mai in modalità `agent`;
- ruoli del processo assegnati solo a persone umane;
- avatar con preset eseguibile; cron validi; revisione da famiglia di modelli diversa, con le famiglie lette dal catalogo LLM;
- preset che puntano a modelli attivi del catalogo; catalogo con alias unici, indirizzi e nomi delle variabili delle chiavi validi.

## Tabelle del database (fase 1)

- `artifacts`: versioni degli artefatti prodotti dagli agenti (`produces`), per progetto e tipo, con stadio, slot ed esecuzione di origine. Gli agenti ricevono l'ultima versione degli artefatti che consumano (`consumes`).
- `reviews`: revisione di una versione di artefatto da parte dello slot indicato in `reviewedBy`, con verdetto (`approved` o `changes_requested`) letto dalla riga «VERDETTO:» dell'output.
- `evidence_packs`: pacchetto del gatekeeper con lo stato (`met`, `unmet`, `unknown`) di ogni criterio del gate dello stadio. È un'informazione per chi approva, non un blocco.
