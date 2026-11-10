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
