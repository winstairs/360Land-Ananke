# Sviluppo

## Senza Docker

Backend (Python 3.12):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --reload            # usa SQLite in backend/dev.db
python -m app.worker                     # in un secondo terminale
```

Frontend (Node 22):

```bash
cd frontend
npm ci
npm run dev                              # http://localhost:5173, proxy /api verso :8000
```

## Modelli reali

1. In `.env`: `LLM_MODE=live`, `ANTHROPIC_API_KEY` e un valore proprio per `LITELLM_SALT_KEY`.
2. `docker compose --profile live up --build`. Il servizio `gateway-db-init` crea il database `litellm`.
3. Il worker pubblica sul gateway i modelli attivi del catalogo LLM entro pochi secondi dall'avvio. L'esito si vede nella scheda «Modelli AI» della configurazione.

## Aggiungere un provider (es. server Hetzner con vLLM)

1. Su Configurazione › Modelli AI scegli «Server proprio con vLLM (es. Hetzner)» e premi «Nuovo provider».
2. Imposta l'indirizzo (`https://<server>/v1`), il nome della variabile della chiave (es. `HETZNER_LLM_API_KEY`) e, per ogni modello, l'alias, l'id servito da vLLM e la famiglia.
3. Salva i modelli. Poi, nei preset della metodologia, scegli il nuovo modello e salva la configurazione.
4. Scrivi la chiave nel file `.env` (`HETZNER_LLM_API_KEY=...`) e riavvia il gateway: `docker compose --profile live up -d gateway`. Il gateway legge le variabili d'ambiente solo all'avvio.
5. Entro `WORKER_RELOAD_MINUTES` il worker pubblica i modelli sul gateway.

Lo stesso vale per OpenAI (`OPENAI_API_KEY`) e per qualunque API compatibile OpenAI.

## Modelli open in locale con Ollama

1. `docker compose --profile live --profile local-llm up --build`
2. Scarica il modello: `docker compose exec ollama ollama pull qwen3.6:35b-a3b-q4_K_M` (verifica tag e licenza sulla model card).
3. GPU NVIDIA: installa NVIDIA Container Toolkit e aggiungi al servizio `ollama` in un `docker-compose.override.yml`:

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

Su una GPU da 12 GB il modello a Q4 scarica parte degli esperti nella RAM: funziona per demo su progetti semplici, ma più lentamente. Aumenta il contesto di Ollama ad almeno 16k token, perché il default è troppo corto per gli agenti.

## Dietro un proxy aziendale con ispezione TLS

Se `pip` o `npm` falliscono nella build con errori di certificato, aggiungi il certificato della CA aziendale alle immagini (variabili `PIP_CERT` e `NODE_EXTRA_CA_CERTS`) in un override locale, senza modificare i Dockerfile del repository.
