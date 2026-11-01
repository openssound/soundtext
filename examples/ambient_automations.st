// Dawn on the Lake: an ambient piece in D, 48 slow bars, all about automation.
//
// A synth pad, piano, glockenspiel with its echo, flute, strings and a very
// long bass. Almost no rhythm: the piece moves because its parameters change
// over time. What's inside:
//   - ramps `>>` with a curve: `vol=0 >>exp` (a natural fade-in), `>>log`
//     (a fade-out); ramps of different names (vol, cho, rev, cc74) overlap;
//   - the pan crossing the stereo field from left to right in the bridge;
//   - the filter (cc74=) opening slowly;
//   - tempo=N with `>>` (accelerando) and `<<` (rallentando) without drums;
//   - the tuning sliding down (tune=, in cents) in the strings of the bridge:
//     the effect of a slowing tape;
//   - the delay ("echo") made with a second track of the same instrument,
//     shifted by 300 ms (shift=);
//   - hairpins `<` on the chords, slurs `( )` and ties `~` on piano and flute;
//     a small slide (bend=) on the flute;
//   - relative octaves (rel:) and the key (key=D) in the melodies;
//   - instruments defined in the file and the fermata on the last chord.
//
// Form (12 sections of 4 bars; A and B are two chord progressions):
//   1 A  2 A  3 A  4 B  5 A  6 B  7 B  8 B  9 A  10 B  11 A  12 ending
//   A  Dmaj7 | Bm7 | Gmaj7 | Asus4          B  Gmaj7 | Em7 | Bm7 | A

ST: 2.6
Tempo: 60 BPM
Metrica: 4/4
Tonalita: D

Strumento Pad:
  program=89 percussione=no ottava=3 range=36-96 poly=si voicing=spread

Strumento Glock:
  program=9 percussione=no ottava=6 range=72-108 poly=si voicing=spread

Strumento Flute:
  program=73 percussione=no ottava=5 range=72-100 poly=no voicing=monophonic

Strumento Strings:
  program=48 percussione=no ottava=3 range=36-96 poly=si voicing=spread

Pattern %Rest:
  4: 4r |

// ---------------------------------------------------------------- pad

Pattern %PadA:
  4: 56@ Dmaj7'1 | Bm7'1 | Gmaj7'1 | Asus4'1 |

Pattern %PadB:
  4: 56@ Gmaj7'1 | Em7'1 | Bm7'1 | A'1 |

// no velocity: inside the stretches with tempo= the velocity cannot change
Pattern %PadAq:
  4: Dmaj7'1 | Bm7'1 | Gmaj7'1 | Asus4'1 |

Pattern %PadBq:
  4: Gmaj7'1 | Em7'1 | Bm7'1 | A'1 |

Pattern %PadEndq:
  4: Dmaj7'1 | Bm7'1 | Gmaj7'1 | Dmaj7'1$fermata |

// ---------------------------------------------------------------- piano (arpeggios)

Pattern %PnA:
  key=D 8: 66@
  (d*4 a*4 c*5 f*5) c*5 a*4 f*4 a*4 |
  b*3 f*4 a*4 d*5 a*4 f*4 d*4 f*4 |
  g*3 d*4 f*4 b*4 f*4 d*4 b*3 d*4 |
  a*3 e*4 a*4 2d*5~ d*5 e*4 d*4 |

Pattern %PnB:
  key=D 8: 66@
  g*3 d*4 f*4 b*4 f*4 d*4 b*3 d*4 |
  (e*3 b*3 d*4 g*4) d*4 b*3 g*3 b*3 |
  b*3 f*4 a*4 d*5 a*4 f*4 d*4 f*4 |
  a*3 e*4 a*4 c*5 a*4 e*4 c*4 e*4 |

Pattern %PnEnd:
  key=D 8: 62@
  d*4 a*4 c*5 f*5 c*5 a*4 f*4 a*4 |
  b*3 f*4 a*4 d*5 a*4 f*4 d*4 f*4 |
  g*3 d*4 f*4 b*4 f*4 d*4 b*3 d*4 |
  1: [d*4 a*4 c*5 f*5]$fermata |

// ---------------------------------------------------------------- glockenspiel

Pattern %BellA:
  key=D 4: 70@
  f*6 r a*6 r |
  r r d*7 r |
  b*6 r r a*6 |
  2e*6 2r |

Pattern %BellB:
  key=D 4: 70@
  g*6 r b*6 r |
  r r e*6 r |
  d*7 r r b*6 |
  2a*6 2r |

Pattern %BellEnd:
  key=D 4: 66@
  d*6 r a*6 r |
  r r d*7 r |
  4r |
  1: d*6$fermata |

// ---------------------------------------------------------------- flute

Pattern %FlP1:
  rel: key=D 4: 76@
  2a*5 f a |
  2d b a |
  2g f d |
  e f 2e |
  2g b a |
  2g e g |
  2d f d |
  4d |

Pattern %FlP2:
  rel: key=D 4: 80@
  (2a*5 f) a |
  2d b~ b |
  (2g f) d |
  e f 2e |
  2g (b a) |
  2g e g |
  2d f d |
  bend=0 >> 4d bend=1 bend=0 |

Pattern %FlP3:
  rel: key=D 4: 84@
  2a*6 f a |
  2d b a |
  2g f d |
  e f 2e |
  2g b a |
  2g e g |
  2d f d |
  4d |

// ---------------------------------------------------------------- strings and bass

Pattern %ArA:
  4: 64@ Dmaj7'1< | Bm7'1< | Gmaj7'1< | Asus4'1 |

Pattern %ArB:
  4: 64@ Gmaj7'1< | Em7'1< | Bm7'1< | A'1 |

Pattern %ArEnd:
  4: 60@ Dmaj7'1 | Bm7'1 | Gmaj7'1 | Dmaj7'1$fermata |

Pattern %BsA:
  key=D 4: 80@ d*2'1 | b*1'1 | g*1'1 | a*1'1 |

Pattern %BsB:
  key=D 4: 80@ g*1'1 | e*2'1 | b*1'1 | a*1'1 |

Pattern %BsEnd:
  key=D 4: 76@ d*2'1 | b*1'1 | g*1'1 | d*2'1$fermata |

// ================================================================ tracks

Pad:
  // the chorus, reverb and filter ramps last the first six sections
  cho=20 >>
  rev=40 >>
  cc74=25 >>
  // section 1: fade-in, with the "exp" curve
  vol=0 >>exp
  %PadA
  vol=85
  // sections 2-6
  %PadA %PadA %PadB %PadA %PadB
  cho=90
  rev=90
  cc74=110
  // sections 7-8, the bridge: the pan moves from left to right and the tempo speeds up
  pan=-0.9 >>
  tempo=60 >>
  %PadBq %PadBq
  pan=0.9
  tempo=84
  pan=0
  // sections 9-10
  %PadA %PadB
  // sections 11-12: rallentando and fade-out ("log" curve)
  tempo=84 <<
  vol=85 >>log
  %PadAq %PadEndq
  vol=10
  tempo=50

Piano:

Box Piano "Intro" |16:
  %PnA %PnA %PnB %PnA %PnB

Box Piano "Bridge" |96:
  // bridge
  %PnB %PnB
  %PnA %PnB %PnA
  %PnEnd

Traccia Glockenspiel [Glock]:

Box Glockenspiel "Intro" |0:
  pan=-0.6
  4%Rest
  %BellA %BellA %BellB

Box Glockenspiel "Second part" |128:
  // the glockenspiel rests in the middle of the piece
  %BellA %BellB %BellA
  %BellEnd

Traccia Echo [Glock]:

Box Echo "Echo" |0:
  // the same track, 300 ms later, softer and on the other side
  pan=0.7
  shift=300
  vol=45
  4%Rest
  %BellA %BellA %BellB
  16%Rest
  %BellA %BellB %BellA
  %BellEnd

Flute:

Box Flute "First part" |32:
  // the first two sections and the last two have no flute
  $"dolce" %FlP1
  %FlP2
  8%Rest

Box Flute "Again" |128:
  // again, an octave higher, when the tempo is faster
  %FlP3
  8%Rest

Strings:

Box Strings "Section 5" |64:
  // section 5: volume crescendo
  vol=40 >>
  %ArA
  vol=90
  %ArB

Box Strings "Bridge" |96:
  // bridge: the tuning drops by 40 cents, like a slowing tape
  tune=0 >>
  %ArB %ArB
  tune=-40
  tune=0
  8%Rest
  %ArA
  %ArEnd

Bass:

Box Bass "Intro" |32:
  %BsA %BsB %BsA %BsB
  %BsB %BsB
  %BsA %BsB %BsA
  %BsEnd

// ================================================================ mixer

Mixer Pad:
  volume: 80 pan: 0 mute: no solo: no reverb: 40 chorus: 20

Mixer Piano:
  volume: 76 pan: -0.2 mute: no solo: no reverb: 35

Mixer Glockenspiel:
  volume: 64 pan: -0.6 mute: no solo: no reverb: 45

Mixer Echo:
  volume: 52 pan: 0.7 mute: no solo: no reverb: 55

Mixer Flute:
  volume: 86 pan: 0.2 mute: no solo: no reverb: 40

Mixer Strings:
  volume: 70 pan: 0 mute: no solo: no reverb: 50

Mixer Bass:
  volume: 88 pan: 0 mute: no solo: no
