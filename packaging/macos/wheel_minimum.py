"""
Controlla che i pacchetti Python installati (quelli che PyInstaller mette
in SoundText.app) funzionino sulla versione minima di macOS dell'app: per
ciascuno conta il macOS dichiarato nel suo wheel (tag macosx_X_Y). Lo usa
build-macos.sh.

    python packaging/macos/wheel_minimum.py 13.0
"""

import re
import sys
from importlib import metadata


def main() -> int:
    minimum = tuple(int(x) for x in (sys.argv[1].split(".") + ["0"])[:2])
    bad = []
    for dist in metadata.distributions():
        try:
            wheel = dist.read_text("WHEEL") or ""
        except OSError:
            continue
        tags = [(int(a), int(b)) for a, b in re.findall(r"macosx_(\d+)_(\d+)", wheel)]
        if tags and min(tags) > minimum:
            bad.append(f"  {dist.metadata['Name']}: macOS {min(tags)[0]}.{min(tags)[1]}")
    if bad:
        print("pacchetti per un macOS piu' recente di " + sys.argv[1] + ":\n" + "\n".join(bad))
        return 1
    print("pacchetti Python: tutti per macOS " + sys.argv[1] + " o precedente")
    return 0


if __name__ == "__main__":
    sys.exit(main())
