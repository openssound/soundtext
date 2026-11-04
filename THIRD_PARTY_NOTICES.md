# Avvisi di terze parti — SoundText

SoundText, Copyright © 2026 Sergio Scolaro, è distribuito con la
licenza **GNU General Public License versione 3** (file `LICENSE`). Si appoggia ai componenti di terze parti
elencati qui sotto, ciascuno con la propria licenza. I testi integrali
delle licenze sono nel file `LICENSE` (GPL-3.0) e nella cartella
`licenses/`.

Per ogni componente sono indicati: autori (titolari del copyright),
licenza, dove trovarne i sorgenti e se è **incluso** nelle build di
SoundText (versioni portabili, AppImage, installer) oppure usato solo se
già presente sul computer.

Le versioni indicate sono quelle con cui è stato verificato l'elenco; le
build possono contenere versioni successive degli stessi componenti.

**Versioni esatte e sorgenti.** Ogni build (installer, zip, AppImage,
portabili) contiene `licenses/COMPONENTI.txt`, generato mentre la si
costruisce (`.github/scripts/avvisi_build.py`): le versioni esatte
dell'interprete Python e di ogni pacchetto incluso, con i testi di licenza
che quei pacchetti portano con sé e la licenza completa dell'interprete
(anche per il software che Python include: OpenSSL, libffi, SQLite, zlib
e altri). Quelle versioni dicono quali sorgenti corrispondono alla build:
i sorgenti di SoundText sono su <https://github.com/openssound/soundtext>,
al tag della versione; quelli dei componenti sui siti dei progetti
indicati qui sotto, a quelle versioni.

## Librerie Python

| Componente | Copyright | Licenza | Testo | Nelle build |
|---|---|---|---|---|
| [Python](https://www.python.org) 3 | Python Software Foundation | PSF License (il software incluso nell'interprete: le licenze di ciascuno) | `licenses/Python-PSF.txt`; la licenza completa dell'interprete della build in `licenses/COMPONENTI.txt` | sì (interprete incluso da PyInstaller) |
| [PySide6 / Qt for Python](https://www.qt.io/qt-for-python) 6.11 e [Qt](https://www.qt.io) 6 | The Qt Company Ltd. e altri contributori | LGPL-3.0 | `licenses/LGPL-3.0.txt` (con `LICENSE` per la GPL-3.0 a cui rimanda) | sì, come librerie separate e sostituibili |
| [FFmpeg](https://ffmpeg.org) (dentro PySide6, per il decodificatore di Qt Multimedia: lettura di mp3, m4a, flac, ogg) | FFmpeg developers | LGPL-2.1 o successiva (build LGPL fornita da Qt) | `licenses/LGPL-2.1.txt` | sì, come librerie separate e sostituibili |
| [ST-language](https://github.com/openssound/st-language) 2.11 (la notazione testuale e il formato `.st`, libreria separata dello stesso autore) | Sergio Scolaro | GPL-3.0-or-later (la specifica: CC BY 4.0) | `LICENSE` | sì (da PyPI, pacchetto `st-language`) |
| [NumPy](https://numpy.org) 1.26 | NumPy Developers; le build includono anche OpenBLAS, LAPACK e altre librerie, con i loro avvisi | BSD-3-Clause (NumPy) e licenze permissive delle librerie incluse | `licenses/numpy.txt` | sì |
| [mido](https://github.com/mido/mido) 1.3 | Ole Martin Bjørndalen | MIT | `licenses/mido.txt` | sì |
| [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) 1.5 (con [RtMidi](https://github.com/thestk/rtmidi) di Gary P. Scavone) | Christopher Arndt; Gary P. Scavone | MIT (RtMidi: licenza in stile MIT) | `licenses/python-rtmidi.md` | sì |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) 0.5 | Matthias Geier | MIT | `licenses/sounddevice.txt` | sì |
| [PortAudio](http://www.portaudio.com) (incluso in sounddevice su Windows e macOS; di sistema su Linux) | Ross Bencina, Phil Burk e altri | MIT | `licenses/PortAudio.txt` | sì su Windows e macOS |
| [Verovio](https://www.verovio.org) 6 (vista Partitura ed esportazione PDF) | RISM Digital Center, Laurent Pugin e altri contributori | LGPL-3.0 (i caratteri musicali inclusi: SIL Open Font License 1.1) | `licenses/LGPL-3.0.txt`, `licenses/OFL-1.1.txt` | sì, come libreria separata e sostituibile |
| [pedalboard](https://github.com/spotify/pedalboard) 0.9 | Spotify AB | GPL-3.0 | `LICENSE`, `licenses/pedalboard-NOTICE.txt` | sì |
| [JUCE](https://juce.com) (dentro pedalboard) | Raw Material Software Limited | GPL-3.0 | `LICENSE` | sì |
| [VST3 SDK](https://github.com/steinbergmedia/vst3sdk) (dentro pedalboard, tramite JUCE) | Steinberg Media Technologies GmbH | GPL-3.0 (nella versione inclusa in pedalboard) | `LICENSE` | sì |

Il pacchetto di pedalboard per Linux include inoltre, come librerie
condivise, **alsa-lib** (LGPL-2.1), **bzip2** (licenza bzip2, in stile
BSD), **FreeType** (FreeType License; *portions of this software are
copyright © The FreeType Project, www.freetype.org*) e **libpng**
(licenza libpng). I loro avvisi di copyright sono distribuiti con
pedalboard; i sorgenti sono sui siti dei rispettivi progetti.

## Programmi e librerie di sistema

| Componente | Copyright | Licenza | Testo | Nelle build |
|---|---|---|---|---|
| [FluidSynth](https://www.fluidsynth.org) (libreria e programma) | Peter Hanappe, Josh Green e altri | LGPL-2.1 o successiva | `licenses/LGPL-2.1.txt` | sì nelle build portabili (libreria separata e sostituibile); di sistema con `install.sh` |
| Dipendenze di FluidSynth nella build per Windows, dalla release ufficiale 2.4.7 di FluidSynth: GLib, libinstpatch, libintl (LGPL-2.1), libsndfile 1.2.2 con dentro libFLAC, libogg, libvorbis, libopus (BSD 3-Clause), mpg123 e LAME (LGPL), SDL 3 (zlib) | i rispettivi autori | LGPL-2.1 o successiva, BSD 3-Clause, zlib | `licenses/fluidsynth-windows.txt` (elenco e testi BSD e zlib), `licenses/LGPL-2.1.txt` | sì su Windows |
| Dipendenze di FluidSynth nel portabile Linux: le librerie che `build-linux-portable.sh` copia in `lib/` dal sistema di build (libsndfile, libinstpatch, readline, SDL2, PipeWire, FLAC, Vorbis, Opus, mpg123, LAME, libgcrypt, Berkeley DB e altre) | i rispettivi autori | LGPL, GPL-3.0 (readline), licenza Sleepycat (Berkeley DB 5.3), BSD, MIT e altre, tutte compatibili con la GPL-3.0 | `licenses/librerie-linux/`: per ognuna il file copyright del suo pacchetto Debian/Ubuntu ed `ELENCO.txt` con pacchetto e versione (sorgenti: `apt-get source` di quei pacchetti) | sì nel portabile Linux |
| [sfizioso](https://github.com/rullopat/sfizioso) (fork di [sfizz](https://github.com/sfztools/sfizz): il motore SFZ interno, libreria libsfizz), con le librerie che contiene: Abseil (Apache-2.0), atomic_queue, filesystem, invoke.hpp, SIMDe, pugixml, tunings (MIT), st_audiofile (BSD 2-Clause), cephes, cpuid, kiss_fft, spline, WavPack (BSD 3-Clause), libaiff (BSD), dr_libs, stb_vorbis (pubblico dominio o MIT), jsl (Boost 1.0), hiir (WTFPL), ThreadPool (zlib) | sfizz contributors; i rispettivi autori | BSD 2-Clause e le licenze permissive di ciascuna | `licenses/sfizioso.txt` (tutti i testi, generato da `.github/scripts/licenze_sfizioso.py`) | sì negli installer, nell'AppImage e nei portabili; altrimenti scaricata da `scarica_strumenti.py libreria` (release `libsfizz-*` di SoundText, con lo stesso file come `LICENSE-sfizz.txt`) |
| [lilv](https://drobilla.net/software/lilv) (plugin LV2) | David Robillard e altri | ISC | vedi sotto | no: usata se presente nel sistema |
| [ffmpeg](https://ffmpeg.org) (programma, ripiego per la lettura dei file audio se il PySide6 in uso non ha il decodificatore di Qt) | FFmpeg developers | LGPL-2.1 o GPL, secondo la build | sul sito di FFmpeg | no: programma esterno facoltativo |

Licenza ISC di lilv: *Permission to use, copy, modify, and/or distribute
this software for any purpose with or without fee is hereby granted,
provided that the above copyright notice and this permission notice
appear in all copies.* (Copyright 2007-2023 David Robillard
<https://drobilla.net>, 2008 Krzysztof Foltman.) SoundText non include
lilv: la carica dal sistema con ctypes, se c'è.

## Contenuti e codice derivato

| Componente | Copyright | Licenza | Testo | Nelle build |
|---|---|---|---|---|
| [NeuralAmpModelerCore](https://github.com/sdatkinson/NeuralAmpModelerCore): il calcolo dei profili `.nam` di `core/nam.py` segue il motore ufficiale | Steven Atkinson | MIT | `licenses/NeuralAmpModelerCore.txt` | sì (come codice derivato) |
| [neural-amp-modeler](https://github.com/sdatkinson/neural-amp-modeler): il segnale di riferimento per la loudness, `assets/nam_loudness_input.wav` | Steven Atkinson | MIT | `licenses/neural-amp-modeler.txt` | sì |
| [MTXT](https://github.com/Daninet/mtxt): la tabella dei nomi delle voci (`voice`) per i 128 programmi General MIDI in `st_language/mtxt.py` (libreria ST-language, repository openssound/st-language, che ne riporta l'avviso) viene dall'implementazione di riferimento | Dani Biró | MIT (o Apache-2.0, a scelta) | `licenses/mtxt.txt` | sì (come dati derivati) |

## Non inclusi

- I **profili NAM consigliati** (Strumenti → Scarica profili NAM
  consigliati) vengono dalla raccolta
  [pelennor2170/NAM_models](https://github.com/pelennor2170/NAM_models),
  licenza GPL-3.0: SoundText li scarica sul computer dell'utente, non li
  distribuisce.
- Le **casse IR consigliate** (Strumenti → Scarica casse IR per gli
  amplificatori NAM) sono il pacchetto BestPlugins Mega Pack 2 (Copyright
  © 2013 David Fau Casquel), licenza GPL-2.0 o successiva, dalla cartella
  `trunk/IR/BestPlugins_Amps` del repository di
  [Guitarix](https://github.com/brummer10/guitarix): SoundText le scarica
  sul computer dell'utente insieme al testo della licenza, non le
  distribuisce.
- I **SoundFont General MIDI** di Suoni → Scarica e installa: SoundText
  li scarica sul computer dell'utente, con il testo della licenza accanto,
  e non li distribuisce. **FluidR3 GM** (Copyright © 2000-2002, 2008 Frank
  Wen, licenza MIT, testo anche in `licenses/FluidR3_GM.txt`, dal
  pacchetto sorgente Debian fluid-soundfont, verificato con lo SHA-256), **MuseScore General** (S. Christian Collins, derivato da
  FluidR3, licenza MIT), **TimGM6mb** (Tim Brechbill e David Bolton,
  licenza GPL-2.0, dal pacchetto Debian timgm6mb-soundfont) e **FreePats
  GM, percussioni** (progetto FreePats, licenza GPL-3.0 con eccezione per
  l'uso musicale).
- Gli **strumenti SFZ** di Suoni → Scarica e installa, compresa
  l'**orchestra** (VSCO 2 CE e VCSL, CC0): SoundText li scarica dalle
  fonti originali sul computer dell'utente, non li distribuisce. Le
  licenze di ciascuno, e chi chiede l'attribuzione, sono in
  `docs/licenze_strumenti_sfz.md`.
- Il **motore NAM veloce** (plugin LV2 Neural Amp Modeler di Mike
  Oliphant, GPL-3.0) e i **plugin VST3 e LV2 gratuiti** di Scarica e
  installa: SoundText li scarica dalle release dei loro autori,
  controllandone lo SHA-256 dove c'è, e non li distribuisce.
- I **plugin VST3 e LV2** e i **SoundFont** scelti dall'utente hanno
  ciascuno la propria licenza: SoundText li carica ma non li include.

## Marchi

VST è un marchio registrato di Steinberg Media Technologies GmbH. Qt è un
marchio di The Qt Company Ltd. Gli altri nomi di prodotti citati sono
marchi dei rispettivi titolari. SoundText non è affiliato a nessuno di
loro, né da loro approvato.

## Strumenti di sviluppo (non inclusi nel programma)

PyInstaller (GPL-2.0 con eccezione per il bootloader, che non si estende
al programma impacchettato), pytest (MIT) e reportlab (BSD, per la guida
PDF) servono a costruire e verificare SoundText, ma non fanno parte del
programma distribuito.
