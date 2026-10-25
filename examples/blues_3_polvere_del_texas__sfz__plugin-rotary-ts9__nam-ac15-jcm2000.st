// Polvere del Texas - Texas shuffle in Mi
//
// Il blues texano: shuffle veloce, la ritmica che
// martella le corde basse, l'Hammond con il Leslie e una chitarra solista
// spinta da un Tube Screamer dentro un Marshall. Introduzione, cinque giri
// da 12 battute (tema, primo assolo, assolo d'organo, secondo assolo al
// culmine, tema) e il finale.
//
// Suoni:
// - batteria, basso e chitarre SFZ (scarica_strumenti: batteria,
//   basso-plettro, chitarra-elettrica; in ~/Strumenti), l'Hammond del
//   SoundFont GM;
// - chitarra solista: GxTubeScreamer (plugin LV2) e il profilo NAM del
//   Marshall JCM2000 crunch con la 4x12; chitarra ritmica: il Vox AC15
//   (profili con Suoni -> Scarica -> profili NAM consigliati);
// - organo: il Leslie del Calf Rotary Speaker, a velocita' alta;
// - master: EQ, compressore e limiter.

ST: 2.6
Tempo: 132 BPM
Metrica: 4/4
Tonalita: E

Strumento Solista:
  program=29 percussione=no ottava=4 range=40-90 poly=no voicing=monophonic

Strumento Ritmica:
  program=27 percussione=no ottava=3 range=40-84 poly=si voicing=spread

Strumento Hammond:
  program=16 percussione=no ottava=4 range=36-96 poly=si voicing=spread

// ---------------------------------------------------------------- batteria

Pattern %Shuffle:
  8: 102@ [kick hihat] 55@ hihat 108@ [snare hihat] 55@ hihat 98@ [kick hihat] 55@ hihat 108@ [snare hihat] 65@ [kick hihat] |

Pattern %ShuffleCrash:
  8: 115@ [kick crash] 55@ hihat 108@ [snare hihat] 55@ hihat 98@ [kick hihat] 55@ hihat 108@ [snare hihat] 65@ [kick hihat] |

Pattern %ShuffleRide:
  8: 100@ [kick ride] 55@ ride 108@ [snare ride] 55@ ride 98@ [kick ride] 55@ ride 108@ [snare ride] 62@ [kick ride] |

Pattern %Fill:
  8: 102@ [kick hihat] 55@ hihat 108@ [snare hihat] 55@ hihat 100@ snare 104@ snare 108@ tom1 112@ floor |

Pattern %FillBig:
  8: 105@ [kick hihat] 100@ snare 104@ snare 106@ tom1 108@ tom2 110@ floor 115@ [kick floor] 100@ snare |

Pattern %DrChorus:
  %ShuffleCrash %Shuffle %Shuffle %Shuffle %Shuffle %Shuffle %Shuffle %Fill %Shuffle %Shuffle %Shuffle %FillBig

Pattern %DrChorusRide:
  %ShuffleCrash %ShuffleRide %ShuffleRide %ShuffleRide %ShuffleRide %ShuffleRide %ShuffleRide %Fill %ShuffleRide %ShuffleRide %ShuffleRide %FillBig

// ---------------------------------------------------------------- basso (boogie)

Pattern %BsE:
  8: 100@ e*1 e*1 g#*1 g#*1 b*1 b*1 c#*2 b*1 |

Pattern %BsA:
  8: 100@ a*1 a*1 c#*2 c#*2 e*2 e*2 f#*2 e*2 |

Pattern %BsB:
  8: 100@ b*1 b*1 d#*2 d#*2 f#*2 f#*2 g#*2 f#*2 |

Pattern %BsEA:
  8: 100@ e*1 e*1 g#*1 b*1 a*1 a*1 c#*2 e*2 |

Pattern %BsEB:
  8: 100@ e*1 e*1 g#*1 b*1 b*1 b*1 a*1 f#*1 |

Pattern %BsChorus:
  %BsE %BsA %BsE %BsE %BsA %BsA %BsE %BsE %BsB %BsA %BsEA %BsEB

// ---------------------------------------------------------------- chitarra ritmica (shuffle sulle corde basse)

Pattern %GE:
  8: 92@ [e*2 b*2] [e*2 b*2] [e*2 c#*3] [e*2 c#*3] [e*2 d*3] [e*2 d*3] [e*2 c#*3] [e*2 c#*3] |

Pattern %GA:
  8: 92@ [a*2 e*3] [a*2 e*3] [a*2 f#*3] [a*2 f#*3] [a*2 g*3] [a*2 g*3] [a*2 f#*3] [a*2 f#*3] |

Pattern %GB:
  8: 92@ [b*2 f#*3] [b*2 f#*3] [b*2 g#*3] [b*2 g#*3] [b*2 a*3] [b*2 a*3] [b*2 g#*3] [b*2 g#*3] |

Pattern %GEA:
  8: 92@ [e*2 b*2] [e*2 b*2] [e*2 c#*3] [e*2 c#*3] [a*2 e*3] [a*2 e*3] [a*2 f#*3] [a*2 f#*3] |

Pattern %GEB:
  8: 92@ [e*2 b*2] [e*2 b*2] [e*2 c#*3] [e*2 c#*3] [b*2 f#*3] [b*2 f#*3] [b*2 a*3] [b*2 a*3] |

Pattern %GChorus:
  %GE %GA %GE %GE %GA %GA %GE %GE %GB %GA %GEA %GEB

// ---------------------------------------------------------------- Hammond: accompagnamento

Pattern %OrE:
  8: 62@ 3E9_ E9! 2r E9! E9! |

Pattern %OrA:
  8: 62@ 3A9_ A9! 2r A9! A9! |

Pattern %OrB:
  8: 64@ 3B9_ B9! 2r B9! B9! |

Pattern %OrEA:
  8: 62@ 3E9_ E9! 2A9_ A9! A9! |

Pattern %OrEB:
  8: 62@ 3E9_ E9! 2B9_ B9! B9! |

Pattern %OrChorus:
  %OrE %OrA %OrE %OrE %OrA %OrA %OrE %OrE %OrB %OrA %OrEA %OrEB

Pattern %OrSolo:
  8: 102@
  2b*4 e*5 g*5 2a*5 g*5 e*5 |
  4a*5_ g*5 e*5 2c#*5 |
  b*4 d*5 e*5 g*5 2b*5 2g*5 |
  8e*5 |
  e*5 a*5 c#*6 e*6 4d*6 |
  c#*6 a*5 2g*5 4e*5 |
  8T: b*5 g*5 e*5 b*5 g*5 e*5 b*5 g*5 e*5 8: 2d*5 |
  4e*5 4r |
  4B7_ 2B7! 2r |
  4A7_ 2A7! 2r |
  e*5 g*5 a*5 b*5 d*6 e*6 2g*6 |
  4e*6_ 2d*6 2b*5 |

// ---------------------------------------------------------------- chitarra solista

Pattern %Head:
  8: 105@
  2r g*4>2g#*4 b*4 d*5 e*5 |
  g*5>2a*5 g*5 e*5 d*5 2e*5 |
  d*5 b*4 g*4 e*4 g*4>2g#*4 e*4 |
  4e*4_ 4r |
  2r a*4 c#*5 e*5 g*5>2a*5 |
  g*5 e*5 c#*5 a*4 4e*5 |
  2r e*5 g*5 a*5 a#*5>2b*5 |
  a*5 g*5 e*5 d*5 4e*5 |
  2r d#*5 f#*5 a*5 a*5>2b*5 |
  a*5 g*5 e*5 c#*5 4a*4 |
  e*4 g*4 g#*4 b*4 c#*5 e*5 2g*5 |
  g*5>2g#*5 f#*5 d#*5 b*4 2a*4 |

Pattern %Solo1:
  8: 110@
  8T: b*4 d*5 e*5 g*5 e*5 d*5 8: g*5>2a*5 b*5 |
  c#*6>d*6>2c#*6 a*5 g*5 2e*5 |
  8T: e*6 d*6 b*5 d*6 b*5 a*5 g*5 a*5 g*5 e*5 g*5 e*5 8: |
  d*5 e*5 g*5>2g#*5 e*5 2b*4 |
  a*5 c#*6 e*6 2g*6 e*6 c#*6 a*5 |
  g*5>2a*5 g*5>2a*5 g*5 e*5 |
  16: e*6 d*6 b*5 g*5 e*6 d*6 b*5 g*5 e*6 d*6 b*5 g*5 8: 2e*5 |
  4e*5_ 4r |
  b*5>2c#*6 b*5 a*5 f#*5 2d#*5 |
  c#*6 a*5 g*5 e*5 2c#*5 2a*4 |
  e*5 g*5 g#*5 b*5 4e*6_ |
  d*6 b*5 a*5 f#*5 d#*5 b*4 2r |

Pattern %Solo2:
  8: 116@
  4g*5>4a*5 |
  g*5 e*5 d*5 e*5 g*5>2a*5 g*5 |
  16: b*5 d*6 e*6 g*6 e*6 d*6 b*5 d*6 b*5 a*5 g*5 e*5 8: 2g#*5 |
  e*6>2f#*6 e*6>2f#*6 2e*6 |
  2r a*5 c#*6 e*6 g*6>2a*6 |
  8T: g*6 e*6 c#*6 g*6 e*6 c#*6 8: 4a*5 |
  16: e*6 e*6 d*6 b*5 e*6 e*6 d*6 b*5 e*6 e*6 d*6 b*5 e*6 e*6 d*6 b*5 |
  8: g*6>2g#*6 e*6 b*5 g*5 2e*5 |
  f#*6>2g#*6 f#*6 d#*6 b*5 2a*5 |
  g*5 a*5 c#*6 e*6 4a*6_ |
  b*5 g*5 e*5 d*5 b*4 g*4 2e*4 |
  g*4>2g#*4 b*4 d*5 e*5 2r |

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  swing=66 %ShuffleCrash %Shuffle %Shuffle %Fill

Box Batteria "Tema" |16:
  swing=66 %DrChorus

Box Batteria "Primo assolo" |64:
  swing=66 %DrChorus

Box Batteria "Assolo d'organo" |112:
  swing=66 %DrChorusRide

Box Batteria "Secondo assolo" |160:
  swing=66 %DrChorus

Box Batteria "Tema finale" |208:
  swing=66 %DrChorus

Box Batteria "Finale" |256:
  swing=66 8: 118@ [kick crash] 3r 115@ [kick crash] 3r |
  105@ snare 106@ snare 108@ tom1 110@ tom1 112@ tom2 114@ floor 120@ [kick crash] r |

Traccia Basso [Bass]:

Box Basso "Introduzione" |0:
  swing=66 %BsE %BsE %BsE %BsB

Box Basso "Giri" |16:
  swing=66 5%BsChorus

Box Basso "Finale" |256:
  swing=66 8: 110@ e*1 3r e*1 3r | 6r 2e*1 |

Traccia Ritmica [Ritmica]:

Box Ritmica "Introduzione" |0:
  swing=66 %GE %GE %GE %GB

Box Ritmica "Giri" |16:
  swing=66 vol=100 %GChorus %GChorus vol=85 %GChorus vol=100 %GChorus %GChorus

Box Ritmica "Finale" |256:
  swing=66 8: 100@ [e*2 b*2 e*3 g#*3] 3r [e*2 b*2 e*3 g#*3] 3r | 6r 2[e*2 b*2 e*3 g#*3] |

Traccia Organo [Hammond]:

Box Organo "Introduzione" |0:
  swing=66 %OrE %OrE %OrE %OrB

Box Organo "Tema" |16:
  swing=66 %OrChorus

Box Organo "Primo assolo" |64:
  swing=66 vol=85 %OrChorus

Box Organo "Assolo d'organo" |112:
  swing=66 vol=100 %OrSolo

Box Organo "Secondo assolo" |160:
  swing=66 vol=85 %OrChorus

Box Organo "Tema finale" |208:
  swing=66 vol=100 %OrChorus

Box Organo "Finale" |256:
  swing=66 8: 100@ E9! 3r E9! 3r | 6r 2E9$fermata |

Traccia Chitarra [Solista]:

Box Chitarra "Introduzione" |0:
  swing=66 8: 4r 4r | 8r | 8r | 105@ 2r g*4>2g#*4 b*4 d*5 e*5 |

Box Chitarra "Tema" |16:
  swing=66 %Head

Box Chitarra "Primo assolo" |64:
  // gli assoli un'ottava sotto: la chitarra campionata arriva al Re6
  swing=66 %Solo1-12

Box Chitarra "Secondo assolo" |160:
  swing=66 %Solo2-12

Box Chitarra "Tema finale" |208:
  swing=66 %Head

Box Chitarra "Finale" |256:
  swing=66 8: 118@ e*5 3r e*5 3r | 116@ 6r 2e*4>g#*4 |

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/batteria/MuldjordKit SFZ+FLAC-20201018/MuldjordKit 20201018-GM.sfz"

Plugin Basso:
  ref="sfz:~/Strumenti/sfz/basso-plettro/PickedBassYR SFZ+FLAC-20190930/PickedBassYR 20190930.sfz"

Plugin Ritmica:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Chitarra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Effetti Batteria:
  compressore: soglia=-16 rapporto=3 attacco=15 rilascio=150 guadagno=7 preset="Batteria"
  riverbero: stanza=30 smorzamento=50 ampiezza=80 mix=10
  volume: guadagno=2

Effetti Basso:
  compressore: soglia=-20 rapporto=4 attacco=15 rilascio=120 guadagno=3 preset="Basso"
  eq: bassi=2 medi=1 alti=0

Effetti Ritmica:
  nam: ingresso=0 cassa=combo_1x12 livello=-13 nam="../profili_nam/Vox AC15 - Top Boost.nam"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=10
  passa_alto: frequenza=110 pendenza=12

Effetti Organo:
  plugin: mix=100 livello=8 ref="lv2:http://calf.sourceforge.net/plugins/RotarySpeaker" p.vib_speed=2 p.level_out=1
  riverbero: stanza=45 smorzamento=40 ampiezza=100 mix=14

Effetti Chitarra:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.5 p.fslider1_=700 p.fslider0_=-4
  nam: ingresso=2 cassa=4x12 livello=-4 nam="../profili_nam/Marshall JCM2000 - crunch.nam"
  delay: suddivisione=libera tempo=95 ripetizioni=10 mix=12 preset="Slapback"
  riverbero: stanza=50 smorzamento=45 ampiezza=100 mix=16
  passa_alto: frequenza=160 pendenza=12

Catena master:
  volume: guadagno=-5.5
  eq: bassi=1 medi=0 alti=1
  compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 95 pan: 0 mute: no solo: no

Mixer Basso:
  volume: 100 pan: 0 mute: no solo: no

Mixer Ritmica:
  volume: 85 pan: -0.55 mute: no solo: no

Mixer Organo:
  volume: 75 pan: 0.5 mute: no solo: no

Mixer Chitarra:
  volume: 110 pan: 0.1 mute: no solo: no
