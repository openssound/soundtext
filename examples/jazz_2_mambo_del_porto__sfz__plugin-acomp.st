// Mambo del Porto - per big band, mambo afro-cubano in Do minore
//
// Una big band latina anni '50: le percussioni aprono
// con il piano montuno e il basso tumbao, i sax espongono il tema, la
// sezione "mambo" sovrappone i riff (prima i tromboni, poi i sax, poi le
// trombe), l'assolo del sax contralto, lo shout a band piena, la ripresa del
// tema e la coda con i colpi d'orchestra.
//
// Suoni:
// - strumenti SFZ: pianoforte a coda Salamander, contrabbasso D. Smolken
//   pizzicato, sax contralto, tenore e baritono MTG, batteria Salamander per
//   cassa, rullante e piatti (scarica_strumenti: piano, contrabbasso, solosax,
//   salamander-drums; in ~/Strumenti); congas, campanaccio, clave e maracas
//   sono quelli del SoundFont GM, come trombe e tromboni;
// - master: compressore stereo ACE Compressor (plugin LV2), EQ e limiter.

ST: 2.6
Tempo: 192 BPM
Metrica: 4/4
Tonalita: Cm

Strumento Contralto:
  program=65 percussione=no ottava=5 range=49-81 poly=no voicing=monophonic

Strumento Tenore:
  program=66 percussione=no ottava=4 range=44-76 poly=no voicing=monophonic

Strumento Baritono:
  program=67 percussione=no ottava=3 range=36-69 poly=no voicing=monophonic

Strumento Trombe:
  program=56 percussione=no ottava=5 range=54-86 poly=si voicing=spread

Strumento Tromboni:
  program=57 percussione=no ottava=3 range=40-72 poly=si voicing=spread

Strumento Contrabbasso:
  program=32 percussione=no ottava=2 range=28-60 poly=no voicing=root_fifth

// ================================================================ percussioni (clave 2-3)

Pattern %Latin:
  8: 92@ [conga_mute cowbell maracas] 60@ [conga_mute maracas] 95@ [conga_open cowbell claves maracas] 75@ [conga_open maracas] 92@ [conga_mute cowbell claves maracas] 60@ [conga_mute maracas] 95@ [conga_low cowbell maracas] 75@ [conga_low maracas] |
  92@ [conga_mute cowbell claves maracas] 60@ [conga_mute maracas] 95@ [conga_open cowbell maracas] 75@ [conga_open claves maracas] 92@ [conga_mute cowbell maracas] 60@ [conga_mute maracas] 95@ [conga_low cowbell claves maracas] 75@ [conga_low maracas] |

// la prima battuta del Latin, per chiudere le sezioni con il fill dei timbales
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

// ================================================================ ritmica: montuno e tumbao

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

// ================================================================ il tema e i riff

Pattern %Tema:
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

Pattern %RiffTromboni:
  8: c*3 2r c*3 eb*3 2r g*3 | 2f*3 eb*3 c*3 4r |

Pattern %RiffSax:
  8: 4r g*4 bb*4 c*5 eb*5 | 2f*5 eb*5 c*5 2bb*4 2g*4 |

Pattern %RiffTrombe:
  8: 2c*6 c*6 bb*5 2g*5 r g*5 | eb*5 f*5 2g*5 4r |

// ================================================================ l'assolo del contralto (16 battute sul vamp)

Pattern %Assolo:
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

// ================================================================ tracce

Traccia Percussioni [Drums]:

Box Percussioni "Introduzione" |0:
  3%Latin %LatinA %TimbaleFill

Box Percussioni "Tema" |32:
  8%Latin

Box Percussioni "Mambo" |96:
  7%Latin %LatinA %TimbaleFill

Box Percussioni "Assolo" |160:
  8%Latin

Box Percussioni "Shout" |224:
  7%Latin %LatinA %TimbaleFill

Box Percussioni "Ripresa" |288:
  3%Latin %LatinA %TimbaleFill

Box Percussioni "Coda" |320:
  8: 115@ [cowbell claves] 3r [cowbell claves] 3r | 8r | 8r | 8r |

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  3%Kit 8: 85@ kick 3r 75@ rimshot r 90@ kick r | %KitFill

Box Batteria "Tema" |32:
  7%Kit %Kit

Box Batteria "Mambo" |96:
  3%Kit %Kit 3%KitShout %Kit

Box Batteria "Assolo" |160:
  8%Kit

Box Batteria "Shout" |224:
  7%KitShout 8: 100@ kick 2r 100@ snare 2r 110@ [kick snare] r | %KitFill

Box Batteria "Ripresa" |288:
  3%Kit 8: 85@ kick 3r 75@ rimshot r 90@ kick r | %KitFill

Box Batteria "Coda" |320:
  8: 120@ [kick crash] 3r 118@ [kick crash] 3r | 105@ snare snare snare snare 110@ snare snare 115@ snare snare | 120@ [kick crash] 3r 120@ [kick crash] 3r | 8r |

Traccia Pianoforte [Piano]:

Box Pianoforte "Introduzione" |0:
  2%MontunoVamp

Box Pianoforte "Tema" |32:
  2%MontunoA

Box Pianoforte "Mambo, assolo e shout" |96:
  12%MontunoVamp

Box Pianoforte "Ripresa" |288:
  %MontunoA

Box Pianoforte "Coda" |320:
  8: 110@ Cm! 3r Cm! 3r | 8r | Cm! 3r G7! 3r | 8Cm$fermata |

Traccia Contrabbasso [Contrabbasso]:

Box Contrabbasso "Introduzione" |0:
  2%TumbaoVamp

Box Contrabbasso "Tema" |32:
  2%TumbaoA

Box Contrabbasso "Mambo, assolo e shout" |96:
  12%TumbaoVamp

Box Contrabbasso "Ripresa" |288:
  %TumbaoA

Box Contrabbasso "Coda" |320:
  8: 110@ c*2 3r c*2 3r | 8r | c*2 3r g*1 3r | 8c*2$fermata |

Traccia Contralto [Contralto]:

Box Contralto "Tema" |32:
  8: 100@ %Tema %Tema

Box Contralto "Mambo" |96:
  8: 8r | 8r | 8r | 8r | 100@ 6%RiffSax

Box Contralto "Assolo" |160:
  8: 108@ %Assolo

Box Contralto "Shout" |224:
  8: 112@ 8%RiffSax

Box Contralto "Ripresa" |288:
  8: 105@ %Tema

Box Contralto "Coda" |320:
  8: 115@ c*5 3r c*5 3r | 8r | c*5 3r b*4 3r | 8c*5$fermata |

Traccia Tenore [Tenore]:

Box Tenore "Tema" |32:
  8: 100@ %Tema-12 %Tema-12

Box Tenore "Mambo" |96:
  8: 8r | 8r | 8r | 8r | 100@ 6%RiffSax-12

Box Tenore "Shout" |224:
  8: 112@ 8%RiffSax-12

Box Tenore "Ripresa" |288:
  8: 105@ %Tema-12

Box Tenore "Coda" |320:
  8: 115@ eb*4 3r eb*4 3r | 8r | eb*4 3r d*4 3r | 8eb*4$fermata |

Traccia Baritono [Baritono]:

Box Baritono "Mambo" |96:
  8: 105@ 8%RiffTromboni

Box Baritono "Assolo" |160:
  8: 85@ 8%RiffTromboni

Box Baritono "Shout" |224:
  8: 112@ 8%RiffTromboni

Box Baritono "Coda" |320:
  8: 115@ c*3 3r c*3 3r | 8r | c*3 3r g*2 3r | 8c*3$fermata |

Traccia Trombe [Trombe]:

Box Trombe "Introduzione" |0:
  8: 8r | 8r | 8r | 8r | 8r | 8r | 112@ Cm! 3r G7! 3r | Cm! 3r G7! r G7! r |

Box Trombe "Tema" |32:
  // la seconda volta il tema anche alle trombe
  8: 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r | 100@ %Tema

Box Trombe "Mambo" |96:
  8: 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r | 112@ 4%RiffTrombe

Box Trombe "Shout" |224:
  8: 115@ 8%RiffTrombe

Box Trombe "Ripresa" |288:
  8: 108@ %Tema

Box Trombe "Coda" |320:
  8: 120@ Cm! 3r Cm! 3r | 8r | Cm! 3r G7! 3r | 8Cm$fermata |

Traccia Tromboni [Tromboni]:

Box Tromboni "Introduzione" |0:
  8: 8r | 8r | 8r | 8r | 8r | 8r | 108@ Cm! 3r G7! 3r | Cm! 3r G7! r G7! r |

Box Tromboni "Tema" |32:
  8: 95@ %ColpiA %ColpiA

Box Tromboni "Mambo" |96:
  8: 108@ 8%RiffTromboni

Box Tromboni "Assolo" |160:
  // lo sfondo sotto l'assolo
  8: 80@ 8%RiffTromboni

Box Tromboni "Shout" |224:
  8: 112@ 8%RiffTromboni

Box Tromboni "Ripresa" |288:
  8: 100@ %ColpiA

Box Tromboni "Coda" |320:
  8: 118@ Cm! 3r Cm! 3r | 8r | Cm! 3r G7! 3r | 8Cm$fermata |

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/salamander-drums/ALL.sfz"

Plugin Pianoforte:
  ref="sfz:~/Strumenti/sfz/piano/SalamanderGrandPiano-SFZ+FLAC-V3+20200602/SalamanderGrandPiano-V3+20200602.sfz"

Plugin Contrabbasso:
  ref="sfz:~/Strumenti/sfz/contrabbasso/dsmolken_double_bass/d_smolken_rubner_bass_pizz.sfz"

Plugin Contralto:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Alto Sax.sfz"

Plugin Tenore:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Tenor Sax.sfz"

Plugin Baritono:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Baritone Sax.sfz"

Effetti Percussioni:
  compressore: soglia=-18 rapporto=2 attacco=10 rilascio=120 guadagno=0
  riverbero: stanza=40 smorzamento=50 ampiezza=100 mix=12

Effetti Batteria:
  compressore: soglia=-18 rapporto=3 attacco=15 rilascio=120 guadagno=12
  riverbero: stanza=40 smorzamento=50 ampiezza=90 mix=10

Effetti Pianoforte:
  compressore: soglia=-22 rapporto=2 attacco=15 rilascio=150 guadagno=5
  eq: bassi=-1 medi=1 alti=2
  riverbero: stanza=40 smorzamento=45 ampiezza=90 mix=10

Effetti Contrabbasso:
  compressore: soglia=-22 rapporto=3 attacco=15 rilascio=150 guadagno=8 preset="Basso"
  eq: bassi=2 medi=1 alti=-1

Effetti Contralto:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=8
  riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=14

Effetti Tenore:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=11
  riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=14

Effetti Baritono:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=15
  riverbero: stanza=45 smorzamento=40 ampiezza=100 mix=10

Effetti Trombe:
  eq: bassi=0 medi=1 alti=2
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=14

Effetti Tromboni:
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=14

Catena master:
  plugin: mix=100 livello=0 ref="lv2:urn:ardour:a-comp#stereo" p.att=20 p.rel=150 p.rat=2.5 p.thr=-14 p.mak=2
  eq: bassi=1 medi=0 alti=1
  limiter: guadagno=3 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Percussioni:
  volume: 86 pan: 0 mute: no solo: no

Mixer Batteria:
  volume: 88 pan: 0 mute: no solo: no

Mixer Pianoforte:
  volume: 88 pan: -0.4 mute: no solo: no

Mixer Contrabbasso:
  volume: 100 pan: 0.1 mute: no solo: no

Mixer Contralto:
  volume: 100 pan: -0.25 mute: no solo: no

Mixer Tenore:
  volume: 100 pan: 0.05 mute: no solo: no

Mixer Baritono:
  volume: 92 pan: 0.25 mute: no solo: no

Mixer Trombe:
  volume: 88 pan: -0.15 mute: no solo: no

Mixer Tromboni:
  volume: 86 pan: 0.3 mute: no solo: no
