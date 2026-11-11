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
