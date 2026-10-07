# Guía del usuario — SoundText

## Índice por temas

Busca aquí el tema que te interesa y ve a la sección indicada (los números son los de los títulos de esta guía).

| Tema | Sección |
| --- | --- |
| [La ventana del programa, barra de comandos, vistas](#1.0) | [1.0](#1.0) |
| [Buscar un comando (Ctrl+K) y atajos de teclado](#1.0bis) | [1.0bis](#1.0bis) |
| [Deshacer / Rehacer](#1.2) | [1.2](#1.2) |
| [Guardado automático y recuperación](#1.2bis) | [1.2bis](#1.2bis) |
| [Idioma de la interfaz](#1.3) | [1.3](#1.3) |
| [Escribir notas, acordes, silencios, duraciones, octavas, sostenidos y bemoles](#2) | [2](#2) |
| [Voicing de acordes y acordes con bajo alternativo (slash)](#2.8) | [2.8](#2.8), [2.9](#2.9) |
| [Repeticiones y tresillos / quintillos](#2.1) | [2.1](#2.1), [2.1bis](#2.1bis) |
| [Slide (pitch bend) y pedal de sustain](#2.3) | [2.3](#2.3), [2.4](#2.4) |
| [Dinámicas, crescendo y diminuendo](#2.5) | [2.5](#2.5) |
| [Cambios de tempo (accelerando, rallentando) y de compás](#2.6) | [2.6](#2.6), [2.7](#2.7) |
| [Tonalidad de la canción y octavas relativas](#2.7bis) | [2.7bis](#2.7bis), [2.18](#2.18) |
| [Controles de compás (|) y comentarios (//)](#2.10) | [2.10](#2.10) |
| [Varias voces en la misma pista y texto cantado](#2.12) | [2.12](#2.12), [2.13](#2.13) |
| [Automatizaciones (volumen, pan... que cambian en el tiempo)](#2.15) | [2.15](#2.15) |
| [Ligaduras, swing, repeticiones, signos e indicaciones](#2.16) | [2.16](#2.16), [2.17](#2.17) |
| [Micro-tempo, afinación, muchas pistas, MTXT](#2.19) | [2.19](#2.19) |
| [Anclas de compás (bar=N)](#2.20) | [2.20](#2.20) |
| [Transposición (transpose=, %Nombre+N)](#2.21) | [2.21](#2.21) |
| [reset:, anacrusa, versión del archivo (ST 2.6)](#2.22) | [2.22](#2.22) |
| [Acordes, notas de adorno, D.C./D.S., estrofas, título (ST 2.7)](#2.23) | [2.23](#2.23) |
| [Patrones (%Nombre): reutilizar y reorganizar partes](#4) | [4](#4) |
| [Biblioteca MIDI (&"Nombre") y carpeta de canciones songs/](#5) | [5](#5), [5bis](#5bis) |
| [Percusión y batería escrita a mano](#6) | [6](#6) |
| [Pistas e instrumentos, instrumentos personalizados](#7) | [7](#7) |
| [Mezclador: volúmenes, pan, mute, solo y volumen master](#8) | [8](#8), [8.1](#8.1), [8.2](#8.2) |
| [Reverb y chorus del sintetizador](#8.3) | [8.3](#8.3) |
| [Efectos: EQ, compresor, delay, reverb, noise gate, bucle de calibración](#8.4) | [8.4](#8.4) |
| [Amplificador de guitarra, distorsión, cajas y archivos IR](#8.4) | [8.4](#8.4) |
| [Perfiles NAM (amplificadores y pedales reales), dónde descargarlos](#8.4) | [8.4](#8.4) |
| [Mastering: efectos en el master y limitador](#8.5) | [8.5](#8.5) |
| [Sonidos de estudio con programas externos (re-amping)](#8.6) | [8.6](#8.6) |
| [Plugins VST3 y LV2, instrumento SFZ interno](#8.7) | [8.7](#8.7) |
| [Vista Estructura en cajas: estrofas, estribillos, mover y copiar partes](#8bis) | [8bis](#8bis) |
| [Congelar acordes, elegir el voicing, autocompletado](#9) | [9](#9), [9.1](#9.1), [9.2](#9.2) |
| [Generar batería, bajo, acompañamiento y riffs sin IA](#9bis) | [9bis](#9bis) |
| [Estilos personales (aprender de tus canciones) y melodías por frases](#9bis.1) | [9bis.1](#9bis.1), [9bis.2](#9bis.2) |
| [Importar y exportar MIDI](#10) | [10](#10) |
| [MusicXML y ABC: exportar e importar partituras](#10.1) | [10.1](#10.1), [10.2](#10.2), [10.3](#10.3) |
| [Ver e imprimir la partitura](#10.1bis) | [10.1bis](#10.1bis) |
| [Importación de audio: de voz, micrófono o archivo a notas](#10bis) | [10bis](#10bis) |
| [Tocar con el teclado del ordenador o un teclado MIDI](#10ter) | [10ter](#10ter) |
| [Pistas de audio: grabar voz y guitarra, exportar](#10quater) | [10quater](#10quater) |
| [Guardar el proyecto (.st)](#11) | [11](#11) |
| [Reproducción, bucle A-B, saltar a un punto](#12) | [12](#12) |
| [Elegir el SoundFont, SoundFont por instrumento](#12.3) | [12.3](#12.3), [12.4](#12.4) |
| [Metrónomo y humanización](#12.5) | [12.5](#12.5), [12.6](#12.6) |
| [Archivo de registro (si algo no funciona)](#13.1) | [13.1](#13.1) |
| [Tecnologías, agradecimientos, licencias](#14) | [14](#14) |
| [Instalación en Linux, Windows y macOS (al final de la guía)](#inst) | [↓](#inst) |

---

## 0. Terminología

- **SoundText Language**: el lenguaje de texto con el que se escribe la
  partitura (notas, acordes, percusiones, patterns, comandos de estado...).
- **ST-Syntax**: la gramática formal del SoundText Language — las reglas de
  sintaxis descritas en la sección 2.
- **SoundText Engine**: el motor que convierte un acorde abstracto (p. ej.
  `Cmaj7`) en notas MIDI concretas, según el instrumento de la pista (a
  menudo llamado también «motor de voicing» en esta guía).
- **.st**: extensión de los archivos de proyecto.

## 1. Conceptos básicos

El programa separa tres niveles: **intención abstracta** (notas y acordes
escritos en SoundText Language), **voicing concreto** (el SoundText Engine,
que depende del instrumento) y **reproducción** (motor MIDI). Cada pista
está asociada a un instrumento y contiene una secuencia de *tokens*
separados por espacios, conformes a la ST-Syntax.

### 1.0 La ventana

- **Barra de comandos**, desde la izquierda: el **transporte** (volver al
  inicio, Play/Pausa, Stop, **●** Grabar en la pista de audio
  seleccionada, bucle A-B, metrónomo), el bloque **Canción** (tempo,
  compás, tonalidad), la elección de la vista **Estructura / Texto** y el
  volumen **Máster**. Al pasar el ratón sobre un botón aparece para qué
  sirve y su atajo.
- **Barra de progreso**, a todo lo ancho debajo de la barra de comandos:
  tiempo transcurrido y duración; haz clic para saltar a ese punto.
- **Vista Estructura de la canción** (8bis): las pistas en boxes, con el
  mezclador en las cabeceras de las filas (8); o bien la **vista Texto**:
  las mismas cabeceras en columna a la izquierda y la notación de la pista
  seleccionada.

### 1.0bis Buscar un comando (Ctrl+K) y atajos

**Buscar un comando**: **Ctrl+K**, o la casilla «Buscar un comando…» arriba
a la derecha en la barra de menús (también **Ayuda → Buscar un
comando...**). Se escribe lo que se quiere hacer («exportar», «grabar»,
«generar bajo», «metrónomo», «tonalidad»...), se elige con las flechas y se
pulsa Intro. Se encuentran todas las opciones de los menús, incluidas las
de «+ Añadir pista»; junto a cada una aparecen el menú en el que está y su
atajo. Las mayúsculas y los acentos no cuentan.

**Atajos en la vista Estructura de la canción** (con el ratón o el foco en
el lienzo; en el editor de texto estas teclas sirven para escribir). Hay un
recordatorio abajo a la derecha en la barra de estado.

| Tecla | Acción |
|---|---|
| Espacio | Play / Pausa de la canción (en todas partes: F5) |
| Mayús+Espacio | escuchar solo el box seleccionado |
| R | grabar en la pista de audio seleccionada (en todas partes: Ctrl+R) |
| Supr | eliminar el box seleccionado |
| Ctrl+D | duplicar el box seleccionado |
| S | dividir el clip de audio seleccionado en el punto del cabezal |
| Ctrl+rueda | zoom horizontal (el punto bajo el ratón no se mueve) |
| Ctrl+= / Ctrl+- / Ctrl+0 | ampliar / reducir / zoom normal (también desde el menú Vista) |
| Ctrl+Z / Ctrl+Y | deshacer / rehacer |

Las opciones correspondientes también están en los menús **Editar**
(eliminar, duplicar, dividir), **Vista** (zoom) y **Reproducción**.

### 1.1 Resaltado de sintaxis y atajos

El editor colorea automáticamente cada token según su tipo: notas
(celeste), acordes (ámbar), percusiones (violeta), comandos de estado
`N:`/`N@` (verde), referencias `%pattern` y `&"midi"` (coral), bloques
`[...]` (amarillo), silencios (gris). Los comentarios `//` van en gris cursiva, los controles
de compás `|` en gris (en rojo subrayado si no caen en una barra de compás,
ver 2.10); los bloques de voces `{ ; }` en turquesa, la letra en rosa cursiva,
y dentro de grupos y voces cada token tiene su color. Los colores reflejan exactamente cómo
interpreta el motor el texto, así que también ayudan a localizar errores de
un vistazo.

Además, las cabeceras de las pistas tienen un borde coloreado según la
familia de instrumentos (guitarras, bajos, metales...), útil para
orientarse rápido cuando hay muchas pistas.

Atajos de teclado principales: `Ctrl+N` nuevo proyecto, `Ctrl+O` abrir,
`Ctrl+S` guardar, `Ctrl+Shift+S` guardar como, `Ctrl+T` añadir pista,
`Ctrl+E` editar pista, `Ctrl+Z`/`Ctrl+Y` deshacer/rehacer, `F5`
play/pausa, `F6` stop, `Ctrl+[`/`Ctrl+]` inicio/final del bucle, `Ctrl+L`
bucle sí/no, `F1` esta guía.

### 1.2 Deshacer/Rehacer

**Editar → Deshacer** (`Ctrl+Z`) y **Rehacer** (`Ctrl+Y` o
`Ctrl+Shift+Z`) valen para **cualquier cambio del proyecto**, venga de
donde venga: texto escrito en el editor, pistas añadidas, eliminadas o
renombradas, mezclador (volumen, pan, mute, solo, máster), tempo, compás y
tonalidad, batería/bajo generados, importación MIDI/audio o desde el
teclado en una pista, patterns, congelación de acordes, reorganización,
boxes de la vista Estructura de la canción. Al deshacer también se vuelve a
ver la pista en la que se estaba trabajando.

Escribir seguido en la misma pista, o arrastrar un control deslizante, se
convierte en un solo paso: basta una pausa de un segundo y medio para
empezar uno nuevo. El historial se borra al abrir o crear un proyecto. En
los diálogos (edición de un box, patterns...) el texto tiene en cambio su
propio Deshacer, independiente.

### 1.2bis Guardado automático y recuperación

Mientras el proyecto tiene **cambios sin guardar**, SoundText escribe una
**copia de recuperación** cada minuto (solo si algo ha cambiado mientras
tanto), en la carpeta `recupero/` de la configuración. El archivo del
proyecto no se toca: guardar sigue siendo decisión tuya.

- Al guardar, abrir o crear otro proyecto, o cerrar SoundText normalmente
  (incluso eligiendo **Descartar**), la copia se elimina.
- Si SoundText se cierra mal (fallo, bloqueo, ordenador apagado), en el
  próximo arranque pregunta si quieres **recuperar** el proyecto, indicando
  la hora de la copia y el archivo original. **Recuperar** lo vuelve a
  abrir como proyecto modificado: **Guardar** (`Ctrl+S`) lo escribe en el
  archivo original, o elige **Guardar como**. **Eliminar la copia** la
  borra, **Decidir después** la conserva para el próximo arranque.
- Varias ventanas de SoundText abiertas a la vez tienen cada una su propia
  copia: una ventana todavía abierta nunca se propone para recuperar.

El guardado normal también es «todo o nada»: SoundText escribe primero un
archivo temporal y lo pone en lugar del proyecto solo al final, así una
interrupción a medias (disco lleno, corte de luz) no deja un archivo `.st`
truncado.

### 1.3 Idioma de la interfaz

SoundText habla **italiano, inglés, francés y español**. El idioma se elige
en **Opciones → Idioma** y vale desde el próximo arranque: SoundText
pregunta si reiniciarse enseguida (si hay cambios sin guardar, antes pide
guardarlos). La primera vez se usa el idioma del sistema, si es uno de los
cuatro; si no, el inglés.

Los menús, las ventanas, los mensajes y esta guía están en el idioma
elegido. En cambio **no cambian** la notación (`c*4`, `Am7`, `kick`...) ni
las palabras del archivo `.st` (`Tempo:`, `Traccia`, `Effetti`...), que son
el formato de los proyectos: una canción escrita con la interfaz en
italiano se abre igual con la interfaz en español, y viceversa.

## 2. ST-Syntax (gramática del SoundText Language)

| Construcción | Significado | Ejemplo |
| --- | --- | --- |
| letra minúscula a-g | nota melódica | `c` |
| letra minúscula + `#` (sostenido) o `b`/`♭` (bemol) | nota alterada | `c#`, `eb`, `e♭` |
| `*n` después de una nota o un acorde | octava | `c*4`, `Cmaj7*3` |
| `/Nota` después de un acorde | bajo alternativo («acorde slash») | `C/E` (do con mi en el bajo) |
| letra MAYÚSCULA + sufijo | acorde abstracto | `Cmaj7`, `Am`, `G7` |
| `.estilo` después de un acorde | impone un voicing concreto (ver 2.8) | `Cmaj7.drop2`, `C.power` |
| palabra en minúscula (36 identificadores de percusión, ver sección 5) | evento de percusión | `kick` |
| número inicial | multiplicador de duración | `2c`, `4Cmaj7` |
| `r` / `Nr` | silencio (1 o N unidades de rejilla) | `r`, `3r` |
| `[...]` | eventos/notas simultáneos | `[c*4 e*4 g*4]`, `[kick hihat]` |
| `N:` | cambia la rejilla rítmica actual | `16:` (semicorcheas) |
| `NT:` / `NQ:` / `NS:` | grupos irregulares: tresillos / quintillos / septillos (ver 2.1bis) | `8T:`, `16Q:`, `8S:` |
| `N@` | cambia la velocidad actual (1-127) | `100@` |
| `%Nombre` | llama a un pattern | `%Rock1` |
| `&"Nombre"` | llama a un archivo MIDI de la biblioteca | `&"Intro"` |
| `N(...)` | grupo de repetición: repite N veces la secuencia entre paréntesis | `4(c d e f)` |
| `!` al final de una nota o un acorde | staccato (reduce a la mitad la duración audible) | `c!`, `Cmaj7!` |
| `x` al final de una nota o un acorde | mute/stop (nota muy breve, «apagada») | `cx`, `Cmaj7x` |
| `_` al final de una nota o un acorde | legato (nota ligeramente alargada) | `c_`, `Cmaj7_` |
| `nota>nota[>nota...]` | slide/portamento (pitch bend continuo entre dos o más notas) | `c*4>d*4`, `c*4>d*4>c*4` |
| `SON` / `SOFF` | pedal de sustain: activa/desactiva para todo lo que sigue | `SON c*4 SOFF` |
| `tempo=N` | fija el tempo (BPM) a partir de este punto | `tempo=120` |
| `>>` después de `tempo=N` | accelerando hasta el siguiente `tempo=N` | `tempo=100 >> c*4 tempo=140` |
| `<<` después de `tempo=N` | rallentando hasta el siguiente `tempo=N` | `tempo=140 << c*4 tempo=80` |
| `pppp@`...`ffff@` | dinámicas clásicas, equivalentes a una velocidad fija | `mf@` = `75@` |
| `>>` después de `N@`/dinámica | crescendo hasta el siguiente valor de velocidad | `p@ >> c*4 ff@` |
| `<<` después de `N@`/dinámica | diminuendo hasta el siguiente valor de velocidad | `110@ << c*4 30@` |
| **\|** | control de compás: aquí termina un compás (no suena, avisa si no cuadra, ver 2.10) | `c d e f` **\|** `g a b c` **\|** |
| `//` | comentario hasta el final de la línea (ignorado) | `c d e f // estrofa` |
| `'N` después de un token | valor de nota explícito, sin cambiar la rejilla (ver 2.11) | `c'8.` (corchea con puntillo), `[c e g]'2`, `r'4`, `e'8T` |
| `{ ... ; ... }` | voces que empiezan juntas en la misma pista (ver 2.12) | `{ c*5 d*5 e*5 f*5 ; 4c*4 }` |
| `"..."` | letra: una sílaba por nota, sobre las notas anteriores (ver 2.13) | `c d e 2f "Ma- ri- a, sei"` |
| `vol=N` `expr=N` `pan=N` `mod=N` `rev=N` `cho=N` | automatizaciones: volumen, expresión, panorama (-1..1), modulación, envíos de reverberación y chorus (ver 2.15) | `vol=80`, `pan=-0.5` |
| `>>` después de una automatización | rampa continua hasta el siguiente valor con el mismo nombre; `>>exp`, `>>log`, `>>s` eligen la curva | `vol=0 >>exp 4c vol=100` |
| `<` / `>` al final de una nota | crescendo / diminuendo durante la nota sostenida (regulador) | `2c<`, `c'2>` |
| `~` al final de una nota | ligadura de prolongación: la nota sigue en la siguiente igual, incluso pasada la barra de compás (ver 2.16) | `2c~ \| 2c` |
| `(` ... `)` al final de las notas | ligadura de expresión: las notas intermedias suenan ligadas (ver 2.16) | `c( d e f)` |
| `swing=N` / `swing16=N` | swing de las corcheas / semicorcheas (50 = recto, 66 = ternario) | `swing=62 8: c d e f` |
| `bar=N` | ancla de compás: lleva el cursor al comienzo del compás N, con los silencios necesarios (ver 2.20) | `bar=29 c d e f` |
| `transpose=N` | transposición: las notas, acordes y slides siguientes suenan N semitonos más agudos o graves (ver 2.21); `%Nombre+N` transpone un patrón | `transpose=-2 c d e` |
| `\|:` ... `:\|` | repetición: la parte entre los dos signos se toca dos veces (ver 2.17) | `\|: c d e f :\|` |
| `\|1.` `\|2.` `\|\|` | casillas de la repetición: un final distinto en cada pasada (ver 2.17) | `\|1. g a :\| \|2. 4c \|\|` |
| `$signo` al final de una nota | acento, calderón, trino, mordente, grupeto, tenuto, marcato (ver 2.17) | `c$fermata`, `d$tr`, `e$accent` |
| `$"texto"` | indicación sobre el pentagrama | `$"rit."`, `$"dolce"` |
| `rel:` / `abs:` | octavas relativas (cada nota va cerca de la anterior) / absolutas (ver 2.18) | `rel: c d e f g a b c` |
| `*+` / `*-` después de una nota (en `rel:`) | una octava arriba / abajo | `rel: g c*+ c*-` |
| `key=K` | las notas toman las alteraciones de la tonalidad K (ver 2.18) | `key=G f` (= fa sostenido) |
| `n` después de una nota | becuadro: quita la alteración de la tonalidad | `key=G fn` |

El carácter `|` es el **control de compás** (ver 2.10): no suena ni mueve
nada, solo declara dónde termina un compás. Las duraciones se acumulan de
todos modos a lo largo de la línea de tiempo, así que las `|` son
opcionales. En el archivo de proyecto `.st` el carácter aparece también en
la cabecera de un box de la vista «Estructura de la canción» (sección
8bis), para indicar su posición en tiempos, p. ej.
`Box Basso1 "Intro" |4:` — un detalle del formato de guardado.

**Rampas y cierre obligatorio**: una rampa `>>`/`<<` siempre debe cerrarse
con otro comando **del mismo tipo** (velocidad tras velocidad, tempo tras
tempo) antes de que llegue uno del otro tipo, o antes del final de la pista
— si no, la validación señala un error explícito en lugar de dejar la rampa
«huérfana» (abierta pero sin ningún efecto audible, un error silencioso
difícil de notar solo escuchando). Un cambio de rejilla (`N:`) en medio de
una rampa ya abierta no la cierra ni la rompe — puede aparecer libremente
antes de la nota/el acorde que la cierra.

### Bemol: `b`, `♭` o `-` (atajo de escritura)

El bemol se puede escribir con la letra `b` (p. ej. `eb`), con el símbolo
musical real `♭` (p. ej. `e♭`), o con un guion `-` (p. ej. `e-`): son tres
sinónimos perfectamente equivalentes para el analizador, tanto en las notas
como en la fundamental de un acorde (`Bb7` = `B-7` = `B♭7`). La letra `b`
sigue siendo válida por compatibilidad con lo escrito hasta ahora, pero
puede confundirse visualmente con la letra de nota `b` (si) — por eso **el
editor sustituye automáticamente por `♭` un `-` escrito justo después de
una letra de nota** (p. ej. al escribir `e` y luego `-` aparece `e♭`), así
en pantalla siempre se ve el símbolo correcto sin tener que buscar `♭` en
el teclado. La sustitución solo se produce cuando el `-` sigue
inmediatamente a una letra de nota al principio de un token (después de un
espacio, `[`, `(`, `>`, o una cifra de multiplicador): un `-` escrito en
otro contexto (p. ej. después de `snare`) sigue siendo un guion normal.

### Calidades de acorde admitidas
`(vacío)`/`maj`, `m`/`min`, `7`, `maj7`, `m7`, `dim`, `dim7`, `aug`,
`sus2`, `sus4`, `6`, `m6`, `9`, `maj9`, `m9`, `mMaj7`, `m7b5`, `add9`,
`7sus4`, `7b9`, `7#9`, `5`, `7alt`, `11`, `13`, `maj13`, `°`, `°7`.

Las seis últimas son alias o extensiones pensados para la notación que se
escribiría «de oído» leyendo un cifrado real:
- **`5`** (p. ej. `E5`): power chord, solo fundamental y quinta, sin
  tercera — equivale a escribir el acorde con el voicing `.power`
  (`E.power`), pero también se reconoce como calidad propia (p. ej. en la
  importación MIDI: una simple quinta tocada ahora se reconoce como `5`, en
  lugar de quedar como un bloque explícito ambiguo).
- **`°`** / **`°7`** (p. ej. `C°`, `C°7`): alias de la notación clásica para
  `dim`/`dim7`, mismos intervalos, mismo voicing.
- **`7alt`** (p. ej. `G7alt`): dominante alterada, aproximada con los mismos
  intervalos que `7b9` (la gramática no modela por separado las tensiones
  alteradas #9/#11/b13).
- **`11`**, **`13`**, **`maj13`**: extensiones más allá de la novena (`13`
  omite la oncena, como es habitual en jazz para evitar el choque con la
  tercera mayor).

### 2.8 Voicing explícito en los acordes (`.estilo`)

Un sufijo opcional `.estilo` después de la calidad del acorde (antes del
posible `/octava`) obliga al motor de voicing a usar un algoritmo concreto
en lugar del automático del instrumento:

```
Cmaj7          -> voicing automático según el instrumento de la pista
Cmaj7.drop2    -> impone el voicing Jazz Drop-2
C7.cagEd*3     -> forma E del sistema CAGED, octava 3
```

**Prioridad**: si está presente, el sufijo siempre tiene precedencia sobre
el algoritmo automático del instrumento. **Alternativa inteligente**: si un
estilo no tiene sentido para el instrumento de la pista (p. ej. `.barre` en
un piano), el motor lo sustituye automáticamente por el equivalente
genérico más cercano (p. ej. `.close`) — nunca es un error. Un estilo
**desconocido** (una errata), en cambio, lo señala la validación como
cualquier otro token no reconocido.

Estilos generales (válidos en cualquier instrumento):
- `noroot`: omite la fundamental.
- `shell`: omite la quinta.
- `close`: notas apiladas lo más juntas posible.
- `open`: forma abierta, notas repartidas en varias octavas.
- `inv1` / `inv2` / `inv3`: 1.ª, 2.ª o 3.ª inversión (tercera, quinta y
  séptima en el bajo respectivamente; si el acorde no tiene notas
  suficientes para la inversión pedida, se usa la más alta disponible).

Estilos para guitarra (alternativa automática si se usan en otros
instrumentos): `barre`, `Caged`/`cAged`/`caGed`/`cagEd`/`cageD` (las 5
formas del sistema CAGED), `drop2`, `drop3`, `triad`, `power`
(fundamental+quinta), `openpos` (aproximación de acordes en primera
posición), `hendrix` (fundamental sola en el bajo + el resto una octava más
arriba), `top` (acorde una octava más arriba), `bottom`
(fundamental+quinta+séptima, sin la tercera). Las combinaciones
calidad/estilo más comunes (p. ej. `Cmaj7.drop2`, `C7#9.hendrix`) usan una
tabla de voicings cuidada para mayor precisión; las demás combinaciones
usan un algoritmo genérico equivalente. Como en el resto del motor, no hay
un modelo real de cuerdas/trastes: son aproximaciones musicalmente
sensatas sobre notas MIDI abstractas, no digitaciones físicas.

Estilos para teclado (alternativa automática si se usan en otros
instrumentos): `left` (mano izquierda fundamental/quinta grave, mano
derecha el resto), `right` (voicing compacto solo para la mano derecha),
`spread` (acorde amplio a dos manos).

Ejemplos válidos: `Cmaj7`, `Cmaj7.drop2`, `C7.cagEd`, `C.power`,
`Am7.open`, `F.barre`.

### 2.9 Bajo alternativo en los acordes (acorde «slash»)

Un sufijo opcional `/Nota` después de la calidad (y después del posible
`.estilo`, antes del posible `*octava`) indica un bajo distinto de la
fundamental del acorde — la clásica notación «slash» de los cifrados
(`C/E` = acorde de do con mi en el bajo):

```
C/E            -> do mayor con mi en el bajo
Dm7/G          -> re menor séptima con sol en el bajo
C.drop2/E*4    -> como arriba, voicing drop2, octava 4
```

El motor de voicing calcula primero el acorde con normalidad (fundamental,
calidad, estilo) y luego añade la nota de bajo pedida una octava por debajo
del voicing obtenido (bajando más octavas si hace falta para quedar por
debajo de todas las demás notas) — siempre es la nota más grave que suena,
como en un verdadero acorde slash. Transponer un acorde con bajo
alternativo desplaza también el bajo el mismo número de semitonos.

**Nota técnica**: `/` después de un acorde indica solo el bajo
alternativo; la octava se escribe siempre con `*n` (ver secc. 2), también
junto al bajo (`C/E*3`). La forma antigua con cifras después de la barra
(`C7/3`, `c/4`) ya no es válida.

### 2.1 Grupos de repetición

Una secuencia de tokens entre paréntesis, precedida de un número, se repite
ese número de veces:

```
4(2C7 2e c d 2A7)   -> repite 4 veces la secuencia: 2C7 2e c d 2A7
```

Los grupos se pueden anidar (`2(c 2(d e))`) y pueden contener cualquier
token válido, incluidos patterns y referencias MIDI.

### 2.1bis Grupos irregulares (tresillos / quintillos / septillos)

Una letra opcional después del número de un comando de rejilla (`N:`,
sección 3) activa una agrupación irregular en lugar de la subdivisión
binaria normal, reduciendo proporcionalmente la duración de cada nota:

| Letra | Grupo | Proporción | Ejemplo |
| --- | --- | --- | --- |
| `T` | tresillo | 3 notas en el espacio de 2 | `8T:` (tresillos de corcheas: 3 en una negra) |
| `Q` | quintillo | 5 notas en el espacio de 4 | `16Q:` (quintillos de semicorcheas: 5 en una negra) |
| `S` | septillo | 7 notas en el espacio de 4 | `8S:` (septillos de corcheas: 7 en dos negras) |

```
8T: c d e            -> tresillo de corcheas: las tres notas llenan una negra
16Q: c d e f g       -> quintillo de semicorcheas: las cinco notas llenan una negra
8S: c d e f g a b    -> septillo de corcheas: las siete notas llenan dos negras
```

Como en la rejilla binaria, el comando sigue activo hasta que se vuelve a
cambiar (sección 3): no hace falta repetirlo antes de cada nota del grupo.
Se puede volver a la subdivisión binaria en cualquier momento con un
comando `N:` sin letra (p. ej. `16:` después de `16Q:`).

### 2.2 Modificadores de la nota (y del acorde)

Un solo carácter al final de una nota o de un acorde (después de la posible
octava `*n`, y después del posible `.estilo` de voicing en un acorde)
cambia su articulación, sin alterar la posición de las notas siguientes en
la línea de tiempo (la nota/el acorde sigue ocupando toda la unidad de
rejilla; solo cambia cuánto tiempo se oye):

- **`!` staccato**: suena durante el 50% de la duración nominal; el resto
  es silencio.
- **`x` mute**: se «apaga» casi enseguida (~15% de la duración nominal),
  para un efecto amortiguado/percusivo.
- **`_` legato**: se alarga un poco más allá de la duración nominal
  (~115%), para «ligarse» suavemente a la siguiente.

En los acordes se puede combinar con el voicing explícito (2.8), p. ej.
`Cmaj7.drop2!` (voicing Drop-2 + staccato). El mismo modificador aplicado a
un acorde actúa sobre **todas** las notas del voicing, no solo sobre la
fundamental. Nota: los bloques simultáneos `[...]` todavía no admiten este
modificador final; para un «power chord staccato» se usa un acorde con
nombre y voicing `.power`, p. ej. `E.power!`.

### 2.3 Slide (pitch bend / portamento)

Dos o más notas unidas por `>` (sin espacios) producen un deslizamiento
continuo de altura de una a otra:

```
c*4>d*4        -> se desliza de Do4 a Re4 en una unidad de cuadrícula (como una nota)
c*4>d*4>c*4    -> sube de Do4 a Re4 en una unidad y vuelve a Do4 en otra
                  (bend-and-release, 2 unidades en total)
```

La regla es una sola: el multiplicador de un paso es la duración de la
rampa que **sale** de ese paso hacia el siguiente (1 si falta); el
multiplicador del **último** paso es cuánto se queda la nota en la altura
alcanzada (0 si falta: el slide termina al llegar).

```
5c*4>d*4       -> rampa lenta de Do4 a Re4 durante 5 unidades
2c*4>3d*4      -> sube en 2 unidades y luego se queda en Re4 otras 3
                  (bend rápido y luego sostenido)
2c*4>2d*4>3c*4 -> sube en 2 unidades, baja en otras 2 y luego se queda
                  en la altura de llegada otras 3
```

Una cadena puede tener tantos pasos como se quiera (`c*4>d*4>c#*4>c*4`...).
Un slide que duraría cero (`0c*4>d*4`) es un error.

Técnicamente se exporta como una sola nota MIDI (un solo note_on/note_off
para toda la cadena) con una secuencia de mensajes de Pitch Bend que
interpolan progresivamente de una etapa a la siguiente (con la amplitud del
pitch bend ajustada automáticamente mediante RPN para cubrir bien slides
incluso de más de una octava). Ver también la sección 10 para saber cómo la
importación MIDI reconoce automáticamente un bending (incluido un
bend-and-release) en un archivo existente y lo traduce a esta sintaxis.

### 2.4 Pedal de sustain (SON / SOFF)

Los tokens `SON` y `SOFF`, colocados libremente en el flujo de notas,
activan/desactivan el pedal de sustain (piano) para todo lo que sigue,
hasta encontrar el comando opuesto:

```
Piano — AcousticPiano:
  8: SON c*3 g*3 c*4 e*4 g*4 e*4 c*4 g*3 SOFF
  8: SON a*2 e*3 a*3 c*4 e*4 c*4 a*3 e*3 SOFF
```

Si se olvida un `SOFF`, el programa suelta igualmente el pedal de forma
automática al final de la pista, para evitar que una nota se quede atascada
en una reverberación infinita.

### 2.5 Dinámicas clásicas y rampas (crescendo/diminuendo)

Además del valor numérico explícito (`100@`), la velocidad acepta las
indicaciones dinámicas clásicas:

| Marcador | Velocidad |
| --- | --- |
| `pppp@` | 10 |
| `ppp@` | 23 |
| `pp@` | 36 |
| `p@` | 49 |
| `mp@` | 62 |
| `mf@` | 75 |
| `f@` | 88 |
| `ff@` | 101 |
| `fff@` | 114 |
| `ffff@` | 127 |

Si a un valor de velocidad (numérico o dinámico) le sigue el símbolo `>>`
(crescendo) o `<<` (diminuendo), la velocidad de las notas siguientes se
interpola linealmente hasta el siguiente valor de velocidad que aparezca:

```
8: p@ >> c*4 d*4 e*4 f*4 f@       -> crescendo de 49 a 88 en las 4 notas
8: 110@ << g*4 f*4 e*4 d*4 30@     -> diminuendo de 110 a 30
```

Después de las flechas se puede elegir la **curva** de la rampa: `>>exp`
empieza despacio y acelera, `>>log` empieza rápido y frena, `>>s` es suave
al principio y al final (`p@ >>exp c d e f ff@`). También vale para las
rampas de tempo y para las automatizaciones (sección 2.15).

### 2.6 Cambios de tempo (accelerando/rallentando)

Dentro de una pista, el comando `tempo=N` (1-999) fija el tempo
(BPM) al instante a partir de ese punto:

```
tempo=120 c*4 d*4    -> tempo fijado en 120 BPM
```

Como en la dinámica, `>>` (accelerando) o `<<` (rallentando) después de un
comando `tempo=N` interpola progresivamente el tempo hasta el siguiente `tempo=N`:

```
tempo=100 >> c*4 d*4 e*4 f*4 tempo=140    -> accelerando de 100 a 140 BPM
tempo=140 << c*4 d*4 e*4 f*4 tempo=80      -> rallentando de 140 a 80 BPM
```

Nota: el tempo es por naturaleza un concepto compartido por todo el
proyecto (todas las pistas suenan sobre la misma línea de tiempo); un
cambio de tempo declarado en una pista se aplica, por tanto, a toda la
canción a partir de ese punto, no solo a esa pista.

### 2.7 Cambios de tempo y de compás por compás

Además de la forma simple (`Tempo: 120 BPM`, `Metrica: 4/4`, un solo valor
para toda la canción), la cabecera del proyecto también acepta una lista de
cambios indexados por número de compás:

```
Tempo: 1: 120, 5: 140, 9: 100
Metrica: 1: 4/4, 5: 3/4, 8: 4/4
```

Significa: tempo 120 BPM desde el compás 1, 140 BPM desde el compás 5, 100
BPM desde el compás 9; compás 4/4 desde el compás 1, 3/4 desde el compás 5,
4/4 desde el compás 8. Las posiciones (en tiempos) de los compases
posteriores al primero se calculan automáticamente teniendo en cuenta el
compás vigente en cada tramo.

**Barra de progreso, resaltado y campos Tempo/Compás durante la
reproducción**: el archivo MIDI exportado, la barra de progreso, el
resaltado del token que está sonando en el editor y los campos **Tempo
(BPM)** y **Compás** de la barra de herramientas principal usan todos el
mismo mapa de tempo/compás del proyecto (todos los cambios por compás más
los marcadores en línea `tempo=N`): así siempre muestran el valor realmente
vigente en ese punto de la canción, no una estimación basada solo en el
tempo/compás inicial. Al parar la reproducción, los campos Tempo/Compás
vuelven al valor «en reposo» del proyecto (el del compás 1).

### 2.7bis Tonalidad de la canción

La cabecera del proyecto también puede declarar la tonalidad de la canción
(línea `Tonalita: <valor>`), que también se puede fijar desde el campo
**Tonalidad** de la barra de herramientas principal, junto a Tempo y
Compás:

```
Tonalita: Am
```

Formato: letra de nota (A-G) + alteración opcional (`#` o `b`) + `m`
opcional para el menor, p. ej. `C`, `F#`, `Ebm`, `Am` (mayor si falta la
`m`). Es una información descriptiva/de referencia (no influye en el
voicing ni en el reconocimiento de acordes); al importar un archivo MIDI
que declara una tonalidad (evento meta *key signature*) se reconoce y se
fija automáticamente. Si el archivo declara do mayor o no declara nada (do
es el valor predeterminado de muchos secuenciadores, así que no es fiable),
la tonalidad se estima a partir de las notas como hace **Analizar
tonalidad**. También la usa **Tocar con el teclado** (sección 10ter) en las
disposiciones de teclado «Escala de la tonalidad».

Si no la conoces ya (o no estás seguro), **Componer → Analizar
tonalidad...** la estima automáticamente analizando las notas realmente
escritas en todas las pistas no percusivas del proyecto (batería excluida),
con el algoritmo clásico de Krumhansl-Schmuckler: compara la distribución
de las 12 clases de altura usadas (ponderada por la duración) con los
perfiles tonales típicos de cada una de las 24 tonalidades posibles y elige
la más parecida, fijándola automáticamente en el campo Tonalidad
(sobrescribiendo el valor que hubiera). Es una estimación estadística, no
un verdadero análisis armónico: puede equivocarse en canciones muy cortas,
cromáticas o que modulan — un buen punto de partida, no un veredicto
infalible. Si el proyecto no contiene notas con altura (ninguna pista, o
solo de percusión), lo indica en lugar de adivinar.

### 2.10 Controles de compás (`|`) y comentarios (`//`)

**Controles de compás.** Una `|` entre dos tokens declara «aquí termina un
compás». No suena ni mueve el tiempo: el programa solo comprueba que en ese
punto haya de verdad una barra de compás, según el **Compás** del proyecto
y sus cambios por compás (sección 2.7). También puede ir pegada a una nota
(`d*4|`).

```
4: c d e f | g a b c | 2c 2e |
8: c d e f g a b c | 2: c c |
```

Si una `|` no cae en una barra de compás, la barra bajo el editor se vuelve
naranja e indica qué compás no cuadra y por cuánto, por ejemplo
`compás 2: falta 1 corchea` o `compás 3: 1 negra de más`; la `|`
equivocada se vuelve roja y subrayada. La información sobre herramientas de
la barra enumera todos los avisos. **No es un error de sintaxis**: la
canción suena y se exporta igual, es una ayuda para notar una nota que
falta o una duración equivocada. Una nota que falta desplaza todo lo que
sigue, pero se señala una sola vez: las `|` siguientes se miden teniéndolo
en cuenta y solo avisan si hay otro error.

- Las barras de compás son las de la **canción**: en un box de la vista
  Estructura de la canción cuentan desde la posición del box (un box que
  empieza a mitad de compás tiene su primera `|` tras medio compás).
- Dentro de un pattern o de un grupo `N(...)` la `|` se comprueba en cada
  repetición; el aviso señala la referencia `%Nombre` o el grupo.
- Dentro de un bloque `[...]` la `|` no está permitida (error de sintaxis).

**Comentarios.** Desde `//` hasta el final de la línea el texto se ignora:
sirve para anotar secciones, acordes, ideas. Una barra sola (`C/E`,
`&"Blues/bajo"`) conserva su significado de siempre.

```
// Estrofa
4: Am | F | C | G |     // ciclo de cuatro acordes
```

Los comentarios y los saltos de línea se conservan en el archivo `.st`, en
los box, en la transposición de los box y al congelar los acordes. No se
conservan en el cuerpo de los patterns (guardados como secuencia de tokens)
ni en las operaciones que reescriben todo el texto de la pista (Reorganizar
con patterns, Expandir patterns). En el archivo `.st` una línea vacía
cierra un bloque: las líneas vacías dentro del texto de una pista se
eliminan al guardar (antes truncaban el resto de la pista).

### 2.11 Valores de nota explícitos (`'8.`)

Además de la rejilla (`N:` seguido de multiplicadores), una duración puede
escribirse como **valor de nota**, con un apóstrofo al final del token:

| Escritura | Valor | Duración en negras |
| --- | --- | --- |
| `c'1` | redonda | 4 |
| `c'2` | blanca | 2 |
| `c'4` | negra | 1 |
| `c'8` | corchea | 1/2 |
| `c'16`, `c'32`, `c'64` | semicorchea, fusa, semifusa | 1/4, 1/8, 1/16 |
| `c'4.` / `c'8.` | negra / corchea **con puntillo** | 1 1/2 / 3/4 |
| `c'2..` | blanca con doble puntillo | 3 1/2 |
| `c'8T` / `c'4T` | corchea / negra de **tresillo** | 1/3 / 2/3 |
| `c'16Q`, `c'8S` | quintillo, septillo (como las rejillas `NQ:`, `NS:`) | |

```
8: c*4'8. d*4'16 e*4 e*4 [c e g]'2    // ritmo con puntillo sin cambiar de rejilla
```

El valor vale **solo para ese token**: la rejilla actual sigue siendo la
misma (en el ejemplo, `e*4 e*4` son corcheas de la rejilla `8:`).
Funciona con notas, acordes (`C7'2`), bloques (`[c e g]'2`), silencios
(`r'4`), percusiones (`kick'16`) y slides. Un multiplicador delante se
suma: `2c'8` dura dos corcheas. La articulación puede ir antes o después:
`c'8!` y `c!'8` son la misma corchea staccato. La rejilla sigue siendo
cómoda para los ritmos regulares; el valor explícito es más legible para
las frases irregulares y para quien viene de la partitura.

### 2.12 Varias voces en la misma pista (`{ ; }`)

Un **bloque de voces** contiene dos o más secuencias, separadas por `;`,
que **empiezan juntas**, cada una con sus duraciones. El bloque dura lo
que la voz más larga y luego la pista sigue:

```
4: { c*5 d*5 e*5 f*5 ; 4c*4 } g*4           // melodía sobre una nota tenida
4: {
  8: e*5 d*5 c*5 d*5 e*5 e*5 2e*5            // mano derecha
  ;
  2c*4 2g*3                                  // mano izquierda
}
```

A diferencia de `[...]`, donde todo empieza y termina a la vez, cada voz
tiene su ritmo: es lo que hace falta para el piano a dos manos, una
melodía sobre un acorde tenido, la guitarra clásica.

- Cada voz empieza con el **estado** (rejilla, velocidad) del punto en que
  se abre el bloque; los cambios hechos **dentro** de una voz se quedan
  ahí.
- Dentro de una voz vale toda la gramática: grupos `N(...)`, patterns
  `%Nombre`, controles de compás `|` (cada voz se comprueba por su
  cuenta), letra, incluso otros bloques de voces.
- El bloque puede ocupar varias líneas; un `;` fuera de un bloque es un
  error.
- En el editor cada voz tiene su propio **fondo de color** (azul la
  primera, ámbar la segunda, luego lila y verde; un bloque anidado empieza
  por otro color): se ve enseguida dónde empieza y termina cada una,
  incluso cuando el bloque ocupa varias líneas. Las llaves y los `;` se
  quedan sin fondo.
- En la partitura (secciones 10.1 y 10.1bis) las voces se convierten en
  **voces del mismo pentagrama**, con las plicas hacia arriba y hacia
  abajo.

### 2.13 Letra (`"..."`)

Una cadena entre comillas es la **letra** de las notas que la
**preceden**, a partir de la nota que sigue a la letra anterior (o desde
el principio): una sílaba por nota, separadas por espacios. Se escribe
como debajo de una línea de partitura:

```
4: c*4 d*4 e*4 2f*4
"Ma- ri- a, sei"
```

- Un guion al final (`Ma-`) indica que la palabra sigue en la sílaba
  siguiente; en la partitura las sílabas se unen con el guion.
- `_` no da a la nota una sílaba nueva: la sílaba anterior se
  **prolonga** (melisma, con la línea de extensión en la partitura).
- `*` salta una nota (sin sílaba).
- Los silencios y las percusiones no reciben sílabas.
- La sílaba también puede ir pegada a la nota: `c"Ma-" d"ri-" e"a"`.
- Dentro de un grupo `2(...)` la letra se repite con las notas; después de
  un bloque de voces va en la **primera voz** (una voz también puede tener
  su propia letra, dentro del bloque).
- La letra no se oye: va a la partitura (debajo de las notas), al MusicXML
  y al MIDI exportado (eventos *lyrics*, que leen los programas de
  karaoke).
- Si hay **más sílabas que notas**, el editor muestra un aviso (naranja),
  como con los controles de compás. Un `//` dentro de las comillas forma
  parte de la letra, no abre un comentario.

### 2.14 La especificación y la biblioteca ST-language

La notación tiene una **especificación formal pública**:
[docs/spec/ST-language.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md) (en inglés; en italiano
[ST-language.it.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.it.md)), con licencia **CC BY 4.0**
(se puede copiar, traducir y adaptar citando la fuente). Describe la
gramática completa, cómo el texto se convierte en notas en el tiempo, los
errores y avisos, el formato de los archivos `.st` y la correspondencia
con el MIDI, con una **suite de conformidad** ([`docs/spec/conformance/`](https://github.com/openssound/st-language/tree/main/docs/spec/conformance)):
los casos de prueba que otro programa debe superar para leer ST-language
como SoundText.

El motor de la notación es también una **biblioteca Python autónoma**,
`st_language`, sin dependencias externas: es la misma que usa SoundText,
así que los dos dan siempre el mismo resultado. Se instala con
`pip install st-language` y ofrece comandos de terminal:

```
st-language check cancion.st         # errores y avisos (compases, letra)
st-language midi cancion.st -o cancion.mid
st-language musicxml cancion.st      # partitura cancion.musicxml
st-language events cancion.st        # los eventos en JSON
echo "4: c d e f | 2g 2g" | st2mid - -o melodia.mid --instrument Trumpet
```

Un archivo sin cabeceras de pista es una canción de una sola pista
(`--instrument` elige su instrumento). Desde Python: `import st_language as
st`, luego `st.parse(texto)`, `st.validate(texto)`, `st.check(texto)`,
`st.load_song("cancion.st")`, `st.to_midi(cancion, "cancion.mid")`. Así las
canciones escritas en ST se pueden comprobar y exportar sin abrir
SoundText (por ejemplo desde un script, o en un repositorio de canciones).

### 2.15 Automatizaciones (volumen, expresión, panorama... que cambian en el tiempo)

Las dinámicas (`p@`, `>>`) cambian la **velocidad**, es decir, la fuerza
con la que se toca cada nota: una nota ya empezada se queda como está. Las
**automatizaciones**, en cambio, actúan sobre el instrumento de forma
**continua**, incluso mientras una nota está sostenida, como mover un
fader del mezclador durante la interpretación:

| Comando | Qué cambia | Valores | Inicial |
| --- | --- | --- | --- |
| `vol=N` | volumen de la pista | 0-127 | 100 |
| `expr=N` | expresión: el volumen "dentro" de la dinámica (cuerdas, vientos, órgano) | 0-127 | 127 |
| `pan=N` | posición estéreo: -1 izquierda, 0 centro, 1 derecha | -1..1 (con decimales) | 0 |
| `mod=N` | modulación (vibrato, en muchos instrumentos) | 0-127 | 0 |
| `rev=N` | envío a la reverberación | 0-127 | 0 |
| `cho=N` | envío al chorus | 0-127 | 0 |
| `bend=N` | pitch bend, en semitonos (como la rueda del sintetizador) | -24..24 (con decimales) | 0 |
| `ccN=V` | cualquier controlador MIDI N (0-119), p. ej. `cc74` brillo | 0-127 | 0 |

Solo, el comando cambia el valor en ese punto. Seguido de `>>` (o `<<`, es
lo mismo) abre una **rampa** que llega hasta el siguiente comando con el
mismo nombre, pasando por todos los valores intermedios:

```
4: vol=0 >>exp 4c*4 vol=100          // fundido de entrada en la nota sostenida
4: pan=-1 >> c d e f pan=1           // el sonido pasa de izquierda a derecha
4: expr=40 >>s 2C 2F expr=127 r      // crece bajo dos acordes
8: rev=20 c d e f rev=90 4g          // la reverberación sube de golpe
```

La **curva** de la rampa se elige después de las flechas: `>>` (lineal),
`>>exp` (empieza despacio y acelera: el fundido de entrada natural),
`>>log` (empieza rápido y frena: el fundido de salida natural), `>>s`
(suave al principio y al final).

**Reguladores en las notas.** Un `<` al final de una nota (o de un acorde,
un bloque, un slide) hace un **crescendo durante la nota**, un `>` un
diminuendo: es el regulador de la partitura, hecho con la expresión (de la
mitad al valor actual o al revés), que luego vuelve a su valor:

```
4: 4c*5<            // una nota sostenida que crece
4: 2C< 2G>          // un acorde crece, el otro baja
4: c'2> [c e g]<    // con un valor de nota o sobre un bloque
```

- Las automatizaciones valen para toda la pista, incluso escritas dentro
  de un bloque de voces `{ ; }`; rampas con nombres distintos pueden
  superponerse (`vol=` y `pan=` a la vez).
- `vol=` se combina con el volumen del mezclador (`vol=100` = el volumen
  del fader); `pan=`, `rev=` y `cho=` escritos en el texto sustituyen los
  valores del mezclador a partir de ese punto.
- Una rampa abierta debe cerrarse con un valor del mismo nombre; si no, la
  validación señala un error; un regulador en un silencio y un regulador
  dentro de una rampa `expr=` abierta también son errores.
- Se oyen en la reproducción y van al MIDI exportado (como control change:
  CC7, CC11, CC10, CC1, CC91, CC93); en la partitura, las rampas de
  `vol=`/`expr=` y los reguladores aparecen como reguladores de crescendo
  y diminuendo.
- Forman parte de la especificación ST-language desde la versión 1.1
  (2.14).

### 2.16 Ligaduras y swing

**Ligadura de prolongación `~`.** Un `~` al final de una nota, un acorde o
un bloque la **une** a la siguiente igual: suenan como una sola nota, tan
larga como las dos juntas. Sirve sobre todo para sostener una nota más
allá de la barra de compás, donde la división en compases no deja
escribirla entera:

```
4: c d 2f~ | 2f g a |        // el fa dura 4 tiempos, a caballo del compás
4: 4C7~ | 4C7 | 4F |         // un acorde sostenido dos compases
4: c'2~ c'8 r'8 d'4          // también con valores de nota
```

La nota después del `~` debe ser la misma (`c#~ db` vale: es el mismo
sonido); si no, es un error. Las percusiones, los silencios y los slides
no se ligan.

**Ligadura de expresión `( )`.** Un `(` al final de la primera nota y un
`)` al final de la última unen una frase: las notas intermedias suenan
**ligadas** (pegadas una a otra, como una frase cantada), la última como
está escrita. En la partitura aparece el arco sobre las notas.

```
4: c( d e f) g( a b c*5)
4: 2(c( d) e)                // dentro de un grupo, la ligadura se repite
```

Una nota con articulación propia (`d!` staccato) la conserva también dentro
de la ligadura. Las ligaduras no se anidan y no atraviesan un bloque de
voces `{ ; }`.

**Swing.** `swing=N` hace que las corcheas "se balanceen" desde donde lo
escribes: en cada tiempo la primera corchea se alarga y la segunda se
acorta, como se toca en el jazz, el blues y el shuffle. N es la parte del
tiempo que se da a la primera corchea: 50 es recto, 66 es ternario (el
swing clásico), hasta 80. `swing16=N` hace lo mismo con las semicorcheas
(funk, hip hop). `swing=50` quita el swing.

```
swing=62 8: c d e f g a b c*5   // se escribe recto, suena con swing
swing16=58 16: kick hihat snare hihat kick kick snare hihat
```

Todo se escribe recto: los controles de compás y la partitura siguen
regulares (en la partitura aparece la indicación "Swing"); solo cambia
cómo suena, en la reproducción y en el MIDI exportado.

### 2.17 Repeticiones, signos e indicaciones

**Repeticiones.** Se escriben como en la partitura: `|:` abre la parte
que se repite, `:|` la cierra, y la parte se toca dos veces. Sin `|:`,
la repetición empieza al principio de la canción (o al final de la
repetición anterior).

```
4: |: c d e f | g a b c :| c*5 d*5 e*5 f*5 |
```

Para un final distinto en cada pasada se usan las **casillas**: `|1.`
abre la primera, `:|` la cierra y vuelve al principio, `|2.` abre la
segunda, que termina con `||` (o con el final del texto). Con tres
casillas se toca tres veces, y así sucesivamente.

```
4: |: c d e f |1. g a b c :| |2. 4c*5 || d e f g |
```

Se oye todo completo; en la **partitura** aparecen los signos de
repetición y las casillas de verdad, siempre que la repetición empiece y
termine en las barras de compás y que cada pasada sea igual a la primera
en todas las pistas (si no, la partitura la escribe completa). Un grupo
`2(...)` que ocupa compases enteros también se imprime como repetición.
`|:`, `:|`, `|1.` y `||` son también controles de compás, y las
repeticiones no se anidan.

**Signos en las notas.** Un `$` seguido del nombre, al final de una nota,
un acorde o un bloque (después del valor de nota), añade un signo que se
ve en la partitura y se oye:

| Signo | Qué hace |
| --- | --- |
| `$accent` | acento: la nota suena más fuerte |
| `$marcato` | acento fuerte |
| `$tenuto` | tenuto |
| `$fermata` | calderón: toda la canción se para en la nota (duración doble); también en un silencio |
| `$tr` | trino con la nota de arriba (en la tonalidad de la canción) |
| `$mordent` | mordente: nota, nota de abajo, nota |
| `$turn` | grupeto: arriba, nota, abajo, nota |

```
4: c$accent d e$tenuto f$fermata | 2g$tr a$mordent b$turn |
4: [c e g]$accent$tenuto r$fermata
```

Trino, mordente y grupeto se tocan en las notas sueltas (en acordes y
bloques quedan como un signo en la partitura).

**Indicaciones de texto.** `$"texto"` escribe una indicación sobre el
pentagrama en ese punto: `$"rit."`, `$"dolce"`, `$"a tempo"`. No cambia
el sonido: para frenar de verdad se usa una rampa de tempo
(`tempo=100 << ... tempo=70`, sección 2.6).

### 2.18 Octavas relativas y tonalidad

Dos comandos hacen que las melodías sean mucho más cortas de escribir. Se
pueden usar juntos, y los dos son opcionales: sin ellos todo funciona
como antes.

**Octavas relativas (`rel:`).** Después de `rel:` ya no se escribe la
octava: cada nota va a la octava **más cercana a la nota anterior** (como
mucho una cuarta arriba o abajo, contando las letras). Para saltar más
lejos se añade `*+` (una octava arriba) o `*-` (una octava abajo), incluso
repetidos (`*++` dos octavas arriba, `*--` dos abajo); `*n` sigue valiendo y fija la octava exacta.

```
rel: c d e f g a b c          // escala de do hasta el do de arriba
rel: c*5 b a g f e d c        // y bajando
rel: g c*+ c*- c                // c*+ salta arriba, c*- vuelve abajo
```

La primera nota después de `rel:` va cerca del do de la octava por
defecto del instrumento. Después de un bloque `[...]` se vuelve a partir
de su primera nota; los acordes y las percusiones no cuentan. `abs:`
vuelve a las octavas absolutas. En las repeticiones y los grupos cada
repetición vuelve a partir de la misma nota, para que suene igual.

**Tonalidad (`key=`).** Después de `key=G` cada nota **sin** alteración
toma la de la tonalidad: en sol mayor `f` es fa sostenido. Un sostenido
o un bemol escrito vale solo para esa nota; `n` (o `♮`) es el becuadro y
quita la alteración de la tonalidad.

```
key=G rel: g a b c d e f g    // sol mayor sin escribir el sostenido
key=Bb rel: b c d e f g a b   // si bemol mayor: b y e son bemoles
key=Dm rel: d e f g a b c# d  // re menor (si bemol) con el do sostenido
key=G f fn f#                 // fa sostenido, fa natural, fa sostenido
```

`key=off` quita la tonalidad. Los acordes (`C`, `F7`...) no cambian: los
cifrados son siempre absolutos. La tonalidad de la canción (en la barra
de arriba) sirve para la armadura de la partitura; `key=` dice cómo leer
las notas de la pista.

Los **patrones** (`%Nombre`) se leen siempre con octavas absolutas y sin
tonalidad, sea cual sea el modo de la pista que los usa: suenan igual en
todas partes.

**Reescribir una pista existente.** El botón **Alturas relativas y
tonalidad**, debajo del editor, reescribe la pista actual con `rel:` y,
si la canción tiene tonalidad, `key=`: las notas siguen siendo las
mismas, el texto se acorta. Es útil después de importar desde MIDI,
MusicXML o ABC. **Transponer** (en las cajas) también conoce los dos
modos: en `rel:` las notas siguen siendo relativas, y con `key=` también
se transpone la tonalidad.

### 2.19 Microtiempo, afinación, muchas pistas, MTXT

**Microtiempo (`shift=`).** `shift=N` hace sonar las notas siguientes N
milisegundos **después** (N positivo) o **antes** (N negativo) de donde
están escritas; `shift=0` las devuelve a tiempo. El ritmo escrito no
cambia: los controles de compás y la partitura siguen iguales, solo
cambia el momento en que suenan las notas. Va de -500 a 500.

```
4: kick shift=20 snare shift=0 kick shift=20 snare   // caja un poco atrás
shift=-10 8: c c g g a a g g                          // bajo que empuja hacia delante
```

Sirve para el "feeling" y para alinear una parte con una grabación; los
ritmos de verdad se escriben con los valores, los grupos irregulares y
el swing.

**Afinación (`tune=`).** `tune=N` afina el instrumento N cents (de -100
a 100: 100 cents son un semitono). Es una automatización como `vol=` o
`bend=`: vale para toda la pista, incluso durante una nota, y acepta
rampas.

```
tune=-20 4: c d e f              // para tocar con un disco afinado un poco bajo
tune=0 >> 4: c d e f tune=50     // sube un cuarto de tono en cuatro notas
```

**Más de 15 pistas.** Cada pista tiene siempre su propio canal MIDI: a
partir de la 16.ª pista melódica, la exportación MIDI usa un segundo
"puerto" (16 canales más), luego un tercero, etc. SoundText los toca y
los vuelve a importar correctamente; algunos reproductores MIDI muy
antiguos ignoran los puertos y tocan esas pistas en los canales de las
primeras.

**MTXT.** **Proyecto → Exportar → MTXT...** escribe la canción en
[MTXT](https://github.com/Daninet/mtxt), un formato de texto con un
evento por línea y los tiempos en negras (`1.5 note C4 dur=0.5
vel=0.8`), fácil de leer, comparar y hacer modificar por una IA.
Contiene notas, instrumentos, automatizaciones, tempo y compás, como el
MIDI. **Proyecto → Importar → MTXT...** hace lo contrario: lee el archivo
como un MIDI (una pista por canal, con los nombres de los canales). La
biblioteca hace lo mismo desde la terminal con `st-language mtxt
cancion.st` y `st-language mtxt archivo.mtxt` (que se convierte en un
`.mid`).

### 2.20 Anclas de compás (`bar=`)

**Dónde entra una parte.** `bar=N` lleva el cursor al **comienzo del
compás N**, con los silencios necesarios: en lugar de contar pausas
(`28%Rest`) se escribe el compás en el que entra la parte.

```
Guitar 2:
  bar=29                          // la segunda guitarra entra en el compás 29
  8: 100@ c d e f g a b c
```

- Si la pista está **antes** de ese punto, el hueco se rellena con
  silencio; si está **exactamente** ahí, no pasa nada.
- Si la pista está **ya más allá** (una parte más larga de lo previsto),
  el ancla no retrocede: la parte sigue donde está y el editor muestra
  un **aviso** en el ancla ("compás 29: la pista ya está 2 negras más
  allá del inicio"), como con los controles de compás `|`.
- Los compases se cuentan como en el resto del programa: desde el 1,
  según el compás del tema y sus cambios. Dentro de un patrón o de un
  grupo repetido vale el compás del tema en cada repetición.
- Una ligadura `~` no puede cruzar un ancla que requiere silencio.

`bar=` coloca y `|` verifica: juntos dicen dónde debe estar cada parte
y avisan cuando una se ha desplazado. En **Extraer patrones** los
bloques con un ancla no se extraen, porque un patrón no sabe en qué
compás está.

### 2.21 Transposición (`transpose=`, `%Nombre+N`)

**Transponer sin reescribir.** `transpose=N` hace sonar las notas,
acordes, slides y bloques siguientes N semitonos **más agudos** (N
positivo) o **más graves** (N negativo) que lo escrito; `transpose=0`
vuelve a la altura escrita. Va de -60 a 60.

```
4: c d e f g a b c*5              // en Do
transpose=2 4: c d e f g a b c*5  // la misma melodía en Re
transpose=0
```

**Un patrón en otra tonalidad.** Tras el nombre de un patrón se escribe
cuántos semitonos transponerlo: `%Tema+7` lo toca una quinta más aguda,
`%Tema-12` una octava más grave, `2%Tema+3` dos veces, tres semitonos más
agudo. No hacen falta patrones copiados: el tema se escribe una sola vez.

```
Pattern %Tema:
  key=Eb 8: 90@ g*5 b*5 e*6 2d*6 2b*5 |

Violini1:
  %Tema  %Tema-3  %Tema+12     // Mi bemol, luego Do (-3), luego una octava más aguda
```

- La transposición vale para **todo** lo que hay dentro del patrón,
  también para los patrones que llama, y se **suma** a la que ya está en
  vigor (`transpose=3 %Tema+4` suena 7 semitonos más agudo).
- Un `transpose=` escrito dentro de un patrón termina con el patrón.
- Lo mismo vale para la biblioteca MIDI: `&"Bajo"+7`, `&"Bajo"-12` (sección 5).
- Con `key=` las notas transpuestas se escriben en la nueva tonalidad:
  `key=G` con `transpose=2` es La mayor (el fa sostenido escrito pasa a
  sol sostenido, el sol pasa a la). Sin tonalidad, un bemol sigue siendo
  bemol y las demás notas alteradas toman el sostenido. También en la
  partitura.
- Los acordes cambian de nombre (`C7/E` +5 es `F7/A`) y suben una octava
  cuando pasan el Do; con +12 cada acorde sube una octava.
- Las percusiones y las pausas no cambian. Si una nota transpuesta sale
  del rango MIDI, el programa lo señala como error.
- **Extraer patrones** no extrae los bloques que contienen un
  `transpose=`: dentro de un patrón la transposición terminaría con el
  patrón.

### 2.22 `reset:`, anacrusa y versión del archivo (ST 2.6)

**`reset:` — volver a empezar.** Devuelve todo al estado inicial:
cuadrícula `4:`, velocity 80, sin swing ni desplazamiento,
transposición 0, octavas absolutas, sin tonalidad. Las automatizaciones
(`vol=`, `pan=`...) se quedan donde están. Sirve cuando un trozo de texto
debe sonar igual sea lo que sea lo que haya antes:

```
rel: key=G 8: 100@ transpose=2 g a b c
reset: c d e f           // otra vez negras, velocity 80, do mayor
```

Cada box de la vista Estructura empieza con un `reset:`: así un
`transpose=` o un `key=` escrito en un box nunca pasa al box siguiente.

**Compás de anacrusa.** Si la canción empieza con una anacrusa, escribe
cuántas negras dura en el campo **Anacrusa** de la barra de la canción (o
`Levare: 1` en el archivo). El compás 1 pasa a ser el primero completo:
los controles de compás `|`, las anclas `bar=N`, los cambios de tempo y
de compás por compás, la regla de la vista Estructura, el metrónomo y la
partitura cuentan desde ahí. La anacrusa es el compás 0.

```
Levare: 1
Metrica: 3/4

Violino:
  4: g | c e g | c*5 2r |      // una negra de anacrusa, luego compases de 3/4
```

**Nombres de los archivos MIDI entre comillas.** El nombre de un archivo
de la biblioteca MIDI se escribe siempre entre comillas: `&"Riff"`,
`&"Blues/bass-line"`, también con espacios (`&"intro take 2"`). Lo que
sigue a las comillas es siempre la transposición: `&"Riff"-2` es el
archivo `Riff` dos semitonos más abajo, `&"take-2"` es el archivo que se
llama `take-2`. Las canciones escritas antes (con `&Riff`) se convierten
solas al abrirlas, y quedan iguales; si escribes `&Riff` sin comillas el
editor te dice cómo corregirlo.

**Versión y palabras en inglés en el archivo.** El archivo `.st` empieza
con `ST: 2.7`, la versión del lenguaje en que está escrito; al abrir un
archivo de una versión más reciente, el programa avisa. El programa lee
también las palabras clave en inglés (`Track`, `Instrument`, `Meter`,
`Key`, `Pickup`, `percussion=`, `octave=`, `yes`), cómodo para quien
escribe los archivos a mano; al guardar usa siempre las formas italianas.

### 2.23 Acordes, notas de adorno, D.C./D.S., estrofas y título (ST 2.7)

**Más acordes.** Además de los de siempre: `C7#5` (también `Caug7`),
`C7b5`, `Cm11`, `Cm13`, `C69` (sexta y novena: en `C6/9` la barra sería el
bajo), `Cmaj7#11`, `C7#11`, `C9sus4`, `C7b13`, `Cadd11`, `Cmadd9`,
`C7sus2`, `Csus` (= `Csus4`), `C13b9`.

**Más percusiones.** El resto de la batería General MIDI: `triangle`,
`triangle_mute`, `agogo_hi`, `agogo_low`, `guiro_short`, `guiro_long`,
`whistle_short`, `whistle_long`, `cuica_mute`, `cuica_open`, `vibraslap`
y `side_stick` (el mismo sonido que `rimshot`).

**Valores y tempo.** `c'128` es la semigarrapatea; la letra `D` hace
dosillos (`8D: c d`, dos corcheas en el tiempo de tres, como en 6/8). El
tempo acepta decimales (`tempo=72.5`) y la figura que se cuenta:
`tempo=60'4.` son 60 negras con puntillo por minuto; la partitura escribe
así el metrónomo.

**Notas de adorno.** `d'g c` es una acciaccatura (el Re antes del Do),
`d'G c` una apoyatura; valen también para acordes, bloques y percusiones
(`snare'g snare` es un flam). No ocupan tiempo escrito: suenan justo antes
de la nota, que pierde esa duración.

**Nuevos signos en las notas.** `C$arp` (acorde arpegiado),
`c$staccatissimo`, `c$sfz` (sforzando), `c$fp` (forte-piano), `c$trem`
(trémolo; en la batería `snare$trem` es un redoble), `c$harmonic`
(armónico).

**Cifrados sin sonido.** `$Am7` escribe el cifrado sobre el pentagrama
sin tocarlo: útil para un lead sheet con solo la melodía
(`$C c d e f $G7 g a b c`).

**D.C., D.S., Coda y Fine.** Se escriben como signos: `$segno`, `$coda`,
`$tocoda`, `$fine`, `$dc` (da capo), `$ds` (dal segno). Se tocan como los
toca un músico; en la vuelta las repeticiones se hacen una sola vez, con
la última casilla:

```
4: c d e f | g a b c*5 $fine | e d c d | 4e $dc     // D.C. al Fine
4: $segno c d e f | g a b c*5 $tocoda | 4e $ds $coda | 4c |   // D.S. al Coda
```

**Más estrofas.** Una letra que empieza con el número de la estrofa va
bajo la misma música: `"Ma- ry had a lit- tle lamb"` y luego
`"2: Ev- ry where that Ma- ry went"`. La partitura escribe una línea por
estrofa.

**Título, autores, cambios de tonalidad, instrumentos transpositores.**
Al principio del archivo `.st` se pueden escribir `Titolo:` (o `Title:`),
`Autore:` (`Composer:`) y `Parole:` (`Lyricist:`), que van a la
partitura, y la tonalidad por compás como el tempo:
`Tonalita: 1: C, 17: G`. En un instrumento definido en el archivo,
`trasposizione=-2` lo hace transpositor (trompeta en Si♭: -2, saxo alto
en Mi♭: -9): se escribe siempre en sonidos reales y la partitura escribe
su parte transportada. El archivo guardado declara `ST: 2.7`.

## 3. Estado actual

La rejilla y la velocidad siguen activas hasta que se vuelven a cambiar:

```
100@ 8: c e 60@ g a 100@ c
```
`c` y `e` duran una corchea con velocidad 100; `g` y `a` con velocidad 60;
la última `c` vuelve a velocidad 100. Los comandos de estado no generan
ningún evento: no ocupan tiempo en la línea de tiempo.

## 4. Patterns (%Nombre)

Se definen en la biblioteca de patterns (menú **Componer →
Gestionar biblioteca de patterns**) o directamente en el archivo `.st`:

```
Pattern %GtrArp:
  16: 90@ c e g e 70@ c e g e
```

y se llaman en cualquier pista con `%GtrArp`.

**Repetición:** anteponiendo un número se repite el pattern N veces:
```
3%GtrArp        -> toca %GtrArp tres veces seguidas
```

### 4.1 Escuchar un pattern

En el diálogo **Componer → Gestionar biblioteca de patterns**, cada
pattern seleccionado se puede escuchar con el botón **▶ Escuchar**,
eligiendo el instrumento de la vista previa en la lista desplegable de al
lado (el pattern sigue siendo universal: la elección solo sirve para la
prueba de audio). Los cambios todavía no guardados en el editor se incluyen
automáticamente en la vista previa. Mientras suena, en el cuerpo del pattern
se resalta el punto que estás escuchando, como en el editor principal y en
los diálogos de edición del box, de generación, de «Tocar con el teclado» y
de conversión de audio.

### 4.2 Reorganizar la canción con patterns

Menú **Componer → Extraer patterns de las pistas...**: analiza todas
las pistas del proyecto actual, localiza bloques de eventos que se repiten
(también no consecutivos) y los convierte automáticamente en patterns
reutilizables, sustituyendo las apariciones por `%Nombre` (con repetición
`N%Nombre` cuando las apariciones son consecutivas). El contenido musical
no cambia: es solo una reescritura más compacta y legible de la misma
secuencia de eventos. Si no se encuentran repeticiones lo bastante largas,
el programa lo indica sin modificar nada.

Los patterns generados toman el nombre del **instrumento de la pista** de
la que proceden (p. ej. `%Guitar1`, `%Guitar2`, `%Bass1`...), no un prefijo
genérico. Además, un pattern extraído **nunca contiene referencias a otros
patterns**: si una pista ya usa `%Lib1` junto con material literal
repetido, `%Lib1` sigue siendo una referencia independiente y nunca se
incluye dentro de un nuevo pattern (sin patterns anidados).

Menú **Componer → Expandir patterns en las pistas...**: la operación
inversa. Sustituye cada referencia `%pattern` y `&"midi"` de las pistas por
los tokens literales correspondientes (con la repetición ya aplicada),
haciendo el proyecto totalmente autosuficiente; los patterns que ya no se
usan se eliminan. Útil antes de compartir una canción sin tener que
adjuntar también la biblioteca de patterns, o para examinar/editar a mano
cada evento sin la indirección de las referencias.

Las dos operaciones actúan sobre todo el proyecto, piden confirmación antes
de aplicarse y se ejecutan en segundo plano con una barra de progreso: la
interfaz sigue respondiendo y la operación se puede cancelar. El tiempo de
búsqueda de los bloques repetidos está siempre limitado (por pista), de
modo que incluso en pistas muy largas la reorganización nunca se queda
bloqueada indefinidamente.

### 4.3 Menú contextual sobre una selección (clic derecho)

Al seleccionar con el ratón una secuencia de tokens en el editor (pista,
cuerpo de un pattern o de un box) y hacer clic con el **botón derecho**, se
abre un menú contextual con tres opciones. En las vistas previas de los
diálogos (Generar batería/bajo/acompañamiento/progresión de acordes, Tocar
con el teclado, conversión de audio, biblioteca MIDI) el menú solo tiene
**▶ Play**, y antes detiene la posible escucha de la vista previa entera:

- **▶ Play**: reproduce solo la selección, con el instrumento de la pista
  actual, reconstruyendo automáticamente la última rejilla rítmica y
  velocidad activas antes de la selección (así suena como sonaría en su
  contexto original, no siempre a 1/4 y velocidad 80).
- **Agrupar**: encierra la selección entre paréntesis, convirtiéndola en un
  grupo `(...)` (ver sección 2.1); útil antes de aplicarle a mano un
  multiplicador de repetición (p. ej. convertir `(...)` en `4(...)`).
- **Convertir en pattern...**: pide un nombre, crea un nuevo pattern con la
  selección y sustituye la propia selección por `%NombrePattern` — una forma
  rápida de extraer a mano un solo fragmento en pattern, como alternativa a
  la búsqueda automática de **Extraer patterns de las pistas...** (sección
  4.2).

La selección hecha con el ratón siempre se «ajusta» a los límites de los
tokens enteros que toca (no hace falta seleccionar con precisión
milimétrica); si el último token incluido es un comando de estado sin nada
detrás (`N:` o `N@`), se descarta automáticamente, así el grupo o el
pattern resultante nunca termina «colgado» sin un evento sonoro.

Si la selección contiene también una referencia a un pattern (`%Nombre`) o
a un archivo MIDI (`&"Nombre"`), en el menú aparece **solo Play**: no está
permitido agrupar ni convertir en un nuevo pattern una indirección que ya
existe.

### 4.4 Cambiar el nombre de un pattern

El botón **Cambiar nombre** (junto a «Nuevo» en el diálogo **Componer → Gestionar biblioteca de patterns**) cambia el nombre del pattern
seleccionado y actualiza automáticamente al nuevo nombre cada referencia
`%nombreantiguo` que ya exista — tanto en las pistas como en el cuerpo de
los demás patterns —, para que el cambio de nombre no rompa en silencio lo
que lo llama. El nuevo nombre debe seguir la misma sintaxis que una
referencia a pattern (letras, cifras y guiones bajos, sin espacios) y no
puede coincidir con el de un pattern ya existente.

## 5. Biblioteca MIDI (&"Nombre")

En la carpeta `midi/` (junto al programa, vacía tras una primera
instalación: la biblioteca es tuya) puedes guardar frases musicales breves
como archivos `.mid`, organizadas también en subcarpetas por categoría
(género, artista, instrumento...), por ejemplo:

```
soundtext/
├── midi/
│   ├── Guitar/
│   │   └── Intro.mid
│   ├── Blues/
│   │   └── shuffle.mid
│   ├── Drums/
│   └── Bass/
└── songs/
    └── tus_proyectos.st
```

Una referencia `&"Nombre"` busca **recursivamente en todas las subcarpetas**:

```
Guitar:
  &"Intro" &"Intro" %GtrArp
```

si tienes un archivo `midi/Guitar/Intro.mid`, lo encuentra
automáticamente (o cualquier otra subcarpeta que contenga un archivo
`Intro.mid`), sin indicar la ruta.

**Rutas completas:** si el mismo nombre existe en varias subcarpetas, la
referencia es ambigua y la validación lo señala, indicando las alternativas
encontradas; para resolverlo basta con completar la ruta:

```
&"Blues/bass_line"      -> usa concretamente midi/Blues/bass_line.mid
```

**Repetición** (como en los patterns):

```
2&"bass_line"            -> repite la referencia dos veces
```

**Transposición:** igual que con los patrones, un número tras el nombre
transpone el archivo esos semitonos: `&"Intro"+7` lo toca una quinta más
aguda, `&"Intro"-12` una octava más grave, `2&"Intro"+2` dos veces, dos
semitonos más agudo (sección 2.21). El nombre va entre comillas, así que
guiones y espacios no dan problemas: `&"Blues/bass-line"-2` es
`Blues/bass-line` dos semitonos más abajo (sección 2.22).

Gestión desde la interfaz: menú **Componer → Gestionar biblioteca
MIDI**. Desde allí puedes importar un archivo `.mid` existente (indicando
también una subcarpeta de destino), cambiarle el nombre/moverlo,
eliminarlo, escucharlo con **▶ Escuchar el archivo original** (reproduce el
archivo .mid tal cual, con todos sus canales), o ver/editar una vista previa
en texto (se convierte el canal con más notas) y «regenerar» el archivo MIDI
a partir del texto editado, eligiendo el instrumento que se usará para el
voicing. Cuando cambias el nombre de un archivo o lo mueves y la canción
abierta lo llama, el programa propone actualizar las llamadas `&"Nombre"`
(también en los box y los patrones), manteniendo multiplicador y
transposición.

Nota: `&"Nombre"` importa solo el canal más significativo del archivo MIDI
(normalmente el que tiene más notas); para una importación multipista
completa usa en su lugar **Proyecto → Importar → MIDI...**, que crea una pista
por cada canal.

## 5bis. Carpeta de canciones (songs/)

Los diálogos **Abrir proyecto** y **Guardar como** se abren por defecto en
la carpeta `songs/` (junto al programa): es el sitio pensado para tus
composiciones, distinto de `examples/`, que contiene los proyectos de
demostración de las funciones del programa.

## 6. Percusión

36 identificadores fijos, asignados al General MIDI Drum Map (canal 10) y
sin octavas. Corresponden, por orden, a las teclas usadas en «Tocar con el
teclado» (sección 10ter): fila de números (1-9, luego 0 ' ì), fila Q, fila
A.

- Kit básico (fila de números): `kick`, `snare`, `hihat`, `hihat_open`,
  `tom1`, `tom2`, `floor`, `crash`, `ride`, `kick2`, `rimshot`, `clap`.
- Otros toms/platillos/charles (fila Q): `snare2`, `hihat_pedal`,
  `tom_lowmid`, `tom_hi`, `tom_highfloor`, `china`, `ride_bell`,
  `tambourine`, `splash`, `cowbell`, `crash2`, `ride2`.
- Percusión latina (fila A): `bongo_hi`, `bongo_low`, `conga_mute`,
  `conga_open`, `conga_low`, `timbale_hi`, `timbale_low`, `cabasa`,
  `maracas`, `claves`, `woodblock_hi`, `woodblock_low`.

## 7. Pistas e instrumentos

- **Añadir pista**: botón **+ Añadir pista** (debajo de la última cabecera,
  tanto en la vista Estructura de la canción como en la vista Texto) o menú **Pista → Añadir**. El botón abre un menú con:
  - **Pista con instrumento...** (Ctrl+T) y **Pista de audio...**;
  - **Generar una pista**: **Batería**, **Progresión de acordes**, **Bajo a
    partir de acordes**, **Acompañamiento o riff** (para este último se
    elige el instrumento: polifónico = acompañamiento, monofónico =
    riff/melodía). Se abre el diálogo del generador y la pista solo se crea
    si confirmas, ya rellena (un box en la vista Estructura, texto en la
    vista Texto). El bajo y el acompañamiento siguen los acordes de otra
    pista: mientras la canción no tenga ninguna, siguen desactivados, con el
    motivo escrito al lado;
  - **Pista desde un archivo MIDI...**: un canal de un archivo MIDI se
    convierte en una nueva pista, con el instrumento reconocido en el
    archivo.
- **Acciones sobre una pista** (generar, tocar con el teclado, importar MIDI
  o audio, nombre e instrumento, exportar MIDI, eliminar): menú **⋯** de la
  cabecera de la pista (en las dos vistas), o clic derecho en la cabecera;
  también siguen en el menú **Pista**.
- **Cambiar nombre / instrumento**: **⋯ → Nombre e instrumento...**, o
  doble clic en la cabecera de la pista.
- **Instrumentos personalizados**: menú **Sonidos → Gestionar
  instrumentos**. El instrumento se elige **por su nombre** en una lista
  General MIDI completa, agrupada por familia (Pianos, Guitarras, Bajos,
  Metales, Lengüetas...) y en la que se puede buscar escribiendo (p. ej.
  «sax», «organ»): no hace falta conocer el número de programa. Al elegir
  un sonido se rellenan automáticamente la octava, el rango y el estilo de
  voicing más adecuados (p. ej. los bajos pasan a `root_fifth`, los metales a
  `monophonic`), que siempre se pueden cambiar a mano. Para un instrumento
  de percusión, marca «Usar el canal de percusión (10)» en lugar de elegir
  un sonido. Parámetros disponibles: nombre (una sola palabra), octava
  predeterminada, rango (nota MIDI más grave y más aguda que se puede tocar)
  y estilo de voicing para los acordes:
  - `spread`: reparte todas las notas del acorde (adecuado para
    piano/guitarra)
  - `root_fifth`: solo la fundamental (+ la quinta si la hay), adecuado para
    el bajo
  - `monophonic`: solo la fundamental, para instrumentos melódicos
    monofónicos
  - `root_only`: solo la fundamental
- **SoundFont por instrumento**: desde **Sonidos → Gestionar
  instrumentos...** también puedes asignar a un solo instrumento
  (predefinido o personalizado) un archivo `.sf2` distinto del
  predeterminado — ver la sección 12.4 más abajo.

### 7.1 Carga automática de los instrumentos personalizados

Cuando guardas un proyecto que usa uno o más instrumentos personalizados,
su definición (programa GM, octava, rango, voicing...) se **incluye
directamente en el archivo `.st`**, en un bloque `Strumento Nombre:`
escrito antes de los patterns y de las pistas. Así, si abres ese proyecto
en otra instalación (o después de limpiar tu configuración local) y el
instrumento aún no está disponible, se **registra automáticamente** al
momento, y la pista que lo usa no se pierde. El programa muestra un aviso
con la lista de los instrumentos cargados de esta forma.

Si en el sistema ya existe un instrumento con el mismo nombre, la
definición incluida en el archivo **no lo sobrescribe** en la lista de
instrumentos (tus cambios hechos a mano se mantienen), pero **las pistas de
esa canción usan la definición del archivo**: una canción suena siempre
como está escrita, aunque antes hayas abierto otra canción que define de
otro modo un instrumento con el mismo nombre (por ejemplo «Archi» o
«Viole»).

Esto vale también para las pistas renombradas con **Editar
nombre/instrumento**: si el nombre de la pista ya no coincide con el
instrumento (p. ej. una pista «Guitar 1» renombrada como «SoloRinominato» y
pasada a otro instrumento), el archivo usa automáticamente una cabecera
explícita (`Traccia SoloRinominato [Bass]:`) en lugar de la forma abreviada,
para que no se pierda nada al guardar.

## 8. Mezclador

Cada pista tiene **Mute (M)**, **Solo (S)**, **Volumen** y **Pan**. Si al
menos una pista está en Solo, en la reproducción/exportación solo suenan
las pistas en Solo (que no estén también en Mute).

Los controles están en la **cabecera** de cada pista, igual en las dos
vistas: en la vista Estructura de la canción a la izquierda de cada fila,
en la vista Texto en la columna **Pistas** de la izquierda (allí también
sirve para elegir la pista cuyo texto se edita). La cabecera contiene:

- nombre e instrumento, **M**, **S**, **●** (solo pistas de audio:
  grabar), **FX** (abre el panel Efectos, ver 8.3 y 8.4) y el menú **⋯** con
  todas las acciones de la pista (generar, tocar con el teclado, importar
  MIDI o audio, nombre e instrumento, exportar MIDI, eliminar);
- a la derecha, dos mandos: **Vol** (volumen, el valor en %) y **Pan**
  (C = centro, L/R = izquierda/derecha). Se giran arrastrando arriba/abajo
  (más fino con Mayús), con la rueda o con las flechas; doble clic = volver
  a 100% / al centro.

Clic en la cabecera = seleccionar la pista; doble clic = cambiar
nombre/instrumento; clic derecho = el mismo menú que ⋯. Debajo de la última
cabecera, **+ Añadir pista** (ver sección 7).

### 8.1 Volumen: 0-200%, escala directamente la velocidad de las notas

El mando Volumen va de 0% a 200%, donde **100% es la intensidad
original** de las notas tal como están escritas en la pista (sin cambios).
Girar el mando escala directamente la velocidad de cada nota de la pista en
la exportación/reproducción — no solo el Channel Volume MIDI (CC7), cuya
curva de respuesta en muchos sintetizadores es débil o poco perceptible.
Esto hace que el control sea eficaz con cualquier motor de reproducción:

- por debajo de 100%: la pista suena más baja que el original;
- por encima de 100% (hasta 200%): la pista se refuerza por encima del
  original, útil para destacar un instrumento demasiado débil en la mezcla;
- la velocidad resultante siempre se mantiene dentro de los límites MIDI
  válidos (1-127).

Los ajustes de Volumen, Pan, Mute y Solo de cada pista se guardan en el
archivo `.st` (bloque `Mixer <Nombre de pista>:`) y se restablecen
automáticamente al volver a abrir el proyecto.

### 8.2 Volumen máster

Además del Volumen de cada pista (8.1), la barra de herramientas principal
tiene un control deslizante **Máster** (0-200%, misma escala y misma
convención: 100% = ganancia original) que escala a la vez el volumen de
**todas** las pistas, además del volumen ya ajustado en cada una — útil
para un ajuste general del nivel sin tener que tocar cada pista por
separado. Como con Mute/Solo/Volumen/Pan de pista, un cambio del Máster
durante la reproducción vuelve a iniciar automáticamente la reproducción
desde la posición actual con el nuevo valor (con un breve retardo si se
arrastra con el ratón, para no encadenar un reinicio por cada paso). El
valor máster se guarda en el archivo `.st` (línea `Master: N`, escrita solo
si es distinta del 100% predeterminado) y se restablece al volver a abrir el
proyecto.

### 8.3 Reverberación y chorus (FX)

El botón **FX** de cada pista, en su cabecera (en las dos vistas), abre en
la parte de abajo de la ventana el **panel Efectos** (ver 8.4). Para las
pistas de texto la primera tarjeta, **Envío rápido**, contiene los efectos
del sintetizador:
- **Reverberación** (0-100%): cuánto de la pista va a la reverberación, de
  seca (0%) a muy «mojada»;
- **Chorus** (0-100%): ensancha y «dobla» el sonido (cuerdas, pads,
  guitarras limpias, coros);
- **Ambiente**, uno para **toda la canción**: el espacio al que todas las
  pistas envían su reverberación. Habitación pequeña (predeterminado),
  Sala, Sala grande o Iglesia.

El botón FX se enciende (celeste) cuando la pista tiene reverberación,
chorus o efectos de la cadena, y su descripción emergente muestra los
valores.

Son los efectos que ya tiene el sintetizador (fluidsynth): se oyen enseguida
con la escucha normal, sin procesos adicionales, y durante la reproducción
la escucha vuelve a empezar sola como con el volumen y el pan.
- **Guardado:** la reverberación y el chorus van al bloque `Mixer` de la
  pista (`riverbero: 35 chorus: 10`), el ambiente a la línea
  `Ambiente: sala` al principio del archivo. Ambos se escriben solo si son
  distintos del valor predeterminado, así que los proyectos que no los usan
  quedan idénticos.
- **Exportación:** la reverberación y el chorus valen para la escucha y
  para las exportaciones WAV y MIDI (controladores CC91 y CC93). El
  ambiente solo vale para la escucha y el WAV: el archivo MIDI no lo puede
  contener, y el reproductor que lo abre usa el suyo.
- **Importación MIDI:** un archivo con reverberación y chorus ajustados en
  los canales (CC91/CC93 al principio de la canción) los lleva a las pistas
  importadas.

Conviene saber:
- **Habitación pequeña:** es el ambiente de siempre de fluidsynth (así los
  proyectos existentes suenan como antes), pero en ella la reverberación
  apenas se oye. Para un efecto claro elige **Sala** o **Sala grande**: la
  tarjeta te lo recuerda cuando subes la reverberación con la habitación
  pequeña.
- **Cambio de ambiente:** incluso con la reverberación a 0, cambiar de
  ambiente puede modificar un poco el sonido, porque algunos SoundFonts ya
  envían por su cuenta una parte de sus instrumentos a la reverberación.
- **Pistas de audio:** no tienen Envío rápido, porque estos efectos son del
  sintetizador, que solo toca las pistas de texto; en cambio sí tienen la
  cadena de efectos (8.4).
- **Tocar con el teclado:** la escucha en directo todavía no aplica la
  reverberación ni el chorus de la pista.

### 8.4 Cadena de efectos y panel Efectos

Cada pista, de texto o de audio, puede tener una **cadena de efectos**: el
sonido de la pista pasa de un efecto al siguiente, de izquierda a derecha.
Los efectos disponibles, divididos por familia en el menú **+ Efecto**:

- **Dinámica:**
  - **Compresor** (umbral, relación, ataque, liberación, ganancia): hace el
    nivel más uniforme (voz, bajo, batería);
  - **Limitador** (ganancia, techo, liberación): sube el volumen de la
    pista en «Ganancia» sin que los picos superen nunca el «Techo» (p. ej.
    −1 dB). Preajustes Seguridad (solo protección de picos), Más fuerte,
    Mucho más fuerte;
  - **Puerta de ruido** (umbral, relación, ataque, liberación): silencia la
    pista cuando baja del umbral, para quitar soplido, zumbido y ruidos
    entre una frase y otra en las pistas de audio grabadas. Si corta el
    principio o el final de las notas, baja el umbral o alarga la
    liberación.
- **Tono:**
  - **EQ de 3 bandas** (bajos, medios, agudos, ±12 dB cada uno);
  - **Filtro de paso alto** (frecuencia 20 Hz–2 kHz, pendiente 6–24
    dB/octava): quita los graves por debajo de la frecuencia. El uso clásico
    es «Limpieza de graves» (80 Hz) en la voz y las guitarras, para dejar
    espacio al bajo y al bombo;
  - **Filtro de paso bajo** (frecuencia 200 Hz–20 kHz, pendiente 6–24
    dB/octava): quita los agudos por encima de la frecuencia, para un sonido
    más oscuro, apagado o «detrás de una puerta». Cuanto más alta la
    pendiente, más neto el corte.
- **Saturación:**
  - **Amplificador** (modelo, caja, ganancia, bajos, medios, agudos,
    presencia, potencia, nivel): un amplificador de guitarra completo, en el
    orden preamplificador → controles de tono → etapa de potencia → caja.
    Los **modelos**: *Limpio* (casi sin saturación), *Crunch* (blues, rock
    ligero), *British* (rock clásico, medios destacados, dos etapas de
    saturación), *High gain* (metal, graves apretados y mucha saturación).

    **Bajos, Medios, Agudos** (de 0 a 10, como en los amplificadores reales)
    son el circuito de tono («tone stack») de los amplificadores reales,
    calculado a partir de los valores de sus componentes: el de **Fender**
    para Limpio y Crunch, el de **Marshall** para British y High gain. Como
    en los originales, los mandos se influyen entre sí (subir los Agudos
    toca también los medios), a mitad de recorrido los medios ya están algo
    «vaciados» (más en el Fender), los Medios a 0 dan el vaciado profundo
    del metal y el volumen cambia un poco al girarlos, como en un
    amplificador de verdad.

    **Saturación que depende de la frecuencia.** Como en las etapas de
    válvulas reales, los graves saturan menos que los medios y los agudos:
    las notas graves y los acordes en las cuerdas graves (power chords)
    siguen definidos en lugar de «empastarse», mientras que las notas
    medias distorsionan como se espera. Cuanto más apretado es el modelo
    (British, High gain), más marcado es el efecto. No le quita graves al
    sonido: cambia cómo distorsionan, no cuántos hay.

    **Respuesta al toque.** El punto de trabajo de las válvulas también se
    desplaza como en los amplificadores reales: en los golpes fuertes la
    etapa pierde un momento algo de ganancia y distorsiona de forma
    asimétrica (armónicos pares, más «cálidos»), luego en una décima de
    segundo más o menos «respira» y vuelve a como estaba. Tocando suave el
    sonido sigue limpio; atacando fuerte se ensucia de forma dinámica: es el
    efecto más evidente con Crunch y British (el sonido «que responde a la
    púa»), más contenido con High gain y casi ausente con Limpio. Después de
    cada etapa está también el filtro de los condensadores de acoplamiento,
    que quita el «retumbe» subgrave que la distorsión asimétrica crearía
    bajo los acordes graves.

    **Presencia** (0-10) ajusta los agudos después de la etapa de potencia,
    como el mando del mismo nombre de los amplificadores de válvulas: más
    «aire» y mordiente sin hacer áspero el preamplificador.

    **Potencia** (0-100%) es cuánto se aprieta la etapa final: las válvulas
    de potencia saturan de forma suave y asimétrica (con armónicos pares, el
    sonido «cálido» de válvulas) y la alimentación que cede en los golpes
    fuertes («sag») comprime un poco los acordes mantenidos. 0% = etapa
    final limpia; 30-50% es el sonido de un amplificador tocado a volumen;
    más allá, el sonido se redondea y se comprime.

    Las **cajas**: *Combo 1×12*, *2×12*, *4×12 cerrada* (más cuerpo en los
    graves), *Vintage 1×10* (más fina y nasal), o *Ninguna* para el sonido
    directo del amplificador. Las cajas las simula SoundText (ningún archivo
    que descargar) y, como las reales, cortan los agudos por encima de 5-6
    kHz: por eso un amplificador suena «cálido» incluso con mucha ganancia.
    Preajustes: Limpio brillante, Blues, Vintage, Rock clásico, Metal.
    «Nivel» compensa el volumen: más ganancia significa más volumen, así que
    bájalo al subir la ganancia. Funciona en pistas de guitarra (de texto o
    grabadas) y también en el bajo o en un órgano para un sonido más sucio.

    **Caja desde un archivo IR.** Con la caja **Archivo IR…** se usa la
    respuesta al impulso (IR) de una caja real, grabada con un micrófono: un
    pequeño archivo WAV (se encuentran muchísimos gratis, de cajas famosas y
    con micrófonos distintos). Al elegir «Archivo IR…» se abre la ventana
    para indicar el archivo; el botón **Elegir IR…** debajo de los menús lo
    cambia, y al lado aparece el nombre del archivo. El archivo se lee en
    mono (media de los canales), se lleva a 48 kHz si tiene otra
    frecuencia, como máximo 1 segundo, y se normaliza como las cajas
    internas, así cambiar de caja no hace saltar el volumen. En el archivo
    `.st` se guarda la ruta (relativa a la carpeta del proyecto, como para
    los clips de audio: `ir="ir/cassa.wav"`): mantén la IR cerca del
    proyecto si lo pasas a otro ordenador. Si el archivo ya no se encuentra,
    la tarjeta lo indica en rojo y se usa la caja Combo 1×12 hasta que
    elijas otro.

    **Calidad de la saturación.** Amplificador y Distorsión saturan el
    sonido a 4 veces la frecuencia de muestreo (192 kHz; la etapa de
    potencia, más suave, a 2 veces) y luego vuelven a 48 kHz con filtros de
    fase lineal («sobremuestreo»): así los armónicos generados por la
    distorsión no se repliegan en frecuencias espurias, el clásico
    «chisporroteo» digital en las notas agudas con mucha ganancia. No añade
    retardo; el procesamiento es algo más lento (unas décimas de segundo
    para el bucle de calibración, unos segundos en segundo plano para una
    pista entera);
  - **Perfil NAM** (entrada, caja, nivel): usa un amplificador o un pedal
    **reales**, «capturados» con **Neural Amp Modeler** (NAM). Un perfil es
    un archivo `.nam`: una red neuronal entrenada escuchando el aparato
    original, que reproduce su sonido con gran fidelidad. Se encuentran
    miles, casi todos gratis, en **Tone3000** (tone3000.com):
    amplificadores famosos, pedales de overdrive y distorsión,
    preamplificadores, a veces con la caja incluida. Para empezar,
    **Sonidos → Descargar → Descargar perfiles NAM recomendados...** descarga una
    docena de golpe (ver «Dónde encontrar perfiles NAM», más abajo).

    Al añadir el efecto (**+ Efecto → Saturación → Perfil NAM**) se abre la
    ventana para elegir el archivo; si cancelas, el efecto no se añade. En
    la tarjeta aparecen el nombre del perfil y, si el archivo los declara,
    marca, modelo, tipo (amplificador, pedal, amplificador con caja…) y
    autor; el botón **Elegir perfil…** lo cambia.
    - **Entrada** es el mando «input» del plugin NAM: con cuánta fuerza
      llega la guitarra. Más alto = más saturación (como tocar más fuerte o
      subir la ganancia del aparato original, hasta donde la captura lo
      permita), más bajo = más limpio.
    - **Caja**: *Ninguna / incluida* si el perfil ya contiene la caja (tipo
      «amplificador con caja») o si es un pedal para poner delante de un
      Amplificador; **Archivo IR…** para añadir la respuesta de una caja
      real, como en el Amplificador (ver arriba). Un perfil solo de cabezal
      sin caja suena áspero y «zumbón»: dale una IR.
    - **Nivel** compensa el volumen. Como el plugin, SoundText ya lleva cada
      perfil a la misma sonoridad de referencia (−18 dB) usando el valor
      escrito en el archivo; los perfiles más antiguos, que no lo escriben,
      se miden de la misma forma que lo hace NAM (con su señal de
      referencia), una sola vez. Así cambiar de perfil no hace saltar el
      volumen.

    Preajustes: Neutro, Más apretado (+6 dB de entrada), Más limpio (−6 dB).

    Conviene saber sobre los perfiles NAM:
    - **Formatos:** se usan los perfiles WaveNet de las dos generaciones,
      **A1** (los clásicos *standard*, *lite*, *feather* y *nano*, la gran
      mayoría de los archivos publicados) y **A2** (la más reciente), y
      también los perfiles **LSTM**, las redes recurrentes de los primeros
      tiempos de NAM. Muchos archivos A2 contienen **varios tamaños** del
      mismo modelo, del más ligero al más completo, para que el plugin pueda
      ahorrar CPU en directo: SoundText no toca en tiempo real y usa siempre
      el tamaño **completo**, el mejor. En la tarjeta, junto a la
      descripción, aparece «formato A2» o «formato LSTM». El cálculo sigue
      al del motor oficial de NAM, verificado comparando las salidas; con los
      LSTM las diferencias quedan por debajo de −80 dB (redondeos del
      cálculo, que una red recurrente arrastra en el tiempo), así que no se
      oyen. Un archivo de otro tipo (por ejemplo las rarísimas arquitecturas
      experimentales ConvNet o Linear) no se usa y el panel explica el
      motivo.
    - **Mono:** el perfil trabaja en mono, como el plugin (los dos canales
      se suman); los efectos «espaciales» van después.
    - **Velocidad:** una red neuronal es más pesada que el Amplificador
      interno: alrededor de un segundo por cada retoque en el bucle de
      calibración y unos veinte segundos, en segundo plano, para una pista
      de 3 minutos (perfiles A1 *standard* y A2; *lite*, *feather* y *nano*
      son más rápidos, los LSTM todavía más: unos segundos para 3 minutos).
      El resultado se queda en memoria como en los demás efectos.
    - **Frecuencia:** los perfiles suelen estar a 48 kHz, como SoundText; si
      un perfil tiene otra frecuencia, el sonido se convierte antes y
      después.
    - **Guardado:** en el archivo `.st` se guarda la ruta, relativa a la
      carpeta del proyecto: `nam: ingresso=3 cassa=file livello=-2
      nam="profili/Plexi.nam" ir="ir/4x12.wav"`. Mantén los perfiles cerca
      del proyecto si lo mueves; si el archivo ya no se encuentra, la
      tarjeta lo indica en rojo y el sonido pasa sin cambios.

    **Dónde encontrar perfiles NAM.**
    - **Perfiles recomendados, de golpe:** **Sonidos → Descargar → Descargar
      perfiles NAM recomendados...** (o, desde un terminal en la carpeta de
      SoundText, `python3 scarica_profili_nam.py`) descarga 11 perfiles de
      amplificadores y pedales famosos, unos 3 MB en total, en la carpeta
      **`profili_nam`** junto a SoundText (o en `~/SoundText/profili_nam` si
      allí no se puede escribir). La carpeta no forma parte del repositorio:
      cada uno la descarga en su propio ordenador. El comando solo vuelve a
      descargar los archivos que faltan y escribe en la carpeta un
      `LEGGIMI.txt` con la procedencia y los autores. La ventana «Elegir
      perfil…» ya se abre allí. Los perfiles proceden de la colección de la
      comunidad de NAM en GitHub (github.com/pelennor2170/NAM_models,
      licencia GNU GPL v3):
      - amplificadores (sin caja: añade una caja con **Caja → Archivo
        IR…**): *Fender Twin Reverb - limpio* (funk, pop, arpegios), *Vox
        AC15 - Top Boost* (el «chime» británico), *Marshall JCM2000 -
        crunch* (rock clásico), *Marshall JCM900 - lead* (hard rock y
        solos), *Mesa Boogie Mark IV - lead* y *Peavey 5150 - high gain*
        (metal);
      - amplificador **con caja** (listo, sin IR): *Bugera 333 - crunch con
        caja*;
      - pedales, para poner **antes** de un amplificador (interno o perfil):
        *Ibanez TS9 Tube Screamer*, *Klon Centaur (clon)*, *Boss HM-2 -
        sueco* (death metal), y para el bajo *Tech 21 dUg DP3X*.
    - **Cajas para los amplificadores sin caja:** **Sonidos → Descargar → Descargar cajas IR para los amplificadores NAM...** descarga 20 cajas
      de guitarra (respuestas al impulso, menos de 1 MB) en la subcarpeta
      **`profili_nam/casse`**, con el texto de la licencia y un
      `LEGGIMI.txt`; la ventana «Elegir IR…» ya se abre ahí. Son el
      *BestPlugins Mega Pack 2* de David Fau Casquel (GNU GPL v2 o
      posterior), tomado del repositorio de Guitarix
      (github.com/brummer10/guitarix). Cada archivo lleva el nombre del
      amplificador cuya caja reproduce (*Mesa Boogie Mark V*, *EVH 5150
      III*, *Marshall JMP 2203*, *Engl Retro Tube*...). El paquete está
      pensado sobre todo para sonidos distorsionados: con los perfiles
      limpios (Fender Twin, Vox AC15) prueba varias cajas, o busca una
      adecuada en Tone3000.
    - **Tone3000** (tone3000.com), el sitio de referencia, con decenas de
      miles de perfiles gratis (para descargar puede pedir que crees una
      cuenta gratuita):
      1. busca el aparato (por ejemplo «Plexi», «Dumble», «Rectifier»,
         «Tube Screamer»);
      2. en los filtros elige la plataforma **NAM** y el tipo: *amp* (solo
         amplificador: hace falta una IR), *full rig* (amplificador con
         caja, listo) o *pedal*; ordenando por descargas encuentras los más
         usados;
      3. en la página del perfil descarga el archivo (a menudo un ZIP con
         varias variantes: *standard* es la calidad completa, *lite*,
         *feather* y *nano* más ligeras; SoundText las lee todas, también A2
         y LSTM);
      4. extrae los archivos `.nam` en la carpeta `profili_nam` (o en una
         carpeta junto al proyecto) y elígelos desde la tarjeta con
         **Elegir perfil…**.
      En Tone3000 también están las **IR** de las cajas (tipo *IR*), para
      usar con **Caja → Archivo IR…**.
    - **Toda la colección en GitHub** (unos 260 perfiles, 108 MB): en la
      página github.com/pelennor2170/NAM_models, **Code → Download ZIP**, y
      luego extrae los `.nam` que te interesen en `profili_nam`.

    Si un perfil descargado no suena como esperas: un amplificador sin caja
    suena áspero hasta que le das una IR; un pedal solo suena «pequeño», hay
    que ponerlo delante de un amplificador; con **Entrada** encuentras el
    punto en el que el perfil reacciona mejor a tu señal.
  - **Distorsión** (drive, tono, nivel, mezcla): desde un color cálido
    apenas insinuado hasta el fuzz. «Drive» es cuánto se satura, «Tono»
    aclara u oscurece el resultado, «Nivel» compensa el volumen (la
    distorsión sube mucho el nivel), «Mezcla» por debajo del 100% mezcla el
    sonido limpio con el distorsionado (preajuste «Paralela»). Adecuada para
    guitarras, bajo y sintetizadores; para un sonido de amplificador
    completo usa en su lugar el Amplificador.
- **Espacio — Delay** (a tempo, tempo, repeticiones, mezcla),
  **Reverberación** (habitación, amortiguación, amplitud, mezcla),
  **Chorus** (velocidad, profundidad, mezcla) y **Phaser** (velocidad,
  profundidad, realimentación, mezcla).

  El **Delay a tempo**: en el menú «A tempo» elige una subdivisión (1/2,
  1/4, 1/4 con puntillo, 1/4 tresillo, 1/8, 1/8 con puntillo, 1/8
  tresillo, 1/16) y las repeticiones caen a tempo con la canción,
  calculadas a partir de su BPM; el mando Tempo se desactiva y muestra los
  milisegundos resultantes. Al cambiar el BPM de la canción, el delay se
  adapta solo. Con «Libre (ms)» el tiempo se ajusta a mano. El cálculo usa
  el tempo **inicial** de la canción: con cambios de tempo a mitad de la
  canción, las repeticiones siguen siendo las del tempo inicial. El 1/8 con
  puntillo (preajuste «A tempo 1/8 con puntillo») es el clásico eco «al
  galope» de las guitarras de rock.

El **panel Efectos** se abre desde el botón FX de la pista (para el máster,
desde el botón FX junto al control Máster: ver 8.5) y se queda en la parte
de abajo de la ventana (se puede redimensionar arrastrando su borde). Cada
efecto es una **tarjeta** con:
- **⏻** para encenderlo o apagarlo sin perder los ajustes;
- **◀ ▶** para moverlo antes o después en la cadena, **✕** para quitarlo;
- los **preajustes** (p. ej. Compresor «Voz», Delay «Slapback»,
  Reverberación «Catedral»): una vez elegido un preajuste puedes retocarlo
  con los mandos, y entonces el menú muestra **Personalizado**;
- los **mandos**, con el valor debajo; doble clic en el valor para volver
  al predeterminado.

En la cabecera del panel:
- **Bucle** (10 s, de 2 a 30): al abrir el panel se elige un fragmento que
  volver a escuchar mientras ajustas, que también se convierte en el bucle
  A-B de la canción (en la regla). Empieza en el box seleccionado de la
  pista; si no, en la posición del cabezal (o en el primer box de la
  pista);
- **▶ Escuchar el bucle**: repite el fragmento; cada retoque se oye **en la
  siguiente vuelta**, sin rehacer el resto de la canción;
- **Con las demás pistas**: en el bucle suena toda la canción, como en la
  mezcla final; sin marcar, solo se oye la pista;
- **Antes / Después**: pulsado, el bucle se oye sin la cadena, para
  comparar (no cambia la pista);
- **Copiar a…**: copia la cadena a otra pista;
- **Deshacer cambios**: devuelve efectos, reverberación, chorus y ambiente
  a como estaban cuando abriste el panel (cada cambio sigue también en
  Editar → Deshacer);
- **✕** cierra el panel: el bucle A-B vuelve a ser el de antes y la cadena
  se aplica a **toda la pista en segundo plano**, así el próximo Play ya
  está listo (la barra de estado avisa cuando ha terminado).

El botón FX muestra cuántos efectos están encendidos (p. ej. **FX 3**).

Conviene saber:
- **Cómo suena:** una pista con efectos encendidos se sintetiza aparte y
  luego se procesa; el resultado se queda en memoria, así que girar un
  mando solo rehace el procesamiento (fracciones de segundo), y cambiar
  otra pista no la toca. El delay y la reverberación pueden alargar la
  canción con su cola.
- **Exportación:** la cadena vale para la escucha y la exportación WAV; el
  archivo MIDI no la contiene (el reproductor MIDI no tiene estos
  efectos).
- **Guardado:** la cadena se guarda en el archivo `.st`, en un bloque por
  pista:
  ```
  Effetti Chitarra:
    compressore: soglia=-20 rapporto=4 attacco=5 rilascio=120 guadagno=4 preset="Voce"
    delay: tempo=250 ripetizioni=25 mix=20 spento
  ```
  (`spento` = efecto presente pero apagado). Los valores fuera de los
  límites se devuelven dentro de ellos, los efectos desconocidos se
  ignoran.
- **Requisitos:** la cadena usa el paquete de Python `pedalboard` (`pip
  install pedalboard`, ya en los requisitos); sin él, el panel solo muestra
  el Envío rápido y un aviso. Escuchar el bucle requiere el streaming de
  audio (`sounddevice`), como el bucle A-B.
- **Una escucha cada vez:** iniciar el bucle detiene la canción y la
  escucha de los boxes; pulsar Play detiene el bucle.

### 8.5 Efectos en el máster (mastering)

Además de las pistas, también la **mezcla final** de la canción puede
pasar por una cadena de efectos: es el «mastering», el último retoque que
hace la canción más compacta, equilibrada y fuerte. El botón **FX** junto
al control **Máster**, en la barra de comandos, abre el panel Efectos del
máster (etiqueta «Máster · mezcla final»). Se usan los mismos efectos y las
mismas tarjetas que en las pistas; los más adecuados para el máster son:
- **EQ de 3 bandas:** pequeños retoques del tono general (±1-3 dB);
- **Compresor**, preajuste **Pegamento de mezcla**: compresión ligera
  (relación 2:1, ataque lento) que une las pistas;
- **Limitador**, preajuste **Más fuerte**: sube el volumen de la canción
  sin que los picos superen el techo de −1 dB. Suele ser el último de la
  cadena.

El botón **+ Cadena de mastering** añade de golpe estos tres efectos, como
punto de partida para ajustar de oído. El botón FX del máster se enciende
y muestra cuántos efectos están activos (p. ej. **FX 3**).

Como en las pistas:
- el **bucle de calibración** (10 s, desde el cabezal) hace oír la mezcla
  de toda la canción con cada retoque; **Antes / Después** compara la
  mezcla con y sin la cadena del máster;
- **Deshacer cambios** devuelve la cadena a como estaba al abrir el panel,
  y cada cambio está también en Editar → Deshacer;
- **Copiar a…** copia la cadena del máster a una pista; desde una pista se
  puede copiar su cadena al máster («Máster (mezcla final)»).

Conviene saber:
- **Dónde se aplica:** el máster se aplica a la escucha de la canción, a la
  exportación WAV de la canción y a la base que se oye mientras se graba.
  No se aplica a la exportación de una sola pista ni a la exportación MIDI.
- **También el bucle de las pistas pasa por el máster:** al calibrar una
  pista ya la oyes con la cadena del máster, es decir, como en la canción
  terminada.
- **Rápido:** la mezcla antes del máster se queda en memoria, así que tras
  un retoque solo del máster el siguiente Play vuelve a procesar la mezcla
  ya lista, sin volver a sintetizar la canción.
- **Volumen máster y cadena:** el control Máster (8.2) actúa antes de la
  cadena, sobre el volumen de las pistas: con un limitador en el máster,
  subirlo hace la canción más «aplastada» pero no más fuerte por encima del
  techo.
- **Guardado:** en el archivo `.st` la cadena del máster está en el bloque
  ```
  Catena master:
    compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=1 preset="Colla del mix"
    limiter: guadagno=6 tetto=-1 rilascio=80 preset="Più forte"
  ```
  (una palabra distinta de `Effetti`, para que no se confunda con una pista
  llamada «Master»). Sin cadena el bloque no se escribe.

### 8.6 Sonidos de estudio con programas externos (re-amping)

El amplificador de SoundText (8.4) está bien para bocetos, bases y demos.
Para un sonido de guitarra de estudio la vía más sencilla es el **Perfil
NAM** (8.4), que usa dentro de SoundText capturas de amplificadores reales.
Si no, se puede pasar la pista por un simulador de amplificador externo y
luego devolverla a la canción: es el **re-amping**, útil para usar
programas como Guitarix o los plugins comerciales.

**El proceso, en cualquier sistema:**
1. Graba la guitarra **limpia** (entrada INST/Hi-Z de la interfaz de audio,
   sin amplificador) en una pista de audio, o escríbela en notas.
2. Clic derecho en el nombre de la pista → **Exportar WAV seco (para
   re-amping)...**
3. En el programa externo aplica al archivo el simulador elegido y guarda
   el resultado en un nuevo WAV.
4. En SoundText crea una **pista de audio** (p. ej. «Guitarra ampli») e
   **Importar archivo de audio...**: en una pista vacía el clip va al
   principio, así que a tempo con la canción. Pon en **Mute** la pista
   original (o quédate con las dos, para mezclar limpio y amplificado).

Si el simulador añade un retardo (ocurre en tiempo real, no en el
procesamiento sin conexión), mueve un poco el clip o acorta su principio
arrastrando el borde.

**Linux — Guitarix** (gratuito, simulación de los circuitos de válvulas de
amplificadores y pedales, cajas e IR): se instala desde los repositorios de
la distribución (`sudo apt install guitarix`, `sudo dnf install guitarix`,
`sudo pacman -S guitarix`; en algunas, como Debian y Ubuntu, los plugins
LV2 están en un paquete aparte, `guitarix-lv2`). Los plugins LV2 de
Guitarix se pueden usar **directamente en SoundText** como efectos (8.7),
sin re-amping. Para usar Guitarix fuera de SoundText hay dos formas:
- **sin conexión (recomendado):** abre el WAV seco en **Audacity** o en
  **Ardour** y aplica los plugins LV2 de Guitarix como efecto, luego
  exporta; ninguna conexión de audio que configurar;
- **en directo:** inicia Guitarix (con PipeWire, si hace falta, `pw-jack
  guitarix`), conecta con **qpwgraph** o **Helvum** la guitarra a la
  entrada de Guitarix y su salida al grabador; para grabar directamente en
  SoundText elige como interfaz de audio la entrada de PipeWire.

**Windows y macOS** (Guitarix solo funciona en Linux):
- **Neural Amp Modeler (NAM)**: gratuito, plugin VST3/AU y programa
  independiente, con modelos «capturados» de amplificadores reales
  (archivos `.nam`, miles gratis en Tone3000) y carga de IR para la caja.
  Los perfiles NAM también se pueden usar directamente en SoundText (Perfil
  NAM, 8.4), en todos los sistemas, sin re-amping (A1, A2 y LSTM); el
  plugin sirve para tocar en directo;
- **AIDA-X**: gratuito, parecido a NAM y más ligero, también en Linux;
- **GarageBand** (macOS): gratuito, con amplificadores y pedales ya
  incluidos;
- para aplicar un plugin al WAV seco vale **Audacity** (gratuito, VST3 en
  todos los sistemas, AU en macOS), o un programa de grabación como
  **Reaper**.

En directo, NAM y AIDA-X también funcionan como programas independientes:
la guitarra entra en el simulador y SoundText graba la salida (con una
conexión de audio virtual, o grabando en otro programa e importando el
archivo).

### 8.7 Plugins externos (VST3 y LV2)

SoundText puede usar los **plugins de audio instalados en el ordenador**,
tanto como **efectos** en la cadena de una pista o del máster, como
**instrumentos virtuales** que tocan las notas de una pista en lugar del
SoundFont.

- **VST3**: en Linux, Windows y macOS. SoundText los busca en las carpetas
  estándar del sistema (en Linux `~/.vst3` y `/usr/lib/vst3`, en Windows
  `C:\Program Files\Common Files\VST3`, en macOS
  `/Library/Audio/Plug-Ins/VST3`); otras carpetas se añaden desde
  **Sonidos → Carpetas de plugins VST3...**
- **LV2**: solo en Linux, y hace falta la biblioteca del sistema `lilv` (en
  Debian/Ubuntu el paquete `liblilv-0-0`, ya presente si están instalados
  Ardour, Carla o Guitarix). Los plugins LV2 se encuentran solos. Por
  ejemplo, con `guitarix-lv2` se tienen decenas de amplificadores y
  pedales.
- Los formatos **CLAP** y **VST2** no son compatibles.

**Un plugin como efecto**: en el panel Efectos (8.4) **+ Efecto → Plugin
(VST3/LV2)** abre la lista de los plugins de efecto instalados, con
búsqueda por nombre. La tarjeta del plugin tiene:
- los mandos **Mezcla** (cuánto sonido procesado mezclar con el original) y
  **Nivel** (el volumen de salida), como los demás efectos;
- **Parámetros...**, que abre una ventana con todos los controles del
  plugin; los cambios se oyen enseguida en el bucle de escucha del panel;
- **Cambiar...** para sustituirlo por otro plugin.

En la ventana de los parámetros, **Interfaz del plugin...** abre la ventana
gráfica del propio plugin (solo VST3). Cuando la cierras, los ajustes
hechos allí se quedan en el proyecto.

**Un plugin como instrumento**: **Pista → Instrumento plugin → Elegir (VST3/LV2)...**, o clic derecho en el nombre de la pista. Elige un
instrumento virtual (sintetizador, piano muestreado...) y luego ajusta sus
parámetros. Las notas de la pista las toca el plugin: el **volumen** de la
pista actúa sobre la fuerza de las notas, el **pan** sobre la posición en
el estéreo, y los efectos de la pista se aplican después del plugin. Para
volver al SoundFont elige **Ninguno: usar el SoundFont**. Debajo del
nombre de la pista aparece el nombre del plugin.

Algunos plugins LV2 cargan un archivo: por ejemplo sfizz LV2 toca un
**archivo SFZ**. En la ventana de parámetros estas propiedades tienen una
fila con **Examinar...** y **Quitar**; el archivo elegido queda en el
proyecto.

**Instrumento SFZ interno.** Un archivo `.sfz` (instrumento muestreado,
como los que descarga `scarica_strumenti.py`) también se puede tocar sin
plugins: en la lista de instrumentos elige **Instrumento SFZ (interno)...**
y luego el archivo. Lo toca la biblioteca del motor **sfizioso** (o de
**sfizz**), que se instala una vez con `python3 scarica_strumenti.py
libreria` (en Linux también `./scarica_strumenti.sh libreria`; en Windows
`py scarica_strumenti.py libreria`, que requiere Visual Studio Build Tools
con C++); sin ella, la entrada aparece en gris. Este instrumento no tiene
parámetros: «Parámetros del instrumento plugin...» permite elegir otro
archivo. Debajo del nombre de la pista aparece el nombre del archivo con
«(SFZ)»; si modificas el archivo `.sfz`, la canción se recalcula.

El proyecto `.st` recuerda el plugin de cada pista y de cada efecto, con
sus parámetros. Al abrir el proyecto en otro ordenador, los VST3 se buscan
por nombre de archivo en las carpetas de plugins.

**Si un plugin no funciona.** Los plugins funcionan en un proceso aparte de
SoundText: si uno se bloquea o se cierra de forma inesperada, SoundText
sigue abierto. El plugin se marca como **«no responde»** hasta el próximo
arranque de la aplicación. Un efecto que no funciona deja pasar el sonido
sin cambios. Una pista cuyo instrumento plugin no funciona suena con el
SoundFont, y el motivo queda en el archivo de registro (Ayuda). Algunos
plugins no se pueden cargar de ninguna forma: en la lista aparecen en gris,
con el motivo al lado (por ejemplo «no responde», o un plugin que solo
acepta audio mono).

**Límites**:
- los instrumentos plugin suenan en la escucha de la canción, en el bucle
  del panel Efectos y en la exportación WAV; las vistas previas rápidas
  (nota del teclado, escucha de un pattern, acorde elegido con doble clic)
  siguen usando el SoundFont;
- la exportación MIDI y MusicXML contiene las notas, no el sonido del
  plugin;
- de los plugins LV2 se guardan los valores de los parámetros y los
  archivos elegidos, no el resto del «estado» interno;
- la primera búsqueda de plugins carga cada VST3 una vez, y puede tardar un
  poco; después la lista se recuerda hasta que cambia un plugin
  (**Actualizar lista** rehace la búsqueda).

## 8bis. Estructura de la canción (vista en boxes)

Una alternativa al editor de texto lineal para trabajar en la
**estructura** de la canción (intro/estrofa/estribillo/solo...) en lugar de
nota a nota: cada pista se convierte en una fila sobre un único eje de
tiempo compartido, y su contenido se divide en **boxes** — rectángulos que
se arrastran en horizontal, cada uno autosuficiente como el cuerpo de un
pattern (sección 4), con su propio nombre y su propia posición en el
tiempo. El contenido real de cada pista (`Track.text`, lo que de verdad
leen la reproducción, la exportación y la validación) siempre se recalcula
automáticamente a partir de la secuencia de sus boxes: trabajar con boxes
no es «otro formato», solo otra forma de escribir el mismo texto.

**Activación**: botones **Estructura** / **Texto** en la barra de
comandos, o menú **Vista → Estructura de la canción (boxes)** (atajo
`Ctrl+Shift+B`): alternan esta vista y el editor de texto lineal clásico.
Es la vista con la que SoundText se abre por defecto.

El color de cada box (y de la franja a la izquierda de la cabecera de la
pista) refleja la familia del instrumento (bajo, guitarra, vientos, etc.),
la misma convención que se usa en otras partes de la aplicación (p. ej.
sección 7). Las cabeceras también contienen el mezclador de la pista (ver
sección 8).

### Crear un box

Un doble clic en un punto vacío de una fila abre el editor de un nuevo box
en esa posición (la misma ventana de edición descrita más abajo). El clic
derecho en un punto vacío ofrece además:

- **Nuevo box desde el teclado aquí** / **Nuevo box desde audio aquí** /
  **Importar MIDI aquí**: los mismos procesos que «Tocar con el
  teclado»/«Importar audio»/«Importar MIDI» de la parte de pistas
  (secciones 10, 10bis, 10ter), pero el resultado se convierte en un nuevo
  box en lugar de sustituir toda la pista.
- **Generar batería en esta pista...** / **Generar bajo a partir de acordes
  en esta pista...** (sección 9bis): solo visibles si el instrumento de la
  pista es de percusión o un bajo, respectivamente; el box generado se añade
  justo después del último box existente.
- **Pegar aquí**: solo si antes se ha cortado o copiado un box (ver más
  abajo).
- **Importar desde .box...**: carga un box guardado anteriormente (ver más
  abajo «Exportar/importar un solo box»).

Las mismas acciones «Generar batería/bajo» también se alcanzan con el clic
derecho en la etiqueta de la pista a la izquierda.

### Mover, seleccionar, editar

- **Arrastrar** un box lo recoloca en el tiempo en la MISMA pista (para
  moverlo a otra pista se usa cortar/pegar, no el arrastre): la posición
  siempre se ajusta al tiempo entero más cercano, y una línea guía vertical
  cruza todas las pistas durante el arrastre para alinear a ojo boxes de
  pistas distintas. Si el punto elegido se superpone a otro box de la misma
  pista, se ajusta automáticamente al borde libre más cercano en lugar de
  superponerse.
- **Un clic** selecciona un box (borde resaltado con el color de acento)
  sin moverlo, aunque el box no estuviera ya en un tiempo entero (p. ej.
  después de un grupo irregular, sección 2.1bis): un pequeño movimiento
  involuntario del ratón entre pulsar y soltar no cuenta como arrastre.
- **Un doble clic** en un box abre el editor dedicado de su contenido (el
  mismo editor de texto con resaltado de sintaxis, autocompletado y
  Play/Stop de vista previa que se usa para los patterns, sección 4) con el
  nombre y el texto del box, validados antes de poder confirmar.

### Menú del clic derecho en un box

- **▶ Play** / **■ Stop**: reproduce (o detiene) la vista previa del
  contenido del box con el instrumento de su pista — un motor de vista
  previa dedicado, independiente del transporte principal F5/F6.
- **Transponer...**: transposición por semitonos de todo el contenido del
  box. Las llamadas a patrones y archivos MIDI se transponen con el
  sufijo: `%Giro` pasa a `%Giro+2`, `&"Riff"+1` pasa a `&"Riff"+3` (el patrón
  queda como está, porque otros pueden usarlo). Si el box usa un ancla de
  compás `bar=N`, **▶ Play** lo toca desde su lugar en la canción, para que
  el ancla lleve al compás correcto (lo mismo vale para **▶ Play** sobre
  una selección).
- **Cambiar nombre...**
- **Duplicar**: crea una copia en la misma pista, justo después del final
  del box original (o en el primer espacio libre disponible a partir de
  ahí).
- **Cortar** / **Copiar** / **Pegar aquí**: el portapapeles también vale
  entre pistas distintas (así es como se mueve un box a otra pista).
- **Exportar como .box...** / **Importar desde .box...** (en un punto
  vacío): ver más abajo.
- **Eliminar**.

### Deshacer/Rehacer (Ctrl+Z / Ctrl+Y)

Cada acción que modifica los boxes de una pista — mover, crear (de
cualquier forma), editar, transponer, cambiar el nombre, duplicar,
cortar/eliminar, pegar, importar desde `.box` — se deshace con `Ctrl+Z` y
se rehace con `Ctrl+Y`, como cualquier otro cambio del proyecto (ver **1.2
Deshacer/Rehacer**). Seleccionar o reproducir un box, en cambio, no genera
nada que deshacer.

### Escuchar solo el box seleccionado

Hay un solo transporte: **Play/Stop** en la barra de comandos reproducen la
canción entera. Para escuchar solo el box seleccionado (clic en un box para
seleccionarlo): **Mayús+Espacio**, o **Reproducción → Escuchar el box
seleccionado**, o clic derecho en el box → **▶ Play**. Pulsado de nuevo
durante la escucha pone en pausa; una vez más continúa desde donde se
detuvo, si entretanto no has seleccionado otro box (en ese caso vuelve a
empezar desde el principio en el nuevo). **Stop** también detiene la
escucha del box, y empezar la canción con **Play** la interrumpe: siempre se
oye una sola cosa cada vez. Mayús+Espacio vale en la vista Estructura: en
el editor de texto sigue siendo un espacio normal.

### Consejos

Encima de las cabeceras de las pistas, **? Cómo se usa** resume los
comandos de la vista (pasando el ratón por encima, o haciendo clic). Las
filas todavía vacías muestran en gris lo que se puede hacer: crear un box,
importar o grabar audio (pistas de audio), o que la pista está escrita como
texto libre.

### El cabezal de reproducción

Mientras suena la canción entera (transporte principal, sección 12), una
línea vertical cruza todas las pistas siguiendo el punto que está sonando,
y el lienzo se desplaza en horizontal lo justo para mantenerla siempre
visible — sea cual sea el box seleccionado.

### Exportar/importar un solo box

**Exportar como .box...** (menú de un box) guarda su contenido en un
archivo de texto legible a mano (mismo estilo que el formato `.st`, sección
11, pero en un solo bloque) en la carpeta `songs/` (sección 5bis).
**Importar desde .box...** (menú de un punto vacío) lo vuelve a cargar como
nuevo box en cualquier punto/pista — útil para reutilizar una sección (p.
ej. un estribillo) entre proyectos distintos.

### Conversión automática en boxes

Al importar un archivo MIDI entero o convertir audio en una pista que ya
usa boxes, el texto resultante se divide automáticamente en varios boxes
donde aparece un silencio continuo de más de 3 tiempos, en lugar de quedar
un único box grande — así el contenido queda organizado de forma legible
desde el primer momento, incluso con un archivo largo, sin tener que
reordenarlo a mano.

### Pistas de texto libre

Una pista sin boxes (texto libre) no muestra nada en la vista Estructura
de la canción: **Editar texto libre...**, la última opción del menú del
clic derecho en su nombre, abre todo su texto en el mismo editor que los
boxes (resaltado, Play, Play de la selección), sin salir de la vista. El
cambio se deshace con Ctrl+Z.

**Convertir en texto libre...** (en su lugar, para una pista que ya tiene
boxes) devuelve esa pista a un único editor de texto lineal: el contenido
musical no cambia, solo cambia la forma de editarlo. Es irreversible solo en
el sentido de que no volverá a dividirse automáticamente en boxes: el texto
se puede volver a dividir a mano.

## 9. Congelar los acordes

El botón «Congelar acordes en notas explícitas» del editor sustituye cada
acorde abstracto de la pista actual por el bloque `[...]` de notas
concretas generado por el motor de voicing para el instrumento asignado.

### 9.1 Elegir el voicing con un doble clic

Un **doble clic en un acorde** — ya sea en forma compacta (`Cmaj7`, también
con un multiplicador, p. ej. `2Cmaj7`) o ya «congelado» en notas
explícitas (`[c*3 g*3 b*3 e*4]`, si se reconoce como acorde estándar),
**aunque el acorde esté dentro de un grupo de repetición `N(...)`** (ver
2.1) — en el editor de la pista o en el cuerpo de un pattern abre un
pequeño menú con todas las alternativas de voicing que tienen sentido para
el instrumento actual (ver 2.8), cada una con una vista previa en texto de
las notas resultantes. Al recorrer las opciones con las flechas se oye una
vista previa de audio de cada una (con un breve retardo, debido al
renderizado); **Intro** o un clic en una opción aplica la elección (en el
token implícito solo añade/cambia el sufijo `.estilo`; en el bloque
explícito recalcula las notas), **Esc** o un clic fuera del menú cancela sin
cambiar nada. Si el bloque `[...]` no corresponde a ninguna calidad de
acorde conocida (p. ej. una simple quinta `[c*3 g*3]`, ambigua entre mayor
y menor), una descripción emergente lo indica y el menú no se abre.

### 9.2 Autocompletado al escribir

Mientras escribes, el editor propone en una ventana emergente los tokens
completos que encajan con el fragmento ya escrito, para agilizar las
notaciones más largas o más difíciles de recordar:

- calidades de acorde (`C7`, `Dm7b5`...) a partir de la fundamental;
- estilos de voicing (`Cmaj7.drop2`, `C7.cagEd`...) después del `.`,
  limitados a los aplicables al instrumento de la pista actual (ver 2.8);
- nombres de percusión, dinámicas (`mf`, `ff`...) y comandos de estado
  (`SON`, `SOFF`, `r`);
- referencias `%Nombre` a patterns definidos en el proyecto y `&"Nombre"` a
  la biblioteca MIDI (ver 6 y 11.1).

Flechas arriba/abajo para recorrer las propuestas, **Intro** o **Tab** para
aceptar la resaltada, **Esc** o un clic fuera para cerrar la ventana sin
cambiar nada. Las notas sueltas (p. ej. `c`, `g#*4`) no generan
sugerencias propias, porque ya son tan cortas como una sugerencia.

## 9bis. Generar batería/bajo (sin IA)

Generación de una línea de batería o de bajo sin modelos/descargas/GPU:
algorítmica, basada en una pequeña biblioteca de patrones por género
(batería) y en la lectura de los acordes ya escritos en otra pista (bajo).
Instantánea y sin dependencias pesadas.

**Variabilidad** (en los dos diálogos): un control deslizante de 0% a 100%
(predeterminado 35%) decide cuánto se aleja el resultado del patrón básico
del estilo. Al 0% el mismo estilo siempre da el mismo texto; más arriba el
generador añade variaciones:
- **Batería**: cajas fantasma a volumen bajo y bombo de más (solo en los
  huecos: los golpes del patrón se quedan en su sitio), golpes de
  charles/ride que se saltan, velocidades ligeramente distintas en cada
  compás, fills a mitad de compás o en el último tiempo en lugar de siempre
  completos. Muchos estilos tienen además **ritmos alternativos** (p. ej. el
  rock con el bombo sincopado, el reggae «steppers», el funk con otro
  bombo): al principio de cada grupo de compases el ritmo puede pasar a uno
  de ellos, y los fills se eligen entre el del estilo y algunos fills
  genéricos (redoble de caja, bajada por los toms, golpes al unísono...).
- **Bajo**: el tratamiento alternativo (notas de aproximación, tercera y
  séptima) también salta fuera del ritmo de «Variación cada N acordes»; las
  notas después de la primera de un acorde pueden alargarse, callar o subir
  una octava. La primera nota de cada acorde (la fundamental) nunca cambia,
  y la duración del acorde sigue siendo idéntica. De vez en cuando un compás
  usa un **patrón alternativo** del estilo (p. ej. las octavas sincopadas,
  el two-feel con la quinta anticipada): la elección se hace compás a
  compás, así que incluso un acorde largo (los 4 compases de tónica del
  blues) cambia de ritmo por dentro. Vale también para el acompañamiento y
  el riff. La variabilidad no solo quita, también **añade**:
  - **notas de paso** (bajo y riff): al final de un acorde, una nota que
    lleva a la fundamental del siguiente — medio tono por debajo o por
    encima, un tono por debajo o su quinta. Si la última nota es larga, la
    nota de paso se añade en su último tiempo; si no, ocupa su lugar;
  - **anticipaciones sincopadas** (bajo, acompañamiento y riff en las
    rejillas de corcheas o tresillos): la primera nota o el primer acorde de
    la vuelta siguiente llega una corchea antes, ligada por encima del
    cambio de acorde, como en el pop, el rock y la música latina. Por eso la
    fundamental puede empezar una corchea antes del compás en lugar de en el
    primer tiempo.
  Con la intensidad **Ligera** no hay notas de paso ni anticipaciones.

**Intensidad** (batería, bajo, acompañamiento y riff): cuánto debe «pesar»
la parte en la canción.
- **Ligera (estrofa, intro)**: menos golpes y menos notas — la batería
  quita los golpes de charles/ride a contratiempo y las notas fantasma y
  toca más suave; el bajo y el acompañamiento solo mantienen los ataques en
  el 1 y el 3 (las notas que quedan duran más).
- **Normal**: el patrón del estilo tal cual.
- **Llena (estribillo)**: la batería pasa del charles al ride, toca más
  fuerte y abre cada grupo de compases con un crash; los acordes del
  acompañamiento toman también la octava superior y el bajo sube una octava
  en el último ataque de cada acorde.
- **En crescendo**: ligera en el primer tercio de la parte, normal en el
  segundo, llena en el último — útil para un puente o un pre-estribillo.

El botón **🎲 Nueva variación** genera una variación distinta con los mismos
controles. La variación está ligada a una «semilla» que se mantiene fija
hasta que lo pulsas: cambiar el estilo, los compases o la octava no la hace
«saltar», y con los mismos controles el texto es reproducible. El texto
generado se puede editar a mano en la vista previa antes de confirmar.

**Preajustes y detalles de la variabilidad.** Junto al control, un menú con
tres preajustes:
- **Fiel**: 15%, sobre todo dinámica, pocas notas y ritmos cambiados;
- **Músico** (predeterminado): 35%, variaciones como las de un músico de
  sesión;
- **Creativo**: 75%, muchas variaciones, para buscar ideas.

El menú muestra «Personalizada» cuando los valores no corresponden a un
preajuste. **Detalles ▸** abre tres controles que indican qué parte de la
variabilidad va a cada aspecto (100% = toda):
- **Ritmo**: ritmos y grooves alternativos, fills, anticipaciones, notas o
  golpes que se saltan, se alargan o se añaden (el bombo extra de la
  batería);
- **Notas y armonía**: variantes del patrón, notas de paso, saltos de
  octava, las cajas fantasma de la batería; en la progresión de acordes, los
  colores y las sustituciones de los acordes (es el único aspecto de la
  progresión de acordes);
- **Dinámica**: velocidades distintas golpe a golpe y nota a nota. Para el
  bajo, el acompañamiento y el riff, la dinámica añade las velocidades
  (`N@`), más fuertes en el primer tiempo del compás y más suaves a
  contratiempo; al 0% las notas no tienen ninguna, como antes.

Por ejemplo, con la variabilidad al 60% y Ritmo y Notas al 0%, las notas
siguen siendo las del patrón y solo cambia cómo se tocan.

**Regenerar solo algunos compases.** Debajo de la vista previa: «Regenerar
solo los compases desde N hasta M» y **🎲 Regenerar estos** generan una
nueva variación solo para esos compases, dejando los demás como están. Se
puede repetir en compases distintos; los retoques se mantienen aunque
cambies los demás controles (estilo, intensidad...), **↺ Deshacer
retoques** los quita y **🎲 Nueva variación** lo regenera todo desde el
principio. El corte nunca parte una nota: si una nota cruza el inicio o el
final del tramo (una anticipación, un acorde largo), el tramo se amplía
para incluirla. Con la variabilidad al 0% el botón está desactivado (el
resultado sería idéntico).

**Componer → Generar en la pista seleccionada → Batería...** (requiere una pista de
percusión seleccionada):
- **Estilo**: el diálogo propone los estilos escritos para el compás del
  proyecto. En 4/4: Rock, Funk, Four-on-the-floor (disco), Reggae (one
  drop), Punk, Soul (Motown), Bossa nova, Rock'n'roll, Shuffle (blues),
  Swing (jazz), Hip-hop (boom bap), Half-time, Metal (doble bombo), Country
  (train beat), Samba, Cha-cha-cha y Marcha; en 3/4: Vals y Vals de jazz;
  en 5/4: Rock en 5/4 (3+2) y Jazz en 5/4 (tresillos); en 6/8: Balada y
  Afrocubano; en 7/8: Rock en 7/8 (2+2+3) y Balcánico en 7/8 (3+2+2); en
  12/8: Slow blues y Slow rock de los 50. Los estilos en 7/8 usan la
  rejilla de corcheas (`8:`). Cada estilo trae su propia rejilla rítmica: la
  mayoría usa semicorcheas (`16:`), Shuffle y Swing tresillos de corchea
  (`8T:`), que es lo que produce su característico «balanceo». No hay un
  selector de rejilla en el diálogo: un ritmo está escrito para una rejilla
  concreta y no se puede adaptar a otra sin cambiar su ritmo. En 6/8 y 12/8
  la rejilla es de corcheas (`8:`). Nota: los instrumentos que suenan en el
  mismo instante comparten la velocidad (límite de la notación en bloques
  `[...]`).
- **▶ Escuchar / ■ Stop**: reproduce la vista previa tal como está escrita
  (también después de un cambio tuyo a mano) antes de confirmar. Con **Con
  las demás pistas** marcado la oyes junto con el resto del proyecto (se
  respetan los Mute, el Solo no; el contenido actual de la pista de destino
  no suena); sin marcar suena sola. Mientras suena, en la vista previa se
  resalta el punto que estás escuchando (si editas el texto durante la
  escucha, el resaltado se suspende hasta el siguiente Escuchar). Ok,
  Cancelar o cerrar la ventana detienen la escucha. Vale también para
  **Generar bajo**, **Generar acompañamiento/riff** y **Generar progresión
  de acordes**.
- **Compases**: cuántos generar.
- **Fill cada N compases**: cada N compases inserta un fill (con un crash
  de entrada en el compás siguiente) en lugar de repetir idéntico el ritmo
  base — 0 desactiva los fills. Nunca inserta un fill en el último compás
  generado (siempre cierra con el ritmo base).
- **Fills por frases** (marcado por defecto): como un batería de verdad, al
  final de cada grupo de N compases hace un fill **pequeño** (solo el
  último tiempo) y al final de cada frase de 2×N compases un fill
  **completo**. Sin marcar, todos los fills son completos.
- **Final en el último compás**: el último compás se convierte en un golpe
  de cierre (crash y bombo en el primer tiempo, luego silencio), para
  terminar la canción o la sección.
- **Intensidad**: ver arriba.

**Componer → Generar en la pista seleccionada → Progresión de acordes...** (requiere un
instrumento polifónico: piano, guitarra, órgano, pad...): escribe una
progresión de acordes como símbolos (`Am7`, `G`...), a la que el motor le
hace el voicing solo para el instrumento de la pista. Es el punto de
partida cuando la canción todavía no tiene acordes: el bajo, el
acompañamiento y el riff necesitan una pista de acordes que seguir. En la
vista Estructura de la canción la opción aparece en el menú del clic
derecho de una pista polifónica mientras ninguna otra pista de la canción
contenga acordes: la pista que ya tiene la progresión sigue ofreciéndola, y
cada nueva progresión va en un box después del último (como en **Generar
bajo**). En cambio, **Generar acompañamiento** y **Generar riff/melodía**
solo aparecen cuando otra pista contiene acordes (desde el menú Componer, sin
acordes, un mensaje remite a la progresión de acordes).
- **Tonalidad**: parte de la del proyecto; si el proyecto no tiene ninguna
  y la pista ya tiene una progresión, de la tonalidad del box después del
  cual se pondrá la nueva (reconocida por sus acordes o sus notas); si no,
  de do mayor. Los estilos propuestos son los de su modo:
  - mayor: **Pop** (I-V-vi-IV), **Años 50 / doo-wop** (I-vi-IV-V),
    **Rock** (I-IV-I-V), **Canon de Pachelbel**, **Blues de 12 compases**,
    **Jazz II-V-I**, **Turnaround de jazz** (I-vi-ii-V), **Tres acordes**
    (I-IV-V-I), **Balada** (I-iii-IV-V), **J-pop / royal road**
    (IV-V-iii-vi-ii-V-I), **Rock mixolidio** (I-bVII-IV-I), **Gospel**
    (I-I7-IV-iv), **Círculo de quintas**, **Rhythm changes**, **Blues jazz
    de 12 compases**;
  - menor: **Pop menor** (i-VI-III-VII), **Cadencia andaluza**
    (i-VII-VI-V), **Rock menor** (i-VII-VI-VII), **Cadencia menor**
    (i-iv-i-V7), **Jazz II-V-I menor**, **Blues menor de 12 compases**,
    **Menor sencillo** (i-iv-v-i), **Menor épico** (i-VI-VII-i), **Vamp
    dórico** (i7-IV7), **Line cliché** (la voz que baja cromáticamente
    dentro del acorde menor), **Círculo menor**, **Frigio** (i-bII).
  Los grados rebajados (bVII del mixolidio, bII del frigio) se escriben con
  bemoles (`Bb` en do, no `A#`), salvo en las tonalidades con sostenidos.
- **Duración de cada acorde**: medio compás, uno o dos (multiplica la
  duración del estilo: en el blues algunos acordes duran varios compases).
- **Compases**: la progresión se repite hasta cubrirlos; **Progresión
  entera** la escribe una sola vez. Por defecto cubre la música que ya hay
  en las demás pistas.
- **Variabilidad**: al 0% el estilo tal cual. Más arriba:
  - los acordes se enriquecen (séptimas, novenas, sus) manteniendo la misma
    función;
  - **dominantes secundarias**: un acorde que dura al menos un compás deja
    su segunda mitad a la dominante del acorde siguiente (en do: `A7` antes
    de `Dm`, `E7` antes de `Am`); si dura al menos dos compases, su último
    compás puede convertirse en un **II-V** hacia él (`Bm7b5 E7` antes de
    `Am`). El último acorde de la progresión no se prepara así, salvo que
    sea la tónica: si no, sonaría como un cambio de tonalidad;
  - **sustituto de tritono**: una dominante que baja una quinta se
    convierte en la que está a un tritono (`Db7` en lugar de `G7` antes de
    `C`), nunca el acorde de tónica (el `C7` del blues se queda);
  - **IV menor** (en mayor): el IV que vuelve al I toma prestado el iv menor
    (`F Fm6 C`).
  Los acordes cromáticos se escriben con bemoles (`Db7`), salvo en las
  tonalidades con sostenidos.
- **Cadencia final** (sin marcar por defecto, para dejar la progresión
  abierta y lista para repetirse): el último compás se convierte en el
  acorde de tónica, precedido durante medio compás por un acorde de
  cadencia. Al 0% siempre es `V7`; con la variabilidad puede ser también
  plagal (`IV`), iv menor (`Fm6`), «backdoor» (`Bb7`) o `V7sus4`, en menor
  `V7`, `iv` o `VII`. Las progresiones que no empiezan en la tónica (II-V-I,
  royal road) siempre cierran con la dominante o su sustituto de tritono,
  porque es la que establece la tonalidad.

**Componer → Generar en la pista seleccionada → Bajo a partir de acordes...** (requiere
otra pista del proyecto con acordes ya escritos):
- **Acordes de**: qué pista da la secuencia armónica que seguir (las notas
  sueltas/percusiones/silencios de esa pista se ignoran, solo cuentan los
  acordes: escritos como símbolo, p. ej. `Cmaj7`, o como bloque
  `[c*4 e*4 g*4]` de al menos dos notas, que es como los escribe la
  importación MIDI; el bloque se reconoce como acorde conocido; si no, la
  fundamental es la nota más grave). Una pista hecha solo de notas sueltas
  (melodía, arpegios) no tiene acordes que seguir.
- **Estilo** (cada uno escribe su propia rejilla rítmica: negras, corcheas
  o, para el shuffle, tresillos de corchea):
  - **Fundamental**: repite la tónica durante toda la duración del acorde.
  - **Fundamental/quinta**: las alterna.
  - **Walking bass**: camina por los grados del acorde con una nota de
    aproximación cromática al acorde siguiente (simplificación del walking
    bass del jazz); la variante usa la tercera y la séptima reales del
    acorde (tercera menor en un acorde menor).
  - **Pedal**: una sola nota larga por acorde (baladas).
  - **Dos tiempos**: fundamental en el 1 y quinta en el 3 (jazz lento,
    country).
  - **Octavas**: fundamental y octava alternadas (disco, funk sencillo).
  - **Blues 1-3-5-6**: la línea clásica del blues/boogie sobre la tercera
    real del acorde (la variante cierra con la séptima de dominante).
  - **Corcheas**: fundamental en corcheas (rock, pop, punk).
  - **Reggae**: el primer tiempo queda vacío, fundamental larga desde el 2.
  - **Bossa nova**: fundamental en el 1 y el 3, quinta en la «y» del 2 y
    del 4.
  - **Shuffle blues**: 1-3-5-6-b7-6-5-3 en corcheas «balanceadas» en
    tresillos.
  Los patrones son modelos genéricos sencillos (un compás que se repite
  sobre el acorde), no transcripciones de canciones; un acorde más corto que
  un compás corta el patrón. Con la Variabilidad algunos estilos alternan un
  segundo patrón (ver arriba).
- **Intensidad**: ver arriba (también en **Generar acompañamiento/riff**).

En **Generar acompañamiento** también está **Inversiones cercanas**
(marcado por defecto): cada acorde elige la inversión más cercana a la
anterior (conducción de voces), como haría un pianista — por ejemplo
do-mi-sol, luego do-fa-la, luego si-re-sol — en lugar de quedarse siempre
en estado fundamental y saltar de una posición a otra. El primer acorde se
queda como está; todos se mantienen dentro del rango del instrumento y no
se alejan demasiado del registro de partida. Vale para acordes de al menos
tres notas (no para arpegios ni bicordes, que ya tienen su propio patrón).
- **Octava** de la línea de bajo generada.
- **Variación cada N acordes**: cada N acordes usa un tratamiento
  ligeramente distinto del mismo acorde (salto de octava, nota distinta...)
  en lugar de repetir idéntico el patrón — 0 desactiva las variaciones.

Los dos muestran una vista previa editable a mano antes de confirmar (como
la importación de audio, sección 10bis), y el resultado se añade a
continuación del contenido que ya hay en la pista de destino, no lo
sustituye.

**Compás**: se usa el compás inicial del proyecto. El bajo, el
acompañamiento y el riff repiten el patrón del estilo en compases de la
duración adecuada (3 tiempos en 3/4 y 6/8, 6 en 12/8...), así que funcionan
con cualquier compás; un estilo pensado para el 4/4 se corta al compás más
corto, y hay estilos hechos a propósito: **Vals** para el bajo (fundamental
en el 1), **Vals** y **Arpegio en 6/8** para el acompañamiento. La batería,
en cambio, requiere un estilo escrito para ese compás (4/4, 3/4, 5/4, 6/8,
7/8, 12/8, o un estilo personal guardado en ese compás, ver 9bis.1): con un
compás sin estilos (p. ej. 9/8) el diálogo lo indica y desactiva la
confirmación.

### 9bis.1 Estilos personales: aprender de tus canciones

Además de los estilos ya preparados, los generadores pueden usar estilos
sacados de una parte tuya: un ritmo de batería o una línea de bajo que te
gusta se convierte en un nuevo modelo, que sigue cualquier progresión de
acordes.

**Desde dónde se guarda** («Guardar como estilo del generador...»):
- clic derecho en un **box** en la vista Estructura de la canción;
- menú **Componer → Estilos de los generadores → Guardar la pista como estilo...** (toda la pista seleccionada);
- **Biblioteca MIDI** (menú Componer → Gestionar biblioteca MIDI):
  el botón debajo de la vista previa ofrece todos los canales del archivo
  seleccionado.

**El diálogo:**
- **Parte**: para un archivo MIDI, qué canal;
- **Tipo**: Batería (para las partes de percusión), o Bajo, Acompañamiento,
  Riff/melodía (propuesto según el instrumento);
- **Acordes de**: la parte con los acordes sobre los que sonaba el patrón
  (para un box, los acordes en el mismo punto de la canción; para un
  archivo MIDI, otro canal). Sirve para saber qué nota es la fundamental, la
  tercera, la quinta... Sin acordes, la primera nota de cada compás hace de
  fundamental;
- **Compás** y **Nombre**. Debajo, un resumen de lo que se ha sacado
  (cuántos compases leídos, rejilla, cuántas alternativas, si hay un fill).

**Cómo se saca:**
- **Batería**: los compases se colocan en la rejilla (semicorcheas o
  tresillos; corcheas en los compases de /8). El compás más frecuente pasa a
  ser el ritmo base, los demás distintos (hasta 3) los ritmos alternativos,
  que se usan con la variabilidad, y el que tiene toms el fill. Sin un compás
  con toms se usa un fill genérico (caja en el último tiempo). El crash en
  el primer tiempo no entra en el ritmo, porque lo añade el generador.
- **Bajo, acompañamiento, riff**: cada nota se convierte en un **grado del
  acorde** en su octava (fundamental, tercera, quinta, sexta, séptima, o un
  intervalo concreto). Sobre otra progresión la línea sigue los nuevos
  acordes, con la tercera correcta (menor en un acorde menor). La última nota
  antes de un cambio de acorde, a medio tono de la nueva fundamental, se
  convierte en una nota de aproximación hacia el acorde siguiente, sea el que
  sea. Los silencios siguen siendo silencios. El compás más frecuente es el
  patrón base, el segundo la variante (usada con «Variación cada N
  acordes»), otros hasta 3 las alternativas. Para el acompañamiento también
  se pueden usar boxes hechos solo de símbolos de acorde: de ellos se saca el
  ritmo. Para el bajo se conserva la nota más grave de cada ataque, para el
  riff la más aguda.

Los estilos guardados aparecen en los diálogos de los generadores con una
**★** delante del nombre, al final de la lista; la batería solo ofrece los
del compás del proyecto. **Componer → Estilos de los generadores → Estilos personales...** los enumera para cambiarles el nombre o eliminarlos. Se
guardan en la carpeta de configuración (`generator_styles.json`, junto a los
instrumentos personalizados), así que valen para todos los proyectos.

### 9bis.2 Melodías por frases

En **Generar riff/melodía** (instrumentos monofónicos: trompeta, saxo,
flauta, voz, synth lead...), además de los riffs que repiten un patrón
sobre las notas del acorde, hay cuatro estilos que escriben una **melodía
de verdad**:
- **Melodía por frases (A A' B A)**: tema, tema repetido con otro final,
  una frase de contraste y la vuelta del tema;
- **Melodía pregunta y respuesta (A A')**: la primera frase queda
  «abierta», la segunda la retoma y la cierra;
- **Melodía lenta (balada)**: como A A' B A, con notas largas;
- **Melodía movida**: como A A' B A, con más corcheas.

**Cómo se construye:**
- **Frases** de dos compases (cuatro en 3/4, 2/4 y 6/8). La forma se repite
  hasta cubrir los compases pedidos; la última frase de la canción siempre
  cierra.
- **Motivo**: la frase A tiene un ritmo y un perfil que vuelven. En la
  repetición, si debajo están los mismos acordes, A vuelve idéntica, salvo
  el final; sobre acordes distintos el motivo se traslada al nuevo acorde,
  con el mismo ritmo y el mismo movimiento. B tiene otro ritmo (más movido,
  o más tranquilo en la versión movida) y sube más.
- **Armonía**: en los tiempos fuertes (primer tiempo y mitad del compás, y
  las notas largas) la melodía usa notas del acorde; en los demás tiempos
  prefiere las notas del acorde; a contratiempo las notas de la escala,
  preferiblemente por grado conjunto. Las notas del acorde ajenas a la
  escala sustituyen a la natural cercana (el sol# de `E7` en la menor, el
  sib de `C7` en do).
- **Movimiento**: cada frase sube hacia un punto más alto, hacia los dos
  tercios, y luego baja a la cadencia. Después de un salto la melodía vuelve
  atrás; evita saltos enormes, tres notas iguales seguidas y los «trinos»
  de ida y vuelta.
- **Cadencias**: una frase «abierta» (la pregunta) termina en una nota del
  acorde distinta de la tónica, preferiblemente la quinta o la segunda de
  la escala. Una frase «cerrada» (la respuesta) termina en la tónica, o, si
  el acorde no la contiene (una frase que termina en el V), en la tercera o
  la quinta de la tónica.
- **Tonalidad**: la del proyecto; si no está definida, la reconocida a
  partir de los acordes de la pista elegida en «Acordes de».

«Variación cada N acordes» no vale para estas melodías (el campo se
desactiva): tienen su propia forma. Los demás controles funcionan como en
los otros estilos:
- **Variabilidad**: al 0% la melodía solo depende de los acordes, el
  estilo y la tonalidad. Más arriba, **🎲 Nueva variación** genera otro
  motivo. El control **Ritmo** hace más variados los ritmos y puede cambiar
  un compás en las repeticiones; **Notas y armonía** hace elegir notas menos
  «obvias» y cambia alguna nota en las repeticiones; **Dinámica** hace
  crecer el volumen hacia el punto más alto de cada frase y acentúa los
  tiempos.
- **Intensidad**: Ligera hace la melodía más tranquila (menos notas), Llena
  más movida, En crescendo cada vez más movida a lo largo de la canción.
- **Regenerar solo los compases** también vale aquí.

## 10. Importar/Exportar MIDI

- **Proyecto → Exportar → MIDI**: todo el conjunto (pistas audibles según
  Solo/Mute) en un único archivo MIDI multipista.
- **Proyecto → Importar → MIDI**: crea un nuevo proyecto con una pista por
  cada canal del archivo MIDI; el canal 10 siempre se convierte en Batería.
- **Pista → Exportar esta pista / Importar en esta pista → MIDI**: exporta solo la
  pista seleccionada, o importa un archivo MIDI (eligiendo el canal, si el
  archivo contiene más de uno) sustituyendo el contenido de la pista
  actual; también se propone actualizar el instrumento según el
  reconocimiento automático.

**Reconocimiento/creación automática del instrumento**: para cada canal,
si un instrumento ya disponible (predefinido o personalizado) tiene
exactamente el Program Change GM del canal, se usa ese; si no, **se crea y
registra automáticamente un nuevo instrumento personalizado** con ese
programa exacto (nombre derivado del nombre oficial General MIDI, p. ej.
programa 81 → `Lead2sawtooth`; parámetros de octava/extensión/voicing
sugeridos según la familia, como al crearlo a mano desde **Sonidos → Gestionar instrumentos**), de modo que la pista importada refleje siempre
fielmente el instrumento original en lugar de conformarse con el más
parecido. Al terminar la importación, si se han creado instrumentos
nuevos, un aviso muestra la lista (siempre se pueden modificar después
desde **Sonidos → Gestionar instrumentos**). Esta creación automática
solo ocurre en una importación confirmada de verdad (no en la simple vista
previa del selector de canal, que sigue mostrando el nombre del
instrumento ya disponible más parecido).

**Canales que cambian de instrumento**: si un canal cambia de instrumento
a mitad de la canción (un Program Change entre las notas: en *Layla* el
riff de la intro está en guitarra overdrive y luego pasa al piano, en el
mismo canal), la importación multipista crea **una pista por
instrumento**, cada una solo con las notas tocadas con ese instrumento y
con el volumen y el pan vigentes cuando entra. Si el canal vuelve varias
veces al mismo instrumento, esas partes van en la misma pista. El canal de
la batería no se divide (ahí el programa elige el kit).

Nota sobre la precisión de la importación: la notación admite notas
cromáticas (`c#`, `eb`, etc.), así que la altura se conserva; el ritmo se
cuantiza en una rejilla de semicorcheas o, compás a compás, en una rejilla
de **tresillos** cuando los ataques lo requieren (ver abajo).

**Tresillos y grupos irregulares**: para cada tiempo, la importación elige
la subdivisión que mejor explica los ataques. La rejilla binaria
(semicorcheas) gana si los explica todos; si no, se usa un tresillo de
corcheas (`8T:`, sección 2.1bis) cuando los explica y la binaria no —
típico del shuffle, del swing 2:1 y del blues en 12/8, donde antes las
notas se movían a la semicorchea más cercana. Los seisillos (`16T:`),
quintillos (`16Q:`) y septillos (`16S:`) tienen umbrales mucho más
estrictos (hacen falta más ataques en el tiempo y una desviación muy
pequeña); si no, una interpretación humana poco precisa se confundiría con
un grupo irregular. Los ataques casi simultáneos (bombo y ride con unos
pocos ticks de diferencia) cuentan como un solo punto rítmico, y los
quintillos/septillos en la práctica solo se reconocen en pasajes muy
regulares. El comando de rejilla solo se escribe cuando cambia. Una nota
que, partiendo de una rejilla, terminaría dentro de un tiempo con otra
rejilla, en un punto que no es un límite de tiempo, se cierra en el
límite: puede quedar, por tanto, un poco más corta que la original, pero el
resto de la pista nunca se desplaza. Un archivo solo binario produce los
mismos tokens que antes.

**Notas superpuestas y voces**: en ST las únicas notas simultáneas son las
de un mismo bloque `[...]` (misma duración), mientras que en MIDI una nota
sostenida bajo una melodía, o un acorde que continúa bajo una voz, se
superponen. Antes la importación se saltaba todo ataque que cayera dentro
de una nota más larga: en una biblioteca de prueba desaparecía cerca del 8%
de las notas, y en algunos archivos casi la mitad. Ahora la **importación de
un archivo completo** separa cada canal en **voces monofónicas** (como
máximo 2 por canal, siempre: si en un mismo ataque empiezan más grupos de
duraciones distintas que voces, los grupos sobrantes se funden con el de
duración más parecida; nunca en la batería): las notas que empiezan juntas
y terminan (con una semicorchea de margen) juntas siguen siendo un único
bloque, cada grupo va a la primera voz libre, y una superposición mínima
(legato dentro de una semicorchea) acorta la nota anterior en lugar de
abrir una voz. Las voces se quedan **en la misma pista**: donde solo suena la primera el
texto es el de siempre, donde suenan también las otras se convierte en un
**bloque de voces** `{ ; }` (sección 2.12) en una línea aparte, que empieza
y termina en las barras de compás cuando no corta ninguna nota; el texto
unido suena exactamente como las voces separadas. (Hasta la versión
anterior cada voz se convertía en una pista aparte, `Piano voce 2`.) Vale
también para la importación de un **solo canal** en una pista. El tempo
(`tempo=N`) está en la primera voz. Cuando se agotan las voces, la nota anterior
se **acorta** hasta el ataque siguiente: se pierde la duración sostenida,
nunca la nota.

**Letra**: los eventos *lyrics* del archivo, y el texto de los archivos de
karaoke (`.kar`, eventos de texto en una pista sin notas), se convierten
en letra entre comillas (sección 2.13) en la primera voz del canal que la
canta (el de las notas de la misma pista MIDI, o aquel cuyas notas atacan
donde caen las sílabas): una línea por compás después de sus notas, `*`
para una nota sin sílaba y `""` antes de un pasaje cantado que sigue a uno
instrumental.


**Canales MIDI con muchas pistas**: un archivo MIDI solo tiene 15 canales
melódicos (el 10 es de la batería) y en cada canal hay un solo instrumento,
un solo volumen/pan y un solo pitch bend. Con más de 15 pistas (fácil con
las voces de la importación) la exportación asigna primero un canal a cada
instrumento *distinto*, luego los canales que sobran a las voces extra, y
las demás comparten el canal de su propio instrumento: ninguna pista suena
nunca con el instrumento de otra. Las voces del mismo instrumento que
comparten canal tienen el pitch bend en común (un slide en una se oye
también en las notas de la otra mientras suenan juntas).

Las notas idénticas en el mismo tick (duplicados) y los ataques a la misma
altura dentro de la misma semicorchea se funden en una.

**Velocity de las notas simultáneas**: en ST cada token (nota, acorde o
bloque `[...]`) tiene una sola velocity, así que las velocities distintas
de las notas de un mismo grupo (por ejemplo un acento en la voz superior de
un acorde, o bombo y charles golpeados a la vez) no se pueden conservar una
por una: el grupo importado toma la **media redondeada** de las velocities,
que mantiene la intensidad global. Con todas las velocities iguales no
cambia nada.

**Dinámicas a partir del volumen y la expresión (CC7/CC11)**: los
crescendos, diminuendos y fundidos del archivo MIDI son automatizaciones
continuas, que ST solo expresa como velocity de las notas (sección 2.5). La
importación calcula el nivel CC7 x CC11 en el momento de cada ataque, lo
normaliza respecto al máximo del canal y lo aplica a la velocity de la
nota: la nota más fuerte del canal conserva su velocity original, las demás
bajan en proporción, y el resultado aparece como una serie de `N@` (por
escalones, uno por cada nota que cambia, no como una rampa `>>`). Un volumen
constante (típicamente CC7 = 100) o una variación inferior al 15% del
máximo no es una dinámica y se ignora. El volumen *absoluto* del canal
respecto a los demás no se importa (se ajusta desde el mezclador).

**Articulaciones (`!`, `x`, `_`)**: para las notas sueltas y los acordes
implícitos (opción «Reconocer acordes») la importación compara la duración
real de la nota con el intervalo hasta el ataque siguiente: más o menos la
mitad → staccato `!` (sección 2.2), menos del 30% → apagada `x`, más del
105% (nota que se superpone a la siguiente) → legato `_`. En ese caso el
token ocupa todo el intervalo hasta la nota siguiente (p. ej. `2c*4!`) en
lugar de una nota corta seguida de silencios, y así sigue siendo editable
como la escribiría un músico. Una nota corta seguida de un silencio largo
(más de un tiempo, o medio tiempo para la apagada) sigue siendo nota +
silencio: no es una articulación. Las notas normales (entre el 70% y el
105% aproximadamente), los bloques explícitos `[...]` (sin modificador
final, sección 2.2), los slides y la batería no cambian.

**Tempo, compás y pedal**: los cambios de tempo del archivo se convierten
en marcadores `tempo=N` (sección 2.6) — en **una sola** pista, porque el tempo
es global en ST: se elige aquella en la que los marcadores se desplazan
menos (en general la batería, hecha de golpes breves; un marcador que
caería dentro de una nota larga se emite al final de esta). El tempo
inicial sigue siendo el del proyecto y las oscilaciones pequeñas (menos de
2 BPM o del 2%: el ruido de un tempo grabado en directo) no son cambios de
tempo y se ignoran. El compás (evento *time signature*) fija el campo
**Compás** del proyecto; si cambia a lo largo de la canción se convierte en
la lista por compás (`Metrica: 1: 3/4, 3: 4/4`, sección 2.7). El pedal de
sustain (CC64, pisado a partir de 64) se convierte en `SON`/`SOFF` (sección
2.4), solo en las transiciones efectivas; un pedal todavía pisado al final
del canal se cierra con un `SOFF` final. La exportación MIDI ahora también
escribe el compás, de modo que un viaje de ida y vuelta
exportación→importación lo conserva. Al importar un solo canal en una
pista existente, los cambios de tempo y de compás NO se importan (son
globales del proyecto); el pedal sí.

**Bending (pitch bend)**: una nota suelta (nunca un acorde) cuyo pitch bend
alcanza al menos un semitono completo durante su duración se importa como
un **slide** (`c*4>d*4`, sección 2) desde la altura de partida hasta el pico
del bend, en lugar de aplanarse a la altura nominal — útil sobre todo para
los MIDI de guitarra blues/rock, donde el bending suele ser parte integral
de la frase. Si la rueda vuelve después de forma significativa hacia un
semitono distinto antes del final de la nota (bend-and-release, técnica
habitual: sube y luego suelta), el slide importado tiene una tercera etapa
(`c*4>d*4>c*4`, sección 2.3) en lugar de detenerse solo en el pico. Las
duraciones de cada etapa (sección 2.3) reflejan el timing REAL del bend
detectado en el MIDI de origen — cuándo se alcanza el pico respecto a la
duración de la nota — en lugar de suponer siempre un reparto a partes
iguales entre rampa y mantenimiento/liberación: un bend rápido seguido de
un mantenimiento largo (p. ej. `1c*4>3d*4`) suena por tanto distinto, y más
fiel al original, que un bend lento que solo alcanza el pico hacia el final
(p. ej. `3c*4>1d*4`). Se respeta la sensibilidad del pitch bend declarada en
el archivo (RPN 0, Pitch Bend Sensitivity); si el archivo no la declara, se
supone el valor por defecto de General MIDI (±2 semitonos). Un bend que se
redondea a 0 semitonos (vibrato o imprecisiones de grabación), demasiado
pequeño respecto a la escala completa de la rueda (una automatización
continua de expresión/humanización, no un bend deliberado) o de una
amplitud inverosímil (más de 12 semitonos: los bends reales de guitarra casi
siempre se quedan en 2-3 semitonos, y un salto mayor no es un bend en ningún
instrumento — sería una nota distinta, no una inflexión de la misma; ocurre
cuando la sensibilidad RPN declarada refleja una capacidad técnica del
canal, no la intención de bend de esa nota concreta) sigue siendo una nota
normal, para evitar un slide sin sentido musical.

**Slide guitar (Opciones → Importación MIDI → Slides en la importación MIDI...)**: en un canal
con una sensibilidad de pitch bend amplia (12 semitonos, típica de los MIDI
de guitarra slide) el umbral de siempre es de unos 1,2 semitonos, y los
bends breves de un semitono siguen siendo notas normales. Marcando **Slide**
en el diálogo se activa el campo **Umbral** (0,5-1,2 semitonos, 0,8 por
defecto): la importación reconoce como slides también los bends más
pequeños. El umbral solo puede bajar, así que en los canales con
sensibilidad estrecha (p. ej. 2 semitonos) no cambia nada. Cuanto más bajo,
más slides se encuentran, pero más crece el riesgo de confundir con un
slide una expresión de la rueda (visto en piezas de jazz): mantenlo alto en
las piezas sin slide. El ajuste vale a partir de la próxima importación y,
sin la casilla marcada, la importación sigue siendo idéntica a antes. El
**timing de la liberación** es el real del archivo: un bend que sube
enseguida, se queda en el pico casi toda la nota y solo suelta al final se
convierte en una cadena de 4 etapas con el mantenimiento como rampa plana
(`1f*5>11g*5>1g*5>3f*5`: sube, mantiene el sol, suelta, se queda en el fa);
uno que suelta enseguida y luego se queda en la altura escrita tiene el
mantenimiento largo al final (`1e*5>1d#*5>2e*5`), en lugar de extenderse
linealmente por toda la nota (lo que hacía deslizar la afinación durante
toda la duración). Si la liberación solo empieza en el último instante, la
nota termina mientras todavía está soltando y se escribe un simple bend con
mantenimiento (`1f*5>3g*5`). Una **cola de liberación** de la nota anterior
(la rueda todavía está volviendo hacia el centro cuando empieza la nota) no
es un bend: la referencia sigue siendo el centro.

**Bends que empiezan tarde y bends en dos direcciones** (típicos del slide/
bottleneck): si la rueda se queda casi quieta durante un tramo (al menos el
15% de la nota, con pequeñas derivas) antes de moverse, el slide tiene un
mantenimiento inicial (`7d*4>1d*4>8c#*4`: se queda quieto y luego baja) en
lugar de partir del ataque. Si la rueda tiene excursiones significativas a
*ambos* lados de la nota escrita (sube un tono y luego baja por debajo), el
bend se importa como un recorrido por etapas — la curva de la rueda
simplificada (desviación máxima de 0,7 semitonos) y redondeada a semitonos —
en lugar de conservar solo la excursión más grande. En notas de pocas
semicorcheas la rejilla limita la precisión: cada rampa ocupa al menos una
semicorchea.

**Bends amplios (hasta una octava)**: antes el límite era de 4 semitonos;
ahora es de **12** (una octava), porque con una sensibilidad de la rueda
declarada (RPN) amplia existen glissandos e inflexiones reales de 5-12
semitonos — slide/bottleneck, la caída de afinación tipo cinta de las
cuerdas en *Strawberry Fields Forever*, los «dives» de palanca. Más allá de
la octava sigue siendo una nota normal (no es una inflexión). Si un canal
empieza ya inflexionado (scoop) y dentro de la nota la rueda se hunde **más
lejos** del centro que el punto de partida en al menos 1,5 semitonos
(empieza en -4, baja a -12 y luego vuelve a subir), la caída se conserva:
recorrido por etapas con el centro como referencia, no un simple scoop. Una
caída tardía (pasada la mitad de la nota, con al menos 3 eventos en la
bajada) deja la nota quieta hasta ese momento.

**Pre-bend de la nota siguiente**: cuando la rueda se aleja del centro en
los últimos ticks de una nota (dentro de una décima de tiempo) y todavía
está descentrada en el ataque de la siguiente, ese movimiento es el
pre-bend de la OTRA nota y no un bend fantasma al final de la primera. Si
en cambio vuelve a 0 justo en el ataque siguiente (un fall-off que se pone
a cero), pertenece a la nota que está terminando.

Un **pre-bend / scoop** (la rueda ya está descentrada *antes* del ataque y
vuelve al centro durante la nota: cuerda ya estirada y luego soltada, o nota
«tomada desde abajo», típica de los MIDI de guitarra y de voz) se importa
como slide desde la altura de partida *real* hacia la nota escrita: una
rueda a -1 semitono que sube a 0 sobre un re se convierte en `c#*4>d*4` (do#
que sube a re), y una a +1 que baja se convierte en `d#*4>d*4`. La altura
escrita en el MIDI es siempre la de llegada. Una rueda descentrada que NUNCA
vuelve al centro durante la nota sigue siendo un desplazamiento estático del
canal (nota normal). Atención: los slides de ST trabajan con semitonos
enteros, así que una inflexión real de alrededor de un semitono se redondea
al semitono entero más cercano.

**Opción «Reconocer acordes en la importación MIDI»** (**Opciones** →
casilla del mismo nombre, desactivada por defecto): cuando un grupo de notas
simultáneas corresponde a una calidad de acorde estándar (p. ej. do mayor),
se importa en la forma implícita equivalente (`C*4`) en lugar de como bloque
explícito (`[c*4 e*4 g*4]`) — más legible y más fácil de transportar a mano.
Un acorde que no se puede reconocer (p. ej. una simple quinta, ambigua entre
mayor y menor) sigue siendo de todos modos un bloque explícito.
**Atención**: a diferencia del bloque explícito, que siempre reproduce
fielmente el voicing y el registro originales del MIDI, la forma implícita
es **revoiceada automáticamente por el motor** según el instrumento de la
pista en la siguiente exportación — útil para adaptar el acorde al
instrumento de destino, pero un viaje de ida y vuelta importación→exportación
ya no reproducirá necesariamente exactamente las mismas notas que el archivo
original. El comportamiento predeterminado (bloque explícito) sigue siendo,
por tanto, el más fiel.

### 10.1 Exportar la partitura (MusicXML)

**Proyecto → Exportar → Partitura MusicXML...** guarda la canción como
partitura en formato **MusicXML** (`.musicxml`), que se abre con los
programas de notación: MuseScore (gratuito), Finale, Sibelius, Dorico y
muchos otros. Desde ahí se puede imprimir, exportar a PDF, corregir la
maquetación o añadir la letra. Como la exportación MIDI, contiene las
**pistas audibles** (tiene en cuenta Solo y Mute); las pistas de audio no
tienen notas y quedan fuera.

Qué contiene la partitura:

- **una parte por pista**, con el nombre de la pista;
- **las notas** exactamente como las toca SoundText: los acordes aparecen
  con las notas elegidas por el motor de voicing, los bloques `[...]` como
  acordes escritos;
- **los cifrados de los acordes** (`Am7`, `C/E`...) sobre el pentagrama,
  escritos solo cuando el acorde cambia, como en un lead sheet;
- **la tonalidad** del proyecto (sección 2.7bis) como armadura; las notas de
  los acordes usan bemoles en las tonalidades con bemoles;
- **compás y tempo**, incluidos los cambios por compás (sección 2.7) y los
  marcadores de tempo en las pistas;
- **tresillos, quintillos y septillos** con su corchete;
- **dinámicas** obtenidas de la velocity (`p`, `mf`, `f`...), escritas solo
  cuando el nuevo nivel dura al menos cuatro notas, **articulaciones**
  (staccato, apagada, legato) y **pedal** de sustain.
- **las voces** de los bloques `{ ; }` (sección 2.12) como voces del
  mismo pentagrama, con las plicas hacia arriba y hacia abajo;
- **la letra** (sección 2.13) debajo de las notas, con guiones y líneas
  de extensión.

Las claves siguen las convenciones de las partes impresas: pianos y órganos
en dos pentagramas (sol y fa, separados en el do central), guitarras en
clave de sol y bajos en clave de fa con el **8 debajo** (suenan una octava
por debajo de lo escrito), los demás instrumentos en clave de sol o de fa
según su registro. La batería usa el pentagrama de percusión con las
posiciones habituales (bombo abajo, caja en el centro, platos arriba con
cabeza en **x**).

Una duración que no corresponde a una figura (por ejemplo 5 corcheas) se
escribe como notas **ligadas**, y una nota que cruza la barra de compás
continúa ligada en el compás siguiente.

**Límites**: dentro de una misma voz no pueden convivir dos notas que se
superponen (ocurre en las canciones importadas de MIDI): la primera se
acorta hasta el ataque de la segunda. Para escribir de verdad varias
voces se usan los bloques `{ ; }`. Los slides aparecen solo con la nota de
partida.

### 10.1bis Ver e imprimir la partitura (Vista → Partitura)

**Vista → Partitura...** (`Ctrl+Shift+P`) abre una ventana con las pistas
en pentagrama, maquetadas en páginas A4: las mismas notas, cifrados,
voces y letra que la exportación MusicXML, **sin programas externos**. La
ventana sigue abierta junto al editor y **se actualiza mientras escribes**
(tras una breve pausa).

- **Todas las pistas audibles** o **Solo la pista seleccionada**.
- **−** / **+**: zoom.
- **Exportar PDF...** guarda la partitura en PDF (vectorial, imprimible a
  cualquier tamaño); **Imprimir...** la envía a la impresora.
- Si una pista tiene un error de sintaxis, sigue visible la última
  partitura válida, con el aviso del error.

**Proyecto → Exportar → Partitura PDF...** hace lo mismo sin abrir la
ventana.

La maquetación la hace **Verovio**, una biblioteca libre de grabado
musical (LGPL) que se instala con SoundText. Si falta, la ventana explica
cómo instalarla (`pip install verovio`); la exportación MusicXML funciona
igualmente. Para retoques de maquetación (espaciados, texto libre en la
página) sigue disponible la vía MusicXML → MuseScore.

### 10.2 Importar una partitura (MusicXML)

**Proyecto → Importar → MusicXML...** crea un proyecto nuevo a partir de una
partitura **MusicXML** (`.musicxml`, `.mxl` comprimido o `.xml`), el
formato de intercambio de MuseScore, Finale, Sibelius, Dorico y de casi
todos los programas de notación; muchas partituras gratuitas en internet
se descargan en este formato. También se puede abrir directamente desde
la línea de comandos (`soundtext cancion.musicxml`).

En qué se convierte la partitura:

- **una pista por parte**, con el nombre de la parte («Flauta»,
  «Violín I»...) y el instrumento indicado en la partitura (o reconocido
  por el nombre de la parte); dos voces en el mismo pentagrama se
  convierten en voces de la misma pista (bloques `{ ; }`, sección 2.12),
  como en la importación MIDI (sección 10);
- **las notas a la altura real**: los instrumentos transpositores (saxo,
  clarinete, trompeta en si♭, guitarra escrita a la octava) suenan como se
  oyen, no como están escritos;
- **tempo, compás y tonalidad**, con los cambios de tempo y de compás, y
  las **dinámicas** (`p`, `mf`, `f`...) como velocity;
- **repeticiones, 1.ª/2.ª casilla, D.C., D.S., Fine y Coda** desplegadas
  en el orden en que se tocan; después de un D.C. o un D.S. las
  repeticiones no se repiten y se toca la última casilla, como es habitual;
- **las notas ligadas** se convierten en una sola nota; un compás en
  **anacrusa** al principio se completa con un silencio, para que los
  compases queden en su sitio;
- **los cifrados de acordes** (`Am7`, `G7b9`, `C/E`...) se convierten en
  una pista **Acordes** («Accordi»): en un lead sheet (melodía y cifrado)
  suena y acompaña la melodía; si la partitura ya tiene otras partes que
  tocan la armonía, la pista queda muda (basta con quitar el Mute para
  oírla). Los acordes que SoundText no tiene se convierten en el más
  cercano (por ejemplo `m11` pasa a ser `m9`).

La batería escrita en el pentagrama de percusión se convierte en una pista
de percusión, con los sonidos indicados en la partitura. Las notas de
adorno (escritas en pequeño) se ignoran. La **letra** se convierte en
letra entre comillas (sección 2.13), con guiones y elisiones; en las
repeticiones se usa la estrofa de esa pasada (la 1 la primera vez, la 2 la
segunda), si existe. La opción
**Reconocer acordes** de la importación MIDI vale también aquí.

### 10.3 Notación ABC (importar y exportar)

El **ABC** es una notación musical de solo texto (estándar 2.1), usada por
las grandes colecciones de música tradicional y folk y por programas como
abcjs, EasyABC, abcm2ps y abc2midi: una pieza `.abc` también se lee y se
escribe a mano.

**Proyecto → Exportar → Partitura ABC...** guarda las pistas audibles
como una pieza ABC:

- cada pista es una **voz** (`V:`) con su nombre y su instrumento
  (`%%MIDI program`); piano y órgano tienen dos pentagramas unidos por
  una llave, las voces de los bloques `{ ; }` comparten pentagrama
  (`%%score`); la batería va en el canal 10, con las notas de los sonidos
  General MIDI;
- **tonalidad** (`K:`), **compás** (`M:`, con los cambios en todas las
  voces), **tempo** (`Q:`), **cifrado de acordes** entre comillas,
  **dinámicas** (`!mf!`), staccato y tenuto, **tresillos** y los demás
  grupos irregulares, notas ligadas de un compás a otro y **letra**
  (`w:`);
- guitarras y bajos usan la clave a la octava baja (`treble-8`, `bass-8`),
  con las notas escritas una octava más arriba como pide el estándar.

Los slides se convierten en su primera nota; el pedal y las automatizaciones
(`vol=`, `pan=`... sección 2.15) no se escriben (no están en el estándar).

**Proyecto → Importar → ABC...** crea un proyecto nuevo a partir de la
primera pieza del archivo (también se puede abrir desde la línea de
comandos: `soundtext pieza.abc`). Se leen notas, silencios, acordes
`[CEG]`, unidad de nota (`L:`, o la que se deriva del compás), ritmo
con puntillo (`>` `<`), grupos irregulares `(3`, `(p:q:r`, ligaduras
(también entre compases, con las alteraciones), alteraciones que valen
hasta la barra de compás, tonalidades con modos (`Dmix`, `Ador`...: se
convierten en la tonalidad con la misma armadura), cambios `[K:]` `[M:]`
`[L:]` `[Q:]`, **repeticiones y casillas 1.ª/2.ª** desplegadas, el
compás **en anacrusa**, dinámicas, cifrado de acordes (en la pista
**Acordes**, como en MusicXML) y letra con varias estrofas. Cada voz es
una pista; las voces del mismo pentagrama (`%%score (S A)`) van en una
sola pista, igual que los dos pentagramas del piano (`{RH | LH}`). El
instrumento viene de `%%MIDI program` (`%%MIDI channel 10` o
`clef=perc` para la batería), si no, del nombre de la voz. Las claves a
la octava, `transpose=` y `octave=` suenan a la altura real. Se ignoran
las notas de adorno, las partes (`P:`) y los adornos que no cambian el
sonido.

## 10bis. Importación de audio (voz/micrófono/archivo)

Menú **Pista → Importar en esta pista → Audio → notación (micrófono o archivo)...** (también
desde el menú **⋯** de la pista, opción «Importar audio → notas...», y como
«Importar audio (en este pattern)» en el diálogo **Componer →
Gestionar biblioteca de patterns**, para capturar directamente un pattern
reutilizable en lugar de una pista): convierte una idea musical captada con
el micrófono o desde un archivo de audio (`.wav`/`.mp3`/`.m4a`)
directamente en notación de texto, que se inserta en la pista (o en el
cuerpo del pattern) tras una vista previa del texto y una escucha
opcional.

- **Fuente**: botón de grabación (Start/Stop) desde el micrófono, o arrastra
  un archivo a la zona correspondiente (arrastrar y soltar) o usa «Examinar
  archivos...». Si grabas con el **Metrónomo** activado, el clic vuelve a
  empezar junto con la grabación: el primer tiempo coincide con el inicio
  del archivo y la transcripción sigue al metrónomo (un silencio antes de
  la primera nota sigue siendo un silencio). Sin metrónomo, la
  transcripción empieza en la primera nota, sea cual sea el momento en que
  pulsaste Grabar. El micrófono requiere
  `libportaudio2` instalado en el sistema en Linux (ver la sección
  Instalación); los archivos mp3, m4a, flac y ogg los lee el decodificador
  de Qt Multimedia, ya incluido en PySide6 (o `ffmpeg`, si el PySide6 de la
  distribución no lo incluye). Si falta algo, el diálogo lo indica con un
  mensaje explícito en lugar de fallar en silencio.
- **Cuantización**: selector con Off, 1/4, 1/8, 1/16 (predeterminado),
  1/32, más una casilla «Ternario» (tresillos 8T/16T) habilitada solo para
  1/8 y 1/16. «Off» no introduce un nuevo tipo de timing libre: usa
  internamente una rejilla muy fina (1/64), por debajo del umbral de
  cuantización perceptible, sin salir de la sintaxis normal `N:`. La última
  combinación usada se recuerda al volver a abrir el diálogo.
- **Modo de análisis**: Melódica (detección de altura, para la voz o
  instrumentos que tocan una nota cada vez: los acordes no se reconocen) o
  Percusiva (detección de transitorios para batería/beatbox, clasificados
  automáticamente como `kick`/`snare`/`hihat`). Se rellena según el
  instrumento de la pista actual, pero siempre se puede cambiar a mano. En
  modo Percusiva la cuantización elegida también cuenta para la detección:
  dos golpes más cercanos que aproximadamente la mitad de una casilla de la
  rejilla se consideran un solo golpe (con 1/16 a 120 BPM, 75 ms), así que
  elige una rejilla al menos tan fina como las notas más rápidas que hayas
  tocado (1/8 para un charles en corcheas, 1/16 para las semicorcheas).
- **Algoritmos**: los ataques se detectan con SuperFlux (flujo espectral
  que no confunde el vibrato con una nota nueva), la altura con YIN;
  están escritos dentro de SoundText (en numpy), sin bibliotecas que
  instalar.
- **Parámetros avanzados de seguimiento de altura** (solo modo Melódica):
  permiten adaptar el reconocimiento a un audio concreto en lugar de
  conformarse con el resultado predeterminado — ajusta los valores, vuelve
  a pulsar «Convertir a SoundText» para reintentar con el mismo archivo, y
  repite hasta que el resultado te convenza:
  - **Frecuencia mínima**: automática (deducida de la extensión grave del
    instrumento de destino) o un valor en Hz elegido a mano.
  - **Ventana de análisis**: número de muestras por estimación — más amplia
    ayuda en bajos/notas graves pero empeora la resolución temporal
    (ataques/notas breves menos precisos).
  - **Paso de análisis (hop size)**: distancia en muestras entre una
    estimación y la siguiente — más pequeño da más resolución temporal pero
    un análisis más lento.
  - **Umbral de confianza**: confianza mínima para aceptar una estimación.
  - **Duración mínima de nota**: descarta las notas más breves que este
    umbral, casi siempre artefactos (onsets espurios muy juntos, típicos de
    un vibrato marcado).
  - **Restablecer valores estándar**: devuelve todo el panel a los valores
    predeterminados.
- **Fuente: voz/beatbox**: casilla que hay que activar cuando estás
  cantando/tarareando la parte (bajo, melodía...) o imitando la batería con
  la boca, en lugar de grabar el instrumento real. La voz humana tiene
  características acústicas distintas de las de un instrumento real:
  afinación menos estable nota a nota (se fragmenta fácilmente en notas
  breves y erráticas) y, para la batería, ninguna resonancia grave real como
  la de un bombo (el tracto vocal es físicamente demasiado corto para
  producirla). Con la casilla activada: en la parte melódica no se amplía la
  ventana de análisis a la extensión grave del instrumento de destino
  (inútil si de todos modos estás cantando en tu propia tesitura, y
  perjudicial para la resolución temporal); en la batería los umbrales
  kick/snare/hihat se recalibran para un «bum» hecho con la boca en lugar de
  un bombo real.
- **Conversión**: el botón «Convertir a SoundText» analiza el audio en
  segundo plano (con una barra de progreso; «Cancelar» lo interrumpe y
  puedes reintentar enseguida con otros parámetros) y muestra el resultado
  en una vista previa con resaltado de sintaxis, antes de una posible
  inserción; el texto generado siempre se valida y nunca se inserta si
  resultara sintácticamente inválido.
- **Vista previa editable**: una vez terminada la conversión, la vista
  previa deja de ser de solo lectura: puedes corregir a mano una nota
  equivocada o probar una alternativa directamente en el texto, antes de
  confirmar. «Escuchar vista previa» reproduce siempre el contenido ACTUAL
  del editor (incluidos los cambios hechos a mano, no el texto original
  generado por el análisis); si los cambios rompen la sintaxis, tanto
  «Escuchar vista previa» como Ok señalan el error en lugar de continuar.
  Una nueva conversión (archivo nuevo, otro algoritmo de altura, etc.)
  sobrescribe cualquier cambio manual todavía no confirmado.
- **Escuchar vista previa**: el botón «▶ Escuchar vista previa» (con
  «■ Stop» al lado), habilitado tras una conversión correcta, reproduce el
  contenido actual de la vista previa con el instrumento de destino antes
  de confirmar con Ok — útil para comprobar de oído la conversión (o tu
  propia variante) antes de sustituir el contenido de la pista/del pattern.

Nota sobre la calidad del reconocimiento: la detección de las notas
melódicas segmenta el audio con un detector de ataques específico (fiable
incluso en el registro grave y en las transiciones «legato» típicas del
canto, sin silencio entre una nota y otra) y estima la altura de cada nota
con la mediana de las medidas del intervalo — más robusta frente al vibrato
y a las pequeñas imprecisiones de afinación de una voz no profesional que
una única medida instantánea. Cada nota termina cuando el sonido se apaga
(no necesariamente en el ataque siguiente), así que las notas separadas
dejan silencios; la misma nota tocada varias veces seguidas (típica del
bajo) sigue siendo una serie de notas distintas, incluso sin silencio entre
ellas, mientras que una nota sostenida con vibrato o trémolo sigue siendo
una sola nota. La dinámica es relativa: la nota (o el golpe) más fuerte de
la grabación se convierte en `110@` y las demás bajan en proporción, en
pasos de 10, de modo que incluso una grabación a bajo volumen suena llena y
el texto no se llena de pequeños cambios de `@`. Para las notas más graves
(p. ej. bajo), la ventana de análisis se amplía automáticamente según la
extensión mínima del instrumento de destino, para una estimación de altura
más precisa (no afecta a la detección del ataque, que se gestiona aparte).
La clasificación percusiva automática solo reconoce `kick`/`snare`/`hihat` a
partir del espectro del «cuerpo» del golpe (justo después del transitorio de
ataque; no tom/crash/ride/hihat_open, poco fiables sin un modelo
específico); el texto generado sigue siendo editable a mano como cualquier
otro token. Los umbrales del modo «voz/beatbox» son una estimación razonada
basada en el comportamiento acústico del tracto vocal, no calibrada con
grabaciones reales: si los resultados no son satisfactorios, el script
`diagnose_audio.py` (en la carpeta del programa) permite inspeccionar los
datos en bruto que usa la clasificación sobre una grabación tuya, para una
calibración específica en lugar de a base de pruebas; corregir a mano el
texto generado siempre sigue siendo posible.

## 10ter. Tocar con el teclado (teclado del ordenador o teclado MIDI)

Menú **Pista → Tocar con el teclado en esta pista...** (también como opción
«Tocar con el teclado...» del menú **⋯** de la pista, y como «Tocar con el
teclado (en este pattern)» en el diálogo **Componer → Gestionar
biblioteca de patterns**): graba una interpretación tocada en directo con
el teclado del ordenador — usado como si fuera un pequeño instrumento
musical — y la convierte en notación, con el mismo flujo final (vista
previa editable, «Escuchar vista previa», Ok/Cancelar) que el diálogo de
importación de audio (sección 10bis), del que es el equivalente
«instrumento tocado en directo» en lugar de «audio grabado/cargado».

- **Disposición del teclado** (distribución italiana): tres filas de 12
  teclas cada una, cada una una octava por encima de la anterior,
  recorridas cromáticamente a partir de do — fila de números (`1`...`0`,
  `'`, `ì`) en la octava elegida con el selector «Octava» del diálogo, fila
  `Q`...`P`, `è`, `+` una octava por encima, fila `A`...`L`, `ò`, `à`, `ù`
  dos octavas por encima. La leyenda exacta (con la octava real de cada
  fila) siempre está visible en el diálogo.
- **Independencia del idioma del teclado**: las notas (las tres filas de
  arriba) y la fila de calidades de acorde (`Z X C V B N M , . /`, sección
  siguiente) están ligadas a la POSICIÓN física de la tecla pulsada, no al
  carácter que produce — si cambias el idioma/la distribución del sistema
  (p. ej. de italiano a español/US/alemán), las mismas teclas físicas siguen
  tocando las mismas notas, aunque el carácter impreso en la tecla (o el
  que produce al escribir en otro sitio) sea otro. Cubre 45 de las 46 teclas
  implicadas: la única excluida es la última tecla de la fila `A`...`L` (la
  que produce `ù` en la distribución italiana — una tecla «extra» de las
  distribuciones ISO europeas sin equivalente único en un teclado US, cuya
  posición física exacta no se puede determinar de forma fiable en todas
  las distribuciones). Aun así, para esa tecla hay una alternativa:
  **Intro** (tanto la principal como la del teclado numérico) toca siempre
  la misma nota que `ù`, sea cual sea la distribución activa — Intro no es
  una tecla de carácter, así que su posición ya es de por sí independiente
  de la distribución. Verificado en Linux (X11 y Wayland); en Windows y
  macOS se basa en los mismos estándares documentados, pero no se pudo
  verificar de forma interactiva durante el desarrollo — si alguna tecla
  resultara fuera de sitio en esas plataformas, avísanos.
- **Acordes al vuelo**: manteniendo pulsada una tecla de la fila
  `Z X C V B N M , . /` junto con la tecla de nota (cualquiera de las tres
  filas de arriba) se toca el acorde correspondiente en lugar de la nota
  suelta:

  | Tecla | Calidad | Intervalos |
  |---|---|---|
  | `Z` | Mayor | 1 - 3 - 5 |
  | `X` | Menor | 1 - ♭3 - 5 |
  | `C` | 7ª de dominante | 1 - 3 - 5 - ♭7 |
  | `V` | Menor 7 | 1 - ♭3 - 5 - ♭7 |
  | `B` | Mayor 7 | 1 - 3 - 5 - 7 |
  | `N` | Suspendido (sus4) | 1 - 4 - 5 |
  | `M` | 9ª añadida (add9) | 1 - 3 - 5 - 9 |
  | `,` | Disminuido 7 | 1 - ♭3 - ♭5 - 𝄫7 |
  | `.` | Power Chord | 1 - 5 - 8 |
  | `/` | Bajo profundo | nota + octava inferior (no es un acorde de verdad) |

  La tecla de calidad hay que mantenerla pulsada ANTES/a la vez que la tecla
  de nota (pulsarla después no «actualiza» retroactivamente una nota ya
  tocada); si se mantienen pulsadas varias teclas de calidad a la vez, gana
  la última pulsada que siga activa. Como las notas, esta fila no depende de
  la disposición elegida (Cromática/Escala de la tonalidad/Jankó): funciona
  igual en cualquier modo.
- **Teclas de interpretación**:
  - `Bloq Mayús` (**Sustain**, mantenida): la nota/el acorde sigue sonando
    y su duración en la pista grabada sigue abierta incluso después de
    soltar la tecla de nota, hasta que se suelta también `Bloq Mayús` — útil
    para acordes sostenidos mientras ya pulsas la nota siguiente. Nota: el
    LED de Bloq Mayús del teclado puede encenderse/apagarse igualmente con
    cada pulsación (depende del sistema/controlador): no afecta al
    funcionamiento, es solo un efecto secundario inofensivo.
  - `Alt izquierda` (**Strumming**, mantenida): al pulsar una tecla de nota
    con un acorde activo (fila de calidades), las notas del acorde ya no
    empiezan todas a la vez sino en una sucesión rapidísima (unos 20 ms
    entre una y otra), como un rasgueo de guitarra — siguen sonando todas
    hasta que se suelta la tecla de nota (solo se escalona el ataque, no el
    final).
  - `Mayús izquierda` (**Bending**, mantenida): imita un bend real de
    guitarra en una nota suelta — en directo se oye la nota subir
    gradualmente un tono entero (una rampa de ~120 ms, no un salto brusco)
    y, al soltar, volver a bajar igual de gradualmente antes de detenerse
    (~80 ms), igual que al soltar una cuerda estirada. En la pista grabada
    se captura como un portamento/slide real (misma sintaxis que
    `c*4>d*4`), que se reproduce/exporta a MIDI con un pitch bend continuo,
    no como dos notas distintas. Solo se aplica de esta forma a una nota
    suelta (sin ningún acorde de la fila de calidades ni bajo profundo
    activos, y no junto con el Arpegiador): en un acorde, o con el
    Arpegiador activo, recurre a un desplazamiento fijo más sencillo de 2
    semitonos aplicado enseguida a todas las notas.
  - `Ctrl izquierda` (**Inversión**, mantenida): sube una octava la nota
    más grave del acorde (1ª inversión), para enlaces armónicos más
    fluidos. Solo se aplica a los acordes (fila de calidades activa), no a
    las notas sueltas.
  - `Tab` (**Piano/Forte**): cambia la dinámica de las notas tocadas a
    partir de ese momento — activo = Piano (velocity 60), inactivo = Forte
    (velocity 110, estado inicial). A diferencia de las demás teclas de
    interpretación, no hay que mantenerla pulsada: una pulsación cambia el
    estado.
  - **Barra espaciadora** (**Arpegiador**, mantenida): cada tecla de nota
    pulsada A PARTIR DE ESE MOMENTO (una ya tocada antes de pulsar la barra
    sigue sonando normalmente, sin arpegiarse retroactivamente) entra en un
    grupo compartido cuyas alturas se tocan de una en una, en ciclo
    continuo, a semicorcheas del tempo del proyecto — manteniendo pulsadas
    varias teclas de nota (o un acorde con la fila de calidades) se
    oye/graba un arpegio que recorre todas sus notas. El grupo se actualiza
    en directo si se añaden/quitan teclas de nota mientras la barra sigue
    pulsada.

  Todas las teclas de interpretación que se mantienen pulsadas (Sustain/
  Strumming/Bending/Inversión/Arpegiador) hay que mantenerlas ANTES o a la
  vez que la tecla de nota: pulsarlas después no tiene efecto retroactivo
  sobre una nota que ya está sonando.

  Nota técnica: Qt no distingue de forma portable la tecla izquierda de la
  derecha en Ctrl/Alt/Mayús, así que responden a Ctrl/Alt/Mayús en general
  (cualquier lado), no solo a la tecla izquierda descrita arriba.
- **Pista de percusión**: si el instrumento de destino es de percusión, las
  tres filas físicas (números, Q, A — las mismas que se usan para las notas,
  ver arriba) tocan en su lugar los 36 identificadores de percusión
  listados en la sección 6, en el mismo orden en que aparecen en la leyenda
  del diálogo (que muestra en pantalla qué tecla produce qué sonido), sin
  octava.
- **Respuesta sonora inmediata**: mientras grabas o pulsas «Tocar» (prueba
  sin grabar), cada tecla pulsada se oye enseguida, sintetizada en tiempo
  real con el instrumento de destino — a diferencia del resto de la
  reproducción de la aplicación, siempre offline (ver sección 12), aquí
  hace falta una latencia mínima. Si la pista tiene un instrumento plugin
  (instrumento SFZ interno, LV2 o VST3), las teclas las toca ese, con el
  sonido que tendrá la pista; el instrumento empieza a cargarse al abrir el
  diálogo y, si no se abre, se usa el SoundFont (el diálogo lo indica). Si la biblioteca FluidSynth o un SoundFont no están
  disponibles, puedes grabar/tocar de todos modos, simplemente sin oír las
  teclas (el diálogo lo indica).
- **Tempo, Compás, Metrónomo y Cuantización**: mismos controles y mismo
  significado que en el diálogo de importación de audio (sección 10bis) —
  el metrónomo (sección 12.5) es especialmente útil aquí para tocar a tempo
  antes de la cuantización.
- **Tonalidad**: muestra la tonalidad del proyecto (sección 2.7bis) nada más
  abrir el diálogo, y se puede cambiar directamente desde aquí — es el mismo
  campo `project.key` de la barra de herramientas principal (no una copia):
  cambiarla en el diálogo se refleja también en la barra de herramientas al
  cerrar el diálogo, y viceversa. Cambiarla actualiza enseguida la
  disposición «Escala de la tonalidad» (ver abajo), si está activa.
- **Disposición**: selector de la distribución de las teclas de nota,
  desactivado si el instrumento es de percusión (la percusión usa siempre
  las teclas `1`-`9`). Se puede cambiar incluso con una grabación o una
  prueba en curso, como la Octava. Opciones disponibles:
  - **Cromática** (predeterminada): el comportamiento descrito arriba, 12
    semitonos por fila, 3 octavas en total.
  - **Escala de la tonalidad (diatónica/pentatónica/blues)**: requiere una
    tonalidad fijada en la barra de herramientas principal (sección 2.7bis)
    — si no está fijada (o no es válida), vuelve automáticamente a la
    cromática, sin bloquear la selección. Cada fila de teclas recorre solo
    las notas de la escala elegida en lugar de las 12 cromáticas, de modo
    que las teclas siempre suenan «en la tonalidad», útil para improvisar
    sin tener que elegir de oído las notas correctas: la **diatónica** usa
    las 7 notas de la escala mayor o menor natural de la tonalidad; la
    **pentatónica** sus 5 notas mayores o menores (más «segura» para
    improvisar, es casi imposible tocar una nota desafinada); la **blues**
    las 6 notas de la escala de blues (pentatónica menor + quinta disminuida
    de paso), siempre las mismas desde la tónica independientemente del
    modo mayor/menor. Cuanto más corta es la escala, más octavas cubre el
    teclado con las mismas 12 teclas por fila (la diatónica llega a ~3,6
    octavas, la blues a ~3,8, la pentatónica a ~4,2).
  - **Jankó (isomorfa)**: distribución por tonos enteros alternados entre
    las filas (la fila de números y la fila A tocan las mismas notas, la
    fila Q las notas intermedias un semitono por encima), independiente de
    la tonalidad: una forma de acorde/intervalo dada suena siempre igual en
    cualquier parte del teclado, cómoda para quien ya la conoce de otros
    instrumentos/programas. Cubre 2 octavas completas (menos que la
    cromática): es el precio del isomorfismo, no un defecto.
- **«Escuchar también las demás pistas» (respeta Solo/Mute)**: casilla
  opcional (desmarcada por defecto). Si está marcada, tanto mientras tocas
  en directo (Grabar/Tocar) como mientras vuelves a escuchar la vista
  previa grabada, se oyen también las demás pistas del proyecto, con el
  mismo estado Solo/Mute que tengan en ese momento en el mezclador — útil
  para tocar o valorar la nueva parte en el contexto del arreglo en lugar
  de aislada. La propia pista de destino nunca se duplica: si el diálogo se
  abrió para una pista ya existente, su contenido actual queda excluido de
  la escucha de fondo, para que no se superponga a lo que estás
  grabando/escuchando en su lugar. Si no está marcada: el comportamiento de
  siempre, solo se oye el instrumento actual. La casilla se desactiva
  durante la propia grabación/prueba (hay que decidirlo antes de pulsar
  Grabar o Tocar).
- **Grabar** inicia/detiene la captura de la interpretación; **Tocar** la
  prueba sin grabar nada. Al detener la grabación se genera la vista previa
  de texto cuantizada, editable y reproducible como en la importación de
  audio, antes de confirmar con Ok. En la pista (a diferencia de los
  patterns, donde siempre sustituye el cuerpo) el resultado se añade al
  final del contenido ya presente en lugar de sobrescribirlo, para no
  perder música escrita a mano o importada antes.

### Teclado MIDI

En el mismo diálogo se puede tocar con un **teclado MIDI** de verdad
(conectado por USB o con una interfaz MIDI), junto con el teclado del
ordenador o en su lugar:

1. conecta el teclado **antes** de abrir el diálogo (si lo conectas
   después, pulsa **⟳** junto al menú **Teclado MIDI**);
2. en el menú **Teclado MIDI** elige el teclado: con un solo teclado
   conectado ya está elegido, y SoundText recuerda el último usado;
3. pulsa **Grabar** (o **Tocar**, para probar) y toca. Como con el teclado
   del ordenador, las notas solo cuentan mientras Grabar o Tocar están
   activos.

En comparación con el teclado del ordenador:
- **dinámica real**: la velocity de cada tecla (con cuánta fuerza la
  pulsas) se convierte en el `@` de la nota;
- **acordes** tocados directamente, una tecla por nota (la fila de acordes
  al vuelo queda para el teclado del ordenador);
- **pedal de sustain**: mantiene las notas como la tecla de sustain; la
  duración grabada llega hasta que se suelta el pedal;
- **rueda de pitch bend**: se oye en directo; si durante una nota sube o
  baja al menos un semitono, la nota se graba como slide (`a*4>b*4`) hacia
  la altura alcanzada (recorrido estándar ±2 semitonos);
- **percusión**: en una pista de batería las notas siguen el mapa General
  MIDI (36 bombo, 38 caja, 42 charles cerrado, 46 charles abierto...), como
  los pads de los teclados y las baterías electrónicas; las notas fuera del
  mapa se ignoran;
- el **arpegiador** (barra espaciadora mantenida en el teclado del
  ordenador) arpegia también las notas del teclado MIDI.

Hace falta el paquete de Python **python-rtmidi** (está en los requisitos:
los scripts de instalación ya lo instalan; a mano, `pip install
python-rtmidi`). Si falta, o si el sistema MIDI no responde, el menú está
desactivado y al lado se indica el motivo. Si el teclado no aparece en la
lista: comprueba el cable y que esté encendido, y pulsa **⟳**; en Linux
`aconnect -l` lista los dispositivos MIDI que ve el sistema. Un teclado
abierto por otro programa (por ejemplo un secuenciador) puede aparecer
ocupado en Windows: cierra el otro programa.

## 10quater. Pistas de audio (voz, guitarra, teclado grabados)

Además de las pistas con notación, una canción puede contener **pistas de
audio**: archivos de audio reales (una voz grabada con el micrófono, una
guitarra eléctrica o un teclado conectados con un jack a la interfaz de
audio) que suenan junto con las demás pistas. A diferencia de la
importación de audio (10bis), el archivo **no se convierte en notas**: se
oye tal cual.

Una pista de audio se llena de dos formas: **grabando** directamente en
SoundText mientras suena el resto de la canción (ver «Grabar» más abajo), o
**importando** archivos grabados con otro programa.

- **Crear una pista de audio**: **+ Añadir pista → Pista de audio...**, o
  menú **Pista → Añadir → Pista de audio...**. En su cabecera aparece como
  «Audio», con Volumen/Pan/Mute/Solo como las demás (volumen 100% = nivel
  original del archivo, hasta 200% ≈ +6 dB).
- **Importar un archivo**: menú **Pista → Importar en esta pista → Archivo de audio como clip...** (o **⋯ → Importar archivo de audio...** en la pista de audio)
  añade el archivo como **clip** al final de la pista. En la vista
  Estructura de la canción: doble clic en un punto vacío de la fila, o clic
  derecho → **Importar archivo de audio aquí...** para colocarlo en un punto
  preciso. Los `.wav` se leen siempre (incluso en 32 bits float); mp3, m4a,
  flac, ogg y aiff los lee el decodificador de Qt Multimedia incluido en
  PySide6 (o `ffmpeg`, si está), y se remuestrean a 48 kHz sin pérdidas en
  los agudos.
- **Clips en la vista Estructura de la canción**: cada clip es un box con la
  forma de onda, tan ancho como la parte del archivo que suena. Se arrastra
  como los boxes de notación (ajustándose al tiempo); doble clic para
  cambiarle el nombre; clic derecho para Play (vista previa solo del clip),
  Cambiar nombre, **Ganancia del clip (dB)**, Duplicar, Cortar/Copiar/Pegar
  (un clip de audio solo se puede pegar en una pista de audio) y Eliminar.
  Todo se deshace con Ctrl+Z.
- **Recortar el inicio y el final**: lleva el ratón a un borde del box (el
  cursor se convierte en ↔) y arrástralo. El audio se queda donde está en
  el tiempo: solo se oculta (o se recupera) el inicio o el final del
  archivo. El recorte se ajusta a la semicorchea (1/4 de tiempo);
  manteniendo pulsado **Mayús** es libre. Arrastrando el borde izquierdo
  hacia la izquierda se recupera también el audio grabado durante la cuenta
  atrás (útil para una nota de anacrusa tocada antes de tiempo). Para
  valores exactos: clic derecho → **Recorte preciso (segundos)...**. El
  archivo nunca se modifica.
- **Dividir un clip**: clic derecho en el punto donde dividirlo → **Dividir
  aquí**: se convierte en dos clips consecutivos del mismo archivo, que se
  pueden mover, recortar o eliminar por separado (por ejemplo para quitar un
  error en mitad de una toma).
- **Convertir en notación...** (clic derecho en un clip): convierte en notas
  la parte del clip que suena, con el mismo motor que «Importar audio»
  (10bis), en una **nueva pista** con el instrumento
  elegido (propuesto según lo que hayas grabado: guitarra, teclado, voz) y
  un box que empieza donde empieza el clip. Funciona bien con partes
  monofónicas (voz, línea de guitarra o de bajo); el clip de audio se
  mantiene.
- **En el editor clásico** una pista de audio muestra, en solo lectura, la
  lista de sus clips: las acciones sobre la notación (Generar, Tocar con el
  teclado, Importar MIDI, Congelar acordes, Exportar MIDI) no valen para las
  pistas de audio y lo explican con un mensaje.
- **Tempo**: el audio no se estira. Un clip queda anclado al tiempo en el
  que empieza pero dura siempre los mismos segundos: si cambias el BPM
  después de colocarlo, la barra de estado te lo recuerda.

### Grabar

Botón rojo **●** en la cabecera de la pista de audio, menú **Pista → Grabar
en la pista de audio...** (Ctrl+R), o en la vista Estructura de la canción
clic derecho en la fila de la pista → **Grabar desde aquí...** (empieza en
ese punto). Se abre el diálogo de grabación:

- **Interfaz de audio**: la entrada desde la que grabar (en Windows
  aparecen primero los controladores de baja latencia, ASIO y WASAPI). Se
  recuerda.
- **Qué estás grabando**: Voz/micrófono, Guitarra o bajo (jack), Teclado
  (salida de línea). Elige la entrada más probable y explica qué ajustar en
  la interfaz: alimentación phantom +48V para un micrófono de condensador,
  entrada INST/Hi-Z para la guitarra (se graba el sonido limpio, sin
  amplificador), entradas 1+2 en LINE para un teclado estéreo.
- **Entrada**: una entrada mono (1, 2, ...) o un par estéreo (1+2). El tipo
  de fuente y la entrada quedan guardados en la pista.
- **Nivel**: el medidor se mueve en cuanto se abre el diálogo: ajusta la
  ganancia en la interfaz de audio para que las partes más fuertes lleguen
  a unos -12/-6 dB sin encender el indicador rojo (saturación).
- **Empezar desde**: posición actual, inicio del bucle A (si está fijado) o
  inicio de la canción.
- **Cuenta atrás** (0-4 compases de clic antes de que empiece la canción) y
  **Metrónomo durante la toma**. El clic sigue incluso después del final de
  la canción, así que también se puede grabar en una canción todavía vacía.
- **Escuchar los clips que ya hay en esta pista**: desmárcala para repetir
  una parte sin oír la toma anterior.
- **Compensación de latencia**: la latencia declarada por la interfaz ya se
  compensa; si aun así la toma queda retrasada respecto a la canción,
  aumenta este valor (adelantada: redúcelo). Se recuerda para cada
  interfaz. **Calibrar...** lo mide solo: conecta con un cable una salida de
  la interfaz a la entrada elegida (o acerca el micrófono a los altavoces),
  SoundText toca 8 clics, los graba y fija el retardo medido. Basta con
  hacerlo una vez por interfaz de audio (y cada vez que cambies los ajustes
  de buffer/latencia del controlador).

**● Grabar** prepara la base (la canción como en la reproducción; sin
SoundFont, solo las pistas de audio y el metrónomo), hace la cuenta atrás y
graba hasta que pulses **■ Stop**. El diálogo muestra la duración y el pico
de la toma (y avisa si ha saturado): **Conservar la toma** la añade a la
pista como clip en el punto de partida; **Grabar** de nuevo la sustituye.
Si la toma se superpone a clips que ya existen, SoundText pregunta si
eliminarlos.

Para oírte mientras tocas usa la **monitorización directa** de la interfaz
de audio (rueda o botón «direct monitor»): no tiene retardo. SoundText solo
envía la canción a los auriculares. El archivo de la toma contiene también
la cuenta atrás, oculta por el recorte inicial del clip (arrastrando el
borde izquierdo se puede recuperar).

### Dónde van los archivos

Las tomas y los archivos importados (de los que SoundText hace una copia a
48 kHz, la misma frecuencia que la reproducción: el original nunca se toca)
van a la carpeta **`<NombreProyecto>_audio/`**, junto al archivo `.st`. Si
el proyecto todavía no se ha guardado, van a una carpeta temporal y se
mueven a la carpeta del proyecto al guardarlo por primera vez. **Guardar
como** copia los archivos de audio en la carpeta del nuevo proyecto. Para
llevar un proyecto a otro ordenador, copia juntos el archivo `.st` y su
carpeta `_audio`.

En el archivo `.st` un clip se escribe así (ruta relativa al archivo):

```
Audio Voz "Estrofa" |8:
  file="Cancion_audio/voz.wav" trim=0.35,0 gain=-2

Traccia Voz [Audio]:
```

`|8` es el tiempo de inicio; `trim` son los segundos que se saltan al
principio y al final del archivo, `gain` la ganancia del clip en dB (ambos
opcionales). Si un archivo ya no se encuentra, el clip se queda en el
proyecto, dibujado en rojo, y no suena: clic derecho → **Localizar
archivo...** para indicarlo de nuevo.

### Exportar

- **Proyecto → Exportar → Mezcla de audio (WAV)...** exporta la canción tal
  como suena (pistas audibles, audio incluido) a un WAV de 48 kHz / 24 bits.
  Hace falta un SoundFont para las pistas con notas; una canción hecha solo
  de pistas de audio se exporta también sin él.
- **Pista → Exportar esta pista → WAV...**, o **clic derecho en el nombre de
  una pista → Exportar WAV (solo esta)...**, exporta a un WAV solo esa pista, con notación o audio, tal como sonaría en
  Solo (el Solo/Mute de las demás pistas no cuenta). Para las pistas con
  notación, el mismo menú tiene también **Exportar MIDI (solo esta)...**.
- **Pista → Exportar esta pista → WAV seco (para re-amping)...**, o el mismo
  comando con clic derecho en el nombre de la pista, exporta la pista **sin** cadena de efectos, sin
  reverb/chorus del sintetizador, con el pan en el centro y sin máster (el
  volumen se mantiene): es el sonido «limpio» para pasarlo por un simulador
  de amplificador externo (ver 8.6). El archivo empieza desde el inicio de
  la canción, así que al volver a importarlo al inicio de una pista de audio
  queda a tempo.
- **Exportar MIDI** contiene solo notas: las pistas de audio no están, y un
  mensaje lo recuerda.
- Al guardar y al exportar se propone como nombre de archivo el del
  proyecto (en las exportaciones de una sola pista, el de la pista), en la
  carpeta donde está guardado el proyecto.

## 11. Guardar el proyecto

El proyecto se guarda en el formato de texto nativo `.st` (legible y
editable también a mano), que incluye tempo, compás, patterns, pistas y las
definiciones de los instrumentos personalizados que se usen (ver 7.1), para
que el archivo sea autosuficiente y portable entre instalaciones distintas.
La biblioteca MIDI (`midi/`), en cambio, sigue siendo compartida a nivel de
instalación y no viaja dentro del archivo `.st`.

El título de la ventana muestra siempre el nombre del archivo abierto
(«SoundText — nombrearchivo.st»), incluso después de una importación MIDI
(«SoundText — nombrearchivo.mid»), para saber siempre de un vistazo en qué
proyecto estás trabajando.

## 12. Reproducción

El botón Play exporta un MIDI temporal. Si están disponibles `fluidsynth` y
un SoundFont, la síntesis se hace **offline** (render en un archivo WAV
temporal, que luego se reproduce con el mejor reproductor de audio
encontrado — en Linux `pw-play`, `paplay`, `aplay`, `ffplay` o `mpv`; en
macOS `afplay` (incluido en el sistema) o, si están instalados,
`ffplay`/`mpv`; en Windows `ffplay`/`mpv` si están instalados, y si no el
módulo `winsound` de la biblioteca estándar de Python, siempre disponible)
en lugar de en tiempo real: así se evitan los chasquidos/cortes debidos a
los underruns del controlador de audio, típicos de la síntesis MIDI en
tiempo real en PulseAudio/PipeWire, y se obtiene un resultado más limpio. Si
está disponible la biblioteca FluidSynth (SoundText la usa directamente),
este render offline usa una única instancia de fluidsynth **persistente**
durante toda la sesión, con el SoundFont cargado en memoria una sola vez en
lugar de en cada Play: una latencia de arranque mucho más baja (el coste de
cargar el SoundFont, incluso cientos de ms para un GM de decenas de MB, solo
se paga la primera vez), con la misma estrategia antichasquidos (el render
sigue siendo offline, no toca la salida de audio en tiempo real). Si el
render offline falla (con o sin la biblioteca), o no hay ningún
reproductor de WAV disponible, se recurre al binario CLI `fluidsynth` y
después a la reproducción de fluidsynth en tiempo real; si fluidsynth no
está disponible en absoluto, a `timidity` o `wildmidi`; y, a falta de todo,
al reproductor MIDI predeterminado del sistema (`xdg-open` en Linux, `open`
en macOS, apertura directa con el programa asociado en Windows).

Con la biblioteca FluidSynth **y** `sounddevice` (en requirements.txt)
instalados, la canción renderizada la reproduce directamente el
programa en lugar de un reproductor externo, y el render se **guarda en
memoria**: solo el primer Play (o el primero después de un cambio que
altera el sonido, como notas, mezclador o humanización) tiene que esperar a
la síntesis, mientras que pausa/reanudación y saltos vuelven a empezar al
instante. La posición que muestran la barra, el resaltado, el cabezal y el
metrónomo es la que lee el dispositivo de audio, así que se mantiene
alineada con lo que se oye.

### Saltar a un punto y repetir una sección (bucle A-B)

- **Salto**: haz clic en la barra de progreso de la barra de herramientas, o
  en la regla de compases de la vista Estructura de la canción. Si la
  canción está sonando, vuelve a empezar desde ahí; si está detenida o en
  pausa, el próximo Play empezará desde ese punto.
- **Bucle A-B** (menú **Reproducción → Bucle**): **Bucle: inicio (A) aquí**
  (`Ctrl+[`) y **Bucle: final (B) aquí** (`Ctrl+]`) fijan los dos extremos
  en el tiempo que se está reproduciendo (o en el punto de pausa/salto),
  redondeado al tiempo entero. Fijar B activa el bucle; **Repetir la
  sección A-B** (`Ctrl+L`) lo activa y desactiva sin perder A y B, **Borrar
  bucle** los pone a cero. La sección aparece como una franja de color en la
  regla de la Estructura de la canción. Se puede activar, mover o quitar el
  bucle incluso mientras la canción suena, sin interrupciones.
- El bucle requiere la reproducción directa descrita arriba (biblioteca
  FluidSynth + `sounddevice`): con los reproductores alternativos la canción no se
  repite, y un mensaje en la barra de estado lo indica.

### 12.1 Barra de progreso y resaltado del token en reproducción

Durante la reproducción, la barra de progreso (la fila de ancho completo
bajo la barra de comandos) muestra el tiempo transcurrido y la duración
total de la canción (p. ej. «00:42 / 01:30»). En la pista que se muestra en
el editor, el token que se está reproduciendo (nota, silencio, acorde,
bloque, o la referencia entera si es un `%pattern`/`&"midi"`) se resalta con
los colores invertidos respecto al tema (fondo claro, texto oscuro), para
seguir visualmente la ejecución línea a línea. El editor se desplaza
automáticamente cuando hace falta para mantener siempre visible el token
resaltado (no hace falta desplazarse a mano mientras escuchas), pero solo
cuando sale de la parte visible: no se desplaza continuamente nota a nota,
y no mueve el cursor de edición del usuario. Si cambias de pista durante la
reproducción, el resaltado pasa a la nueva pista seleccionada, siempre
sincronizado con el mismo tiempo transcurrido.

### 12.2 Cambios en el mezclador durante la reproducción

Mute, Solo, Volumen y Pan se pueden cambiar incluso con la canción sonando:
el programa reinicia automáticamente la reproducción desde la posición en
la que estaba (no desde el principio), aplicando enseguida los nuevos
ajustes. Se nota una breve interrupción en el momento del reinicio (la
canción hay que volver a sintetizarla con los nuevos ajustes), pero no hace
falta detener y volver a iniciar la reproducción a mano para oír el efecto
de un cambio en el mezclador.

**Si el sonido no te convence a pesar de un buen SoundFont**, ten en cuenta
que:
- **Sonidos → SoundFont → Mostrar el SoundFont en uso** indica exactamente qué
  motor y qué archivo `.sf2` se van a usar: si no muestra «fluidsynth
  persistente (biblioteca) + ...sf2» o «fluidsynth (CLI) + ...sf2», el
  programa está recurriendo en silencio a una alternativa de menor calidad
  (a menudo porque `fluidsynth` no está instalado, o no se ha encontrado
  ningún `.sf2`) — instala `fluidsynth` y comprueba el SoundFont desde ahí.
- Incluso con un buen SoundFont, **el sonido General MIDI tiene un límite
  intrínseco de realismo**: no está pensado para competir con bibliotecas de
  muestras profesionales, sino para una reproducción fiel y reconocible de
  la partitura. Un salto de calidad significativo requeriría muestras
  multi-velocity por instrumento (fuera del alcance de este motor basado en
  MIDI/GM estándar).

### 12.3 Elegir el SoundFont (p. ej. FluidR3_GM.sf2)

El programa busca un SoundFont, por orden de prioridad:

1. la ruta fijada a mano desde **Sonidos → SoundFont → Elegir SoundFont
   (.sf2)...** (guardada en el archivo de ajustes:
   `~/.config/soundtext/settings.json` en Linux,
   `%APPDATA%\SoundText\settings.json` en Windows,
   `~/Library/Application Support/SoundText/settings.json` en macOS);
2. la variable de entorno `SOUNDTEXT_SOUNDFONT`, si está definida;
3. algunas rutas habituales del sistema, entre ellas:
   - `~/.local/share/soundfonts/FluidR3_GM.sf2` (Linux)
   - `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora)
   - `/usr/share/soundfonts/FluidR3_GM.sf2` (Arch/CachyOS)
   - `%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` (Windows)
   - `~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (macOS)
   - `/opt/homebrew/share/soundfonts/FluidR3_GM.sf2` (macOS, Homebrew en
     Apple Silicon)

   La lista completa de las rutas buscadas en cada sistema está en la
   sección Instalación correspondiente, más abajo en esta guía.

Si has descargado `FluidR3_GM.sf2` en otro sitio (o quieres usar otro),
basta con seleccionarlo desde **Sonidos → SoundFont → Elegir SoundFont (.sf2)...**:
queda fijado para todas las reproducciones siguientes, en todos los
proyectos. **Sonidos → SoundFont → Mostrar el SoundFont en uso** indica qué archivo
se va a usar en este momento (y con qué motor/reproductor), y permite
comprobar al instante si el problema es de verdad el SoundFont o una
alternativa silenciosa. **Sonidos → SoundFont → Usar la detección automática del
SoundFont** elimina el ajuste manual y vuelve a la búsqueda automática.

### 12.4 SoundFonts distintos para cada instrumento

Además del SoundFont predeterminado (sección 12.3, usado para toda la
reproducción), puedes asignar un archivo `.sf2` distinto a un solo
instrumento — útil para usar un piano dedicado de buena calidad junto con
un banco genérico para el resto, o una batería distinta de todo el resto
del conjunto.

Desde **Sonidos → Gestionar instrumentos...**, selecciona un
instrumento de la lista (predefinido o personalizado: aquí la elección no
se limita a los personalizados) y usa el panel **SoundFont para el
instrumento seleccionado**:
- **Elegir SoundFont...** asigna un archivo `.sf2` a ese instrumento: se
  usará en lugar del predeterminado en cada pista que lo use, en cualquier
  proyecto.
- **Usar el predeterminado** quita la asignación y vuelve al SoundFont
  general.

La lista de instrumentos muestra una indicación (`· SoundFont: nombre.sf2`)
para los que tienen una sustitución activa.

**Límite**: solo funciona con el motor fluidsynth persistente
(la biblioteca FluidSynth, usada por defecto si está disponible — ver la sección 12
arriba): con las alternativas (CLI `fluidsynth`, `timidity`, `wildmidi`,
reproductor MIDI del sistema) la sustitución se ignora y se usa de todos
modos el SoundFont predeterminado para toda la reproducción. Con varios
instrumentos sustituidos a la vez, la reproducción requiere un render
separado para cada SoundFont implicado (que luego se combinan): las
canciones con muchos instrumentos asignados de forma distinta tardan, por
tanto, unos instantes más en empezar.

### 12.5 Metrónomo

El botón **Metrónomo** (icono de pirámide) de la barra de comandos hace
sonar un clic a tempo durante la reproducción del conjunto, sincronizado
con los posibles cambios de tempo/compás del proyecto (el mismo mapa que
usan la barra de progreso y los campos Tempo/Compás, ver 2.7); el mismo
control, con un clic a tempo/compás constantes, está también disponible en
el diálogo de importación de audio y en el diálogo «Tocar con el teclado»
(secciones 10bis y 10ter), útil para grabar/tocar a tempo.

El sonido y el volumen del clic se eligen en **Opciones → Metrónomo**: tres
preajustes de sonido (Clic, Pitido, Madera) y un control deslizante de
volumen (0-100%), que se aplican enseguida (incluso a un clic ya en marcha)
y se pueden probar en el momento con el botón «Prueba», sin necesidad de un
Ok/Cancelar aparte. Los archivos de audio del clic se sintetizan y se
guardan en caché la primera vez (sin dependencias adicionales), así que se
generan una sola vez por máquina.

### 12.6 Humanizar

La opción **Reproducción → Humanizar** (marcable) añade una pequeña
variación aleatoria al timing y a la velocity de las notas que se
reproducen, para un sonido menos mecánico que una rejilla perfectamente
cuantizada. La batería solo recibe la variación de velocity (un
desplazamiento de timing en un pattern de percusión tiende a sonar
«impreciso» más que «humano»); todos los demás instrumentos reciben ambas.
**Se puede activar/desactivar incluso durante la reproducción**: como un
cambio de Volumen/Pan, la reproducción se reinicia automáticamente desde la
posición actual con el nuevo ajuste aplicado.

La intensidad se ajusta en **Opciones → Humanizar** con un control
deslizante (0-100%, 50% por defecto), que se aplica enseguida (reinicia la
reproducción en curso, si Humanizar está activo). La variación **no usa una
semilla fija**: dos reproducciones seguidas con los mismos ajustes nunca
sonarán idénticas, igual que dos interpretaciones en directo del mismo
músico. Solo afecta a la reproducción/exportación MIDI (el render final en
ticks absolutos): el texto de la pista y la línea de tiempo «de rejilla» del
editor se quedan como están escritos, sin cambios.

## 13. Acerca de SoundText

El menú **Ayuda → Acerca de SoundText...** muestra el nombre y el número de
versión del programa, el autor (Sergio Scolaro) y la licencia (GPL-3.0),
junto con quién decodifica los archivos mp3/m4a/flac/ogg (el decodificador
de Qt Multimedia o `ffmpeg`, sección 10bis) con un
icono de verificación verde si está disponible, y una cruz gris si no: útil
para comprobar rápidamente la instalación sin tener que abrir un terminal.

### 13.1 Archivo de registro

Cuando algo no sale como se esperaba (la reproducción recurre a un motor de
menor calidad, un SoundFont no se carga, un error inesperado), SoundText lo
anota con los detalles técnicos en el archivo `soundtext.log` de la carpeta
de configuración (`~/.config/soundtext` en Linux, `%APPDATA%\SoundText` en
Windows, `~/Library/Application Support/SoundText` en macOS). **Ayuda →
Abrir el archivo de registro** lo abre directamente: es lo primero que
debes adjuntar si informas de un problema. Un error inesperado también se
muestra en una ventana, sin cerrar la aplicación.

## 14. Tecnologías, agradecimientos y licencias

### 14.1 Las tecnologías usadas

SoundText está escrito en **Python 3** y se apoya en estas bibliotecas y
estos programas:

| Componente | Para qué sirve en SoundText | Licencia |
|---|---|---|
| Python | el lenguaje del programa | PSF License |
| Qt 6 con PySide6 | la interfaz gráfica | LGPL-3.0 |
| NumPy | el cálculo sobre el audio: efectos, amplificador, perfiles NAM, análisis | BSD-3-Clause |
| FluidSynth | la síntesis de las notas con los SoundFonts (SoundText la usa directamente) | LGPL-2.1 |
| mido | lectura y escritura de archivos MIDI | MIT |
| python-rtmidi (RtMidi) | los teclados MIDI externos | MIT |
| sounddevice y PortAudio | la escucha y la grabación | MIT |
| pedalboard (Spotify) | la cadena de efectos y los plugins VST3 | GPL-3.0 |
| JUCE (dentro de pedalboard) | el motor de audio de pedalboard y el host VST3 | GPL-3.0 (en la forma que usa pedalboard) |
| VST3 SDK de Steinberg (dentro de pedalboard) | el formato de los plugins VST3 | GPL-3.0 en la versión incluida en pedalboard (las versiones más recientes del SDK han pasado a la licencia MIT) |
| lilv y LV2 | los plugins LV2 en Linux (biblioteca del sistema, opcional) | ISC |
| FFmpeg (dentro de Qt Multimedia) | la lectura de mp3, m4a, flac, ogg | LGPL-2.1 |
| ffmpeg (programa externo, opcional) | la lectura de archivos de audio si el PySide6 en uso no tiene el decodificador de Qt | LGPL-2.1 o GPL, según cómo se haya compilado |
| Neural Amp Modeler | el formato de los perfiles `.nam`: SoundText rehace el cálculo con NumPy | MIT (el proyecto NAM) |
| SoundFont FluidR3_GM | los sonidos General MIDI incluidos en las builds | MIT |

Algunos formatos e ideas vienen de estándares abiertos o de la literatura:
**General MIDI** y el archivo MIDI estándar, **MusicXML** (W3C Music
Notation Community Group) para la exportación de la partitura (10.1), el
algoritmo de **Krumhansl-Schmuckler** para reconocer la tonalidad, los
circuitos de los tone stacks Fender y Marshall para el amplificador (8.4).

Para construir y comprobar el programa hacen falta también **PyInstaller**
(las versiones portables; su licencia GPL-2.0 tiene una excepción por la
que no se extiende al programa empaquetado), **pytest** (las pruebas) y
**reportlab** (la guía en PDF).

### 14.2 Agradecimientos

SoundText existe gracias al trabajo, casi siempre voluntario, de quienes
han creado y mantienen los proyectos de código abierto en los que se apoya.
Estamos especialmente en deuda con:

- la comunidad de **FluidSynth**, que desde hace más de veinte años hace
  sonar los SoundFonts en todos los sistemas, y **Frank Wen**, autor del
  SoundFont **FluidR3_GM**;
- **The Qt Company** y la comunidad de **Qt for Python (PySide6)**;
- **Spotify** y los desarrolladores de **pedalboard**, y el equipo de
  **JUCE**, sobre el que está construido pedalboard;
- el **RISM Digital Center** y los desarrolladores de **Verovio**, que
  maqueta la partitura (Vista → Partitura);
- **Alain de Cheveigné** y **Hideki Kawahara** (algoritmo YIN) y
  **Sebastian Böck** y **Gerhard Widmer** (SuperFlux), cuyos artículos
  son la base del reconocimiento de notas a partir del audio;
- los autores de **mido**, de **RtMidi** (Gary P. Scavone) y de
  **python-rtmidi**, de **PortAudio** y de **sounddevice**;
- la comunidad de **NumPy**;
- **Steven Atkinson** y la comunidad de **Neural Amp Modeler**, junto con
  quienes capturan y comparten los perfiles de amplificadores (entre otros
  la colección de **pelennor2170** y el sitio **Tone3000**);
- **David Robillard** y la comunidad de **LV2** y **lilv**, y los autores
  de los plugins de **Ardour** y **Guitarix**;
- **David Fau Casquel** (BestPlugins), que publicó sus cajas IR con una
  licencia libre, y la comunidad de **Guitarix**, que las conserva;
- **Steinberg**, que abrió el formato **VST3**;
- quienes desarrollan plugins gratuitos y de código abierto, como
  **Surge XT**, y el **W3C Music Notation Community Group** por MusicXML.

Si usas SoundText y te resulta útil, la mejor manera de corresponder es
apoyar estos proyectos: informar de problemas, contribuir o hacer una
donación a los que la aceptan.

### 14.3 Licencias y límites a la distribución

Usar SoundText en tu propio ordenador, para cualquier fin (incluso
comercial, incluso para vender la música que hagas con él), **no tiene
límites**: las licencias de abajo solo afectan a quien **distribuye el
programa** a otros (copia la instalación, publica una build, lo vende o lo
incluye en otro producto). La música creada con SoundText es de quien la
crea: ninguna de estas licencias se aplica a las canciones, ni a los
archivos `.st`, MIDI, MusicXML o WAV producidos.

**La restricción principal: la GPL-3.0.** **pedalboard** (con JUCE) se
distribuye con la licencia **GNU GPL versión 3**. Un programa que lo
incluye, como las builds de SoundText, solo se puede distribuir en
las condiciones de la GPL-3.0:
- todo SoundText debe distribuirse con la **licencia GPL-3.0** (o una
  compatible), y quien lo recibe tiene los mismos derechos de usarlo,
  estudiarlo, modificarlo y redistribuirlo;
- junto con el programa (o a petición, según las reglas de la licencia)
  hay que poner a disposición el **código fuente completo** de la versión
  distribuida, incluidas las modificaciones;
- no se pueden añadir **restricciones**: nada de versiones de código
  cerrado, nada de prohibiciones de copia o de modificación, nada de
  sistemas que impidan instalar una versión modificada;
- se puede **vender** una copia o cobrar por la distribución, pero quien la
  compra puede después redistribuirla libremente.

Una versión **de código cerrado** de SoundText solo sería posible quitando
pedalboard (y por tanto la cadena de efectos y los plugins VST3),
sustituyéndolo, o comprando las licencias comerciales de los componentes
que las ofrecen (JUCE, Steinberg...).

**Las bibliotecas LGPL: Qt/PySide6 y FluidSynth.** Se pueden usar también
en programas no GPL, siempre que quien recibe el programa pueda
**sustituirlas por su propia versión**. Las builds portables de SoundText
las mantienen como archivos separados junto al ejecutable, así que la
condición se cumple. Hay que incluir el texto de la licencia LGPL y las
indicaciones sobre dónde obtener el código fuente de estas bibliotecas (por
ejemplo un enlace a la versión usada).

**Las licencias permisivas (MIT, BSD, ISC, PSF).** NumPy, mido, RtMidi,
PortAudio, sounddevice, lilv, el proyecto NAM y el SoundFont FluidR3_GM
solo piden **conservar los avisos de copyright y el texto de la licencia**
en la distribución.

**Marcas.** VST es una marca registrada de Steinberg Media Technologies
GmbH, y Qt de The Qt Company: los nombres se pueden citar para decir que el
programa admite esos formatos o usa esas bibliotecas, no para dar a
entender que SoundText es un producto suyo. El uso del logotipo VST tiene
reglas propias de Steinberg.

**Contenidos descargados y plugins de terceros.**
- Los **perfiles NAM recomendados** (Sonidos → Descargar → Descargar perfiles NAM
  recomendados) proceden de la colección de pelennor2170, con licencia
  GPL-3.0: SoundText los descarga en el ordenador del usuario, no los
  incluye en las builds. Quien los redistribuya debe respetar su licencia.
- Las **cajas IR recomendadas** (Sonidos → Descargar → Descargar cajas IR para
  los amplificadores NAM) son el BestPlugins Mega Pack 2 de David Fau
  Casquel, con licencia GPL v2 o posterior: SoundText también las descarga
  en el ordenador del usuario, junto con el texto de la licencia, y no las
  incluye en las builds.
- Los **plugins VST3 y LV2** (8.7) son programas de terceros, cada uno con
  su propia licencia, incluso de pago: SoundText los carga, pero no los
  incluye. Para distribuirlos junto con SoundText hace falta el permiso de
  sus autores.
- Los **SoundFonts** que elige el usuario tienen cada uno su propia
  licencia: antes de incluir en una distribución uno distinto de
  FluidR3_GM, hay que comprobarla.

**La licencia de SoundText.** SoundText (Copyright © 2026 Sergio Scolaro)
se distribuye con la licencia **GPL-3.0**: el texto está en el archivo
`LICENSE`. Los autores, las licencias y los textos completos de los
componentes de terceros están en `THIRD_PARTY_NOTICES.md` y en la carpeta
`licenses/`. Los scripts de build (versiones portables para Linux y
Windows, AppImage, instalador para Windows) los copian junto al programa, y
el instalador para Windows muestra la licencia durante la instalación.

**En la práctica, para quien distribuye una build de SoundText:**
1. dejar junto al programa `LICENSE`, `THIRD_PARTY_NOTICES.md` y la carpeta
   `licenses/` (los scripts de build lo hacen solos);
2. poner a disposición el **código fuente** de la versión distribuida (por
   ejemplo el repositorio, con la referencia exacta a la versión);
3. si se añade a la build un componente nuevo, añadir sus autores y su
   licencia en `THIRD_PARTY_NOTICES.md` y el texto en `licenses/`;
4. no incluir plugins, SoundFonts o perfiles de terceros sin haber
   comprobado que su licencia lo permite.

Estas indicaciones resumen las licencias de los componentes para ayudar a
orientarse: **no son asesoramiento jurídico**. Para una distribución
comercial o en un contexto particular conviene consultar a un experto en
licencias de software. Los textos completos de las licencias están en los
sitios web de los respectivos proyectos.

---

# Instalación en Linux

## Debian / Ubuntu y derivadas

```bash
sudo apt update
sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtmultimedia python3-pip fluidsynth fluid-soundfont-gm ffmpeg libportaudio2
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
Si `python3-pyside6.qtwidgets` no está disponible en tu versión de la
distribución, como alternativa:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo apt install fluidsynth fluid-soundfont-gm libportaudio2
python3 main.py
```
`libportaudio2` sirve para la escucha directa y el micrófono; `ffmpeg` solo
para leer mp3/m4a/flac/ogg si el PySide6 de la distribución no tiene el
decodificador de Qt Multimedia (con PySide6 instalado con pip, como en la
segunda forma, no hace falta). **Ayuda → Acerca de SoundText...** muestra
quién decodifica los archivos de audio.

## Fedora y derivadas (RHEL, Nobara, etc.)

```bash
sudo dnf install python3-pyside6 python3-pip fluidsynth fluid-soundfont-gm portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
Si `python3-pyside6` no está en los repositorios habilitados:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo dnf install fluidsynth fluid-soundfont-gm portaudio
python3 main.py
```
`ffmpeg` solo hace falta si el PySide6 del sistema no lee los mp3 (ver
arriba) y no está en los repositorios oficiales de Fedora: habilita
[RPM Fusion](https://rpmfusion.org/) y luego `sudo dnf install ffmpeg`, o
usa la segunda forma (PySide6 con pip).

## Arch Linux / CachyOS / Manjaro y derivadas

```bash
sudo pacman -S pyside6 python-mido fluidsynth ffmpeg portaudio
paru -S soundfont-fluid      # o bien yay -S soundfont-fluid (AUR)
pip install --user sounddevice numpy pedalboard
cd soundtext
python3 main.py
```
(El paquete oficial se llama `pyside6`, sin el prefijo `python-`.
`python-mido`, en cambio, está en los repositorios oficiales `extra`.
`portaudio` sirve para la escucha directa y el micrófono, `ffmpeg` solo si
el PySide6 del sistema no lee los mp3.)

## openSUSE

```bash
sudo zypper install python3-PySide6 python3-pip fluidsynth ffmpeg portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```

## Notas comunes

- Sin un SoundFont GM instalado, `fluidsynth` no produce sonido: comprueba
  que exista un archivo como `/usr/share/soundfonts/FluidR3_GM.sf2` (Arch)
  o `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora).
- Si no hay ningún sintetizador en el sistema, el programa exporta de todos
  modos MIDI estándar que se puede reproducir con cualquier otro
  reproductor.
- Los instrumentos personalizados se guardan en
  `~/.config/soundtext/instruments.json` y, por tanto, se comparten entre
  todos los proyectos del usuario en esa máquina.

---

# Instalación en Windows

```powershell
# 1) Python 3.10+ desde python.org (instalador oficial, marca "Add python.exe to PATH")
cd soundtext
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Síntesis de audio (fluidsynth)**: descarga los binarios de fluidsynth
para Windows desde la página oficial de versiones del proyecto
([github.com/FluidSynth/fluidsynth/releases](https://github.com/FluidSynth/fluidsynth/releases),
archivo `-win10-x64.zip`) y pon la carpeta `bin\` (contiene
`libfluidsynth-3.dll`) en el `PATH` del sistema, o copia su contenido en
la carpeta de SoundText: SoundText usa la biblioteca directamente (motor
persistente, por defecto) y `fluidsynth.exe` como alternativa. Otra opción, si tienes
[Chocolatey](https://chocolatey.org/):
```powershell
choco install fluidsynth
```

**SoundFont GM**: el sistema operativo no incluye ninguno (a diferencia de
muchas distribuciones Linux). Descarga un SoundFont GM (p. ej.
`FluidR3_GM.sf2`, disponible libremente) y selecciónalo desde
**Sonidos → SoundFont → Elegir SoundFont (.sf2)...** en el menú de la aplicación,
o ponlo en `%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` para la
detección automática.

**Importación de audio**: nada que instalar. Los archivos mp3/m4a/flac/ogg
los lee el decodificador de Qt Multimedia, ya incluido en PySide6; el
paquete pip `sounddevice` (en requirements.txt) graba con el micrófono y ya
incluye la biblioteca PortAudio para Windows. El reconocimiento de notas
también está escrito dentro de SoundText.

**Reproducción sin reproductores externos**: a diferencia de Linux, Windows
no trae de serie un reproductor de audio de línea de comandos; SoundText
detecta este caso y usa automáticamente el módulo `winsound` de la
biblioteca estándar de Python (sin dependencias adicionales) para
reproducir el render offline. **Sonidos → SoundFont → Mostrar el SoundFont en
uso** muestra siempre qué motor/reproductor está activo de verdad, útil
para comprobar la instalación. El botón **Stop** detiene correctamente la
reproducción con cualquier motor, incluido el último recurso (el
reproductor MIDI predeterminado del sistema, que se usa cuando no están
instalados ni fluidsynth ni un reproductor CLI): SoundText lo abre de forma
que siempre pueda terminarlo, en lugar de dejarlo como un proceso
desvinculado de la aplicación.

```powershell
python main.py
```

---

# Instalación en macOS

```bash
brew install python@3.12 fluidsynth portaudio   # portaudio opcional, ver abajo
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

**Síntesis de audio (fluidsynth)**: se instala con Homebrew junto con el
resto (`libfluidsynth` acaba en `/opt/homebrew/lib` en Apple Silicon o en
`/usr/local/lib` en Intel, ya en la ruta de búsqueda de bibliotecas del
sistema: SoundText la encuentra solo, también en Apple Silicon, sin
configuración adicional).

**SoundFont GM**: como en Windows, macOS no incluye ninguno de serie.
Descarga un SoundFont GM (p. ej. `FluidR3_GM.sf2`) y selecciónalo desde
**Sonidos → SoundFont → Elegir SoundFont (.sf2)...**, o ponlo en
`~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (o, si lo instalaste con
Homebrew, en `/opt/homebrew/share/soundfonts/`) para la detección
automática.

**Importación de audio**: los archivos mp3/m4a/flac/ogg los lee el
decodificador de Qt Multimedia, ya incluido en PySide6 (nada de `ffmpeg`
que instalar); el paquete pip `sounddevice` graba con el micrófono (ya
incluye PortAudio, pero `brew install portaudio` nunca está de más si el
paquete pip diera problemas al compilar). El reconocimiento de notas
también está escrito dentro de SoundText, nada que compilar.

**Reproducción**: macOS incluye de serie `afplay` (reproductor de audio de
línea de comandos incluido en el sistema operativo, sin instalación), que
se usa automáticamente para reproducir el render offline — la misma
estrategia que ya se usa en Linux con `paplay`/`pw-play`. **Sonidos → SoundFont → Mostrar el SoundFont en uso** muestra siempre qué motor/reproductor está
activo de verdad.

**Permisos del micrófono**: la primera vez que grabas con el micrófono,
macOS pide permiso de acceso al micrófono para el terminal/IDE desde el que
lanzaste `python3 main.py`: hay que concederlo en **Ajustes del Sistema →
Privacidad y seguridad → Micrófono**, si no, la grabación falla en
silencio.
