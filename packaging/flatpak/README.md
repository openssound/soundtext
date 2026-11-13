# Flatpak di SoundText

File per costruire SoundText come Flatpak e, in un secondo tempo, proporlo
a Flathub:

| File | Che cos'è |
|---|---|
| `io.github.openssound.SoundText.yml` | la ricetta (manifest) |
| `python-deps.json` | i pacchetti Python di `requirements.txt`, ognuno con il suo SHA-256; lo scrive `genera_dipendenze.py` |
| `io.github.openssound.SoundText.metainfo.xml` | la scheda dell'applicazione per gli store (AppStream) |
| `io.github.openssound.SoundText.desktop`, `soundtext.sh` | voce di menu e comando |

**Stato: la build locale funziona** (novembre 2026, runtime 25.08, sorgenti
del ramo main). Controllato dentro il Flatpak: il programma parte e apre la
finestra principale, vede le schede audio, il sequencer ALSA per le tastiere
MIDI, un server JACK e i plugin LV2 installati come estensioni. Non ancora
provati: l'ascolto vero e proprio, il download dei suoni, la build con il
tag di una release e i controlli di Flathub (`flatpak-builder-lint`).

## Costruirlo in locale

Servono `flatpak` e `flatpak-builder` (anche come Flatpak:
`flatpak install flathub org.flatpak.Builder`, poi `flatpak run
org.flatpak.Builder` al posto di `flatpak-builder`), e circa 3 GB di spazio.

```bash
flatpak install flathub org.freedesktop.Platform//25.08 org.freedesktop.Sdk//25.08
cd packaging/flatpak
git clone https://github.com/flathub/shared-modules.git
```

Per provare i sorgenti di questa cartella, e non il tag di una release, nel
manifest sostituisci la sorgente del modulo `soundtext` con:

```yaml
    sources:
      - type: dir
        path: ../..
```

Poi:

```bash
flatpak-builder --user --install --force-clean build io.github.openssound.SoundText.yml
flatpak run io.github.openssound.SoundText
```

## Da sapere

- **Plugin.** Dentro un Flatpak i plugin installati nel sistema
  (`/usr/lib/lv2`, `~/.vst3`, ...) non si vedono. Si usano quelli pubblicati
  come estensioni Flatpak (`org.freedesktop.LinuxAudio.Plugins.*`: LSP,
  Surge XT, Dragonfly Reverb, x42, ZamPlugins...), che il manifest collega
  con `LV2_PATH`, `VST3_PATH` e `CLAP_PATH`.
- **JACK.** L'uscita su JACK passa dal socket di PipeWire
  (`--filesystem=xdg-run/pipewire-0`); con un `jackd` classico non funziona.
- **Motore SFZ interno.** Si scarica già compilato da *Suoni → Scarica e
  installa*; la compilazione sul posto non è possibile nel Flatpak.
- **Cartelle.** L'app vede Documenti e Musica; gli altri file si aprono
  dalla finestra di scelta dei file.
- **Python.** Il runtime 25.08 ha Python 3.13: se cambi runtime, cambia
  `PYTHON` in `genera_dipendenze.py` e rigenera `python-deps.json`. Lo
  stesso quando cambia `requirements.txt`.
- **Moduli compilati.** Tre cose non arrivano pronte e le compila il
  manifest: `krb5` (lo chiede QtMultimedia di PySide6), PortAudio e
  `python-rtmidi`, che su PyPI non ha il pacchetto per Python 3.13.

## Pubblicarlo su Flathub

1. Fai funzionare la build locale e prova il programma.
2. Nel manifest metti `tag` e `commit` della release che contiene questa
   cartella, e nella scheda AppStream aggiungi la `<release>`.
3. Segui <https://docs.flathub.org/docs/for-app-authors/submission>: fork di
   `flathub/flathub`, ramo `new-pr`, il manifest nella radice (con
   `shared-modules` come sottomodulo e `python-deps.json`), poi la pull
   request. I revisori di Flathub chiedono di solito di restringere i
   permessi (`--device=all`, le cartelle) e di giustificarli.
4. L'identificativo `io.github.openssound.SoundText` richiede che il
   repository sia `github.com/openssound/soundtext`, com'è.
