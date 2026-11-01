// Symphony No. 1 in D minor, "From Darkness to Light": an example symphony in four movements.
//
// Box version: every section of every track is a box of the Structure view
// (`Box Track "Name" |beat:`): the tracks have no text, and the position of
// each box is in its header. Open it in the app to see the blocks in a row.
//
// Original music, written to show ST-language with a full orchestra:
// woodwinds (flute, oboe, clarinet, bassoon), horns and trumpet, timpani and
// strings (first and second violins, violas, cellos, double basses).
//
//   I    Allegro con fuoco   D minor  (32 bars)  exposition of two themes
//                                     (the second in F major), development on
//                                     the dominant, recapitulation and ending in D major
//   II   Adagio              B flat   (16 bars)  the song of the oboe, then of the violins
//   III  Scherzo: Presto     D minor  (16 bars)  staccato theme, passed from flutes to violins
//   IV   Finale: Allegro con brio  D major (32 bars)  fanfare, fugato (cellos, violas,
//                                     second violins, first violins), chorale,
//                                     coda with the rallentando and the fermata
//
// What's inside:
//   - keys changing from one movement to the next (key=Dm, F, Bb, D): each
//     pattern sets its own, and accidentals are not written;
//   - tempo changes between movements (tempo=) on the timpani track, and the
//     final rallentando (tempo=126 << ... tempo=56);
//   - the fugato: the same subject entering in staggered bars, on the right
//     instrument and octave;
//   - dynamics: a volume crescendo in the development (vol=60 >> ... vol=100),
//     hairpins, text markings ($"Adagio") and the fermata ($fermata);
//   - instruments defined in the file with their General MIDI program (flute,
//     oboe, clarinet, bassoon, horn, timpani, strings);
//   - patterns generated per section: held chords, arpeggios, basses, timpani
//     rolls, staccato chords.
// The Mixer panel has a block for every section of the orchestra.

ST: 2.6
Tempo: 132 BPM
Metrica: 4/4
Tonalita: Dm

Strumento Flute:
  program=73 percussione=no ottava=5 range=72-100 poly=no voicing=monophonic

Strumento Oboe:
  program=68 percussione=no ottava=5 range=58-93 poly=no voicing=monophonic

Strumento Clarinet:
  program=71 percussione=no ottava=4 range=50-94 poly=no voicing=monophonic

Strumento Bassoon:
  program=70 percussione=no ottava=3 range=34-72 poly=no voicing=monophonic

Strumento Horns:
  program=60 percussione=no ottava=4 range=41-77 poly=si voicing=spread

Strumento Timpani:
  program=47 percussione=no ottava=2 range=28-60 poly=no voicing=monophonic

Strumento Violins1:
  program=48 percussione=no ottava=5 range=55-103 poly=no voicing=monophonic

Strumento Violins2:
  program=48 percussione=no ottava=5 range=55-103 poly=no voicing=monophonic

Strumento Violas:
  program=48 percussione=no ottava=4 range=48-91 poly=si voicing=spread

Strumento Cellos:
  program=42 percussione=no ottava=3 range=36-76 poly=no voicing=monophonic

Strumento DoubleBasses:
  program=43 percussione=no ottava=2 range=28-60 poly=no voicing=monophonic

Pattern %R1:
  4: 4r |

Pattern %I_ThA:
  key=Dm 8: 100@
  2d*5 f*5 a*5 2d*6 2c*6 |
  b*5 a*5 g*5 f*5 2e*5 2d*5 |
  2e*5 g*5 a*5 2c#*6 2a*5 |
  4d*6 3a*5 r |
  2b*5 d*6 f*6 2b*6 2a*6 |
  g*6 f*6 e*6 d*6 2c*6 b*5 a*5 |
  2g*5 a*5 c#*6 2e*6 2a*5 |
  6d*6 2r |

Pattern %I_ThA_down:
  key=Dm 8: 100@
  2d*4 f*4 a*4 2d*5 2c*5 |
  b*4 a*4 g*4 f*4 2e*4 2d*4 |
  2e*4 g*4 a*4 2c#*5 2a*4 |
  4d*5 3a*4 r |
  2b*4 d*5 f*5 2b*5 2a*5 |
  g*5 f*5 e*5 d*5 2c*5 b*4 a*4 |
  2g*4 a*4 c#*5 2e*5 2a*4 |
  6d*5 2r |

Pattern %I_ThAr:
  key=Dm 8: 100@
  2d*5 f*5 a*5 2d*6 2c*6 |
  b*5 a*5 g*5 f*5 2e*5 2d*5 |
  2e*5 g*5 a*5 2c#*6 2a*5 |
  4d*6 3a*5 r |
  2b*5 d*6 f*6 2b*6 2a*6 |
  g*6 f*6 e*6 d*6 2c*6 b*5 a*5 |
  2g*5 a*5 c#*6 2e*6 2a*5 |
  8d*6$fermata |

Pattern %I_ThAr_down:
  key=Dm 8: 100@
  2d*4 f*4 a*4 2d*5 2c*5 |
  b*4 a*4 g*4 f*4 2e*4 2d*4 |
  2e*4 g*4 a*4 2c#*5 2a*4 |
  4d*5 3a*4 r |
  2b*4 d*5 f*5 2b*5 2a*5 |
  g*5 f*5 e*5 d*5 2c*5 b*4 a*4 |
  2g*4 a*4 c#*5 2e*5 2a*4 |
  8d*5$fermata |

Pattern %I_ThB1_down:
  key=F 8: 80@
  2a*4 c*5 f*5 2e*5 2d*5 |
  2c*5 e*5 g*5 2e*5 2c*5 |
  2d*5 f*5 a*5 2g*5 2f*5 |
  2b*4 d*5 f*5 4d*5 |

Pattern %I_ThB2_down:
  key=F 8: 80@
  2a*4 c*5 f*5 2e*5 2c*5 |
  2b*4 d*5 g*5 2f*5 2d*5 |
  2c*5 e*5 g*5 2b*5 2g*5 |
  6f*5 2r |

Pattern %I_ThB2:
  key=F 8: 75@
  2a*5 c*6 f*6 2e*6 2c*6 |
  2b*5 d*6 g*6 2f*6 2d*6 |
  2c*6 e*6 g*6 2b*6 2g*6 |
  6f*6 2r |

Pattern %I_Dev:
  key=Dm 8: 95@
  2g*5 b*5 d*6 2g*6 2f*6 |
  2g*5 b*5 d*6 2f*6 2e*6 |
  2a*5 c#*6 e*6 2a*6 2g*6 |
  g*6 f*6 e*6 d*6 2c#*6 2a*5 |
  2b*5 d*6 f*6 2b*6 2a*6 |
  g*6 f*6 e*6 d*6 2c*6 b*5 a*5 |
  2a*5 d*6 e*6 2a*6 2d*7 |
  6c#*6 2r |

Pattern %rootsF_IA_08_90:
  key=Dm 4: 90@
  d*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |
  b*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |

Pattern %rootsF_IB_08_55:
  key=F 4: 55@
  f*2'1 |
  c*2'1 |
  d*2'1 |
  b*2'1 |
  f*2'1 |
  g*2'1 |
  c*2'1 |
  f*2'1 |

Pattern %rootsF_ID_08_70:
  key=Dm 4: 70@
  g*2'1 |
  e*2'1 |
  a*2'1 |
  a*2'1 |
  b*2'1 |
  g*2'1 |
  a*2'1 |
  a*2'1 |

Pattern %rootsF_IR_08_95:
  key=Dm 4: 95@
  d*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |
  b*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |

Pattern %chords_IA_08_100:
  key=Dm 4: 100@
  Dm'1 |
  Gm'1 |
  A7'1 |
  Dm'1 |
  Bb'1 |
  Gm'1 |
  A7'1 |
  Dm'1 |

Pattern %chords_IB_08_55:
  key=F 4: 55@
  F'1 |
  C'1 |
  Dm'1 |
  Bb'1 |
  F'1 |
  Gm'1 |
  C7'1 |
  F'1 |

Pattern %chords_ID_08_80:
  key=Dm 4: 80@
  Gm'1 |
  Em7b5'1 |
  A7'1 |
  A7'1 |
  Bb'1 |
  Gm'1 |
  Asus4'1 |
  A7'1 |

Pattern %chords_IR_08_105:
  key=Dm 4: 105@
  Dm'1 |
  Gm'1 |
  A7'1 |
  Dm'1 |
  Bb'1 |
  Gm'1 |
  A7'1 |
  D'1 |

Pattern %hit_IA_08_100:
  key=Dm 4: 100@
  d*2 r d*2 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |
  b*1 r b*1 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |

Pattern %hitS_IB_08_45:
  key=F 4: 45@
  f*1 r r r |
  c*2 r r r |
  d*2 r r r |
  b*1 r r r |
  f*1 r r r |
  g*1 r r r |
  c*2 r r r |
  f*1 r r r |

Pattern %roll_ID_08_70:
  key=Dm 16: 70@
  g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 |
  e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 e*1 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |
  b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 b*1 |
  g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 g*1 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |

Pattern %hit_IR_08_105:
  key=Dm 4: 105@
  d*2 r d*2 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |
  b*1 r b*1 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |

Pattern %arp_IA_08_70:
  key=Dm 8: 70@
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |

Pattern %arp_IB_08_55:
  key=F 8: 55@
  c*5 f*5 a*5 f*5 c*5 f*5 a*5 f*5 |
  c*5 e*5 g*5 e*5 c*5 e*5 g*5 e*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  c*5 f*5 a*5 f*5 c*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  c*5 e*5 g*5 b*5 g*5 e*5 g*5 e*5 |
  c*5 f*5 a*5 f*5 c*5 f*5 a*5 f*5 |

Pattern %arp_ID_08_80:
  key=Dm 8: 80@
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  e*5 g*5 b*5 d*6 b*5 g*5 b*5 g*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  a*4 d*5 e*5 d*5 a*4 d*5 e*5 d*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |

Pattern %arp_IR_08_85:
  key=Dm 8: 85@
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f#*5 a*5 f#*5 d*5 f#*5 a*5 f#*5 |

Pattern %chords_IA_08_78:
  key=Dm 4: 78@
  Dm'1 |
  Gm'1 |
  A7'1 |
  Dm'1 |
  Bb'1 |
  Gm'1 |
  A7'1 |
  Dm'1 |

Pattern %chords_IB_08_50:
  key=F 4: 50@
  F'1 |
  C'1 |
  Dm'1 |
  Bb'1 |
  F'1 |
  Gm'1 |
  C7'1 |
  F'1 |

Pattern %chords_ID_08_75:
  key=Dm 4: 75@
  Gm'1 |
  Em7b5'1 |
  A7'1 |
  A7'1 |
  Bb'1 |
  Gm'1 |
  Asus4'1 |
  A7'1 |

Pattern %chords_IR_08_85:
  key=Dm 4: 85@
  Dm'1 |
  Gm'1 |
  A7'1 |
  Dm'1 |
  Bb'1 |
  Gm'1 |
  A7'1 |
  D'1 |

Pattern %rootsC_IA_08_90:
  key=Dm 4: 90@
  d*2 d*3 d*2 d*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |
  b*2 b*3 b*2 b*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |

Pattern %rootsC_IB_08_60:
  key=F 4: 60@
  f*2 f*3 f*2 f*3 |
  c*2 c*3 c*2 c*3 |
  d*2 d*3 d*2 d*3 |
  b*2 b*3 b*2 b*3 |
  f*2 f*3 f*2 f*3 |
  g*2 g*3 g*2 g*3 |
  c*2 c*3 c*2 c*3 |
  f*2 f*3 f*2 f*3 |

Pattern %rootsC_ID_08_85:
  key=Dm 4: 85@
  g*2 g*3 g*2 g*3 |
  e*2 e*3 e*2 e*3 |
  a*2 a*3 a*2 a*3 |
  a*2 a*3 a*2 a*3 |
  b*2 b*3 b*2 b*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  a*2 a*3 a*2 a*3 |

Pattern %rootsC_IR_08_95:
  key=Dm 4: 95@
  d*2 d*3 d*2 d*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |
  b*2 b*3 b*2 b*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |

Pattern %rootsB_IA_08_92:
  key=Dm 4: 92@
  d*2'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |
  b*1'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |

Pattern %rootsB_IB_08_60:
  key=F 4: 60@
  f*1'1 |
  c*2'1 |
  d*2'1 |
  b*1'1 |
  f*1'1 |
  g*1'1 |
  c*2'1 |
  f*1'1 |

Pattern %rootsB_ID_08_85:
  key=Dm 4: 85@
  g*1'1 |
  e*1'1 |
  a*1'1 |
  a*1'1 |
  b*1'1 |
  g*1'1 |
  a*1'1 |
  a*1'1 |

Pattern %rootsB_IR_08_98:
  key=Dm 4: 98@
  d*2'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |
  b*1'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |

Pattern %II_Oboe:
  key=Bb 8: 80@
  4f*5 2d*5 2c*5 |
  2b*4 d*5 g*5 4f*5 |
  4e*5 2g*5 2b*5 |
  4a*5 2c*6 2e*6 |
  4d*6 2b*5 2f*5 |
  2g*5 b*5 d*6 4c*6 |
  2e*6 2d*6 2c*6 2a*5 |
  6b*5 2r |

Pattern %II_Violin:
  key=Bb 8: 78@
  4g*5 2e*5 2g*5 |
  4f*5 2d*5 2f*5 |
  4e*5 2g*5 2c*6 |
  2a*5 2c*6 4e*6 |
  4d*6 2f*6 2a*5 |
  4b*5 2g*5 2d*5 |
  2c*6 2e*6 2d*6 2c*6 |
  8b*5$fermata |

Pattern %II_Violin_down:
  key=Bb 8: 70@
  4g*4 2e*4 2g*4 |
  4f*4 2d*4 2f*4 |
  4e*4 2g*4 2c*5 |
  2a*4 2c*5 4e*5 |
  4d*5 2f*5 2a*4 |
  4b*4 2g*4 2d*4 |
  2c*5 2e*5 2d*5 2c*5 |
  8b*4$fermata |

Pattern %rootsF_II1_08_55:
  key=Bb 4: 55@
  b*2'1 |
  g*2'1 |
  e*2'1 |
  f*2'1 |
  b*2'1 |
  g*2'1 |
  c*2'2 f*2'2 |
  b*2'1 |

Pattern %rootsF_II2_08_58:
  key=Bb 4: 58@
  e*2'1 |
  d*2'1 |
  c*2'1 |
  f*2'1 |
  d*2'1 |
  g*2'1 |
  c*2'2 f*2'2 |
  b*2'1 |

Pattern %chords_II1_08_50:
  key=Bb 4: 50@
  Bb'1 |
  Gm'1 |
  Eb'1 |
  F7'1 |
  Bb'1 |
  Gm'1 |
  Cm7'2 F7'2 |
  Bb'1 |

Pattern %chords_II2_08_55:
  key=Bb 4: 55@
  Eb'1 |
  Bb/D'1 |
  Cm'1 |
  F7'1 |
  Dm'1 |
  Gm'1 |
  Cm7'2 F7'2 |
  Bb'1 |

Pattern %arp_II1_08_48:
  key=Bb 8: 48@
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  e*5 g*5 b*5 g*5 e*5 g*5 b*5 g*5 |
  a*4 c*5 e*5 f*5 e*5 c*5 e*5 c*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  c*5 e*5 g*5 b*5 a*4 c*5 e*5 f*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |

Pattern %chords_II1_08_45:
  key=Bb 4: 45@
  Bb'1 |
  Gm'1 |
  Eb'1 |
  F7'1 |
  Bb'1 |
  Gm'1 |
  Cm7'2 F7'2 |
  Bb'1 |

Pattern %arp_II2_08_50:
  key=Bb 8: 50@
  e*5 g*5 b*5 g*5 e*5 g*5 b*5 g*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  c*5 e*5 g*5 e*5 c*5 e*5 g*5 e*5 |
  a*4 c*5 e*5 f*5 e*5 c*5 e*5 c*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  c*5 e*5 g*5 b*5 a*4 c*5 e*5 f*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |

Pattern %rootsW_II1_08_70:
  key=Bb 4: 70@
  b*2'1 |
  g*2'1 |
  e*2'1 |
  f*2'1 |
  b*2'1 |
  g*2'1 |
  c*2'2 f*2'2 |
  b*2'1 |

Pattern %rootsW_II2_08_72:
  key=Bb 4: 72@
  e*2'1 |
  d*2'1 |
  c*2'1 |
  f*2'1 |
  d*2'1 |
  g*2'1 |
  c*2'2 f*2'2 |
  b*2'1 |

Pattern %rootsB_II1_08_60:
  key=Bb 4: 60@
  b*1'1 |
  g*1'1 |
  e*1'1 |
  f*1'1 |
  b*1'1 |
  g*1'1 |
  c*2'2 f*1'2 |
  b*1'1 |

Pattern %rootsB_II2_08_62:
  key=Bb 4: 62@
  e*1'1 |
  d*2'1 |
  c*2'1 |
  f*1'1 |
  d*2'1 |
  g*1'1 |
  c*2'2 f*1'2 |
  b*1'1 |

Pattern %III_S1:
  key=Dm 8: 95@
  d*5 f*5 a*5 f*5 d*5 f*5 2a*5 |
  d*6 c*6 b*5 a*5 2g*5 2f*5 |
  e*5 g*5 a*5 g*5 e*5 g*5 2c#*6 |
  2d*6 2a*5 2f*5 2d*5 |
  g*5 b*5 d*6 b*5 g*5 b*5 2d*6 |
  f*5 a*5 d*6 a*5 f*5 a*5 2d*6 |
  e*5 g*5 c#*6 e*6 2a*6 2g*6 |
  4d*6 4r |

Pattern %III_S2:
  key=Dm 8: 100@
  b*5 d*6 f*6 d*6 b*5 d*6 2f*6 |
  g*5 b*5 d*6 b*5 g*5 b*5 2d*6 |
  f*6 d*6 b*5 d*6 f*6 d*6 2b*5 |
  e*6 g*6 e*6 c#*6 2a*5 2e*5 |
  d*6 f*6 a*6 f*6 d*6 f*6 2a*6 |
  g*6 b*6 d*7 b*6 g*6 b*6 2d*7 |
  a*6 g*6 e*6 c#*6 a*5 g*5 2e*5 |
  4d*5 4r |

Pattern %stab_III2_08_75:
  key=Dm 4: 75@
  r Bb! r Bb! |
  r Gm! r Gm! |
  r Bb! r Bb! |
  r A7! r A7! |
  r Dm! r Dm! |
  r Gm! r Gm! |
  r A7! r A7! |
  r Dm! r Dm! |

Pattern %rootsF_III1_08_75:
  key=Dm 4: 75@
  d*2'1 |
  d*2'1 |
  a*2'1 |
  d*2'1 |
  g*2'1 |
  d*2'1 |
  a*2'1 |
  d*2'1 |

Pattern %rootsF_III2_08_80:
  key=Dm 4: 80@
  b*2'1 |
  g*2'1 |
  b*2'1 |
  a*2'1 |
  d*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |

Pattern %stab_III1_08_70:
  key=Dm 4: 70@
  r Dm! r Dm! |
  r Dm! r Dm! |
  r A7! r A7! |
  r Dm! r Dm! |
  r Gm! r Gm! |
  r Dm! r Dm! |
  r A7! r A7! |
  r Dm! r Dm! |

Pattern %stab_III2_08_90:
  key=Dm 4: 90@
  r Bb! r Bb! |
  r Gm! r Gm! |
  r Bb! r Bb! |
  r A7! r A7! |
  r Dm! r Dm! |
  r Gm! r Gm! |
  r A7! r A7! |
  r Dm! r Dm! |

Pattern %hit_III1_08_90:
  key=Dm 4: 90@
  d*2 r d*2 r |
  d*2 r d*2 r |
  a*1 r a*1 r |
  d*2 r d*2 r |
  g*1 r g*1 r |
  d*2 r d*2 r |
  a*1 r a*1 r |
  d*2 r d*2 r |

Pattern %hit_III2_08_95:
  key=Dm 4: 95@
  b*1 r b*1 r |
  g*1 r g*1 r |
  b*1 r b*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |

Pattern %arp_III1_08_65:
  key=Dm 8: 65@
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |

Pattern %arp_III2_08_72:
  key=Dm 8: 72@
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  a*4 c#*5 e*5 g*5 e*5 c#*5 e*5 c#*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |

Pattern %stab_III2_08_78:
  key=Dm 4: 78@
  r Bb! r Bb! |
  r Gm! r Gm! |
  r Bb! r Bb! |
  r A7! r A7! |
  r Dm! r Dm! |
  r Gm! r Gm! |
  r A7! r A7! |
  r Dm! r Dm! |

Pattern %rootsC_III1_08_85:
  key=Dm 4: 85@
  d*2 d*3 d*2 d*3 |
  d*2 d*3 d*2 d*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |
  g*2 g*3 g*2 g*3 |
  d*2 d*3 d*2 d*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |

Pattern %rootsC_III2_08_90:
  key=Dm 4: 90@
  b*2 b*3 b*2 b*3 |
  g*2 g*3 g*2 g*3 |
  b*2 b*3 b*2 b*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |

Pattern %rootsB_III1_08_85:
  key=Dm 4: 85@
  d*2'1 |
  d*2'1 |
  a*1'1 |
  d*2'1 |
  g*1'1 |
  d*2'1 |
  a*1'1 |
  d*2'1 |

Pattern %rootsB_III2_08_88:
  key=Dm 4: 88@
  b*1'1 |
  g*1'1 |
  b*1'1 |
  a*1'1 |
  d*2'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |

Pattern %IV_Theme:
  key=D 8: 100@
  d*5 f*5 a*5 d*6 2f*6 2a*6 |
  g*6 f*6 e*6 d*6 2b*5 2g*5 |
  2c*6 e*6 g*6 2a*6 2e*6 |
  4d*6 2a*5 2f*5 |
  2b*5 d*6 f*6 2b*6 2a*6 |
  2g*6 b*6 a*6 2g*6 2f*6 |
  2a*5 c*6 e*6 2g*6 2e*6 |
  4d*6 4r |

Pattern %IV_Theme_down:
  key=D 8: 100@
  d*4 f*4 a*4 d*5 2f*5 2a*5 |
  g*5 f*5 e*5 d*5 2b*4 2g*4 |
  2c*5 e*5 g*5 2a*5 2e*5 |
  4d*5 2a*4 2f*4 |
  2b*4 d*5 f*5 2b*5 2a*5 |
  2g*5 b*5 a*5 2g*5 2f*5 |
  2a*4 c*5 e*5 2g*5 2e*5 |
  4d*5 4r |

Pattern %IV_Chorale:
  key=D 8: 90@
  2g*5 b*5 d*6 2g*6 2f*6 |
  2a*5 d*6 f*6 4a*6 |
  2g*5 b*5 e*6 2d*6 2b*5 |
  2c*6 e*6 g*6 4a*6 |
  2d*6 f*6 b*6 2a*6 2f*6 |
  2g*5 b*5 d*6 2g*6 2b*6 |
  2e*6 g*6 a*6 2c*7 2a*6 |
  6d*6 2r |

Pattern %IV_Chorale_down:
  key=D 8: 85@
  2g*4 b*4 d*5 2g*5 2f*5 |
  2a*4 d*5 f*5 4a*5 |
  2g*4 b*4 e*5 2d*5 2b*4 |
  2c*5 e*5 g*5 4a*5 |
  2d*5 f*5 b*5 2a*5 2f*5 |
  2g*4 b*4 d*5 2g*5 2b*5 |
  2e*5 g*5 a*5 2c*6 2a*5 |
  6d*5 2r |

Pattern %IV_SubjCellos:
  key=D 8: 85@
  d*3 e*3 f*3 g*3 2a*3 2f*3 |
  b*3 a*3 g*3 f*3 2e*3 2d*3 |

Pattern %IV_RispVle:
  key=D 8: 85@
  a*3 b*3 c*4 d*4 2e*4 2c*4 |
  f*4 e*4 d*4 c*4 2b*3 2a*3 |

Pattern %IV_SubjV2:
  key=D 8: 88@
  d*5 e*5 f*5 g*5 2a*5 2f*5 |
  b*5 a*5 g*5 f*5 2e*5 2d*5 |

Pattern %IV_RispV1:
  key=D 8: 90@
  a*5 b*5 c*6 d*6 2e*6 2c*6 |
  f*6 e*6 d*6 c*6 2b*5 2a*5 |

Pattern %rootsF_IVM_08_90:
  key=D 4: 90@
  d*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |
  b*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |

Pattern %rootsF_IVF_08_70:
  key=D 4: 70@
  d*2'1 |
  d*2'1 |
  a*2'1 |
  a*2'1 |
  d*2'1 |
  d*2'1 |
  a*2'1 |
  a*2'1 |

Pattern %rootsF_IVC_08_80:
  key=D 4: 80@
  g*2'1 |
  f*2'1 |
  e*2'1 |
  a*2'1 |
  b*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |

Pattern %rootsF_IVK_08_95:
  key=D 4: 95@
  d*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |
  b*2'1 |
  g*2'1 |
  a*2'1 |
  d*2'1 |

Pattern %chords_IVM_08_100:
  key=D 4: 100@
  D'1 |
  G'1 |
  A7'1 |
  D'1 |
  Bm'1 |
  G'1 |
  A7'1 |
  D'1 |

Pattern %chords_IVF_08_65:
  key=D 4: 65@
  D'1 |
  D'1 |
  A'1 |
  A'1 |
  D'1 |
  D'1 |
  A'1 |
  A7'1 |

Pattern %chords_IVC_08_80:
  key=D 4: 80@
  G'1 |
  D/F#'1 |
  Em'1 |
  A7'1 |
  Bm'1 |
  G'1 |
  A7'1 |
  D'1 |

Pattern %chords_IVK_08_105:
  key=D 4: 105@
  D'1 |
  G'1 |
  A7'1 |
  D'1 |
  Bm'1 |
  G'1 |
  A7'1 |
  D'1 |

Pattern %hit_IVM_08_100:
  key=D 4: 100@
  d*2 r d*2 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |
  b*1 r b*1 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |

Pattern %roll_IVF_08_60:
  key=D 16: 60@
  d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 |
  d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |
  d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 |
  d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 d*2 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |
  a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 a*1 |

Pattern %hitS_IVC_08_60:
  key=D 4: 60@
  g*1 r r r |
  f*1 r r r |
  e*1 r r r |
  a*1 r r r |
  b*1 r r r |
  g*1 r r r |
  a*1 r r r |
  d*2 r r r |

Pattern %hit_IVK_04_105:
  key=D 4: 105@
  d*2 r d*2 r |
  g*1 r g*1 r |
  a*1 r a*1 r |
  d*2 r d*2 r |

Pattern %hit_IVK_47:
  key=D 4:
  b*1 r b*1 r |
  g*1 r g*1 r |
  a*1 r a*1 r |

Pattern %arp_IVM_08_75:
  key=D 8: 75@
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  e*5 g*5 a*5 c*6 a*5 g*5 a*5 g*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  e*5 g*5 a*5 c*6 a*5 g*5 a*5 g*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |

Pattern %chords_IVF_68_55:
  key=D 4: 55@
  A'1 |
  A7'1 |

Pattern %arp_IVC_08_70:
  key=D 8: 70@
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  e*5 g*5 b*5 g*5 e*5 g*5 b*5 g*5 |
  e*5 g*5 a*5 c*6 a*5 g*5 a*5 g*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  e*5 g*5 a*5 c*6 a*5 g*5 a*5 g*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |

Pattern %arp_IVK_08_85:
  key=D 8: 85@
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  e*5 g*5 a*5 c*6 a*5 g*5 a*5 g*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |
  d*5 f*5 b*5 f*5 d*5 f*5 b*5 f*5 |
  d*5 g*5 b*5 g*5 d*5 g*5 b*5 g*5 |
  e*5 g*5 a*5 c*6 a*5 g*5 a*5 g*5 |
  d*5 f*5 a*5 f*5 d*5 f*5 a*5 f*5 |

Pattern %chords_IVM_08_80:
  key=D 4: 80@
  D'1 |
  G'1 |
  A7'1 |
  D'1 |
  Bm'1 |
  G'1 |
  A7'1 |
  D'1 |

Pattern %chords_IVF_48_60:
  key=D 4: 60@
  D'1 |
  D'1 |
  A'1 |
  A7'1 |

Pattern %chords_IVC_08_70:
  key=D 4: 70@
  G'1 |
  D/F#'1 |
  Em'1 |
  A7'1 |
  Bm'1 |
  G'1 |
  A7'1 |
  D'1 |

Pattern %chords_IVK_08_88:
  key=D 4: 88@
  D'1 |
  G'1 |
  A7'1 |
  D'1 |
  Bm'1 |
  G'1 |
  A7'1 |
  D'1 |

Pattern %rootsC_IVM_08_90:
  key=D 4: 90@
  d*2 d*3 d*2 d*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |
  b*2 b*3 b*2 b*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |

Pattern %rootsC_IVF_28_70:
  key=D 4: 70@
  a*2 a*3 a*2 a*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |
  d*2 d*3 d*2 d*3 |
  a*2 a*3 a*2 a*3 |
  a*2 a*3 a*2 a*3 |

Pattern %rootsC_IVC_08_80:
  key=D 4: 80@
  g*2 g*3 g*2 g*3 |
  f*2 f*3 f*2 f*3 |
  e*2 e*3 e*2 e*3 |
  a*2 a*3 a*2 a*3 |
  b*2 b*3 b*2 b*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |

Pattern %rootsC_IVK_08_95:
  key=D 4: 95@
  d*2 d*3 d*2 d*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |
  b*2 b*3 b*2 b*3 |
  g*2 g*3 g*2 g*3 |
  a*2 a*3 a*2 a*3 |
  d*2 d*3 d*2 d*3 |

Pattern %rootsB_IVM_08_92:
  key=D 4: 92@
  d*2'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |
  b*1'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |

Pattern %rootsB_IVF_08_70:
  key=D 4: 70@
  d*2'1 |
  d*2'1 |
  a*1'1 |
  a*1'1 |
  d*2'1 |
  d*2'1 |
  a*1'1 |
  a*1'1 |

Pattern %rootsB_IVC_08_82:
  key=D 4: 82@
  g*1'1 |
  f*1'1 |
  e*1'1 |
  a*1'1 |
  b*1'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |

Pattern %rootsB_IVK_08_98:
  key=D 4: 98@
  d*2'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |
  b*1'1 |
  g*1'1 |
  a*1'1 |
  d*2'1 |


// ================================================================ tracks

Violins1:

Violins2:

Violas:

Cellos:

DoubleBasses:

Flute:

Oboe:

Clarinet:

Bassoon:

Horns:

Trumpet:

Timpani:

// ================================================================ mixer

Mixer Flute:
  volume: 70 pan: 0.25 mute: no solo: no reverb: 25

Mixer Oboe:
  volume: 67 pan: -0.2 mute: no solo: no reverb: 25

Mixer Clarinet:
  volume: 66 pan: 0.15 mute: no solo: no reverb: 25

Mixer Bassoon:
  volume: 66 pan: -0.3 mute: no solo: no reverb: 20

Mixer Horns:
  volume: 69 pan: 0.3 mute: no solo: no reverb: 28

Mixer Trumpet:
  volume: 67 pan: 0.4 mute: no solo: no reverb: 28

Mixer Timpani:
  volume: 72 pan: 0.0 mute: no solo: no reverb: 30

Mixer Violins1:
  volume: 75 pan: -0.5 mute: no solo: no reverb: 22

Mixer Violins2:
  volume: 70 pan: -0.3 mute: no solo: no reverb: 22

Mixer Violas:
  volume: 67 pan: 0.2 mute: no solo: no reverb: 22

Mixer Cellos:
  volume: 72 pan: 0.45 mute: no solo: no reverb: 20

Mixer DoubleBasses:
  volume: 70 pan: 0.6 mute: no solo: no reverb: 15


// ================================================================ boxes (the position is in the header, in quarter-note beats from the start)

Box Violins1 "I. First theme (D minor)" |0:
  $"Allegro con fuoco" %I_ThA

Box Violins1 "I. Second theme (F major)" |48:
  %I_ThB2

Box Violins1 "I. Development" |64:
  %I_Dev

Box Violins1 "I. Recapitulation and close in D major" |96:
  %I_ThAr

Box Violins1 "II. Adagio: the song" |128:
  $"Adagio" %arp_II1_08_48

Box Violins1 "II. Adagio: the violins" |160:
  %II_Violin

Box Violins1 "III. Scherzo: first part" |192:
  $"Scherzo: Presto" %III_S1

Box Violins1 "III. Scherzo: second part" |224:
  %III_S2

Box Violins1 "IV. Fanfare and theme" |256:
  $"Finale: Allegro con brio" %IV_Theme

Box Violins1 "IV. Fugato" |312:
  %IV_RispV1

Box Violins1 "IV. Chorale" |320:
  %IV_Chorale

Box Violins1 "IV. Coda with the rallentando" |352:
  %IV_Theme

Box Violins2 "I. First theme (D minor)" |0:
  %arp_IA_08_70

Box Violins2 "I. Second theme (F major)" |32:
  %arp_IB_08_55

Box Violins2 "I. Development" |64:
  vol=60 >> %arp_ID_08_80 vol=100

Box Violins2 "I. Recapitulation and close in D major" |96:
  %arp_IR_08_85

Box Violins2 "II. Adagio: the song" |128:
  %chords_II1_08_45

Box Violins2 "II. Adagio: the violins" |160:
  %arp_II2_08_50

Box Violins2 "III. Scherzo: first part" |192:
  %arp_III1_08_65

Box Violins2 "III. Scherzo: second part" |224:
  %arp_III2_08_72

Box Violins2 "IV. Fanfare and theme" |256:
  %arp_IVM_08_75

Box Violins2 "IV. Fugato" |304:
  %IV_SubjV2 %chords_IVF_68_55

Box Violins2 "IV. Chorale" |320:
  %arp_IVC_08_70

Box Violins2 "IV. Coda with the rallentando" |352:
  %arp_IVK_08_85

Box Violas "I. First theme (D minor)" |0:
  %chords_IA_08_78

Box Violas "I. Second theme (F major)" |32:
  %chords_IB_08_50

Box Violas "I. Development" |64:
  vol=60 >> %chords_ID_08_75 vol=100

Box Violas "I. Recapitulation and close in D major" |96:
  %chords_IR_08_85

Box Violas "II. Adagio: the song" |128:
  %chords_II1_08_50

Box Violas "II. Adagio: the violins" |160:
  %chords_II2_08_55

Box Violas "III. Scherzo: first part" |192:
  %stab_III1_08_70

Box Violas "III. Scherzo: second part" |224:
  %stab_III2_08_78

Box Violas "IV. Fanfare and theme" |256:
  %chords_IVM_08_80

Box Violas "IV. Fugato" |296:
  %IV_RispVle %chords_IVF_48_60

Box Violas "IV. Chorale" |320:
  %chords_IVC_08_70

Box Violas "IV. Coda with the rallentando" |352:
  %chords_IVK_08_88

Box Cellos "I. First theme (D minor)" |0:
  %rootsC_IA_08_90

Box Cellos "I. Second theme (F major)" |32:
  %rootsC_IB_08_60

Box Cellos "I. Development" |64:
  %rootsC_ID_08_85

Box Cellos "I. Recapitulation and close in D major" |96:
  %rootsC_IR_08_95

Box Cellos "II. Adagio: the song" |128:
  %rootsW_II1_08_70

Box Cellos "II. Adagio: the violins" |160:
  %rootsW_II2_08_72

Box Cellos "III. Scherzo: first part" |192:
  %rootsC_III1_08_85

Box Cellos "III. Scherzo: second part" |224:
  %rootsC_III2_08_90

Box Cellos "IV. Fanfare and theme" |256:
  %rootsC_IVM_08_90

Box Cellos "IV. Fugato" |288:
  %IV_SubjCellos %rootsC_IVF_28_70

Box Cellos "IV. Chorale" |320:
  %rootsC_IVC_08_80

Box Cellos "IV. Coda with the rallentando" |352:
  %rootsC_IVK_08_95

Box DoubleBasses "I. First theme (D minor)" |0:
  %rootsB_IA_08_92

Box DoubleBasses "I. Second theme (F major)" |32:
  %rootsB_IB_08_60

Box DoubleBasses "I. Development" |64:
  %rootsB_ID_08_85

Box DoubleBasses "I. Recapitulation and close in D major" |96:
  %rootsB_IR_08_98

Box DoubleBasses "II. Adagio: the song" |128:
  %rootsB_II1_08_60

Box DoubleBasses "II. Adagio: the violins" |160:
  %rootsB_II2_08_62

Box DoubleBasses "III. Scherzo: first part" |192:
  %rootsB_III1_08_85

Box DoubleBasses "III. Scherzo: second part" |224:
  %rootsB_III2_08_88

Box DoubleBasses "IV. Fanfare and theme" |256:
  %rootsB_IVM_08_92

Box DoubleBasses "IV. Fugato" |288:
  %rootsB_IVF_08_70

Box DoubleBasses "IV. Chorale" |320:
  %rootsB_IVC_08_82

Box DoubleBasses "IV. Coda with the rallentando" |352:
  %rootsB_IVK_08_98

Box Flute "I. First theme (D minor)" |0:
  %I_ThA

Box Flute "I. Recapitulation and close in D major" |96:
  %I_ThAr

Box Flute "III. Scherzo: first part" |192:
  %III_S1

Box Flute "III. Scherzo: second part" |224:
  %III_S2

Box Flute "IV. Fanfare and theme" |256:
  %IV_Theme

Box Flute "IV. Chorale" |320:
  %IV_Chorale

Box Flute "IV. Coda with the rallentando" |352:
  %IV_Theme

Box Oboe "I. First theme (D minor)" |0:
  %I_ThA_down

Box Oboe "I. Second theme (F major)" |48:
  %I_ThB2_down

Box Oboe "I. Recapitulation and close in D major" |96:
  %I_ThAr_down

Box Oboe "II. Adagio: the song" |128:
  %II_Oboe

Box Oboe "IV. Fanfare and theme" |256:
  %IV_Theme_down

Box Oboe "IV. Chorale" |320:
  %IV_Chorale_down

Box Oboe "IV. Coda with the rallentando" |352:
  %IV_Theme_down

Box Clarinet "I. Second theme (F major)" |32:
  %I_ThB1_down

Box Clarinet "I. Development" |80:
  4: 80@ a*4'1 | a*4'1 | a*4'1 | a*4'1

Box Clarinet "II. Adagio: the violins" |160:
  %II_Violin_down

Box Clarinet "III. Scherzo: second part" |224:
  %stab_III2_08_75

Box Bassoon "I. First theme (D minor)" |0:
  %rootsF_IA_08_90

Box Bassoon "I. Second theme (F major)" |32:
  %rootsF_IB_08_55

Box Bassoon "I. Development" |64:
  %rootsF_ID_08_70

Box Bassoon "I. Recapitulation and close in D major" |96:
  %rootsF_IR_08_95

Box Bassoon "II. Adagio: the song" |128:
  %rootsF_II1_08_55

Box Bassoon "II. Adagio: the violins" |160:
  %rootsF_II2_08_58

Box Bassoon "III. Scherzo: first part" |192:
  %rootsF_III1_08_75

Box Bassoon "III. Scherzo: second part" |224:
  %rootsF_III2_08_80

Box Bassoon "IV. Fanfare and theme" |256:
  %rootsF_IVM_08_90

Box Bassoon "IV. Fugato" |288:
  %rootsF_IVF_08_70

Box Bassoon "IV. Chorale" |320:
  %rootsF_IVC_08_80

Box Bassoon "IV. Coda with the rallentando" |352:
  %rootsF_IVK_08_95

Box Horns "I. First theme (D minor)" |0:
  %chords_IA_08_100

Box Horns "I. Second theme (F major)" |32:
  %chords_IB_08_55

Box Horns "I. Development" |64:
  %chords_ID_08_80

Box Horns "I. Recapitulation and close in D major" |96:
  %chords_IR_08_105

Box Horns "II. Adagio: the song" |128:
  %chords_II1_08_50

Box Horns "II. Adagio: the violins" |160:
  %chords_II2_08_55

Box Horns "III. Scherzo: first part" |192:
  %stab_III1_08_70

Box Horns "III. Scherzo: second part" |224:
  %stab_III2_08_90

Box Horns "IV. Fanfare and theme" |256:
  %chords_IVM_08_100

Box Horns "IV. Fugato" |288:
  %chords_IVF_08_65

Box Horns "IV. Chorale" |320:
  %chords_IVC_08_80

Box Horns "IV. Coda with the rallentando" |352:
  %chords_IVK_08_105

Box Trumpet "I. Recapitulation and close in D major" |96:
  %I_ThAr_down

Box Trumpet "IV. Fanfare and theme" |256:
  %IV_Theme_down

Box Trumpet "IV. Chorale" |320:
  %IV_Chorale_down

Box Trumpet "IV. Coda with the rallentando" |352:
  %IV_Theme_down

Box Timpani "I. First theme (D minor)" |0:
  %hit_IA_08_100

Box Timpani "I. Second theme (F major)" |32:
  %hitS_IB_08_45

Box Timpani "I. Development" |64:
  %roll_ID_08_70

Box Timpani "I. Recapitulation and close in D major" |96:
  %hit_IR_08_105

Box Timpani "II. Adagio: the song" |128:
  tempo=58 4: 32r

Box Timpani "III. Scherzo: first part" |192:
  tempo=152 %hit_III1_08_90

Box Timpani "III. Scherzo: second part" |224:
  %hit_III2_08_95

Box Timpani "IV. Fanfare and theme" |256:
  tempo=126 %hit_IVM_08_100

Box Timpani "IV. Fugato" |288:
  %roll_IVF_08_60

Box Timpani "IV. Chorale" |320:
  %hitS_IVC_08_60

Box Timpani "IV. Coda with the rallentando" |352:
  %hit_IVK_04_105 100@ tempo=126 << %hit_IVK_47 key=D 4: d*2$fermata r r r tempo=56
