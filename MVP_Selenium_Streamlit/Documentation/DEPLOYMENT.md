# Guida al Deployment (Runbook operativo)

Guida operativa per l'installazione, l'avvio e la manutenzione dell'applicazione
**Oracle Course Automator** sul server di produzione. Destinatari: referenti IT
/ Sistemi Informativi.

---

## Indice

1. [Architettura di deployment](#1-architettura-di-deployment)
2. [Prerequisiti sul server](#2-prerequisiti-sul-server)
3. [Struttura delle cartelle sul server](#3-struttura-delle-cartelle-sul-server)
4. [Configurazione (secrets e config)](#4-configurazione-secrets-e-config)
5. [Avvio dell'applicazione](#5-avvio-dellapplicazione)
6. [Reverse proxy e timeout (critico)](#6-reverse-proxy-e-timeout-critico)
7. [Gestione di Edge e del driver (dipendenza critica)](#7-gestione-di-edge-e-del-driver-dipendenza-critica)
8. [Aggiornamento del codice (deploy di una nuova versione)](#8-aggiornamento-del-codice-deploy-di-una-nuova-versione)
9. [Log e diagnostica](#9-log-e-diagnostica)
10. [Sicurezza](#10-sicurezza)
11. [Titolarità e manutenzione dopo la consegna](#11-titolarità-e-manutenzione-dopo-la-consegna)
12. [Checklist rapida](#12-checklist-rapida)

---

## 1. Architettura di deployment

```
   Utente (browser sul proprio PC)
            │  HTTPS
            ▼
   https://oraclecourseautomator.gruppomagis.it
            │  (reverse proxy — Sistemi Informativi)
            ▼
   Server Windows (VM)  ──  Streamlit su 127.0.0.1:8501
            │
            ▼
   Microsoft Edge (headless) + msedgedriver.exe
            │  Selenium
            ▼
   Oracle HCM Cloud
```

- L'applicazione gira su una **VM Windows Server**.
- Viene avviata **manualmente** con `start_app.bat`.
- Usa una copia di **Python portable** in `C:\Prod\python_portable`.
- Gli utenti accedono tramite il **reverse proxy** su
  `https://oraclecourseautomator.gruppomagis.it`; non accedono direttamente
  all'IP:porta del server.
- Il browser automatizzato (Edge) gira **solo sul server**. La versione di Edge
  sui PC degli utenti non ha alcun impatto.

---

## 2. Prerequisiti sul server

| Componente | Note |
|------------|------|
| Windows Server (VM) | Accesso via Desktop Remoto per avvio/manutenzione |
| Python portable | In `C:\Prod\python_portable`. **Verificare la versione** con `C:\Prod\python_portable\python.exe --version` e annotarla. Lo sviluppo è avvenuto su Python 3.13 (Mac); la versione del server va confermata e mantenuta stabile. |
| Microsoft Edge | Installato sul server. Auto-update **disattivato** (vedi §7) |
| msedgedriver.exe | Accanto al codice. Versione allineata a Edge (prime 3 cifre) |
| Dipendenze Python | Da `requirements.txt` + modello spaCy italiano (vedi §5) |
| Porta 8501 | In ascolto solo su `127.0.0.1` (locale). L'esposizione avviene tramite il reverse proxy, non aprendo la porta a tutta la rete. |

---

## 3. Struttura delle cartelle sul server

```
C:\Prod\
├── python_portable\            # interprete Python portable
└── MVP-project-in-Python\
    └── MVP_Selenium_Streamlit\
        ├── main.py
        ├── view.py
        ├── presenter.py
        ├── model.py
        ├── config.py
        ├── automation_lock.py
        ├── requirements.txt
        ├── msedgedriver.exe     # <-- driver, versione allineata a Edge
        ├── start_app.bat
        ├── .streamlit\
        │   ├── secrets.toml      # ORACLE_URL + EDGE_DRIVER_PATH (NON in git)
        │   └── config.toml
        └── logs\                 # session_YYYYMMDD.log (creati a runtime)
```

Cartelle generate a runtime e da NON versionare: `logs\`, `__pycache__\`, e
l'eventuale ambiente virtuale.

---

## 4. Configurazione (secrets e config)

### `.streamlit\secrets.toml` (NON versionato in git)

Contiene due valori. **Non deve mai finire su git** perché include l'URL di
produzione di Oracle.

```toml
# URL di produzione di Oracle HCM
ORACLE_URL = "https://<host-oracle-hcm>/hcmUI/faces/FuseWelcome"

# Percorso del driver Edge SU QUESTA macchina.
# Le prime tre cifre della versione del driver DEVONO corrispondere a Edge.
# Quando si aggiorna Edge, scaricare il driver corrispondente da:
# https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
EDGE_DRIVER_PATH = "msedgedriver.exe"
```

> **Suggerimento:** annotare in un commento, accanto a `EDGE_DRIVER_PATH`, la
> versione esatta del driver installato (es: `# msedgedriver 150.0.4078.x`), così
> chi farà manutenzione in futuro sa a quale versione di Edge è allineato.

### `.streamlit\config.toml`

Configurazione del server Streamlit. Valori di produzione:

```toml
[server]
address = "127.0.0.1"    # solo locale; l'esposizione la fa il reverse proxy
port = 8501
headless = true

[browser]
gatherUsageStats = false
```

**Le credenziali Oracle NON sono nei file di configurazione.** Ogni utente
inserisce le proprie a ogni sessione; restano in memoria e non vengono mai
scritte su disco.

---

## 5. Avvio dell'applicazione

### Prima installazione (una tantum)

Da Desktop Remoto, in un prompt nella cartella del progetto:

```bat
REM 1. Installare le dipendenze Python
C:\Prod\python_portable\python.exe -m pip install -r requirements.txt

REM 2. Scaricare il modello spaCy italiano (NON è in requirements.txt)
C:\Prod\python_portable\python.exe -m spacy download it_core_news_sm

REM 3. Verificare l'allineamento Edge / driver
msedgedriver.exe --version
REM  confrontare le prime 3 cifre con la versione di Edge installata
```

### Avvio quotidiano

Doppio click su **`start_app.bat`** (oppure eseguirlo da prompt). Lo script:

1. chiude eventuali browser Edge/driver rimasti da esecuzioni precedenti;
2. avvia Streamlit sulla porta 8501.

Contenuto tipico di `start_app.bat`:

```bat
@echo off
echo Pulizia di eventuali browser rimasti da esecuzioni precedenti...
taskkill /F /IM msedgedriver.exe /T 2>nul
taskkill /F /IM msedge.exe /T 2>nul
echo Avvio dell'applicazione (PRODUZIONE)...
C:\Prod\python_portable\python.exe -m streamlit run main.py --server.address=127.0.0.1 --server.port=8501
pause
```

> **Nota sul `taskkill`:** all'avvio, lo script chiude **tutti** i processi Edge
> del server. Sulla VM dedicata è corretto. Se qualcuno tenesse aperto Edge
> manualmente sul server, verrebbe chiuso all'avvio dell'app.

La finestra del prompt deve **restare aperta** finché l'app è in uso: chiuderla
ferma l'applicazione.

---

## 6. Reverse proxy e timeout (critico)

Gli utenti accedono tramite `https://oraclecourseautomator.gruppomagis.it`,
servito dal reverse proxy di Sistemi Informativi.

**Requisito critico: il timeout di connessione/inattività del proxy deve essere
generoso (30 minuti).**

Perché: l'automazione gira in modo sincrono (vedi `LIMITAZIONI.md`, punto 1).
Un'operazione lunga (molti allievi o molte edizioni) può durare diversi minuti
mantenendo aperta la connessione. Con un timeout troppo breve (di default alcuni
proxy tagliano dopo ~20-30 secondi), la connessione WebSocket cade a metà e
l'automazione viene abbandonata.

> Durante i test, il timeout sul link è stato portato a **30 minuti** e questo ha
> risolto le interruzioni delle operazioni lunghe. Verificare che la stessa
> configurazione sia applicata all'URL di produzione.

---

## 7. Gestione di Edge e del driver (dipendenza critica)

`msedgedriver.exe` deve corrispondere alla versione di Edge installata (prime 3
cifre). Se Edge si aggiorna da solo e il driver no, **il browser non parte più**.

### Stato attuale

L'aggiornamento automatico di Edge sul server è stato **disattivato**
disabilitando i servizi `edgeupdate` e `edgeupdatem` (via `services.msc`).

> **Nota di trasparenza.** La disattivazione dei servizi è una misura efficace
> ma **non blindata**: in alcuni casi Edge può riabilitare i propri servizi di
> update. La soluzione robusta e duratura è una **policy di registro/GPO**:
> `HKLM\SOFTWARE\Policies\Microsoft\EdgeUpdate` →
> `Update{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}` (REG_DWORD) = `0`
> (canale Stable), oppure `TargetVersionPrefix` per fissare Edge a una versione
> specifica. Riferimento Microsoft:
> https://learn.microsoft.com/en-us/deployedge/microsoft-edge-update-policies
> Se il server è nel dominio, questa policy va impostata via GPO limitata **al
> solo server**, non a un'OU più ampia (altrimenti bloccherebbe gli
> aggiornamenti di Edge su tutti i PC del dominio).

### Procedura di aggiornamento congiunto (quando si aggiorna Edge)

Da eseguire in **un'unica finestra di manutenzione**:

1. Verificare la nuova versione di Edge:
   `edge://settings/help` (oppure proprietà del file `msedge.exe`).
2. Scaricare il `msedgedriver.exe` con le **stesse prime 3 cifre** da:
   https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
   (scegliere **Windows x64**).
3. Sostituire il vecchio `msedgedriver.exe` accanto al codice.
4. Aggiornare il commento con la versione in `secrets.toml`.
5. Riavviare l'applicazione (`start_app.bat`) e fare un test rapido
   (es: creazione di un corso singolo).

> Un disallineamento Edge/driver **non causa danni silenziosi**: il browser non
> si avvia e l'errore è immediato e visibile. Non c'è rischio di scritture
> errate su Oracle.

---

## 8. Aggiornamento del codice (deploy di una nuova versione)

Il codice è versionato su Git. Sul server, il flusso per applicare una nuova
versione è:

```bat
REM Nella cartella del progetto sul server:
git stash          REM mette da parte le modifiche locali (es. secrets, driver)
git pull           REM scarica la nuova versione
git stash pop      REM ripristina le modifiche locali
```

Questo flusso `stash / pull / stash pop` serve a **preservare i file locali del
server** (come `secrets.toml` e l'eventuale `msedgedriver.exe` versionato
localmente) mentre si aggiorna il codice.

Dopo l'aggiornamento:

1. Se `requirements.txt` è cambiato, rieseguire l'installazione delle dipendenze
   (vedi §5).
2. Riavviare l'applicazione con `start_app.bat`.
3. Fare un test rapido di almeno un'operazione.

> Attenzione: `secrets.toml` **non è su git** (per sicurezza). Deve restare sul
> server e non essere sovrascritto dagli aggiornamenti.

---

## 9. Log e diagnostica

- I log stanno in `logs\session_YYYYMMDD.log` (un file al giorno).
- Ogni riga è marcata con l'utente Oracle loggato (`user=<username>`) e un
  timestamp — richiesto da Sistemi Informativi per tracciabilità/audit.
- Tutti i messaggi di avanzamento delle operazioni finiscono nel log.

**Per diagnosticare un'operazione fallita: partire sempre dal log del giorno.**
Contiene la traccia passo-passo, con l'indicazione esatta del punto in cui
un'operazione si è fermata.

Screenshot di errore: in caso di fallimento, l'applicazione salva uno screenshot
(`error_*.png`) nella cartella del progetto, utile per capire cosa mostrava
Oracle al momento del problema.

---

## 10. Sicurezza

Elementi rilevanti per la revisione di sicurezza:

- **Credenziali Oracle:** non vengono mai salvate su disco. Ogni utente inserisce
  le proprie a ogni sessione; restano in memoria (`st.session_state`) solo per la
  durata della sessione. L'app non ha un database di credenziali.
- **Verifica credenziali:** al login, l'app verifica le credenziali direttamente
  su Oracle prima di dare accesso. Non c'è un sistema di autenticazione proprio.
- **Esposizione di rete:** Streamlit è in ascolto solo su `127.0.0.1:8501`.
  L'accesso dall'esterno passa esclusivamente dal reverse proxy su HTTPS. La
  porta 8501 non va aperta direttamente a tutta la rete aziendale.
- **Streamlit — versione:** verificare che la versione installata sia
  **≥ 1.54.0** (`python.exe -m pip show streamlit`). Le versioni precedenti su
  Windows erano soggette a una vulnerabilità SSRF/NTLM quando gli endpoint erano
  esposti a reti non fidate; con l'app dietro il reverse proxy il rischio è
  ridotto, ma è buona norma essere aggiornati.
- **Tracciabilità:** ogni operazione è loggata con utente e timestamp (§9).
- **`secrets.toml`:** contiene l'URL di produzione di Oracle e **non è su git**.
  Verificare che sia elencato in `.gitignore`.
- **Nessuna scrittura silenziosa errata:** i fallimenti sono sempre riportati nel
  riepilogo e nel log (vedi `LIMITAZIONI.md`).

---

## 11. Titolarità e manutenzione dopo la consegna

Con la fine del contratto dello sviluppatore, alcune attività di manutenzione
restano in carico a qualcuno e vanno assegnate esplicitamente:

| Attività | Quando serve | Nota |
|----------|--------------|------|
| Aggiornamento congiunto Edge + driver (§7) | Quando si aggiorna Edge sul server | Dipendenza critica: senza, il browser non parte |
| Correzione XPath in `config.py` | Dopo un aggiornamento maggiore di Oracle | Richiede competenza Python/Selenium |
| Riavvio dell'app | Dopo riavvio del server o chiusura del prompt | `start_app.bat` |
| Policy di registro/GPO per Edge (§7) | Per rendere robusto il blocco degli update | Consigliato, da valutare con Sistemi Informativi |
| Verifica timeout proxy (§6) | Se ricompaiono interruzioni delle operazioni lunghe | 30 minuti |

> È consigliato indicare un **referente tecnico** per gli interventi su
> `config.py` (correzioni XPath) e un **referente infrastruttura** per Edge,
> proxy e riavvii.

---

## 12. Checklist rapida

**Avvio quotidiano**
- [ ] Accedere al server via Desktop Remoto
- [ ] Doppio click su `start_app.bat`
- [ ] Verificare che l'app risponda su `https://oraclecourseautomator.gruppomagis.it`

**Dopo un aggiornamento di Edge**
- [ ] Annotare la nuova versione di Edge
- [ ] Scaricare `msedgedriver.exe` con le stesse prime 3 cifre
- [ ] Sostituire il driver e aggiornare il commento in `secrets.toml`
- [ ] Riavviare `start_app.bat` + test rapido

**Deploy di una nuova versione del codice**
- [ ] `git stash && git pull && git stash pop`
- [ ] Reinstallare dipendenze se `requirements.txt` è cambiato
- [ ] Riavviare `start_app.bat` + test rapido
- [ ] Verificare che `secrets.toml` sia intatto

**Se un'operazione fallisce**
- [ ] Aprire il log del giorno in `logs\`
- [ ] Individuare il passo in cui si è fermata
- [ ] Controllare eventuale screenshot `error_*.png`
