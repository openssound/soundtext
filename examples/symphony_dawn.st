// Dawn Symphony: an original symphonic movement for orchestra.
//
// Strings, flute, oboe, horns, trumpets, timpani and harp, in 40 bars (4/4).
// The form recalls a symphonic first movement in miniature:
//   slow intro      4 bars   Adagio, D minor (tempo 56)
//   theme A         8        Allegro, D minor: the strings
//   theme B         8        F major: oboe and flute, with the harp
//   development     8        the motif of theme A in sequence, with
//                            horns, trumpets and a crescendo
//   recapitulation  8        theme A, now with the whole orchestra
//   coda            4        the rallentando and the cadence in D major,
//                            with the fermata
// What's inside:
//   - instruments defined in the file ("Strumento" blocks): each has its
//     program, its range and whether it plays notes or chords;
//   - the themes are patterns, reused by several instruments: the same
//     %ThemeA is played by violins (intro and recapitulation), flute, oboe and
//     trumpets, each in its own octave (relative octaves, rel:);
//   - tempo changes with tempo=: Adagio, Allegro, a broader theme B, the
//     development pushing ahead and the final rallentando (tempo=126 << ... 70);
//   - dynamics with velocity (50@ = piano, 110@ = fortissimo) and hairpins <
//     on chords and long notes;
//   - the fermata ($fermata) on the last chord.

ST: 2.6
Tempo: 56 BPM
Metrica: 4/4
Tonalita: Dm

Strumento Violins1:
  program=40 percussione=no ottava=5 range=55-100 poly=no voicing=monophonic

Strumento Violins2:
  program=40 percussione=no ottava=4 range=55-100 poly=si voicing=spread

Strumento Violas:
  program=41 percussione=no ottava=3 range=48-91 poly=si voicing=spread

Strumento Cellos:
  program=42 percussione=no ottava=3 range=36-76 poly=no voicing=monophonic

Strumento DoubleBasses:
  program=43 percussione=no ottava=2 range=28-55 poly=no voicing=monophonic

Strumento Flute:
  program=73 percussione=no ottava=5 range=60-96 poly=no voicing=monophonic

Strumento Oboe:
  program=68 percussione=no ottava=5 range=58-91 poly=no voicing=monophonic

Strumento Horns:
  program=60 percussione=no ottava=3 range=41-77 poly=si voicing=spread

Strumento Trumpets:
  program=56 percussione=no ottava=4 range=55-82 poly=no voicing=monophonic

Strumento Timpani:
  program=47 percussione=no ottava=3 range=36-60 poly=no voicing=monophonic

Strumento Harp:
  program=46 percussione=no ottava=4 range=24-103 poly=si voicing=spread

// ---------------------------------------------------------------- themes

Pattern %ThemeA:
  rel: key=Dm 8:
  d f a 3d 2c |
  b a g f 2e 2d |
  e g a 3d 2c |
  b a g a 2b 2a |
  a 3d f 3e |
  2d c b a 2g f |
  g a b d 2c b a |
  a 7d |

Pattern %ThemeB:
  rel: key=Dm 8:
  4a*4 2g 2f |
  2e 2g 2c 2a |
  4b 2a 2g |
  2b 2a 2g 2e |
  2f 2a 2c 2f |
  2d 2f 2b 2a |
  2g 2b 2g 2e |
  8f |

Pattern %Dev1:
  key=Dm 8:
  g*5 b*5 d*6 3g*6 2f*6 |
  c*5 e*5 g*5 3c*6 2b*5 |
  f*5 a*5 c*6 3f*6 2e*6 |
  b*5 d*6 f*6 3b*6 2a*6 |
  g*5 a*5 b*5 d*6 2g*6 2f*6 |
  e*6 g*6 a*6 c#*6 2e*6 2a*5 |
  d*6 f*6 a*6 2f*6 e*6 2d*6 |
  2e*6 2g*6 4c#*6 |

Pattern %CodaVl1:
  key=Dm 8:
  2g*6 2f*6 2d*6 2b*5 |
  2e*6 2g*6 4a*6 |
  3d*6 f#*6 4a*6 |
  8d*6$fermata |

Pattern %IntroVl1:
  key=Dm 4:
  4a*5 | 4b*5 | 4d*6 | 4e*6 |

// ---------------------------------------------------------------- harmony

Pattern %AccIntro:
  Dm'1 | Bb'1 | Gm'1 | A7'1 |

Pattern %AccA:
  Dm'1 | Gm'2 A7'2 | C'2 F'2 | Gm'2 A7'2 | Dm'1 | Bb'2 Gm'2 | Gm'2 A7'2 | Dm'1 |

Pattern %AccB:
  F'1 | C'2 F'2 | Bb'1 | Gm'2 C7'2 | F'1 | Dm'2 Bb'2 | Gm'2 C7'2 | F'1 |

Pattern %AccDev:
  Gm'1< | C7'1< | F'1< | Bb'1< | Gm'1< | A7'1< | Dm'1< | A7'1 |

Pattern %AccCoda:
  Gm'1 | A7'1 | D'1 | D'1$fermata |

// ---------------------------------------------------------------- basses and cellos

Pattern %BassA:
  key=Dm 4:
  2d*2 2a*1 | 2g*1 2a*1 | 2c*2 2f*1 | 2g*1 2a*1 | 2d*2 2a*1 | 2b*1 2g*1 | 2g*1 2a*1 | 4d*2 |

Pattern %CelloA:
  key=Dm 4:
  2d*3 2a*2 | 2g*2 2a*2 | 2c*3 2f*2 | 2g*2 2a*2 | 2d*3 2a*2 | 2b*2 2g*2 | 2g*2 2a*2 | 4d*3 |

Pattern %BassB:
  key=Dm 4:
  4f*1 | 2c*2 2f*1 | 4b*1 | 2g*1 2c*2 | 4f*1 | 2d*2 2b*1 | 2g*1 2c*2 | 4f*1 |

Pattern %CelloB:
  key=Dm 4:
  4f*2 | 2c*3 2f*2 | 4b*2 | 2g*2 2c*3 | 4f*2 | 2d*3 2b*2 | 2g*2 2c*3 | 4f*2 |

Pattern %BassDev:
  key=Dm 4:
  4g*1< | 4c*2< | 4f*1< | 4b*1< | 4g*1< | 4a*1< | 4d*2< | 4a*1 |

Pattern %CelloDev:
  key=Dm 4:
  4g*2< | 4c*3< | 4f*2< | 4b*2< | 4g*2< | 4a*2< | 4d*3< | 4a*2 |

Pattern %BassCoda:
  key=Dm 4:
  4g*1 | 4a*1 | 4d*2 | 4d*2$fermata |

Pattern %CelloCoda:
  key=Dm 4:
  4g*2 | 4a*2 | 4d*3 | 4d*3$fermata |

// ---------------------------------------------------------------- trumpets

Pattern %FanfareTrumpets:
  key=Dm 8:
  2g*4 2b*4 4d*5 |
  2a*4 2c#*5 4e*5 |
  2d*5 2f*5 4a*5 |
  2a*4 2e*5 4a*5 |

// ---------------------------------------------------------------- harp

Pattern %HarpB:
  key=Dm 8:
  f*3 a*3 c*4 f*4 a*4 f*4 c*4 a*3 |
  c*3 e*3 g*3 c*4 f*3 a*3 c*4 f*4 |
  b*2 d*3 f*3 b*3 d*4 b*3 f*3 d*3 |
  g*2 b*2 d*3 g*3 c*3 e*3 g*3 b*3 |
  f*3 a*3 c*4 f*4 a*4 f*4 c*4 a*3 |
  d*3 f*3 a*3 d*4 b*2 d*3 f*3 b*3 |
  g*2 b*2 d*3 g*3 c*3 e*3 g*3 b*3 |
  2f*3 2a*3 4c*4 |

Pattern %HarpCoda:
  key=Dm 8:
  g*2 b*2 d*3 g*3 b*3 g*3 d*3 b*2 |
  a*2 c#*3 e*3 g*3 a*3 g*3 e*3 c#*3 |
  d*3 f#*3 a*3 d*4 f#*4 d*4 a*3 f#*3 |
  D'1$fermata |

// ---------------------------------------------------------------- timpani

Pattern %TimpIntro:
  key=Dm 4:
  d*3 d*3 d*3 d*3 | d*3 d*3 d*3 d*3 | g*2 g*2 g*2 g*2 | a*2 a*2 a*2 a*2 |

Pattern %TimpA:
  key=Dm 4:
  2d*3 2a*2 | 2g*2 2a*2 | 2c*3 2f*2 | 2g*2 2a*2 | 2d*3 2a*2 | 2b*2 2g*2 | 2g*2 2a*2 | 4d*3 |

Pattern %TimpB:
  key=Dm 4:
  4f*2 | 2c*3 2f*2 | 4b*2 | 2g*2 2c*3 | 4f*2 | 2d*3 2b*2 | 2g*2 2c*3 | 4f*2 |

Pattern %TimpDev:
  key=Dm 4:
  g*2 g*2 g*2 g*2 | c*3 c*3 c*3 c*3 | f*2 f*2 f*2 f*2 | b*2 b*2 b*2 b*2 |
  g*2 g*2 g*2 g*2 | a*2 a*2 a*2 a*2 | d*3 d*3 d*3 d*3 | a*2 a*2 a*2 a*2 |

// ================================================================ tracks

Violins1:

Box Violins1 "Intro" |0:
  50@ %IntroVl1

Box Violins1 "Theme A" |16:
  $"con slancio"
  85@ %ThemeA

Box Violins1 "Development" |80:
  80@ %Dev1

Box Violins1 "Recapitulation" |112:
  105@ %ThemeA

Box Violins1 "Coda" |144:
  100@ %CodaVl1

Violins2:

Box Violins2 "Theme B" |48:
  $"dolce"
  55@ %AccB

Box Violins2 "Development" |80:
  70@ %AccDev

Box Violins2 "Recapitulation" |112:
  85@ %AccA
  90@ %AccCoda

Violas:

Box Violas "Intro" |0:
  45@ %AccIntro
  65@ %AccA
  55@ %AccB
  65@ %AccDev
  80@ %AccA

Box Violas "Coda" |144:
  85@ %AccCoda

Cellos:

Box Cellos "Intro" |0:
  4: 45@ 4d*3 | 4b*2 | 4g*2 | 4a*2 |
  80@ %CelloA
  60@ %CelloB
  75@ %CelloDev
  95@ %CelloA
  90@ %CelloCoda

DoubleBasses:

Box DoubleBasses "Intro" |0:
  4: 40@ 4d*2 | 4b*1 | 4g*1 | 4a*1 |
  80@ %BassA
  60@ %BassB
  75@ %BassDev
  95@ %BassA
  90@ %BassCoda

Flute:

Box Flute "Theme B" |48:
  $"cantabile"
  65@ %ThemeB

Box Flute "Recapitulation" |112:
  95@ %ThemeA

Oboe:

Box Oboe "Theme B" |48:
  $"espressivo"
  80@ %ThemeB

Box Oboe "Recapitulation" |112:
  95@ %ThemeA

Horns:

Box Horns "Intro" |0:
  40@ %AccIntro

Box Horns "Development" |80:
  55@ %AccDev
  95@ %AccA
  95@ %AccCoda

Trumpets:

Box Trumpets "Development" |96:
  // the trumpets come in for the last four bars of the development
  90@ %FanfareTrumpets

Box Trumpets "Recapitulation" |112:
  // recapitulation: theme A an octave below the violins
  105@ %ThemeA

Timpani:

Box Timpani "Intro" |0:
  // Adagio: the hushed roll
  35@ %TimpIntro
  // Allegro
  tempo=120
  85@ %TimpA
  // theme B, broader
  tempo=104
  50@ %TimpB
  // development: the tempo pushes and the crescendo grows
  tempo=116
  60@ %TimpDev
  // recapitulation
  tempo=126
  95@ %TimpA

Box Timpani "Coda" |144:
  // coda: the rallentando
  100@ tempo=126 <<
  4: 4g*2 | 4a*2 | 4d*3 |
  4: 4d*3$fermata |
  tempo=70

Harp:

Box Harp "Theme B" |48:
  60@ %HarpB

Box Harp "Coda" |144:
  75@ %HarpCoda

// ================================================================ mixer

Mixer Violins1:
  volume: 92 pan: -0.5 mute: no solo: no reverb: 35

Mixer Violins2:
  volume: 82 pan: -0.25 mute: no solo: no reverb: 35

Mixer Violas:
  volume: 80 pan: 0.15 mute: no solo: no reverb: 35

Mixer Cellos:
  volume: 84 pan: 0.4 mute: no solo: no reverb: 30

Mixer DoubleBasses:
  volume: 80 pan: 0.65 mute: no solo: no reverb: 25

Mixer Flute:
  volume: 80 pan: -0.15 mute: no solo: no reverb: 40

Mixer Oboe:
  volume: 82 pan: 0.1 mute: no solo: no reverb: 40

Mixer Horns:
  volume: 78 pan: 0.3 mute: no solo: no reverb: 40

Mixer Trumpets:
  volume: 80 pan: -0.3 mute: no solo: no reverb: 40

Mixer Timpani:
  volume: 86 pan: 0 mute: no solo: no reverb: 45

Mixer Harp:
  volume: 76 pan: -0.6 mute: no solo: no reverb: 40
