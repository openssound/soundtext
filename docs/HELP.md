# Guida utente — SoundText

## Indice per argomento

Cerca qui l'argomento che ti interessa e vai alla sezione indicata (i numeri sono quelli dei titoli di questa guida).

| Argomento | Sezione |
| --- | --- |
| [La finestra del programma, barra dei comandi, viste](#1.0) | [1.0](#1.0) |
| [Cercare un comando (Ctrl+K) e scorciatoie da tastiera](#1.0bis) | [1.0bis](#1.0bis) |
| [Annulla / Ripeti](#1.2) | [1.2](#1.2) |
| [Salvataggio automatico e recupero](#1.2bis) | [1.2bis](#1.2bis) |
| [Lingua dell'interfaccia](#1.3) | [1.3](#1.3) |
| [Scrivere note, accordi, pause, durate, ottave, diesis e bemolle](#2) | [2](#2) |
| [Voicing degli accordi e accordi con basso alternativo (slash)](#2.8) | [2.8](#2.8), [2.9](#2.9) |
| [Ripetizioni e terzine / quintine](#2.1) | [2.1](#2.1), [2.1bis](#2.1bis) |
| [Slide (pitch bend) e pedale del sustain](#2.3) | [2.3](#2.3), [2.4](#2.4) |
| [Dinamiche, crescendo e diminuendo](#2.5) | [2.5](#2.5) |
| [Cambi di tempo (accelerando, rallentando) e di metrica](#2.6) | [2.6](#2.6), [2.7](#2.7) |
| [Tonalità del brano e ottave relative](#2.7bis) | [2.7bis](#2.7bis), [2.18](#2.18) |
| [Controlli di battuta (|) e commenti (//)](#2.10) | [2.10](#2.10) |
| [Più voci nella stessa traccia e testo cantato](#2.12) | [2.12](#2.12), [2.13](#2.13) |
| [Automazioni (volume, pan... che cambiano nel tempo)](#2.15) | [2.15](#2.15) |
| [Legature, swing, ritornelli, segni e indicazioni](#2.16) | [2.16](#2.16), [2.17](#2.17) |
| [Micro-tempo, accordatura, molte tracce, MTXT](#2.19) | [2.19](#2.19) |
| [Ancore di battuta (bar=N)](#2.20) | [2.20](#2.20) |
| [Trasposizione (transpose=, %Nome+N)](#2.21) | [2.21](#2.21) |
| [reset:, levare, versione del file (ST 2.6)](#2.22) | [2.22](#2.22) |
| [Pattern (%Nome): riutilizzare e riorganizzare parti](#4) | [4](#4) |
| [Libreria MIDI (&"Nome") e cartella dei brani songs/](#5) | [5](#5), [5bis](#5bis) |
| [Percussioni e batteria scritta a mano](#6) | [6](#6) |
| [Tracce e strumenti, strumenti personalizzati](#7) | [7](#7) |
| [Mixer: volumi, pan, mute, solo e volume master](#8) | [8](#8), [8.1](#8.1), [8.2](#8.2) |
| [Riverbero e chorus del sintetizzatore](#8.3) | [8.3](#8.3) |
| [Effetti: EQ, compressore, delay, riverbero, noise gate, loop di calibrazione](#8.4) | [8.4](#8.4) |
| [Amplificatore per chitarra, distorsione, casse e file IR](#8.4) | [8.4](#8.4) |
| [Profili NAM (amplificatori e pedali veri), dove scaricarli](#8.4) | [8.4](#8.4) |
| [Mastering: effetti sul master e limiter](#8.5) | [8.5](#8.5) |
| [Suoni da studio con programmi esterni (re-amping)](#8.6) | [8.6](#8.6) |
| [Plugin VST3 e LV2, strumento SFZ interno](#8.7) | [8.7](#8.7) |
| [Vista Struttura a box: strofe, ritornelli, spostare e copiare parti](#8bis) | [8bis](#8bis) |
| [Congelare gli accordi, scegliere il voicing, autocompletamento](#9) | [9](#9), [9.1](#9.1), [9.2](#9.2) |
| [Generare batteria, basso, accompagnamento e riff senza IA](#9bis) | [9bis](#9bis) |
| [Stili personali (imparare dai tuoi brani) e melodie a frasi](#9bis.1) | [9bis.1](#9bis.1), [9bis.2](#9bis.2) |
| [Importare ed esportare MIDI](#10) | [10](#10) |
| [MusicXML e ABC: esportare e importare partiture](#10.1) | [10.1](#10.1), [10.2](#10.2), [10.3](#10.3) |
| [Vedere e stampare la partitura](#10.1bis) | [10.1bis](#10.1bis) |
| [Importazione audio: da voce, microfono o file a note](#10bis) | [10bis](#10bis) |
| [Suonare con la tastiera del computer o una tastiera MIDI](#10ter) | [10ter](#10ter) |
| [Tracce audio: registrare voce e chitarra, esportare](#10quater) | [10quater](#10quater) |
| [Salvare il progetto (.st)](#11) | [11](#11) |
| [Riproduzione, loop A-B, saltare a un punto](#12) | [12](#12) |
| [Scegliere il SoundFont, SoundFont per singolo strumento](#12.3) | [12.3](#12.3), [12.4](#12.4) |
| [Metronomo e umanizzazione](#12.5) | [12.5](#12.5), [12.6](#12.6) |
| [File di log (se qualcosa non funziona)](#13.1) | [13.1](#13.1) |
| [Tecnologie, ringraziamenti, licenze](#14) | [14](#14) |
| [Installazione su Linux, Windows e macOS (in fondo alla guida)](#inst) | [↓](#inst) |

---

## 0. Terminologia

- **SoundText Language**: il linguaggio testuale con cui si scrive la
  partitura (note, accordi, percussioni, pattern, comandi di stato...).
- **ST-Syntax**: la grammatica formale del SoundText Language — le regole
  sintattiche descritte nella sezione 2.
- **SoundText Engine**: il motore che risolve un accordo astratto (es.
  `Cmaj7`) in note MIDI concrete, in base allo strumento della traccia
  (spesso chiamato anche "motore di voicing" in questa guida).
- **.st**: estensione dei file progetto.

## 1. Concetti di base

Il programma separa tre livelli: **intenzione astratta** (note e accordi
scritti in SoundText Language), **voicing concreto** (il SoundText Engine,
dipendente dallo strumento) e **playback** (motore MIDI). Ogni traccia e'
associata a uno strumento e contiene una sequenza di *token* separati da
spazi, conformi alla ST-Syntax.

### 1.0 La finestra

- **Barra dei comandi**, da sinistra: il **trasporto** (torna all'inizio,
  Play/Pausa, Stop, **●** Registra nella traccia audio selezionata, loop
  A-B, metronomo), il blocco **Brano** (tempo, metrica, tonalita'), la
  scelta della vista **Struttura / Testo** e il volume **Master**. Passando il mouse su un pulsante compare
  a cosa serve e la sua scorciatoia.
- **Barra di avanzamento**, a tutta larghezza sotto la barra dei comandi:
  tempo trascorso e durata; clic per saltare in quel punto.
- **Vista Struttura brano** (8bis): le tracce a box, con il mixer nelle
  testate delle righe (8); oppure **vista Testo**: le stesse testate in
  colonna a sinistra e la notazione della traccia selezionata.

### 1.0bis Cerca un comando (Ctrl+K) e scorciatoie

**Cerca un comando**: **Ctrl+K**, oppure la casella "Cerca un comando…" in
alto a destra nella barra dei menu (anche **Aiuto → Cerca un comando...**).
Si scrive cosa si vuole fare ("esporta", "registra", "genera basso",
"metronomo", "tonalita"...), si sceglie con le frecce e si preme Invio. Si
trovano tutte le voci dei menu, comprese quelle di "+ Aggiungi traccia";
accanto a ognuna ci sono il menu in cui si trova e la sua scorciatoia.
Maiuscole e accenti non contano.

**Scorciatoie nella vista Struttura brano** (con il mouse o il fuoco sul
canvas; nell'editor di testo questi tasti servono a scrivere). Un
promemoria e' in fondo a destra nella barra di stato.

| Tasto | Azione |
|---|---|
| Spazio | Play / Pausa del brano (ovunque: F5) |
| Shift+Spazio | ascolta solo il box selezionato |
| R | registra nella traccia audio selezionata (ovunque: Ctrl+R) |
| Canc | elimina il box selezionato |
| Ctrl+D | duplica il box selezionato |
| S | divide la clip audio selezionata nel punto della testina |
| Ctrl+rotellina | zoom orizzontale (resta fermo il punto sotto il mouse) |
| Ctrl+= / Ctrl+- / Ctrl+0 | ingrandisci / riduci / zoom normale (anche da menu Vista) |
| Ctrl+Z / Ctrl+Y | annulla / ripeti |

Le voci corrispondenti stanno anche nei menu **Modifica** (elimina,
duplica, dividi), **Vista** (zoom) e **Playback**.

### 1.1 Evidenziazione sintattica e scorciatoie

L'editor colora automaticamente ogni token secondo il suo tipo: note
(azzurro), accordi (ambra), percussioni (viola), comandi di stato `N:`/`N@`
(verde), riferimenti `%pattern` e `&"midi"` (corallo), blocchi `[...]`
(giallo), pause (grigio). I commenti `//` sono in grigio corsivo, i controlli di
battuta `|` in grigio (in rosso sottolineato se non cadono su una stanghetta,
vedi 2.10); i blocchi di voci `{ ; }` in turchese, il testo cantato in rosa
corsivo, e dentro gruppi e voci ogni token ha il suo colore. I colori riflettono esattamente come il motore
interpreta il testo, quindi sono anche un aiuto per individuare errori a
colpo d'occhio.

Le testate delle tracce hanno inoltre un bordo colorato per famiglia
strumentale (chitarre, bassi, ottoni...), utile per orientarsi rapidamente
con molte tracce.

Scorciatoie da tastiera principali: `Ctrl+N` nuovo progetto, `Ctrl+O` apri,
`Ctrl+S` salva, `Ctrl+Shift+S` salva con nome, `Ctrl+T` aggiungi traccia,
`Ctrl+E` modifica traccia, `Ctrl+Z`/`Ctrl+Y` annulla/ripeti, `F5` play/pausa, `F6` stop,
`Ctrl+[`/`Ctrl+]` inizio/fine loop, `Ctrl+L` loop on/off, `F1` questa guida.

### 1.2 Annulla/Ripeti

**Modifica → Annulla** (`Ctrl+Z`) e **Ripeti** (`Ctrl+Y` o
`Ctrl+Shift+Z`) valgono per **ogni modifica al progetto**, da qualunque
parte arrivi: testo scritto nell'editor, tracce aggiunte, rimosse o
rinominate, mixer (volume, pan, mute, solo, master), tempo, metrica e
tonalità, batteria/basso generati, import MIDI/audio o dalla tastiera in
una traccia, pattern, congelamento degli accordi, riorganizzazione, box
della vista Struttura brano. Annullando si torna anche a vedere la traccia
su cui si stava lavorando.

La digitazione continua nella stessa traccia, o il trascinamento di uno
slider, diventa un unico passo: basta una pausa di un secondo e mezzo per
iniziarne uno nuovo. La cronologia si azzera aprendo o creando un
progetto. Nei dialoghi (modifica di un box, pattern...) il testo ha invece
il proprio Annulla, indipendente.

### 1.2bis Salvataggio automatico e recupero

Mentre il progetto ha **modifiche non salvate**, SoundText ne scrive una
**copia di recupero** ogni minuto (solo se nel frattempo è cambiato
qualcosa), nella cartella `recupero/` della configurazione. Il file del
progetto non viene toccato: salvare resta una tua scelta.

- Salvando, aprendo o creando un altro progetto, o chiudendo SoundText
  normalmente (anche scegliendo **Scarta**), la copia viene tolta.
- Se SoundText si chiude male (crash, blocco, computer spento), al
  prossimo avvio chiede se **recuperare** il progetto, indicando l'ora
  della copia e il file originale. **Recupera** lo riapre come progetto
  modificato: **Salva** (`Ctrl+S`) lo scrive sul file originale, oppure
  scegli **Salva con nome**. **Elimina la copia** la cancella, **Decidi
  dopo** la lascia per il prossimo avvio.
- Più finestre di SoundText aperte insieme hanno ciascuna la propria
  copia: una finestra ancora aperta non viene mai proposta per il
  recupero.

Anche il salvataggio normale è "tutto o niente": SoundText scrive prima
un file temporaneo e lo mette al posto del progetto solo alla fine, così
un'interruzione a metà (disco pieno, corrente che manca) non lascia un
file `.st` troncato.

### 1.3 Lingua dell'interfaccia

SoundText parla **italiano, inglese, francese e spagnolo**. La lingua si
sceglie in **Opzioni → Lingua** e vale dal prossimo avvio: SoundText
chiede se riavviarsi subito (se ci sono modifiche non salvate, prima
chiede di salvarle). La prima volta si usa la lingua del sistema, se e'
una delle quattro, altrimenti l'inglese.

Nella lingua scelta sono menu, finestre, messaggi e questa guida. **Non
cambiano** invece la notazione (`c*4`, `Am7`, `kick`...) e le parole del
file `.st` (`Tempo:`, `Traccia`, `Effetti`...), che sono il formato dei
progetti: un brano scritto con l'interfaccia in italiano si apre uguale
con l'interfaccia in inglese, e viceversa.

## 2. ST-Syntax (grammatica del SoundText Language)

| Costrutto | Significato | Esempio |
| --- | --- | --- |
| lettera minuscola a-g | nota melodica | `c` |
| lettera minuscola + `#` (diesis) o `b`/`♭` (bemolle) | nota alterata | `c#`, `eb`, `e♭` |
| `*n` dopo una nota o un accordo | ottava | `c*4`, `Cmaj7*3` |
| `/Nota` dopo un accordo | basso alternativo ("accordo slash") | `C/E` (Do col basso Mi) |
| lettera MAIUSCOLA + suffisso | accordo astratto | `Cmaj7`, `Am`, `G7` |
| `.stile` dopo un accordo | forza un voicing specifico (vedi 2.8) | `Cmaj7.drop2`, `C.power` |
| parola minuscola (36 identificatori percussivi, vedi sezione 5) | evento percussivo | `kick` |
| numero iniziale | moltiplicatore di durata | `2c`, `4Cmaj7` |
| `r` / `Nr` | pausa (1 o N unita' di griglia) | `r`, `3r` |
| `[...]` | eventi/note simultanee | `[c*4 e*4 g*4]`, `[kick hihat]` |
| `N:` | cambia la griglia ritmica corrente | `16:` (sedicesimi) |
| `NT:` / `NQ:` / `NS:` | tuplet: terzine / quintine / settimine (vedi 2.1bis) | `8T:`, `16Q:`, `8S:` |
| `N@` | cambia la velocity corrente (1-127) | `100@` |
| `%Nome` | richiama un pattern | `%Rock1` |
| `&"Nome"` | richiama un file MIDI dalla libreria | `&"Intro"` |
| `N(...)` | gruppo di ripetizione: ripete N volte la sequenza racchiusa | `4(c d e f)` |
| `!` in fondo a nota o accordo | staccato (dimezza la durata udibile) | `c!`, `Cmaj7!` |
| `x` in fondo a nota o accordo | mute/stop (nota molto breve, "stoppata") | `cx`, `Cmaj7x` |
| `_` in fondo a nota o accordo | legato (nota leggermente prolungata) | `c_`, `Cmaj7_` |
| `nota>nota[>nota...]` | slide/portamento (pitch bend continuo tra due o piu' note) | `c*4>d*4`, `c*4>d*4>c*4` |
| `SON` / `SOFF` | pedale sustain: attiva/disattiva per tutto cio' che segue | `SON c*4 SOFF` |
| `tempo=N` | imposta il tempo (BPM) a partire da questo punto | `tempo=120` |
| `>>` dopo `tempo=N` | accelerando fino al prossimo `tempo=N` | `tempo=100 >> c*4 tempo=140` |
| `<<` dopo `tempo=N` | rallentando fino al prossimo `tempo=N` | `tempo=140 << c*4 tempo=80` |
| `pppp@`...`ffff@` | dinamiche classiche, equivalenti a una velocity fissa | `mf@` = `75@` |
| `>>` dopo `N@`/dinamica | crescendo fino al prossimo valore di velocity | `p@ >> c*4 ff@` |
| `<<` dopo `N@`/dinamica | diminuendo fino al prossimo valore di velocity | `110@ << c*4 30@` |
| **\|** | controllo di battuta: qui finisce una battuta (non suona, avvisa se non torna, vedi 2.10) | `c d e f` **\|** `g a b c` **\|** |
| `//` | commento fino a fine riga (ignorato) | `c d e f // strofa` |
| `'N` dopo un token | valore di nota esplicito, senza cambiare griglia (vedi 2.11) | `c'8.` (croma puntata), `[c e g]'2`, `r'4`, `e'8T` |
| `{ ... ; ... }` | voci che partono insieme nella stessa traccia (vedi 2.12) | `{ c*5 d*5 e*5 f*5 ; 4c*4 }` |
| `"..."` | testo cantato: una sillaba per nota, sulle note che precedono (vedi 2.13) | `c d e 2f "Ma- ri- a, sei"` |
| `vol=N` `expr=N` `pan=N` `mod=N` `rev=N` `cho=N` | automazioni: volume, espressione, pan (-1..1), modulazione, mandate di riverbero e chorus (vedi 2.15) | `vol=80`, `pan=-0.5` |
| `>>` dopo un'automazione | rampa continua fino al prossimo valore dello stesso nome; `>>exp`, `>>log`, `>>s` scelgono la curva | `vol=0 >>exp 4c vol=100` |
| `<` / `>` in fondo a una nota | crescendo / diminuendo durante la nota tenuta (forcella) | `2c<`, `c'2>` |
| `~` in fondo a una nota | legatura di valore: la nota continua nella successiva uguale, anche oltre la stanghetta (vedi 2.16) | `2c~ \| 2c` |
| `(` ... `)` in fondo alle note | legatura di portamento: le note in mezzo suonano legate (vedi 2.16) | `c( d e f)` |
| `swing=N` / `swing16=N` | swing delle crome / delle semicrome (50 = diritto, 66 = terzinato) | `swing=62 8: c d e f` |
| `bar=N` | ancora di battuta: porta il cursore all'inizio della battuta N, con i silenzi che servono (vedi 2.20) | `bar=29 c d e f` |
| `transpose=N` | trasposizione: le note, gli accordi e gli slide che seguono suonano N semitoni sopra o sotto (vedi 2.21); `%Nome+N` trasporta un pattern | `transpose=-2 c d e` |
| `\|:` ... `:\|` | ritornello: la parte fra i due segni si suona due volte (vedi 2.17) | `\|: c d e f :\|` |
| `\|1.` `\|2.` `\|\|` | caselle del ritornello: finali diversi per ogni passaggio (vedi 2.17) | `\|1. g a :\| \|2. 4c \|\|` |
| `$segno` in fondo a una nota | accento, corona, trillo, mordente, gruppetto, tenuto, marcato (vedi 2.17) | `c$fermata`, `d$tr`, `e$accent` |
| `$"testo"` | indicazione sopra il pentagramma | `$"rit."`, `$"dolce"` |
| `rel:` / `abs:` | ottave relative (ogni nota va vicino alla precedente) / assolute (vedi 2.18) | `rel: c d e f g a b c` |
| `*+` / `*-` dopo una nota (in `rel:`) | un'ottava sopra / sotto | `rel: g c*+ c*-` |
| `key=K` | le note prendono le alterazioni della tonalita' K (vedi 2.18) | `key=G f` (= fa diesis) |
| `n` dopo una nota | bequadro: toglie l'alterazione della tonalita' | `key=G fn` |

Il carattere `|` e' il **controllo di battuta** (vedi 2.10): non suona e non
sposta nulla, serve solo a dichiarare dove finisce una battuta. Le durate si
accumulano comunque lungo la timeline, quindi le `|` sono facoltative. Nel
file di progetto `.st` il carattere compare anche nell'intestazione di un
box della vista "Struttura brano" (sezione 8bis), per indicarne la
posizione in beat, es. `Box Basso1 "Intro" |4:` — un dettaglio del formato
di salvataggio.

**Rampe e chiusura obbligatoria**: una rampa `>>`/`<<` va sempre richiusa da
un altro comando **dello stesso tipo** (velocity dopo velocity, tempo dopo
tempo) prima che ne arrivi uno dell'altro tipo, o prima della fine della
traccia — altrimenti la validazione segnala un errore esplicito invece di
lasciare la rampa "orfana" (aperta ma senza alcun effetto udibile, un bug
silenzioso difficile da notare solo ascoltando). Un cambio di griglia (`N:`)
in mezzo a una rampa gia' aperta non la chiude ne' la rompe — puo' comparire
liberamente prima della nota/accordo che la chiude.

### Bemolle: `b`, `♭` o `-` (scorciatoia di digitazione)

Il bemolle si può scrivere con la lettera `b` (es. `eb`), col simbolo
musicale reale `♭` (es. `e♭`), o con un trattino `-` (es. `e-`): sono tre
sinonimi perfettamente equivalenti per il parser, sia sulle note sia sulla
fondamentale di un accordo (`Bb7` = `B-7` = `B♭7`). La lettera `b` resta
valida per compatibilità con quanto scritto finora, ma può creare
ambiguità visiva con la lettera nota `b` (Si) — per questo **l'editor
digitando `-` subito dopo una lettera nota lo sostituisce automaticamente
con `♭`** (es. digitando `e` poi `-` compare `e♭`), così a schermo si vede
sempre il simbolo corretto senza dover cercare `♭` sulla tastiera. La
sostituzione scatta solo quando il `-` segue immediatamente una lettera
nota a inizio token (dopo uno spazio, `[`, `(`, `>`, o una cifra di
moltiplicatore): digitare `-` in un altro contesto (es. dopo `snare`)
resta un trattino normale.

### Qualita' di accordo supportate
`(vuoto)`/`maj`, `m`/`min`, `7`, `maj7`, `m7`, `dim`, `dim7`, `aug`,
`sus2`, `sus4`, `6`, `m6`, `9`, `maj9`, `m9`, `mMaj7`, `m7b5`, `add9`,
`7sus4`, `7b9`, `7#9`, `5`, `7alt`, `11`, `13`, `maj13`, `°`, `°7`.

Le ultime sei sono alias o estensioni pensate per la notazione che si
scriverebbe "a naso" leggendo un chart reale:
- **`5`** (es. `E5`): power chord, solo fondamentale+quinta, nessuna terza —
  equivalente a scrivere l'accordo con voicing `.power` (`E.power`), ma
  riconosciuto anche come qualita' a se' stante (es. per l'import MIDI:
  una semplice quinta suonata viene ora riconosciuta come `5`, non piu'
  lasciata come blocco esplicito ambiguo).
- **`°`** / **`°7`** (es. `C°`, `C°7`): alias della notazione classica per
  `dim`/`dim7`, stessi intervalli, stesso voicing.
- **`7alt`** (es. `G7alt`): dominante alterato, approssimato con gli stessi
  intervalli di `7b9` (la grammatica non modella separatamente le singole
  tensioni alterate #9/#11/b13).
- **`11`**, **`13`**, **`maj13`**: estensioni oltre la nona (`13` omette
  l'11, come da prassi jazz comune per evitare la dissonanza col terzo
  maggiore).

### 2.8 Voicing esplicito sugli accordi (`.stile`)

Un suffisso opzionale `.stile` dopo la qualita' dell'accordo (prima
dell'eventuale `/ottava`) forza il motore di voicing a usare un algoritmo
specifico invece di quello automatico dello strumento:

```
Cmaj7          -> voicing automatico secondo lo strumento della traccia
Cmaj7.drop2    -> forza il voicing Jazz Drop-2
C7.cagEd*3     -> forma E del sistema CAGED, ottava 3
```

**Priorita'**: se presente, il suffisso ha sempre la precedenza
sull'algoritmo automatico dello strumento. **Fallback intelligente**: se
uno stile non ha senso per lo strumento della traccia (es. `.barre` su un
Pianoforte), il motore lo sostituisce automaticamente con l'equivalente
generico piu' vicino (es. `.close`) — non e' mai un errore. Uno stile
**sconosciuto** (refuso), invece, e' segnalato dalla validazione come
qualunque altro token non riconosciuto.

Stili generali (validi su qualunque strumento):
- `noroot`: omette la fondamentale.
- `shell`: omette la quinta.
- `close`: note impilate il piu' vicino possibile.
- `open`: forma aperta, note distribuite su piu' ottave.
- `inv1` / `inv2` / `inv3`: 1a, 2a o 3a inversione (rispettivamente 3a, 5a,
  7a al basso; se l'accordo non ha abbastanza note per l'inversione
  richiesta, si usa la piu' alta disponibile).

Stili per chitarra (fallback automatico se usati su altri strumenti):
`barre`, `Caged`/`cAged`/`caGed`/`cagEd`/`cageD` (le 5 forme del sistema
CAGED), `drop2`, `drop3`, `triad`, `power` (fondamentale+quinta),
`openpos` (approssimazione di accordi in prima posizione), `hendrix`
(fondamentale sola in basso + resto un'ottava sopra), `top` (accordo
un'ottava sopra), `bottom` (fondamentale+quinta+settima, senza la terza).
Le combinazioni qualita'/stile piu' comuni (es. `Cmaj7.drop2`,
`C7#9.hendrix`) usano una tabella di voicing curata per maggiore
accuratezza; le altre combinazioni usano un algoritmo generico
equivalente. Come per il resto del motore, non c'e' un modello reale di
corde/tasti: sono approssimazioni musicalmente sensate su note MIDI
astratte, non diteggiature fisiche.

Stili per tastiera (fallback automatico se usati su altri strumenti):
`left` (sinistra fondamentale/quinta grave, destra il resto), `right`
(voicing compatto per la sola mano destra), `spread` (accordo ampio a due
mani).

Esempi validi: `Cmaj7`, `Cmaj7.drop2`, `C7.cagEd`, `C.power`,
`Am7.open`, `F.barre`.

### 2.9 Basso alternativo sugli accordi (accordo "slash")

Un suffisso opzionale `/Nota` dopo la qualita' (e dopo l'eventuale `.stile`,
prima dell'eventuale `*ottava`) specifica un basso diverso dalla
fondamentale dell'accordo — la classica notazione "slash" dei chart (`C/E`
= accordo di Do col basso Mi):

```
C/E            -> Do maggiore con basso Mi
Dm7/G          -> Re minore settima con basso Sol
C.drop2/E*4    -> come sopra, voicing drop2, ottava 4
```

Il motore di voicing calcola prima l'accordo normalmente (fondamentale,
qualita', stile), poi aggiunge la nota di basso richiesta un'ottava sotto
la voicing risultante (scendendo di ulteriori ottave se necessario per
restare sotto a tutte le altre note) — e' sempre la nota piu' grave
suonata, come in un vero accordo slash. Trasporre un accordo con basso
alternativo trasla anche il basso della stessa quantita' di semitoni.

**Nota tecnica**: `/` dopo un accordo indica solo il basso alternativo;
l'ottava si scrive sempre con `*n` (vedi sez. 2), anche insieme al basso
(`C/E*3`). La vecchia forma con le cifre dopo la barra (`C7/3`, `c/4`) non
e' piu' valida.

### 2.1 Gruppi di ripetizione

Una sequenza di token racchiusa tra parentesi tonde, preceduta da un
numero, viene ripetuta quel numero di volte:

```
4(2C7 2e c d 2A7)   -> ripete 4 volte la sequenza: 2C7 2e c d 2A7
```

I gruppi possono essere annidati (`2(c 2(d e))`) e possono contenere
qualunque token valido, inclusi pattern e riferimenti MIDI.

### 2.1bis Tuplet (terzine / quintine / settimine)

Una lettera opzionale dopo il numero di un comando griglia (`N:`, sezione
3) attiva un raggruppamento irregolare invece della normale suddivisione
binaria, riducendo la durata di ciascuna nota in proporzione:

| Lettera | Tuplet | Rapporto | Esempio |
| --- | --- | --- | --- |
| `T` | terzina | 3 note nello spazio di 2 | `8T:` (terzine di ottavi: 3 in un quarto) |
| `Q` | quintina | 5 note nello spazio di 4 | `16Q:` (quintine di sedicesimi: 5 in un quarto) |
| `S` | settimina | 7 note nello spazio di 4 | `8S:` (settimine di ottavi: 7 in due quarti) |

```
8T: c d e            -> terzina di ottavi: le tre note riempiono un quarto
16Q: c d e f g       -> quintina di sedicesimi: le cinque note riempiono un quarto
8S: c d e f g a b    -> settimina di ottavi: le sette note riempiono due quarti
```

Come per la griglia binaria, il comando resta attivo finche' non viene
cambiato di nuovo (sezione 3): non serve ripeterlo prima di ogni singola
nota del gruppo. Si puo' tornare alla suddivisione binaria in qualunque
momento con un comando `N:` senza lettera (es. `16:` dopo `16Q:`).

### 2.2 Modificatori della nota (e dell'accordo)

Un singolo carattere in fondo a una nota o a un accordo (dopo l'eventuale
ottava `*n`, e dopo l'eventuale `.stile` di voicing su un accordo) ne
cambia l'articolazione, senza alterare la posizione delle note successive
sulla timeline (la nota/accordo occupa comunque l'intera unita' di
griglia, cambia solo per quanto tempo resta udibile):

- **`!` staccato**: suona per il 50% della durata nominale, il resto e'
  silenzio.
- **`x` mute**: viene "stoppato" quasi subito (~15% della durata
  nominale), per un effetto smorzato/percussivo.
- **`_` legato**: viene prolungato leggermente oltre la durata nominale
  (~115%), per farlo "legare" dolcemente al successivo.

Sugli accordi si puo' combinare con il voicing esplicito (2.8), es.
`Cmaj7.drop2!` (voicing Drop-2 + staccato). Lo stesso modificatore
applicato a un accordo agisce su **tutte** le note del voicing, non solo
sulla fondamentale. Nota: i blocchi simultanei `[...]` non supportano
ancora questo modificatore finale; per un "power chord staccato" si usa
un accordo nominale con voicing `.power`, es. `E.power!`.

### 2.3 Slide (pitch bend / portamento)

Due o piu' note collegate da `>` (senza spazi) producono uno scivolamento
continuo di altezza da una all'altra:

```
c*4>d*4        -> scivola da Do4 a Re4 in un'unita' di griglia (come una nota)
c*4>d*4>c*4    -> sale da Do4 a Re4 in un'unita' e torna a Do4 in un'altra
                  (bend-and-release, 2 unita' in tutto)
```

La regola e' una sola: il moltiplicatore di una tappa e' la durata della
rampa che **parte** da quella tappa verso la successiva (1 se manca); il
moltiplicatore dell'**ultima** tappa e' quanto la nota resta ferma
sull'altezza raggiunta (0 se manca: lo slide finisce arrivando).

```
5c*4>d*4       -> rampa lenta da Do4 a Re4 per 5 unita'
2c*4>3d*4      -> sale in 2 unita', poi resta ferma su Re4 per altre 3
                  (bend rapido poi tenuto)
2c*4>2d*4>3c*4 -> sale in 2 unita', scende in altre 2, poi resta ferma
                  sull'altezza di arrivo per altre 3
```

Una catena puo' avere quante tappe si vuole (`c*4>d*4>c#*4>c*4`...). Uno
slide che durerebbe zero (`0c*4>d*4`) e' un errore.

Tecnicamente viene esportato come una singola nota MIDI (un solo note_on/
note_off per l'intera catena) con una sequenza di messaggi di Pitch Bend
che interpolano progressivamente da una tappa alla successiva (con
l'ampiezza del pitch bend impostata automaticamente via RPN per coprire
correttamente slide anche oltre un'ottava). Vedi anche la sezione 10 per
come l'import MIDI riconosce automaticamente un bending (incluso un
bend-and-release) da un file esistente e lo traduce in questa sintassi.

### 2.4 Pedale del sustain (SON / SOFF)

I token `SON` e `SOFF`, inseriti liberamente nel flusso delle note,
attivano/disattivano il pedale del sustain (pianoforte) per tutto cio'
che segue, finche' non si incontra il comando opposto:

```
Piano — AcousticPiano:
  8: SON c*3 g*3 c*4 e*4 g*4 e*4 c*4 g*3 SOFF
  8: SON a*2 e*3 a*3 c*4 e*4 c*4 a*3 e*3 SOFF
```

Se un `SOFF` viene dimenticato, il programma rilascia comunque
automaticamente il pedale alla fine della traccia, per evitare che una
nota resti incastrata in un riverbero infinito.

### 2.5 Dinamiche classiche e rampe (crescendo/diminuendo)

Oltre al valore numerico esplicito (`100@`), la velocity accetta le
indicazioni dinamiche classiche:

| Marcatore | Velocity |
| --- | --- |
| `pppp@` | 10 |
| `ppp@` | 23 |
| `pp@` | 36 |
| `p@` | 49 |
| `mp@` | 62 |
| `mf@` | 75 |
| `f@` | 88 |
| `ff@` | 101 |
| `fff@` | 114 |
| `ffff@` | 127 |

Facendo seguire a un valore di velocity (numerico o dinamico) il simbolo
`>>` (crescendo) o `<<` (diminuendo), la velocity delle note successive
viene interpolata linearmente fino al prossimo valore di velocity
incontrato:

```
8: p@ >> c*4 d*4 e*4 f*4 f@       -> crescendo da 49 a 88 sulle 4 note
8: 110@ << g*4 f*4 e*4 d*4 30@     -> diminuendo da 110 a 30
```

Dopo le frecce si puo' scegliere la **curva** della rampa: `>>exp` parte
piano e accelera, `>>log` parte veloce e rallenta, `>>s` e' morbida
all'inizio e alla fine (`p@ >>exp c d e f ff@`). Vale anche per le rampe
di tempo e per le automazioni (sezione 2.15).

### 2.6 Cambi di tempo (accelerando/rallentando)

All'interno di una traccia, il comando `tempo=N` (1-999) imposta
il tempo (BPM) istantaneamente da quel punto in poi:

```
tempo=120 c*4 d*4    -> tempo impostato a 120 BPM
```

Come per la dinamica, `>>` (accelerando) o `<<` (rallentando) dopo un
comando `tempo=N` interpola progressivamente il tempo fino al prossimo `tempo=N`:

```
tempo=100 >> c*4 d*4 e*4 f*4 tempo=140    -> accelerando da 100 a 140 BPM
tempo=140 << c*4 d*4 e*4 f*4 tempo=80      -> rallentando da 140 a 80 BPM
```

Nota: il tempo e' per natura un concetto condiviso da tutto il progetto
(tutte le tracce suonano sulla stessa timeline); un cambio di tempo
dichiarato in una traccia si applica quindi all'intero brano a partire da
quel punto, non solo a quella traccia.

### 2.7 Cambi di tempo e metrica per battuta

Oltre alla forma semplice (`Tempo: 120 BPM`, `Metrica: 4/4`, un solo
valore per tutto il brano), l'intestazione del progetto accetta anche un
elenco di cambi indicizzati per numero di battuta:

```
Tempo: 1: 120, 5: 140, 9: 100
Metrica: 1: 4/4, 5: 3/4, 8: 4/4
```

Significa: tempo 120 BPM dalla battuta 1, 140 BPM dalla battuta 5, 100 BPM
dalla battuta 9; metrica 4/4 dalla battuta 1, 3/4 dalla battuta 5, 4/4
dalla battuta 8. Le posizioni (in beat) delle battute successive alla
prima vengono calcolate automaticamente tenendo conto della metrica in
vigore in ciascun tratto.

**Barra di avanzamento, evidenziazione e campi Tempo/Metrica durante la
riproduzione**: il file MIDI esportato, la barra di avanzamento,
l'evidenziazione del token in esecuzione nell'editor e i campi **Tempo
(BPM)** e **Metrica** nella toolbar principale usano tutti la stessa mappa
di tempo/metrica del progetto (tutti i cambi per battuta piu' i marcatori
inline `tempo=N`): mostrano quindi sempre il valore realmente in vigore in quel
punto del brano, non una stima basata sul solo tempo/metrica iniziale.
Fermata la riproduzione, i campi Tempo/Metrica tornano al valore "a
riposo" del progetto (quello della battuta 1).

### 2.7bis Tonalita' del brano

L'intestazione del progetto puo' anche dichiarare la tonalita' del brano
(riga `Tonalita: <valore>`), impostabile anche dal campo **Tonalita'**
nella toolbar principale, accanto a Tempo e Metrica:

```
Tonalita: Am
```

Formato: lettera nota (A-G) + alterazione opzionale (`#` o `b`) + `m`
opzionale per il minore, es. `C`, `F#`, `Ebm`, `Am` (maggiore se `m` e'
assente). E' un'informazione descrittiva/di riferimento (non influenza
voicing o riconoscimento accordi); importando un file MIDI che dichiara una
tonalita' (evento meta *key signature*) viene riconosciuta e impostata
automaticamente. Se il file dichiara Do maggiore o non dichiara nulla (Do e'
il valore predefinito di molti sequencer, quindi non e' affidabile), la
tonalita' viene stimata dalle note come fa **Analizza tonalita'**. Viene usata anche da **Suona con la tastiera** (sezione
10ter) dai layout tastiera "Scala della tonalita'".

Se non la conosci gia' (o non sei sicuro), **Componi → Analizza
tonalita'...** la stima automaticamente analizzando le note effettivamente
scritte in tutte le tracce non percussive del progetto (batteria esclusa),
con l'algoritmo classico di Krumhansl-Schmuckler: confronta la distribuzione
delle 12 classi di altezza usate (pesata per durata) con i profili tonali
tipici di ciascuna delle 24 tonalita' possibili e sceglie quella piu'
somigliante, impostandola automaticamente nel campo Tonalita' (sovrascrive
un eventuale valore gia' presente). E' una stima statistica, non
un'analisi armonica vera e propria: puo' sbagliare su brani molto brevi,
cromatici o che modulano — un buon punto di partenza, non un verdetto
infallibile. Se il progetto non contiene note intonate (nessuna traccia, o
solo percussive), lo segnala invece di indovinare.

### 2.10 Controlli di battuta (`|`) e commenti (`//`)

**Controlli di battuta.** Una `|` fra due token dichiara "qui finisce una
battuta". Non suona e non sposta il tempo: il programma controlla solo che
in quel punto ci sia davvero una stanghetta, secondo la **Metrica** del
progetto e i suoi cambi per battuta (sezione 2.7). Puo' stare anche
attaccata a una nota (`d*4|`).

```
4: c d e f | g a b c | 2c 2e |
8: c d e f g a b c | 2: c c |
```

Se una `|` non cade su una stanghetta, la barra sotto l'editor diventa
arancione e dice quale battuta non torna e di quanto, per esempio
`battuta 2: manca 1 croma` o `battuta 3: 1 semiminima di troppo`; la `|`
sbagliata diventa rossa e sottolineata. Il suggerimento sulla barra elenca
tutti gli avvisi. **Non e' un errore di sintassi**: il brano suona ed
esporta lo stesso, e' un aiuto per accorgersi di una nota mancante o di una
durata sbagliata. Una nota che manca sposta tutto quel che segue, ma viene
segnalata una volta sola: le `|` successive si misurano tenendone conto e
avvisano solo se c'e' un altro errore.

- Le stanghette sono quelle del **brano**: in un box della vista Struttura
  brano contano dalla posizione del box (un box che inizia a meta' battuta
  ha la prima `|` dopo mezza battuta).
- Dentro un pattern o un gruppo `N(...)` la `|` viene controllata a ogni
  ripetizione; l'avviso indica il riferimento `%Nome` o il gruppo.
- Dentro un blocco `[...]` la `|` non e' ammessa (errore di sintassi).

**Commenti.** Da `//` alla fine della riga il testo e' ignorato: serve per
annotare sezioni, accordi, idee. Una barra sola (`C/E`, `&"Blues/basso"`)
resta quella di sempre.

```
// Strofa
4: Am | F | C | G |     // giro di quattro accordi
```

I commenti e gli a capo si conservano nel file `.st`, nei box, nella
trasposizione dei box e nel congelamento degli accordi. Non si conservano
invece nel corpo dei pattern (che sono salvati come sequenza di token) ne'
nelle operazioni che riscrivono tutto il testo della traccia (Riorganizza
con i pattern, Espandi i pattern). Nel file `.st` una riga vuota chiude un
blocco: le righe vuote dentro il testo di una traccia si tolgono al
salvataggio (prima troncavano il resto della traccia).

### 2.11 Valori di nota espliciti (`'8.`)

Oltre alla griglia (`N:` seguito da moltiplicatori), una durata si puo'
scrivere come **valore di nota**, con un apostrofo in fondo al token:

| Scrittura | Valore | Durata in quarti |
| --- | --- | --- |
| `c'1` | semibreve | 4 |
| `c'2` | minima | 2 |
| `c'4` | semiminima | 1 |
| `c'8` | croma | 1/2 |
| `c'16`, `c'32`, `c'64` | semicroma, biscroma, semibiscroma | 1/4, 1/8, 1/16 |
| `c'4.` / `c'8.` | semiminima / croma **puntata** | 1 e 1/2 / 3/4 |
| `c'2..` | minima con due punti | 3 e 1/2 |
| `c'8T` / `c'4T` | croma / semiminima di **terzina** | 1/3 / 2/3 |
| `c'16Q`, `c'8S` | quintina, settimina (come le griglie `NQ:`, `NS:`) | |

```
8: c*4'8. d*4'16 e*4 e*4 [c e g]'2    // ritmo puntato senza cambiare griglia
```

Il valore vale **solo per quel token**: la griglia corrente resta quella di
prima (nell'esempio, `e*4 e*4` sono crome della griglia `8:`). Funziona con
note, accordi (`C7'2`), blocchi (`[c e g]'2`), pause (`r'4`), percussioni
(`kick'16`) e slide. Un moltiplicatore davanti si somma: `2c'8` dura due
crome. L'articolazione puo' stare prima o dopo: `c'8!` e `c!'8` sono la
stessa croma staccata. La griglia resta comoda per i ritmi regolari; il
valore esplicito e' piu' leggibile per le frasi irregolari e per chi viene
dallo spartito.

### 2.12 Piu' voci nella stessa traccia (`{ ; }`)

Un **blocco di voci** contiene due o piu' sequenze, separate da `;`, che
**partono insieme**, ognuna con le sue durate. Il blocco dura quanto la
voce piu' lunga, poi la traccia prosegue:

```
4: { c*5 d*5 e*5 f*5 ; 4c*4 } g*4           // melodia sopra una nota tenuta
4: {
  8: e*5 d*5 c*5 d*5 e*5 e*5 2e*5            // mano destra
  ;
  2c*4 2g*3                                  // mano sinistra
}
```

A differenza di `[...]`, dove tutto inizia e finisce insieme, ogni voce ha
il suo ritmo: e' quello che serve per il pianoforte a due mani, una
melodia sopra un accordo tenuto, la chitarra classica.

- Ogni voce parte con lo **stato** (griglia, velocity) del punto in cui si
  apre il blocco; i cambi fatti **dentro** una voce restano li'.
- Dentro una voce vale tutta la grammatica: gruppi `N(...)`, pattern
  `%Nome`, controlli di battuta `|` (ogni voce si controlla per conto suo),
  testo cantato, anche altri blocchi di voci.
- Il blocco puo' andare a capo; un `;` fuori da un blocco e' un errore.
- Nell'editor ogni voce ha uno **sfondo colorato** diverso (azzurro la
  prima, ambra la seconda, poi lilla e verde; un blocco annidato parte da
  un altro colore): si vede subito dove inizia e finisce ciascuna, anche
  quando il blocco va a capo. Le parentesi e i `;` restano senza sfondo.
- In partitura (sezioni 10.1 e 10.1bis) le voci diventano **voci dello
  stesso pentagramma**, con i gambi in su e in giu'.

### 2.13 Testo cantato (`"..."`)

Una stringa fra virgolette e' il **testo cantato** delle note che la
**precedono**, a partire dalla nota dopo il testo precedente (o
dall'inizio): una sillaba per nota, separate da spazi. Si scrive come
sotto un rigo di spartito:

```
4: c*4 d*4 e*4 2f*4
"Ma- ri- a, sei"
```

- Un trattino in fondo (`Ma-`) dice che la parola continua nella sillaba
  dopo; in partitura le sillabe vengono unite dal trattino.
- `_` lascia la nota senza una sillaba nuova: la sillaba precedente si
  **prolunga** (melisma, con la linea di estensione in partitura).
- `*` salta una nota (nessuna sillaba).
- Pause e percussioni non ricevono sillabe.
- La sillaba si puo' anche attaccare alla nota: `c"Ma-" d"ri-" e"a"`.
- Dentro un gruppo `2(...)` il testo si ripete con le note; dopo un blocco
  di voci va sulla **prima voce** (una voce puo' avere anche il suo testo,
  dentro il blocco).
- Il testo non si sente: va nella partitura (sotto le note), nel MusicXML e
  nel MIDI esportato (eventi *lyrics*, letti dai programmi karaoke).
- Se ci sono **piu' sillabe che note** l'editor lo segnala come avviso
  (arancione), come i controlli di battuta. Un `//` dentro le virgolette fa
  parte del testo, non apre un commento.

### 2.14 La specifica e la libreria ST-language

La notazione ha una **specifica formale pubblica**:
[docs/spec/ST-language.it.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.it.md) (in inglese
[ST-language.md](https://github.com/openssound/st-language/blob/main/docs/spec/ST-language.md)), con licenza **CC BY 4.0** (si puo'
copiare, tradurre e adattare citando la fonte). Descrive la grammatica
completa, come il testo diventa note nel tempo, gli errori e gli avvisi, il
formato dei file `.st` e la corrispondenza con il MIDI, con una **suite di
conformita'** ([`docs/spec/conformance/`](https://github.com/openssound/st-language/tree/main/docs/spec/conformance)): i casi di prova che un altro
programma deve superare per leggere ST-language come SoundText.

Il motore della notazione e' anche una **libreria Python autonoma**,
`st_language`, senza dipendenze esterne: e' la stessa che usa SoundText,
quindi i due danno sempre lo stesso risultato. Si installa con
`pip install git+https://github.com/openssound/st-language.git` e offre dei comandi da terminale:

```
st-language check brano.st           # errori e avvisi (battute, testo cantato)
st-language midi brano.st -o brano.mid
st-language musicxml brano.st        # partitura brano.musicxml
st-language events brano.st          # gli eventi in JSON
echo "4: c d e f | 2g 2g" | st2mid - -o melodia.mid --instrument Trumpet
```

Un file senza intestazioni di traccia e' un brano di una traccia sola
(`--instrument` ne sceglie lo strumento). Da Python: `import st_language as
st`, poi `st.parse(testo)`, `st.validate(testo)`, `st.check(testo)`,
`st.load_song("brano.st")`, `st.to_midi(brano, "brano.mid")`. Cosi' i brani
scritti in ST si possono controllare ed esportare anche senza aprire
SoundText (per esempio da uno script, o in un repository di canzoni).

### 2.15 Automazioni (volume, espressione, pan... che cambiano nel tempo)

Le dinamiche (`p@`, `>>`) cambiano la **velocity**, cioe' la forza con cui
viene suonata ogni nota: una nota gia' partita resta com'e'. Le
**automazioni** invece agiscono sullo strumento in modo **continuo**, anche
mentre una nota e' tenuta, come muovere un fader del mixer durante
l'esecuzione:

| Comando | Cosa cambia | Valori | Di partenza |
| --- | --- | --- | --- |
| `vol=N` | volume della traccia | 0-127 | 100 |
| `expr=N` | espressione: il volume "dentro" la dinamica (archi, fiati, organo) | 0-127 | 127 |
| `pan=N` | posizione stereo: -1 sinistra, 0 centro, 1 destra | -1..1 (anche decimali) | 0 |
| `mod=N` | modulazione (vibrato, per molti strumenti) | 0-127 | 0 |
| `rev=N` | mandata al riverbero | 0-127 | 0 |
| `cho=N` | mandata al chorus | 0-127 | 0 |
| `bend=N` | pitch bend, in semitoni (come la leva del synth) | -24..24 (anche decimali) | 0 |
| `ccN=V` | qualunque controller MIDI N (0-119), es. `cc74` brillantezza | 0-127 | 0 |

Scritto da solo, il comando cambia il valore in quel punto. Seguito da `>>`
(o `<<`, e' lo stesso) apre una **rampa** che arriva al prossimo comando
con lo stesso nome, passando per tutti i valori intermedi:

```
4: vol=0 >>exp 4c*4 vol=100          // fade-in sulla nota tenuta
4: pan=-1 >> c d e f pan=1           // il suono passa da sinistra a destra
4: expr=40 >>s 2C 2F expr=127 r      // si gonfia sotto due accordi
8: rev=20 c d e f rev=90 4g          // il riverbero aumenta di colpo
```

La **curva** della rampa si sceglie dopo le frecce: `>>` (lineare),
`>>exp` (parte piano e accelera: il fade-in naturale), `>>log` (parte
veloce e rallenta: il fade-out naturale), `>>s` (morbida all'inizio e alla
fine).

**Forcelle sulle note.** Un `<` in fondo a una nota (o a un accordo, un
blocco, uno slide) fa un **crescendo durante la nota**, un `>` un
diminuendo: e' la forcella dello spartito, fatta con l'espressione (dalla
meta' al valore corrente o viceversa), che poi torna com'era:

```
4: 4c*5<            // nota tenuta che cresce
4: 2C< 2G>          // un accordo cresce, l'altro cala
4: c'2> [c e g]<    // con un valore di nota o su un blocco
```

- Le automazioni valgono per tutta la traccia, anche scritte dentro un
  blocco di voci `{ ; }`; rampe di nomi diversi possono sovrapporsi
  (`vol=` e `pan=` insieme).
- `vol=` si combina con il volume del mixer (`vol=100` = il volume del
  fader); `pan=`, `rev=` e `cho=` scritti nel testo prendono il posto dei
  valori del mixer da quel punto in poi.
- Una rampa aperta va chiusa da un valore con lo stesso nome, altrimenti
  la validazione segnala l'errore; sono errori anche una forcella su una
  pausa e una forcella dentro una rampa di `expr=` aperta.
- Si sentono in riproduzione e finiscono nel MIDI esportato (come control
  change: CC7, CC11, CC10, CC1, CC91, CC93); in partitura le rampe di
  `vol=`/`expr=` e le forcelle compaiono come forcelle di crescendo e
  diminuendo.
- Fanno parte della specifica ST-language dalla versione 1.1 (2.14).

### 2.16 Legature e swing

**Legatura di valore `~`.** Un `~` in fondo a una nota, un accordo o un
blocco la **unisce** alla successiva uguale: suonano come una nota sola,
lunga quanto le due insieme. Serve soprattutto per tenere una nota oltre
la stanghetta, dove la divisione in battute non lascia scriverla tutta
intera:

```
4: c d 2f~ | 2f g a |        // il fa dura 4 quarti, a cavallo della battuta
4: 4C7~ | 4C7 | 4F |         // un accordo tenuto per due battute
4: c'2~ c'8 r'8 d'4          // anche con i valori di nota
```

La nota dopo il `~` deve essere la stessa (`c#~ db` va bene: e' lo stesso
suono), altrimenti e' un errore; le percussioni, le pause e gli slide non
si legano.

**Legatura di portamento `( )`.** Un `(` in fondo alla prima nota e un
`)` in fondo all'ultima collegano una frase: le note in mezzo suonano
**legate** (attaccate l'una all'altra, come in un fraseggio cantabile),
l'ultima come scritta. In partitura compare l'arco sopra le note.

```
4: c( d e f) g( a b c*5)
4: 2(c( d) e)                // dentro un gruppo, la legatura si ripete
```

Una nota con un'articolazione propria (`d!` staccato) la tiene anche dentro
la legatura. Le legature non si annidano e non attraversano un blocco di
voci `{ ; }`.

**Swing.** `swing=N` fa "dondolare" le crome dal punto in cui lo scrivi: in
ogni battito la prima croma si allunga e la seconda si accorcia, come si
suona nel jazz, nel blues e nello shuffle. N e' la parte del battito data
alla prima croma: 50 e' diritto, 66 e' terzinato (lo swing classico), fino
a 80. `swing16=N` fa lo stesso con le semicrome (funk, hip hop).
`swing=50` toglie lo swing.

```
swing=62 8: c d e f g a b c*5   // si scrive diritto, suona in swing
swing16=58 16: kick hihat snare hihat kick kick snare hihat
```

Si scrive tutto diritto: i controlli di battuta e la partitura restano
regolari (in partitura compare l'indicazione "Swing"), cambia solo come
suona, nella riproduzione e nel MIDI esportato.

### 2.17 Ritornelli, segni e indicazioni

**Ritornelli.** Si scrivono come sullo spartito: `|:` apre la parte da
ripetere, `:|` la chiude, e la parte si suona due volte. Se manca `|:`,
il ritornello parte dall'inizio del brano (o dalla fine del ritornello
precedente).

```
4: |: c d e f | g a b c :| c*5 d*5 e*5 f*5 |
```

Per un finale diverso a ogni passaggio si usano le **caselle**: `|1.`
apre la prima, `:|` la chiude e torna all'inizio, `|2.` apre la seconda,
che finisce con `||` (o con la fine del testo). Con tre caselle si
suona tre volte, e cosi' via.

```
4: |: c d e f |1. g a b c :| |2. 4c*5 || d e f g |
```

Si sente tutto per esteso; in **partitura** compaiono i veri segni di
ritornello e le caselle, a patto che il ritornello cominci e finisca
sulle stanghette e che ogni passaggio sia uguale al primo in tutte le
tracce (altrimenti la partitura lo scrive per esteso). Anche un gruppo
`2(...)` che occupa battute intere si scrive in partitura come
ritornello. `|:`, `:|`, `|1.` e `||` valgono anche come controlli di
battuta, e i ritornelli non si annidano.

**Segni sulle note.** Un `$` seguito dal nome, in fondo a una nota, un
accordo o un blocco (dopo il valore di nota), aggiunge un segno che si
vede in partitura e si sente:

| Segno | Cosa fa |
| --- | --- |
| `$accent` | accento: la nota suona piu' forte |
| `$marcato` | accento forte |
| `$tenuto` | tenuto |
| `$fermata` | corona: tutto il brano si ferma sulla nota (durata doppia); va anche su una pausa |
| `$tr` | trillo con la nota sopra (nella tonalita' del brano) |
| `$mordent` | mordente: nota, nota sotto, nota |
| `$turn` | gruppetto: sopra, nota, sotto, nota |

```
4: c$accent d e$tenuto f$fermata | 2g$tr a$mordent b$turn |
4: [c e g]$accent$tenuto r$fermata
```

Trillo, mordente e gruppetto si suonano sulle note singole (su accordi e
blocchi restano un segno in partitura).

**Indicazioni di testo.** `$"testo"` scrive un'indicazione sopra il
pentagramma nel punto in cui si trova: `$"rit."`, `$"dolce"`,
`$"a tempo"`. Non cambia il suono: per rallentare davvero si usa una
rampa di tempo (`tempo=100 << ... tempo=70`, sezione 2.6).

### 2.18 Ottave relative e tonalita'

Due comandi rendono le melodie molto piu' corte da scrivere. Si possono
usare insieme, ed entrambi sono facoltativi: senza, tutto funziona come
prima.

**Ottave relative (`rel:`).** Dopo `rel:` non serve piu' scrivere
l'ottava: ogni nota va all'ottava **piu' vicina alla nota precedente**
(al massimo una quarta sopra o sotto, contando le lettere). Per saltare
piu' lontano si aggiunge `*+` (un'ottava sopra) o `*-` (un'ottava sotto),
anche ripetuti (`*++` due ottave sopra, `*--` due sotto); `*n` resta valido e fissa l'ottava esatta.

```
rel: c d e f g a b c          // scala di Do salendo fino al Do sopra
rel: c*5 b a g f e d c        // e scendendo
rel: g c*+ c*- c                // c*+ salta in alto, c*- torna giu'
```

La prima nota dopo `rel:` va vicino al Do dell'ottava di default dello
strumento. Dopo un blocco `[...]` si riparte dalla sua prima nota;
accordi e percussioni non contano. `abs:` torna alle ottave assolute.
Nei ritornelli e nei gruppi ogni ripetizione riparte dalla stessa nota,
cosi' suona uguale.

**Tonalita' (`key=`).** Dopo `key=G` ogni nota **senza** alterazione
prende quella della tonalita': in sol maggiore `f` e' fa diesis. Un
diesis o un bemolle scritto vale solo per quella nota; `n` (o `♮`) e' il
bequadro e toglie l'alterazione della tonalita'.

```
key=G rel: g a b c d e f g    // sol maggiore senza scrivere il diesis
key=Bb rel: b c d e f g a b   // si bemolle maggiore: b ed e sono bemolli
key=Dm rel: d e f g a b c# d  // re minore (b bemolle) con il do diesis
key=G f fn f#                 // fa diesis, fa naturale, fa diesis
```

`key=off` toglie la tonalita'. Gli accordi (`C`, `F7`...) non cambiano:
le sigle sono sempre assolute. La tonalita' del brano (nella barra in
alto) serve all'armatura della partitura; `key=` dice come leggere le
note della traccia.

I **pattern** (`%Nome`) si leggono sempre con ottave assolute e senza
tonalita', qualunque sia il modo della traccia che li usa: suonano uguali
ovunque.

**Riscrivere una traccia esistente.** Il pulsante **Altezze relative e
tonalita'**, sotto l'editor, riscrive la traccia corrente con `rel:` e,
se il brano ha una tonalita', `key=`: le note restano le stesse, il testo
diventa piu' corto. E' comodo dopo un'importazione da MIDI, MusicXML o
ABC. Anche **Trasponi** (nei box) conosce i due modi: in `rel:` le note
restano relative, e con `key=` si traspone anche la tonalita'.

### 2.19 Micro-tempo, accordatura, molte tracce, MTXT

**Micro-tempo (`shift=`).** `shift=N` fa suonare le note che seguono N
millisecondi **dopo** (N positivo) o **prima** (N negativo) di dove sono
scritte; `shift=0` le riporta a tempo. Il ritmo scritto non cambia:
controlli di battuta e partitura restano uguali, cambia solo il momento
in cui le note suonano. Va da -500 a 500.

```
4: kick shift=20 snare shift=0 kick shift=20 snare   // rullante un po' indietro
shift=-10 8: c c g g a a g g                          // basso che spinge in avanti
```

Serve per il "feeling" e per allineare una parte a una registrazione;
i ritmi veri si scrivono con i valori, i gruppi irregolari e lo swing.

**Accordatura (`tune=`).** `tune=N` accorda lo strumento di N cent
(da -100 a 100: 100 cent sono un semitono). E' un'automazione come
`vol=` o `bend=`: vale per tutta la traccia, anche durante una nota, e
accetta le rampe.

```
tune=-20 4: c d e f              // per suonare con un disco accordato un po' basso
tune=0 >> 4: c d e f tune=50     // sale di un quarto di tono in quattro note
```

**Piu' di 15 tracce.** Ogni traccia ha sempre il suo canale MIDI: dalla
sedicesima traccia melodica l'export MIDI usa una seconda "porta" (16
canali in piu'), poi una terza e cosi' via. SoundText le suona e le
reimporta correttamente; qualche lettore MIDI molto vecchio ignora le
porte e suona quelle tracce sui canali delle prime.

**MTXT.** **Progetto → Esporta → MTXT...** scrive il brano in
[MTXT](https://github.com/Daninet/mtxt), un formato di testo con un
evento per riga e i tempi in quarti (`1.5 note C4 dur=0.5 vel=0.8`),
comodo da leggere, confrontare e far modificare a un'IA. Contiene note,
strumenti, automazioni, tempo e metrica, come il MIDI. **Progetto → Importa → MTXT...** fa il contrario: legge il file come un MIDI (una traccia per
canale, con i nomi dei canali). La libreria fa lo stesso da terminale
con `st-language mtxt brano.st` e `st-language mtxt file.mtxt` (che
diventa un `.mid`).

### 2.20 Ancore di battuta (`bar=`)

**Dove entra una parte.** `bar=N` porta il cursore all'**inizio della
battuta N**, con i silenzi che servono: invece di contare le pause
(`28%Rest`) si scrive la battuta in cui la parte entra.

```
Guitar 2:
  bar=29                          // la seconda chitarra entra alla battuta 29
  8: 100@ c d e f g a b c
```

- Se la traccia e' **prima** di quel punto, il vuoto si riempie di
  silenzio; se e' **esattamente** li', non succede nulla.
- Se la traccia e' **gia' oltre** (una parte piu' lunga del previsto),
  l'ancora non torna indietro: la parte continua dov'e', e l'editor
  mostra un **avviso** sull'ancora ("battuta 29: la traccia e' gia' 2
  quarti oltre l'inizio"), come per i controlli di battuta `|`.
- Le battute si contano come nel resto del programma: dalla 1, secondo
  la metrica del brano e i suoi cambi. Dentro un pattern o un gruppo
  ripetuto vale la battuta del brano a ogni ripetizione.
- Una legatura `~` non puo' attraversare un'ancora che richiede un
  silenzio.

`bar=` posiziona e `|` verifica: insieme dicono dove deve stare ogni
parte e avvisano quando una si e' spostata. Nella finestra di
**Estrai pattern** i blocchi con un'ancora non vengono estratti, perche'
un pattern non sa in che battuta si trova.

### 2.21 Trasposizione (`transpose=`, `%Nome+N`)

**Trasporre senza riscrivere.** `transpose=N` fa suonare note, accordi,
slide e blocchi che seguono N semitoni **sopra** (N positivo) o **sotto**
(N negativo) rispetto a come sono scritti; `transpose=0` torna all'altezza
scritta. Va da -60 a 60.

```
4: c d e f g a b c*5        // in Do
transpose=2 4: c d e f g a b c*5  // la stessa melodia in Re
transpose=0
```

**Un pattern in un'altra tonalita'.** Dopo il nome di un pattern si scrive
di quanti semitoni trasporlo: `%Tema+7` lo suona una quinta sopra,
`%Tema-12` un'ottava sotto, `2%Tema+3` due volte, tre semitoni sopra.
Non servono pattern copiati: il tema si scrive una volta sola.

```
Pattern %Tema:
  key=Eb 8: 90@ g*5 b*5 e*6 2d*6 2b*5 |

Violini1:
  %Tema  %Tema-3  %Tema+12     // Mi bemolle, poi Do (-3), poi un'ottava sopra
```

- La trasposizione vale per **tutto** quello che c'e' dentro il pattern, anche
  per i pattern che richiama, e si **somma** a quella gia' in vigore
  (`transpose=3 %Tema+4` suona 7 semitoni sopra).
- Un `transpose=` scritto dentro un pattern finisce con il pattern.
- Lo stesso vale per la libreria MIDI: `&"Basso"+7`, `&"Basso"-12`
  (sezione 5).
- Con `key=` le note trasposte si scrivono nella tonalita' nuova: `key=G`
  con `transpose=2` e' La maggiore (il fa diesis scritto diventa sol
  diesis, il sol diventa la). Senza tonalita', un bemolle resta un bemolle
  e le altre note alterate prendono il diesis. Anche nella partitura.
- Gli accordi cambiano nome (`C7/E` +5 e' `F7/A`) e salgono di ottava
  quando scavalcano il Do; con +12 ogni accordo sale di un'ottava.
- Le percussioni e le pause non cambiano. Se una nota trasposta esce
  dall'estensione MIDI, il programma lo segnala come errore.
- Nel pulsante **Estrai pattern** i blocchi con un `transpose=` non vengono
  estratti: nel pattern la trasposizione finirebbe alla fine del pattern.

### 2.22 `reset:`, levare e versione del file (ST 2.6)

**`reset:` — ripartire da zero.** Riporta tutto allo stato iniziale:
griglia `4:`, velocity 80, niente swing ne' spostamento, trasposizione 0,
ottave assolute, nessuna tonalita'. Le automazioni (`vol=`, `pan=`...)
restano dove sono. Serve quando un pezzo di testo deve suonare uguale
qualunque cosa ci sia prima:

```
rel: key=G 8: 100@ transpose=2 g a b c
reset: c d e f           // di nuovo semiminime, velocity 80, Do maggiore
```

Ogni box della vista Struttura comincia con un `reset:`: cosi' un
`transpose=` o un `key=` scritto in un box non passa mai al box dopo.

**Battuta in levare.** Se il brano comincia con un levare, scrivi quanti
quarti dura nel campo **Levare** della barra del brano (o `Levare: 1` nel
file). La battuta 1 diventa la prima intera: i controlli di battuta `|`,
le ancore `bar=N`, i cambi di tempo e di metrica per battuta, il righello
della vista Struttura, il metronomo e la partitura contano da li'. Il
levare e' la battuta 0.

```
Levare: 1
Metrica: 3/4

Violino:
  4: g | c e g | c*5 2r |      // un quarto in levare, poi battute da 3/4
```

**Nomi dei file MIDI fra virgolette.** Il nome di un file della libreria
MIDI si scrive sempre fra virgolette: `&"Riff"`, `&"Blues/bass-line"`,
anche con spazi (`&"intro take 2"`). Quello che segue le virgolette e'
sempre la trasposizione: `&"Riff"-2` e' il file `Riff` due semitoni sotto,
`&"take-2"` e' il file che si chiama `take-2`. I brani scritti prima (con
`&Riff`) si convertono da soli quando li apri, e restano uguali; scrivendo
`&Riff` senza virgolette l'editor ti dice come correggerlo.

**Versione e parole inglesi nel file.** Il file `.st` comincia con
`ST: 2.6`, la versione del linguaggio con cui e' scritto; aprendo un file
di una versione piu' recente il programma avvisa. Il programma legge anche
le parole chiave in inglese (`Track`, `Instrument`, `Meter`, `Key`,
`Pickup`, `percussion=`, `octave=`, `yes`), comodo per chi scrive i file a
mano; salvando usa sempre le forme italiane.

## 3. Stato Corrente

Griglia e velocity restano attive finche' non vengono cambiate di nuovo:

```
100@ 8: c e 60@ g a 100@ c
```
`c` ed `e` durano un ottavo a velocity 100; `g` e `a` a velocity 60; l'ultima
`c` torna a velocity 100. Nessun evento viene generato dai comandi di stato:
non consumano tempo sulla timeline.

## 4. Pattern (%Nome)

Si definiscono nella libreria pattern (menu **Componi → Gestisci
libreria pattern**) o direttamente nel file `.st`:

```
Pattern %GtrArp:
  16: 90@ c e g e 70@ c e g e
```

e si richiamano in qualsiasi traccia con `%GtrArp`.

**Ripetizione:** anteponendo un numero si ripete il pattern N volte:
```
3%GtrArp        -> esegue %GtrArp per tre volte di seguito
```

### 4.1 Ascoltare un pattern

Nel dialogo **Componi → Gestisci libreria pattern**, ogni pattern
selezionato puo' essere ascoltato con il pulsante **▶ Ascolta**, scegliendo
lo strumento di anteprima dalla tendina accanto (il pattern resta comunque
universale: la scelta serve solo per il test audio). Le modifiche non
ancora salvate nell'editor vengono incluse automaticamente nell'anteprima.
Mentre suona, nel corpo del pattern è evidenziato il punto che stai
ascoltando, come nell'editor principale e nei dialoghi di modifica del box,
di generazione, di "Suona con la tastiera" e di conversione audio.

### 4.2 Riorganizzare la song con i pattern

Menu **Componi → Estrai pattern dalle tracce...**: analizza tutte le
tracce del progetto corrente, individua blocchi di eventi che si ripetono
(anche non consecutivamente) e li converte automaticamente in pattern
riutilizzabili, sostituendo le occorrenze con `%Nome` (con ripetizione
`N%Nome` quando le occorrenze sono consecutive). Il contenuto musicale non
cambia: e' solo una riscrittura piu' compatta e leggibile della stessa
sequenza di eventi. Se non vengono trovate ripetizioni sufficientemente
lunghe, il programma lo segnala senza modificare nulla.

I pattern generati prendono il nome dallo **strumento della traccia** da cui
provengono (es. `%Guitar1`, `%Guitar2`, `%Bass1`...), non un prefisso
generico. Inoltre un pattern estratto **non contiene mai riferimenti ad
altri pattern**: se una traccia usa gia' `%Lib1` insieme a materiale
letterale ripetuto, `%Lib1` resta un riferimento a se stante e non viene mai
incluso dentro un nuovo pattern (nessun pattern nidificato).

Menu **Componi → Espandi pattern nelle tracce...**: l'operazione
inversa. Sostituisce ogni riferimento `%pattern` e `&"midi"` presente nelle
tracce con i token letterali corrispondenti (ripetizione gia' applicata),
rendendo il progetto completamente autosufficiente; i
pattern non piu' utilizzati vengono rimossi. Utile prima di condividere una
song senza doverne allegare anche la libreria pattern, o per ispezionare/
modificare a mano ogni singolo evento senza l'indirezione dei riferimenti.

Entrambe le operazioni agiscono sull'intero progetto, chiedono conferma
prima di applicarsi, e vengono eseguite in background con una barra di
progresso: l'interfaccia resta reattiva e l'operazione e' annullabile. Il
tempo di ricerca dei blocchi ripetuti e' comunque sempre limitato (per
traccia), cosi' che anche su tracce molto lunghe la riorganizzazione non
resti mai bloccata a tempo indefinito.

### 4.3 Menu contestuale su una selezione (tasto destro)

Selezionando con il mouse una sequenza di token nell'editor (traccia,
corpo di un pattern o di un box) e facendo click con il **tasto destro**,
si apre un menu contestuale con tre voci. Nelle anteprime dei dialoghi
(Genera batteria/basso/accompagnamento/giro armonico, Suona con la
tastiera, conversione audio, libreria MIDI) il menu ha solo **▶ Play**, e
ferma prima l'eventuale ascolto dell'anteprima intera:

- **▶ Play**: riproduce solo la selezione, con lo strumento della traccia
  corrente, ricostruendo automaticamente l'ultima griglia ritmica e
  velocity attive prima della selezione (cosi' suona come suonerebbe nel
  contesto originale, non sempre a 1/4 e velocity 80).
- **Raggruppa**: racchiude la selezione tra parentesi tonde, trasformandola
  in un gruppo `(...)` (vedi sezione 2.1); utile prima di applicarvi un
  moltiplicatore di ripetizione a mano (es. trasformare `(...)` in
  `4(...)`).
- **Trasforma in pattern...**: chiede un nome, crea un nuovo pattern
  contenente la selezione e sostituisce la selezione stessa con
  `%NomePattern` — un modo rapido per estrarre manualmente un singolo
  frammento in pattern, in alternativa alla ricerca automatica di **Estrai
  pattern dalle tracce...** (sezione 4.2).

La selezione fatta con il mouse viene sempre "agganciata" ai confini dei
token interi che tocca (non serve selezionare con precisione millimetrica);
se l'ultimo token incluso e' un comando di stato senza seguito (`N:` o
`N@`), viene scartato automaticamente, cosi' il gruppo o il pattern
risultante non termina mai "in sospeso" senza un evento sonoro.

Se la selezione contiene anche un riferimento a un pattern (`%Nome`) o a un
file MIDI (`&"Nome"`), nel menu compare **solo Play**: raggruppare o
trasformare in un nuovo pattern un'indirezione gia' esistente non e'
consentito.

### 4.4 Rinominare un pattern

Il pulsante **Rinomina** (accanto a "Nuovo" nel dialogo **Componi →
Gestisci libreria pattern**) rinomina il pattern selezionato e aggiorna
automaticamente ogni riferimento `%vecchionome` gia' presente — sia nelle
tracce sia nel corpo degli altri pattern — al nuovo nome, cosi' la
rinomina non spezza silenziosamente cio' che lo richiama. Il nuovo nome
deve rispettare la stessa sintassi di un riferimento a pattern (lettere,
cifre e underscore, senza spazi) e non puo' coincidere con quello di un
pattern gia' esistente.

## 5. Libreria MIDI (&"Nome")

Nella cartella `midi/` (accanto al programma, vuota alla prima
installazione: la libreria e' tua) puoi conservare brevi frasi musicali come
file `.mid`, organizzate anche in sottocartelle per categoria (genere,
artista, strumento...), ad esempio:

```
soundtext/
├── midi/
│   ├── Guitar/
│   │   └── Intro.mid
│   ├── Blues/
│   │   └── shuffle.mid
│   ├── Drums/
│   └── Bass/
└── songs/
    └── i_tuoi_progetti.st
```

Un riferimento `&"Nome"` cerca **ricorsivamente in tutte le sottocartelle**:

```
Guitar:
  &"Intro" &"Intro" %GtrArp
```

se hai un file `midi/Guitar/Intro.mid`, lo trova automaticamente (o
qualunque altra sottocartella contenga un file `Intro.mid`), senza indicare
il percorso.

**Percorsi qualificati:** se lo stesso nome esiste in piu' sottocartelle, il
riferimento e' ambiguo e la validazione lo segnala, indicando le alternative
trovate; per risolverlo basta qualificare il percorso:

```
&"Blues/bass_line"      -> usa specificamente midi/Blues/bass_line.mid
```

**Ripetizione** (come per i pattern):

```
2&"bass_line"            -> ripete il riferimento due volte
```

**Trasposizione:** come per i pattern, un numero dopo il nome trasporta il
file di quel numero di semitoni: `&"Intro"+7` lo suona una quinta sopra,
`&"Intro"-12` un'ottava sotto, `2&"Intro"+2` due volte, due semitoni sopra
(sezione 2.21). Il nome sta fra le virgolette, quindi trattini e spazi
non danno problemi: `&"Blues/bass-line"-2` e' `Blues/bass-line` due
semitoni sotto (sezione 2.22).


Gestione dalla GUI: menu **Componi → Gestisci libreria MIDI**. Da li'
puoi importare un file `.mid` esistente (anche indicando una sottocartella
di destinazione), rinominarlo/spostarlo, eliminarlo, ascoltarlo con
**▶ Ascolta file originale** (riproduce il file .mid cosi' com'e', con
tutti i suoi canali), o visualizzarne/modificarne un'anteprima testuale
(viene convertito il canale con piu' note) e "rigenerare" il file MIDI dal
testo modificato, scegliendo lo strumento da usare per il voicing.
Quando rinomini o sposti un file e il brano aperto lo richiama, il
programma propone di aggiornare i richiami `&"Nome"` (anche nei box e nei
pattern), tenendo moltiplicatore e trasposizione.

Nota: `&"Nome"` importa solo il canale piu' significativo del file MIDI (in
genere quello con piu' note); per un import multitraccia completo usa invece
**Progetto → Importa → MIDI...**, che crea una traccia per ciascun canale.

## 5bis. Cartella dei brani (songs/)

I dialoghi **Apri progetto** e **Salva con nome** si aprono per default sulla
cartella `songs/` (accanto al programma): e' il posto pensato per le tue
composizioni, distinto da `examples/`, che contiene invece i progetti
dimostrativi delle funzionalita' del programma.

## 6. Percussioni

36 identificatori fissi, mappati sul General MIDI Drum Map (canale 10) e
senza supporto alle ottave. Corrispondono, nell'ordine, ai tasti usati in "Suona con la tastiera"
(sezione 10ter): riga numerica (1-9, poi 0 ' ì), riga Q, riga A.

- Kit base (riga numerica): `kick`, `snare`, `hihat`, `hihat_open`,
  `tom1`, `tom2`, `floor`, `crash`, `ride`, `kick2`, `rimshot`, `clap`.
- Altri tom/piatti/hi-hat (riga Q): `snare2`, `hihat_pedal`,
  `tom_lowmid`, `tom_hi`, `tom_highfloor`, `china`, `ride_bell`,
  `tambourine`, `splash`, `cowbell`, `crash2`, `ride2`.
- Percussioni latine (riga A): `bongo_hi`, `bongo_low`, `conga_mute`,
  `conga_open`, `conga_low`, `timbale_hi`, `timbale_low`, `cabasa`,
  `maracas`, `claves`, `woodblock_hi`, `woodblock_low`.

## 7. Tracce e strumenti

- **Aggiungi traccia**: pulsante **+ Aggiungi traccia** (sotto l'ultima
  testata, sia nella vista Struttura brano sia nella vista Testo) o
  menu **Traccia → Aggiungi**. Il pulsante apre un menu con:
  - **Traccia con strumento...** (Ctrl+T) e **Traccia audio...**;
  - **Genera una traccia**: **Batteria**, **Giro armonico**, **Basso dagli
    accordi**, **Accompagnamento o riff** (per l'ultimo si sceglie lo
    strumento: polifonico = accompagnamento, monofonico = riff/melodia).
    Si apre il dialogo del generatore e la traccia viene creata solo se lo
    confermi, gia' riempita (un box nella vista Struttura, testo nella vista
    Testo). Basso e accompagnamento seguono gli accordi di un'altra traccia:
    finche' il brano non ne ha restano disattivati, con il motivo scritto
    accanto;
  - **Traccia da un file MIDI...**: un canale di un file MIDI diventa una
    nuova traccia, con lo strumento riconosciuto nel file.
- **Azioni su una traccia** (genera, suona con la tastiera, importa MIDI o
  audio, nome e strumento, esporta MIDI, rimuovi): menu **⋯** sulla testata
  della traccia (in entrambe le viste), oppure tasto destro sulla testata;
  restano anche nel menu
  **Traccia**.
- **Rinomina / cambia strumento**: **⋯ → Nome e strumento...**, oppure
  doppio click sulla testata della traccia.
- **Strumenti personalizzati**: menu **Suoni → Gestisci strumenti**.
  Lo strumento si sceglie **per nome** da un elenco General MIDI completo,
  raggruppato per famiglia (Pianoforti, Chitarre, Bassi, Ottoni, Ance...) e
  ricercabile digitando (es. "sax", "organ"): non serve conoscere il numero
  di programma. Scegliendo un suono vengono precompilati automaticamente
  ottava, estensione e stile di voicing piu' adatti (es. i bassi diventano
  `root_fifth`, gli ottoni `monophonic`), sempre modificabili a mano.
  Per uno strumento percussivo, spunta "Usa il canale percussioni (10)"
  invece di scegliere un suono.
  Parametri disponibili: nome (una sola parola), ottava predefinita,
  estensione (nota MIDI minima e massima suonabile) e stile di voicing per
  gli accordi:
  - `spread`: distribuisce tutte le note dell'accordo (adatto a piano/chitarra)
  - `root_fifth`: solo fondamentale (+ quinta se presente), adatto al basso
  - `monophonic`: solo la fondamentale, per strumenti melodici monofonici
  - `root_only`: solo la fondamentale
- **SoundFont per singolo strumento**: da **Suoni → Gestisci
  strumenti...** puoi anche assegnare un file `.sf2` diverso da quello
  predefinito a un singolo strumento (predefinito o personalizzato) — vedi
  sezione 12.4 piu' sotto.

### 7.1 Caricamento automatico degli strumenti personalizzati

Quando salvi un progetto che usa uno o piu' strumenti personalizzati, la
loro definizione (program GM, ottava, estensione, voicing...) viene
**incorporata direttamente nel file `.st`**, in un blocco `Strumento
Nome:` scritto prima dei pattern e delle tracce. Cosi', se apri quel
progetto su un'altra installazione (o dopo aver ripulito la tua
configurazione locale) e lo strumento non e' ancora disponibile, viene
**registrato automaticamente** al volo, e la traccia che lo usa non va
persa. Il programma mostra un avviso con l'elenco degli strumenti caricati
in questo modo.

Se sul sistema esiste gia' uno strumento con lo stesso nome, la
definizione incorporata nel file **non lo sovrascrive** nell'elenco degli
strumenti (le tue modifiche fatte a mano restano), ma **per le tracce di
quel brano vale la definizione del file**: un brano suona sempre come e'
scritto, anche se prima hai aperto un altro brano che definisce in modo
diverso uno strumento con lo stesso nome (per esempio "Archi" o "Viole").

Questo vale anche per le tracce rinominate con **Modifica nome/strumento**:
se il nome della traccia non coincide piu' con lo strumento (es. una
traccia "Guitar 1" rinominata in "SoloRinominato" e passata a un altro
strumento), il file usa automaticamente un'intestazione esplicita
(`Traccia SoloRinominato [Bass]:`) invece della forma abbreviata, cosi' che
niente vada perso al salvataggio.

## 8. Mixer

Ogni traccia ha **Mute (M)**, **Solo (S)**, **Volume** e **Pan**. Se almeno
una traccia e' in Solo, in riproduzione/esportazione suonano solo le tracce
in Solo (che non siano anche Mute).

I controlli stanno nella **testata** di ogni traccia, uguale nelle due
viste: nella vista Struttura brano a sinistra di ogni riga, nella vista
Testo nella colonna **Tracce** a sinistra (li' serve anche a scegliere la
traccia di cui modificare il testo). La testata contiene:

- nome e strumento, **M**, **S**, **●** (solo tracce audio: registra),
  **FX** (apre il pannello Effetti, vedi 8.3 e 8.4) e il menu
  **⋯** con tutte le azioni della traccia (genera, suona con la tastiera,
  importa MIDI o audio, nome e strumento, esporta MIDI, rimuovi);
- a destra, due manopole: **Vol** (volume, il valore in %) e **Pan**
  (C = centro, L/R = sinistra/destra). Si girano trascinando su/giu' (con
  Maiusc piu' fine), con la rotellina o con le frecce; doppio click = torna
  a 100% / al centro.

Click sulla testata = seleziona la traccia; doppio click = rinomina/cambia
strumento; tasto destro = stesso menu di ⋯. Sotto l'ultima testata,
**+ Aggiungi traccia** (vedi sezione 7).

### 8.1 Volume: 0-200%, scala direttamente la velocity delle note

La manopola Volume va da 0% a 200%, dove **100% e' l'intensita' originale**
delle note cosi' come scritte nella traccia (nessuna modifica). Girare la
manopola scala direttamente la velocity di ogni nota della traccia in
esportazione/riproduzione — non solo il Channel Volume MIDI (CC7), la cui
curva di risposta su molti synth e' debole o poco percepibile. Questo rende
il controllo efficace su qualunque motore di riproduzione:

- sotto 100%: la traccia suona piu' piano dell'originale;
- sopra 100% (fino a 200%): la traccia viene rinforzata oltre l'originale,
  utile per far emergere uno strumento troppo debole nel missaggio;
- la velocity risultante resta comunque nei limiti MIDI validi (1-127).

Le impostazioni di Volume, Pan, Mute e Solo di ogni traccia vengono salvate
nel file `.st` (blocco `Mixer <Nome traccia>:`) e ripristinate
automaticamente alla riapertura del progetto.

### 8.2 Volume master

Oltre al Volume di ogni singola traccia (8.1), la toolbar principale ha uno
slider **Master** (0-200%, stessa scala e stessa convenzione: 100% =
guadagno originale) che scala insieme il volume di **tutte** le tracce, in
aggiunta al volume gia' impostato su ciascuna — utile per un aggiustamento
generale del livello senza dover toccare ogni traccia singolarmente. Come
per Mute/Solo/Volume/Pan di traccia, una modifica al Master a riproduzione
in corso riavvia automaticamente la riproduzione dalla posizione corrente
con il nuovo valore applicato (con un breve debounce se lo si trascina col
mouse, per non accodare un riavvio per ogni singolo tick). Il valore
master si salva nel file `.st` (riga `Master: N`, scritta solo se diversa
dal 100% predefinito) e si ripristina alla riapertura del progetto.

### 8.3 Riverbero e chorus (FX)

Il pulsante **FX** di ogni traccia, nella sua testata (in entrambe le
viste), apre in fondo alla finestra il **pannello Effetti** (vedi 8.4). Per
le tracce di testo la prima card, **Invio rapido**, contiene gli effetti
del synth:
- **Riverbero** (0-100%): quanta parte della traccia va al riverbero, da
  asciutta (0%) a molto "bagnata";
- **Chorus** (0-100%): allarga e "raddoppia" il suono (archi, pad, chitarre
  pulite, cori);
- **Ambiente**, uno per **tutto il brano**: lo spazio in cui tutte le tracce
  mandano il loro riverbero. Stanza piccola (predefinito), Sala, Sala grande
  o Chiesa.

Il pulsante FX si accende (azzurro) quando la traccia ha riverbero, chorus
o effetti della catena, e il suo suggerimento ne mostra i valori.

Sono gli effetti già presenti nel synth (fluidsynth): si sentono subito con
il normale ascolto, senza rielaborazioni in più, e a riproduzione in corso
l'ascolto riparte da solo come per volume e pan.
- **Salvataggio:** riverbero e chorus finiscono nel blocco `Mixer` della
  traccia (`riverbero: 35 chorus: 10`), l'ambiente nella riga
  `Ambiente: sala` in testa al file. Entrambi si scrivono solo se diversi dal
  predefinito, quindi i progetti che non li usano restano identici.
- **Export:** riverbero e chorus valgono per l'ascolto e per gli export WAV
  e MIDI (controller CC91 e CC93). L'ambiente vale solo per ascolto e WAV:
  il file MIDI non lo può contenere, e il lettore che lo apre usa il suo.
- **Import MIDI:** un file con riverbero e chorus impostati sui canali
  (CC91/CC93 a inizio brano) li porta nelle tracce importate.

Da sapere:
- **Stanza piccola:** è l'ambiente di sempre di fluidsynth (così i progetti
  esistenti suonano come prima), ma il riverbero ci si sente appena. Per un
  effetto chiaro scegli **Sala** o **Sala grande**: la card lo ricorda
  quando alzi il riverbero con la stanza piccola.
- **Cambio di ambiente:** anche con il riverbero a 0 cambiare ambiente può
  modificare leggermente il suono, perché alcuni SoundFont mandano già da
  soli una parte dei loro strumenti al riverbero.
- **Tracce audio:** non hanno l'Invio rapido, perché questi effetti
  appartengono al synth, che suona solo le tracce di testo; hanno però la
  catena di effetti (8.4).
- **Suona con la tastiera:** l'ascolto dal vivo non applica ancora
  riverbero e chorus della traccia.

### 8.4 Catena di effetti e pannello Effetti

Ogni traccia, di testo o audio, può avere una **catena di effetti**: il
suono della traccia passa da un effetto al successivo, da sinistra a
destra. Gli effetti disponibili, divisi per famiglia nel menu **+ Effetto**:

- **Dinamica:**
  - **Compressore** (soglia, rapporto, attacco, rilascio, guadagno): rende
    il livello più uniforme (voce, basso, batteria);
  - **Limiter** (guadagno, tetto, rilascio): alza il volume della traccia
    di "Guadagno" senza che i picchi superino mai il "Tetto" (es. −1 dB).
    Preset Sicurezza (solo protezione dai picchi), Più forte, Molto forte;
  - **Noise gate** (soglia, rapporto, attacco, rilascio): ammutolisce la
    traccia quando scende sotto la soglia, per togliere fruscio, ronzio e
    rumori tra una frase e l'altra nelle tracce audio registrate. Se taglia
    l'inizio o la fine delle note, abbassa la soglia o allunga il rilascio.
- **Tono:**
  - **EQ a 3 bande** (bassi, medi, alti, ±12 dB ciascuno);
  - **Filtro passa-alto** (frequenza 20 Hz–2 kHz, pendenza 6–24 dB/ottava):
    toglie i bassi sotto la frequenza. Il classico uso è "Pulizia bassi"
    (80 Hz) su voce e chitarre, per lasciare spazio a basso e cassa;
  - **Filtro passa-basso** (frequenza 200 Hz–20 kHz, pendenza 6–24
    dB/ottava): toglie gli acuti sopra la frequenza, per un suono più
    scuro, ovattato o "dietro una porta". Più alta la pendenza, più netto
    il taglio.
- **Saturazione:**
  - **Amplificatore** (modello, cassa, guadagno, bassi, medi, alti,
    presenza, potenza, livello): un amplificatore da chitarra completo,
    nell'ordine preamplificatore → controlli di tono → stadio di potenza →
    cassa. I **modelli**: *Pulito* (quasi senza saturazione), *Crunch*
    (blues, rock leggero), *British* (rock classico, medi in evidenza, due
    stadi di saturazione), *High gain* (metal, bassi stretti e molta
    saturazione).

    **Bassi, Medi, Alti** (da 0 a 10, come sugli amplificatori veri) sono
    il circuito dei toni ("tone stack") degli amplificatori reali, calcolato
    dai valori dei suoi componenti: quello **Fender** per Pulito e Crunch,
    quello **Marshall** per British e High gain. Come negli originali le
    manopole si influenzano a vicenda (alzare gli Alti tocca anche i medi),
    a metà corsa i medi sono già un po' "scavati" (di più nel Fender), i
    Medi a 0 danno lo scavo profondo del metal e il volume cambia un po'
    girandole, come su un amplificatore vero.

    **Saturazione che dipende dalla frequenza.** Come negli stadi a valvole
    veri, i bassi saturano meno dei medi e degli acuti: le note basse e gli
    accordi sulle corde gravi (power chord) restano definiti invece di
    "impastarsi", mentre le note medie distorcono come ti aspetti. Più il
    modello è spinto (British, High gain) più l'effetto è marcato. Non
    toglie bassi al suono: cambia come distorcono, non quanti ce ne sono.

    **Risposta al tocco.** Anche il punto di lavoro delle valvole si sposta
    come negli amplificatori veri: sui colpi forti lo stadio perde per un
    attimo un po' di guadagno e distorce in modo asimmetrico (armoniche
    pari, più "calde"), poi in circa un decimo di secondo "respira" e torna
    com'era. Suonando piano il suono resta pulito, attaccando forte si
    sporca in modo dinamico: è l'effetto più evidente con Crunch e British
    (il suono "che risponde al plettro"), più contenuto con High gain e
    quasi assente con Pulito. Dopo ogni stadio c'è anche il filtro dei
    condensatori di accoppiamento, che toglie il "brontolio" in sub-basso
    che la distorsione asimmetrica creerebbe sotto gli accordi bassi.

    **Presenza** (0-10) regola gli acuti dopo lo stadio di potenza, come la
    manopola omonima degli amplificatori valvolari: più "aria" e mordente
    senza rendere aspro il preamplificatore.

    **Potenza** (0-100%) è quanto si spinge lo stadio finale: le valvole di
    potenza saturano in modo morbido e asimmetrico (con armoniche pari, il
    suono "caldo" valvolare) e l'alimentazione che cede sui colpi forti
    ("sag") comprime un po' gli accordi tenuti. 0% = stadio finale pulito;
    30-50% è il suono di un amplificatore suonato a volume; oltre, il suono
    si arrotonda e comprime.

    Le **casse**: *Combo 1×12*, *2×12*, *4×12
    chiusa* (più corpo sui bassi), *Vintage 1×10* (più sottile e nasale),
    oppure *Nessuna* per il suono diretto dell'amplificatore. Le casse sono
    simulate da SoundText (nessun file da scaricare) e, come quelle vere,
    tagliano gli acuti sopra i 5-6 kHz: per questo un amplificatore suona
    "caldo" anche con molto guadagno. Preset: Pulito brillante, Blues,
    Vintage, Rock classico, Metal. "Livello" compensa il volume: più
    guadagno significa più volume, quindi abbassalo salendo col guadagno.
    Funziona su tracce di chitarra (di testo o registrate) e anche sul
    basso o su un organo per un suono più sporco.

    **Cassa da file IR.** Con la cassa **File IR…** si usa la risposta
    all'impulso (IR) di una cassa vera, registrata con un microfono: un
    piccolo file WAV (se ne trovano moltissimi gratuiti, di casse famose e
    con microfoni diversi). Scegliendo "File IR…" si apre la finestra per
    indicare il file; il pulsante **Scegli IR…** sotto i menu lo cambia, e
    accanto compare il nome del file. Il file viene letto in mono (media dei
    canali), portato a 48 kHz se ha un'altra frequenza, al massimo 1 secondo,
    e normalizzato come le casse interne, così cambiare cassa non fa saltare
    il volume. Nel file `.st` si salva il percorso (relativo alla cartella
    del progetto, come per le clip audio: `ir="ir/cassa.wav"`): tieni l'IR
    vicino al progetto se lo sposti su un altro computer. Se il file non si
    trova più, la card lo scrive in rosso e si usa la cassa Combo 1×12 finché
    non ne scegli un altro.

    **Qualità della saturazione.** Amplificatore e Distorsione saturano il
    suono a 4 volte la frequenza di campionamento (192 kHz; lo stadio di
    potenza, più morbido, a 2 volte) e poi tornano a
    48 kHz con filtri a fase lineare ("sovracampionamento"): così le
    armoniche generate dalla distorsione non si ripiegano in frequenze
    spurie, il classico "frizzare" digitale sulle note acute con molto
    guadagno. Non aggiunge ritardo; l'elaborazione è un po' più lenta
    (qualche decimo di secondo per il loop di calibrazione, qualche secondo
    in sottofondo per una traccia intera);
  - **Profilo NAM** (ingresso, cassa, livello): usa un amplificatore o un
    pedale **vero**, "catturato" con **Neural Amp Modeler** (NAM). Un
    profilo è un file `.nam`: una rete neurale addestrata ascoltando
    l'apparecchio originale, che ne riproduce il suono con grande fedeltà.
    Se ne trovano migliaia, quasi tutti gratuiti, su **Tone3000**
    (tone3000.com): amplificatori famosi, pedali di overdrive e distorsione,
    preamplificatori, a volte anche con la cassa inclusa. Per cominciare,
    **Suoni → Scarica → Scarica profili NAM consigliati...** ne scarica una
    dozzina in un colpo (vedi "Dove trovare i profili NAM", più sotto).

    Aggiungendo l'effetto (**+ Effetto → Saturazione → Profilo NAM**) si
    apre la finestra per scegliere il file; annullando, l'effetto non viene
    aggiunto. Sulla card compaiono il nome del profilo e, se il file li
    dichiara, marca, modello, tipo (amplificatore, pedale, amplificatore con
    cassa…) e autore; il pulsante **Scegli profilo…** lo cambia.
    - **Ingresso** è la manopola "input" del plugin NAM: quanto forte arriva
      la chitarra. Più alto = più saturazione (come suonare più forte o
      alzare il gain dell'apparecchio originale, fin dove la cattura lo
      permette), più basso = più pulito.
    - **Cassa**: *Nessuna / inclusa* se il profilo contiene già la cassa
      (tipo "amplificatore con cassa") o se è un pedale da mettere davanti a
      un Amplificatore; **File IR…** per aggiungere la risposta di una cassa
      vera, come nell'Amplificatore (vedi sopra). Un profilo di sola testata
      senza cassa suona aspro e "ronzante": dagli un IR.
    - **Livello** compensa il volume. Come nel plugin, SoundText porta già
      ogni profilo alla stessa sonorità di riferimento (−18 dB) usando il
      valore scritto nel file; i profili più vecchi, che non lo scrivono,
      vengono misurati nello stesso modo in cui lo fa NAM (con il suo
      segnale di riferimento), una volta sola. Così cambiare profilo non fa
      saltare il volume.

    Preset: Neutro, Più spinto (+6 dB d'ingresso), Più pulito (−6 dB).

    Da sapere sui profili NAM:
    - **Formati:** si usano i profili WaveNet di entrambe le generazioni,
      **A1** (i classici *standard*, *lite*, *feather* e *nano*, la grande
      maggioranza dei file pubblicati) e **A2** (la più recente), e anche i
      profili **LSTM**, le reti ricorrenti dei primi tempi di NAM. Molti
      file A2 contengono **più misure** dello stesso modello, dalla più
      leggera alla più completa, perché il plugin possa risparmiare CPU in
      diretta: SoundText non suona in tempo reale e usa sempre la misura
      **completa**, la migliore. Sulla card, accanto alla descrizione,
      compare "formato A2" o "formato LSTM". Il calcolo segue quello del
      motore ufficiale di NAM, verificato confrontando le uscite; con gli
      LSTM le differenze restano sotto i −80 dB (arrotondamenti dei
      calcoli, che una rete ricorrente si porta dietro nel tempo), quindi
      non udibili. Un file di un altro tipo (per esempio le rarissime
      architetture sperimentali ConvNet o Linear) non viene usato e il
      pannello spiega il motivo.
    - **Mono:** il profilo lavora in mono, come il plugin (i due canali
      vengono sommati); gli effetti "spaziali" vanno messi dopo.
    - **Velocità:** una rete neurale è più pesante dell'Amplificatore
      interno: circa un secondo per ogni ritocco nel loop di calibrazione e
      una ventina di secondi, in sottofondo, per una traccia di 3 minuti
      (profili A1 *standard* e A2; *lite*, *feather* e *nano* sono più
      rapidi, gli LSTM ancora di più: pochi secondi per 3 minuti). Il
      risultato resta in memoria come per gli altri effetti.
    - **Frequenza:** i profili sono di solito a 48 kHz, come SoundText; se
      un profilo ha un'altra frequenza il suono viene convertito prima e
      dopo.
    - **Salvataggio:** nel file `.st` si salva il percorso, relativo alla
      cartella del progetto: `nam: ingresso=3 cassa=file livello=-2
      nam="profili/Plexi.nam" ir="ir/4x12.wav"`. Tieni i profili vicino al
      progetto se lo sposti; se il file non si trova più, la card lo scrive
      in rosso e il suono passa invariato.

    **Dove trovare i profili NAM.**
    - **Profili consigliati, in un colpo:** **Suoni → Scarica → Scarica profili
      NAM consigliati...** (oppure, da terminale nella cartella di
      SoundText, `python3 scarica_profili_nam.py`) scarica 11 profili di
      amplificatori e pedali famosi, circa 3 MB in tutto, nella cartella
      **`profili_nam`** accanto a SoundText (o in `~/SoundText/profili_nam`
      se lì non si può scrivere). La cartella non fa parte del repository:
      ognuno la scarica sul proprio computer. Il comando riscarica solo i
      file che mancano e scrive nella cartella un `LEGGIMI.txt` con
      provenienza e autori. La finestra "Scegli profilo…" si apre già lì.
      I profili vengono dalla raccolta della comunità di NAM su GitHub
      (github.com/pelennor2170/NAM_models, licenza GNU GPL v3):
      - amplificatori (senza cassa: aggiungi una cassa con **Cassa → File
        IR…**): *Fender Twin Reverb - pulito* (funk, pop, arpeggi), *Vox
        AC15 - Top Boost* (il "chime" britannico), *Marshall JCM2000 -
        crunch* (rock classico), *Marshall JCM900 - lead* (hard rock e
        assoli), *Mesa Boogie Mark IV - lead* e *Peavey 5150 - high gain*
        (metal);
      - amplificatore **con cassa** (pronto, niente IR): *Bugera 333 -
        crunch con cassa*;
      - pedali, da mettere **prima** di un amplificatore (interno o
        profilo): *Ibanez TS9 Tube Screamer*, *Klon Centaur (clone)*, *Boss
        HM-2 - svedese* (death metal), e per il basso *Tech 21 dUg DP3X*.
    - **Casse per gli amplificatori senza cassa:** **Suoni → Scarica → Scarica
      casse IR per gli amplificatori NAM...** scarica 20 casse per chitarra
      (risposte all'impulso, meno di 1 MB) nella sottocartella
      **`profili_nam/casse`**, con il testo della licenza e un
      `LEGGIMI.txt`; la finestra "Scegli IR…" si apre già lì. Sono il
      pacchetto *BestPlugins Mega Pack 2* di David Fau Casquel (licenza GNU
      GPL v2 o successiva), preso dal repository di Guitarix
      (github.com/brummer10/guitarix). Ogni file porta il nome
      dell'amplificatore di cui riproduce la cassa (*Mesa Boogie Mark V*,
      *EVH 5150 III*, *Marshall JMP 2203*, *Engl Retro Tube*...). Il
      pacchetto è pensato soprattutto per i suoni distorti: con i profili
      puliti (Fender Twin, Vox AC15) prova più casse, o cercane una adatta
      su Tone3000.
    - **Tone3000** (tone3000.com), il sito di riferimento, con decine di
      migliaia di profili gratuiti (per scaricare può chiedere di creare un
      account gratuito):
      1. cerca l'apparecchio (per esempio "Plexi", "Dumble", "Rectifier",
         "Tube Screamer");
      2. tra i filtri scegli la piattaforma **NAM** e il tipo: *amp* (solo
         amplificatore: serve un IR), *full rig* (amplificatore con cassa,
         pronto) o *pedal*; ordinando per download trovi i più usati;
      3. nella pagina del profilo scarica il file (spesso uno ZIP con più
         varianti: *standard* è la qualità piena, *lite*, *feather* e *nano*
         più leggeri; SoundText li legge tutti, anche A2 e LSTM);
      4. estrai i file `.nam` nella cartella `profili_nam` (o in una
         cartella accanto al progetto) e sceglili dalla card con **Scegli
         profilo…**.
      Su Tone3000 ci sono anche gli **IR** delle casse (tipo *IR*), da usare
      con **Cassa → File IR…**.
    - **Tutta la raccolta su GitHub** (circa 260 profili, 108 MB): nella
      pagina github.com/pelennor2170/NAM_models, **Code → Download ZIP**,
      poi estrai i `.nam` che ti interessano in `profili_nam`.

    Se un profilo scaricato non suona come ti aspetti: un amplificatore
    senza cassa suona aspro finché non gli dai un IR; un pedale da solo
    suona "piccolo", va messo davanti a un amplificatore; con **Ingresso**
    trovi il punto in cui il profilo reagisce meglio al tuo segnale.
  - **Distorsione** (spinta, tono, livello, mix): da un colore
  caldo appena accennato fino al fuzz. "Spinta" è quanto si satura,
  "Tono" schiarisce o scurisce il risultato, "Livello" compensa il volume
  (la distorsione alza molto il livello), "Mix" sotto il 100% mescola il
  suono pulito a quello distorto (preset "Parallela"). Adatta a chitarre,
  basso e synth; per un suono d'amplificatore completo usa invece
  l'Amplificatore.
- **Spazio — Delay** (a tempo, tempo, ripetizioni, mix), **Riverbero** (stanza,
  smorzamento, ampiezza, mix), **Chorus** (velocità, profondità, mix) e
  **Phaser** (velocità, profondità, ritorno, mix).

  Il **Delay a tempo**: nel menu "A tempo" scegli una suddivisione (1/2,
  1/4, 1/4 puntato, 1/4 terzina, 1/8, 1/8 puntato, 1/8 terzina, 1/16) e le
  ripetizioni cadono a tempo col brano, calcolate dal suo BPM; la manopola
  Tempo si spegne e mostra i millisecondi che ne risultano. Cambiando il
  BPM del brano il delay si adegua da solo. Con "Libera (ms)" il tempo si
  regola a mano. Il calcolo usa il tempo **iniziale** del brano: con cambi
  di tempo a metà brano le ripetizioni restano quelle del tempo iniziale.
  L'1/8 puntato (preset "A tempo 1/8 puntato") è il classico eco "a
  cavallo" delle chitarre rock.

Il **pannello Effetti** si apre dal pulsante FX della traccia (per il
master, dal pulsante FX accanto allo slider Master: vedi 8.5) e resta in
fondo alla finestra (si può ridimensionare trascinando il bordo). Ogni
effetto è una **card** con:
- **⏻** per accenderlo o spegnerlo senza perdere le regolazioni;
- **◀ ▶** per spostarlo prima o dopo nella catena, **✕** per toglierlo;
- i **preset** (es. Compressore "Voce", Delay "Slapback", Riverbero
  "Cattedrale"): scelto un preset puoi ritoccarlo con le manopole, e il
  menu mostra allora **Personalizzato**;
- le **manopole**, con il valore sotto; doppio click sul valore per
  tornare al predefinito.

Nella testata del pannello:
- **Loop** (10 s, da 2 a 30): aprendo il pannello viene scelto un tratto
  da risentire mentre regoli, che diventa anche il loop A-B del brano
  (sul righello). Parte dal box selezionato della traccia, altrimenti dalla
  posizione della testina (o dal primo box della traccia);
- **▶ Ascolta il loop**: ripete il tratto; ogni ritocco si sente **dal
  giro successivo**, senza rifare il resto del brano;
- **Con le altre tracce**: nel loop suona tutto il brano, come nel mix
  finale; togliendolo si sente solo la traccia;
- **Prima / Dopo**: premuto, il loop si sente senza la catena, per
  confrontare (non cambia la traccia);
- **Copia su…**: copia la catena su un'altra traccia;
- **Annulla modifiche**: riporta effetti, riverbero, chorus e ambiente a
  com'erano quando hai aperto il pannello (le singole modifiche restano
  anche in Modifica → Annulla);
- **✕** chiude il pannello: il loop A-B torna quello di prima e la catena
  viene applicata a **tutta la traccia in sottofondo**, così il prossimo
  Play è già pronto (la barra di stato avvisa quando ha finito).

Il pulsante FX mostra quanti effetti sono accesi (es. **FX 3**).

Da sapere:
- **Come suona:** una traccia con effetti accesi viene sintetizzata a parte
  e poi elaborata; il risultato resta in memoria, quindi girare una
  manopola rifà solo l'elaborazione (frazioni di secondo), e cambiare
  un'altra traccia non la tocca. Delay e riverbero possono allungare il
  brano con la loro coda.
- **Export:** la catena vale per l'ascolto e l'export WAV; il file MIDI
  non la contiene (il lettore MIDI non ha questi effetti).
- **Salvataggio:** la catena si salva nel file `.st`, in un blocco per
  traccia:
  ```
  Effetti Chitarra:
    compressore: soglia=-20 rapporto=4 attacco=5 rilascio=120 guadagno=4 preset="Voce"
    delay: tempo=250 ripetizioni=25 mix=20 spento
  ```
  (`spento` = effetto presente ma spento). Valori fuori dai limiti vengono
  riportati nei limiti, effetti sconosciuti ignorati.
- **Requisiti:** la catena usa il pacchetto Python `pedalboard`
  (`pip install pedalboard`, già nei requisiti); senza, il pannello mostra
  solo l'Invio rapido e un avviso. L'ascolto del loop richiede lo
  streaming audio (`sounddevice`), come il loop A-B.
- **Un ascolto alla volta:** avviare il loop ferma il brano e l'ascolto
  dei box; premere Play ferma il loop.

### 8.5 Effetti sul master (mastering)

Oltre alle singole tracce, anche il **mix finale** del brano può passare
per una catena di effetti: è il "mastering", l'ultimo ritocco che rende
il brano più compatto, equilibrato e forte. Il pulsante **FX** accanto
allo slider **Master**, nella barra dei comandi, apre il pannello Effetti
sul master (etichetta "Master · mix finale"). Si usano gli stessi effetti
e le stesse card delle tracce; quelli più adatti al master sono:
- **EQ a 3 bande:** piccoli ritocchi al tono generale (±1-3 dB);
- **Compressore**, preset **Colla del mix**: compressione leggera
  (rapporto 2:1, attacco lento) che amalgama le tracce;
- **Limiter**, preset **Più forte**: alza il volume del brano senza che i
  picchi superino il tetto di −1 dB. È di solito l'ultimo della catena.

Il pulsante **+ Catena di mastering** aggiunge in un colpo questi tre
effetti, come punto di partenza da regolare a orecchio. Il pulsante FX
del master si accende e mostra quanti effetti sono attivi (es. **FX 3**).

Come per le tracce:
- il **loop di calibrazione** (10 s, dalla testina) fa risentire il mix
  di tutto il brano a ogni ritocco; **Prima / Dopo** confronta il mix con
  e senza la catena del master;
- **Annulla modifiche** riporta la catena a com'era all'apertura, e ogni
  modifica è anche in Modifica → Annulla;
- **Copia su…** copia la catena del master su una traccia; da una traccia
  si può copiare la sua catena sul master ("Master (mix finale)").

Da sapere:
- **Dove vale:** il master si applica all'ascolto del brano, all'export
  WAV del brano e alla base che si sente mentre si registra. Non si
  applica all'export di una singola traccia né all'export MIDI.
- **Anche il loop delle tracce passa per il master:** calibrando una
  traccia la senti già con la catena del master, cioè come nel brano
  finito.
- **Veloce:** il mix prima del master resta in memoria, quindi dopo un
  ritocco al solo master il Play successivo rielabora il mix già pronto,
  senza risintetizzare il brano.
- **Volume master e catena:** lo slider Master (8.2) agisce prima della
  catena, sul volume delle tracce: con un limiter sul master, alzarlo
  rende il brano più "schiacciato" ma non più forte oltre il tetto.
- **Salvataggio:** nel file `.st` la catena del master sta nel blocco
  ```
  Catena master:
    compressore: soglia=-14 rapporto=2 attacco=30 rilascio=200 guadagno=1 preset="Colla del mix"
    limiter: guadagno=6 tetto=-1 rilascio=80 preset="Più forte"
  ```
  (parola diversa da `Effetti`, così non si confonde con una traccia che
  si chiami "Master"). Senza catena il blocco non si scrive.

### 8.6 Suoni da studio con programmi esterni (re-amping)

L'amplificatore di SoundText (8.4) va bene per bozze, basi e demo. Per un
suono di chitarra da studio la via più semplice è il **Profilo NAM** (8.4),
che usa dentro SoundText le catture di amplificatori veri. In alternativa
si può far passare la traccia in un simulatore di amplificatore esterno e
poi riportarla nel brano: è il **re-amping**, utile per usare programmi
come Guitarix o i plugin commerciali.

**Il flusso, su qualunque sistema:**
1. Registra la chitarra **pulita** (ingresso INST/Hi-Z della scheda audio,
   senza amplificatore) in una traccia audio, oppure scrivila a note.
2. Tasto destro sul nome della traccia → **Esporta WAV asciutto (per il
   re-amping)...**
3. Nel programma esterno applica al file il simulatore scelto e salva il
   risultato in un nuovo WAV.
4. In SoundText crea una **traccia audio** (es. "Chitarra ampli") e
   **Importa file audio...**: su una traccia vuota la clip va all'inizio,
   quindi a tempo col brano. Metti in **Mute** la traccia originale (o
   tienile entrambe, per mescolare pulito e amplificato).

Se il simulatore aggiunge un ritardo (succede in tempo reale, non
nell'elaborazione offline), sposta di poco la clip o accorciane l'inizio
trascinandone il bordo.

**Linux — Guitarix** (gratuito, simulazione dei circuiti a valvole di
amplificatori e pedali, casse e IR): si installa dai repository della
distribuzione (`sudo apt install guitarix`, `sudo dnf install guitarix`,
`sudo pacman -S guitarix`; su alcune, come Debian e Ubuntu, i plugin LV2
sono in un pacchetto a parte, `guitarix-lv2`). I plugin LV2 di Guitarix
si possono usare **direttamente in SoundText** come effetti (8.7), senza
re-amping. Per usare Guitarix fuori da SoundText ci sono due modi:
- **offline (consigliato):** apri il WAV asciutto in **Audacity** o in
  **Ardour** e applica i plugin LV2 di Guitarix come effetto, poi esporta;
  nessun collegamento audio da configurare;
- **in diretta:** avvia Guitarix (con PipeWire, se serve, `pw-jack
  guitarix`), collega con **qpwgraph** o **Helvum** la chitarra all'ingresso
  di Guitarix e la sua uscita al registratore; per registrare
  direttamente in SoundText scegli come scheda audio l'ingresso di PipeWire.

**Windows e macOS** (Guitarix funziona solo su Linux):
- **Neural Amp Modeler (NAM)**: gratuito, plugin VST3/AU e programma a sé,
  con modelli "catturati" da amplificatori veri (file `.nam`, migliaia
  gratuiti su Tone3000) e caricamento di IR per la cassa. I profili NAM
  si possono usare anche direttamente in SoundText (Profilo NAM, 8.4), su
  tutti i sistemi, senza re-amping (A1, A2 e LSTM); il plugin serve per
  suonare in diretta;
- **AIDA-X**: gratuito, simile a NAM e più leggero, anche su Linux;
- **GarageBand** (macOS): gratuito, amplificatori e pedali già inclusi;
- per applicare un plugin al WAV asciutto va bene **Audacity** (gratuito,
  VST3 su tutti i sistemi, AU su macOS), oppure un programma di
  registrazione come **Reaper**.

In diretta, NAM e AIDA-X funzionano anche come programmi a sé: la chitarra
entra nel simulatore e SoundText registra l'uscita (con un collegamento
audio virtuale, o registrando in un altro programma e importando il file).

### 8.7 Plugin esterni (VST3 e LV2)

SoundText puo' usare i **plugin audio installati sul computer**, sia come
**effetti** nella catena di una traccia o del master, sia come
**strumenti virtuali** che suonano le note di una traccia al posto del
SoundFont.

- **VST3**: su Linux, Windows e macOS. SoundText li cerca nelle cartelle
  standard del sistema (su Linux `~/.vst3` e `/usr/lib/vst3`, su Windows
  `C:\Program Files\Common Files\VST3`, su macOS
  `/Library/Audio/Plug-Ins/VST3`); altre cartelle si aggiungono da
  **Suoni → Cartelle dei plugin VST3...**
- **LV2**: solo su Linux, e serve la libreria di sistema `lilv` (su
  Debian/Ubuntu il pacchetto `liblilv-0-0`, gia' presente se sono
  installati Ardour, Carla o Guitarix). I plugin LV2 si trovano da soli.
  Per esempio, con `guitarix-lv2` si hanno decine di amplificatori e pedali.
- I formati **CLAP** e **VST2** non sono supportati.

**Un plugin come effetto**: nel pannello Effetti (8.4) **+ Effetto →
Plugin (VST3/LV2)** apre l'elenco dei plugin di effetti installati, con la
ricerca per nome. La card del plugin ha:
- le manopole **Mix** (quanto suono elaborato mescolare a quello
  originale) e **Livello** (il volume in uscita), come gli altri effetti;
- **Parametri...**, che apre una finestra con tutti i controlli del
  plugin; le modifiche si sentono subito nel loop di ascolto del
  pannello;
- **Cambia...** per sostituirlo con un altro plugin.

Nella finestra dei parametri, **Interfaccia del plugin...** apre la
finestra grafica del plugin stesso (solo VST3). Quando la chiudi, le
regolazioni fatte li' restano nel progetto.

**Un plugin come strumento**: **Traccia → Strumento plugin → Scegli (VST3/LV2)...**,
oppure il tasto destro sul nome della traccia. Scegli uno strumento
virtuale (synth, pianoforte campionato...) e poi regola i suoi parametri.
Le note della traccia le suona il plugin: il **volume** della traccia
agisce sulla forza delle note, il **pan** sulla posizione nello stereo, e
gli effetti della traccia si applicano dopo il plugin. Per tornare al
SoundFont scegli **Nessuno: usa il SoundFont**. Sotto il nome della
traccia compare il nome del plugin.

Alcuni plugin LV2 caricano un file: per esempio sfizz LV2 suona un
**file SFZ**. Nella finestra dei parametri queste proprieta' hanno una
riga con **Sfoglia...** e **Togli**; il file scelto resta nel progetto.

**Strumento SFZ interno.** Un file `.sfz` (strumento campionato, come
quelli che scarica `scarica_strumenti.py`) si puo' suonare anche senza
plugin: nell'elenco degli strumenti scegli **Strumento SFZ (interno)...**
e poi il file. Lo suona la libreria del motore **sfizioso** (o di
**sfizz**), che si installa una volta con `python3 scarica_strumenti.py
libreria` (su Linux anche `./scarica_strumenti.sh libreria`; su Windows
`py scarica_strumenti.py libreria`, che richiede Visual Studio Build Tools
con il C++); senza, la voce compare in grigio. Questo strumento non ha
parametri: "Parametri dello strumento plugin..." fa scegliere un altro
file. Sotto il nome della traccia compare il nome del file con "(SFZ)";
se modifichi il file `.sfz`, il brano viene ricalcolato.

Il progetto `.st` ricorda il plugin di ogni traccia e di ogni effetto,
con i suoi parametri. Aprendo il progetto su un altro computer, i VST3
vengono cercati per nome del file nelle cartelle dei plugin.

**Se un plugin non funziona.** I plugin girano in un processo separato da
SoundText: se uno si blocca o si chiude in modo anomalo, SoundText resta
aperto. Il plugin viene segnato come **"non risponde"** fino al prossimo
avvio dell'app. Un effetto che non funziona lascia passare il suono
invariato. Una traccia il cui strumento plugin non funziona suona con il
SoundFont, e il motivo finisce nel file di log (Aiuto). Alcuni plugin non
si possono proprio caricare: nell'elenco compaiono in grigio, con il
motivo accanto (per esempio "non risponde", o un plugin che accetta solo
audio mono).

**Limiti**:
- gli strumenti plugin suonano nell'ascolto del brano, nel loop del
  pannello Effetti e nell'export WAV; le anteprime veloci (nota della
  tastiera, ascolto di un pattern, accordo scelto con il doppio click)
  usano ancora il SoundFont;
- l'export MIDI e MusicXML contiene le note, non il suono del plugin;
- dei plugin LV2 si salvano i valori dei parametri e i file scelti, non
  il resto dello "stato" interno;
- la prima ricerca dei plugin carica ogni VST3 una volta, e puo' volerci
  un po'; poi l'elenco si ricorda finche' un plugin non cambia
  (**Aggiorna elenco** rifa' la ricerca).

## 8bis. Struttura brano (vista a box)

Un modo alternativo all'editor di testo lineare per lavorare sulla
**struttura** del brano (intro/verse/chorus/assolo...) invece che nota per
nota: ogni traccia diventa una riga su un unico asse del tempo condiviso,
e il suo contenuto e' suddiviso in **box** — rettangoli trascinabili
orizzontalmente, ciascuno autosufficiente come il corpo di un pattern
(sezione 4), con un proprio nome e una propria posizione nel tempo. Il
contenuto effettivo di ogni traccia (`Track.text`, quello che
playback/export/validazione leggono davvero) resta sempre ricalcolato
automaticamente dalla sequenza dei suoi box: lavorare a box non e' "un
altro formato", e' solo un modo diverso di scrivere lo stesso testo.

**Attivazione**: pulsanti **Struttura** / **Testo** nella barra dei
comandi, oppure menu **Vista → Struttura brano (a box)** (scorciatoia
`Ctrl+Shift+B`): alternano questa vista e l'editor di testo lineare
classico. E' la vista con cui SoundText si apre di default.

Il colore di ogni box (e della striscia a sinistra della testata della
traccia) riflette la famiglia dello strumento (basso, chitarra, fiati,
ecc.), la stessa convenzione usata altrove nell'app (es. sezione 7). Le
testate contengono anche il mixer della traccia (vedi sezione 8).

### Creare un box

Doppio click su un punto vuoto di una riga apre l'editor di un nuovo box
in quella posizione (stessa finestra di modifica descritta sotto). Il
tasto destro su un punto vuoto offre in piu':

- **Nuovo box da tastiera qui** / **Nuovo box da audio qui** / **Importa
  MIDI qui**: stessi flussi di "Suona con la tastiera"/"Importa
  audio"/"Importa MIDI" della sezione traccia (sezioni 10, 10bis, 10ter),
  ma il risultato diventa un nuovo box invece di sostituire tutta la
  traccia.
- **Genera batteria in questa traccia...** / **Genera basso da accordi in
  questa traccia...** (sezione 9bis): visibili solo se lo strumento della
  traccia e' rispettivamente percussivo o un basso; il box generato viene
  accodato subito dopo l'ultimo box gia' presente.
- **Incolla qui**: solo se e' stato prima tagliato o copiato un box (vedi
  sotto).
- **Importa da .box...**: carica un box salvato in precedenza (vedi più
  sotto "Esportare/importare un singolo box").

Le stesse azioni "Genera batteria/basso" sono raggiungibili anche col
tasto destro sull'etichetta della traccia a sinistra.

### Spostare, selezionare, modificare

- **Trascinare** un box lo riposiziona nel tempo sulla STESSA traccia
  (per spostarlo su un'altra traccia si usa taglia/incolla, non il
  trascinamento): la posizione si aggancia sempre al beat intero più
  vicino, e una linea guida verticale attraversa tutte le tracce durante
  il trascinamento per allineare a vista box di tracce diverse. Se il
  punto scelto si sovrappone a un altro box della stessa traccia, si
  aggancia automaticamente al bordo libero più vicino invece di
  sovrapporsi.
- **Click singolo** seleziona un box (bordo evidenziato in colore
  d'accento) senza spostarlo, anche se il box non era già su un beat
  intero (es. dopo una tuplet, sezione 2.1bis): un piccolo movimento
  involontario del mouse tra la pressione e il rilascio non conta come
  trascinamento.
- **Doppio click** su un box apre l'editor dedicato del suo contenuto
  (stesso editor di testo con evidenziazione sintattica, autocompletamento
  e Play/Stop di anteprima usato per i pattern, sezione 4) con nome e
  testo del box, validati prima di poter confermare.

### Menu tasto destro su un box

- **▶ Play** / **■ Stop**: riproduce (o ferma) l'anteprima del contenuto
  del box con lo strumento della sua traccia — motore di anteprima
  dedicato, indipendente dal trasporto principale F5/F6. Se il box usa
  un'ancora `bar=N`, l'anteprima lo suona dal suo punto del brano, cosi'
  l'ancora porta alla battuta giusta (lo stesso vale per **▶ Play** su una
  selezione).
- **Trasponi...**: trasposizione per semitoni di tutto il contenuto del
  box. I richiami a pattern e file MIDI si trasportano con il suffisso:
  `%Giro` diventa `%Giro+2`, `&"Riff"+1` diventa `&"Riff"+3` (il pattern
  resta com'e', perche' lo possono usare anche altri).
- **Rinomina...**
- **Duplica**: crea una copia sulla stessa traccia, subito dopo la fine
  del box originale (o nel primo spazio libero disponibile da lì).
- **Taglia** / **Copia** / **Incolla qui**: gli appunti valgono anche tra
  tracce diverse (è così che si sposta un box su un'altra traccia).
- **Esporta come .box...** / **Importa da .box...** (sul punto vuoto):
  vedi sotto.
- **Elimina**.

### Annulla/Ripeti (Ctrl+Z / Ctrl+Y)

Ogni azione che modifica i box di una traccia — spostare, creare (in
qualunque modo), modificare, trasporre, rinominare, duplicare,
tagliare/eliminare, incollare, importare da `.box` — è annullabile con
`Ctrl+Z` e ripetibile con `Ctrl+Y`, come ogni altra modifica al progetto
(vedi **1.2 Annulla/Ripeti**). Selezionare o riprodurre un box non genera
invece nulla da annullare.

### Ascoltare solo il box selezionato

C'e' un solo trasporto: **Play/Stop** nella barra dei comandi suonano il
brano intero. Per ascoltare solo il box selezionato (clic su un box per
selezionarlo): **Shift+Spazio**, oppure **Riproduzione → Ascolta il box
selezionato**, oppure tasto destro sul box → **▶ Play**. Premuto di nuovo
durante l'ascolto mette in pausa; ancora una volta riprende dal punto di
interruzione, se nel frattempo non hai selezionato un box diverso (in quel
caso riparte da capo su quello nuovo). **Stop** ferma anche l'ascolto del
box, e avviare il brano con **Play** lo interrompe: si sente sempre una cosa
alla volta. Shift+Spazio vale nella vista Struttura: nell'editor di testo
resta un normale spazio.

### Suggerimenti

Sopra le testate delle tracce, **? Come si usa** riassume i comandi della
vista (passandoci sopra col mouse, o cliccando). Le righe ancora vuote
mostrano in grigio cosa si puo' fare: creare un box, importare o registrare
audio (tracce audio), oppure che la traccia e' scritta a testo libero.

### La testina di riproduzione

Durante l'esecuzione dell'intero brano (trasporto principale, sezione
12), una linea verticale attraversa tutte le tracce seguendo il punto in
esecuzione, e il canvas scorre in orizzontale quanto basta per tenerla
sempre visibile — indipendentemente da quale box sia selezionato.

### Esportare/importare un singolo box

**Esporta come .box...** (menu di un box) salva il suo contenuto in un
file di testo leggibile a mano (stesso stile del formato `.st`, sezione
11, ma a blocco singolo) nella cartella `songs/` (sezione 5bis).
**Importa da .box...** (menu di un punto vuoto) lo ricarica come nuovo
box in qualunque punto/traccia — utile per riusare una sezione (es. un
ritornello) tra progetti diversi.

### Conversione automatica in box

Importando un intero file MIDI o convertendo audio in una traccia già a
box, il testo risultante viene automaticamente suddiviso in più box dove
compare una pausa continua di più di 3 beat, invece di restare un unico
grande box — così il contenuto è subito organizzato in modo leggibile
anche per un file lungo, senza bisogno di risistemarlo a mano.

### Tracce in testo libero

Una traccia senza box (testo libero) nella vista Struttura brano non mostra
nulla: **Modifica testo libero...**, ultima voce del menu del tasto destro
sul suo nome, apre il suo testo intero nello stesso editor dei box
(evidenziazione, Play, Play della selezione), senza uscire dalla vista. La
modifica si annulla con Ctrl+Z.

**Converti in testo libero...** (al suo posto, per una traccia che ha già
dei box) riporta
quella traccia a un editor di testo lineare unico: il contenuto musicale non
cambia, cambia solo il modo di editarlo. È irreversibile solo nel senso che
non tornerà automaticamente a essere suddivisa in box: il testo resta
comunque libero di essere ri-suddiviso a mano.

## 9. Congelare gli accordi

Il pulsante "Congela accordi in note esplicite" nell'editor sostituisce ogni
accordo astratto della traccia corrente con il blocco `[...]` di note
concrete generato dal motore di voicing per lo strumento assegnato.

### 9.1 Scegliere il voicing con un doppio click

Un **doppio click su un accordo** — sia in forma compatta (`Cmaj7`, anche
con un moltiplicatore, es. `2Cmaj7`) sia già "congelato" in note esplicite
(`[c*3 g*3 b*3 e*4]`, se riconoscibile come accordo standard), **anche se
l'accordo si trova dentro un gruppo di ripetizione `N(...)`** (vedi 2.1) —
nell'editor della traccia o nel corpo di un pattern apre un piccolo menu
con tutte le alternative di voicing sensate per lo strumento corrente
(vedi 2.8), ciascuna con un'anteprima testuale delle note risultanti.
Scorrendo le voci con le frecce si sente un'anteprima audio di ognuna (con
un breve ritardo, dovuto al rendering); **Invio** o click su una voce
applica la scelta (sul token implicito aggiunge/cambia solo il suffisso
`.stile`; sul blocco esplicito ricalcola le note), **Esc** o click fuori
dal menu annulla senza modificare nulla. Se il blocco `[...]` non
corrisponde a nessuna qualità di accordo nota (es. una semplice quinta
`[c*3 g*3]`, ambigua tra maggiore e minore), un tooltip lo segnala e il
menu non si apre.

### 9.2 Autocompletamento durante la digitazione

Mentre si scrive, l'editor propone in un popup i token completi
pertinenti al frammento già digitato, per velocizzare le notazioni più
lunghe o meno immediate da ricordare a memoria:

- qualità d'accordo (`C7`, `Dm7b5`...) a partire dalla fondamentale;
- stili di voicing (`Cmaj7.drop2`, `C7.cagEd`...) dopo il `.`, limitati a
  quelli applicabili allo strumento della traccia corrente (vedi 2.8);
- nomi di percussione, dinamiche (`mf`, `ff`...) e comandi di stato
  (`SON`, `SOFF`, `r`);
- riferimenti `%Nome` a pattern definiti nel progetto e `&"Nome"` alla
  libreria MIDI (vedi 6 e 11.1).

Frecce su/giù per scorrere le proposte, **Invio** o **Tab** per accettare
quella evidenziata, **Esc** o click fuori per chiudere il popup senza
modificare nulla. Le singole note (es. `c`, `g#*4`) non generano
suggerimenti propri, essendo già brevi quanto un suggerimento.

## 9bis. Genera batteria/basso (senza IA)

Generazione di una linea di batteria o basso senza modelli/download/GPU:
algoritmica, basata su una piccola libreria di pattern per genere (batteria)
e sulla lettura degli accordi già scritti in un'altra traccia (basso).
Istantanea e senza dipendenze pesanti.

**Variabilità** (in entrambi i dialoghi): un cursore da 0% a 100% (predefinito
35%) decide quanto si allontana il risultato dal disegno di base dello stile.
A 0% lo stesso stile dà sempre lo stesso testo; più in alto il generatore
aggiunge variazioni:
- **Batteria**: rullanti fantasma a volume basso e cassa in più (solo negli
  spazi vuoti: i colpi del disegno restano al loro posto), colpi di
  charleston/ride che saltano, velocity leggermente diverse a ogni battuta,
  fill a metà battuta o sull'ultimo beat invece che sempre completi.
  Molti stili hanno anche **giri alternativi** (es. il rock con la cassa
  sincopata, il reggae «steppers», il funk con un'altra cassa): all'inizio
  di ogni gruppo di battute il giro può passare a uno di questi, e i fill si
  scelgono fra quello dello stile e alcuni fill generici (rullata di
  rullante, discesa sui tom, colpi all'unisono...).
- **Basso**: il trattamento alternativo (note di avvicinamento, terza e
  settima) scatta anche fuori dal ritmo di «Variazione ogni N accordi»; le
  note dopo la prima di un accordo possono allungarsi, tacere o salire
  d'ottava. La prima nota di ogni accordo (la fondamentale) non cambia mai, e
  la durata dell'accordo resta identica. Ogni tanto una battuta usa un
  **disegno alternativo** dello stile (es. le ottave in sincope, il two-feel
  con la quinta anticipata): la scelta si fa battuta per battuta, quindi
  anche un accordo lungo (le 4 battute di tonica del blues) cambia ritmo al
  suo interno. Vale anche per accompagnamento e riff.
  La variabilità non solo toglie ma **aggiunge**:
  - **note di passaggio** (basso e riff): a fine accordo una nota che porta
    alla fondamentale del successivo — mezzo tono sotto o sopra, un tono
    sotto o la sua quinta. Se l'ultima nota è lunga, la nota di passaggio si
    aggiunge nel suo ultimo tempo; altrimenti ne prende il posto;
  - **anticipi sincopati** (basso, accompagnamento e riff sulle griglie a
    ottavi o terzine): la prima nota o il primo accordo del giro successivo
    arriva un ottavo prima, legato oltre il cambio d'accordo, come nel pop,
    nel rock e nel latin. Per questo la fondamentale può iniziare un ottavo
    prima della battuta invece che sul primo tempo.
  Con l'intensità **Leggera** niente note di passaggio né anticipi.

**Intensità** (batteria, basso, accompagnamento e riff): come deve «pesare»
la parte nel brano.
- **Leggera (strofa, intro)**: meno colpi e meno note — la batteria toglie i
  colpi di charleston/ride in levare e le note fantasma e suona più piano;
  basso e accompagnamento tengono solo gli attacchi sul 1 e sul 3 (le note
  rimaste durano di più).
- **Normale**: il disegno dello stile così com'è.
- **Piena (ritornello)**: la batteria passa dal charleston al ride, suona più
  forte e apre ogni gruppo di battute con un crash; gli accordi
  dell'accompagnamento prendono anche l'ottava sopra e il basso sale d'ottava
  sull'ultimo attacco di ogni accordo.
- **In crescendo**: leggera nel primo terzo della parte, normale nel secondo,
  piena nell'ultimo — utile per un bridge o un pre-ritornello.

Il pulsante **🎲 Nuova variazione** estrae una variazione diversa con gli
stessi controlli. La variazione è legata a un «seme» che resta fisso finché non
lo premi: cambiare stile, battute o ottava non la fa «saltare», e a parità di
controlli il testo è riproducibile. Il testo generato si può comunque
modificare a mano nell'anteprima prima di confermare.

**Preset e dettagli della variabilità.** Accanto al cursore, un menu con tre
preset:
- **Fedele**: 15%, soprattutto dinamica, poche note e ritmi cambiati;
- **Musicista** (predefinito): 35%, variazioni come quelle di un turnista;
- **Creativo**: 75%, molte variazioni, per cercare idee.

Il menu mostra «Personalizzata» quando i valori non corrispondono a un
preset. **Dettagli ▸** apre tre cursori che dicono quanta parte della
variabilità va a ciascun aspetto (100% = tutta):
- **Ritmo**: giri e ritmi alternativi, fill, anticipi, note o colpi che
  saltano, si allungano o si aggiungono (la cassa extra della batteria);
- **Note e armonia**: varianti del disegno, note di passaggio, salti
  d'ottava, i rullanti fantasma della batteria; nel giro armonico i colori
  e le sostituzioni degli accordi (è l'unico aspetto del giro armonico);
- **Dinamica**: velocity diverse colpo per colpo e nota per nota. Per basso,
  accompagnamento e riff la dinamica aggiunge le velocity (`N@`), più forti
  sul primo tempo della battuta e più deboli sui levare; a 0% le note non ne
  hanno, come prima.

Per esempio, con la variabilità al 60% e Ritmo e Note a 0% le note restano
quelle del disegno e cambia solo come vengono suonate.

**Rigenera solo alcune battute.** Sotto l'anteprima: «Rigenera solo le
battute da N a M» e **🎲 Rigenera queste** estraggono una nuova variazione
solo per quelle battute, tenendo le altre come sono. Si può ripetere su
battute diverse; i ritocchi restano anche cambiando gli altri controlli
(stile, intensità...), **↺ Annulla ritocchi** li toglie e **🎲 Nuova
variazione** rigenera tutto da capo. Il taglio non spezza mai una nota: se
una nota attraversa l'inizio o la fine del tratto (un anticipo, un accordo
lungo) il tratto si allarga fino a comprenderla. Con la variabilità a 0% il
pulsante è disattivato (il risultato sarebbe identico).

**Componi → Genera nella traccia selezionata → Batteria...** (richiede una traccia
percussiva selezionata):
- **Stile**: il dialogo propone gli stili scritti per la metrica del
  progetto. In 4/4: Rock, Funk, Four-on-the-floor (disco), Reggae (one drop),
  Punk, Soul (Motown), Bossa nova, Rock'n'roll, Shuffle (blues), Swing
  (jazz), Hip-hop (boom bap), Half-time, Metal (doppia cassa), Country
  (train beat), Samba, Cha-cha-cha e Marcia; in 3/4: Valzer e Valzer jazz;
  in 5/4: Rock in 5/4 (3+2) e Jazz in 5/4 (terzine); in 6/8: Ballata e
  Afro-cubano; in 7/8: Rock in 7/8 (2+2+3) e Balcanico in 7/8 (3+2+2); in
  12/8: Slow blues e Slow rock anni '50. Gli stili in 7/8 usano la griglia a
  ottavi (`8:`). Ogni
  stile porta con se' la sua griglia ritmica: la maggior parte usa i
  sedicesimi (`16:`), Shuffle e Swing le terzine di ottavo (`8T:`), che e' cio'
  che ne produce il caratteristico "dondolo". Non c'e' un selettore di
  griglia nel dialogo: un giro e' scritto per una griglia precisa e non si
  puo' riadattare a un'altra senza cambiarne il ritmo. In 6/8 e 12/8 la
  griglia e' a ottavi (`8:`). Nota: gli strumenti che suonano nello stesso istante condividono la
  velocity (limite della notazione a blocchi `[...]`).
- **▶ Ascolta / ■ Stop**: riproduce l'anteprima cosi' com'e' scritta (anche
  dopo una tua modifica a mano) prima di confermare. Con **Con le altre
  tracce** spuntato la senti insieme al resto del progetto (i Mute restano
  rispettati, il Solo no; il contenuto attuale della traccia di destinazione
  non viene suonato); senza spunta suona da sola. Mentre suona, nell'anteprima
  è evidenziato il punto che stai ascoltando (se modifichi il testo durante
  l'ascolto, l'evidenziazione si sospende fino al prossimo Ascolta). Ok,
  Annulla o la chiusura della finestra fermano l'ascolto. Vale anche per
  **Genera basso**, **Genera accompagnamento/riff** e **Genera giro
  armonico**.
- **Battute**: quante generarne.
- **Fill ogni N battute**: ogni N battute inserisce un fill (con un
  crash di rientro alla battuta successiva) invece di ripetere identico il
  giro base — 0 disattiva i fill. Non inserisce mai un fill
  sull'ultima battuta generata (chiude sempre sul giro base).
- **Fill a frasi** (spuntato di default): come un batterista vero, alla fine
  di ogni gruppo di N battute fa un fill **piccolo** (solo l'ultimo beat) e
  alla fine di ogni frase di 2×N battute un fill **completo**. Senza spunta
  i fill sono tutti completi.
- **Finale sull'ultima battuta**: l'ultima battuta diventa un colpo di
  chiusura (crash e cassa sul primo tempo, poi silenzio), per terminare il
  brano o la sezione.
- **Intensità**: vedi sopra.

**Componi → Genera nella traccia selezionata → Giro armonico...** (richiede uno
strumento polifonico: pianoforte, chitarra, organo, pad...): scrive una
progressione di accordi come simboli (`Am7`, `G`...), che il motore voca da
solo per lo strumento della traccia. È il punto di partenza quando il brano
non ha ancora accordi: basso, accompagnamento e riff hanno bisogno di una
traccia di accordi da seguire. Nella vista Struttura brano la voce compare
nel menu del tasto destro di una traccia polifonica finché nessun'altra
traccia del brano contiene accordi: la traccia che il giro ce l'ha già
continua a proporlo, e ogni nuovo giro va in un box dopo l'ultimo (come per
**Genera basso**). Al contrario, **Genera accompagnamento** e
**Genera riff/melodia** compaiono solo quando un'altra traccia ne contiene
(dal menu Componi, senza accordi, un messaggio rimanda al giro armonico).
- **Tonalità**: parte da quella del progetto; se il progetto non ne ha
  una impostata e la traccia ha già un giro, dalla tonalità del box dopo
  cui verrà messo quello nuovo (riconosciuta dai suoi accordi o dalle sue
  note); altrimenti da Do maggiore. Gli stili proposti sono quelli del suo modo:
  - maggiore: **Pop** (I-V-vi-IV), **Anni '50 / doo-wop** (I-vi-IV-V),
    **Rock** (I-IV-I-V), **Canone di Pachelbel**, **Blues 12 battute**,
    **Jazz II-V-I**, **Turnaround jazz** (I-vi-ii-V), **Tre accordi**
    (I-IV-V-I), **Ballata** (I-iii-IV-V), **J-pop / royal road**
    (IV-V-iii-vi-ii-V-I), **Rock misolidio** (I-bVII-IV-I), **Gospel**
    (I-I7-IV-iv), **Circolo delle quinte**, **Rhythm changes**, **Blues
    jazz 12 battute**;
  - minore: **Pop minore** (i-VI-III-VII), **Cadenza andalusa**
    (i-VII-VI-V), **Rock minore** (i-VII-VI-VII), **Cadenza minore**
    (i-iv-i-V7), **Jazz II-V-I minore**, **Blues minore 12 battute**,
    **Minore semplice** (i-iv-v-i), **Minore epico** (i-VI-VII-i), **Vamp dorico** (i7-IV7), **Line cliché** (la voce che scende
    cromatica dentro l'accordo minore), **Circolo minore**, **Frigio**
    (i-bII).
  I gradi abbassati (bVII del misolidio, bII del frigio) sono scritti con i
  bemolle (`Bb` in Do, non `A#`), tranne nelle tonalità con i diesis.
- **Durata di ogni accordo**: mezza battuta, una o due (moltiplica la
  durata dello stile: nel blues alcuni accordi durano più battute).
- **Battute**: il giro si ripete fino a coprirle; **Giro intero** lo scrive
  una volta sola. Di default copre la musica già presente nelle altre tracce.
- **Variabilità**: a 0% lo stile così com'è. Più in alto:
  - gli accordi si arricchiscono (settime, none, sus) restando della
    stessa funzione;
  - **dominanti secondarie**: un accordo lungo almeno una battuta lascia la
    seconda metà alla dominante dell'accordo successivo (in Do: `A7` prima
    di `Dm`, `E7` prima di `Am`); se dura almeno due battute, la sua ultima
    battuta può diventare un **II-V** verso di esso (`Bm7b5 E7` prima di
    `Am`). L'ultimo accordo del giro non viene preparato così, a meno che
    non sia la tonica: altrimenti suonerebbe come un cambio di tonalità;
  - **sostituto di tritono**: una dominante che scende di quinta diventa
    quella a un tritono di distanza (`Db7` al posto di `G7` prima di `C`),
    mai l'accordo di tonica (il `C7` del blues resta);
  - **IV minore** (in maggiore): il IV che torna al I prende in prestito la
    iv minore (`F Fm6 C`).
  Gli accordi cromatici si scrivono in bemolle (`Db7`), tranne nelle
  tonalità con i diesis.
- **Cadenza finale** (non spuntata di default, per lasciare il giro aperto
  e pronto a ripetersi): l'ultima battuta diventa l'accordo di tonica,
  preceduto per mezza battuta da un accordo di cadenza. A 0% è sempre `V7`;
  con la variabilità può essere anche plagale (`IV`), iv minore (`Fm6`),
  «backdoor» (`Bb7`) o `V7sus4`, in minore `V7`, `iv` o `VII`. I giri che
  non partono dalla tonica (II-V-I, royal road) chiudono sempre con la
  dominante o il suo sostituto di tritono, perché è quella a stabilire la
  tonalità.

**Componi → Genera nella traccia selezionata → Basso da accordi...** (richiede
un'altra traccia nel progetto con accordi già scritti):
- **Accordi da**: quale traccia fornisce la sequenza armonica da seguire
  (le note singole/percussioni/pause in quella traccia vengono ignorate,
  solo gli accordi contano: sia scritti come simbolo, es. `Cmaj7`, sia come
  blocco `[c*4 e*4 g*4]` di almeno due note, che e' come li scrive l'import
  MIDI; il blocco e' riconosciuto come accordo noto, altrimenti la
  fondamentale e' la nota piu' bassa). Una traccia fatta solo di note
  singole (melodia, arpeggi) non ha accordi da seguire.
- **Stile** (ognuno scrive la sua griglia ritmica: quarti, ottavi o, per lo
  shuffle, terzine di ottavo):
  - **Fondamentale**: ripete la tonica per tutta la durata dell'accordo.
  - **Fondamentale/quinta**: le alterna.
  - **Walking bass**: cammina sui gradi dell'accordo con una nota di
    avvicinamento cromatico all'accordo successivo (semplificazione del
    walking bass jazz); la variante usa la terza e la settima vere
    dell'accordo (terza minore su un accordo minore).
  - **Pedale**: una sola nota lunga per accordo (ballate).
  - **Due quarti**: fondamentale sul 1 e quinta sul 3 (jazz lento, country).
  - **Ottave**: fondamentale e ottava alternate (disco, funk semplice).
  - **Blues 1-3-5-6**: il giro classico del blues/boogie sulla terza vera
    dell'accordo (la variante chiude con la settima di dominante).
  - **Ottavi**: fondamentale a ottavi (rock, pop, punk).
  - **Reggae**: il primo tempo resta vuoto, fondamentale lunga dal 2.
  - **Bossa nova**: fondamentale sul 1 e 3, quinta sul "e" del 2 e del 4.
  - **Shuffle blues**: 1-3-5-6-b7-6-5-3 in ottavi "dondolanti" a terzine.
  I disegni sono modelli generici semplici (una battuta che si ripete
  sull'accordo), non trascrizioni di brani; l'accordo piu' corto di una
  battuta ne tronca il disegno. Con la Variabilità alcuni stili alternano
  un secondo disegno (vedi sopra).
- **Intensità**: vedi sopra (anche in **Genera accompagnamento/riff**).

In **Genera accompagnamento** c'è anche **Rivolti vicini** (spuntato di
default): ogni accordo sceglie il rivolto più vicino al precedente
(condotta delle voci), come farebbe un pianista — ad esempio Do-Mi-Sol,
poi Do-Fa-La, poi Si-Re-Sol — invece di stare sempre in posizione
fondamentale e saltare da una posizione all'altra. Il primo accordo resta
com'è; tutti restano nell'estensione dello strumento e non si allontanano
troppo dal registro di partenza. Vale per gli accordi di almeno tre note
(non per arpeggi e bicordi, che hanno già il loro disegno).
- **Ottava** della linea di basso generata.
- **Variazione ogni N accordi**: ogni N accordi usa un trattamento
  leggermente diverso dello stesso accordo (salto d'ottava, nota diversa...)
  invece di ripetere identico il disegno — 0 disattiva le variazioni.

Entrambi mostrano un'anteprima modificabile a mano prima di confermare
(come l'importazione audio, sezione 10bis), e il risultato viene accodato
al contenuto già presente nella traccia di destinazione, non lo sostituisce.

**Metrica**: si usa la metrica iniziale del progetto. Basso, accompagnamento
e riff ripetono il disegno dello stile su battute della durata giusta
(3 beat in 3/4 e 6/8, 6 in 12/8...), quindi funzionano con qualunque
metrica; uno stile pensato per il 4/4 viene troncato alla battuta piu'
corta, e ci sono stili pensati apposta: **Valzer** per il basso (fondamentale
sul 1), **Valzer** e **Arpeggio in 6/8** per l'accompagnamento. La batteria
richiede invece uno stile scritto per quella metrica (4/4, 3/4, 5/4, 6/8,
7/8, 12/8, o uno stile personale salvato in quella metrica, vedi 9bis.1):
con una metrica senza stili (es. 9/8) il dialogo lo segnala e disattiva la
conferma.

### 9bis.1 Stili personali: imparare dai tuoi brani

Oltre agli stili già pronti, i generatori possono usare stili ricavati da
una tua parte: un giro di batteria o una linea di basso che ti piace diventa
un nuovo modello, che segue qualunque giro di accordi.

**Da dove si salva** («Salva come stile del generatore...»):
- tasto destro su un **box** nella vista Struttura brano;
- menu **Componi → Stili dei generatori → Salva la traccia come stile...** (tutta la traccia selezionata);
- **Libreria MIDI** (menu Componi → Gestisci libreria MIDI): il pulsante
  sotto l'anteprima propone tutti i canali del file selezionato.

**Il dialogo:**
- **Parte**: per un file MIDI, quale canale;
- **Tipo**: Batteria (per le parti percussive), oppure Basso,
  Accompagnamento, Riff/melodia (proposto in base allo strumento);
- **Accordi da**: la parte con gli accordi su cui il disegno suonava (per un
  box, gli accordi nello stesso punto del brano; per un file MIDI, un altro
  canale). Serve a capire quale nota è la fondamentale, la terza, la
  quinta... Senza accordi, la prima nota di ogni battuta fa da
  fondamentale;
- **Metrica** e **Nome**. Sotto, un riassunto di cosa è stato ricavato
  (quante battute lette, griglia, quante alternative, se c'è un fill).

**Come viene ricavato:**
- **Batteria**: le battute vengono messe sulla griglia (sedicesimi o
  terzine; ottavi nelle metriche in /8). La battuta più frequente diventa il
  giro base, le altre diverse (fino a 3) i giri alternativi, usati con la
  variabilità, e quella con i tom il fill. Senza una battuta con i tom si usa
  un fill generico (rullante sull'ultimo tempo). Il crash sul primo tempo
  non entra nel giro, perché lo aggiunge il generatore.
- **Basso, accompagnamento, riff**: ogni nota diventa un **grado
  dell'accordo** nella sua ottava (fondamentale, terza, quinta, sesta,
  settima, o un intervallo preciso). Su un altro giro la linea segue i nuovi
  accordi, con la terza giusta (minore su un accordo minore). L'ultima nota
  prima di un cambio d'accordo, a mezzo tono dalla nuova fondamentale,
  diventa una nota di avvicinamento verso l'accordo successivo, qualunque
  esso sia. Le pause restano pause. La battuta più frequente è il disegno
  base, la seconda la variante (usata con «Variazione ogni N accordi»),
  altre fino a 3 le alternative. Per l'accompagnamento si possono usare
  anche box di soli simboli d'accordo: se ne ricava il ritmo. Per il basso
  si tiene la nota più bassa di ogni attacco, per il riff la più alta.

Gli stili salvati compaiono nei dialoghi dei generatori con una **★**
davanti al nome, in fondo all'elenco; la batteria propone solo quelli della
metrica del progetto. **Componi → Stili dei generatori → Stili personali...** li
elenca per rinominarli o eliminarli. Sono salvati nella cartella di
configurazione (`generator_styles.json`, accanto agli strumenti
personalizzati), quindi valgono per tutti i progetti.

### 9bis.2 Melodie a frasi

In **Genera riff/melodia** (strumenti monofonici: tromba, sax, flauto,
voce, synth lead...), oltre ai riff che ripetono un disegno sulle note
dell'accordo, ci sono quattro stili che scrivono una **vera melodia**:
- **Melodia a frasi (A A' B A)**: tema, tema ripreso con un altro finale,
  una frase di contrasto e la ripresa del tema;
- **Melodia domanda e risposta (A A')**: la prima frase resta «aperta»,
  la seconda la riprende e la chiude;
- **Melodia lenta (ballad)**: come A A' B A, con note lunghe;
- **Melodia mossa**: come A A' B A, con più ottavi.

**Come è costruita:**
- **Frasi** di due battute (quattro in 3/4, 2/4 e 6/8). La forma si ripete
  finché copre le battute richieste; l'ultima frase del brano chiude sempre.
- **Motivo**: la frase A ha un ritmo e un profilo che tornano. Nella
  ripresa, se sotto ci sono gli stessi accordi, A torna identica, tranne il
  finale; su accordi diversi il motivo si sposta sul nuovo accordo, con lo
  stesso ritmo e lo stesso andamento. B ha un altro ritmo (più mosso, o più
  calmo nella versione mossa) e sale più in alto.
- **Armonia**: sui tempi forti (primo tempo e metà battuta, e le note lunghe)
  la melodia usa note dell'accordo; sugli altri tempi preferisce le note
  dell'accordo; in levare le note della scala, di preferenza per grado
  congiunto. Le note dell'accordo estranee alla scala sostituiscono quella
  naturale vicina (il sol# di `E7` in La minore, il sib di `C7` in Do).
- **Andamento**: ogni frase sale verso un punto più alto, verso i due terzi,
  poi scende alla cadenza. Dopo un salto la melodia torna indietro; evita
  salti enormi, tre note uguali di fila e i «trilli» avanti e indietro.
- **Cadenze**: una frase «aperta» (la domanda) finisce su una nota
  dell'accordo diversa dalla tonica, di preferenza la quinta o la seconda
  della scala. Una frase «chiusa» (la risposta) finisce sulla tonica, o, se
  l'accordo non la contiene (una frase che finisce sul V), sulla terza o
  sulla quinta della tonica.
- **Tonalità**: quella del progetto; se non è impostata, quella riconosciuta
  dagli accordi della traccia scelta in «Accordi da».

«Variazione ogni N accordi» non vale per queste melodie (il campo si
disattiva): hanno la loro forma. Gli altri controlli valgono come per gli
altri stili:
- **Variabilità**: a 0% la melodia dipende solo da accordi, stile e
  tonalità. Più in alto, **🎲 Nuova variazione** estrae un altro motivo. Il
  cursore **Ritmo** rende più vari i ritmi e può cambiare una battuta nelle
  riprese; **Note e armonia** fa scegliere note meno «ovvie» e cambia
  qualche nota nelle riprese; **Dinamica** fa crescere il volume verso il
  punto più alto di ogni frase e accenta i tempi.
- **Intensità**: Leggera rende la melodia più calma (meno note), Piena più
  mossa, In crescendo sempre più mossa lungo il brano.
- **Rigenera solo le battute** vale anche qui.

## 10. Import/Export MIDI

- **Progetto → Esporta → MIDI**: l'intero ensemble (tracce udibili secondo
  Solo/Mute) in un unico file MIDI multitraccia.
- **Progetto → Importa → MIDI**: crea un nuovo progetto con una traccia per
  ogni canale del file MIDI; il canale 10 diventa sempre Batteria.
- **Traccia → Esporta questa traccia / Importa in questa traccia → MIDI**: esporta solo la
  traccia selezionata, oppure importa un file MIDI (con scelta del canale,
  se il file ne contiene piu' di uno) sostituendo il contenuto della
  traccia corrente; viene proposto di aggiornare anche lo strumento in base
  al riconoscimento automatico.

**Riconoscimento/creazione automatica dello strumento**: per ogni canale,
se uno strumento gia' disponibile (predefinito o personalizzato) ha
esattamente il Program Change GM del canale, viene usato quello;
altrimenti viene **creato e registrato automaticamente un nuovo strumento
personalizzato** con quel programma esatto (nome derivato dal nome
ufficiale General MIDI, es. programma 81 → `Lead2sawtooth`; parametri di
ottava/estensione/voicing suggeriti in base alla famiglia, come nella
creazione manuale da **Suoni → Gestisci strumenti**), cosi' la traccia
importata riflette sempre fedelmente lo strumento originale invece di
limitarsi al piu' vicino approssimato. Al termine dell'import, se sono
stati creati nuovi strumenti, un avviso ne mostra l'elenco (sono comunque
sempre modificabili a posteriori da **Suoni → Gestisci strumenti**).
Questa creazione automatica avviene solo per un import effettivamente
confermato (non per la sola anteprima nel selettore canale, che continua a
mostrare il nome dello strumento gia' disponibile piu' vicino).

**Canali che cambiano strumento**: se un canale cambia strumento a meta'
brano (un Program Change fra le note: in *Layla* il riff dell'intro e' in
chitarra overdrive e poi passa al pianoforte, sullo stesso canale),
l'import multitraccia crea **una traccia per ogni strumento**, ciascuna con
le sole note suonate con quello strumento e con il volume e il pan in
vigore quando attacca. Se il canale torna piu' volte allo stesso strumento,
quelle parti stanno nella stessa traccia. Il canale della batteria non si
divide (li' il programma sceglie il kit).

Nota sulla precisione dell'import: la notazione supporta note cromatiche
(`c#`, `eb`, ecc.), quindi l'altezza viene preservata; la ritmica viene
quantizzata su una griglia di sedicesimi, oppure, battuta per battuta, su
una griglia a **terzine** quando gli attacchi lo richiedono (vedi sotto).

**Terzine e tuplet**: per ogni beat l'import sceglie la suddivisione che
spiega meglio gli attacchi. La griglia binaria (sedicesimi) vince se li
spiega tutti; altrimenti una terzina di ottavi (`8T:`, sezione 2.1bis) viene
usata quando li spiega e la binaria no — tipico di shuffle, swing 2:1 e
blues in 12/8, dove prima le note venivano spostate sul sedicesimo piu'
vicino. Sestine (`16T:`), quintine (`16Q:`) e settimine (`16S:`) hanno soglie
molto piu' severe (servono piu' attacchi nel beat e uno scarto molto
ridotto), altrimenti un suonato umano poco preciso verrebbe scambiato per
una tuplet. Gli attacchi quasi simultanei (kick e ride con qualche tick di scarto) contano
come un solo punto ritmico, e le quintine/settimine sono di fatto
riconosciute solo su passaggi molto regolari. Il comando griglia viene
scritto solo quando cambia. Una nota
che partendo da una griglia finirebbe dentro un beat con un'altra griglia,
in un punto che non e' un confine di beat, viene chiusa sul confine: puo'
quindi risultare leggermente piu' corta dell'originale, ma il resto della
traccia non si sposta mai. Un file solo binario produce gli stessi token di
prima.

**Note sovrapposte e voci**: in ST le uniche note simultanee sono quelle di
uno stesso blocco `[...]` (stessa durata), mentre nel MIDI una nota tenuta
sotto una melodia, o un accordo che continua sotto una voce, si
sovrappongono. Prima l'import saltava ogni attacco che cadeva dentro una nota
piu' lunga: in una libreria di prova circa l'8% delle note spariva, e in
alcuni file quasi la meta'. Ora l'**import di un file intero** separa ogni
canale in **voci monofoniche** (al massimo 2 per canale, sempre: se a uno
stesso attacco iniziano piu' gruppi di durate diverse che voci, i gruppi in
eccesso si fondono con quello dalla durata piu' vicina; la batteria mai): le note che iniziano insieme e finiscono (entro un sedicesimo) insieme
restano un unico blocco, ogni gruppo va nella prima voce libera, e una
sovrapposizione minima (legato entro un sedicesimo) accorcia la nota
precedente invece di aprire una voce. Le voci restano **nella stessa
traccia**: dove suona solo la prima il testo e' quello di sempre, dove
suonano anche le altre diventa un **blocco di voci** `{ ; }` (sezione 2.12)
su una riga a se', che comincia e finisce sulle stanghette quando non
taglia nessuna nota; il testo unito suona esattamente come le voci
separate. (Fino alla versione precedente ogni voce diventava una traccia a
parte, `Piano voce 2`.) Vale anche per l'import di un **singolo canale** in
una traccia. Il tempo (`tempo=N`) sta nella prima voce. Quando le voci sono
esaurite la nota precedente viene **accorciata** all'attacco successivo: si
perde la durata tenuta, mai la nota.

**Testo cantato**: gli eventi *lyrics* del file, e il testo dei file
karaoke (`.kar`, eventi di testo in una traccia senza note), diventano
testo fra virgolette (sezione 2.13) sulla prima voce del canale che li
canta (quello delle note nella stessa traccia MIDI, oppure quello le cui
note attaccano dove cadono le sillabe): una riga per battuta dopo le sue
note, `*` per una nota senza sillaba e `""` prima di un tratto cantato che
segue un passaggio strumentale.

 **Canali MIDI con molte tracce**: un file MIDI ha solo 15 canali melodici
(il 10 e' della batteria) e su ogni canale c'e' un solo strumento, un solo
volume/pan e un solo pitch bend. Con piu' di 15 tracce (facile con le voci
dell'import) l'export assegna prima un canale a ogni strumento *diverso*,
poi i canali che avanzano alle voci extra, e le restanti condividono il canale
del proprio strumento: nessuna traccia suona mai con lo strumento di
un'altra. Le voci dello stesso strumento che condividono un canale hanno il
pitch bend in comune (uno slide di una si sente anche sulle note dell'altra
mentre suonano insieme).

Note identiche allo stesso tick (raddoppi) e attacchi
sulla stessa altezza dentro lo stesso sedicesimo si fondono in una.

**Velocity delle note simultanee**: in ST ogni token (nota, accordo o
blocco `[...]`) ha una sola velocity, quindi le velocity diverse delle note
di uno stesso gruppo (per esempio un accento sul cantabile di un accordo, o
kick e hi-hat della batteria colpiti insieme) non si possono conservare una
per una: il gruppo importato prende la **media arrotondata** delle velocity,
che mantiene l'intensita' complessiva. Con velocity tutte uguali non cambia
nulla.

**Dinamiche da volume ed espressione (CC7/CC11)**: crescendo, diminuendo e
fade del file MIDI sono automazioni continue, che ST esprime solo come
velocity delle note (sezione 2.5). L'import calcola il livello CC7 x CC11 al
momento di ogni attacco, lo normalizza al massimo del canale e lo applica
alla velocity della nota: la nota piu' forte del canale mantiene la velocity
originale, le altre scendono in proporzione, e il risultato compare come
serie di `N@` (a scalini, uno per ogni nota che cambia, non come rampa
`>>`). Un volume costante (tipicamente CC7 = 100) o una variazione sotto il
15% del massimo non e' una dinamica e viene ignorata. Il volume *assoluto*
del canale rispetto agli altri non viene importato (si regola dal mixer).

**Articolazioni (`!`, `x`, `_`)**: per le note singole e gli accordi
impliciti (opzione "Riconosci accordi") l'import confronta la durata reale
della nota con l'intervallo fino all'attacco successivo: circa la meta'
→ staccato `!` (sezione 2.2), meno del 30% → mute `x`, oltre il 105% (nota
che si sovrappone alla successiva) → legato `_`. In quel caso il token
occupa tutto l'intervallo fino alla nota successiva (es. `2c*4!`) invece di
una nota corta seguita da pause, cosi' resta modificabile come la scrisse
un musicista. Una nota corta seguita da una lunga pausa (oltre un beat, o
mezzo beat per il mute) resta nota + pausa: non e' un'articolazione. Le
note normali (circa 70%-105%), i blocchi espliciti `[...]` (senza
modificatore finale, sezione 2.2), gli slide e la batteria non cambiano.

**Tempo, metrica e pedale**: i cambi di tempo del file diventano marcatori
`tempo=N` (sezione 2.6) — in **una sola** traccia, perche' il tempo e' globale in
ST: viene scelta quella su cui i marcatori slittano meno (in genere la
batteria, fatta di colpi brevi; un marcatore che cadrebbe dentro una nota
lunga viene emesso alla sua fine). Il tempo iniziale resta quello del
progetto e le oscillazioni piccole (meno di 2 BPM o del 2%: il rumore di un
tempo registrato dal vivo) non sono cambi di tempo e vengono ignorate.
La metrica (evento *time signature*) imposta il campo **Metrica** del
progetto; se cambia lungo il brano diventa l'elenco per battuta
(`Metrica: 1: 3/4, 3: 4/4`, sezione 2.7). Il pedale del sustain (CC64,
acceso da 64 in su) diventa `SON`/`SOFF` (sezione 2.4), solo alle
transizioni effettive; un pedale ancora premuto a fine canale viene chiuso
con un `SOFF` finale. L'export MIDI scrive ora anche la metrica, cosi' un
giro export→import la conserva. Nell'import di un singolo canale in una
traccia esistente i cambi di tempo e di metrica NON vengono importati
(sono globali al progetto), il pedale si'.

**Bending (pitch bend)**: una nota singola (mai un accordo) il cui pitch
bend raggiunge almeno un semitono pieno durante la sua durata viene
importata come uno **slide** (`c*4>d*4`, sezione 2) dall'altezza di
partenza al picco del bending, invece di essere appiattita all'altezza
nominale — utile in particolare per i MIDI di chitarra blues/rock, dove il
bending e' spesso parte integrante della frase. Se il pitch wheel rientra
poi in modo significativo verso un semitono diverso prima della fine della
nota (bend-and-release, tecnica comune: sale e poi rilascia), lo slide
importato ha una terza tappa (`c*4>d*4>c*4`, sezione 2.3) invece di
fermarsi al solo picco. Le durate delle singole tappe (sezione 2.3)
riflettono il timing REALE del bending rilevato nel MIDI sorgente — quando
il picco viene raggiunto rispetto alla durata della nota — invece di
assumere sempre una divisione a meta' fra rampa e mantenimento/rilascio:
un bend rapido seguito da un lungo mantenimento (es. `1c*4>3d*4`) suona
percio' diverso, e piu' fedele all'originale, da un bend lento che
raggiunge il picco solo verso la fine (es. `3c*4>1d*4`). La sensibilita' del pitch bend dichiarata nel file
(RPN 0, Pitch Bend Sensitivity) viene rispettata; se il file non la
dichiara si assume il default General MIDI (±2 semitoni). Un bending che
arrotonda a 0 semitoni (vibrato o imprecisioni di registrazione), troppo
piccolo rispetto al fondo scala del pitch wheel (un'automazione continua
di espressione/umanizzazione, non un bending deliberato) o implausibilmente
ampio (oltre 12 semitoni: i bending chitarristici reali restano
quasi sempre entro 2-3 semitoni, e un salto piu' ampio non e' un bending su
nessuno strumento — sarebbe una nota diversa, non una piegatura della
stessa; capita quando la sensibilita' RPN dichiarata riflette una capacita'
tecnica del canale, non l'intenzione di bending di quella nota specifica)
resta una nota normale, per evitare uno slide senza senso musicale.

**Slide guitar (Opzioni → Import MIDI → Slide nell'import MIDI...)**: su un canale con
sensibilita' del pitch bend ampia (12 semitoni, tipica dei MIDI di chitarra
slide) la soglia di sempre e' di circa 1,2 semitoni, e i bend brevi di un
semitono restano note normali. Spuntando **Slide** nel dialogo si attiva il
campo **Soglia** (0,5-1,2 semitoni, predefinito 0,8): l'import riconosce come
slide anche i bend piu' piccoli. La soglia puo' solo scendere, quindi sui
canali con sensibilita' stretta (es. 2 semitoni) non cambia nulla. Piu' e'
bassa, piu' slide si trovano ma piu' cresce il rischio di scambiare per uno
slide un'espressione del pitch wheel (visto su brani jazz): tienila alta per
i brani non slide. L'impostazione vale dal prossimo import e senza la spunta
l'import resta identico a prima. Il **timing del rilascio** e' quello reale del file: un bend che sale
subito, resta sul picco per quasi tutta la nota e rilascia solo alla fine
diventa una catena a 4 tappe con la tenuta come rampa piatta
(`1f*5>11g*5>1g*5>3f*5`: sale, tiene il sol, rilascia, resta sul fa); uno
che rilascia subito e poi resta sull'altezza scritta ha la lunga tenuta
finale (`1e*5>1d#*5>2e*5`), invece di essere steso linearmente su tutta la
nota (che faceva scivolare l'intonazione per tutta la durata). Se il
rilascio inizia solo nell'ultimo istante, la nota finisce mentre sta ancora
rilasciando e si scrive un semplice bend con tenuta (`1f*5>3g*5`). Una
**coda di rilascio** della nota precedente (il wheel sta ancora scendendo
verso il centro quando la nota inizia) non e' un bend: il riferimento resta
il centro.

**Bend che parte tardi e bend a due direzioni** (tipici dello slide/
bottleneck): se il wheel resta quasi fermo per un tratto (almeno il 15% della
nota, con piccole derive) prima di muoversi, lo slide ha una tenuta iniziale
(`7d*4>1d*4>8c#*4`: sta fermo, poi scende) invece di partire dall'attacco.
Se il wheel ha escursioni significative da *entrambi* i lati della nota
scritta (sale di un tono e poi scende sotto), il bend viene importato come
percorso a tappe — la curva del wheel semplificata (scarto massimo 0,7
semitoni) e arrotondata ai semitoni — invece di tenere solo l'escursione piu'
grande. Su note di pochi sedicesimi la griglia limita la precisione: ogni
rampa occupa almeno un sedicesimo.

**Bend ampi (fino a un'ottava)**: prima il limite era di 4 semitoni; ora e'
di **12** (un'ottava), perche' con una sensibilita' del wheel dichiarata
(RPN) ampia esistono glissando e piegature vere di 5-12 semitoni — slide/
bottleneck, il calo a nastro degli archi in *Strawberry Fields Forever*, i
"dive" di leva. Oltre l'ottava resta una nota normale (non e' una
piegatura). Se un canale parte gia' piegato (scoop) e dentro la nota il
wheel si tuffa **piu' lontano** dal centro di dove era partito di almeno
1,5 semitoni (parte a -4, scende a -12, poi risale), il tuffo si conserva:
percorso a tappe con il centro come riferimento, non un semplice scoop. Un
tuffo tardivo (oltre meta' nota, con almeno 3 eventi nella discesa) lascia
la nota ferma fin li'.

**Pre-bend della nota successiva**: quando il wheel si allontana dal centro
negli ultimi tick di una nota (entro un decimo di beat) ed e' ancora fuori
centro all'attacco della successiva, quel movimento e' il pre-bend
dell'ALTRA nota e non un bend fantasma in coda alla prima. Se invece torna a
0 proprio all'attacco successivo (un fall-off che si azzera), appartiene alla
nota che sta finendo.

Un **pre-bend / scoop** (il pitch wheel e' gia' fuori centro *prima*
dell'attacco e rientra sul centro durante la nota: corda gia' piegata e poi
rilasciata, o nota "presa dal basso", tipico dei MIDI di chitarra e di
voce) viene importato come slide dall'altezza di partenza *reale* verso la
nota scritta: un wheel a -1 semitono che risale a 0 su un re diventa
`c#*4>d*4` (do# che sale a re), e uno a +1 che scende diventa `d#*4>d*4`.
L'altezza scritta nel MIDI e' sempre quella d'arrivo. Un wheel fuori centro
che NON rientra mai sul centro durante la nota resta un offset statico del
canale (nota normale). Attenzione: gli slide di ST lavorano a semitoni
interi, quindi una piegatura reale di circa mezzo tono viene arrotondata al
semitono piu' vicino.

**Opzione "Riconosci accordi nell'import MIDI"** (**Opzioni** → casella
omonima, disattivata per default): quando un gruppo di note simultanee
corrisponde a una qualita' di accordo standard (es. Do maggiore), viene
importato nella forma implicita equivalente (`C*4`) invece che come blocco
esplicito (`[c*4 e*4 g*4]`) — piu' leggibile e facile da trasporre a mano.
Un accordo non riconoscibile (es. una semplice quinta, ambigua tra
maggiore e minore) resta comunque un blocco esplicito. **Attenzione**: a
differenza del blocco esplicito, che riproduce sempre fedelmente il
voicing e il registro originali del MIDI, la forma implicita viene
**ri-vocalizzata automaticamente dal motore** in base allo strumento della
traccia al successivo export — utile per adattare l'accordo allo
strumento di destinazione, ma un giro import→export non riprodurra' piu'
necessariamente le stesse identiche note del file originale. Il
comportamento predefinito (blocco esplicito) resta quindi il piu' fedele.

### 10.1 Esportare la partitura (MusicXML)

**Progetto → Esporta → Partitura MusicXML...** salva il brano come
partitura in formato **MusicXML** (`.musicxml`), che si apre con i
programmi di notazione: MuseScore (gratuito), Finale, Sibelius, Dorico e
molti altri. Da li' si puo' stampare, esportare in PDF, correggere la
grafica o aggiungere il testo. Come l'export MIDI, contiene le **tracce
udibili** (tiene conto di Solo e Mute); le tracce audio non hanno note e
restano fuori.

Cosa c'e' nella partitura:

- **una parte per traccia**, con il nome della traccia;
- **le note** esattamente come le suona SoundText: gli accordi compaiono
  con le note scelte dal motore di voicing, i blocchi `[...]` come
  accordi scritti;
- **le sigle degli accordi** (`Am7`, `C/E`...) sopra il pentagramma,
  scritte solo quando l'accordo cambia, come in un lead sheet;
- **la tonalita'** del progetto (sezione 2.7bis) come armatura di chiave;
  le note degli accordi usano i bemolle nelle tonalita' con i bemolle;
- **metrica e tempo**, compresi i cambi per battuta (sezione 2.7) e i
  marcatori di tempo nelle tracce;
- **terzine, quintine e settimine** con la loro parentesi;
- **dinamiche** ricavate dalla velocity (`p`, `mf`, `f`...), scritte solo
  quando il nuovo livello dura almeno quattro note, **articolazioni**
  (staccato, stoppato, legato) e **pedale** del sustain.
- **le voci** dei blocchi `{ ; }` (sezione 2.12) come voci dello stesso
  pentagramma, con i gambi in su e in giu';
- **il testo cantato** (sezione 2.13) sotto le note, con trattini e
  linee di estensione.

Le chiavi seguono le convenzioni delle parti stampate: pianoforti e organi
su due pentagrammi (violino e basso, divisi al Do centrale), chitarre in
chiave di violino e bassi in chiave di basso con l'**8 sotto** (suonano
un'ottava sotto lo scritto), gli altri strumenti in chiave di violino o di
basso secondo il registro. La batteria usa il pentagramma a percussione
con le posizioni usuali (cassa in basso, rullante al centro, piatti in
alto con la testa a **x**).

Una durata che non corrisponde a un valore di nota (per esempio 5 crome)
viene scritta come note **legate**, e una nota che scavalca la stanghetta
prosegue legata nella battuta successiva.

**Limiti**: dentro una stessa voce due note che si sovrappongono
(succede nei brani importati da MIDI) non possono convivere: la prima
viene accorciata fino all'attacco della seconda. Per scrivere davvero piu'
voci si usano i blocchi `{ ; }`. Gli slide compaiono con la sola nota di
partenza.

### 10.1bis Vedere e stampare la partitura (Vista → Partitura)

**Vista → Partitura...** (`Ctrl+Shift+P`) apre una finestra con le tracce
su pentagramma, impaginate in pagine A4: le stesse note, sigle, voci e
testo dell'esportazione MusicXML, **senza programmi esterni**. La finestra
resta aperta accanto all'editor e si **aggiorna mentre scrivi** (dopo una
breve pausa nella digitazione).

- **Tutte le tracce udibili** oppure **Solo la traccia selezionata**.
- **−** / **+**: zoom.
- **Esporta PDF...** salva la partitura in PDF (vettoriale, stampabile a
  qualsiasi dimensione); **Stampa...** la manda alla stampante.
- Se una traccia ha un errore di sintassi resta visibile l'ultima
  partitura valida, con l'avviso dell'errore.

**Progetto → Esporta → Partitura PDF...** fa lo stesso senza aprire la
finestra.

L'impaginazione e' di **Verovio**, una libreria libera di incisione
musicale (LGPL) installata insieme a SoundText. Se manca, la finestra
spiega come installarla (`pip install verovio`); l'esportazione MusicXML
funziona comunque. Per ritocchi grafici (spaziature, testo libero sulla
pagina) resta la via MusicXML → MuseScore.

### 10.2 Importare una partitura (MusicXML)

**Progetto → Importa → MusicXML...** crea un nuovo progetto da una partitura
**MusicXML** (`.musicxml`, `.mxl` compresso o `.xml`), il formato di
scambio di MuseScore, Finale, Sibelius, Dorico e di quasi tutti i
programmi di notazione; molte partiture gratuite online si scaricano in
questo formato. Si puo' anche aprire direttamente dalla riga di comando
(`soundtext brano.musicxml`).

Cosa diventa la partitura:

- **una traccia per parte**, con il nome della parte ("Flauto",
  "Violino I"...) e lo strumento indicato nella partitura (o riconosciuto
  dal nome della parte); due voci sullo stesso pentagramma diventano voci
  della stessa traccia (blocchi `{ ; }`, sezione 2.12), come nell'import
  MIDI (sezione 10);
- **le note all'altezza reale**: gli strumenti traspositori (sax,
  clarinetto, tromba in Si♭, chitarra scritta all'ottava) suonano come si
  sentono, non come sono scritti;
- **tempo, metrica e tonalita'**, con i cambi di tempo e di metrica, e le
  **dinamiche** (`p`, `mf`, `f`...) come velocity;
- **ritornelli, finali 1./2., D.C., D.S., Fine e Coda** svolti
  nell'ordine in cui si suonano; dopo un D.C. o un D.S. i ritornelli non
  si ripetono e si suona l'ultimo finale, come d'uso;
- **le note legate** diventano una nota sola; una battuta **in levare**
  all'inizio viene completata con una pausa, cosi' le battute restano al
  loro posto;
- **le sigle degli accordi** (`Am7`, `G7b9`, `C/E`...) diventano una
  traccia **Accordi**: in un lead sheet (melodia e sigle) si sente e
  accompagna la melodia; se la partitura ha gia' altre parti che suonano
  l'armonia, la traccia e' muta (basta togliere il Mute per sentirla).
  Le sigle che SoundText non ha diventano la piu' vicina (per esempio
  `m11` diventa `m9`).

La batteria scritta sul pentagramma a percussione diventa una traccia di
percussioni, con i suoni indicati nella partitura. Le note di
abbellimento (acciaccature, appoggiature scritte piccole) si ignorano. Il
**testo cantato** diventa testo fra virgolette (sezione 2.13), con
trattini ed elisioni; nei ritornelli si usa la strofa del passaggio (la 1
la prima volta, la 2 la seconda), se c'e'. L'opzione **Riconosci accordi** dell'import MIDI
vale anche qui.

### 10.3 Notazione ABC (importare ed esportare)

L'**ABC** e' una notazione musicale in solo testo (standard 2.1), usata
dalle grandi raccolte di musica tradizionale e folk e da programmi come
abcjs, EasyABC, abcm2ps e abc2midi: un brano `.abc` si legge e si scrive
anche a mano.

**Progetto → Esporta → Partitura ABC...** salva le tracce udibili come un
brano ABC:

- ogni traccia e' una **voce** (`V:`) con il suo nome e lo strumento
  (`%%MIDI program`); pianoforte e organo hanno due pentagrammi uniti da
  una graffa, le voci dei blocchi `{ ; }` stanno sullo stesso pentagramma
  (`%%score`); la batteria e' sul canale 10, con le note dei suoni General
  MIDI;
- **tonalita'** (`K:`), **metrica** (`M:`, con i cambi in tutte le voci),
  **tempo** (`Q:`), **sigle degli accordi** fra virgolette, **dinamiche**
  (`!mf!`), staccato e tenuto, **terzine** e le altre tuplet, le note
  legate da una battuta all'altra e il **testo cantato** (`w:`);
- chitarre e bassi usano la chiave all'ottava bassa (`treble-8`,
  `bass-8`), con le note scritte un'ottava sopra come vuole lo standard.

Gli slide diventano la loro prima nota; il pedale e le automazioni
(`vol=`, `pan=`... sezione 2.15) non si scrivono (non sono nello standard).

**Progetto → Importa → ABC...** crea un nuovo progetto dal primo brano del
file (si puo' anche aprire dalla riga di comando: `soundtext brano.abc`).
Si leggono note, pause, accordi `[CEG]`, unita' di nota (`L:`, o quella
che deriva dalla metrica), ritmo puntato (`>` `<`), tuplet `(3`,
`(p:q:r`, legature (anche fra battute, con le alterazioni), alterazioni
che valgono fino alla stanghetta, tonalita' con i modi (`Dmix`, `Ador`...:
diventano la tonalita' con la stessa armatura), cambi `[K:]` `[M:]` `[L:]`
`[Q:]`, **ritornelli e finali 1./2.** svolti, la battuta **in levare**,
dinamiche, sigle degli accordi (nella traccia **Accordi**, come per il
MusicXML) e testo cantato con piu' strofe. Ogni voce e' una traccia; le
voci sullo stesso pentagramma (`%%score (S A)`) stanno in una traccia
sola, e cosi' i due pentagrammi del pianoforte (`{RH | LH}`). Lo
strumento viene da `%%MIDI program` (`%%MIDI channel 10` o `clef=perc`
per la batteria), altrimenti dal nome della voce. Le chiavi all'ottava,
`transpose=` e `octave=` suonano all'altezza reale. Si ignorano le note
di abbellimento, le parti (`P:`) e le decorazioni che non cambiano il
suono.

## 10bis. Importazione audio (voce/microfono/file)

Menu **Traccia → Importa in questa traccia → Audio → notazione (microfono o file)...**
(anche dal menu **⋯** della traccia, voce "Importa audio → note...", e
come "Importa audio (in questo pattern)" nel dialogo **Componi →
Gestisci libreria pattern**, per catturare direttamente un pattern
riutilizzabile invece che una traccia): converte un'idea musicale
catturata via microfono o file audio (`.wav`/`.mp3`/`.m4a`) direttamente
in notazione testuale, inserita nella traccia (o nel corpo del pattern)
dopo un'anteprima testuale e un ascolto opzionale.

- **Sorgente**: pulsante di registrazione (Start/Stop) dal microfono,
  oppure trascina un file nell'area dedicata (drag-and-drop) o usa
  "Sfoglia file...". Registrando con il **Metronomo** acceso, il click
  riparte insieme alla registrazione: il primo battito coincide con
  l'inizio del file e la trascrizione segue il metronomo (una pausa prima
  della prima nota resta una pausa). Senza metronomo la trascrizione parte
  dalla prima nota, qualunque sia il momento in cui hai premuto Registra. Il microfono richiede
  `libportaudio2` installato a livello di sistema su Linux (vedi sezione
  Installazione); i file mp3, m4a, flac e ogg li legge il decodificatore
  di Qt Multimedia, gia' incluso in PySide6 (o `ffmpeg`, se il PySide6
  della distribuzione non lo include). Se manca qualcosa il dialogo lo
  segnala con un messaggio esplicito invece di fallire silenziosamente.
- **Quantizzazione**: selettore con Off, 1/4, 1/8, 1/16 (predefinito),
  1/32, piu' una casella "Ternario" (terzine 8T/16T) abilitata solo per
  1/8 e 1/16. "Off" non introduce un nuovo tipo di timing libero: usa
  internamente una griglia finissima (1/64), sotto la soglia di
  quantizzazione percepibile, restando comunque dentro la normale
  sintassi `N:`. L'ultima combinazione usata viene ricordata alla
  riapertura del dialogo.
- **Modalita' di analisi**: Melodica (pitch detection, per voce o
  strumenti che suonano una nota alla volta: gli accordi non vengono
  riconosciuti) oppure Percussiva (rilevamento transienti per
  batteria/beatbox, classificati automaticamente in `kick`/`snare`/
  `hihat`). Precompilata in base allo strumento della traccia corrente,
  ma sempre modificabile manualmente. In modalità Percussiva la
  quantizzazione scelta conta anche per il rilevamento: due colpi più
  vicini di circa metà slot della griglia vengono considerati un colpo
  solo (con 1/16 a 120 BPM, 75 ms), quindi scegli una griglia fine almeno
  quanto le note più veloci che hai suonato (1/8 per hihat in crome, 1/16
  per i sedicesimi).
- **Algoritmi**: gli attacchi si trovano con SuperFlux (flusso spettrale
  che non scambia il vibrato per una nota nuova), l'altezza con YIN;
  sono scritti dentro SoundText (in numpy), senza librerie da installare.
- **Parametri avanzati di pitch tracking** (solo modalita' Melodica):
  permettono di adattare il riconoscimento a un audio specifico invece di
  accontentarsi del risultato predefinito — regola i valori, premi di
  nuovo "Converti in SoundText" per riprovare sullo stesso file, ripeti
  finche' il risultato non convince:
  - **Frequenza minima**: automatica (dedotta dall'estensione grave dello
    strumento di destinazione) oppure un valore in Hz scelto a mano.
  - **Finestra di analisi**: numero di campioni per stima — piu' ampia
    aiuta sui bassi/note gravi ma peggiora la risoluzione temporale
    (attacchi/note brevi meno precisi).
  - **Passo di analisi (hop size)**: distanza in campioni tra una stima e
    la successiva — piu' piccolo da' piu' risoluzione temporale ma
    un'analisi piu' lenta.
  - **Soglia di confidenza**: confidenza minima per accettare una stima.
  - **Durata minima nota**: scarta le note piu' brevi di questa soglia,
    quasi sempre artefatti (onset spuri ravvicinati, tipici del vibrato
    marcato).
  - **Ripristina valori standard**: riporta l'intero pannello ai default.
- **Sorgente: voce/beatbox**: casella da attivare quando si sta cantando/
  canticchiando la parte (basso, melodia...) o imitando la batteria con la
  bocca, invece di registrare lo strumento vero. La voce umana ha
  caratteristiche acustiche diverse da uno strumento reale: intonazione
  meno stabile nota per nota (frammenta facilmente in note brevi ed
  erratiche) e, per la batteria, nessuna vera risonanza grave come quella
  di una cassa (il tratto vocale e' fisicamente troppo corto per
  produrla). Con la casella attiva: per la parte melodica non si allarga
  la finestra di analisi sull'estensione grave dello strumento di
  destinazione (inutile se si sta comunque cantando nella propria
  estensione vocale, e dannosa per la risoluzione temporale); per la
  batteria le soglie kick/snare/hihat vengono ricalibrate su un "boom" di
  bocca invece che su una cassa vera.
- **Conversione**: il pulsante "Converti in SoundText" analizza l'audio in
  background (con barra di avanzamento, "Annulla" la interrompe e puoi
  subito riprovare con altri parametri) e mostra il risultato in
  un'anteprima con evidenziazione sintattica, prima di un eventuale
  inserimento; il testo generato viene sempre validato e non viene mai
  inserito se risultasse sintatticamente non valido.
- **Anteprima modificabile**: una volta completata la conversione,
  l'anteprima non e' piu' di sola lettura: si puo' correggere a mano una
  nota sbagliata o provare un'alternativa direttamente nel testo, prima di
  confermare. "Ascolta anteprima" riproduce sempre il contenuto ATTUALE
  dell'editor (comprese le modifiche fatte a mano, non il testo originale
  generato dall'analisi); se le modifiche rompono la sintassi, sia
  "Ascolta anteprima" sia Ok segnalano l'errore invece di procedere. Una
  nuova conversione (nuovo file, altro algoritmo di pitch, ecc.) sovrascrive
  qualunque modifica manuale non ancora confermata.
- **Ascolta anteprima**: il pulsante "▶ Ascolta anteprima" (con "■ Stop"
  accanto), abilitato dopo una conversione riuscita, riproduce il
  contenuto attuale dell'anteprima con lo strumento di destinazione prima
  di confermare con Ok — utile per verificare a orecchio la conversione
  (o una propria variante) prima di sostituire il contenuto della
  traccia/pattern.

Nota sulla qualita' del riconoscimento: il rilevamento delle note melodiche
segmenta l'audio con un rilevatore di attacchi dedicato (affidabile anche
in registro grave e sulle transizioni "legato" tipiche del canto, senza
silenzio tra una nota e l'altra) e stima l'altezza di ciascuna nota con la
mediana delle misure nell'intervallo — piu' robusta al vibrato e alle
piccole imprecisioni di intonazione di una voce non professionale rispetto
a una singola misura istantanea. Ogni nota finisce quando il suono si
spegne (non per forza all'attacco successivo), quindi le note staccate
lasciano le pause; la stessa nota suonata più volte di fila (tipica del
basso) resta una serie di note distinte, anche senza pausa in mezzo,
mentre una nota tenuta con vibrato o tremolo resta una nota sola. La
dinamica è relativa: la nota (o il colpo) più forte della registrazione
diventa `110@` e le altre scendono in proporzione, a passi di 10, così
anche una registrazione a volume basso suona piena e il testo non si
riempie di piccoli cambi di `@`. Per le note piu' gravi (es. basso) la
finestra di analisi si allarga automaticamente in base all'estensione
minima dello strumento di destinazione, per una stima di altezza piu'
precisa (non incide sul rilevamento dell'attacco, gestito a parte). La
classificazione percussiva automatica riconosce solo `kick`/`snare`/
`hihat` dallo spettro del "corpo" del colpo (subito dopo il transiente
d'attacco, non tom/crash/ride/hihat_open, inaffidabile senza un modello
dedicato); il testo generato resta comunque modificabile a mano come
qualunque altro token. Le soglie della modalita' "voce/beatbox" sono una
stima ragionata sul comportamento acustico del tratto vocale, non
calibrata su registrazioni reali: se i risultati non sono soddisfacenti,
lo script `diagnose_audio.py` (nella cartella del programma) permette di
ispezionare i dati grezzi usati dalla classificazione su una tua
registrazione, per una calibrazione mirata invece che a tentativi;
correggere a mano il testo generato resta comunque sempre possibile.

## 10ter. Suona con la tastiera (tastiera del computer o tastiera MIDI)

Menu **Traccia → Suona con la tastiera in questa traccia...** (anche come
voce "Suona con la tastiera..." del menu **⋯** della traccia, e come
"Suona con la tastiera (in questo pattern)" nel dialogo **Componi →
Gestisci libreria pattern**): registra una performance suonata dal vivo con
la tastiera del computer — usata come se fosse un piccolo strumento
musicale — e la converte in notazione, con lo stesso flusso finale
(anteprima modificabile, "Ascolta anteprima", Ok/Annulla) del dialogo di
importazione audio (sezione 10bis), di cui e' il pendant "strumento suonato
dal vivo" invece che "audio registrato/caricato".

- **Disposizione tastiera** (layout italiano): tre righe di 12 tasti
  ciascuna, ognuna un'ottava sopra la precedente, percorse cromaticamente a
  partire da Do — riga numerica (`1`...`0`, `'`, `ì`) sull'ottava scelta col
  selettore "Ottava" del dialogo, riga `Q`...`P`, `è`, `+` un'ottava sopra,
  riga `A`...`L`, `ò`, `à`, `ù` due ottave sopra. La legenda esatta (con
  l'ottava effettiva di ciascuna riga) e' sempre visibile nel dialogo.
- **Indipendenza dalla lingua della tastiera**: le note (tre righe sopra) e
  la fila qualità accordi (`Z X C V B N M , . /`, sezione successiva) sono
  agganciate alla POSIZIONE fisica del tasto premuto, non al carattere che
  produce — cambiando la lingua/il layout di sistema (es. da italiano a
  US/UK/tedesco) gli stessi tasti fisici continuano a suonare le stesse
  note, anche se il carattere stampato sul tasto (o prodotto digitando
  altrove) è un altro. Copre 45 dei 46 tasti coinvolti: l'unico escluso è
  l'ultimo tasto della riga `A`...`L` (quello che produce `ù` su layout
  italiano — un tasto "extra" dei layout ISO europei senza equivalente
  univoco su tastiera US, la cui posizione fisica esatta non è determinabile
  in modo affidabile su tutti i layout). Per quel tasto è comunque
  disponibile un ripiego: **Invio** (sia quello principale sia quello del
  tastierino numerico) suona sempre la stessa nota di `ù`, qualunque sia il
  layout attivo — Invio non è un tasto-carattere, quindi la sua posizione è
  già di per sé indipendente dal layout. Verificato su Linux (X11 e
  Wayland); su Windows e macOS si basa sugli stessi standard documentati ma
  non è stato possibile verificarlo interattivamente in fase di sviluppo —
  se un tasto risultasse fuori posto su quelle piattaforme, segnalalo.
- **Accordi al volo**: tenendo premuto un tasto della fila `Z X C V B N M , . /`
  insieme al tasto-nota (una qualunque delle tre righe sopra) si suona
  l'accordo corrispondente invece della nota singola:

  | Tasto | Qualità | Intervalli |
  |---|---|---|
  | `Z` | Maggiore | 1 - 3 - 5 |
  | `X` | Minore | 1 - ♭3 - 5 |
  | `C` | 7ª Dominante | 1 - 3 - 5 - ♭7 |
  | `V` | Minore 7 | 1 - ♭3 - 5 - ♭7 |
  | `B` | Maggiore 7 | 1 - 3 - 5 - 7 |
  | `N` | Sospeso (sus4) | 1 - 4 - 5 |
  | `M` | Aggiunta 9ª (add9) | 1 - 3 - 5 - 9 |
  | `,` | Diminuito 7 | 1 - ♭3 - ♭5 - 𝄫7 |
  | `.` | Power Chord | 1 - 5 - 8 |
  | `/` | Basso profondo | nota + ottava sotto (non un vero accordo) |

  Il tasto-qualità va tenuto premuto PRIMA/insieme al tasto-nota (premerlo
  dopo non "aggiorna" retroattivamente una nota già suonata); se si tengono
  premuti più tasti-qualità insieme, vince l'ultimo premuto ancora attivo.
  Come per le note, questa fila non dipende dal layout scelto (Cromatica/
  Scala della tonalità/Jankó): funziona identica in qualunque modalità.
- **Tasti esecutivi**:
  - `Bloc Maiusc` (**Sustain**, tenuto premuto): la nota/accordo resta
    udibile e la sua durata nella traccia registrata resta aperta anche dopo
    aver rilasciato il tasto-nota, finché non si rilascia anche
    `Bloc Maiusc` — utile per accordi tenuti mentre si preme già la nota
    successiva. Nota: il LED di Bloc Maiusc della tastiera potrebbe comunque
    accendersi/spegnersi ad ogni pressione (dipende da sistema/driver): non
    influisce sul funzionamento, è solo un effetto collaterale innocuo.
  - `L-Alt` (**Strumming**, tenuto premuto): quando si preme un tasto-nota
    con un accordo attivo (fila qualità), le note dell'accordo non partono
    più tutte insieme ma in rapidissima sequenza (circa 20 ms l'una
    dall'altra), come una pennata di chitarra — restano comunque tutte
    udibili finché il tasto-nota non viene rilasciato (solo l'attacco è
    scaglionato, non la fine).
  - `L-Maiusc` (**Bending**, tenuto premuto): imita un vero bending
    chitarristico su una nota singola — dal vivo si sente la nota salire
    gradualmente di un tono intero (rampa di ~120 ms, non un salto secco) e,
    al rilascio, ridiscendere altrettanto gradualmente prima di fermarsi
    (~80 ms), proprio come rilasciare la piegatura di una corda. Nella
    traccia registrata viene catturato come un vero portamento/slide (stessa
    sintassi di `c*4>d*4`), che viene riprodotto/esportato in MIDI con un
    pitch bend continuo, non due note distinte. Si applica in questa forma
    solo a una nota singola (nessun accordo della fila qualità né basso
    profondo attivi, e non insieme all'Arpeggiatore): su un accordo, o con
    l'Arpeggiatore attivo, ricade su un più semplice scarto fisso di 2
    semitoni applicato subito a tutte le note.
  - `L-Ctrl` (**Inversione**, tenuto premuto): sposta la nota più grave
    dell'accordo un'ottava sopra (1ª inversione), per passaggi armonici più
    fluidi. Si applica solo agli accordi (fila qualità attiva), non alle
    note singole.
  - `Tab` (**Piano/Forte**): commuta la dinamica delle note suonate da quel
    momento in poi — attivo = Piano (velocity 60), disattivo = Forte
    (velocity 110, stato di partenza). A differenza degli altri tasti
    esecutivi non va tenuto premuto: un tocco commuta lo stato.
  - **Barra spaziatrice** (**Arpeggiatore**, tenuta premuta): ogni
    tasto-nota premuto DA QUEL MOMENTO IN POI (uno già suonato prima di
    premere la barra continua invece normalmente, senza essere arpeggiato
    retroattivamente) entra in un pool condiviso le cui altezze vengono
    suonate una alla volta, in ciclo continuo, a un sedicesimo del tempo
    del progetto — tenendo premuti più tasti-nota (o un accordo con la fila
    qualità) si sente/registra un arpeggio che attraversa tutte le loro
    note. Il pool si aggiorna dal vivo se si aggiungono/tolgono tasti-nota
    mentre la barra resta premuta.

  Tutti i tasti esecutivi tenuti premuti (Sustain/Strumming/Bending/
  Inversione/Arpeggiatore) vanno tenuti PRIMA o insieme al tasto-nota:
  premerli dopo non ha effetto retroattivo su una nota già in corso.

  Nota tecnica: Qt non distingue in modo portabile il tasto sinistro da
  quello destro di Ctrl/Alt/Maiusc, quindi questi rispondono a Ctrl/Alt/
  Maiusc in generale (qualunque lato), non solo alla copia sinistra
  descritta sopra.
- **Traccia percussiva**: se lo strumento di destinazione e' percussivo, le
  tre righe fisiche (numerica, Q, A - le stesse usate per le note, vedi
  sopra) suonano invece i 36 identificatori percussivi elencati nella
  sezione 6, nello stesso ordine con cui compaiono nella legenda del
  dialogo (che mostra a video quale tasto produce quale suono), senza
  ottava.
- **Feedback sonoro immediato**: mentre si registra o si preme "Suona"
  (prova senza registrare), ogni tasto premuto si sente subito, sintetizzato
  in tempo reale con lo strumento di destinazione — a differenza del resto
  della riproduzione dell'app, sempre offline (vedi sezione 12), qui serve
  latenza minima. Se la traccia ha uno strumento plugin (Strumento SFZ
  interno, LV2 o VST3), i tasti li suona quello, con il suono che avra' la
  traccia; lo strumento si comincia a caricare all'apertura del dialogo e,
  se non si apre, si usa il SoundFont (il dialogo lo segnala). Se la libreria FluidSynth o un SoundFont non sono disponibili, si
  puo' comunque registrare/suonare, semplicemente senza sentire i tasti (il
  dialogo lo segnala).
- **Tempo, Metrica, Metronomo e Quantizzazione**: stessi controlli e stesso
  significato del dialogo di importazione audio (sezione 10bis) — il
  metronomo (sezione 12.5) e' particolarmente utile qui per suonare a tempo
  prima della quantizzazione.
- **Tonalità**: mostra la tonalità del progetto (sezione 2.7bis) già
  all'apertura del dialogo, e si può cambiare direttamente da qui — stesso
  campo `project.key` della toolbar principale (non una copia): modificarla
  nel dialogo si riflette anche nella toolbar una volta chiuso il dialogo, e
  viceversa. Cambiarla aggiorna subito il layout "Scala della tonalità" (vedi
  sotto), se attivo.
- **Layout**: selettore della disposizione dei tasti-nota, disattivo se lo
  strumento e' percussivo (le percussioni usano sempre i tasti `1`-`9`).
  Si puo' cambiare anche a registrazione o prova gia' in corso, come l'Ottava.
  Opzioni disponibili:
  - **Cromatica** (predefinita): comportamento descritto sopra, 12 semitoni
    per riga, 3 ottave totali.
  - **Scala della tonalita' (diatonica/pentatonica/blues)**: richiede una
    tonalita' impostata nella toolbar principale (sezione 2.7bis) — se non
    impostata (o non valida), ricade automaticamente sulla cromatica, senza
    bloccare la selezione. Ogni riga di tasti percorre solo le note della
    scala scelta invece delle 12 cromatiche, cosi' i tasti suonano sempre
    "in tonalita'", utile per improvvisare senza dover scegliere a orecchio
    le note giuste: **diatonica** usa le 7 note della scala maggiore o
    minore naturale della tonalita'; **pentatonica** le sue 5 note maggiori
    o minori (piu' "sicura" per l'improvvisazione, quasi impossibile suonare
    una nota stonata); **blues** le 6 note della scala blues (pentatonica
    minore + quinta diminuita di passaggio), sempre le stesse a partire dalla
    tonica indipendentemente dal modo maggiore/minore. Piu' corta e' la
    scala, piu' ottave copre la tastiera con gli stessi 12 tasti per riga
    (la diatonica arriva a ~3,6 ottave, la blues a ~3,8, la pentatonica a
    ~4,2).
  - **Jankó (isomorfa)**: disposizione a toni interi alternati tra le righe
    (riga numerica e riga A suonano le stesse note, la riga Q le note
    intermedie un semitono sopra), indipendente dalla tonalita': una data
    forma di accordo/intervallo suona sempre identica ovunque sulla
    tastiera, comoda per chi la conosce gia' da altri strumenti/software.
    Copre 2 ottave piene (meno della cromatica): e' il prezzo
    dell'isomorfismo, non un difetto.
- **"Ascolta anche le altre tracce" (rispetta Solo/Mute)**: casella
  facoltativa (non spuntata di default). Se spuntata, sia mentre si suona
  dal vivo (Registra/Suona) sia mentre si riascolta l'anteprima registrata
  si sentono anche le altre tracce del progetto, con lo stesso stato
  Solo/Mute che hanno in quel momento nel mixer — utile per suonare o
  valutare la nuova parte nel contesto dell'arrangiamento invece che in
  isolamento. La traccia di destinazione stessa non viene mai duplicata: se
  il dialogo e' stato aperto per una traccia gia' esistente, il suo
  contenuto attuale resta escluso dall'ascolto di sottofondo, cosi' non si
  sovrappone a quanto si sta registrando/riascoltando al suo posto. Se non
  spuntata: comportamento di sempre, si sente solo lo strumento corrente.
  La casella e' disattivata durante la registrazione/prova stessa (va
  decisa prima di premere Registra o Suona).
- **Registra** avvia/ferma la cattura della performance; **Suona** la prova
  senza registrare nulla. Fermare la registrazione genera l'anteprima
  testuale quantizzata, modificabile e riascoltabile come nell'importazione
  audio, prima di confermare con Ok. Nella traccia (a differenza dei
  pattern, dove sostituisce sempre il corpo) il risultato viene accodato al
  contenuto gia' presente invece di sovrascriverlo, per non perdere musica
  scritta a mano o importata in precedenza.

### Tastiera MIDI

Nello stesso dialogo si può suonare con una **tastiera MIDI** vera
(collegata via USB o con un'interfaccia MIDI), insieme o al posto della
tastiera del computer:

1. collega la tastiera **prima** di aprire il dialogo (se la colleghi dopo,
   premi **⟳** accanto al menu **Tastiera MIDI**);
2. nel menu **Tastiera MIDI** scegli la tastiera: con una sola tastiera
   collegata è già scelta, e SoundText si ricorda l'ultima usata;
3. premi **Registra** (o **Suona**, per provare) e suona. Come per la
   tastiera del computer, le note contano solo mentre Registra o Suona
   sono attivi.

Rispetto alla tastiera del computer:
- **dinamica vera**: la velocity di ogni tasto (quanto forte lo premi)
  diventa il `@` della nota;
- **accordi** suonati direttamente, un tasto per nota (la fila degli
  accordi al volo resta per la tastiera del computer);
- **pedale del sustain**: tiene le note come il tasto del sustain; la
  durata registrata arriva fino al rilascio del pedale;
- **leva del pitch bend**: si sente dal vivo; se durante una nota sale o
  scende di almeno un semitono, la nota viene registrata come slide
  (`a*4>b*4`) verso l'altezza raggiunta (escursione standard ±2 semitoni);
- **percussioni**: su una traccia di batteria le note seguono la mappa
  General MIDI (36 cassa, 38 rullante, 42 hihat chiuso, 46 hihat aperto...),
  come i pad delle tastiere e delle batterie elettroniche; le note fuori
  mappa si ignorano;
- l'**arpeggiatore** (barra spaziatrice tenuta sulla tastiera del computer)
  arpeggia anche le note della tastiera MIDI.

Serve il pacchetto Python **python-rtmidi** (nei requisiti: lo installano
già gli script di installazione; a mano `pip install python-rtmidi`). Se
manca, o se il sistema MIDI non risponde, il menu è disattivato e accanto
c'è il motivo. Se la tastiera non compare nell'elenco: controlla il cavo e
che sia accesa, premi **⟳**; su Linux `aconnect -l` elenca i dispositivi
MIDI visti dal sistema. Una tastiera aperta da un altro programma (per
esempio un sequencer) su Windows può risultare occupata: chiudi l'altro
programma.

## 10quater. Tracce audio (voce, chitarra, tastiera registrate)

Oltre alle tracce con notazione, un brano puo' contenere **tracce audio**:
file audio veri (una voce registrata al microfono, una chitarra elettrica
o una tastiera collegate con il jack alla scheda audio) che suonano insieme
alle altre tracce. A differenza dell'importazione audio (10bis) il file
**non viene convertito in note**: si sente cosi' com'e'.

Una traccia audio si riempie in due modi: **registrando** direttamente in
SoundText mentre suona il resto del brano (vedi "Registrare" qui sotto),
oppure **importando** file registrati con un altro programma.

- **Creare una traccia audio**: **+ Aggiungi traccia → Traccia audio...**,
  o menu **Traccia → Aggiungi → Traccia audio...**. Nella sua testata compare
  come "Audio", con Volume/Pan/Mute/Solo come le altre (volume 100%
  = livello originale del file, fino a 200% ≈ +6 dB).
- **Importare un file**: menu **Traccia → Importa in questa traccia → File audio come clip...** (o **⋯ → Importa file audio...** sulla traccia audio)
  aggiunge il file come **clip** in coda alla traccia.
  Nella vista Struttura brano: doppio click su un punto vuoto della riga,
  oppure tasto destro → **Importa file audio qui...** per metterla in un
  punto preciso. I `.wav` si leggono sempre (anche a 32 bit float); mp3,
  m4a, flac, ogg e aiff li legge il decodificatore di Qt Multimedia
  incluso in PySide6 (o `ffmpeg`, se c'e'), e si ricampionano a 48 kHz
  senza perdite sugli acuti.
- **Clip nella vista Struttura brano**: ogni clip e' un box con la forma
  d'onda, largo quanto la parte del file che suona. Si trascina come i box
  di notazione (agganciandosi al beat); doppio click per rinominarla; tasto
  destro per Play (anteprima della sola clip), Rinomina, **Guadagno clip
  (dB)**, Duplica, Taglia/Copia/Incolla (una clip audio si incolla solo in
  una traccia audio) ed Elimina. Tutto si annulla con Ctrl+Z.
- **Tagliare inizio e fine**: porta il mouse su un bordo del box (il
  cursore diventa ↔) e trascinalo. L'audio resta dov'e' nel tempo: si
  nasconde (o si ritrova) solo l'inizio o la fine del file. Il taglio si
  aggancia al sedicesimo (1/4 di beat); tenendo premuto **Shift** e' libero.
  Trascinando il bordo sinistro verso sinistra si ritrova anche l'audio
  registrato durante il conteggio (utile per una nota d'attacco suonata in
  anticipo). Per valori esatti: tasto destro → **Taglio preciso
  (secondi)...**. Il file non viene mai modificato.
- **Dividere una clip**: tasto destro nel punto in cui dividerla →
  **Dividi qui**: diventa due clip consecutive dello stesso file, che si
  possono spostare, tagliare o eliminare separatamente (per esempio per
  togliere un errore a meta' ripresa).
- **Converti in notazione...** (tasto destro su una clip): trasforma in note
  la parte che suona della clip, con lo stesso motore di "Importa audio"
  (10bis), in una **nuova traccia** con lo strumento scelto
  (proposto in base a cosa hai registrato: chitarra, tastiera, voce) e un
  box che parte dove parte la clip. Funziona bene con parti monofoniche
  (voce, linea di chitarra o basso); la clip audio resta.
- **Nell'editor classico** una traccia audio mostra, in sola lettura,
  l'elenco delle sue clip: le azioni sulla notazione (Genera, Suona con la
  tastiera, Importa MIDI, Congela accordi, Esporta MIDI) non valgono per le
  tracce audio e lo spiegano con un messaggio.
- **Tempo**: l'audio non viene stirato. Una clip resta ancorata al beat in
  cui inizia ma dura sempre gli stessi secondi: se cambi il BPM dopo averla
  posizionata, la barra di stato lo ricorda.

### Registrare

Pulsante rosso **●** sulla testata della traccia audio, menu
**Traccia → Registra nella traccia audio...** (Ctrl+R), oppure nella vista
Struttura brano tasto destro sulla riga della traccia → **Registra da
qui...** (parte da quel punto). Si apre il dialogo di registrazione:

- **Scheda audio**: l'ingresso da cui registrare (su Windows compaiono
  prima i driver a bassa latenza, ASIO e WASAPI). Viene ricordato.
- **Cosa registri**: Voce/microfono, Chitarra o basso (jack), Tastiera
  (uscita line). Sceglie l'ingresso piu' probabile e spiega cosa impostare
  sulla scheda: phantom +48V per un microfono a condensatore, ingresso
  INST/Hi-Z per la chitarra (si registra il suono pulito, senza
  amplificatore), ingressi 1+2 su LINE per una tastiera stereo.
- **Ingresso**: un ingresso mono (1, 2, ...) o una coppia stereo (1+2).
  Tipo di sorgente e ingresso restano salvati nella traccia.
- **Livello**: il misuratore si muove appena il dialogo e' aperto: regola
  il gain sulla scheda audio perche' le parti piu' forti arrivino verso
  -12/-6 dB senza accendere la spia rossa (saturazione).
- **Parti da**: posizione corrente, inizio del loop A (se impostato) o
  inizio del brano.
- **Conteggio** (0-4 battute di click prima che parta il brano) e
  **Metronomo durante la ripresa**. Il click continua anche oltre la fine
  del brano, quindi si puo' registrare anche in un brano ancora vuoto.
- **Ascolta le clip gia' presenti in questa traccia**: toglilo per rifare
  una parte senza sentire la ripresa precedente.
- **Compensazione latenza**: la latenza dichiarata dalla scheda viene gia'
  compensata; se la ripresa risulta comunque in ritardo rispetto al brano,
  aumenta questo valore (in anticipo: diminuiscilo). Viene ricordato per
  ogni scheda. **Calibra...** lo misura da solo: collega con un cavo
  un'uscita della scheda all'ingresso scelto (o avvicina il microfono alle
  casse), SoundText fa suonare 8 click, li registra e imposta il ritardo
  misurato. Basta farlo una volta per scheda audio (e ogni volta che cambi
  le impostazioni di buffer/latenza del driver).

**● Registra** prepara la base (il brano come in riproduzione, senza
SoundFont solo tracce audio e metronomo), fa il conteggio e registra finche'
non premi **■ Stop**. Il dialogo mostra durata e picco della ripresa (e
avvisa se e' saturata): **Tieni la ripresa** la aggiunge alla traccia come
clip al punto di partenza; **Registra** di nuovo la sostituisce. Se la
ripresa si sovrappone a clip gia' presenti, SoundText chiede se eliminarle.

Per sentirti mentre suoni usa il **monitoraggio diretto** della scheda audio
(manopola o tasto "direct monitor"): e' senza ritardo. SoundText manda in
cuffia solo il brano. Il file della ripresa contiene anche il conteggio,
nascosto dal taglio iniziale della clip (trascinando il bordo sinistro lo si
puo' ritrovare).

### Dove finiscono i file

Le riprese e i file importati (di cui SoundText fa una copia a 48 kHz, la
stessa frequenza della riproduzione: l'originale non viene mai toccato)
finiscono nella cartella **`<NomeProgetto>_audio/`**, accanto al file `.st`.
Se il progetto non e' ancora stato salvato vanno in una cartella temporanea
e vengono spostati nella cartella del progetto al primo salvataggio. **Salva con nome** copia i file
audio nella cartella del nuovo progetto. Per spostare un progetto su un
altro computer copia insieme il file `.st` e la sua cartella `_audio`.

Nel file `.st` una clip e' scritta cosi' (percorso relativo al file):

```
Audio Voce "Strofa" |8:
  file="Canzone_audio/voce.wav" trim=0.35,0 gain=-2

Traccia Voce [Audio]:
```

`|8` e' il beat di inizio; `trim` sono i secondi saltati all'inizio e alla
fine del file, `gain` il guadagno della clip in dB (entrambi facoltativi).
Se un file non si trova piu' la clip resta nel progetto, disegnata in rosso,
e non suona: tasto destro → **Ritrova file...** per indicarlo di nuovo.

### Esportare

- **Progetto → Esporta → Mix audio (WAV)...** esporta il brano come si sente
  (tracce udibili, audio compreso) in un WAV 48 kHz / 24 bit. Serve un
  SoundFont per le tracce con note; un brano di sole tracce audio si esporta
  anche senza.
- **Traccia → Esporta questa traccia → WAV...**, o **tasto destro sul nome di
  una traccia → Esporta WAV (solo questa)...**, esporta in un WAV solo quella traccia, con notazione o audio, come si
  sentirebbe in Solo (Solo/Mute delle altre tracce non contano). Per le
  tracce con notazione lo stesso menu ha anche **Esporta MIDI (solo
  questa)...**.
- **Traccia → Esporta questa traccia → WAV asciutto (per il re-amping)...**,
  o lo stesso comando col tasto destro sul nome della traccia, esporta la traccia **senza** catena di effetti, senza
  riverbero/chorus del synth, con il pan al centro e senza master (il
  volume resta): è il suono "pulito" da far passare in un simulatore di
  amplificatore esterno (vedi 8.6). Il file parte dall'inizio del brano,
  così reimportandolo all'inizio di una traccia audio resta a tempo.
- **Esporta MIDI** contiene solo note: le tracce audio non ci sono, e un
  messaggio lo ricorda.
- Salvataggio ed esportazioni propongono come nome del file quello del
  progetto (le esportazioni di una sola traccia quello della traccia), nella
  cartella in cui il progetto e' salvato.

## 11. Salvataggio progetto

Il progetto si salva in formato testuale nativo `.st` (leggibile e
modificabile anche a mano), che include tempo, metrica, pattern, tracce e
le definizioni degli eventuali strumenti personalizzati usati (vedi 7.1),
cosi' che il file sia autosufficiente e portabile tra installazioni diverse.
La libreria MIDI (`midi/`) resta invece condivisa a livello di installazione
e non viaggia dentro al file `.st`.

Il titolo della finestra mostra sempre il nome del file attualmente aperto
("SoundText — nomefile.st"), anche dopo un'importazione MIDI
("SoundText — nomefile.mid"), per sapere sempre a colpo d'occhio su
quale progetto si sta lavorando.

## 12. Riproduzione

Il tasto Play esporta un MIDI temporaneo. Se `fluidsynth` e un SoundFont sono
disponibili, la sintesi avviene **offline** (rendering in un file WAV
temporaneo, poi riprodotto con il miglior player audio trovato — su Linux
`pw-play`, `paplay`, `aplay`, `ffplay` o `mpv`; su macOS `afplay` (incluso
nel sistema) o, se installati, `ffplay`/`mpv`; su Windows `ffplay`/`mpv` se
installati, altrimenti il modulo `winsound` della libreria standard di
Python, sempre disponibile) invece che in tempo reale: questo evita i
crepitii/dropout dovuti a underrun del driver audio, tipici della sintesi
MIDI realtime su PulseAudio/PipeWire, e da un risultato piu' pulito. Se c'e'
la libreria FluidSynth (SoundText la usa direttamente), questo
rendering offline usa un'unica istanza di fluidsynth **persistente** per
tutta la sessione, con il SoundFont caricato in memoria una sola volta
invece che ad ogni Play: latenza di avvio molto piu' bassa (il costo di
caricamento del SoundFont, anche centinaia di ms per un GM da decine di MB,
si paga solo la prima volta), a parita' di strategia anti-crepitio (il
rendering resta offline, non tocca l'output audio in tempo reale). Se il
rendering offline non riesce (con o senza la libreria), o non c'e' un
player WAV disponibile, si ripiega sul binario CLI `fluidsynth` e poi sulla
riproduzione fluidsynth in tempo reale; se fluidsynth non e' disponibile
del tutto, su `timidity` o `wildmidi`; in mancanza di tutto, sul player
MIDI predefinito del sistema (`xdg-open` su Linux, `open` su macOS,
apertura diretta col programma associato su Windows).

Con la libreria FluidSynth **e** `sounddevice` (in requirements.txt)
installati il brano renderizzato viene riprodotto direttamente dal
programma invece che da un player esterno, e il rendering viene
**memorizzato**: solo il primo Play (o il primo dopo una modifica che
cambia il suono, come note, mixer o umanizzazione) deve attendere la
sintesi, mentre pausa/ripresa e salti ripartono all'istante. La posizione
mostrata da barra, evidenziazione, testina e metronomo e' quella letta dal
dispositivo audio, quindi resta allineata a cio' che si sente.

### Saltare a un punto e ripetere una sezione (loop A-B)

- **Salto**: clicca sulla barra di avanzamento in toolbar, oppure sul
  righello delle battute nella vista Struttura brano. Se il brano sta
  suonando riparte da li'; se e' fermo o in pausa, il prossimo Play
  partira' da quel punto.
- **Loop A-B** (menu **Riproduzione → Loop**): **Loop: inizio (A) qui** (`Ctrl+[`) e
  **Loop: fine (B) qui** (`Ctrl+]`) fissano i due estremi sul beat in
  riproduzione (o sul punto di pausa/salto), arrotondato al beat intero.
  Impostare B attiva il loop; **Ripeti la sezione A-B** (`Ctrl+L`) lo
  accende e spegne senza perdere A e B, **Cancella loop** li azzera. La
  sezione appare come una fascia colorata sul righello della Struttura
  brano. Si puo' attivare, spostare o togliere il loop anche mentre il
  brano suona, senza interruzioni.
- Il loop richiede la riproduzione diretta descritta sopra
  (libreria FluidSynth + `sounddevice`): con i player di ripiego il brano non
  viene ripetuto, e un messaggio in barra di stato lo segnala.

### 12.1 Barra di avanzamento ed evidenziazione del token in esecuzione

Durante la riproduzione, la barra di avanzamento (la riga a tutta larghezza
sotto la barra dei comandi) mostra il
tempo trascorso e la durata totale del brano (es. "00:42 / 01:30"). Nella
traccia visualizzata nell'editor, il token attualmente in esecuzione (nota,
pausa, accordo, blocco, o l'intero riferimento se e' un `%pattern`/`&"midi"`)
viene evidenziato con i colori invertiti rispetto al tema (sfondo chiaro,
testo scuro), per seguire visivamente l'esecuzione riga per riga. L'editor
scorre automaticamente quando necessario per tenere sempre visibile il
token evidenziato (nessuno scroll manuale richiesto durante l'ascolto), ma
solo quando esce dalla porzione visibile: non scorre continuamente nota
per nota, e non sposta il cursore di modifica dell'utente. Cambiando
traccia durante la riproduzione, l'evidenziazione si sposta sulla nuova
traccia selezionata, sempre sincronizzata con lo stesso tempo trascorso.

### 12.2 Modifiche al mixer durante la riproduzione

Mute, Solo, Volume e Pan possono essere modificati anche a brano in corso:
il programma riavvia automaticamente la riproduzione dalla posizione in cui
si trovava (non da capo), applicando subito le nuove impostazioni. E'
percepibile una breve interruzione al momento del riavvio (il brano va
risintetizzato con le nuove impostazioni), ma non e' necessario fermare
manualmente e far ripartire la riproduzione per sentire l'effetto di una
modifica al mixer.

**Se il suono non ti soddisfa nonostante un buon SoundFont**, tieni presente che:
- **Suoni → SoundFont → Mostra SoundFont in uso** indica esattamente quale motore e
  quale file `.sf2` verranno usati: se non mostra "fluidsynth persistente
  (libreria) + ...sf2" o "fluidsynth (CLI) + ...sf2", il programma sta
  silenziosamente ricorrendo a un fallback di qualita' inferiore (spesso
  perche' `fluidsynth` non e' installato, o nessun `.sf2` e' stato trovato)
  — installa `fluidsynth` e verifica il SoundFont da li'.
- Anche con un buon SoundFont, il **suono General MIDI ha un limite
  intrinseco di realismo**: non e' pensato per competere con librerie di
  campionamento professionali, ma per una riproduzione fedele e riconoscibile
  della partitura. Un salto di qualita' significativo richiederebbe
  campionamenti multi-velocity per strumento (fuori dallo scopo di questo
  motore basato su MIDI/GM standard).

### 12.3 Scegliere il SoundFont (es. FluidR3_GM.sf2)

Il programma cerca un SoundFont, in ordine di priorita':

1. il percorso impostato manualmente da **Suoni → SoundFont → Scegli SoundFont
   (.sf2)...** (salvato nel file di impostazioni: `~/.config/soundtext/
   settings.json` su Linux, `%APPDATA%\SoundText\settings.json` su
   Windows, `~/Library/Application Support/SoundText/settings.json` su
   macOS);
2. la variabile d'ambiente `SOUNDTEXT_SOUNDFONT`, se impostata;
3. alcuni percorsi comuni di sistema, tra cui:
   - `~/.local/share/soundfonts/FluidR3_GM.sf2` (Linux)
   - `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora)
   - `/usr/share/soundfonts/FluidR3_GM.sf2` (Arch/CachyOS)
   - `%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` (Windows)
   - `~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (macOS)
   - `/opt/homebrew/share/soundfonts/FluidR3_GM.sf2` (macOS, Homebrew su
     Apple Silicon)

   L'elenco completo dei percorsi cercati per ciascun sistema e' nella
   sezione Installazione corrispondente, piu' sotto in questa guida.

Se hai scaricato `FluidR3_GM.sf2` in una posizione diversa (o vuoi usarne
un altro), basta selezionarlo da **Suoni → SoundFont → Scegli SoundFont (.sf2)...**:
resta impostato per tutte le riproduzioni successive, in tutti i progetti.
**Suoni → SoundFont → Mostra SoundFont in uso** indica quale file verra' usato in
questo momento (e con quale motore/player), e permette di verificare al
volo se il problema e' davvero il SoundFont o un fallback silenzioso.
**Suoni → SoundFont → Usa rilevamento automatico del SoundFont** rimuove
l'impostazione manuale e torna alla ricerca automatica.

### 12.4 SoundFont diversi per singolo strumento

Oltre al SoundFont predefinito (sezione 12.3, usato per tutta la
riproduzione), puoi assegnare un file `.sf2` diverso a un singolo
strumento — utile per usare un piano dedicato di buona qualita' insieme a
un font generico per il resto, o una batteria diversa da tutto il resto
dell'ensemble.

Da **Suoni → Gestisci strumenti...**, seleziona uno strumento
nell'elenco (predefinito o personalizzato: qui la scelta non e' limitata
ai soli personalizzati) e usa il pannello **SoundFont per lo strumento
selezionato**:
- **Scegli SoundFont...** assegna un file `.sf2` a quello strumento: verra'
  usato al posto del predefinito su ogni traccia che lo usa, in qualunque
  progetto.
- **Usa predefinito** rimuove l'assegnazione e torna al SoundFont
  generale.

L'elenco degli strumenti mostra un'indicazione (`· SoundFont: nome.sf2`)
per quelli con un override attivo.

**Limite**: effettivo solo con il motore fluidsynth persistente
(la libreria FluidSynth, usata di default se disponibile — vedi sezione 12 sopra):
con i fallback (CLI `fluidsynth`, `timidity`, `wildmidi`, player MIDI di
sistema) l'override viene ignorato e si usa comunque il SoundFont
predefinito su tutta la riproduzione. Con piu' strumenti overridati
contemporaneamente, la riproduzione richiede un rendering separato per
ciascun SoundFont coinvolto (poi ricombinati): brani con molti strumenti
diversamente assegnati impiegano quindi qualche istante in piu' a partire.

### 12.5 Metronomo

Il pulsante **Metronomo** (icona a piramide) nella barra dei comandi fa sentire un click a tempo durante la
riproduzione dell'ensemble, sincronizzato con gli eventuali cambi di
tempo/metrica del progetto (stessa mappa usata da barra di avanzamento e
campi Tempo/Metrica, vedi 2.7); lo stesso controllo, con click a
tempo/metrica costante, e' disponibile anche nel dialogo di importazione
audio e nel dialogo "Suona con la tastiera" (sezioni 10bis e 10ter), utile
per registrare/suonare a tempo.

Suono e volume del click si scelgono in **Opzioni → Metronomo**: tre
preset di suono (Click, Beep, Legno, Blocco di legno, Claves, Campanaccio, Triangolo, Hi-hat) e uno slider di volume (0-100%),
applicati immediatamente (anche a click gia' in corso) e provabili sul
posto col pulsante "Prova", senza bisogno di un Ok/Annulla separato. I
file audio del click sono sintetizzati e salvati in cache alla prima
esecuzione (nessuna dipendenza aggiuntiva), cosi' da generarli una sola
volta per macchina.

### 12.6 Umanizza

La voce **Riproduzione → Umanizza** (spuntabile) aggiunge una
piccola variazione casuale a timing e velocity delle note in riproduzione,
per un suono meno meccanico di una griglia perfettamente quantizzata. La
batteria riceve solo la variazione di velocity (uno spostamento di timing
su un pattern percussivo tende a suonare "impreciso" piuttosto che
"umano"); tutti gli altri strumenti ricevono entrambe. **Attivabile/
disattivabile anche a riproduzione in corso**: come un cambio di
Volume/Pan, la riproduzione si riavvia automaticamente dalla posizione
corrente con la nuova impostazione applicata.

L'intensita' si regola in **Opzioni → Umanizza** con uno slider (0-100%,
predefinito 50%), applicato immediatamente (riavvia la riproduzione in
corso, se Umanizza e' attivo). La variazione **non usa un seed fisso**:
due riproduzioni consecutive con le stesse impostazioni non suoneranno mai
identiche, proprio come due esecuzioni dal vivo dello stesso musicista.
Riguarda solo la riproduzione/l'export MIDI (il rendering finale in tick
assoluti): il testo della traccia e la timeline "di griglia" nell'editor
restano quelli scritti, invariati.

## 13. Informazioni su SoundText

Menu **Aiuto → Informazioni su SoundText...** mostra nome e numero di
versione del programma, l'autore (Sergio Scolaro) e la licenza
(GPL-3.0), insieme a chi decodifica i file mp3/m4a/flac/ogg (il decodificatore di Qt Multimedia o `ffmpeg`, sezione 10bis) con
un'icona di spunta verde se disponibile, una croce grigia altrimenti:
utile per verificare rapidamente l'installazione senza dover aprire un
terminale.

### 13.1 File di log

Quando qualcosa non va come previsto (la riproduzione ripiega su un motore
di qualita' inferiore, un SoundFont non si carica, un errore imprevisto),
SoundText lo annota con i dettagli tecnici nel file `soundtext.log` della
cartella di configurazione (`~/.config/soundtext` su Linux,
`%APPDATA%\SoundText` su Windows, `~/Library/Application Support/SoundText`
su macOS). **Aiuto → Apri il file di log** lo apre direttamente: e' la
prima cosa da allegare se segnali un problema. Un errore imprevisto viene
anche mostrato in una finestra, senza chiudere l'app.

## 14. Tecnologie, ringraziamenti e licenze

### 14.1 Le tecnologie usate

SoundText è scritto in **Python 3** e si appoggia a queste librerie e a
questi programmi:

| Componente | A cosa serve in SoundText | Licenza |
|---|---|---|
| Python | il linguaggio del programma | PSF License |
| Qt 6 con PySide6 | l'interfaccia grafica | LGPL-3.0 |
| NumPy | il calcolo sull'audio: effetti, amplificatore, profili NAM, analisi | BSD-3-Clause |
| FluidSynth | la sintesi delle note con i SoundFont (SoundText la usa direttamente) | LGPL-2.1 |
| mido | lettura e scrittura dei file MIDI | MIT |
| python-rtmidi (RtMidi) | le tastiere MIDI esterne | MIT |
| sounddevice e PortAudio | l'ascolto e la registrazione | MIT |
| pedalboard (Spotify) | la catena di effetti e i plugin VST3 | GPL-3.0 |
| JUCE (dentro pedalboard) | il motore audio di pedalboard e l'host VST3 | GPL-3.0 (nella forma usata da pedalboard) |
| VST3 SDK di Steinberg (dentro pedalboard) | il formato dei plugin VST3 | GPL-3.0 nella versione inclusa in pedalboard (le versioni più recenti dell'SDK sono passate alla licenza MIT) |
| lilv e LV2 | i plugin LV2 su Linux (libreria di sistema, facoltativa) | ISC |
| FFmpeg (dentro Qt Multimedia) | la lettura di mp3, m4a, flac, ogg | LGPL-2.1 |
| ffmpeg (programma esterno, facoltativo) | la lettura dei file audio se il PySide6 in uso non ha il decodificatore di Qt | LGPL-2.1 o GPL, secondo come è stato compilato |
| Neural Amp Modeler | il formato dei profili `.nam`: SoundText ne rifà il calcolo con NumPy | MIT (il progetto NAM) |
| SoundFont FluidR3_GM | i suoni General MIDI inclusi nelle build | MIT |

Alcuni formati e idee vengono da standard aperti o dalla letteratura:
**General MIDI** e il file MIDI standard, **MusicXML** (W3C Music Notation
Community Group) per l'export della partitura (10.1), l'algoritmo di
**Krumhansl-Schmuckler** per riconoscere la tonalità, i circuiti dei tone
stack Fender e Marshall per l'amplificatore (8.4).

Per costruire e verificare il programma servono anche **PyInstaller** (le
versioni portabili; la sua licenza GPL-2.0 ha un'eccezione per cui non si
estende al programma impacchettato), **pytest** (i test) e **reportlab**
(la guida PDF).

### 14.2 Ringraziamenti

SoundText esiste grazie al lavoro, quasi sempre volontario, di chi ha
creato e mantiene i progetti open source su cui si appoggia. Siamo in
debito in particolare con:

- la comunità di **FluidSynth**, che da oltre vent'anni fa suonare i
  SoundFont su ogni sistema, e **Frank Wen**, autore del SoundFont
  **FluidR3_GM**;
- **The Qt Company** e la comunità di **Qt for Python (PySide6)**;
- **Spotify** e gli sviluppatori di **pedalboard**, e il team di **JUCE**
  su cui pedalboard è costruito;
- il **RISM Digital Center** e gli sviluppatori di **Verovio**, che
  impagina la partitura (Vista → Partitura);
- **Alain de Cheveigné** e **Hideki Kawahara** (algoritmo YIN) e
  **Sebastian Böck** e **Gerhard Widmer** (SuperFlux), i cui articoli
  sono alla base del riconoscimento delle note dall'audio;
- gli autori di **mido**, di **RtMidi** (Gary P. Scavone) e di
  **python-rtmidi**, di **PortAudio** e di **sounddevice**;
- la comunità di **NumPy**;
- **Steven Atkinson** e la comunità di **Neural Amp Modeler**, con chi
  cattura e condivide i profili degli amplificatori (fra gli altri la
  raccolta di **pelennor2170** e il sito **Tone3000**);
- **David Robillard** e la comunità di **LV2** e **lilv**, e gli autori
  dei plugin di **Ardour** e **Guitarix**;
- **David Fau Casquel** (BestPlugins), che ha rilasciato le sue casse IR
  con licenza libera, e la comunità di **Guitarix**, che le conserva;
- **Steinberg**, che ha aperto il formato **VST3**;
- chi sviluppa i plugin gratuiti e open source, come **Surge XT**, e il
  **W3C Music Notation Community Group** per MusicXML.

Se usi SoundText e ti è utile, il modo migliore per ricambiare è
sostenere questi progetti: segnalare i problemi, contribuire, o fare una
donazione a quelli che la accettano.

### 14.3 Licenze e limiti alla distribuzione

Usare SoundText sul proprio computer, per qualunque scopo (anche
commerciale, anche per vendere la musica che ci si fa), **non ha limiti**:
le licenze qui sotto riguardano solo chi **distribuisce il programma** ad
altri (ne copia l'installazione, pubblica una build, lo vende o lo
include in un altro prodotto). La musica creata con SoundText è di chi la
crea: nessuna di queste licenze si applica ai brani, ai file `.st`, MIDI,
MusicXML o WAV prodotti.

**Il vincolo principale: la GPL-3.0.** **pedalboard** (con JUCE) è
distribuito con la licenza **GNU GPL versione 3**. Un programma che lo
include, come le build di SoundText, si può distribuire
solo alle condizioni della GPL-3.0:
- tutto SoundText va distribuito con la **licenza GPL-3.0** (o una
  compatibile), e chi lo riceve ha gli stessi diritti di usarlo,
  studiarlo, modificarlo e ridistribuirlo;
- insieme al programma (o su richiesta, secondo le regole della licenza)
  va reso disponibile il **codice sorgente completo** della versione
  distribuita, comprese le modifiche;
- non si possono aggiungere **restrizioni**: niente versioni a codice
  chiuso, niente divieti di copia o di modifica, niente sistemi che
  impediscano di installare una versione modificata;
- si può **vendere** una copia o chiedere un compenso per la
  distribuzione, ma chi la compra la può poi ridistribuire liberamente.

Una versione **a codice chiuso** di SoundText sarebbe possibile solo
togliendo pedalboard (e quindi la catena di effetti e i plugin VST3),
oppure sostituendolo o acquistando le licenze commerciali dei componenti
che le offrono (JUCE, Steinberg...).

**Le librerie LGPL: Qt/PySide6 e FluidSynth.** Si possono usare anche in
programmi non GPL, purché chi riceve il programma possa **sostituirle con
una propria versione**. Le build portabili di SoundText le tengono come
file separati accanto all'eseguibile, quindi la condizione è rispettata.
Vanno inclusi il testo della licenza LGPL e le indicazioni su dove avere
i sorgenti di queste librerie (per esempio un link alla versione usata).

**Le licenze permissive (MIT, BSD, ISC, PSF).** NumPy, mido, RtMidi,
PortAudio, sounddevice, lilv, il progetto NAM e il SoundFont FluidR3_GM
chiedono solo di **conservare gli avvisi di copyright e il testo della
licenza** nella distribuzione.

**Marchi.** VST è un marchio registrato di Steinberg Media Technologies
GmbH, Qt di The Qt Company: i nomi si possono citare per dire che il
programma supporta quei formati o usa quelle librerie, non per far
credere che SoundText sia un loro prodotto. L'uso del logo VST ha regole
proprie di Steinberg.

**Contenuti scaricati e plugin di altri.**
- I **profili NAM consigliati** (Suoni → Scarica → Scarica profili NAM
  consigliati) vengono dalla raccolta di pelennor2170, con licenza
  GPL-3.0: SoundText li scarica sul computer dell'utente, non li include
  nelle build. Chi li ridistribuisce deve rispettarne la licenza.
- Le **casse IR consigliate** (Suoni → Scarica → Scarica casse IR per gli
  amplificatori NAM) sono il pacchetto BestPlugins Mega Pack 2 di David Fau
  Casquel, con licenza GPL v2 o successiva: anche queste SoundText le
  scarica sul computer dell'utente, insieme al testo della licenza, e non
  le include nelle build.
- I **plugin VST3 e LV2** (8.7) sono programmi di terzi, ciascuno con la
  propria licenza, anche a pagamento: SoundText li carica, ma non li
  include. Per distribuirli insieme a SoundText serve il permesso dei
  loro autori.
- I **SoundFont** scelti dall'utente hanno ciascuno la propria licenza:
  prima di includerne uno diverso da FluidR3_GM in una distribuzione, va
  controllata.

**La licenza di SoundText.** SoundText (Copyright © 2026 Sergio
Scolaro) è distribuito con la licenza **GPL-3.0**: il testo è nel file `LICENSE`. Autori, licenze e testi
integrali dei componenti di terze parti sono in `THIRD_PARTY_NOTICES.md`
e nella cartella `licenses/`. Gli script di build (versioni portabili per
Linux e Windows, AppImage, installer per Windows) li copiano accanto al
programma, e l'installer per Windows mostra la licenza durante
l'installazione.

**In pratica, per chi distribuisce una build di SoundText:**
1. lasciare accanto al programma `LICENSE`, `THIRD_PARTY_NOTICES.md` e la
   cartella `licenses/` (gli script di build lo fanno da soli);
2. rendere disponibile il **codice sorgente** della versione distribuita
   (per esempio il repository, con il riferimento esatto alla versione);
3. se si aggiunge alla build un componente nuovo, aggiungerne autori e
   licenza in `THIRD_PARTY_NOTICES.md` e il testo in `licenses/`;
4. non includere plugin, SoundFont o profili di terzi senza aver
   controllato che la loro licenza lo permetta.

Queste indicazioni riassumono le licenze dei componenti per aiutare a
orientarsi: **non sono una consulenza legale**. Per una distribuzione
commerciale o in un contesto particolare conviene rivolgersi a un
esperto di licenze software. I testi completi delle licenze sono sui siti
dei rispettivi progetti.

---

# Installazione su Linux

## Debian / Ubuntu e derivate

```bash
sudo apt update
sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtmultimedia python3-pip fluidsynth fluid-soundfont-gm ffmpeg libportaudio2
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
Se `python3-pyside6.qtwidgets` non e' disponibile nella tua versione della
distribuzione, in alternativa:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo apt install fluidsynth fluid-soundfont-gm libportaudio2
python3 main.py
```
`libportaudio2` serve per l'ascolto diretto e il microfono; `ffmpeg` solo
per leggere mp3/m4a/flac/ogg se il PySide6 della distribuzione non ha il
decodificatore di Qt Multimedia (con PySide6 installato via pip, come nel
secondo modo, non serve). **Aiuto → Informazioni su SoundText...** mostra
chi decodifica i file audio.

## Fedora e derivate (RHEL, Nobara, ecc.)

```bash
sudo dnf install python3-pyside6 python3-pip fluidsynth fluid-soundfont-gm portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```
Se `python3-pyside6` non e' nei repository abilitati:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
sudo dnf install fluidsynth fluid-soundfont-gm portaudio
python3 main.py
```
`ffmpeg` serve solo se il PySide6 di sistema non legge gli mp3 (vedi
sopra) e non e' nei repository ufficiali Fedora: abilita
[RPM Fusion](https://rpmfusion.org/) e poi `sudo dnf install ffmpeg`,
oppure usa il secondo modo (PySide6 via pip).

## Arch Linux / CachyOS / Manjaro e derivate

```bash
sudo pacman -S pyside6 python-mido fluidsynth ffmpeg portaudio
paru -S soundfont-fluid      # oppure yay -S soundfont-fluid (AUR)
pip install --user sounddevice numpy pedalboard
cd soundtext
python3 main.py
```
(Il pacchetto ufficiale si chiama `pyside6`, senza prefisso `python-`.
`python-mido` e' invece nei repository ufficiali `extra`. `portaudio`
serve per l'ascolto diretto e il microfono, `ffmpeg` solo se il PySide6
di sistema non legge gli mp3.)

## openSUSE

```bash
sudo zypper install python3-PySide6 python3-pip fluidsynth ffmpeg portaudio
cd soundtext
pip install --user mido sounddevice numpy pedalboard
python3 main.py
```

## Note comuni

- Senza un SoundFont GM installato, `fluidsynth` non produce audio: verifica
  che esista un file tipo `/usr/share/soundfonts/FluidR3_GM.sf2` (Arch) o
  `/usr/share/sounds/sf2/FluidR3_GM.sf2` (Debian/Ubuntu/Fedora).
- In assenza di qualunque synth di sistema, il programma esporta comunque
  MIDI standard riproducibile con qualsiasi altro player.
- Gli strumenti personalizzati vengono salvati in
  `~/.config/soundtext/instruments.json` e sono quindi condivisi tra tutti
  i progetti dell'utente su quella macchina.

---

# Installazione su Windows

```powershell
# 1) Python 3.10+ da python.org (installer ufficiale, spunta "Add python.exe to PATH")
cd soundtext
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Sintesi audio (fluidsynth)**: scarica i binari Windows di fluidsynth
dalla pagina release ufficiale del progetto
([github.com/FluidSynth/fluidsynth/releases](https://github.com/FluidSynth/fluidsynth/releases),
archivio `-win10-x64.zip`) e metti la cartella `bin\` (contiene
`libfluidsynth-3.dll`) nel `PATH` di sistema, oppure copia il suo
contenuto nella cartella di SoundText: SoundText usa la libreria
direttamente (motore persistente, di default) e `fluidsynth.exe` come
ripiego. In alternativa, se hai [Chocolatey](https://chocolatey.org/):
```powershell
choco install fluidsynth
```

**SoundFont GM**: nessuno e' incluso nel sistema operativo (a differenza
di molte distribuzioni Linux). Scarica un SoundFont GM (es. `FluidR3_GM.sf2`,
liberamente disponibile) e impostalo da **Suoni → SoundFont → Scegli SoundFont
(.sf2)...** nel menu dell'app, oppure mettilo in
`%APPDATA%\SoundText\soundfonts\FluidR3_GM.sf2` per il rilevamento
automatico.

**Importazione audio**: niente da installare. I file mp3/m4a/flac/ogg li
legge il decodificatore di Qt Multimedia, gia' incluso in PySide6; il
pacchetto pip `sounddevice` (in requirements.txt) registra dal microfono
e include gia' la libreria PortAudio per Windows. Anche il riconoscimento
delle note e' scritto dentro SoundText.

**Playback senza player esterni**: a differenza di Linux, Windows non ha
di serie un player audio da riga di comando; SoundText rileva questo
caso e usa automaticamente il modulo `winsound` della libreria standard
di Python (nessuna dipendenza aggiuntiva) per riprodurre il rendering
offline. **Suoni → SoundFont → Mostra SoundFont in uso** mostra sempre quale
motore/player e' effettivamente attivo, utile per verificare
l'installazione. Il pulsante **Stop** interrompe correttamente la
riproduzione con qualunque motore, incluso l'ultima risorsa (il player
MIDI predefinito del sistema, usata quando non e' installato ne'
fluidsynth ne' un player CLI): SoundText lo apre in modo da poterlo
sempre terminare, invece di lasciarlo come processo slegato
dall'applicazione.

```powershell
python main.py
```

---

# Installazione su macOS

```bash
brew install python@3.12 fluidsynth portaudio   # portaudio opzionale, vedi sotto
cd soundtext
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

**Sintesi audio (fluidsynth)**: installata da Homebrew insieme al resto
(`libfluidsynth` finisce in `/opt/homebrew/lib` su Apple Silicon o
`/usr/local/lib` su Intel, gia' nel percorso di ricerca delle librerie
di sistema: SoundText la trova da solo, anche su Apple Silicon, senza
configurazione aggiuntiva).

**SoundFont GM**: come su Windows, macOS non ne include uno di serie.
Scarica un SoundFont GM (es. `FluidR3_GM.sf2`) e impostalo da
**Suoni → SoundFont → Scegli SoundFont (.sf2)...**, oppure mettilo in
`~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2` (o, se installato via
Homebrew in `/opt/homebrew/share/soundfonts/`) per il rilevamento
automatico.

**Importazione audio**: i file mp3/m4a/flac/ogg li legge il decodificatore
di Qt Multimedia, gia' incluso in PySide6 (niente `ffmpeg` da
installare); il pacchetto pip `sounddevice` registra dal microfono
(include gia' PortAudio, ma `brew install portaudio` non fa mai male se
il pacchetto pip desse problemi in fase di build). Anche il
riconoscimento delle note e' scritto dentro SoundText, niente da
compilare.

**Playback**: macOS include di serie `afplay` (player audio a riga di
comando incluso nel sistema operativo, nessuna installazione
richiesta), usato automaticamente per la riproduzione del rendering
offline — stessa strategia gia' in uso su Linux con `paplay`/`pw-play`.
**Suoni → SoundFont → Mostra SoundFont in uso** mostra sempre quale
motore/player e' effettivamente attivo.

**Permessi microfono**: alla prima registrazione da microfono, macOS
chiede il permesso di accesso al microfono per il terminale/IDE da cui
hai lanciato `python3 main.py`: va concesso da **Impostazioni di
Sistema → Privacy e sicurezza → Microfono**, altrimenti la
registrazione fallisce silenziosamente.

