// Un contenitore MP4 (e M4A) scritto qui, senza librerie: i campioni gia' codificati
// da WebCodecs (AAC per l'audio, H.264 per il video) in un file che si apre ovunque.
// Non frammentato, con il «moov» prima dei dati (parte subito e si condivide bene).
// Si prova da Node con mobile/tests/mp4.test.cjs, che fa leggere il risultato a ffprobe.
"use strict";

const Mp4 = (() => {
  const enc = new TextEncoder();

  const u8 = (...n) => Uint8Array.from(n);
  const u16 = (v) => u8((v >>> 8) & 255, v & 255);
  const u32 = (v) => u8((v >>> 24) & 255, (v >>> 16) & 255, (v >>> 8) & 255, v & 255);
  const fourcc = (s) => enc.encode(s);
  const zeros = (n) => new Uint8Array(n);

  function concat(parts) {
    let size = 0;
    for (const p of parts) size += p.length;
    const out = new Uint8Array(size);
    let at = 0;
    for (const p of parts) { out.set(p, at); at += p.length; }
    return out;
  }

  const box = (type, ...children) => {
    const body = concat(children);
    return concat([u32(body.length + 8), fourcc(type), body]);
  };
  // box con versione e flag
  const full = (type, version, flags, ...children) => box(type, u8(version, (flags >>> 16) & 255, (flags >>> 8) & 255, flags & 255), ...children);

  // descrittori di «esds»: tag, lunghezza in forma estesa (4 byte), contenuto
  const desc = (tag, ...children) => {
    const body = concat(children);
    return concat([u8(tag, 0x80 | ((body.length >>> 21) & 127), 0x80 | ((body.length >>> 14) & 127), 0x80 | ((body.length >>> 7) & 127), body.length & 127), body]);
  };

  const MATRIX = concat([u32(0x00010000), u32(0), u32(0), u32(0), u32(0x00010000), u32(0), u32(0), u32(0), u32(0x40000000)]);

  // stts: una voce per ogni gruppo di campioni con la stessa durata
  function sttsOf(samples) {
    const entries = [];
    for (const s of samples) {
      const last = entries[entries.length - 1];
      if (last && last[1] === s.duration) last[0]++;
      else entries.push([1, s.duration]);
    }
    return full("stts", 0, 0, u32(entries.length), ...entries.map(([count, delta]) => concat([u32(count), u32(delta)])));
  }

  function sizesOf(samples) {
    return full("stsz", 0, 0, u32(0), u32(samples.length), ...samples.map((s) => u32(s.data.length)));
  }

  const mdhd = (timescale, duration) => full("mdhd", 0, 0, u32(0), u32(0), u32(timescale), u32(duration), u16(0x55C4), u16(0));
  const hdlr = (kind, name) => full("hdlr", 0, 0, u32(0), fourcc(kind), zeros(12), enc.encode(name + "\0"));
  const dinf = () => box("dinf", full("dref", 0, 0, u32(1), full("url ", 0, 1)));

  function tkhd(id, durationMs, volume, width, height) {
    return full("tkhd", 0, 3, u32(0), u32(0), u32(id), u32(0), u32(durationMs), zeros(8), u16(0), u16(0), u16(volume), u16(0),
                MATRIX, u32(width << 16), u32(height << 16));
  }

  // L'AudioSpecificConfig che WebCodecs da' nella descrizione del decoder, dentro «esds»
  function esds(config, bitrate) {
    const decoderInfo = desc(0x05, config);
    const decoderConfig = desc(0x04, u8(0x40, 0x15), u8(0, 0, 0), u32(bitrate || 0), u32(bitrate || 0), decoderInfo);
    return full("esds", 0, 0, desc(0x03, u16(1), u8(0), decoderConfig, desc(0x06, u8(2))));
  }

  function audioTrack(id, audio, offset, movieMs) {
    const rate = audio.sampleRate;
    const total = audio.samples.reduce((n, s) => n + s.duration, 0);
    const entry = box("mp4a", zeros(6), u16(1), zeros(8), u16(audio.channels), u16(16), u16(0), u16(0), u32(rate << 16), esds(audio.config, audio.bitrate));
    const stbl = box("stbl", full("stsd", 0, 0, u32(1), entry), sttsOf(audio.samples),
                     full("stsc", 0, 0, u32(1), u32(1), u32(audio.samples.length), u32(1)),
                     sizesOf(audio.samples), full("stco", 0, 0, u32(1), u32(offset)));
    return box("trak", tkhd(id, movieMs, 0x0100, 0, 0),
               box("mdia", mdhd(rate, total), hdlr("soun", "SoundText audio"),
                   box("minf", full("smhd", 0, 0, u16(0), u16(0)), dinf(), stbl)));
  }

  function videoTrack(id, video, offset, movieMs) {
    const total = video.samples.reduce((n, s) => n + s.duration, 0);
    const name = zeros(32);
    const entry = box("avc1", zeros(6), u16(1), u16(0), u16(0), zeros(12), u16(video.width), u16(video.height), u32(0x00480000), u32(0x00480000),
                      u32(0), u16(1), name, u16(0x0018), u16(0xFFFF), box("avcC", video.config));
    const sync = [];
    video.samples.forEach((s, i) => { if (s.key) sync.push(i + 1); });
    const stbl = box("stbl", full("stsd", 0, 0, u32(1), entry), sttsOf(video.samples),
                     full("stss", 0, 0, u32(sync.length), ...sync.map(u32)),
                     full("stsc", 0, 0, u32(1), u32(1), u32(video.samples.length), u32(1)),
                     sizesOf(video.samples), full("stco", 0, 0, u32(1), u32(offset)));
    return box("trak", tkhd(id, movieMs, 0, video.width, video.height),
               box("mdia", mdhd(video.timescale, total), hdlr("vide", "SoundText video"),
                   box("minf", full("vmhd", 0, 1, u16(0), zeros(6)), dinf(), stbl)));
  }

  // audio: { sampleRate, channels, config (AudioSpecificConfig), bitrate, samples: [{data, duration (in campioni)}] }
  // video: { width, height, timescale, config (avcC), samples: [{data, duration (nel timescale), key}] }
  // Uno dei due puo' mancare.
  function mux({ audio, video }) {
    const kind = video ? "mp42" : "M4A ";
    const ftyp = box("ftyp", fourcc(kind), u32(0), fourcc(kind), fourcc("isom"), fourcc("mp42"), fourcc("iso2"));
    const audioMs = audio ? Math.round(audio.samples.reduce((n, s) => n + s.duration, 0) * 1000 / audio.sampleRate) : 0;
    const videoMs = video ? Math.round(video.samples.reduce((n, s) => n + s.duration, 0) * 1000 / video.timescale) : 0;
    const movieMs = Math.max(audioMs, videoMs);
    const build = (audioOffset, videoOffset) => {
      const tracks = [];
      if (audio) tracks.push(audioTrack(tracks.length + 1, audio, audioOffset, movieMs));
      if (video) tracks.push(videoTrack(tracks.length + 1, video, videoOffset, movieMs));
      return box("moov", full("mvhd", 0, 0, u32(0), u32(0), u32(1000), u32(movieMs), u32(0x00010000), u16(0x0100), u16(0), zeros(8),
                              MATRIX, zeros(24), u32(tracks.length + 1)), ...tracks);
    };
    // la dimensione del «moov» non dipende dagli scostamenti: si costruisce due volte
    const moovSize = build(0, 0).length;
    const dataStart = ftyp.length + moovSize + 8;
    const audioBytes = audio ? audio.samples.reduce((n, s) => n + s.data.length, 0) : 0;
    const moov = build(dataStart, dataStart + audioBytes);
    const data = [];
    if (audio) for (const s of audio.samples) data.push(s.data);
    if (video) for (const s of video.samples) data.push(s.data);
    const body = concat(data);
    return concat([ftyp, moov, u32(body.length + 8), fourcc("mdat"), body]);
  }

  return { mux };
})();

if (typeof module !== "undefined") module.exports = { Mp4 };
