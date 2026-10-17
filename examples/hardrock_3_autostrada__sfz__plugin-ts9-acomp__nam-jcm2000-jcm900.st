// Autostrada - hard rock veloce in La
//
// Rock'n'roll a tutto volume alla AC/DC: un riff di accordi con le pause,
// strofe a colpi secchi, ritornello con gli accordi pieni, un assolo di 16
// battute e la chiusura. Due chitarre ritmiche in due Marshall diversi, una
// per lato, il basso sugli ottavi e una solista che morde.
//
// Suoni:
// - batteria, basso e chitarre: strumenti SFZ (scarica_strumenti: batteria,
//   basso-plettro, chitarra-elettrica; in ~/Strumenti);
// - ritmica a sinistra nel profilo NAM del Marshall JCM2000 (crunch), a
//   destra nel JCM900 con meno ingresso; la solista in un Tube Screamer e nel
//   JCM900, con un'eco corta (profili con Suoni -> Scarica -> profili NAM
//   consigliati);
// - il basso nel compressore ACE (plugin LV2: senza, passa invariato); sul
//   master compressore e limiter.

ST: 2.6
Tempo: 160 BPM
Metrica: 4/4
Tonalita: A

Strumento Ritmica:
  program=29 percussione=no ottava=2 range=35-86 poly=si voicing=power

Strumento Solista:
  program=29 percussione=no ottava=4 range=35-86 poly=no voicing=monophonic

// ---------------------------------------------------------------- batteria

Pattern %Beat:
  8: 114@ [kick hihat] 76@ hihat 114@ [snare hihat] 76@ hihat 108@ [kick hihat] 76@ hihat 114@ [snare hihat] 76@ hihat |

Pattern %BeatCrash:
  8: 122@ [kick crash] 76@ hihat 114@ [snare hihat] 76@ hihat 108@ [kick hihat] 76@ hihat 114@ [snare hihat] 76@ hihat |

Pattern %BeatOpen:
  8: 116@ [kick hihat_open] 80@ hihat_open 116@ [snare hihat_open] 80@ hihat_open 110@ [kick hihat_open] 80@ hihat_open 116@ [snare hihat_open] 80@ hihat_open |

Pattern %BeatOpenCrash:
  8: 124@ [kick crash] 80@ hihat_open 116@ [snare hihat_open] 80@ hihat_open 110@ [kick hihat_open] 80@ hihat_open 116@ [snare hihat_open] 80@ hihat_open |

Pattern %Fill:
  8: 114@ [kick hihat] 76@ hihat 114@ [snare hihat] 76@ hihat 104@ snare 108@ snare 112@ tom2 116@ floor |

Pattern %FillBig:
  16: 108@ snare snare snare snare 110@ tom1 tom1 112@ tom2 tom2 116@ floor floor floor floor 120@ [kick floor] [kick floor] [kick crash] r |

Pattern %Drums8:
  %BeatCrash %Beat %Beat %Fill %Beat %Beat %Beat %FillBig

Pattern %DrumsChorus8:
  %BeatOpenCrash %BeatOpen %BeatOpen %BeatOpen %BeatOpenCrash %BeatOpen %BeatOpen %FillBig

// ---------------------------------------------------------------- chitarre ritmiche

Pattern %Riff:
  8: 115@ 2A5*2 r A5*2! 2r D5*3 A5*2! | 2A5*2 r A5*2! G5*2 2D5*3 r |

Pattern %VerseA:
  8: 112@ A5*2! 3r D5*3! r E5*2! r |

Pattern %VerseB:
  8: 112@ A5*2! 3r G5*2! r D5*3! r |

Pattern %Verse:
  %VerseA %VerseB %VerseA %VerseB %VerseA %VerseB %VerseA %VerseB

Pattern %ChX:
  8: 118@ 4A5*2_ 2A5*2 A5*2! A5*2! |

Pattern %ChG:
  8: 118@ 4G5*2_ 2G5*2 G5*2! G5*2! |

Pattern %ChD:
  8: 118@ 4D5*3_ 2D5*3 D5*3! D5*3! |

Pattern %ChE:
  8: 120@ 4E5*2_ 2E5*2 E5*2! E5*2! |

Pattern %Chorus:
  %ChX %ChG %ChD %ChX %ChX %ChG %ChD %ChE

// ---------------------------------------------------------------- basso

Pattern %BsRiff:
  8: 112@ 8(a*1) | 4(a*1) g*1 g*1 d*2 d*2 |

Pattern %BsVerse:
  8: 110@ a*1 3r d*2 r e*1 r | a*1 3r g*1 r d*2 r |

Pattern %BsChorus:
  8: 114@ 8(a*1) | 8(g*1) | 8(d*2) | 8(a*1) | 8(a*1) | 8(g*1) | 8(d*2) | 8(e*1) |

// ---------------------------------------------------------------- solista

Pattern %VerseMelody:
  8: 108@
  2r e*5 e*5 g*5 e*5 2a*5 |
  g*5>2a*5 g*5 e*5 2d*5 r |
  2r c*5 d*5 e*5 g*5 2e*5 |
  4a*4_ 4r |
  2r a*5 a*5 c*6 a*5 2g*5 |
  e*5 g*5 a*5 g*5>2a*5 2e*5 |
  2d*5 c*5 a*4 2c*5 2d*5 |
  8e*5_ |

Pattern %ChorusMelody:
  8: 112@
  6c#*5_ b*4 a*4 |
  4b*4_ d*5 b*4 2g*4 |
  6a*4_ f#*4 a*4 |
  8e*5_ |
  6c#*5_ e*5 f#*5 |
  4g*5_ f#*5 e*5 2d*5 |
  6f#*5_ e*5 d*5 |
  e*5>2f#*5 e*5 d*5 b*4 2r |

Pattern %Solo:
  8: 116@
  4c*5>4d*5 |
  16: a*5 g*5 e*5 a*5 g*5 e*5 a*5 g*5 e*5 a*5 g*5 e*5 a*5 g*5 e*5 d*5 |
  8: c*6>2d*6 c*6 a*5 g*5 2e*5 |
  8T: c*6 a*5 g*5 c*6 a*5 g*5 8: 4a*5 |
  2r e*5 g*5 a*5 c*6>2d*6 |
  16: d*6 c*6 a*5 c*6 d*6 c*6 a*5 c*6 d*6 c*6 a*5 c*6 d*6 c*6 a*5 g*5 |
  8: a*5 g*5 e*5 d*5 c*5 a*4 2g*4 |
  4g*4>4a*4 |
  6c#*6_ b*5 a*5 |
  b*5>2c#*6 b*5 g*5 d*5 2b*4 |
  16: a*5 f#*5 d*5 a*5 f#*5 d*5 a*5 f#*5 8: 4d*6_ |
  c*6>2c#*6 a*5 e*5 2c#*5 r |
  8T: e*5 a*5 c#*6 e*5 a*5 c#*6 e*5 a*5 c#*6 e*5 a*5 c#*6 8: |
  4d*6_ b*5 g*5 2d*5 |
  2f#*5 a*5 d*6 a*5 f#*5 2d*5 |
  4b*5>4c#*6 |

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  8: 8r | 8r | 122@ [kick crash] 3r [kick crash] 3r | %FillBig

Box Batteria "Riff" |16:
  %Drums8

Box Batteria "Strofa 1" |48:
  %Drums8

Box Batteria "Ritornello 1" |80:
  %DrumsChorus8

Box Batteria "Riff 2" |112:
  %BeatCrash %Beat %Beat %FillBig

Box Batteria "Strofa 2" |128:
  %Drums8

Box Batteria "Ritornello 2" |160:
  %DrumsChorus8

Box Batteria "Assolo" |192:
  %Drums8 %DrumsChorus8

Box Batteria "Ultimo ritornello" |256:
  %DrumsChorus8

Box Batteria "Chiusura" |288:
  %BeatCrash %Fill 8: 125@ [kick crash] 3r 125@ [kick crash] 3r | %FillBig

Traccia Basso [Bass]:

Box Basso "Introduzione" |0:
  8: 8r | 8r | 120@ a*1 3r a*1 3r | 8r |

Box Basso "Riff" |16:
  4%BsRiff

Box Basso "Strofa 1" |48:
  4%BsVerse

Box Basso "Ritornello 1" |80:
  %BsChorus

Box Basso "Riff 2" |112:
  2%BsRiff

Box Basso "Strofa 2" |128:
  4%BsVerse

Box Basso "Ritornello 2" |160:
  %BsChorus

Box Basso "Assolo" |192:
  4%BsRiff %BsChorus

Box Basso "Ultimo ritornello" |256:
  %BsChorus

Box Basso "Chiusura" |288:
  %BsRiff 8: 122@ a*1 3r a*1 3r | 8a*1$fermata |

Traccia Ritmica Sinistra [Ritmica]:

Box Ritmica Sinistra "Introduzione" |0:
  2%Riff

Box Ritmica Sinistra "Riff" |16:
  4%Riff

Box Ritmica Sinistra "Strofa 1" |48:
  %Verse

Box Ritmica Sinistra "Ritornello 1" |80:
  %Chorus

Box Ritmica Sinistra "Riff 2" |112:
  2%Riff

Box Ritmica Sinistra "Strofa 2" |128:
  %Verse

Box Ritmica Sinistra "Ritornello 2" |160:
  %Chorus

Box Ritmica Sinistra "Assolo" |192:
  4%Riff %Chorus

Box Ritmica Sinistra "Ultimo ritornello" |256:
  %Chorus

Box Ritmica Sinistra "Chiusura" |288:
  %Riff 8: 122@ A5*2 3r A5*2 3r | 8A5*2$fermata |

Traccia Ritmica Destra [Ritmica]:

Box Ritmica Destra "Introduzione" |0:
  8: 8r | 8r | %Riff

Box Ritmica Destra "Riff" |16:
  4%Riff

Box Ritmica Destra "Strofa 1" |48:
  %Verse

Box Ritmica Destra "Ritornello 1" |80:
  %Chorus

Box Ritmica Destra "Riff 2" |112:
  2%Riff

Box Ritmica Destra "Strofa 2" |128:
  %Verse

Box Ritmica Destra "Ritornello 2" |160:
  %Chorus

Box Ritmica Destra "Assolo" |192:
  4%Riff %Chorus

Box Ritmica Destra "Ultimo ritornello" |256:
  %Chorus

Box Ritmica Destra "Chiusura" |288:
  %Riff 8: 122@ A5*2 3r A5*2 3r | 8A5*2$fermata |

Traccia Solista [Solista]:

Box Solista "Strofa 1" |48:
  %VerseMelody

Box Solista "Ritornello 1" |80:
  %ChorusMelody

Box Solista "Strofa 2" |128:
  %VerseMelody

Box Solista "Ritornello 2" |160:
  %ChorusMelody

Box Solista "Assolo" |192:
  %Solo

Box Solista "Ultimo ritornello" |256:
  %ChorusMelody

Box Solista "Chiusura" |288:
  8: 8r | 8r | 8r | 120@ 4c*5>4c#*5 |

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/batteria/MuldjordKit SFZ+FLAC-20201018/MuldjordKit 20201018-GM.sfz"

Plugin Basso:
  ref="sfz:~/Strumenti/sfz/basso-plettro/PickedBassYR SFZ+FLAC-20190930/PickedBassYR 20190930.sfz"

Plugin Ritmica Sinistra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Ritmica Destra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Plugin Solista:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Effetti Batteria:
  compressore: soglia=-18 rapporto=4 attacco=10 rilascio=120 guadagno=1 preset="Batteria"
  riverbero: stanza=40 smorzamento=50 ampiezza=90 mix=10
  volume: guadagno=2

Effetti Basso:
  plugin: mix=100 livello=0 ref="lv2:urn:ardour:a-comp" p.att=5 p.rel=100 p.rat=6 p.thr=-20 p.mak=2
  eq: bassi=2 medi=2 alti=0

Effetti Ritmica Sinistra:
  nam: ingresso=0 cassa=4x12 livello=-7 nam="../profili_nam/Marshall JCM2000 - crunch.nam"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Ritmica Destra:
  nam: ingresso=-6 cassa=4x12 livello=-6 nam="../profili_nam/Marshall JCM900 - lead.nam"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=8
  passa_alto: frequenza=110 pendenza=12

Effetti Solista:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.4 p.fslider1_=800 p.fslider0_=-2
  nam: ingresso=0 cassa=4x12 livello=-3 nam="../profili_nam/Marshall JCM900 - lead.nam"
  delay: suddivisione=libera tempo=110 ripetizioni=12 mix=14 preset="Slapback"
  riverbero: stanza=50 smorzamento=45 ampiezza=100 mix=14
  passa_alto: frequenza=160 pendenza=12

Catena master:
  volume: guadagno=-5
  compressore: soglia=-14 rapporto=2.5 attacco=25 rilascio=180 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 100 pan: 0 mute: no solo: no

Mixer Basso:
  volume: 105 pan: 0 mute: no solo: no

Mixer Ritmica Sinistra:
  volume: 92 pan: -0.8 mute: no solo: no

Mixer Ritmica Destra:
  volume: 92 pan: 0.8 mute: no solo: no

Mixer Solista:
  volume: 110 pan: 0.1 mute: no solo: no
