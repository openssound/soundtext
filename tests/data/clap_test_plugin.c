/* Un file .clap minimo per i test di core.clap_host (tests/test_clap_host.py),
 * scritto senza gli header di CLAP: le strutture sono quelle della versione
 * 1.2 dell'interfaccia binaria (https://github.com/free-audio/clap).
 *
 * Contiene due plugin:
 *   test.soundtext.gain  effetto stereo con due parametri: "Gain" (0..2,
 *                        predefinito 1) e "Mode" (elenco: Normal, Invert).
 *                        Dichiara una latenza di 32 frame e ritarda davvero
 *                        l'audio di 32 frame. Ha uno stato (clap.state):
 *                        "STG1" + gain, mode e trim (double), dove trim e'
 *                        un guadagno interno che non e' un parametro e si
 *                        cambia solo caricando uno stato. Ha anche una
 *                        finta interfaccia (clap.gui) senza finestre: quando
 *                        la si mostra chiede all'host un timer e (non su
 *                        Windows) di sorvegliare una pipe in cui scrive un
 *                        byte; al terzo scatto del timer, arrivato il byte,
 *                        mette gain a 1.5 e trim a 0.5 come farebbe l'utente,
 *                        chiede una misura nuova e dice all'host di chiudere.
 *   test.soundtext.sine  strumento: una sinusoide per ogni nota tenuta, con
 *                        le note ricevute come eventi MIDI.
 *
 * Si compila con:  cc -shared -fPIC -o test.clap clap_test_plugin.c -lm
 */
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#if !defined(_WIN32)
#include <unistd.h>
#endif

typedef struct { uint32_t major, minor, revision; } clap_version_t;

typedef struct {
    clap_version_t clap_version;
    const char *id, *name, *vendor, *url, *manual_url, *support_url, *version, *description;
    const char *const *features;
} clap_plugin_descriptor_t;

typedef struct clap_host {
    clap_version_t clap_version;
    void *host_data;
    const char *name, *vendor, *url, *version;
    const void *(*get_extension)(const struct clap_host *, const char *);
    void (*request_restart)(const struct clap_host *);
    void (*request_process)(const struct clap_host *);
    void (*request_callback)(const struct clap_host *);
} clap_host_t;

typedef struct { uint32_t size, time; uint16_t space_id, type; uint32_t flags; } clap_event_header_t;
typedef struct { clap_event_header_t header; uint16_t port_index; uint8_t data[3]; } clap_event_midi_t;
typedef struct {
    clap_event_header_t header; uint32_t param_id; void *cookie; int32_t note_id;
    int16_t port_index, channel, key; double value;
} clap_event_param_value_t;

typedef struct clap_input_events {
    void *ctx;
    uint32_t (*size)(const struct clap_input_events *);
    const clap_event_header_t *(*get)(const struct clap_input_events *, uint32_t);
} clap_input_events_t;

typedef struct clap_output_events {
    void *ctx;
    bool (*try_push)(const struct clap_output_events *, const clap_event_header_t *);
} clap_output_events_t;

typedef struct {
    float **data32; double **data64; uint32_t channel_count, latency; uint64_t constant_mask;
} clap_audio_buffer_t;

typedef struct {
    int64_t steady_time; uint32_t frames_count; const void *transport;
    const clap_audio_buffer_t *audio_inputs; clap_audio_buffer_t *audio_outputs;
    uint32_t audio_inputs_count, audio_outputs_count;
    const clap_input_events_t *in_events; const clap_output_events_t *out_events;
} clap_process_t;

typedef struct clap_plugin {
    const clap_plugin_descriptor_t *desc;
    void *plugin_data;
    bool (*init)(const struct clap_plugin *);
    void (*destroy)(const struct clap_plugin *);
    bool (*activate)(const struct clap_plugin *, double, uint32_t, uint32_t);
    void (*deactivate)(const struct clap_plugin *);
    bool (*start_processing)(const struct clap_plugin *);
    void (*stop_processing)(const struct clap_plugin *);
    void (*reset)(const struct clap_plugin *);
    int32_t (*process)(const struct clap_plugin *, const clap_process_t *);
    const void *(*get_extension)(const struct clap_plugin *, const char *);
    void (*on_main_thread)(const struct clap_plugin *);
} clap_plugin_t;

typedef struct {
    uint32_t id, flags; void *cookie; char name[256]; char module[1024];
    double min_value, max_value, default_value;
} clap_param_info_t;

typedef struct {
    uint32_t (*count)(const clap_plugin_t *);
    bool (*get_info)(const clap_plugin_t *, uint32_t, clap_param_info_t *);
    bool (*get_value)(const clap_plugin_t *, uint32_t, double *);
    bool (*value_to_text)(const clap_plugin_t *, uint32_t, double, char *, uint32_t);
    bool (*text_to_value)(const clap_plugin_t *, uint32_t, const char *, double *);
    void (*flush)(const clap_plugin_t *, const clap_input_events_t *, const clap_output_events_t *);
} clap_plugin_params_t;

typedef struct {
    uint32_t id; char name[256]; uint32_t flags, channel_count; const char *port_type; uint32_t in_place_pair;
} clap_audio_port_info_t;

typedef struct {
    uint32_t (*count)(const clap_plugin_t *, bool);
    bool (*get)(const clap_plugin_t *, uint32_t, bool, clap_audio_port_info_t *);
} clap_plugin_audio_ports_t;

typedef struct { uint32_t id, supported_dialects, preferred_dialect; char name[256]; } clap_note_port_info_t;

typedef struct {
    uint32_t (*count)(const clap_plugin_t *, bool);
    bool (*get)(const clap_plugin_t *, uint32_t, bool, clap_note_port_info_t *);
} clap_plugin_note_ports_t;

typedef struct { uint32_t (*get)(const clap_plugin_t *); } clap_plugin_latency_t;

typedef struct clap_istream {
    void *ctx;
    int64_t (*read)(const struct clap_istream *, void *, uint64_t);
} clap_istream_t;

typedef struct clap_ostream {
    void *ctx;
    int64_t (*write)(const struct clap_ostream *, const void *, uint64_t);
} clap_ostream_t;

typedef struct {
    bool (*save)(const clap_plugin_t *, const clap_ostream_t *);
    bool (*load)(const clap_plugin_t *, const clap_istream_t *);
} clap_plugin_state_t;

typedef struct { const char *api; void *handle; } clap_window_t;

typedef struct {
    bool (*is_api_supported)(const clap_plugin_t *, const char *, bool);
    bool (*get_preferred_api)(const clap_plugin_t *, const char **, bool *);
    bool (*create)(const clap_plugin_t *, const char *, bool);
    void (*destroy)(const clap_plugin_t *);
    bool (*set_scale)(const clap_plugin_t *, double);
    bool (*get_size)(const clap_plugin_t *, uint32_t *, uint32_t *);
    bool (*can_resize)(const clap_plugin_t *);
    bool (*get_resize_hints)(const clap_plugin_t *, void *);
    bool (*adjust_size)(const clap_plugin_t *, uint32_t *, uint32_t *);
    bool (*set_size)(const clap_plugin_t *, uint32_t, uint32_t);
    bool (*set_parent)(const clap_plugin_t *, const clap_window_t *);
    bool (*set_transient)(const clap_plugin_t *, const clap_window_t *);
    void (*suggest_title)(const clap_plugin_t *, const char *);
    bool (*show)(const clap_plugin_t *);
    bool (*hide)(const clap_plugin_t *);
} clap_plugin_gui_t;

typedef struct {
    void (*resize_hints_changed)(const clap_host_t *);
    bool (*request_resize)(const clap_host_t *, uint32_t, uint32_t);
    bool (*request_show)(const clap_host_t *);
    bool (*request_hide)(const clap_host_t *);
    void (*closed)(const clap_host_t *, bool);
} clap_host_gui_t;

typedef struct { void (*on_timer)(const clap_plugin_t *, uint32_t); } clap_plugin_timer_support_t;

typedef struct {
    bool (*register_timer)(const clap_host_t *, uint32_t, uint32_t *);
    bool (*unregister_timer)(const clap_host_t *, uint32_t);
} clap_host_timer_support_t;

typedef struct { void (*on_fd)(const clap_plugin_t *, int, uint32_t); } clap_plugin_posix_fd_support_t;

typedef struct {
    bool (*register_fd)(const clap_host_t *, int, uint32_t);
    bool (*modify_fd)(const clap_host_t *, int, uint32_t);
    bool (*unregister_fd)(const clap_host_t *, int);
} clap_host_posix_fd_support_t;

typedef struct {
    uint32_t (*get_plugin_count)(const void *);
    const clap_plugin_descriptor_t *(*get_plugin_descriptor)(const void *, uint32_t);
    const clap_plugin_t *(*create_plugin)(const void *, const clap_host_t *, const char *);
} clap_plugin_factory_t;

typedef struct {
    clap_version_t clap_version;
    bool (*init)(const char *);
    void (*deinit)(void);
    const void *(*get_factory)(const char *);
} clap_plugin_entry_t;

#define LATENCY 32
#define VERSION {1, 2, 0}

/* ------------------------------------------------------------ stato */

typedef struct {
    clap_plugin_t plugin;
    bool is_sine;
    double rate, gain, mode, trim;
    float delay[2][LATENCY];
    uint32_t delay_pos;
    bool held[128];
    double phase[128];
    const clap_host_t *host;
    bool gui_open, gui_has_parent, fd_seen;
    uint32_t timer_id, ticks, gui_width, gui_height;
    int pipe_fds[2];
} state_t;

static state_t *state_of(const clap_plugin_t *p) { return (state_t *)p->plugin_data; }

static void clear_state(state_t *s) {
    memset(s->delay, 0, sizeof s->delay);
    s->delay_pos = 0;
    memset(s->held, 0, sizeof s->held);
    memset(s->phase, 0, sizeof s->phase);
}

/* -------------------------------------------------------- estensioni */

static uint32_t params_count(const clap_plugin_t *p) { return state_of(p)->is_sine ? 0 : 2; }

static bool params_info(const clap_plugin_t *p, uint32_t index, clap_param_info_t *info) {
    if (state_of(p)->is_sine || index > 1) return false;
    memset(info, 0, sizeof *info);
    if (index == 0) {
        info->id = 100; strcpy(info->name, "Gain"); strcpy(info->module, "Main");
        info->min_value = 0.0; info->max_value = 2.0; info->default_value = 1.0;
    } else {
        info->id = 200; strcpy(info->name, "Mode");
        info->flags = (1u << 0) | (1u << 16);                 /* a passi, elenco */
        info->min_value = 0.0; info->max_value = 1.0; info->default_value = 0.0;
    }
    return true;
}

static bool params_value(const clap_plugin_t *p, uint32_t id, double *value) {
    if (id == 100) { *value = state_of(p)->gain; return true; }
    if (id == 200) { *value = state_of(p)->mode; return true; }
    return false;
}

static bool params_text(const clap_plugin_t *p, uint32_t id, double value, char *out, uint32_t size) {
    (void)p;
    if (id != 200 || size < 8) return false;
    strcpy(out, value < 0.5 ? "Normal" : "Invert");
    return true;
}

static bool params_from_text(const clap_plugin_t *p, uint32_t id, const char *text, double *value) {
    (void)p; (void)id; (void)text; (void)value;
    return false;
}

static void apply_events(state_t *s, const clap_input_events_t *in, uint32_t frame, uint32_t *next) {
    uint32_t count = in ? in->size(in) : 0;
    while (*next < count) {
        const clap_event_header_t *h = in->get(in, *next);
        if (h->time > frame) break;
        if (h->space_id == 0 && h->type == 5) {                /* PARAM_VALUE */
            const clap_event_param_value_t *e = (const clap_event_param_value_t *)h;
            if (e->param_id == 100) s->gain = e->value;
            if (e->param_id == 200) s->mode = e->value;
        } else if (h->space_id == 0 && h->type == 10) {        /* MIDI */
            const clap_event_midi_t *e = (const clap_event_midi_t *)h;
            uint8_t status = e->data[0] & 0xF0, key = e->data[1] & 0x7F;
            if (status == 0x90 && e->data[2] > 0) { s->held[key] = true; s->phase[key] = 0.0; }
            else if (status == 0x80 || status == 0x90) s->held[key] = false;
        }
        (*next)++;
    }
}

static void params_flush(const clap_plugin_t *p, const clap_input_events_t *in, const clap_output_events_t *out) {
    uint32_t next = 0;
    (void)out;
    apply_events(state_of(p), in, UINT32_MAX, &next);
}

static const clap_plugin_params_t params_ext = {
    params_count, params_info, params_value, params_text, params_from_text, params_flush};

static uint32_t audio_ports_count(const clap_plugin_t *p, bool is_input) {
    return (is_input && state_of(p)->is_sine) ? 0 : 1;
}

static bool audio_ports_get(const clap_plugin_t *p, uint32_t index, bool is_input, clap_audio_port_info_t *info) {
    if (index != 0 || (is_input && state_of(p)->is_sine)) return false;
    memset(info, 0, sizeof *info);
    strcpy(info->name, is_input ? "In" : "Out");
    info->flags = 1; info->channel_count = 2; info->port_type = "stereo"; info->in_place_pair = UINT32_MAX;
    return true;
}

static const clap_plugin_audio_ports_t audio_ports_ext = {audio_ports_count, audio_ports_get};

static uint32_t note_ports_count(const clap_plugin_t *p, bool is_input) {
    return (is_input && state_of(p)->is_sine) ? 1 : 0;
}

static bool note_ports_get(const clap_plugin_t *p, uint32_t index, bool is_input, clap_note_port_info_t *info) {
    if (index != 0 || !is_input || !state_of(p)->is_sine) return false;
    memset(info, 0, sizeof *info);
    info->supported_dialects = 2; info->preferred_dialect = 2;      /* MIDI */
    strcpy(info->name, "Notes");
    return true;
}

static const clap_plugin_note_ports_t note_ports_ext = {note_ports_count, note_ports_get};

static uint32_t latency_get(const clap_plugin_t *p) { return state_of(p)->is_sine ? 0 : LATENCY; }

static const clap_plugin_latency_t latency_ext = {latency_get};

/* Lo stato si scrive e si legge a pezzi di 5 byte: l'host deve reggere le
 * chiamate ripetute, e una lettura puo' dare meno byte di quelli chiesti. */
#define STATE_SIZE (4 + 3 * sizeof(double))

static bool state_save(const clap_plugin_t *p, const clap_ostream_t *stream) {
    state_t *s = state_of(p);
    char data[STATE_SIZE];
    double values[3] = {s->gain, s->mode, s->trim};
    memcpy(data, "STG1", 4);
    memcpy(data + 4, values, sizeof values);
    for (uint64_t done = 0; done < STATE_SIZE;) {
        uint64_t chunk = STATE_SIZE - done < 5 ? STATE_SIZE - done : 5;
        int64_t written = stream->write(stream, data + done, chunk);
        if (written <= 0) return false;
        done += (uint64_t)written;
    }
    return true;
}

static bool state_load(const clap_plugin_t *p, const clap_istream_t *stream) {
    state_t *s = state_of(p);
    char data[STATE_SIZE];
    double values[3];
    for (uint64_t done = 0; done < STATE_SIZE;) {
        uint64_t chunk = STATE_SIZE - done < 5 ? STATE_SIZE - done : 5;
        int64_t got = stream->read(stream, data + done, chunk);
        if (got <= 0) return false;
        done += (uint64_t)got;
    }
    if (memcmp(data, "STG1", 4)) return false;
    memcpy(values, data + 4, sizeof values);
    s->gain = values[0]; s->mode = values[1]; s->trim = values[2];
    return true;
}

static const clap_plugin_state_t state_ext = {state_save, state_load};

/* ------------------------------------------------- finta interfaccia */

static bool gui_supported(const clap_plugin_t *p, const char *api, bool floating) {
    (void)p; (void)api;
    return !floating;
}
static bool gui_preferred(const clap_plugin_t *p, const char **api, bool *floating) {
    (void)p; (void)api; (void)floating;
    return false;
}
static bool gui_create(const clap_plugin_t *p, const char *api, bool floating) {
    state_t *s = state_of(p);
    (void)api;
    if (floating || s->gui_open) return false;
    s->gui_open = true; s->gui_has_parent = false; s->fd_seen = false; s->ticks = 0;
    s->gui_width = 320; s->gui_height = 120;
    s->pipe_fds[0] = s->pipe_fds[1] = -1;
    return true;
}
static void gui_destroy(const clap_plugin_t *p) {
    state_t *s = state_of(p);
    const clap_host_timer_support_t *timers = s->host->get_extension(s->host, "clap.timer-support");
    if (timers && s->timer_id) timers->unregister_timer(s->host, s->timer_id);
    s->timer_id = 0;
#if !defined(_WIN32)
    const clap_host_posix_fd_support_t *fds = s->host->get_extension(s->host, "clap.posix-fd-support");
    if (s->pipe_fds[0] >= 0) {
        if (fds && !s->fd_seen) fds->unregister_fd(s->host, s->pipe_fds[0]);
        close(s->pipe_fds[0]); close(s->pipe_fds[1]);
    }
#endif
    s->gui_open = false;
}
static bool gui_scale(const clap_plugin_t *p, double scale) { (void)p; return scale > 0.0; }
static bool gui_get_size(const clap_plugin_t *p, uint32_t *w, uint32_t *h) {
    *w = state_of(p)->gui_width; *h = state_of(p)->gui_height;
    return true;
}
static bool gui_can_resize(const clap_plugin_t *p) { (void)p; return false; }
static bool gui_hints(const clap_plugin_t *p, void *hints) { (void)p; (void)hints; return false; }
static bool gui_adjust(const clap_plugin_t *p, uint32_t *w, uint32_t *h) { (void)p; (void)w; (void)h; return true; }
static bool gui_set_size(const clap_plugin_t *p, uint32_t w, uint32_t h) {
    state_of(p)->gui_width = w; state_of(p)->gui_height = h;
    return true;
}
static bool gui_set_parent(const clap_plugin_t *p, const clap_window_t *window) {
    state_of(p)->gui_has_parent = window && window->api;
    return state_of(p)->gui_has_parent;
}
static bool gui_set_transient(const clap_plugin_t *p, const clap_window_t *window) { (void)p; (void)window; return false; }
static void gui_title(const clap_plugin_t *p, const char *title) { (void)p; (void)title; }

static bool gui_show(const clap_plugin_t *p) {
    state_t *s = state_of(p);
    const clap_host_timer_support_t *timers = s->host->get_extension(s->host, "clap.timer-support");
    if (!s->gui_open || !s->gui_has_parent || !timers) return false;
    if (!timers->register_timer(s->host, 5, &s->timer_id)) return false;
#if !defined(_WIN32)
    const clap_host_posix_fd_support_t *fds = s->host->get_extension(s->host, "clap.posix-fd-support");
    if (fds && pipe(s->pipe_fds) == 0) {
        fds->register_fd(s->host, s->pipe_fds[0], 1);           /* lettura */
        if (write(s->pipe_fds[1], "x", 1) != 1) return false;
    }
#else
    s->fd_seen = true;
#endif
    return true;
}
static bool gui_hide(const clap_plugin_t *p) { (void)p; return true; }

static const clap_plugin_gui_t gui_ext = {
    gui_supported, gui_preferred, gui_create, gui_destroy, gui_scale, gui_get_size, gui_can_resize, gui_hints,
    gui_adjust, gui_set_size, gui_set_parent, gui_set_transient, gui_title, gui_show, gui_hide};

static void timer_tick(const clap_plugin_t *p, uint32_t id) {
    state_t *s = state_of(p);
    if (!s->gui_open || id != s->timer_id) return;
    s->ticks++;
    /* al terzo scatto, col byte della pipe arrivato; dopo 400 scatti si
     * chiude comunque, senza cambiare nulla (il test se ne accorge) */
    if ((s->ticks >= 3 && s->fd_seen) || s->ticks == 400) {
        const clap_host_gui_t *host_gui = s->host->get_extension(s->host, "clap.gui");
        if (s->fd_seen) { s->gain = 1.5; s->trim = 0.5; }
        s->ticks = 1000;                                        /* una volta sola */
        if (host_gui) {
            if (host_gui->request_resize(s->host, 400, 150)) { s->gui_width = 400; s->gui_height = 150; }
            host_gui->closed(s->host, false);
        }
    }
}
static const clap_plugin_timer_support_t timer_ext = {timer_tick};

static void fd_ready(const clap_plugin_t *p, int fd, uint32_t flags) {
    state_t *s = state_of(p);
    (void)flags;
#if !defined(_WIN32)
    char byte;
    const clap_host_posix_fd_support_t *fds = s->host->get_extension(s->host, "clap.posix-fd-support");
    if (fd != s->pipe_fds[0] || read(fd, &byte, 1) != 1) return;
    s->fd_seen = true;
    if (fds) fds->unregister_fd(s->host, fd);
#else
    (void)s; (void)fd;
#endif
}
static const clap_plugin_posix_fd_support_t fd_ext = {fd_ready};

/* ------------------------------------------------------------ plugin */

static bool plugin_init(const clap_plugin_t *p) { (void)p; return true; }
static void plugin_destroy(const clap_plugin_t *p) { free(state_of(p)); }

static bool plugin_activate(const clap_plugin_t *p, double rate, uint32_t min_frames, uint32_t max_frames) {
    (void)min_frames; (void)max_frames;
    state_of(p)->rate = rate;
    clear_state(state_of(p));
    return true;
}

static void plugin_deactivate(const clap_plugin_t *p) { (void)p; }
static bool plugin_start(const clap_plugin_t *p) { (void)p; return true; }
static void plugin_stop(const clap_plugin_t *p) { (void)p; }
static void plugin_reset(const clap_plugin_t *p) { clear_state(state_of(p)); }
static void plugin_main_thread(const clap_plugin_t *p) { (void)p; }

static int32_t plugin_process(const clap_plugin_t *p, const clap_process_t *process) {
    state_t *s = state_of(p);
    uint32_t next = 0;
    if (process->audio_outputs_count < 1 || process->audio_outputs[0].channel_count < 2) return 0;
    float **out = process->audio_outputs[0].data32;
    for (uint32_t i = 0; i < process->frames_count; i++) {
        apply_events(s, process->in_events, i, &next);
        if (s->is_sine) {
            double sample = 0.0;
            for (int key = 0; key < 128; key++) {
                if (!s->held[key]) continue;
                sample += 0.25 * sin(s->phase[key]);
                s->phase[key] += 2.0 * M_PI * 440.0 * pow(2.0, (key - 69) / 12.0) / s->rate;
            }
            out[0][i] = out[1][i] = (float)sample;
        } else {
            float **in = process->audio_inputs[0].data32;
            double gain = s->gain * s->trim * (s->mode < 0.5 ? 1.0 : -1.0);
            for (int c = 0; c < 2; c++) {
                float delayed = s->delay[c][s->delay_pos];
                s->delay[c][s->delay_pos] = in[c][i];
                out[c][i] = (float)(delayed * gain);
            }
            s->delay_pos = (s->delay_pos + 1) % LATENCY;
        }
    }
    return 1;                                                   /* CLAP_PROCESS_CONTINUE */
}

static const void *plugin_extension(const clap_plugin_t *p, const char *id) {
    if (!strcmp(id, "clap.state")) return state_of(p)->is_sine ? NULL : &state_ext;
    if (!strcmp(id, "clap.gui")) return state_of(p)->is_sine ? NULL : &gui_ext;
    if (!strcmp(id, "clap.timer-support")) return state_of(p)->is_sine ? NULL : &timer_ext;
    if (!strcmp(id, "clap.posix-fd-support")) return state_of(p)->is_sine ? NULL : &fd_ext;
    if (!strcmp(id, "clap.params")) return &params_ext;
    if (!strcmp(id, "clap.audio-ports")) return &audio_ports_ext;
    if (!strcmp(id, "clap.note-ports")) return &note_ports_ext;
    if (!strcmp(id, "clap.latency")) return &latency_ext;
    return NULL;
}

/* ----------------------------------------------------------- fabbrica */

static const char *const gain_features[] = {"audio-effect", "utility", "stereo", NULL};
static const char *const sine_features[] = {"instrument", "synthesizer", "stereo", NULL};
static const char *const note_features[] = {"note-effect", NULL};

static const clap_plugin_descriptor_t descriptors[] = {
    {VERSION, "test.soundtext.gain", "Test Gain", "SoundText tests", "", "", "", "1.0", "Gain di prova", gain_features},
    {VERSION, "test.soundtext.sine", "Test Sine", "SoundText tests", "", "", "", "1.0", "Sinusoide di prova", sine_features},
    {VERSION, "test.soundtext.notes", "Test Notes", "SoundText tests", "", "", "", "1.0", "Non elabora audio", note_features},
};

static uint32_t factory_count(const void *f) { (void)f; return 3; }

static const clap_plugin_descriptor_t *factory_descriptor(const void *f, uint32_t index) {
    (void)f;
    return index < 3 ? &descriptors[index] : NULL;
}

static const clap_plugin_t *factory_create(const void *f, const clap_host_t *host, const char *id) {
    (void)f;
    for (int i = 0; i < 2; i++) {
        if (strcmp(id, descriptors[i].id)) continue;
        state_t *s = calloc(1, sizeof *s);
        s->is_sine = i == 1;
        s->gain = 1.0;
        s->trim = 1.0;
        s->host = host;
        s->plugin = (clap_plugin_t){&descriptors[i], s, plugin_init, plugin_destroy, plugin_activate,
                                    plugin_deactivate, plugin_start, plugin_stop, plugin_reset,
                                    plugin_process, plugin_extension, plugin_main_thread};
        return &s->plugin;
    }
    return NULL;
}

static const clap_plugin_factory_t factory = {factory_count, factory_descriptor, factory_create};

static bool entry_init(const char *path) { (void)path; return true; }
static void entry_deinit(void) {}
static const void *entry_factory(const char *id) {
    return strcmp(id, "clap.plugin-factory") ? NULL : &factory;
}

#if defined(_WIN32)
__declspec(dllexport)
#else
__attribute__((visibility("default")))
#endif
const clap_plugin_entry_t clap_entry = {VERSION, entry_init, entry_deinit, entry_factory};
