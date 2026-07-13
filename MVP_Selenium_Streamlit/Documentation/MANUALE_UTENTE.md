# Manuale Utente — Oracle Course Automator

Guida all'uso dello strumento di automazione per la gestione dei corsi in
Oracle HCM.

Questo manuale è pensato per chi **usa** l'applicazione (team formazione). Non
richiede alcuna competenza tecnica: si spiega passo passo cosa fare per ogni
operazione.

---

## Indice

1. [Che cos'è questo strumento](#che-cosè-questo-strumento)
2. [Come accedere](#come-accedere)
3. [Regole importanti da conoscere prima di iniziare](#regole-importanti-da-conoscere-prima-di-iniziare)
4. [I tre modi di inserire i dati](#i-tre-modi-di-inserire-i-dati)
5. [Operazione 1 — Creazione Corso](#operazione-1--creazione-corso)
6. [Operazione 2 — Creazione Edizione + Attività](#operazione-2--creazione-edizione--attività)
7. [Operazione 3 — Aggiungi Allievi](#operazione-3--aggiungi-allievi)
8. [Operazione 4 — Assegnazione Presenza](#operazione-4--assegnazione-presenza)
9. [Formati dei file Excel](#formati-dei-file-excel)
10. [Personalizzare l'aspetto (temi)](#personalizzare-laspetto-temi)
11. [Domande frequenti e messaggi di errore](#domande-frequenti-e-messaggi-di-errore)

---

## Che cos'è questo strumento

È un'applicazione che compila automaticamente Oracle HCM al posto tuo. Tu
fornisci i dati (compilando un modulo, caricando un file Excel, oppure scrivendo
una frase), e l'applicazione apre Oracle e inserisce tutto da sola.

Copre quattro operazioni:

1. **Creazione Corso** — creare un nuovo corso.
2. **Creazione Edizione + Attività** — creare un'edizione di un corso e le sue
   giornate di attività.
3. **Aggiungi Allievi** — iscrivere gli allievi a un'edizione.
4. **Assegnazione Presenza** — assegnare lo stato di completamento agli allievi.

---

## Come accedere

1. Apri il browser e vai all'indirizzo:
   **https://oraclecourseautomator.gruppomagis.it**
2. Compare la schermata di accesso. Inserisci le **tue credenziali Oracle HCM**
   (le stesse che usi per entrare in Oracle: nome utente e password).
3. Clicca **Accedi**.

L'applicazione verifica le credenziali direttamente su Oracle. La verifica può
richiedere fino a circa **25 secondi**: è normale, attendi.

- Se le credenziali sono corrette, entri nell'applicazione.
- Se sono errate, compare un messaggio e resti sulla schermata di accesso.

> **Le tue credenziali sono al sicuro.** Non vengono mai salvate su disco:
> restano in memoria solo per la durata della tua sessione e servono unicamente
> per far accedere l'automazione a Oracle con il tuo profilo.

Per uscire, usa il pulsante **🚪 Logout** nella barra laterale a sinistra.

---

## Regole importanti da conoscere prima di iniziare

Poche regole, ma importanti. Rispettarle evita quasi tutti i problemi.

1. **Una sola operazione alla volta sul server.** L'automazione usa un vero
   browser sul server. Mettetevi d'accordo con i colleghi per non lanciare due
   operazioni contemporaneamente.

2. **Non ricaricare la pagina mentre un'operazione è in corso.** Quando
   l'automazione sta lavorando, vedi una barra di avanzamento e un messaggio.
   **Non premere F5, non chiudere la scheda, non cliccare altri pulsanti.**
   Ricaricare la pagina può interrompere l'operazione a metà.

3. **Le operazioni lunghe richiedono tempo.** Un inserimento di molti allievi o
   molte edizioni può durare diversi minuti. È normale. Attendi il messaggio
   finale di riepilogo.

4. **Controlla sempre il messaggio di riepilogo finale.** Alla fine di ogni
   operazione compare un riepilogo che dice cosa è andato a buon fine e cosa no.
   Leggilo: è lì che l'applicazione ti segnala eventuali righe non completate.

5. **Le date si scrivono nel formato GG/MM/AAAA** (esempio: `15/03/2026`).

6. **Gli orari delle attività** possono essere scritti liberamente (`9`, `9:00`,
   `09.00`): l'applicazione li converte automaticamente nel formato richiesto da
   Oracle.

---

## I tre modi di inserire i dati

Ogni operazione offre tre metodi, selezionabili in alto con i pulsanti a
scelta. Scegli quello più comodo per la situazione:

| Metodo | Quando usarlo |
|--------|---------------|
| 📝 **Input Strutturato (Form)** | Per **un singolo** elemento: compili i campi a mano. Il modo più semplice e controllato. |
| 📊 **Caricamento File Excel** | Per **molti** elementi in una volta sola (creazione in blocco). Ideale per liste lunghe. |
| 💬 **Compilazione con AI** | Scrivi una frase in italiano e il sistema estrae i dati. Comodo e veloce, ma **controlla sempre l'anteprima** prima di confermare. |

Con i metodi Excel e AI, prima di eseguire l'operazione vedrai sempre
un'**anteprima** dei dati estratti, con la possibilità di modificarli o
annullare.

---

## Operazione 1 — Creazione Corso

**Scheda: `1. Creazione Corso`**

### Metodo Form (un corso)

1. Seleziona **📝 Input Strutturato**.
2. Compila:
   - **Titolo del Corso** (obbligatorio)
   - **Dettagli del Programma** (facoltativo)
   - **Breve Descrizione** (obbligatorio)
   - **Data di Pubblicazione** (obbligatorio, GG/MM/AAAA)
3. Clicca **Crea Corso**.
4. Attendi il messaggio di riepilogo.

Se il corso esiste già in Oracle, l'applicazione **non lo ricrea** e te lo
segnala.

### Metodo Excel (più corsi)

1. Seleziona **📊 Caricamento File Excel**.
2. Carica il file (formato nella sezione [Formati dei file Excel](#formati-dei-file-excel)).
3. Clicca **Analizza File Excel** → controlla l'anteprima.
4. Clicca **Conferma e Crea** per procedere.

I corsi già esistenti vengono automaticamente saltati.

### Pulisci

Il pulsante **Pulisci 🧹** svuota tutti i campi del modulo.

---

## Operazione 2 — Creazione Edizione + Attività

**Scheda: `2. Creazione Edizione + Attività`**

Questa operazione crea un'edizione di un **corso già esistente** e le sue
giornate di attività.

### Metodo Form (una edizione)

1. Seleziona **📝 Input Strutturato**.
2. Indica **quanti giorni di attività** avrà l'edizione (in alto).
3. Compila i **Dettagli Edizione**:
   - **Nome del Corso Esistente** (obbligatorio — deve già esistere in Oracle)
   - **Titolo Edizione** (facoltativo)
   - **Data Inizio** e **Data Fine** Edizione (obbligatori)
   - Descrizione, Aula, Fornitore, Prezzo (facoltativi)
4. Compila gli **Attributi Aggiuntivi** se necessari (Centro di Costo, Società
   Pagante, Direzione Pagante, Servizio Pagante, Sottotipologia, Finanziata).
5. Per ogni **giornata di attività**, compila:
   - **Titolo Attività** (obbligatorio)
   - **Data** (obbligatorio, deve rientrare tra inizio e fine edizione)
   - **Ora Inizio** e **Ora Fine**
   - Descrizione e Impegno in ore (facoltativi)
6. Clicca **Crea Edizione e Attività**.

> **Le date delle attività devono rientrare nel periodo dell'edizione.** Se una
> data è fuori periodo, Oracle rifiuta quell'attività: l'edizione viene creata
> lo stesso, ma nel riepilogo finale l'attività risulterà **non creata** con il
> motivo. Correggi la data direttamente in Oracle o rilancia.

### Metodo Excel (più edizioni)

Carica un file con le edizioni e le loro attività → **Analizza** → controlla
l'anteprima (ogni edizione ha tre tabelle: dettagli, attributi, attività) →
**Conferma**.

### Metodo AI

Scrivi una frase che descriva l'edizione e le attività (nel riquadro c'è un
esempio completo). Poi **Analizza Testo** → controlla l'anteprima → **Conferma**.

---

## Operazione 3 — Aggiungi Allievi

**Scheda: `3. Aggiungi Allievi`**

Iscrive gli allievi a un'edizione, a partire da un elenco di **numeri persona**.

### Metodo TXT (una edizione)

1. Seleziona **📄 Caricamento File TXT**.
2. Inserisci il **Codice Edizione** (es: `OLC466201`).
3. (Facoltativo) Inserisci una **Data scadenza** (GG/MM/AAAA). Se la lasci
   vuota, viene usata la data di domani.
4. Carica un file **.txt** con un numero persona per riga:
   ```
   1168
   1189
   1199
   1216
   ```
5. Clicca **Analizza File** → controlla l'anteprima → **Aggiungi Allievi**.

### Metodo Excel (più edizioni)

1. Seleziona **📊 Caricamento File Excel**.
2. Carica il file. Gli allievi vengono letti dal foglio **ALLIEVI**.
3. **Analizza** → l'anteprima mostra un'espansione per ogni edizione →
   **Aggiungi Allievi**.

### Metodo AI

Scrivi una frase, ad esempio:
*"Aggiungi allievi 1168, 1189, 1199 all'edizione OLC466201"*.
Poi **Analizza** e conferma.

> Dopo l'invio, se gli allievi non compaiono subito nella lista di Oracle,
> **attendi qualche minuto**: Oracle può impiegare del tempo per elaborare il
> file. Non è un errore.

---

## Operazione 4 — Assegnazione Presenza

**Scheda: `4. Assegnazione Presenza`**

Assegna lo stato di completamento agli allievi di un'edizione.

Gli stati possibili sono: **Completato**, **Esente**, **Non passato**.

### Metodo Form (una edizione)

1. Seleziona **📝 Input Strutturato**.
2. Inserisci il **Codice Edizione**.
3. Scegli lo **Stato Completamento**.
4. Inserisci i **numeri persona** degli allievi (uno per riga).
5. **Anteprima** → controlla → **Assegna Presenza**.

### Metodo Excel (più edizioni / più stati)

Il foglio si chiama **PRESENZA** e permette di indicare uno stato diverso per
ogni allievo. Vedi [Formati dei file Excel](#formati-dei-file-excel).

### Metodo AI

Esempio: *"Edizione OLC466201 completato: 1168, 1189, 1199"*.

> **Attività in data futura.** Oracle non permette di assegnare il completamento
> a un'attività che non è ancora avvenuta. Gli allievi le cui attività sono in
> una data futura vengono **saltati** e segnalati a parte nel riepilogo, sotto
> "⏭️ Non completati (data futura)". Potrai assegnarli quando le attività
> saranno avvenute.

---

## Formati dei file Excel

Regole generali:
- La **prima riga** contiene i nomi delle colonne (intestazioni).
- Le righe incomplete vengono saltate e segnalate.
- Le date possono essere scritte in vari formati; l'applicazione le normalizza.

### Corsi (Operazione 1)

| NOME CORSO | DESCRIZIONE | DATA INIZIO PUBBLICAZIONE |
|------------|-------------|---------------------------|
| Analitica  | Informatica | 01/01/2026 |
| Musica     | Arte        | 01/01/2026 |

### Edizioni + Attività (Operazione 2)

Formato consigliato: **due fogli** nello stesso file.
- Foglio **Edizioni**: una riga per edizione, con una colonna `ID_EDIZIONE`
  (es: `E1`, `E2`) più i dettagli (nome corso, titolo, date, aula, fornitore,
  costo, e gli attributi aggiuntivi).
- Foglio **Attivita**: una riga per attività, con la colonna `ID_EDIZIONE` che
  la collega alla sua edizione, più titolo, data, ora inizio, ora fine, impegno.

### Allievi (Operazione 3)

Foglio **ALLIEVI**:

| CODICE EDIZIONE | PERSON NUMBER |
|-----------------|---------------|
| OLC466201       | 1168 |
| OLC466201       | 1189 |
| OLC466205       | 1200 |

### Presenza (Operazione 4)

Foglio **PRESENZA**. La colonna STATO è facoltativa; se vuota si usa lo stato di
default scelto nella schermata. Il codice edizione può essere lasciato vuoto
nelle righe successive: viene ereditato da quello sopra.

| CODICE EDIZIONE | PERSON NUMBER | STATO |
|-----------------|---------------|-------|
| OLC621263       | 1168 | Completato |
|                 | 1189 |            |
| OLC621270       | 1200 | Non passato |

---

## Personalizzare l'aspetto (temi)

Nella barra laterale a sinistra, sotto **⚙️ Impostazioni colori**, puoi scegliere
un **tema colori** e un **tipo di carattere**, vedere un'anteprima, e cliccare
**Applica tema**. Con **💾 Salva preferenze** la scelta viene ricordata anche
alle sessioni successive. È solo estetica: non influisce sul funzionamento.

---

## Domande frequenti e messaggi di errore

**"L'operazione è ferma da minuti, cosa faccio?"**
Le operazioni lunghe (molti allievi/edizioni) sono normali. Attendi. Non
ricaricare la pagina. Attendi il riepilogo finale.

**"Ho ricaricato la pagina per sbaglio durante un'operazione."**
L'operazione potrebbe essersi interrotta. Attendi un minuto, poi verifica in
Oracle cosa è stato effettivamente inserito prima di rilanciare, per evitare
duplicati.

**"Credenziali errate" ma sono sicuro che siano giuste.**
Verifica di riuscire ad accedere a Oracle HCM normalmente dal browser. Se Oracle
funziona ma qui no, segnala il problema al referente IT.

**"Edizione creata, ma alcune attività NON create."**
Quasi sempre significa che la data di quelle attività è **fuori dal periodo
dell'edizione**. Correggi le date in Oracle (o rilancia con date corrette).

**"Allievi inviati ma non li vedo nella lista."**
Attendi qualche minuto: Oracle elabora il file con un ritardo. Ricontrolla dopo.

**"Alcuni allievi non completati per data futura."**
È corretto: non si può assegnare il completamento a un'attività non ancora
avvenuta. Riprova dopo la data dell'attività.

**Qualcosa non va e non capisco il messaggio.**
Annota il messaggio esattamente come appare e a quale operazione/edizione si
riferisce, e inoltralo al referente tecnico. Ogni operazione è registrata in un
file di log giornaliero, che aiuta a capire cosa è successo.
