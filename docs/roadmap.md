# Roadmap

Ogni fase si implementa in Claude Code con `/prossima-fase` (oppure `/prossima-fase 2`). Una fase è chiusa quando tutti i criteri sono spuntati e `governance-reviewer` la considera approvabile.

## Fase 0 · Scheletro (completata)

- [x] Modelli JSON v1.1 per waterfall e Scrum, validati
- [x] API: progetti, stadi, RACI per persone, dettaglio persona, coda dei compiti, decisioni sui gate, configurazione versionata con validazione
- [x] Worker cron: compiti degli avatar, richieste manuali a intervalli, applicazione delle decisioni sui gate, chiusura dei timebox Scrum
- [x] Agenti con LangGraph in modalità mock e live tramite LiteLLM
- [x] Frontend: console e configurazione
- [x] Docker compose con profili `live` e `local-llm`

## Fase 1 · Pilota sui requisiti con modelli reali

Obiettivo: la fase Requisiti del progetto «Portale prenotazioni» gira con agenti veri e produce una SRS revisionata.

Prompt suggerito per Claude Code:
> Implementa la fase 1 della roadmap. Gli agenti dello stadio requirements devono produrre artefatti reali: salva l'output di ogni esecuzione come artefatto versionato (tabella `artifacts`), passa al compito successivo gli artefatti che consuma, e fai verificare la SRS al requirements-validator-agent prima del gate. Mostra gli artefatti nella console.

- [ ] Tabella `artifacts` con versioni, collegata a esecuzioni e stadi
- [ ] Gli agenti ricevono in ingresso gli artefatti che consumano (`consumes` nella topologia)
- [ ] La revisione (`reviewedBy`) avviene prima della consegna al gatekeeper
- [ ] Il gatekeeper produce un pacchetto di evidenze con lo stato di ogni criterio del gate
- [ ] La console mostra artefatti, revisioni e pacchetto di evidenze
- [ ] Test end-to-end in modalità mock; prova manuale in modalità live con `claude-sonnet` e `oss-generalist`

## Fase 2 · Connettori MCP

Obiettivo: gli agenti leggono e scrivono su Jira, Confluence e GitHub tramite MCP, come utente tecnico.

Prompt suggerito:
> Implementa la fase 2: aggiungi al runner LangGraph un client MCP per i connettori abilitati nello slot (`connectors`), rispettando autonomia e `allowedConnectors` del preset. In modalità `supervised` le scritture diventano proposte da approvare in console.

- [ ] Client MCP nel runner (verifica la licenza della libreria con `/licenza`)
- [ ] Connettori filtrati per slot e preset
- [ ] Autonomia applicata: `advisory` solo lettura, `supervised` scritture come proposte, `autonomous` scritture dirette
- [ ] Coda delle proposte in console con approva o rifiuta
- [ ] Delega ad agenti esterni via A2A (Rovo) per gli avatar che la prevedono
- [ ] Decisione registrata su OpenProject come work tracker alternativo

## Fase 3 · Implementazione e test con agenti di coding

- [ ] Slot di coding eseguiti con Claude Agent SDK in container sandbox
- [ ] Branch e pull request su GitHub; code review dall'agente di famiglia diversa
- [ ] Integrazione con la CI per test e build
- [ ] Gate di code freeze con evidenze da CI e review

## Fase 4 · Esercizio della piattaforma

- [ ] Autenticazione e ruoli utente della console
- [ ] Osservabilità: tracce degli agenti (Langfuse o OpenTelemetry) e costi per progetto
- [ ] Persistenza dei grafi LangGraph (vedi decisioni aperte)
- [ ] Grafo del processo con React Flow nella console
- [ ] Backup del database e procedure di ripristino
