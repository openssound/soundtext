// Lights on the Naviglio: a jazz tune in the classic AABA form (32 bars).
//
// A quintet (tenor sax, piano, guitar, double bass and drums) playing one
// "chorus" after another, as in a real club:
//   a 4-bar intro, the head on tenor sax, a piano solo,
//   the head again with a livelier rhythm section, and a short coda.
// What's inside:
//   - swing (swing=66): straight eighth notes are played "triplet-like";
//   - the key (key=F): B flat without writing it;
//   - the walking bass: four notes per bar, always moving towards the next
//     chord;
//   - the piano comping with the "Charleston" rhythm and drop-2 voicings
//     (.drop2); the guitar playing "four to the bar";
//   - the drums with the swing ride, the hi-hat pedal on 2 and 4, and the
//     "feathered" bass drum in the last chorus;
//   - the A and B sections as patterns: A, A, B, A for three choruses;
//   - dynamic hairpins on the bridge and the final fermata.
//
// Form: intro 4 + head 32 + solo 32 + head 32 + coda 4 = 104 bars.
//   A  Fmaj7 | D7 | Gm7 | C7 | Am7 D7 | Gm7 C7 | Fmaj7 Dm7 | Gm7 C7
//   B  Em7 A7 | Dmaj7 | Dm7 G7 | Cmaj7 | Cm7 F7 | Bbmaj7 | Gm7 C7 | C7

ST: 2.6
Tempo: 132 BPM
Metrica: 4/4
Tonalita: F

Strumento TenorSax:
  program=66 percussione=no ottava=4 range=49-82 poly=no voicing=monophonic

// ---------------------------------------------------------------- general

Pattern %Rest:
  4: 4r |

// ---------------------------------------------------------------- head (tenor sax)

Pattern %HeadA1:
  key=F 8: 92@
  r a*4 c*5 f*5 2e*5 c*5 a*4 |
  2f#*4 a*4 d*5 3c*5 r |
  r b*4 d*5 g*5 2f*5 d*5 b*4 |
  3e*5 c*5 4r |
  r c*5 e*5 a*5 2g*5 f#*5 d*5 |
  b*4 d*5 f*5 e*5 2c*5 b*4 g*4 |
  2a*4 c*5 f*5 3d*5 r |
  r g*4 b*4 d*5 2c*5 e*5 g*5 |

Pattern %HeadA3:
  key=F 8: 92@
  r a*4 c*5 f*5 2e*5 c*5 a*4 |
  2f#*4 a*4 d*5 3c*5 r |
  r b*4 d*5 g*5 2f*5 d*5 b*4 |
  3e*5 c*5 4r |
  r c*5 e*5 a*5 2g*5 f#*5 d*5 |
  b*4 d*5 f*5 e*5 2c*5 b*4 g*4 |
  r b*4 d*5 f*5 e*5 c*5 b*4 g*4 |
  6f*4 2r |

Pattern %HeadB:
  key=F 8: 96@
  r g*4 e*5 g*5 2f#*5 e*5 c#*5 |
  2a*5 f#*5 d*5 4a*4 |
  r a*4 d*5 f*5 2g*5 f*5 d*5 |
  2e*5 g*5 e*5 4c*5 |
  r g*4 c*5 eb*5 2d*5 c*5 a*4 |
  2b*4 d*5 f*5 4a*5 |
  r g*4 b*4 d*5 2f*5 e*5 c*5 |
  2g*4 b*4 c*5 3e*5 r |

Pattern %Head:
  %HeadA1 %HeadA1 %HeadB %HeadA3

// ---------------------------------------------------------------- solo (piano)

Pattern %SoloA1:
  key=F 8: 88@
  r f*4 a*4 c*5 e*5 d*5 c*5 a*4 |
  f#*4 a*4 d*5 c*5 a*4 f#*4 d*4 r |
  g*4 b*4 d*5 f*5 d*5 b*4 a*4 g*4 |
  e*4 g*4 b*4 c*5 b*4 g*4 e*4 c*4 |
  c*5 e*5 a*5 g*5 f#*5 d*5 c*5 a*4 |
  b*4 d*5 g*5 f*5 e*5 c*5 b*4 g*4 |
  a*4 c*5 f*5 e*5 d*5 f*5 a*5 f*5 |
  g*5 f*5 d*5 b*4 g*4 b*4 c*5 e*5 |

Pattern %SoloA2:
  key=F 8: 94@
  2a*5 g*5 f*5 e*5 c*5 2a*4 |
  d*5 c*5 a*4 f#*4 2d*4 2r |
  r b*4 d*5 g*5 2a*5 g*5 f*5 |
  e*5 d*5 c*5 b*4 4g*4 |
  2a*4 c*5 e*5 2f#*5 d*5 c*5 |
  b*4 g*4 d*5 g*5 2f*5 e*5 g*5 |
  f*5 a*5 c*6 a*5 f*5 d*5 f*5 a*5 |
  g*5 f*5 d*5 b*4 2c*5 r r |

Pattern %SoloB:
  key=F 8: 100@
  e*5 g*5 e*5 d*5 c#*5 e*5 a*4 c#*5 |
  d*5 f#*5 a*5 f#*5 d*5 c#*5 a*4 f#*4 |
  d*5 f*5 a*5 g*5 f*5 d*5 a*4 g*4 |
  e*5 g*5 c*6 g*5 e*5 c*5 g*4 e*4 |
  c*5 eb*5 g*5 f*5 e*5 c*5 a*4 f*4 |
  b*4 d*5 f*5 a*5 f*5 d*5 b*4 f*4 |
  g*4 b*4 d*5 f*5 e*5 c*5 b*4 g*4 |
  e*4 g*4 b*4 c*5 2e*5 2r |

Pattern %SoloA3:
  key=F 8: 96@
  r f*5 a*5 c*6 2a*5 f*5 c*5 |
  a*5 f#*5 d*5 f#*5 a*5 d*6 c*6 a*5 |
  g*5 b*5 d*6 c*6 b*5 g*5 f*5 d*5 |
  e*5 g*5 e*5 c*5 e*5 g*5 b*5 g*5 |
  a*5 c*6 e*6 d*6 c*6 a*5 f#*5 d*5 |
  b*4 d*5 g*5 b*5 2a*5 g*5 f*5 |
  r g*5 b*5 d*6 c*6 b*5 g*5 e*5 |
  2f*5 c*5 a*4 4f*4 |

Pattern %Solo:
  %SoloA1 %SoloA2 %SoloB %SoloA3

// ---------------------------------------------------------------- double bass (walking)

Pattern %BF:
  key=F 4: 90@ f*1 a*1 c*2 e*2 |

Pattern %BD7:
  key=F 4: 86@ d*2 c*2 a*1 f#*1 |

Pattern %BGm:
  key=F 4: 90@ g*1 b*1 d*2 f*2 |

Pattern %BC7:
  key=F 4: 86@ c*2 b*1 g*1 g#*1 |

Pattern %BAmD:
  key=F 4: 90@ a*1 c*2 d*2 f#*2 |

Pattern %BGmC:
  key=F 4: 88@ g*1 b*1 c*2 e*2 |

Pattern %BFDm:
  key=F 4: 90@ f*1 a*1 d*2 c*2 |

Pattern %BFend:
  key=F 4: 90@ f*1 c*2 a*1 f*1 |

Pattern %BassA:
  %BF %BD7 %BGm %BC7 %BAmD %BGmC %BFDm %BGmC

Pattern %BassAEnd:
  %BF %BD7 %BGm %BC7 %BAmD %BGmC %BGmC %BFend

Pattern %BassB:
  key=F 4: 90@
  e*2 b*1 a*1 c#*2 |
  d*2 f#*2 a*2 f#*2 |
  d*2 a*1 g*1 d*2 |
  c*2 e*2 g*1 e*2 |
  c*2 g*1 f*1 a*1 |
  b*1 d*2 f*2 d*2 |
  g*1 d*2 c*2 e*2 |
  c*2 b*1 a*1 g*1 |

Pattern %BassChorus:
  %BassA %BassA %BassB %BassAEnd

// ---------------------------------------------------------------- piano (comping)

Pattern %CF:
  8: 74@ 3Fmaj7.drop2! Fmaj7.drop2! 4r |

Pattern %CD7:
  8: 74@ r 2D7.drop2! 2r 3r |

Pattern %CGm:
  8: 74@ 3Gm7.drop2! Gm7.drop2! 4r |

Pattern %CC7:
  8: 74@ r 2C7.drop2! 2r 3r |

Pattern %CAmD:
  8: 74@ 3Am7.drop2! r 2D7.drop2! 2r |

Pattern %CGmC:
  8: 74@ 3Gm7.drop2! r 2C7.drop2! 2r |

Pattern %CFDm:
  8: 74@ 3Fmaj7.drop2! r 2Dm7.drop2! 2r |

Pattern %CFend:
  8: 70@ 3Fmaj7.drop2! Fmaj7.drop2! 4r |

Pattern %CompB:
  8: 76@
  3Em7.drop2! r 2A7.drop2! 2r |
  3Dmaj7.drop2! Dmaj7.drop2! 4r |
  3Dm7.drop2! r 2G7.drop2! 2r |
  r 2Cmaj7.drop2! 2r 3r |
  3Cm7.drop2! r 2F7.drop2! 2r |
  3Bbmaj7.drop2! Bbmaj7.drop2! 4r |
  3Gm7.drop2! r 2C7.drop2! 2r |
  r 2C7.drop2! 2r 3r |

Pattern %CompA:
  %CF %CD7 %CGm %CC7 %CAmD %CGmC %CFDm %CGmC

Pattern %CompAEnd:
  %CF %CD7 %CGm %CC7 %CAmD %CGmC %CGmC %CFend

Pattern %CompChorus:
  %CompA %CompA %CompB %CompAEnd

// ---------------------------------------------------------------- guitar (four to the bar)

Pattern %GtrA:
  4: 62@
  Fmaj7! Fmaj7! Fmaj7! Fmaj7! |
  D7! D7! D7! D7! |
  Gm7! Gm7! Gm7! Gm7! |
  C7! C7! C7! C7! |
  Am7! Am7! D7! D7! |
  Gm7! Gm7! C7! C7! |
  Fmaj7! Fmaj7! Dm7! Dm7! |
  Gm7! Gm7! C7! C7! |

Pattern %GtrAEnd:
  4: 62@
  Fmaj7! Fmaj7! Fmaj7! Fmaj7! |
  D7! D7! D7! D7! |
  Gm7! Gm7! Gm7! Gm7! |
  C7! C7! C7! C7! |
  Am7! Am7! D7! D7! |
  Gm7! Gm7! C7! C7! |
  Gm7! Gm7! C7! C7! |
  Fmaj7! Fmaj7! Fmaj7! Fmaj7! |

Pattern %GtrB:
  4: 66@
  Em7! Em7! A7! A7! |
  Dmaj7! Dmaj7! Dmaj7! Dmaj7! |
  Dm7! Dm7! G7! G7! |
  Cmaj7! Cmaj7! Cmaj7! Cmaj7! |
  Cm7! Cm7! F7! F7! |
  Bbmaj7! Bbmaj7! Bbmaj7! Bbmaj7! |
  Gm7! Gm7! C7! C7! |
  C7! C7! C7! C7! |

Pattern %GtrChorus:
  %GtrA %GtrA %GtrB %GtrAEnd

// ---------------------------------------------------------------- drums

Pattern %Ride:
  8: 72@ ride r [ride hihat_pedal] 52@ ride 72@ ride r [ride hihat_pedal] 52@ ride |

Pattern %RideK:
  8: 72@ [ride kick] r [ride hihat_pedal] 52@ ride 72@ [ride kick] r [ride hihat_pedal] 52@ ride |

Pattern %RideFill:
  8: 72@ ride r [ride hihat_pedal] 52@ ride 80@ snare snare 85@ snare 90@ [snare crash] |

Pattern %RideFillTom:
  8: 72@ ride r [ride hihat_pedal] 52@ ride 82@ snare tom1 tom2 90@ [floor crash] |

Pattern %RideBridge:
  8: 78@ ride r [ride hihat_pedal] 56@ ride 78@ ride r [ride hihat_pedal] 56@ ride |

Pattern %Brush:
  8: 60@ [snare hihat_pedal] r r snare 60@ [snare hihat_pedal] r r snare |

Pattern %DrumsA:
  7%Ride %RideFill

Pattern %DrumsAK:
  7%RideK %RideFillTom

Pattern %DrumsB:
  7%RideBridge %RideFillTom

Pattern %DrumsChorus1:
  %DrumsA %DrumsA %DrumsB %DrumsA

Pattern %DrumsChorus2:
  %DrumsA %DrumsA %DrumsB %DrumsA

Pattern %DrumsChorus3:
  %DrumsAK %DrumsAK %DrumsB %DrumsAK

// ================================================================ tracks

Traccia Tenor Sax [TenorSax]:

Box Tenor Sax "Chorus 1" |16:
  // chorus 1: the head, an octave below the written notes: the tenor's register
  swing=66 transpose=-12 $"head" %Head

Box Tenor Sax "Chorus 3" |272:
  // chorus 3: the head again, stronger
  swing=66 transpose=-12 100@ %Head

Box Tenor Sax "Coda" |400:
  // coda
  swing=66 transpose=-12 100@ key=F 8: 90@
  r g*4 b*4 d*5 2f*5 e*5 c*5 |
  2a*4 c*5 f*5 3d*5 r |
  r g*4 b*4 d*5 2c*5 e*5 c*5 |
  8f*4$fermata |

Piano:

Box Piano "Intro" |0:
  // intro: a short one-handed phrase over the ii-V
  swing=66 key=F 8: 82@
  r c*5 e*5 a*5 g*5 f#*5 a*5 d*5 |
  c*5 b*4 g*4 b*4 d*5 c*5 e*4 g*4 |
  r c*5 e*5 a*5 g*5 f#*5 a*5 d*5 |
  b*4 d*5 g*5 f*5 2e*5 c*5 e*5 |

Box Piano "Chorus 1" |16:
  // chorus 1: Charleston comping under the head
  swing=66 key=F 8: 82@ %CompChorus

Box Piano "Chorus 2" |144:
  // chorus 2: the solo
  swing=66 key=F 8: 82@ $"solo" %Solo

Box Piano "Chorus 3" |272:
  // chorus 3: comping again
  swing=66 key=F 8: 82@ 100@ %CompChorus

Box Piano "Coda" |400:
  // coda
  swing=66 key=F 8: 100@ 8: 76@ 3Gm7.drop2! r 2C7.drop2! 2r |
  3Am7.drop2! r 2D7.drop2! 2r |
  3Gm7.drop2! r 2C7.drop2! 2r |
  1: Fmaj7.drop2$fermata |

Guitar 1:

Box Guitar 1 "Chorus 2" |144:
  // the guitar comes in with the piano solo
  swing=66 vol=100 %GtrChorus

Box Guitar 1 "Chorus 3" |272:
  // chorus 3: in the background again
  swing=66 vol=80 %GtrChorus

Box Guitar 1 "Coda" |400:
  // coda
  swing=66 4: 62@ Gm7! Gm7! C7! C7! |
  Am7! Am7! D7! D7! |
  Gm7! Gm7! C7! C7! |
  1: Fmaj7$fermata |

Bass:

Box Bass "Intro" |8:
  // intro: the bass comes in on bar 3
  swing=66 %BAmD %BGmC

Box Bass "Chorus x3" |16:
  // three choruses
  swing=66 3%BassChorus

Box Bass "Coda" |400:
  // coda
  swing=66 %BGmC %BAmD %BGmC
  1: 90@ f*1$fermata |

Drums:

Box Drums "Intro" |8:
  // intro: two bars of rest, then the ride and the lead-in fill
  swing=66 %Ride %RideFill

Box Drums "Chorus 1 and 2" |16:
  // choruses 1 and 2: swing ride
  swing=66 %DrumsChorus1 %DrumsChorus2

Box Drums "Chorus 3" |272:
  // chorus 3: the "feathered" bass drum and more energy
  swing=66 %DrumsChorus3

Box Drums "Coda" |400:
  // coda
  swing=66 %Ride %Ride %RideFill 8: [kick crash] 7r |

// ================================================================ mixer

Mixer Tenor Sax:
  volume: 92 pan: 0.3 mute: no solo: no reverb: 30

Mixer Piano:
  volume: 86 pan: -0.3 mute: no solo: no reverb: 18

Mixer Guitar 1:
  volume: 72 pan: -0.55 mute: no solo: no reverb: 10

Mixer Bass:
  volume: 100 pan: 0.1 mute: no solo: no

Mixer Drums:
  volume: 84 pan: 0 mute: no solo: no reverb: 15
