"""Look at the base video (or voiceover) or a folder of the creator's own footage.

usage:
  python3 inspect_media.py broll/inputs/source.mp4 broll/work      -> work/base.json + work/contact.png
  python3 inspect_media.py broll/inputs/voiceover.wav broll/work   -> work/base.json (you choose size/fps)
  python3 inspect_media.py broll/inputs/own broll/work             -> work/library.json + work/library/<file>.jpg strips
"""
import json, os, pathlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import IMAGE_EXT, VIDEO_EXT, AUDIO_EXT, probe, run, label, die, fmt


def contact(src, dur, out, n=16, cols=4, w=480):
    step = max(dur / n, 0.04)
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', f'fps=1/{step:.3f},scale={w}:-2,tile={cols}x{-(-n // cols)}:padding=4',
         '-frames:v', '1', str(out)])


def strip(src, info, out, n=6):
    """One row of frames across a clip (or the photo itself), labelled with the file name."""
    name = pathlib.Path(src).name
    if info.get('image'):
        run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', f'scale=-2:240{label(name, 18)}', '-frames:v', '1', str(out)])
        return
    step = max(info['duration'] / n, 0.04)
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', f'fps=1/{step:.3f},scale=-2:180,tile={n}x1:padding=3{label(name, 18)}',
         '-frames:v', '1', str(out)])


def main():
    if len(sys.argv) != 3:
        die(__doc__)
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    if src.is_dir():  # the creator's own footage library
        files = sorted(p for p in src.rglob('*') if p.suffix.lower() in VIDEO_EXT | IMAGE_EXT and not p.name.startswith('.'))
        if not files:
            die(f'no video or image files in {src}')
        (out / 'library').mkdir(exist_ok=True)
        lib = []
        for f in files:
            i = probe(f)
            if not i.get('has_video'):
                continue
            sheet = out / 'library' / (f.stem + '.jpg')
            strip(f, i, sheet)
            o = 'portrait' if i['height'] > i['width'] else 'square' if i['height'] == i['width'] else 'landscape'
            lib.append({'file': str(f), 'kind': 'photo' if i['image'] else 'video', 'size': [i['width'], i['height']], 'orientation': o,
                        'fps': i['fps'], 'duration': i['duration'], 'hdr': i['hdr'], 'sheet': str(sheet)})
            print(f"{f.name:40.40}  {'photo' if i['image'] else fmt(i['duration']):>8}  {i['width']}x{i['height']} {o:9} "
                  f"{i['fps'] or '':>10}{'  HDR' if i['hdr'] else ''}")
        json.dump(lib, open(out / 'library.json', 'w'), indent=1)
        print(f'\n{len(lib)} files -> {out / "library.json"}; one frame strip per file in {out / "library"}/ (look at them)')
        return

    i = probe(src)
    base = {'base': str(src), 'duration': i['duration'], 'has_audio': i['has_audio']}
    if i.get('has_video') and not i.get('image'):
        base.update({'size': [i['width'], i['height']], 'fps': i['fps'], 'hdr': i['hdr'], 'rotation': i['rotation']})
        contact(src, i['duration'], out / 'contact.png')
        base['contact'] = str(out / 'contact.png')
        if i['hdr']:
            print('note: the base video is HDR. Stock B-roll is SDR, so the two will not match exactly in an HDR timeline; '
                  'the preview is SDR.')
    elif src.suffix.lower() in AUDIO_EXT or (i['has_audio'] and not i.get('has_video')):
        base['voiceover'] = True
        print('Voiceover only: there is no picture, so B-roll carries the whole video. Ask the user for the format '
              '(16:9 1920x1080, 9:16 1080x1920 or 1:1 1080x1080) and fps (30 is a safe default), and set "size", "fps" '
              'and "voiceover": true in plan.json.')
    else:
        die(f'{src} has no video or audio stream')
    if not i['has_audio']:
        print('note: no audio track. Word timings must come from a transcript.')
    json.dump(base, open(out / 'base.json', 'w'), indent=1)
    print(json.dumps(base, indent=1))


if __name__ == '__main__':
    main()
