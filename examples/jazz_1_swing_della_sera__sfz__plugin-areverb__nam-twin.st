// Swing della Sera - per big band, swing in Si bemolle
//
// Uno swing classico per big band, su una forma AABA da 32 battute:
// introduzione degli ottoni, il tema (i sax all'unisono nelle A, le trombe
// nel ponte), un intero giro di assolo del sax tenore con gli sfondi dei
// tromboni, lo "shout chorus" a band piena, la ripresa dell'ultima A e il
// finale. La sezione ritmica e' quella classica: contrabbasso che cammina,
// pianoforte che commenta sul 2 e sul 4, chitarra "quattro in battuta" e
// batteria con lo swing sul piatto ride.
//
// Suoni:
// - strumenti SFZ: batteria Salamander, contrabbasso D. Smolken pizzicato,
//   pianoforte a coda Salamander, sax contralto, tenore e baritono MTG,
//   chitarra FreePats (scarica_strumenti: salamander-drums, contrabbasso,
//   piano, solosax, chitarra-elettrica; in ~/Strumenti); trombe e tromboni
//   sono quelli del SoundFont GM;
// - la chitarra nel profilo NAM del Fender Twin, scurita come una chitarra
//   jazz (profili con Suoni -> Scarica -> profili NAM consigliati);
// - master: riverbero ACE Reverb (plugin LV2), compressore e limiter.

ST: 2.6
Tempo: 168 BPM
Metrica: 4/4
Tonalita: Bb

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

Strumento Ritmica:
  program=26 percussione=no ottava=3 range=40-76 poly=si voicing=spread

Strumento Contrabbasso:
  program=32 percussione=no ottava=2 range=28-60 poly=no voicing=root_fifth

// ================================================================ batteria

Pattern %Swing:
  8: 82@ [ride kick] 40@ kick 98@ [ride hihat_pedal] 72@ ride 82@ [ride kick] 40@ kick 98@ [ride hihat_pedal] 72@ ride |

Pattern %SwingCrash:
  8: 105@ [crash kick] 40@ kick 98@ [ride hihat_pedal] 72@ ride 82@ [ride kick] 40@ kick 98@ [ride hihat_pedal] 72@ ride |

Pattern %SwingFill:
  8: 82@ [ride kick] 40@ kick 98@ [ride hihat_pedal] 72@ ride 95@ snare 85@ snare 100@ tom1 105@ [kick snare] |

Pattern %SwingHat:
  8: 80@ [hihat kick] 40@ kick 95@ [hihat hihat_pedal] 70@ hihat 80@ [hihat kick] 40@ kick 95@ [hihat hihat_pedal] 70@ hihat |

Pattern %DrA:
  %SwingCrash %Swing %Swing %Swing %Swing %Swing %Swing %SwingFill

Pattern %DrB:
  %SwingCrash %Swing %Swing %Swing %Swing %Swing %Swing %SwingFill

Pattern %DrChorus:
  %DrA %DrA %DrB %DrA

Pattern %Shout:
  8: 118@ [crash kick] 50@ kick 105@ [ride snare] 72@ ride 85@ [ride kick] 50@ kick 110@ [ride snare] 105@ [kick snare] |

// ================================================================ armonia: A = Bb6 G7 | Cm7 F7 | Bb6 G7 | Cm7 F7 | Fm7 Bb7 | Eb6 Ebm6 | Cm7 F7 | Bb6 (F7)
//                                            B = D7 | D7 | G7 | G7 | C7 | C7 | F7 | F7

Pattern %CompA:
  4: r Bb6! r G7! | r Cm7! r F7! | r Bb6! r G7! | r Cm7! r F7! | r Fm7! r Bb7! | r Eb6! r Ebm6! | r Cm7! r F7! | r Bb6! r F7! |

Pattern %CompA3:
  4: r Bb6! r G7! | r Cm7! r F7! | r Bb6! r G7! | r Cm7! r F7! | r Fm7! r Bb7! | r Eb6! r Ebm6! | r Cm7! r F7! | r Bb6! 2r |

Pattern %CompB:
  4: r D7! r D7! | r D7! r D7! | r G7! r G7! | r G7! r G7! | r C7! r C7! | r C7! r C7! | r F7! r F7! | r F7! r F7! |

Pattern %CompChorus:
  %CompA %CompA %CompB %CompA3

Pattern %GtA:
  4: Bb6! Bb6! G7! G7! | Cm7! Cm7! F7! F7! | Bb6! Bb6! G7! G7! | Cm7! Cm7! F7! F7! | Fm7! Fm7! Bb7! Bb7! | Eb6! Eb6! Ebm6! Ebm6! | Cm7! Cm7! F7! F7! | Bb6! Bb6! F7! F7! |

Pattern %GtB:
  4: 4(D7!) | 4(D7!) | 4(G7!) | 4(G7!) | 4(C7!) | 4(C7!) | 4(F7!) | 4(F7!) |

Pattern %GtChorus:
  %GtA %GtA %GtB %GtA

Pattern %WalkA:
  4: bb*1 d*2 g*1 b*1 | c*2 eb*2 f*1 a*1 | bb*1 d*2 g*1 b*1 | c*2 eb*2 f*1 a*1 |
  f*1 ab*1 bb*1 d*2 | eb*2 g*2 eb*2 gb*1 | c*2 eb*2 f*1 a*1 | bb*1 d*2 f*2 f*1 |

Pattern %WalkB:
  4: d*2 f#*2 a*2 c*2 | d*2 a*1 f#*1 a*1 | g*1 b*1 d*2 f*2 | g*1 d*2 b*1 d*2 |
  c*2 e*2 g*2 bb*1 | c*2 g*1 e*1 g*1 | f*1 a*1 c*2 eb*2 | f*1 c*2 a*1 f*1 |

Pattern %WalkChorus:
  %WalkA %WalkA %WalkB %WalkA

Pattern %PadA:
  4: 2Bb6_ 2G7_ | 2Cm7_ 2F7_ | 2Bb6_ 2G7_ | 2Cm7_ 2F7_ | 2Fm7_ 2Bb7_ | 2Eb6_ 2Ebm6_ | 2Cm7_ 2F7_ | 2Bb6_ 2F7_ |

Pattern %PadB:
  4: 4D7_ | 4D7_ | 4G7_ | 4G7_ | 4C7_ | 4C7_ | 4F7_ | 4F7_ |

// ================================================================ il tema

Pattern %MelA:
  8:
  r d*5 2f*5 g*5 2f*5 d*5 |
  eb*5 d*5 c*5 2bb*4 r 2r |
  r d*5 2f*5 g*5 2f*5 d*5 |
  2eb*5 c*5 a*4 4f*4 |
  r ab*4 c*5 eb*5 2d*5 c*5 r |
  2g*5 f*5 eb*5 2gb*5 2r |
  f*5 eb*5 d*5 c*5 2a*4 2f*4 |
  4bb*4_ 4r |

Pattern %MelB:
  8:
  r f#*5 2a*5 c*6 2a*5 f#*5 |
  4d*5_ 4r |
  r b*4 2d*5 f*5 2d*5 b*4 |
  4g*4_ 4r |
  r e*5 2g*5 bb*5 2g*5 e*5 |
  4c*5_ 4r |
  a*4 c*5 eb*5 f*5 2a*5 2g*5 |
  2f*5 eb*5 c*5 4a*4 |

// lo shout chorus: accordi della band sul ritmo "charleston"
Pattern %ShoutA:
  8: 2Bb6 Bb6! r 2G7 G7! r | 2Cm7 Cm7! r 2F7 F7! r | 2Bb6 Bb6! r 2G7 G7! r | 2Cm7 Cm7! r 2F7 F7! r |
  2Fm7 Fm7! r 2Bb7 Bb7! r | 2Eb6 Eb6! r 2Ebm6 Ebm6! r | 2Cm7 Cm7! r 2F7 F7! r | 2Bb6 Bb6! r 2F7 F7! r |

// ================================================================ l'assolo del sax tenore (un giro AABA)

Pattern %SoloA1:
  8:
  2r f*3 g*3 bb*3 d*4 2f*4 |
  eb*4 d*4 c*4 a*3 bb*3 c*4 2d*4 |
  8T: f*4 g*4 f*4 d*4 bb*3 g*3 8: 2bb*3 2r |
  r c*4 eb*4 g*4 2f*4 eb*4 c*4 |
  ab*3 c*4 eb*4 f*4 ab*4 g*4 f*4 d*4 |
  2eb*4 g*4 bb*4 2gb*4 eb*4 r |
  16: f*4 g*4 f*4 eb*4 d*4 eb*4 d*4 c*4 8: a*3 c*4 2f*4 |
  4bb*3_ 4r |

Pattern %SoloA2:
  8:
  d*4 f*4 g*4 bb*4 2d*5 2bb*4 |
  c*5 bb*4 g*4 eb*4 2f*4 2r |
  16: bb*4 a*4 bb*4 d*5 bb*4 a*4 g*4 f*4 8: g*4 bb*4 2d*5 |
  c*5 a*4 f*4 eb*4 4c*4 |
  2r ab*4 f*4 d*4 2bb*3 r |
  eb*4 g*4 bb*4 c*5 2gb*4 2eb*4 |
  2f*4 a*4 c*5 eb*5 2c*5 a*4 |
  4bb*4_ 2r f*4 g*4 |

Pattern %SoloB:
  8:
  a*4 f#*4 d*4 a*3 c*4 d*4 f#*4 a*4 |
  2c*5 a*4 f#*4 4d*4 |
  g*4 b*4 d*5 f*4 2g*4 2r |
  8T: b*3 d*4 f*4 a*4 g*4 f*4 8: 2d*4 2b*3 |
  c*4 e*4 g*4 bb*4 2c*5 2bb*4 |
  16: g*4 bb*4 g*4 e*4 c*4 e*4 g*4 bb*4 8: 4c*5_ |
  a*4 f*4 eb*4 c*4 2a*3 2c*4 |
  eb*4 f*4 a*4 c*5 2eb*5 2c*5 |

Pattern %SoloA3:
  8:
  4d*5_ c*5 bb*4 2g*4 |
  2eb*4 g*4 bb*4 2a*4 2f*4 |
  8T: d*5 c*5 bb*4 g*4 f*4 d*4 8: 2f*4 2g*4 |
  eb*4 c*4 a*3 c*4 4f*4 |
  ab*4 g*4 f*4 d*4 2bb*3 2d*4 |
  2g*4 eb*4 c*4 2gb*4 2eb*4 |
  f*4 g*4 a*4 c*5 2eb*5 2c*5 |
  4bb*4_ 4r |

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  swing=66 %Swing %Swing %Swing %SwingFill

Box Batteria "Tema" |16:
  swing=66 %DrChorus

Box Batteria "Assolo di tenore" |144:
  swing=66 %SwingHat %SwingHat %SwingHat %SwingHat %SwingHat %SwingHat %SwingHat %SwingFill
  %DrA %DrB %DrA

Box Batteria "Shout chorus" |272:
  swing=66 7%Shout %SwingFill 7%Shout %SwingFill

Box Batteria "Ripresa" |336:
  swing=66 %DrA

Box Batteria "Finale" |368:
  swing=66 8: 112@ [crash kick] 3r 112@ [crash kick] 3r | 8: 100@ snare snare snare snare snare snare 110@ snare snare |
  118@ [crash kick] 7r | 8r |

Traccia Contrabbasso [Contrabbasso]:

Box Contrabbasso "Introduzione" |0:
  swing=66 4: 95@ f*1 a*1 c*2 eb*2 | f*1 a*1 c*2 eb*2 | f*1 a*1 c*2 eb*2 | f*1 c*2 a*1 f*1 |

Box Contrabbasso "Giri" |16:
  swing=66 4: 95@ %WalkChorus %WalkChorus %WalkA %WalkA %WalkA

Box Contrabbasso "Finale" |368:
  swing=66 4: 100@ bb*1 3r | bb*1 3r | bb*1 3r | 4bb*1$fermata |

Traccia Pianoforte [Piano]:

Box Pianoforte "Introduzione" |0:
  swing=66 4: 75@ r F7! r F7! | r F7! r F7! | r F7! r F7! | r F7! 2r |

Box Pianoforte "Giri" |16:
  swing=66 4: 72@ %CompChorus %CompChorus %CompA %CompA %CompA3

Box Pianoforte "Finale" |368:
  swing=66 4: 90@ Bb6! 3r | Bb6! 3r | 8: 85@ d*5 f*5 g*5 bb*5 d*6 f*6 g*6 bb*6 | 4: 4Bb6$fermata |

Traccia Chitarra [Ritmica]:

Box Chitarra "Introduzione" |0:
  swing=66 4: 80@ 4(F7!) | 4(F7!) | 4(F7!) | 4(F7!) |

Box Chitarra "Giri" |16:
  swing=66 4: 78@ %GtChorus %GtChorus %GtA %GtA %GtA

Box Chitarra "Finale" |368:
  swing=66 4: 85@ Bb6! 3r | Bb6! 3r | 4r | 4Bb6$fermata |

Traccia Contralto [Contralto]:

Box Contralto "Tema" |16:
  // i sax all'unisono nelle A, pausa nel ponte (lo fanno le trombe)
  swing=66 8: 100@ %MelA %MelA 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r | %MelA

Box Contralto "Sfondi" |208:
  // dietro l'ultima parte dell'assolo
  swing=66 4: 62@ 4d*5_ | 4eb*5_ | 4d*5_ | 4c*5_ | 4ab*4_ | 4g*4_ | 4eb*5_ | 4d*5_ |
  4f#*5_ | 4f#*5_ | 4f*5_ | 4f*5_ | 4e*5_ | 4e*5_ | 4eb*5_ | 4eb*5_ |

Box Contralto "Shout chorus" |272:
  swing=66 8: 112@ %MelA %MelA

Box Contralto "Ripresa" |336:
  swing=66 8: 100@ %MelA

Box Contralto "Finale" |368:
  swing=66 8: 110@ d*5 3r d*5 3r | 8r | 8r | 8d*5$fermata |

Traccia Tenore [Tenore]:

Box Tenore "Tema" |16:
  swing=66 8: 100@ %MelA-12 %MelA-12 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r | %MelA-12

Box Tenore "Assolo" |144:
  swing=66 8: 105@ %SoloA1 %SoloA2 %SoloB %SoloA3

Box Tenore "Shout chorus" |272:
  swing=66 8: 112@ %MelA-12 %MelA-12

Box Tenore "Ripresa" |336:
  swing=66 8: 100@ %MelA-12

Box Tenore "Finale" |368:
  swing=66 8: 110@ f*4 3r f*4 3r | 8r | 8r | 8f*4$fermata |

Traccia Baritono [Baritono]:

Box Baritono "Tema" |16:
  swing=66 4: 88@ %WalkA+12 %WalkA+12 %WalkB+12 %WalkA+12

Box Baritono "Shout chorus" |272:
  swing=66 4: 100@ %WalkA+12 %WalkA+12

Box Baritono "Ripresa" |336:
  swing=66 4: 92@ %WalkA+12

Box Baritono "Finale" |368:
  swing=66 4: 105@ bb*2 3r | bb*2 3r | 4r | 4bb*2$fermata |

Traccia Trombe [Trombe]:

Box Trombe "Introduzione" |0:
  swing=66 8: 110@ 2F7 F7! r 2F7 F7! r | 2F7 F7! r 2F7 F7! r | 2F7 F7! r 2F7 F7! r | 4F7_ 4r |

Box Trombe "Tema" |16:
  // colpi nelle A, la melodia nel ponte
  swing=66 8: 95@ 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r |
  8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r |
  105@ %MelB
  8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r |

Box Trombe "Shout chorus" |272:
  swing=66 8: 112@ %ShoutA %ShoutA

Box Trombe "Finale" |368:
  swing=66 8: 115@ Bb6! 3r Bb6! 3r | 8r | 8r | 8Bb6$fermata |

Traccia Tromboni [Tromboni]:

Box Tromboni "Introduzione" |0:
  swing=66 8: 105@ 2F7 F7! r 2F7 F7! r | 2F7 F7! r 2F7 F7! r | 2F7 F7! r 2F7 F7! r | 4F7_ 4r |

Box Tromboni "Tema" |16:
  // gli accordi lunghi sotto il ponte delle trombe
  swing=66 4: 70@ 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r |
  %PadB
  4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r |

Box Tromboni "Sfondi" |144:
  // gli sfondi dietro l'assolo di tenore
  swing=66 4: 58@ %PadA %PadA %PadB %PadA

Box Tromboni "Shout chorus" |272:
  swing=66 8: 108@ %ShoutA %ShoutA

Box Tromboni "Finale" |368:
  swing=66 8: 112@ Bb6! 3r Bb6! 3r | 8r | 8r | 8Bb6$fermata |

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/salamander-drums/ALL.sfz"

Plugin Contrabbasso:
  ref="sfz:~/Strumenti/sfz/contrabbasso/dsmolken_double_bass/d_smolken_rubner_bass_pizz.sfz"

Plugin Pianoforte:
  ref="sfz:~/Strumenti/sfz/piano/SalamanderGrandPiano-SFZ+FLAC-V3+20200602/SalamanderGrandPiano-V3+20200602.sfz"

Plugin Chitarra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Contralto:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Alto Sax.sfz"

Plugin Tenore:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Tenor Sax.sfz"

Plugin Baritono:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Baritone Sax.sfz"

Effetti Batteria:
  compressore: soglia=-18 rapporto=3 attacco=20 rilascio=150 guadagno=11
  riverbero: stanza=40 smorzamento=50 ampiezza=90 mix=12

Effetti Contrabbasso:
  compressore: soglia=-22 rapporto=3 attacco=15 rilascio=150 guadagno=6 preset="Basso"
  eq: bassi=2 medi=1 alti=-1

Effetti Pianoforte:
  compressore: soglia=-24 rapporto=2 attacco=20 rilascio=200 guadagno=9
  eq: bassi=-1 medi=0 alti=1
  riverbero: stanza=45 smorzamento=45 ampiezza=90 mix=14

Effetti Chitarra:
  nam: ingresso=0 cassa=2x12 livello=12 nam="../profili_nam/Fender Twin Reverb - pulito.nam"
  eq: bassi=3 medi=1 alti=-6
  riverbero: stanza=40 smorzamento=50 ampiezza=80 mix=10

Effetti Contralto:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=8
  riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=16

Effetti Tenore:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=8
  riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=16

Effetti Baritono:
  compressore: soglia=-20 rapporto=2 attacco=15 rilascio=150 guadagno=14
  riverbero: stanza=45 smorzamento=40 ampiezza=100 mix=12

Effetti Trombe:
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=16

Effetti Tromboni:
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=16

Catena master:
  plugin: mix=15 livello=0 ref="lv2:urn:ardour:a-reverb"
  compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=2 preset="Colla del mix"
  limiter: guadagno=3 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 95 pan: 0 mute: no solo: no

Mixer Contrabbasso:
  volume: 100 pan: 0.1 mute: no solo: no

Mixer Pianoforte:
  volume: 85 pan: -0.35 mute: no solo: no

Mixer Chitarra:
  volume: 80 pan: 0.45 mute: no solo: no

Mixer Contralto:
  volume: 100 pan: -0.25 mute: no solo: no

Mixer Tenore:
  volume: 105 pan: 0.05 mute: no solo: no

Mixer Baritono:
  volume: 92 pan: 0.25 mute: no solo: no

Mixer Trombe:
  volume: 80 pan: -0.15 mute: no solo: no

Mixer Tromboni:
  volume: 74 pan: 0.3 mute: no solo: no
