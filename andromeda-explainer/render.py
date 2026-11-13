#!/usr/bin/env python3
"""Render a seek(t) HTML motion piece to stills, a beat sheet, or an MP4.

The page must define window.W, window.H, window.DURATION and window.seek(t).
Optional: window.BPM (for beat sheets), window.OFFSET (seconds before beat 0),
window.ready (a Promise to await before capture, e.g. image decoding).

  python3 render.py stills scene.html --times 0.5,3,6.2 --out stills
  python3 render.py beats  scene.html --out beats            # one still per beat + sheet.jpg
  python3 render.py video  scene.html --out out.mp4 --audio music.wav [--fps 30 --sub 4]
  python3 render.py video  scene.html --out part.mp4 --from 4 --to 8   # quick partial
  python3 render.py video  http://localhost:8765/scene.html --out out.mp4  # ES-module pages
"""
import argparse, math, subprocess, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

KILL_CSS = "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}"


def open_page(p, html):
    if not html.startswith("http") and not Path(html).is_file():
        sys.exit(f"No such page: {html}")
    try:
        browser = p.chromium.launch(args=["--font-render-hinting=none", "--disable-lcd-text"])
    except Exception:
        browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--font-render-hinting=none", "--disable-lcd-text"])
    page = browser.new_page(device_scale_factor=1)
    page.on("pageerror", lambda e: print(f"PAGE ERROR: {e}", file=sys.stderr))
    page.on("console", lambda m: m.type == "error" and print(f"CONSOLE: {m.text}", file=sys.stderr))
    # a local server URL (needed for ES-module pages such as three.js) or a file path
    page.goto(html if html.startswith("http") else Path(html).resolve().as_uri())
    page.wait_for_function("typeof window.seek === 'function'", timeout=15000)
    meta = page.evaluate("({w: window.W||1080, h: window.H||1920, d: window.DURATION||0,"
                         " bpm: window.BPM||0, off: window.OFFSET||0})")
    page.set_viewport_size({"width": int(meta["w"]), "height": int(meta["h"])})
    page.add_style_tag(content=KILL_CSS)
    page.evaluate("""async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(i => i.complete ? 0 :
            new Promise(r => { i.onload = i.onerror = r; })));
        if (window.ready && window.ready.then) await window.ready;
    }""")
    return browser, page, meta


def grab(page, t, fmt="png", quality=92, frame_t=None):
    # FRAME_T = the output frame's own time. Subframes vary t for motion blur; text that swaps
    # (counters, typed text) should read FRAME_T so it stays crisp instead of ghosting.
    ft = t if frame_t is None else frame_t
    page.evaluate(f"window.FRAME_T = {ft:.6f}; window.seek({t:.6f})")
    if fmt == "jpeg":
        return page.screenshot(type="jpeg", quality=quality)
    return page.screenshot(type="png")


def contact_sheet(paths, labels, out, cols=6, thumb_w=240):
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(x).convert("RGB") for x in paths]
    w, h = ims[0].size
    tw, th = thumb_w, int(thumb_w * h / w)
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 8, rows * (th + 28) + 8), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x = 8 + (i % cols) * (tw + 8)
        y = 8 + (i // cols) * (th + 28)
        sheet.paste(im.resize((tw, th)), (x, y))
        d.text((x, y + th + 4), lab, fill=(220, 220, 220), font=font)
    sheet.save(out, quality=90)


def cmd_stills(a, times, labels=None):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser, page, meta = open_page(p, a.html)
        paths = []
        for i, t in enumerate(times):
            path = out / f"{i:03d}_{t:06.2f}s.png"
            path.write_bytes(grab(page, t))
            paths.append(path)
        browser.close()
    labels = labels or [f"{t:.2f}s" for t in times]
    contact_sheet(paths, labels, out / "sheet.jpg", cols=min(6, len(paths)))
    print(f"{len(paths)} stills + sheet.jpg in {out}")


def cmd_beats(a):
    with sync_playwright() as p:
        browser, page, meta = open_page(p, a.html)
        browser.close()
    bpm = a.bpm or meta["bpm"]
    if not bpm:
        sys.exit("No BPM: set window.BPM in the page or pass --bpm")
    beat = 60.0 / bpm
    off = meta["off"] if a.offset is None else a.offset
    times, labels, n = [], [], 0
    while off + n * beat < meta["d"] - 1e-6:
        t = off + n * beat + a.after
        times.append(min(t, meta["d"] - 1e-3))
        labels.append(f"beat {n + 1} | bar {n // 4 + 1}.{n % 4 + 1} | {t:.2f}s")
        n += 1
    cmd_stills(a, times, labels)


def cmd_video(a):
    fps, sub = a.fps, max(1, a.sub)
    with sync_playwright() as p:
        browser, page, meta = open_page(p, a.html)
        dur = meta["d"]
        t0 = a.t_from or 0.0
        t1 = min(a.t_to or dur, dur)
        nframes = int(round((t1 - t0) * fps))
        w, h = int(meta["w"]), int(meta["h"])
        vf = []
        if sub > 1:
            vf.append(f"tmix=frames={sub}")
            vf.append(f"select='eq(mod(n\\,{sub})\\,{sub - 1})'")
        vf.append(f"setpts=N/({fps}*TB)")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg",
               "-framerate", str(fps * sub), "-i", "-"]
        if a.audio:
            cmd += ["-ss", f"{t0:.3f}", "-i", a.audio]
        cmd += ["-filter:v", ",".join(vf), "-r", str(fps), "-c:v", "libx264", "-preset", a.preset,
                "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        if a.audio:
            cmd += ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{t1 - t0:.3f}"]
        cmd += [a.out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        start = time.time()
        shutter = a.shutter
        for k in range(nframes):
            base = t0 + k / fps
            for j in range(sub):
                if sub == 1:
                    t = base
                else:
                    t = base + (-shutter / 2 + (j + 0.5) * shutter / sub) / fps
                t = min(max(t, 0.0), dur - 1e-4)
                ff.stdin.write(grab(page, t, fmt="jpeg", quality=a.quality, frame_t=base))
            if k and k % fps == 0:
                el = time.time() - start
                print(f"  {k}/{nframes} frames, {el:.0f}s elapsed, ~{el / k * (nframes - k):.0f}s left",
                      flush=True)
        ff.stdin.close()
        rc = ff.wait()
        browser.close()
    if rc != 0:
        sys.exit("ffmpeg failed")
    print(f"wrote {a.out}: {w}x{h}, {t1 - t0:.2f}s, {fps}fps, {sub} subframes, "
          f"{time.time() - start:.0f}s render")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("stills"); s.add_argument("html"); s.add_argument("--times", required=True)
    s.add_argument("--out", default="stills")
    b = sp.add_parser("beats"); b.add_argument("html"); b.add_argument("--out", default="beats")
    b.add_argument("--bpm", type=float); b.add_argument("--offset", type=float)
    b.add_argument("--after", type=float, default=0.12, help="seconds after each beat to capture")
    v = sp.add_parser("video"); v.add_argument("html"); v.add_argument("--out", default="out.mp4")
    v.add_argument("--audio"); v.add_argument("--fps", type=int, default=30)
    v.add_argument("--sub", type=int, default=4, help="subframes blended per frame (motion blur)")
    v.add_argument("--shutter", type=float, default=0.5, help="0.5 = 180-degree shutter")
    v.add_argument("--from", dest="t_from", type=float); v.add_argument("--to", dest="t_to", type=float)
    v.add_argument("--crf", type=int, default=17); v.add_argument("--preset", default="medium")
    v.add_argument("--quality", type=int, default=92, help="JPEG quality of captured subframes")
    a = ap.parse_args()
    if a.cmd == "stills":
        cmd_stills(a, [float(x) for x in a.times.split(",")])
    elif a.cmd == "beats":
        cmd_beats(a)
    else:
        cmd_video(a)


if __name__ == "__main__":
    main()
