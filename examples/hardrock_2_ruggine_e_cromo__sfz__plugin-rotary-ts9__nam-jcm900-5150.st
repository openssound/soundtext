// Ruggine e Cromo - hard rock pesante in Re minore
//
// Un riff lento e pesante alla Deep Purple / Black Sabbath, con l'organo
// Hammond che passa per un Leslie e poi dentro un Marshall, come faceva Jon
// Lord: l'organo apre da solo, poi il riff, la strofa (la melodia e'
// all'organo), il ritornello (alla chitarra), un assolo d'organo, un assolo
// di chitarra, l'ultimo ritornello e la chiusura.
//
// Suoni:
// - batteria DRSKit, basso Pastabass e chitarre: strumenti SFZ
//   (scarica_strumenti: drskit-sfz, pastabass, chitarra-dist,
//   chitarra-elettrica; in ~/Strumenti); l'organo e' quello del SoundFont GM;
// - organo: Leslie veloce (Calf Rotary Speaker, plugin LV2) e poi il profilo
//   NAM del Marshall JCM900 con la 4x12;
// - chitarra a sinistra: il campione gia' distorto, solo ripulito sui bassi;
//   chitarra a destra: pulita in un Tube Screamer e nel profilo NAM del Peavey
//   5150 high gain; la solista: Tube Screamer e Marshall JCM900, eco e
//   riverbero (profili con Suoni -> Scarica -> profili NAM consigliati);
// - il basso nell'Amplificatore interno, per il ringhio; sul master
//   compressore e limiter.

ST: 2.6
Tempo: 96 BPM
Metrica: 4/4
Tonalita: Dm

Strumento Ritmica:
  program=30 percussione=no ottava=2 range=35-86 poly=si voicing=power

Strumento Solista:
  program=29 percussione=no ottava=4 range=35-86 poly=no voicing=monophonic

Strumento Hammond:
  program=18 percussione=no ottava=4 range=36-96 poly=si voicing=spread

// ---------------------------------------------------------------- batteria

Pattern %Beat:
  8: 118@ [kick hihat] 75@ hihat 115@ [snare hihat] 75@ hihat 110@ [kick hihat] 105@ [kick hihat] 115@ [snare hihat] 75@ hihat |

Pattern %BeatCrash:
  8: 124@ [kick crash] 75@ hihat 115@ [snare hihat] 75@ hihat 110@ [kick hihat] 105@ [kick hihat] 115@ [snare hihat] 75@ hihat |

Pattern %BeatRide:
  8: 118@ [kick ride] 80@ ride 118@ [snare ride] 80@ ride 112@ [kick ride] 106@ [kick ride] 118@ [snare ride] 80@ ride |

Pattern %BeatRideCrash:
  8: 124@ [kick crash] 80@ ride 118@ [snare ride] 80@ ride 112@ [kick ride] 106@ [kick ride] 118@ [snare ride] 80@ ride |

Pattern %Fill:
  8: 118@ [kick hihat] 75@ hihat 115@ [snare hihat] 75@ hihat 16: 104@ snare snare 108@ tom1 tom1 112@ tom2 tom2 116@ floor floor |

Pattern %FillBig:
  16: 110@ snare snare snare snare 112@ tom1 tom1 tom1 tom1 115@ tom2 tom2 tom2 tom2 120@ floor floor [kick floor] [kick floor] |

Pattern %Riff8:
  %BeatCrash %Beat %Beat %Fill %Beat %Beat %Beat %FillBig

Pattern %Chorus8:
  %BeatRideCrash %BeatRide %BeatRide %BeatRide %BeatRideCrash %BeatRide %BeatRide %FillBig

// ---------------------------------------------------------------- il riff

Pattern %Riff:
  8: 112@ d*2 d*2 f*2 d*2 g*2 ab*2>2a*2 | d*2 d*2 f*2 d*2 c*3 a*2 2f*2 |

Pattern %BsRiff:
  8: 110@ d*2 d*2 f*2 d*2 g*2 ab*2>2a*2 | d*2 d*2 f*2 d*2 c*3 a*2 2f*2 |

// ---------------------------------------------------------------- ritornello: Bb | C | Dm | Dm | Bb | C | A | A

Pattern %ChBb:
  8: 115@ 2Bb5*2 Bb5*2! Bb5*2! 2Bb5*2 Bb5*2! Bb5*2! |

Pattern %ChC:
  8: 115@ 2C5*3 C5*3! C5*3! 2C5*3 C5*3! C5*3! |

Pattern %ChD:
  8: 118@ 4D5*2_ 2D5*2 D5*2! D5*2! |

Pattern %ChA:
  8: 118@ 2A5*2 A5*2! A5*2! A5*2! A5*2! A5*2! A5*2! |

Pattern %Chorus:
  %ChBb %ChC %ChD %ChD %ChBb %ChC %ChA %ChA

Pattern %BsChorus:
  8: 112@ 8(bb*1) | 8(c*2) | 8(d*2) | 8(d*2) | 8(bb*1) | 8(c*2) | 8(a*1) | 8(a*1) |

Pattern %OrChorus:
  8: 95@ 8Bb_ | 8C_ | 8Dm_ | 8Dm_ | 8Bb_ | 8C_ | 8A7_ | 8A7_ |

// ---------------------------------------------------------------- organo: melodia della strofa e assolo

Pattern %OrVerse:
  8: 100@
  4a*4_ g*4 f*4 2d*4 |
  2f*4 g*4 a*4 4c*5 |
  4d*5_ c*5 a*4 2g*4 |
  2a*4 g*4 f*4 4d*4_ |
  4a*4_ c*5 d*5 2f*5 |
  2e*5 d*5 c*5 4a*4 |
  2c*5 d*5 c*5 a*4 g*4 2f*4 |
  8d*4_ |

Pattern %OrSolo:
  8: 112@
  d*5 f*5 g*5 a*5 c*6 a*5 g*5 f*5 |
  16: d*6 c*6 a*5 g*5 d*6 c*6 a*5 g*5 8: f*5 g*5 2a*5 |
  8T: a*5 c*6 d*6 a*5 c*6 d*6 a*5 c*6 d*6 a*5 c*6 d*6 8: |
  4f*6_ 2e*6 2d*6 |
  4Dm_ 4C_ |
  4Bb_ 4A7_ |
  16: d*5 f*5 a*5 d*6 f*5 a*5 d*6 f*6 a*5 d*6 f*6 a*6 8: 2d*6 |
  8Dm_ |

// ---------------------------------------------------------------- chitarra solista: ritornello e assolo

Pattern %GtChorus:
  8: 110@
  6d*5_ c*5 d*5 |
  4e*5_ d*5 c*5 2g*4 |
  8f*5_ |
  4r e*5 f*5 2a*5 |
  6f*5_ e*5 d*5 |
  e*5>2f*5 e*5 c*5 g*4 2c*5 |
  4c#*5_ e*5 c#*5 2a*4 |
  8a*4_ |

Pattern %GtSolo:
  8: 115@
  4c*5>4d*5 |
  f*5 d*5 c*5 a*4 c*5>2d*5 f*5 |
  16: a*5 g*5 f*5 d*5 a*5 g*5 f*5 d*5 a*5 g*5 f*5 d*5 8: 2c*5 |
  d*5>2e*5 d*5 c*5 a*4 2d*5 |
  2r d*6 c*6 a*5 g*5 2f*5 |
  8T: d*6 c*6 a*5 d*6 c*6 a*5 d*6 c*6 a*5 d*6 c*6 a*5 8: |
  c*6>2d*6 c*6 a*5 g*5 2a*5 |
  4a*5>4bb*5 |

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  8: 8r | 8r | 8r | %FillBig

Box Batteria "Riff" |16:
  %Riff8

Box Batteria "Strofa" |48:
  %Riff8

Box Batteria "Ritornello" |80:
  %Chorus8

Box Batteria "Assolo d'organo" |112:
  %Riff8

Box Batteria "Assolo di chitarra" |144:
  %Riff8

Box Batteria "Ultimo ritornello" |176:
  %Chorus8

Box Batteria "Chiusura" |208:
  %BeatCrash %Fill 8: 125@ [kick crash] 3r 125@ [kick crash] 3r | %FillBig

Traccia Basso [Bass]:

Box Basso "Introduzione" |0:
  8: 8r | 8r | 8r | 8r |

Box Basso "Riff e strofa" |16:
  8%BsRiff

Box Basso "Ritornello" |80:
  %BsChorus

Box Basso "Assoli" |112:
  8%BsRiff

Box Basso "Ultimo ritornello" |176:
  %BsChorus

Box Basso "Chiusura" |208:
  %BsRiff 8: 120@ d*2 3r d*2 3r | 8d*2$fermata |

Traccia Chitarra Sinistra [Ritmica]:

Box Chitarra Sinistra "Riff e strofa" |16:
  8%Riff

Box Chitarra Sinistra "Ritornello" |80:
  %Chorus

Box Chitarra Sinistra "Assoli" |112:
  8%Riff

Box Chitarra Sinistra "Ultimo ritornello" |176:
  %Chorus

Box Chitarra Sinistra "Chiusura" |208:
  %Riff 8: 122@ D5*2 3r D5*2 3r | 8D5*2$fermata |

Traccia Chitarra Destra [Ritmica]:

Box Chitarra Destra "Riff e strofa" |16:
  8%Riff

Box Chitarra Destra "Ritornello" |80:
  %Chorus

Box Chitarra Destra "Assoli" |112:
  8%Riff

Box Chitarra Destra "Ultimo ritornello" |176:
  %Chorus

Box Chitarra Destra "Chiusura" |208:
  %Riff 8: 122@ D5*2 3r D5*2 3r | 8D5*2$fermata |

Traccia Organo [Hammond]:

Box Organo "Introduzione" |0:
  // l'organo da solo, crescendo
  8: 55@ >> 8Dm_ | 8Bb_ | 8C_ | 8A7_ | 110@

Box Organo "Riff" |16:
  8: 90@ 8(4Dm_ 4Dm!) |

Box Organo "Strofa" |48:
  %OrVerse

Box Organo "Ritornello" |80:
  %OrChorus

Box Organo "Assolo" |112:
  %OrSolo

Box Organo "Sotto l'assolo di chitarra" |144:
  8: 80@ 8(4Dm_ 4Dm!) |

Box Organo "Ultimo ritornello" |176:
  %OrChorus

Box Organo "Chiusura" |208:
  8: 95@ 8Dm_ | 8Dm_ | 115@ Dm 3r Dm 3r | 8Dm$fermata |

Traccia Solista [Solista]:

Box Solista "Ritornello" |80:
  %GtChorus

Box Solista "Assolo" |144:
  %GtSolo

Box Solista "Ultimo ritornello" |176:
  %GtChorus

Box Solista "Chiusura" |208:
  8: 8r | 8r | 8r | 118@ 4c*5>4d*5 |

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/drskit-sfz/DrumGizmo/DRSKit/Stereo/DrumGizmo DRSKit.sfz"

Plugin Basso:
  ref="sfz:~/Strumenti/sfz/pastabass/Pastabass/spaghetti.sfz"

Plugin Chitarra Sinistra:
  ref="sfz:~/Strumenti/sfz/chitarra-dist/EGuitarFSBS-dist1 SFZ+FLAC-20220911/EGuitarFSBS-dist1 bridge 20220911.sfz"

Plugin Chitarra Destra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Solista:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Effetti Batteria:
  compressore: soglia=-18 rapporto=4 attacco=10 rilascio=120 guadagno=8 preset="Batteria"
  riverbero: stanza=60 smorzamento=40 ampiezza=100 mix=14
  volume: guadagno=2

Effetti Basso:
  amplificatore: modello=crunch cassa=nessuna guadagno=10 bassi=6 medi=6 alti=4 presenza=4 potenza=40 livello=-8
  compressore: soglia=-20 rapporto=4 attacco=10 rilascio=120 guadagno=4 preset="Basso"

Effetti Chitarra Sinistra:
  passa_alto: frequenza=90 pendenza=12
  eq: bassi=0 medi=2 alti=-1
  riverbero: stanza=40 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Chitarra Destra:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.15 p.fslider1_=650 p.fslider0_=0
  nam: ingresso=0 cassa=4x12 livello=-8 nam="../profili_nam/Peavey 5150 - high gain.nam"
  riverbero: stanza=40 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Organo:
  plugin: mix=100 livello=0 ref="lv2:http://calf.sourceforge.net/plugins/RotarySpeaker" p.vib_speed=2 p.level_out=1
  nam: ingresso=-4 cassa=4x12 livello=-4 nam="../profili_nam/Marshall JCM900 - lead.nam"
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=14

Effetti Solista:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.45 p.fslider1_=750 p.fslider0_=-2
  nam: ingresso=0 cassa=4x12 livello=-2 nam="../profili_nam/Marshall JCM900 - lead.nam"
  delay: suddivisione=1/4 tempo=625 ripetizioni=28 mix=15
  riverbero: stanza=60 smorzamento=45 ampiezza=100 mix=16
  passa_alto: frequenza=160 pendenza=12

Catena master:
  volume: guadagno=-8.5
  compressore: soglia=-14 rapporto=2.5 attacco=25 rilascio=180 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 100 pan: 0 mute: no solo: no

Mixer Basso:
  volume: 105 pan: 0 mute: no solo: no

Mixer Chitarra Sinistra:
  volume: 90 pan: -0.8 mute: no solo: no

Mixer Chitarra Destra:
  volume: 90 pan: 0.8 mute: no solo: no

Mixer Organo:
  volume: 95 pan: 0.2 mute: no solo: no

Mixer Solista:
  volume: 110 pan: -0.1 mute: no solo: no
