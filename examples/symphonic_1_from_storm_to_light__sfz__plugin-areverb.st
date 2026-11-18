// Overture "From Storm to Light" - for symphony orchestra
//
// Four sections without a break:
// 1. Lento: tremolo strings in the darkness of D minor, timpani rolls, the
//    horn call and the cello's answer;
// 2. Allegro agitato: the storm, the violin theme over the driving eighths of
//    the low strings, accents from trumpets and trombones;
// 3. Tranquillo: the calm, the solo cello sings over the harp arpeggios;
// 4. Maestoso: the light, the horn call becomes a hymn in D major for full
//    orchestra, slowing down to the fermata.
//
// Sounds:
// - SFZ instruments: tremolo strings (Discord GM Bank), Karoryfer Bigcat
//   cello, D. Smolken bowed double basses, concert harp (Sounds -> Download
//   and install); violins, woodwinds, brass and timpani are the General MIDI
//   SoundFont's;
// - a concert hall: the built-in reverb on each section and the ACE Reverb
//   (LV2 plugin) on the master, then EQ, a light compressor and a limiter.

ST: 2.6
Tempo: 66 BPM
Metrica: 4/4
Tonalita: Dm

Strumento Violins:
  program=48 percussione=no ottava=5 range=55-100 poly=si voicing=spread

Strumento Tremolos:
  program=44 percussione=no ottava=4 range=28-84 poly=si voicing=spread

Strumento Cello:
  program=42 percussione=no ottava=3 range=36-77 poly=no voicing=monophonic

Strumento DoubleBasses:
  program=43 percussione=no ottava=2 range=28-60 poly=no voicing=root_only

Strumento Flute:
  program=73 percussione=no ottava=5 range=60-96 poly=no voicing=monophonic

Strumento Oboe:
  program=68 percussione=no ottava=5 range=58-91 poly=no voicing=monophonic

Strumento Horns:
  program=60 percussione=no ottava=4 range=34-77 poly=si voicing=spread

Strumento Trumpets:
  program=56 percussione=no ottava=4 range=54-86 poly=si voicing=spread

Strumento Trombones:
  program=57 percussione=no ottava=3 range=40-72 poly=si voicing=spread

Strumento Timpani:
  program=47 percussione=no ottava=2 range=28-57 poly=no voicing=root_only

Strumento Harp:
  program=46 percussione=no ottava=3 range=28-102 poly=si voicing=spread

// ================================================================ themes

// Allegro agitato: the storm theme (16 bars)
Pattern %Storm:
  8: 100@
  d*5 a*4 d*5 f*5 a*5 f*5 d*5 a*4 |
  2e*5 f*5 g*5 4a*5 |
  bb*5 a*5 g*5 f*5 g*5 d*5 bb*4 g*4 |
  2a*4 c#*5 e*5 4g*5 |
  f*5 e*5 d*5 c#*5 d*5 e*5 f*5 g*5 |
  4a*5 2bb*5 2a*5 |
  g*5 f*5 e*5 d*5 c#*5 d*5 e*5 c#*5 |
  4d*5 4r |
  c*5 f*5 a*5 c*6 a*5 f*5 c*5 a*4 |
  2g*4 c*5 e*5 4g*5 |
  f*5 a*5 d*6 a*5 f*5 d*5 a*4 f*4 |
  2e*4 a*4 c#*5 4e*5 |
  d*5 f*5 bb*5 d*6 c*6 bb*5 a*5 g*5 |
  f*5 g*5 bb*5 d*6 2c*6 2bb*5 |
  16: a*5 g*5 f*5 e*5 d*5 c#*5 d*5 e*5 8: 2f*5 2e*5 |
  4c#*5_ 4a*4 |

// the harmonies of the Allegro (16 bars)
Pattern %HarmonyStorm:
  4: 4Dm_ | 4Dm_ | 4Gm_ | 4A7_ | 4Dm_ | 4Bb_ | 2Gm 2A7 | 4Dm |
  4F_ | 4C_ | 4Dm_ | 4A7_ | 4Bb_ | 4Gm_ | 4A7_ | 4A7_ |

Pattern %AccentsStorm:
  4: Dm! 3r | 4r | Gm! 3r | A7! 3r | Dm! 3r | Bb! 3r | Gm! r A7! r | Dm! 3r |
  F! 3r | C! 3r | Dm! 3r | A7! 3r | Bb! 3r | Gm! 3r | A7! A7! A7! A7! | 4A7_ |

// Maestoso: the hymn (12 bars)
Pattern %Hymn:
  4:
  2d*4 a*4 d*5 | 4f#*5_ | 2g*5 f#*5 e*5 | 4e*5_ |
  2a*4 d*5 f#*5 | 3f#*5 e*5 | 2d*5 e*5 f#*5 | 4e*5_ |
  2f#*5 g*5 a*5 | 3b*5 a*5 | 2a*5 g*5 e*5 | 4d*5$fermata |

Pattern %HarmonyHymn:
  4: 4D_ | 4D_ | 4G_ | 4A_ | 4D_ | 4Bm_ | 4G_ | 4A_ | 4D_ | 4G_ | 4A7_ | 4D$fermata |

// ================================================================ tracks

Traccia Violins [Violins]:

Box Violins "Lento" |0:
  tempo=66 4: 4r | 4r | 4r | 4r | 4r | 4r | 4r | 4r |

Box Violins "Allegro agitato" |32:
  tempo=120 %Storm

Box Violins "Tranquillo" |96:
  tempo=80 4: 45@ 4F_ | 4Dm_ | 4Bb_ | 4C_ | 4F_ | 4Am_ | 4Gm_ | 4A7_ |

Box Violins "Maestoso" |128:
  tempo=96 4: 108@ %Hymn+12

Traccia Tremolo Strings [Tremolos]:

Box Tremolo Strings "Lento" |0:
  4: 30@ >> 4Dm_ | 4Dm_ | 4Bb_ | 4Gm_ | 4Dm_ | 4Gm_ | 4A7_ | 4A7_ 85@

Box Tremolo Strings "Tranquillo" |96:
  4: 38@ 4F_ | 4Dm_ | 4Bb_ | 4C_ | 4F_ | 4Am_ | 4Gm_ | 4A7_ |

Box Tremolo Strings "Maestoso" |128:
  4: 105@ %HarmonyHymn

Traccia Cello [Cello]:

Box Cello "Lento" |0:
  // the answer to the horn call
  4: 4r | 4r | 4r | 4r | 72@ 2a*3 f*3 d*3 | g*3 bb*3 a*3 g*3 | 2f*3 e*3 d*3 | 4c#*3_ |

Box Cello "Allegro agitato" |32:
  8: 95@ 8(d*3) | 8(d*3) | 8(g*2) | 8(a*2) | 8(d*3) | 8(bb*2) | 4(g*2) 4(a*2) | 8(d*3) |
  8(f*2) | 8(c*3) | 8(d*3) | 8(a*2) | 8(bb*2) | 8(g*2) | 8(a*2) | 8(a*2) |

Box Cello "Tranquillo" |96:
  // the song of the solo cello
  4: 80@ 3c*4 a*3 | 2d*4 f*4 e*4 | 3d*4 c*4 | 4c*4_ |
  2a*3 c*4 f*4 | 3e*4 c*4 | 2d*4 bb*3 g*3 | 4c#*4_ |

Box Cello "Maestoso" |128:
  4: 105@ 2d*3 2d*3 | 2d*3 2d*3 | 2g*2 2g*2 | 2a*2 2a*2 | 2d*3 2d*3 | 2b*2 2b*2 |
  2g*2 2g*2 | 2a*2 2a*2 | 2d*3 2d*3 | 2g*2 2g*2 | 2a*2 2a*2 | 4d*3$fermata |

Traccia DoubleBasses [DoubleBasses]:

Box DoubleBasses "Lento" |0:
  4: 35@ >> 4d*2_ | 4d*2_ | 4bb*1_ | 4g*1_ | 4d*2_ | 4g*1_ | 4a*1_ | 4a*1_ 85@

Box DoubleBasses "Allegro agitato" |32:
  4: 100@ 4d*2 | 4d*2 | 4g*1 | 4a*1 | 4d*2 | 4bb*1 | 2g*1 2a*1 | 4d*2 |
  4f*1 | 4c*2 | 4d*2 | 4a*1 | 4bb*1 | 4g*1 | 4a*1 | 4a*1 |

Box DoubleBasses "Tranquillo" |96:
  4: 45@ 4f*1_ | 4d*2_ | 4bb*1_ | 4c*2_ | 4f*1_ | 4a*1_ | 4g*1_ | 4a*1_ |

Box DoubleBasses "Maestoso" |128:
  // the rallentando of the last two bars (no dynamic change inside the ramp)
  4: 108@ 4d*2 | 4d*2 | 4g*1 | 4a*1 | 4d*2 | 4b*1 | 4g*1 | 4a*1 | 4d*2 | 4g*1 |
  tempo=96 << 4a*1 | tempo=60 4d*2$fermata |

Traccia Flute [Flute]:

Box Flute "Allegro agitato" |32:
  // with the violins in the second half of the storm
  8: 8r | 8r | 8r | 8r | 8r | 8r | 8r | 8r |
  92@ c*5 f*5 a*5 c*6 a*5 f*5 c*5 a*4 |
  2g*4 c*5 e*5 4g*5 |
  f*5 a*5 d*6 a*5 f*5 d*5 a*4 f*4 |
  2e*4 a*4 c#*5 4e*5 |
  d*5 f*5 bb*5 d*6 c*6 bb*5 a*5 g*5 |
  f*5 g*5 bb*5 d*6 2c*6 2bb*5 |
  16: a*5 g*5 f*5 e*5 d*5 c#*5 d*5 e*5 8: 2f*5 2e*5 |
  4c#*5_ 4a*4 |

Box Flute "Tranquillo" |96:
  // the echo of the cello's song
  4: 4r | 4r | 4r | 4r | 4r | 65@ 2r e*5 c*5 | 2bb*4 g*4 d*5 | 4c#*5_ |

Box Flute "Maestoso" |128:
  4: 100@ %Hymn+12

Traccia Oboe [Oboe]:

Box Oboe "Allegro agitato" |32:
  // the long notes over the storm
  4: 85@ 4f*5_ | 4f*5_ | 4d*5_ | 4e*5_ | 4f*5_ | 4f*5_ | 2d*5 2e*5 | 4d*5 |
  4c*5_ | 4e*5_ | 4f*5_ | 4e*5_ | 4d*5_ | 4d*5_ | 4c#*5_ | 4e*5_ |

Box Oboe "Maestoso" |128:
  4: 95@ %Hymn

Traccia Horns [Horns]:

Box Horns "Lento" |0:
  // the call
  4: 4r | 4r | 82@ 2d*4 a*4 d*5 | 4d*5_ | 4r | 78@ 2bb*3 g*3 d*4 | 4c#*4_ | 4r |

Box Horns "Allegro agitato" |32:
  4: 80@ %HarmonyStorm

Box Horns "Maestoso" |128:
  // the call becomes the hymn
  4: 110@ %Hymn-12

Traccia Trumpets [Trumpets]:

Box Trumpets "Allegro agitato" |32:
  4: 108@ %AccentsStorm

Box Trumpets "Maestoso" |128:
  4: 112@ %Hymn

Traccia Trombones [Trombones]:

Box Trombones "Allegro agitato" |32:
  4: 104@ %AccentsStorm

Box Trombones "Maestoso" |128:
  4: 108@ %HarmonyHymn

Traccia Timpani [Timpani]:

Box Timpani "Lento" |0:
  16: 40@ >> 16(d*2) | 16(d*2) 80@ | 4: 4r | 4r | 4r | 4r |
  16: 50@ >> 16(a*1) | 16(a*1) 105@ |

Box Timpani "Allegro agitato" |32:
  4: 110@ d*2 3r | 4r | 4r | a*1 3r | d*2 3r | 4r | 2r a*1 a*1 | d*2 3r |
  4r | 4r | d*2 3r | a*1 3r | 4r | 4r | 16: 70@ >> 16(a*1) | 16(a*1) 112@ |

Box Timpani "Tranquillo" |96:
  4: 4r | 4r | 4r | 4r | 4r | 4r | 4r | 16: 35@ >> 16(a*1) 70@ |

Box Timpani "Maestoso" |128:
  4: 112@ d*2 3r | 4r | 4r | a*1 3r | d*2 3r | 4r | 4r | a*1 a*1 a*1 a*1 |
  d*2 3r | 4r | 16: 80@ >> 16(a*1) | 16(d*2) 118@ |

Traccia Harp [Harp]:

Box Harp "Tranquillo" |96:
  8: 72@
  f*2 c*3 f*3 a*3 c*4 a*3 f*3 c*3 |
  d*2 a*2 d*3 f*3 a*3 f*3 d*3 a*2 |
  bb*1 f*2 bb*2 d*3 f*3 d*3 bb*2 f*2 |
  c*2 g*2 c*3 e*3 g*3 e*3 c*3 g*2 |
  f*2 c*3 f*3 a*3 c*4 a*3 f*3 c*3 |
  a*1 e*2 a*2 c*3 e*3 c*3 a*2 e*2 |
  g*1 d*2 g*2 bb*2 d*3 bb*2 g*2 d*2 |
  a*1 e*2 a*2 c#*3 e*3 g*3 e*3 c#*3 |

Box Harp "Maestoso" |128:
  16: 88@
  d*2 f#*2 a*2 d*3 f#*3 a*3 d*4 f#*4 a*4 d*5 f#*5 a*5 d*6 a*5 f#*5 d*5 |
  4: 4D_ |
  16: g*2 b*2 d*3 g*3 b*3 d*4 g*4 b*4 d*5 g*5 b*5 d*6 g*6 d*6 b*5 g*5 |
  16: a*2 c#*3 e*3 a*3 c#*4 e*4 a*4 c#*5 e*5 a*5 c#*6 e*6 a*6 e*6 c#*6 a*5 |
  4: 4D_ | 4Bm_ | 4G_ | 4A_ |
  16: d*2 f#*2 a*2 d*3 f#*3 a*3 d*4 f#*4 a*4 d*5 f#*5 a*5 d*6 f#*6 a*6 d*7 |
  4: 4G_ | 4A7_ | 4D$fermata |

// ================================================================ sounds

Plugin Tremolo Strings:
  ref="sfz:~/Strumenti/sfz/gm-bank/Discord GM/Melodic/045-Tremolo Strings.sfz"

Plugin Cello:
  ref="sfz:~/Strumenti/sfz/cello/Karoryfer_Bigcat_cello/Programs/01- Bowed (velocity layer).sfz"

Plugin DoubleBasses:
  ref="sfz:~/Strumenti/sfz/contrabbasso/dsmolken_double_bass/d_smolken_rubner_bass_arco.sfz"

Plugin Harp:
  ref="sfz:~/Strumenti/sfz/arpa/ConcertHarp-SFZ+FLAC-20200702/ConcertHarp-20200702.sfz"

Effetti Violins:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=22

Effetti Tremolo Strings:
  compressore: soglia=-26 rapporto=2 attacco=40 rilascio=300 guadagno=10
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=22

Effetti Cello:
  compressore: soglia=-24 rapporto=2 attacco=30 rilascio=300 guadagno=4
  riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=20

Effetti DoubleBasses:
  compressore: soglia=-24 rapporto=2 attacco=30 rilascio=300 guadagno=6
  riverbero: stanza=75 smorzamento=50 ampiezza=100 mix=14

Effetti Harp:
  riverbero: stanza=80 smorzamento=40 ampiezza=100 mix=24

Effetti Horns:
  riverbero: stanza=85 smorzamento=40 ampiezza=100 mix=24

Effetti Trumpets:
  riverbero: stanza=85 smorzamento=40 ampiezza=100 mix=20

Effetti Trombones:
  riverbero: stanza=85 smorzamento=40 ampiezza=100 mix=20

Effetti Timpani:
  riverbero: stanza=85 smorzamento=50 ampiezza=100 mix=22

Catena master:
  plugin: mix=25 livello=0 ref="lv2:urn:ardour:a-reverb"
  eq: bassi=1 medi=0 alti=1
  compressore: soglia=-18 rapporto=1.5 attacco=40 rilascio=300 guadagno=2
  limiter: guadagno=4 tetto=-1 rilascio=200

// ================================================================ mixer

Mixer Violins:
  volume: 88 pan: -0.35 mute: no solo: no

Mixer Tremolo Strings:
  volume: 85 pan: -0.15 mute: no solo: no

Mixer Cello:
  volume: 100 pan: 0.3 mute: no solo: no

Mixer DoubleBasses:
  volume: 95 pan: 0.45 mute: no solo: no

Mixer Flute:
  volume: 90 pan: -0.1 mute: no solo: no

Mixer Oboe:
  volume: 92 pan: 0.1 mute: no solo: no

Mixer Horns:
  volume: 72 pan: -0.25 mute: no solo: no

Mixer Trumpets:
  volume: 75 pan: 0.2 mute: no solo: no

Mixer Trombones:
  volume: 62 pan: 0.35 mute: no solo: no

Mixer Timpani:
  volume: 92 pan: 0 mute: no solo: no

Mixer Harp:
  volume: 90 pan: -0.4 mute: no solo: no
