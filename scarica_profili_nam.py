#!/usr/bin/env python3
"""
Scarica i profili NAM consigliati (amplificatori e pedali famosi, circa
5 MB) nella cartella profili_nam/ di SoundText, che non e' versionata.
Lo stesso comando c'e' nell'app: Strumenti → Scarica profili NAM
consigliati...

Uso:
    python3 scarica_profili_nam.py [cartella]
"""

import sys

from core.nam_profiles import PROFILES, download_profiles


def main() -> int:
    folder = sys.argv[1] if len(sys.argv) > 1 else None

    def progress(i, total, name):
        if name:
            print(f"[{i + 1}/{total}] {name}", flush=True)

    result = download_profiles(folder, progress)
    print(f"\nCartella: {result['folder']}")
    print(f"Scaricati: {len(result['downloaded'])}, gia' presenti: {len(result['present'])}, "
          f"non riusciti: {len(result['failed'])} (su {len(PROFILES)})")
    for name, reason in result["failed"]:
        print(f"  - {name}: {reason}")
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
