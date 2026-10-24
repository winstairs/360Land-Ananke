---
name: nuovo-compito
description: Aggiunge un compito standard pianificato con cron a uno slot agente nei modelli, mantenendo allineate waterfall e Scrum.
argument-hint: "[slot] \"[nome del compito]\" \"[cron]\""
---

Aggiungi il compito «$1» con cron `$2` allo slot `$0`.

1. Trova lo slot in `models/*/*.agents.json`. Se esiste in una sola metodologia, chiedi se va aggiunto anche nell'altra.
2. Aggiungi a `scheduledTasks` un oggetto con: `id` in kebab-case inglese, `name` in italiano, `cron` a 5 campi, `activity` se il compito contribuisce a un'attività del processo.
3. Verifica che il nome sia coerente con i compiti standard già presenti per lo stesso ruolo.
4. Esegui `/valida-modelli`.
