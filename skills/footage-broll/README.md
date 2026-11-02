# footage-broll

**Real-looking B-roll for your videos, picked and cut by Claude.** Give it a talking-head video (or a voiceover) and its transcript. It plans which lines to cover, finds or makes a shot for each, and cuts every clip to land on your words, at your video's size and frame rate.

Each shot comes from the best of four places:

- **Your own footage and photos.** They show your real product, place and team, so they come first when you have them.
- **Free stock** from Pexels and Pixabay, for real-world shots like a market, a street or hands at work.
- **AI video** from whatever generator you have connected, for shots stock doesn't have. It can also animate your own product photos.
- **A shot list** for moments only you can film.

## What you get

You run `/footage-broll`, answer a few questions, approve a plan, and get back, in `broll/out/`:

- **The clips**, cut to length with no sound, each named by where it goes on your timeline (`02-tying_0m07s95.mp4` starts at 0:07.95).
- **`preview.mp4`**: your video with the clips cut in, for review.
- **`TIMING.md`**: every clip with its in and out point and the line it covers.
- **`CREDITS.md`**: who made each stock clip and under which licence, plus the prompt behind each AI clip.
- **`SHOTLIST.md`**: what to film yourself, if anything.

The preview is for checking. For the final cut, put the clips on a track above your video in your own editor.

## Install

Copy `skills/footage-broll/` into your project's `.claude/skills/` (or `~/.claude/skills/` to use it everywhere). With the skills CLI:

```
npx skills add roeybi/skill-bank
```

**Requirements:** Python 3.9+ and ffmpeg. For stock, a free API key from [Pexels](https://www.pexels.com/api/) and/or [Pixabay](https://pixabay.com/api/docs/), set as `PEXELS_API_KEY` / `PIXABAY_API_KEY` or in a `.env` file (keep `.env` out of git). For AI clips, any connected video generator. To work without a transcript, add `pip install faster-whisper`.

## How it works

1. **Inspects** your video (size, frame rate, length) and your footage folder, if you have one.
2. **Reads word timings** from your SRT or VTT, or transcribes the audio.
3. **Plans** a table of cutaways and waits for your OK. Each row has the line, the shot, the source and the reason. It keeps your face on the hook, personal lines and the call to action, and lands each shot on the word that names the thing.
4. **Sources** each shot. For stock, it searches both libraries and picks from a numbered contact sheet. For AI, it shows the cost first.
5. **Conforms** every clip: trim, slow motion if a clip is short, crop to fill the frame, frame-rate conversion, phone rotation and HDR fixes, and a slow push-in on photos. It then checks four frames of each clip.
6. **Delivers** the preview, timing sheet, credits and shot list.

Works with [motion-broll](https://github.com/Barty-Bart/motion-graphics/tree/main/skills/motion-broll): plan both together and add its renders as `"source": "motion"` rows, so all the B-roll shares one timeline and one preview.

## Scripts

| Script | Does |
|---|---|
| `setup.sh` | Checks ffmpeg, Python and keys, and creates `broll/` |
| `inspect_media.py` | Video or voiceover specs and a contact sheet, or a footage folder's frame strips |
| `words.py` | SRT/VTT to word timings, or transcription with faster-whisper |
| `stock.py` | Pexels and Pixabay search (numbered contact sheet) and download (with a credit file) |
| `conform.py` | Raw clip to a slot-ready clip, plus a check sheet |
| `deliver.py` | Preview render, `TIMING.md`, `CREDITS.md`, `SHOTLIST.md` |

## Licence

MIT. Stock clips keep their own licences (Pexels License, Pixabay Content License); see `reference/sourcing.md`.
