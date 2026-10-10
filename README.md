# SoundText — Notazione Testuale Semplificata

**Italiano** · [English](README.en.md) · [Français](README.fr.md) · [Español](README.es.md)

Implementazione funzionante dell'MVP descritto nelle *Specifiche di
Progetto — Player Musicale v1.2* (nome originale del progetto, ora
**SoundText**): un motore musicale che separa intenzione astratta
(accordi/note simboliche), voicing concreto (dipendente dallo strumento) e
playback (MIDI), con una GUI desktop per Linux, Windows e macOS — tema scuro coerente,
evidenziazione sintattica live, scorciatoie da tastiera e mixer con
codifica colore per famiglia strumentale.

## Terminologia

- **SoundText Language**: il linguaggio testuale con cui si scrive la
  partitura (note, accordi, percussioni, pattern...).
- **ST-Syntax**: la grammatica formale del SoundText Language (token,
  regole di sintassi, vedi sezione 2 della guida utente).
- **SoundText Engine**: il motore interno che risolve un accordo astratto
  in note MIDI concrete in base allo strumento (il "motore di voicing").
- **.st**: estensione dei file progetto.

## Guida completa

Il menu **Aiuto → Guida utente** dentro l'app mostra la documentazione
completa (anche disponibile qui: `docs/HELP.md`), incluse le istruzioni di
installazione per Debian/Ubuntu, Arch/CachyOS, Fedora e openSUSE.

## Cosa implementa

- **Grammatica completa** (ST-Syntax): note minuscole a-g, accordi astratti
  MAIUSCOLI (`Cmaj7`, `Am`, `G7`...), eventi percussivi testuali, pause `r`,
  blocchi simultanei `[...]`, moltiplicatori di durata, ottave `*n`, cambio
  griglia ritmica `N:` / `NT:` (terzine), cambio velocity `N@`. Le durate si
  accumulano lungo la timeline; la `|` facoltativa e' un controllo di
  battuta (non suona: se non cade su una stanghetta, secondo la metrica del
  progetto, avvisa quale battuta non torna e di quanto), e `//` apre un
  commento fino a fine riga (sezione 2.10 della guida). Le durate si possono
  scrivere anche come valori di nota (`c'8.` croma puntata), piu' voci nella
  stessa traccia con `{ voce1 ; voce2 }` e il testo cantato fra virgolette
  (`"Ma- ri- a"`), sezioni 2.11-2.13.
- **Automazioni**: volume, espressione, pan, modulazione e mandate degli
  effetti che cambiano nel tempo, anche durante una nota tenuta
  (`vol=0 >>exp 4c vol=100`, `pan=-1 >> c d pan=1`), con rampe a curva
  (`>>exp`, `>>log`, `>>s`) e forcelle sulle note (`2c<`, `c'2>`):
  si sentono, finiscono nel MIDI e in partitura (sezione 2.15). Anche
  qualunque controller MIDI (`cc74=`) e il pitch bend (`bend=`).
- **Legature e swing**: legature di valore anche oltre la stanghetta
  (`2f~ | 2f`), legature di portamento suonate legate e disegnate in
  partitura (`c( d e f)`), swing di crome e semicrome (`swing=62`),
  sezione 2.16.
- **Ritornelli e segni**: ritornelli con le caselle (`|: ... |1. ... :|
  |2. ... ||`) scritti come tali in partitura, accenti, corone, trilli,
  mordenti e gruppetti che si sentono (`c$fermata`, `d$tr`), indicazioni
  di testo (`$"rit."`), sezione 2.17.
- **Ottave relative e tonalita'**: `rel:` scrive le melodie senza ottave
  (ogni nota va vicino alla precedente, `*+` e `*-` per saltare), `key=G`
  da' alle note le alterazioni della tonalita' (`n` per il bequadro); un
  pulsante riscrive cosi' una traccia esistente, sezione 2.18.
- **Micro-tempo, accordatura, MTXT**: `shift=-10` anticipa o ritarda le note
  di pochi millisecondi senza cambiare il ritmo scritto, `tune=-20` accorda
  lo strumento in cent (anche con le rampe); oltre 15 tracce il MIDI usa
  piu' porte, cosi' ogni traccia ha il suo canale; import ed export in
  [MTXT](https://github.com/Daninet/mtxt), sezione 2.19.
- **Ancore di battuta**: `bar=29` porta il cursore all'inizio della battuta
  29 (con i silenzi che servono) e avvisa se la traccia e' gia' oltre,
  sezione 2.20.
- **Trasposizione**: `transpose=2` trasporta le note che seguono, `%Tema+7`
  suona un pattern una quinta sopra (le alterazioni seguono la tonalita'),
  sezione 2.21; vale anche per i file della libreria MIDI (`&"Basso"+7`).
- **Levare e `reset:`**: la battuta in levare (`Levare: 1`) sposta la
  battuta 1 dove deve stare; `reset:` riporta lo stato iniziale; il file
  dichiara la versione (`ST: 2.7`) e accetta anche le parole chiave
  inglesi, sezione 2.22.
- **Accordi, abbellimenti, D.C./D.S. e strofe (ST 2.7)**: nuovi accordi
  (`C7#5`, `Cm11`, `C69`, `Cmaj7#11`...) e percussioni (`triangle`,
  `agogo_hi`...), note di abbellimento (`d'g c`), segni `$arp`, `$sfz`,
  `$trem`, sigle senza suono (`$Am7`), `$segno`/`$coda`/`$fine`/`$dc`/`$ds`,
  piu' strofe di testo, titolo e autori, tonalita' per battuta e strumenti
  traspositori nella partitura, sezione 2.23.
- **Specifica formale e libreria autonoma**: la notazione e il formato `.st`
  sono descritti in [docs/spec/ST-language.it.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.it.md)
  (CC BY 4.0, anche in inglese) con una suite di conformita'; il motore e' la
  libreria Python `st_language`, senza dipendenze, che si installa con
  `pip install st-language` e offre i comandi `st-language check | midi | musicxml`
  (sezione 2.14 della guida).
- **Stato Corrente** (sezione 4): griglia e velocity persistono lungo la
  scansione sequenziale della traccia.
- **Percussioni e Drum Kit** (sezione 5): 36 identificatori mappati sul
  General MIDI Drum Map — kit base (kick, snare, hihat, hihat_open, tom1,
  tom2, floor, crash, ride, kick2, rimshot, clap), altri tom/piatti/hi-hat
  (snare2, hihat_pedal, tom_lowmid, tom_hi, tom_highfloor, china, ride_bell,
  tambourine, splash, cowbell, crash2, ride2) e percussioni latine (bongo_hi,
  bongo_low, conga_mute, conga_open, conga_low, timbale_hi, timbale_low,
  cabasa, maracas, claves, woodblock_hi, woodblock_low).
- **Pattern universali** (sezione 6): libreria `%Nome` riutilizzabile su
  qualsiasi strumento, con espansione ricorsiva e persistenza dello stato.
- **Motore di voicing automatico** (Visione del prodotto): converte un
  accordo astratto in note concrete in base al profilo dello strumento
  (Piano/Chitarra: voicing esteso; Basso: fondamentale+quinta; Tromba:
  monofonico sulla fondamentale), adattando le note al registro suonabile.
  Suffisso opzionale `.stile` (es. `Cmaj7.drop2`, `C7.cagEd`, `C.power`)
  per forzare uno stile di voicing specifico, con priorità sull'algoritmo
  automatico e fallback intelligente sull'equivalente generico più vicino
  se lo stile richiesto non ha senso per lo strumento della traccia.
  **Doppio click su un accordo** (compatto o già congelato in note
  esplicite) nell'editor traccia/pattern apre un menu con le alternative
  di voicing sensate per lo strumento, navigabile con le frecce con
  anteprima audio di ciascuna, Invio/click per applicare, Esc/click fuori
  per annullare.
- **Congelamento voicing → note esplicite**: pulsante in GUI che sostituisce
  ogni accordo con il blocco `[...]` di note concrete generate.
- **Timeline comune e mixaggio**: Solo/Mute/Volume/Pan per traccia, engine
  di sintesi condiviso, le tracce non si sincronizzano con le stanghette
  (le durate si accumulano sulla timeline: la `|` controlla, non sposta).
- **Editor con validazione sintattica live** e **autocompletamento** dei
  token (qualità d'accordo, stili di voicing, percussioni/dinamiche,
  riferimenti `%pattern` e `&"midi"`).
- **Struttura brano** (vista alternativa a box, `Ctrl+Shift+B`): ogni
  traccia diventa una riga su un asse del tempo condiviso, con il
  contenuto suddiviso in box trascinabili orizzontalmente — utile per
  lavorare sulla struttura del brano (intro/verse/chorus...) invece che
  nota per nota. Import MIDI/audio dividono automaticamente il risultato
  in più box dove il brano fa una pausa lunga. Undo/redo dedicato
  (`Ctrl+Z`/`Ctrl+Y`), generazione batteria/basso direttamente in un
  nuovo box, esportazione/importazione di un singolo box come file
  `.box`, anteprima Play/Pausa del box selezionato e testina di
  riproduzione durante l'esecuzione dell'intero brano.
- **Import/Export MIDI standard** (best-effort per l'import: le note
  vengono quantizzate sulla griglia, le sovrapposizioni diventano voci
  `{ ; }` nella stessa traccia e il testo cantato, anche dei file karaoke,
  testo fra virgolette).
- **Export della partitura in MusicXML** (Progetto → Esporta → Partitura MusicXML):
  una parte per traccia con note, sigle degli accordi, tonalita', metrica,
  tempo, dinamiche e batteria su pentagramma a percussione, da aprire e
  stampare con MuseScore, Finale, Sibelius o Dorico (sezione 10.1 della guida),
  con le voci dei blocchi `{ ; }` e il testo cantato.
- **Partitura dentro SoundText** (Vista → Partitura, `Ctrl+Shift+P`): le tracce
  su pentagramma, aggiornate mentre scrivi, impaginate da Verovio;
  esportazione in PDF e stampa senza programmi esterni (sezione 10.1bis).
- **Import di partiture MusicXML** (Progetto → Importa → MusicXML, anche
  `.mxl`): una traccia per parte, strumenti traspositori all'altezza reale,
  ritornelli, finali, D.C./D.S./Coda svolti, piu' voci nella stessa
  traccia, testo cantato, sigle degli accordi in una traccia Accordi
  (sezione 10.2 della guida).
- **Notazione ABC** (Progetto → Importa → ABC / Esporta → Partitura ABC): il
  formato di testo delle raccolte di musica tradizionale, di abcjs ed
  EasyABC, in entrambe le direzioni: voci, strumenti, tonalita', metrica,
  tuplet, ritornelli e finali, sigle e testo cantato (sezione 10.3 della
  guida).
- **Plugin esterni VST3 e LV2**: come effetti nella catena di una traccia o
  del master, o come strumenti virtuali che suonano le note di una traccia
  al posto del SoundFont. I plugin girano in un processo separato, cosi'
  uno che si blocca non ferma l'app (sezione 8.7 della guida).
- **Interfaccia in quattro lingue**: italiano, inglese, francese e
  spagnolo (Opzioni → Lingua), con la guida utente tradotta nelle stesse
  lingue. Il formato dei file `.st` e la notazione restano uguali in tutte
  le lingue.
- **5 strumenti iniziali**: Piano, Chitarra, Basso, Tromba, Batteria, piu'
  **strumenti personalizzati** definibili dall'utente (menu Suoni).
- **Tracce modificabili**: rinomina e cambio strumento in qualsiasi momento
  (doppio click sulla testata della traccia, o menu ⋯).
- **Import/Export MIDI per singola traccia**, oltre che per l'intero
  ensemble.
- **Libreria MIDI riutilizzabile** (cartella `midi/`, anche con
  sottocartelle per categoria): file `.mid` richiamabili in una traccia con
  `&"Nome"` (ricerca ricorsiva) o `&"Sottocartella/Nome"` (percorso esplicito),
  con supporto alla ripetizione (`2&"Nome"`).
  Gestibili (vedi/modifica/importa/rinomina/elimina) dalla GUI analogamente
  ai pattern.
- **Cartella `songs/`** come posizione predefinita per aprire/salvare i
  propri progetti, distinta da `examples/` (progetti dimostrativi).
- **Caricamento automatico degli strumenti personalizzati**: se una song usa
  uno strumento non ancora presente in locale, la sua definizione (salvata
  dentro al file `.st` stesso) viene registrata automaticamente
  all'apertura, senza perdere tracce ne' richiedere passaggi manuali.
- **Riconoscimento strumento in import MIDI**: se un canale usa esattamente
  il Program Change GM di uno strumento gia' disponibile lo riusa, altrimenti
  **crea e registra automaticamente un nuovo strumento personalizzato** con
  quel programma (nome/parametri suggeriti dalla famiglia General MIDI),
  cosi' l'import e' sempre fedele allo strumento originale invece di
  limitarsi al piu' vicino approssimato. L'utente viene avvisato con
  l'elenco dei nuovi strumenti creati.
- **Pattern con ripetizione** (`3%Nome`). La vecchia sintassi di
  trasposizione inline (`%Nome/2`) non esiste piu': per trasporre un box
  si usa **Trasponi...** dal menu tasto destro della vista Struttura brano.
- **Guida utente integrata** (menu Aiuto), con istruzioni di installazione
  per le principali distribuzioni Linux, per Windows e per macOS.
- **Riproduzione con rendering offline** (fluidsynth + SoundFont renderizzato
  in WAV prima della riproduzione, per evitare crepitii da underrun del
  driver audio), con SoundFont configurabile e diagnostica del motore in uso.
  Con la libreria FluidSynth (usata direttamente), il rendering usa un'unica
  istanza di fluidsynth persistente per tutta la sessione (SoundFont
  caricato in memoria una sola volta invece che ad ogni Play): latenza di
  avvio molto piu' bassa, stessa strategia anti-crepitio (rendering resta
  offline su file, non sull'output audio in tempo reale). Ripiega
  automaticamente sul binario CLI `fluidsynth` se il binding non e'
  installato. Con anche `sounddevice` il brano renderizzato viene
  riprodotto direttamente e tenuto in cache: **pausa/ripresa e salti
  istantanei** (click sulla barra di avanzamento o sul righello della
  Struttura brano) e **loop A-B** di una sezione (menu Riproduzione → Loop).
- **Interfaccia curata**: tema scuro coerente su finestra principale e
  dialoghi, evidenziazione sintattica live nell'editor (colori per
  note/accordi/percussioni/comandi di stato/riferimenti, basati sul
  tokenizer reale del parser), scorciatoie da tastiera, tooltip diffusi,
  mixer con codifica colore per famiglia strumentale e stato vuoto guidato.
  Durante la riproduzione l'editor scorre automaticamente (solo quando
  serve) per tenere sempre visibile il token in esecuzione.
- **Riorganizzazione automatica con pattern**: estrazione di blocchi
  ripetuti in pattern riutilizzabili, o espansione di tutti i riferimenti
  in token letterali, senza alterare il contenuto musicale (verificato con
  test di round-trip su tutti i progetti di esempio).
- **Ascolto diretto** di un pattern (con scelta dello strumento di anteprima)
  o di un file della libreria MIDI, direttamente dai rispettivi dialoghi di
  gestione.
- **Volume di traccia incisivo (0-200%)**: scala direttamente la velocity
  delle note in esportazione/riproduzione (non solo il Channel Volume MIDI,
  spesso poco percepibile), con margine di boost fino al 200% per far
  emergere strumenti deboli nel missaggio.
- **Persistenza del mixer**: Volume/Pan/Mute/Solo di ogni traccia vengono
  salvati nel file `.st` e ripristinati alla riapertura (prima si
  perdevano ad ogni salvataggio).
- **Importazione audio (voce/microfono/file)**: registrazione da microfono
  o caricamento (anche via drag-and-drop) di un file `.wav`/`.mp3`/`.m4a`,
  convertito automaticamente in notazione testuale con motore di
  quantizzazione configurabile (griglia 1/4-1/32, terzine 8T/16T). Pitch
  detection per tracce melodiche/armoniche (segmentazione via rilevamento
  attacchi dedicato, affidabile anche in registro grave e sul canto legato,
  con stima dell'altezza per mediana robusta a vibrato/imprecisioni di
  intonazione), transient detection con classificazione
  kick/snare/hihat per tracce percussive, con anteprima d'ascolto prima di
  confermare; il testo generato viene sempre validato prima
  dell'inserimento nella traccia o nel pattern (menu **Traccia → Importa in questa traccia → Audio → notazione...**, voce "Importa audio → note" del menu ⋯ della traccia, o dal dialogo di gestione
  pattern). Casella **"Sorgente: voce/beatbox"** per quando si canta/
  canticchia la parte invece di registrare lo strumento vero: ricalibra
  l'analisi sulle caratteristiche acustiche della voce umana invece che
  su quelle dello strumento di destinazione.

Non implementato in questa prima versione (indicato nel documento come fase
successiva o fuori standard MVP): importazione via OMR da spartiti
tradizionali.

## Requisiti

- Linux, Windows o macOS, con Python 3.10+
- Un sintetizzatore MIDI di sistema per l'ascolto diretto in-app (uno tra
  `fluidsynth` con un SoundFont GM, `timidity`, `wildmidi`). Senza di essi
  l'app può comunque esportare MIDI standard riproducibile con qualunque
  player esterno. Con la libreria di sistema `libfluidsynth` (installata
  insieme al pacchetto `fluidsynth` della distribuzione, vedi sotto)
  SoundText usa il motore di rendering persistente a bassa latenza (vedi
  sopra), senza pacchetti Python in piu'.
- Per convertire audio (microfono o file .mp3/.m4a/.flac/.ogg/.wav) in
  notazione: i file li legge il decodificatore di Qt Multimedia, gia'
  incluso in PySide6 (il programma `ffmpeg` serve solo come ripiego, se il
  PySide6 in uso non lo include); il microfono richiede la libreria di
  sistema `libportaudio2` su Linux (per il pacchetto pip `sounddevice`, che
  serve anche alla riproduzione diretta con loop e salti). Se manca
  qualcosa, **Traccia → Importa in questa traccia → Audio → notazione...** lo segnala con un messaggio
  esplicito invece di fallire silenziosamente.
- **(Opzionale)** Tracce audio: `libportaudio2` (con `sounddevice`) serve
  anche a registrare voce, chitarra o tastiera dalla scheda audio
  (Traccia → Registra nella traccia audio...); i file mp3/m4a/flac/ogg si
  importano come i `.wav`, ricampionati a 48 kHz.
## Installazione

Il codice si scarica con `git clone https://github.com/openssound/soundtext.git` (oppure **Code → Download ZIP** su GitHub). I pacchetti pronti (AppImage, installer per Windows, versioni portable) sono nelle [Release](https://github.com/openssound/soundtext/releases), quando ne viene pubblicata una.

Scegli il metodo adatto al tuo sistema. Per **plugin e amplificatori NAM** serve poi scaricare i plugin gratuiti (`scarica_strumenti`) e i profili NAM (menu **Strumenti → Scarica profili NAM consigliati...**): non sono inclusi. Serve una connessione a Internet.

| Sistema | Come installare | Dopo l'installazione |
|---|---|---|
| **Linux (consigliato)** | dal repository: `./install.sh` (installa FluidSynth, PortAudio, lilv col package manager, crea il virtualenv, aggiunge comando `soundtext` e voce di menu; `--yes` senza domande, `--uninstall` per rimuoverlo) | `~/.local/share/soundtext/scarica_strumenti.sh` |
| **Linux, AppImage** | scarica `SoundText-linux-*.AppImage`, `setup-appimage.sh` e `scarica_strumenti.sh`/`.py` nella stessa cartella, poi `./setup-appimage.sh` (installa FUSE 2, FluidSynth, SoundFont GM, PortAudio, lilv e le librerie di Qt; `--integra` aggiunge la voce di menu) | `./scarica_strumenti.sh` |
| **Linux, portable** (`.tar.gz`) | estrai e lancia `./setup-portable-linux.sh` (stesse librerie di sistema, senza FUSE), poi `./SoundText` | `./scarica_strumenti.sh` |
| **Windows, installer** (`SoundText-setup-*.exe`) o **portable** (`.zip`) | esegui l'installer, oppure estrai lo zip e lancia `setup-windows.bat` (controlla il Visual C++ Redistributable e Python; FluidSynth è già incluso), poi `SoundText.exe` | `scarica_strumenti.bat` |
| **macOS** | dal repository: `./install-macos.sh` (installa con Homebrew FluidSynth, PortAudio e Python, crea il virtualenv) | `~/Library/Application Support/SoundText/scarica_strumenti.sh` |

`scarica_strumenti.sh`/`.bat` richiedono Python 3.8+ installato (non serve per usare l'app). `./scarica_strumenti.sh` senza argomenti elenca i gruppi; `host` installa 7-Zip, sfizz e Surge XT; `libreria` compila il motore SFZ interno (circa 5 minuti).

### Installazione manuale dal sorgente

```bash
git clone https://github.com/openssound/soundtext.git
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# opzionale, per l'ascolto diretto in-app:
sudo apt install fluidsynth fluid-soundfont-gm   # Debian/Ubuntu

# opzionale, per l'ascolto diretto con loop e il microfono:
sudo apt install libportaudio2                   # Debian/Ubuntu

# opzionale, per i plugin LV2 (Linux; i VST3 non richiedono altro):
sudo apt install liblilv-0-0                     # Debian/Ubuntu
```

Istruzioni dettagliate per Debian/Ubuntu, Arch/CachyOS, Fedora, openSUSE,
**Windows e macOS** (inclusa l'installazione di fluidsynth e di un
SoundFont) nel menu **Aiuto → Guida utente** dentro l'app, o in
`docs/HELP.md`.

## Avvio

Su Linux/macOS, e su Windows da Git Bash, lo script `run.sh` crea al primo avvio il virtualenv `venv/`
con le dipendenze di `requirements.txt` (le aggiorna quando il file cambia)
e avvia l'app; accetta gli stessi argomenti di `main.py`:

```bash
./run.sh
./run.sh examples/ensemble_demo.st
```

Con le dipendenze gia' installate si puo' anche avviare direttamente:

```bash
python3 main.py
# oppure aprendo direttamente un progetto di esempio:
python3 main.py examples/ensemble_demo.st
```

La lingua dell'interfaccia si sceglie in **Opzioni → Lingua** (la prima
volta SoundText usa quella del sistema, se e' una delle quattro
disponibili, altrimenti l'inglese).

## Uso rapido

1. **+ Aggiungi traccia → Traccia con strumento...**: scegli uno strumento
   (Piano/Guitar/Bass/Trumpet/Drums) e assegnagli un nome. Dallo stesso menu
   si creano tracce audio o tracce gia' generate (batteria, giro armonico...).
2. Passa alla vista **Testo** e seleziona la traccia nella colonna Tracce a sinistra:
   si apre l'editor a destra.
3. Scrivi la notazione, es.:
   ```
   16: 100@ 4c*4 4e*4 4g*4 4e*4
   ```
   La validazione sintattica appare sotto l'editor in tempo reale.
4. Usa Solo/Mute/Volume/Pan sulla striscia della traccia per il mixaggio.
5. **Componi → Gestisci libreria pattern (%Nome)...** per definire `%Nome` riusabili
   su qualsiasi traccia.
6. **▶ Play** per l'ascolto (richiede un synth di sistema), **Progetto → Esporta → MIDI...** per salvare il file `.mid`, **Progetto → Esporta → Partitura MusicXML...** per aprire il brano in MuseScore, Finale,
   Sibelius o Dorico e stamparlo.
7. **Progetto → Salva** salva nel formato testuale nativo `.st`,
   leggibile/modificabile anche a mano.

## Test

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

I test girano anche automaticamente su GitHub a ogni push (workflow
`.github/workflows/tests.yml`).

## Struttura del progetto

```
soundtext/
  st_language/           (la libreria ST-language vive nel repository openssound/st-language: pip install, vedi requirements.txt)
  core/
    instruments.py     profili strumento + mappa percussioni GM + catalogo General MIDI
    chords.py           -> st_language/chords.py (stesso modulo)
    notation.py          -> st_language/notation.py (stesso modulo)
    completion.py         autocompletamento dei token nell'editor
    model.py              Project/Track, logica Solo/Mute, rinomina/cambio strumento
    project_io.py          formato progetto testuale (.st) + cartella songs/
    tempo_map.py           -> st_language/timing.py (stesso modulo)
    arrangement.py         box della vista Struttura brano (durate, appiattimento)
    rhythm_generate.py     generazione algoritmica di batteria, basso e accompagnamento
    key_detect.py          stima della tonalita' del brano
    midi_convert.py         analisi MIDI condivisa, indicizzazione libreria &"Nome"
    midi_export.py          export MIDI multitraccia o di singola traccia
    midi_import.py           import MIDI -> notazione (con riconoscimento strumento)
    musicxml_import.py       import di partiture MusicXML (anche .mxl) -> notazione
    abc_import.py            import di brani ABC -> notazione
    voice_merge.py           voci di un canale importato unite in blocchi { ; }
    import_lyrics.py         testo cantato dagli import MIDI (anche karaoke) e MusicXML
    score_render.py          partitura impaginata da Verovio (SVG per la vista e il PDF)
    playback.py               engine di riproduzione (rendering offline + SoundFont + cache)
    audio_stream.py           riproduzione diretta del rendering (salto, loop A-B, posizione esatta)
    metronome_sounds.py       suoni del click del metronomo
    settings.py                impostazioni persistenti (percorso SoundFont, quantizzazione, lingua)
    i18n.py                    lingue dell'interfaccia (tr() e i cataloghi di locales/)
    reorganize.py               estrazione/espansione automatica dei pattern
    audio_quantize.py            motore di quantizzazione audio -> notazione
    audio_decode.py               lettura file audio (Qt Multimedia, ripiego ffmpeg)
    fluid.py                      collegamento diretto alla libreria FluidSynth
    audio_recorder.py              registrazione da microfono (sounddevice)
    audio_pitch.py                  pitch detection per tracce melodiche
    audio_percussion.py              transient detection per tracce percussive
    audio_dsp.py                      analisi audio in numpy (attacchi SuperFlux, pitch YIN)
    audio_import.py                   pipeline completa import audio -> notazione
    midi_input.py                      tastiera MIDI esterna (mido + python-rtmidi)
  gui/
    main_window.py     finestra principale (editor, menu, toolbar); le sue parti in
                       main_window_project.py / _mixer.py / _playback.py
    arrangement_view.py vista Struttura brano (box, righello, testina, loop)
    keyboard_play_dialog.py "Suona con la tastiera" (registrazione dalla tastiera del PC)
    midi_keyboard.py    tastiera MIDI esterna nello stesso dialogo (core/midi_input.py)
    rhythm_generate_dialog.py dialoghi Genera batteria/basso/accompagnamento
    metronome_engine.py  click del metronomo sincronizzato con la riproduzione
    track_header.py     testata della traccia (M/S/●, ⋯, manopole Vol/Pan), uguale nelle due viste
    knob.py             manopola compatta per volume e pan
    track_widget.py     codifica colore per famiglia strumentale, etichetta del pan
    instrument_dialog.py gestione strumenti personalizzati (selezione GM per nome)
    midi_library_dialog.py gestione libreria MIDI (sottocartelle incluse)
    audio_import_dialog.py registrazione/caricamento audio + quantizzazione
    voicing_picker.py       menu di scelta voicing su doppio click sugli accordi
    help_dialog.py       guida utente integrata
    highlighter.py         evidenziazione sintattica (basata sul tokenizer reale)
    theme.py                foglio di stile scuro globale dell'applicazione
  locales/              traduzioni dell'interfaccia (en, fr, es) ed extract.py
  assets/
    icon.png              icona dell'applicazione
  examples/            progetti .st dimostrativi delle funzionalita'
  songs/                cartella predefinita per i tuoi progetti (Apri/Salva)
  midi/                 libreria di frammenti MIDI richiamabili con &"Nome",
                        organizzabile in sottocartelle (Guitar/, Blues/, ...)
  tests/                test automatici del motore di notazione
  main.py                punto di ingresso dell'app (applica tema + icona)
  diagnose_audio.py       strumento diagnostico da riga di comando per calibrare
                          pitch detection/classificazione percussiva su registrazioni
                          reali (vedi 'python3 diagnose_audio.py --help')
```

## Licenza

Copyright © 2026 Sergio Scolaro.

SoundText è software libero: puoi ridistribuirlo e/o modificarlo secondo
i termini della **GNU General Public License versione 3** (file
[LICENSE](LICENSE)). È distribuito nella speranza che sia utile, ma
**senza alcuna garanzia**.

SoundText usa librerie e contenuti di terze parti (FluidSynth, Qt/PySide6,
pedalboard, NumPy, il SoundFont FluidR3_GM e altri), ciascuno con
la propria licenza: autori, licenze e testi integrali sono in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) e nella cartella
[licenses/](licenses/). La guida (Aiuto → Guida utente, capitolo 14)
spiega cosa comportano queste licenze per chi distribuisce il programma.
