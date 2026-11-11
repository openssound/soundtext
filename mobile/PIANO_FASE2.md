# SoundText Mobile, fase 2: piano a tappe

La fase 2 parte l'11 novembre 2026, sul ramo `mobile-prototipo`, dopo la fase 1 (vedi `PIANO_FASE1.md`). Le prove della fase 1 sul telefono sono ancora da fare.

Obiettivo del documento di progetto per la fase 2:

- **Crea**: giro, basso, batteria, accompagnamento;
- **Struttura** a box;
- **funzioni sui pattern** con anteprima;
- **dettatura**.

Criteri di accettazione:

- i generatori danno gli stessi risultati di SoundText con gli stessi parametri e lo stesso seme;
- da un giro di 4 accordi a una base completa in meno di un minuto;
- dettatura: un giro di 8 accordi e una melodia di 2 battute su griglia fissa, dettati in italiano da 3 persone, entrano corretti almeno al 90% senza ritocchi;
- l'interprete della dettatura ha test automatici per ogni riga della tabella e per gli errori tipici del riconoscimento, nelle quattro lingue;
- dettatura e lettura del risultato funzionano con VoiceOver e TalkBack.

## Tappe

| # | Tappa | Contenuto | Fatto quando |
| --- | --- | --- | --- |
| 1 | **Generatori nel motore** | Giro armonico, batteria, basso e accompagnamento nel worker, con i generatori di SoundText | Stessi parametri e stesso seme, stesso testo delle finestre «Genera …» di SoundText |
| 2 | **Schermata Crea** | Una scheda per generatore (stile, tonalità, intensità, battute), anteprima che suona a ogni modifica, «Aggiungi al brano» | Da un giro di 4 accordi a una base completa in meno di un minuto |
| 3 | **Struttura** | Le sezioni (box) in verticale, le tracce in colonne; un tocco apre il box nel Testo; trascinare, duplicare, ripetere | Si costruisce un brano a sezioni senza scrivere le intestazioni dei box |
| 4 | **Funzioni sui pattern con anteprima** | Ascolto e piccola partitura di `%Tema.invert.retro` prima di inserirlo (`core/transform_preview.py`) | L'anteprima coincide con quello che suona dopo l'inserimento |
| 5 | **Interprete della dettatura** | Modulo Python: frase riconosciuta → testo ST, nelle quattro lingue, con le correzioni degli errori tipici del riconoscimento | Test per ogni riga della tabella del documento e per gli errori tipici |
| 6 | **Dettatura nell'app** | Microfono nella barra musicale, trascrizione e testo ST da confermare, comandi a voce, avviso sulla privacy, lettura con TalkBack e VoiceOver | Prova con 3 persone: almeno il 90% corretto |
| 7 | **Chiusura** | Prove sul telefono e di accessibilità, tabella dei criteri | I criteri della fase 2 |

Da decidere prima della tappa 6: il riconoscimento vocale. La Web Speech API del browser funziona su Chrome per Android e su Safari per iPhone, ma manda l'audio a Google o Apple e non funziona senza rete. Un modello locale (Whisper in WebAssembly) pesa 40–75 MB.

## Stato

**Tappa 1, fatta (11 novembre 2026).**

- **`engine.generate(testo, tipo, opzioni)`** in `mobile/engine.py`: giro armonico (`progression`), batteria (`drums`), basso (`bass`), accompagnamento (`comping`). Restituisce il testo e il seme usato; senza un seme ne sceglie uno.
  - Usa i generatori di SoundText (`core/rhythm_generate.py`, `core/performance_style.py`), con i parametri e i valori predefiniti delle finestre «Genera …» (`gui/rhythm_generate_dialog.py`). Queste finestre usano Qt, quindi nel motore la loro logica è riscritta: il programma per computer non cambia.
  - Supporta stile, tonalità, battute, variabilità (35%), intensità, cadenza o finale, fill, ottava, «Variazione ogni N accordi», la traccia degli accordi da seguire, la cassa da seguire, «Esecuzione dello strumento», «Rivolti vicini» e «Lascia spazio alle altre parti».
- **`engine.generator_choices(testo)`**: gli stili di ogni generatore (quelli della batteria secondo la metrica del brano), le tonalità e le intensità. Le etichette leggibili arrivano con la schermata Crea.
- **Errori leggibili e tradotti**, per esempio quando nel brano non ci sono accordi da seguire.
- **Nel worker** i comandi `generate` e `generator_choices`. In Pyodide ogni generatore risponde in 3–10 ms (Chrome sul portatile).
- **Test, `tests/test_mobile_generators.py` (44 casi):**
  - apre le finestre «Genera giro armonico», «Genera batteria», «Genera basso» e «Genera accompagnamento» di SoundText senza schermo;
  - le imposta come farebbe l'utente (stile, tonalità, intensità, cadenza, finale, esecuzione, cassa);
  - controlla che il testo dell'anteprima sia identico a quello del motore, con tre semi diversi.
- **Nel browser:** gli stessi testi generati in Pyodide hanno la stessa impronta SHA-256 di quelli del motore sul computer.
- **Bundle:** 23 moduli di `core/`; `rhythm_generate` e `performance_style` sono fra i moduli controllati per PySide6 e per numpy.

Non portati nell'app (servono tracce audio o configurazioni del computer):

- la batteria che segue il groove di una traccia audio;
- gli accordi riconosciuti da una traccia audio;
- gli stili personali (★);
- la rigenerazione di singole battute.

Riff e melodie (strumenti monofonici) e la melodia dal testo cantato possono arrivare con la schermata Crea, se servono.
