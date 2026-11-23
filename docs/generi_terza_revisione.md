# Generi, terza revisione: batterie, fraseggio, forma

Documento per chi sviluppa. Approfondisce tre punti per rendere più riconoscibili i generi di «Un brano in 60 secondi». Vale anche per «Arrangia il brano» e Crea dove usano lo stesso motore.

1. Una batteria diversa per genere.
2. Il fraseggio della melodia: abbellimenti, bend, terze e seste parallele.
3. La forma del brano: parti diverse fra strofa e ritornello, stacchi, finali propri del genere.

Il punto di partenza è il commit che chiude la seconda revisione. Lì ogni genere ha già i suoi strumenti, la sua scala (`_GENRE_SCALE`), lo swing (`_GENRE_SWING`), le note di avvicinamento (`_GENRE_FIGURE`) e gli effetti (`_GENRE_FX`), tutti in `core/quicksong.py`.

Regole comuni ai tre punti:
- Ogni scelta è una tabella per genere in `core/quicksong.py`, accanto a quelle che ci sono già. I generi che non compaiono restano come sono.
- Tutto passa dal testo del brano. Quello che non si può scrivere nel testo non arriva al telefono, al MIDI esportato, né a chi riapre il file.
- A variabilità 0 il risultato non dipende dal seme, come oggi (`random.Random(seed if free else 0)` in `core/melody_generate.py`).
- Dopo ogni modifica al motore vanno rifatti il bundle (`mobile/build.py`) e la versione della cache (`mobile/sw.js`).

## Stato: fatto, con queste differenze dalla proposta

- **Kit:** fatto con la strada (a), cioè `Traccia Drums [BatteriaSpazzole]:`. I nomi dei kit sono tradotti: BatteriaSpazzole, BatteriaJazz, BatteriaSala, BatteriaElettronica, BatteriaPotente, BatteriaOrchestra. L'opzione `kit=False` li toglie. Il render con FluidSynth (FluidR3 e TimGM6mb) dà un suono diverso per ogni kit e nessun silenzio. Non ancora ascoltati sul telefono.
- **Melodia nella strofa:** suona in tutti i brani con almeno tre sezioni, con lo stile della strofa più rado e a intensità leggera (`_VERSE_MELODY_STYLE`). L'opzione `verse_melody=False` la toglie. La soglia complessiva del test sulle note dei tempi forti (`tests/test_generator_quality.py`) scende da 0,90 a 0,85: nella strofa l'accompagnamento leggero lascia fuori settime e quinte che la melodia suona.
- **Entrate per genere:** fatte come proposte (`_GENRE_ENTER`).
- **Break:** fatti per funk, soul, rock, punk (colpo d'insieme), reggae (drop di due battute), jazz e swing (fill della batteria prima dell'assolo). Le forme AABA del jazz non hanno assolo, quindi lì il break non c'è. L'opzione `breaks=False` li toglie.
- **Finali:**
  - Rallentando di partenza per valzer e ballate, sfumato per bossa, lo-fi ed elettronica (solo dai 45 secondi in su, mai nei loop).
  - Ultimo accordo con la sesta per jazz e swing, la settima per blues e rock'n'roll, la nona per la bossa. È scritto nella voicing dell'accompagnamento, perché nel testo finale non c'è una traccia di accordi.
  - I tre colpi finali per la marcia.
- **Fraseggio:**
  - Acciaccature: sopra per samba, balcanico, valzer e ballate; sotto per il country.
  - Bend alla blues: blues, rock'n'roll, rock e soul, solo sugli strumenti di `BENDABLE` in `core/quicksong.py`.
  - Seconda voce automatica: terze o seste in ogni ritornello, solo quando c'è lo sviluppo del tema, cioè almeno due ritornelli e un finale.
  - L'opzione `figures=False` toglie le figure, `second_voice=False` la seconda voce.
- **Correzione collaterale:** il compattatore in battute (`core/compact_text.py`) e la lettura dei testi generati (`_generated_timeline`) ora contano gli abbellimenti come durata zero e gli slide con la somma dei loro tratti.
- **Non fatto:** le caselle nei dialoghi del computer e del telefono per le nuove opzioni; per ora si usano dal motore.

---

## 1. Una batteria per genere

### Cosa c'è oggi

Tutti i generi suonano con il kit standard (programma 0 sul canale 10). Il kit si può cambiare solo da Gestione strumenti, come preferenza dell'utente per uno strumento (`core/settings.py`, `get_drum_kit_override`). Quella preferenza vale per tutti i brani e non è scritta nel file.

### Si può già fare senza toccare il linguaggio

Nella revisione precedente avevo detto che serviva una modifica al linguaggio. Non è così. Il formato dei file ha già il blocco `Strumento Nome:` (`st_language/stfile.py`, `_parse_instrument_body`), che definisce uno strumento con il suo programma e dice se è una percussione:

```
Strumento Spazzole:
  program=40 percussione=si

Traccia Batteria [Spazzole]:
  8: kick hihat snare hihat ...
```

L'ho provato con `core.midi_export.export_project_to_midi`. Sul canale 10 il MIDI contiene `control_change control=0 value=120` (il banco delle batterie GM2), poi `program_change program=40` e poi le note. Il kit quindi arriva al MIDI.

I kit General MIDI 2 sono elencati in `st_language/instruments.py` (`GM_DRUM_KITS`):

| Programma | Kit |
|---|---|
| 0 | Standard |
| 8 | Room |
| 16 | Power |
| 24 | Electronic |
| 25 | TR-808 |
| 32 | Jazz |
| 40 | Brush (spazzole) |
| 48 | Orchestra |

La «Base di suoni» del telefono ha tutti questi kit (`mobile/tools/pacchetti/base.json`, chiave `batterie`: 0, 8, 16, 24, 25, 32, 40, 48). Il pacchetto elettronico ha il suo Electronic Kit. TimGM6mb, il suono incluso nell'app, ha probabilmente solo il kit standard: senza la base, il telefono dovrebbe ripiegare sul kit 0. Va verificato a orecchio.

### Proposta

Una tabella in `core/quicksong.py`:

```python
# il kit di batteria per genere (programma GM2 sul canale 10): si scrive come «Strumento <Nome>: program=N percussione=si»
_GENRE_KIT = {
    "jazz": ("Spazzole", 40), "swing": ("Jazz", 32), "bossa": ("Spazzole", 40), "ballata": ("Sala", 8),
    "ballata68": ("Sala", 8), "valzer": ("Sala", 8), "lofi": ("Elettronica", 24), "elettronica": ("Elettronica", 24),
    "disco": ("Elettronica", 24), "rock": ("Potente", 16), "metal": ("Potente", 16), "punk": ("Potente", 16),
    "marcia": ("Orchestra", 48), "orchestrale": ("Orchestra", 48),
}
```

Valori da confermare all'ascolto:
- **Lo-fi:** il kit TR-808 (25) è un'alternativa plausibile all'Electronic.
- **Soul e funk:** restano sul kit standard, che è già quello giusto.

In `quick_song`, quando la batteria suona e il genere è nella tabella:
1. Aggiungere il blocco `Strumento <Nome>:` all'intestazione del brano, una volta sola.
2. Scrivere la traccia come `Traccia Batteria [<Nome>]:` invece di `Drums:`.

Il nome dello strumento finisce nel testo che l'utente vede, quindi va tradotto con `tr()`. Deve però restare un identificatore valido: `\w+`, senza spazi.

### Cosa controllare

- **Nome della traccia.** Oggi il codice cerca la batteria per nome («Drums») in più punti: la riga «Suoni:» e i pacchetti in `mobile/app/fonts.js`, il mixer, la lettura vocale in `tests/test_mobile_speech.py`, la «cassa da seguire» nel generatore di basso. Due strade:
  - **(a) Più sicura:** tenere il nome `Drums` e cambiare solo lo strumento, cioè `Traccia Drums [Spazzole]:`. Il parser la accetta: la traccia si chiama `Drums`, ha lo strumento `Spazzole` con `gm_program` 40 ed è una percussione. Resta da verificare che i punti che cercano «Drums» non leggano anche lo strumento predefinito con quel nome.
  - **(b) Più leggibile:** chiamare la traccia «Batteria». Richiede di cercare tutti i punti che riconoscono la batteria per nome e farli lavorare su `instrument.is_percussion`.

  Consiglio la (a).
- **Telefono, SoundFont assegnati alle tracce.** Quando una traccia ha un SoundFont diverso dal predefinito, `fontBanks()` in `mobile/app/fonts.js` riscrive il banco della traccia nel MIDI. Va verificato che su una traccia di percussioni non sovrascriva il banco 128 del kit con quello del pacchetto. Il caso da provare: un brano jazz con il pacchetto acustico e il kit spazzole, che stanno in due SoundFont diversi.
- **Kit mancante.** Se il SoundFont in uso non ha il kit chiesto, FluidSynth di solito ripiega sul kit 0 dello stesso banco. Va verificato sia sul computer sia sul telefono con il solo TimGM6mb, perché c'è il rischio di silenzio.
- **Interazione con Gestione strumenti.** La preferenza dell'utente è legata al nome dello strumento («Drums»). Con uno strumento definito nel file, la preferenza non si applica più a quella traccia. Va bene così, perché il brano dichiara il suo kit, ma va scritto nella guida.
- **Arrangia e Crea.** Si potrebbe proporre il kit del genere anche lì. Però non conoscono il genere del brano, tranne nei brani nati da «Un brano in 60 secondi», che hanno il commento `// quick: {...}`. Per ora lasciarli fuori.

### Test

- Per ogni genere in `_GENRE_KIT`: il testo contiene il blocco `Strumento` con il programma giusto e `percussione=si`. La traccia della batteria si interpreta con quello strumento (`is_percussion` vero, `gm_program` come in tabella).
- Il MIDI esportato di un brano jazz ha `program_change channel=9 program=40`.
- Un genere fuori tabella (per esempio funk) non ha il blocco e la sua batteria resta `Drums:`.
- `tests/test_mobile_speech.py` e i test del mixer passano senza adattamenti. Se servono adattamenti, è segno che la scelta del nome della traccia (a o b) va rivista.

---

## 2. Il fraseggio della melodia

### Cosa c'è oggi

La melodia nasce in `core/melody_generate.py`, funzione `generate_phrase_melody`. È una lista di note `(inizio, durata, nota, frase B?)` su una griglia di ottavi, scritta poi da `_write` come testo `8: ...`. Sopra la melodia di base ci sono già due passaggi che la modificano:
- `_add_pickups`: anacrusi a inizio frase;
- `_add_approaches`: note di avvicinamento cromatiche, per genere (`FIGURES`, con la tabella `_GENRE_FIGURE` in `core/quicksong.py`).

Le nuove figure vanno costruite allo stesso modo: un passaggio dopo `_add_pickups` e prima di `_apply_repeats`. Così una sezione che ritorna ripete anche le sue figure.

Il limite attuale è che la lista non ha posto per abbellimenti né per curve di intonazione. Va estesa, per esempio con un quinto campo facoltativo `ornament`, e `_write` deve imparare a scriverlo.

### Cosa offre il linguaggio

- **Abbellimenti:** `d'g` (acciaccatura) e `d'G` (appoggiatura), subito prima della nota a cui appartengono. Non occupano tempo scritto (`st_language/notation.py`, `GRACE_VALUES`). Non possono avere una legatura di valore e devono stare subito prima della loro nota.
- **Slide e bend:** `c*4>d*4` è un portamento, e `c*4>d*4>c*4` un bend con rilascio. Le durate dei segmenti si scrivono con il moltiplicatore (`2c*4>3d*4`). La sintassi è in `notation.py` (`RE_SLIDE`, `_parse_slide_points`).
- **Pitch bend continuo:** la parola `bend=` vale da -24 a 24 semitoni (`CONTROL_RANGES`). Serve per curve libere, ma lo slide è più semplice da generare.

Da verificare prima di scrivere codice: come la griglia `8:` scrive l'ottava in una catena di slide (`c*4` contro `c`), e se lo slide funziona in tutte le uscite, cioè MIDI, partitura (`musicxml.py`) e lettura vocale. Conviene farsi dare il testo esatto dal parser su un esempio, per esempio `parse_track_text("8: 2e*4>2g*4", {})`.

### Proposta: tre figure nuove

Si aggiungono a `FIGURES` e i generi le scelgono da `_GENRE_FIGURE`. La tabella va trasformata in un elenco per genere, perché un genere può avere più figure. Ogni figura ha la sua probabilità e il suo generatore casuale con seme derivato (`f"{seed}/grace"` e così via), così aggiungerne una non cambia le altre.

**a) Acciaccatura (`grace`)**
- **Dove:** sulle note lunghe (almeno un tempo) che cadono sul tempo forte e sono note dell'accordo.
- **Cosa:** un'acciaccatura un grado sopra, presa dalla scala, o un semitono sotto.
- **Generi:** country e bluegrass (sotto), balcanico (sopra, dalla frigia dominante), valzer e ballate (sopra, raramente), samba.
- **Probabilità di partenza:** 0,15 per nota candidata.

**b) Bend alla blues (`blue_bend`)**
- **Dove:** sulla terza minore o sulla settima minore di una nota lunga.
- **Cosa:** la nota parte un semitono sotto e sale con uno slide nel primo ottavo, per esempio `eb*4>e*4` sulla terza di Do. In alternativa, una nota tenuta che sale e torna (`g>ab>g`).
- **Generi:** blues, rock'n'roll, rock, soul.
- **Strumenti:** solo quelli che possono piegare la nota: chitarre, sax, armonica, voce, organo con leva. Pianoforte, marimba e vibrafono no. Serve un elenco `BENDABLE` in `core/instruments.py`, o un attributo del profilo.
- **Probabilità:** 0,25 per nota candidata.

**c) Terze e seste parallele (`parallel`)**
- **Cosa c'è già:** la seconda voce, che si chiede con `options["second_voice"]` e si scrive come pattern `.thirds` (`_HARM_FOR` in `core/quicksong.py`). Oggi parte solo su richiesta e solo nei ritornelli sviluppati.
- **Proposta:** renderla automatica per genere, in una tabella `_GENRE_SECOND_VOICE`:
  - **Terze:** pop e ballata, nel ritornello.
  - **Seste:** valzer e ballata 6/8, nel ritornello e nel ponte.
  - **Terze:** bossa e cha cha, una frase su due.
  - **Terze:** balcanico.
- **Regola sul registro:** la seconda voce sta sotto la melodia, a una terza o sesta della scala, e non scende sotto l'accompagnamento. Usare `part_registers` e `fit_register` di `core/rhythm_generate.py`, già usati per lasciare spazio alle parti.

### Cosa controllare

- **Test di qualità (`tests/test_generator_quality.py`).**
  - *Note sui tempi forti:* almeno il 70% deve appartenere all'accordo. Le acciaccature non occupano tempo, quindi non dovrebbero contare, ma va verificato come il test legge gli eventi `grace`. Un bend che parte fuori dall'accordo sul tempo forte rischia invece di farlo fallire: in quel caso la nota di partenza va sul levare, oppure il test deve contare la nota d'arrivo.
  - *Registri:* la seconda voce automatica aggiunge una parte. Il test che controlla che i registri non si sovrappongano deve includerla.
- **Ripetizioni:** le figure vanno aggiunte prima di `_apply_repeats`, altrimenti un ritornello che torna perde le sue.
- **Lettura vocale e partitura:** un abbellimento o uno slide non devono rompere `speak_at` (telefono) né l'esportazione MusicXML. Serve un test per ciascuno.
- **Scelta dell'utente:** oggi non c'è un comando per togliere le figure. Proposta: un'opzione `figures` (sì o no) nelle opzioni di `quick_song`, con una casella nel dialogo del computer e del telefono, come lo swing.

### Test

- Per ogni genere con una figura, su sei semi a variabilità 0, la figura compare almeno tre volte. Il test va scritto come `test_jazz_and_blues_melodies_have_chromatic_approach_notes` in `tests/test_quicksong.py`.
- Nessuna figura su uno strumento che non la può suonare: niente bend sul pianoforte.
- I brani restano validi (`validate_track_text`) ed esportabili in MIDI e MusicXML.
- La seconda voce automatica è entro l'estensione del suo strumento e sotto la melodia.

---

## 3. La forma del brano

### Cosa c'è oggi

- **Sezioni:** `_form_sections` costruisce le sezioni (nome, ruolo, battute) per le forme `loop`, `canzone`, `aaba`, `blues` e `ponte`, con una scala di lunghezze. I ruoli sono intro, verse, chorus, bridge, solo, end, loop e fade.
- **Quali parti suonano:** lo decide `_ENTER`, uguale per tutti i generi. In particolare:
  - **La melodia suona solo in ritornello, assolo, finale e loop.** Nella strofa non c'è melodia: si sentono solo accompagnamento, basso e batteria. È la differenza più evidente da affrontare.
  - `comp2`, i fiati e il pad entrano dal ritornello.
- **Intensità per ruolo:** strofa leggera o normale, ritornello pieno (`intensity` in `quick_song`).
- **Progressioni:** la strofa usa la prima progressione del genere, il ritornello la seconda, il ponte la terza.
- **Finali:** cadenza, rallentando o sfumato (`ENDINGS`).
- **Batteria:** fill ogni 4 o 8 battute (`drum_fill`, `_BUSY_DRUM_GENRES`).
- **Arrangia** (`core/arrange.py`) ha già due pause che «Un brano in 60 secondi» non usa:
  - **Break:** colpo d'insieme e silenzio (`_break_drums`, `_first_hit_only`).
  - **Stop:** la sezione tace.

### Proposta

**a) La melodia anche nella strofa.**
Aggiungere `verse` alle sezioni della melodia in `_ENTER`, ma con una melodia diversa da quella del ritornello:
- **Strofa:** stile `cantabile` o `ballata`, più basso e con meno note: `b_lift` negativo e densità -1 rispetto al ritornello.
- **Ritornello:** lo stile di oggi, che è il culmine.

`generate_phrase_melody` supporta già l'intensità per frase e il sollevamento della frase B. Basta passare stile e intensità diversi per sezione. In alternativa la strofa può essere suonata da un altro strumento, per esempio il sax nella strofa e la tromba nel ritornello del jazz.

Rischio: con melodia anche nella strofa, un brano di 30 secondi ha melodia quasi sempre. I brani brevissimi (`short`, fino a 20 secondi) non vanno toccati.

**b) Entrate e uscite per genere.**
Rendere `_ENTER` modificabile per genere con una tabella di eccezioni, `_GENRE_ENTER = {genere: {parte: ruoli}}`:
- **Jazz e swing:** il pianoforte tace nell'assolo, e il basso walking con la batteria accompagna l'assolo del fiato. La batteria tace nell'intro, dove pianoforte e basso suonano soli.
- **Reggae:** nella strofa l'organo (`organ_bubble`) suona già, non solo dal ritornello.
- **Funk:** i fiati entrano con colpi brevi anche nella strofa (`horn` in `verse`, a intensità leggera).
- **Ballata:** strofa con solo pianoforte e voce, poi basso e batteria dal ritornello (batteria non in `verse`).
- **Elettronica:** l'intro è solo batteria, poi entra il basso, e la melodia arriva al secondo loop (costruzione per strati).

**c) Stacchi e break.**
Portare in «Un brano in 60 secondi» il break che Arrangia sa già fare (`_break_drums`, `_first_hit_only`). Una battuta di break prima dell'ultimo ritornello, o alla fine del ponte, nei generi che lo usano:
- **Funk e soul:** stacco d'insieme sul primo tempo, poi silenzio fino al ritornello.
- **Jazz e swing:** la battuta di break prima dell'assolo, con un fill solo della batteria.
- **Rock e punk:** silenzio di una battuta o di mezza battuta prima dell'ultimo ritornello.
- **Reggae:** «drop», in cui basso e batteria tacciono per due battute e resta solo lo skank.

Tecnicamente: un ruolo nuovo `break` di una battuta, inserito da `_form_sections` dove la tabella del genere lo chiede (`_GENRE_BREAK = {genere: ("before_last_chorus", "end_of_bridge")}`). Le parti lo realizzano con le funzioni di `core/arrange.py`, da spostare in un modulo condiviso o importare.

**d) Finali propri del genere.**
Oggi i finali sono tre e uguali per tutti. Proposte:
- **Blues e rock'n'roll:** il turnaround finale (V7 che risolve su I7), con la figura cromatica che scende sulla tonica, più un colpo finale sul I7.
- **Jazz:** finale su accordo con la sesta o la nona (I6, Imaj9) tenuto, con un colpo di piatto.
- **Marcia:** cadenza piena V-I con tre colpi finali ravvicinati (il «ta-ta-tà»).
- **Valzer:** rallentando sulle ultime due battute e accordo tenuto sul primo tempo.
- **Bossa:** chiusura sfumata sulla figura del basso, senza colpo finale.
- **Elettronica e lo-fi:** sfumato, già scelto per loro in parte.

Tecnicamente: un parametro `ending_style` per genere, letto da chi scrive l'ultima sezione. Oggi il finale passa come `ending` ai generatori di basso, batteria e accompagnamento, e va esteso con lo stile.

### Cosa controllare

- **Durata:** il motore sceglie la forma più vicina alla durata chiesta. Aggiungere battute di break cambia la durata, e va mantenuto il vincolo dei test sulla durata (`_valid` in `tests/test_quicksong.py`).
- **Loop e telefono:** le sezioni del brano sono quelle che il telefono mostra nella struttura e che Arrangia rilegge (`all_sections`). Una sezione `break` deve avere un nome tradotto e un ruolo che `section_intensity` riconosce.
- **«Un'altra»:** con forme più varie, «Un'altra» deve continuare a cambiare solo le parti libere, non la struttura scelta. Verificare `c["seeds"]` e `_SWAP_COMP`.
- **Sviluppo del tema** (`develop`, ultimo ritornello un'ottava sopra): deve continuare a funzionare con la melodia anche nella strofa.

### Test

- Per ogni genere con eccezioni in `_GENRE_ENTER`, le parti suonano e tacciono nelle sezioni attese. Si controllano le tracce e gli inizi dei box.
- Con almeno due ritornelli, i generi con break hanno una battuta di break prima dell'ultimo. La batteria del break ha il colpo d'insieme e poi pause.
- La melodia della strofa è più bassa o più rada di quella del ritornello, in media su sei semi.
- I finali per genere: l'ultimo accordo del blues è I7, la marcia finisce con tre attacchi ravvicinati, e così via.
- I test di qualità e di durata passano per tutti i generi.

---

## Ordine consigliato

1. **Batterie (punto 1).** Poco codice e un effetto subito udibile. Prima vanno provati a orecchio due kit (spazzole e potente) sul computer e sul telefono con la base.
2. **Forma: melodia nella strofa ed entrate per genere (punti 3a e 3b).** Cambiano la percezione del brano più di ogni dettaglio melodico.
3. **Stacchi e finali (punti 3c e 3d).**
4. **Fraseggio (punto 2).** Prima la seconda voce automatica, che usa codice già esistente, poi acciaccature e bend.

Ogni passo va chiuso da un giro d'ascolto: almeno un brano per genere toccato, con il seme annotato, così un difetto si può riprodurre.
