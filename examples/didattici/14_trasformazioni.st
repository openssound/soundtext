ST: 2.12
Titolo: Trasformazioni
Tempo: 96 BPM
Metrica: 4/4
Tonalita: C

// Un tema, e che cosa ne fanno le funzioni sui pattern: ferma il mouse su un
// richiamo (o Ctrl+I) per vedere e sentire che cosa suona, tasto destro per
// la finestra Trasforma...
Pattern %Tema:
  8: 90@ c d e g 2e 2c

Pattern %Motivo:
  8: 90@ e f g a

Pattern %Giro:
  4C 4Am 4F 4G

Traccia Melodia [Pianoforte]:
  // il tema, poi la risposta: lo stesso tema capovolto intorno al mi
  %Tema | %Tema.invert(e*4) |
  // una progressione: il motivo tre volte, ogni volta un grado sotto
  %Motivo.sequence(3,-1) r'2 |
  // il tema dalla fine all'inizio, poi due volte piu' lento
  %Tema.retro | %Tema.augment(2) |
  // un canone all'ottava, poi il tema a terze
  %Tema.canon('2,12) r'4 r'4 | %Tema.thirds |

Traccia Accordi [Pianoforte]:
  // due battute di attesa, il giro fermo, poi spezzato con arp=
  4: 70@ 8r | %Giro |
  arp=alberti,8 %Giro arp=off |
