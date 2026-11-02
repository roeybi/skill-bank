# Sourcing B-roll: search, pick, prompt, licences

## Stock search terms

Stock libraries are tagged by what is literally in the frame, so search for that, not for the idea.

- **Concrete noun + action (+ setting), 2–4 words:** `florist tying bouquet`, `courier scooter city`, `coffee pour slow motion`, `hands typing laptop`. Not `freshness`, `fast delivery`, `productivity`.
- **Translate abstract lines into a visible moment.** "We care about quality" → `hands inspecting flower petals`. "Business is growing" → `busy shop counter customers`. If no visible moment exists, the line probably belongs on the face.
- **Try three angles before giving up:** the object (`peonies bucket`), the action (`arranging flowers`), the place (`flower market stall`). Then a synonym (`florist` / `flower shop`).
- **Shot words help:** `close up`, `top view` / `overhead`, `aerial`, `slow motion`, `timelapse`, `handheld`.
- **Search in English.** Both libraries index English tags best, even for local scenes; add the city or country only when the location matters and is likely to be tagged (`tel aviv street`, `paris cafe`).
- **Orientation follows the video.** `stock.py` filters by it; for 9:16, portrait results are fewer, so expect to try more searches.

## Picking a candidate

From `sheet.jpg` and the table, in this order:

1. **It shows the line.** Would a viewer connect the picture to the words without thinking?
2. **It matches the look line:** light, colour temperature, indoor/outdoor, camera feel. One cold blue office shot among warm daylight shots jars.
3. **It is long enough** (slot + 1s; `--min-dur` already filters) and **sharp enough** (no `soft` flag, meaning it would be upscaled more than 1.25x).
4. **Nothing that causes trouble:** watermarks, burned-in text, other brands' logos, a recognisable face as the subject, a person looking into the lens, the wrong country, season or climate.
5. **Motion fits the moment:** calm for calm lines, energetic for energetic ones. A static tripod shot can get `"move": "in"` for life.

A thumbnail is one frame. After `get` and `conform`, the check sheet shows four frames from the part actually used; judge again there and move `ss` if a better moment is elsewhere in the clip.

## AI video prompts

Structure one prompt per shot, one action per prompt:

`[shot size and angle] of [subject] [doing one action], [setting], [light and time of day], [camera movement], [look line]. No text, no logos.`

Example: `Close-up, slightly overhead, of a florist's hands tying a bouquet of pink peonies with brown twine on a scrubbed wooden table, morning window light from the left, slow push in, warm natural tones, shallow depth of field. No text, no logos.`

- **Generate at the video's aspect ratio** (16:9, 9:16, 1:1) and slightly longer than the slot; most models make 4–10 second clips.
- **What AI does badly:** readable text and signs, specific real products, logos and places, fingers doing precise work, close-ups of faces talking, crowds, fast complex physics. Frame around these (hands from further back, products out of focus, no signage).
- **What AI does well:** textures, light, food and drink, nature, materials, slow camera moves, atmospheric wides, stylised looks that stock can't match.
- **Image-to-video is the strongest option for a business:** animate the creator's own product or shop photo (gentle camera move, petals stirring, steam rising) so the real product stays real. Prompt only the motion.
- **Consistency across several AI shots:** reuse the same look line and light description word for word; if the tool supports a style or reference image, use the first good result as the reference.
- **Never** generate a real, identifiable person, a real event presented as having happened, or a "result" (a crowd at their launch, a full shop) that didn't happen.
- **Cost:** say what each generation costs before running it (use the tool's estimate if it has one); generate one shot, check it, then do the rest; don't re-run a generation without the user's OK, because each run is billed.

After generating, conform it and look at the check sheet with AI faults in mind: extra or fused fingers, faces that drift, objects that melt or pop in, text that looks like text but isn't, wrong physics (liquid, fabric, flames).

## Own footage

- Their footage of their own product, place and people beats any stock shot, even if it is less polished. Look through every strip in `work/library/` before planning.
- Set `"ss"` to the best moment (strips show six evenly spaced frames; the file's duration is in `library.json`).
- Phone video: rotation, variable frame rate and HDR (HLG) are handled by `conform.py`. A portrait phone clip in a landscape video is heavily cropped; use `"focus"` or a different clip.
- Photos become moving shots with `"move"` (`in` by default). Use `left` or `right` on wide photos, `up` or `down` on tall ones, and `"focus"` to push in toward the subject.

## Licences in short

Not legal advice. Link the user to the licence for anything high-stakes, such as a paid ad campaign or TV.

- **Pexels License** (https://www.pexels.com/license/) and **Pixabay Content License** (https://pixabay.com/service/license-summary/): free to use, including commercially, modified or not, with no attribution required. Not allowed: selling or redistributing the clips unaltered (as stock or wallpapers, for example), implying that people or brands shown endorse the creator, or using identifiable people in a way that is offensive, misleading or defamatory. Trademarks, logos and artwork that appear in a clip are not licensed.
- Credit is listed in `CREDITS.md` anyway. It is good practice, and the Pexels API guidelines ask for it where possible.
- **AI footage:** check the generator's terms for commercial use on the user's plan. YouTube, TikTok and Meta ask creators to disclose realistic AI-generated or altered video; the rules change, so tell the user to check when uploading.
- **API terms:** both APIs are meant for finding and downloading individual clips, not bulk scraping. Pixabay asks that results be cached rather than re-requested and that clips be downloaded rather than hotlinked; `stock.py` downloads.
