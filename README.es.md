# SoundText

[Italiano](README.md) · [English](README.en.md) · [Français](README.fr.md) · **Español**

**SoundText** es un programa para escribir música como texto. Notas,
acordes y ritmos se escriben en un lenguaje sencillo, el **SoundText
Language**; SoundText los toca, los muestra en partitura y los mezcla con
efectos, amplificadores y plugins. Funciona en Linux, Windows y macOS, en
español, italiano, inglés y francés.

```
ST: 2.7
Tempo: 100 BPM

Track Acordes [Piano]:
  4: 4C | 4Am | 4F | 4G |

Track Melodia [Piano]:
  8: e g c*5 g e g c*5 g | a c*5 e*5 c*5 a c*5 e*5 c*5 |
  f a c*5 a f a c*5 a | g b d*5 b 4g |

Track Bateria [Drums]:
  8: [kick hihat] hihat [snare hihat] hihat [kick hihat] hihat [snare hihat] hihat |
```

Las mayúsculas son acordes (`C`, `Am`, `G7`): SoundText elige por sí solo
las notas adecuadas para el instrumento de la pista. Las minúsculas son
notas, `*5` la octava, `8:` la duración base, `|` el final del compás.

## Qué puedes hacer

- **Escribir la música**: notas, acordes con voicing automático o elegido,
  tresillos, ligaduras, dinámicas, automatizaciones, repeticiones, varias
  voces en la misma pista, letra. Mientras escribes, el editor colorea la
  sintaxis y señala los errores.
- **Organizar la canción**: la vista **Estructura** muestra cada pista como
  una fila de boxes (intro, estrofa, estribillo...) para mover, copiar y
  escuchar uno a uno. Los **patterns** (`%Nombre`) y la **biblioteca MIDI**
  (`&"Nombre"`) sirven para reutilizar partes.
- **Generar las partes**: batería, bajo, acompañamiento y melodías a partir
  de los acordes, sin IA, también en el estilo de tus canciones.
- **Dar forma al sonido**: mezclador, SoundFonts, instrumentos sampleados
  SFZ, efectos (EQ, compresor, delay, reverberación), amplificadores de
  guitarra y perfiles **NAM** de amplificadores reales, plugins **VST3** y
  **LV2**, mastering.
- **Tocar y grabar**: el teclado del ordenador o un teclado MIDI; pistas de
  audio para voz y guitarra, con varias tomas, loop y punch-in; de una
  grabación de audio a las notas.
- **Importar y exportar**: MIDI, MusicXML (MuseScore, Finale, Sibelius,
  Dorico), ABC, MTXT, WAV; la partitura se ve y se imprime en PDF
  directamente desde el programa.

Todo se explica en la **guía del usuario**, dentro del programa (**Ayuda →
Guía del usuario**, F1) y en [docs/HELP.es.md](docs/HELP.es.md).

## Instalación

### Paquetes listos

Desde las [Releases](https://github.com/openssound/soundtext/releases/latest) descarga el paquete para tu sistema:

| Sistema | Qué descargar | Luego |
|---|---|---|
| **Windows** | `SoundText-setup-<versión>.exe` (instalador) | ejecútalo; en la última página deja marcada la casilla que ejecuta `setup-windows.bat`, que comprueba el Visual C++ Redistributable |
| **Windows**, portable | `SoundText-windows-<versión>.zip` | extrae, ejecuta `setup-windows.bat`, luego `SoundText.exe` |
| **Linux**, AppImage | `SoundText-linux-<versión>.AppImage` y `setup-appimage.sh`, en la misma carpeta | `./setup-appimage.sh` (instala con `sudo` FUSE 2, FluidSynth, PortAudio, lilv y las bibliotecas de Qt; `--integra` añade la entrada de menú y el comando `soundtext`), luego inicia el AppImage |
| **Linux**, portable | `SoundText-linux-portable-<versión>.tar.gz` | extrae, ejecuta `./setup-portable-linux.sh` (las mismas bibliotecas, sin FUSE; también aquí `--integra`), luego `./SoundText` |

### Desde el código

Para macOS, que no tiene un paquete listo, o para seguir las
actualizaciones con git. Los scripts funcionan también descargados solos:
toman las fuentes de GitHub.

- **Linux**: `./install.sh` instala las bibliotecas del sistema (apt, dnf,
  pacman o zypper), copia el programa en `~/.local/share/soundtext`, crea
  el virtualenv, el comando `soundtext` y la entrada de menú. Si lo
  vuelves a ejecutar, actualiza. `--yes` sin preguntas, `--uninstall` quita
  el comando y el menú (los proyectos se quedan), `--purge` borra también
  los proyectos.
- **macOS**: `./install-macos.sh` instala Homebrew si falta, luego
  FluidSynth, PortAudio y Python; crea el virtualenv, el comando
  `soundtext` y **SoundText.app** en `~/Applications`. Mismas opciones que
  `install.sh`.
- **A mano**, con Python 3.10 o posterior y FluidSynth, PortAudio y lilv
  del sistema (los paquetes para cada distribución están en la guía):

  ```bash
  git clone https://github.com/openssound/soundtext.git
  cd soundtext
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  python3 main.py
  ```

Las instrucciones completas están en los capítulos 30-32 de la guía del
usuario.

### Después de instalar

El **SoundFont General MIDI** no está incluido: en el primer inicio
SoundText propone descargarlo (FluidR3 GM, unos 150 MB). Desde la misma
ventana, **Sonidos → Descargar e instalar...**, presente en todas las
versiones, se descargan también los instrumentos sampleados SFZ, los
plugins gratuitos, los perfiles NAM y las cajas IR. Hace falta conexión a
Internet.

Quien prefiera el terminal tiene los scripts `scarica_strumenti.sh` y
`scarica_strumenti.bat`, en la carpeta del programa (salvo con el
AppImage, donde se usa la ventana): hacen el mismo
trabajo y requieren Python 3.8+ (sin argumentos muestran un menú
numerado).

## Inicio

Los paquetes listos se inician desde el menú Inicio (instalador), desde
`SoundText.exe`, desde el AppImage o desde `./SoundText`; después de los
scripts de instalación, desde el menú de aplicaciones o con el comando
`soundtext`. Desde el código:

```bash
./run.sh                                # Linux, macOS, Git Bash en Windows
./run.sh examples/funk_in_mi.st         # abriendo enseguida un ejemplo
```

En el primer inicio `run.sh` crea el virtualenv `venv/` con las
dependencias de `requirements.txt` y las actualiza cuando el archivo
cambia.

El idioma se elige en **Opciones → Idioma**; la primera vez SoundText usa
el del sistema, si es uno de los cuatro disponibles, si no el inglés.

## Primeros pasos

1. **Proyecto → Abrir ejemplo...** abre una de las canciones de la carpeta
   `examples/`: escúchala con **F5** y mira cómo está escrita en la vista
   **Texto**.
2. El capítulo 1.2 de la guía, **Tu primera canción**, lleva en cinco
   pasos de un proyecto vacío a cuatro compases con acordes y melodía.
3. La gramática completa está en el capítulo 4 de la guía; la
   [especificación del SoundText Language](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md)
   (CC BY 4.0) la describe de forma formal.

Los proyectos se guardan como archivos `.st` de texto, legibles y
modificables con cualquier editor; la carpeta predeterminada es `songs/`.

## Para desarrolladores

**Tests**:

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

También se ejecutan en GitHub en cada push (`.github/workflows/tests.yml`).

**Estructura del proyecto**:

```
soundtext/
  main.py          el punto de entrada del programa
  core/            el motor: modelo del proyecto, archivos .st, MIDI, reproducción,
                   efectos, plugins, importación de audio, generación de partes
  gui/             la interfaz (PySide6): ventana principal, vista Estructura,
                   panel Efectos, diálogos
  docs/            la guía del usuario (HELP.md y sus traducciones)
  locales/         las traducciones de la interfaz
  examples/        canciones de ejemplo
  songs/           la carpeta predeterminada para tus proyectos
  midi/            la biblioteca MIDI (&"Nombre"), también en subcarpetas
  tests/           los tests automáticos
```

La notación es la biblioteca Python **st-language** (repositorio
[openssound/st-language](https://github.com/openssound/st-language),
`pip install st-language`): un motor sin dependencias, con los comandos
`st-language check | midi | musicxml`, que se puede usar también sin
SoundText.

## Licencia

Copyright © 2026 Sergio Scolaro.

SoundText es software libre: puedes redistribuirlo y/o modificarlo según
los términos de la **GNU General Public License versión 3** (archivo
[LICENSE](LICENSE)). Se distribuye con la esperanza de que sea útil, pero
**sin ninguna garantía**.

SoundText usa bibliotecas y contenidos de terceros (FluidSynth, Qt/PySide6,
pedalboard, NumPy y otros), cada uno con su propia licencia: autores,
licencias y textos completos están en
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) y en la carpeta
[licenses/](licenses/). El capítulo 29 de la guía explica qué implican
estas licencias para quien distribuye el programa.
