"""
Le etichette degli stili dei generatori (batteria, basso, accompagnamento,
riff e melodie, giri armonici), delle intensita' e delle durate degli
accordi: un posto solo per le finestre «Genera ...» di SoundText
(gui/rhythm_generate_dialog.py) e per la schermata Crea di SoundText Mobile
(mobile/engine.py), che prima ne teneva una copia.

Dentro una funzione, cosi' tr() vale per la lingua scelta al momento della
chiamata (in SoundText Mobile la lingua si sceglie dopo l'avvio del motore).
"""

from .i18n import tr


def generator_labels() -> dict:
    """{"drums", "bass", "comping", "riff", "progression", "intensity":
    [(chiave, etichetta)], "chord_duration": [(battute, etichetta)]}."""
    drum_style_labels = [
        ("rock", "Rock"),
        ("funk", "Funk"),
        ("disco", tr("Four-on-the-floor (disco)")),
        ("reggae", tr("Reggae (one drop)")),
        ("punk", "Punk"),
        ("soul", tr("Soul (Motown)")),
        ("bossa", tr("Bossa nova")),
        ("rocknroll", "Rock'n'roll"),
        ("shuffle", tr("Shuffle (blues, terzine)")),
        ("swing", tr("Swing (jazz, terzine)")),
        ("waltz", tr("Valzer (3/4)")),
        ("jazz_waltz", tr("Valzer jazz (3/4, terzine)")),
        ("ballad_68", tr("Ballata (6/8)")),
        ("afro_68", tr("Afro-cubano (6/8)")),
        ("blues_128", tr("Slow blues (12/8)")),
        ("slow_rock_128", tr("Slow rock anni '50 (12/8)")),
        ("hiphop", tr("Hip-hop (boom bap)")),
        ("halftime", "Half-time"),
        ("metal", tr("Metal (doppia cassa)")),
        ("country", tr("Country (train beat)")),
        ("samba", "Samba"),
        ("cha_cha", "Cha-cha-cha"),
        ("march", tr("Marcia")),
        ("rock_54", tr("Rock in 5/4 (3+2)")),
        ("jazz_54", tr("Jazz in 5/4 (terzine)")),
        ("rock_78", tr("Rock in 7/8 (2+2+3)")),
        ("balkan_78", tr("Balcanico in 7/8 (3+2+2)")),
    ]
    bass_style_labels = [
        ("root", tr("Fondamentale")),
        ("root_fifth", tr("Fondamentale/quinta")),
        ("walking", tr("Walking bass")),
        ("pedal", tr("Pedale (nota lunga)")),
        ("two_feel", tr("Due quarti (two-feel)")),
        ("octaves", tr("Ottave")),
        ("blues", tr("Blues 1-3-5-6")),
        ("eighths", tr("Ottavi (rock/pop/punk)")),
        ("reggae", "Reggae"),
        ("bossa", tr("Bossa nova")),
        ("shuffle", tr("Shuffle blues (terzine)")),
        ("waltz", tr("Valzer (1 del 3/4, oom-pah-pah)")),
    ]
    comping_style_labels = [
        ("block_chords", tr("Accordi battuti (comping)")),
        ("arpeggio_up", tr("Arpeggio ascendente")),
        ("broken_chord", tr("Accordo spezzato (Alberti)")),
        ("sustained", tr("Accordo sostenuto")),
        ("montuno", tr("Montuno (latin)")),
        ("skank_chords", tr("Skank reggae (in levare)")),
        ("quarter_chords", tr("Accordi su ogni quarto")),
        ("bossa_comp", tr("Bossa nova")),
        ("funk_stab", tr("Stop-time funk")),
        ("waltz_comp", tr("Valzer (accordi sul 2 e sul 3)")),
        ("arpeggio_68", tr("Arpeggio in 6/8")),
    ]
    progression_style_labels = [
        ("pop", tr("Pop (I-V-vi-IV)")),
        ("doo_wop", tr("Anni '50 / doo-wop (I-vi-IV-V)")),
        ("rock", tr("Rock (I-IV-I-V)")),
        ("canon", tr("Canone di Pachelbel")),
        ("blues_12", tr("Blues 12 battute")),
        ("jazz_251", tr("Jazz II-V-I")),
        ("turnaround", tr("Turnaround jazz (I-vi-ii-V)")),
        ("minor_pop", tr("Pop minore (i-VI-III-VII)")),
        ("andalusian", tr("Cadenza andalusa (i-VII-VI-V)")),
        ("minor_rock", tr("Rock minore (i-VII-VI-VII)")),
        ("minor_cadence", tr("Cadenza minore (i-iv-i-V7)")),
        ("minor_251", tr("Jazz II-V-I minore")),
        ("minor_blues_12", tr("Blues minore 12 battute")),
        ("three_chord", tr("Tre accordi (I-IV-V-I)")),
        ("ballad", tr("Ballata (I-iii-IV-V)")),
        ("royal_road", tr("J-pop / royal road (IV-V-iii-vi-ii-V-I)")),
        ("mixolydian", tr("Rock misolidio (I-bVII-IV-I)")),
        ("gospel", tr("Gospel (I-I7-IV-iv)")),
        ("circle", tr("Circolo delle quinte (maggiore)")),
        ("rhythm_changes", tr("Rhythm changes (jazz, due accordi per battuta)")),
        ("jazz_blues", tr("Blues jazz 12 battute")),
        ("minor_three", tr("Minore semplice (i-iv-v-i)")),
        ("minor_epic", tr("Minore epico (i-VI-VII-i)")),
        ("dorian_vamp", tr("Vamp dorico (i7-IV7)")),
        ("line_cliche", tr("Line cliché (i - i maj7 - i7 - i6)")),
        ("minor_circle", tr("Circolo delle quinte (minore)")),
        ("phrygian", tr("Frigio (i-bII)")),
    ]
    intensity_labels = [
        ("light", tr("Leggera (strofa, intro)")),
        ("normal", tr("Normale")),
        ("full", tr("Piena (ritornello)")),
        ("build", tr("In crescendo")),
    ]
    chord_duration_choices = [(tr("Mezza battuta"), 0.5), (tr("1 battuta"), 1.0), (tr("2 battute"), 2.0)]
    riff_style_labels = [
        ("riff_short", tr("Riff breve")),
        ("call_response", tr("Botta e risposta")),
        ("guide_tones", tr("Note guida (3ª/7ª)")),
        ("scale_run", tr("Passaggio scalare")),
        ("blues_lick", tr("Lick blues (terzine)")),
        ("arpeggio_updown", tr("Arpeggio su e giù")),
        ("reggae_skank", tr("Skank reggae (in levare)")),
        ("pedal_riff", tr("Nota ribattuta (drone)")),
        ("held_note", tr("Nota sostenuta")),
        ("melody_aaba", tr("Melodia a frasi (A A' B A)")),
        ("melody_period", tr("Melodia domanda e risposta (A A')")),
        ("melody_ballad", tr("Melodia lenta (ballad, A A' B A)")),
        ("melody_lively", tr("Melodia mossa (A A' B A)")),
    ]
    return {"drums": drum_style_labels, "bass": bass_style_labels, "comping": comping_style_labels,
            "riff": riff_style_labels, "progression": progression_style_labels, "intensity": intensity_labels,
            "chord_duration": [(value, label) for label, value in chord_duration_choices]}
