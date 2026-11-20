# SoundText Mobile: prove sul telefono

Una scheda da seguire con in mano un Android di fascia media e un iPhone, dall'indirizzo di GitHub Pages
(https://openssound.github.io/soundtext/), la prima volta anche in 4G. Per ogni voce: che cosa fare, che cosa
deve succedere, che numero annotare. Le misure le raccoglie la pagina **Diagnostica**
(`diagnostica.html`): a fine prova si tocca «Copia le misure (JSON)» e si incolla il testo in un messaggio.

Prima di cominciare: «Svuota la cache e misura un avvio a freddo» (Diagnostica), poi aprire l'app e aspettare
«motore pronto». Annotare modello del telefono, versione di Android o iOS, browser e versione.

| # | Voce | Che cosa fare | Deve succedere | Da annotare |
| --- | --- | --- | --- | --- |
| 1 | Senza rete | Aprire l'app, aspettare il motore, mettere il telefono in modo aereo, chiuderla e riaprirla | Si apre, si ascolta un esempio, si vede la partitura, si cambia lingua | Secondi di avvio a freddo e a caldo |
| 2 | Crea, Struttura, Trasforma | Creare un giro, una batteria e un basso; in Struttura spostare un box; applicare una trasformazione | Il brano suona e il testo cambia come mostrato nell'anteprima | Qualsiasi errore o attesa oltre 2 s |
| 3 | Dettatura | Tre persone dettano un giro di 8 accordi e una melodia di 2 battute (con `prova_voce.html` per la voce) | Almeno il 90% corretto | Percentuale per persona, lingua |
| 4 | Partitura di «Orizzonti» | Aprire «Orizzonti» (orchestra sinfonica), andare in Partitura | La partitura compare. Se no: Diagnostica → copiare il JSON e mandarlo | Il JSON, la memoria prima e dopo |
| 5 | Link e QR | Condividere il link di un brano per WhatsApp; aprirlo su un altro telefono; mostrare il QR e inquadrarlo | Il brano si apre in sola lettura e suona | Se WhatsApp taglia il link |
| 6 | Esporta | WAV e m4a; clip da 15, 30 e 60 s e «tutto il brano» con accordi, testo, partitura e forme; condividere su WhatsApp e Instagram | I file si ascoltano e si guardano altrove | Secondi per creare ogni clip; se la condivisione parte al primo tocco |
| 7 | Pad | Pad degli accordi e della batteria suonando a tempo con un brano | La risposta non si nota | Latenza stimata nella finestra dei pad |
| 8 | Esercizi e icona | Una sessione di esercizi; aggiungere l'app alla schermata Home; usare le scorciatoie dell'icona | Funziona | — |
| 9 | SoundFont proprio | Caricare un .sf2 da almeno 30 MB; chiudere e riaprire l'app | Resta tra i SoundFont e suona | Picco di memoria (Diagnostica → memoria) |
| 10 | Pacchetto orchestra | Impostazioni SoundFont → «Scarica il pacchetto orchestra» (46 MB, meglio con il Wi-Fi); aprire un brano d'orchestra | Si scarica, si controlla, suona con archi, ottoni e arpa; resta dopo il riavvio; si toglie con «Elimina» | Secondi di download, picco di memoria con un brano orchestrale |
| 11 | Effetti | Un brano con riverbero, delay e compressore, effetti attivi e spenti | Si sente la differenza | Batteria e calore del telefono dopo 5 minuti |
| 12 | Brano in 60 secondi | Aprire «Un brano in 60 secondi», creare tre brani di fila (anche 4 minuti), poi «Un’altra» e «Sorprendimi» | Suona sempre, la prima volta in meno di 5 s dal tocco | `brano_veloce`: `to_sound_ms` e `composed_ms` in Diagnostica |
| 13 | Accordatore | Aprire l'accordatore e suonare o fischiare un La | Mostra La; entro ±3 cent con un La di prova a 440 Hz; la vibrazione rallenta avvicinandosi | Cent mostrati con un diapason o un'altra app di riferimento |
| 14 | Suona con la base | Scegliere la melodia, cuffie, cantare una melodia di 8 battute a tempo | Almeno il 90% delle note «giuste»; una sbagliata di proposito risulta rossa | Percentuale; ritardo fra la nota e il colore (sotto 150 ms) |
| 15 | Vista accordi | Aprire la vista accordi di un brano di 4 minuti | Si legge a un metro; lo schermo non si spegne; un pedale Bluetooth gira pagina e avvia | Se lo schermo si è spento |
| 16 | Lettore dopo una pausa | Suonare, mettere in pausa, riprendere; saltare a una battuta; ripetere un tratto A–B | Riparte dallo stesso punto e il suono non sparisce | Qualsiasi silenzio |
| 17 | Screen reader | TalkBack (Android) e VoiceOver (iPhone): aprire un brano da un link, ascoltarlo, spostarsi per battuta e sezione, farselo leggere con 🔊, esercizi, accordatore e modalità studio senza guardare | Ogni passo si può fare e si sente | Dove ci si perde; se la voce del telefono e lo screen reader si sovrappongono |
| 18 | File .st | Aprire un .st dall'app File o da un allegato | Si apre nell'app | — |

## Come si riferisce un problema

1. Che cosa si stava facendo (il numero della voce) e che cosa è successo.
2. Il JSON di Diagnostica («Copia le misure (JSON)»).
3. Se c'è un messaggio d'errore in rosso, il testo.
4. Per un suono che manca: se `Suona` è in basso, se la barra di avanzamento si muove, se dopo un
   ricaricamento torna.

Ogni problema che si può riprodurre sul computer diventa un test (`tests/`, `mobile/tests/`).
