// Tempesta Elettrica - hard rock epico in Mi minore
//
// Comincia come una ballata (pianoforte, arpeggi di chitarra pulita, archi)
// e poi esplode: un galoppo alla Iron Maiden con due chitarre pesanti, il
// ritornello con gli archi, l'assolo, un ponte quieto che torna all'inizio,
// l'ultimo ritornello e la chiusura con il pianoforte.
//
// Suoni:
// - batteria, basso, pianoforte e chitarre: strumenti SFZ
//   (scarica_strumenti: salamander-drums, pastabass, splendid-piano,
//   chitarra-elettrica; in ~/Strumenti); gli archi sono quelli del SoundFont GM;
// - pianoforte nel riverbero ACE Reverb (plugin LV2: senza, passa invariato);
// - chitarra degli arpeggi nel profilo NAM del Fender Twin, con chorus ed eco;
//   ritmiche pesanti: Tube Screamer e i profili del Mesa Boogie Mark IV (a
//   sinistra) e del Peavey 5150 (a destra); solista: Tube Screamer e Marshall
//   JCM900 (profili con Suoni -> Scarica -> profili NAM consigliati);
// - master: compressore e limiter.

ST: 2.6
Tempo: 112 BPM
Metrica: 4/4
Tonalita: Em

Strumento Pulita:
  program=27 percussione=no ottava=3 range=35-86 poly=si voicing=spread

Strumento Ritmica:
  program=30 percussione=no ottava=2 range=35-86 poly=si voicing=power

Strumento Solista:
  program=29 percussione=no ottava=4 range=35-86 poly=no voicing=monophonic

Strumento Archi:
  program=48 percussione=no ottava=4 range=28-96 poly=si voicing=spread

// ---------------------------------------------------------------- batteria

Pattern %Beat:
  8: 116@ [kick hihat] 76@ hihat 116@ [snare hihat] 76@ hihat 110@ [kick hihat] 104@ [kick hihat] 116@ [snare hihat] 76@ hihat |

Pattern %Gallop:
  16: 118@ [kick crash] r kick kick 116@ [snare hihat] r kick kick 112@ [kick hihat] r kick kick 116@ [snare hihat] r kick kick |

Pattern %GallopHat:
  16: 114@ [kick hihat] r kick kick 116@ [snare hihat] r kick kick 112@ [kick hihat] r kick kick 116@ [snare hihat] r kick kick |

Pattern %BeatRideCrash:
  8: 124@ [kick crash] 80@ ride 118@ [snare ride] 80@ ride 112@ [kick ride] 106@ [kick ride] 118@ [snare ride] 80@ ride |

Pattern %BeatRide:
  8: 116@ [kick ride] 80@ ride 118@ [snare ride] 80@ ride 112@ [kick ride] 106@ [kick ride] 118@ [snare ride] 80@ ride |

Pattern %FillBig:
  16: 108@ snare snare snare snare 110@ tom1 tom1 tom1 tom1 112@ tom2 tom2 tom2 tom2 118@ floor floor [kick floor] [kick floor] |

Pattern %TomsBuild:
  16: 70@ >> floor floor floor floor floor floor floor floor tom2 tom2 tom2 tom2 tom2 tom2 tom2 tom2 |
  tom1 tom1 tom1 tom1 tom1 tom1 tom1 tom1 snare snare snare snare snare snare snare snare |
  floor floor tom2 tom2 tom1 tom1 snare snare floor floor tom2 tom2 tom1 tom1 snare snare |
  snare snare snare snare snare snare snare snare snare snare snare snare snare snare snare snare 120@ |

Pattern %Verse8:
  %Gallop %GallopHat %GallopHat %GallopHat %Gallop %GallopHat %GallopHat %FillBig

Pattern %Chorus8:
  %BeatRideCrash %BeatRide %BeatRide %BeatRide %BeatRideCrash %BeatRide %BeatRide %FillBig

// ---------------------------------------------------------------- arpeggi e pianoforte (Em C G D | Em C Am B7)

Pattern %ArpEm:
  8: 80@ e*3 b*3 e*4 g*4 b*4 g*4 e*4 b*3 |

Pattern %ArpC:
  8: 80@ c*3 g*3 c*4 e*4 g*4 e*4 c*4 g*3 |

Pattern %ArpG:
  8: 80@ g*2 d*3 g*3 b*3 d*4 b*3 g*3 d*3 |

Pattern %ArpD:
  8: 80@ d*3 a*3 d*4 f#*4 a*4 f#*4 d*4 a*3 |

Pattern %ArpAm:
  8: 80@ a*2 e*3 a*3 c*4 e*4 c*4 a*3 e*3 |

Pattern %ArpB7:
  8: 82@ b*2 f#*3 a*3 d#*4 f#*4 d#*4 a*3 f#*3 |

Pattern %Arp8:
  %ArpEm %ArpC %ArpG %ArpD %ArpEm %ArpC %ArpAm %ArpB7

Pattern %Piano8:
  4: 62@ 4Em9_ | 4Cmaj7_ | 4G_ | 4D_ | 4Em9_ | 4Cmaj7_ | 4Am7_ | 4B7_ |

Pattern %PianoMelody:
  // la melodia dell'introduzione, alla mano destra (suona insieme agli
  // accordi, vedi il box: senza stanghette, che conterebbero da capo)
  8: 78@ 6b*5_ a*5 g*5 4e*5_ g*5 e*5 2c*5 6g*5_ f#*5 g*5 4f#*5_ e*5 d*5 2a*4
  6b*5_ c*6 b*5 4g*5_ e*5 g*5 2c*6 4c*6_ b*5 a*5 2e*5 8b*5_

// ---------------------------------------------------------------- chitarre pesanti

Pattern %Riff:
  16: 120@ 2E5*2 E5*2x E5*2x 2E5*2 E5*2x E5*2x 2E5*2 E5*2x E5*2x 2G5*2 A5*2 B5*2 |
  2C5*3 C5*3x C5*3x 2C5*3 C5*3x C5*3x 2D5*3 D5*3x D5*3x 2D5*3 D5*3x D5*3x |

Pattern %Chorus:
  4: 118@ 4E5*2_ | 4C5*3_ | 4G5*2_ | 4D5*3_ | 4E5*2_ | 4C5*3_ | 4D5*3_ | 4B5*2_ |

Pattern %BsRiff:
  16: 116@ 2e*2 e*2 e*2 2e*2 e*2 e*2 2e*2 e*2 e*2 2g*2 a*2 b*2 |
  2c*2 c*2 c*2 2c*2 c*2 c*2 2d*2 d*2 d*2 2d*2 d*2 d*2 |

Pattern %BsChorus:
  8: 114@ 8(e*2) | 8(c*2) | 8(g*2) | 8(d*2) | 8(e*2) | 8(c*2) | 8(d*2) | 8(b*1) |

Pattern %StChorus:
  4: 4Em_ | 4C_ | 4G_ | 4D_ | 4Em_ | 4C_ | 4D_ | 4B7_ |

// ---------------------------------------------------------------- solista

Pattern %ChorusMelody:
  8: 112@
  6b*4_ a*4 g*4 |
  4e*5_ d*5 c*5 2g*4 |
  6d*5_ b*4 d*5 |
  4f#*5_ e*5 d*5 2a*4 |
  6g*5_ f#*5 e*5 |
  4e*5_ g*5 e*5 2c*5 |
  4d*5_ f#*5 a*5 2d*6 |
  c*6>2d*6 b*5 a*5 f#*5 d#*5 r |

Pattern %Solo:
  8: 116@
  4a*5>4b*5 |
  16: c*6 b*5 g*5 e*5 c*6 b*5 g*5 e*5 8: g*5 a*5 2b*5 |
  8T: d*6 b*5 g*5 d*6 b*5 g*5 d*6 b*5 g*5 d*6 b*5 g*5 8: |
  c*6>2d*6 c*6 a*5 f#*5 2d*5 |
  2r e*5 g*5 b*5 c*6>2d*6 |
  16: e*5 g*5 c*6 g*5 e*5 g*5 c*6 g*5 e*5 g*5 c*6 g*5 8: 2c*6 |
  16: d*5 f#*5 a*5 d*6 a*5 f#*5 d*5 f#*5 8: 4a*5_ |
  4b*5>4c*6 |

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Il temporale arriva" |32:
  %TomsBuild

Box Batteria "Galoppo" |48:
  %Verse8

Box Batteria "Ritornello" |80:
  %Chorus8

Box Batteria "Assolo" |112:
  %Chorus8

Box Batteria "Ultimo ritornello" |160:
  %Chorus8

Box Batteria "Chiusura" |192:
  8: 124@ [kick crash] 7r | 8r | 8r | 8r |

Traccia Basso [Bass]:

Box Basso "Il temporale arriva" |32:
  4: 100@ 4e*2 | 4c*2 | 4d*2 | 4b*1 |

Box Basso "Galoppo" |48:
  4%BsRiff

Box Basso "Ritornello" |80:
  %BsChorus

Box Basso "Assolo" |112:
  %BsChorus

Box Basso "Ultimo ritornello" |160:
  %BsChorus

Box Basso "Chiusura" |192:
  4: 110@ 4e*2 | 4r | 4r | 4r |

Traccia Pianoforte [Piano]:

Box Pianoforte "Introduzione" |0:
  { %Piano8 ; %PianoMelody }

Box Pianoforte "Ponte" |144:
  4: 60@ 4Em9_ | 4Cmaj7_ | 4G_ | 4D_ |

Box Pianoforte "Chiusura" |192:
  4: 75@ 4Em9_ | 4Cmaj7_ | 4Am7_ | 70@ 4Em9$fermata |

Traccia Arpeggi [Pulita]:

Box Arpeggi "Introduzione" |0:
  %Arp8

Box Arpeggi "Ponte" |144:
  %ArpEm %ArpC %ArpG %ArpD

Box Arpeggi "Chiusura" |192:
  %ArpEm %ArpC %ArpAm 8: 80@ 8[e*3 b*3 e*4 g*4]$fermata |

Traccia Archi [Archi]:

Box Archi "Introduzione" |0:
  4: 35@ >> %StChorus 70@

Box Archi "Il temporale arriva" |32:
  4: 70@ >> 4Em_ | 4C_ | 4D_ | 4B7_ 110@

Box Archi "Ritornello" |80:
  4: 85@ %StChorus

Box Archi "Assolo" |112:
  4: 70@ %StChorus

Box Archi "Ponte" |144:
  4: 55@ 4Em_ | 4C_ | 4G_ | 4D_ |

Box Archi "Ultimo ritornello" |160:
  4: 95@ %StChorus

Box Archi "Chiusura" |192:
  4: 80@ 4Em_ | 4C_ | 4Am_ | 4Em$fermata |

Traccia Ritmica Sinistra [Ritmica]:

Box Ritmica Sinistra "Il temporale arriva" |32:
  4: 120@ 4E5*2_ | 4C5*3_ | 4D5*3_ | 4B5*2_ |

Box Ritmica Sinistra "Galoppo" |48:
  4%Riff

Box Ritmica Sinistra "Ritornello" |80:
  %Chorus

Box Ritmica Sinistra "Assolo" |112:
  %Chorus

Box Ritmica Sinistra "Ultimo ritornello" |160:
  %Chorus

Box Ritmica Sinistra "Chiusura" |192:
  4: 124@ 4E5*2_ | 4r | 4r | 4r |

Traccia Ritmica Destra [Ritmica]:

Box Ritmica Destra "Il temporale arriva" |32:
  4: 120@ 4E5*2_ | 4C5*3_ | 4D5*3_ | 4B5*2_ |

Box Ritmica Destra "Galoppo" |48:
  4%Riff

Box Ritmica Destra "Ritornello" |80:
  %Chorus

Box Ritmica Destra "Assolo" |112:
  %Chorus

Box Ritmica Destra "Ultimo ritornello" |160:
  %Chorus

Box Ritmica Destra "Chiusura" |192:
  4: 124@ 4E5*2_ | 4r | 4r | 4r |

Traccia Solista [Solista]:

Box Solista "Ritornello" |80:
  %ChorusMelody

Box Solista "Assolo" |112:
  %Solo

Box Solista "Ultimo ritornello" |160:
  %ChorusMelody

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/salamander-drums/ALL.sfz"

Plugin Basso:
  ref="sfz:~/Strumenti/sfz/pastabass/Pastabass/linguine.sfz"

Plugin Pianoforte:
  ref="sfz:~/Strumenti/sfz/splendid-piano/Splendid Grand Piano.sfz"

Plugin Arpeggi:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Ritmica Sinistra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Ritmica Destra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Solista:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Effetti Batteria:
  compressore: soglia=-18 rapporto=4 attacco=10 rilascio=120 guadagno=6 preset="Batteria"
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=14
  volume: guadagno=2

Effetti Basso:
  amplificatore: modello=crunch cassa=nessuna guadagno=8 bassi=6 medi=6 alti=4 presenza=4 potenza=40 livello=-8
  compressore: soglia=-20 rapporto=4 attacco=10 rilascio=120 guadagno=4 preset="Basso"

Effetti Pianoforte:
  plugin: mix=40 livello=5 ref="lv2:urn:ardour:a-reverb"
  eq: bassi=0 medi=0 alti=1

Effetti Arpeggi:
  nam: ingresso=0 cassa=2x12 livello=12 nam="../profili_nam/Fender Twin Reverb - pulito.nam"
  chorus: velocita=0.8 profondita=40 mix=35
  delay: suddivisione=1/8p tempo=402 ripetizioni=30 mix=20
  riverbero: stanza=65 smorzamento=40 ampiezza=100 mix=22
  passa_alto: frequenza=110 pendenza=12

Effetti Archi:
  passa_alto: frequenza=120 pendenza=12
  riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=30

Effetti Ritmica Sinistra:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.15 p.fslider1_=650 p.fslider0_=0
  nam: ingresso=0 cassa=4x12 livello=-8 nam="../profili_nam/Mesa Boogie Mark IV - lead.nam"
  riverbero: stanza=40 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Ritmica Destra:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.15 p.fslider1_=650 p.fslider0_=0
  nam: ingresso=0 cassa=4x12 livello=-8 nam="../profili_nam/Peavey 5150 - high gain.nam"
  riverbero: stanza=40 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Solista:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.45 p.fslider1_=750 p.fslider0_=-2
  nam: ingresso=0 cassa=4x12 livello=-2 nam="../profili_nam/Marshall JCM900 - lead.nam"
  delay: suddivisione=1/4 tempo=536 ripetizioni=30 mix=16
  riverbero: stanza=65 smorzamento=45 ampiezza=100 mix=18
  passa_alto: frequenza=160 pendenza=12

Catena master:
  volume: guadagno=-5.5
  compressore: soglia=-14 rapporto=2.5 attacco=25 rilascio=180 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 100 pan: 0 mute: no solo: no

Mixer Basso:
  volume: 105 pan: 0 mute: no solo: no

Mixer Pianoforte:
  volume: 95 pan: -0.25 mute: no solo: no

Mixer Arpeggi:
  volume: 90 pan: 0.35 mute: no solo: no

Mixer Archi:
  volume: 80 pan: 0 mute: no solo: no

Mixer Ritmica Sinistra:
  volume: 92 pan: -0.8 mute: no solo: no

Mixer Ritmica Destra:
  volume: 92 pan: 0.8 mute: no solo: no

Mixer Solista:
  volume: 110 pan: 0.1 mute: no solo: no
