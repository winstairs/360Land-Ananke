---
paths:
  - "frontend/src/**/*.{ts,tsx,css}"
---

# Frontend

- React 19 e TypeScript in modalità strict. Nessuna libreria di componenti o di stato senza la skill `/licenza`.
- Chiamate al backend solo tramite `src/api.ts`. I tipi delle risposte stanno in `src/types.ts`, allineati all'API.
- Stile: i token di colore e spaziatura sono in `src/styles.css`. Bordo pieno per gli umani, tratteggiato per gli avatar, come nel mockup in `docs/mockup/`.
- Accessibilità: elementi interattivi come `<button>` o `<a>` veri, `<label>` per ogni campo, target di almeno 44px, contrasto almeno 4.5:1.
- Testi dell'interfaccia in italiano, frasi brevi, in prima persona plurale o impersonali.
- La validazione delle regole di governance resta sul server: il frontend mostra gli errori restituiti da `/config/validate`, senza duplicarli.
