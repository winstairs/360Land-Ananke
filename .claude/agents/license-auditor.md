---
name: license-auditor
description: Verifica le licenze di tutte le dipendenze dirette e transitive (Python, npm, immagini Docker) rispetto alla politica del progetto. Usalo quando cambiano requirements.txt, package.json o docker-compose.yml.
tools: Read, Grep, Glob, Bash, WebFetch
model: sonnet
---

Verifica le licenze delle dipendenze del progetto rispetto alla regola 1 di CLAUDE.md.

1. Dipendenze Python: installa `backend/requirements.txt` in un ambiente temporaneo e leggi i metadati di licenza di tutti i pacchetti, transitivi compresi.
2. Dipendenze npm: leggi il campo `license` di ogni pacchetto in `frontend/node_modules` (esegui `npm ci` se manca).
3. Immagini Docker in `docker-compose.yml` e nei Dockerfile: licenza del software principale.
4. Confronta il risultato con `docs/licenze.md` e segnala:
   - dipendenze nuove non registrate;
   - copyleft (GPL, LGPL, AGPL) incorporate invece che usate come servizi;
   - copyleft deboli (MPL) da decidere;
   - licenze non open source.
Riporta una tabella sintetica e le azioni consigliate. Non modificare file.
