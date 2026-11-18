#!/usr/bin/env python3
"""
Le licenze di libsfizz (il motore SFZ interno, sfizioso) e di tutte le
librerie che contiene, in un unico file: va accanto al binario, nella
release libsfizz-* (.github/workflows/libsfizz.yml) e in licenses/sfizioso.txt
(che le build di SoundText distribuiscono). Le licenze BSD e MIT di quelle
librerie chiedono che il loro testo accompagni il binario.

Uso:
    python3 .github/scripts/licenze_sfizioso.py SORGENTI_SFIZIOSO FILE_DI_USCITA

SORGENTI_SFIZIOSO e' un checkout di sfizioso al commit di SFIZIOSO_COMMIT,
con i sottomoduli. Restano fuori le librerie che non finiscono in
libsfizz: cxxopts (programmi da riga di comando), doctest (test di
invoke.hpp), fmidi (lettore MIDI dei programmi di prova) e il plugin xmms
di WavPack (GPL-2.0, non compilato).
"""

import sys
from pathlib import Path

# (componente, licenza, file nei sorgenti), nell'ordine del file di uscita
COMPONENTI = [
    ("sfizioso (fork di sfizz)", "BSD 2-Clause", "LICENSE"),
    ("sfizioso: avviso del fork", "", "NOTICE"),
    ("Abseil (abseil-cpp)", "Apache-2.0", "external/abseil-cpp/LICENSE"),
    ("atomic_queue", "MIT", "external/atomic_queue/LICENSE"),
    ("cephes", "BSD 3-Clause (Netlib)", "external/cephes/LICENSE.txt"),
    ("filesystem (gulrak)", "MIT", "external/filesystem/LICENSE"),
    ("invoke.hpp", "MIT", "external/invoke.hpp/LICENSE.md"),
    ("jsl", "Boost Software License 1.0", "external/jsl/LICENSE.md"),
    ("SIMDe", "MIT", "external/simde/COPYING"),
    ("st_audiofile", "BSD 2-Clause", "external/st_audiofile/LICENSE.md"),
    ("dr_libs (in st_audiofile)", "pubblico dominio o MIT-0", "external/st_audiofile/thirdparty/dr_libs/LICENSE"),
    ("libaiff (in st_audiofile)", "BSD", "external/st_audiofile/thirdparty/libaiff/LICENSE"),
    ("stb_vorbis (in st_audiofile)", "MIT o pubblico dominio", "external/st_audiofile/thirdparty/stb_vorbis/LICENSE"),
    ("WavPack (in st_audiofile)", "BSD 3-Clause", "external/st_audiofile/thirdparty/wavpack/license.txt"),
    ("cpuid", "BSD 3-Clause", "src/external/cpuid/LICENSE.rst"),
    ("hiir", "WTFPL 2", "src/external/hiir/license.txt"),
    ("kiss_fft", "BSD 3-Clause", "src/external/kiss_fft/COPYING"),
    ("pugixml", "MIT", "src/external/pugixml/LICENSE.md"),
    ("spline", "BSD 3-Clause", "src/external/spline/LICENSE"),
    ("tunings (Surge Synth Team)", "MIT", "src/external/tunings/LICENSE.md"),
]

# ThreadPool non ha un file di licenza: la dichiara l'intestazione del sorgente
THREADPOOL = """ThreadPool (external/threadpool/ThreadPool.h) - zlib
Il file dichiara solo "SPDX-License-Identifier: zlib"; e' ThreadPool di
https://github.com/progschj/ThreadPool, di cui questo e' il file COPYING.

Copyright (c) 2012 Jakob Progsch, Vaclav Zeman

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

   1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.

   2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.

   3. This notice may not be removed or altered from any source
   distribution.
"""


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    src, out = Path(argv[0]), Path(argv[1])
    header = src / "external" / "threadpool" / "ThreadPool.h"
    if "zlib" not in header.read_text(encoding="utf-8", errors="replace")[:300]:
        print(f"{header}: la licenza non e' piu' zlib, controlla THREADPOOL")
        return 1
    parti = ["Licenze di libsfizz, il motore SFZ interno di SoundText: sfizioso\n"
             "(https://github.com/rullopat/sfizioso) e le librerie che contiene.\n"]
    for nome, licenza, percorso in COMPONENTI:
        testo = (src / percorso).read_text(encoding="utf-8", errors="replace").strip()
        titolo = f"{nome} - {licenza}" if licenza else nome
        parti.append(f"{'=' * 72}\n{titolo}\n({percorso})\n{'=' * 72}\n\n{testo}\n")
    parti.append(f"{'=' * 72}\n{THREADPOOL}")
    out.write_text("\n".join(parti), encoding="utf-8")
    print(f"{out}: {len(COMPONENTI) + 1} licenze")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
