// Midnight Boom Bap: a hip hop beat in A minor, 56 bars at 90 BPM.
//
// Drums, percussion, synth bass, electric piano, vibraphone and strings: the
// instrumental "boom bap" sound, with the kick landing a little late and the
// snare on beats two and four. Form:
//   intro 4 + verse 16 + chorus 8 + verse 16
//   + chorus 8 + coda 4
//   Verse   Am9 | Fmaj7 | Dm7 | E7
//   Chorus  Fmaj7 | G7 | Am9 | Am9
// What's inside:
//   - sixteenth-note swing (swing16=58), always written on the 16 grid: the
//     kick and the "ghost" snare fall on odd and even sixteenths and give the
//     typical sway of the genre;
//   - snare and clap together, [snare clap hihat], and ghost notes at low
//     velocity;
//   - the bass with long notes (`7a*1` lasts seven sixteenths), following the
//     kick and letting the groove breathe;
//   - the electric piano in syncopated stabs: chords with the length in
//     front (`3Am9`) and `!` for a short hit;
//   - a drum fill (snare, toms, kick and cymbal) at the end of every verse
//     and chorus;
//   - the vibraphone theme in relative octaves (rel:), the percussion
//     (maracas, tambourine, conga) and slow strings in the chorus;
//   - the coda with a fermata ($fermata) on every instrument;
//   - instruments defined in the file (synth bass, electric piano,
//     vibraphone, strings).

ST: 2.6
Tempo: 90 BPM
Metrica: 4/4
Tonalita: Am

Strumento Rhodes:
  program=4 percussione=no ottava=4 range=48-84 poly=si voicing=spread

Strumento Synbass:
  program=38 percussione=no ottava=2 range=28-60 poly=no voicing=monophonic

Strumento Vibraphone:
  program=11 percussione=no ottava=5 range=53-96 poly=no voicing=monophonic

Strumento Strings:
  program=49 percussione=no ottava=4 range=36-96 poly=si voicing=spread

// ---------------------------------------------------------------- drums

Pattern %DrHats:
  16: 60@ hihat 28@ hihat 45@ hihat 28@ hihat 60@ hihat 28@ hihat 45@ hihat 28@ hihat 60@ hihat 28@ hihat 45@ hihat 28@ hihat 60@ hihat 28@ hihat 45@ hihat 35@ hihat_open |

Pattern %DrBoom:
  16: 105@ [kick hihat] r 50@ hihat 28@ hihat 100@ [snare clap hihat] r 50@ hihat 80@ kick 60@ hihat r 100@ [kick hihat] 28@ hihat 100@ [snare clap hihat] r 50@ hihat 35@ snare |

Pattern %DrBoom2:
  16: 105@ [kick hihat] r 50@ hihat 28@ hihat 100@ [snare clap hihat] r 50@ hihat r 100@ [kick hihat] 75@ kick 50@ hihat 28@ hihat 100@ [snare clap hihat] r 50@ hihat_open r |

Pattern %DrFill:
  16: 105@ [kick hihat] r 50@ hihat r 100@ [snare clap] r 60@ snare 70@ snare 85@ snare 90@ tom2 95@ tom1 100@ floor 105@ [kick snare] 90@ snare 105@ [kick snare] 110@ [kick crash] |

Pattern %DrVerse4:
  %DrBoom %DrBoom2 %DrBoom %DrBoom2

Pattern %DrVerse4Fill:
  %DrBoom %DrBoom2 %DrBoom %DrFill

// ---------------------------------------------------------------- percussion

Pattern %PercHook:
  16: 40@ maracas r 55@ maracas r 90@ tambourine r 55@ maracas r 40@ maracas r 55@ maracas r 90@ tambourine r 55@ maracas r |

Pattern %PercVerse:
  16: r r r r r r r 70@ conga_open r r r r r r 60@ conga_low r |

// ---------------------------------------------------------------- bass

Pattern %BsAm9:
  key=Am 16: 7a*1 3a*1 6g*1 |

Pattern %BsF:
  key=Am 16: 7f*1 3f*1 6c*2 |

Pattern %BsDm:
  key=Am 16: 7d*2 3d*2 6c*2 |

Pattern %BsE:
  key=Am 16: 7e*2 3e*2 6b*1 |

Pattern %BsG:
  key=Am 16: 7g*1 3g*1 6d*2 |

Pattern %BsAmHook:
  key=Am 16: 7a*1 3a*1 6e*2 |

Pattern %BsAmHook2:
  key=Am 16: 7a*1 2r 3a*1 4g*1 |

Pattern %BsVerse4:
  %BsAm9 %BsF %BsDm %BsE

Pattern %BsHook4:
  %BsF %BsG %BsAmHook %BsAmHook2

// ---------------------------------------------------------------- electric piano

Pattern %RhAm9:
  16: 72@ 3Am9 r 56@ 2Am9 r 66@ 3Am9 r 50@ Am9! r 60@ 2Am9 r |

Pattern %RhF:
  16: 72@ 3Fmaj7 r 56@ 2Fmaj7 r 66@ 3Fmaj7 r 50@ Fmaj7! r 60@ 2Fmaj7 r |

Pattern %RhDm:
  16: 72@ 3Dm7 r 56@ 2Dm7 r 66@ 3Dm7 r 50@ Dm7! r 60@ 2Dm7 r |

Pattern %RhE:
  16: 72@ 3E7 r 56@ 2E7 r 66@ 3E7 r 50@ E7! r 60@ 2E7 r |

Pattern %RhG:
  16: 72@ 3G7 r 56@ 2G7 r 66@ 3G7 r 50@ G7! r 60@ 2G7 r |

Pattern %RhVerse4:
  %RhAm9 %RhF %RhDm %RhE

Pattern %RhHook4:
  %RhF %RhG %RhAm9 %RhAm9

// ---------------------------------------------------------------- vibraphone

Pattern %LeadHook:
  rel: key=Am 16:
  2r 2e 2g 4a 2g 2e 2r |
  2r 2d 2g 4b 2a 2g 2r |
  2r 2e 2a 4c 2b 2a 2g |
  6a 2g 4e 4r |

Pattern %LeadOutro:
  rel: key=Am 16:
  2r 2e 2a 4c 2b 2a 2g |
  2r 2c 2e 4a 2g 2e 2r |
  2r 2d 2f 4a 2g 2f 2e |
  16a$fermata |

// ---------------------------------------------------------------- strings

Pattern %PadHook:
  Fmaj7'1 | G7'1 | Am9'1< | Am9'1 |

Pattern %PadOutro:
  Am9'1 | Fmaj7'1 | Dm7'1 | Am9'1$fermata |

// ================================================================ tracks

Drums:

Box Drums "Intro" |0:
  // intro: hi-hats only
  swing16=58 4%DrHats

Box Drums "Verse 1" |16:
  // verse 1: three groove cycles and the fill at the end
  swing16=58 3%DrVerse4 %DrVerse4Fill

Box Drums "Chorus 1" |80:
  // chorus 1
  swing16=58 %DrVerse4 %DrVerse4Fill

Box Drums "Verse 2" |112:
  // verse 2
  swing16=58 3%DrVerse4 %DrVerse4Fill

Box Drums "Chorus 2" |176:
  // chorus 2
  swing16=58 %DrVerse4 %DrVerse4Fill

Box Drums "Coda" |208:
  // coda: the groove stops on the last hit
  swing16=58 %DrBoom %DrBoom2 %DrBoom
  16: 100@ [kick crash] 15r |

Traccia Percussion [Drums]:

Box Percussion "Chorus 1" |80:
  // chorus 1: maracas and tambourine
  swing16=58 8%PercHook

Box Percussion "Verse 2" |112:
  // verse 2: the congas
  swing16=58 16%PercVerse

Box Percussion "Chorus 2" |176:
  // chorus 2
  swing16=58 8%PercHook

Synbass:

Box Synbass "Verse 1" |16:
  // verse 1: the bass comes in with the verse
  swing16=58 shift=-6 100@ 4%BsVerse4

Box Synbass "Chorus 1" |80:
  // chorus 1
  swing16=58 shift=-6 105@ 2%BsHook4

Box Synbass "Verse 2" |112:
  // verse 2
  swing16=58 shift=-6 100@ 4%BsVerse4

Box Synbass "Chorus 2" |176:
  // chorus 2
  swing16=58 shift=-6 105@ 2%BsHook4

Box Synbass "Coda" |208:
  // coda
  swing16=58 shift=-6 100@ %BsAm9 %BsF %BsDm
  16: 90@ 16a*1$fermata |

Rhodes:

Box Rhodes "Intro" |0:
  // intro: the piano alone
  swing16=58 vol=70 %RhVerse4

Box Rhodes "Verse 1" |16:
  // verse 1
  swing16=58 vol=85 4%RhVerse4

Box Rhodes "Chorus 1" |80:
  // chorus 1
  swing16=58 vol=95 2%RhHook4

Box Rhodes "Verse 2" |112:
  // verse 2
  swing16=58 vol=85 4%RhVerse4

Box Rhodes "Chorus 2" |176:
  // chorus 2
  swing16=58 vol=95 2%RhHook4

Box Rhodes "Coda" |208:
  // coda: the reverb grows as the beat fades
  swing16=58 rev=20 >>
  %RhAm9 %RhF %RhDm
  Am9'1$fermata |
  rev=70

Vibraphone:

Box Vibraphone "Chorus 1" |80:
  // chorus 1: the theme, twice
  swing16=58 90@ 2%LeadHook

Box Vibraphone "Chorus 2" |176:
  // chorus 2
  swing16=58 100@ 2%LeadHook

Box Vibraphone "Coda" |208:
  // coda
  swing16=58 85@ %LeadOutro

Strings:

Box Strings "Chorus 1" |80:
  // chorus 1: the slow strings
  60@ %PadHook %PadHook

Box Strings "Chorus 2" |176:
  // chorus 2
  70@ %PadHook %PadHook

Box Strings "Coda" |208:
  // coda
  55@ %PadOutro

// ================================================================ mixer

Mixer Drums:
  volume: 92 pan: 0 mute: no solo: no reverb: 10

Mixer Percussion:
  volume: 62 pan: 0.35 mute: no solo: no reverb: 18

Mixer Synbass:
  volume: 98 pan: 0 mute: no solo: no

Mixer Rhodes:
  volume: 82 pan: -0.25 mute: no solo: no reverb: 28 chorus: 25

Mixer Vibraphone:
  volume: 72 pan: 0.3 mute: no solo: no reverb: 35

Mixer Strings:
  volume: 66 pan: 0 mute: no solo: no reverb: 40
