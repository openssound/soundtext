# SoundText

**Italiano** · [English](README.en.md) · [Français](README.fr.md) · [Español](README.es.md)

**SoundText** è un programma per scrivere musica come testo. Note, accordi
e ritmi si scrivono in un linguaggio semplice, il **SoundText Language**;
SoundText li suona, li mostra in partitura e li mixa con effetti,
amplificatori e plugin. Funziona su Linux, Windows e macOS, in italiano,
inglese, francese e spagnolo.

```
ST: 2.7
Tempo: 100 BPM

Traccia Accordi [Piano]:
  4: 4C | 4Am | 4F | 4G |

Traccia Melodia [Piano]:
  8: e g c*5 g e g c*5 g | a c*5 e*5 c*5 a c*5 e*5 c*5 |
  f a c*5 a f a c*5 a | g b d*5 b 4g |

Traccia Batteria [Drums]:
  8: [kick hihat] hihat [snare hihat] hihat [kick hihat] hihat [snare hihat] hihat |
```

Le maiuscole sono accordi (`C`, `Am`, `G7`): SoundText sceglie da solo le
note giuste per lo strumento della traccia. Le minuscole sono note, `*5`
l'ottava, `8:` la durata di base, `|` la fine della battuta.

## Cosa puoi fare

- **Scrivere la musica**: note, accordi con il voicing automatico o scelto,
  terzine, legature, dinamiche, automazioni, ritornelli, più voci nella
  stessa traccia, testo cantato. Mentre scrivi, l'editor colora la sintassi
  e segnala gli errori.
- **Organizzare il brano**: la vista **Struttura** mostra ogni traccia come
  una fila di box (intro, strofa, ritornello...) da spostare, copiare e
  ascoltare uno per uno. I **pattern** (`%Nome`) e la **libreria MIDI**
  (`&"Nome"`) servono a riusare le parti.
- **Generare le parti**: batteria, basso, accompagnamento e melodie a
  partire dagli accordi, senza IA, anche nello stile dei tuoi brani.
- **Dare forma al suono**: mixer, SoundFont, strumenti campionati SFZ,
  effetti (EQ, compressore, delay, riverbero), amplificatori per chitarra e
  profili **NAM** di amplificatori veri, plugin **VST3** e **LV2**,
  mastering.
- **Suonare e registrare**: la tastiera del computer o una tastiera MIDI;
  tracce audio per voce e chitarra, con riprese multiple, loop e punch-in;
  da una registrazione audio alle note.
- **Importare ed esportare**: MIDI, MusicXML (MuseScore, Finale, Sibelius,
  Dorico), ABC, MTXT, WAV; la partitura si vede e si stampa in PDF
  direttamente dal programma.

Tutto è spiegato nella **guida utente**, dentro il programma (**Aiuto →
Guida utente**, F1) e in [docs/HELP.md](docs/HELP.md).

## Installazione

### Pacchetti pronti

Dalle [Release](https://github.com/openssound/soundtext/releases/latest) scarica il pacchetto per il tuo sistema:

| Sistema | Cosa scaricare | Poi |
|---|---|---|
| **Windows** | `SoundText-setup-<versione>.exe` (installer) | eseguilo; nell'ultima pagina lascia spuntata la casella che lancia `setup-windows.bat`, che controlla il Visual C++ Redistributable |
| **Windows**, portable | `SoundText-windows-<versione>.zip` | estrai, lancia `setup-windows.bat`, poi `SoundText.exe` |
| **Linux**, AppImage | `SoundText-linux-<versione>.AppImage` e `setup-appimage.sh`, nella stessa cartella | `./setup-appimage.sh` (installa con `sudo` FUSE 2, FluidSynth, PortAudio, lilv e le librerie di Qt; `--integra` aggiunge la voce di menu e il comando `soundtext`), poi avvia l'AppImage |
| **Linux**, portable | `SoundText-linux-portable-<versione>.tar.gz` | estrai, lancia `./setup-portable-linux.sh` (le stesse librerie, senza FUSE; anche qui `--integra`), poi `./SoundText` |

### Dal codice

Per macOS, che non ha un pacchetto pronto, o per seguire gli aggiornamenti
con git. Gli script funzionano anche scaricati da soli: i sorgenti li
prendono da GitHub.

- **Linux**: `./install.sh` installa le librerie di sistema (apt, dnf,
  pacman o zypper), copia il programma in `~/.local/share/soundtext`, crea
  il virtualenv, il comando `soundtext` e la voce di menu. Rilanciato,
  aggiorna. `--yes` senza domande, `--uninstall` toglie comando e menu (i
  progetti restano), `--purge` cancella anche i progetti.
- **macOS**: `./install-macos.sh` installa Homebrew se manca, poi
  FluidSynth, PortAudio e Python; crea il virtualenv, il comando
  `soundtext` e **SoundText.app** in `~/Applications`. Stesse opzioni di
  `install.sh`.
- **A mano**, con Python 3.10 o più recente e FluidSynth, PortAudio e lilv
  del sistema (i pacchetti per ogni distribuzione sono nella guida):

  ```bash
  git clone https://github.com/openssound/soundtext.git
  cd soundtext
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  python3 main.py
  ```

Le istruzioni complete sono nei capitoli 30-32 della guida utente.

### Dopo l'installazione

Il **SoundFont General MIDI** non è incluso: al primo avvio SoundText
propone di scaricarlo (FluidR3 GM, circa 150 MB). Dalla stessa finestra,
**Suoni → Scarica e installa...**, presente in tutte le versioni, si
scaricano anche gli strumenti campionati SFZ, i plugin gratuiti, i profili
NAM e le casse IR. Serve una connessione a Internet.

Chi preferisce il terminale ha gli script `scarica_strumenti.sh` e
`scarica_strumenti.bat`, nella cartella del programma (tranne che con
l'AppImage, dove si usa la finestra): fanno lo stesso
lavoro e richiedono Python 3.8+ (senza argomenti mostrano un menu
numerato).

## Avvio

I pacchetti pronti si avviano dal menu Start (installer), da
`SoundText.exe`, dall'AppImage o da `./SoundText`; dopo gli script di
installazione, dal menu delle applicazioni o con il comando `soundtext`.
Dal codice:

```bash
./run.sh                                # Linux, macOS, Git Bash su Windows
./run.sh examples/funk_in_mi.st         # aprendo subito un esempio
```

`run.sh` crea al primo avvio il virtualenv `venv/` con le dipendenze di
`requirements.txt` e le aggiorna quando il file cambia.

La lingua si sceglie in **Opzioni → Lingua**; la prima volta SoundText usa
quella del sistema, se è una delle quattro disponibili, altrimenti
l'inglese.

## Primi passi

1. **Progetto → Apri esempio...** apre uno dei brani della cartella
   `examples/`: ascoltalo con **F5** e guarda come è scritto nella vista
   **Testo**.
2. Il capitolo 1.2 della guida, **Il primo brano**, porta in cinque passi da
   un progetto vuoto a quattro battute con accordi e melodia.
3. La grammatica completa è nel capitolo 4 della guida; la
   [specifica del SoundText Language](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.it.md)
   (CC BY 4.0) la descrive in modo formale.

I progetti si salvano come file `.st` di testo, leggibili e modificabili
anche con un editor qualsiasi; la cartella predefinita è `songs/`.

## Per chi sviluppa

**Test**:

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

Girano anche su GitHub a ogni push (`.github/workflows/tests.yml`).

**Struttura del progetto**:

```
soundtext/
  main.py          punto di ingresso del programma
  core/            il motore: modello del progetto, file .st, MIDI, riproduzione,
                   effetti, plugin, import audio, generazione delle parti
  gui/             l'interfaccia (PySide6): finestra principale, vista Struttura,
                   pannello Effetti, dialoghi
  docs/            la guida utente (HELP.md e le traduzioni)
  locales/         le traduzioni dell'interfaccia
  examples/        brani di esempio
  songs/           la cartella predefinita per i tuoi progetti
  midi/            la libreria MIDI (&"Nome"), anche in sottocartelle
  tests/           i test automatici
```

La notazione è la libreria Python **st-language** (repository
[openssound/st-language](https://github.com/openssound/st-language),
`pip install st-language`): un motore senza dipendenze, con i comandi
`st-language check | midi | musicxml`, usabile anche senza SoundText.

## Licenza

Copyright © 2026 Sergio Scolaro.

SoundText è software libero: puoi ridistribuirlo e/o modificarlo secondo
i termini della **GNU General Public License versione 3** (file
[LICENSE](LICENSE)). È distribuito nella speranza che sia utile, ma
**senza alcuna garanzia**.

SoundText usa librerie e contenuti di terze parti (FluidSynth, Qt/PySide6,
pedalboard, NumPy e altri), ciascuno con la propria licenza: autori,
licenze e testi integrali sono in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) e nella cartella
[licenses/](licenses/). Il capitolo 29 della guida spiega cosa comportano
queste licenze per chi distribuisce il programma.
