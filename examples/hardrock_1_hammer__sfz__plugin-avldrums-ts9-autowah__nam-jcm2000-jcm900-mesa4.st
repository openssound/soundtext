// Hammer - hard rock in E
//
// A hard rock guitar riff over a seventies drum kit: intro, verse, chorus
// with open chords, verse and chorus again, a 16-bar solo with the wah, the
// last chorus and the ending on E.
//
// Sounds:
// - drums: the AVL Drums instrument plugin, "Red Zeppelin" kit (LV2; on a
//   system without LV2 the SoundFont drums play);
// - bass and guitars: SFZ instruments (Sounds -> Download and install:
//   electric bass with pick, clean electric guitar);
// - the two rhythm guitars, one per side, go clean into a Tube Screamer used
//   as a booster and then into two different amplifiers (NAM profiles
//   Marshall JCM2000 and JCM900, a Marshall cabinet IR): the "wide" sound of
//   two guitars;
// - the lead: GxAutoWah, Tube Screamer and the Mesa Boogie Mark IV NAM
//   profile, then dotted delay and reverb;
// - the bass: parallel distortion and compressor; compressor and limiter on
//   the master.

ST: 2.6
Tempo: 128 BPM
Metrica: 4/4
Tonalita: Em

Strumento Rhythm:
  program=29 percussione=no ottava=2 range=35-86 poly=si voicing=power

Strumento Lead:
  program=29 percussione=no ottava=4 range=35-86 poly=no voicing=monophonic

// ---------------------------------------------------------------- drums

Pattern %Beat:
  8: 112@ [kick hihat] 72@ hihat 112@ [snare hihat] 72@ hihat 106@ [kick hihat] 100@ [kick hihat] 112@ [snare hihat] 72@ hihat |

Pattern %BeatCrash:
  8: 120@ [kick crash] 72@ hihat 112@ [snare hihat] 72@ hihat 106@ [kick hihat] 100@ [kick hihat] 112@ [snare hihat] 72@ hihat |

Pattern %BeatRide:
  8: 112@ [kick ride] 78@ ride 115@ [snare ride] 78@ ride 108@ [kick ride] 102@ [kick ride] 115@ [snare ride] 78@ ride |

Pattern %BeatRideCrash:
  8: 122@ [kick crash] 78@ ride 115@ [snare ride] 78@ ride 108@ [kick ride] 102@ [kick ride] 115@ [snare ride] 78@ ride |

Pattern %Fill:
  8: 112@ [kick hihat] 72@ hihat 112@ [snare hihat] 72@ hihat 16: 100@ snare snare 105@ tom1 tom1 108@ tom2 tom2 114@ floor floor |

Pattern %FillBig:
  16: 108@ snare snare snare snare 110@ tom1 tom1 tom1 tom1 112@ tom2 tom2 tom2 tom2 118@ floor floor [kick floor] [kick floor] |

Pattern %Verse8:
  %BeatCrash %Beat %Beat %Fill %Beat %Beat %Beat %FillBig

Pattern %Chorus8:
  %BeatRideCrash %BeatRide %BeatRide %BeatRide %BeatRideCrash %BeatRide %BeatRide %FillBig

// ---------------------------------------------------------------- the riff (two bars)

Pattern %Riff:
  8: 108@ e*2 e*2 g*2 e*2 a*2 e*2 G5*2 A5*2 | e*2 e*2 g*2 e*2 b*2 a*2 g*2 d*2 |

Pattern %BsRiff:
  8: 108@ e*1 e*1 g*1 e*1 a*1 e*1 g*1 a*1 | e*1 e*1 g*1 e*1 b*1 a*1 g*1 d*1 |

// ---------------------------------------------------------------- chorus: A5 | C5 D5 | E5 | E5 | A5 | C5 D5 | G5 | B5

Pattern %ChA:
  8: 112@ 2A5*2 A5*2! A5*2! 2A5*2 A5*2! A5*2! |

Pattern %ChCD:
  8: 112@ 2C5*3 C5*3! C5*3! 2D5*3 D5*3! D5*3! |

Pattern %ChE:
  8: 115@ 4E5*2_ 2E5*2 E5*2! E5*2! |

Pattern %ChG:
  8: 112@ 2G5*2 G5*2! G5*2! 2G5*2 G5*2! G5*2! |

Pattern %ChB:
  8: 115@ 2B5*2 B5*2! B5*2! B5*2! B5*2! B5*2! B5*2! |

Pattern %Chorus:
  %ChA %ChCD %ChE %ChE %ChA %ChCD %ChG %ChB

Pattern %BsChorus:
  8: 110@ 8(a*1) | 4(c*2) 4(d*2) | 8(e*1) | 8(e*1) | 8(a*1) | 4(c*2) 4(d*2) | 8(g*1) | 8(b*1) |

// ---------------------------------------------------------------- lead

Pattern %VerseMelody:
  8: 100@
  4b*4_ a*4 g*4 2e*4 |
  2g*4 a*4 b*4 4d*5 |
  4e*5_ d*5 b*4 2a*4 |
  2b*4 a*4 g*4 4e*4_ |
  4b*4_ d*5 e*5 2g*5 |
  g*5>2a*5 g*5 e*5 d*5 2b*4 |
  2d*5 e*5 d*5 b*4 a*4 2g*4 |
  8e*4_ |

Pattern %ChorusMelody:
  8: 110@
  6e*5_ d*5 e*5 |
  c*5>2d*5 c*5 a*4 b*4 2d*5 |
  8e*5_ |
  4r g*5 a*5 2b*5 |
  6a*5_ g*5 e*5 |
  g*5>2a*5 g*5 e*5 d*5 2e*5 |
  4d*5_ b*4 d*5 2g*5 |
  f#*5>2g*5 f#*5 d#*5 b*4 2r |

Pattern %Solo:
  8: 112@
  4g*5>4a*5 |
  g*5 e*5 d*5 e*5 g*5>2a*5 b*5 |
  16: b*5 a*5 g*5 e*5 b*5 a*5 g*5 e*5 b*5 a*5 g*5 e*5 8: 2d*5 |
  e*5>2f#*5 e*5 d*5 b*4 2e*5 |
  2r d*6 b*5 a*5 g*5 2e*5 |
  8T: d*6 b*5 a*5 d*6 b*5 a*5 d*6 b*5 a*5 d*6 b*5 a*5 8: |
  c*6>2d*6 c*6 b*5 a*5 2g*5 |
  a*5>2b*5 4b*5_ r |
  2a*5 c*6 d*6 c*6>2d*6 a*5 |
  16: d*6 c*6 a*5 g*5 d*6 c*6 a*5 g*5 8: a*5 c*6 2d*6 |
  4c*6>4d*6 |
  8T: d*6 b*5 g*5 d*6 b*5 g*5 8: 4e*5 |
  6c*6_ b*5 a*5 |
  c*6>2d*6 c*6 a*5 g*5 2e*5 |
  16: b*5 d*6 g*5 d*6 b*5 d*6 g*5 d*6 b*5 d*6 g*5 d*6 8: 2d*6 |
  c#*6>2d#*6 c#*6 b*5 f#*5 2d#*5 |

// ================================================================ tracks

Traccia Drums [Drums]:

Box Drums "Intro" |0:
  // two bars of riff alone, then the drums come in
  8: 8r | 8r | %Beat %FillBig

Box Drums "Verse 1" |16:
  %Verse8

Box Drums "Chorus 1" |48:
  %Chorus8

Box Drums "Verse 2" |80:
  %Verse8

Box Drums "Chorus 2" |112:
  %Chorus8

Box Drums "Solo" |144:
  %Verse8 %Chorus8

Box Drums "Chorus 3" |208:
  %Chorus8

Box Drums "Outro" |240:
  %BeatCrash %Beat 8: 125@ [kick crash] 3r 125@ [kick crash] 3r | %FillBig

Traccia Bass [Bass]:

Box Bass "Intro" |0:
  8: 8r | 8r | %BsRiff

Box Bass "Verse 1" |16:
  4%BsRiff

Box Bass "Chorus 1" |48:
  %BsChorus

Box Bass "Verse 2" |80:
  4%BsRiff

Box Bass "Chorus 2" |112:
  %BsChorus

Box Bass "Solo" |144:
  4%BsRiff %BsChorus

Box Bass "Chorus 3" |208:
  %BsChorus

Box Bass "Outro" |240:
  %BsRiff 8: 120@ e*1 3r e*1 3r | 8e*1$fermata |

Traccia Rhythm Left [Rhythm]:

Box Rhythm Left "Intro" |0:
  2%Riff

Box Rhythm Left "Verse 1" |16:
  4%Riff

Box Rhythm Left "Chorus 1" |48:
  %Chorus

Box Rhythm Left "Verse 2" |80:
  4%Riff

Box Rhythm Left "Chorus 2" |112:
  %Chorus

Box Rhythm Left "Solo" |144:
  4%Riff %Chorus

Box Rhythm Left "Chorus 3" |208:
  %Chorus

Box Rhythm Left "Outro" |240:
  %Riff 8: 120@ E5*2 3r E5*2 3r | 8E5*2$fermata |

Traccia Rhythm Right [Rhythm]:

Box Rhythm Right "Intro" |0:
  8: 8r | 8r | %Riff

Box Rhythm Right "Verse 1" |16:
  4%Riff

Box Rhythm Right "Chorus 1" |48:
  %Chorus

Box Rhythm Right "Verse 2" |80:
  4%Riff

Box Rhythm Right "Chorus 2" |112:
  %Chorus

Box Rhythm Right "Solo" |144:
  4%Riff %Chorus

Box Rhythm Right "Chorus 3" |208:
  %Chorus

Box Rhythm Right "Outro" |240:
  %Riff 8: 120@ E5*2 3r E5*2 3r | 8E5*2$fermata |

Traccia Lead [Lead]:

Box Lead "Verse 1" |16:
  %VerseMelody

Box Lead "Chorus 1" |48:
  %ChorusMelody

Box Lead "Verse 2" |80:
  %VerseMelody

Box Lead "Chorus 2" |112:
  %ChorusMelody

Box Lead "Solo" |144:
  %Solo

Box Lead "Chorus 3" |208:
  %ChorusMelody

Box Lead "Outro" |240:
  8: 8r | 8r | 8r | 115@ 4e*5>4g*5 |

// ================================================================ sounds

Plugin Drums:
  ref="lv2:http://gareus.org/oss/lv2/avldrums#RedZeppelin"

Plugin Bass:
  ref="sfz:~/Strumenti/sfz/basso-plettro/PickedBassYR SFZ+FLAC-20190930/PickedBassYR 20190930.sfz"

Plugin Rhythm Left:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Rhythm Right:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Lead:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Effetti Drums:
  compressore: soglia=-30 rapporto=6 attacco=15 rilascio=120 guadagno=3
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=14
  volume: guadagno=2

Effetti Bass:
  distorsione: spinta=14 tono=45 livello=-8 mix=35
  compressore: soglia=-20 rapporto=4 attacco=10 rilascio=120 guadagno=1 preset="Basso"

Effetti Rhythm Left:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.2 p.fslider1_=700 p.fslider0_=0
  nam: ingresso=3 cassa=file livello=-8 nam="../profili_nam/Marshall JCM2000 - crunch.nam" ir="../profili_nam/casse/Marshall JMP 2203  Jose Arredondo mod.wav"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Rhythm Right:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.2 p.fslider1_=650 p.fslider0_=0
  nam: ingresso=0 cassa=file livello=-8 nam="../profili_nam/Marshall JCM900 - lead.nam" ir="../profili_nam/casse/Marshall JMP 2203  Jose Arredondo mod.wav"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Lead:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxautowah#autowah" p.BYPASS=1
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.45 p.fslider1_=750 p.fslider0_=-2
  nam: ingresso=0 cassa=file livello=-1 nam="../profili_nam/Mesa Boogie Mark IV - lead.nam" ir="../profili_nam/casse/Mesa Boogie Mark V.wav"
  delay: suddivisione=1/8p tempo=352 ripetizioni=30 mix=16
  riverbero: stanza=55 smorzamento=45 ampiezza=100 mix=16
  passa_alto: frequenza=160 pendenza=12

Catena master:
  volume: guadagno=-6
  compressore: soglia=-14 rapporto=2.5 attacco=25 rilascio=180 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Drums:
  volume: 100 pan: 0 mute: no solo: no

Mixer Bass:
  volume: 105 pan: 0 mute: no solo: no

Mixer Rhythm Left:
  volume: 92 pan: -0.8 mute: no solo: no

Mixer Rhythm Right:
  volume: 92 pan: 0.8 mute: no solo: no

Mixer Lead:
  volume: 110 pan: 0.1 mute: no solo: no
