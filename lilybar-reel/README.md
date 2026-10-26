# The Lily Bar: Signature Bouquets showreel

A 15 s, 1920x1080, 60 fps motion piece for https://www.thelilybar.co/collection/signature-bouquet,
built entirely in code. See [STORYBOARD.md](STORYBOARD.md) for the research, the through-line object
and the beat-by-beat plan.

- `out/lilybar-signature-bouquets-15s.mp4`: 16:9 (1920x1080) cut, desktop-site layout
- `out/lilybar-signature-bouquets-15s-9x16.mp4`: 9:16 (1080x1920) cut for Reels/TikTok, mobile-site layout
  (category chips, two-column grid, cart as a bottom sheet), taps instead of a mouse pointer
- `scene.html` / `scene-9x16.html`: the two pieces; every style is computed from time inside `window.seek(t)`
- `soundtrack.html`: original 120 BPM track, synthesized with the Web Audio API (OfflineAudioContext)
- `render.js`: Playwright renderer (stills, beat sheet, audio, video)

## Re-render

```bash
npm install                                    # Fraunces variable font (@fontsource-variable/fraunces)
node render.js beats scene.html --out work/beats                  # one frame per beat + sheet.jpg
node render.js audio soundtrack.html --out work/music.wav
node render.js video scene.html --out out/lilybar-signature-bouquets-15s.mp4 \
  --audio work/music.wav --fps 60 --sub 3 --workers 3
node render.js video scene-9x16.html --out out/lilybar-signature-bouquets-15s-9x16.mp4 \
  --audio work/music.wav --fps 60 --sub 3 --workers 3
```

The video pass captures 3 subframes per frame, blends them with ffmpeg `tmix` for motion blur,
encodes H.264 and muxes the AAC audio.

## Swapping in real brand assets

- Products and prices: `PRODUCTS` at the top of the script in `scene.html`.
- Colours: the CSS variables in `:root` (`--accent` is the only accent).
- Typeface: the `@font-face` rule (one family is used throughout).
- Product photos: in `scene-9x16.html`, set `img` on each entry of `PRODUCTS` (e.g. `'assets/elora.jpg'`);
  the card tile and the cart thumbnail switch from the line drawing to the photo.
