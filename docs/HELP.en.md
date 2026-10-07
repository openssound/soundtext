# User guide — SoundText

## Topic index

Find the topic you need here, then go to the section shown (the numbers are those of the headings in this guide).

| Topic | Section |
| --- | --- |
| [The program window, command bar, views](#1.0) | [1.0](#1.0) |
| [Searching for a command (Ctrl+K) and keyboard shortcuts](#1.0bis) | [1.0bis](#1.0bis) |
| [Undo / Redo](#1.2) | [1.2](#1.2) |
| [Autosave and recovery](#1.2bis) | [1.2bis](#1.2bis) |
| [Interface language](#1.3) | [1.3](#1.3) |
| [Writing notes, chords, rests, durations, octaves, sharps and flats](#2) | [2](#2) |
| [Chord voicings and slash chords](#2.8) | [2.8](#2.8), [2.9](#2.9) |
| [Repetitions and triplets / quintuplets](#2.1) | [2.1](#2.1), [2.1bis](#2.1bis) |
| [Slides (pitch bend) and sustain pedal](#2.3) | [2.3](#2.3), [2.4](#2.4) |
| [Dynamics, crescendo and diminuendo](#2.5) | [2.5](#2.5) |
| [Tempo changes (accelerando, ritardando) and time signature changes](#2.6) | [2.6](#2.6), [2.7](#2.7) |
| [Song key and relative octaves](#2.7bis) | [2.7bis](#2.7bis), [2.18](#2.18) |
| [Bar checks (|) and comments (//)](#2.10) | [2.10](#2.10) |
| [Several voices in one track and sung lyrics](#2.12) | [2.12](#2.12), [2.13](#2.13) |
| [Automations (volume, pan... changing over time)](#2.15) | [2.15](#2.15) |
| [Ties, slurs, swing, repeats, marks and directions](#2.16) | [2.16](#2.16), [2.17](#2.17) |
| [Micro-timing, tuning, many tracks, MTXT](#2.19) | [2.19](#2.19) |
| [Bar anchors (bar=N)](#2.20) | [2.20](#2.20) |
| [Transposition (transpose=, %Name+N)](#2.21) | [2.21](#2.21) |
| [reset:, pickup bar, file version (ST 2.6)](#2.22) | [2.22](#2.22) |
| [Chords, grace notes, D.C./D.S., verses, title (ST 2.7)](#2.23) | [2.23](#2.23) |
| [Patterns (%Name): reusing and rearranging parts](#4) | [4](#4) |
| [MIDI library (&"Name") and the songs/ folder](#5) | [5](#5), [5bis](#5bis) |
| [Percussion and hand-written drums](#6) | [6](#6) |
| [Tracks and instruments, custom instruments](#7) | [7](#7) |
| [Mixer: volumes, pan, mute, solo and master volume](#8) | [8](#8), [8.1](#8.1), [8.2](#8.2) |
| [Synthesizer reverb and chorus](#8.3) | [8.3](#8.3) |
| [Effects: EQ, compressor, delay, reverb, noise gate, calibration loop](#8.4) | [8.4](#8.4) |
| [Guitar amplifier, distortion, cabinets and IR files](#8.4) | [8.4](#8.4) |
| [NAM profiles (real amps and pedals), where to download them](#8.4) | [8.4](#8.4) |
| [Mastering: effects on the master and limiter](#8.5) | [8.5](#8.5) |
| [Studio sounds with external programs (re-amping)](#8.6) | [8.6](#8.6) |
| [VST3 and LV2 plugins, internal SFZ instrument](#8.7) | [8.7](#8.7) |
| [Structure view (boxes): verses, choruses, moving and copying parts](#8bis) | [8bis](#8bis) |
| [Freezing chords, choosing the voicing, autocompletion](#9) | [9](#9), [9.1](#9.1), [9.2](#9.2) |
| [Generating drums, bass, accompaniment and riffs without AI](#9bis) | [9bis](#9bis) |
| [Personal styles (learning from your songs) and phrase-based melodies](#9bis.1) | [9bis.1](#9bis.1), [9bis.2](#9bis.2) |
| [Importing and exporting MIDI](#10) | [10](#10) |
| [MusicXML and ABC: exporting and importing scores](#10.1) | [10.1](#10.1), [10.2](#10.2), [10.3](#10.3) |
| [Viewing and printing the score](#10.1bis) | [10.1bis](#10.1bis) |
| [Audio import: from voice, microphone or file to notes](#10bis) | [10bis](#10bis) |
| [Playing with the computer keyboard or a MIDI keyboard](#10ter) | [10ter](#10ter) |
| [Audio tracks: recording voice and guitar, exporting](#10quater) | [10quater](#10quater) |
| [Saving the project (.st)](#11) | [11](#11) |
| [Playback, A-B loop, jumping to a point](#12) | [12](#12) |
| [Choosing the SoundFont, a SoundFont per instrument](#12.3) | [12.3](#12.3), [12.4](#12.4) |
| [Metronome and humanization](#12.5) | [12.5](#12.5), [12.6](#12.6) |
| [Log file (when something goes wrong)](#13.1) | [13.1](#13.1) |
| [Technologies, acknowledgements, licenses](#14) | [14](#14) |
| [Installation on Linux, Windows and macOS (at the end of the guide)](#inst) | [↓](#inst) |

---

## 0. Terminology

- **SoundText Language**: the text language in which the score is written
  (notes, chords, percussion, patterns, state commands...).
- **ST-Syntax**: the formal grammar of the SoundText Language — the syntax
  rules described in section 2.
- **SoundText Engine**: the engine that resolves an abstract chord (e.g.
  `Cmaj7`) into concrete MIDI notes, according to the track's instrument
  (often also called the "voicing engine" in this guide).
- **.st**: extension of project files.

## 1. Basic concepts

The program separates three levels: **abstract intention** (notes and
chords written in SoundText Language), **concrete voicing** (the SoundText
Engine, which depends on the instrument) and **playback** (MIDI engine).
Each track is associated with an instrument and contains a sequence of
*tokens* separated by spaces, following the ST-Syntax.

### 1.0 The window

- **Command bar**, from the left: the **transport** (back to the start,
  Play/Pause, Stop, **●** Record into the selected audio track, A-B loop,
  metronome), the **Song** block (tempo, time signature, key), the choice of
  the **Structure / Text** view and the **Master** volume. Hovering over a
  button shows what it does and its shortcut.
- **Progress bar**, full width below the command bar: elapsed time and
  length; click to jump to that point.
- **Song structure view** (8bis): the tracks as boxes, with the mixer in
  the row headers (8); or the **Text view**: the same headers in a column
  on the left and the notation of the selected track.

### 1.0bis Search for a command (Ctrl+K) and shortcuts

**Search for a command**: **Ctrl+K**, or the "Search for a command…" box at
the top right of the menu bar (also **Help → Search for a command...**).
Type what you want to do ("export", "record", "generate bass",
"metronome", "key"...), choose with the arrows and press Enter. All menu
items can be found, including those of "+ Add track"; next to each one are
the menu it belongs to and its shortcut. Upper case and accents do not
matter.

**Shortcuts in the Song structure view** (with the mouse or the focus on
the canvas; in the text editor these keys are used for typing). A reminder
is at the bottom right of the status bar.

| Key | Action |
|---|---|
| Space | Play / Pause the song (everywhere: F5) |
| Shift+Space | listen to the selected box only |
| R | record into the selected audio track (everywhere: Ctrl+R) |
| Del | delete the selected box |
| Ctrl+D | duplicate the selected box |
| S | split the selected audio clip at the playhead |
| Ctrl+wheel | horizontal zoom (the point under the mouse stays still) |
| Ctrl+= / Ctrl+- / Ctrl+0 | zoom in / zoom out / normal zoom (also from the View menu) |
| Ctrl+Z / Ctrl+Y | undo / redo |

The corresponding items are also in the **Edit** (delete, duplicate,
split), **View** (zoom) and **Playback** menus.

### 1.1 Syntax highlighting and shortcuts

The editor automatically colours each token according to its type: notes
(light blue), chords (amber), percussion (purple), state commands
`N:`/`N@` (green), `%pattern` and `&"midi"` references (coral), `[...]`
blocks (yellow), rests (grey). `//` comments are grey italic, `|` bar checks grey (red
and underlined when they do not fall on a bar line, see 2.10); `{ ; }` voice blocks are turquoise, lyrics pink italic, and inside
groups and voices every token has its own colour. The colours reflect exactly how the engine
interprets the text, so they also help you spot mistakes at a glance.

The track headers also have a border coloured by instrument family
(guitars, basses, brass...), useful to find your way quickly among many
tracks.

Main keyboard shortcuts: `Ctrl+N` new project, `Ctrl+O` open, `Ctrl+S`
save, `Ctrl+Shift+S` save as, `Ctrl+T` add track, `Ctrl+E` edit track,
`Ctrl+Z`/`Ctrl+Y` undo/redo, `F5` play/pause, `F6` stop, `Ctrl+[`/`Ctrl+]`
loop start/end, `Ctrl+L` loop on/off, `F1` this guide.

### 1.2 Undo/Redo

**Edit → Undo** (`Ctrl+Z`) and **Redo** (`Ctrl+Y` or `Ctrl+Shift+Z`) apply
to **every change to the project**, wherever it comes from: text typed in
the editor, tracks added, removed or renamed, mixer (volume, pan, mute,
solo, master), tempo, time signature and key, generated drums/bass,
MIDI/audio import or keyboard input into a track, patterns, chord freezing,
reorganisation, boxes of the Song structure view. Undoing also takes you
back to the track you were working on.

Continuous typing in the same track, or dragging a slider, becomes a
single step: a pause of a second and a half is enough to start a new one.
The history is cleared when you open or create a project. In dialogs
(editing a box, patterns...) the text has its own, independent Undo.

### 1.2bis Automatic saving and recovery

While the project has **unsaved changes**, SoundText writes a **recovery
copy** of it every minute (only if something changed in the meantime),
in the `recupero/` folder of the configuration. The project file is not
touched: saving remains your choice.

- When you save, open or create another project, or close SoundText
  normally (even choosing **Discard**), the copy is removed.
- If SoundText closes badly (crash, freeze, computer switched off), at the
  next start it asks whether to **recover** the project, showing the time
  of the copy and the original file. **Recover** reopens it as a modified
  project: **Save** (`Ctrl+S`) writes it to the original file, or choose
  **Save as**. **Delete the copy** deletes it, **Decide later** keeps it
  for the next start.
- Several SoundText windows open at the same time each have their own
  copy: a window that is still open is never offered for recovery.

Normal saving is also "all or nothing": SoundText first writes a temporary
file and puts it in place of the project only at the end, so an
interruption halfway through (full disk, power cut) does not leave a
truncated `.st` file.

### 1.3 Interface language

SoundText speaks **Italian, English, French and Spanish**. The language is
chosen in **Options → Language** and applies from the next start:
SoundText asks whether to restart right away (if there are unsaved
changes, it first asks you to save them). The first time, the system
language is used if it is one of the four, otherwise English.

Menus, windows, messages and this guide are in the chosen language. What
does **not change** is the notation (`c*4`, `Am7`, `kick`...) and the words
of the `.st` file (`Tempo:`, `Traccia`, `Effetti`...), which are the format
of the projects: a song written with the interface in Italian opens the
same way with the interface in English, and vice versa.

## 2. ST-Syntax (grammar of the SoundText Language)

| Construct | Meaning | Example |
| --- | --- | --- |
| lowercase letter a-g | melodic note | `c` |
| lowercase letter + `#` (sharp) or `b`/`♭` (flat) | altered note | `c#`, `eb`, `e♭` |
| `*n` after a note or chord | octave | `c*4`, `Cmaj7*3` |
| `/Note` after a chord | alternative bass ("slash chord") | `C/E` (C with E in the bass) |
| UPPERCASE letter + suffix | abstract chord | `Cmaj7`, `Am`, `G7` |
| `.style` after a chord | forces a specific voicing (see 2.8) | `Cmaj7.drop2`, `C.power` |
| lowercase word (36 percussion identifiers, see section 5) | percussion event | `kick` |
| leading number | duration multiplier | `2c`, `4Cmaj7` |
| `r` / `Nr` | rest (1 or N grid units) | `r`, `3r` |
| `[...]` | simultaneous events/notes | `[c*4 e*4 g*4]`, `[kick hihat]` |
| `N:` | changes the current rhythmic grid | `16:` (sixteenths) |
| `NT:` / `NQ:` / `NS:` | tuplets: triplets / quintuplets / septuplets (see 2.1bis) | `8T:`, `16Q:`, `8S:` |
| `N@` | changes the current velocity (1-127) | `100@` |
| `%Name` | calls a pattern | `%Rock1` |
| `&"Name"` | calls a MIDI file from the library | `&"Intro"` |
| `N(...)` | repetition group: repeats the enclosed sequence N times | `4(c d e f)` |
| `!` at the end of a note or chord | staccato (halves the audible length) | `c!`, `Cmaj7!` |
| `x` at the end of a note or chord | mute/stop (very short, "stopped" note) | `cx`, `Cmaj7x` |
| `_` at the end of a note or chord | legato (slightly lengthened note) | `c_`, `Cmaj7_` |
| `note>note[>note...]` | slide/portamento (continuous pitch bend between two or more notes) | `c*4>d*4`, `c*4>d*4>c*4` |
| `SON` / `SOFF` | sustain pedal: on/off for everything that follows | `SON c*4 SOFF` |
| `tempo=N` | sets the tempo (BPM) from this point on | `tempo=120` |
| `>>` after `tempo=N` | accelerando up to the next `tempo=N` | `tempo=100 >> c*4 tempo=140` |
| `<<` after `tempo=N` | rallentando up to the next `tempo=N` | `tempo=140 << c*4 tempo=80` |
| `pppp@`...`ffff@` | classical dynamics, equivalent to a fixed velocity | `mf@` = `75@` |
| `>>` after `N@`/dynamic | crescendo up to the next velocity value | `p@ >> c*4 ff@` |
| `<<` after `N@`/dynamic | diminuendo up to the next velocity value | `110@ << c*4 30@` |
| **\|** | bar check: a bar ends here (silent, warns if it does not add up, see 2.10) | `c d e f` **\|** `g a b c` **\|** |
| `//` | comment up to the end of the line (ignored) | `c d e f // verse` |
| `'N` after a token | explicit note value, without changing the grid (see 2.11) | `c'8.` (dotted eighth), `[c e g]'2`, `r'4`, `e'8T` |
| `{ ... ; ... }` | voices starting together in the same track (see 2.12) | `{ c*5 d*5 e*5 f*5 ; 4c*4 }` |
| `"..."` | lyrics: one syllable per note, on the notes before them (see 2.13) | `c d e 2f "Ma- ri- a, sei"` |
| `vol=N` `expr=N` `pan=N` `mod=N` `rev=N` `cho=N` | automations: volume, expression, pan (-1..1), modulation, reverb and chorus sends (see 2.15) | `vol=80`, `pan=-0.5` |
| `>>` after an automation | continuous ramp up to the next value with the same name; `>>exp`, `>>log`, `>>s` choose the curve | `vol=0 >>exp 4c vol=100` |
| `<` / `>` at the end of a note | crescendo / diminuendo during the held note (hairpin) | `2c<`, `c'2>` |
| `~` at the end of a note | tie: the note continues into the next identical one, even across the bar line (see 2.16) | `2c~ \| 2c` |
| `(` ... `)` at the end of notes | slur: the notes in between sound legato (see 2.16) | `c( d e f)` |
| `swing=N` / `swing16=N` | swing of the eighths / sixteenths (50 = straight, 66 = triplet feel) | `swing=62 8: c d e f` |
| `bar=N` | bar anchor: moves the cursor to the start of bar N, with the silence needed (see 2.20) | `bar=29 c d e f` |
| `transpose=N` | transposition: the following notes, chords and slides sound N semitones higher or lower (see 2.21); `%Name+N` transposes a pattern | `transpose=-2 c d e` |
| `\|:` ... `:\|` | repeat: the part between the two signs is played twice (see 2.17) | `\|: c d e f :\|` |
| `\|1.` `\|2.` `\|\|` | repeat endings: a different ending for each pass (see 2.17) | `\|1. g a :\| \|2. 4c \|\|` |
| `$mark` at the end of a note | accent, fermata, trill, mordent, turn, tenuto, marcato (see 2.17) | `c$fermata`, `d$tr`, `e$accent` |
| `$"text"` | indication above the staff | `$"rit."`, `$"dolce"` |
| `rel:` / `abs:` | relative octaves (each note goes near the previous one) / absolute (see 2.18) | `rel: c d e f g a b c` |
| `*+` / `*-` after a note (in `rel:`) | one octave up / down | `rel: g c*+ c*-` |
| `key=K` | notes take the accidentals of key K (see 2.18) | `key=G f` (= F sharp) |
| `n` after a note | natural: cancels the key's accidental | `key=G fn` |

The `|` character is the **bar check** (see 2.10): it makes no sound and
moves nothing, it only states where a bar ends. Durations accumulate along
the timeline anyway, so `|` is optional. In the `.st` project file the
character also appears in the header of a box of the "Song structure" view
(section 8bis), to give its position in beats, e.g.
`Box Basso1 "Intro" |4:` — a detail of the save format.

**Ramps must be closed**: a `>>`/`<<` ramp must always be closed by another
command **of the same type** (velocity after velocity, tempo after tempo)
before a command of the other type arrives, or before the end of the track
— otherwise validation reports an explicit error instead of leaving the
ramp "orphaned" (open but with no audible effect, a silent bug that is hard
to notice just by listening). A grid change (`N:`) in the middle of a ramp
already open neither closes nor breaks it — it can appear freely before the
note/chord that closes it.

### Flat: `b`, `♭` or `-` (typing shortcut)

A flat can be written with the letter `b` (e.g. `eb`), with the real music
symbol `♭` (e.g. `e♭`), or with a hyphen `-` (e.g. `e-`): they are three
perfectly equivalent synonyms for the parser, both on notes and on the root
of a chord (`Bb7` = `B-7` = `B♭7`). The letter `b` remains valid for
compatibility with what has been written so far, but it can be visually
ambiguous with the note letter `b` (B) — that is why **the editor
automatically replaces a `-` typed right after a note letter with `♭`**
(e.g. typing `e` then `-` shows `e♭`), so the correct symbol always appears
on screen without having to look for `♭` on the keyboard. The replacement
only happens when the `-` immediately follows a note letter at the start of
a token (after a space, `[`, `(`, `>`, or a multiplier digit): typing `-`
in any other context (e.g. after `snare`) stays a normal hyphen.

### Supported chord qualities
`(empty)`/`maj`, `m`/`min`, `7`, `maj7`, `m7`, `dim`, `dim7`, `aug`,
`sus2`, `sus4`, `6`, `m6`, `9`, `maj9`, `m9`, `mMaj7`, `m7b5`, `add9`,
`7sus4`, `7b9`, `7#9`, `5`, `7alt`, `11`, `13`, `maj13`, `°`, `°7`.

The last six are aliases or extensions meant for the notation you would
write "by ear" when reading a real chart:
- **`5`** (e.g. `E5`): power chord, root and fifth only, no third —
  equivalent to writing the chord with the `.power` voicing (`E.power`), but
  also recognised as a quality of its own (e.g. for MIDI import: a plain
  fifth being played is now recognised as `5`, instead of being left as an
  ambiguous explicit block).
- **`°`** / **`°7`** (e.g. `C°`, `C°7`): classical-notation aliases for
  `dim`/`dim7`, same intervals, same voicing.
- **`7alt`** (e.g. `G7alt`): altered dominant, approximated with the same
  intervals as `7b9` (the grammar does not model the individual altered
  tensions #9/#11/b13 separately).
- **`11`**, **`13`**, **`maj13`**: extensions beyond the ninth (`13` omits
  the 11th, as is common jazz practice to avoid the clash with the major
  third).

### 2.8 Explicit voicing on chords (`.style`)

An optional `.style` suffix after the chord quality (before any `/octave`)
forces the voicing engine to use a specific algorithm instead of the
instrument's automatic one:

```
Cmaj7          -> automatic voicing according to the track's instrument
Cmaj7.drop2    -> forces the Jazz Drop-2 voicing
C7.cagEd*3     -> E shape of the CAGED system, octave 3
```

**Priority**: when present, the suffix always takes precedence over the
instrument's automatic algorithm. **Smart fallback**: if a style makes no
sense for the track's instrument (e.g. `.barre` on a Piano), the engine
automatically replaces it with the closest generic equivalent (e.g.
`.close`) — it is never an error. An **unknown** style (a typo), on the
other hand, is reported by validation like any other unrecognised token.

General styles (valid on any instrument):
- `noroot`: omits the root.
- `shell`: omits the fifth.
- `close`: notes stacked as close as possible.
- `open`: open shape, notes spread over several octaves.
- `inv1` / `inv2` / `inv3`: 1st, 2nd or 3rd inversion (3rd, 5th, 7th in
  the bass respectively; if the chord does not have enough notes for the
  requested inversion, the highest available one is used).

Guitar styles (automatic fallback if used on other instruments):
`barre`, `Caged`/`cAged`/`caGed`/`cagEd`/`cageD` (the 5 shapes of the
CAGED system), `drop2`, `drop3`, `triad`, `power` (root+fifth), `openpos`
(approximation of first-position chords), `hendrix` (root alone in the bass
+ the rest an octave above), `top` (chord an octave higher), `bottom`
(root+fifth+seventh, without the third). The most common quality/style
combinations (e.g. `Cmaj7.drop2`, `C7#9.hendrix`) use a curated voicing
table for greater accuracy; the other combinations use an equivalent
generic algorithm. As for the rest of the engine, there is no real model of
strings/frets: these are musically sensible approximations on abstract MIDI
notes, not physical fingerings.

Keyboard styles (automatic fallback if used on other instruments): `left`
(left hand low root/fifth, right hand the rest), `right` (compact voicing
for the right hand only), `spread` (wide two-handed chord).

Valid examples: `Cmaj7`, `Cmaj7.drop2`, `C7.cagEd`, `C.power`,
`Am7.open`, `F.barre`.

### 2.9 Alternative bass on chords ("slash" chord)

An optional `/Note` suffix after the quality (and after any `.style`,
before any `*octave`) specifies a bass different from the root of the
chord — the classic "slash" notation of charts (`C/E` = C chord with E in
the bass):

```
C/E            -> C major with E in the bass
Dm7/G          -> D minor seventh with G in the bass
C.drop2/E*4    -> as above, drop2 voicing, octave 4
```

The voicing engine first computes the chord normally (root, quality,
style), then adds the requested bass note an octave below the resulting
voicing (going down further octaves if needed to stay below all the other
notes) — it is always the lowest note played, as in a real slash chord.
Transposing a chord with an alternative bass also shifts the bass by the
same number of semitones.

**Technical note**: `/` after a chord only indicates the alternative bass;
the octave is always written with `*n` (see sec. 2), also together with
the bass (`C/E*3`). The old form with digits after the slash (`C7/3`,
`c/4`) is no longer valid.

### 2.1 Repetition groups

A sequence of tokens enclosed in round brackets, preceded by a number, is
repeated that number of times:

```
4(2C7 2e c d 2A7)   -> repeats the sequence 4 times: 2C7 2e c d 2A7
```

Groups can be nested (`2(c 2(d e))`) and can contain any valid token,
including patterns and MIDI references.

### 2.1bis Tuplets (triplets / quintuplets / septuplets)

An optional letter after the number of a grid command (`N:`, section 3)
switches on an irregular grouping instead of the normal binary
subdivision, shortening each note proportionally:

| Letter | Tuplet | Ratio | Example |
| --- | --- | --- | --- |
| `T` | triplet | 3 notes in the space of 2 | `8T:` (eighth-note triplets: 3 in a quarter) |
| `Q` | quintuplet | 5 notes in the space of 4 | `16Q:` (sixteenth-note quintuplets: 5 in a quarter) |
| `S` | septuplet | 7 notes in the space of 4 | `8S:` (eighth-note septuplets: 7 in two quarters) |

```
8T: c d e            -> eighth-note triplet: the three notes fill a quarter
16Q: c d e f g       -> sixteenth-note quintuplet: the five notes fill a quarter
8S: c d e f g a b    -> eighth-note septuplet: the seven notes fill two quarters
```

As with the binary grid, the command stays active until it is changed again
(section 3): there is no need to repeat it before every single note of the
group. You can go back to the binary subdivision at any time with an `N:`
command without a letter (e.g. `16:` after `16Q:`).

### 2.2 Note (and chord) modifiers

A single character at the end of a note or a chord (after any `*n` octave,
and after any voicing `.style` on a chord) changes its articulation,
without altering the position of the following notes on the timeline (the
note/chord still takes up the whole grid unit, only how long it stays
audible changes):

- **`!` staccato**: plays for 50% of the nominal length, the rest is
  silence.
- **`x` mute**: it is "stopped" almost immediately (~15% of the nominal
  length), for a damped/percussive effect.
- **`_` legato**: it is lengthened slightly beyond the nominal length
  (~115%), so that it "ties" smoothly into the next one.

On chords it can be combined with explicit voicing (2.8), e.g.
`Cmaj7.drop2!` (Drop-2 voicing + staccato). The same modifier applied to a
chord acts on **all** the notes of the voicing, not just on the root. Note:
simultaneous `[...]` blocks do not support this final modifier yet; for a
"staccato power chord" use a named chord with the `.power` voicing, e.g.
`E.power!`.

### 2.3 Slide (pitch bend / portamento)

Two or more notes joined by `>` (without spaces) produce a continuous glide
in pitch from one to the other:

```
c*4>d*4        -> glides from C4 to D4 over one grid unit (like a note)
c*4>d*4>c*4    -> rises from C4 to D4 in one unit and comes back to C4 in
                  another (bend-and-release, 2 units in all)
```

There is a single rule: the multiplier of a step is the length of the ramp
that **starts** from that step towards the next one (1 if absent); the
multiplier of the **last** step is how long the note holds the pitch
reached (0 if absent: the slide ends as it arrives).

```
5c*4>d*4       -> slow ramp from C4 to D4 over 5 units
2c*4>3d*4      -> rises in 2 units, then holds D4 for another 3
                  (quick bend then held)
2c*4>2d*4>3c*4 -> rises in 2 units, falls in another 2, then holds
                  the arrival pitch for another 3
```

A chain can have as many steps as you like (`c*4>d*4>c#*4>c*4`...). A
slide that would last zero (`0c*4>d*4`) is an error.

Technically it is exported as a single MIDI note (a single note_on/note_off
for the whole chain) with a sequence of Pitch Bend messages that gradually
interpolate from one step to the next (with the pitch-bend range set
automatically via RPN so that slides even beyond an octave are covered
correctly). See also section 10 for how MIDI import automatically
recognises a bend (including a bend-and-release) in an existing file and
translates it into this syntax.

### 2.4 Sustain pedal (SON / SOFF)

The `SON` and `SOFF` tokens, placed freely in the flow of notes, switch the
sustain pedal (piano) on/off for everything that follows, until the
opposite command is found:

```
Piano — AcousticPiano:
  8: SON c*3 g*3 c*4 e*4 g*4 e*4 c*4 g*3 SOFF
  8: SON a*2 e*3 a*3 c*4 e*4 c*4 a*3 e*3 SOFF
```

If a `SOFF` is forgotten, the program still releases the pedal
automatically at the end of the track, so that no note stays stuck in an
endless reverb.

### 2.5 Classical dynamics and ramps (crescendo/diminuendo)

Besides the explicit numeric value (`100@`), velocity accepts the classical
dynamic markings:

| Marker | Velocity |
| --- | --- |
| `pppp@` | 10 |
| `ppp@` | 23 |
| `pp@` | 36 |
| `p@` | 49 |
| `mp@` | 62 |
| `mf@` | 75 |
| `f@` | 88 |
| `ff@` | 101 |
| `fff@` | 114 |
| `ffff@` | 127 |

By following a velocity value (numeric or dynamic) with `>>` (crescendo) or
`<<` (diminuendo), the velocity of the following notes is interpolated
linearly up to the next velocity value found:

```
8: p@ >> c*4 d*4 e*4 f*4 f@       -> crescendo from 49 to 88 over the 4 notes
8: 110@ << g*4 f*4 e*4 d*4 30@     -> diminuendo from 110 to 30
```

After the arrows you can choose the **curve** of the ramp: `>>exp` starts
slowly and speeds up, `>>log` starts fast and slows down, `>>s` is smooth
at both ends (`p@ >>exp c d e f ff@`). This also works for tempo ramps and
for automations (section 2.15).

### 2.6 Tempo changes (accelerando/rallentando)

Inside a track, the `tempo=N` command (1-999) sets the tempo (BPM)
instantly from that point on:

```
tempo=120 c*4 d*4    -> tempo set to 120 BPM
```

As for dynamics, `>>` (accelerando) or `<<` (rallentando) after an `tempo=N`
command gradually interpolates the tempo up to the next `tempo=N`:

```
tempo=100 >> c*4 d*4 e*4 f*4 tempo=140    -> accelerando from 100 to 140 BPM
tempo=140 << c*4 d*4 e*4 f*4 tempo=80      -> rallentando from 140 to 80 BPM
```

Note: tempo is by nature a concept shared by the whole project (all tracks
play on the same timeline); a tempo change declared in one track therefore
applies to the whole song from that point on, not just to that track.

### 2.7 Tempo and time signature changes by bar

Besides the simple form (`Tempo: 120 BPM`, `Metrica: 4/4`, a single value
for the whole song), the project header also accepts a list of changes
indexed by bar number:

```
Tempo: 1: 120, 5: 140, 9: 100
Metrica: 1: 4/4, 5: 3/4, 8: 4/4
```

It means: tempo 120 BPM from bar 1, 140 BPM from bar 5, 100 BPM from bar 9;
time signature 4/4 from bar 1, 3/4 from bar 5, 4/4 from bar 8. The
positions (in beats) of the bars after the first are computed automatically
taking into account the time signature in force in each section.

**Progress bar, highlighting and Tempo/Time sig. fields during playback**:
the exported MIDI file, the progress bar, the highlighting of the token
being played in the editor and the **Tempo (BPM)** and **Time sig.** fields
in the main toolbar all use the same tempo/time-signature map of the
project (all the changes by bar plus the inline `tempo=N` markers): so they
always show the value really in force at that point of the song, not an
estimate based on the initial tempo/time signature alone. Once playback
stops, the Tempo/Time sig. fields go back to the project's "resting" value
(the one of bar 1).

### 2.7bis Key of the song

The project header can also declare the key of the song (the line
`Tonalita: <value>`), which can also be set from the **Key** field in the
main toolbar, next to Tempo and Time sig.:

```
Tonalita: Am
```

Format: note letter (A-G) + optional accidental (`#` or `b`) + optional
`m` for minor, e.g. `C`, `F#`, `Ebm`, `Am` (major if `m` is missing). It is
descriptive/reference information (it does not affect voicing or chord
recognition); when importing a MIDI file that declares a key (*key
signature* meta event) it is recognised and set automatically. If the file
declares C major or declares nothing (C is the default value of many
sequencers, so it is not reliable), the key is estimated from the notes as
**Analyse key** does. It is also used by **Play with the keyboard**
(section 10ter) in the "Scale of the key" keyboard layouts.

If you do not know it already (or you are not sure), **Compose → Analyse
key...** estimates it automatically by analysing the notes actually written
in all the non-percussion tracks of the project (drums excluded), with the
classic Krumhansl-Schmuckler algorithm: it compares the distribution of the
12 pitch classes used (weighted by length) with the typical tonal profiles
of each of the 24 possible keys and chooses the most similar one, setting
it automatically in the Key field (overwriting any value already there). It
is a statistical estimate, not a real harmonic analysis: it can be wrong on
very short, chromatic or modulating songs — a good starting point, not an
infallible verdict. If the project contains no pitched notes (no tracks, or
only percussion ones), it says so instead of guessing.

### 2.10 Bar checks (`|`) and comments (`//`)

**Bar checks.** A `|` between two tokens states "a bar ends here". It makes
no sound and does not move time: the program only checks that there really
is a bar line at that point, according to the project **Time signature**
and its per-bar changes (section 2.7). It can also be attached to a note
(`d*4|`).

```
4: c d e f | g a b c | 2c 2e |
8: c d e f g a b c | 2: c c |
```

If a `|` does not fall on a bar line, the bar below the editor turns orange
and tells you which bar does not add up and by how much, for example
`bar 2: 1 eighth note missing` or `bar 3: 1 quarter note too many`; the
wrong `|` turns red and underlined. The tooltip on the bar lists all the
warnings. **It is not a syntax error**: the song plays and exports anyway,
it is a help to notice a missing note or a wrong duration. A missing note
shifts everything after it, but it is reported only once: the following
`|` are measured taking it into account and warn only if there is another
mistake.

- The bar lines are those of the **song**: in a box of the Song structure
  view they count from the box position (a box starting in the middle of a
  bar has its first `|` after half a bar).
- Inside a pattern or an `N(...)` group the `|` is checked at every
  repetition; the warning points at the `%Name` reference or the group.
- Inside a `[...]` block `|` is not allowed (syntax error).

**Comments.** From `//` to the end of the line the text is ignored: use it
to annotate sections, chords, ideas. A single slash (`C/E`, `&"Blues/bass"`)
keeps its usual meaning.

```
// Verse
4: Am | F | C | G |     // four-chord loop
```

Comments and line breaks are kept in the `.st` file, in boxes, in box
transposition and in chord freezing. They are not kept in pattern bodies
(saved as a sequence of tokens) nor by the operations that rewrite the
whole track text (Reorganize with patterns, Expand patterns). In the `.st`
file an empty line closes a block: empty lines inside a track text are
removed when saving (they used to truncate the rest of the track).

### 2.11 Explicit note values (`'8.`)

Besides the grid (`N:` followed by multipliers), a duration can be written
as a **note value**, with an apostrophe at the end of the token:

| Written | Value | Duration in quarters |
| --- | --- | --- |
| `c'1` | whole note | 4 |
| `c'2` | half note | 2 |
| `c'4` | quarter note | 1 |
| `c'8` | eighth note | 1/2 |
| `c'16`, `c'32`, `c'64` | sixteenth, thirty-second, sixty-fourth note | 1/4, 1/8, 1/16 |
| `c'4.` / `c'8.` | **dotted** quarter / eighth note | 1 1/2 / 3/4 |
| `c'2..` | double-dotted half note | 3 1/2 |
| `c'8T` / `c'4T` | **triplet** eighth / quarter note | 1/3 / 2/3 |
| `c'16Q`, `c'8S` | quintuplet, septuplet (like the `NQ:`, `NS:` grids) | |

```
8: c*4'8. d*4'16 e*4 e*4 [c e g]'2    // dotted rhythm without changing the grid
```

The value applies **only to that token**: the current grid stays the same
(in the example, `e*4 e*4` are eighth notes of the `8:` grid). It works
with notes, chords (`C7'2`), blocks (`[c e g]'2`), rests (`r'4`),
percussion (`kick'16`) and slides. A multiplier in front adds up: `2c'8`
lasts two eighth notes. The articulation can go before or after: `c'8!`
and `c!'8` are the same staccato eighth note. The grid stays handy for
regular rhythms; the explicit value is more readable for irregular
phrases and for those who come from sheet music.

### 2.12 Several voices in the same track (`{ ; }`)

A **voice block** holds two or more sequences, separated by `;`, that
**start together**, each with its own durations. The block lasts as long
as the longest voice, then the track goes on:

```
4: { c*5 d*5 e*5 f*5 ; 4c*4 } g*4           // melody over a held note
4: {
  8: e*5 d*5 c*5 d*5 e*5 e*5 2e*5            // right hand
  ;
  2c*4 2g*3                                  // left hand
}
```

Unlike `[...]`, where everything starts and ends together, each voice has
its own rhythm: that is what you need for two-handed piano, a melody over
a held chord, classical guitar.

- Each voice starts with the **state** (grid, velocity) of the point where
  the block opens; changes made **inside** a voice stay there.
- The whole grammar works inside a voice: `N(...)` groups, `%Name`
  patterns, `|` bar checks (each voice is checked on its own), lyrics,
  even other voice blocks.
- The block can span several lines; a `;` outside a block is an error.
- In the editor each voice has its own **coloured background** (blue for
  the first, amber for the second, then lilac and green; a nested block
  starts from another colour): you can see at a glance where each one
  starts and ends, even when the block spans several lines. Braces and
  `;` have no background.
- In the score (sections 10.1 and 10.1bis) the voices become **voices of
  the same staff**, with stems up and down.

### 2.13 Lyrics (`"..."`)

A string in double quotes is the **lyrics** of the notes **before** it,
starting from the note after the previous lyrics (or from the beginning):
one syllable per note, separated by spaces. You write it as under a line
of sheet music:

```
4: c*4 d*4 e*4 2f*4
"Ma- ri- a, sei"
```

- A hyphen at the end (`Ma-`) says the word continues in the next
  syllable; in the score the syllables are joined by the hyphen.
- `_` gives the note no new syllable: the previous syllable is
  **extended** (melisma, with the extension line in the score).
- `*` skips a note (no syllable).
- Rests and percussion get no syllables.
- The syllable can also be attached to the note: `c"Ma-" d"ri-" e"a"`.
- Inside a `2(...)` group the lyrics repeat with the notes; after a voice
  block they go on the **first voice** (a voice can also have its own
  lyrics, inside the block).
- Lyrics are not heard: they go into the score (under the notes), the
  MusicXML and the exported MIDI (*lyrics* events, read by karaoke
  programs).
- If there are **more syllables than notes** the editor shows a warning
  (orange), like the bar checks. A `//` inside the quotes is part of the
  lyrics, it does not start a comment.

### 2.14 The ST-language specification and library

The notation has a **public formal specification**:
[docs/spec/ST-language.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md) (in Italian
[ST-language.it.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.it.md)), licensed **CC BY 4.0** (you
may copy, translate and adapt it, crediting the source). It describes the
complete grammar, how the text becomes notes in time, errors and warnings,
the `.st` file format and the mapping to MIDI, with a **conformance
suite** ([`docs/spec/conformance/`](https://github.com/openssound/st-language/tree/main/docs/spec/conformance)): the test cases another program must
pass to read ST-language like SoundText.

The notation engine is also a **standalone Python library**,
`st_language`, with no external dependencies: it is the same one SoundText
uses, so both always give the same result. Install it with
`pip install git+https://github.com/openssound/st-language.git`; it provides command-line tools:

```
st-language check song.st            # errors and warnings (bars, lyrics)
st-language midi song.st -o song.mid
st-language musicxml song.st         # score song.musicxml
st-language events song.st           # the events as JSON
echo "4: c d e f | 2g 2g" | st2mid - -o melody.mid --instrument Trumpet
```

A file without track headers is a one-track song (`--instrument` chooses
its instrument). From Python: `import st_language as st`, then
`st.parse(text)`, `st.validate(text)`, `st.check(text)`,
`st.load_song("song.st")`, `st.to_midi(song, "song.mid")`. So songs written
in ST can be checked and exported without opening SoundText (for example
from a script, or in a repository of songs).

### 2.15 Automations (volume, expression, pan... changing over time)

Dynamics (`p@`, `>>`) change the **velocity**, i.e. how hard each note is
played: a note that has already started stays as it is. **Automations**
act on the instrument **continuously** instead, even while a note is held,
like moving a mixer fader during the performance:

| Command | What it changes | Values | Initial |
| --- | --- | --- | --- |
| `vol=N` | track volume | 0-127 | 100 |
| `expr=N` | expression: the volume "inside" the dynamic (strings, winds, organ) | 0-127 | 127 |
| `pan=N` | stereo position: -1 left, 0 centre, 1 right | -1..1 (decimals allowed) | 0 |
| `mod=N` | modulation (vibrato, on many instruments) | 0-127 | 0 |
| `rev=N` | reverb send | 0-127 | 0 |
| `cho=N` | chorus send | 0-127 | 0 |
| `bend=N` | pitch bend, in semitones (like the synth wheel) | -24..24 (decimals allowed) | 0 |
| `ccN=V` | any MIDI controller N (0-119), e.g. `cc74` brightness | 0-127 | 0 |

On its own, the command changes the value at that point. Followed by `>>`
(or `<<`, it is the same) it opens a **ramp** that reaches the next command
with the same name, going through all the values in between:

```
4: vol=0 >>exp 4c*4 vol=100          // fade-in on the held note
4: pan=-1 >> c d e f pan=1           // the sound moves from left to right
4: expr=40 >>s 2C 2F expr=127 r      // swells under two chords
8: rev=20 c d e f rev=90 4g          // the reverb jumps up
```

The **curve** of the ramp goes after the arrows: `>>` (linear), `>>exp`
(starts slowly and speeds up: the natural fade-in), `>>log` (starts fast
and slows down: the natural fade-out), `>>s` (smooth at both ends).

**Hairpins on notes.** A `<` at the end of a note (or chord, block, slide)
makes a **crescendo during the note**, a `>` a diminuendo: the hairpin of
a score, made with the expression (from half to the current value or the
other way round), which then goes back to what it was:

```
4: 4c*5<            // a held note that swells
4: 2C< 2G>          // one chord grows, the other fades
4: c'2> [c e g]<    // with a note value or on a block
```

- Automations apply to the whole track, even when written inside a voice
  block `{ ; }`; ramps with different names may overlap (`vol=` and
  `pan=` together).
- `vol=` combines with the mixer volume (`vol=100` = the fader volume);
  `pan=`, `rev=` and `cho=` written in the text replace the mixer values
  from that point on.
- An open ramp must be closed by a value with the same name, otherwise
  validation reports an error; a hairpin on a rest and a hairpin inside an
  open `expr=` ramp are errors too.
- You hear them in playback and they go into the exported MIDI (as control
  changes: CC7, CC11, CC10, CC1, CC91, CC93); in the score, `vol=`/`expr=`
  ramps and hairpins appear as crescendo and diminuendo hairpins.
- They are part of the ST-language specification since version 1.1 (2.14).

### 2.16 Ties, slurs and swing

**Tie `~`.** A `~` at the end of a note, chord or block **joins** it to the
next identical one: they sound as a single note, as long as both
together. It is mostly used to hold a note across the bar line, where the
bar division does not let you write it in one piece:

```
4: c d 2f~ | 2f g a |        // the F lasts 4 beats, across the bar line
4: 4C7~ | 4C7 | 4F |         // a chord held for two bars
4: c'2~ c'8 r'8 d'4          // also with note values
```

The note after the `~` must be the same (`c#~ db` is fine: it is the same
sound), otherwise it is an error; percussion, rests and slides cannot be
tied.

**Slur `( )`.** A `(` at the end of the first note and a `)` at the end of
the last one connect a phrase: the notes in between sound **legato**
(joined to one another, like a singing phrase), the last one as written.
The score shows the arc over the notes.

```
4: c( d e f) g( a b c*5)
4: 2(c( d) e)                // inside a group, the slur is repeated
```

A note with its own articulation (`d!` staccato) keeps it inside the slur
too. Slurs do not nest and do not cross a voice block `{ ; }`.

**Swing.** `swing=N` makes the eighth notes "swing" from the point where
you write it: in every beat the first eighth gets longer and the second
shorter, as played in jazz, blues and shuffle. N is the part of the beat
given to the first eighth: 50 is straight, 66 is the triplet feel (classic
swing), up to 80. `swing16=N` does the same with sixteenth notes (funk,
hip hop). `swing=50` turns swing off.

```
swing=62 8: c d e f g a b c*5   // written straight, played with swing
swing16=58 16: kick hihat snare hihat kick kick snare hihat
```

Everything is written straight: bar checks and the score stay regular
(the score shows a "Swing" marking), only the way it sounds changes, in
playback and in the exported MIDI.

### 2.17 Repeats, marks and indications

**Repeats.** They are written as on a score: `|:` opens the part to
repeat, `:|` closes it, and the part is played twice. Without `|:`, the
repeat starts at the beginning of the song (or at the end of the
previous repeat).

```
4: |: c d e f | g a b c :| c*5 d*5 e*5 f*5 |
```

For a different ending on each pass use **endings**: `|1.` opens the
first, `:|` closes it and goes back to the start, `|2.` opens the second,
which ends with `||` (or with the end of the text). With three endings
the part is played three times, and so on.

```
4: |: c d e f |1. g a b c :| |2. 4c*5 || d e f g |
```

You hear everything written out; the **score** shows real repeat signs
and endings, as long as the repeat starts and ends on bar lines and
every pass is the same as the first in all the tracks (otherwise the
score writes it out). A group `2(...)` that fills whole bars is also
printed as a repeat. `|:`, `:|`, `|1.` and `||` are bar checks too, and
repeats do not nest.

**Marks on notes.** A `$` followed by the name, at the end of a note,
chord or block (after the note value), adds a mark that you see in the
score and hear:

| Mark | What it does |
| --- | --- |
| `$accent` | accent: the note sounds louder |
| `$marcato` | strong accent |
| `$tenuto` | tenuto |
| `$fermata` | fermata: the whole song stops on the note (double length); also on a rest |
| `$tr` | trill with the note above (in the song's key) |
| `$mordent` | mordent: note, note below, note |
| `$turn` | turn: above, note, below, note |

```
4: c$accent d e$tenuto f$fermata | 2g$tr a$mordent b$turn |
4: [c e g]$accent$tenuto r$fermata
```

Trill, mordent and turn are played on single notes (on chords and blocks
they stay a mark in the score).

**Text indications.** `$"text"` writes an indication above the staff at
that point: `$"rit."`, `$"dolce"`, `$"a tempo"`. It does not change the
sound: to really slow down use a tempo ramp (`tempo=100 << ... tempo=70`,
section 2.6).

### 2.18 Relative octaves and key

Two commands make melodies much shorter to write. They can be used
together, and both are optional: without them everything works as
before.

**Relative octaves (`rel:`).** After `rel:` you no longer write the
octave: each note goes to the octave **nearest to the previous note**
(at most a fourth above or below, counting letters). To jump further add
`*+` (one octave up) or `*-` (one octave down), also repeated (`*++` two octaves up, `*--` two down); `*n` is
still valid and sets the exact octave.

```
rel: c d e f g a b c          // C scale up to the C above
rel: c*5 b a g f e d c        // and down
rel: g c*+ c*- c                // c*+ jumps up, c*- comes back down
```

The first note after `rel:` goes near the C of the instrument's default
octave. After a block `[...]` it starts again from its first note;
chords and percussion do not count. `abs:` goes back to absolute
octaves. In repeats and groups every repetition starts again from the
same note, so it sounds the same.

**Key (`key=`).** After `key=G` every note **without** an accidental
takes the key's one: in G major `f` is F sharp. A written sharp or flat
applies to that note only; `n` (or `♮`) is the natural and cancels the
key's accidental.

```
key=G rel: g a b c d e f g    // G major without writing the sharp
key=Bb rel: b c d e f g a b   // B flat major: b and e are flat
key=Dm rel: d e f g a b c# d  // D minor (B flat) with the C sharp
key=G f fn f#                 // F sharp, F natural, F sharp
```

`key=off` removes the key. Chords (`C`, `F7`...) do not change: chord
symbols are always absolute. The song's key (in the top bar) sets the
key signature of the score; `key=` tells how to read the track's notes.

**Patterns** (`%Name`) are always read with absolute octaves and no key,
whatever the mode of the track using them: they sound the same
everywhere.

**Rewriting an existing track.** The **Relative pitches and key** button,
under the editor, rewrites the current track with `rel:` and, if the song
has a key, `key=`: the notes stay the same, the text gets shorter. It is
handy after importing from MIDI, MusicXML or ABC. **Transpose** (on
boxes) knows both modes too: in `rel:` notes stay relative, and with
`key=` the key is transposed as well.

### 2.19 Micro-timing, tuning, many tracks, MTXT

**Micro-timing (`shift=`).** `shift=N` plays the following notes N
milliseconds **later** (positive N) or **earlier** (negative N) than
written; `shift=0` puts them back on time. The written rhythm does not
change: bar checks and the score stay the same, only the moment the notes
sound changes. It goes from -500 to 500.

```
4: kick shift=20 snare shift=0 kick shift=20 snare   // snare a little behind
shift=-10 8: c c g g a a g g                          // bass pushing ahead
```

It is meant for the "feel" and for lining a part up with a recording;
real rhythms are written with note values, tuplets and swing.

**Tuning (`tune=`).** `tune=N` tunes the instrument by N cents (from
-100 to 100: 100 cents are a semitone). It is an automation like `vol=`
or `bend=`: it applies to the whole track, even during a note, and takes
ramps.

```
tune=-20 4: c d e f              // to play along with a record tuned a bit low
tune=0 >> 4: c d e f tune=50     // rises a quarter tone over four notes
```

**More than 15 tracks.** Every track always has its own MIDI channel:
from the 16th melodic track on, the MIDI export uses a second "port" (16
more channels), then a third, and so on. SoundText plays them and imports
them back correctly; some very old MIDI players ignore ports and play
those tracks on the channels of the first ones.

**MTXT.** **Project → Export → MTXT...** writes the song as
[MTXT](https://github.com/Daninet/mtxt), a text format with one event
per line and times in quarter notes (`1.5 note C4 dur=0.5 vel=0.8`),
easy to read, compare and have edited by an AI. It contains notes,
instruments, automations, tempo and time signature, like the MIDI file.
**Project → Import → MTXT...** does the opposite: it reads the file like a MIDI
file (one track per channel, with the channel names). The library does
the same from the terminal with `st-language mtxt song.st` and
`st-language mtxt file.mtxt` (which becomes a `.mid`).

### 2.20 Bar anchors (`bar=`)

**Where a part comes in.** `bar=N` moves the cursor to the **start of
bar N**, with the silence needed: instead of counting rests (`28%Rest`)
you write the bar where the part comes in.

```
Guitar 2:
  bar=29                          // the second guitar comes in at bar 29
  8: 100@ c d e f g a b c
```

- If the track is **before** that point, the gap is filled with silence;
  if it is **exactly** there, nothing happens.
- If the track is **already past** it (a part longer than planned), the
  anchor does not go back: the part goes on where it is, and the editor
  shows a **warning** on the anchor ("bar 29: the track is already 2
  quarter notes past the start"), as for the `|` bar checks.
- Bars are counted as everywhere else in the program: from 1, following
  the song's time signature and its changes. Inside a pattern or a
  repeated group the song's bar applies at every repetition.
- A tie `~` cannot cross an anchor that needs silence.

`bar=` positions and `|` verifies: together they say where each part
must be and warn when one has drifted. In **Extract patterns**, blocks
that contain an anchor are not extracted, because a pattern does not
know which bar it is in.

### 2.21 Transposition (`transpose=`, `%Name+N`)

**Transposing without rewriting.** `transpose=N` makes the following
notes, chords, slides and blocks sound N semitones **higher** (positive
N) or **lower** (negative N) than written; `transpose=0` returns to the
written pitch. The range is -60 to 60.

```
4: c d e f g a b c*5              // in C
transpose=2 4: c d e f g a b c*5  // the same melody in D
transpose=0
```

**A pattern in another key.** After the name of a pattern you write by
how many semitones to transpose it: `%Theme+7` plays it a fifth higher,
`%Theme-12` an octave lower, `2%Theme+3` twice, three semitones higher.
No copied patterns are needed: the theme is written once.

```
Pattern %Theme:
  key=Eb 8: 90@ g*5 b*5 e*6 2d*6 2b*5 |

Violini1:
  %Theme  %Theme-3  %Theme+12   // E flat, then C (-3), then an octave higher
```

- The transposition applies to **everything** inside the pattern,
  including the patterns it calls, and is **added** to the one already in
  force (`transpose=3 %Theme+4` sounds 7 semitones higher).
- A `transpose=` written inside a pattern ends with the pattern.
- The same goes for the MIDI library: `&"Bass"+7`, `&"Bass"-12` (section 5).
- With `key=` the transposed notes are written in the new key: `key=G`
  with `transpose=2` is A major (the written F sharp becomes G sharp, G
  becomes A). Without a key, a flat stays a flat and the other altered
  notes take the sharp. In the score too.
- Chords change name (`C7/E` +5 is `F7/A`) and move up an octave when
  they pass the C; with +12 every chord goes up an octave.
- Percussion and rests do not change. If a transposed note leaves the
  MIDI range, the program reports it as an error.
- **Extract patterns** does not extract blocks that contain a
  `transpose=`: inside a pattern the transposition would end with the
  pattern.

### 2.22 `reset:`, pickup bar and file version (ST 2.6)

**`reset:` — start over.** Puts everything back to the initial state:
grid `4:`, velocity 80, no swing or shift, transposition 0, absolute
octaves, no key. The automations (`vol=`, `pan=`...) stay where they are.
Useful when a piece of text must sound the same whatever comes before:

```
rel: key=G 8: 100@ transpose=2 g a b c
reset: c d e f           // quarter notes again, velocity 80, C major
```

Every box of the Song structure view starts with a `reset:`: so a
`transpose=` or a `key=` written in a box never carries over to the next
box.

**Pickup bar.** If the song starts with a pickup, write how many quarter
notes it lasts in the **Pickup** field of the song bar (or `Levare: 1` in
the file). Bar 1 becomes the first full bar: the bar checks `|`, the
anchors `bar=N`, the per-bar tempo and meter changes, the ruler of the
Song structure view, the metronome and the score count from there. The
pickup is bar 0.

```
Levare: 1
Metrica: 3/4

Violino:
  4: g | c e g | c*5 2r |      // a quarter-note pickup, then 3/4 bars
```

**MIDI file names in quotes.** The name of a file of the MIDI library is
always written in quotes: `&"Riff"`, `&"Blues/bass-line"`, spaces
included (`&"intro take 2"`). What follows the quotes is always the
transposition: `&"Riff"-2` is the file `Riff` two semitones lower,
`&"take-2"` is the file called `take-2`. Songs written before (with
`&Riff`) are converted by themselves when you open them, and stay the
same; if you write `&Riff` without quotes the editor tells you how to fix
it.

**Version and English keywords in the file.** The `.st` file starts with
`ST: 2.7`, the version of the language it is written in; opening a file of
a newer version, the program warns. The program also reads the keywords
in English (`Track`, `Instrument`, `Meter`, `Key`, `Pickup`,
`percussion=`, `octave=`, `yes`), handy for those who write files by
hand; when saving it always uses the Italian forms.

### 2.23 Chords, grace notes, D.C./D.S., verses and title (ST 2.7)

**More chords.** Besides the usual ones: `C7#5` (also `Caug7`), `C7b5`,
`Cm11`, `Cm13`, `C69` (six-nine: in `C6/9` the slash would be the bass),
`Cmaj7#11`, `C7#11`, `C9sus4`, `C7b13`, `Cadd11`, `Cmadd9`, `C7sus2`,
`Csus` (= `Csus4`), `C13b9`.

**More drums.** The rest of the General MIDI drum set: `triangle`,
`triangle_mute`, `agogo_hi`, `agogo_low`, `guiro_short`, `guiro_long`,
`whistle_short`, `whistle_long`, `cuica_mute`, `cuica_open`, `vibraslap`
and `side_stick` (the same sound as `rimshot`).

**Values and tempo.** `c'128` is a 128th note; the letter `D` makes
duplets (`8D: c d`, two eighths in the time of three, as in 6/8). Tempo
accepts decimals (`tempo=72.5`) and the counted note: `tempo=60'4.` is 60
dotted quarters per minute; the score writes the metronome that way.

**Grace notes.** `d'g c` is an acciaccatura (the D before the C), `d'G c`
an appoggiatura; they also work on chords, blocks and drums (`snare'g
snare` is a flam). They take no written time: they sound just before the
note, which loses that much of its length.

**New marks on notes.** `C$arp` (rolled chord), `c$staccatissimo`,
`c$sfz` (sforzando), `c$fp` (forte-piano), `c$trem` (tremolo; on drums
`snare$trem` is a roll), `c$harmonic` (harmonic).

**Chord symbols without sound.** `$Am7` writes the symbol above the
staff without playing it: handy for a lead sheet with only the melody
(`$C c d e f $G7 g a b c`).

**D.C., D.S., Coda and Fine.** They are written as signs: `$segno`,
`$coda`, `$tocoda`, `$fine`, `$dc` (da capo), `$ds` (dal segno). They are
played as a musician plays them; on the way back the repeats are played
once, with the last ending:

```
4: c d e f | g a b c*5 $fine | e d c d | 4e $dc     // D.C. al Fine
4: $segno c d e f | g a b c*5 $tocoda | 4e $ds $coda | 4c |   // D.S. al Coda
```

**More verses.** A lyric that starts with the verse number goes under the
same music: `"Ma- ry had a lit- tle lamb"` and then
`"2: Ev- ry where that Ma- ry went"`. The score writes one line per verse.

**Title, authors, key changes, transposing instruments.** At the top of
the `.st` file you can write `Titolo:` (or `Title:`), `Autore:`
(`Composer:`) and `Parole:` (`Lyricist:`), which go into the score, and
the key per bar like the tempo: `Tonalita: 1: C, 17: G`. In an instrument
defined in the file, `trasposizione=-2` makes it transposing (B♭ trumpet:
-2, E♭ alto sax: -9): you always write at sounding pitch and the score
writes its part transposed. The saved file declares `ST: 2.7`.

## 3. Current State

Grid and velocity stay active until they are changed again:

```
100@ 8: c e 60@ g a 100@ c
```
`c` and `e` last an eighth at velocity 100; `g` and `a` at velocity 60; the
last `c` goes back to velocity 100. State commands generate no events: they
take up no time on the timeline.

## 4. Patterns (%Name)

They are defined in the pattern library (menu **Compose → Manage
pattern library**) or directly in the `.st` file:

```
Pattern %GtrArp:
  16: 90@ c e g e 70@ c e g e
```

and are called in any track with `%GtrArp`.

**Repetition:** putting a number in front repeats the pattern N times:
```
3%GtrArp        -> plays %GtrArp three times in a row
```

### 4.1 Listening to a pattern

In the **Compose → Manage pattern library** dialog, each selected
pattern can be listened to with the **▶ Listen** button, choosing the
preview instrument from the drop-down next to it (the pattern stays
universal anyway: the choice is only for the audio test). Changes not yet
saved in the editor are automatically included in the preview. While it
plays, the point you are listening to is highlighted in the pattern body,
as in the main editor and in the box editing, generation, "Play with the
keyboard" and audio conversion dialogs.

### 4.2 Reorganising the song with patterns

Menu **Compose → Extract patterns from tracks...**: analyses all
the tracks of the current project, finds blocks of events that repeat (even
non-consecutively) and automatically turns them into reusable patterns,
replacing the occurrences with `%Name` (with repetition `N%Name` when the
occurrences are consecutive). The musical content does not change: it is
just a more compact and readable rewrite of the same sequence of events. If
no long enough repetitions are found, the program says so without changing
anything.

The generated patterns are named after the **instrument of the track** they
come from (e.g. `%Guitar1`, `%Guitar2`, `%Bass1`...), not a generic prefix.
Moreover, an extracted pattern **never contains references to other
patterns**: if a track already uses `%Lib1` together with repeated literal
material, `%Lib1` stays a reference of its own and is never included inside
a new pattern (no nested patterns).

Menu **Compose → Expand patterns in tracks...**: the reverse
operation. It replaces every `%pattern` and `&"midi"` reference in the tracks
with the corresponding literal tokens (repetition already applied), making
the project completely self-contained; patterns no longer used are removed.
Useful before sharing a song without having to attach the pattern library
too, or to inspect/edit each single event by hand without the indirection
of references.

Both operations act on the whole project, ask for confirmation before being
applied, and run in the background with a progress bar: the interface stays
responsive and the operation can be cancelled. The search time for repeated
blocks is in any case always limited (per track), so that even on very long
tracks the reorganisation never stays stuck indefinitely.

### 4.3 Context menu on a selection (right-click)

Selecting a sequence of tokens with the mouse in the editor (track, body of
a pattern or of a box) and clicking with the **right mouse button** opens a
context menu with three items. In the dialog previews (Generate
drums/bass/accompaniment/chord progression, Play with the keyboard, audio
conversion, MIDI library) the menu only has **▶ Play**, and it first stops
any playback of the whole preview:

- **▶ Play**: plays only the selection, with the instrument of the current
  track, automatically rebuilding the last rhythmic grid and velocity active
  before the selection (so it sounds as it would in the original context,
  not always at 1/4 and velocity 80).
- **Group**: encloses the selection in round brackets, turning it into a
  `(...)` group (see section 2.1); useful before applying a repetition
  multiplier to it by hand (e.g. turning `(...)` into `4(...)`).
- **Turn into pattern...**: asks for a name, creates a new pattern
  containing the selection and replaces the selection itself with
  `%PatternName` — a quick way to extract a single fragment into a pattern
  by hand, as an alternative to the automatic search of **Extract patterns
  from tracks...** (section 4.2).

The mouse selection is always "snapped" to the boundaries of the whole
tokens it touches (no need to select with pinpoint precision); if the last
token included is a state command with nothing after it (`N:` or `N@`), it
is discarded automatically, so the resulting group or pattern never ends
"hanging" without a sound event.

If the selection also contains a reference to a pattern (`%Name`) or to a
MIDI file (`&"Name"`), the menu shows **only Play**: grouping an existing
indirection or turning it into a new pattern is not allowed.

### 4.4 Renaming a pattern

The **Rename** button (next to "New" in the **Compose → Manage
pattern library** dialog) renames the selected pattern and automatically
updates every `%oldname` reference already present — both in the tracks and
in the body of the other patterns — to the new name, so the renaming does
not silently break what calls it. The new name must follow the same syntax
as a pattern reference (letters, digits and underscores, no spaces) and
cannot be the same as that of an existing pattern.

## 5. MIDI library (&"Name")

In the `midi/` folder (next to the program, empty after a first
installation: the library is yours) you can keep short musical phrases as
`.mid` files, also organised in subfolders by category (genre, artist,
instrument...), for example:

```
soundtext/
├── midi/
│   ├── Guitar/
│   │   └── Intro.mid
│   ├── Blues/
│   │   └── shuffle.mid
│   ├── Drums/
│   └── Bass/
└── songs/
    └── your_projects.st
```

An `&"Name"` reference searches **recursively in all subfolders**:

```
Guitar:
  &"Intro" &"Intro" %GtrArp
```

if you have a file `midi/Guitar/Intro.mid`, it finds it automatically (or
any other subfolder containing an `Intro.mid` file), without giving the
path.

**Qualified paths:** if the same name exists in several subfolders, the
reference is ambiguous and validation reports it, listing the alternatives
found; to resolve it just qualify the path:

```
&"Blues/bass_line"      -> specifically uses midi/Blues/bass_line.mid
```

**Repetition** (as for patterns):

```
2&"bass_line"            -> repeats the reference twice
```

**Transposition:** as with patterns, a number after the name transposes
the file by that many semitones: `&"Intro"+7` plays it a fifth higher,
`&"Intro"-12` an octave lower, `2&"Intro"+2` twice, two semitones higher
(section 2.21). The name is in quotes, so dashes and spaces are no
problem: `&"Blues/bass-line"-2` is `Blues/bass-line` two semitones lower
(section 2.22).

Management from the GUI: menu **Compose → Manage MIDI library**.
From there you can import an existing `.mid` file (also giving a
destination subfolder), rename/move it, delete it, listen to it with
**▶ Listen to original file** (plays the .mid file as it is, with all its
channels), or view/edit a text preview of it (the channel with the most
notes is converted) and "regenerate" the MIDI file from the edited text,
choosing the instrument to use for the voicing.
When you rename or move a file and the open song references it, the
program offers to update the `&"Name"` references (also in boxes and
patterns), keeping multiplier and transposition.

Note: `&"Name"` imports only the most significant channel of the MIDI file
(usually the one with the most notes); for a complete multitrack import use
**Project → Import → MIDI...** instead, which creates one track per channel.

## 5bis. Songs folder (songs/)

The **Open project** and **Save as** dialogs open by default on the
`songs/` folder (next to the program): it is the place meant for your
compositions, separate from `examples/`, which contains the demo projects
of the program's features.

## 6. Percussion

36 fixed identifiers, mapped onto the General MIDI Drum Map (channel 10) and
without octave support. In order, they correspond to the keys used in "Play
with the keyboard" (section 10ter): number row (1-9, then 0 ' ì), Q row, A
row.

- Basic kit (number row): `kick`, `snare`, `hihat`, `hihat_open`, `tom1`,
  `tom2`, `floor`, `crash`, `ride`, `kick2`, `rimshot`, `clap`.
- Other toms/cymbals/hi-hats (Q row): `snare2`, `hihat_pedal`,
  `tom_lowmid`, `tom_hi`, `tom_highfloor`, `china`, `ride_bell`,
  `tambourine`, `splash`, `cowbell`, `crash2`, `ride2`.
- Latin percussion (A row): `bongo_hi`, `bongo_low`, `conga_mute`,
  `conga_open`, `conga_low`, `timbale_hi`, `timbale_low`, `cabasa`,
  `maracas`, `claves`, `woodblock_hi`, `woodblock_low`.

## 7. Tracks and instruments

- **Add track**: the **+ Add track** button (below the last header, both in
  the Song structure view and in the Text view) or the **Track → Add** menu. The button opens a menu with:
  - **Track with instrument...** (Ctrl+T) and **Audio track...**;
  - **Generate a track**: **Drums**, **Chord progression**, **Bass from
    chords**, **Accompaniment or riff** (for the last one you choose the
    instrument: polyphonic = accompaniment, monophonic = riff/melody). The
    generator dialog opens and the track is created only if you confirm,
    already filled (a box in the Structure view, text in the Text view).
    Bass and accompaniment follow the chords of another track: until the
    song has one, they stay disabled, with the reason written next to them;
  - **Track from a MIDI file...**: a channel of a MIDI file becomes a new
    track, with the instrument recognised in the file.
- **Actions on a track** (generate, play with the keyboard, import MIDI or
  audio, name and instrument, export MIDI, remove): the **⋯** menu on the
  track header (in both views), or right-click on the header; they are also
  still in the **Track** menu.
- **Rename / change instrument**: **⋯ → Name and instrument...**, or
  double-click the track header.
- **Custom instruments**: menu **Sounds → Manage instruments**. The
  instrument is chosen **by name** from a complete General MIDI list,
  grouped by family (Pianos, Guitars, Basses, Brass, Reeds...) and
  searchable by typing (e.g. "sax", "organ"): you do not need to know the
  program number. Choosing a sound automatically prefills the most suitable
  octave, range and voicing style (e.g. basses become `root_fifth`, brass
  `monophonic`), which can always be changed by hand. For a percussion
  instrument, tick "Use the percussion channel (10)" instead of choosing a
  sound. Available parameters: name (a single word), default octave, range
  (lowest and highest playable MIDI note) and voicing style for chords:
  - `spread`: spreads all the notes of the chord (suited to piano/guitar)
  - `root_fifth`: only the root (+ fifth if present), suited to bass
  - `monophonic`: only the root, for monophonic melodic instruments
  - `root_only`: only the root
- **SoundFont per instrument**: from **Sounds → Manage
  instruments...** you can also assign a `.sf2` file other than the default
  one to a single instrument (built-in or custom) — see section 12.4 below.

### 7.1 Automatic loading of custom instruments

When you save a project that uses one or more custom instruments, their
definition (GM program, octave, range, voicing...) is **embedded directly
in the `.st` file**, in a `Strumento Name:` block written before the
patterns and the tracks. So, if you open that project on another
installation (or after cleaning up your local configuration) and the
instrument is not available yet, it is **registered automatically** on the
fly, and the track using it is not lost. The program shows a notice with
the list of instruments loaded this way.

If an instrument with the same name already exists on the system, the
definition embedded in the file **does not overwrite it** in the
instrument list (your changes made by hand stay), but **the tracks of that
song use the definition in the file**: a song always sounds as written,
even if you first opened another song that defines an instrument with the
same name differently (for example "Archi" or "Viole").

This also applies to tracks renamed with **Edit name/instrument**: if the
track name no longer matches the instrument (e.g. a track "Guitar 1"
renamed to "SoloRinominato" and switched to another instrument), the file
automatically uses an explicit header (`Traccia SoloRinominato [Bass]:`)
instead of the short form, so that nothing is lost when saving.

## 8. Mixer

Each track has **Mute (M)**, **Solo (S)**, **Volume** and **Pan**. If at
least one track is in Solo, only the tracks in Solo (that are not also
Mute) play in playback/export.

The controls are in the **header** of each track, the same in both views:
in the Song structure view on the left of each row, in the Text view in the
**Tracks** column on the left (there it is also used to choose the track
whose text to edit). The header contains:

- name and instrument, **M**, **S**, **●** (audio tracks only: record),
  **FX** (opens the Effects panel, see 8.3 and 8.4) and the **⋯** menu with
  all the actions of the track (generate, play with the keyboard, import
  MIDI or audio, name and instrument, export MIDI, remove);
- on the right, two knobs: **Vol** (volume, the value in %) and **Pan**
  (C = centre, L/R = left/right). They are turned by dragging up/down
  (finer with Shift), with the mouse wheel or with the arrows;
  double-click = back to 100% / to the centre.

Click on the header = select the track; double-click = rename/change
instrument; right-click = the same menu as ⋯. Below the last header,
**+ Add track** (see section 7).

### 8.1 Volume: 0-200%, it directly scales the velocity of the notes

The Volume knob goes from 0% to 200%, where **100% is the original
intensity** of the notes as written in the track (no change). Turning the
knob directly scales the velocity of every note of the track in
export/playback — not just the MIDI Channel Volume (CC7), whose response
curve on many synths is weak or barely noticeable. This makes the control
effective on any playback engine:

- below 100%: the track plays softer than the original;
- above 100% (up to 200%): the track is boosted beyond the original, useful
  to bring out an instrument that is too weak in the mix;
- the resulting velocity still stays within the valid MIDI limits
  (1-127).

The Volume, Pan, Mute and Solo settings of each track are saved in the
`.st` file (`Mixer <Track name>:` block) and restored automatically when
the project is reopened.

### 8.2 Master volume

Besides the Volume of each single track (8.1), the main toolbar has a
**Master** slider (0-200%, same scale and same convention: 100% = original
gain) that scales the volume of **all** tracks together, on top of the
volume already set on each one — useful for a general level adjustment
without having to touch every track individually. As for track
Mute/Solo/Volume/Pan, a change to the Master during playback automatically
restarts playback from the current position with the new value applied
(with a short debounce if you drag it with the mouse, so as not to queue a
restart for every single tick). The master value is saved in the `.st`
file (line `Master: N`, written only if different from the default 100%)
and restored when the project is reopened.

### 8.3 Reverb and chorus (FX)

The **FX** button of each track, in its header (in both views), opens the
**Effects panel** at the bottom of the window (see 8.4). For text tracks the
first card, **Quick send**, contains the synth effects:
- **Reverb** (0-100%): how much of the track goes to the reverb, from dry
  (0%) to very "wet";
- **Chorus** (0-100%): widens and "doubles" the sound (strings, pads, clean
  guitars, choirs);
- **Room**, one for **the whole song**: the space into which all tracks send
  their reverb. Small room (default), Hall, Large hall or Church.

The FX button lights up (light blue) when the track has reverb, chorus or
chain effects, and its tooltip shows their values.

These are the effects already present in the synth (fluidsynth): they are
heard immediately with normal listening, without extra processing, and
during playback listening restarts by itself as for volume and pan.
- **Saving:** reverb and chorus go into the track's `Mixer` block
  (`riverbero: 35 chorus: 10`), the room into the `Ambiente: sala` line at
  the top of the file. Both are written only if different from the
  default, so projects that do not use them stay identical.
- **Export:** reverb and chorus apply to listening and to WAV and MIDI
  exports (controllers CC91 and CC93). The room applies only to listening
  and WAV: the MIDI file cannot contain it, and the player that opens it
  uses its own.
- **MIDI import:** a file with reverb and chorus set on the channels
  (CC91/CC93 at the start of the song) carries them into the imported
  tracks.

Good to know:
- **Small room:** it is fluidsynth's usual room (so existing projects sound
  as before), but the reverb is barely audible in it. For a clear effect
  choose **Hall** or **Large hall**: the card reminds you when you raise the
  reverb with the small room.
- **Changing the room:** even with the reverb at 0, changing room can
  slightly change the sound, because some SoundFonts already send part of
  their instruments to the reverb by themselves.
- **Audio tracks:** they have no Quick send, because these effects belong to
  the synth, which only plays text tracks; they do have the effect chain
  (8.4), though.
- **Play with the keyboard:** live listening does not apply the track's
  reverb and chorus yet.

### 8.4 Effect chain and Effects panel

Every track, text or audio, can have an **effect chain**: the sound of the
track passes from one effect to the next, from left to right. The available
effects, divided by family in the **+ Effect** menu:

- **Dynamics:**
  - **Compressor** (threshold, ratio, attack, release, gain): makes the
    level more even (vocals, bass, drums);
  - **Limiter** (gain, ceiling, release): raises the volume of the track by
    "Gain" without the peaks ever exceeding the "Ceiling" (e.g. −1 dB).
    Presets Safety (peak protection only), Louder, Much louder;
  - **Noise gate** (threshold, ratio, attack, release): silences the track
    when it drops below the threshold, to remove hiss, hum and noises
    between phrases in recorded audio tracks. If it cuts the start or the end
    of the notes, lower the threshold or lengthen the release.
- **Tone:**
  - **3-band EQ** (bass, mids, treble, ±12 dB each);
  - **High-pass filter** (frequency 20 Hz–2 kHz, slope 6–24 dB/octave):
    removes the lows below the frequency. The classic use is "Low-end
    cleanup" (80 Hz) on vocals and guitars, to leave room for bass and kick;
  - **Low-pass filter** (frequency 200 Hz–20 kHz, slope 6–24 dB/octave):
    removes the highs above the frequency, for a darker, muffled or "behind
    a door" sound. The higher the slope, the sharper the cut.
- **Saturation:**
  - **Amplifier** (model, cabinet, gain, bass, mids, treble, presence,
    power, level): a complete guitar amplifier, in the order preamplifier →
    tone controls → power stage → cabinet. The **models**: *Clean* (almost
    no saturation), *Crunch* (blues, light rock), *British* (classic rock,
    mids to the fore, two saturation stages), *High gain* (metal, tight lows
    and lots of saturation).

    **Bass, Mids, Treble** (from 0 to 10, as on real amplifiers) are the tone
    circuit ("tone stack") of real amplifiers, computed from the values of
    its components: the **Fender** one for Clean and Crunch, the
    **Marshall** one for British and High gain. As in the originals the
    knobs affect each other (raising the Treble also touches the mids), at
    half travel the mids are already somewhat "scooped" (more in the
    Fender), Mids at 0 give the deep scoop of metal, and the volume changes a
    little when you turn them, as on a real amplifier.

    **Frequency-dependent saturation.** As in real valve stages, the lows
    saturate less than the mids and highs: low notes and chords on the low
    strings (power chords) stay defined instead of turning to "mush", while
    mid notes distort as you expect. The more pushed the model (British,
    High gain), the stronger the effect. It does not take bass away from the
    sound: it changes how they distort, not how much of them there is.

    **Touch response.** The operating point of the valves also shifts as in
    real amplifiers: on hard hits the stage loses a little gain for a moment
    and distorts asymmetrically (even harmonics, "warmer"), then in about a
    tenth of a second it "breathes" and goes back to how it was. Playing
    softly the sound stays clean, attacking hard it gets dirty dynamically:
    it is the most noticeable effect with Crunch and British (the sound
    "that responds to the pick"), more restrained with High gain and almost
    absent with Clean. After each stage there is also the filter of the
    coupling capacitors, which removes the sub-bass "rumble" that the
    asymmetric distortion would create under low chords.

    **Presence** (0-10) adjusts the highs after the power stage, like the
    knob of the same name on valve amplifiers: more "air" and bite without
    making the preamplifier harsh.

    **Power** (0-100%) is how hard the final stage is pushed: the power
    valves saturate softly and asymmetrically (with even harmonics, the
    "warm" valve sound) and the power supply sagging on hard hits ("sag")
    compresses held chords a little. 0% = clean final stage; 30-50% is the
    sound of an amplifier played loud; beyond that, the sound rounds off and
    compresses.

    The **cabinets**: *Combo 1×12*, *2×12*, *4×12 closed* (more body in the
    lows), *Vintage 1×10* (thinner and nasal), or *None* for the direct sound
    of the amplifier. The cabinets are simulated by SoundText (no file to
    download) and, like real ones, they cut the highs above 5-6 kHz: that is
    why an amplifier sounds "warm" even with lots of gain. Presets: Bright
    clean, Blues, Vintage, Classic rock, Metal. "Level" compensates the
    volume: more gain means more volume, so lower it as you raise the gain.
    It works on guitar tracks (text or recorded) and also on bass or on an
    organ for a dirtier sound.

    **Cabinet from an IR file.** With the **IR file…** cabinet, the impulse
    response (IR) of a real cabinet, recorded with a microphone, is used: a
    small WAV file (lots of free ones can be found, of famous cabinets and
    with different microphones). Choosing "IR file…" opens the window to
    point to the file; the **Choose IR…** button below the menus changes it,
    and the name of the file appears next to it. The file is read in mono
    (average of the channels), brought to 48 kHz if it has another rate, at
    most 1 second, and normalised like the built-in cabinets, so changing
    cabinet does not make the volume jump. The path is saved in the `.st`
    file (relative to the project folder, as for audio clips:
    `ir="ir/cassa.wav"`): keep the IR next to the project if you move it to
    another computer. If the file can no longer be found, the card says so
    in red and the Combo 1×12 cabinet is used until you choose another one.

    **Saturation quality.** Amplifier and Distortion saturate the sound at 4
    times the sample rate (192 kHz; the softer power stage at 2 times) and
    then go back to 48 kHz with linear-phase filters ("oversampling"): this
    way the harmonics generated by the distortion do not fold back into
    spurious frequencies, the classic digital "fizz" on high notes with lots
    of gain. It adds no delay; processing is a little slower (a few tenths
    of a second for the calibration loop, a few seconds in the background
    for a whole track);
  - **NAM profile** (input, cabinet, level): uses a **real** amplifier or
    pedal, "captured" with **Neural Amp Modeler** (NAM). A profile is a
    `.nam` file: a neural network trained by listening to the original
    device, which reproduces its sound with great fidelity. Thousands can be
    found, almost all free, on **Tone3000** (tone3000.com): famous
    amplifiers, overdrive and distortion pedals, preamplifiers, sometimes
    with the cabinet included. To get started, **Sounds → Download → Download
    recommended NAM profiles...** downloads a dozen in one go (see "Where to
    find NAM profiles", below).

    When you add the effect (**+ Effect → Saturation → NAM profile**) the
    window to choose the file opens; if you cancel, the effect is not added.
    The card shows the name of the profile and, if the file declares them,
    brand, model, type (amplifier, pedal, amplifier with cabinet…) and
    author; the **Choose profile…** button changes it.
    - **Input** is the "input" knob of the NAM plugin: how hard the guitar
      comes in. Higher = more saturation (like playing harder or raising the
      gain of the original device, as far as the capture allows), lower =
      cleaner.
    - **Cabinet**: *None / included* if the profile already contains the
      cabinet (type "amplifier with cabinet") or if it is a pedal to put in
      front of an Amplifier; **IR file…** to add the response of a real
      cabinet, as in the Amplifier (see above). A head-only profile without a
      cabinet sounds harsh and "buzzy": give it an IR.
    - **Level** compensates the volume. As in the plugin, SoundText already
      brings every profile to the same reference loudness (−18 dB) using the
      value written in the file; older profiles, which do not write it, are
      measured the same way NAM does (with its reference signal), once only.
      So changing profile does not make the volume jump.

    Presets: Neutral, Pushed harder (+6 dB of input), Cleaner (−6 dB).

    Good to know about NAM profiles:
    - **Formats:** WaveNet profiles of both generations are used, **A1**
      (the classic *standard*, *lite*, *feather* and *nano*, the vast
      majority of published files) and **A2** (the most recent), and also
      **LSTM** profiles, the recurrent networks of NAM's early days. Many
      A2 files contain **several sizes** of the same model, from the lightest
      to the most complete, so that the plugin can save CPU live: SoundText
      does not play in real time and always uses the **complete** size, the
      best one. On the card, next to the description, "A2 format" or "LSTM
      format" appears. The computation follows that of NAM's official
      engine, checked by comparing the outputs; with LSTMs the differences
      stay below −80 dB (rounding in the calculations, which a recurrent
      network carries along over time), so they are not audible. A file of
      another type (for example the very rare experimental ConvNet or Linear
      architectures) is not used and the panel explains why.
    - **Mono:** the profile works in mono, like the plugin (the two channels
      are summed); "spatial" effects should go after it.
    - **Speed:** a neural network is heavier than the built-in Amplifier:
      about one second for each tweak in the calibration loop and about
      twenty seconds, in the background, for a 3-minute track (A1 *standard*
      and A2 profiles; *lite*, *feather* and *nano* are faster, LSTMs even
      more so: a few seconds for 3 minutes). The result stays in memory as
      for the other effects.
    - **Sample rate:** profiles are usually at 48 kHz, like SoundText; if a
      profile has another rate the sound is converted before and after.
    - **Saving:** the path is saved in the `.st` file, relative to the
      project folder: `nam: ingresso=3 cassa=file livello=-2
      nam="profili/Plexi.nam" ir="ir/4x12.wav"`. Keep the profiles next to
      the project if you move it; if the file can no longer be found, the
      card says so in red and the sound passes through unchanged.

    **Where to find NAM profiles.**
    - **Recommended profiles, in one go:** **Sounds → Download → Download
      recommended NAM profiles...** (or, from a terminal in the SoundText
      folder, `python3 scarica_profili_nam.py`) downloads 11 profiles of
      famous amplifiers and pedals, about 3 MB in all, into the
      **`profili_nam`** folder next to SoundText (or into
      `~/SoundText/profili_nam` if that one cannot be written). The folder is
      not part of the repository: everyone downloads it on their own
      computer. The command only downloads again the missing files and
      writes a `LEGGIMI.txt` in the folder with the origin and the authors.
      The "Choose profile…" window already opens there. The profiles come
      from the NAM community collection on GitHub
      (github.com/pelennor2170/NAM_models, GNU GPL v3 licence):
      - amplifiers (without cabinet: add a cabinet with **Cabinet → IR
        file…**): *Fender Twin Reverb - clean* (funk, pop, arpeggios), *Vox
        AC15 - Top Boost* (the British "chime"), *Marshall JCM2000 - crunch*
        (classic rock), *Marshall JCM900 - lead* (hard rock and solos), *Mesa
        Boogie Mark IV - lead* and *Peavey 5150 - high gain* (metal);
      - amplifier **with cabinet** (ready, no IR needed): *Bugera 333 -
        crunch with cabinet*;
      - pedals, to put **before** an amplifier (built-in or profile):
        *Ibanez TS9 Tube Screamer*, *Klon Centaur (clone)*, *Boss HM-2 -
        Swedish* (death metal), and for bass *Tech 21 dUg DP3X*.
    - **Cabinets for amplifiers without a cabinet:** **Sounds → Download → Download IR cabinets for NAM amplifiers...** downloads 20 guitar
      cabinets (impulse responses, less than 1 MB) into the
      **`profili_nam/casse`** subfolder, with the licence text and a
      `LEGGIMI.txt`; the "Choose IR…" window already opens there. They are
      the *BestPlugins Mega Pack 2* by David Fau Casquel (GNU GPL v2 or
      later), taken from the Guitarix repository
      (github.com/brummer10/guitarix). Each file is named after the
      amplifier whose cabinet it reproduces (*Mesa Boogie Mark V*, *EVH
      5150 III*, *Marshall JMP 2203*, *Engl Retro Tube*...). The pack is
      aimed mainly at distorted sounds: with clean profiles (Fender Twin,
      Vox AC15) try several cabinets, or look for a suitable one on
      Tone3000.
    - **Tone3000** (tone3000.com), the reference site, with tens of
      thousands of free profiles (to download it may ask you to create a
      free account):
      1. search for the device (for example "Plexi", "Dumble", "Rectifier",
         "Tube Screamer");
      2. among the filters choose the **NAM** platform and the type: *amp*
         (amplifier only: it needs an IR), *full rig* (amplifier with
         cabinet, ready) or *pedal*; sorting by downloads you find the most
         used ones;
      3. on the profile page download the file (often a ZIP with several
         variants: *standard* is full quality, *lite*, *feather* and *nano*
         lighter; SoundText reads them all, A2 and LSTM included);
      4. extract the `.nam` files into the `profili_nam` folder (or into a
         folder next to the project) and choose them from the card with
         **Choose profile…**.
      Tone3000 also has cabinet **IRs** (type *IR*), to use with **Cabinet →
      IR file…**.
    - **The whole collection on GitHub** (about 260 profiles, 108 MB): on
      the page github.com/pelennor2170/NAM_models, **Code → Download ZIP**,
      then extract the `.nam` files you are interested in into
      `profili_nam`.

    If a downloaded profile does not sound as you expect: an amplifier
    without a cabinet sounds harsh until you give it an IR; a pedal on its
    own sounds "small", it should go in front of an amplifier; with
    **Input** you find the point where the profile reacts best to your
    signal.
  - **Distortion** (drive, tone, level, mix): from a barely hinted warm
    colour up to fuzz. "Drive" is how much it saturates, "Tone" brightens or
    darkens the result, "Level" compensates the volume (distortion raises
    the level a lot), "Mix" below 100% blends the clean sound with the
    distorted one ("Parallel" preset). Suited to guitars, bass and synths;
    for a complete amplifier sound use the Amplifier instead.
- **Space — Delay** (in time, tempo, repeats, mix), **Reverb** (room,
  damping, width, mix), **Chorus** (rate, depth, mix) and **Phaser** (rate,
  depth, feedback, mix).

  The **tempo-synced Delay**: in the "In time" menu choose a subdivision
  (1/2, 1/4, dotted 1/4, 1/4 triplet, 1/8, dotted 1/8, 1/8 triplet, 1/16)
  and the repeats fall in time with the song, computed from its BPM; the
  Tempo knob is disabled and shows the resulting milliseconds. Changing the
  song's BPM, the delay adapts by itself. With "Free (ms)" the time is set
  by hand. The computation uses the **initial** tempo of the song: with
  tempo changes in the middle of the song the repeats stay those of the
  initial tempo. The dotted 1/8 ("In time dotted 1/8" preset) is the classic
  "galloping" echo of rock guitars.

The **Effects panel** opens from the track's FX button (for the master,
from the FX button next to the Master slider: see 8.5) and stays at the
bottom of the window (it can be resized by dragging its edge). Each effect
is a **card** with:
- **⏻** to switch it on or off without losing the settings;
- **◀ ▶** to move it earlier or later in the chain, **✕** to remove it;
- the **presets** (e.g. Compressor "Vocals", Delay "Slapback", Reverb
  "Cathedral"): after choosing a preset you can fine-tune it with the
  knobs, and the menu then shows **Custom**;
- the **knobs**, with the value below; double-click the value to go back to
  the default.

In the panel header:
- **Loop** (10 s, from 2 to 30): when the panel opens, a section to listen
  to while you adjust is chosen, and it also becomes the song's A-B loop
  (on the ruler). It starts from the track's selected box, otherwise from
  the playhead position (or from the track's first box);
- **▶ Listen to the loop**: repeats the section; every tweak is heard **from
  the next pass**, without redoing the rest of the song;
- **With the other tracks**: the whole song plays in the loop, as in the
  final mix; unchecked, only the track is heard;
- **Before / After**: when pressed, the loop is heard without the chain, to
  compare (it does not change the track);
- **Copy to…**: copies the chain to another track;
- **Undo changes**: restores effects, reverb, chorus and room to how they
  were when you opened the panel (the single changes also stay in Edit →
  Undo);
- **✕** closes the panel: the A-B loop goes back to the previous one and
  the chain is applied to **the whole track in the background**, so the
  next Play is already ready (the status bar tells you when it has
  finished).

The FX button shows how many effects are on (e.g. **FX 3**).

Good to know:
- **How it sounds:** a track with effects on is synthesised separately and
  then processed; the result stays in memory, so turning a knob only redoes
  the processing (fractions of a second), and changing another track does
  not touch it. Delay and reverb can lengthen the song with their tail.
- **Export:** the chain applies to listening and to the WAV export; the
  MIDI file does not contain it (the MIDI player does not have these
  effects).
- **Saving:** the chain is saved in the `.st` file, in one block per
  track:
  ```
  Effetti Chitarra:
    compressore: soglia=-20 rapporto=4 attacco=5 rilascio=120 guadagno=4 preset="Voce"
    delay: tempo=250 ripetizioni=25 mix=20 spento
  ```
  (`spento` = effect present but switched off). Out-of-range values are
  brought back within the limits, unknown effects are ignored.
- **Requirements:** the chain uses the Python package `pedalboard` (`pip
  install pedalboard`, already in the requirements); without it, the panel
  shows only the Quick send and a notice. Listening to the loop requires
  audio streaming (`sounddevice`), like the A-B loop.
- **One playback at a time:** starting the loop stops the song and box
  playback; pressing Play stops the loop.

### 8.5 Master effects (mastering)

Besides single tracks, the song's **final mix** can also go through an
effect chain: it is "mastering", the final touch that makes the song more
compact, balanced and loud. The **FX** button next to the **Master** slider,
in the command bar, opens the Effects panel on the master (label "Master ·
final mix"). The same effects and cards as for tracks are used; the most
suitable for the master are:
- **3-band EQ:** small touches to the overall tone (±1-3 dB);
- **Compressor**, preset **Mix glue**: light compression (ratio 2:1, slow
  attack) that blends the tracks together;
- **Limiter**, preset **Louder**: raises the volume of the song without the
  peaks exceeding the −1 dB ceiling. It is usually the last in the chain.

The **+ Mastering chain** button adds these three effects in one go, as a
starting point to adjust by ear. The master's FX button lights up and
shows how many effects are active (e.g. **FX 3**).

As for tracks:
- the **calibration loop** (10 s, from the playhead) lets you hear the mix
  of the whole song at every tweak; **Before / After** compares the mix
  with and without the master chain;
- **Undo changes** restores the chain to how it was when the panel was
  opened, and every change is also in Edit → Undo;
- **Copy to…** copies the master chain to a track; from a track you can
  copy its chain to the master ("Master (final mix)").

Good to know:
- **Where it applies:** the master applies to listening to the song, to the
  song's WAV export and to the backing track you hear while recording. It
  does not apply to the export of a single track nor to the MIDI export.
- **The track loop also goes through the master:** when calibrating a
  track you already hear it with the master chain, that is, as in the
  finished song.
- **Fast:** the mix before the master stays in memory, so after a tweak to
  the master alone the next Play reprocesses the mix already prepared,
  without synthesising the song again.
- **Master volume and chain:** the Master slider (8.2) acts before the
  chain, on the volume of the tracks: with a limiter on the master, raising
  it makes the song more "squashed" but not louder beyond the ceiling.
- **Saving:** in the `.st` file the master chain is in the block
  ```
  Catena master:
    compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=1 preset="Colla del mix"
    limiter: guadagno=6 tetto=-1 rilascio=80 preset="Più forte"
  ```
  (a word different from `Effetti`, so it is not confused with a track
  called "Master"). Without a chain the block is not written.

### 8.6 Studio sounds with external programs (re-amping)

The SoundText amplifier (8.4) is fine for sketches, backing tracks and
demos. For a studio guitar sound the simplest way is the **NAM profile**
(8.4), which uses captures of real amplifiers inside SoundText.
Alternatively, you can run the track through an external amplifier
simulator and then bring it back into the song: this is **re-amping**,
useful for using programs such as Guitarix or commercial plugins.

**The workflow, on any system:**
1. Record the guitar **clean** (INST/Hi-Z input of the audio interface,
   without an amplifier) into an audio track, or write it as notes.
2. Right-click the track name → **Export dry WAV (for re-amping)...**
3. In the external program apply the chosen simulator to the file and save
   the result as a new WAV.
4. In SoundText create an **audio track** (e.g. "Guitar amp") and **Import
   audio file...**: on an empty track the clip goes at the start, so in time
   with the song. **Mute** the original track (or keep both, to blend clean
   and amplified).

If the simulator adds a delay (it happens in real time, not in offline
processing), move the clip slightly or shorten its start by dragging its
edge.

**Linux — Guitarix** (free, simulation of the valve circuits of amplifiers
and pedals, cabinets and IRs): it is installed from the distribution's
repositories (`sudo apt install guitarix`, `sudo dnf install guitarix`,
`sudo pacman -S guitarix`; on some, such as Debian and Ubuntu, the LV2
plugins are in a separate package, `guitarix-lv2`). The Guitarix LV2
plugins can be used **directly in SoundText** as effects (8.7), without
re-amping. To use Guitarix outside SoundText there are two ways:
- **offline (recommended):** open the dry WAV in **Audacity** or in
  **Ardour** and apply the Guitarix LV2 plugins as an effect, then export;
  no audio connections to set up;
- **live:** start Guitarix (with PipeWire, if needed, `pw-jack guitarix`),
  connect with **qpwgraph** or **Helvum** the guitar to Guitarix's input
  and its output to the recorder; to record directly in SoundText choose
  the PipeWire input as the audio interface.

**Windows and macOS** (Guitarix only works on Linux):
- **Neural Amp Modeler (NAM)**: free, VST3/AU plugin and standalone
  program, with models "captured" from real amplifiers (`.nam` files,
  thousands free on Tone3000) and IR loading for the cabinet. NAM profiles
  can also be used directly in SoundText (NAM profile, 8.4), on all
  systems, without re-amping (A1, A2 and LSTM); the plugin is for playing
  live;
- **AIDA-X**: free, similar to NAM and lighter, also on Linux;
- **GarageBand** (macOS): free, amplifiers and pedals already included;
- to apply a plugin to the dry WAV, **Audacity** is fine (free, VST3 on all
  systems, AU on macOS), or a recording program such as **Reaper**.

Live, NAM and AIDA-X also work as standalone programs: the guitar goes into
the simulator and SoundText records the output (with a virtual audio
connection, or by recording in another program and importing the file).

### 8.7 External plugins (VST3 and LV2)

SoundText can use the **audio plugins installed on the computer**, both as
**effects** in the chain of a track or of the master, and as **virtual
instruments** that play the notes of a track instead of the SoundFont.

- **VST3**: on Linux, Windows and macOS. SoundText looks for them in the
  standard system folders (on Linux `~/.vst3` and `/usr/lib/vst3`, on
  Windows `C:\Program Files\Common Files\VST3`, on macOS
  `/Library/Audio/Plug-Ins/VST3`); other folders are added from **Sounds → VST3 plugin folders...**
- **LV2**: on Linux only, and it needs the `lilv` system library (on
  Debian/Ubuntu the `liblilv-0-0` package, already present if Ardour, Carla
  or Guitarix are installed). LV2 plugins are found automatically. For
  example, with `guitarix-lv2` you get dozens of amplifiers and pedals.
- The **CLAP** and **VST2** formats are not supported.

**A plugin as an effect**: in the Effects panel (8.4) **+ Effect → Plugin
(VST3/LV2)** opens the list of installed effect plugins, with search by
name. The plugin card has:
- the **Mix** (how much processed sound to blend with the original) and
  **Level** (output volume) knobs, like the other effects;
- **Parameters...**, which opens a window with all the plugin's controls;
  changes are heard immediately in the panel's listening loop;
- **Change...** to replace it with another plugin.

In the parameters window, **Plugin interface...** opens the plugin's own
graphical window (VST3 only). When you close it, the settings made there
stay in the project.

**A plugin as an instrument**: **Track → Plugin instrument → Choose (VST3/LV2)...**,
or right-click the track name. Choose a virtual instrument (synth, sampled
piano...) and then adjust its parameters. The track's notes are played by
the plugin: the track's **volume** acts on the strength of the notes, the
**pan** on the position in the stereo image, and the track's effects are
applied after the plugin. To go back to the SoundFont choose **None: use
the SoundFont**. The name of the plugin appears under the track name.

Some LV2 plugins load a file: for example sfizz LV2 plays an **SFZ
file**. In the parameters window these properties have a row with
**Browse...** and **Remove**; the chosen file is kept in the project.

**Built-in SFZ instrument.** An `.sfz` file (a sampled instrument, like
the ones downloaded by `scarica_strumenti.py`) can also be played without
plugins: in the instrument list choose **SFZ instrument (built-in)...** and
then the file. It is played by the library of the **sfizioso** engine (or
of **sfizz**), installed once with `python3 scarica_strumenti.py libreria`
(on Linux also `./scarica_strumenti.sh libreria`; on Windows
`py scarica_strumenti.py libreria`, which needs Visual Studio Build Tools
with C++); without it, the entry is greyed out. This instrument has no parameters:
"Plugin instrument parameters..." lets you choose another file. Under the
track name the file name appears with "(SFZ)"; if you edit the `.sfz`
file, the song is recalculated.

The `.st` project remembers the plugin of every track and every effect,
with its parameters. When the project is opened on another computer, VST3
plugins are looked for by file name in the plugin folders.

**If a plugin does not work.** Plugins run in a process separate from
SoundText: if one hangs or closes unexpectedly, SoundText stays open. The
plugin is marked as **"not responding"** until the next start of the app.
An effect that does not work lets the sound through unchanged. A track
whose plugin instrument does not work plays with the SoundFont, and the
reason goes into the log file (Help). Some plugins simply cannot be loaded:
in the list they appear greyed out, with the reason next to them (for
example "not responding", or a plugin that only accepts mono audio).

**Limitations**:
- plugin instruments play in song playback, in the Effects panel loop and
  in the WAV export; quick previews (a keyboard note, listening to a
  pattern, a chord chosen with a double-click) still use the SoundFont;
- the MIDI and MusicXML export contains the notes, not the sound of the
  plugin;
- for LV2 plugins the parameter values and the chosen files are saved,
  not the rest of the internal "state";
- the first plugin search loads every VST3 once, and it may take a while;
  after that the list is remembered until a plugin changes (**Refresh
  list** redoes the search).

## 8bis. Song structure (box view)

An alternative to the linear text editor for working on the **structure**
of the song (intro/verse/chorus/solo...) instead of note by note: each
track becomes a row on a single shared timeline, and its content is divided
into **boxes** — rectangles that can be dragged horizontally, each one
self-contained like the body of a pattern (section 4), with its own name
and its own position in time. The actual content of each track
(`Track.text`, what playback/export/validation really read) is always
recomputed automatically from the sequence of its boxes: working with boxes
is not "another format", just a different way of writing the same text.

**Activation**: the **Structure** / **Text** buttons in the command bar, or
the **View → Song structure (boxes)** menu (shortcut `Ctrl+Shift+B`): they
switch between this view and the classic linear text editor. It is the view
SoundText opens with by default.

The colour of each box (and of the strip on the left of the track header)
reflects the instrument family (bass, guitar, winds, etc.), the same
convention used elsewhere in the app (e.g. section 7). The headers also
contain the track's mixer (see section 8).

### Creating a box

Double-clicking an empty spot of a row opens the editor of a new box at
that position (the same editing window described below). Right-clicking an
empty spot also offers:

- **New box from keyboard here** / **New box from audio here** / **Import
  MIDI here**: the same flows as "Play with the keyboard"/"Import
  audio"/"Import MIDI" of the track section (sections 10, 10bis, 10ter),
  but the result becomes a new box instead of replacing the whole track.
- **Generate drums in this track...** / **Generate bass from chords in this
  track...** (section 9bis): visible only if the track's instrument is
  respectively a percussion instrument or a bass; the generated box is
  queued right after the last existing box.
- **Paste here**: only if a box has been cut or copied first (see below).
- **Import from .box...**: loads a previously saved box (see "Exporting/
  importing a single box" below).

The same "Generate drums/bass" actions can also be reached by right-clicking
the track label on the left.

### Moving, selecting, editing

- **Dragging** a box repositions it in time on the SAME track (to move it
  to another track use cut/paste, not dragging): the position always snaps
  to the nearest whole beat, and a vertical guide line crosses all the
  tracks while dragging to line up boxes of different tracks by eye. If the
  chosen point overlaps another box of the same track, it automatically
  snaps to the nearest free edge instead of overlapping.
- **Single click** selects a box (edge highlighted in the accent colour)
  without moving it, even if the box was not already on a whole beat (e.g.
  after a tuplet, section 2.1bis): a small involuntary movement of the mouse
  between pressing and releasing does not count as dragging.
- **Double-clicking** a box opens the dedicated editor of its content (the
  same text editor with syntax highlighting, autocompletion and preview
  Play/Stop used for patterns, section 4) with the box's name and text,
  validated before you can confirm.

### Right-click menu on a box

- **▶ Play** / **■ Stop**: plays (or stops) the preview of the box's content
  with the instrument of its track — a dedicated preview engine,
  independent of the main F5/F6 transport.
- **Transpose...**: transposes the whole content of the box by semitones.
  References to patterns and MIDI files are transposed with the suffix:
  `%Giro` becomes `%Giro+2`, `&"Riff"+1` becomes `&"Riff"+3` (the pattern
  stays as it is, because others may use it too). If the box uses a bar
  anchor `bar=N`, **▶ Play** plays it from its place in the song, so the
  anchor reaches the right bar (the same holds for **▶ Play** on a
  selection).
- **Rename...**
- **Duplicate**: creates a copy on the same track, right after the end of
  the original box (or in the first free space available from there).
- **Cut** / **Copy** / **Paste here**: the clipboard also works between
  different tracks (that is how you move a box to another track).
- **Export as .box...** / **Import from .box...** (on an empty spot): see
  below.
- **Delete**.

### Undo/Redo (Ctrl+Z / Ctrl+Y)

Every action that changes the boxes of a track — moving, creating (in any
way), editing, transposing, renaming, duplicating, cutting/deleting,
pasting, importing from `.box` — can be undone with `Ctrl+Z` and redone
with `Ctrl+Y`, like any other change to the project (see **1.2
Undo/Redo**). Selecting or playing a box, on the other hand, generates
nothing to undo.

### Listening to the selected box only

There is a single transport: **Play/Stop** in the command bar play the
whole song. To listen to the selected box only (click a box to select
it): **Shift+Space**, or **Playback → Listen to the selected box**, or
right-click the box → **▶ Play**. Pressed again during playback it pauses;
once more it resumes from the point where it stopped, if you have not
selected a different box in the meantime (in that case it starts from the
beginning on the new one). **Stop** also stops box playback, and starting
the song with **Play** interrupts it: you always hear one thing at a time.
Shift+Space works in the Structure view: in the text editor it stays a
normal space.

### Hints

Above the track headers, **? How to use** summarises the commands of the
view (hover over it with the mouse, or click). Rows that are still empty
show in grey what can be done: create a box, import or record audio (audio
tracks), or that the track is written as free text.

### The playhead

While the whole song is playing (main transport, section 12), a vertical
line crosses all the tracks following the point being played, and the
canvas scrolls horizontally just enough to keep it always visible —
regardless of which box is selected.

### Exporting/importing a single box

**Export as .box...** (menu of a box) saves its content in a
human-readable text file (same style as the `.st` format, section 11, but
as a single block) in the `songs/` folder (section 5bis). **Import from
.box...** (menu of an empty spot) loads it again as a new box at any
point/track — useful to reuse a section (e.g. a chorus) across different
projects.

### Automatic conversion into boxes

When importing a whole MIDI file or converting audio into a track that
already uses boxes, the resulting text is automatically split into several
boxes wherever there is a continuous rest of more than 3 beats, instead of
staying one big box — so the content is organised readably right away even
for a long file, with no need to rearrange it by hand.

### Free-text tracks

A track without boxes (free text) shows nothing in the Song structure
view: **Edit free text...**, the last item of the right-click menu on its
name, opens its whole text in the same editor as the boxes (highlighting,
Play, Play of the selection), without leaving the view. The change can be
undone with Ctrl+Z.

**Convert to free text...** (in its place, for a track that already has
boxes) brings that track back to a single linear text editor: the musical
content does not change, only the way of editing it does. It is
irreversible only in the sense that it will not automatically go back to
being split into boxes: the text can still be split again by hand.

## 9. Freezing chords

The "Freeze chords into explicit notes" button in the editor replaces every
abstract chord of the current track with the `[...]` block of concrete
notes generated by the voicing engine for the assigned instrument.

### 9.1 Choosing the voicing with a double-click

A **double-click on a chord** — whether in compact form (`Cmaj7`, also with
a multiplier, e.g. `2Cmaj7`) or already "frozen" into explicit notes
(`[c*3 g*3 b*3 e*4]`, if recognisable as a standard chord), **even if the
chord is inside an `N(...)` repetition group** (see 2.1) — in the track
editor or in the body of a pattern opens a small menu with all the voicing
alternatives that make sense for the current instrument (see 2.8), each one
with a text preview of the resulting notes. Scrolling through the items with
the arrows you hear an audio preview of each (with a short delay, due to
rendering); **Enter** or a click on an item applies the choice (on the
implicit token it only adds/changes the `.style` suffix; on the explicit
block it recomputes the notes), **Esc** or a click outside the menu cancels
without changing anything. If the `[...]` block does not match any known
chord quality (e.g. a plain fifth `[c*3 g*3]`, ambiguous between major and
minor), a tooltip says so and the menu does not open.

### 9.2 Autocompletion while typing

While you type, the editor proposes in a popup the complete tokens relevant
to the fragment already typed, to speed up the longer notations or those
that are harder to remember:

- chord qualities (`C7`, `Dm7b5`...) starting from the root;
- voicing styles (`Cmaj7.drop2`, `C7.cagEd`...) after the `.`, limited to
  those applicable to the current track's instrument (see 2.8);
- percussion names, dynamics (`mf`, `ff`...) and state commands (`SON`,
  `SOFF`, `r`);
- `%Name` references to patterns defined in the project and `&"Name"`
  references to the MIDI library (see 6 and 11.1).

Up/down arrows to scroll the proposals, **Enter** or **Tab** to accept the
highlighted one, **Esc** or a click outside to close the popup without
changing anything. Single notes (e.g. `c`, `g#*4`) do not generate their own
suggestions, being already as short as a suggestion.

## 9bis. Generate drums/bass (without AI)

Generation of a drum or bass line without models/downloads/GPU:
algorithmic, based on a small library of patterns by genre (drums) and on
reading the chords already written in another track (bass). Instant and
without heavy dependencies.

**Variability** (in both dialogs): a slider from 0% to 100% (default 35%)
decides how far the result moves away from the basic pattern of the style.
At 0% the same style always gives the same text; higher up the generator
adds variations:
- **Drums**: soft ghost snares and extra kicks (only in the empty spaces:
  the hits of the pattern stay in place), hi-hat/ride hits that skip,
  slightly different velocities in every bar, half-bar or last-beat fills
  instead of always full ones. Many styles also have **alternative
  grooves** (e.g. rock with a syncopated kick, "steppers" reggae, funk with
  another kick): at the start of each group of bars the groove can switch
  to one of these, and the fills are chosen between the style's own one and
  some generic fills (snare roll, run down the toms, unison hits...).
- **Bass**: the alternative treatment (approach notes, third and seventh)
  also kicks in outside the rhythm of "Variation every N chords"; the notes
  after the first of a chord can get longer, go silent or rise an octave.
  The first note of every chord (the root) never changes, and the length of
  the chord stays identical. Now and then a bar uses an **alternative
  pattern** of the style (e.g. syncopated octaves, two-feel with an
  anticipated fifth): the choice is made bar by bar, so even a long chord
  (the 4 bars of tonic in the blues) changes rhythm inside. This also
  applies to accompaniment and riff. Variability does not only take away
  but also **adds**:
  - **passing notes** (bass and riff): at the end of a chord, a note leading
    to the root of the next one — a semitone below or above, a tone below or
    its fifth. If the last note is long, the passing note is added in its
    last beat; otherwise it takes its place;
  - **syncopated anticipations** (bass, accompaniment and riff on eighth or
    triplet grids): the first note or chord of the next pass arrives an
    eighth early, tied across the chord change, as in pop, rock and Latin.
    That is why the root can start an eighth before the bar instead of on
    the first beat.
  With the **Light** intensity there are no passing notes or anticipations.

**Intensity** (drums, bass, accompaniment and riff): how much "weight" the
part should have in the song.
- **Light (verse, intro)**: fewer hits and fewer notes — the drums drop the
  off-beat hi-hat/ride hits and the ghost notes and play softer; bass and
  accompaniment keep only the attacks on 1 and 3 (the remaining notes last
  longer).
- **Normal**: the style's pattern as it is.
- **Full (chorus)**: the drums move from the hi-hat to the ride, play louder
  and open each group of bars with a crash; the accompaniment's chords also
  take the octave above and the bass rises an octave on the last attack of
  each chord.
- **Building up**: light in the first third of the part, normal in the
  second, full in the last — useful for a bridge or a pre-chorus.

The **🎲 New variation** button draws a different variation with the same
controls. The variation is tied to a "seed" that stays fixed until you
press it: changing style, bars or octave does not make it "jump", and with
the same controls the text is reproducible. The generated text can still be
edited by hand in the preview before confirming.

**Presets and details of the variability.** Next to the slider, a menu with
three presets:
- **Faithful**: 15%, mostly dynamics, few notes and rhythms changed;
- **Musician** (default): 35%, variations like those of a session player;
- **Creative**: 75%, many variations, to look for ideas.

The menu shows "Custom" when the values do not match a preset. **Details ▸**
opens three sliders that say how much of the variability goes to each
aspect (100% = all of it):
- **Rhythm**: alternative grooves and rhythms, fills, anticipations, notes
  or hits that skip, get longer or get added (the extra kick of the drums);
- **Notes and harmony**: variants of the pattern, passing notes, octave
  jumps, the drums' ghost snares; in the chord progression, the chord
  colours and substitutions (it is the only aspect of the chord
  progression);
- **Dynamics**: different velocities hit by hit and note by note. For bass,
  accompaniment and riff, dynamics add the velocities (`N@`), louder on the
  first beat of the bar and softer on the off-beats; at 0% the notes have
  none, as before.

For example, with variability at 60% and Rhythm and Notes at 0%, the notes
stay those of the pattern and only the way they are played changes.

**Regenerate only some bars.** Below the preview: "Regenerate only the bars
from N to M" and **🎲 Regenerate these** draw a new variation only for those
bars, keeping the others as they are. It can be repeated on different
bars; the tweaks stay even when changing the other controls (style,
intensity...), **↺ Undo tweaks** removes them and **🎲 New variation**
regenerates everything from scratch. The cut never breaks a note: if a
note crosses the start or the end of the section (an anticipation, a long
chord) the section widens to include it. With variability at 0% the button
is disabled (the result would be identical).

**Compose → Generate into the selected track → Drums...** (requires a selected percussion
track):
- **Style**: the dialog proposes the styles written for the project's time
  signature. In 4/4: Rock, Funk, Four-on-the-floor (disco), Reggae (one
  drop), Punk, Soul (Motown), Bossa nova, Rock'n'roll, Shuffle (blues),
  Swing (jazz), Hip-hop (boom bap), Half-time, Metal (double kick), Country
  (train beat), Samba, Cha-cha-cha and March; in 3/4: Waltz and Jazz waltz;
  in 5/4: Rock in 5/4 (3+2) and Jazz in 5/4 (triplets); in 6/8: Ballad and
  Afro-Cuban; in 7/8: Rock in 7/8 (2+2+3) and Balkan in 7/8 (3+2+2); in
  12/8: Slow blues and '50s slow rock. The 7/8 styles use the eighth-note
  grid (`8:`). Each style brings its own rhythmic grid: most use sixteenths
  (`16:`), Shuffle and Swing eighth-note triplets (`8T:`), which is what
  produces their characteristic "swing". There is no grid selector in the
  dialog: a groove is written for a precise grid and cannot be adapted to
  another without changing its rhythm. In 6/8 and 12/8 the grid is in
  eighths (`8:`). Note: instruments playing at the same instant share the
  velocity (a limit of the `[...]` block notation).
- **▶ Listen / ■ Stop**: plays the preview as it is written (even after an
  edit of yours by hand) before confirming. With **With the other tracks**
  checked you hear it together with the rest of the project (Mutes are
  still respected, Solo is not; the current content of the destination
  track is not played); unchecked, it plays on its own. While it plays, the
  point you are listening to is highlighted in the preview (if you edit the
  text during playback, the highlighting pauses until the next Listen). Ok,
  Cancel or closing the window stop playback. This also applies to
  **Generate bass**, **Generate accompaniment/riff** and **Generate chord
  progression**.
- **Bars**: how many to generate.
- **Fill every N bars**: every N bars inserts a fill (with a crash coming
  back in on the next bar) instead of repeating the basic groove
  identically — 0 disables fills. It never inserts a fill on the last
  generated bar (it always closes on the basic groove).
- **Phrase fills** (checked by default): like a real drummer, at the end of
  each group of N bars it plays a **small** fill (last beat only) and at the
  end of each phrase of 2×N bars a **full** fill. Unchecked, all fills are
  full.
- **Ending on the last bar**: the last bar becomes a closing hit (crash and
  kick on the first beat, then silence), to end the song or the section.
- **Intensity**: see above.

**Compose → Generate into the selected track → Chord progression...** (requires a
polyphonic instrument: piano, guitar, organ, pad...): writes a chord
progression as symbols (`Am7`, `G`...), which the engine voices by itself
for the track's instrument. It is the starting point when the song has no
chords yet: bass, accompaniment and riff need a chord track to follow. In
the Song structure view the item appears in the right-click menu of a
polyphonic track as long as no other track of the song contains chords: the
track that already has the progression keeps offering it, and each new
progression goes into a box after the last one (as for **Generate bass**).
Conversely, **Generate accompaniment** and **Generate riff/melody** only
appear when another track contains chords (from the Compose menu, without chords, a message points you to the chord progression).
- **Key**: it starts from the project's one; if the project has none set
  and the track already has a progression, from the key of the box after
  which the new one will be placed (recognised from its chords or its
  notes); otherwise from C major. The styles proposed are those of its
  mode:
  - major: **Pop** (I-V-vi-IV), **'50s / doo-wop** (I-vi-IV-V), **Rock**
    (I-IV-I-V), **Pachelbel's Canon**, **12-bar blues**, **Jazz II-V-I**,
    **Jazz turnaround** (I-vi-ii-V), **Three chords** (I-IV-V-I),
    **Ballad** (I-iii-IV-V), **J-pop / royal road** (IV-V-iii-vi-ii-V-I),
    **Mixolydian rock** (I-bVII-IV-I), **Gospel** (I-I7-IV-iv), **Circle of
    fifths**, **Rhythm changes**, **12-bar jazz blues**;
  - minor: **Minor pop** (i-VI-III-VII), **Andalusian cadence**
    (i-VII-VI-V), **Minor rock** (i-VII-VI-VII), **Minor cadence**
    (i-iv-i-V7), **Minor jazz II-V-I**, **12-bar minor blues**, **Simple
    minor** (i-iv-v-i), **Epic minor** (i-VI-VII-i), **Dorian vamp**
    (i7-IV7), **Line cliché** (the voice descending chromatically inside
    the minor chord), **Minor circle**, **Phrygian** (i-bII).
  Lowered degrees (bVII of Mixolydian, bII of Phrygian) are written with
  flats (`Bb` in C, not `A#`), except in sharp keys.
- **Length of each chord**: half a bar, one or two (it multiplies the
  length of the style: in the blues some chords last several bars).
- **Bars**: the progression repeats until it covers them; **Whole
  progression** writes it once only. By default it covers the music already
  present in the other tracks.
- **Variability**: at 0% the style as it is. Higher up:
  - the chords get richer (sevenths, ninths, sus) while keeping the same
    function;
  - **secondary dominants**: a chord lasting at least one bar leaves its
    second half to the dominant of the next chord (in C: `A7` before `Dm`,
    `E7` before `Am`); if it lasts at least two bars, its last bar can
    become a **II-V** towards it (`Bm7b5 E7` before `Am`). The last chord of
    the progression is not prepared this way, unless it is the tonic:
    otherwise it would sound like a change of key;
  - **tritone substitute**: a dominant falling by a fifth becomes the one a
    tritone away (`Db7` instead of `G7` before `C`), never the tonic chord
    (the `C7` of the blues stays);
  - **minor IV** (in major): the IV going back to the I borrows the minor iv
    (`F Fm6 C`).
  Chromatic chords are written with flats (`Db7`), except in sharp keys.
- **Final cadence** (unchecked by default, to leave the progression open
  and ready to repeat): the last bar becomes the tonic chord, preceded for
  half a bar by a cadence chord. At 0% it is always `V7`; with variability
  it can also be plagal (`IV`), minor iv (`Fm6`), "backdoor" (`Bb7`) or
  `V7sus4`, in minor `V7`, `iv` or `VII`. Progressions that do not start
  from the tonic (II-V-I, royal road) always close with the dominant or its
  tritone substitute, because that is what establishes the key.

**Compose → Generate into the selected track → Bass from chords...** (requires another
track in the project with chords already written):
- **Chords from**: which track provides the harmonic sequence to follow
  (single notes/percussion/rests in that track are ignored, only chords
  count: both written as a symbol, e.g. `Cmaj7`, and as a `[c*4 e*4 g*4]`
  block of at least two notes, which is how MIDI import writes them; the
  block is recognised as a known chord, otherwise the root is the lowest
  note). A track made only of single notes (melody, arpeggios) has no chords
  to follow.
- **Style** (each one writes its own rhythmic grid: quarters, eighths or,
  for the shuffle, eighth-note triplets):
  - **Root**: repeats the root for the whole length of the chord.
  - **Root/fifth**: alternates them.
  - **Walking bass**: walks over the chord degrees with a chromatic
    approach note to the next chord (a simplification of jazz walking
    bass); the variant uses the chord's real third and seventh (minor third
    on a minor chord).
  - **Pedal**: a single long note per chord (ballads).
  - **Two beats**: root on 1 and fifth on 3 (slow jazz, country).
  - **Octaves**: root and octave alternating (disco, simple funk).
  - **Blues 1-3-5-6**: the classic blues/boogie line on the chord's real
    third (the variant closes with the dominant seventh).
  - **Eighths**: root in eighths (rock, pop, punk).
  - **Reggae**: the first beat stays empty, a long root from 2.
  - **Bossa nova**: root on 1 and 3, fifth on the "and" of 2 and 4.
  - **Shuffle blues**: 1-3-5-6-b7-6-5-3 in "swinging" triplet eighths.
  The patterns are simple generic models (one bar repeating over the
  chord), not transcriptions of songs; a chord shorter than a bar cuts the
  pattern short. With Variability some styles alternate a second pattern
  (see above).
- **Intensity**: see above (also in **Generate accompaniment/riff**).

**Generate accompaniment** also has **Close inversions** (checked by
default): each chord chooses the inversion closest to the previous one
(voice leading), as a pianist would — for example C-E-G, then C-F-A, then
B-D-G — instead of always staying in root position and jumping from one
position to another. The first chord stays as it is; all of them stay in
the instrument's range and do not move too far from the starting register.
It applies to chords of at least three notes (not to arpeggios and
two-note chords, which already have their own pattern).
- **Octave** of the generated bass line.
- **Variation every N chords**: every N chords uses a slightly different
  treatment of the same chord (octave jump, different note...) instead of
  repeating the pattern identically — 0 disables variations.

Both show a preview that can be edited by hand before confirming (like the
audio import, section 10bis), and the result is appended to the content
already present in the destination track, it does not replace it.

**Time signature**: the project's initial time signature is used. Bass,
accompaniment and riff repeat the style's pattern over bars of the right
length (3 beats in 3/4 and 6/8, 6 in 12/8...), so they work with any time
signature; a style meant for 4/4 is cut short to the shorter bar, and there
are styles made on purpose: **Waltz** for the bass (root on 1), **Waltz**
and **Arpeggio in 6/8** for the accompaniment. The drums instead require a
style written for that time signature (4/4, 3/4, 5/4, 6/8, 7/8, 12/8, or a
personal style saved in that time signature, see 9bis.1): with a time
signature without styles (e.g. 9/8) the dialog says so and disables
confirmation.

### 9bis.1 Personal styles: learning from your songs

Besides the ready-made styles, the generators can use styles derived from
a part of yours: a drum groove or a bass line you like becomes a new model,
which follows any chord progression.

**Where to save from** ("Save as generator style..."):
- right-click a **box** in the Song structure view;
- the **Compose → Generator styles → Save the track as a style...** menu (the whole selected track);
- the **MIDI library** (menu Compose → Manage MIDI library): the
  button below the preview offers all the channels of the selected file.

**The dialog:**
- **Part**: for a MIDI file, which channel;
- **Type**: Drums (for percussion parts), or Bass, Accompaniment,
  Riff/melody (proposed according to the instrument);
- **Chords from**: the part with the chords the pattern was played over
  (for a box, the chords at the same point of the song; for a MIDI file,
  another channel). It is used to work out which note is the root, the
  third, the fifth... Without chords, the first note of each bar acts as the
  root;
- **Time signature** and **Name**. Below, a summary of what was derived (how
  many bars read, grid, how many alternatives, whether there is a fill).

**How it is derived:**
- **Drums**: the bars are put on the grid (sixteenths or triplets; eighths
  in /8 time signatures). The most frequent bar becomes the basic groove,
  the other different ones (up to 3) the alternative grooves, used with
  variability, and the one with toms the fill. Without a bar with toms a
  generic fill is used (snare on the last beat). The crash on the first beat
  does not go into the groove, because the generator adds it.
- **Bass, accompaniment, riff**: each note becomes a **chord degree** in its
  octave (root, third, fifth, sixth, seventh, or a precise interval). On
  another progression the line follows the new chords, with the right third
  (minor on a minor chord). The last note before a chord change, a semitone
  from the new root, becomes an approach note towards the next chord,
  whatever it is. Rests stay rests. The most frequent bar is the basic
  pattern, the second the variant (used with "Variation every N chords"),
  others up to 3 the alternatives. For the accompaniment, boxes made only of
  chord symbols can also be used: their rhythm is derived. For the bass the
  lowest note of each attack is kept, for the riff the highest.

Saved styles appear in the generator dialogs with a **★** in front of the
name, at the bottom of the list; the drums only offer those of the
project's time signature. **Compose → Generator styles → Personal styles...** lists
them to rename or delete them. They are saved in the configuration folder
(`generator_styles.json`, next to the custom instruments), so they apply to
all projects.

### 9bis.2 Phrased melodies

In **Generate riff/melody** (monophonic instruments: trumpet, sax, flute,
voice, synth lead...), besides the riffs that repeat a pattern on the chord
notes, there are four styles that write a **real melody**:
- **Phrased melody (A A' B A)**: theme, theme repeated with a different
  ending, a contrasting phrase and the return of the theme;
- **Question-and-answer melody (A A')**: the first phrase stays "open", the
  second picks it up and closes it;
- **Slow melody (ballad)**: like A A' B A, with long notes;
- **Lively melody**: like A A' B A, with more eighths.

**How it is built:**
- **Phrases** of two bars (four in 3/4, 2/4 and 6/8). The form repeats until
  it covers the requested bars; the last phrase of the song always closes.
- **Motif**: phrase A has a rhythm and a contour that come back. In the
  repeat, if the same chords are underneath, A comes back identical, except
  for the ending; on different chords the motif moves onto the new chord,
  with the same rhythm and the same shape. B has another rhythm (busier, or
  calmer in the lively version) and goes higher.
- **Harmony**: on the strong beats (first beat and half bar, and long notes)
  the melody uses chord notes; on the other beats it prefers chord notes;
  on the off-beats scale notes, preferably by step. Chord notes outside the
  scale replace the nearby natural one (the G# of `E7` in A minor, the Bb of
  `C7` in C).
- **Shape**: each phrase rises towards a high point, around two thirds, then
  falls to the cadence. After a leap the melody turns back; it avoids huge
  leaps, three equal notes in a row and back-and-forth "trills".
- **Cadences**: an "open" phrase (the question) ends on a chord note other
  than the tonic, preferably the fifth or the second of the scale. A
  "closed" phrase (the answer) ends on the tonic, or, if the chord does not
  contain it (a phrase ending on the V), on the third or the fifth of the
  tonic.
- **Key**: the project's one; if it is not set, the one recognised from the
  chords of the track chosen in "Chords from".

"Variation every N chords" does not apply to these melodies (the field is
disabled): they have their own form. The other controls work as for the
other styles:
- **Variability**: at 0% the melody depends only on chords, style and key.
  Higher up, **🎲 New variation** draws another motif. The **Rhythm**
  slider makes the rhythms more varied and can change a bar in the repeats;
  **Notes and harmony** makes it choose less "obvious" notes and changes a
  few notes in the repeats; **Dynamics** makes the volume grow towards the
  highest point of each phrase and accents the beats.
- **Intensity**: Light makes the melody calmer (fewer notes), Full busier,
  Building up busier and busier across the song.
- **Regenerate only the bars** applies here too.

## 10. MIDI Import/Export

- **Project → Export → MIDI**: the whole ensemble (tracks audible according
  to Solo/Mute) in a single multitrack MIDI file.
- **Project → Import → MIDI**: creates a new project with one track for each
  channel of the MIDI file; channel 10 always becomes Drums.
- **Track → Export this track / Import into this track → MIDI**: exports only the
  selected track, or imports a MIDI file (choosing the channel, if the file
  contains more than one) replacing the content of the current track; you
  are also offered to update the instrument based on automatic recognition.

**Automatic instrument recognition/creation**: for each channel, if an
instrument already available (built-in or custom) has exactly the
channel's GM Program Change, that one is used; otherwise **a new custom
instrument is automatically created and registered** with that exact
program (name derived from the official General MIDI name, e.g. program 81
→ `Lead2sawtooth`; octave/range/voicing parameters suggested according to
the family, as when creating one manually from **Sounds → Manage
instruments**), so the imported track always faithfully reflects the
original instrument instead of settling for the closest approximation. At
the end of the import, if new instruments were created, a notice lists
them (they can always be edited afterwards from **Sounds → Manage
instruments**). This automatic creation only happens for an import that is
actually confirmed (not for the mere preview in the channel selector, which
keeps showing the name of the closest instrument already available).

**Channels that change instrument**: if a channel changes instrument
mid-song (a Program Change between the notes: in *Layla* the intro riff is
on overdrive guitar and then switches to piano, on the same channel), the
multi-track import creates **one track per instrument**, each with only
the notes played with that instrument and with the volume and pan in
effect when it comes in. If the channel goes back to the same instrument
several times, those parts go in the same track. The drum channel is not
split (there the program chooses the kit).

Note on import accuracy: the notation supports chromatic notes (`c#`,
`eb`, etc.), so pitch is preserved; rhythm is quantised to a sixteenth-note
grid or, bar by bar, to a **triplet** grid when the attacks require it (see
below).

**Triplets and tuplets**: for each beat the import chooses the subdivision
that best explains the attacks. The binary grid (sixteenths) wins if it
explains them all; otherwise an eighth-note triplet (`8T:`, section 2.1bis)
is used when it explains them and the binary grid does not — typical of
shuffle, 2:1 swing and 12/8 blues, where notes used to be moved to the
nearest sixteenth. Sextuplets (`16T:`), quintuplets (`16Q:`) and septuplets
(`16S:`) have much stricter thresholds (more attacks in the beat and a much
smaller deviation are needed), otherwise slightly imprecise human playing
would be mistaken for a tuplet. Nearly simultaneous attacks (kick and ride a
few ticks apart) count as a single rhythmic point, and quintuplets/
septuplets are in practice only recognised on very regular passages. The
grid command is written only when it changes. A note that, starting on one
grid, would end inside a beat with another grid, at a point that is not a
beat boundary, is closed at the boundary: it may therefore end up slightly
shorter than the original, but the rest of the track never shifts. A purely
binary file produces the same tokens as before.

**Overlapping notes and voices**: in ST the only simultaneous notes are
those of the same `[...]` block (same length), whereas in MIDI a note held
under a melody, or a chord continuing under a voice, overlap. The import
used to skip every attack falling inside a longer note: in a test library
about 8% of the notes disappeared, and in some files almost half. Now the
**import of a whole file** splits each channel into **monophonic voices**
(at most 2 per channel, always: if more groups of different lengths than voices
start on the same attack, the extra groups merge with the one of closest
length; never for drums): notes that start together and end (within a
sixteenth) together stay a single block, each group goes into the first
free voice, and a minimal overlap (legato within a sixteenth) shortens the
previous note instead of opening a voice. The voices stay **in the same
track**: where only the first one plays the text is as always, where the
others play too it becomes a **voice block** `{ ; }` (section 2.12) on a
line of its own, which starts and ends on bar lines when that cuts no
note; the merged text sounds exactly like the separate voices. (Up to the
previous version each voice became a separate track, `Piano voce 2`.) The
same applies when importing a **single channel** into a track. The tempo
(`tempo=N`) is in the first voice. When the voices run out, the previous note
is **shortened** to the next attack: the held length is lost, never the
note.

**Lyrics**: the *lyrics* events of the file, and the text of karaoke files
(`.kar`, text events in a track without notes), become lyrics in double
quotes (section 2.13) on the first voice of the channel that sings them
(the one with notes in the same MIDI track, or the one whose notes start
where the syllables fall): one line per bar after its notes, `*` for a
note without a syllable and `""` before a sung passage that follows an
instrumental one.

 **MIDI channels with many tracks**: a MIDI file has only 15
melodic channels (channel 10 belongs to the drums) and each channel has
only one instrument, one volume/pan and one pitch bend. With more than 15
tracks (easy with the voices from the import) the export first assigns a
channel to each *different* instrument, then the remaining channels to the
extra voices, and the rest share the channel of their own instrument: no
track ever plays with another track's instrument. Voices of the same
instrument sharing a channel have a common pitch bend (a slide on one is
also heard on the other's notes while they play together).

Identical notes on the same tick (doublings) and attacks on the same pitch
within the same sixteenth merge into one.

**Velocity of simultaneous notes**: in ST each token (note, chord or `[...]`
block) has a single velocity, so the different velocities of the notes of
one group (for example an accent on the top voice of a chord, or drum kick
and hi-hat hit together) cannot be kept one by one: the imported group
takes the **rounded average** of the velocities, which preserves the
overall intensity. With all velocities equal nothing changes.

**Dynamics from volume and expression (CC7/CC11)**: crescendos,
diminuendos and fades in the MIDI file are continuous automations, which ST
expresses only as note velocity (section 2.5). The import computes the CC7 x
CC11 level at the moment of each attack, normalises it to the channel's
maximum and applies it to the note's velocity: the loudest note of the
channel keeps its original velocity, the others drop proportionally, and
the result appears as a series of `N@` (in steps, one for each note that
changes, not as a `>>` ramp). A constant volume (typically CC7 = 100) or a
variation below 15% of the maximum is not a dynamic and is ignored. The
*absolute* volume of the channel relative to the others is not imported
(set it from the mixer).

**Articulations (`!`, `x`, `_`)**: for single notes and implicit chords
("Recognise chords" option) the import compares the note's real length with
the interval up to the next attack: about half → staccato `!` (section 2.2),
less than 30% → mute `x`, over 105% (a note overlapping the next one) →
legato `_`. In that case the token takes up the whole interval up to the
next note (e.g. `2c*4!`) instead of a short note followed by rests, so it
stays editable the way a musician would write it. A short note followed by
a long rest (more than a beat, or half a beat for mute) stays note + rest:
it is not an articulation. Normal notes (about 70%-105%), explicit `[...]`
blocks (without a final modifier, section 2.2), slides and drums do not
change.

**Tempo, time signature and pedal**: the file's tempo changes become `tempo=N`
markers (section 2.6) — in **one track only**, because tempo is global in
ST: the one on which the markers drift least is chosen (usually the drums,
made of short hits; a marker that would fall inside a long note is emitted
at its end). The initial tempo stays the project's, and small fluctuations
(less than 2 BPM or 2%: the noise of a tempo recorded live) are not tempo
changes and are ignored. The time signature (*time signature* event) sets
the project's **Time sig.** field; if it changes during the song it
becomes the per-bar list (`Metrica: 1: 3/4, 3: 4/4`, section 2.7). The
sustain pedal (CC64, on from 64 upwards) becomes `SON`/`SOFF` (section 2.4),
only at actual transitions; a pedal still pressed at the end of the channel
is closed with a final `SOFF`. MIDI export now also writes the time
signature, so an export→import round trip keeps it. When importing a single
channel into an existing track, tempo and time signature changes are NOT
imported (they are global to the project); the pedal is.

**Bending (pitch bend)**: a single note (never a chord) whose pitch bend
reaches at least a full semitone during its length is imported as a
**slide** (`c*4>d*4`, section 2) from the starting pitch to the peak of the
bend, instead of being flattened to the nominal pitch — useful especially
for blues/rock guitar MIDI files, where bending is often an integral part of
the phrase. If the pitch wheel then comes back significantly towards a
different semitone before the end of the note (bend-and-release, a common
technique: up and then release), the imported slide has a third stage
(`c*4>d*4>c*4`, section 2.3) instead of stopping at the peak alone. The
lengths of the individual stages (section 2.3) reflect the REAL timing of
the bend detected in the source MIDI — when the peak is reached relative to
the note's length — instead of always assuming a half-and-half split
between ramp and hold/release: a quick bend followed by a long hold (e.g.
`1c*4>3d*4`) therefore sounds different, and more faithful to the original,
than a slow bend that reaches the peak only towards the end (e.g.
`3c*4>1d*4`). The pitch bend sensitivity declared in the file (RPN 0, Pitch
Bend Sensitivity) is respected; if the file does not declare it the General
MIDI default (±2 semitones) is assumed. A bend that rounds to 0 semitones
(vibrato or recording imprecision), too small relative to the pitch wheel's
full scale (a continuous expression/humanisation automation, not a
deliberate bend) or implausibly wide (over 12 semitones: real guitar bends
almost always stay within 2-3 semitones, and a wider jump is not a bend on
any instrument — it would be a different note, not a bending of the same
one; it happens when the declared RPN sensitivity reflects a technical
capability of the channel, not the bending intention of that specific
note) stays a normal note, to avoid a musically meaningless slide.

**Slide guitar (Options → MIDI import → Slides in MIDI import...)**: on a channel with a
wide pitch bend sensitivity (12 semitones, typical of slide guitar MIDI
files) the usual threshold is about 1.2 semitones, and short one-semitone
bends stay normal notes. Ticking **Slide** in the dialog enables the
**Threshold** field (0.5-1.2 semitones, default 0.8): the import also
recognises smaller bends as slides. The threshold can only go down, so on
channels with a narrow sensitivity (e.g. 2 semitones) nothing changes. The
lower it is, the more slides are found but the greater the risk of
mistaking a pitch wheel expression for a slide (seen on jazz pieces): keep
it high for non-slide pieces. The setting applies from the next import, and
without the tick the import stays exactly as before. The **release
timing** is the file's real one: a bend that rises immediately, stays on the
peak for almost the whole note and releases only at the end becomes a
4-stage chain with the hold as a flat ramp (`1f*5>11g*5>1g*5>3f*5`: rises,
holds the G, releases, stays on the F); one that releases immediately and
then stays on the written pitch has the long final hold (`1e*5>1d#*5>2e*5`),
instead of being spread linearly over the whole note (which made the
intonation drift for the whole length). If the release only starts at the
very last moment, the note ends while still releasing and a simple bend
with hold is written (`1f*5>3g*5`). A **release tail** of the previous note
(the wheel is still going back towards the centre when the note starts) is
not a bend: the reference stays the centre.

**Late-starting bends and two-way bends** (typical of slide/bottleneck):
if the wheel stays almost still for a stretch (at least 15% of the note,
with small drifts) before moving, the slide has an initial hold
(`7d*4>1d*4>8c#*4`: stays still, then goes down) instead of starting from
the attack. If the wheel has significant excursions on *both* sides of the
written note (goes up a tone and then down below), the bend is imported as a
multi-stage path — the wheel curve simplified (maximum deviation 0.7
semitones) and rounded to semitones — instead of keeping only the largest
excursion. On notes a few sixteenths long the grid limits precision: each
ramp takes at least a sixteenth.

**Wide bends (up to an octave)**: the limit used to be 4 semitones; now it
is **12** (an octave), because with a wide declared wheel sensitivity (RPN)
real glissandos and bends of 5-12 semitones exist — slide/bottleneck, the
tape-style pitch drop of the strings in *Strawberry Fields Forever*,
whammy-bar "dives". Beyond an octave it stays a normal note (it is not a
bend). If a channel starts already bent (scoop) and inside the note the
wheel dives **further** from the centre than where it started by at least
1.5 semitones (starts at -4, goes down to -12, then comes back up), the dive
is kept: a multi-stage path with the centre as reference, not a simple
scoop. A late dive (past half the note, with at least 3 events in the
descent) leaves the note still until then.

**Pre-bend of the next note**: when the wheel moves away from the centre in
the last ticks of a note (within a tenth of a beat) and is still off-centre
at the attack of the next one, that movement is the pre-bend of the OTHER
note and not a phantom bend at the tail of the first. If instead it goes
back to 0 right at the next attack (a fall-off returning to zero), it
belongs to the note that is ending.

A **pre-bend / scoop** (the pitch wheel is already off-centre *before* the
attack and comes back to the centre during the note: a string already bent
and then released, or a note "taken from below", typical of guitar and
vocal MIDI files) is imported as a slide from the *real* starting pitch to
the written note: a wheel at -1 semitone rising to 0 on a D becomes
`c#*4>d*4` (C# rising to D), and one at +1 going down becomes `d#*4>d*4`.
The pitch written in the MIDI is always the arrival one. An off-centre wheel
that NEVER comes back to the centre during the note stays a static offset of
the channel (a normal note). Note: ST slides work in whole semitones, so a
real bend of roughly a semitone is rounded to the nearest whole semitone.

**"Recognise chords in MIDI import" option** (**Options** → checkbox of the
same name, off by default): when a group of simultaneous notes matches a
standard chord quality (e.g. C major), it is imported in the equivalent
implicit form (`C*4`) instead of as an explicit block (`[c*4 e*4 g*4]`) —
more readable and easier to transpose by hand. A chord that cannot be
recognised (e.g. a bare fifth, ambiguous between major and minor) stays an
explicit block anyway. **Note**: unlike the explicit block, which always
faithfully reproduces the original MIDI voicing and register, the implicit
form is **automatically re-voiced by the engine** according to the track's
instrument at the next export — useful to adapt the chord to the target
instrument, but an import→export round trip will no longer necessarily
reproduce exactly the same notes as the original file. The default
behaviour (explicit block) therefore remains the most faithful.

### 10.1 Exporting the score (MusicXML)

**Project → Export → MusicXML score...** saves the song as a score in
**MusicXML** format (`.musicxml`), which opens in notation programs:
MuseScore (free), Finale, Sibelius, Dorico and many others. From there you
can print, export to PDF, fix the layout or add lyrics. Like the MIDI
export, it contains the **audible tracks** (it takes Solo and Mute into
account); audio tracks have no notes and are left out.

What the score contains:

- **one part per track**, with the track's name;
- **the notes** exactly as SoundText plays them: chords appear with the
  notes chosen by the voicing engine, `[...]` blocks as written chords;
- **chord symbols** (`Am7`, `C/E`...) above the staff, written only when the
  chord changes, as in a lead sheet;
- **the key** of the project (section 2.7bis) as the key signature; chord
  notes use flats in flat keys;
- **time signature and tempo**, including per-bar changes (section 2.7) and
  the tempo markers in the tracks;
- **triplets, quintuplets and septuplets** with their bracket;
- **dynamics** derived from velocity (`p`, `mf`, `f`...), written only when
  the new level lasts at least four notes, **articulations** (staccato,
  stopped, legato) and sustain **pedal**.
- **the voices** of `{ ; }` blocks (section 2.12) as voices of the same
  staff, with stems up and down;
- **the lyrics** (section 2.13) under the notes, with hyphens and
  extension lines.

Clefs follow the conventions of printed parts: pianos and organs on two
staves (treble and bass, split at middle C), guitars in treble clef and
basses in bass clef with an **8 below** (they sound an octave below the
written pitch), other instruments in treble or bass clef according to their
register. Drums use the percussion staff with the usual positions (kick at
the bottom, snare in the middle, cymbals at the top with an **x** head).

A length that does not match a note value (for example 5 eighth notes) is
written as **tied** notes, and a note crossing the bar line continues tied
into the next bar.

**Limits**: within the same voice two overlapping notes (it happens in
songs imported from MIDI) cannot coexist: the first is shortened up to the
attack of the second. To really write several voices, use `{ ; }` blocks.
Slides appear with the starting note only.

### 10.1bis Viewing and printing the score (View → Score)

**View → Score...** (`Ctrl+Shift+P`) opens a window with the tracks on
staves, laid out on A4 pages: the same notes, chord symbols, voices and
lyrics as the MusicXML export, **without external programs**. The window
stays open next to the editor and **updates as you type** (after a short
pause in typing).

- **All audible tracks** or **Selected track only**.
- **−** / **+**: zoom.
- **Export PDF...** saves the score as a PDF (vector, printable at any
  size); **Print...** sends it to the printer.
- If a track has a syntax error, the last valid score stays visible, with
  the error message.

**Project → Export → PDF score...** does the same without opening the
window.

The layout is done by **Verovio**, a free music engraving library (LGPL)
installed together with SoundText. If it is missing, the window explains
how to install it (`pip install verovio`); the MusicXML export works
anyway. For layout touch-ups (spacing, free text on the page) the
MusicXML → MuseScore route remains.

### 10.2 Importing a score (MusicXML)

**Project → Import → MusicXML...** creates a new project from a **MusicXML**
score (`.musicxml`, compressed `.mxl` or `.xml`), the exchange format of
MuseScore, Finale, Sibelius, Dorico and almost every notation program;
many free scores online can be downloaded in this format. It can also be
opened directly from the command line (`soundtext song.musicxml`).

What the score becomes:

- **one track per part**, with the name of the part ("Flute",
  "Violin I"...) and the instrument given in the score (or recognised from
  the part name); two voices on the same staff become voices of the same
  track (`{ ; }` blocks, section 2.12), as in the MIDI import (section 10);
- **notes at concert pitch**: transposing instruments (sax, clarinet,
  B♭ trumpet, guitar written an octave up) sound as they are heard, not
  as they are written;
- **tempo, time signature and key**, with tempo and time signature
  changes, and **dynamics** (`p`, `mf`, `f`...) as velocity;
- **repeats, 1st/2nd endings, D.C., D.S., Fine and Coda** unrolled in the
  order they are played; after a D.C. or D.S. repeats are not taken again
  and the last ending is played, as is customary;
- **tied notes** become a single note; a **pickup** bar at the start is
  completed with a rest, so bars stay in place;
- **chord symbols** (`Am7`, `G7b9`, `C/E`...) become a **Chords** track
  ("Accordi"): in a lead sheet (melody and chord symbols) it is audible
  and accompanies the melody; if the score already has other parts playing
  the harmony, the track is muted (just turn Mute off to hear it). Chord
  symbols SoundText does not have become the closest one (for example
  `m11` becomes `m9`).

Drums written on the percussion staff become a percussion track, with the
sounds given in the score. Grace notes (written small) are ignored. The
**lyrics** become lyrics in double quotes (section 2.13), with hyphens and
elisions; in repeats the verse of that pass is used (1 the first time, 2
the second), if there is one. The **Recognise chords** option of the MIDI import applies here
too.

### 10.3 ABC notation (import and export)

**ABC** is a plain-text music notation (standard 2.1), used by the large
collections of traditional and folk music and by programs such as abcjs,
EasyABC, abcm2ps and abc2midi: an `.abc` tune can also be read and written
by hand.

**Project → Export → ABC score...** saves the audible tracks as an ABC
tune:

- each track is a **voice** (`V:`) with its name and instrument
  (`%%MIDI program`); piano and organ have two staves joined by a brace,
  the voices of `{ ; }` blocks share a staff (`%%score`); drums are on
  channel 10, with the notes of the General MIDI sounds;
- **key** (`K:`), **time signature** (`M:`, with the changes in every
  voice), **tempo** (`Q:`), **chord symbols** in quotes, **dynamics**
  (`!mf!`), staccato and tenuto, **triplets** and the other tuplets, notes
  tied across bar lines and **lyrics** (`w:`);
- guitars and basses use the octave-down clef (`treble-8`, `bass-8`), with
  the notes written an octave higher as the standard requires.

Slides become their first note; the pedal and the automations (`vol=`,
`pan=`... section 2.15) are not written (they are not in the standard).

**Project → Import → ABC...** creates a new project from the first tune in
the file (it can also be opened from the command line: `soundtext
tune.abc`). It reads notes, rests, chords `[CEG]`, the unit note length
(`L:`, or the one implied by the time signature), broken rhythm (`>`
`<`), tuplets `(3`, `(p:q:r`, ties (also across bar lines, keeping the
accidentals), accidentals that last until the bar line, keys with modes
(`Dmix`, `Ador`...: they become the key with the same signature), `[K:]`
`[M:]` `[L:]` `[Q:]` changes, **repeats and 1st/2nd endings** unrolled,
the **pickup** bar, dynamics, chord symbols (in the **Chords** track, as
for MusicXML) and lyrics with several verses. Each voice is a track;
voices on the same staff (`%%score (S A)`) go into one track, and so do
the two piano staves (`{RH | LH}`). The instrument comes from `%%MIDI
program` (`%%MIDI channel 10` or `clef=perc` for drums), otherwise from
the voice name. Octave clefs, `transpose=` and `octave=` sound at concert
pitch. Grace notes, parts (`P:`) and decorations that do not change the
sound are ignored.

## 10bis. Audio import (voice/microphone/file)

Menu **Track → Import into this track → Audio → notation (microphone or file)...** (also
from the track's **⋯** menu, item "Import audio → notes...", and as "Import
audio (into this pattern)" in the **Compose → Manage pattern
library** dialog, to capture a reusable pattern directly instead of a
track): converts a musical idea captured via microphone or audio file
(`.wav`/`.mp3`/`.m4a`) directly into text notation, inserted into the track
(or into the pattern body) after a text preview and optional listening.

- **Source**: record button (Start/Stop) from the microphone, or drag a
  file onto the dedicated area (drag-and-drop) or use "Browse files...".
  When recording with the **Metronome** on, the click restarts together
  with the recording: the first beat coincides with the start of the file
  and the transcription follows the metronome (a rest before the first note
  stays a rest). Without the metronome the transcription starts from the
  first note, whenever you pressed Record. The microphone requires
  `libportaudio2` installed system-wide on Linux (see the Installation
  section); mp3, m4a, flac and ogg files are read by the Qt Multimedia
  decoder, already included in PySide6 (or by `ffmpeg`, if the
  distribution's PySide6 lacks it). If something is missing the dialog
  says so with an explicit message instead of failing silently.
- **Quantisation**: selector with Off, 1/4, 1/8, 1/16 (default), 1/32, plus
  a "Triple" checkbox (8T/16T triplets) enabled only for 1/8 and 1/16. "Off"
  does not introduce a new kind of free timing: internally it uses a very
  fine grid (1/64), below the perceptible quantisation threshold, while
  still staying within the normal `N:` syntax. The last combination used is
  remembered when the dialog is reopened.
- **Analysis mode**: Melodic (pitch detection, for voice or instruments
  playing one note at a time: chords are not recognised) or Percussive
  (transient detection for drums/beatbox, automatically classified as
  `kick`/`snare`/`hihat`). Pre-filled according to the current track's
  instrument, but always changeable by hand. In Percussive mode the chosen
  quantisation also matters for detection: two hits closer than about half
  a grid slot are considered a single hit (with 1/16 at 120 BPM, 75 ms), so
  choose a grid at least as fine as the fastest notes you played (1/8 for
  hihat in eighth notes, 1/16 for sixteenths).
- **Algorithms**: onsets are found with SuperFlux (spectral flux that
  does not mistake vibrato for a new note), pitch with YIN; both are
  written inside SoundText (in numpy), with no libraries to install.
- **Advanced pitch tracking parameters** (Melodic mode only): they let you
  adapt recognition to a specific audio instead of settling for the default
  result — adjust the values, press "Convert to SoundText" again to retry on
  the same file, repeat until the result convinces you:
  - **Minimum frequency**: automatic (deduced from the low range of the
    target instrument) or a value in Hz chosen by hand.
  - **Analysis window**: number of samples per estimate — wider helps on
    basses/low notes but worsens time resolution (attacks/short notes less
    precise).
  - **Analysis step (hop size)**: distance in samples between one estimate
    and the next — smaller gives more time resolution but a slower
    analysis.
  - **Confidence threshold**: minimum confidence to accept an estimate.
  - **Minimum note length**: discards notes shorter than this threshold,
    almost always artefacts (spurious close onsets, typical of strong
    vibrato).
  - **Restore standard values**: brings the whole panel back to the
    defaults.
- **Source: voice/beatbox**: checkbox to turn on when you are singing/
  humming the part (bass, melody...) or imitating the drums with your mouth,
  instead of recording the real instrument. The human voice has different
  acoustic characteristics from a real instrument: pitch less stable note by
  note (it easily fragments into short, erratic notes) and, for drums, no
  real low resonance like that of a kick drum (the vocal tract is physically
  too short to produce it). With the checkbox on: for the melodic part the
  analysis window is not widened to the target instrument's low range
  (useless if you are singing in your own vocal range anyway, and harmful to
  time resolution); for drums the kick/snare/hihat thresholds are
  recalibrated for a mouth "boom" instead of a real kick drum.
- **Conversion**: the "Convert to SoundText" button analyses the audio in
  the background (with a progress bar; "Cancel" stops it and you can retry
  right away with other parameters) and shows the result in a preview with
  syntax highlighting, before any insertion; the generated text is always
  validated and is never inserted if it turns out to be syntactically
  invalid.
- **Editable preview**: once the conversion is complete, the preview is no
  longer read-only: you can fix a wrong note by hand or try an alternative
  directly in the text, before confirming. "Listen to preview" always plays
  the CURRENT content of the editor (including manual changes, not the
  original text generated by the analysis); if the changes break the
  syntax, both "Listen to preview" and Ok report the error instead of
  proceeding. A new conversion (new file, other pitch algorithm, etc.)
  overwrites any manual change not yet confirmed.
- **Listen to preview**: the "▶ Listen to preview" button (with "■ Stop"
  next to it), enabled after a successful conversion, plays the current
  content of the preview with the target instrument before confirming with
  Ok — useful to check the conversion (or your own variant) by ear before
  replacing the content of the track/pattern.

Note on recognition quality: melodic note detection segments the audio with
a dedicated onset detector (reliable even in the low register and on the
"legato" transitions typical of singing, with no silence between one note
and the next) and estimates each note's pitch with the median of the
measurements in the interval — more robust to vibrato and to the small
intonation inaccuracies of a non-professional voice than a single
instantaneous measurement. Each note ends when the sound dies away (not
necessarily at the next attack), so detached notes leave rests; the same
note played several times in a row (typical of the bass) stays a series of
distinct notes, even without a rest in between, while a note held with
vibrato or tremolo stays a single note. Dynamics are relative: the loudest
note (or hit) of the recording becomes `110@` and the others drop
proportionally, in steps of 10, so even a low-volume recording sounds full
and the text does not fill up with small `@` changes. For the lowest notes
(e.g. bass) the analysis window widens automatically according to the
target instrument's lowest range, for a more precise pitch estimate (it
does not affect onset detection, handled separately). Automatic percussive
classification recognises only `kick`/`snare`/`hihat` from the spectrum of
the "body" of the hit (right after the attack transient; not
tom/crash/ride/hihat_open, unreliable without a dedicated model); the
generated text can always be edited by hand like any other token. The
thresholds of the "voice/beatbox" mode are a reasoned estimate based on
the acoustic behaviour of the vocal tract, not calibrated on real
recordings: if the results are not satisfactory, the `diagnose_audio.py`
script (in the program folder) lets you inspect the raw data used by the
classification on your own recording, for a targeted calibration instead
of trial and error; fixing the generated text by hand is always possible
anyway.

## 10ter. Play with the keyboard (computer keyboard or MIDI keyboard)

Menu **Track → Play with the keyboard in this track...** (also as the
"Play with the keyboard..." item of the track's **⋯** menu, and as "Play
with the keyboard (into this pattern)" in the **Compose → Manage
pattern library** dialog): records a performance played live on the
computer keyboard — used as if it were a small musical instrument — and
converts it into notation, with the same final flow (editable preview,
"Listen to preview", Ok/Cancel) as the audio import dialog (section 10bis),
of which it is the "instrument played live" counterpart instead of
"recorded/loaded audio".

- **Keyboard layout** (Italian layout): three rows of 12 keys each, each
  one an octave above the previous, run through chromatically starting from
  C — number row (`1`...`0`, `'`, `ì`) on the octave chosen with the
  dialog's "Octave" selector, row `Q`...`P`, `è`, `+` an octave above, row
  `A`...`L`, `ò`, `à`, `ù` two octaves above. The exact legend (with the
  actual octave of each row) is always visible in the dialog.
- **Independence from the keyboard language**: the notes (three rows above)
  and the chord quality row (`Z X C V B N M , . /`, next section) are tied
  to the physical POSITION of the key pressed, not to the character it
  produces — changing the system language/layout (e.g. from Italian to
  US/UK/German) the same physical keys keep playing the same notes, even if
  the character printed on the key (or produced when typing elsewhere) is
  different. It covers 45 of the 46 keys involved: the only one excluded is
  the last key of the `A`...`L` row (the one producing `ù` on the Italian
  layout — an "extra" key of European ISO layouts with no unique equivalent
  on a US keyboard, whose exact physical position cannot be reliably
  determined on every layout). A fallback is still available for that key:
  **Enter** (both the main one and the numeric keypad one) always plays the
  same note as `ù`, whatever the active layout — Enter is not a character
  key, so its position is layout-independent in itself. Verified on Linux
  (X11 and Wayland); on Windows and macOS it relies on the same documented
  standards but it could not be verified interactively during development —
  if a key turns out to be in the wrong place on those platforms, please
  report it.
- **Chords on the fly**: holding down a key of the `Z X C V B N M , . /` row
  together with the note key (any of the three rows above) plays the
  corresponding chord instead of the single note:

  | Key | Quality | Intervals |
  |---|---|---|
  | `Z` | Major | 1 - 3 - 5 |
  | `X` | Minor | 1 - ♭3 - 5 |
  | `C` | Dominant 7th | 1 - 3 - 5 - ♭7 |
  | `V` | Minor 7 | 1 - ♭3 - 5 - ♭7 |
  | `B` | Major 7 | 1 - 3 - 5 - 7 |
  | `N` | Suspended (sus4) | 1 - 4 - 5 |
  | `M` | Added 9th (add9) | 1 - 3 - 5 - 9 |
  | `,` | Diminished 7 | 1 - ♭3 - ♭5 - 𝄫7 |
  | `.` | Power Chord | 1 - 5 - 8 |
  | `/` | Deep bass | note + octave below (not a real chord) |

  The quality key must be held BEFORE/together with the note key (pressing
  it afterwards does not retroactively "update" a note already played); if
  several quality keys are held together, the last one pressed that is still
  active wins. As for the notes, this row does not depend on the chosen
  layout (Chromatic/Scale of the key/Jankó): it works the same in any mode.
- **Performance keys**:
  - `Caps Lock` (**Sustain**, held down): the note/chord stays audible and
    its length in the recorded track stays open even after releasing the
    note key, until `Caps Lock` is released too — useful for chords held
    while already pressing the next note. Note: the keyboard's Caps Lock LED
    may still turn on/off at each press (it depends on the system/driver):
    it does not affect operation, it is just a harmless side effect.
  - `L-Alt` (**Strumming**, held down): when you press a note key with a
    chord active (quality row), the notes of the chord no longer all start
    together but in very quick succession (about 20 ms apart), like a guitar
    strum — they all stay audible until the note key is released (only the
    attack is staggered, not the end).
  - `L-Shift` (**Bending**, held down): imitates a real guitar bend on a
    single note — live, you hear the note rise gradually by a whole tone (a
    ramp of ~120 ms, not a sharp jump) and, on release, come back down just
    as gradually before stopping (~80 ms), just like releasing the bend of a
    string. In the recorded track it is captured as a real portamento/slide
    (same syntax as `c*4>d*4`), which is played/exported to MIDI with a
    continuous pitch bend, not two separate notes. It applies in this form
    only to a single note (no chord from the quality row or deep bass
    active, and not together with the Arpeggiator): on a chord, or with the
    Arpeggiator active, it falls back to a simpler fixed offset of 2
    semitones applied immediately to all notes.
  - `L-Ctrl` (**Inversion**, held down): moves the lowest note of the chord
    an octave up (1st inversion), for smoother harmonic passages. It applies
    only to chords (quality row active), not to single notes.
  - `Tab` (**Piano/Forte**): toggles the dynamics of the notes played from
    that moment on — on = Piano (velocity 60), off = Forte (velocity 110,
    initial state). Unlike the other performance keys it does not need to be
    held: one tap toggles the state.
  - **Space bar** (**Arpeggiator**, held down): every note key pressed FROM
    THAT MOMENT ON (one already played before pressing the bar keeps
    sounding normally instead, without being arpeggiated retroactively)
    enters a shared pool whose pitches are played one at a time, in a
    continuous cycle, at a sixteenth of the project tempo — holding down
    several note keys (or a chord with the quality row) you hear/record an
    arpeggio running through all their notes. The pool updates live if note
    keys are added/removed while the bar stays pressed.

  All held performance keys (Sustain/Strumming/Bending/Inversion/
  Arpeggiator) must be held BEFORE or together with the note key: pressing
  them afterwards has no retroactive effect on a note already sounding.

  Technical note: Qt does not portably distinguish the left key from the
  right key of Ctrl/Alt/Shift, so these respond to Ctrl/Alt/Shift in
  general (either side), not only to the left copy described above.
- **Percussion track**: if the target instrument is percussive, the three
  physical rows (number, Q, A — the same ones used for notes, see above)
  play instead the 36 percussion identifiers listed in section 6, in the
  same order in which they appear in the dialog's legend (which shows on
  screen which key produces which sound), without octave.
- **Immediate audio feedback**: while recording or pressing "Play" (trying
  without recording), every key pressed is heard right away, synthesised in
  real time with the target instrument — unlike the rest of the app's
  playback, always offline (see section 12), here minimal latency is
  needed. If the track has a plugin instrument (internal SFZ instrument,
  LV2 or VST3), the keys are played by it, with the sound the track will
  have; the instrument starts loading when the dialog opens and, if it
  cannot be opened, the SoundFont is used (the dialog says so). If the FluidSynth library or a SoundFont are not available, you can still
  record/play, simply without hearing the keys (the dialog says so).
- **Tempo, Time signature, Metronome and Quantisation**: same controls and
  same meaning as in the audio import dialog (section 10bis) — the metronome
  (section 12.5) is especially useful here to play in time before
  quantisation.
- **Key**: shows the project's key (section 2.7bis) as soon as the dialog
  opens, and it can be changed directly from here — it is the same
  `project.key` field as the main toolbar (not a copy): changing it in the
  dialog is reflected in the toolbar too once the dialog is closed, and
  vice versa. Changing it immediately updates the "Scale of the key" layout
  (see below), if active.
- **Layout**: selector of the note key arrangement, disabled if the
  instrument is percussive (percussion always uses keys `1`-`9`). It can be
  changed even while recording or trying, like the Octave. Available
  options:
  - **Chromatic** (default): the behaviour described above, 12 semitones
    per row, 3 octaves in total.
  - **Scale of the key (diatonic/pentatonic/blues)**: requires a key set in
    the main toolbar (section 2.7bis) — if not set (or not valid), it
    automatically falls back to chromatic, without blocking the selection.
    Each row of keys runs only through the notes of the chosen scale instead
    of the 12 chromatic ones, so the keys always play "in key", useful to
    improvise without having to pick the right notes by ear: **diatonic**
    uses the 7 notes of the key's major or natural minor scale;
    **pentatonic** its 5 major or minor notes ("safer" for improvisation,
    almost impossible to play a wrong note); **blues** the 6 notes of the
    blues scale (minor pentatonic + passing diminished fifth), always the
    same from the tonic regardless of major/minor mode. The shorter the
    scale, the more octaves the keyboard covers with the same 12 keys per row
    (diatonic reaches ~3.6 octaves, blues ~3.8, pentatonic ~4.2).
  - **Jankó (isomorphic)**: an arrangement of alternating whole tones
    between the rows (the number row and the A row play the same notes, the
    Q row the in-between notes a semitone above), independent of the key: a
    given chord/interval shape always sounds the same anywhere on the
    keyboard, handy for those who already know it from other instruments/
    software. It covers 2 full octaves (less than chromatic): that is the
    price of isomorphism, not a defect.
- **"Also listen to the other tracks" (respects Solo/Mute)**: optional
  checkbox (unticked by default). If ticked, both while playing live
  (Record/Play) and while listening back to the recorded preview you also
  hear the project's other tracks, with the same Solo/Mute state they have
  in the mixer at that moment — useful to play or judge the new part in the
  context of the arrangement instead of in isolation. The target track
  itself is never duplicated: if the dialog was opened for an existing
  track, its current content stays excluded from background listening, so
  it does not overlap what you are recording/listening back to in its
  place. If unticked: the usual behaviour, only the current instrument is
  heard. The checkbox is disabled during the recording/trying itself (it
  must be decided before pressing Record or Play).
- **Record** starts/stops capturing the performance; **Play** tries it
  without recording anything. Stopping the recording generates the
  quantised text preview, editable and playable back as in the audio
  import, before confirming with Ok. In the track (unlike patterns, where it
  always replaces the body) the result is appended to the content already
  there instead of overwriting it, so as not to lose music written by hand
  or imported earlier.

### MIDI keyboard

In the same dialog you can play with a real **MIDI keyboard** (connected
via USB or through a MIDI interface), together with or instead of the
computer keyboard:

1. connect the keyboard **before** opening the dialog (if you connect it
   afterwards, press **⟳** next to the **MIDI keyboard** menu);
2. in the **MIDI keyboard** menu choose the keyboard: with only one keyboard
   connected it is already selected, and SoundText remembers the last one
   used;
3. press **Record** (or **Play**, to try) and play. As with the computer
   keyboard, notes only count while Record or Play are active.

Compared with the computer keyboard:
- **real dynamics**: the velocity of each key (how hard you press it)
  becomes the note's `@`;
- **chords** played directly, one key per note (the chords-on-the-fly row
  remains for the computer keyboard);
- **sustain pedal**: holds the notes like the sustain key; the recorded
  length lasts until the pedal is released;
- **pitch bend wheel**: heard live; if during a note it goes up or down by
  at least a semitone, the note is recorded as a slide (`a*4>b*4`) towards
  the pitch reached (standard range ±2 semitones);
- **percussion**: on a drum track the notes follow the General MIDI map (36
  kick, 38 snare, 42 closed hihat, 46 open hihat...), like the pads of
  keyboards and electronic drum kits; notes outside the map are ignored;
- the **arpeggiator** (space bar held on the computer keyboard) also
  arpeggiates the MIDI keyboard's notes.

It requires the Python package **python-rtmidi** (in the requirements: the
installation scripts already install it; by hand `pip install
python-rtmidi`). If it is missing, or if the MIDI system does not respond,
the menu is disabled and the reason is shown next to it. If the keyboard
does not appear in the list: check the cable and that it is switched on,
press **⟳**; on Linux `aconnect -l` lists the MIDI devices seen by the
system. A keyboard opened by another program (for example a sequencer) may
appear busy on Windows: close the other program.

## 10quater. Audio tracks (recorded voice, guitar, keyboard)

Besides tracks with notation, a song can contain **audio tracks**: real
audio files (a voice recorded with the microphone, an electric guitar or a
keyboard connected with a jack to the audio interface) that play together
with the other tracks. Unlike audio import (10bis) the file **is not
converted into notes**: it is heard as it is.

An audio track is filled in two ways: by **recording** directly in
SoundText while the rest of the song plays (see "Recording" below), or by
**importing** files recorded with another program.

- **Creating an audio track**: **+ Add track → Audio track...**, or menu
  **Track → Add → Audio track...**. In its header it appears as "Audio", with
  Volume/Pan/Mute/Solo like the others (volume 100% = original level of the
  file, up to 200% ≈ +6 dB).
- **Importing a file**: menu **Track → Import into this track → Audio file as a clip...** (or **⋯ → Import audio file...** on the audio track) adds the
  file as a **clip** at the end of the track. In the Song structure view:
  double-click on an empty spot of the row, or right-click → **Import audio
  file here...** to place it at a precise point. `.wav` files can always be
  read (even 32-bit float); mp3, m4a, flac, ogg and aiff are read by the
  Qt Multimedia decoder included in PySide6 (or by `ffmpeg`, if present),
  and resampled to 48 kHz without losing the highs.
- **Clips in the Song structure view**: each clip is a box with the
  waveform, as wide as the part of the file that plays. It is dragged like
  notation boxes (snapping to the beat); double-click to rename it;
  right-click for Play (preview of the clip alone), Rename, **Clip gain
  (dB)**, Duplicate, Cut/Copy/Paste (an audio clip can only be pasted into
  an audio track) and Delete. Everything can be undone with Ctrl+Z.
- **Trimming start and end**: move the mouse over an edge of the box (the
  cursor becomes ↔) and drag it. The audio stays where it is in time: only
  the start or the end of the file is hidden (or revealed). The trim snaps
  to the sixteenth (1/4 of a beat); holding **Shift** it is free. Dragging
  the left edge to the left also reveals the audio recorded during the
  count-in (useful for a pickup note played early). For exact values:
  right-click → **Precise trim (seconds)...**. The file is never modified.
- **Splitting a clip**: right-click at the point where to split it → **Split
  here**: it becomes two consecutive clips of the same file, which can be
  moved, trimmed or deleted separately (for example to remove a mistake in
  the middle of a take).
- **Convert to notation...** (right-click on a clip): turns the playing part
  of the clip into notes, with the same engine as "Import audio" (10bis),
  in a **new track** with the chosen instrument
  (suggested according to what you recorded: guitar, keyboard, voice) and a
  box starting where the clip starts. It works well with monophonic parts
  (voice, guitar or bass line); the audio clip remains.
- **In the classic editor** an audio track shows, read-only, the list of
  its clips: the notation actions (Generate, Play with the keyboard, Import
  MIDI, Freeze chords, Export MIDI) do not apply to audio tracks and say so
  with a message.
- **Tempo**: audio is not stretched. A clip stays anchored to the beat on
  which it starts but always lasts the same number of seconds: if you change
  the BPM after placing it, the status bar reminds you.

### Recording

Red **●** button on the audio track's header, menu **Track → Record into
the audio track...** (Ctrl+R), or in the Song structure view right-click on
the track's row → **Record from here...** (starts from that point). The
recording dialog opens:

- **Audio interface**: the input to record from (on Windows the low-latency
  drivers, ASIO and WASAPI, appear first). It is remembered.
- **What you are recording**: Voice/microphone, Guitar or bass (jack),
  Keyboard (line output). It chooses the most likely input and explains what
  to set on the interface: +48V phantom power for a condenser microphone,
  INST/Hi-Z input for the guitar (the clean sound is recorded, without
  amplifier), inputs 1+2 on LINE for a stereo keyboard.
- **Input**: a mono input (1, 2, ...) or a stereo pair (1+2). Source type
  and input stay saved in the track.
- **Level**: the meter moves as soon as the dialog is open: adjust the gain
  on the audio interface so that the loudest parts reach around -12/-6 dB
  without lighting the red LED (clipping).
- **Start from**: current position, start of loop A (if set) or start of
  the song.
- **Count-in** (0-4 bars of click before the song starts) and **Metronome
  during the take**. The click continues even past the end of the song, so
  you can also record into a song that is still empty.
- **Listen to the clips already in this track**: untick it to redo a part
  without hearing the previous take.
- **Latency compensation**: the latency declared by the interface is
  already compensated; if the take still turns out late relative to the
  song, increase this value (early: decrease it). It is remembered for each
  interface. **Calibrate...** measures it by itself: connect an output of
  the interface to the chosen input with a cable (or bring the microphone
  close to the speakers), SoundText plays 8 clicks, records them and sets
  the measured delay. It only needs doing once per audio interface (and
  whenever you change the driver's buffer/latency settings).

**● Record** prepares the backing (the song as in playback; without a
SoundFont, only audio tracks and metronome), does the count-in and records
until you press **■ Stop**. The dialog shows the length and peak of the take
(and warns if it clipped): **Keep the take** adds it to the track as a clip
at the starting point; **Record** again replaces it. If the take overlaps
clips already there, SoundText asks whether to delete them.

To hear yourself while playing use the audio interface's **direct
monitoring** (knob or "direct monitor" button): it has no delay. SoundText
only sends the song to the headphones. The take's file also contains the
count-in, hidden by the clip's initial trim (dragging the left edge
reveals it).

### Where the files go

Takes and imported files (of which SoundText makes a copy at 48 kHz, the
same rate as playback: the original is never touched) go into the
**`<ProjectName>_audio/`** folder, next to the `.st` file. If the project
has not been saved yet they go into a temporary folder and are moved into
the project folder at the first save. **Save as** copies the audio files
into the new project's folder. To move a project to another computer, copy
the `.st` file and its `_audio` folder together.

In the `.st` file a clip is written like this (path relative to the file):

```
Audio Vocals "Verse" |8:
  file="Song_audio/vocals.wav" trim=0.35,0 gain=-2

Traccia Vocals [Audio]:
```

`|8` is the starting beat; `trim` are the seconds skipped at the start and
at the end of the file, `gain` the clip gain in dB (both optional). If a
file can no longer be found the clip stays in the project, drawn in red,
and does not play: right-click → **Locate file...** to point to it again.

### Exporting

- **Project → Export → Audio mix (WAV)...** exports the song as it sounds
  (audible tracks, audio included) to a 48 kHz / 24-bit WAV. A SoundFont is
  needed for tracks with notes; a song made only of audio tracks can be
  exported even without one.
- **Track → Export this track → WAV...**, or **right-click on a track's name
  → Export WAV (this one only)...**, exports
  only that track to a WAV, with notation or audio, as it would sound in Solo
  (Solo/Mute of the other tracks do not count). For tracks with notation the
  same menu also has **Export MIDI (this one only)...**.
- **Track → Export this track → Dry WAV (for re-amping)...**, or the same
  command when right-clicking the track's name, exports the track **without** effects chain, without the synth's
  reverb/chorus, with pan in the centre and without master (the volume
  stays): it is the "clean" sound to run through an external amp simulator
  (see 8.6). The file starts from the beginning of the song, so reimporting
  it at the start of an audio track keeps it in time.
- **Export MIDI** contains only notes: audio tracks are not there, and a
  message reminds you.
- Saving and exporting suggest the project's name as the file name (the
  single-track exports the track's name), in the folder where the project
  is saved.

## 11. Saving the project

The project is saved in the native `.st` text format (readable and editable
by hand too), which includes tempo, time signature, patterns, tracks and the
definitions of any custom instruments used (see 7.1), so that the file is
self-contained and portable between different installations. The MIDI
library (`midi/`) instead stays shared at installation level and does not
travel inside the `.st` file.

The window title always shows the name of the file currently open
("SoundText — filename.st"), even after a MIDI import
("SoundText — filename.mid"), so you always know at a glance which project
you are working on.

## 12. Playback

The Play button exports a temporary MIDI. If `fluidsynth` and a SoundFont
are available, synthesis happens **offline** (rendering into a temporary WAV
file, then played with the best audio player found — on Linux `pw-play`,
`paplay`, `aplay`, `ffplay` or `mpv`; on macOS `afplay` (included in the
system) or, if installed, `ffplay`/`mpv`; on Windows `ffplay`/`mpv` if
installed, otherwise the `winsound` module of the Python standard library,
always available) instead of in real time: this avoids the crackles/dropouts
caused by audio driver underruns, typical of realtime MIDI synthesis on
PulseAudio/PipeWire, and gives a cleaner result. If the FluidSynth
library is available (SoundText uses it directly), this offline rendering
uses a single **persistent** fluidsynth instance for the whole session, with
the SoundFont loaded into memory only once instead of at every Play: much
lower start-up latency (the cost of loading the SoundFont, even hundreds of
ms for a GM of tens of MB, is paid only the first time), with the same
anti-crackle strategy (rendering stays offline, it does not touch the
real-time audio output). If offline rendering fails (with or without
the library), or there is no WAV player available, it falls back to the
`fluidsynth` CLI binary and then to real-time fluidsynth playback; if
fluidsynth is not available at all, to `timidity` or `wildmidi`; failing
everything, to the system's default MIDI player (`xdg-open` on Linux,
`open` on macOS, opening directly with the associated program on Windows).

With the FluidSynth library **and** `sounddevice` (in requirements.txt)
installed the rendered song is played directly by the program
instead of by an external player, and the rendering is **cached**: only the
first Play (or the first after a change that alters the sound, such as
notes, mixer or humanisation) has to wait for the synthesis, while
pause/resume and jumps restart instantly. The position shown by the bar,
highlighting, playhead and metronome is the one read from the audio device,
so it stays aligned with what you hear.

### Jumping to a point and repeating a section (A-B loop)

- **Jump**: click on the progress bar in the toolbar, or on the bar ruler in
  the Song structure view. If the song is playing it restarts from there; if
  it is stopped or paused, the next Play will start from that point.
- **A-B loop** (**Playback → Loop** menu): **Loop: start (A) here** (`Ctrl+[`) and
  **Loop: end (B) here** (`Ctrl+]`) set the two ends on the beat being
  played (or on the pause/jump point), rounded to the whole beat. Setting B
  turns the loop on; **Repeat the A-B section** (`Ctrl+L`) turns it on and
  off without losing A and B, **Clear loop** resets them. The section
  appears as a coloured band on the Song structure ruler. You can turn on,
  move or remove the loop even while the song is playing, without
  interruptions.
- The loop requires the direct playback described above (FluidSynth library +
  `sounddevice`): with the fallback players the song is not repeated, and a
  message in the status bar says so.

### 12.1 Progress bar and highlighting of the token being played

During playback, the progress bar (the full-width row under the command
bar) shows the elapsed time and the total length of the song (e.g.
"00:42 / 01:30"). In the track shown in the editor, the token currently
being played (note, rest, chord, block, or the whole reference if it is a
`%pattern`/`&"midi"`) is highlighted with colours inverted relative to the
theme (light background, dark text), to follow playback visually line by
line. The editor scrolls automatically when needed to keep the highlighted
token always visible (no manual scrolling required while listening), but
only when it leaves the visible portion: it does not scroll continuously
note by note, and it does not move the user's editing cursor. Changing track
during playback, the highlighting moves to the newly selected track, always
synchronised with the same elapsed time.

### 12.2 Mixer changes during playback

Mute, Solo, Volume and Pan can be changed even while the song is playing:
the program automatically restarts playback from the position it was at
(not from the beginning), applying the new settings right away. A short
interruption is noticeable at the moment of the restart (the song has to be
re-synthesised with the new settings), but there is no need to stop and
restart playback manually to hear the effect of a mixer change.

**If the sound does not satisfy you despite a good SoundFont**, keep in
mind that:
- **Sounds → SoundFont → Show SoundFont in use** states exactly which engine and which
  `.sf2` file will be used: if it does not show "persistent fluidsynth
  (library) + ...sf2" or "fluidsynth (CLI) + ...sf2", the program is
  silently falling back to a lower-quality option (often because
  `fluidsynth` is not installed, or no `.sf2` was found) — install
  `fluidsynth` and check the SoundFont from there.
- Even with a good SoundFont, **General MIDI sound has an intrinsic limit
  of realism**: it is not meant to compete with professional sample
  libraries, but to give a faithful and recognisable playback of the score.
  A significant jump in quality would require multi-velocity samples per
  instrument (outside the scope of this engine based on standard MIDI/GM).

### 12.3 Choosing the SoundFont (e.g. FluidR3_GM.sf2)

The program looks for a SoundFont, in order of priority:

1. the path set manually from **Sounds → SoundFont → Choose SoundFont (.sf2)...**
   (saved in the settings file: `~/.config/soundtext/settings.json` on
   Linux, `%APPDATA%\SoundText\settings.json` on Windows,
   `~/Library/Application Support/SoundText/settings.json` on macOS);
2. the environment variable `SOUNDTEXT_SOUNDFONT`, if set;
3. some common system paths, including:
   - `~/.local/share/soundfonts/FluidR3_GM.sf2` (Linux)
   - `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora)
   - `/usr/share/soundfonts/FluidR3_GM.sf2` (Arch/CachyOS)
   - `%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` (Windows)
   - `~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (macOS)
   - `/opt/homebrew/share/soundfonts/FluidR3_GM.sf2` (macOS, Homebrew on
     Apple Silicon)

   The full list of paths searched for each system is in the corresponding
   Installation section, further down in this guide.

If you downloaded `FluidR3_GM.sf2` to a different location (or want to use
another one), just select it from **Sounds → SoundFont → Choose SoundFont (.sf2)...**:
it stays set for all subsequent playbacks, in all projects. **Sounds → SoundFont → Show SoundFont in use** tells you which file will be used right now (and
with which engine/player), and lets you check on the spot whether the
problem really is the SoundFont or a silent fallback. **Sounds → SoundFont → Use
automatic SoundFont detection** removes the manual setting and goes back to
automatic search.

### 12.4 Different SoundFonts for individual instruments

Besides the default SoundFont (section 12.3, used for all playback), you can
assign a different `.sf2` file to a single instrument — useful to use a
good-quality dedicated piano together with a generic font for the rest, or
a drum kit different from the rest of the ensemble.

From **Sounds → Manage instruments...**, select an instrument in the
list (built-in or custom: here the choice is not limited to custom ones)
and use the **SoundFont for the selected instrument** panel:
- **Choose SoundFont...** assigns a `.sf2` file to that instrument: it will
  be used instead of the default on every track using it, in any project.
- **Use default** removes the assignment and goes back to the general
  SoundFont.

The instrument list shows an indication (`· SoundFont: name.sf2`) for those
with an active override.

**Limit**: effective only with the persistent fluidsynth engine
(the FluidSynth library, used by default if available — see section 12 above): with
the fallbacks (`fluidsynth` CLI, `timidity`, `wildmidi`, system MIDI player)
the override is ignored and the default SoundFont is used for all playback
anyway. With several instruments overridden at the same time, playback
requires a separate rendering for each SoundFont involved (then
recombined): songs with many differently assigned instruments therefore
take a few moments longer to start.

### 12.5 Metronome

The **Metronome** button (pyramid icon) in the command bar plays a click in
time during ensemble playback, synchronised with any tempo/time signature
changes in the project (the same map used by the progress bar and the
Tempo/Time signature fields, see 2.7); the same control, with a click at a
constant tempo/time signature, is also available in the audio import
dialog and in the "Play with the keyboard" dialog (sections 10bis and
10ter), useful to record/play in time.

The sound and volume of the click are chosen in **Options → Metronome**:
eight sound presets (Click, Beep, Wood, Wood block, Claves, Cowbell, Triangle, Hi-hat) and a volume slider (0-100%),
applied immediately (even to a click already running) and testable on the
spot with the "Test" button, without the need for a separate Ok/Cancel. The
click's audio files are synthesised and cached at the first run (no
additional dependency), so they are generated only once per machine.

### 12.6 Humanize

The **Playback → Humanize** item (checkable) adds a small random variation
to the timing and velocity of the notes being played, for a less mechanical
sound than a perfectly quantised grid. Drums get only the velocity variation
(a timing shift on a percussion pattern tends to sound "sloppy" rather than
"human"); all other instruments get both. **It can be turned on/off even
during playback**: like a Volume/Pan change, playback restarts
automatically from the current position with the new setting applied.

The intensity is set in **Options → Humanize** with a slider (0-100%,
default 50%), applied immediately (it restarts the playback in progress, if
Humanize is on). The variation **does not use a fixed seed**: two
consecutive playbacks with the same settings will never sound identical,
just like two live performances by the same musician. It only concerns
playback/MIDI export (the final rendering in absolute ticks): the track's
text and the "grid" timeline in the editor stay as written, unchanged.

## 13. About SoundText

Menu **Help → About SoundText...** shows the program's name and version
number, the author (Sergio Scolaro) and the licence (GPL-3.0), together
with who decodes mp3/m4a/flac/ogg files (the Qt Multimedia decoder or
`ffmpeg`, section 10bis) with a green tick icon if
available, a grey cross otherwise: useful to check the installation quickly
without having to open a terminal.

### 13.1 Log file

When something does not go as expected (playback falls back to a
lower-quality engine, a SoundFont does not load, an unexpected error),
SoundText records it with the technical details in the `soundtext.log` file
of the configuration folder (`~/.config/soundtext` on Linux,
`%APPDATA%\SoundText` on Windows, `~/Library/Application Support/SoundText`
on macOS). **Help → Open the log file** opens it directly: it is the first
thing to attach if you report a problem. An unexpected error is also shown
in a window, without closing the app.

## 14. Technologies, acknowledgements and licences

### 14.1 The technologies used

SoundText is written in **Python 3** and relies on these libraries and
programs:

| Component | What it does in SoundText | Licence |
|---|---|---|
| Python | the program's language | PSF License |
| Qt 6 with PySide6 | the graphical interface | LGPL-3.0 |
| NumPy | audio computation: effects, amplifier, NAM profiles, analysis | BSD-3-Clause |
| FluidSynth | synthesis of the notes with SoundFonts (SoundText uses it directly) | LGPL-2.1 |
| mido | reading and writing MIDI files | MIT |
| python-rtmidi (RtMidi) | external MIDI keyboards | MIT |
| sounddevice and PortAudio | listening and recording | MIT |
| pedalboard (Spotify) | the effects chain and VST3 plugins | GPL-3.0 |
| JUCE (inside pedalboard) | pedalboard's audio engine and the VST3 host | GPL-3.0 (in the form used by pedalboard) |
| Steinberg VST3 SDK (inside pedalboard) | the VST3 plugin format | GPL-3.0 in the version included in pedalboard (more recent versions of the SDK have moved to the MIT licence) |
| lilv and LV2 | LV2 plugins on Linux (system library, optional) | ISC |
| FFmpeg (inside Qt Multimedia) | reading mp3, m4a, flac, ogg | LGPL-2.1 |
| ffmpeg (external program, optional) | reading audio files if the PySide6 in use lacks the Qt decoder | LGPL-2.1 or GPL, depending on how it was built |
| Neural Amp Modeler | the `.nam` profile format: SoundText redoes the computation with NumPy | MIT (the NAM project) |
| FluidR3_GM SoundFont | the General MIDI sounds included in the builds | MIT |

Some formats and ideas come from open standards or from the literature:
**General MIDI** and the standard MIDI file, **MusicXML** (W3C Music
Notation Community Group) for the score export (10.1), the
**Krumhansl-Schmuckler** algorithm to recognise the key, the Fender and
Marshall tone stack circuits for the amplifier (8.4).

Building and testing the program also requires **PyInstaller** (the
portable versions; its GPL-2.0 licence has an exception so that it does not
extend to the packaged program), **pytest** (the tests) and **reportlab**
(the PDF guide).

### 14.2 Acknowledgements

SoundText exists thanks to the work, almost always voluntary, of those who
created and maintain the open source projects it relies on. We are
especially indebted to:

- the **FluidSynth** community, which for over twenty years has been making
  SoundFonts play on every system, and **Frank Wen**, author of the
  **FluidR3_GM** SoundFont;
- **The Qt Company** and the **Qt for Python (PySide6)** community;
- **Spotify** and the developers of **pedalboard**, and the **JUCE** team
  on which pedalboard is built;
- the **RISM Digital Center** and the developers of **Verovio**, which lays
  out the score (View → Score);
- **Alain de Cheveigné** and **Hideki Kawahara** (the YIN algorithm) and
  **Sebastian Böck** and **Gerhard Widmer** (SuperFlux), whose papers
  are the basis of note recognition from audio;
- the authors of **mido**, of **RtMidi** (Gary P. Scavone) and of
  **python-rtmidi**, of **PortAudio** and of **sounddevice**;
- the **NumPy** community;
- **Steven Atkinson** and the **Neural Amp Modeler** community, with those
  who capture and share amplifier profiles (among others the collection of
  **pelennor2170** and the **Tone3000** site);
- **David Robillard** and the **LV2** and **lilv** community, and the
  authors of the **Ardour** and **Guitarix** plugins;
- **David Fau Casquel** (BestPlugins), who released these IR cabinets under
  a free licence, and the **Guitarix** community, which keeps them;
- **Steinberg**, which opened up the **VST3** format;
- those who develop free and open source plugins, such as **Surge XT**, and
  the **W3C Music Notation Community Group** for MusicXML.

If you use SoundText and find it useful, the best way to give back is to
support these projects: report problems, contribute, or donate to those
that accept donations.

### 14.3 Licences and limits on distribution

Using SoundText on your own computer, for any purpose (even commercial,
even to sell the music you make with it), **has no limits**: the licences
below only concern those who **distribute the program** to others (copy the
installation, publish a build, sell it or include it in another product).
The music created with SoundText belongs to whoever creates it: none of
these licences applies to the songs, or to the `.st`, MIDI, MusicXML or WAV
files produced.

**The main constraint: the GPL-3.0.** **pedalboard** (with JUCE) is
distributed under the **GNU GPL version 3** licence. A program that
includes it, like the SoundText builds, can only be distributed under
the terms of the GPL-3.0:
- all of SoundText must be distributed under the **GPL-3.0 licence** (or a
  compatible one), and whoever receives it has the same rights to use,
  study, modify and redistribute it;
- the **complete source code** of the distributed version, including
  changes, must be made available together with the program (or on
  request, according to the licence's rules);
- no **restrictions** can be added: no closed-source versions, no bans on
  copying or modifying, no systems preventing the installation of a
  modified version;
- you can **sell** a copy or charge for distribution, but whoever buys it
  can then redistribute it freely.

A **closed-source** version of SoundText would only be possible by removing
pedalboard (and therefore the effects chain and VST3 plugins), or by
replacing it, or by buying the commercial licences of the components that
offer them (JUCE, Steinberg...).

**The LGPL libraries: Qt/PySide6 and FluidSynth.** They can also be used in
non-GPL programs, as long as whoever receives the program can **replace them
with their own version**. The portable SoundText builds keep them as
separate files next to the executable, so the condition is met. The text of
the LGPL licence and indications on where to get the sources of these
libraries (for example a link to the version used) must be included.

**The permissive licences (MIT, BSD, ISC, PSF).** NumPy, mido, RtMidi,
PortAudio, sounddevice, lilv, the NAM project and the FluidR3_GM SoundFont
only ask to **keep the copyright notices and the licence text** in the
distribution.

**Trademarks.** VST is a registered trademark of Steinberg Media
Technologies GmbH, Qt of The Qt Company: the names can be mentioned to say
that the program supports those formats or uses those libraries, not to
suggest that SoundText is one of their products. Use of the VST logo has
Steinberg's own rules.

**Downloaded content and third-party plugins.**
- The **recommended NAM profiles** (Sounds → Download → Download recommended NAM
  profiles) come from the pelennor2170 collection, under the GPL-3.0
  licence: SoundText downloads them to the user's computer, it does not
  include them in the builds. Whoever redistributes them must respect their
  licence.
- The **recommended IR cabinets** (Sounds → Download → Download IR cabinets for
  NAM amplifiers) are the BestPlugins Mega Pack 2 by David Fau Casquel,
  under the GPL v2 or later: SoundText also downloads these to the user's
  computer, together with the licence text, and does not include them in
  the builds.
- **VST3 and LV2 plugins** (8.7) are third-party programs, each with its own
  licence, possibly paid: SoundText loads them, but does not include them.
  Distributing them together with SoundText requires their authors'
  permission.
- The **SoundFonts** chosen by the user each have their own licence: before
  including one other than FluidR3_GM in a distribution, it must be
  checked.

**SoundText's licence.** SoundText (Copyright © 2026 Sergio Scolaro) is
distributed under the **GPL-3.0** licence: the text is in the `LICENSE`
file. Authors, licences and full texts of the third-party components are in
`THIRD_PARTY_NOTICES.md` and in the `licenses/` folder. The build scripts
(portable versions for Linux and Windows, AppImage, Windows installer) copy
them next to the program, and the Windows installer shows the licence during
installation.

**In practice, for those distributing a SoundText build:**
1. leave `LICENSE`, `THIRD_PARTY_NOTICES.md` and the `licenses/` folder
   next to the program (the build scripts do it by themselves);
2. make the **source code** of the distributed version available (for
   example the repository, with the exact reference to the version);
3. if a new component is added to the build, add its authors and licence to
   `THIRD_PARTY_NOTICES.md` and its text to `licenses/`;
4. do not include third-party plugins, SoundFonts or profiles without
   having checked that their licence allows it.

These notes summarise the components' licences to help you find your way:
**they are not legal advice**. For a commercial distribution or in a
particular context it is advisable to consult an expert in software
licences. The full texts of the licences are on the websites of the
respective projects.

---

# Installation on Linux

## Debian / Ubuntu and derivatives

```bash
sudo apt update
sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtmultimedia python3-pip fluidsynth fluid-soundfont-gm ffmpeg libportaudio2
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
If `python3-pyside6.qtwidgets` is not available in your version of the
distribution, alternatively:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo apt install fluidsynth fluid-soundfont-gm libportaudio2
python3 main.py
```
`libportaudio2` is needed for direct playback and the microphone; `ffmpeg`
only to read mp3/m4a/flac/ogg if the distribution's PySide6 lacks the Qt
Multimedia decoder (with PySide6 installed via pip, as in the second way,
it is not needed). **Help → About SoundText...** shows who decodes audio
files.

## Fedora and derivatives (RHEL, Nobara, etc.)

```bash
sudo dnf install python3-pyside6 python3-pip fluidsynth fluid-soundfont-gm portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
If `python3-pyside6` is not in the enabled repositories:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo dnf install fluidsynth fluid-soundfont-gm portaudio
python3 main.py
```
`ffmpeg` is only needed if the system PySide6 cannot read mp3 files (see
above) and is not in the official Fedora repositories: enable
[RPM Fusion](https://rpmfusion.org/) and then `sudo dnf install ffmpeg`,
or use the second way (PySide6 via pip).

## Arch Linux / CachyOS / Manjaro and derivatives

```bash
sudo pacman -S pyside6 python-mido fluidsynth ffmpeg portaudio
paru -S soundfont-fluid      # or yay -S soundfont-fluid (AUR)
pip install --user sounddevice numpy pedalboard
cd soundtext
python3 main.py
```
(The official package is called `pyside6`, without the `python-` prefix.
`python-mido` is instead in the official `extra` repositories. `portaudio` is
needed for direct playback and the microphone, `ffmpeg` only if the system
PySide6 cannot read mp3 files.)

## openSUSE

```bash
sudo zypper install python3-PySide6 python3-pip fluidsynth ffmpeg portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```

## Common notes

- Without a GM SoundFont installed, `fluidsynth` produces no audio: check
  that a file such as `/usr/share/soundfonts/FluidR3_GM.sf2` (Arch) or
  `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora) exists.
- Without any system synth, the program still exports standard MIDI that
  can be played with any other player.
- Custom instruments are saved in `~/.config/soundtext/instruments.json`
  and are therefore shared between all the user's projects on that machine.

---

# Installation on Windows

```powershell
# 1) Python 3.10+ from python.org (official installer, tick "Add python.exe to PATH")
cd soundtext
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Audio synthesis (fluidsynth)**: download the Windows binaries of
fluidsynth from the project's official release page
([github.com/FluidSynth/fluidsynth/releases](https://github.com/FluidSynth/fluidsynth/releases),
`-win10-x64.zip` archive) and put the `bin\` folder (it contains
`libfluidsynth-3.dll`) in the system `PATH`, or copy its contents into
the SoundText folder: SoundText uses the library directly (persistent
engine, by default) and `fluidsynth.exe` as a fallback. Alternatively, if you have [Chocolatey](https://chocolatey.org/):
```powershell
choco install fluidsynth
```

**GM SoundFont**: none is included in the operating system (unlike many
Linux distributions). Download a GM SoundFont (e.g. `FluidR3_GM.sf2`,
freely available) and set it from **Sounds → SoundFont → Choose SoundFont (.sf2)...**
in the app's menu, or put it in
`%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` for automatic detection.

**Audio import**: nothing to install. mp3/m4a/flac/ogg files are read by
the Qt Multimedia decoder, already included in PySide6; the pip package
`sounddevice` (in requirements.txt) records from the microphone and
already includes the PortAudio library for Windows. Note recognition is
also written inside SoundText.

**Playback without external players**: unlike Linux, Windows has no
command-line audio player by default; SoundText detects this case and
automatically uses the `winsound` module of the Python standard library (no
additional dependency) to play the offline rendering. **Sounds → SoundFont → Show SoundFont in use** always shows which engine/player is actually active,
useful to check the installation. The **Stop** button correctly stops
playback with any engine, including the last resort (the system's default
MIDI player, used when neither fluidsynth nor a CLI player is installed):
SoundText opens it in a way that it can always be terminated, instead of
leaving it as a process detached from the application.

```powershell
python main.py
```

---

# Installation on macOS

```bash
brew install python@3.12 fluidsynth portaudio   # portaudio optional, see below
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

**Audio synthesis (fluidsynth)**: installed from Homebrew together with the
rest (`libfluidsynth` ends up in `/opt/homebrew/lib` on Apple Silicon or
`/usr/local/lib` on Intel, already in the system library search path: SoundText finds it by itself,
also on Apple Silicon, without additional configuration).

**GM SoundFont**: as on Windows, macOS does not include one by default.
Download a GM SoundFont (e.g. `FluidR3_GM.sf2`) and set it from
**Sounds → SoundFont → Choose SoundFont (.sf2)...**, or put it in
`~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (or, if installed via
Homebrew, in `/opt/homebrew/share/soundfonts/`) for automatic detection.

**Audio import**: mp3/m4a/flac/ogg files are read by the Qt Multimedia
decoder, already included in PySide6 (no `ffmpeg` to install); the pip
package `sounddevice` records from the microphone (it already includes
PortAudio, but `brew install portaudio` never hurts if the pip package
gives problems at build time). Note recognition is also written inside
SoundText, nothing to compile.

**Playback**: macOS includes `afplay` by default (a command-line audio
player included in the operating system, no installation required), used
automatically to play the offline rendering — the same strategy already used
on Linux with `paplay`/`pw-play`. **Sounds → SoundFont → Show SoundFont in use**
always shows which engine/player is actually active.

**Microphone permissions**: at the first microphone recording, macOS asks
for permission to access the microphone for the terminal/IDE from which you
launched `python3 main.py`: it must be granted from **System Settings →
Privacy & Security → Microphone**, otherwise recording fails silently.
