# SoundText — Simplified Text Notation

[Italiano](README.md) · **English** · [Français](README.fr.md) · [Español](README.es.md)

A working implementation of the MVP described in the *Project Specification —
Music Player v1.2* (the original name of the project, now **SoundText**): a
music engine that separates abstract intention (symbolic chords/notes),
concrete voicing (depending on the instrument) and playback (MIDI), with a
desktop GUI for Linux, Windows and macOS — a consistent dark theme, live
syntax highlighting, keyboard shortcuts and a mixer colour-coded by
instrument family.

## Terminology

- **SoundText Language**: the text language in which the score is written
  (notes, chords, percussion, patterns...).
- **ST-Syntax**: the formal grammar of the SoundText Language (tokens,
  syntax rules, see section 2 of the user guide).
- **SoundText Engine**: the internal engine that resolves an abstract chord
  into concrete MIDI notes according to the instrument (the "voicing
  engine").
- **.st**: extension of project files.

## Full guide

The **Help → User guide** menu inside the app shows the full documentation
(also available here: `docs/HELP.en.md`, the original Italian version is
`docs/HELP.md`), including installation instructions for Debian/Ubuntu,
Arch/CachyOS, Fedora and openSUSE.

## What it implements

- **Complete grammar** (ST-Syntax): lowercase notes a-g, UPPERCASE abstract
  chords (`Cmaj7`, `Am`, `G7`...), text percussion events, rests `r`,
  simultaneous blocks `[...]`, duration multipliers, octaves `*n`, rhythmic
  grid changes `N:` / `NT:` (triplets), velocity changes `N@`. Durations
  accumulate along the timeline; the optional `|` is a bar check (silent:
  it warns when it does not fall on a bar line, according to the project
  time signature, and tells which bar is short or long), and `//` starts a
  comment up to the end of the line (section 2.10 of the guide). Durations can
  also be written as note values (`c'8.` dotted eighth), several voices in
  the same track with `{ voice1 ; voice2 }` and lyrics in double quotes
  (`"Ma- ri- a"`), sections 2.11-2.13.
- **Automations**: volume, expression, pan, modulation and effect sends
  changing over time, even during a held note (`vol=0 >>exp 4c vol=100`,
  `pan=-1 >> c d pan=1`), with curved ramps (`>>exp`, `>>log`, `>>s`) and
  hairpins on notes (`2c<`, `c'2>`): you hear them, and they go into the
  MIDI and the score (section 2.15). Also any MIDI controller (`cc74=`)
  and the pitch bend (`bend=`).
- **Ties and swing**: ties even across the bar line (`2f~ | 2f`), slurs
  played legato and drawn in the score (`c( d e f)`), swing of eighths and
  sixteenths (`swing=62`), section 2.16.
- **Repeats and marks**: repeats with endings (`|: ... |1. ... :| |2. ...
  ||`) printed as such in the score, accents, fermatas, trills, mordents
  and turns that you can hear (`c$fermata`, `d$tr`), text indications
  (`$"rit."`), section 2.17.
- **Relative octaves and key**: `rel:` writes melodies without octaves
  (each note goes near the previous one, `*+` and `*-` to jump), `key=G`
  gives notes the key's accidentals (`n` for the natural); a button
  rewrites an existing track this way, section 2.18.
- **Micro-timing, tuning, MTXT**: `shift=-10` plays notes a few
  milliseconds early or late without changing the written rhythm,
  `tune=-20` tunes the instrument in cents (ramps included); beyond 15
  tracks the MIDI file uses more ports, so every track has its own
  channel; [MTXT](https://github.com/Daninet/mtxt) import and export,
  section 2.19.
- **Bar anchors**: `bar=29` moves the cursor to the start of bar 29 (with
  the silence needed) and warns if the track is already past it, section
  2.20.
- **Transposition**: `transpose=2` transposes the notes that follow,
  `%Theme+7` plays a pattern a fifth higher (accidentals follow the key),
  section 2.21; it works on MIDI library files too (`&"Bass"+7`).
- **Pickup bar and `reset:`**: the pickup bar (`Levare: 1`) puts bar 1
  where it belongs; `reset:` restores the initial state; the file declares
  its version (`ST: 2.7`) and also accepts English keywords, section 2.22.
- **Chords, grace notes, D.C./D.S. and verses (ST 2.7)**: new chords
  (`C7#5`, `Cm11`, `C69`, `Cmaj7#11`...) and drums (`triangle`,
  `agogo_hi`...), grace notes (`d'g c`), marks `$arp`, `$sfz`, `$trem`,
  chord symbols without sound (`$Am7`), `$segno`/`$coda`/`$fine`/`$dc`/`$ds`,
  several lyric verses, title and authors, key per bar and transposing
  instruments in the score, section 2.23.
- **Formal specification and standalone library**: the notation and the
  `.st` format are described in [docs/spec/ST-language.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md)
  (CC BY 4.0, also in Italian) with a conformance suite; the engine is the
  Python library `st_language`, with no dependencies, installed with
  `pip install git+https://github.com/openssound/st-language.git` and providing the `st-language check | midi | musicxml`
  commands (section 2.14 of the guide).
- **Current State** (section 4): grid and velocity persist along the
  sequential scan of the track.
- **Percussion and Drum Kit** (section 5): 36 identifiers mapped onto the
  General MIDI Drum Map — basic kit (kick, snare, hihat, hihat_open, tom1,
  tom2, floor, crash, ride, kick2, rimshot, clap), other toms/cymbals/hi-hats
  (snare2, hihat_pedal, tom_lowmid, tom_hi, tom_highfloor, china, ride_bell,
  tambourine, splash, cowbell, crash2, ride2) and Latin percussion (bongo_hi,
  bongo_low, conga_mute, conga_open, conga_low, timbale_hi, timbale_low,
  cabasa, maracas, claves, woodblock_hi, woodblock_low).
- **Universal patterns** (section 6): a `%Name` library reusable on any
  instrument, with recursive expansion and state persistence.
- **Automatic voicing engine** (Product vision): converts an abstract chord
  into concrete notes according to the instrument profile (Piano/Guitar:
  spread voicing; Bass: root+fifth; Trumpet: monophonic on the root),
  fitting the notes to the playable register. Optional `.style` suffix
  (e.g. `Cmaj7.drop2`, `C7.cagEd`, `C.power`) to force a specific voicing
  style, overriding the automatic algorithm, with a smart fallback to the
  closest generic equivalent if the requested style makes no sense for the
  track's instrument. **Double-clicking a chord** (compact or already frozen
  into explicit notes) in the track/pattern editor opens a menu with the
  voicing alternatives that make sense for the instrument, navigable with
  the arrows with an audio preview of each, Enter/click to apply, Esc/click
  outside to cancel.
- **Freezing voicing → explicit notes**: a GUI button that replaces every
  chord with the `[...]` block of generated concrete notes.
- **Common timeline and mixing**: Solo/Mute/Volume/Pan per track, shared
  synthesis engine, tracks are not synchronised by bar lines (durations
  accumulate on the timeline: `|` checks, it does not move anything).
- **Editor with live syntax validation** and **autocompletion** of tokens
  (chord qualities, voicing styles, percussion/dynamics, `%pattern` and
  `&"midi"` references).
- **Song structure** (alternative box view, `Ctrl+Shift+B`): each track
  becomes a row on a shared timeline, with its content divided into boxes
  that can be dragged horizontally — useful to work on the structure of the
  song (intro/verse/chorus...) instead of note by note. MIDI/audio imports
  automatically split the result into several boxes where the song has a
  long pause. Dedicated undo/redo (`Ctrl+Z`/`Ctrl+Y`), drum/bass generation
  directly into a new box, export/import of a single box as a `.box` file,
  Play/Pause preview of the selected box and a playhead while the whole song
  is playing.
- **Standard MIDI import/export** (best-effort for import: notes are
  quantised on the grid, overlaps become `{ ; }` voices in the same track
  and lyrics, karaoke files included, become lyrics in double quotes).
- **Score export to MusicXML** (Project → Export → MusicXML score): one part per
  track with notes, chord symbols, key, time signature, tempo, dynamics and
  drums on a percussion staff, to open and print with MuseScore, Finale,
  Sibelius or Dorico (section 10.1 of the guide), with the voices of `{ ; }`
  blocks and the lyrics.
- **Score inside SoundText** (View → Score, `Ctrl+Shift+P`): the tracks on
  staves, updated as you type, laid out by Verovio; PDF export and printing
  without external programs (section 10.1bis).
- **MusicXML score import** (Project → Import → MusicXML, also `.mxl`): one
  track per part, transposing instruments at concert pitch, repeats,
  endings and D.C./D.S./Coda unrolled, several voices in the same track,
  lyrics, chord symbols in a Chords track (section 10.2 of the guide).
- **ABC notation** (Project → Import → ABC / Export → ABC score): the text
  format of traditional music collections, abcjs and EasyABC, both ways:
  voices, instruments, key, time signature, tuplets, repeats and endings,
  chord symbols and lyrics (section 10.3 of the guide).
- **External VST3 and LV2 plugins**: as effects in the chain of a track or
  of the master, or as virtual instruments that play a track's notes
  instead of the SoundFont. Plugins run in a separate process, so one that
  hangs does not stop the app (section 8.7 of the guide).
- **Interface in four languages**: Italian, English, French and Spanish
  (Options → Language), with the user guide translated into the same
  languages. The `.st` file format and the notation are the same in every
  language.
- **5 starting instruments**: Piano, Guitar, Bass, Trumpet, Drums, plus
  user-definable **custom instruments** (Sounds menu).
- **Editable tracks**: rename and change instrument at any time
  (double-click the track header, or the ⋯ menu).
- **MIDI import/export for a single track**, as well as for the whole
  ensemble.
- **Reusable MIDI library** (`midi/` folder, also with subfolders by
  category): `.mid` files that can be recalled in a track with `&"Name"`
  (recursive search) or `&"Subfolder/Name"` (explicit path), with repetition
  support (`2&"Name"`). They can be managed (view/edit/import/rename/delete)
  from the GUI just like patterns.
- **`songs/` folder** as the default location to open/save your own
  projects, separate from `examples/` (demo projects).
- **Automatic loading of custom instruments**: if a song uses an instrument
  not yet present locally, its definition (saved inside the `.st` file
  itself) is registered automatically when opening it, without losing
  tracks or requiring manual steps.
- **Instrument recognition in MIDI import**: if a channel uses exactly the
  GM Program Change of an instrument already available it reuses it,
  otherwise it **automatically creates and registers a new custom
  instrument** with that program (name/parameters suggested by the General
  MIDI family), so the import is always faithful to the original instrument
  instead of settling for the closest approximation. The user is told the
  list of new instruments created.
- **Patterns with repetition** (`3%Name`). The old inline transposition
  syntax (`%Name/2`) no longer exists: to transpose a box, use
  **Transpose...** from the right-click menu of the Song structure view.
- **Built-in user guide** (Help menu), with installation instructions for
  the main Linux distributions, for Windows and for macOS.
- **Playback with offline rendering** (fluidsynth + SoundFont rendered to
  WAV before playback, to avoid crackling from audio driver underruns),
  with a configurable SoundFont and diagnostics of the engine in use. With the
  FluidSynth library (used directly), rendering uses a single persistent
  fluidsynth instance for the whole session (SoundFont loaded into memory
  once instead of at every Play): much lower start-up latency, same
  anti-crackling strategy (rendering stays offline to a file, not on the
  real-time audio output). It falls back automatically to the `fluidsynth`
  CLI binary if the binding is not installed. With `sounddevice` as well,
  the rendered song is played directly and kept in a cache: **instant
  pause/resume and jumps** (click on the progress bar or on the ruler of the
  Song structure) and **A-B loop** of a section (Playback → Loop menu).
- **Polished interface**: a consistent dark theme on the main window and
  dialogs, live syntax highlighting in the editor (colours for
  notes/chords/percussion/state commands/references, based on the parser's
  real tokenizer), keyboard shortcuts, tooltips everywhere, a mixer
  colour-coded by instrument family and a guided empty state. During
  playback the editor scrolls automatically (only when needed) to keep the
  token being played always visible.
- **Automatic reorganisation with patterns**: extraction of repeated blocks
  into reusable patterns, or expansion of all references into literal
  tokens, without altering the musical content (verified with round-trip
  tests on all example projects).
- **Direct listening** to a pattern (with a choice of preview instrument) or
  to a file of the MIDI library, straight from their management dialogs.
- **Effective track volume (0-200%)**: directly scales the velocity of the
  notes in export/playback (not just the MIDI Channel Volume, often barely
  noticeable), with boost headroom up to 200% to bring out weak instruments
  in the mix.
- **Mixer persistence**: Volume/Pan/Mute/Solo of each track are saved in the
  `.st` file and restored when reopening it (they used to be lost at every
  save).
- **Audio import (voice/microphone/file)**: recording from the microphone or
  loading (also via drag-and-drop) of a `.wav`/`.mp3`/`.m4a` file,
  automatically converted into text notation with a configurable
  quantisation engine (grid 1/4-1/32, triplets 8T/16T). Pitch detection for
  melodic/harmonic tracks (segmentation through dedicated onset detection,
  reliable even in the low register and on legato singing, with a pitch
  estimate by median robust to vibrato/intonation inaccuracies), transient
  detection with kick/snare/hihat classification for percussion tracks,
  with a listening preview before confirming; the generated text is always
  validated before being inserted into the track or pattern (**Track → Import into this track → Audio → notation...** menu, the "Import audio → notes" item of the track's ⋯
  menu, or from the pattern management dialog). **"Source: voice/beatbox"**
  box for when you sing/hum the part instead of recording the real
  instrument: it recalibrates the analysis on the acoustic features of the
  human voice instead of those of the destination instrument.

Not implemented in this first version (indicated in the document as a later
phase or outside the MVP standard): OMR import from traditional scores.

## Requirements

- Linux, Windows or macOS, with Python 3.10+
- A system MIDI synthesizer for direct listening in the app (one of
  `fluidsynth` with a GM SoundFont, `timidity`, `wildmidi`). Without them
  the app can still export standard MIDI playable with any external
  player. With the `libfluidsynth` system library (installed together with
  the distribution's `fluidsynth` package, see below) SoundText uses the
  low-latency persistent rendering engine (see above), with no extra Python
  packages.
- To convert audio (microphone or .mp3/.m4a/.flac/.ogg/.wav files) into
  notation: files are read by the Qt Multimedia decoder, already included
  in PySide6 (the `ffmpeg` program is only a fallback, if the PySide6 in use
  lacks it); the microphone requires the `libportaudio2` system library on
  Linux (for the pip package `sounddevice`, also used for direct playback
  with loop and jumps). If something is missing, **Track → Import into this track → Audio → notation...** reports it with an explicit message instead of failing
  silently.
- **(Optional)** Audio tracks: `libportaudio2` (with `sounddevice`) is also
  used to record vocals, guitar or keyboard from the audio interface
  (Track → Record into the audio track...); mp3/m4a/flac/ogg files are
  imported like `.wav` files, resampled to 48 kHz.

## Installation

Pick the method that fits your system. For **plugins and NAM amplifiers** you then need to download the free plugins (`scarica_strumenti`) and the NAM profiles (menu **Instruments → Download recommended NAM profiles...**): they are not bundled. An Internet connection is required.

| System | How to install | After installing |
|---|---|---|
| **Linux (recommended)** | from the repository: `./install.sh` (installs FluidSynth, PortAudio, lilv with the package manager, creates the virtualenv, adds the `soundtext` command and a menu entry; `--yes` for no questions, `--uninstall` to remove) | `~/.local/share/soundtext/scarica_strumenti.sh` |
| **Linux, AppImage** | download `SoundText-linux-*.AppImage`, `setup-appimage.sh` and `scarica_strumenti.sh`/`.py` into the same folder, then `./setup-appimage.sh` (installs FUSE 2, FluidSynth, GM SoundFont, PortAudio, lilv and the Qt libraries; `--integra` adds a menu entry) | `./scarica_strumenti.sh` |
| **Linux, portable** (`.tar.gz`) | extract and run `./setup-portable-linux.sh` (same system libraries, no FUSE), then `./SoundText` | `./scarica_strumenti.sh` |
| **Windows, installer** (`SoundText-setup-*.exe`) or **portable** (`.zip`) | run the installer, or extract the zip and run `setup-windows.bat` (checks the Visual C++ Redistributable and Python; FluidSynth is already bundled), then `SoundText.exe` | `scarica_strumenti.bat` |
| **macOS** | from the repository: `./install-macos.sh` (installs FluidSynth, PortAudio and Python with Homebrew, creates the virtualenv) | `~/Library/Application Support/SoundText/scarica_strumenti.sh` |

`scarica_strumenti.sh`/`.bat` need Python 3.8+ installed (not needed to use the app). `./scarica_strumenti.sh` with no arguments lists the groups; `host` installs 7-Zip, sfizz and Surge XT; `libreria` builds the internal SFZ engine (about 5 minutes).

### Manual installation from source

```bash
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# optional, for direct listening in the app:
sudo apt install fluidsynth fluid-soundfont-gm   # Debian/Ubuntu

# optional, for direct listening with loop and the microphone:
sudo apt install libportaudio2                   # Debian/Ubuntu

# optional, for LV2 plugins (Linux; VST3 plugins need nothing else):
sudo apt install liblilv-0-0                     # Debian/Ubuntu
```

Detailed instructions for Debian/Ubuntu, Arch/CachyOS, Fedora, openSUSE,
**Windows and macOS** (including the installation of fluidsynth and of a
SoundFont) in the **Help → User guide** menu inside the app, or in
`docs/HELP.en.md`.

## Starting the app

On Linux/macOS the `run.sh` script creates the `venv/` virtualenv at the
first start with the dependencies of `requirements.txt` (it updates them
when the file changes) and starts the app; it accepts the same arguments as
`main.py`:

```bash
./run.sh
./run.sh examples/ensemble_demo.st
```

With the dependencies already installed you can also start it directly:

```bash
python3 main.py
# or opening an example project directly:
python3 main.py examples/ensemble_demo.st
```

The interface language is chosen in **Options → Language** (the first
time, SoundText uses the language of the system if it is one of the four
available, otherwise English).

## Quick start

1. **+ Add track → Track with instrument...**: choose an instrument
   (Piano/Guitar/Bass/Trumpet/Drums) and give it a name. From the same menu
   you can create audio tracks or already generated tracks (drums, chord
   progression...).
2. Switch to the **Text** view and select the track in the Tracks column on
   the left: the editor opens on the right.
3. Write the notation, e.g.:
   ```
   16: 100@ c*4 e*4 g*4 e*4 Cmaj7 [kick hihat]
   ```
   Syntax validation appears below the editor in real time.
4. Use Solo/Mute/Volume/Pan on the track strip for mixing.
5. **Compose → Manage pattern library (%Name)...** to define
   reusable `%Name` patterns on any track.
6. **▶ Play** to listen (requires a system synth), **Project → Export → MIDI...** to save the `.mid` file, **Project → Export → MusicXML score...** to open the song in MuseScore, Finale, Sibelius or
   Dorico and print it.
7. **Project → Save** saves in the native `.st` text format, readable and
   editable by hand too.

## Tests

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

The tests also run automatically on GitHub at every push (workflow
`.github/workflows/tests.yml`).

## Project structure

```
soundtext/
  st_language/           (the ST-language library lives in the openssound/st-language repository: pip install, see requirements.txt)
  core/
    instruments.py     instrument profiles + GM percussion map + General MIDI catalogue
    chords.py           -> st_language/chords.py (same module)
    notation.py          -> st_language/notation.py (same module)
    completion.py         token autocompletion in the editor
    model.py              Project/Track, Solo/Mute logic, rename/change instrument
    project_io.py          text project format (.st) + songs/ folder
    tempo_map.py           -> st_language/timing.py (same module)
    arrangement.py         boxes of the Song structure view (durations, flattening)
    rhythm_generate.py     algorithmic generation of drums, bass and accompaniment
    key_detect.py          estimate of the key of the song
    midi_convert.py         shared MIDI analysis, &"Name" library indexing
    midi_export.py          multitrack or single-track MIDI export
    midi_import.py           MIDI import -> notation (with instrument recognition)
    musicxml_import.py       MusicXML score import (also .mxl) -> notation
    abc_import.py            ABC tune import -> notation
    voice_merge.py           voices of an imported channel merged into { ; } blocks
    import_lyrics.py         lyrics from MIDI (karaoke too) and MusicXML imports
    score_render.py          score laid out by Verovio (SVG for the view and the PDF)
    playback.py               playback engine (offline rendering + SoundFont + cache)
    audio_stream.py           direct playback of the rendering (jump, A-B loop, exact position)
    metronome_sounds.py       metronome click sounds
    settings.py                persistent settings (SoundFont path, quantisation, language)
    i18n.py                    interface languages (tr() and the locales/ catalogues)
    reorganize.py               automatic extraction/expansion of patterns
    audio_quantize.py            audio -> notation quantisation engine
    audio_decode.py               audio file reading (Qt Multimedia, ffmpeg fallback)
    fluid.py                      direct binding to the FluidSynth library
    audio_recorder.py              microphone recording (sounddevice)
    audio_pitch.py                  pitch detection for melodic tracks
    audio_percussion.py              transient detection for percussion tracks
    audio_dsp.py                      audio analysis in numpy (SuperFlux onsets, YIN pitch)
    audio_import.py                   complete audio -> notation import pipeline
    midi_input.py                      external MIDI keyboard (mido + python-rtmidi)
  gui/
    main_window.py     main window (editor, menus, toolbar); its parts in
                       main_window_project.py / _mixer.py / _playback.py
    arrangement_view.py Song structure view (boxes, ruler, playhead, loop)
    keyboard_play_dialog.py "Play with the keyboard" (recording from the PC keyboard)
    midi_keyboard.py    external MIDI keyboard in the same dialog (core/midi_input.py)
    rhythm_generate_dialog.py Generate drums/bass/accompaniment dialogs
    metronome_engine.py  metronome click synchronised with playback
    track_header.py     track header (M/S/●, ⋯, Vol/Pan knobs), the same in both views
    knob.py             compact knob for volume and pan
    track_widget.py     colour coding by instrument family, pan label
    instrument_dialog.py custom instrument management (GM selection by name)
    midi_library_dialog.py MIDI library management (subfolders included)
    audio_import_dialog.py audio recording/loading + quantisation
    voicing_picker.py       voicing choice menu on double-click on chords
    help_dialog.py       built-in user guide
    highlighter.py         syntax highlighting (based on the real tokenizer)
    theme.py                global dark style sheet of the application
  locales/              translations of the interface (en, fr, es) and extract.py
  assets/
    icon.png              application icon
  examples/            demo .st projects of the features
  songs/                default folder for your projects (Open/Save)
  midi/                 library of MIDI fragments recalled with &"Name",
                        can be organised in subfolders (Guitar/, Blues/, ...)
  tests/                automatic tests of the notation engine
  main.py                entry point of the app (applies theme + icon)
  diagnose_audio.py       command-line diagnostic tool to calibrate
                          pitch detection/percussion classification on real
                          recordings (see 'python3 diagnose_audio.py --help')
```

## Licence

Copyright © 2026 Sergio Scolaro.

SoundText is free software: you can redistribute it and/or modify it under
the terms of the **GNU General Public License version 3** (file
[LICENSE](LICENSE)). It is distributed in the hope that it will be useful,
but **without any warranty**.

SoundText uses third-party libraries and content (FluidSynth, Qt/PySide6,
pedalboard, NumPy, the FluidR3_GM SoundFont and others), each with
its own licence: authors, licences and full texts are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) (in Italian) and in the
[licenses/](licenses/) folder. The guide (Help → User guide, chapter 14)
explains what these licences mean for anyone distributing the program.
