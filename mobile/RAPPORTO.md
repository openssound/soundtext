# SoundText Mobile, fase 0: rapporto del prototipo

10 novembre 2026. Prototipo in `mobile/`, una PWA che:

- apre un esempio di `examples/` e lo mostra come testo;
- lo analizza in un Web Worker con Pyodide, st-language e i moduli di `core/` senza Qt;
- lo suona con js-synthesizer (FluidSynth in WebAssembly) in un AudioWorklet;
- cambia velocità (50–100%) e trasposizione;
- evidenzia il testo durante l'ascolto;
- funziona senza rete dopo il primo avvio.

Le misure qui sotto sono state prese **sul computer**. Le prove su telefono (in fondo) restano da fare a mano.

## Come si prova

```bash
mobile/scarica_vendor.sh            # una volta: Pyodide, wheel, js-synthesizer, SoundFont (con SHA-256)
venv/bin/python mobile/build.py     # dopo ogni modifica a core/ o a mobile/engine.py
python3 -m http.server 8765 --directory mobile
```

Poi si apre `http://localhost:8765/`.

Sul telefono serve HTTPS: il service worker e l'AudioWorklet non funzionano su `http://` fuori da localhost. Le strade possibili:

- GitHub Pages su un ramo o repository di prova;
- un tunnel HTTPS verso il computer.

La pagina `diagnostica.html` mostra tutte le misure salvate (e le copia in JSON). Ha anche un pulsante per svuotare la cache e ripetere l'avvio a freddo. Per le misure automatiche in un browser senza finestra: `python3 mobile/misura_headless.py`.

## Com'è fatto

| Parte | File | Note |
| --- | --- | --- |
| Pagina e lettore | `index.html`, `app.js`, `style.css` | Play/pausa, velocità, trasposizione, «Segui» una traccia, apri un `.st` dal telefono |
| Motore | `worker.js` + `engine.py` | Worker di tipo *module*: Pyodide 314 non accetta più i worker classici |
| Codice di SoundText | `bundle/engine.zip` (da `build.py`) | 16 moduli di `core/` (319 KB con `locales/`): `project_io`, `model`, `midi_export`, `notation`, `tempo_map`… |
| Audio | js-synthesizer 1.13.0, FluidSynth 2.4.6 | Il player MIDI di FluidSynth nel worklet; velocità con `setPlayerTempo` (moltiplicatore), senza rianalizzare |
| SoundFont | TimGM6mb (GPL 2, 5,7 MB) | Stesso pacchetto Debian di `core/soundfont_downloads.py`; scaricato al primo Play |
| Offline | `sw.js`, `manifest.webmanifest` | Pagina e bundle: prima la rete, poi la cache. `vendor/`: prima la cache, in una cache a parte che resta fra le versioni |
| Misure | `metrics.js`, `diagnostica.html` | In console (`[misura]`) e in `localStorage` |

**Come funziona l'evidenziazione.** `engine.py` scorre i blocchi del file `.st` (box, tracce, pattern). Per ogni blocco chiama `compute_token_spans` di st-language, come fa SoundText. Quando incontra un `%Pattern`, scende nel corpo del pattern con lo spostamento di tempo del riferimento. Così su `jazz_aaba.st` e `symphony_d_minor_box.st` si illumina la nota che suona dentro `Pattern %HeadA1`, e non tutto il box (vedi la decisione 4).

La posizione arriva dal player di FluidSynth (`retrievePlayerCurrentTick`, 480 tick per battito come `core/midi_export.py`), corretta della latenza d'uscita. L'evidenziazione usa la CSS Custom Highlight API: niente DOM da rifare a ogni fotogramma.

**Trasposizione.** Si fa sulle note del MIDI esportato, tranne il canale 10 delle percussioni. Il documento proponeva invece `transpose=` di st-language davanti al testo, ma non funziona: i box degli esempi cominciano con `reset:` e hanno un loro `transpose=` (per esempio il sax un'ottava sotto), che lo annullano. Il MIDI si esporta una volta sola e si traspone in circa 0,5 s.

**Test.** `tests/test_mobile_engine.py` (8 test):

- in un processo nuovo, un finder intercetta ogni tentativo di importare PySide6 mentre il motore analizza ed esporta i due esempi;
- un controllo statico (AST) cerca gli import di PySide6 anche dentro le funzioni dei moduli usati; lo stesso controllo trova quelli di `core/audio_decode.py` e `core/autosave.py`;
- verifica la trasposizione e la mappa nota → testo.

## Misure sul computer

Portatile AMD Ryzen 7 3700U, 8 GB di RAM, Linux, server locale. Quindi la rete non pesa: i tempi sono di caricamento e calcolo.

- **Chrome 152**: il pannello del browser dell'app Claude, che era nascosto durante le prove; un pannello in secondo piano può rallentare un po'.
- **Firefox 160**: senza finestra, con `misura_headless.py`.

### Avvio del motore (Pyodide + numpy + st-language + core/)

| | Chrome, 1° avvio | Chrome, con cache (media di 4) | Firefox, 1° avvio | Firefox, con cache |
| --- | --- | --- | --- | --- |
| `loadPyodide` | 5,0 s | 4,8 s | 7,1 s | 5,9 s |
| numpy (+ packaging) | 1,1 s | 1,0 s | 1,1 s | 1,0 s |
| wheel st-language e mido | 0,1 s | 0,1 s | 0,1 s | 0,1 s |
| import dei moduli di `core/` | 2,5 s | 2,5 s | 3,2 s | 3,1 s |
| **totale** | **8,6 s** | **8,4 s** | **11,5 s** | **10,1 s** |

Obiettivo del documento: meno di 3 s con la cache. **Non è raggiunto nemmeno sul computer.** La cache toglie quasi solo il tempo di rete, che qui è zero. Il tempo se ne va a compilare il WebAssembly, avviare Python e compilare i sorgenti `.py`.

**Peso da scaricare al primo avvio:**

| Parte | Peso | Compresso (gzip) |
| --- | --- | --- |
| Motore (Pyodide, numpy, wheel, `engine.zip`) | 16,4 MB | circa 9,5 MB |
| `pyodide.asm.wasm` (incluso sopra) | 9,2 MB | 3,4 MB |
| `python_stdlib.zip` (incluso sopra) | 2,4 MB | già compresso |
| numpy (incluso sopra) | 2,8 MB | già compresso |
| Audio (al primo Play): js-synthesizer + FluidSynth | 0,7 MB | 0,24 MB |
| Audio (al primo Play): SoundFont | 5,7 MB | 5,3 MB |

Su un 4G a 20 Mbit/s il motore richiede circa 4 s di solo download, più l'avvio. **L'obiettivo di 10 s la prima volta è quindi a rischio, già prima di misurare il telefono.**

### Analisi dei due esempi (nel worker, con la cache calda)

| Brano | Python nativo | Chrome | Firefox | Rapporto Chrome/nativo |
| --- | --- | --- | --- | --- |
| `jazz_aaba.st` (10 KB, 5 tracce) | 0,86 s | 1,65–2,07 s | 2,4–2,7 s | circa 2× |
| `symphony_d_minor_box.st` (30 KB, 12 tracce) | 1,25 s | 2,09–2,19 s | 3,1–3,6 s | circa 1,7× |

Il totale comprende lettura del file, export MIDI e mappa per l'evidenziazione. Il dettaglio per `symphony_d_minor_box.st` in Chrome:

- lettura: 0,54 s (nativo 0,45);
- MIDI: 0,86 s (nativo 0,43);
- evidenziazione: 0,68 s (nativo 0,37).

Il documento stimava da 2 a 4 volte il tempo nativo: siamo in basso in quella forbice. Trasposizione: 0,48 s (il MIDI si riscrive con mido nel worker).

### Audio (Chrome)

| Misura | Valore |
| --- | --- |
| Dal tocco su Play al suono, primo Play (SoundFont non in cache) | 0,5 s |
| Dal tocco su Play al suono, primo Play della sessione (SoundFont in cache) | 0,34 s |
| Ripresa dopo una pausa | immediata |
| Caricamento del worklet FluidSynth | 0,13–0,17 s |
| Caricamento del SoundFont in FluidSynth | 0,09 s |
| Latenza (`baseLatency` + `outputLatency`) | 21 + 64 ms |

Velocità al 50%: 529,5 tick/s misurati contro 528 attesi. La pausa riprende dallo stesso tick.

L'evidenziazione segue la nota senza ritardi visibili. Non ho fatto un confronto all'ascolto con SoundText sul computer: è una delle prove a mano qui sotto.

FluidSynth avvisa una volta: «Instrument not found on channel 9 [bank=248]». Il kit di batteria richiesto non c'è in TimGM6mb e FluidSynth usa il kit standard; con il SoundFont di SoundText succede lo stesso.

### Memoria

| Misura | Valore |
| --- | --- |
| Heap WebAssembly di Pyodide, dopo l'analisi della sinfonia | 43 MB, stabile aprendo i brani più volte |
| Heap JavaScript della pagina (Chrome) | 2–3 MB |
| Memoria totale di pagina, worker e worklet | non misurata |

La memoria totale (`measureUserAgentSpecificMemory`) non è disponibile nel pannello dell'app né in Firefox, anche con la pagina isolata (il service worker aggiunge COOP/COEP). Su Chrome per Android va provata. Su iPhone si legge con Safari → Sviluppo → Timeline, collegando il telefono al Mac.

## Cosa si può migliorare prima della fase 1

1. **`.pyc` precompilati per Python 3.14.** Nel worker l'import di `core/` e st-language costa 2,5–3 s. In Python nativo i `.pyc` tolgono più di un terzo del tempo di import (0,61 → 0,39 s). Si possono preparare con `pyodide py-compile` nella CI.
2. **Moduli di `core/` più leggeri.** `core.effects` (numpy, pedalboard facoltativo) e `core.memory` entrano solo perché li importa `project_io`. Con `soundtext-engine` conviene spostarli dietro import locali.
3. **Mappa dell'evidenziazione al primo Play** e non all'apertura: risparmia 0,5–0,7 s sull'apertura del brano.
4. **Pyodide in cache già alla prima visita**, con un indicatore di avanzamento. I 9,5 MB compressi restano: bisogna vedere sul telefono se l'attesa è accettabile, con la schermata Brani usabile nel frattempo, come propone il documento.

## Prove da fare a mano su iPhone e Android

Su almeno un iPhone (Safari) e un telefono Android (Chrome), uno dei due di fascia bassa. Per ogni prova annotare modello, sistema e browser. Le misure si copiano da Diagnostica → «Copia le misure».

| # | Prova | Come | Cosa annotare |
| --- | --- | --- | --- |
| 1 | Primo avvio su 4G | Rete mobile, prima visita (o Diagnostica → «Svuota la cache») | `avvio.total_ms`, tempo percepito fino al testo |
| 2 | Avvio con la cache | Chiudere e riaprire (anche dall'icona sulla schermata Home) | `avvio.total_ms` (obiettivo < 3 s) |
| 3 | Installazione | iPhone: Condividi → Aggiungi alla schermata Home; Android: Installa app | si apre a tutto schermo, icona giusta |
| 4 | Senza rete | Modalità aereo dopo il primo avvio e il primo Play | si apre, si analizza, suona |
| 5 | Analisi | Aprire `jazz_aaba` e `symphony_d_minor_box` | `analisi.worker_total_ms` |
| 6 | **Primo Play dopo un tocco** | Pagina appena aperta, un solo tocco su ▶ | parte al primo tocco? `play.tap_to_play_ms`, stato `ctx_state` |
| 7 | **Interruttore silenzioso (iPhone)** | Interruttore su silenzioso; provare con e senza le due opzioni audio (ricaricare la pagina fra le prove) | si sente? Con quale combinazione? |
| 8 | **Schermo bloccato** | Mentre suona, bloccare lo schermo per 30 s e poi sbloccare | continua, si ferma o riprende? Voci `visibilita` in Diagnostica |
| 9 | App in background | Mentre suona, passare a un'altra app e tornare | come sopra |
| 10 | Chiamata o notifica | Ricevere una chiamata mentre suona | l'audio torna dopo? |
| 11 | Velocità e trasposizione | 50%, 75%, 100%; ±3 semitoni durante l'ascolto | nessun taglio o ritardo evidente |
| 12 | Evidenziazione | «Segui» sul Tenor Sax e sui Violins1 | segue la musica senza ritardi visibili |
| 13 | **Batteria** | Carica scollegata, 10 minuti di ascolto in loop (schermo acceso) | livello prima/dopo. Chrome Android lo registra da solo ogni minuto (voci `batteria`); su iPhone a mano |
| 14 | Memoria | Dopo i due brani e dopo 10 minuti | iPhone: Timeline di Safari; Android: `chrome://inspect` → Memory |
| 15 | Confronto con il computer | Stesso brano su SoundText (FluidSynth con il suo SoundFont) e sul telefono | differenze di suono, volume relativo delle tracce, batteria |
| 16 | Telefono di fascia bassa | Prove 1, 2, 5, 6 e 13 | se l'avvio supera di molto i 10 s, provare SpessaSynth o un motore senza numpy |

## Decisione proposta (da confermare dopo le prove sui telefoni)

Sul computer la strada PWA funziona: stesso codice di SoundText, stesso sintetizzatore, nessuna riscrittura. Il punto debole è l'avvio (8–11 s su un portatile, senza rete in mezzo). Sui telefoni sarà probabilmente più lento.

La proposta è decidere fra «PWA sì» e «PWA sì con Capacitor da subito» guardando due risultati:

- **prove 2 e 6–9 su iPhone.** Se lo schermo bloccato e l'interruttore silenzioso fermano l'audio, serve Capacitor con la sessione audio nativa;
- **prova 1 sul telefono economico.** Se l'avvio è molto oltre i 10 s, prima di cambiare tecnologia conviene fare i miglioramenti 1–2 qui sopra e rimisurare.
