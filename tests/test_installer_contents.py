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
        assert "FluidR3_GM.sf2" in text
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
    assert 'test -z "$(find AppDir/usr/bin/midi -mindepth 1 -print -quit)"' in workflow
