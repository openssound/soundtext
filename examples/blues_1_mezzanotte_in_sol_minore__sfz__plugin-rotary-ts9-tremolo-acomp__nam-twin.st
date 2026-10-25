// Mezzanotte in Sol minore - slow blues in 12/8
//
// Un blues lento e minore, con la chitarra che canta: tre giri da 12
// battute (il tema, l'assolo, la ripresa che cresce fino al culmine) e un
// finale con il rallentando e la corona.
//
// Suoni:
// - batteria, basso, Wurlitzer e chitarra sono strumenti SFZ (scaricali
//   con  scarica_strumenti  : batteria, basso, epiano-vintage,
//   chitarra-elettrica, nella cartella ~/Strumenti); l'organo e' quello del
//   SoundFont GM;
// - il Wurlitzer passa per il tremolo valvolare GxTubeTremelo, l'organo per
//   il Leslie Calf Rotary Speaker, il basso per il compressore ACE (plugin
//   LV2: Guitarix, Calf, Ardour; su un sistema senza LV2 il suono passa
//   invariato);
// - la chitarra entra pulita in un Tube Screamer (GxTubeScreamer) e poi nel
//   profilo NAM di un Fender Twin Reverb con la cassa 2x12 (profili con
//   Suoni -> Scarica -> Scarica profili NAM consigliati...), poi eco in
//   terzine e riverbero;
// - sul master: EQ, compressore "colla" e limiter.

ST: 2.6
Tempo: 70 BPM
Metrica: 12/8
Tonalita: Gm

Strumento Wurli:
  program=4 percussione=no ottava=4 range=33-96 poly=si voicing=spread

Strumento Organo:
  program=16 percussione=no ottava=4 range=36-96 poly=si voicing=spread

Strumento Solista:
  program=27 percussione=no ottava=4 range=40-88 poly=no voicing=monophonic

// ---------------------------------------------------------------- batteria (12/8: kick sull'1 e sul 3, rullante sul 2 e sul 4)

Pattern %DrSlow:
  8: 92@ [kick hihat] 42@ hihat 50@ hihat 100@ [snare hihat] 42@ hihat 55@ hihat 85@ [kick hihat] 42@ hihat 68@ [kick hihat] 100@ [snare hihat] 42@ hihat 52@ hihat |

Pattern %DrSlowCrash:
  8: 105@ [kick crash] 42@ hihat 50@ hihat 100@ [snare hihat] 42@ hihat 55@ hihat 85@ [kick hihat] 42@ hihat 68@ [kick hihat] 100@ [snare hihat] 42@ hihat 52@ hihat |

Pattern %DrRide:
  8: 98@ [kick ride] 50@ ride 58@ ride 108@ [snare ride] 50@ ride 62@ ride 92@ [kick ride] 50@ ride 75@ [kick ride] 108@ [snare ride] 50@ ride 60@ ride |

Pattern %DrRideCrash:
  8: 112@ [kick crash] 50@ ride 58@ ride 108@ [snare ride] 50@ ride 62@ ride 92@ [kick ride] 50@ ride 75@ [kick ride] 108@ [snare ride] 50@ ride 60@ ride |

Pattern %DrFill:
  8: 92@ [kick hihat] 42@ hihat 50@ hihat 100@ [snare hihat] 42@ hihat 55@ hihat 88@ snare 65@ snare 95@ snare 100@ tom1 98@ tom2 108@ floor |

Pattern %DrFillBig:
  8: 98@ [kick ride] 50@ ride 58@ ride 108@ [snare ride] 85@ snare 95@ snare 100@ tom1 102@ tom1 104@ tom2 108@ tom2 112@ floor 118@ [kick floor] |

Pattern %DrChorus:
  %DrSlowCrash %DrSlow %DrSlow %DrSlow %DrSlow %DrSlow %DrSlow %DrFill %DrSlow %DrSlow %DrSlow %DrFill

Pattern %DrChorusSolo:
  %DrRideCrash %DrRide %DrRide %DrRide %DrRide %DrRide %DrRide %DrFillBig %DrRide %DrRide %DrRide %DrFillBig

// ---------------------------------------------------------------- basso (terzinato: fondamentale, quinta, settima)

Pattern %BsGm:
  8: 100@ 2g*1 g*1 2d*2 g*1 2f*2 g*2 2d*2 bb*1 |

Pattern %BsCm:
  8: 100@ 2c*2 c*2 2g*2 c*2 2bb*1 c*2 2g*1 eb*2 |

Pattern %BsEb:
  8: 100@ 2eb*2 eb*2 2g*2 eb*2 2bb*1 eb*2 2g*1 bb*1 |

Pattern %BsD:
  8: 100@ 2d*2 d*2 2f#*2 d*2 2a*2 d*2 2c*2 a*1 |

Pattern %BsGmEb:
  8: 100@ 2g*1 g*1 2d*2 g*1 2eb*2 eb*2 2bb*1 d*2 |

Pattern %BsChorus:
  %BsGm %BsCm %BsGm %BsGm %BsCm %BsCm %BsGm %BsGm %BsEb %BsD %BsGmEb %BsD

// ---------------------------------------------------------------- Wurlitzer (accordi lunghi e terzine sul 4)

Pattern %WuGm:
  8: 62@ 3Gm9_ 2Gm9! Gm9! 3Gm9_ 3r |

Pattern %WuCm:
  8: 62@ 3Cm9_ 2Cm9! Cm9! 3Cm9_ 3r |

Pattern %WuEb:
  8: 62@ 3Eb9_ 2Eb9! Eb9! 3Eb9_ 3r |

Pattern %WuD:
  8: 66@ 3D7#9_ 2D7#9! D7#9! 3D7#9_ 3r |

Pattern %WuGmEb:
  8: 62@ 3Gm9_ 2Gm9! Gm9! 3Eb9_ 3Eb9! |

Pattern %WuChorus:
  %WuGm %WuCm %WuGm %WuGm %WuCm %WuCm %WuGm %WuGm %WuEb %WuD %WuGmEb %WuD

// ---------------------------------------------------------------- organo (tappeto lungo, Leslie lento)

Pattern %OrChorus:
  8: 52@ 12Gm7_ | 12Cm7_ | 12Gm7_ | 12Gm7_ | 12Cm7_ | 12Cm7_ | 12Gm7_ | 12Gm7_ |
  12Eb9_ | 12D7_ | 6Gm7_ 6Eb9_ | 12D7_ |

// ---------------------------------------------------------------- chitarra solista: il tema (domanda, con lo spazio per le risposte)

Pattern %ThemeA:
  8: 96@
  3r d*5 f*5 g*5 bb*4>2c*5 bb*4 g*4 r |
  6g*4 3r bb*4 c*5 eb*5 |
  f*5>3g*5 f*5 d*5 c*5 2d*5 bb*4 2r |
  6g*4_ 6r |

Pattern %ThemeB:
  8: 98@
  3r c*5 eb*5 f*5 g*5>2ab*5 g*5 f*5 eb*5 |
  c*5>d*5>2c*5 bb*4 g*4 3c*5 3r |
  3r g*5 bb*5 g*5 f*5 d*5 f*5 2g*5 r |
  d*5 c*5 bb*4 2g*4 f*4 6g*4 |

Pattern %ThemeTurn:
  8: 100@
  3r bb*4 db*5 eb*5 f*5 2g*5 f*5 eb*5 r |
  f*5>2f#*5 d*5 c*5 a*4 f#*4 a*4 c*5 d*5 2r |
  3g*4 bb*4 c*5 d*5 3eb*5 2d*5 c*5 |
  c*5>2d*5 c*5 a*4 f#*4 6d*4 |

Pattern %Theme:
  %ThemeA %ThemeB %ThemeTurn

// ---------------------------------------------------------------- chitarra solista: l'assolo

Pattern %SoloA:
  8: 108@
  bb*5>2c*6 bb*5 g*5 f*5 g*5 f*5 d*5 c*5 d*5 bb*4 |
  c*6>d*6>2c*6 bb*5 g*5 bb*5 c*6 2d*6 2c*6 |
  3d*6 c*6 bb*5 g*5 f*5 g*5 f*5 d*5 c*5 bb*4 |
  g*4 bb*4 c*5 db*5 d*5 f*5 g*5 bb*5 c*6 3d*6 |

Pattern %SoloB:
  8: 110@
  6d*6_ c*6>d*6>2c*6 2r |
  bb*5 g*5 eb*5 c*5 bb*4 g*4 c*5 eb*5 g*5 3c*6 |
  16: d*6 c*6 bb*5 c*6 8: bb*5 g*5 f*5 g*5 f*5 d*5 c*5 3d*5 |
  6g*5_ 3r d*5 f*5 g*5 |

Pattern %SoloTurn:
  8: 112@
  bb*5>2c*6 bb*5 g*5 f*5 eb*5 f*5 g*5 3db*6 |
  c*6>d*6>2c*6 a*5 f#*5 d*5 f*5>2f#*5 2r |
  g*5 bb*5 d*6 3c*6 bb*5 g*5 f*5 3g*5 |
  a*5 c*6 a*5 f#*5 d*5 c*5 a*4 f#*4 a*4 3d*5 |

Pattern %Solo:
  %SoloA %SoloB %SoloTurn

// ================================================================ tracce

Traccia Batteria [Drums]:

Box Batteria "Introduzione" |0:
  %DrSlow %DrFill

Box Batteria "Tema" |12:
  %DrChorus

Box Batteria "Assolo" |84:
  %DrChorusSolo

Box Batteria "Ripresa" |156:
  // meta' giro piano, poi si cresce
  vol=70 %DrSlow %DrSlow %DrSlow %DrSlow %DrSlow %DrSlow vol=100 %DrRide %DrFillBig %DrRideCrash %DrRide %DrRide %DrFillBig

Box Batteria "Finale" |228:
  // rallentando fino alla corona (dentro la rampa una sola dinamica)
  100@ tempo=70 <<
  8: [kick hihat] hihat hihat [snare hihat] hihat hihat snare snare tom1 tom2 floor [kick floor] |
  tempo=52
  115@ [kick crash] 11r |

Traccia Basso [Bass]:

Box Basso "Introduzione" |0:
  %BsEb %BsD

Box Basso "Giri" |12:
  3%BsChorus

Box Basso "Finale" |228:
  8: 100@ 2g*1 g*1 2d*2 g*1 2eb*2 eb*2 2d*2 d*2 | 12g*1 |

Traccia Wurlitzer [Wurli]:

Box Wurlitzer "Introduzione" |0:
  %WuEb %WuD

Box Wurlitzer "Tema" |12:
  %WuChorus

Box Wurlitzer "Assolo" |84:
  vol=82 %WuChorus

Box Wurlitzer "Ripresa" |156:
  vol=72 %WuChorus

Box Wurlitzer "Finale" |228:
  vol=90 %WuGmEb 8: 70@ 12Gm9$fermata |

Traccia Organo [Organo]:

Box Organo "Tema" |12:
  %OrChorus

Box Organo "Assolo" |84:
  %OrChorus

Box Organo "Ripresa" |156:
  %OrChorus

Box Organo "Finale" |228:
  8: 55@ 6Gm7_ 6Eb9_ | 12Gm7$fermata |

Traccia Chitarra [Solista]:

Box Chitarra "Introduzione" |0:
  // la frase d'attacco sul giro finale
  8: 100@ 3r bb*4 db*5 eb*5 f*5 2g*5 f*5 eb*5 r |
  f*5>2f#*5 d*5 c*5 a*4 f#*4 a*4 c*5 d*5 2r |

Box Chitarra "Tema" |12:
  %Theme

Box Chitarra "Assolo" |84:
  %Solo

Box Chitarra "Ripresa" |156:
  // il tema piu' piano, poi l'ultima parte dell'assolo per il culmine
  80@ %ThemeA 100@ %SoloB %SoloTurn

Box Chitarra "Finale" |228:
  8: 108@ 3r d*5 f*5 g*5 bb*5>2c*6 bb*5 g*5 r | 12g*4$fermata |

// ================================================================ suoni

Plugin Batteria:
  ref="sfz:~/Strumenti/sfz/batteria/MuldjordKit SFZ+FLAC-20201018/MuldjordKit 20201018-GM.sfz"

Plugin Basso:
  ref="sfz:~/Strumenti/sfz/basso/FingerBassYR SFZ+FLAC-20190930/FingerBassYR 20190930.sfz"

Plugin Wurlitzer:
  ref="sfz:~/Strumenti/sfz/epiano-vintage/Wurlitzer EP200/Wurlitzer EP200.sfz"

Plugin Chitarra:
  ref="sfz:~/Strumenti/sfz/chitarra-elettrica/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz"

Effetti Batteria:
  compressore: soglia=-16 rapporto=3 attacco=15 rilascio=150 guadagno=7 preset="Batteria"
  riverbero: stanza=35 smorzamento=50 ampiezza=80 mix=12
  volume: guadagno=2

Effetti Basso:
  plugin: mix=100 livello=-5 ref="lv2:urn:ardour:a-comp" p.att=10 p.rel=120 p.rat=4 p.thr=-18 p.mak=3
  eq: bassi=2 medi=0 alti=-2

Effetti Wurlitzer:
  plugin: mix=100 livello=4 ref="lv2:http://guitarix.sourceforge.net/plugins/gxtubetremelo#tubetremelo" p.sinewave=1 p.depth=0.35 p.speed=4.5 p.drive=0.3 p.output=6
  riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=20

Effetti Organo:
  plugin: mix=100 livello=4 ref="lv2:http://calf.sourceforge.net/plugins/RotarySpeaker" p.vib_speed=1 p.level_out=1
  riverbero: stanza=60 smorzamento=40 ampiezza=100 mix=22

Effetti Chitarra:
  plugin: mix=100 livello=0 ref="lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim" p.BYPASS=1 p.fslider2_=0.35 p.fslider1_=600 p.fslider0_=-6
  nam: ingresso=0 cassa=2x12 livello=6 nam="../profili_nam/Fender Twin Reverb - pulito.nam"
  delay: suddivisione=1/4t tempo=571 ripetizioni=28 mix=14
  riverbero: stanza=65 smorzamento=45 ampiezza=100 mix=20
  passa_alto: frequenza=160 pendenza=12

Catena master:
  volume: guadagno=-4.5
  eq: bassi=1 medi=0 alti=1
  compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=2 preset="Colla del mix"
  limiter: guadagno=1 tetto=-1 rilascio=100

// ================================================================ mixer

Mixer Batteria:
  volume: 95 pan: 0 mute: no solo: no

Mixer Basso:
  volume: 105 pan: 0 mute: no solo: no

Mixer Wurlitzer:
  volume: 80 pan: -0.45 mute: no solo: no

Mixer Organo:
  volume: 95 pan: 0.4 mute: no solo: no

Mixer Chitarra:
  volume: 110 pan: 0.1 mute: no solo: no
