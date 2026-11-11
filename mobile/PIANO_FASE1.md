# SoundText Mobile, fase 1: piano a tappe

La fase 1 parte l'11 novembre 2026, senza aspettare le prove su iPhone. L'app resta una PWA in `mobile/`, sul ramo `mobile-prototipo`. Se le prove su iPhone lo richiederanno, Capacitor si aggiungerà dopo, attorno alla stessa app web.

Obiettivo del documento di progetto per la fase 1:

- schermate: Brani, Testo con la barra musicale, Lettore (loop A–B, velocità, trasposizione, metronomo, mute e solo), Partitura;
- apertura e condivisione dei `.st`;
- installazione dalla schermata Home;
- interfaccia nelle quattro lingue.

## Scelta di fondo: si modifica il testo del file

L'app tiene il brano come **testo del file `.st`** e modifica direttamente quello. Non lo rilegge in un modello per poi riscriverlo.

Il motivo: rileggere e riscrivere un brano con `core/project_io.py` (`parse_project_text` → `project_to_text`) non lo lascia mai identico (0 esempi su 17), perché si perdono i commenti e la formattazione.

Con le modifiche sul testo, il criterio «un `.st` aperto e salvato senza modifiche resta identico byte per byte» vale per costruzione. Vale anche per le parti che l'app non gestisce (plugin, effetti, tracce audio, SFZ), che restano come sono.

Il motore Python resta in sola lettura: dal testo produce eventi, MIDI, avvisi, la mappa per l'evidenziazione e, nella tappa 5, il MusicXML.

## Tappe

| # | Tappa | Contenuto | Fatto quando |
| --- | --- | --- | --- |
| 1 | **Brani e navigazione** | Schermate Brani, Testo e Lettore con una barra in basso; archivio nel browser (IndexedDB); nuovo brano, apri da file, duplica, rinomina, elimina, condividi o scarica il `.st`; esempi in sola lettura (modificarli crea una copia); testo modificabile con salvataggio automatico | Un brano creato o aperto sul telefono si ritrova dopo aver chiuso l'app; un `.st` aperto e salvato senza modifiche resta identico |
| 2 | **Testo** | Evidenziazione della sintassi; avvisi delle battute (`check_bar_lines` di st-language) vicino alla riga; modifica per blocco (traccia, box, pattern) oltre al file intero | Gli avvisi coincidono con quelli di SoundText sugli stessi brani |
| 3 | **Barra musicale** | Riga di tasti sopra la tastiera del telefono, tre pagine (note, durate e struttura, accordi e pattern); completamento con `core/completion.py`; «▶ battuta» | 8 battute scritte in meno di 2 minuti (prova con 3 persone) |
| 4 | **Lettore completo** | Loop A–B, metronomo, mute e solo per traccia, barra di avanzamento trascinabile, mini lettore sempre visibile | Tutti i comandi funzionano anche durante l'ascolto, senza ricaricare il brano |
| 5 | **Partitura** | verovio in WebAssembly dal MusicXML di st-language; una traccia o tutte; nota corrente evidenziata | La partitura degli esempi didattici si legge sul telefono e segue la musica |
| 6 | **Lingue e accessibilità** | Testi da `locales/*.json` (italiano, inglese, francese, spagnolo); etichette per VoiceOver e TalkBack | Tutta l'interfaccia è tradotta; le prove con TalkBack passano |
| 7 | **Chiusura** | Tutti gli esempi di `examples/` e `examples/didattici/` si aprono e suonano (le parti non supportate con un avviso); `soundtext-engine` come pacchetto, se serve per separare il repository | I criteri della fase 1 del documento di progetto |

Ogni tappa si pubblica sul sito di prova (`https://openssound.github.io/soundtext/`) e si prova sul telefono Android. L'iPhone si prova appena disponibile.

## Stato

**Tappa 1, fatta (11 novembre 2026).** Provata nel browser del computer, anche nel formato del telefono (375×812):

- **Schermate:** Brani, Testo e Lettore, con la barra in basso e il mini lettore sempre visibile; su schermi larghi (≥ 900 px) Testo e Lettore stanno affiancati.
- **Brani:** nuovo brano da un modello di due tracce, apri un `.st` dal telefono, rinomina, duplica, condividi (foglio di condivisione del sistema, oppure download), elimina con conferma.
- **Esempi:** in sola lettura; la prima modifica crea una copia fra i brani dell'utente, e l'esempio resta intatto.
- **Testo:** modificabile (`contenteditable="plaintext-only"`), salvato da solo in IndexedDB 0,6 s dopo l'ultima modifica e quando l'app va in background. Il Play rianalizza il testo se è cambiato.
- **Riapertura:** all'avvio si riapre l'ultimo brano aperto.
- **Formato:** il file torna identico byte per byte, anche con il BOM e gli a capo di Windows. Lo verificano `mobile/tests/formato.test.cjs` (`node --test mobile/tests/*.test.cjs`), su tutti gli esempi, e il workflow di pubblicazione.

Da provare sul telefono: scrivere con la tastiera del telefono nel testo, condividere un `.st` (per esempio verso Drive o WhatsApp) e aprirne uno ricevuto.

Trovato durante la tappa: una traccia con un nome di strumento sconosciuto (per esempio «Basso:», che esiste solo nella configurazione personale di un computer) viene ignorata in silenzio. L'avviso va nella tappa 2.

**Tappa 2, fatta (11 novembre 2026).** Provata nel browser del computer, nel formato del telefono:

- **Colori della sintassi** come nell'editor di SoundText: la classificazione dei token è passata da `gui/highlighter.py` (Qt) a **`core/syntax.py`** (senza Qt), che usano sia SoundText sia l'app. I 386 test dell'evidenziazione di SoundText passano senza modifiche. Sono colorati anche commenti e intestazioni; durante l'ascolto la nota corrente resta sopra i colori.
- **Avvisi**: un pulsante ⚠ con il numero di avvisi e il loro elenco con la riga; un tocco porta alla riga. Nel testo, sottolineatura rossa. Gli avvisi coprono:
  - le battute che non tornano e gli altri avvisi di `notation_warnings`, con gli stessi parametri dell'editor dei box di SoundText;
  - i box, le tracce e i pattern che non si leggono;
  - gli strumenti sconosciuti segnalati dal lettore dei file;
  - le tracce «Nome:» di uno strumento sconosciuto, che prima venivano saltate in silenzio. Questo avviso nel programma per computer non c'è.
- **Quando si aggiorna**: all'apertura e 0,7 s dopo l'ultima modifica, nel worker. Costa 0,7 s per `jazz_aaba.st` e 1,1 s per `symphony_d_minor_box.st` (Chrome sul portatile). Mentre gira, un Play aspetta la fine del controllo.
- **«Vai a»**: menu con tracce, box e pattern del file.
- **Test**: in `tests/test_mobile_engine.py` (12 test), su avvisi, colori e assenza di falsi avvisi negli esempi; `core.syntax` è fra i moduli controllati per PySide6.

Non fatto: la modifica isolata di un solo blocco (si modifica sempre il file intero; «Vai a» ci porta). Si può aggiungere con la barra musicale della tappa 3, se servirà.

**Tappa 3, fatta (11 novembre 2026), da provare sul telefono.** Provata nel browser del computer, nel formato del telefono:

- **Barra musicale** in fondo alla schermata Testo, sopra la tastiera del telefono; mentre si scrive, la barra delle schermate sparisce per lasciare spazio. I tasti non tolgono il fuoco al testo, così la tastiera resta aperta. Scrivono come la tastiera (`execCommand("insertText")`): l'annulla del telefono e il salvataggio automatico funzionano come per il testo battuto a mano.
- **Tre pagine:**
  - **Note:** `c d e f g a b r`; `#`, `♭`, `*3`–`*6` e `~` si attaccano alla nota prima.
  - **Durate e struttura:** `1:` `2:` `4:` `8:` `16:` `8T:`; i moltiplicatori `2` `3` `4` si attaccano alla nota dopo (`2g`); `|`, `(` `)`, `[` `]`.
  - **Accordi e pattern:** gli accordi della scala nella tonalità al cursore (l'ultimo `key=` prima, altrimenti `Tonalita:`), la dominante con la settima, i pattern del brano e le funzioni sui pattern (`.retrogrado`, `.inverti(asse)`…).
- **Spazi:** ogni tasto mette lo spazio giusto prima e dopo; `⌫` cancella il token prima del cursore.
- **Suggerimenti** sopra i tasti: quelli dell'editor di SoundText (`core/completion.py`), per esempio `Cma` → `Cmaj7`, `%Te` → `%Tema`, `hi` → `hihat`; un tocco sostituisce la parola.
- **▶ battuta:** suona la battuta del token sotto il cursore e si ferma alla sua fine (circa 10 ms di scarto). Le battute si contano con la metrica del brano (`bar_starts` di st-language, con cambi e levare), poi il lettore torna dove era.
- **Test:** completamento, battuta e funzioni in `tests/test_mobile_engine.py` (13 test).

Limiti:

- gli stili di voicing (`Am7.drop2`) si suggeriscono solo nei box e nelle tracce, perché in un pattern non c'è uno strumento;
- con caratteri fuori dal piano di base (emoji) nel testo, le posizioni del cursore mandate al motore possono sfasarsi.

Criterio da verificare: 8 battute scritte in meno di 2 minuti, con 3 persone.

**Tappa 4, fatta (11 novembre 2026), da provare sul telefono.** Provata nel browser del computer, nel formato del telefono, con `jazz_aaba.st`:

- **Barra di avanzamento** nel mini lettore, sempre visibile: si trascina e il lettore va all'inizio della battuta, anche mentre suona. Accanto, «battuta 5/104».
- **Ripeti un tratto (loop A–B)** nella schermata Lettore: A segna l'inizio della battuta che si sente, B la sua fine, e accende «Ripeti». Premendo B più avanti, il tratto copre più battute. Il ritorno da B ad A cade a meno di 10 ms dalla fine del tratto (provato: da 19,985 a 16 su un tratto 16–20). Con «Ripeti» acceso, il Play parte da A.
- **Metronomo:** un click a ogni battito, più forte sul primo della battuta, con la metrica del brano.
- **Mute e solo** per traccia (M e S): con un solo attivo si sentono solo le tracce in solo.
- **Durante l'ascolto:** metronomo, mute, solo e trasposizione rifanno solo il MIDI nel motore (circa 0,1 s sul computer) e il lettore riparte dallo stesso punto, senza rianalizzare il brano. Restano anche dopo una modifica del testo; aprire un altro brano li azzera.
- **Test:** mute, metronomo e linea del tempo in `tests/test_mobile_engine.py` (14 test).

Limiti:

- con lo schermo spento il browser rallenta i timer della pagina: il ritorno da B ad A può arrivare fino a un secondo in ritardo;
- per togliere il tratto si spegne «Ripeti»; A e B restano segnati.

**Tappa 5, fatta (11 novembre 2026), da provare sul telefono.** Provata nel browser del computer, nel formato del telefono, con `jazz_aaba.st` e `symphony_d_minor_box.st`:

- **Schermata Partitura**, fra Testo e Lettore. Il MusicXML lo fa il motore con `st_language.musicxml`, lo stesso della vista Partitura di SoundText. Lo impagina **verovio 6.3.0**, la stessa versione di SoundText sul computer, in un worker suo (`score-worker.js`): la pagina non si blocca mentre disegna.
- **Caricamento:** verovio (7,3 MB, 2,4 MB compressi) si scarica solo alla prima apertura della Partitura, poi resta nella cache come gli altri componenti. Il controllo SHA-256 è in `scarica_vendor.sh`.
- **Pagine** larghe quanto lo schermo, nero su bianco anche col tema scuro. Si ridisegnano quando si ruota il telefono.
- **Tracce:** tutte, oppure una sola. Con più di 4 tracce si parte da quella seguita dal lettore, perché una partitura d'orchestra intera sul telefono non si legge.
- **Zoom** con − e ＋, da 25% a 75%.
- **Durante l'ascolto** la nota corrente si colora di rosso e la pagina scorre per tenerla in vista. La mappa dei tempi di verovio sviluppa i ritornelli, e i battiti sono quelli del lettore. Provato: la nota colorata era quella giusta in 39 controlli su 40; l'unico scarto cadeva sul cambio di nota.
- **Un tocco su una nota** porta il lettore all'inizio della sua battuta.
- **Errori:** un brano con un errore di notazione mostra il messaggio al posto della partitura.
- **Tempi sul computer (Chrome):**

  | Partitura | Tempo |
  | --- | --- |
  | `jazz_aaba.st`, una traccia, compreso l'avvio di verovio | 2,6 s |
  | `jazz_aaba.st`, tutte e 5 le tracce | 3,6 s |
  | `symphony_d_minor_box.st`, una traccia | 1,3 s |

  Sul telefono sono da misurare (tabella «partitura» della diagnostica).
- **Test:** il MusicXML con tutte le tracce o con alcune, in `tests/test_mobile_engine.py` (15 test).

Limiti:

- la partitura non segue la trasposizione del lettore, ed è scritta come in SoundText (strumenti traspositori compresi);
- con molte tracce e molte battute il disegno può richiedere parecchi secondi sul telefono. La partitura precedente resta visibile finché la nuova non è pronta.

**Tappa 6, fatta (11 novembre 2026), da provare con TalkBack sul telefono.** Provata nel browser del computer, nel formato del telefono, in inglese, francese e spagnolo:

- **Lingue come in SoundText:** i testi restano scritti in italiano nel codice, dentro `t("...")` (`mobile/i18n.js`) o con `data-i18n` nella pagina. Le traduzioni stanno negli stessi cataloghi `locales/*.json` del programma per computer (circa 100 voci nuove per lingua).
  - `locales/extract.py` raccoglie anche i testi dell'app: `t("...")` in `app.js`; `data-i18n`, `aria-label`, `title` e `placeholder` in `index.html`; `tr("...")` in `engine.py`.
  - `tests/test_i18n.py` controlla quindi che l'app sia tradotta tutta, con i segnaposto conservati.
  - `build.py` copia in `bundle/locales/` solo le voci dell'app (circa 5 KB per lingua).
- **Messaggi del motore:** avvisi, errori di notazione, suggerimenti e nomi delle funzioni sui pattern escono nella stessa lingua, con `core.i18n` nel worker; l'istantanea di Pyodide resta una sola per tutte le lingue.
- **Scelta della lingua:** in fondo alla schermata Brani; senza una scelta vale quella del telefono, se è fra le quattro, altrimenti l'inglese. Date e numeri seguono la lingua. Il commento del modello «Nuovo brano» è nella lingua dell'app; le parole del formato (`Tempo:`, `Metrica:`) restano quelle del file.
- **Testi del programma con un senso diverso:** «Ripeti» nel programma è il comando di modifica (in inglese «Redo»), quindi il pulsante del loop ha la sua voce, «Ripeti A–B».
- **Accessibilità (TalkBack, VoiceOver):**
  - ogni pulsante e cursore ha un nome: nella barra musicale «nota C», «diesis», «semiminima», «accordo F»…; nel lettore «Mute Piano», «Solo Bass»;
  - le pagine della partitura sono figure con un nome («Partitura di jazz_aaba, pagina 1 di 4»);
  - la barra di avanzamento e i cursori dicono il valore in parole («battuta 5/104», «+2 semitoni»);
  - il testo del brano è una casella di testo multiriga;
  - il pulsante degli avvisi dice quanti sono e quale elenco apre;
  - il fuoco si vede.

  Un controllo automatico nella pagina non trova più elementi senza nome. In questa prova ho corretto i cursori Velocità e Trasposizione: la loro etichetta finiva sull'`<output>` accanto.

Non tradotti: la pagina `diagnostica.html` (strumento di misura) e i nomi degli argomenti delle funzioni sui pattern che vengono da st-language (per esempio `.invert(asse)`).

Da provare: TalkBack su Android e VoiceOver su iPhone, criterio della tappa.
