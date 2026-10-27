"""
Cosa NON deve finire negli installer e nelle build: il manuale Word, la guida
PDF, le immagini della guida PDF (docs/guida_brano), le sottocartelle e il file
d'esempio di midi/ (la libreria MIDI e' dell'utente) e gli script che
preparano gli installer. La guida utente del programma e' docs/HELP*.md, che
invece ci deve stare, come gli script che il programma stesso cita.
"""

# gli script che preparano gli installer: servono a chi compila, non a chi installa
BUILD_SCRIPTS = ("build-appimage.sh", "build-linux-portable.sh", "build-windows-portable.ps1",
                 "installer-windows.iss", "package-for-linux.ps1")
# script e programmi di servizio che l'installazione deve invece tenere
KEPT_SCRIPTS = ("scarica_strumenti.sh", "scarica_strumenti.py", "scarica_profili_nam.py")

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _app_items(text):
    """Gli elementi della radice che gli installer da sorgente copiano (APP_ITEMS)."""
    match = re.search(r"APP_ITEMS=\(([^)]*)\)", text)
    assert match, "APP_ITEMS non trovato"
    return match.group(1).split()


def test_source_installers_copy_only_what_the_program_needs():
    for script in ("install.sh", "install-macos.sh"):
        text = _read(script)
        items = _app_items(text)
        for needed in ("main.py", "core", "gui", "locales", "assets", "docs", "licenses",
                       "requirements.txt", "LICENSE", "THIRD_PARTY_NOTICES.md"):
            assert needed in items, f"{script}: {needed} deve essere copiato"
        for name in KEPT_SCRIPTS:
            assert name in items, f"{script}: {name} serve al programma installato"
        for unwanted in ("st_language", "tests", "midi", "songs", "SoundText_Manuale_Utente.docx", "README.md", *BUILD_SCRIPTS):
            assert unwanted not in items, f"{script}: {unwanted} non va copiato"
        assert "examples/*" in text and "*.wav) continue" in text     # esempi senza i render audio
        assert "FluidR3_GM.sf2" not in text                    # il SoundFont lo propone l'app al primo avvio
        # la pulizia delle installazioni precedenti sta DENTRO il ramo "copia i sorgenti":
        # lanciato dalla cartella di installazione stessa, lo script non cancella file del repository
        start = text.index('if [ "$SRC_DIR" != "$INSTALL_DIR" ]; then')
        end = text.index("# rsync/cp non cancellano")
        block = text[start:end]
        assert 'rm -rf "$INSTALL_DIR/docs/guida_brano"' in block, script
        assert "PUBBLICARE_SU_PYPI.md" in block, script
        assert re.search(r'cp -a .*SoundText_Guida_dal_primo_accordo_al_WAV\.pdf "\$INSTALL_DIR/docs/"', block), script  # la guida PDF in docs/
        assert "SoundText_Manuale_Utente.docx" in block and "SoundText_Guida_dal_primo_accordo_al_WAV.pdf" in block
        for name in BUILD_SCRIPTS:
            assert f'"$INSTALL_DIR/{name}"' in block, f"{script}: {name} non viene tolto da un'installazione precedente"
        for name in KEPT_SCRIPTS:
            assert f'"$INSTALL_DIR/{name}"' not in block, f"{script}: {name} serve al programma installato"


def test_portable_builds_and_release_workflow_drop_the_pdf_images():
    assert 'rm -rf "$DIST_DIR/docs/guida_brano"' in _read("build-linux-portable.sh")
    assert 'docs\\guida_brano' in _read("build-windows-portable.ps1")
    assert 'docs\\guida_brano' in _read("package-for-linux.ps1")
    workflow = _read(".github", "workflows", "build-release.yml")
    assert "dist\\SoundText\\docs\\guida_brano" in workflow          # zip e installer Windows
    assert "rm -rf AppDir/usr/bin/docs/guida_brano" in workflow       # AppImage
    assert "test ! -e AppDir/usr/bin/docs/guida_brano" in workflow    # e lo si controlla


def test_the_app_help_stays_in_the_builds():
    """docs/ si copia ancora per intero (meno guida_brano): la guida e' docs/HELP.md."""
    for script in ("build-linux-portable.sh", "build-windows-portable.ps1"):
        assert re.search(r'\bdocs\b', _read(script))
    assert "docs\\HELP.md" in _read(".github", "workflows", "build-release.yml")
    for name in ("HELP.md", "HELP.en.md", "HELP.fr.md", "HELP.es.md"):
        assert os.path.exists(os.path.join(ROOT, "docs", name))


def test_the_midi_library_is_shipped_empty_and_the_users_files_are_never_deleted():
    for script in ("install.sh", "install-macos.sh"):
        text = _read(script)
        assert "midi" not in _app_items(text), script                      # la libreria MIDI non si copia
        start = text.index('if [ "$SRC_DIR" != "$INSTALL_DIR" ]; then')
        block = text[start:text.index("# rsync/cp non cancellano")]
        assert 'mkdir -p "$INSTALL_DIR/midi"' in block                      # la cartella c'e', vuota
        assert 'cmp -s "$shipped"' in block                                  # si tolgono solo i file d'esempio identici
        assert 'rmdir "$INSTALL_DIR/midi/' in block                          # e le sottocartelle rimaste vuote
        assert "rm -rf \"$INSTALL_DIR/midi" not in block                     # mai la libreria dell'utente
    assert 'mkdir -p "$DIST_DIR/midi"' in _read("build-linux-portable.sh")
    assert 'Join-Path $DistDir "midi"' in _read("build-windows-portable.ps1")
    workflow = _read(".github", "workflows", "build-release.yml")
    assert 'New-Item -ItemType Directory -Force -Path "dist\\SoundText\\midi"' in workflow
    assert "mkdir -p AppDir/usr/bin/midi" in workflow
    # "Scarica e installa" cerca lo script accanto all'eseguibile: dentro l'AppImage
    assert "cp scarica_strumenti.py AppDir/usr/bin/" in workflow
    release_files = workflow[workflow.index("SoundText-linux-*.AppImage"):].split("\n\n")[0]
    assert "scarica_strumenti" not in release_files                  # non piu' allegati a parte
    assert 'test -z "$(find AppDir/usr/bin/midi -mindepth 1 -print -quit)"' in workflow


def test_macos_installer_works_without_the_repository_and_reports_failures():
    """Lanciato da solo (fuori dal repository) scarica i sorgenti invece di
    fallire su requirements.txt; il comando finisce nel PATH e SoundText.app,
    se il programma non parte, mostra un avviso col log invece di non fare nulla."""
    text = _read("install-macos.sh")
    assert "has_sources \"$SRC_DIR\"" in text and "archive/refs/heads/main.tar.gz" in text
    assert '"$INSTALL_DIR/$needed"' in text                     # main.py e requirements.txt verificati
    assert "grep -v '^python-rtmidi'" in text                    # rtmidi facoltativo non blocca pip
    assert 'export PATH="$HOME/.local/bin:$PATH"' in text and ".zshrc" in text
    assert "Library/Logs/SoundText.log" in text and "osascript" in text
    assert os.access(os.path.join(ROOT, "install-macos.sh"), os.X_OK)


def test_no_installer_or_build_ships_the_soundfont():
    """SoundText non include un SoundFont: lo propone al primo avvio e lo si
    scarica da Suoni -> Scarica e installa (core.soundfont_downloads, con
    lo SHA-256). Ne' gli installer ne' le build lo copiano o lo scaricano."""
    for name in ("install.sh", "install-macos.sh", "build-linux-portable.sh", "build-windows-portable.ps1",
                 "package-for-linux.ps1", os.path.join(".github", "workflows", "build-release.yml")):
        text = _read(name)
        assert "FluidR3_GM.sf2" not in text and "releases/download/resources" not in text, name
    for name in ("install.sh", "setup-appimage.sh", "setup-portable-linux.sh"):   # neanche quello della distribuzione
        text = _read(name)
        assert "fluid-soundfont-gm" not in text and "soundfont-fluid" not in text, name
    from core.soundfont_downloads import find
    fluid = find("sf-fluidr3")
    assert fluid.url.startswith("https://deb.debian.org/") and len(fluid.sha256) == 64   # non dal GitHub di SoundText


def test_linux_installer_works_without_the_repository_and_reports_failures():
    """Come install-macos.sh: sorgenti scaricati se mancano, rtmidi
    facoltativo, PATH aggiornato e avviso se l'avvio dal menu fallisce."""
    text = _read("install.sh")
    assert "has_sources \"$SRC_DIR\"" in text and "archive/refs/heads/main.tar.gz" in text
    assert '"$INSTALL_DIR/$needed"' in text
    assert "grep -v '^python-rtmidi'" in text
    assert 'export PATH="$HOME/.local/bin:$PATH"' in text and ".bashrc" in text
    assert "soundtext.log" in text and "notify-send" in text
    assert "incluso nel repository" not in text
