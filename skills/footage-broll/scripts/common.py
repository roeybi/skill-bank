"""Shared helpers for the footage-broll scripts (standard library only, plus ffmpeg/ffprobe on PATH)."""
import functools, json, math, os, pathlib, subprocess, sys

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.tif', '.tiff', '.bmp'}
VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.mkv', '.webm', '.avi', '.mts', '.mxf'}
AUDIO_EXT = {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus', '.aif', '.aiff'}
STANDARD_FPS = ['24000/1001', '24', '25', '30000/1001', '30', '48', '50', '60000/1001', '60']
LICENCES = {
    'Pexels': ('Pexels License', 'https://www.pexels.com/license/'),
    'Pixabay': ('Pixabay Content License', 'https://pixabay.com/service/license-summary/'),
}


def die(msg):
    sys.exit(f'error: {msg}')


def fps_value(s):
    s = str(s or '0')
    if '/' in s:
        a, b = s.split('/')
        return float(a) / float(b) if float(b) else 0.0
    return float(s)


def clean_fps(s):
    """Snap a measured rate (e.g. iPhone '18000/601') to the nearest standard rate when it is within 0.5%."""
    v = fps_value(s)
    if v <= 0:
        return '30'
    best = min(STANDARD_FPS, key=lambda f: abs(fps_value(f) - v))
    return best if abs(fps_value(best) - v) / v < 0.005 else (str(round(v, 3)).rstrip('0').rstrip('.'))


def fps_label(s):
    """'30000/1001' -> '29.97' for people; keep the exact string for ffmpeg."""
    v = fps_value(s)
    return f'{v:.3f}'.rstrip('0').rstrip('.') if '/' in str(s) else str(s)


def probe(path):
    """Size after rotation, fps, duration, audio, HDR and whether it is a still image."""
    path = pathlib.Path(path)
    if not path.exists():
        die(f'{path} does not exist')
    r = subprocess.run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', str(path)],
                       capture_output=True, text=True)
    if r.returncode:
        die(f'ffprobe could not read {path}: {r.stderr.strip()}')
    p = json.loads(r.stdout)
    v = next((s for s in p['streams'] if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic')), None)
    a = next((s for s in p['streams'] if s['codec_type'] == 'audio'), None)
    dur = float(p['format'].get('duration') or 0) or float((v or a or {}).get('duration') or 0)
    info = {'path': str(path), 'duration': round(dur, 3), 'has_audio': a is not None, 'has_video': v is not None}
    if not v:
        return info
    w, h = int(v['width']), int(v['height'])
    rot = 0
    for sd in v.get('side_data_list') or []:
        if 'rotation' in sd:
            rot = int(float(sd['rotation']))
    rot = int((v.get('tags') or {}).get('rotate', rot))
    if abs(rot) % 180 == 90:  # phones store portrait video as landscape + a rotation flag; ffmpeg applies it on decode
        w, h = h, w
    rate = v.get('r_frame_rate') if fps_value(v.get('r_frame_rate')) <= 120 else v.get('avg_frame_rate')
    image = path.suffix.lower() in IMAGE_EXT or (v.get('codec_name') in ('mjpeg', 'png', 'webp', 'bmp', 'tiff') and dur < 0.1)
    trc = v.get('color_transfer', '')
    info.update({'width': w, 'height': h, 'fps': None if image else clean_fps(rate), 'image': image,
                 'rotation': rot, 'pix_fmt': v.get('pix_fmt'), 'hdr': trc in ('smpte2084', 'arib-std-b67'),
                 'color': {k: v.get(k) for k in ('color_transfer', 'color_primaries', 'color_space') if v.get(k)}})
    return info


@functools.lru_cache(None)
def has_filter(name):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True).stdout
    return any(line.split()[1:2] == [name] for line in out.splitlines() if len(line.split()) > 2)


@functools.lru_cache(None)
def can_drawtext():
    """drawtext needs libfreetype + fontconfig; some ffmpeg builds have neither, so labels are optional."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=64x64:d=0.1', '-vf', 'drawtext=text=a',
                        '-f', 'null', '-'], capture_output=True)
    return r.returncode == 0


def tonemap(info):
    """HDR (PQ or HLG, e.g. iPhone) -> SDR Rec.709. Needs the zscale filter (zimg)."""
    tin = info['color'].get('color_transfer')
    return (f'zscale=tin={tin}:min=bt2020nc:pin=bt2020:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,'
            f'tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p')


def label(text, size=22):
    if not can_drawtext():
        return ''
    t = str(text).replace('\\', '\\\\').replace("'", '').replace(':', '\\:').replace('%', '\\%').replace(',', '\\,')
    return f",drawtext=text='{t}':x=8:y=8:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=6"


def tc(t):
    """Timeline in-point for file names: 12.4 -> '0m12s40'."""
    cs = round(t * 100)
    return f'{cs // 6000}m{cs % 6000 // 100:02d}s{cs % 100:02d}'


def fmt(t):
    """Human time: 72.4 -> '1:12.40'."""
    cs = round(t * 100)
    return f'{cs // 6000}:{cs % 6000 / 100:05.2f}'


def load_plan(path):
    path = pathlib.Path(path).resolve()
    try:
        plan = json.load(open(path, encoding='utf-8'))
    except json.JSONDecodeError as e:
        die(f'{path} is not valid JSON: {e}')
    plan['_dir'] = path.parent
    for c in plan.get('clips', []):
        c.setdefault('name', 'clip')
        c['id'] = str(c['id'])
    return plan


def rel(plan, p):
    """Plan paths are relative to the plan's folder."""
    p = pathlib.Path(p)
    return p if p.is_absolute() else (plan['_dir'] / p)


def clip_file(plan, c):
    """Final clip path: explicit 'file' (e.g. a motion-broll render), else out/NN-name_<in-point>.mp4."""
    if c.get('file'):
        return rel(plan, c['file'])
    return plan['_dir'] / 'out' / f"{c['id']}-{c['name']}_{tc(c['in'])}.mp4"


def size_fps(plan):
    try:
        W, H = (int(x) for x in plan['size'])
    except (KeyError, ValueError, TypeError):
        die('plan.json needs "size": [width, height] (copy it from work/base.json)')
    if W % 2 or H % 2:
        die(f'size {W}x{H} must be even for H.264')
    return W, H, str(plan.get('fps') or '30')


def is_voiceover(plan):
    """No face to protect: the base is an audio file (B-roll carries the whole picture)."""
    return bool(plan.get('voiceover')) or pathlib.Path(str(plan.get('base', ''))).suffix.lower() in AUDIO_EXT


def check_plan(plan, base_duration=None):
    """Editorial lint. Returns (errors, warnings)."""
    errs, warns = [], []
    vo = is_voiceover(plan)
    clips = [c for c in plan.get('clips', [])]
    seen = set()
    for c in clips:
        tag = f"clip {c.get('id')}"
        if c['id'] in seen:
            errs.append(f'{tag}: duplicate id')
        seen.add(c['id'])
        if not isinstance(c.get('in'), (int, float)) or not isinstance(c.get('out'), (int, float)):
            errs.append(f'{tag}: needs numeric "in" and "out" (seconds on the timeline)')
            continue
        if c['out'] <= c['in']:
            errs.append(f'{tag}: out ({c["out"]}) must be after in ({c["in"]})')
        if base_duration and c['out'] > base_duration + 0.05:
            errs.append(f'{tag}: ends at {fmt(c["out"])}, after the video ends ({fmt(base_duration)})')
        d = c['out'] - c['in']
        if 0 < d < 1.0:
            warns.append(f'{tag}: only {d:.2f}s on screen; under ~1s reads as a glitch, not a shot')
        if d > 10 and c.get('source') != 'motion':
            warns.append(f'{tag}: {d:.1f}s is long for one shot; consider two shots or giving the face back')
        if c['in'] < 1.5 and c.get('source') not in ('motion',) and not vo:
            warns.append(f'{tag}: starts in the first 1.5s and covers the hook; viewers decide on the face')
    timed = sorted((c for c in clips if isinstance(c.get('in'), (int, float)) and isinstance(c.get('out'), (int, float))
                    and c.get('source') != 'shoot'), key=lambda c: c['in'])
    for a, b in zip(timed, timed[1:]):
        gap = b['in'] - a['out']
        if gap < -0.01:
            warns.append(f"clips {a['id']} and {b['id']} overlap by {-gap:.2f}s; the later one wins in the preview")
        elif 0.01 < gap < 0.7 and not vo:
            warns.append(f"clips {a['id']} and {b['id']}: {gap:.2f}s of face between them flashes; join them or open the gap to 2s+")
    return errs, warns


def report(errs, warns):
    for w in warns:
        print('warning:', w)
    if errs:
        for e in errs:
            print('error:', e)
        sys.exit(1)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        die('ffmpeg failed:\n' + ' '.join(map(str, cmd))[:600] + '\n' + r.stderr.strip()[-1500:])
    return r


def even(x):
    return int(math.ceil(x / 2) * 2)
