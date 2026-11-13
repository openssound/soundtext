# Pacchetto AUR `soundtext-bin`

Il pacchetto per Arch Linux e derivate (Manjaro, EndeavourOS) prende il
pacchetto portable di una release di GitHub e lo installa in
`/opt/soundtext`, con il comando `soundtext`, la voce nel menu e l'icona.
Non compila niente.

File: `PKGBUILD`, `.SRCINFO` (generato dal PKGBUILD) e `soundtext.desktop`.

## Installarlo dal repository, senza AUR

Il pacchetto non e' ancora su AUR. Chi usa Arch puo' costruirlo e
installarlo da qui: il risultato e' lo stesso pacchetto, gestito da pacman.

```bash
git clone https://github.com/openssound/soundtext.git
cd soundtext/packaging/aur
makepkg -si
```

Per toglierlo: `sudo pacman -R soundtext-bin`.

## Provarlo prima di pubblicare (su Arch)

```bash
cd packaging/aur
makepkg -si            # scarica la release, costruisce e installa
namcap PKGBUILD *.pkg.tar.zst   # facoltativo: i controlli di Arch
```

Qui e' stato controllato solo che `package()` metta i file al loro posto,
con una cartella finta: `makepkg` su una macchina Arch non e' stato
provato.

## Pubblicarlo la prima volta

1. Crea un account su <https://aur.archlinux.org> e aggiungi la tua chiave
   SSH pubblica nel profilo. (A novembre 2026 le registrazioni erano
   chiuse: si pubblica quando riaprono.)
2. Clona il repository vuoto del pacchetto e copiaci i tre file:

   ```bash
   git clone ssh://aur@aur.archlinux.org/soundtext-bin.git
   cp PKGBUILD .SRCINFO soundtext.desktop soundtext-bin/
   cd soundtext-bin
   makepkg --printsrcinfo > .SRCINFO
   git add PKGBUILD .SRCINFO soundtext.desktop
   git commit -m "soundtext-bin 1.19.0"
   git push
   ```

## A ogni versione nuova

1. Cambia `pkgver` nel PKGBUILD (e riporta `pkgrel` a 1).
2. `updpkgsums` aggiorna i due `sha256sums` (oppure copia lo SHA-256 del
   file `SoundText-linux-portable-v<versione>.tar.gz` dalla pagina della
   release).
3. `makepkg --printsrcinfo > .SRCINFO`, prova con `makepkg -si`, poi commit
   e push nel repository AUR.
