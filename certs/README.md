# Certificati aggiuntivi per le build

Metti qui, in formato PEM con estensione `.crt`, i certificati radice che le build Docker devono considerare attendibili. Serve quando un antivirus o un proxy aziendale ispeziona il traffico HTTPS (per esempio Avast con la «scansione HTTPS» attiva) e `pip` o `npm` falliscono con `CERTIFICATE_VERIFY_FAILED`.

I file `.crt` sono specifici della macchina e git li ignora. Se la cartella non contiene certificati, le build funzionano come sempre.

Esportazione da Windows (PowerShell), sostituendo l'impronta del certificato:

```powershell
Get-ChildItem Cert:\LocalMachine\Root | Where-Object Subject -like "*Avast*"
```

poi esporta il certificato in Base64 (PEM) come `certs/<nome>.crt`.
