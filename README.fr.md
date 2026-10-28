# SoundText

[Italiano](README.md) · [English](README.en.md) · **Français** · [Español](README.es.md)

**SoundText** est un programme pour écrire de la musique sous forme de
texte. Notes, accords et rythmes s'écrivent dans un langage simple, le
**SoundText Language** ; SoundText les joue, les affiche en partition et
les mixe avec des effets, des amplis et des plugins. Il fonctionne sous
Linux, Windows et macOS, en français, italien, anglais et espagnol.

```
ST: 2.7
Tempo: 100 BPM

Track Accords [Piano]:
  4: 4C | 4Am | 4F | 4G |

Track Melodie [Piano]:
  8: e g c*5 g e g c*5 g | a c*5 e*5 c*5 a c*5 e*5 c*5 |
  f a c*5 a f a c*5 a | g b d*5 b 4g |

Track Batterie [Drums]:
  8: [kick hihat] hihat [snare hihat] hihat [kick hihat] hihat [snare hihat] hihat |
```

Les majuscules sont des accords (`C`, `Am`, `G7`) : SoundText choisit tout
seul les bonnes notes pour l'instrument de la piste. Les minuscules sont
des notes, `*5` l'octave, `8:` la durée de base, `|` la fin de la mesure.

## Ce que vous pouvez faire

- **Écrire la musique** : notes, accords avec voicing automatique ou
  choisi, triolets, liaisons, nuances, automations, reprises, plusieurs voix
  dans la même piste, paroles. Pendant la saisie, l'éditeur colore la
  syntaxe et signale les erreurs.
- **Organiser le morceau** : la vue **Structure** montre chaque piste comme
  une rangée de box (intro, couplet, refrain...) à déplacer, copier et
  écouter un par un. Les **patterns** (`%Nom`) et la **bibliothèque MIDI**
  (`&"Nom"`) servent à réutiliser des parties.
- **Générer les parties** : batterie, basse, accompagnement et mélodies à
  partir des accords, sans IA, aussi dans le style de vos morceaux.
- **Façonner le son** : table de mixage, SoundFonts, instruments
  échantillonnés SFZ, effets (EQ, compresseur, delay, réverbération),
  amplis guitare et profils **NAM** d'amplis réels, plugins **VST3** et
  **LV2**, mastering.
- **Jouer et enregistrer** : le clavier de l'ordinateur ou un clavier
  MIDI ; pistes audio pour la voix et la guitare, avec prises multiples,
  boucle et punch-in ; d'un enregistrement audio aux notes.
- **Importer et exporter** : MIDI, MusicXML (MuseScore, Finale, Sibelius,
  Dorico), ABC, MTXT, WAV ; la partition s'affiche et s'imprime en PDF
  directement depuis le programme.

Tout est expliqué dans le **guide de l'utilisateur**, dans le programme
(**Aide → Guide de l'utilisateur**, F1) et dans
[docs/HELP.fr.md](docs/HELP.fr.md).

## Installation

### Paquets prêts

Depuis les [Releases](https://github.com/openssound/soundtext/releases/latest) téléchargez le paquet pour votre système :

| Système | Quoi télécharger | Ensuite |
|---|---|---|
| **Windows** | `SoundText-setup-<version>.exe` (installateur) | lancez-le ; à la dernière page laissez cochée la case qui lance `setup-windows.bat`, qui vérifie le Visual C++ Redistributable |
| **Windows**, portable | `SoundText-windows-<version>.zip` | extrayez, lancez `setup-windows.bat`, puis `SoundText.exe` |
| **Linux**, AppImage | `SoundText-linux-<version>.AppImage` et `setup-appimage.sh`, dans le même dossier | `./setup-appimage.sh` (installe avec `sudo` FUSE 2, FluidSynth, PortAudio, lilv et les bibliothèques Qt ; `--integra` ajoute l'entrée de menu et la commande `soundtext`), puis lancez l'AppImage |
| **Linux**, portable | `SoundText-linux-portable-<version>.tar.gz` | extrayez, lancez `./setup-portable-linux.sh` (les mêmes bibliothèques, sans FUSE ; `--integra` ici aussi), puis `./SoundText` |

### Depuis le code

Pour macOS, qui n'a pas de paquet prêt, ou pour suivre les mises à jour
avec git. Les scripts fonctionnent aussi téléchargés seuls : ils
récupèrent les sources sur GitHub.

- **Linux** : `./install.sh` installe les bibliothèques système (apt, dnf,
  pacman ou zypper), copie le programme dans `~/.local/share/soundtext`,
  crée le virtualenv, la commande `soundtext` et l'entrée de menu.
  Relancé, il met à jour. `--yes` sans questions, `--uninstall` retire la
  commande et le menu (les projets restent), `--purge` efface aussi les
  projets.
- **macOS** : `./install-macos.sh` installe Homebrew s'il manque, puis
  FluidSynth, PortAudio et Python ; il crée le virtualenv, la commande
  `soundtext` et **SoundText.app** dans `~/Applications`. Mêmes options
  que `install.sh`.
- **À la main**, avec Python 3.10 ou plus récent et FluidSynth, PortAudio
  et lilv du système (les paquets pour chaque distribution sont dans le
  guide) :

  ```bash
  git clone https://github.com/openssound/soundtext.git
  cd soundtext
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  python3 main.py
  ```

Les instructions complètes sont aux chapitres 30-32 du guide de
l'utilisateur.

### Après l'installation

Le **SoundFont General MIDI** n'est pas inclus : au premier démarrage
SoundText propose de le télécharger (FluidR3 GM, environ 150 Mo). Depuis
la même fenêtre, **Sons → Télécharger et installer...**, présente dans
toutes les versions, on télécharge aussi les instruments échantillonnés
SFZ, les plugins gratuits, les profils NAM et les baffles IR. Une
connexion Internet est nécessaire.

Si vous préférez le terminal, les scripts `scarica_strumenti.sh` et
`scarica_strumenti.bat`, dans le dossier du programme (sauf avec
l'AppImage, où l'on utilise la fenêtre), font le même
travail et demandent Python 3.8+ (sans arguments ils affichent un menu
numéroté).

## Démarrage

Les paquets prêts se lancent depuis le menu Démarrer (installateur),
depuis `SoundText.exe`, depuis l'AppImage ou depuis `./SoundText` ; après
les scripts d'installation, depuis le menu des applications ou avec la
commande `soundtext`. Depuis le code :

```bash
./run.sh                                # Linux, macOS, Git Bash sous Windows
./run.sh examples/funk_in_mi.st         # en ouvrant tout de suite un exemple
```

Au premier démarrage `run.sh` crée le virtualenv `venv/` avec les
dépendances de `requirements.txt` et les met à jour quand le fichier
change.

La langue se choisit dans **Options → Langue** ; la première fois
SoundText utilise celle du système, si c'est l'une des quatre disponibles,
sinon l'anglais.

## Premiers pas

1. **Projet → Ouvrir un exemple...** ouvre l'un des morceaux du dossier
   `examples/` : écoutez-le avec **F5** et regardez comment il est écrit
   dans la vue **Texte**.
2. Le chapitre 1.2 du guide, **Votre premier morceau**, mène en cinq étapes
   d'un projet vide à quatre mesures avec accords et mélodie.
3. La grammaire complète est au chapitre 4 du guide ; la
   [spécification du SoundText Language](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md)
   (CC BY 4.0) la décrit de façon formelle.

Les projets s'enregistrent comme fichiers `.st` de texte, lisibles et
modifiables avec n'importe quel éditeur ; le dossier par défaut est
`songs/`.

## Pour les développeurs

**Tests** :

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

Ils tournent aussi sur GitHub à chaque push (`.github/workflows/tests.yml`).

**Structure du projet** :

```
soundtext/
  main.py          le point d'entrée du programme
  core/            le moteur : modèle du projet, fichiers .st, MIDI, lecture,
                   effets, plugins, import audio, génération des parties
  gui/             l'interface (PySide6) : fenêtre principale, vue Structure,
                   panneau Effets, boîtes de dialogue
  docs/            le guide de l'utilisateur (HELP.md et ses traductions)
  locales/         les traductions de l'interface
  examples/        morceaux d'exemple
  songs/           le dossier par défaut pour vos projets
  midi/            la bibliothèque MIDI (&"Nom"), aussi en sous-dossiers
  tests/           les tests automatiques
```

La notation est la bibliothèque Python **st-language** (dépôt
[openssound/st-language](https://github.com/openssound/st-language),
`pip install st-language`) : un moteur sans dépendances, avec les
commandes `st-language check | midi | musicxml`, utilisable aussi sans
SoundText.

## Licence

Copyright © 2026 Sergio Scolaro.

SoundText est un logiciel libre : vous pouvez le redistribuer et/ou le
modifier selon les termes de la **GNU General Public License version 3**
(fichier [LICENSE](LICENSE)). Il est distribué dans l'espoir qu'il sera
utile, mais **sans aucune garantie**.

SoundText utilise des bibliothèques et des contenus tiers (FluidSynth,
Qt/PySide6, pedalboard, NumPy et autres), chacun avec sa propre licence :
auteurs, licences et textes intégraux sont dans
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) et dans le dossier
[licenses/](licenses/). Le chapitre 29 du guide explique ce que ces
licences impliquent pour qui distribue le programme.
