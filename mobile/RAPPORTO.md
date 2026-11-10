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

**Online, per iPhone e 4G.** Il workflow `.github/workflows/mobile-pages.yml` pubblica `mobile/` su GitHub Pages a ogni push sul ramo `mobile-prototipo`: `https://openssound.github.io/soundtext/`. Il sito ridistribuisce componenti di terzi, ciascuno con la sua licenza:

- Pyodide: MPL 2.0;
- js-synthesizer: BSD-3;
- FluidSynth: LGPL 2.1;
- TimGM6mb: GPL 2, e il file `.sf2` è anche la sua forma sorgente;
- st-language: GPL 3 (come SoundText);
- mido: MIT.

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

**Avvio con istantanea.** Il primo avvio fa partire Python, importa il motore e salva in Cache Storage un'istantanea della memoria di Pyodide: circa 30 MB, creata in 50 ms. Usa `makeMemorySnapshot` con le opzioni `_makeSnapshot` e `_loadSnapshot`, ancora sperimentali in Pyodide. Gli avvii seguenti ripartono dall'istantanea, senza rifare l'avvio dell'interprete né gli import. I file non sono nell'istantanea: a ogni avvio si rimettono `engine.zip` e le wheel (meno di 0,1 s).

La chiave dell'istantanea cambia con `engine.zip`, le wheel, la versione di Pyodide e il browser. Se un'istantanea non si carica, il worker la cancella e fa l'avvio normale.

**numpy dopo.** Fra i moduli usati, numpy lo importa solo `core/effects.py`, per gli effetti audio che qui non servono, e l'analisi dei brani non lo usa mai (lo controlla un test). Al suo posto c'è un modulo sostituto, che importa numpy vero al primo uso. Il pacchetto si carica in background dopo il primo brano aperto.

**Come funziona l'evidenziazione.** `engine.py` scorre i blocchi del file `.st` (box, tracce, pattern). Per ogni blocco chiama `compute_token_spans` di st-language, come fa SoundText. Quando incontra un `%Pattern`, scende nel corpo del pattern con lo spostamento di tempo del riferimento. Così su `jazz_aaba.st` e `symphony_d_minor_box.st` si illumina la nota che suona dentro `Pattern %HeadA1`, e non tutto il box.

La mappa si calcola dopo l'apertura: il brano si può già suonare mentre arriva. La posizione arriva dal player di FluidSynth (`retrievePlayerCurrentTick`, 480 tick per battito come `core/midi_export.py`), corretta della latenza d'uscita. L'evidenziazione usa la CSS Custom Highlight API: niente DOM da rifare a ogni fotogramma.

**Trasposizione.** Si fa sulle note del MIDI esportato, tranne il canale 10 delle percussioni. Il documento proponeva invece `transpose=` di st-language davanti al testo, ma non funziona: i box degli esempi cominciano con `reset:` e hanno un loro `transpose=` (per esempio il sax un'ottava sotto), che lo annullano. Il MIDI si esporta una volta sola e si traspone in circa 0,5 s.

**Test.** `tests/test_mobile_engine.py` (9 test):

- in un processo nuovo, un finder intercetta ogni tentativo di importare PySide6 mentre il motore analizza ed esporta i due esempi;
- un controllo statico (AST) cerca gli import di PySide6 anche dentro le funzioni dei moduli usati; lo stesso controllo trova quelli di `core/audio_decode.py` e `core/autosave.py`;
- l'analisi dei quattro esempi non legge nessun attributo di numpy;
- verifica la trasposizione e la mappa nota → testo.

## Misure sul computer

Portatile AMD Ryzen 7 3700U, 8 GB di RAM, Linux, server locale. Quindi la rete non pesa: i tempi sono di caricamento e calcolo.

- **Chrome 152**: il pannello del browser dell'app Claude, nascosto durante le prove; un pannello in secondo piano può rallentare un po'.
- **Firefox 160**: senza finestra, con `misura_headless.py`.

### Avvio del motore

«Prima» è la prima versione del prototipo (Pyodide, numpy e import a ogni avvio); «ora» è con l'istantanea e numpy rinviato.

| | Chrome, prima | Chrome, ora | Firefox, prima | Firefox, ora |
| --- | --- | --- | --- | --- |
| Primo avvio (crea l'istantanea) | 8,6 s | 5,4 s | 11,5 s | 9,4–10,8 s |
| **Avvio con la cache** | **8,4 s** | **0,67–0,82 s** | **10,1 s** | **2,2 s** |
| Heap WebAssembly di Pyodide all'avvio | 43 MB | 30 MB | 43 MB | 30 MB |

Obiettivo del documento: meno di 3 s con la cache. Sul computer ora è raggiunto in tutti e due i browser. Il primo avvio resta lungo: è l'avvio di Python (4–5 s in Chrome); la compilazione del WebAssembly costa solo 80 ms.

Prima dell'istantanea avevo provato anche i `.pyc` precompilati in cache: l'import di `core/` scendeva da 3,1 a 1,4 s in Firefox (con numpy rinviato). L'istantanea li rende inutili e li ho tolti.

**Peso da scaricare al primo avvio:**

| Parte | Peso | Compresso (gzip) |
| --- | --- | --- |
| Motore (Pyodide, wheel, `engine.zip`) | 13,5 MB | circa 6,7 MB |
| `pyodide.asm.wasm` (incluso sopra) | 9,2 MB | 3,4 MB |
| `python_stdlib.zip` (incluso sopra) | 2,4 MB | già compresso |
| numpy, dopo il primo brano | 2,8 MB | già compresso |
| Audio (al primo Play): js-synthesizer + FluidSynth | 0,7 MB | 0,24 MB |
| Audio (al primo Play): SoundFont | 5,7 MB | 5,3 MB |

Su un 4G a 20 Mbit/s il motore richiede circa 3 s di solo download, più l'avvio di Python. **L'obiettivo di 10 s la prima volta è quindi stretto, già prima di misurare il telefono.**

### Analisi dei due esempi (nel worker, con la cache calda)

«Pronto» va dalla richiesta al brano che si può suonare: lettura del file ed export MIDI. La mappa per l'evidenziazione arriva dopo.

| Brano | Python nativo (lettura + MIDI) | Chrome, pronto | Chrome, mappa | Firefox, pronto | Firefox, mappa |
| --- | --- | --- | --- | --- | --- |
| `jazz_aaba.st` (10 KB, 5 tracce) | 0,59 s | 1,1 s | 0,5 s | 1,8–2,9 s | 0,8–1,1 s |
| `symphony_d_minor_box.st` (30 KB, 12 tracce) | 0,88 s | 1,4–1,5 s | 0,7 s | 2,1–3,1 s | 1,0–1,5 s |

Il dettaglio per `symphony_d_minor_box.st` in Chrome, contro Python nativo:

- lettura: 0,54 s (nativo 0,45);
- MIDI: 0,86 s (nativo 0,43);
- mappa: 0,68 s (nativo 0,37).

Il documento stimava da 2 a 4 volte il tempo nativo: Chrome sta in basso in quella forbice. Trasposizione: 0,46–0,48 s (il MIDI si riscrive con mido nel worker).

### Audio (Chrome)

| Misura | Valore |
| --- | --- |
| Dal tocco su Play al suono, primo Play (SoundFont non in cache) | 0,5 s |
| Dal tocco su Play al suono, primo Play della sessione (SoundFont in cache) | 0,33 s |
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
| Heap WebAssembly di Pyodide | 30 MB all'avvio, 36–43 MB dopo i brani e numpy |
| Istantanea in Cache Storage | 30 MB |
| Heap JavaScript della pagina (Chrome) | 2–3 MB |
| Memoria totale di pagina, worker e worklet | non misurata |

La memoria totale (`measureUserAgentSpecificMemory`) non è disponibile nel pannello dell'app né in Firefox, anche con la pagina isolata (il service worker aggiunge COOP/COEP). Su Chrome per Android va provata. Su iPhone si legge con Safari → Sviluppo → Timeline, collegando il telefono al Mac.

## Prime misure su un telefono Android

11 novembre 2026. Telefono Android 10 con Chrome 156, 8 core e 4 GB di RAM (modello da annotare), in Wi-Fi verso il server del computer. È stato usato il flag `unsafely-treat-insecure-origin-as-secure`: senza, la pagina non è «sicura» e mancano service worker, istantanea e audio.

| Misura | Telefono | Computer (Chrome) |
| --- | --- | --- |
| Primo avvio senza service worker (pagina non sicura) | 7,2–9,8 s | – |
| Primo avvio, con creazione dell'istantanea | 6,5 s | 5,4 s |
| **Avvio con l'istantanea** | **0,96–1,53 s** (pagina pronta in 1,1–1,9 s) | 0,7–0,8 s |
| `jazz_aaba.st` pronto da suonare | 1,13–1,21 s (una volta 2,4 s, subito dopo l'avvio) | 1,1 s |
| `boom_bap.st` pronto da suonare | 1,21 s | – |
| Mappa per l'evidenziazione | 0,28–0,58 s | 0,5 s |
| numpy in background | 0,8–1,3 s | 0,7 s |
| Trasposizione | 0,53 s | 0,46 s |
| Primo Play, con download di FluidSynth e SoundFont in Wi-Fi | 1,8 s (worklet 0,77 s, SoundFont 0,88 s) | 0,5 s |
| Primo Play con il SoundFont in cache | 0,28 s | 0,33 s |
| Ripresa dopo una pausa | 12 ms | immediata |
| Latenza d'uscita (`baseLatency` + `outputLatency`) | 21 + 120–128 ms | 21 + 64 ms |
| Memoria totale di pagina, worker e worklet (`measureUserAgentSpecificMemory`) | 57 MB | non misurabile |
| Heap di Pyodide (dopo numpy) | 43 MB | 43 MB |

Su questo telefono l'avvio con la cache sta sotto i 3 s e l'analisi è veloce quanto sul portatile. L'audio parte al primo tocco.

Nei tempi d'avvio, 0,55–0,58 s su 1–1,5 s servono a leggere `engine.zip` e le wheel dalla cache: si possono mettere nell'istantanea o in un solo file.

Non ancora provati: primo avvio su 4G, schermo bloccato e app in background mentre suona, 10 minuti di batteria, confronto all'ascolto. Le voci `visibilita` registrate finora sono tutte a riproduzione ferma.

## Cosa resta da migliorare prima della fase 1

1. **L'istantanea su iPhone.** È un'opzione sperimentale di Pyodide: va provata su Safari (prova 17). Se non funziona, il ripiego sono i `.pyc` precompilati con `pyodide py-compile` nella CI, che valgono circa 1–2 s.
2. **Moduli di `core/` più leggeri.** `core.effects` (numpy, pedalboard facoltativo) e `core.memory` entrano solo perché li importa `project_io`. Con `soundtext-engine` conviene spostarli dietro import locali: così numpy non servirebbe neanche dopo.
3. **Il primo avvio.** Restano 6,7 MB compressi da scaricare e 4–5 s di avvio di Python, che sul telefono saranno di più. Serve un indicatore di avanzamento, con la schermata Brani usabile nel frattempo, come propone il documento.
4. **numpy in background in Firefox.** Nelle prove headless in Firefox il caricamento di numpy dopo il primo brano non ha registrato la sua misura (in Chrome sì: 0,7 s). Non tocca l'analisi né l'ascolto, ma va guardato.

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
| 16 | Telefono di fascia bassa | Prove 1, 2, 5, 6 e 13 | se l'avvio supera di molto i 10 s, provare SpessaSynth o un motore più leggero |
| 17 | **Istantanea di Pyodide** | Secondo avvio dopo il primo, e di nuovo dopo aver chiuso Safari o Chrome del tutto | in Diagnostica, `avvio.snapshot` deve dire «caricata» e `total_ms` deve scendere sotto i 3 s |

## Decisione proposta (da confermare dopo le prove sui telefoni)

Sul computer la strada PWA funziona: stesso codice di SoundText, stesso sintetizzatore, nessuna riscrittura. Con l'istantanea l'avvio con la cache sta sotto i 3 s (0,7 s in Chrome, 2,2 s in Firefox). Il punto debole resta il primo avvio: 5–11 s su un portatile, senza rete in mezzo. Sui telefoni sarà probabilmente più lento.

La proposta è decidere fra «PWA sì» e «PWA sì con Capacitor da subito» guardando due risultati:

- **prove 2 e 6–9 su iPhone.** Se lo schermo bloccato e l'interruttore silenzioso fermano l'audio, serve Capacitor con la sessione audio nativa;
- **prove 1 e 17 sul telefono economico e su iPhone.** Se l'istantanea non funziona su Safari, o il primo avvio è molto oltre i 10 s, prima di cambiare tecnologia conviene fare i miglioramenti 1–3 qui sopra e rimisurare.
