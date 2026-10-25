// Shuffle a Chicago - blues shuffle in La
//
// Il blues elettrico di Chicago anni '50: l'armonica suonata dentro un
// microfono e un amplificatore, il contrabbasso che
// cammina, il piano barrelhouse e la chitarra che tiene lo shuffle.
// Introduzione, quattro giri da 12 battute (il tema all'armonica, l'assolo
// di armonica, l'assolo di piano, di nuovo il tema) e il finale.
//
// Suoni:
// - batteria, contrabbasso, piano e chitarra sono SFZ (scarica_strumenti:
//   salamander-drums, contrabbasso, upright, chitarra-elettrica; in
//   ~/Strumenti), l'armonica e' quella del SoundFont GM;
// - l'armonica passa per il profilo NAM di un Vox AC15 con il combo 1x12 e
//   un'eco "slapback" corta, come nei vecchi dischi; la chitarra ritmica per
//   il profilo di un Fender Twin (Suoni -> Scarica -> profili NAM consigliati);
// - sul master il nastro del Calf Tape Simulator (plugin LV2: senza, il
//   suono passa invariato), poi compressore e limiter.

ST: 2.6
Tempo: 108 BPM
Metrica: 4/4
Tonalita: A

Strumento Armonica:
  program=22 percussione=no ottava=4 range=55-96 poly=no voicing=monophonic

Strumento Ritmica:
  program=27 percussione=no ottava=3 range=40-84 poly=si voicing=spread

Strumento Contrabbasso:
  program=32 percussione=no ottava=2 range=28-60 poly=no voicing=root_fifth

// ---------------------------------------------------------------- batteria

Pattern %Shuffle:
  8: 100@ [kick hihat] 52@ hihat 100@ [snare hihat] 52@ hihat 95@ [kick hihat] 52@ hihat 100@ [snare hihat] 62@ [kick hihat] |

Pattern %ShuffleCrash:
  8: 112@ [kick crash] 52@ hihat 100@ [snare hihat] 52@ hihat 95@ [kick hihat] 52@ hihat 100@ [snare hihat] 62@ [kick hihat] |

Pattern %ShuffleRide:
  8: 92@ [kick ride] 50@ ride 95@ [snare ride] 50@ ride 90@ [kick ride] 50@ ride 95@ [snare ride] 58@ [kick ride] |

Pattern %FillA:
  8: 100@ [kick hihat] 52@ hihat 100@ [snare hihat] 52@ hihat 95@ snare snare 105@ tom1 floor |

Pattern %FillB:
  8: 100@ [kick hihat] 100@ snare 105@ snare 100@ tom1 tom2 floor 112@ [kick floor] 92@ snare |

Pattern %DrChorus:
  %ShuffleCrash %Shuffle %Shuffle %Shuffle %Shuffle %Shuffle %Shuffle %FillA %Shuffle %Shuffle %Shuffle %FillB

Pattern %DrChorusRide:
  %ShuffleCrash %ShuffleRide %ShuffleRide %ShuffleRide %ShuffleRide %ShuffleRide %ShuffleRide %FillA %ShuffleRide %ShuffleRide %ShuffleRide %FillB

// ---------------------------------------------------------------- contrabbasso (walking)

Pattern %BsA1:
  4: 95@ a*1 c#*2 e*2 f#*2 |

Pattern %BsA2:
  4: 92@ a*1 e*2 g*2 e*2 |

Pattern %BsD1:
  4: 95@ d*2 f#*2 a*2 b*2 |

Pattern %BsD2:
  4: 92@ d*2 a*2 c*3 a*2 |

Pattern %BsE:
  4: 95@ e*2 g#*2 b*2 c#*3 |

Pattern %BsAD:
  4: 95@ a*1 c#*2 d*2 f#*2 |

Pattern %BsTurn:
  4: 98@ e*2 d*2 c#*2 b*1 |

Pattern %BsChorus:
  %BsA1 %BsD1 %BsA2 %BsA1 %BsD2 %BsD1 %BsA2 %BsA1 %BsE %BsD2 %BsAD %BsTurn

// ---------------------------------------------------------------- chitarra ritmica (shuffle a due corde)

Pattern %GA:
  8: 85@ [a*2 e*3] [a*2 e*3] [a*2 f#*3] [a*2 f#*3] [a*2 g*3] [a*2 g*3] [a*2 f#*3] [a*2 f#*3] |

Pattern %GD:
  8: 85@ [d*3 a*3] [d*3 a*3] [d*3 b*3] [d*3 b*3] [d*3 c*4] [d*3 c*4] [d*3 b*3] [d*3 b*3] |

Pattern %GE:
  8: 85@ [e*3 b*3] [e*3 b*3] [e*3 c#*4] [e*3 c#*4] [e*3 d*4] [e*3 d*4] [e*3 c#*4] [e*3 c#*4] |

Pattern %GAD:
  8: 85@ [a*2 e*3] [a*2 e*3] [a*2 f#*3] [a*2 f#*3] [d*3 a*3] [d*3 a*3] [d*3 b*3] [d*3 b*3] |

Pattern %GChorus:
  %GA %GD %GA %GA %GD %GD %GA %GA %GE %GD %GAD %GE

// ---------------------------------------------------------------- piano (accordi sul 2 e sul 4)

Pattern %CompA:
  4: 74@ r A7! r A7! |

Pattern %CompD:
  4: 74@ r D9! r D9! |

Pattern %CompE:
  4: 76@ r E9! r E9! |

Pattern %CompAD:
  4: 74@ r A7! r D9! |

Pattern %CompChorus:
  %CompA %CompD %CompA %CompA %CompD %CompD %CompA %CompA %CompE %CompD %CompAD %CompE

Pattern %PianoSolo:
  8: 100@
  e*5 2g*5 e*5 c*5 2a*4 r |
  d*5 f#*5 2a*5 f#*5 d*5 2c*5 |
  a*4 c*5 d*5 d#*5 2e*5 e*5 r |
  4e*5 g*5 e*5 2c*5 |
  a*5 2f#*5 d*5 2c*5 a*4 r |
  d*5 f#*5 a*5 c*6 2a*5 f#*5 r |
  e*5 e*5 g*5 a*5 2c*6 a*5 e*5 |
  4a*5 2e*5 c*5 a*4 |
  b*5 d*6 2e*6 d*6 b*5 2g#*5 |
  a*5 c*6 2d*6 c*6 a*5 2f#*5 |
  e*5 g*5 a*5 c*6 4e*6 |
  2b*5 g#*5 e*5 d*5 b*4 2e*4 |

// ---------------------------------------------------------------- armonica: il tema

Pattern %HarpHead:
  8: 100@
  2r e*4 g*4 a*4>2c*5 a*4 |
  4c*5_ 2a*4 2r |
  r a*4 c*5 d*5 eb*5>2e*5 c*5 |
  2a*4 g*4 e*4 4a*4 |
  2r d*5 f#*4 a*4>2c*5 a*4 |
  4c*5_ a*4 f#*4 2d*4 |
  r e*5 d*5 c*5 2a*4 2c*5 |
  2a*4 g*4 e*4 4a*4 |
  2r b*4 d*5 e*5>2f#*5 e*5 |
  d*5 c*5 a*4 f#*4 4a*4 |
  e*4 g*4 a*4 c*5 c*5>2d*5 c*5 |
  a*4 g*4 e*4 c#*4 2e*4 2r |

// ---------------------------------------------------------------- armonica: l'assolo

Pattern %HarpSolo:
  8: 110@
  8T: e*5 g*5 a*5 e*5 g*5 a*5 8: 4a*5_ |
  c*6 a*5 g*5 f#*5 2e*5 2d*5 |
  eb*5>2e*5 c*5 a*4 c*5 2e*5 |
  8T: g*5 e*5 c*5 a*4 c*5 e*5 8: 4a*4 |
  2r a*5 c*6 d*6>2c*6 a*5 |
  f#*5 a*5 f#*5 d*5 4c*5_ |
  8T: a*5 g*5 e*5 a*5 g*5 e*5 a*5 g*5 e*5 8: 2c*5 |
  4a*4_ 4r |
  b*5 d*6 2e*6_ d*6 b*5 2g#*5 |
  a*5 c*6 2d*6 c*6 a*5 2f#*5 |
  e*5 g*5 a*5 c*6 4a*5 |
  2b*4 g#*4 e*4 d*4 b*3 2e*4 |

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  swing=66 %ShuffleCrash %Shuffle %Shuffle %FillB

Box Batteria "Tema" |16:
  swing=66 %DrChorus

Box Batteria "Assolo di armonica" |64:
  swing=66 %DrChorus

Box Batteria "Assolo di piano" |112:
  swing=66 vol=85 %DrChorusRide

Box Batteria "Tema finale" |160:
  swing=66 vol=100 %DrChorus

Box Batteria "Finale" |208:
  swing=66 8: 110@ [kick crash] 52@ hihat 100@ [snare hihat] 52@ hihat 105@ snare tom1 tom2 floor |
  100@ snare 102@ snare 104@ snare 106@ snare 108@ snare 110@ snare 112@ snare 120@ [kick crash] |

Traccia Contrabbasso [Contrabbasso]:

Box Contrabbasso "Introduzione" |0:
  swing=66 %BsE %BsD2 %BsA1 %BsTurn

Box Contrabbasso "Giri" |16:
  swing=66 4%BsChorus

Box Contrabbasso "Finale" |208:
  swing=66 4: 98@ a*1 c#*2 e*2 g*2 | 4: 100@ 3a*1 r |

Traccia Piano [Piano]:

Box Piano "Introduzione" |0:
  swing=66 %CompE %CompD %CompA %CompE

Box Piano "Tema" |16:
  swing=66 %CompChorus

Box Piano "Assolo di armonica" |64:
  swing=66 %CompChorus

Box Piano "Assolo di piano" |112:
  swing=66 %PianoSolo

Box Piano "Tema finale" |160:
  swing=66 %CompChorus

Box Piano "Finale" |208:
  swing=66 4: 80@ r A7! r A7! | 1: 92@ A9$fermata |

Traccia Ritmica [Ritmica]:

Box Ritmica "Introduzione" |0:
  swing=66 %GE %GD %GA %GE

Box Ritmica "Giri" |16:
  swing=66 vol=100 %GChorus %GChorus vol=80 %GChorus vol=100 %GChorus

Box Ritmica "Finale" |208:
  swing=66 %GA 8: 90@ [a*2 e*3 a*3 c#*4]'1 |

Traccia Armonica [Armonica]:

Box Armonica "Introduzione" |0:
  // la frase d'attacco sul giro finale
  swing=66 8: 100@ 2r b*4 d*5 e*5>2f#*5 e*5 |
  d*5 c*5 a*4 f#*4 4a*4 |
  e*4 g*4 a*4 c*5 c*5>2d*5 c*5 |
  a*4 g*4 e*4 c#*4 2e*4 2r |

Box Armonica "Tema" |16:
  swing=66 %HarpHead

Box Armonica "Assolo" |64:
  swing=66 %HarpSolo

Box Armonica "Tema finale" |160:
  swing=66 %HarpHead

Box Armonica "Finale" |208:
  swing=66 8: 110@ e*4 g*4 a*4 c*5 eb*5>2e*5 r | 8a*5$fermata |

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/salamander-drums/ALL.sfz"

Plugin Contrabbasso:
  ref="sfz:~/Strumenti/sfz/contrabbasso/dsmolken_double_bass/d_smolken_rubner_bass_pizz.sfz"

Plugin Piano:
  ref="sfz:~/Strumenti/sfz/upright/UprightPianoKW-small-SFZ+FLAC-20190703/UprightPianoKW-small-20190703.sfz"

Plugin Ritmica:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Effetti Batteria:
  compressore: soglia=-16 rapporto=3 attacco=15 rilascio=150 guadagno=12 preset="Batteria"
  riverbero: stanza=30 smorzamento=55 ampiezza=70 mix=10
  volume: guadagno=2

Effetti Contrabbasso:
  compressore: soglia=-20 rapporto=3 attacco=20 rilascio=150 guadagno=7 preset="Basso"
  eq: bassi=2 medi=1 alti=-2

Effetti Piano:
  eq: bassi=-2 medi=1 alti=2
  riverbero: stanza=40 smorzamento=50 ampiezza=80 mix=14

Effetti Ritmica:
  nam: ingresso=3 cassa=2x12 livello=12 nam="../profili_nam/Fender Twin Reverb - pulito.nam"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=12
  passa_alto: frequenza=110 pendenza=12

Effetti Armonica:
  passa_alto: frequenza=180 pendenza=12
  nam: ingresso=6 cassa=combo_1x12 livello=-5 nam="../profili_nam/Vox AC15 - Top Boost.nam"
  delay: suddivisione=libera tempo=110 ripetizioni=15 mix=18 preset="Slapback"
  riverbero: stanza=30 smorzamento=50 ampiezza=70 mix=12

Catena master:
  volume: guadagno=-7
  plugin: mix=60 livello=0 ref="lv2:http://calf.sourceforge.net/plugins/TapeSimulator" p.level_in=0.5 p.level_out=1 p.lowpass=11000 p.speed=1 p.noise=0.03 p.mechanical=0.15 p.magnetical=0.8
  compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 95 pan: 0 mute: no solo: no

Mixer Contrabbasso:
  volume: 105 pan: -0.1 mute: no solo: no

Mixer Piano:
  volume: 88 pan: -0.4 mute: no solo: no

Mixer Ritmica:
  volume: 80 pan: 0.45 mute: no solo: no

Mixer Armonica:
  volume: 110 pan: 0.05 mute: no solo: no
