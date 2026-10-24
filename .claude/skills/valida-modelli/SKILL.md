---
name: valida-modelli
description: Esegue la validazione completa dei modelli JSON e i test del backend. Usala dopo ogni modifica a models/, a validation.py o alla logica di pianificazione.
---

1. Esegui `python scripts/validate_models.py` dalla radice del repository.
2. Esegui `cd backend && python -m pytest -q`.
3. Riporta in modo sintetico: metodologie valide, numero di slot e compiti, test superati. Per ogni errore indica file, campo e correzione proposta.
4. Non correggere gli errori indebolendo le regole in `validation.py`: correggi i modelli.
