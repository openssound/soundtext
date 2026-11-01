// Harbour Mambo - for big band, Afro-Cuban mambo in C minor
//
// A fifties Latin big band: the percussion opens with the piano montuno and
// the tumbao bass, the saxes play the head, the "mambo" section stacks the
// riffs (first the trombones, then the saxes, then the trumpets), the alto
// sax solo, the shout with the full band, the head again and the coda with
// orchestra hits.
//
// Sounds:
// - SFZ instruments: Salamander grand piano, D. Smolken pizzicato double
//   bass, MTG alto, tenor and baritone saxes, Salamander drums for kick,
//   snare and cymbals (Sounds -> Download and install); congas, cowbell,
//   clave and maracas are the General MIDI SoundFont's, as are trumpets and
//   trombones;
// - master: ACE Compressor (stereo, LV2 plugin), EQ and limiter.

ST: 2.6
Tempo: 192 BPM
Metrica: 4/4
Tonalita: Cm

Strumento Alto:
  program=65 percussione=no ottava=5 range=49-81 poly=no voicing=monophonic

Strumento Tenor:
  program=66 percussione=no ottava=4 range=44-76 poly=no voicing=monophonic

Strumento Baritone:
  program=67 percussione=no ottava=3 range=36-69 poly=no voicing=monophonic

Strumento Trumpets:
  program=56 percussione=no ottava=5 range=54-86 poly=si voicing=spread

Strumento Trombones:
  program=57 percussione=no ottava=3 range=40-72 poly=si voicing=spread

Strumento DoubleBass:
  program=32 percussione=no ottava=2 range=28-60 poly=no voicing=root_fifth

// ================================================================ percussion (2-3 clave)

Pattern %Latin:
  8: 92@ [conga_mute cowbell maracas] 60@ [conga_mute maracas] 95@ [conga_open cowbell claves maracas] 75@ [conga_open maracas] 92@ [conga_mute cowbell claves maracas] 60@ [conga_mute maracas] 95@ [conga_low cowbell maracas] 75@ [conga_low maracas] |
  92@ [conga_mute cowbell claves maracas] 60@ [conga_mute maracas] 95@ [conga_open cowbell maracas] 75@ [conga_open claves maracas] 92@ [conga_mute cowbell maracas] 60@ [conga_mute maracas] 95@ [conga_low cowbell claves maracas] 75@ [conga_low maracas] |

// the first bar of the Latin groove, to end the sections with the timbales fill
Pattern %LatinA:
  8: 92@ [conga_mute cowbell maracas] 60@ [conga_mute maracas] 95@ [conga_open cowbell claves maracas] 75@ [conga_open maracas] 92@ [conga_mute cowbell claves maracas] 60@ [conga_mute maracas] 95@ [conga_low cowbell maracas] 75@ [conga_low maracas] |

Pattern %TimbaleFill:
  8: 100@ timbale_hi timbale_hi timbale_low timbale_low 105@ timbale_hi timbale_low 115@ [timbale_hi crash] r |

Pattern %KitFill:
  8: 95@ snare snare 100@ tom1 tom1 105@ tom2 floor 115@ [kick crash] r |

Pattern %Kit:
  8: 85@ kick 3r 75@ rimshot r 90@ kick r | 85@ kick 2r 80@ rimshot 2r 90@ kick r |

Pattern %KitShout:
  8: 110@ [kick crash] 3r 95@ snare r 105@ kick r | 100@ kick 2r 100@ snare 2r 110@ [kick snare] r |

// ================================================================ rhythm section: montuno and tumbao

Pattern %MonCm:
  8: 82@ Cm! Cm! r Cm! r Cm! Cm! r |

Pattern %MonFm:
  8: 82@ Fm! Fm! r Fm! r Fm! Fm! r |

Pattern %MonG:
  8: 85@ G7! G7! r G7! r G7! G7! r |

Pattern %BsCm:
  8: 100@ 3r 3c*2 2g*1 |

Pattern %BsFm:
  8: 100@ 3r 3f*1 2c*2 |

Pattern %BsG:
  8: 100@ 3r 3g*1 2d*2 |

// A: Cm Cm Fm Fm G7 G7 Cm Cm      mambo: Cm Fm G7 Cm
Pattern %MontunoA:
  %MonCm %MonCm %MonFm %MonFm %MonG %MonG %MonCm %MonCm

Pattern %MontunoVamp:
  %MonCm %MonFm %MonG %MonCm

Pattern %TumbaoA:
  %BsCm %BsCm %BsFm %BsFm %BsG %BsG %BsCm %BsCm

Pattern %TumbaoVamp:
  %BsCm %BsFm %BsG %BsCm

// ================================================================ the head and the riffs

Pattern %Theme:
  8:
  g*4 c*5 eb*5 g*5 2f*5 eb*5 d*5 |
  4c*5_ r g*4 c*5 d*5 |
  c*5 eb*5 f*5 ab*5 2g*5 f*5 eb*5 |
  4f*5_ r c*5 eb*5 f*5 |
  g*5 f*5 d*5 b*4 2d*5 c*5 b*4 |
  4g*4_ r b*4 d*5 f*5 |
  eb*5 d*5 c*5 g*4 2c*5 eb*5 g*5 |
  4c*5_ 4r |

Pattern %ColpiA:
  8: 3r Cm! 2r Cm! r | 3r Cm! 2r Cm! r | 3r Fm! 2r Fm! r | 3r Fm! 2r Fm! r |
  3r G7! 2r G7! r | 3r G7! 2r G7! r | 3r Cm! 2r Cm! r | Cm! 3r 4r |

Pattern %RiffTrombones:
  8: c*3 2r c*3 eb*3 2r g*3 | 2f*3 eb*3 c*3 4r |

Pattern %RiffSax:
  8: 4r g*4 bb*4 c*5 eb*5 | 2f*5 eb*5 c*5 2bb*4 2g*4 |

Pattern %RiffTrumpets:
  8: 2c*6 c*6 bb*5 2g*5 r g*5 | eb*5 f*5 2g*5 4r |

// ================================================================ the alto solo (16 bars on the vamp)

Pattern %Solo:
  8:
  2r c*5 d*5 eb*5 f*5 2g*5 |
  ab*5 g*5 f*5 eb*5 2c*5 2r |
  b*4 d*5 f*5 ab*5 2g*5 f*5 d*5 |
  4c*5_ eb*5 d*5 2c*5 |
  16: g*5 f*5 eb*5 c*5 g*5 f*5 eb*5 c*5 8: eb*5 f*5 2g*5 |
  ab*5 f*5 c*5 ab*4 4c*5 |
  8T: b*4 d*5 f*5 b*4 d*5 f*5 8: g*5 f*5 2d*5 |
  4eb*5_ 4r |
  g*5 ab*5 g*5 eb*5 c*5 eb*5 2g*5 |
  2ab*5 f*5 ab*5 4c*5 |
  16: ab*5 g*5 f*5 d*5 b*4 d*5 f*5 ab*5 8: 4g*5 |
  4c*5_ 2eb*5 2g*5 |
  8T: c*5 eb*5 g*5 c*5 eb*5 g*5 c*5 eb*5 g*5 c*5 eb*5 g*5 8: |
  2ab*5 g*5 f*5 2eb*5 2c*5 |
  d*5 f*5 ab*5 g*5 2f*5 2d*5 |
  4c*5_ 4r |

// ================================================================ tracks

Traccia Percussion [Drums]:

Box Percussion "Intro" |0:
  3%Latin %LatinA %TimbaleFill

Box Percussion "Head" |32:
  8%Latin

Box Percussion "Mambo" |96:
  7%Latin %LatinA %TimbaleFill

Box Percussion "Solo" |160:
  8%Latin

Box Percussion "Shout" |224:
  7%Latin %LatinA %TimbaleFill

Box Percussion "Recapitulation" |288:
  3%Latin %LatinA %TimbaleFill

Box Percussion "Coda" |320:
  8: 115@ [cowbell claves] 3r [cowbell claves] 3r | 8r | 8r | 8r |

Traccia Drums [Drums]:

Box Drums "Intro" |0:
  3%Kit 8: 85@ kick 3r 75@ rimshot r 90@ kick r | %KitFill

Box Drums "Head" |32:
  7%Kit %Kit

Box Drums "Mambo" |96:
  3%Kit %Kit 3%KitShout %Kit

Box Drums "Solo" |160:
  8%Kit

Box Drums "Shout" |224:
  7%KitShout 8: 100@ kick 2r 100@ snare 2r 110@ [kick snare] r | %KitFill

Box Drums "Recapitulation" |288:
  3%Kit 8: 85@ kick 3r 75@ rimshot r 90@ kick r | %KitFill

Box Drums "Coda" |320:
  8: 120@ [kick crash] 3r 118@ [kick crash] 3r | 105@ snare snare snare snare 110@ snare snare 115@ snare snare | 120@ [kick crash] 3r 120@ [kick crash] 3r | 8r |

Traccia Piano [Piano]:

Box Piano "Intro" |0:
  2%MontunoVamp

Box Piano "Head" |32:
  2%MontunoA

Box Piano "Mambo, solo and shout" |96:
  12%MontunoVamp

Box Piano "Recapitulation" |288:
  %MontunoA

Box Piano "Coda" |320:
  8: 110@ Cm! 3r Cm! 3r | 8r | Cm! 3r G7! 3r | 8Cm$fermata |

Traccia DoubleBass [DoubleBass]:

Box DoubleBass "Intro" |0:
  2%TumbaoVamp

Box DoubleBass "Head" |32:
  2%TumbaoA

Box DoubleBass "Mambo, solo and shout" |96:
  12%TumbaoVamp

Box DoubleBass "Recapitulation" |288:
  %TumbaoA

Box DoubleBass "Coda" |320:
  8: 110@ c*2 3r c*2 3r | 8r | c*2 3r g*1 3r | 8c*2$fermata |

Traccia Alto [Alto]:

Box Alto "Head" |32:
  8: 100@ %Theme %Theme

Box Alto "Mambo" |96:
  8: 8r | 8r | 8r | 8r | 100@ 6%RiffSax

Box Alto "Solo" |160:
  8: 108@ %Solo

Box Alto "Shout" |224:
  8: 112@ 8%RiffSax

Box Alto "Recapitulation" |288:
  8: 105@ %Theme

Box Alto "Coda" |320:
  8: 115@ c*5 3r c*5 3r | 8r | c*5 3r b*4 3r | 8c*5$fermata |

Traccia Tenor [Tenor]:

Box Tenor "Head" |32:
  8: 100@ %Theme-12 %Theme-12

Box Tenor "Mambo" |96:
  8: 8r | 8r | 8r | 8r | 100@ 6%RiffSax-12

Box Tenor "Shout" |224:
  8: 112@ 8%RiffSax-12

Box Tenor "Recapitulation" |288:
  8: 105@ %Theme-12

Box Tenor "Coda" |320:
  8: 115@ eb*4 3r eb*4 3r | 8r | eb*4 3r d*4 3r | 8eb*4$fermata |

Traccia Baritone [Baritone]:

Box Baritone "Mambo" |96:
  8: 105@ 8%RiffTrombones

Box Baritone "Solo" |160:
  8: 85@ 8%RiffTrombones

Box Baritone "Shout" |224:
  8: 112@ 8%RiffTrombones

Box Baritone "Coda" |320:
  8: 115@ c*3 3r c*3 3r | 8r | c*3 3r g*2 3r | 8c*3$fermata |

Traccia Trumpets [Trumpets]:

Box Trumpets "Intro" |0:
  8: 8r | 8r | 8r | 8r | 8r | 8r | 112@ Cm! 3r G7! 3r | Cm! 3r G7! r G7! r |

Box Trumpets "Head" |32:
  // the second time the trumpets play the head too
  8: 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r | 100@ %Theme

Box Trumpets "Mambo" |96:
  8: 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r | 112@ 4%RiffTrumpets

Box Trumpets "Shout" |224:
  8: 115@ 8%RiffTrumpets

Box Trumpets "Recapitulation" |288:
  8: 108@ %Theme

Box Trumpets "Coda" |320:
  8: 120@ Cm! 3r Cm! 3r | 8r | Cm! 3r G7! 3r | 8Cm$fermata |

Traccia Trombones [Trombones]:

Box Trombones "Intro" |0:
  8: 8r | 8r | 8r | 8r | 8r | 8r | 108@ Cm! 3r G7! 3r | Cm! 3r G7! r G7! r |

Box Trombones "Head" |32:
  8: 95@ %ColpiA %ColpiA

Box Trombones "Mambo" |96:
  8: 108@ 8%RiffTrombones

Box Trombones "Solo" |160:
  // the background under the solo
  8: 80@ 8%RiffTrombones

Box Trombones "Shout" |224:
  8: 112@ 8%RiffTrombones

Box Trombones "Recapitulation" |288:
  8: 100@ %ColpiA

Box Trombones "Coda" |320:
  8: 118@ Cm! 3r Cm! 3r | 8r | Cm! 3r G7! 3r | 8Cm$fermata |

// ================================================================ sounds

Plugin Drums:
  ref="sfz:~/Strumenti/sfz/salamander-drums/ALL.sfz"

Plugin Piano:
  ref="sfz:~/Strumenti/sfz/piano/SalamanderGrandPiano-SFZ+FLAC-V3+20200602/SalamanderGrandPiano-V3+20200602.sfz"

Plugin DoubleBass:
  ref="sfz:~/Strumenti/sfz/contrabbasso/dsmolken_double_bass/d_smolken_rubner_bass_pizz.sfz"

Plugin Alto:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Alto Sax.sfz"

Plugin Tenor:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Tenor Sax.sfz"

Plugin Baritone:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Baritone Sax.sfz"

Effetti Percussion:
  compressore: soglia=-18 rapporto=2 attacco=10 rilascio=120 guadagno=0
  riverbero: stanza=40 smorzamento=50 ampiezza=100 mix=12

Effetti Drums:
  compressore: soglia=-18 rapporto=3 attacco=15 rilascio=120 guadagno=12
  riverbero: stanza=40 smorzamento=50 ampiezza=90 mix=10

Effetti Piano:
  compressore: soglia=-22 rapporto=2 attacco=15 rilascio=150 guadagno=5
  eq: bassi=-1 medi=1 alti=2
  riverbero: stanza=40 smorzamento=45 ampiezza=90 mix=10

Effetti DoubleBass:
  compressore: soglia=-22 rapporto=3 attacco=15 rilascio=150 guadagno=8 preset="Basso"
  eq: bassi=2 medi=1 alti=-1

Effetti Alto:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=8
  riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=14

Effetti Tenor:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=11
  riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=14

Effetti Baritone:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=15
  riverbero: stanza=45 smorzamento=40 ampiezza=100 mix=10

Effetti Trumpets:
  eq: bassi=0 medi=1 alti=2
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=14

Effetti Trombones:
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=14

Catena master:
  plugin: mix=100 livello=0 ref="lv2:urn:ardour:a-comp#stereo" p.att=20 p.rel=150 p.rat=2.5 p.thr=-14 p.mak=2
  eq: bassi=1 medi=0 alti=1
  limiter: guadagno=3 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Percussion:
  volume: 86 pan: 0 mute: no solo: no

Mixer Drums:
  volume: 88 pan: 0 mute: no solo: no

Mixer Piano:
  volume: 88 pan: -0.4 mute: no solo: no

Mixer DoubleBass:
  volume: 100 pan: 0.1 mute: no solo: no

Mixer Alto:
  volume: 100 pan: -0.25 mute: no solo: no

Mixer Tenor:
  volume: 100 pan: 0.05 mute: no solo: no

Mixer Baritone:
  volume: 92 pan: 0.25 mute: no solo: no

Mixer Trumpets:
  volume: 88 pan: -0.15 mute: no solo: no

Mixer Trombones:
  volume: 86 pan: 0.3 mute: no solo: no
