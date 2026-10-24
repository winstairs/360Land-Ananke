---
name: licenza
description: Verifica la licenza di una dipendenza (npm, PyPI o immagine Docker) prima di aggiungerla al progetto, e la registra in docs/licenze.md. Usala ogni volta che si propone una nuova dipendenza.
argument-hint: "[pacchetto] [npm|pypi|docker]"
---

Verifica la licenza di `$0` (ecosistema: `$1`, se non indicato deducilo).

1. Leggi la licenza dichiarata dalla fonte ufficiale:
   - npm: `npm view $0 license`
   - PyPI: la pagina JSON `https://pypi.org/pypi/$0/json` (campi `license_expression`, `license`, `classifiers`)
   - Docker: il repository dell'immagine e il file LICENSE del progetto
2. Elenca anche le dipendenze transitive principali che porta con sé e le loro licenze.
3. Classifica secondo la politica del progetto (CLAUDE.md, regola 1):
   - **ammessa**: Apache-2.0, MIT
   - **ammessa e da dichiarare**: BSD-2/3-Clause, ISC, PostgreSQL License
   - **da decidere**: MPL-2.0 e altre copyleft deboli
   - **solo come servizio esterno**: GPL, LGPL, AGPL
   - **vietata**: licenze non open source o con restrizioni d'uso (Elastic, BSL, Sustainable Use, Commons Clause)
4. Se è ammessa, aggiungi una riga alla tabella in `docs/licenze.md`. Altrimenti fermati, spiega il motivo e proponi un'alternativa con licenza compatibile.
