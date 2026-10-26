#!/usr/bin/env node
// Render a seek(t) HTML motion piece with Playwright.
//   node render.js stills scene.html --times 1,6,12.5 --out stills
//   node render.js beats  scene.html --out beats               (one still per beat + sheet.jpg)
//   node render.js audio  soundtrack.html --out music.wav       (OfflineAudioContext -> WAV)
//   node render.js video  scene.html --out final.mp4 --audio music.wav [--fps 60 --sub 3 --workers 3]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const argv = process.argv.slice(2);
const cmd = argv[0], html = argv[1];
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i > 0 ? argv[i + 1] : d; };

async function open(browser, file) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE:', m.text()); });
  await page.goto('file://' + path.resolve(file));
  return page;
}
async function openScene(browser) {
  const page = await open(browser, html);
  await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important}' });
  await page.waitForFunction(() => window.READY === true, null, { timeout: 30000 });
  return page;
}
const grab = (page, t, frameT, type, file, quality) =>
  page.evaluate(([t, ft]) => { window.FRAME_T = ft; window.seek(t); }, [t, frameT])
    .then(() => page.screenshot(type === 'png' ? { path: file, type: 'png' } : { path: file, type: 'jpeg', quality }));

function sheet(files, labels, out, cols = 5) {
  const py = `
import sys, json
from PIL import Image, ImageDraw, ImageFont
files, labels, out, cols = json.loads(sys.argv[1]), json.loads(sys.argv[2]), sys.argv[3], int(sys.argv[4])
tw = 384; th = int(tw * 1080 / 1920)
rows = (len(files) + cols - 1) // cols
S = Image.new('RGB', (cols * (tw + 8) + 8, rows * (th + 26) + 8), (24, 24, 24))
d = ImageDraw.Draw(S)
try: f = ImageFont.truetype('DejaVuSans.ttf', 14)
except Exception: f = ImageFont.load_default()
for i, (p, l) in enumerate(zip(files, labels)):
    x = 8 + (i % cols) * (tw + 8); y = 8 + (i // cols) * (th + 26)
    S.paste(Image.open(p).convert('RGB').resize((tw, th), Image.LANCZOS), (x, y))
    d.text((x, y + th + 4), l, fill=(225, 225, 225), font=f)
S.save(out, quality=90)`;
  const r = spawnSync('python3', ['-I', '-c', py, JSON.stringify(files), JSON.stringify(labels), out, String(cols)], { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('contact sheet failed');
}

async function stills(times, labels, out) {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await openScene(browser);
  const files = [];
  for (let i = 0; i < times.length; i++) {
    const f = path.join(out, `${String(i).padStart(3, '0')}_${times[i].toFixed(2)}s.png`);
    await grab(page, times[i], times[i], 'png', f);
    files.push(f);
  }
  await browser.close();
  sheet(files, labels || times.map(t => t.toFixed(2) + 's'), path.join(out, 'sheet.jpg'));
  console.log(`${files.length} stills + sheet.jpg in ${out}`);
}

async function audio() {
  const out = opt('out', 'music.wav');
  const browser = await chromium.launch();
  const page = await open(browser, html);
  const { b64, peak } = await page.evaluate(() => window.renderAudio());
  fs.writeFileSync(out, Buffer.from(b64, 'base64'));
  await browser.close();
  console.log(`wrote ${out} (raw peak ${peak.toFixed(3)}, normalised to -1 dBFS)`);
}

async function video() {
  const fps = +opt('fps', 60), sub = +opt('sub', 3), workers = +opt('workers', 3);
  const shutter = +opt('shutter', 0.6), q = +opt('quality', 94);
  const out = opt('out', 'final.mp4'), audioFile = opt('audio');
  const t0 = +opt('from', 0), browser0 = await chromium.launch();
  const p0 = await openScene(browser0);
  const dur = await p0.evaluate(() => window.DURATION);
  await browser0.close();
  const t1 = Math.min(+opt('to', dur), dur);
  const nframes = Math.round((t1 - t0) * fps), total = nframes * sub;
  const dir = opt('frames', path.join(path.dirname(path.resolve(out)), 'frames'));
  fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  const start = Date.now();
  let done = 0;
  const chunk = Math.ceil(nframes / workers);
  await Promise.all([...Array(workers)].map(async (_, w) => {
    const browser = await chromium.launch();
    const page = await openScene(browser);
    for (let k = w * chunk; k < Math.min(nframes, (w + 1) * chunk); k++) {
      const base = t0 + k / fps;
      for (let j = 0; j < sub; j++) {
        // subframes spread across the shutter, centred on the frame time
        const t = Math.min(Math.max(sub === 1 ? base : base + ((j + 0.5) / sub - 0.5) * shutter / fps, 0), dur - 1e-4);
        await grab(page, t, base, 'jpeg', path.join(dir, `f_${String(k * sub + j).padStart(6, '0')}.jpg`), q);
      }
      if (++done % 60 === 0) {
        const el = (Date.now() - start) / 1000;
        console.log(`  ${done}/${nframes} frames, ${el.toFixed(0)}s elapsed, ~${(el / done * (nframes - done)).toFixed(0)}s left`);
      }
    }
    await browser.close();
  }));
  const vf = [];
  if (sub > 1) vf.push(`tmix=frames=${sub}`, `select='eq(mod(n\\,${sub})\\,${sub - 1})'`);
  vf.push(`setpts=N/(${fps}*TB)`);
  const args = ['-y', '-loglevel', 'error', '-framerate', String(fps * sub), '-i', path.join(dir, 'f_%06d.jpg')];
  if (audioFile) args.push('-ss', t0.toFixed(3), '-i', audioFile);
  args.push('-filter:v', vf.join(','), '-r', String(fps), '-c:v', 'libx264', '-preset', opt('preset', 'slow'),
    '-crf', opt('crf', '16'), '-pix_fmt', 'yuv420p', '-movflags', '+faststart');
  if (audioFile) args.push('-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-t', (t1 - t0).toFixed(3));
  args.push(out);
  const r = spawnSync('ffmpeg', args, { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('ffmpeg failed');
  if (!opt('keep')) fs.rmSync(dir, { recursive: true, force: true });
  console.log(`wrote ${out}: ${(t1 - t0).toFixed(2)}s, ${fps}fps, ${sub} subframes, ${((Date.now() - start) / 1000).toFixed(0)}s`);
}

(async () => {
  if (cmd === 'stills') await stills(opt('times').split(',').map(Number), null, opt('out', 'stills'));
  else if (cmd === 'beats') {
    const after = +opt('after', 0.2), times = [], labels = [];
    for (let n = 0; n < 30; n++) { const t = n * 0.5 + after; times.push(Math.min(t, 14.99)); labels.push(`beat ${n + 1} | bar ${Math.floor(n / 4) + 1}.${n % 4 + 1} | ${t.toFixed(2)}s`); }
    await stills(times, labels, opt('out', 'beats'));
  } else if (cmd === 'audio') await audio();
  else if (cmd === 'video') await video();
  else { console.error('usage: node render.js stills|beats|audio|video <html> [...]'); process.exit(1); }
})().catch(e => { console.error(e); process.exit(1); });
