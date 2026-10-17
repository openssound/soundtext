// Pioggia su Memphis - blues minore soul in La minore
//
// Un blues minore lento e "pieno", alla The Thrill Is Gone: groove in
// sedicesimi, Rhodes con il phaser, gli archi che entrano piano e crescono,
// la chitarra che canta il tema, il sax tenore che risponde con l'assolo,
// poi l'ultimo giro con l'assolo di chitarra sopra gli archi al culmine.
//
// Suoni:
// - batteria, basso, Rhodes, sax e chitarra SFZ (scarica_strumenti:
//   salamander-drums, pastabass, rhodes, solosax, chitarra-elettrica; in
//   ~/Strumenti), gli archi del SoundFont GM;
// - Rhodes nel Calf Phaser (plugin LV2: senza, il suono passa invariato);
// - chitarra nel profilo NAM del Bugera 333 "crunch con cassa" (la cassa e'
//   gia' nel profilo), poi eco puntata e riverbero;
// - master: EQ, compressore e limiter.

ST: 2.6
Tempo: 84 BPM
Metrica: 4/4
Tonalita: Am

Strumento Rhodes:
  program=4 percussione=no ottava=4 range=28-103 poly=si voicing=spread

Strumento Tenore:
  program=66 percussione=no ottava=3 range=44-77 poly=no voicing=monophonic

Strumento Solista:
  program=27 percussione=no ottava=4 range=40-90 poly=no voicing=monophonic

Strumento Archi:
  program=48 percussione=no ottava=4 range=36-96 poly=si voicing=spread

// ---------------------------------------------------------------- batteria (sedicesimi)

Pattern %Groove:
  16: 95@ [kick hihat] 42@ hihat 60@ hihat 42@ hihat 100@ [snare hihat] 42@ hihat 60@ hihat 70@ kick 85@ [kick hihat] 42@ hihat 60@ hihat 42@ hihat 100@ [snare hihat] 42@ hihat 60@ hihat 42@ hihat |

Pattern %GrooveCrash:
  16: 108@ [kick crash] 42@ hihat 60@ hihat 42@ hihat 100@ [snare hihat] 42@ hihat 60@ hihat 70@ kick 85@ [kick hihat] 42@ hihat 60@ hihat 42@ hihat 100@ [snare hihat] 42@ hihat 60@ hihat 42@ hihat |

Pattern %GrooveRide:
  16: 98@ [kick ride] 48@ ride 62@ ride 48@ ride 104@ [snare ride] 48@ ride 62@ ride 72@ kick 88@ [kick ride] 48@ ride 62@ ride 48@ ride 104@ [snare ride] 48@ ride 62@ ride 48@ ride |

Pattern %Fill:
  16: 95@ [kick hihat] 42@ hihat 60@ hihat 42@ hihat 100@ [snare hihat] 42@ hihat 60@ hihat 70@ kick 90@ snare 70@ snare 95@ snare 75@ snare 100@ tom1 95@ tom1 105@ floor 110@ floor |

Pattern %DrChorus:
  %GrooveCrash %Groove %Groove %Groove %Groove %Groove %Groove %Fill %Groove %Groove %Groove %Fill

Pattern %DrChorusRide:
  %GrooveCrash %GrooveRide %GrooveRide %GrooveRide %GrooveRide %GrooveRide %GrooveRide %Fill %GrooveRide %GrooveRide %GrooveRide %Fill

// ---------------------------------------------------------------- basso

Pattern %BsAm:
  16: 100@ 3a*1 a*1 2r 2e*2 3a*1 a*1 2c*2 2e*2 |

Pattern %BsDm:
  16: 100@ 3d*2 d*2 2r 2a*2 3d*2 d*2 2f*2 2a*2 |

Pattern %BsF:
  16: 100@ 3f*2 f*2 2r 2c*2 3f*2 f*2 2eb*2 2c*2 |

Pattern %BsE:
  16: 100@ 3e*2 e*2 2r 2b*1 3e*2 e*2 2g#*2 2b*1 |

Pattern %BsChorus:
  %BsAm %BsAm %BsAm %BsAm %BsDm %BsDm %BsAm %BsAm %BsF %BsE %BsAm %BsE

// ---------------------------------------------------------------- Rhodes

Pattern %RhAm:
  16: 60@ 6Am9_ 2Am9! 4r 2Am9! 2Am9! |

Pattern %RhDm:
  16: 60@ 6Dm9_ 2Dm9! 4r 2Dm9! 2Dm9! |

Pattern %RhF:
  16: 60@ 6F9_ 2F9! 4r 2F9! 2F9! |

Pattern %RhE:
  16: 64@ 6E7#9_ 2E7#9! 4r 2E7#9! 2E7#9! |

Pattern %RhChorus:
  %RhAm %RhAm %RhAm %RhAm %RhDm %RhDm %RhAm %RhAm %RhF %RhE %RhAm %RhE

// ---------------------------------------------------------------- archi (tappeto)

Pattern %StChorus:
  4: 4Am_ | 4Am_ | 4Am_ | 4Am_ | 4Dm_ | 4Dm_ | 4Am_ | 4Am_ | 4F_ | 4E7_ | 4Am_ | 4E7_ |

// ---------------------------------------------------------------- chitarra: il tema

Pattern %Theme:
  8: 100@
  2r e*5 c*5 a*4>2c*5 r |
  a*4 g*4 2a*4_ 4r |
  2r c*5 d*5 e*5 g*5>2a*5 |
  g*5 e*5 d*5 c*5 4a*4 |
  2r f*5 d*5 c*5>2d*5 r |
  c*5 a*4 2d*4_ 4r |
  2r e*5 g*5 a*5 c*6>2d*6 |
  c*6 a*5 g*5 e*5 4a*5 |
  2r f*5 a*5 c*6>2eb*6 r |
  d*6 b*5 g#*5 e*5 4e*5 |
  c*5 d*5 e*5 g*5 4a*5_ |
  g#*5 f*5 e*5 d*5 b*4 g#*4 2e*4 |

// ---------------------------------------------------------------- sax tenore: l'assolo

Pattern %SaxSolo:
  8: 100@
  2r a*3 c*4 d*4 e*4 2g*4 |
  a*4 g*4 e*4 d*4 4c*4_ |
  8T: e*4 g*4 a*4 c*5 a*4 g*4 8: e*4 d*4 2c*4 |
  4a*3_ 4r |
  2r d*4 f*4 a*4 c*5 2d*5 |
  c*5 a*4 f*4 d*4 4f*4_ |
  e*4 g*4 a*4 b*4 c*5 d*5 2e*5 |
  16: e*5 d*5 c*5 a*4 e*5 d*5 c*5 a*4 8: 4a*4 |
  2r c*5 eb*5 d*5 eb*5 2c*5 |
  b*4 g#*4 e*4 d*4 4e*4 |
  a*3 c*4 e*4 a*4 c*5 e*5 2a*4 |
  g#*4 b*4 d*5 e*5 4g#*4 |

// ---------------------------------------------------------------- chitarra: l'assolo finale

Pattern %GtSolo:
  8: 110@
  4d*5>4e*5 |
  c*5 a*4 c*5 e*5 d*5>2e*5 c*5 |
  16: a*5 g*5 e*5 d*5 a*5 g*5 e*5 d*5 8: c*5 d*5 2e*5 |
  4a*4_ 2r c*5 e*5 |
  g*5>2a*5 g*5 f*5 d*5 2c*5 |
  d*5 f*5 a*5 c*6 4d*6_ |
  c*6>d*6>2c*6 a*5 g*5 2e*5 |
  8T: c*6 a*5 g*5 e*5 d*5 c*5 8: 4a*4 |
  2r f*5 a*5 c*6>2eb*6 r |
  d*6 b*5 g#*5 e*5 2d*5 2b*4 |
  c*5 e*5 a*5 b*5 4c*6_ |
  d*6 b*5 g#*5 e*5 2d*5 2b*4 |

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  %Groove %Groove %Groove %Fill

Box Batteria "Tema" |16:
  %DrChorus

Box Batteria "Assolo di sax" |64:
  %DrChorusRide

Box Batteria "Assolo di chitarra" |112:
  %DrChorus

Box Batteria "Finale" |160:
  16: 110@ [kick crash] 15r | 16r |

Traccia Basso [Bass]:

Box Basso "Introduzione" |0:
  %BsAm %BsAm %BsAm %BsE

Box Basso "Giri" |16:
  3%BsChorus

Box Basso "Finale" |160:
  4: 100@ 4a*1 | 4r |

Traccia Rhodes [Rhodes]:

Box Rhodes "Introduzione" |0:
  %RhAm %RhAm %RhAm %RhE

Box Rhodes "Giri" |16:
  vol=100 %RhChorus vol=85 %RhChorus vol=100 %RhChorus

Box Rhodes "Finale" |160:
  4: 70@ 4Am9$fermata | 4r |

Traccia Archi [Archi]:

Box Archi "Introduzione" |0:
  4: 40@ >> 4Am_ | 4Am_ | 4Am_ | 55@ 4E7_ |

Box Archi "Tema" |16:
  4: 45@ %StChorus

Box Archi "Assolo di sax" |64:
  4: 40@ %StChorus

Box Archi "Assolo di chitarra" |112:
  4: 50@ >> %StChorus 85@

Box Archi "Finale" |160:
  4: 80@ 4Am$fermata | 4r |

Traccia Chitarra [Solista]:

Box Chitarra "Introduzione" |0:
  8: 98@ 2r e*5 c*5 a*4>2c*5 r | a*4 g*4 2a*4_ 4r | 8r | g#*5 f*5 e*5 d*5 b*4 g#*4 2e*4 |

Box Chitarra "Tema" |16:
  %Theme

Box Chitarra "Assolo" |112:
  %GtSolo

Box Chitarra "Finale" |160:
  8: 105@ 8a*4$fermata | 8r |

Traccia Sax [Tenore]:

Box Sax "Risposte al tema" |16:
  // risposte brevi negli spazi del tema
  8: 4r 4r | 4r 85@ c*4 d*4 2e*4 | 8r | 4r 85@ g*4 e*4 2d*4 |
  8r | 4r 85@ f*4 a*4 2d*4 | 8r | 4r 85@ e*4 g*4 2a*4 |
  8r | 8r | 8r | 8r |

Box Sax "Assolo" |64:
  %SaxSolo

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/salamander-drums/ALL.sfz"

Plugin Basso:
  ref="sfz:~/Strumenti/sfz/pastabass/Pastabass/fetuccine.sfz"

Plugin Rhodes:
  ref="sfz:~/Strumenti/sfz/rhodes/jRhodes3d-st.sfz"

Plugin Chitarra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Sax:
  ref="sfz:~/Strumenti/sfz/solosax/MTG Solo Saxophones/MTG Tenor Sax.sfz"

Effetti Batteria:
  compressore: soglia=-16 rapporto=3 attacco=15 rilascio=150 guadagno=14 preset="Batteria"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=12
  volume: guadagno=2

Effetti Basso:
  compressore: soglia=-20 rapporto=3 attacco=20 rilascio=150 guadagno=10 preset="Basso"
  eq: bassi=2 medi=0 alti=-2

Effetti Rhodes:
  plugin: mix=70 livello=2 ref="lv2:http://calf.sourceforge.net/plugins/Phaser"
  riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=18

Effetti Archi:
  passa_alto: frequenza=150 pendenza=12
  compressore: soglia=-24 rapporto=2 attacco=30 rilascio=300 guadagno=6
  riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=30

Effetti Chitarra:
  nam: ingresso=0 cassa=nessuna livello=-2 nam="../profili_nam/Bugera 333 - crunch con cassa.nam"
  delay: suddivisione=1/8p tempo=536 ripetizioni=25 mix=14
  riverbero: stanza=60 smorzamento=45 ampiezza=100 mix=18
  passa_alto: frequenza=160 pendenza=12

Effetti Sax:
  compressore: soglia=-18 rapporto=3 attacco=10 rilascio=150 guadagno=13 preset="Voce"
  riverbero: stanza=60 smorzamento=40 ampiezza=100 mix=22

Catena master:
  volume: guadagno=-7
  eq: bassi=1 medi=0 alti=1
  compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 92 pan: 0 mute: no solo: no

Mixer Basso:
  volume: 100 pan: 0 mute: no solo: no

Mixer Rhodes:
  volume: 82 pan: -0.4 mute: no solo: no

Mixer Archi:
  volume: 75 pan: 0.3 mute: no solo: no

Mixer Chitarra:
  volume: 110 pan: 0.15 mute: no solo: no

Mixer Sax:
  volume: 105 pan: -0.15 mute: no solo: no
