// Il contenitore MP4 di mobile/mp4.js: si prova con i campioni veri che ffmpeg codifica
// (AAC e H.264), si scrive il file e lo si fa leggere e decodificare a ffprobe/ffmpeg.
// Senza ffmpeg la prova si salta. Si lancia con: node --test mobile/tests/*.test.cjs
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { Mp4 } = require("../mp4.js");

const have = (cmd) => spawnSync(cmd, ["-version"], { stdio: "ignore" }).status === 0;
const skip = !(have("ffmpeg") && have("ffprobe")) && "ffmpeg non c'e'";

function ffmpeg(...args) {
  const r = spawnSync("ffmpeg", ["-v", "error", "-y", ...args], { encoding: "buffer" });
  assert.strictEqual(r.status, 0, String(r.stderr));
  return r;
}

// l'AAC come lo da' WebCodecs: campioni grezzi (senza ADTS) e l'AudioSpecificConfig
function aacSamples(seconds, rate, channels) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "stmp4-"));
  const file = path.join(dir, "a.aac");
  ffmpeg("-f", "lavfi", "-i", `sine=frequency=440:sample_rate=${rate}:duration=${seconds}`, "-ac", String(channels), "-c:a", "aac", "-b:a", "96k", "-f", "adts", file);
  const bytes = fs.readFileSync(file);
  const samples = [];
  let config = null;
  for (let at = 0; at < bytes.length;) {
    assert.strictEqual(bytes[at], 0xFF);
    const length = ((bytes[at + 3] & 3) << 11) | (bytes[at + 4] << 3) | (bytes[at + 5] >> 5);
    const header = (bytes[at + 1] & 1) ? 7 : 9;                      // senza o con CRC
    if (!config) {
      const profile = ((bytes[at + 2] >> 6) & 3) + 1, index = (bytes[at + 2] >> 2) & 15;
      const channelConfig = ((bytes[at + 2] & 1) << 2) | (bytes[at + 3] >> 6);
      config = Uint8Array.of((profile << 3) | (index >> 1), ((index & 1) << 7) | (channelConfig << 3));
    }
    samples.push({ data: bytes.subarray(at + header, at + length), duration: 1024 });
    at += length;
  }
  return { sampleRate: rate, channels, config, bitrate: 96000, samples };
}

// l'H.264 come lo da' WebCodecs (formato avc): campioni con la lunghezza davanti e avcC
function h264Samples(seconds, fps, width, height) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "stmp4-"));
  const file = path.join(dir, "v.h264");
  ffmpeg("-f", "lavfi", "-i", `testsrc=size=${width}x${height}:rate=${fps}:duration=${seconds}`, "-c:v", "libx264", "-bf", "0", "-g", "10",
         "-pix_fmt", "yuv420p", "-bsf:v", "h264_mp4toannexb", "-f", "h264", file);
  const bytes = fs.readFileSync(file);
  const nals = [];
  for (let i = 0, start = -1; i + 3 <= bytes.length; i++) {
    if (bytes[i] === 0 && bytes[i + 1] === 0 && (bytes[i + 2] === 1 || (bytes[i + 2] === 0 && bytes[i + 3] === 1))) {
      const code = bytes[i + 2] === 1 ? 3 : 4;
      if (start >= 0) nals.push(bytes.subarray(start, i));
      start = i + code;
      i += code - 1;
    }
    if (i + 3 >= bytes.length && start >= 0) { nals.push(bytes.subarray(start)); break; }
  }
  const sps = nals.find((n) => (n[0] & 31) === 7), pps = nals.find((n) => (n[0] & 31) === 8);
  const lengthPrefixed = (nal) => Uint8Array.from([...Buffer.from([(nal.length >>> 24) & 255, (nal.length >>> 16) & 255, (nal.length >>> 8) & 255, nal.length & 255]), ...nal]);
  const samples = nals.filter((n) => [1, 5].includes(n[0] & 31)).map((n) => ({ data: lengthPrefixed(n), duration: 90000 / fps, key: (n[0] & 31) === 5 }));
  const config = Uint8Array.from([1, sps[1], sps[2], sps[3], 0xFF, 0xE1, sps.length >> 8, sps.length & 255, ...sps, 1, pps.length >> 8, pps.length & 255, ...pps]);
  return { width, height, timescale: 90000, config, samples };
}

function probe(file) {
  const r = spawnSync("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", file], { encoding: "utf8" });
  assert.strictEqual(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
}

function decodes(file) {                                             // ffmpeg decodifica tutto, senza un errore
  const r = spawnSync("ffmpeg", ["-v", "error", "-i", file, "-f", "null", "-"], { encoding: "utf8" });
  assert.strictEqual(r.status, 0, r.stderr);
  assert.strictEqual(r.stderr.trim(), "");
}

const write = (name, bytes) => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "stmp4-")), name);
  fs.writeFileSync(file, bytes);
  return file;
};

test("un M4A: l'AAC di ffmpeg si legge e si decodifica, con la durata giusta", { skip }, () => {
  for (const [rate, channels] of [[44100, 2], [48000, 1]]) {
    const audio = aacSamples(3, rate, channels);
    const file = write("a.m4a", Mp4.mux({ audio }));
    const info = probe(file);
    assert.strictEqual(info.streams.length, 1);
    const s = info.streams[0];
    assert.strictEqual(s.codec_name, "aac");
    assert.strictEqual(Number(s.sample_rate), rate);
    assert.strictEqual(s.channels, channels);
    const expected = audio.samples.length * 1024 / rate;
    assert.ok(Math.abs(Number(info.format.duration) - expected) < 0.02, `${info.format.duration} vs ${expected}`);
    assert.match(info.format.format_name, /mov,mp4/);
    decodes(file);
  }
});

test("un MP4 con video H.264 e audio AAC: due flussi, a tempo, decodificabili", { skip }, () => {
  const audio = aacSamples(2, 44100, 2);
  const video = h264Samples(2, 30, 320, 240);
  assert.ok(video.samples.length >= 55 && video.samples[0].key);
  const file = write("clip.mp4", Mp4.mux({ audio, video }));
  const info = probe(file);
  const kinds = info.streams.map((s) => s.codec_type).sort();
  assert.deepStrictEqual(kinds, ["audio", "video"]);
  const v = info.streams.find((s) => s.codec_type === "video");
  assert.strictEqual(v.codec_name, "h264");
  assert.strictEqual([v.width, v.height].join("x"), "320x240");
  assert.strictEqual(Number(v.nb_frames), video.samples.length);
  assert.ok(Math.abs(Number(v.duration) - 2) < 0.1, v.duration);
  const a = info.streams.find((s) => s.codec_type === "audio");
  assert.ok(Math.abs(Number(a.duration) - audio.samples.length * 1024 / 44100) < 0.02);
  decodes(file);
});

test("un MP4 solo video si legge", { skip }, () => {
  const video = h264Samples(1, 25, 160, 90);
  const file = write("v.mp4", Mp4.mux({ video }));
  assert.strictEqual(probe(file).streams.length, 1);
  decodes(file);
});
