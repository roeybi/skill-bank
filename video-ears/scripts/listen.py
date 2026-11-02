#!/usr/bin/env python3
"""listen.py - give Claude ears: turn the speech in a video (or audio file) into text.

Usage:
    python3 listen.py VIDEO_OR_AUDIO_OR_URL [options]

Writes, into the output folder:
    transcript.md    timestamped transcript, easy for Claude to read
    transcript.srt   subtitles, ready to load into a video editor
    transcript.json  segments with timing and confidence, plus language info
    frames/          (only with --frames-every) stills named by timestamp

The markdown transcript is also printed to stdout.

Audio is decoded with ffmpeg rather than faster-whisper's built-in PyAV decoder,
so it works with any file ffmpeg can read and avoids PyAV version clashes.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SAMPLE_RATE = 16000

# Whisper segment-level confidence thresholds. Segments past either are marked
# "(?)" so Claude knows to treat them with care rather than quote them as fact.
LOW_LOGPROB = -1.0
HIGH_NO_SPEECH = 0.6


def fail(msg):
    print(f"listen.py: {msg}", file=sys.stderr)
    sys.exit(1)


def require(tool):
    if shutil.which(tool) is None:
        fail(f"'{tool}' is not installed or not on PATH.")


def is_url(s):
    return s.startswith(("http://", "https://"))


def download(url, workdir):
    """Fetch the media behind a URL with yt-dlp (audio only when possible)."""
    require("yt-dlp")
    template = str(Path(workdir) / "download.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "-f", "bestaudio/best", "-o", template, url]
    print(f"Downloading {url} ...", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        fail("yt-dlp could not download that URL:\n" + result.stderr.strip()[-2000:])
    files = sorted(Path(workdir).glob("download.*"))
    if not files:
        fail("yt-dlp finished but no file was saved.")
    return files[0]


def probe(path):
    """Return (duration_seconds, has_audio, has_video) using ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration",
           "-of", "json", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"ffprobe could not read {path}:\n{result.stderr.strip()}")
    data = json.loads(result.stdout or "{}")
    kinds = {s.get("codec_type") for s in data.get("streams", [])}
    duration = float(data.get("format", {}).get("duration") or 0)
    return duration, "audio" in kinds, "video" in kinds


def decode_audio(path):
    """Decode the first audio stream to 16 kHz mono float32 with ffmpeg."""
    import numpy as np

    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0",
           "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        fail("ffmpeg could not decode the audio:\n" + result.stderr.decode(errors="replace")[-2000:])
    return np.frombuffer(result.stdout, dtype=np.float32)


def stamp(seconds, srt=False):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def extract_frames(path, out_dir, every, duration):
    """Save one still every `every` seconds, named by its timestamp."""
    out_dir.mkdir(parents=True, exist_ok=True)
    t = 0.0
    saved = []
    while t < max(duration, 0.01):
        name = out_dir / f"frame_{stamp(t).replace(':', '-')}.jpg"
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path),
               "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2", "-q:v", "3", str(name)]
        if subprocess.run(cmd, capture_output=True).returncode == 0 and name.exists():
            saved.append(name)
        t += every
    return saved


def main():
    p = argparse.ArgumentParser(description="Transcribe the speech in a video or audio file.")
    p.add_argument("source", help="Path to a video/audio file, or an http(s) URL")
    p.add_argument("--model", default="small",
                   help="Whisper model: tiny, base, small (default), medium, large-v3, turbo")
    p.add_argument("--language", default=None,
                   help="Spoken language code, e.g. en, he, es. Default: auto-detect")
    p.add_argument("--translate", action="store_true",
                   help="Translate the speech into English instead of transcribing as spoken")
    p.add_argument("--out", default=None,
                   help="Output folder. Default: ./<file name>_transcript")
    p.add_argument("--frames-every", type=float, default=0,
                   help="Also save a still every N seconds so Claude can see the video")
    p.add_argument("--no-vad", action="store_true",
                   help="Turn off silence/music filtering (keep if speech is being cut off)")
    p.add_argument("--quiet", action="store_true", help="Don't print the transcript to stdout")
    args = p.parse_args()

    require("ffmpeg")
    require("ffprobe")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        fail("faster-whisper is missing. Install it with:  pip install faster-whisper")

    with tempfile.TemporaryDirectory(prefix="listen-") as tmp:
        if is_url(args.source):
            media = download(args.source, tmp)
            stem = "download"
        else:
            media = Path(args.source).expanduser()
            if not media.is_file():
                fail(f"No such file: {media}")
            stem = media.stem

        out = Path(args.out) if args.out else Path.cwd() / f"{stem}_transcript"
        out.mkdir(parents=True, exist_ok=True)

        duration, has_audio, has_video = probe(media)
        if not has_audio:
            fail(f"{media.name} has no audio track, so there is nothing to hear.")

        print(f"Listening to {media.name} ({stamp(duration)}) with Whisper '{args.model}' ...",
              file=sys.stderr)
        audio = decode_audio(media)

        model = WhisperModel(args.model, device="auto", compute_type="int8")
        segments_iter, info = model.transcribe(
            audio,
            language=args.language,
            task="translate" if args.translate else "transcribe",
            vad_filter=not args.no_vad,
            beam_size=5,
        )

        segments = []
        for seg in segments_iter:
            text = seg.text.strip()
            if not text:
                continue
            unsure = seg.avg_logprob < LOW_LOGPROB or seg.no_speech_prob > HIGH_NO_SPEECH
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": text,
                "avg_logprob": round(seg.avg_logprob, 3),
                "no_speech_prob": round(seg.no_speech_prob, 3),
                "unsure": unsure,
            })
            print(f"  [{stamp(seg.start)}] {text}", file=sys.stderr)

        frames = []
        if args.frames_every > 0 and has_video:
            frames = extract_frames(media, out / "frames", args.frames_every, duration)

    # --- write outputs -------------------------------------------------------
    task = "translated to English" if args.translate else "as spoken"
    header = [
        f"# Transcript: {stem}",
        "",
        f"- Duration: {stamp(duration)}",
        f"- Language: {info.language} (confidence {info.language_probability:.0%}), {task}",
        f"- Model: Whisper {args.model}",
        f"- Speech found: {stamp(sum(s['end'] - s['start'] for s in segments))}",
        "- Lines marked (?) were low-confidence; check them before quoting.",
        "- No speaker labels: Whisper does not tell voices apart.",
        "",
    ]
    if not segments:
        header.append("_No speech detected. The audio may be music, noise or silence._")
    body = [f"[{stamp(s['start'])}] {s['text']}{' (?)' if s['unsure'] else ''}" for s in segments]
    if frames:
        body += ["", f"## Frames ({len(frames)}, one every {args.frames_every:g}s)", ""]
        body += [f"- frames/{f.name}" for f in frames]
    md = "\n".join(header + body) + "\n"
    (out / "transcript.md").write_text(md, encoding="utf-8")

    srt = []
    for i, s in enumerate(segments, 1):
        srt += [str(i), f"{stamp(s['start'], True)} --> {stamp(s['end'], True)}", s["text"], ""]
    (out / "transcript.srt").write_text("\n".join(srt), encoding="utf-8")

    (out / "transcript.json").write_text(json.dumps({
        "source": str(args.source),
        "duration": round(duration, 2),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "task": "translate" if args.translate else "transcribe",
        "model": args.model,
        "segments": segments,
        "frames": [f"frames/{f.name}" for f in frames],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.quiet:
        print(md)
    print(f"Saved transcript.md, transcript.srt, transcript.json to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
