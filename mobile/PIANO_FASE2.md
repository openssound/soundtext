# SoundText Mobile, fase 2: piano a tappe

La fase 2 parte l'11 novembre 2026, sul ramo `mobile-prototipo`, dopo la fase 1 (vedi `PIANO_FASE1.md`). Le prove della fase 1 sul telefono sono ancora da fare.

Obiettivo del documento di progetto per la fase 2:

- **Crea**: giro, basso, batteria, accompagnamento;
- **Struttura** a box;
- **funzioni sui pattern** con anteprima;
- **dettatura**.

Criteri di accettazione:

- i generatori danno gli stessi risultati di SoundText con gli stessi parametri e lo stesso seme;
- da un giro di 4 accordi a una base completa in meno di un minuto;
- dettatura: un giro di 8 accordi e una melodia di 2 battute su griglia fissa, dettati in italiano da 3 persone, entrano corretti almeno al 90% senza ritocchi;
- l'interprete della dettatura ha test automatici per ogni riga della tabella e per gli errori tipici del riconoscimento, nelle quattro lingue;
- dettatura e lettura del risultato funzionano con VoiceOver e TalkBack.

## Tappe

| # | Tappa | Contenuto | Fatto quando |
| --- | --- | --- | --- |
| 1 | **Generatori nel motore** | Giro armonico, batteria, basso e accompagnamento nel worker, con i generatori di SoundText | Stessi parametri e stesso seme, stesso testo delle finestre «Genera …» di SoundText |
| 2 | **Schermata Crea** | Una scheda per generatore (stile, tonalità, intensità, battute), anteprima che suona a ogni modifica, «Aggiungi al brano» | Da un giro di 4 accordi a una base completa in meno di un minuto |
| 3 | **Struttura** | Le sezioni (box) in verticale, le tracce in colonne; un tocco apre il box nel Testo; trascinare, duplicare, ripetere | Si costruisce un brano a sezioni senza scrivere le intestazioni dei box |
| 4 | **Funzioni sui pattern con anteprima** | Ascolto e piccola partitura di `%Tema.invert.retro` prima di inserirlo (`core/transform_preview.py`) | L'anteprima coincide con quello che suona dopo l'inserimento |
| 5 | **Interprete della dettatura** | Modulo Python: frase riconosciuta → testo ST, nelle quattro lingue, con le correzioni degli errori tipici del riconoscimento | Test per ogni riga della tabella del documento e per gli errori tipici |
| 6 | **Dettatura nell'app** | Microfono nella barra musicale, trascrizione e testo ST da confermare, comandi a voce, avviso sulla privacy, lettura con TalkBack e VoiceOver | Prova con 3 persone: almeno il 90% corretto |
| 7 | **Chiusura** | Prove sul telefono e di accessibilità, tabella dei criteri | I criteri della fase 2 |

Da decidere prima della tappa 6: il riconoscimento vocale. La Web Speech API del browser funziona su Chrome per Android e su Safari per iPhone, ma manda l'audio a Google o Apple e non funziona senza rete. Un modello locale (Whisper in WebAssembly) pesa 40–75 MB.

## Stato

**Tappa 1, fatta (11 novembre 2026).**

- **`engine.generate(testo, tipo, opzioni)`** in `mobile/engine.py`: giro armonico (`progression`), batteria (`drums`), basso (`bass`), accompagnamento (`comping`). Restituisce il testo e il seme usato; senza un seme ne sceglie uno.
  - Usa i generatori di SoundText (`core/rhythm_generate.py`, `core/performance_style.py`), con i parametri e i valori predefiniti delle finestre «Genera …» (`gui/rhythm_generate_dialog.py`). Queste finestre usano Qt, quindi nel motore la loro logica è riscritta: il programma per computer non cambia.
  - Supporta stile, tonalità, battute, variabilità (35%), intensità, cadenza o finale, fill, ottava, «Variazione ogni N accordi», la traccia degli accordi da seguire, la cassa da seguire, «Esecuzione dello strumento», «Rivolti vicini» e «Lascia spazio alle altre parti».
- **`engine.generator_choices(testo)`**: gli stili di ogni generatore (quelli della batteria secondo la metrica del brano), le tonalità e le intensità. Le etichette leggibili arrivano con la schermata Crea.
- **Errori leggibili e tradotti**, per esempio quando nel brano non ci sono accordi da seguire.
- **Nel worker** i comandi `generate` e `generator_choices`. In Pyodide ogni generatore risponde in 3–10 ms (Chrome sul portatile).
- **Test, `tests/test_mobile_generators.py` (44 casi):**
  - apre le finestre «Genera giro armonico», «Genera batteria», «Genera basso» e «Genera accompagnamento» di SoundText senza schermo;
  - le imposta come farebbe l'utente (stile, tonalità, intensità, cadenza, finale, esecuzione, cassa);
  - controlla che il testo dell'anteprima sia identico a quello del motore, con tre semi diversi.
- **Nel browser:** gli stessi testi generati in Pyodide hanno la stessa impronta SHA-256 di quelli del motore sul computer.
- **Bundle:** 23 moduli di `core/`; `rhythm_generate` e `performance_style` sono fra i moduli controllati per PySide6 e per numpy.

Non portati nell'app (servono tracce audio o configurazioni del computer):

- la batteria che segue il groove di una traccia audio;
- gli accordi riconosciuti da una traccia audio;
- gli stili personali (★);
- la rigenerazione di singole battute.

Riff e melodie (strumenti monofonici) e la melodia dal testo cantato possono arrivare con la schermata Crea, se servono.

**Tappa 2, fatta (11 novembre 2026), da provare sul telefono.** Provata nel browser del computer, nel formato del telefono:

- **Schermata Crea**, fra Testo e Partitura, con quattro schede: Giro, Batteria, Basso, Accompagnamento.
- **Campi**: i controlli principali delle finestre «Genera …» di SoundText, con le stesse etichette e gli stessi valori predefiniti. Le etichette degli stili vengono dalla finestra di SoundText, copiate nel motore; un test controlla che restino uguali.
  - Giro: tonalità, stile (secondo il modo della tonalità), durata di ogni accordo, battute (0 = giro intero), strumento, variabilità, cadenza finale.
  - Batteria: stile (secondo la metrica del brano), battute, intensità, variabilità, fill a frasi, finale.
  - Basso e accompagnamento: accordi da (le tracce con degli accordi), stile, strumento, battute, intensità, variabilità; per il basso anche la cassa da seguire, per l'accompagnamento i rivolti vicini; per entrambi l'esecuzione dello strumento.
  - Le battute partono dalla lunghezza del brano.
- **A ogni modifica** la parte si rigenera con lo stesso seme e il suo testo si vede sotto i campi. «🎲 Un'altra» sceglie un seme nuovo.
- **▶ Ascolta** suona il brano con la parte nuova. Se si cambia un campo mentre suona, l'anteprima riparte con la parte nuova dallo stesso punto. Per farlo il worker ha un motore a parte: il brano aperto, il suo MIDI e la sua posizione restano com'erano, e alla fine dell'anteprima (o con ■, o con il Play) si torna al brano.
- **«Aggiungi al brano»** mette la parte in una traccia nuova in fondo al file, senza toccare il resto (`engine.add_track`).
  - Intestazione breve («Drums:») quando il nome è lo strumento, altrimenti «Traccia Bass 2 [Bass]:».
  - Un esempio diventa una copia, come per ogni modifica.
  - Poi si resta in Crea sulla scheda dopo (giro → batteria → basso → accompagnamento), senza aprire la tastiera.
- **Criterio, da un giro di 4 accordi a una base completa:** dal modello «Nuovo brano» (accordi C F G7 C):
  - servono 7 tocchi: Nuovo brano, Crea, Batteria, tre volte «Aggiungi al brano», Play;
  - nella prova automatica, con un secondo fra un tocco e l'altro, ci sono voluti 8,2 s, e la base suona;
  - a mano restano 20–30 s, sotto il minuto. Da confermare sul telefono.
- **Test:** etichette uguali a SoundText, scelte della schermata, aggiunta di una traccia che lascia il resto del file identico (`tests/test_mobile_generators.py`, 47 casi).

Da migliorare:

- il modello «Nuovo brano» ha già una linea di basso, quindi il basso generato si aggiunge come «Bass 2». Manca un «Sostituisci la traccia …»;
- la parte nuova parte sempre dall'inizio del brano: non si accoda a una traccia già scritta e non va in un box.

**Tappa 3, fatta (11 novembre 2026), da provare sul telefono.** Provata nel browser del computer, nel formato del telefono:

- **Schermata Struttura**, fra Crea e Partitura:
  - le sezioni del brano una sotto l'altra, ricavate dai box come il righello della vista Struttura di SoundText (`core.arrangement.song_sections`);
  - le tracce in colonne, che scorrono in orizzontale con la colonna delle sezioni ferma;
  - in ogni cella i box di quella traccia che cominciano nella sezione, con le battute.
- **Un tocco su un box** apre le azioni: «Apri nel Testo» (il cursore va nel corpo del box), «Rinomina…», «Sposta alla battuta…», «Duplica in fondo al brano», «Elimina».
- **Un tocco su una sezione**: «Duplica la sezione in fondo al brano» (tutti i suoi box, con le stesse distanze), «Rinomina la sezione…», «Elimina la sezione».
- **«Dividi in sezioni»**, per le tracce senza box (per esempio quelle fatte con Crea): il testo di ogni traccia diventa un box con il nome scelto, alla battuta 1.
- **«Annulla la modifica»** torna indietro di una modifica della Struttura, fino a 30.
- **Le modifiche** (`engine.box_edit`) cambiano solo le intestazioni «Box Traccia "Nome" |battito:» (scritte come le scrive SoundText) e i blocchi dei box. Commenti, mixer, effetti e il resto del file restano com'erano. Se due box della stessa traccia si sovrapporrebbero, la modifica non si fa e si dice perché.
- **Criterio, un brano a sezioni senza scrivere le intestazioni dei box:** dal modello «Nuovo brano» si fanno «Dividi in sezioni» (Strofa), «Duplica la sezione» due volte e «Rinomina la sezione» (Ritornello): esce Strofa–Ritornello–Strofa, 12 battute, che suona. Provato con clic veri sul foglio delle azioni.
- **Test** in `tests/test_mobile_engine.py`:
  - il brano a sezioni costruito come sopra, letto da SoundText con i box giusti e con il resto del file intatto;
  - la sezione copiata suona come l'originale, spostata di 8 battute;
  - spostamento, sovrapposizione rifiutata, eliminazione e rinomina;
  - la struttura di `jazz_aaba.st`.

Non fatto:

- trascinare i box con il dito: si spostano con «Sposta alla battuta…», più preciso e utilizzabile con TalkBack;
- le funzioni sui pattern («trasforma») dal foglio delle azioni: arrivano con la tappa 4.

**Tappa 4, fatta (11 novembre 2026), da provare sul telefono.** Provata nel browser del computer, nel formato del telefono, con `14_trasformazioni.st`:

- **Trasforma**: un tasto «✦ Trasforma» nella pagina Accordi della barra musicale apre, sul richiamo di pattern sotto il cursore (`%Tema`, `%Tema.invert(e*4)`…), un foglio con le funzioni della finestra Trasforma di SoundText:
  - il richiamo in un campo che si può scrivere, e «Aggiungi una funzione…», che allunga la catena con una funzione già pronta di valori (`.progressione(3,-1)`, `.canone('2)`…) e ne mostra la spiegazione;
  - la catena passo per passo (il pattern, poi ogni funzione con le note che produce), come nella finestra del computer;
  - due piccole partiture con verovio, il pattern e il risultato, e «▶ Ascolta» per tutte e due;
  - «Sostituisci» scrive il richiamo nuovo come se lo si battesse, quindi entra nell'annulla della tastiera;
  - «Scrivi le note» lo scrive per esteso nota per nota («Congela la trasformazione» di SoundText), con il commento «// da …», e rifiuta se il suono cambierebbe;
  - gli errori (una funzione che non esiste, argomenti sbagliati) compaiono sotto il campo.
- **Il motore** (`transform_at`, `transform_preview`, `transform_apply`) usa `core/transform_preview.py`, lo stesso codice della finestra del computer: griglia, velocity e tonalità del punto del brano in cui sta il richiamo.
- **Criterio, l'anteprima coincide con quello che suona dopo l'inserimento:** verificato da un test su quattro catene (`.retro`, `.invert(e*4).augment(2)`, `.thirds`, `2%Tema.step(1)`). Le note dell'anteprima sono esattamente quelle che il brano suona in quel punto dopo «Sostituisci». «Scrivi le note» non cambia il suono e lascia il rientro del file.
- **Trovato e corretto durante la tappa:**
  - «Scrivi le note» lasciava senza rientro le righe scritte, cosa che in un `.st` rompe il blocco: `freeze_span` lavora sul testo di una traccia, ora il motore toglie e rimette il rientro;
  - la prova del bundle ha trovato che mancava `core.transform_preview` (24 moduli ora).

Non portato: «Crea pattern» dalla catena (un pattern nuovo con il risultato).

**Tappa 5, fatta (11 novembre 2026).** L'interprete della dettatura, `core/dictation.py`: modulo Python puro (niente Qt, niente numpy), quindi lo può usare anche SoundText sul computer.

- **`interpret(frase, lingua, mode, patterns)`**: la frase riconosciuta diventa testo ST, pezzo per pezzo, in italiano, inglese, francese e spagnolo, con i nomi delle note di ogni lingua (do re mi / C D E, «ut» in francese).
- **La tabella del progetto, tutta:**
  - note e alterazioni;
  - ottave («do ottava cinque» `c*5`; «ottava sopra» e «ottava sotto» `*+` e `*-`, che valgono in `rel:`);
  - griglie («ottavi», «terzine di ottavi», anche «crome» e «semicrome»);
  - valori di nota («re semiminima puntata» `d'4.`, «pausa di minima» `r'2`, in inglese «half rest»);
  - pause con il numero («due pause» `2r`);
  - stanghette;
  - accordi con le qualità di SoundText («re minore sette bemolle cinque» `Dm7b5`, «settima maggiore», «semidiminuito», «sus quattro», «do su mi» `C/E`);
  - «ripeti due volte»: racchiude quello che si è dettato dopo l'ultima stanghetta, oppure diventa un comando per l'ultima battuta o la selezione;
  - pattern con le loro funzioni («Tema invertito» `%Tema.invert`, «retrogrado», «con le terze», «un'ottava sopra»).
- **Note o accordi:**
  - in modo automatico, se nella frase c'è un accordo con la sua qualità, anche i nomi soli diventano accordi: «la minore, fa, do, sol» dà `Am F C G`;
  - l'app potrà fissare il modo secondo la riga del cursore;
  - un accordo già scritto come simbolo dal riconoscimento («G7», «F#m») passa così com'è.
- **Comandi** nelle quattro lingue: cancella, annulla, suona la battuta, suona da capo, stop, tempo, trasponi su o giù, vai alla battuta, nuova traccia, fine dettatura.
  - Comandi e musica possono stare nella stessa frase.
  - I numeri si possono dire a parole, anche composti («centoventi», «quatre-vingt-dix», «ciento veinte»), o in cifre.
- **Errori tipici del riconoscimento:**
  - «re» capito come «e», «si» come «sì», «la» come «là», «sol» come «sole» o «so», «do» come «dò»;
  - in inglese «see», «bee», «gee»; in francese «raie», «saule», «scie»; in spagnolo «sí», «rey».
  - Le parole corrette diventano la nota giusta ma restano segnalate come incerte, con la parola capita.
  - Fra gli accordi «e», «and», «et» e «y» sono la congiunzione.
  - Le parole che l'interprete non capisce non diventano note: restano nell'elenco, segnalate.
- **Ogni pezzo porta le parole dette**, per la lettura con TalkBack e VoiceOver nella tappa 6 («inserito: la minore, fa, do, sol»).
- **Nel motore dell'app:**
  - `engine.dictate(testo, frase, lingua, mode)` riconosce per nome i pattern del brano e usa la lingua dell'interfaccia se non se ne indica una;
  - nel worker c'è il comando `dictate`; in Pyodide risponde in 2–19 ms;
  - il bundle ha 25 moduli di `core/`.
- **Test, `tests/test_dictation.py` (152 casi):**
  - ogni riga della tabella in ognuna delle quattro lingue, più qualità, valori e griglie in più;
  - gli errori tipici, con le parole segnalate;
  - tutti i comandi in tutte le lingue;
  - il giro di 8 accordi e la melodia di 2 battute del criterio di accettazione;
  - 1600 frasi a caso con le parole del lessico.
  - Il testo prodotto deve sempre leggersi in SoundText (`validate_track_text`).
  - In `tests/test_mobile_engine.py` c'è un test per `engine.dictate` con i pattern di `14_trasformazioni.st`.

**Riconoscimento vocale: Vosk, senza rete (prova, 12 novembre 2026).** Scelto il modello locale invece della Web Speech API: l'audio non esce dal telefono e funziona offline.

- vosk-browser 0.0.8 (Apache 2.0) e il modello piccolo italiano di Alphacephei (`vosk-model-small-it-0.22`, 50 MB), scaricati da `scarica_vendor.sh` con le somme di controllo in `vendor/vosk/` (non versionati). Il modello si carica una volta e resta nel browser (IndexedDB): 7,4 s la prima volta, 5,1 s le successive.
- **Vocabolario limitato:** `grammar(lingua, patterns)` in `core/dictation.py` (nel motore `engine.dictation_words`, nel worker `dictation_words`) dà al riconoscitore solo le parole dell'interprete, i nomi dei pattern del brano e circa 300 frasi tipiche (in italiano 1006 voci). Il rumore non produce testo.
  - Nel vocabolario di Vosk mancano le parole composte («semiminima», «biscroma», «semidiminuito»): l'interprete accetta anche «semi minima», «bis croma».
  - Un test controlla che ogni parola delle frasi della tabella e dei comandi sia nella grammatica.
- **Pagina di prova:** `mobile/prova_voce.html` (microfono o file audio, con la grammatica attivabile, confidenza per parola e latenza). Non ancora provata con una voce vera.
- Da scaricare, se la prova va bene: i modelli piccoli inglese, francese e spagnolo (circa 120 MB in tutto).

**Tappa 6, scritta (12 novembre 2026); manca la prova a voce.** La dettatura nell'app, nella schermata Testo.

- **Microfono 🎤 nella barra musicale**, a sinistra delle pagine. Il primo tocco apre l'avviso: la voce si riconosce sul telefono, l'audio non viene registrato e non esce dal dispositivo, la prima volta si scaricano circa 50 MB; con qualche frase di esempio.
- **Riconoscimento:** Vosk, caricato solo al primo uso (`vendor/vosk/vosk.js` e il modello della lingua dell'interfaccia). `bundle/files.json` elenca le lingue che hanno un modello (`voice`); per ora solo l'italiano, nelle altre l'app dice che la dettatura non è ancora disponibile. Il riconoscitore riceve la grammatica del brano aperto (`dictation_words`, con i nomi dei suoi pattern).
- **Pannello sopra la barra:** la frase capita, il testo ST (pezzi incerti evidenziati, parole non capite sottolineate) e una riga di stato `role="status"` che TalkBack e VoiceOver leggono («Inserito: la minore, fa, do, sol»).
- **Conferma:**
  - una frase capita tutta entra subito al cursore (o in fondo all'ultima riga, se il cursore non è nel testo);
  - con parole incerte, non capite, saltate in mezzo alla frase o con confidenza sotto il 40% aspetta: «conferma» o «cancella» a voce, oppure i tasti «Inserisci» e «Scarta»; ridire la frase la sostituisce;
  - «Chiedi sempre conferma» fa aspettare ogni frase.
- **Comandi a voce:**
  - «cancella» e «annulla» tolgono l'ultima modifica fatta a voce;
  - «suona la battuta», «suona da capo», «stop»;
  - «tempo novanta» cambia la riga `Tempo:` (o la aggiunge);
  - «trasponi su di due» sposta la trasposizione del lettore (fra −6 e +6);
  - «vai alla battuta cinque» porta il cursore sulla prima nota della battuta, nella traccia del cursore;
  - «nuova traccia basso» aggiunge la traccia in fondo e ci porta il cursore (`engine.dictate_track`; gli strumenti fuori dal catalogo diventano «Traccia Violino [Violin]:»);
  - «ripeti due volte» da solo racchiude l'ultima battuta della riga in `2( … )`;
  - «fine dettatura» spegne il microfono.
  - Nell'interprete c'è il comando nuovo «conferma» (confirm, confirme, confirma).
- **Frasi dette con parole proprie** (dopo la prima prova a voce, 12 novembre):
  - le parole con cui si chiede sono ignorate: «inserisci», «aggiungi», «scrivi», «metti», «crea», «per favore» («inserisci nuova traccia flauto», «metti il tempo a novanta»);
  - «traccia» basta per la traccia nuova («aggiungi una traccia di flauto», «traccia nuova basso»); «suona» da solo fa partire il brano, «suona tutto» lo fa partire da capo; «va bene» e «ok» confermano («inserisci» non è più una conferma);
  - una pausa in mezzo alla frase la spezza in più risultati: se un pezzo non si capisce da solo, l'app lo riprova unito al successivo (entro 6 secondi).
- **Mentre il brano suona** il microfono sente la musica: valgono solo i comandi («stop»).
- La dettatura si ferma cambiando schermata o brano e con l'app in background.
- Le modifiche a voce passano da `replaceDocText`, come Crea e Struttura: si annullano a voce, non con l'annulla della tastiera.
- **Provato:** nel browser del computer, con frasi date all'app al posto del riconoscitore (inserimento, conferma, tutti i comandi) e con l'avvio vero di Vosk dentro l'app (modello pronto in 5,2 s, riavvio immediato). I test: comando «conferma» e strumenti in `tests/test_dictation.py`, `dictate_track` in `tests/test_mobile_engine.py`.
- **Non provato:** il microfono vero (il browser di prova lo blocca), TalkBack e VoiceOver, la memoria sul telefono con Pyodide e Vosk insieme, l'audio su iPhone mentre il microfono è aperto (`audioSession` passa a `play-and-record`).

Resta per la tappa 6: la prova con 3 persone (almeno il 90% corretto) e i modelli delle altre tre lingue.
