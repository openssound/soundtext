# Guide de l'utilisateur — SoundText

## Index par sujet

Trouvez ici le sujet qui vous intéresse et allez à la section indiquée (les numéros sont ceux des titres de ce guide).

| Sujet | Section |
| --- | --- |
| [La fenêtre du programme, barre de commandes, vues](#1.0) | [1.0](#1.0) |
| [Chercher une commande (Ctrl+K) et raccourcis clavier](#1.0bis) | [1.0bis](#1.0bis) |
| [Annuler / Rétablir](#1.2) | [1.2](#1.2) |
| [Sauvegarde automatique et récupération](#1.2bis) | [1.2bis](#1.2bis) |
| [Langue de l'interface](#1.3) | [1.3](#1.3) |
| [Écrire notes, accords, silences, durées, octaves, dièses et bémols](#2) | [2](#2) |
| [Voicings d'accords et accords avec basse alternative (slash)](#2.8) | [2.8](#2.8), [2.9](#2.9) |
| [Répétitions et triolets / quintolets](#2.1) | [2.1](#2.1), [2.1bis](#2.1bis) |
| [Slides (pitch bend) et pédale de sustain](#2.3) | [2.3](#2.3), [2.4](#2.4) |
| [Nuances, crescendo et diminuendo](#2.5) | [2.5](#2.5) |
| [Changements de tempo (accelerando, ritardando) et de métrique](#2.6) | [2.6](#2.6), [2.7](#2.7) |
| [Tonalité du morceau et octaves relatives](#2.7bis) | [2.7bis](#2.7bis), [2.18](#2.18) |
| [Contrôles de mesure (|) et commentaires (//)](#2.10) | [2.10](#2.10) |
| [Plusieurs voix dans une même piste et texte chanté](#2.12) | [2.12](#2.12), [2.13](#2.13) |
| [Automations (volume, pan... qui changent dans le temps)](#2.15) | [2.15](#2.15) |
| [Liaisons, swing, reprises, signes et indications](#2.16) | [2.16](#2.16), [2.17](#2.17) |
| [Micro-tempo, accordage, nombreuses pistes, MTXT](#2.19) | [2.19](#2.19) |
| [Ancres de mesure (bar=N)](#2.20) | [2.20](#2.20) |
| [Transposition (transpose=, %Nom+N)](#2.21) | [2.21](#2.21) |
| [reset:, levée, version du fichier (ST 2.6)](#2.22) | [2.22](#2.22) |
| [Accords, notes d'agrément, D.C./D.S., couplets, titre (ST 2.7)](#2.23) | [2.23](#2.23) |
| [Motifs (%Nom) : réutiliser et réorganiser des parties](#4) | [4](#4) |
| [Bibliothèque MIDI (&"Nom") et dossier des morceaux songs/](#5) | [5](#5), [5bis](#5bis) |
| [Percussions et batterie écrite à la main](#6) | [6](#6) |
| [Pistes et instruments, instruments personnalisés](#7) | [7](#7) |
| [Mixeur : volumes, pan, mute, solo et volume master](#8) | [8](#8), [8.1](#8.1), [8.2](#8.2) |
| [Réverbération et chorus du synthétiseur](#8.3) | [8.3](#8.3) |
| [Effets : EQ, compresseur, delay, réverbération, noise gate, boucle d'étalonnage](#8.4) | [8.4](#8.4) |
| [Ampli de guitare, distorsion, baffles et fichiers IR](#8.4) | [8.4](#8.4) |
| [Profils NAM (vrais amplis et pédales), où les télécharger](#8.4) | [8.4](#8.4) |
| [Mastering : effets sur le master et limiteur](#8.5) | [8.5](#8.5) |
| [Sons de studio avec des programmes externes (re-amping)](#8.6) | [8.6](#8.6) |
| [Plugins VST3 et LV2, instrument SFZ interne](#8.7) | [8.7](#8.7) |
| [Vue Structure en boîtes : couplets, refrains, déplacer et copier des parties](#8bis) | [8bis](#8bis) |
| [Figer les accords, choisir le voicing, autocomplétion](#9) | [9](#9), [9.1](#9.1), [9.2](#9.2) |
| [Générer batterie, basse, accompagnement et riffs sans IA](#9bis) | [9bis](#9bis) |
| [Styles personnels (apprendre de vos morceaux) et mélodies par phrases](#9bis.1) | [9bis.1](#9bis.1), [9bis.2](#9bis.2) |
| [Importer et exporter du MIDI](#10) | [10](#10) |
| [MusicXML et ABC : exporter et importer des partitions](#10.1) | [10.1](#10.1), [10.2](#10.2), [10.3](#10.3) |
| [Voir et imprimer la partition](#10.1bis) | [10.1bis](#10.1bis) |
| [Import audio : de la voix, du micro ou d'un fichier aux notes](#10bis) | [10bis](#10bis) |
| [Jouer avec le clavier de l'ordinateur ou un clavier MIDI](#10ter) | [10ter](#10ter) |
| [Pistes audio : enregistrer voix et guitare, exporter](#10quater) | [10quater](#10quater) |
| [Enregistrer le projet (.st)](#11) | [11](#11) |
| [Lecture, boucle A-B, aller à un point](#12) | [12](#12) |
| [Choisir la SoundFont, une SoundFont par instrument](#12.3) | [12.3](#12.3), [12.4](#12.4) |
| [Métronome et humanisation](#12.5) | [12.5](#12.5), [12.6](#12.6) |
| [Fichier journal (en cas de problème)](#13.1) | [13.1](#13.1) |
| [Technologies, remerciements, licences](#14) | [14](#14) |
| [Installation sur Linux, Windows et macOS (à la fin du guide)](#inst) | [↓](#inst) |

---

## 0. Terminologie

- **SoundText Language** : le langage textuel dans lequel on écrit la
  partition (notes, accords, percussions, patterns, commandes d'état...).
- **ST-Syntax** : la grammaire formelle du SoundText Language — les règles
  de syntaxe décrites à la section 2.
- **SoundText Engine** : le moteur qui transforme un accord abstrait (ex.
  `Cmaj7`) en notes MIDI concrètes, selon l'instrument de la piste (souvent
  appelé aussi « moteur de voicing » dans ce guide).
- **.st** : extension des fichiers de projet.

## 1. Notions de base

Le programme sépare trois niveaux : l'**intention abstraite** (notes et
accords écrits en SoundText Language), le **voicing concret** (le
SoundText Engine, qui dépend de l'instrument) et la **lecture** (moteur
MIDI). Chaque piste est associée à un instrument et contient une suite de
*tokens* séparés par des espaces, conformes à la ST-Syntax.

### 1.0 La fenêtre

- **Barre des commandes**, depuis la gauche : le **transport** (retour au
  début, Lecture/Pause, Stop, **●** Enregistrer dans la piste audio
  sélectionnée, boucle A-B, métronome), le bloc **Morceau** (tempo,
  métrique, tonalité), le choix de la vue **Structure / Texte** et le volume
  **Master**. En survolant un bouton on voit à quoi il sert et son
  raccourci.
- **Barre d'avancement**, sur toute la largeur sous la barre des
  commandes : temps écoulé et durée ; cliquez pour sauter à cet endroit.
- **Vue Structure du morceau** (8bis) : les pistes en box, avec la table de
  mixage dans les en-têtes des lignes (8) ; ou bien la **vue Texte** : les
  mêmes en-têtes en colonne à gauche et la notation de la piste
  sélectionnée.

### 1.0bis Rechercher une commande (Ctrl+K) et raccourcis

**Rechercher une commande** : **Ctrl+K**, ou la case « Rechercher une
commande… » en haut à droite de la barre des menus (aussi **Aide →
Rechercher une commande...**). On écrit ce qu'on veut faire (« exporter »,
« enregistrer », « générer la basse », « métronome », « tonalité »...), on
choisit avec les flèches et on appuie sur Entrée. On trouve toutes les
entrées des menus, y compris celles de « + Ajouter une piste » ; à côté de
chacune figurent le menu où elle se trouve et son raccourci. Majuscules et
accents ne comptent pas.

**Raccourcis dans la vue Structure du morceau** (avec la souris ou le focus
sur le canevas ; dans l'éditeur de texte ces touches servent à écrire). Un
aide-mémoire se trouve en bas à droite de la barre d'état.

| Touche | Action |
|---|---|
| Espace | Lecture / Pause du morceau (partout : F5) |
| Maj+Espace | écouter seulement le box sélectionné |
| R | enregistrer dans la piste audio sélectionnée (partout : Ctrl+R) |
| Suppr | supprimer le box sélectionné |
| Ctrl+D | dupliquer le box sélectionné |
| S | diviser le clip audio sélectionné à la position de la tête de lecture |
| Ctrl+molette | zoom horizontal (le point sous la souris reste fixe) |
| Ctrl+= / Ctrl+- / Ctrl+0 | agrandir / réduire / zoom normal (aussi depuis le menu Affichage) |
| Ctrl+Z / Ctrl+Y | annuler / rétablir |

Les entrées correspondantes se trouvent aussi dans les menus **Édition**
(supprimer, dupliquer, diviser), **Affichage** (zoom) et **Lecture**.

### 1.1 Coloration syntaxique et raccourcis

L'éditeur colore automatiquement chaque token selon son type : notes (bleu
clair), accords (ambre), percussions (violet), commandes d'état `N:`/`N@`
(vert), références `%pattern` et `&"midi"` (corail), blocs `[...]` (jaune),
silences (gris). Les commentaires `//` sont en gris italique, les contrôles
de mesure `|` en gris (en rouge souligné s'ils ne tombent pas sur une barre
de mesure, voir 2.10) ; les blocs de voix `{ ; }` en turquoise, les paroles en rose italique,
et dans les groupes et les voix chaque token a sa couleur. Les couleurs reflètent exactement la façon dont le moteur
interprète le texte : elles aident donc aussi à repérer les erreurs d'un
coup d'œil.

Les en-têtes des pistes ont en plus une bordure colorée selon la famille
d'instruments (guitares, basses, cuivres...), utile pour s'y retrouver
rapidement avec beaucoup de pistes.

Principaux raccourcis clavier : `Ctrl+N` nouveau projet, `Ctrl+O` ouvrir,
`Ctrl+S` enregistrer, `Ctrl+Shift+S` enregistrer sous, `Ctrl+T` ajouter une
piste, `Ctrl+E` modifier la piste, `Ctrl+Z`/`Ctrl+Y` annuler/rétablir,
`F5` lecture/pause, `F6` stop, `Ctrl+[`/`Ctrl+]` début/fin de boucle,
`Ctrl+L` boucle activée/désactivée, `F1` ce guide.

### 1.2 Annuler/Rétablir

**Édition → Annuler** (`Ctrl+Z`) et **Rétablir** (`Ctrl+Y` ou
`Ctrl+Shift+Z`) valent pour **toute modification du projet**, d'où qu'elle
vienne : texte écrit dans l'éditeur, pistes ajoutées, supprimées ou
renommées, table de mixage (volume, pan, mute, solo, master), tempo,
métrique et tonalité, batterie/basse générées, import MIDI/audio ou au
clavier dans une piste, patterns, figement des accords, réorganisation,
box de la vue Structure du morceau. En annulant on revoit aussi la piste
sur laquelle on travaillait.

La saisie continue dans la même piste, ou le glissement d'un curseur,
devient une seule étape : une pause d'une seconde et demie suffit pour en
commencer une nouvelle. L'historique est remis à zéro quand on ouvre ou
crée un projet. Dans les fenêtres de dialogue (modification d'un box,
patterns...) le texte a en revanche son propre Annuler, indépendant.

### 1.2bis Sauvegarde automatique et récupération

Tant que le projet a des **modifications non enregistrées**, SoundText en
écrit une **copie de récupération** toutes les minutes (seulement si
quelque chose a changé entre-temps), dans le dossier `recupero/` de la
configuration. Le fichier du projet n'est pas touché : enregistrer reste
votre choix.

- Quand vous enregistrez, ouvrez ou créez un autre projet, ou fermez
  SoundText normalement (même en choisissant **Ignorer**), la copie est
  supprimée.
- Si SoundText se ferme mal (plantage, blocage, ordinateur éteint), au
  prochain démarrage il demande s'il faut **récupérer** le projet, en
  indiquant l'heure de la copie et le fichier d'origine. **Récupérer** le
  rouvre comme projet modifié : **Enregistrer** (`Ctrl+S`) l'écrit dans le
  fichier d'origine, ou choisissez **Enregistrer sous**. **Supprimer la
  copie** l'efface, **Décider plus tard** la garde pour le prochain
  démarrage.
- Plusieurs fenêtres de SoundText ouvertes en même temps ont chacune leur
  propre copie : une fenêtre encore ouverte n'est jamais proposée pour la
  récupération.

L'enregistrement normal est lui aussi « tout ou rien » : SoundText écrit
d'abord un fichier temporaire et ne le met à la place du projet qu'à la
fin, ainsi une interruption en cours de route (disque plein, coupure de
courant) ne laisse pas un fichier `.st` tronqué.

### 1.3 Langue de l'interface

SoundText parle **italien, anglais, français et espagnol**. La langue se
choisit dans **Options → Langue** et s'applique au prochain démarrage :
SoundText demande s'il doit redémarrer tout de suite (s'il y a des
modifications non enregistrées, il demande d'abord de les enregistrer). La
première fois on utilise la langue du système si c'est l'une des quatre,
sinon l'anglais.

Les menus, les fenêtres, les messages et ce guide sont dans la langue
choisie. En revanche **ne changent pas** la notation (`c*4`, `Am7`,
`kick`...) ni les mots du fichier `.st` (`Tempo:`, `Traccia`,
`Effetti`...), qui sont le format des projets : un morceau écrit avec
l'interface en italien s'ouvre de la même façon avec l'interface en
français, et inversement.

## 2. ST-Syntax (grammaire du SoundText Language)

| Construction | Signification | Exemple |
| --- | --- | --- |
| lettre minuscule a-g | note mélodique | `c` |
| lettre minuscule + `#` (dièse) ou `b`/`♭` (bémol) | note altérée | `c#`, `eb`, `e♭` |
| `*n` après une note ou un accord | octave | `c*4`, `Cmaj7*3` |
| `/Note` après un accord | basse alternative (« accord slash ») | `C/E` (do avec mi à la basse) |
| lettre MAJUSCULE + suffixe | accord abstrait | `Cmaj7`, `Am`, `G7` |
| `.style` après un accord | impose un voicing précis (voir 2.8) | `Cmaj7.drop2`, `C.power` |
| mot en minuscules (36 identifiants de percussion, voir section 5) | événement de percussion | `kick` |
| nombre initial | multiplicateur de durée | `2c`, `4Cmaj7` |
| `r` / `Nr` | silence (1 ou N unités de grille) | `r`, `3r` |
| `[...]` | événements/notes simultanés | `[c*4 e*4 g*4]`, `[kick hihat]` |
| `N:` | change la grille rythmique courante | `16:` (doubles croches) |
| `NT:` / `NQ:` / `NS:` | nolets : triolets / quintolets / septolets (voir 2.1bis) | `8T:`, `16Q:`, `8S:` |
| `N@` | change la vélocité courante (1-127) | `100@` |
| `%Nom` | appelle un pattern | `%Rock1` |
| `&"Nom"` | appelle un fichier MIDI de la bibliothèque | `&"Intro"` |
| `N(...)` | groupe de répétition : répète N fois la suite entre parenthèses | `4(c d e f)` |
| `!` à la fin d'une note ou d'un accord | staccato (divise par deux la durée audible) | `c!`, `Cmaj7!` |
| `x` à la fin d'une note ou d'un accord | mute/stop (note très brève, « étouffée ») | `cx`, `Cmaj7x` |
| `_` à la fin d'une note ou d'un accord | legato (note légèrement prolongée) | `c_`, `Cmaj7_` |
| `note>note[>note...]` | slide/portamento (pitch bend continu entre deux notes ou plus) | `c*4>d*4`, `c*4>d*4>c*4` |
| `SON` / `SOFF` | pédale de sustain : active/désactive pour tout ce qui suit | `SON c*4 SOFF` |
| `tempo=N` | règle le tempo (BPM) à partir de ce point | `tempo=120` |
| `>>` après `tempo=N` | accelerando jusqu'au `tempo=N` suivant | `tempo=100 >> c*4 tempo=140` |
| `<<` après `tempo=N` | rallentando jusqu'au `tempo=N` suivant | `tempo=140 << c*4 tempo=80` |
| `pppp@`...`ffff@` | nuances classiques, équivalentes à une vélocité fixe | `mf@` = `75@` |
| `>>` après `N@`/nuance | crescendo jusqu'à la valeur de vélocité suivante | `p@ >> c*4 ff@` |
| `<<` après `N@`/nuance | diminuendo jusqu'à la valeur de vélocité suivante | `110@ << c*4 30@` |
| **\|** | contrôle de mesure : une mesure finit ici (muet, avertit si le compte n'y est pas, voir 2.10) | `c d e f` **\|** `g a b c` **\|** |
| `//` | commentaire jusqu'à la fin de la ligne (ignoré) | `c d e f // couplet` |
| `'N` après un token | valeur de note explicite, sans changer la grille (voir 2.11) | `c'8.` (croche pointée), `[c e g]'2`, `r'4`, `e'8T` |
| `{ ... ; ... }` | voix qui commencent ensemble dans la même piste (voir 2.12) | `{ c*5 d*5 e*5 f*5 ; 4c*4 }` |
| `"..."` | paroles : une syllabe par note, sur les notes qui précèdent (voir 2.13) | `c d e 2f "Ma- ri- a, sei"` |
| `vol=N` `expr=N` `pan=N` `mod=N` `rev=N` `cho=N` | automations : volume, expression, panoramique (-1..1), modulation, départs de réverbération et de chorus (voir 2.15) | `vol=80`, `pan=-0.5` |
| `>>` après une automation | rampe continue jusqu'à la prochaine valeur du même nom ; `>>exp`, `>>log`, `>>s` choisissent la courbe | `vol=0 >>exp 4c vol=100` |
| `<` / `>` à la fin d'une note | crescendo / diminuendo pendant la note tenue (soufflet) | `2c<`, `c'2>` |
| `~` à la fin d'une note | liaison de prolongation : la note continue dans la suivante identique, même au-delà de la barre de mesure (voir 2.16) | `2c~ \| 2c` |
| `(` ... `)` à la fin des notes | liaison : les notes entre les deux sont jouées legato (voir 2.16) | `c( d e f)` |
| `swing=N` / `swing16=N` | swing des croches / des doubles croches (50 = droit, 66 = ternaire) | `swing=62 8: c d e f` |
| `bar=N` | ancre de mesure : amène le curseur au début de la mesure N, avec les silences nécessaires (voir 2.20) | `bar=29 c d e f` |
| `transpose=N` | transposition : les notes, accords et slides suivants sonnent N demi-tons plus haut ou plus bas (voir 2.21) ; `%Nom+N` transpose un pattern | `transpose=-2 c d e` |
| `\|:` ... `:\|` | reprise : la partie entre les deux signes est jouée deux fois (voir 2.17) | `\|: c d e f :\|` |
| `\|1.` `\|2.` `\|\|` | cases de reprise : une fin différente à chaque passage (voir 2.17) | `\|1. g a :\| \|2. 4c \|\|` |
| `$signe` à la fin d'une note | accent, point d'orgue, trille, mordant, gruppetto, tenuto, marcato (voir 2.17) | `c$fermata`, `d$tr`, `e$accent` |
| `$"texte"` | indication au-dessus de la portée | `$"rit."`, `$"dolce"` |
| `rel:` / `abs:` | octaves relatives (chaque note va près de la précédente) / absolues (voir 2.18) | `rel: c d e f g a b c` |
| `*+` / `*-` après une note (en `rel:`) | une octave au-dessus / au-dessous | `rel: g c*+ c*-` |
| `key=K` | les notes prennent les altérations de la tonalité K (voir 2.18) | `key=G f` (= fa dièse) |
| `n` après une note | bécarre : enlève l'altération de la tonalité | `key=G fn` |

Le caractère `|` est le **contrôle de mesure** (voir 2.10) : il ne joue
rien et ne déplace rien, il sert seulement à déclarer où finit une mesure.
Les durées s'accumulent de toute façon le long de la timeline, les `|` sont
donc facultatives. Dans le fichier de projet `.st`, le caractère apparaît
aussi dans l'en-tête d'un box de la vue « Structure du morceau » (section
8bis), pour indiquer sa position en temps, ex. `Box Basso1 "Intro" |4:` —
un détail du format d'enregistrement.

**Rampes et fermeture obligatoire** : une rampe `>>`/`<<` doit toujours être
refermée par une autre commande **du même type** (vélocité après vélocité,
tempo après tempo) avant qu'arrive une commande de l'autre type, ou avant
la fin de la piste — sinon la validation signale une erreur explicite au
lieu de laisser la rampe « orpheline » (ouverte mais sans aucun effet
audible, un bug silencieux difficile à remarquer à l'écoute seule). Un
changement de grille (`N:`) au milieu d'une rampe déjà ouverte ne la ferme
pas et ne la casse pas — il peut apparaître librement avant la note/l'accord
qui la ferme.

### Bémol : `b`, `♭` ou `-` (raccourci de saisie)

Le bémol peut s'écrire avec la lettre `b` (ex. `eb`), avec le vrai symbole
musical `♭` (ex. `e♭`), ou avec un tiret `-` (ex. `e-`) : ce sont trois
synonymes parfaitement équivalents pour le parseur, sur les notes comme sur
la fondamentale d'un accord (`Bb7` = `B-7` = `B♭7`). La lettre `b` reste
valable par compatibilité avec ce qui a été écrit jusqu'ici, mais elle peut
se confondre visuellement avec la lettre de note `b` (si) — c'est pourquoi
**l'éditeur remplace automatiquement par `♭` un `-` tapé juste après une
lettre de note** (ex. en tapant `e` puis `-` on voit `e♭`) : ainsi l'écran
montre toujours le bon symbole sans avoir à chercher `♭` sur le clavier. Le
remplacement ne se fait que lorsque le `-` suit immédiatement une lettre de
note en début de token (après un espace, `[`, `(`, `>`, ou un chiffre
multiplicateur) : un `-` tapé dans un autre contexte (ex. après `snare`)
reste un tiret normal.

### Qualités d'accord prises en charge
`(vide)`/`maj`, `m`/`min`, `7`, `maj7`, `m7`, `dim`, `dim7`, `aug`,
`sus2`, `sus4`, `6`, `m6`, `9`, `maj9`, `m9`, `mMaj7`, `m7b5`, `add9`,
`7sus4`, `7b9`, `7#9`, `5`, `7alt`, `11`, `13`, `maj13`, `°`, `°7`.

Les six dernières sont des alias ou des extensions pensés pour la notation
qu'on écrirait « à l'oreille » en lisant une vraie grille :
- **`5`** (ex. `E5`) : power chord, seulement fondamentale et quinte, pas de
  tierce — équivaut à écrire l'accord avec le voicing `.power` (`E.power`),
  mais il est aussi reconnu comme qualité à part entière (ex. pour l'import
  MIDI : une simple quinte jouée est maintenant reconnue comme `5`, au lieu
  d'être laissée comme un bloc explicite ambigu).
- **`°`** / **`°7`** (ex. `C°`, `C°7`) : alias de la notation classique pour
  `dim`/`dim7`, mêmes intervalles, même voicing.
- **`7alt`** (ex. `G7alt`) : dominante altérée, approchée avec les mêmes
  intervalles que `7b9` (la grammaire ne modélise pas séparément les
  tensions altérées #9/#11/b13).
- **`11`**, **`13`**, **`maj13`** : extensions au-delà de la neuvième
  (`13` omet la onzième, comme c'est l'usage courant en jazz pour éviter la
  dissonance avec la tierce majeure).

### 2.8 Voicing explicite sur les accords (`.style`)

Un suffixe optionnel `.style` après la qualité de l'accord (avant
l'éventuel `/octave`) oblige le moteur de voicing à utiliser un algorithme
précis au lieu de l'algorithme automatique de l'instrument :

```
Cmaj7          -> voicing automatique selon l'instrument de la piste
Cmaj7.drop2    -> impose le voicing Jazz Drop-2
C7.cagEd*3     -> forme E du système CAGED, octave 3
```

**Priorité** : s'il est présent, le suffixe l'emporte toujours sur
l'algorithme automatique de l'instrument. **Repli intelligent** : si un
style n'a pas de sens pour l'instrument de la piste (ex. `.barre` sur un
piano), le moteur le remplace automatiquement par l'équivalent générique le
plus proche (ex. `.close`) — ce n'est jamais une erreur. Un style
**inconnu** (faute de frappe) est en revanche signalé par la validation
comme tout autre token non reconnu.

Styles généraux (valables sur n'importe quel instrument) :
- `noroot` : omet la fondamentale.
- `shell` : omet la quinte.
- `close` : notes empilées le plus près possible.
- `open` : forme ouverte, notes réparties sur plusieurs octaves.
- `inv1` / `inv2` / `inv3` : 1er, 2e ou 3e renversement (respectivement
  tierce, quinte, septième à la basse ; si l'accord n'a pas assez de notes
  pour le renversement demandé, on utilise le plus haut disponible).

Styles pour guitare (repli automatique s'ils sont utilisés sur d'autres
instruments) : `barre`, `Caged`/`cAged`/`caGed`/`cagEd`/`cageD` (les 5
formes du système CAGED), `drop2`, `drop3`, `triad`, `power`
(fondamentale+quinte), `openpos` (approximation des accords en première
position), `hendrix` (fondamentale seule à la basse + le reste une octave
au-dessus), `top` (accord une octave au-dessus), `bottom`
(fondamentale+quinte+septième, sans la tierce). Les combinaisons
qualité/style les plus courantes (ex. `Cmaj7.drop2`, `C7#9.hendrix`)
utilisent une table de voicings soignée pour plus de précision ; les autres
combinaisons utilisent un algorithme générique équivalent. Comme pour le
reste du moteur, il n'y a pas de vrai modèle de cordes/frettes : ce sont des
approximations musicalement sensées sur des notes MIDI abstraites, pas des
doigtés physiques.

Styles pour clavier (repli automatique s'ils sont utilisés sur d'autres
instruments) : `left` (main gauche fondamentale/quinte grave, main droite le
reste), `right` (voicing compact pour la seule main droite), `spread`
(accord large à deux mains).

Exemples valides : `Cmaj7`, `Cmaj7.drop2`, `C7.cagEd`, `C.power`,
`Am7.open`, `F.barre`.

### 2.9 Basse alternative sur les accords (accord « slash »)

Un suffixe optionnel `/Note` après la qualité (et après l'éventuel
`.style`, avant l'éventuel `*octave`) indique une basse différente de la
fondamentale de l'accord — la notation « slash » classique des grilles
(`C/E` = accord de do avec mi à la basse) :

```
C/E            -> do majeur avec mi à la basse
Dm7/G          -> ré mineur septième avec sol à la basse
C.drop2/E*4    -> comme ci-dessus, voicing drop2, octave 4
```

Le moteur de voicing calcule d'abord l'accord normalement (fondamentale,
qualité, style), puis ajoute la note de basse demandée une octave sous le
voicing obtenu (en descendant d'autres octaves si nécessaire pour rester
sous toutes les autres notes) — c'est toujours la note la plus grave jouée,
comme dans un vrai accord slash. Transposer un accord avec basse
alternative déplace aussi la basse du même nombre de demi-tons.

**Note technique** : `/` après un accord indique seulement la basse
alternative ; l'octave s'écrit toujours avec `*n` (voir sect. 2), même avec
la basse (`C/E*3`). L'ancienne forme avec des chiffres après la barre
(`C7/3`, `c/4`) n'est plus valide.

### 2.1 Groupes de répétition

Une suite de tokens entre parenthèses, précédée d'un nombre, est répétée ce
nombre de fois :

```
4(2C7 2e c d 2A7)   -> répète 4 fois la suite : 2C7 2e c d 2A7
```

Les groupes peuvent être imbriqués (`2(c 2(d e))`) et contenir n'importe
quel token valide, y compris des patterns et des références MIDI.

### 2.1bis Nolets (triolets / quintolets / septolets)

Une lettre optionnelle après le nombre d'une commande de grille (`N:`,
section 3) active un groupement irrégulier au lieu de la subdivision
binaire normale, en réduisant proportionnellement la durée de chaque note :

| Lettre | Nolet | Rapport | Exemple |
| --- | --- | --- | --- |
| `T` | triolet | 3 notes dans l'espace de 2 | `8T:` (triolets de croches : 3 dans une noire) |
| `Q` | quintolet | 5 notes dans l'espace de 4 | `16Q:` (quintolets de doubles croches : 5 dans une noire) |
| `S` | septolet | 7 notes dans l'espace de 4 | `8S:` (septolets de croches : 7 dans deux noires) |

```
8T: c d e            -> triolet de croches : les trois notes remplissent une noire
16Q: c d e f g       -> quintolet de doubles croches : les cinq notes remplissent une noire
8S: c d e f g a b    -> septolet de croches : les sept notes remplissent deux noires
```

Comme pour la grille binaire, la commande reste active jusqu'à ce qu'on la
change à nouveau (section 3) : inutile de la répéter avant chaque note du
groupe. On peut revenir à la subdivision binaire à tout moment avec une
commande `N:` sans lettre (ex. `16:` après `16Q:`).

### 2.2 Modificateurs de la note (et de l'accord)

Un seul caractère à la fin d'une note ou d'un accord (après l'éventuelle
octave `*n`, et après l'éventuel `.style` de voicing sur un accord) en
change l'articulation, sans modifier la position des notes suivantes sur la
timeline (la note/l'accord occupe toujours toute l'unité de grille, seule
change la durée pendant laquelle on l'entend) :

- **`!` staccato** : joue pendant 50 % de la durée nominale, le reste est
  du silence.
- **`x` mute** : elle est « étouffée » presque tout de suite (~15 % de la
  durée nominale), pour un effet amorti/percussif.
- **`_` legato** : elle est prolongée un peu au-delà de la durée nominale
  (~115 %), pour se « lier » en douceur à la suivante.

Sur les accords on peut le combiner avec le voicing explicite (2.8), ex.
`Cmaj7.drop2!` (voicing Drop-2 + staccato). Le même modificateur appliqué à
un accord agit sur **toutes** les notes du voicing, pas seulement sur la
fondamentale. Remarque : les blocs simultanés `[...]` ne prennent pas encore
en charge ce modificateur final ; pour un « power chord staccato » on
utilise un accord nommé avec le voicing `.power`, ex. `E.power!`.

### 2.3 Slide (pitch bend / portamento)

Deux notes ou plus reliées par `>` (sans espaces) produisent un glissement
continu de hauteur de l'une à l'autre :

```
c*4>d*4        -> glisse de Do4 à Ré4 en une unité de grille (comme une note)
c*4>d*4>c*4    -> monte de Do4 à Ré4 en une unité et revient à Do4 en une
                  autre (bend-and-release, 2 unités en tout)
```

La règle est unique : le multiplicateur d'une étape est la durée de la
rampe qui **part** de cette étape vers la suivante (1 s'il manque) ; le
multiplicateur de la **dernière** étape est le temps pendant lequel la note
reste sur la hauteur atteinte (0 s'il manque : le slide se termine en
arrivant).

```
5c*4>d*4       -> rampe lente de Do4 à Ré4 sur 5 unités
2c*4>3d*4      -> monte en 2 unités, puis reste sur Ré4 pendant 3 autres
                  (bend rapide puis tenu)
2c*4>2d*4>3c*4 -> monte en 2 unités, descend en 2 autres, puis reste sur
                  la hauteur d'arrivée pendant 3 autres
```

Une chaîne peut avoir autant d'étapes qu'on veut (`c*4>d*4>c#*4>c*4`...).
Un slide qui durerait zéro (`0c*4>d*4`) est une erreur.

Techniquement, c'est exporté comme une seule note MIDI (un seul
note_on/note_off pour toute la chaîne) avec une suite de messages de Pitch
Bend qui interpolent progressivement d'une étape à la suivante (l'amplitude
du pitch bend étant réglée automatiquement par RPN pour couvrir
correctement des slides même au-delà d'une octave). Voir aussi la section 10
pour la façon dont l'import MIDI reconnaît automatiquement un bend (y
compris un bend-and-release) dans un fichier existant et le traduit dans
cette syntaxe.

### 2.4 Pédale de sustain (SON / SOFF)

Les tokens `SON` et `SOFF`, placés librement dans le flux des notes,
activent/désactivent la pédale de sustain (piano) pour tout ce qui suit,
jusqu'à la commande opposée :

```
Piano — AcousticPiano:
  8: SON c*3 g*3 c*4 e*4 g*4 e*4 c*4 g*3 SOFF
  8: SON a*2 e*3 a*3 c*4 e*4 c*4 a*3 e*3 SOFF
```

Si un `SOFF` est oublié, le programme relâche quand même automatiquement
la pédale à la fin de la piste, pour éviter qu'une note reste coincée dans
une réverbération sans fin.

### 2.5 Nuances classiques et rampes (crescendo/diminuendo)

En plus de la valeur numérique explicite (`100@`), la vélocité accepte les
indications de nuance classiques :

| Marqueur | Vélocité |
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

En faisant suivre une valeur de vélocité (numérique ou nuance) du symbole
`>>` (crescendo) ou `<<` (diminuendo), la vélocité des notes suivantes est
interpolée linéairement jusqu'à la prochaine valeur de vélocité
rencontrée :

```
8: p@ >> c*4 d*4 e*4 f*4 f@       -> crescendo de 49 à 88 sur les 4 notes
8: 110@ << g*4 f*4 e*4 d*4 30@     -> diminuendo de 110 à 30
```

Après les flèches, on peut choisir la **courbe** de la rampe : `>>exp`
démarre doucement puis accélère, `>>log` démarre vite puis ralentit, `>>s`
est douce au début et à la fin (`p@ >>exp c d e f ff@`). Cela vaut aussi
pour les rampes de tempo et pour les automations (section 2.15).

### 2.6 Changements de tempo (accelerando/rallentando)

Dans une piste, la commande `tempo=N` (1-999) règle le tempo (BPM)
instantanément à partir de ce point :

```
tempo=120 c*4 d*4    -> tempo réglé à 120 BPM
```

Comme pour la nuance, `>>` (accelerando) ou `<<` (rallentando) après une
commande `tempo=N` interpole progressivement le tempo jusqu'au `tempo=N` suivant :

```
tempo=100 >> c*4 d*4 e*4 f*4 tempo=140    -> accelerando de 100 à 140 BPM
tempo=140 << c*4 d*4 e*4 f*4 tempo=80      -> rallentando de 140 à 80 BPM
```

Remarque : le tempo est par nature une notion partagée par tout le projet
(toutes les pistes jouent sur la même timeline) ; un changement de tempo
déclaré dans une piste s'applique donc à tout le morceau à partir de ce
point, pas seulement à cette piste.

### 2.7 Changements de tempo et de métrique par mesure

En plus de la forme simple (`Tempo: 120 BPM`, `Metrica: 4/4`, une seule
valeur pour tout le morceau), l'en-tête du projet accepte aussi une liste
de changements indexés par numéro de mesure :

```
Tempo: 1: 120, 5: 140, 9: 100
Metrica: 1: 4/4, 5: 3/4, 8: 4/4
```

Cela signifie : tempo 120 BPM à partir de la mesure 1, 140 BPM à partir de
la mesure 5, 100 BPM à partir de la mesure 9 ; métrique 4/4 à partir de la
mesure 1, 3/4 à partir de la mesure 5, 4/4 à partir de la mesure 8. Les
positions (en temps) des mesures qui suivent la première sont calculées
automatiquement en tenant compte de la métrique en vigueur dans chaque
passage.

**Barre d'avancement, surlignage et champs Tempo/Métrique pendant la
lecture** : le fichier MIDI exporté, la barre d'avancement, le surlignage
du token en cours dans l'éditeur et les champs **Tempo (BPM)** et
**Métrique** de la barre d'outils principale utilisent tous la même table
de tempo/métrique du projet (tous les changements par mesure plus les
marqueurs en ligne `tempo=N`) : ils montrent donc toujours la valeur réellement
en vigueur à cet endroit du morceau, pas une estimation basée sur le seul
tempo/métrique initial. Une fois la lecture arrêtée, les champs
Tempo/Métrique reviennent à la valeur « au repos » du projet (celle de la
mesure 1).

### 2.7bis Tonalité du morceau

L'en-tête du projet peut aussi déclarer la tonalité du morceau (ligne
`Tonalita: <valeur>`), réglable aussi depuis le champ **Tonalité** de la
barre d'outils principale, à côté de Tempo et Métrique :

```
Tonalita: Am
```

Format : lettre de note (A-G) + altération optionnelle (`#` ou `b`) + `m`
optionnel pour le mineur, ex. `C`, `F#`, `Ebm`, `Am` (majeur si `m` est
absent). C'est une information descriptive/de référence (elle n'influence
ni le voicing ni la reconnaissance des accords) ; en important un fichier
MIDI qui déclare une tonalité (événement méta *key signature*) elle est
reconnue et réglée automatiquement. Si le fichier déclare do majeur ou ne
déclare rien (do est la valeur par défaut de beaucoup de séquenceurs, donc
peu fiable), la tonalité est estimée à partir des notes comme le fait
**Analyser la tonalité**. Elle sert aussi à **Jouer au clavier** (section
10ter) dans les dispositions de clavier « Gamme de la tonalité ».

Si vous ne la connaissez pas déjà (ou si vous n'êtes pas sûr),
**Composer → Analyser la tonalité...** l'estime automatiquement en analysant
les notes réellement écrites dans toutes les pistes non percussives du
projet (batterie exclue), avec l'algorithme classique de
Krumhansl-Schmuckler : il compare la distribution des 12 classes de hauteur
utilisées (pondérée par la durée) avec les profils tonaux typiques de
chacune des 24 tonalités possibles et choisit la plus ressemblante, en la
réglant automatiquement dans le champ Tonalité (en écrasant une éventuelle
valeur déjà présente). C'est une estimation statistique, pas une vraie
analyse harmonique : elle peut se tromper sur des morceaux très courts,
chromatiques ou qui modulent — un bon point de départ, pas un verdict
infaillible. Si le projet ne contient pas de notes à hauteur définie
(aucune piste, ou seulement des percussions), il le signale au lieu de
deviner.

### 2.10 Contrôles de mesure (`|`) et commentaires (`//`)

**Contrôles de mesure.** Un `|` entre deux tokens déclare « une mesure finit
ici ». Il ne joue rien et ne déplace pas le temps : le programme vérifie
seulement qu'il y a bien une barre de mesure à cet endroit, selon la
**Métrique** du projet et ses changements par mesure (section 2.7). Il peut
aussi être collé à une note (`d*4|`).

```
4: c d e f | g a b c | 2c 2e |
8: c d e f g a b c | 2: c c |
```

Si un `|` ne tombe pas sur une barre de mesure, la barre sous l'éditeur
devient orange et indique quelle mesure ne tombe pas juste et de combien,
par exemple `mesure 2 : il manque 1 croche` ou
`mesure 3 : 1 noire en trop` ; le `|` fautif devient rouge et souligné.
L'infobulle de la barre liste tous les avertissements. **Ce n'est pas une
erreur de syntaxe** : le morceau se joue et s'exporte quand même, c'est une
aide pour remarquer une note manquante ou une durée erronée. Une note
manquante décale tout ce qui suit, mais elle n'est signalée qu'une fois :
les `|` suivants sont mesurés en en tenant compte et n'avertissent que s'il
y a une autre erreur.

- Les barres de mesure sont celles du **morceau** : dans un box de la vue
  Structure du morceau, elles comptent à partir de la position du box (un
  box qui commence au milieu d'une mesure a son premier `|` après une
  demi-mesure).
- Dans un pattern ou un groupe `N(...)`, le `|` est vérifié à chaque
  répétition ; l'avertissement désigne la référence `%Nom` ou le groupe.
- Dans un bloc `[...]`, le `|` n'est pas admis (erreur de syntaxe).

**Commentaires.** De `//` à la fin de la ligne, le texte est ignoré : pour
annoter des sections, des accords, des idées. Une barre simple (`C/E`,
`&"Blues/basse"`) garde son sens habituel.

```
// Couplet
4: Am | F | C | G |     // grille de quatre accords
```

Les commentaires et les retours à la ligne sont conservés dans le fichier
`.st`, dans les box, dans la transposition des box et dans le gel des
accords. Ils ne sont pas conservés dans le corps des patterns (enregistrés
comme une suite de tokens) ni par les opérations qui réécrivent tout le
texte de la piste (Réorganiser avec les patterns, Développer les patterns).
Dans le fichier `.st`, une ligne vide ferme un bloc : les lignes vides à
l'intérieur du texte d'une piste sont supprimées à l'enregistrement
(auparavant elles tronquaient le reste de la piste).

### 2.11 Valeurs de note explicites (`'8.`)

En plus de la grille (`N:` suivi de multiplicateurs), une durée peut
s'écrire comme **valeur de note**, avec une apostrophe à la fin du token :

| Écriture | Valeur | Durée en noires |
| --- | --- | --- |
| `c'1` | ronde | 4 |
| `c'2` | blanche | 2 |
| `c'4` | noire | 1 |
| `c'8` | croche | 1/2 |
| `c'16`, `c'32`, `c'64` | double, triple, quadruple croche | 1/4, 1/8, 1/16 |
| `c'4.` / `c'8.` | noire / croche **pointée** | 1 1/2 / 3/4 |
| `c'2..` | blanche doublement pointée | 3 1/2 |
| `c'8T` / `c'4T` | croche / noire de **triolet** | 1/3 / 2/3 |
| `c'16Q`, `c'8S` | quintolet, septolet (comme les grilles `NQ:`, `NS:`) | |

```
8: c*4'8. d*4'16 e*4 e*4 [c e g]'2    // rythme pointé sans changer de grille
```

La valeur vaut **seulement pour ce token** : la grille courante reste la
même (dans l'exemple, `e*4 e*4` sont des croches de la grille `8:`). Elle
fonctionne avec les notes, les accords (`C7'2`), les blocs (`[c e g]'2`),
les silences (`r'4`), les percussions (`kick'16`) et les slides. Un
multiplicateur devant s'ajoute : `2c'8` dure deux croches.
L'articulation peut se placer avant ou après : `c'8!` et `c!'8` sont la
même croche staccato. La grille reste pratique pour les rythmes réguliers ;
la valeur explicite est plus lisible pour les phrases irrégulières et pour
qui vient de la partition.

### 2.12 Plusieurs voix dans la même piste (`{ ; }`)

Un **bloc de voix** contient deux séquences ou plus, séparées par `;`, qui
**commencent ensemble**, chacune avec ses durées. Le bloc dure autant que
la voix la plus longue, puis la piste continue :

```
4: { c*5 d*5 e*5 f*5 ; 4c*4 } g*4           // mélodie sur une note tenue
4: {
  8: e*5 d*5 c*5 d*5 e*5 e*5 2e*5            // main droite
  ;
  2c*4 2g*3                                  // main gauche
}
```

Contrairement à `[...]`, où tout commence et finit ensemble, chaque voix a
son rythme : c'est ce qu'il faut pour le piano à deux mains, une mélodie
sur un accord tenu, la guitare classique.

- Chaque voix part avec l'**état** (grille, vélocité) de l'endroit où le
  bloc s'ouvre ; les changements faits **dans** une voix y restent.
- Toute la grammaire fonctionne dans une voix : groupes `N(...)`,
  patterns `%Nom`, contrôles de mesure `|` (chaque voix est vérifiée pour
  son compte), paroles, et même d'autres blocs de voix.
- Le bloc peut s'étendre sur plusieurs lignes ; un `;` hors d'un bloc est
  une erreur.
- Dans l'éditeur, chaque voix a son propre **fond coloré** (bleu pour la
  première, ambre pour la deuxième, puis lilas et vert ; un bloc imbriqué
  part d'une autre couleur) : on voit tout de suite où chacune commence et
  finit, même quand le bloc s'étend sur plusieurs lignes. Les accolades et
  les `;` restent sans fond.
- Dans la partition (sections 10.1 et 10.1bis), les voix deviennent des
  **voix de la même portée**, hampes vers le haut et vers le bas.

### 2.13 Paroles (`"..."`)

Une chaîne entre guillemets est les **paroles** des notes qui la
**précèdent**, à partir de la note qui suit les paroles précédentes (ou du
début) : une syllabe par note, séparées par des espaces. On l'écrit comme
sous une ligne de partition :

```
4: c*4 d*4 e*4 2f*4
"Ma- ri- a, sei"
```

- Un tiret à la fin (`Ma-`) indique que le mot continue dans la syllabe
  suivante ; dans la partition, les syllabes sont reliées par le tiret.
- `_` ne donne pas de nouvelle syllabe à la note : la syllabe précédente
  se **prolonge** (mélisme, avec la ligne de prolongation dans la
  partition).
- `*` saute une note (pas de syllabe).
- Les silences et les percussions ne reçoivent pas de syllabes.
- La syllabe peut aussi être collée à la note : `c"Ma-" d"ri-" e"a"`.
- Dans un groupe `2(...)`, les paroles se répètent avec les notes ; après
  un bloc de voix, elles vont sur la **première voix** (une voix peut aussi
  avoir ses propres paroles, dans le bloc).
- Les paroles ne s'entendent pas : elles vont dans la partition (sous les
  notes), dans le MusicXML et dans le MIDI exporté (événements *lyrics*,
  lus par les logiciels de karaoké).
- S'il y a **plus de syllabes que de notes**, l'éditeur affiche un
  avertissement (orange), comme pour les contrôles de mesure. Un `//`
  entre guillemets fait partie des paroles, il n'ouvre pas de commentaire.

### 2.14 La spécification et la bibliothèque ST-language

La notation a une **spécification formelle publique** :
[docs/spec/ST-language.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md) (en anglais ; en italien
[ST-language.it.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.it.md)), sous licence **CC BY 4.0**
(on peut la copier, la traduire et l'adapter en citant la source). Elle
décrit la grammaire complète, la façon dont le texte devient des notes dans
le temps, les erreurs et les avertissements, le format des fichiers `.st`
et la correspondance avec le MIDI, avec une **suite de conformité**
([`docs/spec/conformance/`](https://github.com/openssound/st-language/tree/main/docs/spec/conformance)) : les cas de test qu'un autre programme doit
réussir pour lire ST-language comme SoundText.

Le moteur de la notation est aussi une **bibliothèque Python autonome**,
`st_language`, sans dépendances externes : c'est celle qu'utilise
SoundText, donc les deux donnent toujours le même résultat. Elle
s'installe avec `pip install git+https://github.com/openssound/st-language.git` et fournit des
commandes en ligne :

```
st-language check morceau.st         # erreurs et avertissements (mesures, paroles)
st-language midi morceau.st -o morceau.mid
st-language musicxml morceau.st      # partition morceau.musicxml
st-language events morceau.st        # les événements en JSON
echo "4: c d e f | 2g 2g" | st2mid - -o melodie.mid --instrument Trumpet
```

Un fichier sans en-têtes de piste est un morceau d'une seule piste
(`--instrument` en choisit l'instrument). En Python : `import st_language
as st`, puis `st.parse(texte)`, `st.validate(texte)`, `st.check(texte)`,
`st.load_song("morceau.st")`, `st.to_midi(morceau, "morceau.mid")`. Ainsi,
les morceaux écrits en ST peuvent être vérifiés et exportés sans ouvrir
SoundText (par exemple depuis un script, ou dans un dépôt de chansons).

### 2.15 Automations (volume, expression, panoramique... qui évoluent dans le temps)

Les nuances (`p@`, `>>`) changent la **vélocité**, c'est-à-dire la force
avec laquelle chaque note est jouée : une note déjà commencée reste telle
quelle. Les **automations**, elles, agissent sur l'instrument de façon
**continue**, même pendant une note tenue, comme si l'on bougeait un
curseur de la table de mixage pendant le jeu :

| Commande | Ce qu'elle change | Valeurs | Au départ |
| --- | --- | --- | --- |
| `vol=N` | volume de la piste | 0-127 | 100 |
| `expr=N` | expression : le volume « à l'intérieur » de la nuance (cordes, vents, orgue) | 0-127 | 127 |
| `pan=N` | position stéréo : -1 gauche, 0 centre, 1 droite | -1..1 (décimales permises) | 0 |
| `mod=N` | modulation (vibrato, sur beaucoup d'instruments) | 0-127 | 0 |
| `rev=N` | départ vers la réverbération | 0-127 | 0 |
| `cho=N` | départ vers le chorus | 0-127 | 0 |
| `bend=N` | pitch bend, en demi-tons (comme la molette du synthé) | -24..24 (décimales permises) | 0 |
| `ccN=V` | n'importe quel contrôleur MIDI N (0-119), p. ex. `cc74` brillance | 0-127 | 0 |

Seule, la commande change la valeur à cet endroit. Suivie de `>>` (ou `<<`,
c'est pareil), elle ouvre une **rampe** qui va jusqu'à la prochaine
commande du même nom, en passant par toutes les valeurs intermédiaires :

```
4: vol=0 >>exp 4c*4 vol=100          // fondu d'entrée sur la note tenue
4: pan=-1 >> c d e f pan=1           // le son passe de gauche à droite
4: expr=40 >>s 2C 2F expr=127 r      // gonfle sous deux accords
8: rev=20 c d e f rev=90 4g          // la réverbération augmente d'un coup
```

La **courbe** de la rampe se choisit après les flèches : `>>` (linéaire),
`>>exp` (démarre doucement puis accélère : le fondu d'entrée naturel),
`>>log` (démarre vite puis ralentit : le fondu de sortie naturel), `>>s`
(douce au début et à la fin).

**Soufflets sur les notes.** Un `<` à la fin d'une note (ou d'un accord,
d'un bloc, d'un slide) fait un **crescendo pendant la note**, un `>` un
diminuendo : c'est le soufflet de la partition, réalisé avec l'expression
(de la moitié à la valeur courante ou l'inverse), qui revient ensuite à sa
valeur :

```
4: 4c*5<            // une note tenue qui enfle
4: 2C< 2G>          // un accord grandit, l'autre diminue
4: c'2> [c e g]<    // avec une valeur de note ou sur un bloc
```

- Les automations valent pour toute la piste, même écrites dans un bloc de
  voix `{ ; }` ; des rampes de noms différents peuvent se superposer
  (`vol=` et `pan=` ensemble).
- `vol=` se combine avec le volume de la table de mixage (`vol=100` = le
  volume du curseur) ; `pan=`, `rev=` et `cho=` écrits dans le texte
  remplacent les valeurs de la table de mixage à partir de cet endroit.
- Une rampe ouverte doit être fermée par une valeur du même nom, sinon la
  validation signale une erreur ; un soufflet sur un silence et un
  soufflet dans une rampe `expr=` ouverte sont aussi des erreurs.
- On les entend à la lecture et elles vont dans le MIDI exporté (en
  control change : CC7, CC11, CC10, CC1, CC91, CC93) ; dans la partition,
  les rampes `vol=`/`expr=` et les soufflets apparaissent comme des
  soufflets de crescendo et de diminuendo.
- Elles font partie de la spécification ST-language depuis la version 1.1
  (2.14).

### 2.16 Liaisons et swing

**Liaison de prolongation `~`.** Un `~` à la fin d'une note, d'un accord ou
d'un bloc la **relie** à la suivante identique : elles sonnent comme une
seule note, aussi longue que les deux ensemble. Cela sert surtout à tenir
une note au-delà de la barre de mesure, là où la division en mesures ne
permet pas de l'écrire d'un seul tenant :

```
4: c d 2f~ | 2f g a |        // le fa dure 4 temps, à cheval sur la barre
4: 4C7~ | 4C7 | 4F |         // un accord tenu pendant deux mesures
4: c'2~ c'8 r'8 d'4          // aussi avec les valeurs de note
```

La note après le `~` doit être la même (`c#~ db` convient : c'est le même
son), sinon c'est une erreur ; les percussions, les silences et les
slides ne se lient pas.

**Liaison `( )`.** Un `(` à la fin de la première note et un `)` à la fin
de la dernière relient une phrase : les notes entre les deux sont jouées
**legato** (enchaînées, comme une phrase chantée), la dernière comme
écrite. La partition montre l'arc au-dessus des notes.

```
4: c( d e f) g( a b c*5)
4: 2(c( d) e)                // dans un groupe, la liaison se répète
```

Une note avec sa propre articulation (`d!` staccato) la garde aussi dans
la liaison. Les liaisons ne s'imbriquent pas et ne traversent pas un bloc
de voix `{ ; }`.

**Swing.** `swing=N` fait « balancer » les croches à partir de l'endroit où
on l'écrit : dans chaque temps, la première croche s'allonge et la seconde
se raccourcit, comme on joue le jazz, le blues et le shuffle. N est la part
du temps donnée à la première croche : 50 est droit, 66 est ternaire (le
swing classique), jusqu'à 80. `swing16=N` fait de même avec les doubles
croches (funk, hip-hop). `swing=50` enlève le swing.

```
swing=62 8: c d e f g a b c*5   // écrit droit, joué swing
swing16=58 16: kick hihat snare hihat kick kick snare hihat
```

Tout s'écrit droit : les contrôles de mesure et la partition restent
réguliers (la partition affiche l'indication « Swing »), seule la façon de
jouer change, à la lecture et dans le MIDI exporté.

### 2.17 Reprises, signes et indications

**Reprises.** Elles s'écrivent comme sur une partition : `|:` ouvre la
partie à répéter, `:|` la ferme, et la partie est jouée deux fois. Sans
`|:`, la reprise part du début du morceau (ou de la fin de la reprise
précédente).

```
4: |: c d e f | g a b c :| c*5 d*5 e*5 f*5 |
```

Pour une fin différente à chaque passage, on utilise les **cases** :
`|1.` ouvre la première, `:|` la ferme et revient au début, `|2.` ouvre
la seconde, qui se termine par `||` (ou par la fin du texte). Avec trois
cases, la partie est jouée trois fois, et ainsi de suite.

```
4: |: c d e f |1. g a b c :| |2. 4c*5 || d e f g |
```

On entend tout en entier ; la **partition** montre les vrais signes de
reprise et les cases, à condition que la reprise commence et finisse sur
les barres de mesure et que chaque passage soit identique au premier dans
toutes les pistes (sinon la partition l'écrit en entier). Un groupe
`2(...)` qui occupe des mesures entières s'imprime aussi comme une
reprise. `|:`, `:|`, `|1.` et `||` sont aussi des contrôles de mesure, et
les reprises ne s'imbriquent pas.

**Signes sur les notes.** Un `$` suivi du nom, à la fin d'une note, d'un
accord ou d'un bloc (après la valeur de note), ajoute un signe qu'on voit
dans la partition et qu'on entend :

| Signe | Ce qu'il fait |
| --- | --- |
| `$accent` | accent : la note sonne plus fort |
| `$marcato` | accent fort |
| `$tenuto` | tenuto |
| `$fermata` | point d'orgue : tout le morceau s'arrête sur la note (durée double) ; aussi sur un silence |
| `$tr` | trille avec la note au-dessus (dans la tonalité du morceau) |
| `$mordent` | mordant : note, note en dessous, note |
| `$turn` | gruppetto : au-dessus, note, en dessous, note |

```
4: c$accent d e$tenuto f$fermata | 2g$tr a$mordent b$turn |
4: [c e g]$accent$tenuto r$fermata
```

Trille, mordant et gruppetto sont joués sur les notes seules (sur les
accords et les blocs, ils restent un signe dans la partition).

**Indications de texte.** `$"texte"` écrit une indication au-dessus de la
portée à cet endroit : `$"rit."`, `$"dolce"`, `$"a tempo"`. Le son ne
change pas : pour ralentir vraiment, on utilise une rampe de tempo
(`tempo=100 << ... tempo=70`, section 2.6).

### 2.18 Octaves relatives et tonalité

Deux commandes rendent les mélodies beaucoup plus courtes à écrire. On
peut les utiliser ensemble, et elles sont facultatives : sans elles,
tout fonctionne comme avant.

**Octaves relatives (`rel:`).** Après `rel:`, on n'écrit plus l'octave :
chaque note va à l'octave **la plus proche de la note précédente** (au
plus une quarte au-dessus ou au-dessous, en comptant les lettres). Pour
sauter plus loin on ajoute `*+` (une octave au-dessus) ou `*-` (une octave
au-dessous), même répétés (`*++` deux octaves au-dessus, `*--` deux au-dessous) ; `*n` reste valable et fixe l'octave exacte.

```
rel: c d e f g a b c          // gamme de do jusqu'au do au-dessus
rel: c*5 b a g f e d c        // et en descendant
rel: g c*+ c*- c                // c*+ saute en haut, c*- redescend
```

La première note après `rel:` va près du do de l'octave par défaut de
l'instrument. Après un bloc `[...]` on repart de sa première note ; les
accords et les percussions ne comptent pas. `abs:` revient aux octaves
absolues. Dans les reprises et les groupes, chaque répétition repart de
la même note, pour sonner pareil.

**Tonalité (`key=`).** Après `key=G`, chaque note **sans** altération
prend celle de la tonalité : en sol majeur, `f` est fa dièse. Un dièse
ou un bémol écrit ne vaut que pour cette note ; `n` (ou `♮`) est le
bécarre et enlève l'altération de la tonalité.

```
key=G rel: g a b c d e f g    // sol majeur sans écrire le dièse
key=Bb rel: b c d e f g a b   // si bémol majeur : b et e sont bémols
key=Dm rel: d e f g a b c# d  // ré mineur (si bémol) avec le do dièse
key=G f fn f#                 // fa dièse, fa bécarre, fa dièse
```

`key=off` enlève la tonalité. Les accords (`C`, `F7`...) ne changent pas :
les symboles sont toujours absolus. La tonalité du morceau (dans la barre
du haut) sert à l'armure de la partition ; `key=` dit comment lire les
notes de la piste.

Les **patterns** (`%Nom`) se lisent toujours avec des octaves absolues et
sans tonalité, quel que soit le mode de la piste qui les utilise : ils
sonnent pareil partout.

**Réécrire une piste existante.** Le bouton **Hauteurs relatives et
tonalité**, sous l'éditeur, réécrit la piste courante avec `rel:` et, si
le morceau a une tonalité, `key=` : les notes restent les mêmes, le texte
devient plus court. C'est pratique après un import MIDI, MusicXML ou ABC.
**Transposer** (sur les boîtes) connaît aussi les deux modes : en `rel:`
les notes restent relatives, et avec `key=` la tonalité est transposée
aussi.

### 2.19 Micro-timing, accordage, nombreuses pistes, MTXT

**Micro-timing (`shift=`).** `shift=N` fait jouer les notes qui suivent N
millisecondes **plus tard** (N positif) ou **plus tôt** (N négatif) que
là où elles sont écrites ; `shift=0` les remet en place. Le rythme écrit
ne change pas : contrôles de mesure et partition restent identiques,
seul le moment où les notes sonnent change. De -500 à 500.

```
4: kick shift=20 snare shift=0 kick shift=20 snare   // caisse claire un peu en arrière
shift=-10 8: c c g g a a g g                          // basse qui pousse en avant
```

Il sert au « feeling » et à aligner une partie sur un enregistrement ;
les vrais rythmes s'écrivent avec les valeurs, les n-olets et le swing.

**Accordage (`tune=`).** `tune=N` accorde l'instrument de N cents (de
-100 à 100 : 100 cents font un demi-ton). C'est une automation comme
`vol=` ou `bend=` : elle vaut pour toute la piste, même pendant une
note, et accepte les rampes.

```
tune=-20 4: c d e f              // pour jouer avec un disque accordé un peu bas
tune=0 >> 4: c d e f tune=50     // monte d'un quart de ton en quatre notes
```

**Plus de 15 pistes.** Chaque piste a toujours son propre canal MIDI : à
partir de la 16e piste mélodique, l'export MIDI utilise un deuxième
« port » (16 canaux de plus), puis un troisième, etc. SoundText les joue
et les réimporte correctement ; certains lecteurs MIDI très anciens
ignorent les ports et jouent ces pistes sur les canaux des premières.

**MTXT.** **Projet → Exporter → MTXT...** écrit le morceau en
[MTXT](https://github.com/Daninet/mtxt), un format texte avec un
événement par ligne et les temps en noires (`1.5 note C4 dur=0.5
vel=0.8`), facile à lire, à comparer et à faire modifier par une IA. Il
contient notes, instruments, automations, tempo et mesure, comme le
MIDI. **Projet → Importer → MTXT...** fait l'inverse : il lit le
fichier comme un MIDI (une piste par canal, avec les noms des canaux).
La bibliothèque fait de même en ligne de commande avec
`st-language mtxt morceau.st` et `st-language mtxt fichier.mtxt` (qui
devient un `.mid`).

### 2.20 Ancres de mesure (`bar=`)

**Où entre une partie.** `bar=N` amène le curseur au **début de la
mesure N**, avec les silences nécessaires : au lieu de compter des
pauses (`28%Rest`) on écrit la mesure où la partie entre.

```
Guitar 2:
  bar=29                          // la seconde guitare entre à la mesure 29
  8: 100@ c d e f g a b c
```

- Si la piste est **avant** ce point, le trou est comblé par du silence ;
  si elle est **exactement** là, il ne se passe rien.
- Si la piste est **déjà au-delà** (une partie plus longue que prévu),
  l'ancre ne revient pas en arrière : la partie continue où elle est et
  l'éditeur affiche un **avertissement** sur l'ancre (« mesure 29 : la
  piste a déjà dépassé le début de 2 noires »), comme pour les contrôles
  de mesure `|`.
- Les mesures se comptent comme dans le reste du programme : à partir de
  1, selon la mesure du morceau et ses changements. Dans un pattern ou un
  groupe répété, c'est la mesure du morceau qui compte à chaque
  répétition.
- Une liaison `~` ne peut pas traverser une ancre qui demande du silence.

`bar=` positionne et `|` vérifie : ensemble ils disent où doit se trouver
chaque partie et avertissent quand l'une s'est décalée. Dans **Extraire
des patterns**, les blocs contenant une ancre ne sont pas extraits, car
un pattern ne sait pas dans quelle mesure il se trouve.

### 2.21 Transposition (`transpose=`, `%Nom+N`)

**Transposer sans réécrire.** `transpose=N` fait sonner les notes,
accords, slides et blocs suivants N demi-tons **plus haut** (N positif)
ou **plus bas** (N négatif) que ce qui est écrit ; `transpose=0` revient
à la hauteur écrite. De -60 à 60.

```
4: c d e f g a b c*5              // en Do
transpose=2 4: c d e f g a b c*5  // la même mélodie en Ré
transpose=0
```

**Un pattern dans une autre tonalité.** Après le nom d'un pattern on
écrit de combien de demi-tons le transposer : `%Theme+7` le joue une
quinte plus haut, `%Theme-12` une octave plus bas, `2%Theme+3` deux fois,
trois demi-tons plus haut. Pas besoin de patterns copiés : le thème
s'écrit une seule fois.

```
Pattern %Theme:
  key=Eb 8: 90@ g*5 b*5 e*6 2d*6 2b*5 |

Violini1:
  %Theme  %Theme-3  %Theme+12   // Mi bémol, puis Do (-3), puis une octave plus haut
```

- La transposition vaut pour **tout** ce qui est dans le pattern, y
  compris les patterns qu'il appelle, et **s'ajoute** à celle déjà en
  vigueur (`transpose=3 %Theme+4` sonne 7 demi-tons plus haut).
- Un `transpose=` écrit dans un pattern se termine avec le pattern.
- Il en va de même pour la bibliothèque MIDI : `&"Basse"+7`, `&"Basse"-12`
  (section 5).
- Avec `key=` les notes transposées s'écrivent dans la nouvelle
  tonalité : `key=G` avec `transpose=2` donne La majeur (le fa dièse écrit
  devient sol dièse, le sol devient la). Sans tonalité, un bémol reste
  bémol et les autres notes altérées prennent le dièse. Aussi dans la
  partition.
- Les accords changent de nom (`C7/E` +5 donne `F7/A`) et montent d'une
  octave quand ils passent le Do ; avec +12 chaque accord monte d'une
  octave.
- Les percussions et les silences ne changent pas. Si une note transposée
  sort de l'étendue MIDI, le programme le signale comme une erreur.
- **Extraire des patterns** n'extrait pas les blocs qui contiennent un
  `transpose=` : dans un pattern la transposition s'arrêterait avec le
  pattern.

### 2.22 `reset:`, levée et version du fichier (ST 2.6)

**`reset:` — repartir de zéro.** Remet tout à l'état initial : grille
`4:`, vélocité 80, ni swing ni décalage, transposition 0, octaves
absolues, aucune tonalité. Les automations (`vol=`, `pan=`...) restent
où elles sont. Utile quand un morceau de texte doit sonner pareil quoi
qu'il y ait avant :

```
rel: key=G 8: 100@ transpose=2 g a b c
reset: c d e f           // de nouveau des noires, vélocité 80, do majeur
```

Chaque box de la vue Structure commence par un `reset:` : ainsi un
`transpose=` ou un `key=` écrit dans un box ne passe jamais au box
suivant.

**Mesure en levée.** Si le morceau commence par une levée, indiquez
combien de noires elle dure dans le champ **Levée** de la barre du
morceau (ou `Levare: 1` dans le fichier). La mesure 1 devient la
première complète : les contrôles de mesure `|`, les ancres `bar=N`, les
changements de tempo et de mesure par mesure, la règle de la vue
Structure, le métronome et la partition comptent à partir de là. La
levée est la mesure 0.

```
Levare: 1
Metrica: 3/4

Violino:
  4: g | c e g | c*5 2r |      // une noire en levée, puis des mesures à 3/4
```

**Noms des fichiers MIDI entre guillemets.** Le nom d'un fichier de la
bibliothèque MIDI s'écrit toujours entre guillemets : `&"Riff"`,
`&"Blues/bass-line"`, espaces compris (`&"intro take 2"`). Ce qui suit les
guillemets est toujours la transposition : `&"Riff"-2` est le fichier
`Riff` deux demi-tons plus bas, `&"take-2"` est le fichier qui s'appelle
`take-2`. Les morceaux écrits avant (avec `&Riff`) sont convertis tout
seuls à l'ouverture, et restent identiques ; si vous écrivez `&Riff` sans
guillemets, l'éditeur vous indique comment le corriger.

**Version et mots anglais dans le fichier.** Le fichier `.st` commence
par `ST: 2.7`, la version du langage dans laquelle il est écrit ; en
ouvrant un fichier d'une version plus récente, le programme avertit. Le
programme lit aussi les mots-clés en anglais (`Track`, `Instrument`,
`Meter`, `Key`, `Pickup`, `percussion=`, `octave=`, `yes`), pratique pour
qui écrit les fichiers à la main ; à l'enregistrement il utilise toujours
les formes italiennes.

### 2.23 Accords, notes d'agrément, D.C./D.S., couplets et titre (ST 2.7)

**Plus d'accords.** En plus des habituels : `C7#5` (aussi `Caug7`),
`C7b5`, `Cm11`, `Cm13`, `C69` (sixte et neuvième : dans `C6/9` la barre
serait la basse), `Cmaj7#11`, `C7#11`, `C9sus4`, `C7b13`, `Cadd11`,
`Cmadd9`, `C7sus2`, `Csus` (= `Csus4`), `C13b9`.

**Plus de percussions.** Le reste de la batterie General MIDI :
`triangle`, `triangle_mute`, `agogo_hi`, `agogo_low`, `guiro_short`,
`guiro_long`, `whistle_short`, `whistle_long`, `cuica_mute`,
`cuica_open`, `vibraslap` et `side_stick` (le même son que `rimshot`).

**Valeurs et tempo.** `c'128` est la quadruple croche ; la lettre `D` fait
les duolets (`8D: c d`, deux croches dans le temps de trois, comme en
6/8). Le tempo accepte les décimales (`tempo=72.5`) et la figure comptée :
`tempo=60'4.` font 60 noires pointées par minute ; la partition écrit
ainsi le métronome.

**Notes d'agrément.** `d'g c` est une acciaccatura (le ré avant le do),
`d'G c` une appoggiature ; elles marchent aussi sur les accords, les
blocs et les percussions (`snare'g snare` est un fla). Elles ne prennent
pas de temps écrit : elles sonnent juste avant la note, qui perd cette
durée.

**Nouveaux signes sur les notes.** `C$arp` (accord arpégé),
`c$staccatissimo`, `c$sfz` (sforzando), `c$fp` (forte-piano), `c$trem`
(trémolo ; à la batterie `snare$trem` est un roulement), `c$harmonic`
(harmonique).

**Grilles d'accords sans son.** `$Am7` écrit l'accord au-dessus de la
portée sans le jouer : pratique pour un lead sheet avec seulement la
mélodie (`$C c d e f $G7 g a b c`).

**D.C., D.S., Coda et Fine.** Ils s'écrivent comme des signes : `$segno`,
`$coda`, `$tocoda`, `$fine`, `$dc` (da capo), `$ds` (dal segno). Ils se
jouent comme un musicien les joue ; au retour les reprises se font une
seule fois, avec la dernière fin :

```
4: c d e f | g a b c*5 $fine | e d c d | 4e $dc     // D.C. al Fine
4: $segno c d e f | g a b c*5 $tocoda | 4e $ds $coda | 4c |   // D.S. al Coda
```

**Plusieurs couplets.** Des paroles qui commencent par le numéro du
couplet vont sous la même musique : `"Ma- ry had a lit- tle lamb"` puis
`"2: Ev- ry where that Ma- ry went"`. La partition écrit une ligne par
couplet.

**Titre, auteurs, changements de tonalité, instruments transpositeurs.**
En haut du fichier `.st` on peut écrire `Titolo:` (ou `Title:`),
`Autore:` (`Composer:`) et `Parole:` (`Lyricist:`), qui vont dans la
partition, et la tonalité par mesure comme le tempo :
`Tonalita: 1: C, 17: G`. Dans un instrument défini dans le fichier,
`trasposizione=-2` le rend transpositeur (trompette en si♭ : -2, saxo
alto en mi♭ : -9) : on écrit toujours en sons réels et la partition écrit
sa partie transposée. Le fichier enregistré déclare `ST: 2.7`.

## 3. État courant

La grille et la vélocité restent actives tant qu'on ne les change pas à
nouveau :

```
100@ 8: c e 60@ g a 100@ c
```
`c` et `e` durent une croche à la vélocité 100 ; `g` et `a` à la vélocité
60 ; le dernier `c` revient à la vélocité 100. Les commandes d'état ne
génèrent aucun événement : elles n'occupent pas de temps sur la timeline.

## 4. Patterns (%Nom)

On les définit dans la bibliothèque de patterns (menu **Composer →
Gérer la bibliothèque de patterns**) ou directement dans le fichier `.st` :

```
Pattern %GtrArp:
  16: 90@ c e g e 70@ c e g e
```

et on les appelle dans n'importe quelle piste avec `%GtrArp`.

**Répétition :** en mettant un nombre devant, on répète le pattern N fois :
```
3%GtrArp        -> joue %GtrArp trois fois de suite
```

### 4.1 Écouter un pattern

Dans la fenêtre **Composer → Gérer la bibliothèque de patterns**,
chaque pattern sélectionné peut être écouté avec le bouton **▶ Écouter**, en
choisissant l'instrument d'aperçu dans la liste à côté (le pattern reste de
toute façon universel : le choix sert seulement au test audio). Les
modifications pas encore enregistrées dans l'éditeur sont incluses
automatiquement dans l'aperçu. Pendant la lecture, le passage que vous
écoutez est surligné dans le corps du pattern, comme dans l'éditeur
principal et dans les fenêtres de modification du box, de génération, de
« Jouer au clavier » et de conversion audio.

### 4.2 Réorganiser le morceau avec les patterns

Menu **Composer → Extraire des patterns des pistes...** : analyse
toutes les pistes du projet courant, repère des blocs d'événements qui se
répètent (même de façon non consécutive) et les convertit automatiquement
en patterns réutilisables, en remplaçant les occurrences par `%Nom` (avec
répétition `N%Nom` quand les occurrences sont consécutives). Le contenu
musical ne change pas : ce n'est qu'une réécriture plus compacte et plus
lisible de la même suite d'événements. Si aucune répétition assez longue
n'est trouvée, le programme le signale sans rien modifier.

Les patterns générés prennent le nom de l'**instrument de la piste** d'où
ils viennent (ex. `%Guitar1`, `%Guitar2`, `%Bass1`...), pas un préfixe
générique. De plus, un pattern extrait **ne contient jamais de références à
d'autres patterns** : si une piste utilise déjà `%Lib1` avec du matériel
littéral répété, `%Lib1` reste une référence à part et n'est jamais inclus
dans un nouveau pattern (pas de patterns imbriqués).

Menu **Composer → Développer les patterns dans les pistes...** :
l'opération inverse. Elle remplace chaque référence `%pattern` et `&"midi"`
présente dans les pistes par les tokens littéraux correspondants
(répétition déjà appliquée), ce qui rend le projet entièrement autonome ;
les patterns qui ne servent plus sont supprimés. Utile avant de partager un
morceau sans devoir y joindre la bibliothèque de patterns, ou pour
inspecter/modifier à la main chaque événement sans l'indirection des
références.

Les deux opérations agissent sur tout le projet, demandent une confirmation
avant de s'appliquer et s'exécutent en arrière-plan avec une barre de
progression : l'interface reste réactive et l'opération peut être annulée.
Le temps de recherche des blocs répétés est de toute façon toujours limité
(par piste), de sorte que même sur des pistes très longues la
réorganisation ne reste jamais bloquée indéfiniment.

### 4.3 Menu contextuel sur une sélection (clic droit)

En sélectionnant à la souris une suite de tokens dans l'éditeur (piste,
corps d'un pattern ou d'un box) et en cliquant avec le **bouton droit**, on
ouvre un menu contextuel avec trois entrées. Dans les aperçus des fenêtres
(Générer batterie/basse/accompagnement/grille d'accords, Jouer au clavier,
conversion audio, bibliothèque MIDI) le menu n'a que **▶ Play**, et il
arrête d'abord l'éventuelle écoute de l'aperçu entier :

- **▶ Play** : joue seulement la sélection, avec l'instrument de la piste
  courante, en reconstruisant automatiquement la dernière grille rythmique
  et la vélocité actives avant la sélection (ainsi elle sonne comme dans son
  contexte d'origine, pas toujours à 1/4 et vélocité 80).
- **Grouper** : entoure la sélection de parenthèses, la transformant en
  groupe `(...)` (voir section 2.1) ; utile avant de lui appliquer à la main
  un multiplicateur de répétition (ex. transformer `(...)` en `4(...)`).
- **Transformer en pattern...** : demande un nom, crée un nouveau pattern
  contenant la sélection et remplace la sélection elle-même par
  `%NomPattern` — un moyen rapide d'extraire à la main un seul fragment en
  pattern, en alternative à la recherche automatique de **Extraire des
  patterns des pistes...** (section 4.2).

La sélection faite à la souris est toujours « accrochée » aux limites des
tokens entiers qu'elle touche (inutile de sélectionner avec une précision
millimétrique) ; si le dernier token inclus est une commande d'état sans
suite (`N:` ou `N@`), il est écarté automatiquement, ainsi le groupe ou le
pattern obtenu ne se termine jamais « en suspens » sans événement sonore.

Si la sélection contient aussi une référence à un pattern (`%Nom`) ou à un
fichier MIDI (`&"Nom"`), le menu n'affiche **que Play** : grouper ou
transformer en nouveau pattern une indirection déjà existante n'est pas
autorisé.

### 4.4 Renommer un pattern

Le bouton **Renommer** (à côté de « Nouveau » dans la fenêtre **Composer → Gérer la bibliothèque de patterns**) renomme le pattern sélectionné
et met à jour automatiquement vers le nouveau nom toutes les références
`%ancien_nom` déjà présentes — dans les pistes comme dans le corps des
autres patterns — pour que le renommage ne casse pas en silence ce qui
l'appelle. Le nouveau nom doit respecter la même syntaxe qu'une référence de
pattern (lettres, chiffres et tirets bas, sans espaces) et ne peut pas être
celui d'un pattern existant.

## 5. Bibliothèque MIDI (&"Nom")

Dans le dossier `midi/` (à côté du programme, vide après une première
installation : la bibliothèque est la vôtre) vous pouvez conserver de
courtes phrases musicales sous forme de fichiers `.mid`, organisées aussi en
sous-dossiers par catégorie (genre, artiste, instrument...), par exemple :

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
    └── vos_projets.st
```

Une référence `&"Nom"` cherche **récursivement dans tous les sous-dossiers** :

```
Guitar:
  &"Intro" &"Intro" %GtrArp
```

si vous avez un fichier `midi/Guitar/Intro.mid`, il le trouve
automatiquement (ou tout autre sous-dossier contenant un fichier
`Intro.mid`), sans indiquer le chemin.

**Chemins qualifiés :** si le même nom existe dans plusieurs sous-dossiers,
la référence est ambiguë et la validation le signale en indiquant les
alternatives trouvées ; pour lever l'ambiguïté il suffit de qualifier le
chemin :

```
&"Blues/bass_line"      -> utilise précisément midi/Blues/bass_line.mid
```

**Répétition** (comme pour les patterns) :

```
2&"bass_line"            -> répète la référence deux fois
```

**Transposition :** comme pour les patterns, un nombre après le nom
transpose le fichier de ce nombre de demi-tons : `&"Intro"+7` le joue une
quinte plus haut, `&"Intro"-12` une octave plus bas, `2&"Intro"+2` deux fois,
deux demi-tons plus haut (section 2.21). Le nom est entre guillemets,
donc tirets et espaces ne posent aucun problème : `&"Blues/bass-line"-2`
est `Blues/bass-line` deux demi-tons plus bas (section 2.22).

Gestion depuis l'interface : menu **Composer → Gérer la
bibliothèque MIDI**. De là vous pouvez importer un fichier `.mid` existant
(en indiquant aussi un sous-dossier de destination), le renommer/déplacer,
le supprimer, l'écouter avec **▶ Écouter le fichier d'origine** (joue le
fichier .mid tel quel, avec tous ses canaux), ou en voir/modifier un aperçu
textuel (le canal avec le plus de notes est converti) et « régénérer » le
fichier MIDI à partir du texte modifié, en choisissant l'instrument à
utiliser pour le voicing. Quand vous renommez ou déplacez un fichier et que
le morceau ouvert l'appelle, le programme propose de mettre à jour les
appels `&"Nom"` (aussi dans les box et les motifs), en gardant
multiplicateur et transposition.

Remarque : `&"Nom"` n'importe que le canal le plus significatif du fichier
MIDI (en général celui qui a le plus de notes) ; pour un import multipiste
complet utilisez plutôt **Projet → Importer → MIDI...**, qui crée une piste
par canal.

## 5bis. Dossier des morceaux (songs/)

Les fenêtres **Ouvrir un projet** et **Enregistrer sous** s'ouvrent par
défaut sur le dossier `songs/` (à côté du programme) : c'est l'endroit prévu
pour vos compositions, distinct de `examples/`, qui contient les projets de
démonstration des fonctionnalités du programme.

## 6. Percussions

36 identifiants fixes, associés au General MIDI Drum Map (canal 10) et sans
prise en charge des octaves. Dans l'ordre, ils correspondent aux touches
utilisées dans « Jouer au clavier » (section 10ter) : rangée des chiffres
(1-9, puis 0 ' ì), rangée Q, rangée A.

- Kit de base (rangée des chiffres) : `kick`, `snare`, `hihat`,
  `hihat_open`, `tom1`, `tom2`, `floor`, `crash`, `ride`, `kick2`,
  `rimshot`, `clap`.
- Autres toms/cymbales/charlestons (rangée Q) : `snare2`, `hihat_pedal`,
  `tom_lowmid`, `tom_hi`, `tom_highfloor`, `china`, `ride_bell`,
  `tambourine`, `splash`, `cowbell`, `crash2`, `ride2`.
- Percussions latines (rangée A) : `bongo_hi`, `bongo_low`, `conga_mute`,
  `conga_open`, `conga_low`, `timbale_hi`, `timbale_low`, `cabasa`,
  `maracas`, `claves`, `woodblock_hi`, `woodblock_low`.

## 7. Pistes et instruments

- **Ajouter une piste** : bouton **+ Ajouter une piste** (sous le dernier
  en-tête, dans la vue Structure du morceau comme dans la vue Texte) ou menu **Piste → Ajouter**. Le bouton ouvre un menu avec :
  - **Piste avec instrument...** (Ctrl+T) et **Piste audio...** ;
  - **Générer une piste** : **Batterie**, **Grille d'accords**, **Basse
    depuis les accords**, **Accompagnement ou riff** (pour ce dernier on
    choisit l'instrument : polyphonique = accompagnement, monophonique =
    riff/mélodie). La fenêtre du générateur s'ouvre et la piste n'est créée
    que si vous confirmez, déjà remplie (un box dans la vue Structure, du
    texte dans la vue Texte). La basse et l'accompagnement suivent les
    accords d'une autre piste : tant que le morceau n'en a pas, ils restent
    désactivés, avec la raison écrite à côté ;
  - **Piste depuis un fichier MIDI...** : un canal d'un fichier MIDI devient
    une nouvelle piste, avec l'instrument reconnu dans le fichier.
- **Actions sur une piste** (générer, jouer au clavier, importer du MIDI ou
  de l'audio, nom et instrument, exporter en MIDI, supprimer) : menu **⋯**
  de l'en-tête de la piste (dans les deux vues), ou clic droit sur
  l'en-tête ; elles restent aussi dans le menu **Piste**.
- **Renommer / changer d'instrument** : **⋯ → Nom et instrument...**, ou
  double-clic sur l'en-tête de la piste.
- **Instruments personnalisés** : menu **Sons → Gérer les
  instruments**. L'instrument se choisit **par son nom** dans une liste
  General MIDI complète, regroupée par famille (Pianos, Guitares, Basses,
  Cuivres, Anches...) et consultable en tapant (ex. « sax », « organ ») :
  pas besoin de connaître le numéro de programme. En choisissant un son,
  l'octave, l'étendue et le style de voicing les plus adaptés sont
  préremplis automatiquement (ex. les basses deviennent `root_fifth`, les
  cuivres `monophonic`), toujours modifiables à la main. Pour un instrument
  de percussion, cochez « Utiliser le canal des percussions (10) » au lieu
  de choisir un son. Paramètres disponibles : nom (un seul mot), octave par
  défaut, étendue (note MIDI la plus grave et la plus aiguë jouable) et
  style de voicing des accords :
  - `spread` : répartit toutes les notes de l'accord (adapté au
    piano/à la guitare)
  - `root_fifth` : seulement la fondamentale (+ la quinte si présente),
    adapté à la basse
  - `monophonic` : seulement la fondamentale, pour les instruments
    mélodiques monophoniques
  - `root_only` : seulement la fondamentale
- **SoundFont par instrument** : depuis **Sons → Gérer les
  instruments...** vous pouvez aussi associer à un seul instrument
  (prédéfini ou personnalisé) un fichier `.sf2` différent de celui par
  défaut — voir la section 12.4 plus bas.

### 7.1 Chargement automatique des instruments personnalisés

Quand vous enregistrez un projet qui utilise un ou plusieurs instruments
personnalisés, leur définition (programme GM, octave, étendue, voicing...)
est **incluse directement dans le fichier `.st`**, dans un bloc `Strumento
Nom:` écrit avant les patterns et les pistes. Ainsi, si vous ouvrez ce
projet sur une autre installation (ou après avoir nettoyé votre
configuration locale) et que l'instrument n'est pas encore disponible, il
est **enregistré automatiquement** à la volée, et la piste qui l'utilise
n'est pas perdue. Le programme affiche un avis avec la liste des
instruments chargés de cette façon.

Si un instrument du même nom existe déjà sur le système, la définition
incluse dans le fichier **ne l'écrase pas** dans la liste des instruments
(vos modifications faites à la main restent), mais **les pistes de ce
morceau utilisent la définition du fichier** : un morceau sonne toujours
comme il est écrit, même si vous avez d'abord ouvert un autre morceau qui
définit autrement un instrument du même nom (par exemple « Archi » ou
« Viole »).

Cela vaut aussi pour les pistes renommées avec **Modifier le
nom/l'instrument** : si le nom de la piste ne correspond plus à
l'instrument (ex. une piste « Guitar 1 » renommée en « SoloRinominato » et
passée à un autre instrument), le fichier utilise automatiquement un
en-tête explicite (`Traccia SoloRinominato [Bass]:`) au lieu de la forme
abrégée, pour que rien ne soit perdu à l'enregistrement.

## 8. Table de mixage

Chaque piste a **Mute (M)**, **Solo (S)**, **Volume** et **Pan**. Si au
moins une piste est en Solo, en lecture/à l'export on n'entend que les
pistes en Solo (qui ne sont pas aussi en Mute).

Les commandes sont dans l'**en-tête** de chaque piste, identique dans les
deux vues : dans la vue Structure du morceau à gauche de chaque ligne, dans
la vue Texte dans la colonne **Pistes** à gauche (là il sert aussi à
choisir la piste dont on modifie le texte). L'en-tête contient :

- nom et instrument, **M**, **S**, **●** (pistes audio seulement :
  enregistrer), **FX** (ouvre le panneau Effets, voir 8.3 et 8.4) et le menu
  **⋯** avec toutes les actions de la piste (générer, jouer au clavier,
  importer du MIDI ou de l'audio, nom et instrument, exporter en MIDI,
  supprimer) ;
- à droite, deux boutons rotatifs : **Vol** (volume, la valeur en %) et
  **Pan** (C = centre, L/R = gauche/droite). On les tourne en faisant
  glisser vers le haut/bas (plus finement avec Maj), avec la molette ou avec
  les flèches ; double-clic = retour à 100 % / au centre.

Clic sur l'en-tête = sélectionner la piste ; double-clic =
renommer/changer d'instrument ; clic droit = même menu que ⋯. Sous le
dernier en-tête, **+ Ajouter une piste** (voir section 7).

### 8.1 Volume : 0-200 %, il agit directement sur la vélocité des notes

Le bouton Volume va de 0 % à 200 %, où **100 % est l'intensité d'origine**
des notes telles qu'écrites dans la piste (aucune modification). Tourner le
bouton modifie directement la vélocité de chaque note de la piste à
l'export/à la lecture — pas seulement le Channel Volume MIDI (CC7), dont la
courbe de réponse est faible ou peu perceptible sur beaucoup de
synthétiseurs. Cela rend la commande efficace avec n'importe quel moteur de
lecture :

- sous 100 % : la piste joue plus doucement que l'original ;
- au-dessus de 100 % (jusqu'à 200 %) : la piste est renforcée au-delà de
  l'original, utile pour faire ressortir un instrument trop faible dans le
  mixage ;
- la vélocité obtenue reste de toute façon dans les limites MIDI valables
  (1-127).

Les réglages de Volume, Pan, Mute et Solo de chaque piste sont enregistrés
dans le fichier `.st` (bloc `Mixer <Nom de piste>:`) et rétablis
automatiquement à la réouverture du projet.

### 8.2 Volume master

En plus du Volume de chaque piste (8.1), la barre d'outils principale a un
curseur **Master** (0-200 %, même échelle et même convention : 100 % = gain
d'origine) qui règle ensemble le volume de **toutes** les pistes, en plus
du volume déjà réglé sur chacune — utile pour un ajustement général du
niveau sans devoir toucher chaque piste une à une. Comme pour
Mute/Solo/Volume/Pan de piste, une modification du Master pendant la
lecture relance automatiquement la lecture depuis la position actuelle avec
la nouvelle valeur (avec un court délai si on le fait glisser à la souris,
pour ne pas empiler une relance à chaque cran). La valeur master est
enregistrée dans le fichier `.st` (ligne `Master: N`, écrite seulement si
elle diffère des 100 % par défaut) et rétablie à la réouverture du projet.

### 8.3 Réverbération et chorus (FX)

Le bouton **FX** de chaque piste, dans son en-tête (dans les deux vues),
ouvre en bas de la fenêtre le **panneau Effets** (voir 8.4). Pour les pistes
de texte, la première carte, **Envoi rapide**, contient les effets du
synthé :
- **Réverbération** (0-100 %) : quelle part de la piste va à la
  réverbération, de sèche (0 %) à très « mouillée » ;
- **Chorus** (0-100 %) : élargit et « double » le son (cordes, pads,
  guitares claires, chœurs) ;
- **Ambiance**, une seule pour **tout le morceau** : l'espace dans lequel
  toutes les pistes envoient leur réverbération. Petite pièce (par défaut),
  Salle, Grande salle ou Église.

Le bouton FX s'allume (bleu clair) quand la piste a de la réverbération, du
chorus ou des effets de la chaîne, et son info-bulle en montre les valeurs.

Ce sont les effets déjà présents dans le synthé (fluidsynth) : on les
entend tout de suite à l'écoute normale, sans traitement supplémentaire, et
pendant la lecture l'écoute redémarre d'elle-même comme pour le volume et
le pan.
- **Enregistrement :** réverbération et chorus vont dans le bloc `Mixer` de
  la piste (`riverbero: 35 chorus: 10`), l'ambiance dans la ligne
  `Ambiente: sala` en tête du fichier. Les deux ne sont écrits que s'ils
  diffèrent de la valeur par défaut : les projets qui ne les utilisent pas
  restent identiques.
- **Export :** réverbération et chorus valent pour l'écoute et pour les
  exports WAV et MIDI (contrôleurs CC91 et CC93). L'ambiance ne vaut que
  pour l'écoute et le WAV : le fichier MIDI ne peut pas la contenir, et le
  lecteur qui l'ouvre utilise la sienne.
- **Import MIDI :** un fichier avec réverbération et chorus réglés sur les
  canaux (CC91/CC93 au début du morceau) les reporte dans les pistes
  importées.

À savoir :
- **Petite pièce :** c'est l'ambiance habituelle de fluidsynth (ainsi les
  projets existants sonnent comme avant), mais la réverbération s'y entend à
  peine. Pour un effet net choisissez **Salle** ou **Grande salle** : la
  carte vous le rappelle quand vous montez la réverbération avec la petite
  pièce.
- **Changement d'ambiance :** même avec la réverbération à 0, changer
  d'ambiance peut modifier légèrement le son, parce que certains SoundFonts
  envoient déjà d'eux-mêmes une partie de leurs instruments à la
  réverbération.
- **Pistes audio :** elles n'ont pas d'Envoi rapide, parce que ces effets
  appartiennent au synthé, qui ne joue que les pistes de texte ; elles ont
  en revanche la chaîne d'effets (8.4).
- **Jouer au clavier :** l'écoute en direct n'applique pas encore la
  réverbération et le chorus de la piste.

### 8.4 Chaîne d'effets et panneau Effets

Chaque piste, de texte ou audio, peut avoir une **chaîne d'effets** : le son
de la piste passe d'un effet au suivant, de gauche à droite. Les effets
disponibles, divisés par famille dans le menu **+ Effet** :

- **Dynamique :**
  - **Compresseur** (seuil, taux, attaque, relâchement, gain) : rend le
    niveau plus régulier (voix, basse, batterie) ;
  - **Limiteur** (gain, plafond, relâchement) : monte le volume de la piste
    de « Gain » sans que les crêtes dépassent jamais le « Plafond » (ex.
    −1 dB). Préréglages Sécurité (seulement protection des crêtes), Plus
    fort, Beaucoup plus fort ;
  - **Noise gate** (seuil, taux, attaque, relâchement) : rend la piste
    muette quand elle descend sous le seuil, pour enlever souffle,
    ronflement et bruits entre les phrases dans les pistes audio
    enregistrées. S'il coupe le début ou la fin des notes, baissez le seuil
    ou allongez le relâchement.
- **Tonalité :**
  - **EQ 3 bandes** (basses, médiums, aigus, ±12 dB chacun) ;
  - **Filtre passe-haut** (fréquence 20 Hz–2 kHz, pente 6–24 dB/octave) :
    enlève les graves sous la fréquence. L'usage classique est « Nettoyage
    des basses » (80 Hz) sur la voix et les guitares, pour laisser de la
    place à la basse et à la grosse caisse ;
  - **Filtre passe-bas** (fréquence 200 Hz–20 kHz, pente 6–24 dB/octave) :
    enlève les aigus au-dessus de la fréquence, pour un son plus sombre,
    étouffé ou « derrière une porte ». Plus la pente est forte, plus la
    coupure est nette.
- **Saturation :**
  - **Amplificateur** (modèle, baffle, gain, basses, médiums, aigus,
    présence, puissance, niveau) : un amplificateur de guitare complet,
    dans l'ordre préamplificateur → contrôles de tonalité → étage de
    puissance → baffle. Les **modèles** : *Clair* (presque sans saturation),
    *Crunch* (blues, rock léger), *British* (rock classique, médiums en
    avant, deux étages de saturation), *High gain* (metal, basses serrées et
    beaucoup de saturation).

    **Basses, Médiums, Aigus** (de 0 à 10, comme sur les vrais
    amplificateurs) sont le circuit de tonalité (« tone stack ») des vrais
    amplificateurs, calculé d'après les valeurs de ses composants : celui de
    **Fender** pour Clair et Crunch, celui de **Marshall** pour British et
    High gain. Comme sur les originaux, les boutons s'influencent entre eux
    (monter les Aigus touche aussi les médiums), à mi-course les médiums
    sont déjà un peu « creusés » (davantage sur le Fender), les Médiums à 0
    donnent le creux profond du metal et le volume change un peu quand on
    les tourne, comme sur un vrai amplificateur.

    **Saturation qui dépend de la fréquence.** Comme dans les vrais étages à
    lampes, les graves saturent moins que les médiums et les aigus : les
    notes graves et les accords sur les cordes graves (power chords) restent
    définis au lieu de « baver », tandis que les notes médiums saturent
    comme on s'y attend. Plus le modèle est poussé (British, High gain),
    plus l'effet est marqué. Cela n'enlève pas de graves au son : cela
    change la façon dont ils saturent, pas leur quantité.

    **Réponse au toucher.** Le point de fonctionnement des lampes se déplace
    lui aussi comme dans les vrais amplificateurs : sur les coups forts
    l'étage perd un instant un peu de gain et sature de façon asymétrique
    (harmoniques paires, plus « chaudes »), puis en un dixième de seconde
    environ il « respire » et revient comme avant. En jouant doucement le
    son reste clair, en attaquant fort il se salit de façon dynamique :
    c'est l'effet le plus évident avec Crunch et British (le son « qui
    répond au médiator »), plus contenu avec High gain et presque absent
    avec Clair. Après chaque étage il y a aussi le filtre des condensateurs
    de liaison, qui enlève le « grondement » dans l'infra-grave que la
    saturation asymétrique créerait sous les accords graves.

    **Présence** (0-10) règle les aigus après l'étage de puissance, comme le
    bouton du même nom des amplificateurs à lampes : plus d'« air » et de
    mordant sans rendre le préamplificateur agressif.

    **Puissance** (0-100 %) indique à quel point on pousse l'étage final :
    les lampes de puissance saturent de façon douce et asymétrique (avec des
    harmoniques paires, le son « chaud » des lampes) et l'alimentation qui
    faiblit sur les coups forts (« sag ») comprime un peu les accords tenus.
    0 % = étage final clair ; 30-50 % est le son d'un amplificateur joué
    fort ; au-delà, le son s'arrondit et se comprime.

    Les **baffles** : *Combo 1×12*, *2×12*, *4×12 fermé* (plus de corps
    dans les graves), *Vintage 1×10* (plus fin et nasillard), ou *Aucun*
    pour le son direct de l'amplificateur. Les baffles sont simulés par
    SoundText (aucun fichier à télécharger) et, comme les vrais, ils coupent
    les aigus au-dessus de 5-6 kHz : c'est pourquoi un amplificateur sonne
    « chaud » même avec beaucoup de gain. Préréglages : Clair brillant,
    Blues, Vintage, Rock classique, Metal. « Niveau » compense le volume :
    plus de gain veut dire plus de volume, baissez-le donc en montant le
    gain. Il fonctionne sur les pistes de guitare (de texte ou enregistrées)
    et aussi sur la basse ou sur un orgue pour un son plus sale.

    **Baffle depuis un fichier IR.** Avec le baffle **Fichier IR…** on
    utilise la réponse impulsionnelle (IR) d'un vrai baffle, enregistrée
    avec un micro : un petit fichier WAV (on en trouve énormément de
    gratuits, de baffles célèbres et avec des micros différents). En
    choisissant « Fichier IR… » la fenêtre s'ouvre pour indiquer le
    fichier ; le bouton **Choisir l'IR…** sous les menus le change, et le
    nom du fichier apparaît à côté. Le fichier est lu en mono (moyenne des
    canaux), converti à 48 kHz s'il a une autre fréquence, limité à 1
    seconde, et normalisé comme les baffles intégrés, pour que changer de
    baffle ne fasse pas sauter le volume. Le chemin est enregistré dans le
    fichier `.st` (relatif au dossier du projet, comme pour les clips
    audio : `ir="ir/cassa.wav"`) : gardez l'IR près du projet si vous le
    déplacez sur un autre ordinateur. Si le fichier est introuvable, la
    carte l'écrit en rouge et le baffle Combo 1×12 est utilisé jusqu'à ce
    que vous en choisissiez un autre.

    **Qualité de la saturation.** Amplificateur et Distorsion saturent le
    son à 4 fois la fréquence d'échantillonnage (192 kHz ; l'étage de
    puissance, plus doux, à 2 fois) puis reviennent à 48 kHz avec des
    filtres à phase linéaire (« suréchantillonnage ») : ainsi les harmoniques
    produites par la saturation ne se replient pas en fréquences parasites,
    le classique « grésillement » numérique sur les notes aiguës avec
    beaucoup de gain. Cela n'ajoute pas de retard ; le traitement est un
    peu plus lent (quelques dixièmes de seconde pour la boucle de
    calibration, quelques secondes en arrière-plan pour une piste entière) ;
  - **Profil NAM** (entrée, baffle, niveau) : utilise un **vrai**
    amplificateur ou une vraie pédale, « capturés » avec **Neural Amp
    Modeler** (NAM). Un profil est un fichier `.nam` : un réseau de neurones
    entraîné en écoutant l'appareil d'origine, qui en reproduit le son très
    fidèlement. On en trouve des milliers, presque tous gratuits, sur
    **Tone3000** (tone3000.com) : amplificateurs célèbres, pédales
    d'overdrive et de distorsion, préamplificateurs, parfois avec le baffle
    inclus. Pour commencer, **Sons → Télécharger → Télécharger les profils NAM
    recommandés...** en télécharge une douzaine d'un coup (voir « Où trouver
    des profils NAM », plus bas).

    En ajoutant l'effet (**+ Effet → Saturation → Profil NAM**) la fenêtre
    s'ouvre pour choisir le fichier ; si vous annulez, l'effet n'est pas
    ajouté. La carte affiche le nom du profil et, si le fichier les déclare,
    marque, modèle, type (amplificateur, pédale, amplificateur avec
    baffle…) et auteur ; le bouton **Choisir un profil…** le change.
    - **Entrée** est le bouton « input » du plugin NAM : avec quelle force
      arrive la guitare. Plus haut = plus de saturation (comme jouer plus
      fort ou monter le gain de l'appareil d'origine, autant que la capture
      le permet), plus bas = plus clair.
    - **Baffle** : *Aucun / inclus* si le profil contient déjà le baffle
      (type « amplificateur avec baffle ») ou s'il s'agit d'une pédale à
      mettre devant un Amplificateur ; **Fichier IR…** pour ajouter la
      réponse d'un vrai baffle, comme dans l'Amplificateur (voir plus haut).
      Un profil de tête seule sans baffle sonne agressif et « bourdonnant » :
      donnez-lui une IR.
    - **Niveau** compense le volume. Comme le plugin, SoundText amène déjà
      chaque profil à la même sonie de référence (−18 dB) en utilisant la
      valeur écrite dans le fichier ; les profils plus anciens, qui ne
      l'écrivent pas, sont mesurés de la même façon que le fait NAM (avec
      son signal de référence), une seule fois. Ainsi changer de profil ne
      fait pas sauter le volume.

    Préréglages : Neutre, Plus poussé (+6 dB d'entrée), Plus propre (−6 dB).

    À savoir sur les profils NAM :
    - **Formats :** on utilise les profils WaveNet des deux générations,
      **A1** (les classiques *standard*, *lite*, *feather* et *nano*, la
      grande majorité des fichiers publiés) et **A2** (la plus récente), et
      aussi les profils **LSTM**, les réseaux récurrents des débuts de NAM.
      Beaucoup de fichiers A2 contiennent **plusieurs tailles** du même
      modèle, de la plus légère à la plus complète, pour que le plugin
      économise du processeur en direct : SoundText ne joue pas en temps
      réel et utilise toujours la taille **complète**, la meilleure. Sur la
      carte, à côté de la description, apparaît « format A2 » ou « format
      LSTM ». Le calcul suit celui du moteur officiel de NAM, vérifié en
      comparant les sorties ; avec les LSTM les différences restent sous
      −80 dB (arrondis de calcul, qu'un réseau récurrent traîne avec lui
      dans le temps), donc inaudibles. Un fichier d'un autre type (par
      exemple les très rares architectures expérimentales ConvNet ou
      Linear) n'est pas utilisé et le panneau en explique la raison.
    - **Mono :** le profil travaille en mono, comme le plugin (les deux
      canaux sont additionnés) ; les effets « spatiaux » se placent après.
    - **Vitesse :** un réseau de neurones est plus lourd que l'Amplificateur
      intégré : environ une seconde pour chaque retouche dans la boucle de
      calibration et une vingtaine de secondes, en arrière-plan, pour une
      piste de 3 minutes (profils A1 *standard* et A2 ; *lite*, *feather* et
      *nano* sont plus rapides, les LSTM encore plus : quelques secondes pour
      3 minutes). Le résultat reste en mémoire comme pour les autres effets.
    - **Fréquence :** les profils sont en général à 48 kHz, comme SoundText ;
      si un profil a une autre fréquence le son est converti avant et après.
    - **Enregistrement :** le chemin est enregistré dans le fichier `.st`,
      relatif au dossier du projet : `nam: ingresso=3 cassa=file livello=-2
      nam="profili/Plexi.nam" ir="ir/4x12.wav"`. Gardez les profils près du
      projet si vous le déplacez ; si le fichier est introuvable, la carte
      l'écrit en rouge et le son passe inchangé.

    **Où trouver des profils NAM.**
    - **Profils recommandés, d'un coup :** **Sons → Télécharger → Télécharger les
      profils NAM recommandés...** (ou, depuis un terminal dans le dossier
      de SoundText, `python3 scarica_profili_nam.py`) télécharge 11 profils
      d'amplificateurs et de pédales célèbres, environ 3 Mo au total, dans le
      dossier **`profili_nam`** à côté de SoundText (ou dans
      `~/SoundText/profili_nam` si on ne peut pas y écrire). Le dossier ne
      fait pas partie du dépôt : chacun le télécharge sur son propre
      ordinateur. La commande ne retélécharge que les fichiers manquants et
      écrit dans le dossier un `LEGGIMI.txt` avec la provenance et les
      auteurs. La fenêtre « Choisir un profil… » s'ouvre déjà là. Les profils
      viennent de la collection de la communauté NAM sur GitHub
      (github.com/pelennor2170/NAM_models, licence GNU GPL v3) :
      - amplificateurs (sans baffle : ajoutez un baffle avec **Baffle →
        Fichier IR…**) : *Fender Twin Reverb - clair* (funk, pop, arpèges),
        *Vox AC15 - Top Boost* (le « chime » britannique), *Marshall JCM2000
        - crunch* (rock classique), *Marshall JCM900 - lead* (hard rock et
        solos), *Mesa Boogie Mark IV - lead* et *Peavey 5150 - high gain*
        (metal) ;
      - amplificateur **avec baffle** (prêt, pas d'IR) : *Bugera 333 -
        crunch avec baffle* ;
      - pédales, à mettre **avant** un amplificateur (intégré ou profil) :
        *Ibanez TS9 Tube Screamer*, *Klon Centaur (clone)*, *Boss HM-2 -
        suédois* (death metal), et pour la basse *Tech 21 dUg DP3X*.
    - **Baffles pour les amplis sans baffle :** **Sons → Télécharger → Télécharger des baffles IR pour les amplis NAM...** télécharge 20
      baffles de guitare (réponses impulsionnelles, moins de 1 Mo) dans le
      sous-dossier **`profili_nam/casse`**, avec le texte de la licence et
      un `LEGGIMI.txt` ; la fenêtre « Choisir l'IR… » s'ouvre déjà là. Il
      s'agit du *BestPlugins Mega Pack 2* de David Fau Casquel (GNU GPL v2
      ou ultérieure), pris dans le dépôt de Guitarix
      (github.com/brummer10/guitarix). Chaque fichier porte le nom de
      l'ampli dont il reproduit le baffle (*Mesa Boogie Mark V*, *EVH 5150
      III*, *Marshall JMP 2203*, *Engl Retro Tube*...). Le pack vise
      surtout les sons saturés : avec les profils clairs (Fender Twin, Vox
      AC15), essayez plusieurs baffles, ou cherchez-en un adapté sur
      Tone3000.
    - **Tone3000** (tone3000.com), le site de référence, avec des dizaines
      de milliers de profils gratuits (pour télécharger, il peut demander de
      créer un compte gratuit) :
      1. cherchez l'appareil (par exemple « Plexi », « Dumble »,
         « Rectifier », « Tube Screamer ») ;
      2. dans les filtres choisissez la plateforme **NAM** et le type :
         *amp* (amplificateur seul : il faut une IR), *full rig*
         (amplificateur avec baffle, prêt) ou *pedal* ; en triant par
         téléchargements vous trouvez les plus utilisés ;
      3. sur la page du profil téléchargez le fichier (souvent un ZIP avec
         plusieurs variantes : *standard* est la pleine qualité, *lite*,
         *feather* et *nano* plus légers ; SoundText les lit tous, A2 et LSTM
         compris) ;
      4. extrayez les fichiers `.nam` dans le dossier `profili_nam` (ou dans
         un dossier près du projet) et choisissez-les depuis la carte avec
         **Choisir un profil…**.
      Tone3000 propose aussi les **IR** des baffles (type *IR*), à utiliser
      avec **Baffle → Fichier IR…**.
    - **Toute la collection sur GitHub** (environ 260 profils, 108 Mo) : sur
      la page github.com/pelennor2170/NAM_models, **Code → Download ZIP**,
      puis extrayez les `.nam` qui vous intéressent dans `profili_nam`.

    Si un profil téléchargé ne sonne pas comme prévu : un amplificateur sans
    baffle sonne agressif tant que vous ne lui donnez pas d'IR ; une pédale
    seule sonne « petit », elle se place devant un amplificateur ; avec
    **Entrée** vous trouvez le point où le profil réagit le mieux à votre
    signal.
  - **Distorsion** (drive, tonalité, niveau, mix) : d'une couleur chaude à
    peine esquissée jusqu'au fuzz. « Drive » est la quantité de saturation,
    « Tonalité » éclaircit ou assombrit le résultat, « Niveau » compense le
    volume (la distorsion monte beaucoup le niveau), « Mix » sous 100 %
    mélange le son clair au son distordu (préréglage « Parallèle »). Adaptée
    aux guitares, à la basse et aux synthés ; pour un son d'amplificateur
    complet utilisez plutôt l'Amplificateur.
- **Espace — Delay** (en rythme, tempo, répétitions, mix), **Réverbération**
  (pièce, amortissement, largeur, mix), **Chorus** (vitesse, profondeur, mix)
  et **Phaser** (vitesse, profondeur, réinjection, mix).

  Le **Delay en rythme** : dans le menu « En rythme » choisissez une
  subdivision (1/2, 1/4, 1/4 pointée, 1/4 triolet, 1/8, 1/8 pointée, 1/8
  triolet, 1/16) et les répétitions tombent en rythme avec le morceau,
  calculées d'après son BPM ; le bouton Tempo se désactive et montre les
  millisecondes obtenues. Si l'on change le BPM du morceau, le delay
  s'adapte tout seul. Avec « Libre (ms) » le temps se règle à la main. Le
  calcul utilise le tempo **initial** du morceau : avec des changements de
  tempo en cours de morceau, les répétitions restent celles du tempo
  initial. La 1/8 pointée (préréglage « En rythme 1/8 pointée ») est l'écho
  « au galop » classique des guitares rock.

Le **panneau Effets** s'ouvre depuis le bouton FX de la piste (pour le
master, depuis le bouton FX à côté du curseur Master : voir 8.5) et reste en
bas de la fenêtre (on peut le redimensionner en faisant glisser son bord).
Chaque effet est une **carte** avec :
- **⏻** pour l'allumer ou l'éteindre sans perdre les réglages ;
- **◀ ▶** pour le déplacer plus tôt ou plus loin dans la chaîne, **✕** pour
  le retirer ;
- les **préréglages** (ex. Compresseur « Voix », Delay « Slapback »,
  Réverbération « Cathédrale ») : après avoir choisi un préréglage vous
  pouvez le retoucher avec les boutons, et le menu affiche alors
  **Personnalisé** ;
- les **boutons**, avec la valeur dessous ; double-clic sur la valeur pour
  revenir à la valeur par défaut.

Dans l'en-tête du panneau :
- **Boucle** (10 s, de 2 à 30) : à l'ouverture du panneau un passage à
  réécouter pendant les réglages est choisi, et il devient aussi la boucle
  A-B du morceau (sur la règle). Il part du box sélectionné de la piste,
  sinon de la position de la tête de lecture (ou du premier box de la
  piste) ;
- **▶ Écouter la boucle** : répète le passage ; chaque retouche s'entend
  **au tour suivant**, sans refaire le reste du morceau ;
- **Avec les autres pistes** : tout le morceau joue dans la boucle, comme
  dans le mix final ; décoché, on n'entend que la piste ;
- **Avant / Après** : enfoncé, la boucle s'entend sans la chaîne, pour
  comparer (la piste ne change pas) ;
- **Copier vers…** : copie la chaîne sur une autre piste ;
- **Annuler les modifications** : remet effets, réverbération, chorus et
  ambiance comme ils étaient à l'ouverture du panneau (chaque modification
  reste aussi dans Édition → Annuler) ;
- **✕** ferme le panneau : la boucle A-B redevient celle d'avant et la
  chaîne est appliquée à **toute la piste en arrière-plan**, ainsi le
  prochain Play est déjà prêt (la barre d'état prévient quand c'est fini).

Le bouton FX montre combien d'effets sont allumés (ex. **FX 3**).

À savoir :
- **Comment ça sonne :** une piste avec des effets allumés est synthétisée
  à part puis traitée ; le résultat reste en mémoire, donc tourner un bouton
  ne refait que le traitement (des fractions de seconde), et modifier une
  autre piste n'y touche pas. Le delay et la réverbération peuvent allonger
  le morceau avec leur queue.
- **Export :** la chaîne vaut pour l'écoute et l'export WAV ; le fichier
  MIDI ne la contient pas (le lecteur MIDI n'a pas ces effets).
- **Enregistrement :** la chaîne est enregistrée dans le fichier `.st`,
  dans un bloc par piste :
  ```
  Effetti Chitarra:
    compressore: soglia=-20 rapporto=4 attacco=5 rilascio=120 guadagno=4 preset="Voce"
    delay: tempo=250 ripetizioni=25 mix=20 spento
  ```
  (`spento` = effet présent mais éteint). Les valeurs hors limites sont
  ramenées dans les limites, les effets inconnus sont ignorés.
- **Prérequis :** la chaîne utilise le paquet Python `pedalboard` (`pip
  install pedalboard`, déjà dans les prérequis) ; sans lui, le panneau
  n'affiche que l'Envoi rapide et un avertissement. L'écoute de la boucle
  nécessite le streaming audio (`sounddevice`), comme la boucle A-B.
- **Une écoute à la fois :** lancer la boucle arrête le morceau et l'écoute
  des box ; appuyer sur Play arrête la boucle.

### 8.5 Effets sur le master (mastering)

En plus des pistes, le **mix final** du morceau peut aussi passer par une
chaîne d'effets : c'est le « mastering », la dernière retouche qui rend le
morceau plus compact, équilibré et fort. Le bouton **FX** à côté du curseur
**Master**, dans la barre des commandes, ouvre le panneau Effets sur le
master (étiquette « Master · mix final »). On utilise les mêmes effets et
les mêmes cartes que pour les pistes ; les plus adaptés au master sont :
- **EQ 3 bandes :** petites retouches de la tonalité générale (±1-3 dB) ;
- **Compresseur**, préréglage **Colle du mix** : compression légère (taux
  2:1, attaque lente) qui fond les pistes ensemble ;
- **Limiteur**, préréglage **Plus fort** : monte le volume du morceau sans
  que les crêtes dépassent le plafond de −1 dB. C'est en général le dernier
  de la chaîne.

Le bouton **+ Chaîne de mastering** ajoute d'un coup ces trois effets,
comme point de départ à régler à l'oreille. Le bouton FX du master
s'allume et montre combien d'effets sont actifs (ex. **FX 3**).

Comme pour les pistes :
- la **boucle de calibration** (10 s, depuis la tête de lecture) fait
  réentendre le mix de tout le morceau à chaque retouche ; **Avant / Après**
  compare le mix avec et sans la chaîne du master ;
- **Annuler les modifications** remet la chaîne comme elle était à
  l'ouverture, et chaque modification est aussi dans Édition → Annuler ;
- **Copier vers…** copie la chaîne du master sur une piste ; depuis une
  piste on peut copier sa chaîne sur le master (« Master (mix final) »).

À savoir :
- **Où elle s'applique :** le master s'applique à l'écoute du morceau, à
  l'export WAV du morceau et à l'accompagnement que l'on entend pendant
  l'enregistrement. Il ne s'applique ni à l'export d'une seule piste ni à
  l'export MIDI.
- **La boucle des pistes passe aussi par le master :** en calibrant une
  piste vous l'entendez déjà avec la chaîne du master, c'est-à-dire comme
  dans le morceau fini.
- **Rapide :** le mix avant le master reste en mémoire, donc après une
  retouche du seul master le Play suivant retraite le mix déjà prêt, sans
  resynthétiser le morceau.
- **Volume master et chaîne :** le curseur Master (8.2) agit avant la
  chaîne, sur le volume des pistes : avec un limiteur sur le master, le
  monter rend le morceau plus « écrasé » mais pas plus fort au-delà du
  plafond.
- **Enregistrement :** dans le fichier `.st` la chaîne du master est dans
  le bloc
  ```
  Catena master:
    compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=1 preset="Colla del mix"
    limiter: guadagno=6 tetto=-1 rilascio=80 preset="Più forte"
  ```
  (un mot différent de `Effetti`, pour ne pas le confondre avec une piste
  nommée « Master »). Sans chaîne le bloc n'est pas écrit.

### 8.6 Sons de studio avec des programmes externes (re-amping)

L'amplificateur de SoundText (8.4) convient aux maquettes, aux
accompagnements et aux démos. Pour un son de guitare de studio, le plus
simple est le **Profil NAM** (8.4), qui utilise dans SoundText des captures
de vrais amplificateurs. Sinon, on peut faire passer la piste dans un
simulateur d'amplificateur externe puis la remettre dans le morceau : c'est
le **re-amping**, utile pour utiliser des programmes comme Guitarix ou des
plugins commerciaux.

**La marche à suivre, sur n'importe quel système :**
1. Enregistrez la guitare **claire** (entrée INST/Hi-Z de la carte son,
   sans amplificateur) dans une piste audio, ou écrivez-la en notes.
2. Clic droit sur le nom de la piste → **Exporter en WAV sec (pour le
   re-amping)...**
3. Dans le programme externe, appliquez au fichier le simulateur choisi et
   enregistrez le résultat dans un nouveau WAV.
4. Dans SoundText créez une **piste audio** (ex. « Guitare ampli ») et
   **Importer un fichier audio...** : sur une piste vide le clip se place
   au début, donc en rythme avec le morceau. Mettez la piste d'origine en
   **Mute** (ou gardez les deux, pour mélanger clair et amplifié).

Si le simulateur ajoute un retard (cela arrive en temps réel, pas dans le
traitement hors ligne), décalez un peu le clip ou raccourcissez son début
en faisant glisser son bord.

**Linux — Guitarix** (gratuit, simulation des circuits à lampes
d'amplificateurs et de pédales, baffles et IR) : il s'installe depuis les
dépôts de la distribution (`sudo apt install guitarix`, `sudo dnf install
guitarix`, `sudo pacman -S guitarix` ; sur certaines, comme Debian et
Ubuntu, les plugins LV2 sont dans un paquet à part, `guitarix-lv2`). Les
plugins LV2 de Guitarix peuvent s'utiliser **directement dans SoundText**
comme effets (8.7), sans re-amping. Pour utiliser Guitarix en dehors de
SoundText il y a deux façons :
- **hors ligne (recommandé) :** ouvrez le WAV sec dans **Audacity** ou dans
  **Ardour** et appliquez les plugins LV2 de Guitarix comme effet, puis
  exportez ; aucune connexion audio à configurer ;
- **en direct :** lancez Guitarix (avec PipeWire, si besoin, `pw-jack
  guitarix`), reliez avec **qpwgraph** ou **Helvum** la guitare à l'entrée
  de Guitarix et sa sortie à l'enregistreur ; pour enregistrer directement
  dans SoundText choisissez comme carte son l'entrée de PipeWire.

**Windows et macOS** (Guitarix ne fonctionne que sous Linux) :
- **Neural Amp Modeler (NAM)** : gratuit, plugin VST3/AU et programme
  autonome, avec des modèles « capturés » sur de vrais amplificateurs
  (fichiers `.nam`, des milliers gratuits sur Tone3000) et chargement d'IR
  pour le baffle. Les profils NAM peuvent aussi s'utiliser directement dans
  SoundText (Profil NAM, 8.4), sur tous les systèmes, sans re-amping (A1, A2
  et LSTM) ; le plugin sert à jouer en direct ;
- **AIDA-X** : gratuit, semblable à NAM et plus léger, aussi sous Linux ;
- **GarageBand** (macOS) : gratuit, amplificateurs et pédales déjà
  inclus ;
- pour appliquer un plugin au WAV sec, **Audacity** convient (gratuit, VST3
  sur tous les systèmes, AU sur macOS), ou un programme d'enregistrement
  comme **Reaper**.

En direct, NAM et AIDA-X fonctionnent aussi comme programmes autonomes : la
guitare entre dans le simulateur et SoundText enregistre la sortie (avec une
connexion audio virtuelle, ou en enregistrant dans un autre programme et en
important le fichier).

### 8.7 Plugins externes (VST3 et LV2)

SoundText peut utiliser les **plugins audio installés sur l'ordinateur**,
comme **effets** dans la chaîne d'une piste ou du master, ou comme
**instruments virtuels** qui jouent les notes d'une piste à la place du
SoundFont.

- **VST3** : sous Linux, Windows et macOS. SoundText les cherche dans les
  dossiers standard du système (sous Linux `~/.vst3` et `/usr/lib/vst3`,
  sous Windows `C:\Program Files\Common Files\VST3`, sous macOS
  `/Library/Audio/Plug-Ins/VST3`) ; d'autres dossiers s'ajoutent depuis
  **Sons → Dossiers des plugins VST3...**
- **LV2** : seulement sous Linux, et il faut la bibliothèque système `lilv`
  (sous Debian/Ubuntu le paquet `liblilv-0-0`, déjà présent si Ardour,
  Carla ou Guitarix sont installés). Les plugins LV2 sont trouvés
  automatiquement. Par exemple, avec `guitarix-lv2` on dispose de dizaines
  d'amplificateurs et de pédales.
- Les formats **CLAP** et **VST2** ne sont pas pris en charge.

**Un plugin comme effet** : dans le panneau Effets (8.4) **+ Effet → Plugin
(VST3/LV2)** ouvre la liste des plugins d'effet installés, avec une
recherche par nom. La carte du plugin a :
- les boutons **Mix** (quelle part du son traité mélanger à l'original) et
  **Niveau** (le volume de sortie), comme les autres effets ;
- **Paramètres...**, qui ouvre une fenêtre avec toutes les commandes du
  plugin ; les modifications s'entendent tout de suite dans la boucle
  d'écoute du panneau ;
- **Changer...** pour le remplacer par un autre plugin.

Dans la fenêtre des paramètres, **Interface du plugin...** ouvre la fenêtre
graphique du plugin lui-même (VST3 seulement). Quand vous la fermez, les
réglages faits là restent dans le projet.

**Un plugin comme instrument** : **Piste → Instrument plugin → Choisir (VST3/LV2)...**, ou clic droit sur le nom de la piste. Choisissez un
instrument virtuel (synthé, piano échantillonné...) puis réglez ses
paramètres. Les notes de la piste sont jouées par le plugin : le **volume**
de la piste agit sur la force des notes, le **pan** sur la position dans
l'image stéréo, et les effets de la piste s'appliquent après le plugin. Pour
revenir au SoundFont choisissez **Aucun : utiliser le SoundFont**. Le nom du
plugin apparaît sous le nom de la piste.

Certains plugins LV2 chargent un fichier : par exemple sfizz LV2 joue un
**fichier SFZ**. Dans la fenêtre des paramètres ces propriétés ont une
ligne avec **Parcourir...** et **Retirer** ; le fichier choisi reste dans
le projet.

**Instrument SFZ intégré.** Un fichier `.sfz` (instrument échantillonné,
comme ceux que télécharge `scarica_strumenti.py`) peut aussi être joué sans
plugin : dans la liste des instruments choisissez **Instrument SFZ
(intégré)...** puis le fichier. Il est joué par la bibliothèque du moteur
**sfizioso** (ou de **sfizz**), installée une fois avec
`python3 scarica_strumenti.py libreria` (sous Linux aussi
`./scarica_strumenti.sh libreria` ; sous Windows
`py scarica_strumenti.py libreria`, qui demande Visual Studio Build Tools
avec le C++) ; sans elle, l'entrée apparaît en gris.
Cet instrument n'a pas de paramètres : « Paramètres de l'instrument
plugin... » permet de choisir un autre fichier. Sous le nom de la piste
apparaît le nom du fichier avec « (SFZ) » ; si vous modifiez le fichier
`.sfz`, le morceau est recalculé.

Le projet `.st` mémorise le plugin de chaque piste et de chaque effet, avec
ses paramètres. En ouvrant le projet sur un autre ordinateur, les VST3 sont
recherchés par nom de fichier dans les dossiers des plugins.

**Si un plugin ne fonctionne pas.** Les plugins tournent dans un processus
séparé de SoundText : si l'un d'eux se bloque ou se ferme de façon
anormale, SoundText reste ouvert. Le plugin est marqué comme **« ne répond
pas »** jusqu'au prochain démarrage de l'application. Un effet qui ne
fonctionne pas laisse passer le son inchangé. Une piste dont l'instrument
plugin ne fonctionne pas joue avec le SoundFont, et la raison est notée
dans le fichier journal (Aide). Certains plugins ne peuvent pas du tout
être chargés : dans la liste ils apparaissent en gris, avec la raison à
côté (par exemple « ne répond pas », ou un plugin qui n'accepte que de
l'audio mono).

**Limites** :
- les instruments plugins jouent à l'écoute du morceau, dans la boucle du
  panneau Effets et dans l'export WAV ; les aperçus rapides (note du
  clavier, écoute d'un pattern, accord choisi par double-clic) utilisent
  encore le SoundFont ;
- l'export MIDI et MusicXML contient les notes, pas le son du plugin ;
- pour les plugins LV2 on enregistre les valeurs des paramètres et les
  fichiers choisis, pas le reste de l'« état » interne ;
- la première recherche de plugins charge chaque VST3 une fois, et cela
  peut prendre un moment ; ensuite la liste est mémorisée tant qu'aucun
  plugin ne change (**Actualiser la liste** refait la recherche).

## 8bis. Structure du morceau (vue en box)

Une alternative à l'éditeur de texte linéaire pour travailler sur la
**structure** du morceau (intro/couplet/refrain/solo...) plutôt que note
par note : chaque piste devient une ligne sur un seul axe temporel commun,
et son contenu est divisé en **box** — des rectangles que l'on fait glisser
horizontalement, chacun autonome comme le corps d'un pattern (section 4),
avec son propre nom et sa propre position dans le temps. Le contenu effectif
de chaque piste (`Track.text`, ce que lecture/export/validation lisent
vraiment) est toujours recalculé automatiquement à partir de la suite de ses
box : travailler en box n'est pas « un autre format », seulement une autre
façon d'écrire le même texte.

**Activation** : boutons **Structure** / **Texte** dans la barre des
commandes, ou menu **Affichage → Structure du morceau (box)** (raccourci
`Ctrl+Shift+B`) : ils alternent cette vue et l'éditeur de texte linéaire
classique. C'est la vue avec laquelle SoundText s'ouvre par défaut.

La couleur de chaque box (et de la bande à gauche de l'en-tête de la piste)
reflète la famille de l'instrument (basse, guitare, vents, etc.), la même
convention qu'ailleurs dans l'application (ex. section 7). Les en-têtes
contiennent aussi la table de mixage de la piste (voir section 8).

### Créer un box

Un double-clic sur un endroit vide d'une ligne ouvre l'éditeur d'un nouveau
box à cette position (la même fenêtre de modification décrite plus bas). Le
clic droit sur un endroit vide propose en plus :

- **Nouveau box depuis le clavier ici** / **Nouveau box depuis l'audio
  ici** / **Importer un MIDI ici** : les mêmes démarches que « Jouer au
  clavier »/« Importer de l'audio »/« Importer un MIDI » de la partie piste
  (sections 10, 10bis, 10ter), mais le résultat devient un nouveau box au
  lieu de remplacer toute la piste.
- **Générer la batterie dans cette piste...** / **Générer la basse depuis
  les accords dans cette piste...** (section 9bis) : visibles seulement si
  l'instrument de la piste est respectivement une percussion ou une basse ;
  le box généré est ajouté juste après le dernier box existant.
- **Coller ici** : seulement si un box a d'abord été coupé ou copié (voir
  plus bas).
- **Importer depuis un .box...** : charge un box enregistré auparavant
  (voir plus bas « Exporter/importer un seul box »).

Les mêmes actions « Générer batterie/basse » sont aussi accessibles par un
clic droit sur l'étiquette de la piste à gauche.

### Déplacer, sélectionner, modifier

- **Faire glisser** un box le repositionne dans le temps sur la MÊME piste
  (pour le déplacer sur une autre piste on utilise couper/coller, pas le
  glissement) : la position s'accroche toujours au temps entier le plus
  proche, et une ligne-guide verticale traverse toutes les pistes pendant le
  glissement pour aligner à l'œil des box de pistes différentes. Si le point
  choisi chevauche un autre box de la même piste, il s'accroche
  automatiquement au bord libre le plus proche au lieu de le chevaucher.
- **Un clic** sélectionne un box (bord surligné de la couleur d'accent)
  sans le déplacer, même si le box n'était pas déjà sur un temps entier
  (ex. après un nolet, section 2.1bis) : un petit mouvement involontaire de
  la souris entre l'appui et le relâchement ne compte pas comme un
  glissement.
- **Un double-clic** sur un box ouvre l'éditeur dédié à son contenu (le
  même éditeur de texte avec coloration syntaxique, autocomplétion et
  Lecture/Stop d'aperçu utilisé pour les patterns, section 4) avec le nom et
  le texte du box, validés avant de pouvoir confirmer.

### Menu du clic droit sur un box

- **▶ Play** / **■ Stop** : joue (ou arrête) l'aperçu du contenu du box avec
  l'instrument de sa piste — un moteur d'aperçu dédié, indépendant du
  transport principal F5/F6.
- **Transposer...** : transposition par demi-tons de tout le contenu du box.
  Les appels de motifs et de fichiers MIDI se transposent avec le
  suffixe : `%Giro` devient `%Giro+2`, `&"Riff"+1` devient `&"Riff"+3` (le
  motif reste tel quel, car d'autres peuvent l'utiliser). Si le box
  utilise une ancre de mesure `bar=N`, **▶ Play** le joue depuis sa place
  dans le morceau, pour que l'ancre mène à la bonne mesure (de même pour
  **▶ Play** sur une sélection).
- **Renommer...**
- **Dupliquer** : crée une copie sur la même piste, juste après la fin du
  box d'origine (ou dans le premier espace libre disponible à partir de là).
- **Couper** / **Copier** / **Coller ici** : le presse-papiers fonctionne
  aussi entre pistes différentes (c'est ainsi qu'on déplace un box sur une
  autre piste).
- **Exporter en .box...** / **Importer depuis un .box...** (sur un endroit
  vide) : voir plus bas.
- **Supprimer**.

### Annuler/Rétablir (Ctrl+Z / Ctrl+Y)

Chaque action qui modifie les box d'une piste — déplacer, créer (de
n'importe quelle façon), modifier, transposer, renommer, dupliquer,
couper/supprimer, coller, importer depuis un `.box` — s'annule avec
`Ctrl+Z` et se rétablit avec `Ctrl+Y`, comme toute autre modification du
projet (voir **1.2 Annuler/Rétablir**). Sélectionner ou jouer un box ne
produit en revanche rien à annuler.

### Écouter seulement le box sélectionné

Il n'y a qu'un seul transport : **Play/Stop** dans la barre des commandes
jouent le morceau entier. Pour écouter seulement le box sélectionné
(cliquez sur un box pour le sélectionner) : **Maj+Espace**, ou **Lecture →
Écouter le box sélectionné**, ou clic droit sur le box → **▶ Play**. Appuyé
de nouveau pendant l'écoute, il met en pause ; une fois de plus il reprend
là où il s'était arrêté, si entre-temps vous n'avez pas sélectionné un autre
box (dans ce cas il repart du début sur le nouveau). **Stop** arrête aussi
l'écoute du box, et lancer le morceau avec **Play** l'interrompt : on
n'entend toujours qu'une chose à la fois. Maj+Espace vaut dans la vue
Structure : dans l'éditeur de texte il reste un espace normal.

### Conseils

Au-dessus des en-têtes des pistes, **? Mode d'emploi** résume les commandes
de la vue (en le survolant à la souris, ou en cliquant). Les lignes encore
vides montrent en gris ce qu'on peut faire : créer un box, importer ou
enregistrer de l'audio (pistes audio), ou que la piste est écrite en texte
libre.

### La tête de lecture

Pendant l'exécution du morceau entier (transport principal, section 12),
une ligne verticale traverse toutes les pistes en suivant le point en cours
de lecture, et le canevas défile horizontalement juste assez pour la garder
toujours visible — quel que soit le box sélectionné.

### Exporter/importer un seul box

**Exporter en .box...** (menu d'un box) enregistre son contenu dans un
fichier texte lisible à la main (même style que le format `.st`, section
11, mais en un seul bloc) dans le dossier `songs/` (section 5bis).
**Importer depuis un .box...** (menu d'un endroit vide) le recharge comme
nouveau box à n'importe quel endroit/piste — utile pour réutiliser une
section (ex. un refrain) entre différents projets.

### Conversion automatique en box

En important un fichier MIDI entier ou en convertissant de l'audio dans une
piste déjà en box, le texte obtenu est automatiquement divisé en plusieurs
box là où apparaît un silence continu de plus de 3 temps, au lieu de rester
un seul grand box — ainsi le contenu est tout de suite organisé de façon
lisible même pour un fichier long, sans devoir le réarranger à la main.

### Pistes en texte libre

Une piste sans box (texte libre) n'affiche rien dans la vue Structure du
morceau : **Modifier le texte libre...**, dernière entrée du menu du clic
droit sur son nom, ouvre tout son texte dans le même éditeur que les box
(coloration, Play, Play de la sélection), sans quitter la vue. La
modification s'annule avec Ctrl+Z.

**Convertir en texte libre...** (à sa place, pour une piste qui a déjà des
box) ramène cette piste à un seul éditeur de texte linéaire : le contenu
musical ne change pas, seule la façon de le modifier change. C'est
irréversible seulement au sens où elle ne sera pas automatiquement
redivisée en box : le texte reste libre d'être redivisé à la main.

## 9. Figer les accords

Le bouton « Figer les accords en notes explicites » de l'éditeur remplace
chaque accord abstrait de la piste courante par le bloc `[...]` de notes
concrètes généré par le moteur de voicing pour l'instrument assigné.

### 9.1 Choisir le voicing par un double-clic

Un **double-clic sur un accord** — en forme compacte (`Cmaj7`, même avec un
multiplicateur, ex. `2Cmaj7`) ou déjà « figé » en notes explicites
(`[c*3 g*3 b*3 e*4]`, s'il est reconnaissable comme accord standard),
**même si l'accord se trouve dans un groupe de répétition `N(...)`** (voir
2.1) — dans l'éditeur de piste ou dans le corps d'un pattern ouvre un petit
menu avec tous les voicings sensés pour l'instrument courant (voir 2.8),
chacun avec un aperçu textuel des notes obtenues. En parcourant les entrées
avec les flèches on entend un aperçu sonore de chacune (avec un court
délai, dû au rendu) ; **Entrée** ou un clic sur une entrée applique le
choix (sur le token implicite il ajoute/change seulement le suffixe
`.style` ; sur le bloc explicite il recalcule les notes), **Échap** ou un
clic hors du menu annule sans rien modifier. Si le bloc `[...]` ne
correspond à aucune qualité d'accord connue (ex. une simple quinte
`[c*3 g*3]`, ambiguë entre majeur et mineur), une info-bulle le signale et
le menu ne s'ouvre pas.

### 9.2 Autocomplétion pendant la saisie

Pendant la saisie, l'éditeur propose dans une fenêtre surgissante les
tokens complets correspondant au fragment déjà tapé, pour accélérer les
notations plus longues ou moins faciles à retenir :

- qualités d'accord (`C7`, `Dm7b5`...) à partir de la fondamentale ;
- styles de voicing (`Cmaj7.drop2`, `C7.cagEd`...) après le `.`, limités à
  ceux applicables à l'instrument de la piste courante (voir 2.8) ;
- noms de percussions, nuances (`mf`, `ff`...) et commandes d'état (`SON`,
  `SOFF`, `r`) ;
- références `%Nom` aux patterns définis dans le projet et `&"Nom"` à la
  bibliothèque MIDI (voir 6 et 11.1).

Flèches haut/bas pour parcourir les propositions, **Entrée** ou **Tab** pour
accepter celle qui est surlignée, **Échap** ou un clic à l'extérieur pour
fermer la fenêtre sans rien modifier. Les notes seules (ex. `c`, `g#*4`) ne
produisent pas de suggestions propres, étant déjà aussi courtes qu'une
suggestion.

## 9bis. Générer batterie/basse (sans IA)

Génération d'une ligne de batterie ou de basse sans modèles/
téléchargements/GPU : algorithmique, basée sur une petite bibliothèque de
motifs par genre (batterie) et sur la lecture des accords déjà écrits dans
une autre piste (basse). Instantanée et sans dépendances lourdes.

**Variabilité** (dans les deux fenêtres) : un curseur de 0 % à 100 % (par
défaut 35 %) décide à quel point le résultat s'éloigne du motif de base du
style. À 0 % le même style donne toujours le même texte ; plus haut le
générateur ajoute des variations :
- **Batterie** : caisses claires fantômes à faible volume et grosse caisse
  en plus (seulement dans les espaces vides : les coups du motif restent à
  leur place), coups de charleston/ride qui sautent, vélocités légèrement
  différentes à chaque mesure, fills sur une demi-mesure ou sur le dernier
  temps au lieu d'être toujours complets. Beaucoup de styles ont aussi des
  **grooves alternatifs** (ex. le rock avec la grosse caisse syncopée, le
  reggae « steppers », le funk avec une autre grosse caisse) : au début de
  chaque groupe de mesures le groove peut passer à l'un d'eux, et les fills
  sont choisis entre celui du style et quelques fills génériques (roulement
  de caisse claire, descente sur les toms, coups à l'unisson...).
- **Basse** : le traitement alternatif (notes d'approche, tierce et
  septième) se déclenche aussi en dehors du rythme de « Variation toutes les
  N accords » ; les notes après la première d'un accord peuvent s'allonger,
  se taire ou monter d'une octave. La première note de chaque accord (la
  fondamentale) ne change jamais, et la durée de l'accord reste identique.
  De temps en temps une mesure utilise un **motif alternatif** du style
  (ex. les octaves syncopées, le two-feel avec la quinte anticipée) : le
  choix se fait mesure par mesure, donc même un accord long (les 4 mesures
  de tonique du blues) change de rythme à l'intérieur. Cela vaut aussi pour
  l'accompagnement et le riff. La variabilité n'enlève pas seulement, elle
  **ajoute** aussi :
  - des **notes de passage** (basse et riff) : à la fin d'un accord une note
    qui mène à la fondamentale du suivant — un demi-ton en dessous ou
    au-dessus, un ton en dessous ou sa quinte. Si la dernière note est
    longue, la note de passage s'ajoute dans son dernier temps ; sinon elle
    prend sa place ;
  - des **anticipations syncopées** (basse, accompagnement et riff sur les
    grilles en croches ou en triolets) : la première note ou le premier
    accord du tour suivant arrive une croche plus tôt, lié par-dessus le
    changement d'accord, comme dans la pop, le rock et le latin. C'est
    pourquoi la fondamentale peut commencer une croche avant la mesure au
    lieu du premier temps.
  Avec l'intensité **Légère**, ni notes de passage ni anticipations.

**Intensité** (batterie, basse, accompagnement et riff) : quel « poids » la
partie doit avoir dans le morceau.
- **Légère (couplet, intro)** : moins de coups et moins de notes — la
  batterie enlève les coups de charleston/ride en levée et les notes
  fantômes et joue plus doucement ; basse et accompagnement ne gardent que
  les attaques sur le 1 et le 3 (les notes restantes durent plus longtemps).
- **Normale** : le motif du style tel quel.
- **Pleine (refrain)** : la batterie passe du charleston à la ride, joue plus
  fort et ouvre chaque groupe de mesures par un crash ; les accords de
  l'accompagnement prennent aussi l'octave au-dessus et la basse monte d'une
  octave sur la dernière attaque de chaque accord.
- **En crescendo** : légère dans le premier tiers de la partie, normale dans
  le deuxième, pleine dans le dernier — utile pour un pont ou un
  pré-refrain.

Le bouton **🎲 Nouvelle variation** tire une variation différente avec les
mêmes réglages. La variation est liée à une « graine » qui reste fixe tant
que vous n'appuyez pas dessus : changer de style, de mesures ou d'octave ne
la fait pas « sauter », et à réglages égaux le texte est reproductible. Le
texte généré peut de toute façon être modifié à la main dans l'aperçu avant
de confirmer.

**Préréglages et détails de la variabilité.** À côté du curseur, un menu
avec trois préréglages :
- **Fidèle** : 15 %, surtout la dynamique, peu de notes et de rythmes
  changés ;
- **Musicien** (par défaut) : 35 %, des variations comme celles d'un
  musicien de studio ;
- **Créatif** : 75 %, beaucoup de variations, pour chercher des idées.

Le menu affiche « Personnalisée » quand les valeurs ne correspondent à aucun
préréglage. **Détails ▸** ouvre trois curseurs qui indiquent quelle part de
la variabilité va à chaque aspect (100 % = toute) :
- **Rythme** : grooves et rythmes alternatifs, fills, anticipations, notes
  ou coups qui sautent, s'allongent ou s'ajoutent (la grosse caisse en plus
  de la batterie) ;
- **Notes et harmonie** : variantes du motif, notes de passage, sauts
  d'octave, caisses claires fantômes de la batterie ; dans la grille
  d'accords, les couleurs et substitutions des accords (c'est le seul aspect
  de la grille d'accords) ;
- **Dynamique** : vélocités différentes coup par coup et note par note. Pour
  la basse, l'accompagnement et le riff, la dynamique ajoute les vélocités
  (`N@`), plus fortes sur le premier temps de la mesure et plus faibles sur
  les levées ; à 0 % les notes n'en ont pas, comme avant.

Par exemple, avec la variabilité à 60 % et Rythme et Notes à 0 %, les notes
restent celles du motif et seule change la façon de les jouer.

**Régénérer seulement quelques mesures.** Sous l'aperçu : « Régénérer
seulement les mesures de N à M » et **🎲 Régénérer celles-ci** tirent une
nouvelle variation seulement pour ces mesures, en gardant les autres telles
quelles. On peut le répéter sur d'autres mesures ; les retouches restent
même en changeant les autres réglages (style, intensité...), **↺ Annuler
les retouches** les enlève et **🎲 Nouvelle variation** régénère tout depuis
le début. La coupe ne casse jamais une note : si une note traverse le début
ou la fin du passage (une anticipation, un accord long), le passage
s'élargit pour l'englober. Avec la variabilité à 0 % le bouton est
désactivé (le résultat serait identique).

**Composer → Générer dans la piste sélectionnée → Batterie...** (nécessite une piste de
percussion sélectionnée) :
- **Style** : la fenêtre propose les styles écrits pour la métrique du
  projet. En 4/4 : Rock, Funk, Four-on-the-floor (disco), Reggae (one
  drop), Punk, Soul (Motown), Bossa nova, Rock'n'roll, Shuffle (blues),
  Swing (jazz), Hip-hop (boom bap), Half-time, Metal (double grosse
  caisse), Country (train beat), Samba, Cha-cha-cha et Marche ; en 3/4 :
  Valse et Valse jazz ; en 5/4 : Rock en 5/4 (3+2) et Jazz en 5/4
  (triolets) ; en 6/8 : Ballade et Afro-cubain ; en 7/8 : Rock en 7/8
  (2+2+3) et Balkanique en 7/8 (3+2+2) ; en 12/8 : Slow blues et Slow rock
  années 50. Les styles en 7/8 utilisent la grille en croches (`8:`).
  Chaque style apporte sa propre grille rythmique : la plupart utilisent les
  doubles croches (`16:`), Shuffle et Swing les triolets de croches (`8T:`),
  ce qui produit leur « balancement » caractéristique. Il n'y a pas de
  sélecteur de grille dans la fenêtre : un groove est écrit pour une grille
  précise et on ne peut pas l'adapter à une autre sans en changer le
  rythme. En 6/8 et 12/8 la grille est en croches (`8:`). Remarque : les
  instruments qui jouent au même instant partagent la vélocité (limite de la
  notation en blocs `[...]`).
- **▶ Écouter / ■ Stop** : joue l'aperçu tel qu'il est écrit (même après une
  modification de votre part à la main) avant de confirmer. Avec **Avec les
  autres pistes** coché vous l'entendez avec le reste du projet (les Mute
  sont respectés, le Solo non ; le contenu actuel de la piste de
  destination n'est pas joué) ; décoché, il joue seul. Pendant la lecture,
  le passage que vous écoutez est surligné dans l'aperçu (si vous modifiez
  le texte pendant l'écoute, le surlignage se suspend jusqu'au prochain
  Écouter). Ok, Annuler ou la fermeture de la fenêtre arrêtent l'écoute.
  Cela vaut aussi pour **Générer la basse**, **Générer
  l'accompagnement/le riff** et **Générer une grille d'accords**.
- **Mesures** : combien en générer.
- **Fill toutes les N mesures** : toutes les N mesures insère un fill (avec
  un crash de reprise à la mesure suivante) au lieu de répéter le groove de
  base à l'identique — 0 désactive les fills. Il n'insère jamais de fill
  sur la dernière mesure générée (il finit toujours sur le groove de base).
- **Fills par phrases** (coché par défaut) : comme un vrai batteur, à la fin
  de chaque groupe de N mesures il fait un **petit** fill (dernier temps
  seulement) et à la fin de chaque phrase de 2×N mesures un fill
  **complet**. Décoché, tous les fills sont complets.
- **Final sur la dernière mesure** : la dernière mesure devient un coup de
  conclusion (crash et grosse caisse sur le premier temps, puis silence),
  pour terminer le morceau ou la section.
- **Intensité** : voir plus haut.

**Composer → Générer dans la piste sélectionnée → Grille d'accords...** (nécessite un
instrument polyphonique : piano, guitare, orgue, pad...) : écrit une grille
d'accords sous forme de symboles (`Am7`, `G`...), que le moteur voice tout
seul pour l'instrument de la piste. C'est le point de départ quand le
morceau n'a pas encore d'accords : basse, accompagnement et riff ont besoin
d'une piste d'accords à suivre. Dans la vue Structure du morceau l'entrée
apparaît dans le menu du clic droit d'une piste polyphonique tant qu'aucune
autre piste du morceau ne contient d'accords : la piste qui a déjà la
grille continue de la proposer, et chaque nouvelle grille va dans un box
après le dernier (comme pour **Générer la basse**). À l'inverse, **Générer
l'accompagnement** et **Générer riff/mélodie** n'apparaissent que quand une
autre piste contient des accords (depuis le menu Composer, sans accords, un
message renvoie à la grille d'accords).
- **Tonalité** : elle part de celle du projet ; si le projet n'en a pas et
  que la piste a déjà une grille, de la tonalité du box après lequel sera
  placée la nouvelle (reconnue d'après ses accords ou ses notes) ; sinon de
  do majeur. Les styles proposés sont ceux de son mode :
  - majeur : **Pop** (I-V-vi-IV), **Années 50 / doo-wop** (I-vi-IV-V),
    **Rock** (I-IV-I-V), **Canon de Pachelbel**, **Blues 12 mesures**,
    **Jazz II-V-I**, **Turnaround jazz** (I-vi-ii-V), **Trois accords**
    (I-IV-V-I), **Ballade** (I-iii-IV-V), **J-pop / royal road**
    (IV-V-iii-vi-ii-V-I), **Rock mixolydien** (I-bVII-IV-I), **Gospel**
    (I-I7-IV-iv), **Cycle des quintes**, **Rhythm changes**, **Blues jazz
    12 mesures** ;
  - mineur : **Pop mineur** (i-VI-III-VII), **Cadence andalouse**
    (i-VII-VI-V), **Rock mineur** (i-VII-VI-VII), **Cadence mineure**
    (i-iv-i-V7), **Jazz II-V-I mineur**, **Blues mineur 12 mesures**,
    **Mineur simple** (i-iv-v-i), **Mineur épique** (i-VI-VII-i), **Vamp
    dorien** (i7-IV7), **Line cliché** (la voix qui descend chromatiquement
    dans l'accord mineur), **Cycle mineur**, **Phrygien** (i-bII).
  Les degrés abaissés (bVII du mixolydien, bII du phrygien) sont écrits avec
  des bémols (`Bb` en do, pas `A#`), sauf dans les tonalités à dièses.
- **Durée de chaque accord** : une demi-mesure, une ou deux (elle multiplie
  la durée du style : dans le blues certains accords durent plusieurs
  mesures).
- **Mesures** : la grille se répète jusqu'à les couvrir ; **Grille
  entière** l'écrit une seule fois. Par défaut elle couvre la musique déjà
  présente dans les autres pistes.
- **Variabilité** : à 0 % le style tel quel. Plus haut :
  - les accords s'enrichissent (septièmes, neuvièmes, sus) en gardant la
    même fonction ;
  - **dominantes secondaires** : un accord qui dure au moins une mesure
    laisse sa seconde moitié à la dominante de l'accord suivant (en do :
    `A7` avant `Dm`, `E7` avant `Am`) ; s'il dure au moins deux mesures, sa
    dernière mesure peut devenir un **II-V** vers lui (`Bm7b5 E7` avant
    `Am`). Le dernier accord de la grille n'est pas préparé ainsi, sauf s'il
    s'agit de la tonique : sinon on entendrait un changement de tonalité ;
  - **substitution tritonique** : une dominante qui descend d'une quinte
    devient celle située à un triton (`Db7` à la place de `G7` avant `C`),
    jamais l'accord de tonique (le `C7` du blues reste) ;
  - **IV mineur** (en majeur) : le IV qui revient au I emprunte le iv mineur
    (`F Fm6 C`).
  Les accords chromatiques s'écrivent avec des bémols (`Db7`), sauf dans les
  tonalités à dièses.
- **Cadence finale** (non cochée par défaut, pour laisser la grille ouverte
  et prête à se répéter) : la dernière mesure devient l'accord de tonique,
  précédé pendant une demi-mesure d'un accord de cadence. À 0 % c'est
  toujours `V7` ; avec la variabilité ce peut être aussi plagal (`IV`), iv
  mineur (`Fm6`), « backdoor » (`Bb7`) ou `V7sus4`, en mineur `V7`, `iv` ou
  `VII`. Les grilles qui ne partent pas de la tonique (II-V-I, royal road)
  finissent toujours par la dominante ou sa substitution tritonique, car
  c'est elle qui établit la tonalité.

**Composer → Générer dans la piste sélectionnée → Basse depuis les accords...**
(nécessite une autre piste du projet avec des accords déjà écrits) :
- **Accords depuis** : quelle piste fournit la suite harmonique à suivre
  (les notes seules/percussions/silences de cette piste sont ignorés, seuls
  les accords comptent : écrits comme symbole, ex. `Cmaj7`, ou comme bloc
  `[c*4 e*4 g*4]` d'au moins deux notes, qui est la façon dont les écrit
  l'import MIDI ; le bloc est reconnu comme accord connu, sinon la
  fondamentale est la note la plus grave). Une piste faite seulement de
  notes seules (mélodie, arpèges) n'a pas d'accords à suivre.
- **Style** (chacun écrit sa propre grille rythmique : noires, croches ou,
  pour le shuffle, triolets de croches) :
  - **Fondamentale** : répète la tonique pendant toute la durée de l'accord.
  - **Fondamentale/quinte** : les alterne.
  - **Walking bass** : marche sur les degrés de l'accord avec une note
    d'approche chromatique vers l'accord suivant (simplification de la
    walking bass du jazz) ; la variante utilise les vraies tierce et
    septième de l'accord (tierce mineure sur un accord mineur).
  - **Pédale** : une seule note longue par accord (ballades).
  - **Deux temps** : fondamentale sur le 1 et quinte sur le 3 (jazz lent,
    country).
  - **Octaves** : fondamentale et octave alternées (disco, funk simple).
  - **Blues 1-3-5-6** : la ligne classique du blues/boogie sur la vraie
    tierce de l'accord (la variante finit sur la septième de dominante).
  - **Croches** : fondamentale en croches (rock, pop, punk).
  - **Reggae** : le premier temps reste vide, fondamentale longue à partir
    du 2.
  - **Bossa nova** : fondamentale sur le 1 et le 3, quinte sur le « et » du
    2 et du 4.
  - **Shuffle blues** : 1-3-5-6-b7-6-5-3 en croches « balancées » en
    triolets.
  Les motifs sont des modèles génériques simples (une mesure qui se répète
  sur l'accord), pas des transcriptions de morceaux ; un accord plus court
  qu'une mesure en tronque le motif. Avec la Variabilité certains styles
  alternent un second motif (voir plus haut).
- **Intensité** : voir plus haut (aussi dans **Générer
  l'accompagnement/le riff**).

Dans **Générer l'accompagnement** il y a aussi **Renversements proches**
(coché par défaut) : chaque accord choisit le renversement le plus proche
du précédent (conduite des voix), comme le ferait un pianiste — par exemple
do-mi-sol, puis do-fa-la, puis si-ré-sol — au lieu de rester toujours à
l'état fondamental et de sauter d'une position à l'autre. Le premier accord
reste tel quel ; tous restent dans l'étendue de l'instrument et ne
s'éloignent pas trop du registre de départ. Cela vaut pour les accords d'au
moins trois notes (pas pour les arpèges et les bichords, qui ont déjà leur
motif).
- **Octave** de la ligne de basse générée.
- **Variation toutes les N accords** : toutes les N accords utilise un
  traitement légèrement différent du même accord (saut d'octave, note
  différente...) au lieu de répéter le motif à l'identique — 0 désactive
  les variations.

Les deux affichent un aperçu modifiable à la main avant de confirmer (comme
l'import audio, section 10bis), et le résultat est ajouté à la suite du
contenu déjà présent dans la piste de destination, il ne le remplace pas.

**Métrique** : on utilise la métrique initiale du projet. Basse,
accompagnement et riff répètent le motif du style sur des mesures de la
bonne durée (3 temps en 3/4 et 6/8, 6 en 12/8...), donc ils fonctionnent
avec n'importe quelle métrique ; un style pensé pour le 4/4 est tronqué à la
mesure plus courte, et il existe des styles faits exprès : **Valse** pour la
basse (fondamentale sur le 1), **Valse** et **Arpège en 6/8** pour
l'accompagnement. La batterie, en revanche, nécessite un style écrit pour
cette métrique (4/4, 3/4, 5/4, 6/8, 7/8, 12/8, ou un style personnel
enregistré dans cette métrique, voir 9bis.1) : avec une métrique sans
styles (ex. 9/8) la fenêtre le signale et désactive la confirmation.

### 9bis.1 Styles personnels : apprendre de vos morceaux

En plus des styles tout prêts, les générateurs peuvent utiliser des styles
tirés d'une de vos parties : un groove de batterie ou une ligne de basse qui
vous plaît devient un nouveau modèle, qui suit n'importe quelle grille
d'accords.

**D'où l'enregistrer** (« Enregistrer comme style du générateur... ») :
- clic droit sur un **box** dans la vue Structure du morceau ;
- menu **Composer → Styles des générateurs → Enregistrer la piste comme style...** (toute la piste sélectionnée) ;
- **Bibliothèque MIDI** (menu Composer → Gérer la bibliothèque
  MIDI) : le bouton sous l'aperçu propose tous les canaux du fichier
  sélectionné.

**La fenêtre :**
- **Partie** : pour un fichier MIDI, quel canal ;
- **Type** : Batterie (pour les parties de percussion), ou Basse,
  Accompagnement, Riff/mélodie (proposé selon l'instrument) ;
- **Accords depuis** : la partie avec les accords sur lesquels le motif
  était joué (pour un box, les accords au même endroit du morceau ; pour un
  fichier MIDI, un autre canal). Elle sert à comprendre quelle note est la
  fondamentale, la tierce, la quinte... Sans accords, la première note de
  chaque mesure sert de fondamentale ;
- **Métrique** et **Nom**. Dessous, un résumé de ce qui a été tiré
  (combien de mesures lues, grille, combien d'alternatives, s'il y a un
  fill).

**Comment il est tiré :**
- **Batterie** : les mesures sont placées sur la grille (doubles croches ou
  triolets ; croches dans les métriques en /8). La mesure la plus fréquente
  devient le groove de base, les autres différentes (jusqu'à 3) les grooves
  alternatifs, utilisés avec la variabilité, et celle avec les toms le fill.
  Sans mesure avec des toms, on utilise un fill générique (caisse claire sur
  le dernier temps). Le crash sur le premier temps n'entre pas dans le
  groove, parce que le générateur l'ajoute.
- **Basse, accompagnement, riff** : chaque note devient un **degré de
  l'accord** dans son octave (fondamentale, tierce, quinte, sixte, septième,
  ou un intervalle précis). Sur une autre grille la ligne suit les nouveaux
  accords, avec la bonne tierce (mineure sur un accord mineur). La dernière
  note avant un changement d'accord, à un demi-ton de la nouvelle
  fondamentale, devient une note d'approche vers l'accord suivant, quel
  qu'il soit. Les silences restent des silences. La mesure la plus fréquente
  est le motif de base, la deuxième la variante (utilisée avec « Variation
  toutes les N accords »), d'autres jusqu'à 3 les alternatives. Pour
  l'accompagnement on peut aussi utiliser des box faits seulement de
  symboles d'accords : on en tire le rythme. Pour la basse on garde la note
  la plus grave de chaque attaque, pour le riff la plus aiguë.

Les styles enregistrés apparaissent dans les fenêtres des générateurs avec
une **★** devant le nom, à la fin de la liste ; la batterie ne propose que
ceux de la métrique du projet. **Composer → Styles des générateurs → Styles personnels...** les liste pour les renommer ou les supprimer. Ils sont
enregistrés dans le dossier de configuration (`generator_styles.json`, à
côté des instruments personnalisés), donc ils valent pour tous les projets.

### 9bis.2 Mélodies en phrases

Dans **Générer riff/mélodie** (instruments monophoniques : trompette, sax,
flûte, voix, synth lead...), en plus des riffs qui répètent un motif sur les
notes de l'accord, il y a quatre styles qui écrivent une **vraie mélodie** :
- **Mélodie en phrases (A A' B A)** : thème, thème repris avec une autre
  fin, une phrase de contraste et la reprise du thème ;
- **Mélodie question-réponse (A A')** : la première phrase reste
  « ouverte », la seconde la reprend et la ferme ;
- **Mélodie lente (ballade)** : comme A A' B A, avec des notes longues ;
- **Mélodie animée** : comme A A' B A, avec plus de croches.

**Comment elle est construite :**
- **Phrases** de deux mesures (quatre en 3/4, 2/4 et 6/8). La forme se
  répète jusqu'à couvrir les mesures demandées ; la dernière phrase du
  morceau conclut toujours.
- **Motif** : la phrase A a un rythme et un profil qui reviennent. Dans la
  reprise, si les mêmes accords sont dessous, A revient identique, sauf la
  fin ; sur des accords différents le motif se déplace sur le nouvel accord,
  avec le même rythme et la même allure. B a un autre rythme (plus animé, ou
  plus calme dans la version animée) et monte plus haut.
- **Harmonie** : sur les temps forts (premier temps et demi-mesure, et les
  notes longues) la mélodie utilise des notes de l'accord ; sur les autres
  temps elle préfère les notes de l'accord ; en levée les notes de la
  gamme, de préférence par degrés conjoints. Les notes de l'accord
  étrangères à la gamme remplacent la note naturelle voisine (le sol# de
  `E7` en la mineur, le sib de `C7` en do).
- **Allure** : chaque phrase monte vers un point culminant, vers les deux
  tiers, puis redescend vers la cadence. Après un saut la mélodie revient en
  arrière ; elle évite les sauts énormes, trois notes identiques de suite et
  les « trilles » d'avant en arrière.
- **Cadences** : une phrase « ouverte » (la question) finit sur une note de
  l'accord autre que la tonique, de préférence la quinte ou la seconde de
  la gamme. Une phrase « fermée » (la réponse) finit sur la tonique, ou, si
  l'accord ne la contient pas (une phrase qui finit sur le V), sur la tierce
  ou la quinte de la tonique.
- **Tonalité** : celle du projet ; si elle n'est pas définie, celle
  reconnue d'après les accords de la piste choisie dans « Accords depuis ».

« Variation toutes les N accords » ne vaut pas pour ces mélodies (le champ
se désactive) : elles ont leur propre forme. Les autres réglages valent
comme pour les autres styles :
- **Variabilité** : à 0 % la mélodie ne dépend que des accords, du style et
  de la tonalité. Plus haut, **🎲 Nouvelle variation** tire un autre motif.
  Le curseur **Rythme** rend les rythmes plus variés et peut changer une
  mesure dans les reprises ; **Notes et harmonie** fait choisir des notes
  moins « évidentes » et change quelques notes dans les reprises ;
  **Dynamique** fait monter le volume vers le point culminant de chaque
  phrase et accentue les temps.
- **Intensité** : Légère rend la mélodie plus calme (moins de notes), Pleine
  plus animée, En crescendo de plus en plus animée au fil du morceau.
- **Régénérer seulement les mesures** vaut aussi ici.

## 10. Import/Export MIDI

- **Projet → Exporter → MIDI** : tout l'ensemble (pistes audibles selon
  Solo/Mute) dans un seul fichier MIDI multipiste.
- **Projet → Importer → MIDI** : crée un nouveau projet avec une piste pour
  chaque canal du fichier MIDI ; le canal 10 devient toujours Batterie.
- **Piste → Exporter cette piste / Importer dans cette piste → MIDI** : exporte
  seulement la piste sélectionnée, ou importe un fichier MIDI (avec choix du
  canal, si le fichier en contient plusieurs) en remplaçant le contenu de la
  piste courante ; il vous est aussi proposé de mettre à jour l'instrument
  d'après la reconnaissance automatique.

**Reconnaissance/création automatique de l'instrument** : pour chaque
canal, si un instrument déjà disponible (prédéfini ou personnalisé) a
exactement le Program Change GM du canal, c'est lui qui est utilisé ;
sinon **un nouvel instrument personnalisé est automatiquement créé et
enregistré** avec ce programme exact (nom dérivé du nom officiel General
MIDI, p. ex. programme 81 → `Lead2sawtooth` ; paramètres d'octave/
tessiture/voicing suggérés selon la famille, comme lors de la création
manuelle depuis **Sons → Gérer les instruments**), de sorte que la
piste importée reflète toujours fidèlement l'instrument d'origine au lieu
de se contenter du plus proche approché. À la fin de l'import, si de
nouveaux instruments ont été créés, un avertissement en affiche la liste
(ils restent toujours modifiables après coup depuis **Sons → Gérer
les instruments**). Cette création automatique n'a lieu que pour un import
réellement confirmé (pas pour le simple aperçu dans le sélecteur de canal,
qui continue d'afficher le nom de l'instrument déjà disponible le plus
proche).

**Canaux qui changent d'instrument** : si un canal change d'instrument en
cours de morceau (un Program Change entre les notes : dans *Layla* le riff
de l'intro est à la guitare overdrive puis passe au piano, sur le même
canal), l'import multipiste crée **une piste par instrument**, chacune avec
les seules notes jouées avec cet instrument et avec le volume et le pan en
vigueur quand il entre. Si le canal revient plusieurs fois au même
instrument, ces parties vont dans la même piste. Le canal de la batterie
n'est pas divisé (là, le programme choisit le kit).

Note sur la précision de l'import : la notation prend en charge les notes
chromatiques (`c#`, `eb`, etc.), donc la hauteur est conservée ; le rythme
est quantifié sur une grille de doubles croches ou, mesure par mesure, sur
une grille de **triolets** quand les attaques l'exigent (voir plus bas).

**Triolets et n-olets** : pour chaque temps, l'import choisit la
subdivision qui explique le mieux les attaques. La grille binaire (doubles
croches) l'emporte si elle les explique toutes ; sinon un triolet de
croches (`8T:`, section 2.1bis) est utilisé quand il les explique et que la
binaire ne le fait pas — typique du shuffle, du swing 2:1 et du blues en
12/8, où les notes étaient auparavant déplacées sur la double croche la
plus proche. Les sextolets (`16T:`), quintolets (`16Q:`) et septolets
(`16S:`) ont des seuils beaucoup plus stricts (il faut plus d'attaques dans
le temps et un écart très réduit), sinon un jeu humain peu précis serait
pris pour un n-olet. Les attaques quasi simultanées (grosse caisse et ride
à quelques ticks d'écart) comptent comme un seul point rythmique, et les
quintolets/septolets ne sont en pratique reconnus que sur des passages très
réguliers. La commande de grille n'est écrite que lorsqu'elle change. Une
note qui, partant d'une grille, finirait dans un temps ayant une autre
grille, à un endroit qui n'est pas une limite de temps, est fermée sur la
limite : elle peut donc être légèrement plus courte que l'originale, mais
le reste de la piste ne se décale jamais. Un fichier uniquement binaire
produit les mêmes tokens qu'avant.

**Notes superposées et voix** : en ST, les seules notes simultanées sont
celles d'un même bloc `[...]` (même durée), alors qu'en MIDI une note tenue
sous une mélodie, ou un accord qui continue sous une voix, se superposent.
Auparavant l'import sautait toute attaque tombant à l'intérieur d'une note
plus longue : dans une bibliothèque de test environ 8 % des notes
disparaissaient, et dans certains fichiers presque la moitié. Désormais
l'**import d'un fichier entier** sépare chaque canal en **voix
monophoniques** (au maximum 2 par canal, toujours : si sur une même
attaque commencent plus de groupes de durées différentes que de voix, les
groupes en excès fusionnent avec celui de la durée la plus proche ; jamais
pour la batterie) : les notes qui commencent ensemble et finissent
ensemble (à une double croche près) restent un seul bloc, chaque groupe va
dans la première voix libre, et un chevauchement minime (legato à une
double croche près) raccourcit la note précédente au lieu d'ouvrir une
voix. Les voix restent **dans la même piste** : là où seule la première joue, le
texte est comme d'habitude ; là où les autres jouent aussi, il devient un
**bloc de voix** `{ ; }` (section 2.12) sur une ligne à part, qui commence
et finit sur les barres de mesure quand cela ne coupe aucune note ; le
texte fusionné sonne exactement comme les voix séparées. (Jusqu'à la
version précédente, chaque voix devenait une piste séparée,
`Piano voce 2`.) Cela vaut aussi pour l'import d'un **seul canal** dans
une piste. Le tempo (`tempo=N`) est dans la première voix. Quand les voix sont
épuisées, la note précédente est **raccourcie** jusqu'à l'attaque
suivante : on perd la durée tenue, jamais la note.

**Paroles** : les événements *lyrics* du fichier, et le texte des fichiers
karaoké (`.kar`, événements de texte dans une piste sans notes), deviennent
des paroles entre guillemets (section 2.13) sur la première voix du canal
qui les chante (celui des notes de la même piste MIDI, ou celui dont les
notes attaquent là où tombent les syllabes) : une ligne par mesure après
ses notes, `*` pour une note sans syllabe et `""` avant un passage chanté
qui suit un passage instrumental.

 **Canaux MIDI avec beaucoup de pistes** : un fichier MIDI
n'a que 15 canaux mélodiques (le 10 est celui de la batterie) et sur chaque
canal il n'y a qu'un instrument, un seul volume/pan et un seul pitch bend.
Avec plus de 15 pistes (facile avec les voix de l'import), l'export
attribue d'abord un canal à chaque instrument *différent*, puis les canaux
restants aux voix supplémentaires, et les autres partagent le canal de leur
instrument : aucune piste ne joue jamais avec l'instrument d'une autre. Les
voix du même instrument qui partagent un canal ont le pitch bend en commun
(un slide sur l'une s'entend aussi sur les notes de l'autre pendant
qu'elles jouent ensemble).

Les notes identiques sur le même tick (doublures) et les attaques sur la
même hauteur dans la même double croche fusionnent en une seule.

**Vélocité des notes simultanées** : en ST chaque token (note, accord ou
bloc `[...]`) n'a qu'une vélocité, donc les vélocités différentes des notes
d'un même groupe (par exemple un accent sur la voix supérieure d'un accord,
ou grosse caisse et charleston frappés ensemble) ne peuvent pas être
conservées une par une : le groupe importé prend la **moyenne arrondie** des
vélocités, ce qui préserve l'intensité globale. Avec des vélocités toutes
égales rien ne change.

**Nuances à partir du volume et de l'expression (CC7/CC11)** : crescendos,
diminuendos et fondus du fichier MIDI sont des automations continues, que
ST n'exprime que par la vélocité des notes (section 2.5). L'import calcule
le niveau CC7 x CC11 au moment de chaque attaque, le normalise par rapport
au maximum du canal et l'applique à la vélocité de la note : la note la plus
forte du canal garde sa vélocité d'origine, les autres baissent en
proportion, et le résultat apparaît comme une série de `N@` (par paliers,
un pour chaque note qui change, pas comme une rampe `>>`). Un volume
constant (typiquement CC7 = 100) ou une variation inférieure à 15 % du
maximum n'est pas une nuance et est ignoré. Le volume *absolu* du canal par
rapport aux autres n'est pas importé (il se règle depuis la table de
mixage).

**Articulations (`!`, `x`, `_`)** : pour les notes seules et les accords
implicites (option « Reconnaître les accords ») l'import compare la durée
réelle de la note à l'intervalle jusqu'à l'attaque suivante : environ la
moitié → staccato `!` (section 2.2), moins de 30 % → étouffé `x`, plus de
105 % (note qui chevauche la suivante) → legato `_`. Dans ce cas le token
occupe tout l'intervalle jusqu'à la note suivante (p. ex. `2c*4!`) au lieu
d'une note courte suivie de silences, et reste ainsi modifiable comme un
musicien l'aurait écrit. Une note courte suivie d'un long silence (plus
d'un temps, ou d'un demi-temps pour l'étouffé) reste note + silence : ce
n'est pas une articulation. Les notes normales (environ 70 %-105 %), les
blocs explicites `[...]` (sans modificateur final, section 2.2), les slides
et la batterie ne changent pas.

**Tempo, mesure et pédale** : les changements de tempo du fichier
deviennent des marqueurs `tempo=N` (section 2.6) — dans **une seule** piste,
car le tempo est global en ST : on choisit celle sur laquelle les
marqueurs glissent le moins (en général la batterie, faite de coups brefs ;
un marqueur qui tomberait à l'intérieur d'une note longue est émis à sa
fin). Le tempo initial reste celui du projet et les petites oscillations
(moins de 2 BPM ou de 2 % : le bruit d'un tempo enregistré en direct) ne
sont pas des changements de tempo et sont ignorées. La mesure (événement
*time signature*) définit le champ **Métrique** du projet ; si elle change au
cours du morceau elle devient la liste par mesure (`Metrica: 1: 3/4, 3:
4/4`, section 2.7). La pédale de sustain (CC64, enfoncée à partir de 64)
devient `SON`/`SOFF` (section 2.4), seulement aux transitions effectives ;
une pédale encore enfoncée en fin de canal est fermée par un `SOFF` final.
L'export MIDI écrit désormais aussi la mesure, de sorte qu'un aller-retour
export→import la conserve. Lors de l'import d'un seul canal dans une piste
existante, les changements de tempo et de mesure ne sont PAS importés (ils
sont globaux au projet), la pédale oui.

**Bending (pitch bend)** : une note seule (jamais un accord) dont le pitch
bend atteint au moins un demi-ton entier pendant sa durée est importée
comme un **slide** (`c*4>d*4`, section 2) de la hauteur de départ au sommet
du bend, au lieu d'être aplatie sur la hauteur nominale — utile en
particulier pour les MIDI de guitare blues/rock, où le bending fait souvent
partie intégrante de la phrase. Si la molette revient ensuite nettement
vers un demi-ton différent avant la fin de la note (bend-and-release,
technique courante : on monte puis on relâche), le slide importé a une
troisième étape (`c*4>d*4>c*4`, section 2.3) au lieu de s'arrêter au seul
sommet. Les durées des étapes (section 2.3) reflètent le timing RÉEL du
bend détecté dans le MIDI source — le moment où le sommet est atteint par
rapport à la durée de la note — au lieu de toujours supposer une division
à moitié entre rampe et tenue/relâchement : un bend rapide suivi d'une
longue tenue (p. ex. `1c*4>3d*4`) sonne donc différemment, et plus
fidèlement à l'original, qu'un bend lent qui n'atteint le sommet que vers
la fin (p. ex. `3c*4>1d*4`). La sensibilité du pitch bend déclarée dans le
fichier (RPN 0, Pitch Bend Sensitivity) est respectée ; si le fichier ne la
déclare pas, on suppose la valeur par défaut General MIDI (±2 demi-tons).
Un bend qui s'arrondit à 0 demi-ton (vibrato ou imprécisions
d'enregistrement), trop petit par rapport à la pleine échelle de la molette
(une automation continue d'expression/humanisation, pas un bend délibéré)
ou d'une amplitude invraisemblable (plus de 12 demi-tons : les vrais bends
de guitare restent presque toujours dans les 2-3 demi-tons, et un saut plus
large n'est un bend sur aucun instrument — ce serait une note différente,
pas une inflexion de la même ; cela arrive quand la sensibilité RPN
déclarée reflète une capacité technique du canal, pas l'intention de bend
de cette note précise) reste une note normale, pour éviter un slide sans
sens musical.

**Slide guitar (Options → Import MIDI → Slides à l'import MIDI...)** : sur un canal avec
une sensibilité de pitch bend large (12 demi-tons, typique des MIDI de
guitare slide) le seuil habituel est d'environ 1,2 demi-ton, et les bends
brefs d'un demi-ton restent des notes normales. En cochant **Slide** dans
la fenêtre, on active le champ **Seuil** (0,5-1,2 demi-ton, 0,8 par
défaut) : l'import reconnaît aussi comme slides les bends plus petits. Le
seuil ne peut que descendre, donc sur les canaux à sensibilité étroite
(p. ex. 2 demi-tons) rien ne change. Plus il est bas, plus on trouve de
slides mais plus le risque augmente de prendre pour un slide une
expression de la molette (constaté sur des morceaux de jazz) : gardez-le
haut pour les morceaux sans slide. Le réglage vaut à partir du prochain
import et sans la case cochée l'import reste identique à avant. Le
**timing du relâchement** est celui, réel, du fichier : un bend qui monte
tout de suite, reste au sommet presque toute la note et ne relâche qu'à la
fin devient une chaîne à 4 étapes avec la tenue comme rampe plate
(`1f*5>11g*5>1g*5>3f*5` : monte, tient le sol, relâche, reste sur le fa) ;
un bend qui relâche tout de suite puis reste sur la hauteur écrite a la
longue tenue finale (`1e*5>1d#*5>2e*5`), au lieu d'être étalé linéairement
sur toute la note (ce qui faisait glisser l'intonation pendant toute la
durée). Si le relâchement ne commence qu'au tout dernier instant, la note
se termine alors qu'elle relâche encore et on écrit un simple bend avec
tenue (`1f*5>3g*5`). Une **queue de relâchement** de la note précédente (la
molette redescend encore vers le centre quand la note commence) n'est pas
un bend : la référence reste le centre.

**Bends qui partent tard et bends dans les deux sens** (typiques du slide/
bottleneck) : si la molette reste presque immobile pendant un moment (au
moins 15 % de la note, avec de petites dérives) avant de bouger, le slide a
une tenue initiale (`7d*4>1d*4>8c#*4` : reste immobile, puis descend) au
lieu de partir de l'attaque. Si la molette fait des excursions
significatives des *deux* côtés de la note écrite (monte d'un ton puis
descend en dessous), le bend est importé comme un parcours à étapes — la
courbe de la molette simplifiée (écart maximal 0,7 demi-ton) et arrondie
aux demi-tons — au lieu de ne garder que l'excursion la plus grande. Sur
des notes de quelques doubles croches, la grille limite la précision :
chaque rampe occupe au moins une double croche.

**Bends larges (jusqu'à une octave)** : la limite était de 4 demi-tons ;
elle est désormais de **12** (une octave), car avec une sensibilité de
molette déclarée (RPN) large il existe de vrais glissandos et inflexions de
5 à 12 demi-tons — slide/bottleneck, la chute de hauteur façon bande des
cordes dans *Strawberry Fields Forever*, les « dives » au vibrato. Au-delà
de l'octave cela reste une note normale (ce n'est pas une inflexion). Si un
canal part déjà infléchi (scoop) et qu'à l'intérieur de la note la molette
plonge **plus loin** du centre que son point de départ d'au moins 1,5
demi-ton (part à -4, descend à -12, puis remonte), la plongée est
conservée : parcours à étapes avec le centre comme référence, pas un simple
scoop. Une plongée tardive (après la moitié de la note, avec au moins 3
événements dans la descente) laisse la note immobile jusque-là.

**Pré-bend de la note suivante** : quand la molette s'éloigne du centre
dans les derniers ticks d'une note (à un dixième de temps près) et est
encore décentrée à l'attaque de la suivante, ce mouvement est le pré-bend
de l'AUTRE note et non un bend fantôme en fin de la première. Si au
contraire elle revient à 0 pile à l'attaque suivante (un fall-off qui se
remet à zéro), il appartient à la note qui se termine.

Un **pré-bend / scoop** (la molette est déjà décentrée *avant* l'attaque et
revient au centre pendant la note : corde déjà tirée puis relâchée, ou note
« prise par en dessous », typique des MIDI de guitare et de voix) est
importé comme slide de la hauteur de départ *réelle* vers la note écrite :
une molette à -1 demi-ton qui remonte à 0 sur un ré devient `c#*4>d*4` (do#
qui monte au ré), et une à +1 qui descend devient `d#*4>d*4`. La hauteur
écrite dans le MIDI est toujours celle d'arrivée. Une molette décentrée
qui ne revient JAMAIS au centre pendant la note reste un décalage statique
du canal (note normale). Attention : les slides de ST travaillent en
demi-tons entiers, donc une inflexion réelle d'environ un demi-ton est
arrondie au demi-ton entier le plus proche.

**Option « Reconnaître les accords à l'import MIDI »** (**Options** → case
du même nom, désactivée par défaut) : quand un groupe de notes simultanées
correspond à une qualité d'accord standard (p. ex. do majeur), il est
importé sous la forme implicite équivalente (`C*4`) plutôt que comme bloc
explicite (`[c*4 e*4 g*4]`) — plus lisible et plus facile à transposer à la
main. Un accord non reconnaissable (p. ex. une simple quinte, ambiguë entre
majeur et mineur) reste de toute façon un bloc explicite. **Attention** :
contrairement au bloc explicite, qui reproduit toujours fidèlement le
voicing et le registre d'origine du MIDI, la forme implicite est
**re-voicée automatiquement par le moteur** selon l'instrument de la piste
lors de l'export suivant — utile pour adapter l'accord à l'instrument de
destination, mais un aller-retour import→export ne reproduira plus
nécessairement exactement les mêmes notes que le fichier d'origine. Le
comportement par défaut (bloc explicite) reste donc le plus fidèle.

### 10.1 Exporter la partition (MusicXML)

**Projet → Exporter → Partition MusicXML...** enregistre le morceau
comme partition au format **MusicXML** (`.musicxml`), qui s'ouvre avec les
logiciels de notation : MuseScore (gratuit), Finale, Sibelius, Dorico et
bien d'autres. De là, on peut imprimer, exporter en PDF, corriger la mise
en page ou ajouter les paroles. Comme l'export MIDI, elle contient les
**pistes audibles** (elle tient compte de Solo et Mute) ; les pistes audio
n'ont pas de notes et en sont exclues.

Ce que contient la partition :

- **une partie par piste**, avec le nom de la piste ;
- **les notes** exactement comme SoundText les joue : les accords
  apparaissent avec les notes choisies par le moteur de voicing, les blocs
  `[...]` comme des accords écrits ;
- **les symboles d'accords** (`Am7`, `C/E`...) au-dessus de la portée,
  écrits seulement quand l'accord change, comme dans une grille (lead
  sheet) ;
- **la tonalité** du projet (section 2.7bis) comme armure ; les notes des
  accords utilisent les bémols dans les tonalités à bémols ;
- **mesure et tempo**, y compris les changements par mesure (section 2.7)
  et les marqueurs de tempo dans les pistes ;
- **triolets, quintolets et septolets** avec leur crochet ;
- **nuances** tirées de la vélocité (`p`, `mf`, `f`...), écrites seulement
  quand le nouveau niveau dure au moins quatre notes, **articulations**
  (staccato, étouffé, legato) et **pédale** de sustain.
- **les voix** des blocs `{ ; }` (section 2.12) comme voix de la même
  portée, hampes vers le haut et vers le bas ;
- **les paroles** (section 2.13) sous les notes, avec tirets et lignes de
  prolongation.

Les clés suivent les conventions des parties imprimées : pianos et orgues
sur deux portées (sol et fa, séparées au do central), guitares en clé de
sol et basses en clé de fa avec le **8 en dessous** (elles sonnent une
octave sous la note écrite), les autres instruments en clé de sol ou de fa
selon leur registre. La batterie utilise la portée de percussion avec les
positions habituelles (grosse caisse en bas, caisse claire au milieu,
cymbales en haut avec la tête en **x**).

Une durée qui ne correspond pas à une valeur de note (par exemple 5
croches) est écrite en notes **liées**, et une note qui franchit la barre
de mesure continue liée dans la mesure suivante.

**Limites** : dans une même voix, deux notes qui se superposent (cela
arrive dans les morceaux importés depuis un MIDI) ne peuvent pas
coexister : la première est raccourcie jusqu'à l'attaque de la seconde.
Pour écrire vraiment plusieurs voix, on utilise les blocs `{ ; }`. Les
slides n'apparaissent qu'avec leur note de départ.

### 10.1bis Voir et imprimer la partition (Affichage → Partition)

**Affichage → Partition...** (`Ctrl+Shift+P`) ouvre une fenêtre avec les
pistes sur la portée, mises en page sur des pages A4 : les mêmes notes,
grilles d'accords, voix et paroles que l'export MusicXML, **sans logiciel
externe**. La fenêtre reste ouverte à côté de l'éditeur et **se met à jour
pendant la saisie** (après une courte pause).

- **Toutes les pistes audibles** ou **Piste sélectionnée seulement**.
- **−** / **+** : zoom.
- **Exporter en PDF...** enregistre la partition en PDF (vectoriel,
  imprimable à n'importe quelle taille) ; **Imprimer...** l'envoie à
  l'imprimante.
- Si une piste a une erreur de syntaxe, la dernière partition valide
  reste visible, avec le message d'erreur.

**Projet → Exporter → Partition PDF...** fait la même chose sans ouvrir
la fenêtre.

La mise en page est faite par **Verovio**, une bibliothèque libre de
gravure musicale (LGPL) installée avec SoundText. Si elle manque, la
fenêtre explique comment l'installer (`pip install verovio`) ; l'export
MusicXML fonctionne de toute façon. Pour les retouches de mise en page
(espacements, texte libre sur la page), la voie MusicXML → MuseScore
reste disponible.

### 10.2 Importer une partition (MusicXML)

**Projet → Importer → MusicXML...** crée un nouveau projet à partir d'une
partition **MusicXML** (`.musicxml`, `.mxl` compressé ou `.xml`), le
format d'échange de MuseScore, Finale, Sibelius, Dorico et de presque tous
les logiciels de notation ; beaucoup de partitions gratuites en ligne se
téléchargent dans ce format. On peut aussi l'ouvrir directement depuis la
ligne de commande (`soundtext morceau.musicxml`).

Ce que devient la partition :

- **une piste par partie**, avec le nom de la partie (« Flûte »,
  « Violon I »...) et l'instrument indiqué dans la partition (ou reconnu
  d'après le nom de la partie) ; deux voix sur la même portée deviennent
  des voix de la même piste (blocs `{ ; }`, section 2.12), comme dans
  l'import MIDI (section 10) ;
- **les notes à la hauteur réelle** : les instruments transpositeurs
  (sax, clarinette, trompette en si♭, guitare écrite à l'octave) sonnent
  comme on les entend, pas comme ils sont écrits ;
- **tempo, métrique et tonalité**, avec les changements de tempo et de
  métrique, et les **nuances** (`p`, `mf`, `f`...) comme vélocité ;
- **reprises, 1re/2e fois, D.C., D.S., Fine et Coda** déroulées dans
  l'ordre où on les joue ; après un D.C. ou un D.S. les reprises ne se
  répètent pas et on joue la dernière fois, selon l'usage ;
- **les notes liées** deviennent une seule note ; une mesure en
  **anacrouse** au début est complétée par un silence, pour que les
  mesures restent à leur place ;
- **les symboles d'accords** (`Am7`, `G7b9`, `C/E`...) deviennent une
  piste **Accords** (« Accordi ») : dans un lead sheet (mélodie et
  accords) elle s'entend et accompagne la mélodie ; si la partition a déjà
  d'autres parties qui jouent l'harmonie, la piste est muette (il suffit
  d'enlever le Mute pour l'entendre). Les accords que SoundText n'a pas
  deviennent le plus proche (par exemple `m11` devient `m9`).

La batterie écrite sur la portée de percussion devient une piste de
percussions, avec les sons indiqués dans la partition. Les notes
d'ornement (écrites en petit) sont ignorées. Les **paroles** deviennent
des paroles entre guillemets (section 2.13), avec tirets et élisions ; dans
les reprises, on prend le couplet du passage (le 1 la première fois, le 2
la deuxième), s'il existe. L'option
**Reconnaître les accords** de l'import MIDI s'applique ici aussi.

### 10.3 Notation ABC (importer et exporter)

L'**ABC** est une notation musicale en texte seul (standard 2.1), utilisée
par les grands recueils de musique traditionnelle et folk et par des
programmes comme abcjs, EasyABC, abcm2ps et abc2midi : un morceau `.abc`
se lit et s'écrit aussi à la main.

**Projet → Exporter → Partition ABC...** enregistre les pistes audibles
comme un morceau ABC :

- chaque piste est une **voix** (`V:`) avec son nom et son instrument
  (`%%MIDI program`) ; piano et orgue ont deux portées réunies par une
  accolade, les voix des blocs `{ ; }` partagent une portée (`%%score`) ;
  la batterie est sur le canal 10, avec les notes des sons General MIDI ;
- **tonalité** (`K:`), **mesure** (`M:`, avec les changements dans toutes
  les voix), **tempo** (`Q:`), **symboles d'accords** entre guillemets,
  **nuances** (`!mf!`), staccato et tenuto, **triolets** et autres
  n-olets, notes liées d'une mesure à l'autre et **paroles** (`w:`) ;
- guitares et basses utilisent la clé à l'octave inférieure (`treble-8`,
  `bass-8`), avec les notes écrites une octave plus haut comme le veut le
  standard.

Les slides deviennent leur première note ; la pédale et les automations
(`vol=`, `pan=`... section 2.15) ne sont pas écrites (elles ne sont pas
dans le standard).

**Projet → Importer → ABC...** crée un nouveau projet à partir du premier
morceau du fichier (on peut aussi l'ouvrir en ligne de commande :
`soundtext morceau.abc`). Sont lus : notes, silences, accords `[CEG]`,
unité de note (`L:`, ou celle qui découle de la mesure), rythme pointé
(`>` `<`), n-olets `(3`, `(p:q:r`, liaisons (aussi d'une mesure à
l'autre, avec les altérations), altérations valables jusqu'à la barre de
mesure, tonalités avec les modes (`Dmix`, `Ador`... : elles deviennent la
tonalité de même armure), changements `[K:]` `[M:]` `[L:]` `[Q:]`,
**reprises et 1re/2e fois** déroulées, la mesure **en anacrouse**,
nuances, symboles d'accords (dans la piste **Accords**, comme pour le
MusicXML) et paroles avec plusieurs couplets. Chaque voix est une piste ;
les voix d'une même portée (`%%score (S A)`) vont dans une seule piste,
de même que les deux portées du piano (`{RH | LH}`). L'instrument vient
de `%%MIDI program` (`%%MIDI channel 10` ou `clef=perc` pour la
batterie), sinon du nom de la voix. Les clés à l'octave, `transpose=` et
`octave=` sonnent à la hauteur réelle. Les notes d'agrément, les parties
(`P:`) et les ornements qui ne changent pas le son sont ignorés.

## 10bis. Import audio (voix/micro/fichier)

Menu **Piste → Importer dans cette piste → Audio → notation (micro ou fichier)...**
(aussi depuis le menu **⋯** de la piste, entrée « Importer de l'audio →
notes... », et sous la forme « Importer de l'audio (dans ce pattern) » dans
la fenêtre **Composer → Gérer la bibliothèque de patterns**, pour
capturer directement un pattern réutilisable plutôt qu'une piste) :
convertit une idée musicale captée au micro ou depuis un fichier audio
(`.wav`/`.mp3`/`.m4a`) directement en notation texte, insérée dans la piste
(ou dans le corps du pattern) après un aperçu texte et une écoute
facultative.

- **Source** : bouton d'enregistrement (Start/Stop) depuis le micro, ou
  faites glisser un fichier dans la zone prévue (glisser-déposer) ou
  utilisez « Parcourir les fichiers... ». En enregistrant avec le
  **Métronome** activé, le clic redémarre avec l'enregistrement : le
  premier temps coïncide avec le début du fichier et la transcription suit
  le métronome (un silence avant la première note reste un silence). Sans
  métronome, la transcription part de la première note, quel que soit le
  moment où vous avez appuyé sur Enregistrer. Le micro nécessite
  `libportaudio2` installé au niveau du système sous Linux (voir la section
  Installation) ; les fichiers mp3, m4a, flac et ogg sont lus par le
  décodeur de Qt Multimedia, déjà inclus dans PySide6 (ou par `ffmpeg`, si
  le PySide6 de la distribution ne l'inclut pas). S'il manque quelque chose,
  la fenêtre le signale par un message explicite au lieu d'échouer en
  silence.
- **Quantification** : sélecteur avec Off, 1/4, 1/8, 1/16 (par défaut),
  1/32, plus une case « Ternaire » (triolets 8T/16T) active seulement pour
  1/8 et 1/16. « Off » n'introduit pas un nouveau type de timing libre : il
  utilise en interne une grille très fine (1/64), sous le seuil de
  quantification perceptible, tout en restant dans la syntaxe normale
  `N:`. La dernière combinaison utilisée est mémorisée à la réouverture de
  la fenêtre.
- **Mode d'analyse** : Mélodique (détection de hauteur, pour la voix ou les
  instruments qui jouent une note à la fois : les accords ne sont pas
  reconnus) ou Percussive (détection des transitoires pour batterie/
  beatbox, classés automatiquement en `kick`/`snare`/`hihat`). Pré-rempli
  selon l'instrument de la piste courante, mais toujours modifiable à la
  main. En mode Percussive la quantification choisie compte aussi pour la
  détection : deux coups plus proches qu'environ la moitié d'une case de la
  grille sont considérés comme un seul coup (avec 1/16 à 120 BPM, 75 ms),
  donc choisissez une grille au moins aussi fine que les notes les plus
  rapides que vous avez jouées (1/8 pour un charleston en croches, 1/16 pour
  les doubles croches).
- **Algorithmes** : les attaques sont trouvées avec SuperFlux (flux
  spectral qui ne prend pas le vibrato pour une nouvelle note), la hauteur
  avec YIN ; ils sont écrits dans SoundText (en numpy), sans bibliothèque
  à installer.
- **Paramètres avancés de suivi de hauteur** (mode Mélodique seulement) :
  ils permettent d'adapter la reconnaissance à un audio précis au lieu de
  se contenter du résultat par défaut — réglez les valeurs, appuyez de
  nouveau sur « Convertir en SoundText » pour réessayer sur le même
  fichier, répétez jusqu'à ce que le résultat vous convainque :
  - **Fréquence minimale** : automatique (déduite de la tessiture grave de
    l'instrument de destination) ou une valeur en Hz choisie à la main.
  - **Fenêtre d'analyse** : nombre d'échantillons par estimation — plus
    large, elle aide pour les basses/notes graves mais dégrade la
    résolution temporelle (attaques/notes brèves moins précises).
  - **Pas d'analyse (hop size)** : distance en échantillons entre une
    estimation et la suivante — plus petit, il donne plus de résolution
    temporelle mais une analyse plus lente.
  - **Seuil de confiance** : confiance minimale pour accepter une
    estimation.
  - **Durée minimale de note** : écarte les notes plus brèves que ce seuil,
    presque toujours des artefacts (onsets parasites rapprochés, typiques
    d'un vibrato marqué).
  - **Rétablir les valeurs standard** : ramène tout le panneau aux valeurs
    par défaut.
- **Source : voix/beatbox** : case à cocher quand vous chantez/fredonnez la
  partie (basse, mélodie...) ou imitez la batterie avec la bouche, au lieu
  d'enregistrer le vrai instrument. La voix humaine a des caractéristiques
  acoustiques différentes d'un instrument réel : justesse moins stable note
  par note (elle se fragmente facilement en notes brèves et erratiques) et,
  pour la batterie, aucune vraie résonance grave comme celle d'une grosse
  caisse (le conduit vocal est physiquement trop court pour la produire).
  Avec la case cochée : pour la partie mélodique, la fenêtre d'analyse
  n'est pas élargie sur la tessiture grave de l'instrument de destination
  (inutile si vous chantez de toute façon dans votre propre tessiture, et
  nuisible à la résolution temporelle) ; pour la batterie, les seuils
  kick/snare/hihat sont recalibrés sur un « boum » de bouche plutôt que sur
  une vraie grosse caisse.
- **Conversion** : le bouton « Convertir en SoundText » analyse l'audio en
  arrière-plan (avec une barre de progression ; « Annuler » l'interrompt et
  vous pouvez réessayer tout de suite avec d'autres paramètres) et affiche
  le résultat dans un aperçu avec coloration syntaxique, avant une
  éventuelle insertion ; le texte généré est toujours validé et n'est
  jamais inséré s'il se révélait syntaxiquement invalide.
- **Aperçu modifiable** : une fois la conversion terminée, l'aperçu n'est
  plus en lecture seule : vous pouvez corriger à la main une note fausse ou
  essayer une variante directement dans le texte, avant de confirmer.
  « Écouter l'aperçu » joue toujours le contenu ACTUEL de l'éditeur (y
  compris les modifications faites à la main, pas le texte d'origine généré
  par l'analyse) ; si les modifications cassent la syntaxe, « Écouter
  l'aperçu » comme Ok signalent l'erreur au lieu de continuer. Une nouvelle
  conversion (nouveau fichier, autre algorithme de hauteur, etc.) écrase
  toute modification manuelle pas encore confirmée.
- **Écouter l'aperçu** : le bouton « ▶ Écouter l'aperçu » (avec « ■ Stop »
  à côté), activé après une conversion réussie, joue le contenu actuel de
  l'aperçu avec l'instrument de destination avant de confirmer par Ok —
  utile pour vérifier à l'oreille la conversion (ou votre propre variante)
  avant de remplacer le contenu de la piste/du pattern.

Note sur la qualité de la reconnaissance : la détection des notes
mélodiques segmente l'audio avec un détecteur d'attaques dédié (fiable même
dans le registre grave et sur les transitions « legato » typiques du chant,
sans silence entre une note et l'autre) et estime la hauteur de chaque note
par la médiane des mesures dans l'intervalle — plus robuste au vibrato et
aux petites imprécisions de justesse d'une voix non professionnelle qu'une
mesure instantanée unique. Chaque note se termine quand le son s'éteint
(pas forcément à l'attaque suivante), donc les notes détachées laissent des
silences ; la même note jouée plusieurs fois de suite (typique de la basse)
reste une série de notes distinctes, même sans silence entre elles, alors
qu'une note tenue avec vibrato ou trémolo reste une seule note. La
dynamique est relative : la note (ou le coup) la plus forte de
l'enregistrement devient `110@` et les autres baissent en proportion, par
pas de 10, de sorte que même un enregistrement à faible volume sonne plein
et que le texte ne se remplit pas de petits changements de `@`. Pour les
notes les plus graves (p. ex. basse), la fenêtre d'analyse s'élargit
automatiquement selon la tessiture minimale de l'instrument de
destination, pour une estimation de hauteur plus précise (cela n'influe
pas sur la détection de l'attaque, gérée à part). La classification
percussive automatique ne reconnaît que `kick`/`snare`/`hihat` à partir du
spectre du « corps » du coup (juste après le transitoire d'attaque ; pas
tom/crash/ride/hihat_open, peu fiable sans modèle dédié) ; le texte généré
reste de toute façon modifiable à la main comme n'importe quel autre
token. Les seuils du mode « voix/beatbox » sont une estimation raisonnée
fondée sur le comportement acoustique du conduit vocal, non calibrée sur
des enregistrements réels : si les résultats ne sont pas satisfaisants, le
script `diagnose_audio.py` (dans le dossier du programme) permet
d'inspecter les données brutes utilisées par la classification sur votre
propre enregistrement, pour un calibrage ciblé plutôt qu'à tâtons ;
corriger à la main le texte généré reste de toute façon toujours possible.

## 10ter. Jouer au clavier (clavier de l'ordinateur ou clavier MIDI)

Menu **Piste → Jouer au clavier dans cette piste...** (aussi comme entrée
« Jouer au clavier... » du menu **⋯** de la piste, et comme « Jouer au
clavier (dans ce pattern) » dans la fenêtre **Composer → Gérer la
bibliothèque de patterns**) : enregistre une performance jouée en direct
avec le clavier de l'ordinateur — utilisé comme s'il était un petit
instrument de musique — et la convertit en notation, avec le même
déroulement final (aperçu modifiable, « Écouter l'aperçu », Ok/Annuler)
que la fenêtre d'import audio (section 10bis), dont elle est le pendant
« instrument joué en direct » au lieu d'« audio enregistré/chargé ».

- **Disposition du clavier** (disposition italienne) : trois rangées de 12
  touches chacune, chacune une octave au-dessus de la précédente,
  parcourues chromatiquement à partir de do — rangée des chiffres
  (`1`...`0`, `'`, `ì`) sur l'octave choisie avec le sélecteur « Octave »
  de la fenêtre, rangée `Q`...`P`, `è`, `+` une octave au-dessus, rangée
  `A`...`L`, `ò`, `à`, `ù` deux octaves au-dessus. La légende exacte (avec
  l'octave effective de chaque rangée) est toujours visible dans la
  fenêtre.
- **Indépendance vis-à-vis de la langue du clavier** : les notes (trois
  rangées ci-dessus) et la rangée des qualités d'accord
  (`Z X C V B N M , . /`, section suivante) sont liées à la POSITION
  physique de la touche enfoncée, pas au caractère qu'elle produit — en
  changeant la langue/la disposition du système (p. ex. d'italien à
  français/US/allemand) les mêmes touches physiques continuent de jouer les
  mêmes notes, même si le caractère imprimé sur la touche (ou produit en
  tapant ailleurs) est différent. Cela couvre 45 des 46 touches
  concernées : la seule exclue est la dernière touche de la rangée
  `A`...`L` (celle qui produit `ù` en disposition italienne — une touche
  « en plus » des dispositions ISO européennes sans équivalent unique sur
  un clavier US, dont la position physique exacte ne peut pas être
  déterminée de façon fiable sur toutes les dispositions). Un repli est
  tout de même disponible pour cette touche : **Entrée** (aussi bien la
  principale que celle du pavé numérique) joue toujours la même note que
  `ù`, quelle que soit la disposition active — Entrée n'est pas une touche
  de caractère, donc sa position est en soi indépendante de la
  disposition. Vérifié sous Linux (X11 et Wayland) ; sous Windows et macOS
  cela repose sur les mêmes standards documentés mais il n'a pas été
  possible de le vérifier de manière interactive pendant le
  développement — si une touche se révélait mal placée sur ces
  plateformes, signalez-le.
- **Accords à la volée** : en maintenant une touche de la rangée
  `Z X C V B N M , . /` avec la touche de note (n'importe laquelle des trois
  rangées ci-dessus), on joue l'accord correspondant au lieu de la note
  seule :

  | Touche | Qualité | Intervalles |
  |---|---|---|
  | `Z` | Majeur | 1 - 3 - 5 |
  | `X` | Mineur | 1 - ♭3 - 5 |
  | `C` | 7e de dominante | 1 - 3 - 5 - ♭7 |
  | `V` | Mineur 7 | 1 - ♭3 - 5 - ♭7 |
  | `B` | Majeur 7 | 1 - 3 - 5 - 7 |
  | `N` | Suspendu (sus4) | 1 - 4 - 5 |
  | `M` | 9e ajoutée (add9) | 1 - 3 - 5 - 9 |
  | `,` | Diminué 7 | 1 - ♭3 - ♭5 - 𝄫7 |
  | `.` | Power Chord | 1 - 5 - 8 |
  | `/` | Basse profonde | note + octave en dessous (pas un vrai accord) |

  La touche de qualité doit être maintenue AVANT/en même temps que la
  touche de note (l'enfoncer après ne « met pas à jour » rétroactivement
  une note déjà jouée) ; si plusieurs touches de qualité sont maintenues
  ensemble, c'est la dernière enfoncée encore active qui l'emporte. Comme
  pour les notes, cette rangée ne dépend pas de la disposition choisie
  (Chromatique/Gamme de la tonalité/Jankó) : elle fonctionne de la même
  façon dans tous les modes.
- **Touches de jeu** :
  - `Verr. Maj` (**Sustain**, maintenue) : la note/l'accord reste audible
    et sa durée dans la piste enregistrée reste ouverte même après avoir
    relâché la touche de note, jusqu'à ce qu'on relâche aussi `Verr. Maj` —
    utile pour des accords tenus pendant qu'on appuie déjà sur la note
    suivante. Note : le voyant Verr. Maj du clavier peut quand même
    s'allumer/s'éteindre à chaque pression (cela dépend du système/pilote) :
    cela n'influe pas sur le fonctionnement, c'est juste un effet secondaire
    inoffensif.
  - `Alt gauche` (**Strumming**, maintenue) : quand on appuie sur une
    touche de note avec un accord actif (rangée des qualités), les notes de
    l'accord ne partent plus toutes ensemble mais en succession très rapide
    (environ 20 ms l'une de l'autre), comme un coup de médiator à la
    guitare — elles restent toutes audibles jusqu'à ce que la touche de note
    soit relâchée (seule l'attaque est échelonnée, pas la fin).
  - `Maj gauche` (**Bending**, maintenue) : imite un vrai bend de guitare
    sur une note seule — en direct on entend la note monter progressivement
    d'un ton entier (rampe d'environ 120 ms, pas un saut sec) et, au
    relâchement, redescendre tout aussi progressivement avant de s'arrêter
    (environ 80 ms), exactement comme quand on relâche une corde tirée. Dans
    la piste enregistrée, c'est capturé comme un vrai portamento/slide (même
    syntaxe que `c*4>d*4`), qui est joué/exporté en MIDI avec un pitch bend
    continu, pas deux notes distinctes. Cela ne s'applique sous cette forme
    qu'à une note seule (aucun accord de la rangée des qualités ni basse
    profonde actifs, et pas avec l'Arpégiateur) : sur un accord, ou avec
    l'Arpégiateur actif, on se rabat sur un simple décalage fixe de 2
    demi-tons appliqué tout de suite à toutes les notes.
  - `Ctrl gauche` (**Renversement**, maintenue) : déplace la note la plus
    grave de l'accord une octave plus haut (1er renversement), pour des
    enchaînements harmoniques plus fluides. Cela ne s'applique qu'aux
    accords (rangée des qualités active), pas aux notes seules.
  - `Tab` (**Piano/Forte**) : bascule la dynamique des notes jouées à partir
    de ce moment — actif = Piano (vélocité 60), inactif = Forte (vélocité
    110, état de départ). Contrairement aux autres touches de jeu, il ne
    faut pas la maintenir : une pression bascule l'état.
  - **Barre d'espace** (**Arpégiateur**, maintenue) : chaque touche de note
    enfoncée À PARTIR DE CE MOMENT (une note déjà jouée avant d'appuyer sur
    la barre continue normalement, sans être arpégée rétroactivement) entre
    dans un réservoir commun dont les hauteurs sont jouées une à la fois, en
    boucle continue, à la double croche du tempo du projet — en maintenant
    plusieurs touches de note (ou un accord avec la rangée des qualités) on
    entend/enregistre un arpège qui parcourt toutes leurs notes. Le
    réservoir se met à jour en direct si on ajoute/retire des touches de
    note pendant que la barre reste enfoncée.

  Toutes les touches de jeu maintenues (Sustain/Strumming/Bending/
  Renversement/Arpégiateur) doivent être maintenues AVANT ou en même temps
  que la touche de note : les enfoncer après n'a pas d'effet rétroactif sur
  une note déjà en cours.

  Note technique : Qt ne distingue pas de façon portable la touche gauche
  de la droite pour Ctrl/Alt/Maj, donc celles-ci répondent à Ctrl/Alt/Maj
  en général (n'importe quel côté), pas seulement à la touche gauche
  décrite ci-dessus.
- **Piste de percussion** : si l'instrument de destination est percussif,
  les trois rangées physiques (chiffres, Q, A — les mêmes que pour les
  notes, voir plus haut) jouent à la place les 36 identifiants de
  percussion listés à la section 6, dans le même ordre que dans la légende
  de la fenêtre (qui affiche à l'écran quelle touche produit quel son), sans
  octave.
- **Retour sonore immédiat** : pendant l'enregistrement ou quand on appuie
  sur « Jouer » (essai sans enregistrer), chaque touche enfoncée s'entend
  tout de suite, synthétisée en temps réel avec l'instrument de
  destination — contrairement au reste de la lecture de l'application,
  toujours hors ligne (voir section 12), ici une latence minimale est
  nécessaire. Si la piste a un instrument plugin (instrument SFZ interne,
  LV2 ou VST3), les touches sont jouées par lui, avec le son qu'aura la
  piste ; l'instrument commence à se charger à l'ouverture de la fenêtre et,
  s'il ne s'ouvre pas, le SoundFont est utilisé (la fenêtre le signale). Si la bibliothèque FluidSynth ou un SoundFont ne sont pas disponibles, on
  peut quand même enregistrer/jouer, simplement sans entendre les touches
  (la fenêtre le signale).
- **Tempo, Métrique, Métronome et Quantification** : mêmes commandes et
  même signification que dans la fenêtre d'import audio (section 10bis) —
  le métronome (section 12.5) est particulièrement utile ici pour jouer en
  mesure avant la quantification.
- **Tonalité** : affiche la tonalité du projet (section 2.7bis) dès
  l'ouverture de la fenêtre, et on peut la changer directement ici — c'est
  le même champ `project.key` que la barre d'outils principale (pas une
  copie) : la modifier dans la fenêtre se répercute aussi dans la barre
  d'outils une fois la fenêtre fermée, et inversement. La changer met
  immédiatement à jour la disposition « Gamme de la tonalité » (voir plus
  bas), si elle est active.
- **Disposition** : sélecteur de l'agencement des touches de note, désactivé
  si l'instrument est percussif (les percussions utilisent toujours les
  touches `1`-`9`). On peut la changer même pendant un enregistrement ou un
  essai, comme l'Octave. Options disponibles :
  - **Chromatique** (par défaut) : le comportement décrit plus haut, 12
    demi-tons par rangée, 3 octaves au total.
  - **Gamme de la tonalité (diatonique/pentatonique/blues)** : nécessite une
    tonalité définie dans la barre d'outils principale (section 2.7bis) —
    si elle n'est pas définie (ou pas valide), on revient automatiquement à
    la chromatique, sans bloquer la sélection. Chaque rangée de touches ne
    parcourt que les notes de la gamme choisie au lieu des 12 chromatiques,
    de sorte que les touches jouent toujours « dans la tonalité », utile
    pour improviser sans devoir choisir les bonnes notes à l'oreille : la
    **diatonique** utilise les 7 notes de la gamme majeure ou mineure
    naturelle de la tonalité ; la **pentatonique** ses 5 notes majeures ou
    mineures (plus « sûre » pour l'improvisation, il est presque impossible
    de jouer une fausse note) ; le **blues** les 6 notes de la gamme blues
    (pentatonique mineure + quinte diminuée de passage), toujours les mêmes
    à partir de la tonique quel que soit le mode majeur/mineur. Plus la
    gamme est courte, plus le clavier couvre d'octaves avec les mêmes 12
    touches par rangée (la diatonique atteint ~3,6 octaves, le blues ~3,8,
    la pentatonique ~4,2).
  - **Jankó (isomorphe)** : agencement par tons entiers alternés entre les
    rangées (la rangée des chiffres et la rangée A jouent les mêmes notes,
    la rangée Q les notes intermédiaires un demi-ton au-dessus),
    indépendant de la tonalité : une forme d'accord/d'intervalle donnée
    sonne toujours pareil partout sur le clavier, pratique pour qui la
    connaît déjà d'autres instruments/logiciels. Elle couvre 2 octaves
    pleines (moins que la chromatique) : c'est le prix de l'isomorphisme,
    pas un défaut.
- **« Écouter aussi les autres pistes » (respecte Solo/Mute)** : case
  facultative (non cochée par défaut). Si elle est cochée, aussi bien
  pendant qu'on joue en direct (Enregistrer/Jouer) que pendant la
  réécoute de l'aperçu enregistré, on entend aussi les autres pistes du
  projet, avec le même état Solo/Mute qu'elles ont à ce moment dans la
  table de mixage — utile pour jouer ou évaluer la nouvelle partie dans le
  contexte de l'arrangement plutôt qu'isolément. La piste de destination
  elle-même n'est jamais dupliquée : si la fenêtre a été ouverte pour une
  piste existante, son contenu actuel reste exclu de l'écoute d'arrière-plan,
  pour ne pas se superposer à ce qu'on enregistre/réécoute à sa place. Si
  elle n'est pas cochée : comportement habituel, on n'entend que
  l'instrument courant. La case est désactivée pendant l'enregistrement/
  l'essai lui-même (il faut décider avant d'appuyer sur Enregistrer ou
  Jouer).
- **Enregistrer** démarre/arrête la capture de la performance ; **Jouer**
  l'essaie sans rien enregistrer. Arrêter l'enregistrement génère l'aperçu
  texte quantifié, modifiable et réécoutable comme dans l'import audio,
  avant de confirmer par Ok. Dans la piste (contrairement aux patterns, où
  il remplace toujours le corps) le résultat est ajouté à la suite du
  contenu déjà présent au lieu de l'écraser, pour ne pas perdre de la
  musique écrite à la main ou importée auparavant.

### Clavier MIDI

Dans la même fenêtre, on peut jouer avec un vrai **clavier MIDI** (branché
en USB ou via une interface MIDI), avec ou à la place du clavier de
l'ordinateur :

1. branchez le clavier **avant** d'ouvrir la fenêtre (si vous le branchez
   après, appuyez sur **⟳** à côté du menu **Clavier MIDI**) ;
2. dans le menu **Clavier MIDI**, choisissez le clavier : avec un seul
   clavier branché il est déjà choisi, et SoundText se souvient du dernier
   utilisé ;
3. appuyez sur **Enregistrer** (ou **Jouer**, pour essayer) et jouez.
   Comme pour le clavier de l'ordinateur, les notes ne comptent que tant
   qu'Enregistrer ou Jouer sont actifs.

Par rapport au clavier de l'ordinateur :
- **vraie dynamique** : la vélocité de chaque touche (la force avec
  laquelle vous l'enfoncez) devient le `@` de la note ;
- **accords** joués directement, une touche par note (la rangée des accords
  à la volée reste pour le clavier de l'ordinateur) ;
- **pédale de sustain** : tient les notes comme la touche de sustain ; la
  durée enregistrée va jusqu'au relâchement de la pédale ;
- **molette de pitch bend** : s'entend en direct ; si pendant une note elle
  monte ou descend d'au moins un demi-ton, la note est enregistrée comme
  slide (`a*4>b*4`) vers la hauteur atteinte (amplitude standard ±2
  demi-tons) ;
- **percussions** : sur une piste de batterie les notes suivent la table
  General MIDI (36 grosse caisse, 38 caisse claire, 42 charleston fermé, 46
  charleston ouvert...), comme les pads des claviers et des batteries
  électroniques ; les notes hors table sont ignorées ;
- l'**arpégiateur** (barre d'espace maintenue sur le clavier de
  l'ordinateur) arpège aussi les notes du clavier MIDI.

Il faut le paquet Python **python-rtmidi** (dans les prérequis : les
scripts d'installation l'installent déjà ; à la main `pip install
python-rtmidi`). S'il manque, ou si le système MIDI ne répond pas, le menu
est désactivé et la raison est indiquée à côté. Si le clavier n'apparaît
pas dans la liste : vérifiez le câble et qu'il est allumé, appuyez sur
**⟳** ; sous Linux `aconnect -l` liste les périphériques MIDI vus par le
système. Un clavier ouvert par un autre programme (par exemple un
séquenceur) peut apparaître occupé sous Windows : fermez l'autre
programme.

## 10quater. Pistes audio (voix, guitare, clavier enregistrés)

En plus des pistes avec notation, un morceau peut contenir des **pistes
audio** : de vrais fichiers audio (une voix enregistrée au micro, une
guitare électrique ou un clavier branchés par jack sur la carte son) qui
jouent en même temps que les autres pistes. Contrairement à l'import audio
(10bis), le fichier **n'est pas converti en notes** : on l'entend tel quel.

Une piste audio se remplit de deux façons : en **enregistrant** directement
dans SoundText pendant que le reste du morceau joue (voir « Enregistrer »
plus bas), ou en **important** des fichiers enregistrés avec un autre
programme.

- **Créer une piste audio** : **+ Ajouter une piste → Piste audio...**, ou
  menu **Piste → Ajouter → Piste audio...**. Dans son en-tête elle
  apparaît comme « Audio », avec Volume/Pan/Mute/Solo comme les autres
  (volume 100 % = niveau d'origine du fichier, jusqu'à 200 % ≈ +6 dB).
- **Importer un fichier** : menu **Piste → Importer dans cette piste → Fichier audio comme clip...** (ou **⋯ → Importer un fichier audio...** sur la piste
  audio) ajoute le fichier comme **clip** à la fin de la piste. Dans la vue
  Structure du morceau : double-clic sur un endroit vide de la rangée, ou
  clic droit → **Importer un fichier audio ici...** pour le placer à un
  endroit précis. Les `.wav` se lisent toujours (même en 32 bits float) ;
  mp3, m4a, flac, ogg et aiff sont lus par le décodeur de Qt Multimedia
  inclus dans PySide6 (ou par `ffmpeg`, s'il est présent), et rééchantillonnés
  à 48 kHz sans perte dans les aigus.
- **Clips dans la vue Structure du morceau** : chaque clip est un box avec
  la forme d'onde, aussi large que la partie du fichier qui joue. Il se
  fait glisser comme les box de notation (en s'accrochant au temps) ;
  double-clic pour le renommer ; clic droit pour Lecture (aperçu du seul
  clip), Renommer, **Gain du clip (dB)**, Dupliquer, Couper/Copier/Coller
  (un clip audio ne se colle que dans une piste audio) et Supprimer. Tout
  s'annule avec Ctrl+Z.
- **Couper le début et la fin** : placez la souris sur un bord du box (le
  curseur devient ↔) et faites-le glisser. L'audio reste à sa place dans le
  temps : on masque (ou on retrouve) seulement le début ou la fin du
  fichier. La coupe s'accroche à la double croche (1/4 de temps) ; en
  maintenant **Maj** elle est libre. En faisant glisser le bord gauche vers
  la gauche, on retrouve aussi l'audio enregistré pendant le décompte
  (utile pour une note d'attaque jouée en avance). Pour des valeurs
  exactes : clic droit → **Coupe précise (secondes)...**. Le fichier n'est
  jamais modifié.
- **Diviser un clip** : clic droit à l'endroit où le diviser → **Diviser
  ici** : il devient deux clips consécutifs du même fichier, qu'on peut
  déplacer, couper ou supprimer séparément (par exemple pour enlever une
  erreur au milieu d'une prise).
- **Convertir en notation...** (clic droit sur un clip) : transforme en
  notes la partie du clip qui joue, avec le même moteur qu'« Importer de
  l'audio » (10bis), dans une **nouvelle piste** avec
  l'instrument choisi (proposé selon ce que vous avez enregistré : guitare,
  clavier, voix) et un box qui commence là où commence le clip. Cela
  fonctionne bien avec les parties monophoniques (voix, ligne de guitare
  ou de basse) ; le clip audio reste.
- **Dans l'éditeur classique**, une piste audio affiche, en lecture seule,
  la liste de ses clips : les actions sur la notation (Générer, Jouer au
  clavier, Importer un MIDI, Figer les accords, Exporter en MIDI) ne
  s'appliquent pas aux pistes audio et l'expliquent par un message.
- **Tempo** : l'audio n'est pas étiré. Un clip reste ancré au temps où il
  commence mais dure toujours le même nombre de secondes : si vous changez
  le BPM après l'avoir placé, la barre d'état vous le rappelle.

### Enregistrer

Bouton rouge **●** sur l'en-tête de la piste audio, menu **Piste →
Enregistrer dans la piste audio...** (Ctrl+R), ou dans la vue Structure du
morceau clic droit sur la rangée de la piste → **Enregistrer à partir
d'ici...** (part de ce point). La fenêtre d'enregistrement s'ouvre :

- **Carte son** : l'entrée depuis laquelle enregistrer (sous Windows
  apparaissent d'abord les pilotes à faible latence, ASIO et WASAPI). Elle
  est mémorisée.
- **Ce que vous enregistrez** : Voix/micro, Guitare ou basse (jack),
  Clavier (sortie ligne). Choisit l'entrée la plus probable et explique quoi
  régler sur la carte : alimentation fantôme +48 V pour un micro à
  condensateur, entrée INST/Hi-Z pour la guitare (on enregistre le son
  clair, sans ampli), entrées 1+2 sur LINE pour un clavier stéréo.
- **Entrée** : une entrée mono (1, 2, ...) ou une paire stéréo (1+2). Le
  type de source et l'entrée restent enregistrés dans la piste.
- **Niveau** : l'indicateur bouge dès que la fenêtre est ouverte : réglez
  le gain sur la carte son pour que les passages les plus forts arrivent
  vers -12/-6 dB sans allumer le voyant rouge (saturation).
- **Partir de** : position courante, début de la boucle A (si définie) ou
  début du morceau.
- **Décompte** (0-4 mesures de clic avant le départ du morceau) et
  **Métronome pendant la prise**. Le clic continue même après la fin du
  morceau, donc on peut aussi enregistrer dans un morceau encore vide.
- **Écouter les clips déjà présents dans cette piste** : décochez-la pour
  refaire une partie sans entendre la prise précédente.
- **Compensation de latence** : la latence déclarée par la carte est déjà
  compensée ; si la prise est quand même en retard par rapport au morceau,
  augmentez cette valeur (en avance : diminuez-la). Elle est mémorisée pour
  chaque carte. **Calibrer...** la mesure tout seul : reliez avec un câble
  une sortie de la carte à l'entrée choisie (ou approchez le micro des
  enceintes), SoundText joue 8 clics, les enregistre et règle le retard
  mesuré. Il suffit de le faire une fois par carte son (et chaque fois que
  vous changez les réglages de buffer/latence du pilote).

**● Enregistrer** prépare l'accompagnement (le morceau comme en lecture ;
sans SoundFont, seulement les pistes audio et le métronome), fait le
décompte et enregistre jusqu'à ce que vous appuyiez sur **■ Stop**. La
fenêtre affiche la durée et la crête de la prise (et avertit si elle a
saturé) : **Garder la prise** l'ajoute à la piste comme clip au point de
départ ; **Enregistrer** de nouveau la remplace. Si la prise chevauche des
clips déjà présents, SoundText demande s'il faut les supprimer.

Pour vous entendre pendant que vous jouez, utilisez le **monitoring
direct** de la carte son (bouton ou touche « direct monitor ») : il est
sans retard. SoundText n'envoie au casque que le morceau. Le fichier de la
prise contient aussi le décompte, masqué par la coupe initiale du clip (en
faisant glisser le bord gauche on peut le retrouver).

### Où vont les fichiers

Les prises et les fichiers importés (dont SoundText fait une copie à
48 kHz, la même fréquence que la lecture : l'original n'est jamais touché)
vont dans le dossier **`<NomDuProjet>_audio/`**, à côté du fichier `.st`.
Si le projet n'a pas encore été enregistré, ils vont dans un dossier
temporaire et sont déplacés dans le dossier du projet au premier
enregistrement. **Enregistrer sous** copie les fichiers audio dans le
dossier du nouveau projet. Pour déplacer un projet sur un autre ordinateur,
copiez ensemble le fichier `.st` et son dossier `_audio`.

Dans le fichier `.st`, un clip s'écrit ainsi (chemin relatif au fichier) :

```
Audio Voix "Couplet" |8:
  file="Chanson_audio/voix.wav" trim=0.35,0 gain=-2

Traccia Voix [Audio]:
```

`|8` est le temps de départ ; `trim` sont les secondes sautées au début et
à la fin du fichier, `gain` le gain du clip en dB (tous deux facultatifs).
Si un fichier est introuvable, le clip reste dans le projet, dessiné en
rouge, et ne joue pas : clic droit → **Retrouver le fichier...** pour
l'indiquer de nouveau.

### Exporter

- **Projet → Exporter → Mix audio (WAV)...** exporte le morceau tel qu'on
  l'entend (pistes audibles, audio compris) en WAV 48 kHz / 24 bits. Il
  faut un SoundFont pour les pistes avec des notes ; un morceau composé
  uniquement de pistes audio s'exporte même sans.
- **Piste → Exporter cette piste → WAV...**, ou **clic droit sur le nom d'une
  piste → Exporter en WAV (celle-ci seulement)...**, exporte en WAV seulement cette piste, avec notation ou
  audio, telle qu'on l'entendrait en Solo (le Solo/Mute des autres pistes ne
  compte pas). Pour les pistes avec notation, le même menu a aussi
  **Exporter en MIDI (celle-ci seulement)...**.
- **Piste → Exporter cette piste → WAV sec (pour le re-amping)...**, ou la
  même commande par clic droit sur le nom de la piste, exporte la piste **sans** chaîne d'effets, sans
  réverbération/chorus du synthé, avec le pan au centre et sans master (le
  volume reste) : c'est le son « propre » à faire passer dans un simulateur
  d'ampli externe (voir 8.6). Le fichier part du début du morceau, de sorte
  qu'en le réimportant au début d'une piste audio il reste en mesure.
- **Exporter en MIDI** ne contient que des notes : les pistes audio n'y sont
  pas, et un message le rappelle.
- L'enregistrement et les exports proposent comme nom de fichier celui du
  projet (les exports d'une seule piste celui de la piste), dans le dossier
  où le projet est enregistré.

## 11. Enregistrement du projet

Le projet s'enregistre au format texte natif `.st` (lisible et modifiable
aussi à la main), qui comprend le tempo, la métrique, les patterns, les
pistes et les définitions des éventuels instruments personnalisés utilisés
(voir 7.1), afin que le fichier soit autonome et portable d'une
installation à l'autre. La bibliothèque MIDI (`midi/`) reste en revanche
partagée au niveau de l'installation et ne voyage pas dans le fichier
`.st`.

Le titre de la fenêtre affiche toujours le nom du fichier ouvert
(« SoundText — nomfichier.st »), même après un import MIDI
(« SoundText — nomfichier.mid »), pour savoir toujours d'un coup d'œil sur
quel projet on travaille.

## 12. Lecture

Le bouton Play exporte un MIDI temporaire. Si `fluidsynth` et un SoundFont
sont disponibles, la synthèse se fait **hors ligne** (rendu dans un fichier
WAV temporaire, puis lu avec le meilleur lecteur audio trouvé — sous Linux
`pw-play`, `paplay`, `aplay`, `ffplay` ou `mpv` ; sous macOS `afplay`
(inclus dans le système) ou, s'ils sont installés, `ffplay`/`mpv` ; sous
Windows `ffplay`/`mpv` s'ils sont installés, sinon le module `winsound` de
la bibliothèque standard de Python, toujours disponible) plutôt qu'en temps
réel : cela évite les craquements/décrochages dus aux underruns du pilote
audio, typiques de la synthèse MIDI en temps réel sous PulseAudio/PipeWire,
et donne un résultat plus propre. Si la bibliothèque FluidSynth est
disponible (SoundText l'utilise directement), ce rendu hors ligne utilise une seule
instance de fluidsynth **persistante** pour toute la session, avec le
SoundFont chargé en mémoire une seule fois au lieu de le faire à chaque
Play : latence de démarrage bien plus basse (le coût de chargement du
SoundFont, parfois des centaines de ms pour un GM de plusieurs dizaines de
Mo, ne se paie que la première fois), avec la même stratégie
anti-craquements (le rendu reste hors ligne, il ne touche pas la sortie
audio en temps réel). Si le rendu hors ligne échoue (avec ou sans
la bibliothèque), ou s'il n'y a pas de lecteur WAV disponible, on se rabat
sur le binaire CLI `fluidsynth` puis sur la lecture fluidsynth en temps
réel ; si fluidsynth n'est pas disponible du tout, sur `timidity` ou
`wildmidi` ; à défaut de tout, sur le lecteur MIDI par défaut du système
(`xdg-open` sous Linux, `open` sous macOS, ouverture directe avec le
programme associé sous Windows).

Avec la bibliothèque FluidSynth **et** `sounddevice` (dans
requirements.txt) installés, le morceau rendu est joué directement par le programme
au lieu d'un lecteur externe, et le rendu est **mis en mémoire** : seul le
premier Play (ou le premier après une modification qui change le son, comme
les notes, la table de mixage ou l'humanisation) doit attendre la synthèse,
tandis que pause/reprise et sauts repartent instantanément. La position
affichée par la barre, le surlignage, la tête de lecture et le métronome
est celle lue par le périphérique audio, elle reste donc alignée sur ce
qu'on entend.

### Sauter à un point et répéter une section (boucle A-B)

- **Saut** : cliquez sur la barre de progression dans la barre d'outils, ou
  sur la règle des mesures dans la vue Structure du morceau. Si le morceau
  joue, il repart de là ; s'il est arrêté ou en pause, le prochain Play
  partira de ce point.
- **Boucle A-B** (menu **Lecture → Boucle**) : **Boucle : début (A) ici** (`Ctrl+[`)
  et **Boucle : fin (B) ici** (`Ctrl+]`) fixent les deux extrémités sur le
  temps en cours de lecture (ou sur le point de pause/saut), arrondi au
  temps entier. Définir B active la boucle ; **Répéter la section A-B**
  (`Ctrl+L`) l'active et la désactive sans perdre A et B, **Effacer la
  boucle** les remet à zéro. La section apparaît comme une bande colorée
  sur la règle de la Structure du morceau. On peut activer, déplacer ou
  retirer la boucle même pendant que le morceau joue, sans interruption.
- La boucle nécessite la lecture directe décrite plus haut (bibliothèque
  FluidSynth + `sounddevice`) : avec les lecteurs de repli le morceau n'est pas
  répété, et un message dans la barre d'état le signale.

### 12.1 Barre de progression et surlignage du token en cours

Pendant la lecture, la barre de progression (la ligne sur toute la largeur
sous la barre de commandes) affiche le temps écoulé et la durée totale du
morceau (p. ex. « 00:42 / 01:30 »). Dans la piste affichée dans l'éditeur,
le token en cours de lecture (note, silence, accord, bloc, ou toute la
référence s'il s'agit d'un `%pattern`/`&"midi"`) est surligné avec les
couleurs inversées par rapport au thème (fond clair, texte foncé), pour
suivre visuellement l'exécution ligne par ligne. L'éditeur défile
automatiquement quand il le faut pour garder toujours visible le token
surligné (aucun défilement manuel nécessaire pendant l'écoute), mais
seulement quand il sort de la partie visible : il ne défile pas en continu
note par note, et il ne déplace pas le curseur d'édition de l'utilisateur.
En changeant de piste pendant la lecture, le surlignage passe sur la
nouvelle piste sélectionnée, toujours synchronisé sur le même temps écoulé.

### 12.2 Modifications de la table de mixage pendant la lecture

Mute, Solo, Volume et Pan peuvent être modifiés même pendant que le morceau
joue : le programme relance automatiquement la lecture à partir de la
position où elle se trouvait (pas depuis le début), en appliquant tout de
suite les nouveaux réglages. Une brève interruption est perceptible au
moment de la relance (le morceau doit être resynthétisé avec les nouveaux
réglages), mais il n'est pas nécessaire d'arrêter et de relancer la lecture
à la main pour entendre l'effet d'une modification de la table de mixage.

**Si le son ne vous satisfait pas malgré un bon SoundFont**, gardez à
l'esprit que :
- **Sons → SoundFont → Afficher le SoundFont utilisé** indique exactement quel
  moteur et quel fichier `.sf2` seront utilisés : s'il n'affiche pas
  « fluidsynth persistant (bibliothèque) + ...sf2 » ou « fluidsynth (CLI)
  + ...sf2 », le programme se rabat en silence sur une solution de qualité
  inférieure (souvent parce que `fluidsynth` n'est pas installé, ou
  qu'aucun `.sf2` n'a été trouvé) — installez `fluidsynth` et vérifiez le
  SoundFont depuis là.
- Même avec un bon SoundFont, **le son General MIDI a une limite
  intrinsèque de réalisme** : il n'est pas conçu pour rivaliser avec des
  banques d'échantillons professionnelles, mais pour une lecture fidèle et
  reconnaissable de la partition. Un saut de qualité significatif
  nécessiterait des échantillons multi-vélocité par instrument (hors du
  champ de ce moteur fondé sur le MIDI/GM standard).

### 12.3 Choisir le SoundFont (p. ex. FluidR3_GM.sf2)

Le programme cherche un SoundFont, par ordre de priorité :

1. le chemin défini à la main depuis **Sons → SoundFont → Choisir le SoundFont
   (.sf2)...** (enregistré dans le fichier de réglages :
   `~/.config/soundtext/settings.json` sous Linux,
   `%APPDATA%\SoundText\settings.json` sous Windows,
   `~/Library/Application Support/SoundText/settings.json` sous macOS) ;
2. la variable d'environnement `SOUNDTEXT_SOUNDFONT`, si elle est définie ;
3. quelques chemins système courants, dont :
   - `~/.local/share/soundfonts/FluidR3_GM.sf2` (Linux)
   - `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora)
   - `/usr/share/soundfonts/FluidR3_GM.sf2` (Arch/CachyOS)
   - `%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` (Windows)
   - `~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (macOS)
   - `/opt/homebrew/share/soundfonts/FluidR3_GM.sf2` (macOS, Homebrew sur
     Apple Silicon)

   La liste complète des chemins cherchés pour chaque système se trouve
   dans la section Installation correspondante, plus bas dans ce guide.

Si vous avez téléchargé `FluidR3_GM.sf2` à un autre endroit (ou voulez en
utiliser un autre), il suffit de le sélectionner depuis **Sons → SoundFont → Choisir le SoundFont (.sf2)...** : il reste défini pour toutes les lectures
suivantes, dans tous les projets. **Sons → SoundFont → Afficher le SoundFont
utilisé** indique quel fichier sera utilisé en ce moment (et avec quel
moteur/lecteur), et permet de vérifier sur-le-champ si le problème vient
vraiment du SoundFont ou d'un repli silencieux. **Sons → SoundFont → Utiliser la
détection automatique du SoundFont** supprime le réglage manuel et revient
à la recherche automatique.

### 12.4 SoundFonts différents par instrument

En plus du SoundFont par défaut (section 12.3, utilisé pour toute la
lecture), vous pouvez attribuer un fichier `.sf2` différent à un seul
instrument — utile pour utiliser un piano dédié de bonne qualité avec une
banque générique pour le reste, ou une batterie différente de tout le reste
de l'ensemble.

Depuis **Sons → Gérer les instruments...**, sélectionnez un
instrument dans la liste (prédéfini ou personnalisé : ici le choix n'est
pas limité aux personnalisés) et utilisez le panneau **SoundFont pour
l'instrument sélectionné** :
- **Choisir le SoundFont...** attribue un fichier `.sf2` à cet instrument :
  il sera utilisé à la place de celui par défaut sur chaque piste qui
  l'utilise, dans n'importe quel projet.
- **Utiliser la valeur par défaut** supprime l'attribution et revient au
  SoundFont général.

La liste des instruments affiche une indication (`· SoundFont: nom.sf2`)
pour ceux qui ont une substitution active.

**Limite** : effectif seulement avec le moteur fluidsynth persistant
(la bibliothèque FluidSynth, utilisée par défaut si elle est disponible — voir la section
12 plus haut) : avec les solutions de repli (CLI `fluidsynth`, `timidity`,
`wildmidi`, lecteur MIDI du système) la substitution est ignorée et le
SoundFont par défaut est utilisé pour toute la lecture. Avec plusieurs
instruments substitués en même temps, la lecture nécessite un rendu séparé
pour chaque SoundFont concerné (puis recombinés) : les morceaux avec
beaucoup d'instruments attribués différemment mettent donc quelques
instants de plus à démarrer.

### 12.5 Métronome

Le bouton **Métronome** (icône en pyramide) dans la barre de commandes fait
entendre un clic en mesure pendant la lecture de l'ensemble, synchronisé
avec les éventuels changements de tempo/métrique du projet (la même table
que celle utilisée par la barre de progression et les champs
Tempo/Métrique, voir 2.7) ; la même commande, avec un clic à
tempo/métrique constants, est aussi disponible dans la fenêtre d'import
audio et dans la fenêtre « Jouer au clavier » (sections 10bis et 10ter),
utile pour enregistrer/jouer en mesure.

Le son et le volume du clic se choisissent dans **Options → Métronome** :
trois préréglages de son (Clic, Bip, Bois) et un curseur de volume
(0-100 %), appliqués immédiatement (même à un clic déjà en cours) et
testables sur place avec le bouton « Essai », sans besoin d'un Ok/Annuler
séparé. Les fichiers audio du clic sont synthétisés et mis en cache à la
première exécution (aucune dépendance supplémentaire), de sorte qu'ils ne
sont générés qu'une fois par machine.

### 12.6 Humaniser

L'entrée **Lecture → Humaniser** (à cocher) ajoute une petite variation
aléatoire au timing et à la vélocité des notes jouées, pour un son moins
mécanique qu'une grille parfaitement quantifiée. La batterie ne reçoit que
la variation de vélocité (un décalage de timing sur un pattern de
percussion a tendance à sonner « imprécis » plutôt qu'« humain ») ; tous les
autres instruments reçoivent les deux. **Activable/désactivable même
pendant la lecture** : comme un changement de Volume/Pan, la lecture
redémarre automatiquement à partir de la position courante avec le nouveau
réglage appliqué.

L'intensité se règle dans **Options → Humaniser** avec un curseur
(0-100 %, 50 % par défaut), appliqué immédiatement (il relance la lecture en
cours, si Humaniser est actif). La variation **n'utilise pas de graine
fixe** : deux lectures consécutives avec les mêmes réglages ne sonneront
jamais de façon identique, exactement comme deux exécutions en direct du
même musicien. Cela ne concerne que la lecture/l'export MIDI (le rendu
final en ticks absolus) : le texte de la piste et la timeline « de grille »
dans l'éditeur restent tels qu'ils ont été écrits, inchangés.

## 13. À propos de SoundText

Le menu **Aide → À propos de SoundText...** affiche le nom et le numéro de
version du programme, l'auteur (Sergio Scolaro) et la licence (GPL-3.0),
ainsi que qui décode les fichiers mp3/m4a/flac/ogg (le décodeur de Qt
Multimedia ou `ffmpeg`, section 10bis) avec une icône de coche verte
s'il est disponible, une croix grise sinon : utile pour vérifier
rapidement l'installation sans avoir à ouvrir un terminal.

### 13.1 Fichier journal

Quand quelque chose ne se passe pas comme prévu (la lecture se rabat sur
un moteur de qualité inférieure, un SoundFont ne se charge pas, une erreur
imprévue), SoundText le note avec les détails techniques dans le fichier
`soundtext.log` du dossier de configuration (`~/.config/soundtext` sous
Linux, `%APPDATA%\SoundText` sous Windows,
`~/Library/Application Support/SoundText` sous macOS). **Aide → Ouvrir le
fichier journal** l'ouvre directement : c'est la première chose à joindre si
vous signalez un problème. Une erreur imprévue est aussi affichée dans une
fenêtre, sans fermer l'application.

## 14. Technologies, remerciements et licences

### 14.1 Les technologies utilisées

SoundText est écrit en **Python 3** et s'appuie sur ces bibliothèques et
ces programmes :

| Composant | À quoi il sert dans SoundText | Licence |
|---|---|---|
| Python | le langage du programme | PSF License |
| Qt 6 avec PySide6 | l'interface graphique | LGPL-3.0 |
| NumPy | le calcul sur l'audio : effets, ampli, profils NAM, analyse | BSD-3-Clause |
| FluidSynth | la synthèse des notes avec les SoundFonts (SoundText l'utilise directement) | LGPL-2.1 |
| mido | lecture et écriture des fichiers MIDI | MIT |
| python-rtmidi (RtMidi) | les claviers MIDI externes | MIT |
| sounddevice et PortAudio | l'écoute et l'enregistrement | MIT |
| pedalboard (Spotify) | la chaîne d'effets et les plugins VST3 | GPL-3.0 |
| JUCE (dans pedalboard) | le moteur audio de pedalboard et l'hôte VST3 | GPL-3.0 (sous la forme utilisée par pedalboard) |
| SDK VST3 de Steinberg (dans pedalboard) | le format des plugins VST3 | GPL-3.0 dans la version incluse dans pedalboard (les versions plus récentes du SDK sont passées à la licence MIT) |
| lilv et LV2 | les plugins LV2 sous Linux (bibliothèque système, facultative) | ISC |
| FFmpeg (dans Qt Multimedia) | la lecture des mp3, m4a, flac, ogg | LGPL-2.1 |
| ffmpeg (programme externe, facultatif) | la lecture des fichiers audio si le PySide6 utilisé n'a pas le décodeur de Qt | LGPL-2.1 ou GPL, selon la façon dont il a été compilé |
| Neural Amp Modeler | le format des profils `.nam` : SoundText en refait le calcul avec NumPy | MIT (le projet NAM) |
| SoundFont FluidR3_GM | les sons General MIDI inclus dans les builds | MIT |

Certains formats et idées viennent de standards ouverts ou de la
littérature : le **General MIDI** et le fichier MIDI standard, le
**MusicXML** (W3C Music Notation Community Group) pour l'export de la
partition (10.1), l'algorithme de **Krumhansl-Schmuckler** pour reconnaître
la tonalité, les circuits des tone stacks Fender et Marshall pour l'ampli
(8.4).

Pour construire et vérifier le programme, il faut aussi **PyInstaller** (les
versions portables ; sa licence GPL-2.0 a une exception qui fait qu'elle ne
s'étend pas au programme empaqueté), **pytest** (les tests) et
**reportlab** (le guide PDF).

### 14.2 Remerciements

SoundText existe grâce au travail, presque toujours bénévole, de ceux qui
ont créé et maintiennent les projets open source sur lesquels il s'appuie.
Nous avons une dette particulière envers :

- la communauté de **FluidSynth**, qui depuis plus de vingt ans fait jouer
  les SoundFonts sur tous les systèmes, et **Frank Wen**, auteur du
  SoundFont **FluidR3_GM** ;
- **The Qt Company** et la communauté de **Qt for Python (PySide6)** ;
- **Spotify** et les développeurs de **pedalboard**, et l'équipe de
  **JUCE** sur lequel pedalboard est construit ;
- le **RISM Digital Center** et les développeurs de **Verovio**, qui met en
  page la partition (Affichage → Partition) ;
- **Alain de Cheveigné** et **Hideki Kawahara** (algorithme YIN) et
  **Sebastian Böck** et **Gerhard Widmer** (SuperFlux), dont les articles
  sont à la base de la reconnaissance des notes à partir de l'audio ;
- les auteurs de **mido**, de **RtMidi** (Gary P. Scavone) et de
  **python-rtmidi**, de **PortAudio** et de **sounddevice** ;
- la communauté de **NumPy** ;
- **Steven Atkinson** et la communauté de **Neural Amp Modeler**, avec ceux
  qui capturent et partagent les profils d'amplis (entre autres la
  collection de **pelennor2170** et le site **Tone3000**) ;
- **David Robillard** et la communauté de **LV2** et **lilv**, et les
  auteurs des plugins d'**Ardour** et de **Guitarix** ;
- **David Fau Casquel** (BestPlugins), qui a publié ses baffles IR sous
  licence libre, et la communauté de **Guitarix**, qui les conserve ;
- **Steinberg**, qui a ouvert le format **VST3** ;
- ceux qui développent des plugins gratuits et open source, comme
  **Surge XT**, et le **W3C Music Notation Community Group** pour MusicXML.

Si vous utilisez SoundText et qu'il vous est utile, la meilleure façon de
rendre la pareille est de soutenir ces projets : signaler les problèmes,
contribuer, ou faire un don à ceux qui en acceptent.

### 14.3 Licences et limites à la distribution

Utiliser SoundText sur son propre ordinateur, dans n'importe quel but (même
commercial, même pour vendre la musique qu'on y fait), **n'a aucune
limite** : les licences ci-dessous ne concernent que ceux qui **distribuent
le programme** à d'autres (copient l'installation, publient un build, le
vendent ou l'incluent dans un autre produit). La musique créée avec
SoundText appartient à qui la crée : aucune de ces licences ne s'applique
aux morceaux, ni aux fichiers `.st`, MIDI, MusicXML ou WAV produits.

**La contrainte principale : la GPL-3.0.** **pedalboard** (avec JUCE) est
distribué sous la licence **GNU GPL version 3**. Un programme qui
l'inclut, comme les builds de SoundText, ne peut être
distribué qu'aux conditions de la GPL-3.0 :
- tout SoundText doit être distribué sous la **licence GPL-3.0** (ou une
  licence compatible), et celui qui le reçoit a les mêmes droits de
  l'utiliser, l'étudier, le modifier et le redistribuer ;
- le **code source complet** de la version distribuée, modifications
  comprises, doit être mis à disposition avec le programme (ou sur demande,
  selon les règles de la licence) ;
- on ne peut ajouter aucune **restriction** : pas de versions à code fermé,
  pas d'interdictions de copie ou de modification, pas de systèmes qui
  empêchent d'installer une version modifiée ;
- on peut **vendre** une copie ou demander une rémunération pour la
  distribution, mais celui qui l'achète peut ensuite la redistribuer
  librement.

Une version **à code fermé** de SoundText ne serait possible qu'en retirant
pedalboard (et donc la chaîne d'effets et les plugins VST3), ou en le
remplaçant, ou en achetant les licences commerciales des composants qui
en proposent (JUCE, Steinberg...).

**Les bibliothèques LGPL : Qt/PySide6 et FluidSynth.** Elles peuvent aussi
être utilisées dans des programmes non GPL, à condition que celui qui reçoit
le programme puisse **les remplacer par sa propre version**. Les builds
portables de SoundText les gardent comme fichiers séparés à côté de
l'exécutable, la condition est donc respectée. Il faut inclure le texte de
la licence LGPL et les indications sur où obtenir les sources de ces
bibliothèques (par exemple un lien vers la version utilisée).

**Les licences permissives (MIT, BSD, ISC, PSF).** NumPy, mido, RtMidi,
PortAudio, sounddevice, lilv, le projet NAM et le SoundFont FluidR3_GM
demandent seulement de **conserver les mentions de copyright et le texte de
la licence** dans la distribution.

**Marques.** VST est une marque déposée de Steinberg Media Technologies
GmbH, Qt de The Qt Company : on peut citer ces noms pour dire que le
programme prend en charge ces formats ou utilise ces bibliothèques, pas
pour faire croire que SoundText est l'un de leurs produits. L'utilisation
du logo VST obéit à des règles propres à Steinberg.

**Contenus téléchargés et plugins de tiers.**
- Les **profils NAM recommandés** (Sons → Télécharger → Télécharger les profils NAM
  recommandés) viennent de la collection de pelennor2170, sous licence
  GPL-3.0 : SoundText les télécharge sur l'ordinateur de l'utilisateur, il
  ne les inclut pas dans les builds. Celui qui les redistribue doit en
  respecter la licence.
- Les **baffles IR recommandés** (Sons → Télécharger → Télécharger des baffles IR
  pour les amplis NAM) sont le BestPlugins Mega Pack 2 de David Fau
  Casquel, sous licence GPL v2 ou ultérieure : SoundText les télécharge
  eux aussi sur l'ordinateur de l'utilisateur, avec le texte de la
  licence, et ne les inclut pas dans les builds.
- Les **plugins VST3 et LV2** (8.7) sont des programmes de tiers, chacun
  avec sa propre licence, parfois payante : SoundText les charge, mais ne
  les inclut pas. Pour les distribuer avec SoundText, il faut l'autorisation
  de leurs auteurs.
- Les **SoundFonts** choisis par l'utilisateur ont chacun leur propre
  licence : avant d'en inclure un autre que FluidR3_GM dans une
  distribution, il faut la vérifier.

**La licence de SoundText.** SoundText (Copyright © 2026 Sergio Scolaro)
est distribué sous la licence **GPL-3.0** : le texte se trouve dans le
fichier `LICENSE`. Les auteurs, licences et textes intégraux des composants
tiers sont dans `THIRD_PARTY_NOTICES.md` et dans le dossier `licenses/`. Les
scripts de build (versions portables pour Linux et Windows, AppImage,
installeur Windows) les copient à côté du programme, et l'installeur
Windows affiche la licence pendant l'installation.

**En pratique, pour qui distribue un build de SoundText :**
1. laisser à côté du programme `LICENSE`, `THIRD_PARTY_NOTICES.md` et le
   dossier `licenses/` (les scripts de build le font d'eux-mêmes) ;
2. mettre à disposition le **code source** de la version distribuée (par
   exemple le dépôt, avec la référence exacte de la version) ;
3. si l'on ajoute au build un nouveau composant, ajouter ses auteurs et sa
   licence dans `THIRD_PARTY_NOTICES.md` et son texte dans `licenses/` ;
4. ne pas inclure de plugins, SoundFonts ou profils de tiers sans avoir
   vérifié que leur licence le permet.

Ces indications résument les licences des composants pour aider à s'y
retrouver : **elles ne constituent pas un conseil juridique**. Pour une
distribution commerciale ou dans un contexte particulier, il est
préférable de consulter un spécialiste des licences logicielles. Les textes
complets des licences se trouvent sur les sites des projets respectifs.

---

# Installation sous Linux

## Debian / Ubuntu et dérivées

```bash
sudo apt update
sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtmultimedia python3-pip fluidsynth fluid-soundfont-gm ffmpeg libportaudio2
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
Si `python3-pyside6.qtwidgets` n'est pas disponible dans votre version de
la distribution, autre possibilité :
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo apt install fluidsynth fluid-soundfont-gm libportaudio2
python3 main.py
```
`libportaudio2` sert à l'écoute directe et au micro ; `ffmpeg` seulement à
lire les mp3/m4a/flac/ogg si le PySide6 de la distribution n'a pas le
décodeur de Qt Multimedia (avec PySide6 installé via pip, comme dans la
deuxième méthode, il ne sert pas). **Aide → À propos de SoundText...**
indique qui décode les fichiers audio.

## Fedora et dérivées (RHEL, Nobara, etc.)

```bash
sudo dnf install python3-pyside6 python3-pip fluidsynth fluid-soundfont-gm portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
Si `python3-pyside6` n'est pas dans les dépôts activés :
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo dnf install fluidsynth fluid-soundfont-gm portaudio
python3 main.py
```
`ffmpeg` ne sert que si le PySide6 du système ne lit pas les mp3 (voir
plus haut) et n'est pas dans les dépôts officiels de Fedora : activez
[RPM Fusion](https://rpmfusion.org/) puis `sudo dnf install ffmpeg`, ou
utilisez la deuxième méthode (PySide6 via pip).

## Arch Linux / CachyOS / Manjaro et dérivées

```bash
sudo pacman -S pyside6 python-mido fluidsynth ffmpeg portaudio
paru -S soundfont-fluid      # ou yay -S soundfont-fluid (AUR)
pip install --user sounddevice numpy pedalboard
cd soundtext
python3 main.py
```
(Le paquet officiel s'appelle `pyside6`, sans le préfixe `python-`.
`python-mido` se trouve en revanche dans les dépôts officiels `extra`.
`portaudio` sert à l'écoute directe et au micro, `ffmpeg` seulement si le
PySide6 du système ne lit pas les mp3.)

## openSUSE

```bash
sudo zypper install python3-PySide6 python3-pip fluidsynth ffmpeg portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```

## Remarques communes

- Sans SoundFont GM installé, `fluidsynth` ne produit aucun son : vérifiez
  qu'il existe un fichier comme `/usr/share/soundfonts/FluidR3_GM.sf2`
  (Arch) ou `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora).
- En l'absence de tout synthé système, le programme exporte quand même un
  MIDI standard lisible avec n'importe quel autre lecteur.
- Les instruments personnalisés sont enregistrés dans
  `~/.config/soundtext/instruments.json` et sont donc partagés entre tous
  les projets de l'utilisateur sur cette machine.

---

# Installation sous Windows

```powershell
# 1) Python 3.10+ depuis python.org (installeur officiel, cochez "Add python.exe to PATH")
cd soundtext
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Synthèse audio (fluidsynth)** : téléchargez les binaires Windows de
fluidsynth depuis la page officielle des versions du projet
([github.com/FluidSynth/fluidsynth/releases](https://github.com/FluidSynth/fluidsynth/releases),
archive `-win10-x64.zip`) et placez le dossier `bin\` (il contient
`libfluidsynth-3.dll`) dans le `PATH` du système, ou copiez son contenu dans
le dossier de SoundText : SoundText utilise directement la bibliothèque
(moteur persistant, par défaut) et `fluidsynth.exe` comme solution de
repli. Sinon, si vous avez
[Chocolatey](https://chocolatey.org/) :
```powershell
choco install fluidsynth
```

**SoundFont GM** : aucun n'est inclus dans le système d'exploitation
(contrairement à beaucoup de distributions Linux). Téléchargez un SoundFont
GM (p. ex. `FluidR3_GM.sf2`, librement disponible) et définissez-le depuis
**Sons → SoundFont → Choisir le SoundFont (.sf2)...** dans le menu de l'application,
ou placez-le dans `%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` pour la
détection automatique.

**Import audio** : rien à installer. Les fichiers mp3/m4a/flac/ogg sont lus
par le décodeur de Qt Multimedia, déjà inclus dans PySide6 ; le paquet pip
`sounddevice` (dans requirements.txt) enregistre au micro et inclut déjà la
bibliothèque PortAudio pour Windows. La reconnaissance des notes est elle
aussi écrite dans SoundText.

**Lecture sans lecteurs externes** : contrairement à Linux, Windows n'a pas
de lecteur audio en ligne de commande par défaut ; SoundText détecte ce cas
et utilise automatiquement le module `winsound` de la bibliothèque standard
de Python (aucune dépendance supplémentaire) pour jouer le rendu hors
ligne. **Sons → SoundFont → Afficher le SoundFont utilisé** montre toujours quel
moteur/lecteur est réellement actif, utile pour vérifier l'installation. Le
bouton **Stop** arrête correctement la lecture avec n'importe quel moteur,
y compris le dernier recours (le lecteur MIDI par défaut du système,
utilisé quand ni fluidsynth ni un lecteur CLI ne sont installés) :
SoundText l'ouvre de façon à pouvoir toujours l'arrêter, au lieu de le
laisser comme processus détaché de l'application.

```powershell
python main.py
```

---

# Installation sous macOS

```bash
brew install python@3.12 fluidsynth portaudio   # portaudio facultatif, voir plus bas
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

**Synthèse audio (fluidsynth)** : installée par Homebrew avec le reste
(`libfluidsynth` se retrouve dans `/opt/homebrew/lib` sur Apple Silicon ou
`/usr/local/lib` sur Intel, déjà dans le chemin de recherche des
bibliothèques du système : SoundText la trouve tout seul, même sur Apple
Silicon, sans configuration supplémentaire).

**SoundFont GM** : comme sous Windows, macOS n'en inclut pas par défaut.
Téléchargez un SoundFont GM (p. ex. `FluidR3_GM.sf2`) et définissez-le
depuis **Sons → SoundFont → Choisir le SoundFont (.sf2)...**, ou placez-le dans
`~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (ou, s'il est installé via
Homebrew, dans `/opt/homebrew/share/soundfonts/`) pour la détection
automatique.

**Import audio** : les fichiers mp3/m4a/flac/ogg sont lus par le décodeur
de Qt Multimedia, déjà inclus dans PySide6 (pas de `ffmpeg` à installer) ;
le paquet pip `sounddevice` enregistre au micro (il inclut déjà PortAudio,
mais `brew install portaudio` ne fait jamais de mal si le paquet pip posait
problème à la compilation). La reconnaissance des notes est elle aussi
écrite dans SoundText, rien à compiler.

**Lecture** : macOS inclut par défaut `afplay` (lecteur audio en ligne de
commande inclus dans le système d'exploitation, aucune installation
nécessaire), utilisé automatiquement pour jouer le rendu hors ligne — la
même stratégie que celle déjà utilisée sous Linux avec `paplay`/`pw-play`.
**Sons → SoundFont → Afficher le SoundFont utilisé** montre toujours quel
moteur/lecteur est réellement actif.

**Autorisations du micro** : au premier enregistrement au micro, macOS
demande l'autorisation d'accéder au micro pour le terminal/l'IDE depuis
lequel vous avez lancé `python3 main.py` : il faut l'accorder depuis
**Réglages Système → Confidentialité et sécurité → Microphone**, sinon
l'enregistrement échoue en silence.
