# SoundText — Notation textuelle simplifiée

[Italiano](README.md) · [English](README.en.md) · **Français** · [Español](README.es.md)

Une implémentation fonctionnelle du MVP décrit dans les *Spécifications du
projet — Lecteur musical v1.2* (le nom d'origine du projet, aujourd'hui
**SoundText**) : un moteur musical qui sépare l'intention abstraite
(accords/notes symboliques), le voicing concret (qui dépend de
l'instrument) et la lecture (MIDI), avec une interface de bureau pour Linux,
Windows et macOS — thème sombre cohérent, coloration syntaxique en direct,
raccourcis clavier et table de mixage avec un code couleur par famille
d'instruments.

## Terminologie

- **SoundText Language** : le langage textuel dans lequel on écrit la
  partition (notes, accords, percussions, patterns...).
- **ST-Syntax** : la grammaire formelle du SoundText Language (tokens,
  règles de syntaxe, voir la section 2 du guide de l'utilisateur).
- **SoundText Engine** : le moteur interne qui transforme un accord abstrait
  en notes MIDI concrètes selon l'instrument (le « moteur de voicing »).
- **.st** : extension des fichiers de projet.

## Guide complet

Le menu **Aide → Guide de l'utilisateur** de l'application affiche la
documentation complète (disponible aussi ici : `docs/HELP.fr.md`, la version
originale en italien est `docs/HELP.md`), avec les instructions
d'installation pour Debian/Ubuntu, Arch/CachyOS, Fedora et openSUSE.

## Ce qui est implémenté

- **Grammaire complète** (ST-Syntax) : notes en minuscules a-g, accords
  abstraits en MAJUSCULES (`Cmaj7`, `Am`, `G7`...), événements de
  percussion textuels, silences `r`, blocs simultanés `[...]`,
  multiplicateurs de durée, octaves `*n`, changement de grille rythmique
  `N:` / `NT:` (triolets), changement de vélocité `N@`. Les durées
  s'accumulent le long de la timeline ; le `|` facultatif est un contrôle de
  mesure (muet : il avertit s'il ne tombe pas sur une barre de mesure, selon
  la métrique du projet, et indique la mesure trop courte ou trop longue), et
  `//` ouvre un commentaire jusqu'à la fin de la ligne (section 2.10 du
  guide). Les durées peuvent aussi s'écrire comme valeurs de note (`c'8.`
  croche pointée), plusieurs voix dans la même piste avec
  `{ voix1 ; voix2 }` et les paroles entre guillemets (`"Ma- ri- a"`),
  sections 2.11-2.13.
- **Automations** : volume, expression, panoramique, modulation et départs
  d'effets qui évoluent dans le temps, même pendant une note tenue
  (`vol=0 >>exp 4c vol=100`, `pan=-1 >> c d pan=1`), avec des rampes à
  courbe (`>>exp`, `>>log`, `>>s`) et des soufflets sur les notes (`2c<`,
  `c'2>`) : on les entend, et elles vont dans le MIDI et la partition
  (section 2.15). Aussi n'importe quel contrôleur MIDI (`cc74=`) et le
  pitch bend (`bend=`).
- **Liaisons et swing** : liaisons de prolongation même au-delà de la barre
  de mesure (`2f~ | 2f`), liaisons jouées legato et dessinées dans la
  partition (`c( d e f)`), swing des croches et doubles croches
  (`swing=62`), section 2.16.
- **Reprises et signes** : reprises avec cases (`|: ... |1. ... :| |2. ...
  ||`) imprimées comme telles dans la partition, accents, points d'orgue,
  trilles, mordants et gruppettos qu'on entend (`c$fermata`, `d$tr`),
  indications de texte (`$"rit."`), section 2.17.
- **Octaves relatives et tonalité** : `rel:` écrit les mélodies sans
  octaves (chaque note va près de la précédente, `*+` et `*-` pour sauter),
  `key=G` donne aux notes les altérations de la tonalité (`n` pour le
  bécarre) ; un bouton réécrit ainsi une piste existante, section 2.18.
- **Micro-timing, accordage, MTXT** : `shift=-10` avance ou retarde les
  notes de quelques millisecondes sans changer le rythme écrit,
  `tune=-20` accorde l'instrument en cents (rampes comprises) ; au-delà
  de 15 pistes le MIDI utilise plusieurs ports, ainsi chaque piste a son
  canal ; import et export [MTXT](https://github.com/Daninet/mtxt),
  section 2.19.
- **Ancres de mesure** : `bar=29` amène le curseur au début de la mesure 29
  (avec les silences nécessaires) et avertit si la piste l'a déjà dépassé,
  section 2.20.
- **Transposition** : `transpose=2` transpose les notes qui suivent,
  `%Theme+7` joue un pattern une quinte plus haut (les altérations suivent
  la tonalité), section 2.21 ; valable aussi pour les fichiers de la bibliothèque MIDI (`&"Basse"+7`).
- **Levée et `reset:`** : la mesure en levée (`Levare: 1`) place la
  mesure 1 où elle doit être ; `reset:` remet l'état initial ; le fichier
  déclare sa version (`ST: 2.6`) et accepte aussi les mots-clés anglais,
  section 2.22.
- **Spécification formelle et bibliothèque autonome** : la notation et le
  format `.st` sont décrits dans [docs/spec/ST-language.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md)
  (CC BY 4.0, en anglais et en italien) avec une suite de conformité ; le
  moteur est la bibliothèque Python `st_language`, sans dépendances, qui
  s'installe avec `pip install git+https://github.com/openssound/st-language.git` et fournit les commandes
  `st-language check | midi | musicxml` (section 2.14 du guide).
- **État courant** (section 4) : grille et vélocité persistent pendant le
  parcours séquentiel de la piste.
- **Percussions et kit de batterie** (section 5) : 36 identifiants associés
  au General MIDI Drum Map — kit de base (kick, snare, hihat, hihat_open,
  tom1, tom2, floor, crash, ride, kick2, rimshot, clap), autres
  toms/cymbales/charlestons (snare2, hihat_pedal, tom_lowmid, tom_hi,
  tom_highfloor, china, ride_bell, tambourine, splash, cowbell, crash2,
  ride2) et percussions latines (bongo_hi, bongo_low, conga_mute,
  conga_open, conga_low, timbale_hi, timbale_low, cabasa, maracas, claves,
  woodblock_hi, woodblock_low).
- **Patterns universels** (section 6) : une bibliothèque `%Nom`
  réutilisable sur n'importe quel instrument, avec développement récursif
  et persistance de l'état.
- **Moteur de voicing automatique** (Vision du produit) : convertit un
  accord abstrait en notes concrètes selon le profil de l'instrument
  (Piano/Guitare : voicing étendu ; Basse : fondamentale+quinte ;
  Trompette : monophonique sur la fondamentale), en adaptant les notes au
  registre jouable. Suffixe optionnel `.style` (ex. `Cmaj7.drop2`,
  `C7.cagEd`, `C.power`) pour imposer un style de voicing précis, prioritaire
  sur l'algorithme automatique, avec un repli intelligent sur l'équivalent
  générique le plus proche si le style demandé n'a pas de sens pour
  l'instrument de la piste. **Un double-clic sur un accord** (compact ou
  déjà figé en notes explicites) dans l'éditeur de piste/pattern ouvre un
  menu avec les voicings possibles pour l'instrument, navigable avec les
  flèches avec un aperçu sonore de chacun, Entrée/clic pour appliquer,
  Échap/clic à l'extérieur pour annuler.
- **Figement du voicing → notes explicites** : un bouton de l'interface qui
  remplace chaque accord par le bloc `[...]` de notes concrètes générées.
- **Timeline commune et mixage** : Solo/Mute/Volume/Pan par piste, moteur de
  synthèse partagé, les pistes ne se synchronisent pas par les barres de
  mesure (les durées s'accumulent sur la timeline : le `|` contrôle, il ne
  déplace rien).
- **Éditeur avec validation syntaxique en direct** et **autocomplétion** des
  tokens (qualités d'accord, styles de voicing, percussions/nuances,
  références `%pattern` et `&"midi"`).
- **Structure du morceau** (vue alternative en box, `Ctrl+Shift+B`) : chaque
  piste devient une ligne sur un axe temporel commun, son contenu étant
  divisé en box que l'on fait glisser horizontalement — utile pour
  travailler sur la structure du morceau (intro/couplet/refrain...) plutôt
  que note par note. Les imports MIDI/audio divisent automatiquement le
  résultat en plusieurs box là où le morceau fait une longue pause.
  Annuler/rétablir dédiés (`Ctrl+Z`/`Ctrl+Y`), génération de batterie/basse
  directement dans un nouveau box, export/import d'un seul box en fichier
  `.box`, aperçu Lecture/Pause du box sélectionné et tête de lecture pendant
  l'exécution du morceau entier.
- **Import/export MIDI standard** (au mieux pour l'import : les notes sont
  quantifiées sur la grille, les chevauchements deviennent des voix `{ ; }`
  dans la même piste et les paroles, fichiers karaoké compris, des paroles
  entre guillemets).
- **Export de la partition en MusicXML** (Projet → Exporter → Partition MusicXML) :
  une partie par piste avec notes, grilles d'accords, tonalité, métrique,
  tempo, nuances et batterie sur une portée de percussion, à ouvrir et
  imprimer avec MuseScore, Finale, Sibelius ou Dorico (section 10.1 du
  guide), avec les voix des blocs `{ ; }` et les paroles.
- **Partition dans SoundText** (Affichage → Partition, `Ctrl+Shift+P`) : les
  pistes sur la portée, mises à jour pendant la saisie, mises en page par
  Verovio ; export PDF et impression sans logiciel externe (section
  10.1bis).
- **Import de partitions MusicXML** (Projet → Importer → MusicXML, aussi
  `.mxl`) : une piste par partie, instruments transpositeurs à la hauteur
  réelle, reprises, fois et D.C./D.S./Coda déroulés, plusieurs voix dans la
  même piste, paroles, symboles d'accords dans une piste Accords (section
  10.2 du guide).
- **Notation ABC** (Projet → Importer → ABC / Exporter → Partition ABC) :
  le format texte des recueils de musique traditionnelle, d'abcjs et
  d'EasyABC, dans les deux sens : voix, instruments, tonalité, mesure,
  n-olets, reprises et fois, symboles d'accords et paroles (section 10.3
  du guide).
- **Plugins externes VST3 et LV2** : comme effets dans la chaîne d'une piste
  ou du master, ou comme instruments virtuels qui jouent les notes d'une
  piste à la place du SoundFont. Les plugins tournent dans un processus
  séparé, donc un plugin qui se bloque n'arrête pas l'application (section
  8.7 du guide).
- **Interface en quatre langues** : italien, anglais, français et espagnol
  (Options → Langue), avec le guide de l'utilisateur traduit dans les mêmes
  langues. Le format des fichiers `.st` et la notation sont identiques dans
  toutes les langues.
- **5 instruments de départ** : Piano, Guitare, Basse, Trompette, Batterie,
  plus des **instruments personnalisés** définis par l'utilisateur (menu Sons).
- **Pistes modifiables** : renommage et changement d'instrument à tout
  moment (double-clic sur l'en-tête de la piste, ou menu ⋯).
- **Import/export MIDI d'une seule piste**, en plus de l'ensemble entier.
- **Bibliothèque MIDI réutilisable** (dossier `midi/`, aussi avec des
  sous-dossiers par catégorie) : fichiers `.mid` que l'on rappelle dans une
  piste avec `&"Nom"` (recherche récursive) ou `&"SousDossier/Nom"` (chemin
  explicite), avec répétition (`2&"Nom"`). On les gère
  (voir/modifier/importer/renommer/supprimer) depuis l'interface comme les
  patterns.
- **Dossier `songs/`** comme emplacement par défaut pour ouvrir/enregistrer
  vos projets, distinct de `examples/` (projets de démonstration).
- **Chargement automatique des instruments personnalisés** : si un morceau
  utilise un instrument pas encore présent en local, sa définition
  (enregistrée dans le fichier `.st` lui-même) est enregistrée
  automatiquement à l'ouverture, sans perdre de pistes ni demander
  d'opérations manuelles.
- **Reconnaissance de l'instrument à l'import MIDI** : si un canal utilise
  exactement le Program Change GM d'un instrument déjà disponible, il le
  réutilise, sinon il **crée et enregistre automatiquement un nouvel
  instrument personnalisé** avec ce programme (nom/paramètres suggérés par
  la famille General MIDI) ; ainsi l'import reste fidèle à l'instrument
  d'origine au lieu de se contenter du plus proche. L'utilisateur reçoit la
  liste des nouveaux instruments créés.
- **Patterns avec répétition** (`3%Nom`). L'ancienne syntaxe de
  transposition en ligne (`%Nom/2`) n'existe plus : pour transposer un box
  on utilise **Transposer...** dans le menu du clic droit de la vue
  Structure du morceau.
- **Guide de l'utilisateur intégré** (menu Aide), avec les instructions
  d'installation pour les principales distributions Linux, pour Windows et
  pour macOS.
- **Lecture avec rendu hors ligne** (fluidsynth + SoundFont rendu en WAV
  avant la lecture, pour éviter les crépitements dus aux sous-alimentations
  du pilote audio), avec un SoundFont configurable et un diagnostic du
  moteur utilisé. Avec la bibliothèque FluidSynth (utilisée directement), le rendu
  utilise une seule instance persistante de fluidsynth pour toute la
  session (SoundFont chargé une seule fois en mémoire au lieu de le faire à
  chaque Play) : latence de démarrage beaucoup plus faible, même stratégie
  contre les crépitements (le rendu reste hors ligne vers un fichier, pas
  sur la sortie audio en temps réel). Il se replie automatiquement sur le
  binaire CLI `fluidsynth` si le binding n'est pas installé. Avec
  `sounddevice` en plus, le morceau rendu est joué directement et gardé en
  cache : **pause/reprise et sauts instantanés** (clic sur la barre
  d'avancement ou sur la règle de la Structure du morceau) et **boucle A-B**
  d'une section (menu Lecture → Boucle).
- **Interface soignée** : thème sombre cohérent sur la fenêtre principale
  et les fenêtres de dialogue, coloration syntaxique en direct dans
  l'éditeur (couleurs pour notes/accords/percussions/commandes
  d'état/références, basées sur le vrai tokenizer du parseur), raccourcis
  clavier, info-bulles partout, table de mixage avec code couleur par
  famille d'instruments et état vide guidé. Pendant la lecture l'éditeur
  défile automatiquement (seulement si nécessaire) pour garder toujours
  visible le token en cours.
- **Réorganisation automatique avec les patterns** : extraction des blocs
  répétés en patterns réutilisables, ou développement de toutes les
  références en tokens littéraux, sans modifier le contenu musical (vérifié
  par des tests aller-retour sur tous les projets d'exemple).
- **Écoute directe** d'un pattern (avec choix de l'instrument d'aperçu) ou
  d'un fichier de la bibliothèque MIDI, directement depuis leurs fenêtres de
  gestion.
- **Volume de piste efficace (0-200 %)** : il agit directement sur la
  vélocité des notes à l'export/à la lecture (pas seulement sur le Channel
  Volume MIDI, souvent peu perceptible), avec une marge de boost jusqu'à
  200 % pour faire ressortir les instruments faibles dans le mixage.
- **Persistance de la table de mixage** : Volume/Pan/Mute/Solo de chaque
  piste sont enregistrés dans le fichier `.st` et rétablis à la réouverture
  (auparavant ils se perdaient à chaque enregistrement).
- **Import audio (voix/micro/fichier)** : enregistrement depuis le micro ou
  chargement (aussi par glisser-déposer) d'un fichier `.wav`/`.mp3`/`.m4a`,
  converti automatiquement en notation textuelle avec un moteur de
  quantification configurable (grille 1/4-1/32, triolets 8T/16T). Détection
  de hauteur pour les pistes mélodiques/harmoniques (segmentation par une
  détection d'attaques dédiée, fiable même dans le registre grave et sur le
  chant lié, avec une estimation de la hauteur par médiane robuste au
  vibrato/aux imprécisions de justesse), détection de transitoires avec
  classification kick/snare/hihat pour les pistes de percussion, avec un
  aperçu d'écoute avant de confirmer ; le texte généré est toujours validé
  avant d'être inséré dans la piste ou le pattern (menu **Piste → Importer dans cette piste → Audio → notation...**, l'entrée « Importer de l'audio → notes » du menu ⋯ de la
  piste, ou depuis la fenêtre de gestion des patterns). Case **« Source :
  voix/beatbox »** pour quand on chante/fredonne la partie au lieu
  d'enregistrer le vrai instrument : elle recalibre l'analyse sur les
  caractéristiques acoustiques de la voix humaine au lieu de celles de
  l'instrument de destination.

Non implémenté dans cette première version (indiqué dans le document comme
phase ultérieure ou hors du standard MVP) : l'import par OMR depuis des
partitions traditionnelles.

## Prérequis

- Linux, Windows ou macOS, avec Python 3.10+
- Un synthétiseur MIDI du système pour l'écoute directe dans l'application
  (l'un de `fluidsynth` avec un SoundFont GM, `timidity`, `wildmidi`). Sans
  eux l'application peut quand même exporter du MIDI standard lisible par
  n'importe quel lecteur externe. Avec la bibliothèque système `libfluidsynth` (installée avec le paquet
  `fluidsynth` de la distribution, voir plus bas) SoundText utilise le
  moteur de rendu persistant à faible latence (voir plus haut), sans
  paquet Python supplémentaire.
- Pour convertir de l'audio (micro ou fichiers .mp3/.m4a/.flac/.ogg/.wav)
  en notation : les fichiers sont lus par le décodeur de Qt Multimedia, déjà
  inclus dans PySide6 (le programme `ffmpeg` ne sert que de solution de
  repli, si le PySide6 utilisé ne l'inclut pas) ; le micro nécessite la
  bibliothèque système `libportaudio2` sous Linux (pour le paquet pip
  `sounddevice`, qui sert aussi à la lecture directe avec boucle et sauts).
  S'il manque quelque chose, **Piste → Importer dans cette piste → Audio → notation...** le signale
  par un message explicite au lieu d'échouer en silence.
- **(Optionnel)** Pistes audio : `libportaudio2` (avec `sounddevice`) sert
  aussi à enregistrer voix, guitare ou clavier depuis la carte son (Piste →
  Enregistrer dans la piste audio...) ; les fichiers mp3/m4a/flac/ogg
  s'importent comme les `.wav`, rééchantillonnés à 48 kHz.

## Installation

Choisissez la méthode adaptée à votre système. Pour les **plugins et les amplis NAM**, il faut ensuite télécharger les plugins gratuits (`scarica_strumenti`) et les profils NAM (menu **Instruments → Télécharger les profils NAM recommandés...**) : ils ne sont pas inclus. Une connexion Internet est nécessaire.

| Système | Comment installer | Après l'installation |
|---|---|---|
| **Linux (recommandé)** | depuis le dépôt : `./install.sh` (installe FluidSynth, PortAudio, lilv via le gestionnaire de paquets, crée le virtualenv, ajoute la commande `soundtext` et une entrée de menu ; `--yes` sans questions, `--uninstall` pour désinstaller) | `~/.local/share/soundtext/scarica_strumenti.sh` |
| **Linux, AppImage** | téléchargez `SoundText-linux-*.AppImage`, `setup-appimage.sh` et `scarica_strumenti.sh`/`.py` dans le même dossier, puis `./setup-appimage.sh` (installe FUSE 2, FluidSynth, SoundFont GM, PortAudio, lilv et les bibliothèques Qt ; `--integra` ajoute une entrée de menu) | `./scarica_strumenti.sh` |
| **Linux, portable** (`.tar.gz`) | extrayez et lancez `./setup-portable-linux.sh` (mêmes bibliothèques, sans FUSE), puis `./SoundText` | `./scarica_strumenti.sh` |
| **Windows, installateur** (`SoundText-setup-*.exe`) ou **portable** (`.zip`) | lancez l'installateur, ou extrayez le zip et lancez `setup-windows.bat` (vérifie le Visual C++ Redistributable et Python ; FluidSynth est déjà inclus), puis `SoundText.exe` | `scarica_strumenti.bat` |
| **macOS** | depuis le dépôt : `./install-macos.sh` (installe FluidSynth, PortAudio et Python avec Homebrew, crée le virtualenv) | `~/Library/Application Support/SoundText/scarica_strumenti.sh` |

`scarica_strumenti.sh`/`.bat` nécessitent Python 3.8+ (inutile pour utiliser l'application). `./scarica_strumenti.sh` sans argument liste les groupes ; `host` installe 7-Zip, sfizz et Surge XT ; `libreria` compile le moteur SFZ interne (environ 5 minutes).

### Installation manuelle depuis les sources

```bash
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# optionnel, pour l'écoute directe dans l'application :
sudo apt install fluidsynth fluid-soundfont-gm   # Debian/Ubuntu

# optionnel, pour l'écoute directe avec boucle et le micro :
sudo apt install libportaudio2                   # Debian/Ubuntu

# optionnel, pour les plugins LV2 (Linux ; les VST3 n'ont besoin de rien d'autre) :
sudo apt install liblilv-0-0                     # Debian/Ubuntu
```

Instructions détaillées pour Debian/Ubuntu, Arch/CachyOS, Fedora, openSUSE,
**Windows et macOS** (y compris l'installation de fluidsynth et d'un
SoundFont) dans le menu **Aide → Guide de l'utilisateur** de l'application,
ou dans `docs/HELP.fr.md`.

## Démarrage

Sous Linux/macOS le script `run.sh` crée au premier démarrage le
virtualenv `venv/` avec les dépendances de `requirements.txt` (il les met à
jour quand le fichier change) et lance l'application ; il accepte les mêmes
arguments que `main.py` :

```bash
./run.sh
./run.sh examples/ensemble_demo.st
```

Avec les dépendances déjà installées on peut aussi la lancer directement :

```bash
python3 main.py
# ou en ouvrant directement un projet d'exemple :
python3 main.py examples/ensemble_demo.st
```

La langue de l'interface se choisit dans **Options → Langue** (la première
fois, SoundText utilise la langue du système si elle fait partie des quatre
disponibles, sinon l'anglais).

## Prise en main rapide

1. **+ Ajouter une piste → Piste avec instrument...** : choisissez un
   instrument (Piano/Guitar/Bass/Trumpet/Drums) et donnez-lui un nom. Depuis
   le même menu on crée des pistes audio ou des pistes déjà générées
   (batterie, grille d'accords...).
2. Passez à la vue **Texte** et sélectionnez la piste dans la colonne Pistes
   à gauche : l'éditeur s'ouvre à droite.
3. Écrivez la notation, ex. :
   ```
   16: 100@ c*4 e*4 g*4 e*4 Cmaj7 [kick hihat]
   ```
   La validation syntaxique apparaît sous l'éditeur en temps réel.
4. Utilisez Solo/Mute/Volume/Pan sur la bande de la piste pour le mixage.
5. **Composer → Gérer la bibliothèque de patterns (%Nom)...** pour
   définir des `%Nom` réutilisables sur n'importe quelle piste.
6. **▶ Play** pour l'écoute (nécessite un synthé du système), **Projet → Exporter → MIDI...** pour enregistrer le fichier `.mid`, **Projet → Exporter → Partition MusicXML...** pour ouvrir le morceau dans
   MuseScore, Finale, Sibelius ou Dorico et l'imprimer.
7. **Projet → Enregistrer** enregistre dans le format texte natif `.st`,
   lisible et modifiable aussi à la main.

## Tests

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

Les tests tournent aussi automatiquement sur GitHub à chaque push
(workflow `.github/workflows/tests.yml`).

## Structure du projet

```
soundtext/
  st_language/           (la bibliothèque ST-language vit dans le dépôt openssound/st-language : pip install, voir requirements.txt)
  core/
    instruments.py     profils d'instrument + table des percussions GM + catalogue General MIDI
    chords.py           -> st_language/chords.py (même module)
    notation.py          -> st_language/notation.py (même module)
    completion.py         autocomplétion des tokens dans l'éditeur
    model.py              Project/Track, logique Solo/Mute, renommage/changement d'instrument
    project_io.py          format de projet texte (.st) + dossier songs/
    tempo_map.py           -> st_language/timing.py (même module)
    arrangement.py         box de la vue Structure du morceau (durées, aplatissement)
    rhythm_generate.py     génération algorithmique de batterie, basse et accompagnement
    key_detect.py          estimation de la tonalité du morceau
    midi_convert.py         analyse MIDI partagée, indexation de la bibliothèque &"Nom"
    midi_export.py          export MIDI multipiste ou d'une seule piste
    midi_import.py           import MIDI -> notation (avec reconnaissance de l'instrument)
    musicxml_import.py       import de partitions MusicXML (aussi .mxl) -> notation
    abc_import.py            import de morceaux ABC -> notation
    voice_merge.py           voix d'un canal importé réunies en blocs { ; }
    import_lyrics.py         paroles des imports MIDI (karaoké aussi) et MusicXML
    score_render.py          partition mise en page par Verovio (SVG pour la vue et le PDF)
    playback.py               moteur de lecture (rendu hors ligne + SoundFont + cache)
    audio_stream.py           lecture directe du rendu (saut, boucle A-B, position exacte)
    metronome_sounds.py       sons du clic du métronome
    settings.py                réglages persistants (chemin du SoundFont, quantification, langue)
    i18n.py                    langues de l'interface (tr() et les catalogues de locales/)
    reorganize.py               extraction/développement automatique des patterns
    audio_quantize.py            moteur de quantification audio -> notation
    audio_decode.py               lecture des fichiers audio (Qt Multimedia, repli ffmpeg)
    fluid.py                      liaison directe avec la bibliothèque FluidSynth
    audio_recorder.py              enregistrement au micro (sounddevice)
    audio_pitch.py                  détection de hauteur pour les pistes mélodiques
    audio_percussion.py              détection de transitoires pour les pistes de percussion
    audio_dsp.py                      analyse audio en numpy (attaques SuperFlux, hauteur YIN)
    audio_import.py                   chaîne complète d'import audio -> notation
    midi_input.py                      clavier MIDI externe (mido + python-rtmidi)
  gui/
    main_window.py     fenêtre principale (éditeur, menus, barre d'outils) ; ses parties dans
                       main_window_project.py / _mixer.py / _playback.py
    arrangement_view.py vue Structure du morceau (box, règle, tête de lecture, boucle)
    keyboard_play_dialog.py « Jouer au clavier » (enregistrement depuis le clavier du PC)
    midi_keyboard.py    clavier MIDI externe dans la même fenêtre (core/midi_input.py)
    rhythm_generate_dialog.py fenêtres Générer batterie/basse/accompagnement
    metronome_engine.py  clic du métronome synchronisé avec la lecture
    track_header.py     en-tête de piste (M/S/●, ⋯, boutons Vol/Pan), identique dans les deux vues
    knob.py             bouton compact pour le volume et le pan
    track_widget.py     code couleur par famille d'instruments, étiquette du pan
    instrument_dialog.py gestion des instruments personnalisés (sélection GM par nom)
    midi_library_dialog.py gestion de la bibliothèque MIDI (sous-dossiers compris)
    audio_import_dialog.py enregistrement/chargement audio + quantification
    voicing_picker.py       menu de choix du voicing au double-clic sur les accords
    help_dialog.py       guide de l'utilisateur intégré
    highlighter.py         coloration syntaxique (basée sur le vrai tokenizer)
    theme.py                feuille de style sombre globale de l'application
  locales/              traductions de l'interface (en, fr, es) et extract.py
  assets/
    icon.png              icône de l'application
  examples/            projets .st de démonstration des fonctionnalités
  songs/                dossier par défaut pour vos projets (Ouvrir/Enregistrer)
  midi/                 bibliothèque de fragments MIDI rappelés avec &"Nom",
                        organisable en sous-dossiers (Guitar/, Blues/, ...)
  tests/                tests automatiques du moteur de notation
  main.py                point d'entrée de l'application (applique thème + icône)
  diagnose_audio.py       outil de diagnostic en ligne de commande pour calibrer
                          la détection de hauteur/la classification des percussions sur
                          de vrais enregistrements (voir 'python3 diagnose_audio.py --help')
```

## Licence

Copyright © 2026 Sergio Scolaro.

SoundText est un logiciel libre : vous pouvez le redistribuer et/ou le
modifier selon les termes de la **GNU General Public License version 3**
(fichier [LICENSE](LICENSE)). Il est distribué dans l'espoir qu'il sera
utile, mais **sans aucune garantie**.

SoundText utilise des bibliothèques et des contenus tiers (FluidSynth,
Qt/PySide6, pedalboard, NumPy, le SoundFont FluidR3_GM et d'autres),
chacun avec sa propre licence : auteurs, licences et textes intégraux sont
dans [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) (en italien) et dans
le dossier [licenses/](licenses/). Le guide (Aide → Guide de l'utilisateur,
chapitre 14) explique ce que ces licences impliquent pour qui distribue le
programme.
