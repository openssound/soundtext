# SoundText — Notación de texto simplificada

[Italiano](README.md) · [English](README.en.md) · [Français](README.fr.md) · **Español**

Una implementación funcional del MVP descrito en las *Especificaciones del
proyecto — Reproductor musical v1.2* (el nombre original del proyecto, hoy
**SoundText**): un motor musical que separa la intención abstracta
(acordes/notas simbólicos), el voicing concreto (que depende del
instrumento) y la reproducción (MIDI), con una interfaz de escritorio para
Linux, Windows y macOS — tema oscuro coherente, resaltado de sintaxis en
directo, atajos de teclado y mezclador con código de colores por familia de
instrumentos.

## Terminología

- **SoundText Language**: el lenguaje de texto con el que se escribe la
  partitura (notas, acordes, percusiones, patterns...).
- **ST-Syntax**: la gramática formal del SoundText Language (tokens, reglas
  de sintaxis, ver la sección 2 de la guía del usuario).
- **SoundText Engine**: el motor interno que convierte un acorde abstracto
  en notas MIDI concretas según el instrumento (el «motor de voicing»).
- **.st**: extensión de los archivos de proyecto.

## Guía completa

El menú **Ayuda → Guía del usuario** de la aplicación muestra la
documentación completa (también disponible aquí: `docs/HELP.es.md`; la
versión original en italiano es `docs/HELP.md`), con las instrucciones de
instalación para Debian/Ubuntu, Arch/CachyOS, Fedora y openSUSE.

## Qué implementa

- **Gramática completa** (ST-Syntax): notas en minúscula a-g, acordes
  abstractos en MAYÚSCULA (`Cmaj7`, `Am`, `G7`...), eventos de percusión de
  texto, silencios `r`, bloques simultáneos `[...]`, multiplicadores de
  duración, octavas `*n`, cambio de rejilla rítmica `N:` / `NT:`
  (tresillos), cambio de velocidad `N@`. Las duraciones se
  acumulan a lo largo de la línea de tiempo; la `|` opcional es un control
  de compás (no suena: avisa si no cae en una barra de compás, según el
  compás del proyecto, e indica qué compás es corto o largo), y `//` abre un
  comentario hasta el final de la línea (sección 2.10 de la guía). Las
  duraciones también se pueden escribir como valores de nota (`c'8.` corchea
  con puntillo), varias voces en la misma pista con `{ voz1 ; voz2 }` y la
  letra entre comillas (`"Ma- ri- a"`), secciones 2.11-2.13.
- **Automatizaciones**: volumen, expresión, panorama, modulación y envíos
  de efectos que cambian en el tiempo, incluso durante una nota sostenida
  (`vol=0 >>exp 4c vol=100`, `pan=-1 >> c d pan=1`), con rampas con curva
  (`>>exp`, `>>log`, `>>s`) y reguladores en las notas (`2c<`, `c'2>`): se
  oyen y van al MIDI y a la partitura (sección 2.15). También cualquier
  controlador MIDI (`cc74=`) y el pitch bend (`bend=`).
- **Ligaduras y swing**: ligaduras de prolongación incluso más allá de la
  barra de compás (`2f~ | 2f`), ligaduras de expresión tocadas ligadas y
  dibujadas en la partitura (`c( d e f)`), swing de corcheas y
  semicorcheas (`swing=62`), sección 2.16.
- **Repeticiones y signos**: repeticiones con casillas (`|: ... |1. ... :|
  |2. ... ||`) impresas como tales en la partitura, acentos, calderones,
  trinos, mordentes y grupetos que se oyen (`c$fermata`, `d$tr`),
  indicaciones de texto (`$"rit."`), sección 2.17.
- **Octavas relativas y tonalidad**: `rel:` escribe las melodías sin
  octavas (cada nota va cerca de la anterior, `*+` y `*-` para saltar),
  `key=G` da a las notas las alteraciones de la tonalidad (`n` para el
  becuadro); un botón reescribe así una pista existente, sección 2.18.
- **Microtiempo, afinación, MTXT**: `shift=-10` adelanta o retrasa las
  notas unos milisegundos sin cambiar el ritmo escrito, `tune=-20` afina
  el instrumento en cents (también con rampas); con más de 15 pistas el
  MIDI usa varios puertos, así cada pista tiene su canal; importación y
  exportación [MTXT](https://github.com/Daninet/mtxt), sección 2.19.
- **Anclas de compás**: `bar=29` lleva el cursor al comienzo del compás 29
  (con los silencios necesarios) y avisa si la pista ya está más allá,
  sección 2.20.
- **Transposición**: `transpose=2` transpone las notas siguientes,
  `%Tema+7` toca un patrón una quinta más aguda (las alteraciones siguen la
  tonalidad), sección 2.21; también vale para los archivos de la biblioteca MIDI (`&"Bajo"+7`).
- **Anacrusa y `reset:`**: el compás de anacrusa (`Levare: 1`) pone el
  compás 1 donde debe estar; `reset:` devuelve el estado inicial; el
  archivo declara su versión (`ST: 2.6`) y acepta también palabras clave
  en inglés, sección 2.22.
- **Especificación formal y biblioteca autónoma**: la notación y el formato
  `.st` se describen en [docs/spec/ST-language.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md)
  (CC BY 4.0, en inglés y en italiano) con una suite de conformidad; el
  motor es la biblioteca Python `st_language`, sin dependencias, que se
  instala con `pip install git+https://github.com/openssound/st-language.git` y ofrece los comandos
  `st-language check | midi | musicxml` (sección 2.14 de la guía).
- **Estado actual** (sección 4): la rejilla y la velocidad se mantienen a lo
  largo del recorrido secuencial de la pista.
- **Percusión y kit de batería** (sección 5): 36 identificadores asignados
  al General MIDI Drum Map — kit básico (kick, snare, hihat, hihat_open,
  tom1, tom2, floor, crash, ride, kick2, rimshot, clap), otros
  toms/platillos/charles (snare2, hihat_pedal, tom_lowmid, tom_hi,
  tom_highfloor, china, ride_bell, tambourine, splash, cowbell, crash2,
  ride2) y percusión latina (bongo_hi, bongo_low, conga_mute, conga_open,
  conga_low, timbale_hi, timbale_low, cabasa, maracas, claves, woodblock_hi,
  woodblock_low).
- **Patterns universales** (sección 6): una biblioteca `%Nombre`
  reutilizable en cualquier instrumento, con expansión recursiva y
  persistencia del estado.
- **Motor de voicing automático** (Visión del producto): convierte un acorde
  abstracto en notas concretas según el perfil del instrumento
  (Piano/Guitarra: voicing abierto; Bajo: fundamental+quinta; Trompeta:
  monofónico sobre la fundamental), adaptando las notas al registro que se
  puede tocar. Sufijo opcional `.estilo` (p. ej. `Cmaj7.drop2`, `C7.cagEd`,
  `C.power`) para imponer un estilo de voicing concreto, con prioridad sobre
  el algoritmo automático y una alternativa inteligente al equivalente
  genérico más cercano si el estilo pedido no tiene sentido para el
  instrumento de la pista. **Un doble clic en un acorde** (compacto o ya
  congelado en notas explícitas) en el editor de pista/pattern abre un menú
  con las alternativas de voicing adecuadas al instrumento, navegable con
  las flechas con una vista previa sonora de cada una, Intro/clic para
  aplicar, Esc/clic fuera para cancelar.
- **Congelación del voicing → notas explícitas**: un botón de la interfaz
  que sustituye cada acorde por el bloque `[...]` de notas concretas
  generadas.
- **Línea de tiempo común y mezcla**: Solo/Mute/Volumen/Pan por pista, motor
  de síntesis compartido, las pistas no se sincronizan por las barras de compás
  (las duraciones se acumulan en la línea de tiempo: la `|` controla, no
  mueve nada).
- **Editor con validación de sintaxis en directo** y **autocompletado** de
  los tokens (calidades de acorde, estilos de voicing,
  percusiones/dinámicas, referencias `%pattern` y `&"midi"`).
- **Estructura de la canción** (vista alternativa en boxes,
  `Ctrl+Shift+B`): cada pista se convierte en una fila sobre un eje de
  tiempo compartido, con su contenido dividido en boxes que se arrastran en
  horizontal — útil para trabajar en la estructura de la canción
  (intro/estrofa/estribillo...) en lugar de nota a nota. Las importaciones
  MIDI/audio dividen automáticamente el resultado en varios boxes donde la
  canción hace una pausa larga. Deshacer/rehacer propios
  (`Ctrl+Z`/`Ctrl+Y`), generación de batería/bajo directamente en un nuevo
  box, exportación/importación de un solo box como archivo `.box`, vista
  previa Play/Pausa del box seleccionado y cabezal de reproducción mientras
  suena la canción entera.
- **Importación/exportación MIDI estándar** (lo mejor posible en la
  importación: las notas se cuantizan en la rejilla, las superposiciones se
  convierten en voces `{ ; }` en la misma pista y la letra, también la de
  los archivos de karaoke, en letra entre comillas).
- **Exportación de la partitura a MusicXML** (Proyecto → Exportar → Partitura MusicXML): una parte por pista con notas, cifrado de acordes, tonalidad,
  compás, tempo, dinámicas y batería en un pentagrama de percusión, para
  abrirla e imprimirla con MuseScore, Finale, Sibelius o Dorico (sección
  10.1 de la guía), con las voces de los bloques `{ ; }` y la letra.
- **Partitura dentro de SoundText** (Vista → Partitura, `Ctrl+Shift+P`): las
  pistas en pentagrama, actualizadas mientras escribes, maquetadas por
  Verovio; exportación a PDF e impresión sin programas externos (sección
  10.1bis).
- **Importación de partituras MusicXML** (Proyecto → Importar → MusicXML,
  también `.mxl`): una pista por parte, instrumentos transpositores a la
  altura real, repeticiones, casillas y D.C./D.S./Coda desplegados, varias
  voces en la misma pista, letra, cifrado de acordes en una pista Acordes
  (sección 10.2 de la guía).
- **Notación ABC** (Proyecto → Importar → ABC / Exportar → Partitura ABC): el
  formato de texto de las colecciones de música tradicional, de abcjs y
  de EasyABC, en ambos sentidos: voces, instrumentos, tonalidad, compás,
  grupos irregulares, repeticiones y casillas, cifrado de acordes y letra
  (sección 10.3 de la guía).
- **Plugins externos VST3 y LV2**: como efectos en la cadena de una pista o
  del máster, o como instrumentos virtuales que tocan las notas de una
  pista en lugar del SoundFont. Los plugins funcionan en un proceso aparte,
  así que uno que se bloquea no detiene la aplicación (sección 8.7 de la
  guía).
- **Interfaz en cuatro idiomas**: italiano, inglés, francés y español
  (Opciones → Idioma), con la guía del usuario traducida a los mismos
  idiomas. El formato de los archivos `.st` y la notación son iguales en
  todos los idiomas.
- **5 instrumentos iniciales**: Piano, Guitarra, Bajo, Trompeta, Batería,
  más **instrumentos personalizados** que define el usuario (menú Sonidos).
- **Pistas editables**: cambio de nombre y de instrumento en cualquier
  momento (doble clic en la cabecera de la pista, o menú ⋯).
- **Importación/exportación MIDI de una sola pista**, además de la del
  conjunto entero.
- **Biblioteca MIDI reutilizable** (carpeta `midi/`, también con
  subcarpetas por categoría): archivos `.mid` que se llaman en una pista con
  `&"Nombre"` (búsqueda recursiva) o `&"Subcarpeta/Nombre"` (ruta explícita),
  con repetición (`2&"Nombre"`). Se gestionan
  (ver/editar/importar/renombrar/eliminar) desde la interfaz igual que los
  patterns.
- **Carpeta `songs/`** como ubicación predeterminada para abrir/guardar tus
  proyectos, distinta de `examples/` (proyectos de demostración).
- **Carga automática de los instrumentos personalizados**: si una canción
  usa un instrumento que aún no está en local, su definición (guardada
  dentro del propio archivo `.st`) se registra automáticamente al abrirla,
  sin perder pistas ni pedir pasos manuales.
- **Reconocimiento del instrumento en la importación MIDI**: si un canal usa
  exactamente el Program Change GM de un instrumento ya disponible, lo
  reutiliza; si no, **crea y registra automáticamente un nuevo instrumento
  personalizado** con ese programa (nombre/parámetros sugeridos por la
  familia General MIDI), de modo que la importación siempre es fiel al
  instrumento original en lugar de conformarse con el más parecido. El
  usuario recibe la lista de los nuevos instrumentos creados.
- **Patterns con repetición** (`3%Nombre`). La antigua sintaxis de
  transposición en línea (`%Nombre/2`) ya no existe: para transponer un box
  se usa **Transponer...** en el menú del clic derecho de la vista
  Estructura de la canción.
- **Guía del usuario integrada** (menú Ayuda), con instrucciones de
  instalación para las principales distribuciones Linux, para Windows y
  para macOS.
- **Reproducción con renderizado sin conexión** (fluidsynth + SoundFont
  renderizado a WAV antes de reproducir, para evitar crepitaciones por
  vaciados del búfer del controlador de audio), con un SoundFont
  configurable y un diagnóstico del motor en uso. Con la biblioteca
  FluidSynth (usada directamente), el renderizado usa una única instancia persistente
  de fluidsynth para toda la sesión (SoundFont cargado en memoria una sola
  vez en lugar de en cada Play): latencia de arranque mucho menor, misma
  estrategia contra las crepitaciones (el renderizado sigue siendo sin
  conexión a un archivo, no a la salida de audio en tiempo real). Si el
  binding no está instalado, usa automáticamente el binario CLI
  `fluidsynth`. Con `sounddevice` además, la canción renderizada se
  reproduce directamente y se guarda en caché: **pausa/reanudación y saltos
  instantáneos** (clic en la barra de progreso o en la regla de la
  Estructura de la canción) y **bucle A-B** de una sección (menú Reproducción → Bucle).
- **Interfaz cuidada**: tema oscuro coherente en la ventana principal y en
  los diálogos, resaltado de sintaxis en directo en el editor (colores para
  notas/acordes/percusiones/comandos de estado/referencias, basados en el
  tokenizador real del analizador), atajos de teclado, descripciones
  emergentes por todas partes, mezclador con código de colores por familia
  de instrumentos y estado vacío guiado. Durante la reproducción el editor
  se desplaza automáticamente (solo cuando hace falta) para mantener
  siempre visible el token que está sonando.
- **Reorganización automática con patterns**: extracción de bloques
  repetidos en patterns reutilizables, o expansión de todas las referencias
  en tokens literales, sin alterar el contenido musical (verificado con
  pruebas de ida y vuelta en todos los proyectos de ejemplo).
- **Escucha directa** de un pattern (eligiendo el instrumento de la vista
  previa) o de un archivo de la biblioteca MIDI, directamente desde sus
  diálogos de gestión.
- **Volumen de pista eficaz (0-200%)**: escala directamente la velocidad de
  las notas en la exportación/reproducción (no solo el Channel Volume MIDI,
  a menudo poco perceptible), con margen de refuerzo hasta el 200% para
  destacar en la mezcla los instrumentos débiles.
- **Persistencia del mezclador**: Volumen/Pan/Mute/Solo de cada pista se
  guardan en el archivo `.st` y se restablecen al volver a abrirlo (antes
  se perdían en cada guardado).
- **Importación de audio (voz/micrófono/archivo)**: grabación desde el
  micrófono o carga (también arrastrando y soltando) de un archivo
  `.wav`/`.mp3`/`.m4a`, convertido automáticamente en notación de texto con
  un motor de cuantización configurable (rejilla 1/4-1/32, tresillos
  8T/16T). Detección de altura para pistas melódicas/armónicas
  (segmentación mediante una detección de ataques dedicada, fiable incluso
  en el registro grave y en el canto ligado, con una estimación de la altura
  por mediana robusta al vibrato/a las imprecisiones de afinación),
  detección de transitorios con clasificación kick/snare/hihat para pistas
  de percusión, con una vista previa de escucha antes de confirmar; el texto
  generado siempre se valida antes de insertarlo en la pista o en el pattern
  (menú **Pista → Importar en esta pista → Audio → notación...**, la opción «Importar audio → notas»
  del menú ⋯ de la pista, o desde el diálogo de gestión de patterns).
  Casilla **«Fuente: voz/beatbox»** para cuando cantas/tarareas la parte en
  lugar de grabar el instrumento real: recalibra el análisis según las
  características acústicas de la voz humana en lugar de las del
  instrumento de destino.

No implementado en esta primera versión (indicado en el documento como fase
posterior o fuera del estándar MVP): importación por OMR desde partituras
tradicionales.

## Requisitos

- Linux, Windows o macOS, con Python 3.10+
- Un sintetizador MIDI del sistema para la escucha directa en la aplicación
  (uno entre `fluidsynth` con un SoundFont GM, `timidity`, `wildmidi`). Sin
  ellos la aplicación puede seguir exportando MIDI estándar reproducible con
  cualquier reproductor externo. Con la biblioteca del sistema `libfluidsynth` (que se instala junto con
  el paquete `fluidsynth` de la distribución, ver abajo) SoundText usa el
  motor de renderizado persistente de baja latencia (ver arriba), sin
  paquetes de Python adicionales.
- Para convertir audio (micrófono o archivos .mp3/.m4a/.flac/.ogg/.wav) en
  notación: los archivos los lee el decodificador de Qt Multimedia, ya
  incluido en PySide6 (el programa `ffmpeg` solo sirve como alternativa, si
  el PySide6 en uso no lo incluye); el micrófono requiere la biblioteca del
  sistema `libportaudio2` en Linux (para el paquete pip `sounddevice`, usado
  también para la reproducción directa con bucle y saltos). Si falta algo,
  **Pista → Importar en esta pista → Audio → notación...** lo avisa con un mensaje explícito en lugar
  de fallar en silencio.
- **(Opcional)** Pistas de audio: `libportaudio2` (con `sounddevice`) sirve
  también para grabar voz, guitarra o teclado desde la interfaz de audio
  (Pista → Grabar en la pista de audio...); los archivos mp3/m4a/flac/ogg
  se importan como los `.wav`, remuestreados a 48 kHz.

## Instalación

Elige el método adecuado para tu sistema. Para **plugins y amplificadores NAM** hay que descargar después los plugins gratuitos (`scarica_strumenti`) y los perfiles NAM (menú **Instrumentos → Descargar perfiles NAM recomendados...**): no están incluidos. Se necesita conexión a Internet.

| Sistema | Cómo instalar | Tras instalar |
|---|---|---|
| **Linux (recomendado)** | desde el repositorio: `./install.sh` (instala FluidSynth, PortAudio y lilv con el gestor de paquetes, crea el virtualenv, añade el comando `soundtext` y una entrada de menú; `--yes` sin preguntas, `--uninstall` para quitarlo) | `~/.local/share/soundtext/scarica_strumenti.sh` |
| **Linux, AppImage** | descarga `SoundText-linux-*.AppImage`, `setup-appimage.sh` y `scarica_strumenti.sh`/`.py` en la misma carpeta, luego `./setup-appimage.sh` (instala FUSE 2, FluidSynth, SoundFont GM, PortAudio, lilv y las bibliotecas de Qt; `--integra` añade una entrada de menú) | `./scarica_strumenti.sh` |
| **Linux, portable** (`.tar.gz`) | extrae y ejecuta `./setup-portable-linux.sh` (mismas bibliotecas, sin FUSE), luego `./SoundText` | `./scarica_strumenti.sh` |
| **Windows, instalador** (`SoundText-setup-*.exe`) o **portable** (`.zip`) | ejecuta el instalador, o extrae el zip y ejecuta `setup-windows.bat` (comprueba el Visual C++ Redistributable y Python; FluidSynth ya está incluido), luego `SoundText.exe` | `scarica_strumenti.bat` |
| **macOS** | desde el repositorio: `./install-macos.sh` (instala FluidSynth, PortAudio y Python con Homebrew, crea el virtualenv) | `~/Library/Application Support/SoundText/scarica_strumenti.sh` |

`scarica_strumenti.sh`/`.bat` necesitan Python 3.8+ (no hace falta para usar la aplicación). `./scarica_strumenti.sh` sin argumentos lista los grupos; `host` instala 7-Zip, sfizz y Surge XT; `libreria` compila el motor SFZ interno (unos 5 minutos).

### Instalación manual desde el código fuente

```bash
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# opcional, para la escucha directa en la aplicación:
sudo apt install fluidsynth fluid-soundfont-gm   # Debian/Ubuntu

# opcional, para la escucha directa con bucle y el micrófono:
sudo apt install libportaudio2                   # Debian/Ubuntu

# opcional, para los plugins LV2 (Linux; los VST3 no necesitan nada más):
sudo apt install liblilv-0-0                     # Debian/Ubuntu
```

Instrucciones detalladas para Debian/Ubuntu, Arch/CachyOS, Fedora,
openSUSE, **Windows y macOS** (incluida la instalación de fluidsynth y de un
SoundFont) en el menú **Ayuda → Guía del usuario** de la aplicación, o en
`docs/HELP.es.md`.

## Inicio

En Linux/macOS el script `run.sh` crea en el primer arranque el virtualenv
`venv/` con las dependencias de `requirements.txt` (las actualiza cuando el
archivo cambia) e inicia la aplicación; acepta los mismos argumentos que
`main.py`:

```bash
./run.sh
./run.sh examples/ensemble_demo.st
```

Con las dependencias ya instaladas también se puede iniciar directamente:

```bash
python3 main.py
# o abriendo directamente un proyecto de ejemplo:
python3 main.py examples/ensemble_demo.st
```

El idioma de la interfaz se elige en **Opciones → Idioma** (la primera vez,
SoundText usa el idioma del sistema si es uno de los cuatro disponibles; si
no, el inglés).

## Uso rápido

1. **+ Añadir pista → Pista con instrumento...**: elige un instrumento
   (Piano/Guitar/Bass/Trumpet/Drums) y ponle un nombre. Desde el mismo menú
   se crean pistas de audio o pistas ya generadas (batería, progresión de
   acordes...).
2. Pasa a la vista **Texto** y selecciona la pista en la columna Pistas de
   la izquierda: el editor se abre a la derecha.
3. Escribe la notación, p. ej.:
   ```
   16: 100@ c*4 e*4 g*4 e*4 Cmaj7 [kick hihat]
   ```
   La validación de sintaxis aparece debajo del editor en tiempo real.
4. Usa Solo/Mute/Volumen/Pan en la tira de la pista para la mezcla.
5. **Componer → Gestionar biblioteca de patterns (%Nombre)...** para
   definir `%Nombre` reutilizables en cualquier pista.
6. **▶ Play** para escuchar (requiere un sintetizador del sistema),
   **Proyecto → Exportar → MIDI...** para guardar el archivo `.mid`,
   **Proyecto → Exportar → Partitura MusicXML...** para abrir la canción en
   MuseScore, Finale, Sibelius o Dorico e imprimirla.
7. **Proyecto → Guardar** guarda en el formato de texto nativo `.st`, que
   también se puede leer y editar a mano.

## Pruebas

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

Las pruebas también se ejecutan automáticamente en GitHub con cada push
(workflow `.github/workflows/tests.yml`).

## Estructura del proyecto

```
soundtext/
  st_language/           (la biblioteca ST-language vive en el repositorio openssound/st-language: pip install, ver requirements.txt)
  core/
    instruments.py     perfiles de instrumento + mapa de percusión GM + catálogo General MIDI
    chords.py           -> st_language/chords.py (mismo módulo)
    notation.py          -> st_language/notation.py (mismo módulo)
    completion.py         autocompletado de los tokens en el editor
    model.py              Project/Track, lógica Solo/Mute, cambio de nombre/de instrumento
    project_io.py          formato de proyecto de texto (.st) + carpeta songs/
    tempo_map.py           -> st_language/timing.py (mismo módulo)
    arrangement.py         boxes de la vista Estructura de la canción (duraciones, aplanado)
    rhythm_generate.py     generación algorítmica de batería, bajo y acompañamiento
    key_detect.py          estimación de la tonalidad de la canción
    midi_convert.py         análisis MIDI compartido, indexación de la biblioteca &"Nombre"
    midi_export.py          exportación MIDI multipista o de una sola pista
    midi_import.py           importación MIDI -> notación (con reconocimiento del instrumento)
    musicxml_import.py       importación de partituras MusicXML (también .mxl) -> notación
    abc_import.py            importación de piezas ABC -> notación
    voice_merge.py           voces de un canal importado unidas en bloques { ; }
    import_lyrics.py         letra de las importaciones MIDI (también karaoke) y MusicXML
    score_render.py          partitura maquetada por Verovio (SVG para la vista y el PDF)
    playback.py               motor de reproducción (renderizado sin conexión + SoundFont + caché)
    audio_stream.py           reproducción directa del renderizado (salto, bucle A-B, posición exacta)
    metronome_sounds.py       sonidos del clic del metrónomo
    settings.py                ajustes persistentes (ruta del SoundFont, cuantización, idioma)
    i18n.py                    idiomas de la interfaz (tr() y los catálogos de locales/)
    reorganize.py               extracción/expansión automática de patterns
    audio_quantize.py            motor de cuantización audio -> notación
    audio_decode.py               lectura de archivos de audio (Qt Multimedia, alternativa ffmpeg)
    fluid.py                      conexión directa con la biblioteca FluidSynth
    audio_recorder.py              grabación desde el micrófono (sounddevice)
    audio_pitch.py                  detección de altura para pistas melódicas
    audio_percussion.py              detección de transitorios para pistas de percusión
    audio_dsp.py                      análisis de audio en numpy (ataques SuperFlux, altura YIN)
    audio_import.py                   cadena completa de importación audio -> notación
    midi_input.py                      teclado MIDI externo (mido + python-rtmidi)
  gui/
    main_window.py     ventana principal (editor, menús, barra de herramientas); sus partes en
                       main_window_project.py / _mixer.py / _playback.py
    arrangement_view.py vista Estructura de la canción (boxes, regla, cabezal, bucle)
    keyboard_play_dialog.py «Tocar con el teclado» (grabación desde el teclado del PC)
    midi_keyboard.py    teclado MIDI externo en el mismo diálogo (core/midi_input.py)
    rhythm_generate_dialog.py diálogos Generar batería/bajo/acompañamiento
    metronome_engine.py  clic del metrónomo sincronizado con la reproducción
    track_header.py     cabecera de la pista (M/S/●, ⋯, mandos Vol/Pan), igual en las dos vistas
    knob.py             mando compacto para volumen y pan
    track_widget.py     código de colores por familia de instrumentos, etiqueta del pan
    instrument_dialog.py gestión de instrumentos personalizados (selección GM por nombre)
    midi_library_dialog.py gestión de la biblioteca MIDI (subcarpetas incluidas)
    audio_import_dialog.py grabación/carga de audio + cuantización
    voicing_picker.py       menú de elección del voicing con doble clic en los acordes
    help_dialog.py       guía del usuario integrada
    highlighter.py         resaltado de sintaxis (basado en el tokenizador real)
    theme.py                hoja de estilo oscura global de la aplicación
  locales/              traducciones de la interfaz (en, fr, es) y extract.py
  assets/
    icon.png              icono de la aplicación
  examples/            proyectos .st de demostración de las funciones
  songs/                carpeta predeterminada para tus proyectos (Abrir/Guardar)
  midi/                 biblioteca de fragmentos MIDI que se llaman con &"Nombre",
                        organizable en subcarpetas (Guitar/, Blues/, ...)
  tests/                pruebas automáticas del motor de notación
  main.py                punto de entrada de la aplicación (aplica tema + icono)
  diagnose_audio.py       herramienta de diagnóstico de línea de comandos para calibrar
                          la detección de altura/la clasificación de percusiones con
                          grabaciones reales (ver 'python3 diagnose_audio.py --help')
```

## Licencia

Copyright © 2026 Sergio Scolaro.

SoundText es software libre: puedes redistribuirlo y/o modificarlo según
los términos de la **GNU General Public License versión 3** (archivo
[LICENSE](LICENSE)). Se distribuye con la esperanza de que sea útil, pero
**sin ninguna garantía**.

SoundText usa bibliotecas y contenidos de terceros (FluidSynth,
Qt/PySide6, pedalboard, NumPy, el SoundFont FluidR3_GM y otros),
cada uno con su propia licencia: autores, licencias y textos completos
están en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) (en italiano) y en
la carpeta [licenses/](licenses/). La guía (Ayuda → Guía del usuario,
capítulo 14) explica lo que estas licencias suponen para quien distribuye
el programa.
