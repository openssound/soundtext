# SoundText

[Italiano](README.md) · **English** · [Français](README.fr.md) · [Español](README.es.md)

**SoundText** is a program for writing music as text. Notes, chords and
rhythms are written in a simple language, the **SoundText Language**;
SoundText plays them, shows them as a score and mixes them with effects,
amplifiers and plugins. It runs on Linux, Windows and macOS, in English,
Italian, French and Spanish.

```
ST: 2.7
Tempo: 100 BPM

Track Chords [Piano]:
  4: 4C | 4Am | 4F | 4G |

Track Melody [Piano]:
  8: e g c*5 g e g c*5 g | a c*5 e*5 c*5 a c*5 e*5 c*5 |
  f a c*5 a f a c*5 a | g b d*5 b 4g |

Track Drums [Drums]:
  8: [kick hihat] hihat [snare hihat] hihat [kick hihat] hihat [snare hihat] hihat |
```

Capital letters are chords (`C`, `Am`, `G7`): SoundText picks the right
notes for the track's instrument by itself. Lowercase letters are notes,
`*5` is the octave, `8:` the base length, `|` the end of the bar.

## What you can do

- **Write music**: notes, chords with automatic or chosen voicing,
  triplets, ties, dynamics, automation, repeats, several voices in the same
  track, lyrics. As you type, the editor colours the syntax and flags
  errors.
- **Arrange the song**: the **Structure** view shows each track as a row of
  boxes (intro, verse, chorus...) to move, copy and play one at a time.
  **Patterns** (`%Name`) and the **MIDI library** (`&"Name"`) let you reuse
  parts.
- **Generate parts**: drums, bass, accompaniment and melodies from the
  chords, without AI, also in the style of your own songs.
- **Shape the sound**: mixer, SoundFonts, SFZ sampled instruments, effects
  (EQ, compressor, delay, reverb), guitar amplifiers and **NAM** profiles of
  real amplifiers, **VST3** and **LV2** plugins, mastering.
- **Play and record**: the computer keyboard or a MIDI keyboard; audio
  tracks for voice and guitar, with multiple takes, loop and punch-in; from
  an audio recording to notes.
- **Import and export**: MIDI, MusicXML (MuseScore, Finale, Sibelius,
  Dorico), ABC, MTXT, WAV; the score can be viewed and printed to PDF
  right in the program.

Everything is explained in the **user guide**, inside the program (**Help →
User guide**, F1) and in [docs/HELP.en.md](docs/HELP.en.md).

## Installation

### Ready-made packages

From the [Releases](https://github.com/openssound/soundtext/releases/latest) download the package for your system:

| System | What to download | Then |
|---|---|---|
| **Windows** | `SoundText-setup-<version>.exe` (installer) | run it; on the last page leave ticked the box that runs `setup-windows.bat`, which checks the Visual C++ Redistributable |
| **Windows**, portable | `SoundText-windows-<version>.zip` | extract, run `setup-windows.bat`, then `SoundText.exe` |
| **Linux**, AppImage | `SoundText-linux-<version>.AppImage` and `setup-appimage.sh`, in the same folder | `./setup-appimage.sh` (installs with `sudo` FUSE 2, FluidSynth, PortAudio, lilv and the Qt libraries; `--integra` adds the menu entry and the `soundtext` command), then start the AppImage |
| **Linux**, portable | `SoundText-linux-portable-<version>.tar.gz` | extract, run `./setup-portable-linux.sh` (the same libraries, without FUSE; `--integra` here too), then `./SoundText` |

### From the code

For macOS, which has no ready-made package, or to follow updates with git.
The scripts also work when downloaded on their own: they fetch the sources
from GitHub.

- **Linux**: `./install.sh` installs the system libraries (apt, dnf,
  pacman or zypper), copies the program to `~/.local/share/soundtext`,
  creates the virtualenv, the `soundtext` command and the menu entry. Run
  again, it updates. `--yes` without questions, `--uninstall` removes the
  command and the menu entry (projects stay), `--purge` deletes the
  projects too.
- **macOS**: `./install-macos.sh` installs Homebrew if it is missing, then
  FluidSynth, PortAudio and Python; it creates the virtualenv, the
  `soundtext` command and **SoundText.app** in `~/Applications`. Same
  options as `install.sh`.
- **By hand**, with Python 3.10 or later and the system's FluidSynth,
  PortAudio and lilv (the packages for each distribution are in the
  guide):

  ```bash
  git clone https://github.com/openssound/soundtext.git
  cd soundtext
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  python3 main.py
  ```

The full instructions are in chapters 30-32 of the user guide.

### After installing

The **General MIDI SoundFont** is not included: on first start SoundText
offers to download it (FluidR3 GM, about 150 MB). From the same window,
**Sounds → Download and install...**, present in every version, you can
also download the SFZ sampled instruments, the free plugins, the NAM
profiles and the IR cabinets. An Internet connection is needed.

If you prefer the terminal, the `scarica_strumenti.sh` and
`scarica_strumenti.bat` scripts in the program folder (except with the
AppImage, where you use the window) do the same job and
need Python 3.8+ (without arguments they show a numbered menu).

## Starting

Ready-made packages start from the Start menu (installer), from
`SoundText.exe`, from the AppImage or from `./SoundText`; after the
install scripts, from the applications menu or with the `soundtext`
command. From the code:

```bash
./run.sh                                # Linux, macOS, Git Bash on Windows
./run.sh examples/funk_in_mi.st         # opening an example right away
```

On first start `run.sh` creates the `venv/` virtualenv with the
dependencies in `requirements.txt` and updates them when the file changes.

Choose the language in **Options → Language**; the first time SoundText
uses the system language, if it is one of the four available, otherwise
English.

## First steps

1. **Project → Open example...** opens one of the songs in the `examples/`
   folder: listen with **F5** and see how it is written in the **Text**
   view.
2. Chapter 1.2 of the guide, **Your first song**, goes in five steps from
   an empty project to four bars with chords and a melody.
3. The full grammar is in chapter 4 of the guide; the
   [SoundText Language specification](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md)
   (CC BY 4.0) describes it formally.

Projects are saved as plain-text `.st` files, readable and editable in any
editor; the default folder is `songs/`.

## For developers

**Tests**:

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

They also run on GitHub on every push (`.github/workflows/tests.yml`).

**Project layout**:

```
soundtext/
  main.py          the program's entry point
  core/            the engine: project model, .st files, MIDI, playback,
                   effects, plugins, audio import, part generation
  gui/             the interface (PySide6): main window, Structure view,
                   Effects panel, dialogs
  docs/            the user guide (HELP.md and its translations)
  locales/         the interface translations
  examples/        example songs
  songs/           the default folder for your projects
  midi/            the MIDI library (&"Name"), also in subfolders
  tests/           the automated tests
```

The notation is the **st-language** Python library (repository
[openssound/st-language](https://github.com/openssound/st-language),
`pip install st-language`): an engine with no dependencies, with the
`st-language check | midi | musicxml` commands, usable without SoundText
too.

## Licence

Copyright © 2026 Sergio Scolaro.

SoundText is free software: you can redistribute it and/or modify it under
the terms of the **GNU General Public License version 3** (file
[LICENSE](LICENSE)). It is distributed in the hope that it will be useful,
but **without any warranty**.

SoundText uses third-party libraries and content (FluidSynth, Qt/PySide6,
pedalboard, NumPy and others), each with its own licence: authors,
licences and full texts are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
and in the [licenses/](licenses/) folder. Chapter 29 of the guide explains
what these licences mean for anyone distributing the program.
