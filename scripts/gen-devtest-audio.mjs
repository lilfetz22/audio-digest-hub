/**
 * Generates the local audio fixtures used by the /devtest player harness
 * (src/pages/DevPlayerTest.tsx).
 *
 * The WAVs are not committed — `*.wav` is gitignored, and they are ~5 MB each —
 * so run this once after cloning if you need to exercise the harness:
 *
 *   node scripts/gen-devtest-audio.mjs            # 120s parts, the default
 *   node scripts/gen-devtest-audio.mjs 30         # shorter parts
 *
 * Each part opens with N short beeps (part 1 = one beep, part 2 = two, ...) then
 * a steady tone at its own pitch, so a part transition is unmistakable with the
 * phone screen off.
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SAMPLE_RATE = 22050;
const BEEP_SECONDS = 0.18;
const BEEP_GAP_SECONDS = 0.22;
const BEEP_AMPLITUDE = 0.42;
const TONE_AMPLITUDE = 0.16;

function renderPart({ seconds, freq, beeps }) {
  const total = Math.floor(SAMPLE_RATE * seconds);
  const samples = Buffer.alloc(total * 2);
  const beepLen = BEEP_SECONDS * SAMPLE_RATE;
  const slotLen = beepLen + BEEP_GAP_SECONDS * SAMPLE_RATE;
  const beepZone = beeps * slotLen;

  for (let i = 0; i < total; i++) {
    let amplitude;
    if (i < beepZone) {
      const posInSlot = i - Math.floor(i / slotLen) * slotLen;
      amplitude = posInSlot < beepLen ? BEEP_AMPLITUDE : 0;
    } else {
      amplitude = TONE_AMPLITUDE;
    }

    if (amplitude === 0) {
      samples.writeInt16LE(0, i * 2);
      continue;
    }

    // Short fades keep the file from clicking at the edges.
    const envelope = Math.min(
      1,
      i / (SAMPLE_RATE * 0.02),
      (total - i) / (SAMPLE_RATE * 0.05),
    );
    const value = Math.sin((2 * Math.PI * freq * i) / SAMPLE_RATE) * amplitude * envelope;
    samples.writeInt16LE(Math.round(value * 32767), i * 2);
  }

  return samples;
}

function toWav(samples) {
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + samples.length, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20); // PCM
  header.writeUInt16LE(1, 22); // mono
  header.writeUInt32LE(SAMPLE_RATE, 24);
  header.writeUInt32LE(SAMPLE_RATE * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write('data', 36);
  header.writeUInt32LE(samples.length, 40);
  return Buffer.concat([header, samples]);
}

const seconds = Number(process.argv[2] ?? 120);
if (!Number.isFinite(seconds) || seconds <= 0) {
  console.error(`Invalid duration: ${process.argv[2]}`);
  process.exit(1);
}

const publicDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'public');
mkdirSync(publicDir, { recursive: true });

[
  { part: 1, freq: 440 },
  { part: 2, freq: 660 },
  { part: 3, freq: 880 },
].forEach(({ part, freq }) => {
  const path = join(publicDir, `devtest-part${part}.wav`);
  writeFileSync(path, toWav(renderPart({ seconds, freq, beeps: part })));
  console.log(`wrote ${path} — ${seconds}s, ${freq}Hz, ${part} beep(s)`);
});
