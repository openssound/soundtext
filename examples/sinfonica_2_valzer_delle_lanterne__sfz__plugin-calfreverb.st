// Valzer delle Lanterne - valzer sinfonico in Sol maggiore
//
// Un valzer da concerto alla maniera viennese: l'arpa e il flauto aprono,
// il tema A ai violini sull'"um-pa-pa" dei contrabbassi e degli archi
// pizzicati, il tema B in Mi minore al violoncello solista con il
// controcanto dell'oboe, il tema A a piena orchestra, il trio in Do maggiore
// ai corni, l'ultimo tema A con il glockenspiel e la coda.
//
// Suoni:
// - strumenti SFZ: archi pizzicati (Discord GM Bank), violoncello Karoryfer
//   Bigcat, contrabbassi D. Smolken pizzicati, arpa da concerto
//   (scarica_strumenti: gm-bank, cello, contrabbasso, arpa; in ~/Strumenti);
//   violini, legni, ottoni, timpani e glockenspiel sono quelli del SoundFont GM;
// - la sala: riverbero interno sulle sezioni e Calf Reverb (plugin LV2) sul
//   master, poi EQ, compressore leggero e limiter.

ST: 2.6
Tempo: 160 BPM
Metrica: 3/4
Tonalita: G

Strumento Violini:
  program=48 percussione=no ottava=5 range=55-100 poly=si voicing=spread

Strumento Pizzicati:
  program=45 percussione=no ottava=4 range=28-88 poly=si voicing=spread

Strumento Violoncello:
  program=42 percussione=no ottava=3 range=36-77 poly=no voicing=monophonic

Strumento Contrabbassi:
  program=43 percussione=no ottava=2 range=28-60 poly=no voicing=root_only

Strumento Flauto:
  program=73 percussione=no ottava=5 range=60-96 poly=no voicing=monophonic

Strumento Oboe:
  program=68 percussione=no ottava=5 range=58-91 poly=no voicing=monophonic

Strumento Corni:
  program=60 percussione=no ottava=4 range=34-77 poly=si voicing=spread

Strumento Trombe:
  program=56 percussione=no ottava=4 range=54-86 poly=si voicing=spread

Strumento Timpani:
  program=47 percussione=no ottava=2 range=28-57 poly=no voicing=root_only

Strumento Arpa:
  program=46 percussione=no ottava=3 range=28-102 poly=si voicing=spread

Strumento Glockenspiel:
  program=9 percussione=no ottava=6 range=72-108 poly=no voicing=monophonic

// ================================================================ tema A (16 battute)

Pattern %TemaA:
  4:
  d*5 g*5 b*5 | 2a*5 g*5 | f#*5 a*5 c*6 | 3b*5 |
  a*5 f#*5 d*5 | 2e*5 f#*5 | 3g*5 | 2d*5 r |
  d*5 g*5 b*5 | 2d*6 b*5 | e*6 d*6 c*6 | 2eb*6 c*6 |
  b*5 d*6 g*5 | 2a*5 f#*5 | 3g*5 | 2g*5 r |

Pattern %BassiA:
  4: g*1 2r | g*1 2r | d*2 2r | a*1 2r | d*2 2r | a*1 2r | g*1 2r | d*2 2r |
  g*1 2r | g*1 2r | c*2 2r | c*2 2r | d*2 2r | d*2 2r | g*1 2r | g*1 2r |

Pattern %PizzA:
  4: r G! G! | r G! G! | r D7! D7! | r D7! D7! | r D7! D7! | r D7! D7! | r G! G! | r G! G! |
  r G! G! | r G7! G7! | r C! C! | r Cm! Cm! | r G! G! | r D7! D7! | r G! G! | r G! G! |

Pattern %ArmonieA:
  4: 3G_ | 3G_ | 3D7_ | 3D7_ | 3D7_ | 3D7_ | 3G_ | 3G_ | 3G_ | 3G7_ | 3C_ | 3Cm_ | 3G_ | 3D7_ | 3G_ | 3G_ |

// ================================================================ tema B in Mi minore (16 battute)

Pattern %TemaB:
  4:
  2e*4 b*3 | g*3 b*3 e*4 | 2d#*4 f#*4 | 3a*4 |
  a*4 f#*4 d#*4 | 2b*3 c*4 | 3b*3 | 2e*3 r |
  c*4 e*4 a*4 | 2c*4 a*3 | b*3 d*4 g*4 | 2e*4 g*4 |
  e*4 c*4 a*3 | 2d#*4 f#*4 | 3e*4 | 2d*4 c*4 |

Pattern %ControcantoB:
  4: 3g*5 | 3g*5 | 3f#*5 | 3f#*5 | 3a*5 | 3a*5 | 3g*5 | 3g*5 |
  3e*5 | 3f#*5 | 3g*5 | 3g*5 | 3e*5 | 3f#*5 | 3e*5 | 3f#*5 |

Pattern %ArmonieB:
  4: 3Em_ | 3Em_ | 3B7_ | 3B7_ | 3B7_ | 3B7_ | 3Em_ | 3Em_ | 3Am_ | 3D7_ | 3G_ | 3C_ | 3Am_ | 3B7_ | 3Em_ | 3D7_ |

Pattern %BassiB:
  4: e*2 2r | e*2 2r | b*1 2r | b*1 2r | b*1 2r | b*1 2r | e*2 2r | e*2 2r |
  a*1 2r | d*2 2r | g*1 2r | c*2 2r | a*1 2r | b*1 2r | e*2 2r | d*2 2r |

Pattern %PizzB:
  4: r Em! Em! | r Em! Em! | r B7! B7! | r B7! B7! | r B7! B7! | r B7! B7! | r Em! Em! | r Em! Em! |
  r Am! Am! | r D7! D7! | r G! G! | r C! C! | r Am! Am! | r B7! B7! | r Em! Em! | r D7! D7! |

// ================================================================ trio in Do maggiore (16 battute)

Pattern %Trio:
  4:
  2e*4 g*4 | 3c*5 | b*4 a*4 g*4 | 3f*4 |
  d*4 f*4 b*4 | 2d*5 b*4 | 3c*5 | 2g*4 r |
  a*4 c*5 f*5 | 2e*5 c*5 | 3g*4 | 2c#*5 a*4 |
  d*5 c*5 a*4 | 2b*4 g*4 | 3c*5 | 2d*5 r |

Pattern %ArmonieTrio:
  4: 3C_ | 3C_ | 3G7_ | 3G7_ | 3G7_ | 3G7_ | 3C_ | 3C_ | 3F_ | 3F_ | 3C_ | 3A7_ | 3Dm_ | 3G7_ | 3C_ | 3D7_ |

Pattern %BassiTrio:
  4: c*2 2r | c*2 2r | g*1 2r | g*1 2r | g*1 2r | g*1 2r | c*2 2r | c*2 2r |
  f*1 2r | f*1 2r | c*2 2r | a*1 2r | d*2 2r | g*1 2r | c*2 2r | d*2 2r |

// arpeggi di una battuta (sei crome) per l'ultimo tema A
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

Pattern %ArpaA:
  %ArG %ArG %ArD7 %ArD7 %ArD7 %ArD7 %ArG %ArG %ArG %ArG7 %ArC %ArCm %ArG %ArD7 %ArG %ArG

Pattern %ArpaTrio:
  4: c*3 g*3 e*4 | c*3 g*3 e*4 | g*2 d*3 f*3 | g*2 d*3 b*3 | g*2 d*3 f*3 | g*2 d*3 b*3 | c*3 g*3 e*4 | c*3 g*3 e*4 |
  f*2 c*3 a*3 | f*2 c*3 a*3 | c*3 g*3 e*4 | a*2 e*3 c#*4 | d*3 a*3 f*4 | g*2 d*3 b*3 | c*3 g*3 e*4 | d*3 a*3 f#*4 |

// ================================================================ tracce

Traccia Violini [Violini]:

Box Violini "Tema A" |24:
  4: 90@ %TemaA

Box Violini "Tema B" |72:
  4: 50@ %ArmonieB

Box Violini "Tema A, piena orchestra" |120:
  4: 105@ %TemaA

Box Violini "Trio" |168:
  4: 60@ %ArmonieTrio

Box Violini "Ultimo tema A" |216:
  4: 110@ %TemaA

Box Violini "Coda" |264:
  // accelerando e corona finale
  4: 112@ tempo=160 >> d*5 g*5 b*5 | d*6 b*5 g*5 | e*6 c*6 g*5 | d*6 a*5 f#*5 |
  g*5 b*5 d*6 | a*5 c*6 f#*6 | tempo=176 3g*6 | 3g*5$fermata |

Traccia Pizzicati [Pizzicati]:

Box Pizzicati "Tema A" |24:
  4: 72@ %PizzA

Box Pizzicati "Tema B" |72:
  4: 65@ %PizzB

Box Pizzicati "Tema A, piena orchestra" |120:
  4: 80@ %PizzA

Box Pizzicati "Ultimo tema A" |216:
  4: 85@ %PizzA

Traccia Violoncello [Violoncello]:

Box Violoncello "Tema B" |72:
  // il canto del violoncello solista
  4: 85@ %TemaB

Box Violoncello "Trio" |168:
  4: 70@ 3c*3 | 3c*3 | 3g*2 | 3g*2 | 3g*2 | 3g*2 | 3c*3 | 3c*3 | 3f*2 | 3f*2 | 3c*3 | 3a*2 | 3d*3 | 3g*2 | 3c*3 | 3d*3 |

Box Violoncello "Coda" |264:
  4: 100@ 3g*2 | 3g*2 | 3c*3 | 3d*3 | 3g*2 | 3d*3 | 3g*2 | 3g*2$fermata |

Traccia Contrabbassi [Contrabbassi]:

Box Contrabbassi "Introduzione" |0:
  4: 70@ g*1 2r | g*1 2r | d*2 2r | d*2 2r | g*1 2r | g*1 2r | d*2 2r | d*2 2r |

Box Contrabbassi "Tema A" |24:
  4: 95@ %BassiA

Box Contrabbassi "Tema B" |72:
  4: 90@ %BassiB

Box Contrabbassi "Tema A, piena orchestra" |120:
  4: 100@ %BassiA

Box Contrabbassi "Trio" |168:
  4: 85@ %BassiTrio

Box Contrabbassi "Ultimo tema A" |216:
  4: 105@ %BassiA

Box Contrabbassi "Coda" |264:
  4: 108@ g*1 2r | g*1 2r | c*2 2r | d*2 2r | g*1 2r | d*2 2r | g*1 2r | 3g*1$fermata |

Traccia Flauto [Flauto]:

Box Flauto "Introduzione" |0:
  4: 72@ d*5 g*5 b*5 | 2a*5 g*5 | f#*5 a*5 c*6 | 3b*5 | a*5 f#*5 d*5 | 2e*5 f#*5 | 3g*5 | 2d*5 r |

Box Flauto "Tema A, piena orchestra" |120:
  4: 95@ %TemaA

Box Flauto "Ultimo tema A" |216:
  4: 100@ %TemaA

Traccia Oboe [Oboe]:

Box Oboe "Tema B" |72:
  4: 72@ %ControcantoB

Box Oboe "Trio" |168:
  4: 65@ %Trio+12

Traccia Corni [Corni]:

Box Corni "Tema A, piena orchestra" |120:
  4: 82@ %ArmonieA

Box Corni "Trio" |168:
  // il tema del trio
  4: 92@ %Trio

Box Corni "Ultimo tema A" |216:
  4: 90@ %ArmonieA

Box Corni "Coda" |264:
  4: 100@ 3G_ | 3G_ | 3C_ | 3D7_ | 3G_ | 3D7_ | 3G_ | 3G$fermata |

Traccia Trombe [Trombe]:

Box Trombe "Ultimo tema A" |216:
  4: 95@ G! 2r | 3r | D7! 2r | 3r | D7! 2r | 3r | G! 2r | 3r | G! 2r | G7! 2r | C! 2r | Cm! 2r | G! 2r | D7! 2r | G! 2r | 3r |

Box Trombe "Coda" |264:
  4: 105@ G! 2r | 3r | C! 2r | D7! 2r | G! 2r | D7! 2r | G! G! G! | 3G$fermata |

Traccia Timpani [Timpani]:

Box Timpani "Tema A, piena orchestra" |120:
  4: 95@ g*1 2r | 3r | d*2 2r | 3r | d*2 2r | 3r | g*1 2r | d*2 2r |
  g*1 2r | 3r | 3r | 3r | g*1 2r | d*2 2r | g*1 2r | 3r |

Box Timpani "Ultimo tema A" |216:
  4: 100@ g*1 2r | 3r | d*2 2r | 3r | d*2 2r | 3r | g*1 2r | d*2 2r |
  g*1 2r | 3r | 3r | 3r | g*1 2r | d*2 2r | g*1 2r | 3r |

Box Timpani "Coda" |264:
  4: 108@ g*1 2r | 3r | 3r | d*2 2r | g*1 2r | d*2 2r | g*1 g*1 g*1 | 16: 70@ >> 12(g*1) 118@ |

Traccia Arpa [Arpa]:

Box Arpa "Introduzione" |0:
  4: 75@ g*2 d*3 b*3 | g*2 d*3 b*3 | d*2 a*2 c*4 | d*2 a*2 f#*3 | d*2 a*2 c*4 | d*2 a*2 f#*3 | g*2 d*3 b*3 | g*2 d*3 b*3 |

Box Arpa "Trio" |168:
  4: 78@ %ArpaTrio

Box Arpa "Ultimo tema A" |216:
  8: 82@ %ArpaA

Box Arpa "Coda" |264:
  8: 90@ 2(g*2 d*3 g*3 b*3 d*4 g*4) | 2(c*3 g*3 c*4 e*4 g*4 c*5) |
  d*3 a*3 d*4 f#*4 a*4 d*5 | g*2 d*3 g*3 b*3 d*4 g*4 | d*3 a*3 d*4 f#*4 a*4 d*5 |
  g*2 d*3 g*3 b*3 d*4 g*4 | 4: 3G$fermata |

Traccia Glockenspiel [Glockenspiel]:

Box Glockenspiel "Ultimo tema A" |216:
  4: 100@ %TemaA+12

// ================================================================ suoni

Plugin Pizzicati:
  ref="sfz:~/Strumenti/sfz/gm-bank/Discord GM/Melodic/046-Pizzicato Strings.sfz"

Plugin Violoncello:
  ref="sfz:~/Strumenti/sfz/cello/Karoryfer_Bigcat_cello/Programs/01- Bowed (velocity layer).sfz"

Plugin Contrabbassi:
  ref="sfz:~/Strumenti/sfz/contrabbasso/dsmolken_double_bass/d_smolken_rubner_bass_pizz.sfz"

Plugin Arpa:
  ref="sfz:~/Strumenti/sfz/arpa/ConcertHarp-SFZ+FLAC-20200702/ConcertHarp-20200702.sfz"

Effetti Violini:
  riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=20

Effetti Pizzicati:
  compressore: soglia=-26 rapporto=2 attacco=10 rilascio=200 guadagno=10
  riverbero: stanza=70 smorzamento=40 ampiezza=100 mix=18

Effetti Violoncello:
  compressore: soglia=-24 rapporto=2 attacco=30 rilascio=300 guadagno=10
  riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=20

Effetti Contrabbassi:
  compressore: soglia=-24 rapporto=2 attacco=20 rilascio=200 guadagno=6
  riverbero: stanza=70 smorzamento=50 ampiezza=100 mix=12

Effetti Arpa:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=22

Effetti Corni:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=22

Effetti Glockenspiel:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=25

Catena master:
  plugin: mix=22 livello=0 ref="lv2:http://calf.sourceforge.net/plugins/Reverb"
  eq: bassi=1 medi=0 alti=1
  compressore: soglia=-18 rapporto=1.5 attacco=40 rilascio=300 guadagno=2
  limiter: guadagno=4 tetto=-1 rilascio=200

// ================================================================ mixer

Mixer Violini:
  volume: 88 pan: -0.35 mute: no solo: no

Mixer Pizzicati:
  volume: 85 pan: -0.15 mute: no solo: no

Mixer Violoncello:
  volume: 100 pan: 0.3 mute: no solo: no

Mixer Contrabbassi:
  volume: 95 pan: 0.4 mute: no solo: no

Mixer Flauto:
  volume: 100 pan: -0.1 mute: no solo: no

Mixer Oboe:
  volume: 115 pan: 0.1 mute: no solo: no

Mixer Corni:
  volume: 72 pan: -0.25 mute: no solo: no

Mixer Trombe:
  volume: 100 pan: 0.2 mute: no solo: no

Mixer Timpani:
  volume: 110 pan: 0 mute: no solo: no

Mixer Arpa:
  volume: 92 pan: -0.45 mute: no solo: no

Mixer Glockenspiel:
  volume: 100 pan: 0.25 mute: no solo: no
