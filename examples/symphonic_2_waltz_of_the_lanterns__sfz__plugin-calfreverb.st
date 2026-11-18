// Waltz of the Lanterns - symphonic waltz in G major
//
// A concert waltz in the Viennese style: harp and flute open, theme A on the
// violins over the "oom-pah-pah" of the double basses and the pizzicato
// strings, theme B in E minor on the solo cello with an oboe countermelody,
// theme A with the full orchestra, the trio in C major on the horns, the last
// theme A with the glockenspiel and the coda.
//
// Sounds:
// - SFZ instruments: pizzicato strings (Discord GM Bank), Karoryfer Bigcat
//   cello, D. Smolken pizzicato double basses, concert harp (Sounds ->
//   Download and install); violins, woodwinds, brass, timpani and
//   glockenspiel are the General MIDI SoundFont's;
// - the hall: the built-in reverb on the sections and Calf Reverb (LV2 plugin)
//   on the master, then EQ, a light compressor and a limiter.

ST: 2.6
Tempo: 160 BPM
Metrica: 3/4
Tonalita: G

Strumento Violins:
  program=48 percussione=no ottava=5 range=55-100 poly=si voicing=spread

Strumento Pizzicato:
  program=45 percussione=no ottava=4 range=28-88 poly=si voicing=spread

Strumento Cello:
  program=42 percussione=no ottava=3 range=36-77 poly=no voicing=monophonic

Strumento DoubleBasses:
  program=43 percussione=no ottava=2 range=28-60 poly=no voicing=root_only

Strumento Flute:
  program=73 percussione=no ottava=5 range=60-96 poly=no voicing=monophonic

Strumento Oboe:
  program=68 percussione=no ottava=5 range=58-91 poly=no voicing=monophonic

Strumento Horns:
  program=60 percussione=no ottava=4 range=34-77 poly=si voicing=spread

Strumento Trumpets:
  program=56 percussione=no ottava=4 range=54-86 poly=si voicing=spread

Strumento Timpani:
  program=47 percussione=no ottava=2 range=28-57 poly=no voicing=root_only

Strumento Harp:
  program=46 percussione=no ottava=3 range=28-102 poly=si voicing=spread

Strumento Glockenspiel:
  program=9 percussione=no ottava=6 range=72-108 poly=no voicing=monophonic

// ================================================================ theme A (16 bars)

Pattern %ThemeA:
  4:
  d*5 g*5 b*5 | 2a*5 g*5 | f#*5 a*5 c*6 | 3b*5 |
  a*5 f#*5 d*5 | 2e*5 f#*5 | 3g*5 | 2d*5 r |
  d*5 g*5 b*5 | 2d*6 b*5 | e*6 d*6 c*6 | 2eb*6 c*6 |
  b*5 d*6 g*5 | 2a*5 f#*5 | 3g*5 | 2g*5 r |

Pattern %BassesA:
  4: g*1 2r | g*1 2r | d*2 2r | a*1 2r | d*2 2r | a*1 2r | g*1 2r | d*2 2r |
  g*1 2r | g*1 2r | c*2 2r | c*2 2r | d*2 2r | d*2 2r | g*1 2r | g*1 2r |

Pattern %PizzA:
  4: r G! G! | r G! G! | r D7! D7! | r D7! D7! | r D7! D7! | r D7! D7! | r G! G! | r G! G! |
  r G! G! | r G7! G7! | r C! C! | r Cm! Cm! | r G! G! | r D7! D7! | r G! G! | r G! G! |

Pattern %HarmonyA:
  4: 3G_ | 3G_ | 3D7_ | 3D7_ | 3D7_ | 3D7_ | 3G_ | 3G_ | 3G_ | 3G7_ | 3C_ | 3Cm_ | 3G_ | 3D7_ | 3G_ | 3G_ |

// ================================================================ theme B in E minor (16 bars)

Pattern %ThemeB:
  4:
  2e*4 b*3 | g*3 b*3 e*4 | 2d#*4 f#*4 | 3a*4 |
  a*4 f#*4 d#*4 | 2b*3 c*4 | 3b*3 | 2e*3 r |
  c*4 e*4 a*4 | 2c*4 a*3 | b*3 d*4 g*4 | 2e*4 g*4 |
  e*4 c*4 a*3 | 2d#*4 f#*4 | 3e*4 | 2d*4 c*4 |

Pattern %CounterB:
  4: 3g*5 | 3g*5 | 3f#*5 | 3f#*5 | 3a*5 | 3a*5 | 3g*5 | 3g*5 |
  3e*5 | 3f#*5 | 3g*5 | 3g*5 | 3e*5 | 3f#*5 | 3e*5 | 3f#*5 |

Pattern %HarmonyB:
  4: 3Em_ | 3Em_ | 3B7_ | 3B7_ | 3B7_ | 3B7_ | 3Em_ | 3Em_ | 3Am_ | 3D7_ | 3G_ | 3C_ | 3Am_ | 3B7_ | 3Em_ | 3D7_ |

Pattern %BassesB:
  4: e*2 2r | e*2 2r | b*1 2r | b*1 2r | b*1 2r | b*1 2r | e*2 2r | e*2 2r |
  a*1 2r | d*2 2r | g*1 2r | c*2 2r | a*1 2r | b*1 2r | e*2 2r | d*2 2r |

Pattern %PizzB:
  4: r Em! Em! | r Em! Em! | r B7! B7! | r B7! B7! | r B7! B7! | r B7! B7! | r Em! Em! | r Em! Em! |
  r Am! Am! | r D7! D7! | r G! G! | r C! C! | r Am! Am! | r B7! B7! | r Em! Em! | r D7! D7! |

// ================================================================ trio in C major (16 bars)

Pattern %Trio:
  4:
  2e*4 g*4 | 3c*5 | b*4 a*4 g*4 | 3f*4 |
  d*4 f*4 b*4 | 2d*5 b*4 | 3c*5 | 2g*4 r |
  a*4 c*5 f*5 | 2e*5 c*5 | 3g*4 | 2c#*5 a*4 |
  d*5 c*5 a*4 | 2b*4 g*4 | 3c*5 | 2d*5 r |

Pattern %HarmonyTrio:
  4: 3C_ | 3C_ | 3G7_ | 3G7_ | 3G7_ | 3G7_ | 3C_ | 3C_ | 3F_ | 3F_ | 3C_ | 3A7_ | 3Dm_ | 3G7_ | 3C_ | 3D7_ |

Pattern %BassesTrio:
  4: c*2 2r | c*2 2r | g*1 2r | g*1 2r | g*1 2r | g*1 2r | c*2 2r | c*2 2r |
  f*1 2r | f*1 2r | c*2 2r | a*1 2r | d*2 2r | g*1 2r | c*2 2r | d*2 2r |

// one-bar arpeggios (six eighths) for the last theme A
Pattern %ArG:
  8: g*3 b*3 d*4 g*4 d*4 b*3 |

Pattern %ArD7:
  8: d*3 f#*3 a*3 c*4 a*3 f#*3 |

Pattern %ArG7:
  8: g*2 b*2 d*3 f*3 d*3 b*2 |

Pattern %ArC:
  8: c*3 e*3 g*3 c*4 g*3 e*3 |

Pattern %ArCm:
  8: c*3 eb*3 g*3 c*4 g*3 eb*3 |

Pattern %HarpA:
  %ArG %ArG %ArD7 %ArD7 %ArD7 %ArD7 %ArG %ArG %ArG %ArG7 %ArC %ArCm %ArG %ArD7 %ArG %ArG

Pattern %HarpTrio:
  4: c*3 g*3 e*4 | c*3 g*3 e*4 | g*2 d*3 f*3 | g*2 d*3 b*3 | g*2 d*3 f*3 | g*2 d*3 b*3 | c*3 g*3 e*4 | c*3 g*3 e*4 |
  f*2 c*3 a*3 | f*2 c*3 a*3 | c*3 g*3 e*4 | a*2 e*3 c#*4 | d*3 a*3 f*4 | g*2 d*3 b*3 | c*3 g*3 e*4 | d*3 a*3 f#*4 |

// ================================================================ tracks

Traccia Violins [Violins]:

Box Violins "Theme A" |24:
  4: 90@ %ThemeA

Box Violins "Theme B" |72:
  4: 50@ %HarmonyB

Box Violins "Theme A, full orchestra" |120:
  4: 105@ %ThemeA

Box Violins "Trio" |168:
  4: 60@ %HarmonyTrio

Box Violins "Last theme A" |216:
  4: 110@ %ThemeA

Box Violins "Coda" |264:
  // accelerando and final fermata
  4: 112@ tempo=160 >> d*5 g*5 b*5 | d*6 b*5 g*5 | e*6 c*6 g*5 | d*6 a*5 f#*5 |
  g*5 b*5 d*6 | a*5 c*6 f#*6 | tempo=176 3g*6 | 3g*5$fermata |

Traccia Pizzicato [Pizzicato]:

Box Pizzicato "Theme A" |24:
  4: 72@ %PizzA

Box Pizzicato "Theme B" |72:
  4: 65@ %PizzB

Box Pizzicato "Theme A, full orchestra" |120:
  4: 80@ %PizzA

Box Pizzicato "Last theme A" |216:
  4: 85@ %PizzA

Traccia Cello [Cello]:

Box Cello "Theme B" |72:
  // the song of the solo cello
  4: 85@ %ThemeB

Box Cello "Trio" |168:
  4: 70@ 3c*3 | 3c*3 | 3g*2 | 3g*2 | 3g*2 | 3g*2 | 3c*3 | 3c*3 | 3f*2 | 3f*2 | 3c*3 | 3a*2 | 3d*3 | 3g*2 | 3c*3 | 3d*3 |

Box Cello "Coda" |264:
  4: 100@ 3g*2 | 3g*2 | 3c*3 | 3d*3 | 3g*2 | 3d*3 | 3g*2 | 3g*2$fermata |

Traccia DoubleBasses [DoubleBasses]:

Box DoubleBasses "Intro" |0:
  4: 70@ g*1 2r | g*1 2r | d*2 2r | d*2 2r | g*1 2r | g*1 2r | d*2 2r | d*2 2r |

Box DoubleBasses "Theme A" |24:
  4: 95@ %BassesA

Box DoubleBasses "Theme B" |72:
  4: 90@ %BassesB

Box DoubleBasses "Theme A, full orchestra" |120:
  4: 100@ %BassesA

Box DoubleBasses "Trio" |168:
  4: 85@ %BassesTrio

Box DoubleBasses "Last theme A" |216:
  4: 105@ %BassesA

Box DoubleBasses "Coda" |264:
  4: 108@ g*1 2r | g*1 2r | c*2 2r | d*2 2r | g*1 2r | d*2 2r | g*1 2r | 3g*1$fermata |

Traccia Flute [Flute]:

Box Flute "Intro" |0:
  4: 72@ d*5 g*5 b*5 | 2a*5 g*5 | f#*5 a*5 c*6 | 3b*5 | a*5 f#*5 d*5 | 2e*5 f#*5 | 3g*5 | 2d*5 r |

Box Flute "Theme A, full orchestra" |120:
  4: 95@ %ThemeA

Box Flute "Last theme A" |216:
  4: 100@ %ThemeA

Traccia Oboe [Oboe]:

Box Oboe "Theme B" |72:
  4: 72@ %CounterB

Box Oboe "Trio" |168:
  4: 65@ %Trio+12

Traccia Horns [Horns]:

Box Horns "Theme A, full orchestra" |120:
  4: 82@ %HarmonyA

Box Horns "Trio" |168:
  // the theme of the trio
  4: 92@ %Trio

Box Horns "Last theme A" |216:
  4: 90@ %HarmonyA

Box Horns "Coda" |264:
  4: 100@ 3G_ | 3G_ | 3C_ | 3D7_ | 3G_ | 3D7_ | 3G_ | 3G$fermata |

Traccia Trumpets [Trumpets]:

Box Trumpets "Last theme A" |216:
  4: 95@ G! 2r | 3r | D7! 2r | 3r | D7! 2r | 3r | G! 2r | 3r | G! 2r | G7! 2r | C! 2r | Cm! 2r | G! 2r | D7! 2r | G! 2r | 3r |

Box Trumpets "Coda" |264:
  4: 105@ G! 2r | 3r | C! 2r | D7! 2r | G! 2r | D7! 2r | G! G! G! | 3G$fermata |

Traccia Timpani [Timpani]:

Box Timpani "Theme A, full orchestra" |120:
  4: 95@ g*1 2r | 3r | d*2 2r | 3r | d*2 2r | 3r | g*1 2r | d*2 2r |
  g*1 2r | 3r | 3r | 3r | g*1 2r | d*2 2r | g*1 2r | 3r |

Box Timpani "Last theme A" |216:
  4: 100@ g*1 2r | 3r | d*2 2r | 3r | d*2 2r | 3r | g*1 2r | d*2 2r |
  g*1 2r | 3r | 3r | 3r | g*1 2r | d*2 2r | g*1 2r | 3r |

Box Timpani "Coda" |264:
  4: 108@ g*1 2r | 3r | 3r | d*2 2r | g*1 2r | d*2 2r | g*1 g*1 g*1 | 16: 70@ >> 12(g*1) 118@ |

Traccia Harp [Harp]:

Box Harp "Intro" |0:
  4: 75@ g*2 d*3 b*3 | g*2 d*3 b*3 | d*2 a*2 c*4 | d*2 a*2 f#*3 | d*2 a*2 c*4 | d*2 a*2 f#*3 | g*2 d*3 b*3 | g*2 d*3 b*3 |

Box Harp "Trio" |168:
  4: 78@ %HarpTrio

Box Harp "Last theme A" |216:
  8: 82@ %HarpA

Box Harp "Coda" |264:
  8: 90@ 2(g*2 d*3 g*3 b*3 d*4 g*4) | 2(c*3 g*3 c*4 e*4 g*4 c*5) |
  d*3 a*3 d*4 f#*4 a*4 d*5 | g*2 d*3 g*3 b*3 d*4 g*4 | d*3 a*3 d*4 f#*4 a*4 d*5 |
  g*2 d*3 g*3 b*3 d*4 g*4 | 4: 3G$fermata |

Traccia Glockenspiel [Glockenspiel]:

Box Glockenspiel "Last theme A" |216:
  4: 100@ %ThemeA+12

// ================================================================ sounds

Plugin Pizzicato:
  ref="sfz:~/Strumenti/sfz/gm-bank/Discord GM/Melodic/046-Pizzicato Strings.sfz"

Plugin Cello:
  ref="sfz:~/Strumenti/sfz/cello/Karoryfer_Bigcat_cello/Programs/01- Bowed (velocity layer).sfz"

Plugin DoubleBasses:
  ref="sfz:~/Strumenti/sfz/contrabbasso/dsmolken_double_bass/d_smolken_rubner_bass_pizz.sfz"

Plugin Harp:
  ref="sfz:~/Strumenti/sfz/arpa/ConcertHarp-SFZ+FLAC-20200702/ConcertHarp-20200702.sfz"

Effetti Violins:
  riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=20

Effetti Pizzicato:
  compressore: soglia=-26 rapporto=2 attacco=10 rilascio=200 guadagno=10
  riverbero: stanza=70 smorzamento=40 ampiezza=100 mix=18

Effetti Cello:
  compressore: soglia=-24 rapporto=2 attacco=30 rilascio=300 guadagno=10
  riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=20

Effetti DoubleBasses:
  compressore: soglia=-24 rapporto=2 attacco=20 rilascio=200 guadagno=6
  riverbero: stanza=70 smorzamento=50 ampiezza=100 mix=12

Effetti Harp:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=22

Effetti Horns:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=22

Effetti Glockenspiel:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=25

Catena master:
  plugin: mix=22 livello=0 ref="lv2:http://calf.sourceforge.net/plugins/Reverb"
  eq: bassi=1 medi=0 alti=1
  compressore: soglia=-18 rapporto=1.5 attacco=40 rilascio=300 guadagno=2
  limiter: guadagno=4 tetto=-1 rilascio=200

// ================================================================ mixer

Mixer Violins:
  volume: 88 pan: -0.35 mute: no solo: no

Mixer Pizzicato:
  volume: 85 pan: -0.15 mute: no solo: no

Mixer Cello:
  volume: 100 pan: 0.3 mute: no solo: no

Mixer DoubleBasses:
  volume: 95 pan: 0.4 mute: no solo: no

Mixer Flute:
  volume: 100 pan: -0.1 mute: no solo: no

Mixer Oboe:
  volume: 115 pan: 0.1 mute: no solo: no

Mixer Horns:
  volume: 72 pan: -0.25 mute: no solo: no

Mixer Trumpets:
  volume: 100 pan: 0.2 mute: no solo: no

Mixer Timpani:
  volume: 110 pan: 0 mute: no solo: no

Mixer Harp:
  volume: 92 pan: -0.45 mute: no solo: no

Mixer Glockenspiel:
  volume: 100 pan: 0.25 mute: no solo: no
