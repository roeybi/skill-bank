---
name: footage-broll
description: Plan, source and cut real-looking B-roll footage over a talking-head video or voiceover, timed to the speaker's words. Pulls free stock clips (Pexels, Pixabay), generates AI clips with whatever video model is connected, or uses the creator's own footage and photos, then conforms every clip to the video's size and frame rate and delivers the clips, a preview render, a timing sheet, credits and a shot list. Use whenever someone wants B-roll, cutaways, stock footage, AI footage or "something to cover" their talking head, jump cuts or voiceover, even if they don't say "B-roll". For animated graphic B-roll (UI, charts, kinetic type) use motion-broll instead.
---

# Footage B-roll

You make the cutaway shots for a creator's video: real-looking footage that shows what they are talking about, cut to land on the words. Each clip comes from one of four places:

| Source | When it wins |
|---|---|
| **Own** footage or photos | It shows *their* product, place or people. Most credible, always first choice when it exists. |
| **Stock** (Pexels, Pixabay) | Generic real-world things: a flower market, a city street, hands on a keyboard. Free, real, fast. |
| **AI** generation | What stock doesn't have, a specific composition, or a consistent stylised look. Animating *their* photo (image-to-video) is the best AI use. Costs credits. |
| **Shoot** | Only real footage of their thing will do and they don't have it. Becomes a row in a shot list for them to film. |

The output is a set of clips the creator drops into their editor, each named by its timeline in-point, plus a preview of their video with the clips cut in, `TIMING.md`, `CREDITS.md` and, if needed, `SHOTLIST.md`.

`$SKILL` below means this skill's folder. Work in a `broll/` folder in the user's project. The scripts need only Python 3 and ffmpeg.

## 1. Set up

```bash
bash $SKILL/scripts/setup.sh broll
```

It checks ffmpeg, reports whether the stock keys are set and creates `broll/{inputs/own,raw,out,work}`. Stock search needs a free key from Pexels and/or Pixabay. Ask the user to set it themselves (`export PEXELS_API_KEY=...` or a line in `.env`, with `.env` in `.gitignore`); keys should not pass through the chat.

## 2. Interview

Use AskUserQuestion, one round. Skip anything already answered.

- **The video** (or a voiceover audio file) and **the transcript** (SRT or VTT from their editor, Descript or YouTube). Without one, `words.py` can transcribe the audio if `faster-whisper` is installed.
- **Sources they're happy with:** stock, AI (which generator, and roughly what they'll spend), their own footage (a folder of clips and photos), a shot list for them to film.
- **Density:** light (2–4 cutaways a minute, only the strongest moments), medium (5–8, the default), heavy (10+, fast social edits). A voiceover-only video needs picture for its whole length.
- **Look and limits:** the feel (light, colour, camera), where the business is so streets, shops and people look right, and anything to avoid (competitors, faces, alcohol, lines that must stay on their face). Ask whether there are jump cuts they want covered.

## 3. Inspect

```bash
python3 $SKILL/scripts/inspect_media.py broll/inputs/source.mp4 broll/work          # size, fps, duration -> work/base.json, work/contact.png
python3 $SKILL/scripts/words.py broll/inputs/transcript.srt > broll/work/words.txt     # or: words.py source.mp4 --srt work/transcript.srt
python3 $SKILL/scripts/inspect_media.py broll/inputs/own broll/work                 # if they gave a footage folder
```

Look at `contact.png`. For a footage folder, look at every strip in `work/library/` and note in a line what each file shows and its best moment, so you can match lines to it. Phone rotation, variable frame rate and HDR are handled later by `conform.py`.

Word times from an SRT or VTT are spread evenly across each cue, so they are estimates (±0.2s). Transcribed audio gives real word times.

## 4. Plan, and get approval before sourcing anything

Show a table, one row per cutaway:

| # | In–Out | The line it covers | The shot | Source | Search terms or prompt | Why |

Then the cost: number of AI clips and the estimated credits or money (use the generator's own estimate tool if it has one).

**What earns a cutaway.** The line names something you can *see* (an object, a place, an action, a process); it lists things (one shot per item, cut on each item); it jumps in time or place ("every morning…", "in Tel Aviv…"); there's a jump cut to hide; or a long explanation needs a change of picture to keep pace.

**What stays on the face.** The first 1.5–2 seconds (viewers decide on the person, so the hook stays on camera), personal, emotional and opinion lines, jokes and punchlines, moments where the speaker gestures or shows something, and the call to action. Leave at least ~2 seconds of face between groups of cutaways; a sub-second flash of face between two shots looks like a mistake (`conform.py` warns about it).

**Timing.** Start the shot on the word that names the thing, or 2–3 frames before it, so the picture arrives with the word. End it at the end of the phrase, not mid-word. Most shots run 1.5–4 seconds; a list of short items can go faster (~1s each); a slow, beautiful shot can hold 5–6 seconds. Put cuts on the first or last word of an SRT cue when you can, because times inside a cue drift.

**Choosing the shot.** Be literal and specific: "close-up of hands tying peonies with twine" beats "flowers", and both beat a metaphor. Avoid stock clichés (handshake for partnership, lightbulb for idea, people laughing in an office). Keep one look across the video (light, colour temperature, lens feel) and write it as a "look line" in the plan. Match the video's orientation; a landscape clip cropped to 9:16 loses two-thirds of its frame. Avoid on-screen text, watermarks, other brands' logos, a stranger looking into the lens (it reads as someone else talking), and the wrong country, season or product.

**Honesty.** When the line says "we", "our" or "my", the viewer assumes the picture is the creator's own shop, product, team or customers. Use their footage or a shot-list row there. If you use stock or AI anyway, keep it generic (hands, materials, no identifiable shop or person) and say so in the "Why" column so the user decides. Never make stock or AI footage stand in for a specific real person, event or result.

Wait for the user to approve or edit the plan. Then write `broll/plan.json` (schema below) with the approved rows.

## 5. Source each clip

Read `reference/sourcing.md` before the first search or prompt: it covers search terms that work, how to pick a candidate, prompt structure for AI video, and licence details.

**Stock:**

```bash
python3 $SKILL/scripts/stock.py search "florist tying bouquet" --out broll/work/stock/02 --size 1920x1080 --min-dur 4
python3 $SKILL/scripts/stock.py get pexels:1234567 --out broll/raw/02-tying.mp4 --size 1920x1080
```

`--min-dur` should be the slot length plus about a second of spare. Look at `sheet.jpg` (cells are numbered) and the table: relevance first, then look, then quality (avoid anything marked `soft`). If nothing fits, try two different searches before falling back to AI or a shot-list row. `get` downloads the smallest file that covers the frame and writes the credit next to it (`raw/02-tying.json`), which `deliver.py` picks up.

**AI:** use whichever video generator is available: a connected tool that generates video (for example Viewmax, ElevenLabs, Higgsfield or Runway connectors), or the `video` skill and its provider APIs. Generate at the video's aspect ratio, a little longer than the slot. Each generation is billed, so get the user's OK on the cost first, and don't re-run a generation as a retry without asking. Save the result to `broll/raw/NN-name.mp4` and put `"tool"` and `"prompt"` in that plan row for the credits.

**Own:** set `"raw"` to the file in `inputs/own/` and `"ss"` to the best moment you noted. Photos get a slow push-in automatically.

**Shoot:** leave `"raw"` out. `deliver.py` turns these rows into `SHOTLIST.md`.

## 6. Conform and check

```bash
python3 $SKILL/scripts/conform.py broll/plan.json          # or: conform.py broll/plan.json 02 05
```

Every clip is trimmed to its slot, cover-cropped to the video's size, converted to its frame rate, stripped of audio and named `NN-name_0m12s40.mp4` (in-point 0:12.40). A raw clip that is too short is slowed down (to 0.5x at most) and then holds its last frame. Phone rotation and HDR are handled.

Act on every `note:` it prints: a soft upscale means a better file or another clip; a heavy crop means setting `"focus"` or picking a clip in the right orientation; a held frame means a shorter slot or a longer clip. Then look at each check sheet in `broll/work/check/` (four frames across the clip): is the subject in frame, is anything cut off, is there text, a watermark or a logo, and does it match the look? For AI clips, look for warped hands and faces, melting objects, garbled text and broken physics. Fix and re-run those ids.

## 7. Deliver

```bash
python3 $SKILL/scripts/deliver.py broll/plan.json
```

It writes to `broll/out/`: the clips, `preview.mp4` (their video with the clips cut in, original audio), `TIMING.md`, `CREDITS.md` and `SHOTLIST.md` if there are shoot rows. Tell the user plainly that the preview is for review: for the final cut they place the clips on a track above their video in their own editor, where they can nudge timing and add transitions. Point out the shot list if there is one, and that realistic AI footage may need a label on YouTube, TikTok and Meta.

## plan.json

Paths are relative to the plan's folder (`broll/`). Copy `size` and `fps` from `work/base.json`.

```json
{
  "title": "Spring bouquets",
  "base": "inputs/source.mp4",
  "size": [1920, 1080],
  "fps": "30000/1001",
  "look": "soft morning daylight, warm whites, handheld, shallow depth of field",
  "clips": [
    {"id": "01", "name": "market", "in": 4.87, "out": 7.40, "line": "fresh peonies from the flower market",
     "shot": "Wide: buckets of peonies at a market stall", "source": "stock", "query": "flower market peonies",
     "raw": "raw/01-market.mp4", "focus": [0.5, 0.4]},
    {"id": "02", "name": "tying", "in": 7.95, "out": 9.93, "line": "we tie each bouquet by hand",
     "shot": "Close-up: hands tying peonies with twine", "source": "ai", "tool": "Veo 3 via Viewmax",
     "prompt": "Close-up of hands tying pink peonies with twine on a wooden table, soft morning light, shallow depth of field, no text",
     "raw": "raw/02-tying.mp4"},
    {"id": "03", "name": "shopfront", "in": 12.27, "out": 14.81, "line": "our shop on Dizengoff",
     "shot": "Their shop-front photo, slow push in", "source": "own", "raw": "inputs/own/shop.jpg"},
    {"id": "04", "name": "courier", "in": 15.2, "out": 17.6, "line": "our couriers deliver the same day",
     "shot": "Their courier handing a bouquet over at a door", "source": "shoot"}
  ]
}
```

- `source`: `own`, `stock`, `ai`, `shoot`, or `motion` (a finished render from motion-broll, given as `"file"` with no `"raw"`, so both kinds of B-roll share one timeline and one preview).
- Optional per clip: `ss` (start offset into the raw file, default centred), `speed` (below 1 is slow motion), `focus` ([x, y] from 0 to 1, what to keep when cropping), `move` (`in`, `out`, `left`, `right`, `up`, `down`, `none`; photos default to `in`), `zoom` (how far the move goes, default 0.08), `keep_audio` (default off), `credit` (overrides the sidecar).
- For a voiceover with no picture, set `"base"` to the audio file, choose `"size"` and `"fps"` with the user, and cover the whole timeline; gaps render black.

## Gotchas

- Pexels allows 200 requests an hour and Pixabay 100 a minute. One search per row plus a couple of retries is plenty.
- Stock licences don't clear logos, trademarks or people's endorsement. Skip shots where a brand or a recognisable face is the subject.
- 4K stock is downloaded only when the video needs it; the smallest file that covers the frame is faster and looks the same.
- Variable-frame-rate phone footage is converted to a constant rate; slow motion from 60fps footage looks smooth, while slowing 24 or 30fps footage below ~0.7x starts to stutter.
- If the base video is HDR, the preview is SDR, and the delivered clips are SDR Rec.709. Tell the user if their timeline is HDR.
