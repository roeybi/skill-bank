"""Word timings for planning, one line per cue: [12.40-16.10] 12.40:So 12.61:the 12.80:first ...

usage:
  python3 words.py transcript.srt|transcript.vtt > broll/work/words.txt
      Estimates each word's time by spreading the cue across its characters (about +-0.2s).
  python3 words.py broll/inputs/source.mp4 [--model small] [--srt broll/work/transcript.srt] > broll/work/words.txt
      Real word timestamps from the audio with faster-whisper (pip install faster-whisper). First run downloads the model.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import die


def ts(x):  # SRT hh:mm:ss,mmm or VTT [hh:]mm:ss.mmm
    return sum(float(v) * 60 ** i for i, v in enumerate(reversed(x.strip().replace(',', '.').split(':'))))


def from_subtitles(path):
    cues = []
    for blk in re.split(r'\n\s*\n', open(path, encoding='utf-8-sig').read().replace('\r\n', '\n').strip()):
        lines = blk.strip().split('\n')
        i = next((i for i, l in enumerate(lines[:3]) if '-->' in l), None)
        if i is None:
            continue  # WEBVTT header, NOTE / STYLE blocks
        a, b = [ts(x.split()[0]) for x in lines[i].split('-->')]
        words = re.sub(r'<[^>]*>|\{[^}]*\}', '', ' '.join(lines[i + 1:])).split()
        if not words:
            continue
        n = sum(len(w) + 1 for w in words)
        c, out = 0, []
        for w in words:
            out.append((a + (b - a) * c / n, w))
            c += len(w) + 1
        cues.append((a, b, out))
    if not cues:
        die(f'no cues found in {path} (expected SRT or VTT)')
    return cues


def from_audio(path, model_name, srt_out):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die('faster-whisper is not installed. Run: python3 -m pip install faster-whisper   (or give an SRT/VTT transcript)')
    import subprocess, numpy as np
    # decode with ffmpeg (any audio or video file) instead of PyAV, whose versions often clash with faster-whisper
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True)
    if pcm.returncode or not pcm.stdout:
        die(f'ffmpeg could not read audio from {path}: {pcm.stderr.decode(errors="ignore").strip()[-300:]}')
    audio = np.frombuffer(pcm.stdout, np.int16).astype(np.float32) / 32768.0
    model = WhisperModel(model_name, compute_type='int8')
    segments, info = model.transcribe(audio, word_timestamps=True, vad_filter=True)
    print(f'# language: {info.language} ({info.language_probability:.0%}), model {model_name}', file=sys.stderr)
    cues = []
    for s in segments:
        ws = [(w.start, w.word.strip()) for w in (s.words or []) if w.word.strip()]
        if ws:
            cues.append((s.start, s.end, ws))
    if srt_out:
        def srt_ts(t):
            ms = round(t * 1000)
            return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
        with open(srt_out, 'w', encoding='utf-8') as f:
            for k, (a, b, ws) in enumerate(cues, 1):
                f.write(f"{k}\n{srt_ts(a)} --> {srt_ts(b)}\n{' '.join(w for _, w in ws)}\n\n")
        print(f'# wrote {srt_out}', file=sys.stderr)
    return cues


def main():
    args = sys.argv[1:]
    if not args:
        die(__doc__)
    src = args[0]
    opt = lambda k, d=None: args[args.index(k) + 1] if k in args else d
    if src.lower().endswith(('.srt', '.vtt')):
        cues = from_subtitles(src)
    else:
        cues = from_audio(src, opt('--model', 'small'), opt('--srt'))
    for a, b, ws in cues:
        print(f'[{a:.2f}-{b:.2f}] ' + ' '.join(f'{t:.2f}:{w}' for t, w in ws))


if __name__ == '__main__':
    main()
