---
name: video-ears
description: Gives Claude ears for video and audio, turning what people say into a timestamped transcript so Claude can answer what they're talking about, summarize it, quote it, translate it or make subtitles. Runs locally with ffmpeg and Whisper (faster-whisper) in 99 languages, with no API key. It can also save stills so Claude sees what's on screen while they talk. Use when the user shares or links a video, recording, podcast, voice note, interview, meeting, lecture, reel or call and asks what's said, "listen to this", "what are they talking about", "summarize this video", "transcribe", "subtitles", "captions", "SRT", "translate what they say", "find the part where...", or when a video's meaning depends on its dialogue.
---

# Video Ears

Claude can't hear audio directly. This skill turns the speech in a video into text with
timestamps. Claude reads that text and answers the user's question.

## Setup (once per machine)

```bash
pip install faster-whisper yt-dlp
```

`ffmpeg` and `ffprobe` must be on PATH. The first run downloads the Whisper model from
Hugging Face, about 500 MB for `small`, and caches it. `yt-dlp` is only needed for URLs.

## Steps

1. **Find the file.** Use the path the user gave, an attachment, or a URL. With a URL, the
   script downloads the audio only.

2. **Listen.** Run this from a working or scratch folder, not inside the user's media folder:

   ```bash
   python3 <skill-dir>/scripts/listen.py "<video, audio file or URL>"
   ```

   It prints a timestamped transcript and saves `<name>_transcript/` containing:
   - `transcript.md`: what Claude reads
   - `transcript.srt`: subtitles the user can load into a video editor
   - `transcript.json`: segments with start and end times and confidence

   Useful flags:
   | Flag | When |
   |---|---|
   | `--frames-every 10` | The question involves what's on screen too ("what are they pointing at", "what product is this"). This saves a still every N seconds into `frames/`. **Read** the stills that matter. For a long video, use a bigger N, then re-run on the part you need. |
   | `--language he` | You know the language and auto-detect got it wrong, or the clip is short or noisy. |
   | `--translate` | The user wants the speech in English. Without this flag, the transcript stays in the language spoken. |
   | `--model medium` / `large-v3` | Accents, crosstalk, poor audio, non-English, or names and jargon that `small` gets wrong. These are slower but more accurate. |
   | `--model base` / `tiny` | Very long recordings when a rough pass is enough. |
   | `--no-vad` | Quiet speech is being dropped. By default, a silence and music filter skips non-speech. |
   | `--out DIR` | Save the outputs somewhere specific. |

3. **Answer from the transcript.** Answer what the user actually asked. That may be a
   summary, key points, a specific quote, or "when do they mention X". Cite timestamps like
   `[02:14]` so the user can jump to that moment. Keep a long transcript in the file and
   don't paste it into chat unless the user asks for it.

## Reading the output honestly

- **Lines marked `(?)` are low-confidence.** Say so, or check them before quoting them as fact.
- **There are no speaker labels.** Whisper doesn't tell voices apart. You may infer speaker
  changes from context (a question followed by an answer, or names used). Present that as
  inference, not as fact.
- **"No speech detected"** means the audio is music, noise or silence. Tell the user that
  rather than inventing dialogue. Then describe the music, or use `--frames-every` to describe
  the visuals.
- **Names, brands and jargon** are the most common mistakes. If one matters, flag it or
  re-run with a larger model.
- **Language** shows the detected language and its confidence. A confidence below about 50%
  on a speech clip means you should re-run with `--language`.

## When it fails

- `has no audio track`: the video is silent. Use `--frames-every` and describe what you see.
- A URL won't download (login wall, region lock, or a blocked site): ask the user to upload
  the file instead.
- Model download blocked: the machine needs access to `huggingface.co`, or a model folder
  copied in and passed as `--model /path/to/model`.

## Optional upgrade: who said what

If the user needs speaker labels (interviews, panels, meetings) and an ElevenLabs connector
is attached, its `creative_transcribe_audio` (Scribe) can label speakers. Mention this to the
user before using it, because it spends their ElevenLabs credits.
