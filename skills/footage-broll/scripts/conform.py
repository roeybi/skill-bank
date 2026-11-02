"""Make each raw B-roll file slot-ready: trimmed to its slot, cover-cropped to the video's size, at the video's frame
rate, no audio, named by its timeline in-point. Stills get a slow push (Ken Burns). Writes a 4-frame check sheet per clip.

usage: python3 conform.py broll/plan.json [all | 01 03 ...]

Optional per-clip fields in plan.json:
  "ss": 2.0             start this many seconds into the raw file (default: centre the part that is used)
  "speed": 0.75         below 1 = slow motion, above 1 = faster (default 1; auto-slowed down to 0.5x if the raw file is short)
  "focus": [0.5, 0.35]  what to keep when cropping or pushing in, 0..1 across and down (default centre)
  "move": "in"          in | out | left | right | up | down | none (stills default "in", video "none")
  "zoom": 0.08          how far the move travels (default 8%)
  "keep_audio": true    keep the clip's own sound (default off: B-roll plays under the speaker)
"""
import os, pathlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_plan, rel, clip_file, size_fps, check_plan, report, probe, fps_value, has_filter, run, even,
                    die, fmt, tonemap, fps_label)

MOVES = ('in', 'out', 'left', 'right', 'up', 'down', 'none')


def move_exprs(move, zoom, fx, fy, n):
    p = f'(on/{max(n - 1, 1)})'
    z = {'in': f'1+{zoom}*{p}', 'out': f'1+{zoom}*(1-{p})'}.get(move, f'{1 + zoom}')
    x, y = f'(iw-iw/zoom)*{fx}', f'(ih-ih/zoom)*{fy}'
    if move == 'left':
        x = f'(iw-iw/zoom)*(1-{p})'
    elif move == 'right':
        x = f'(iw-iw/zoom)*{p}'
    elif move == 'up':
        y = f'(ih-ih/zoom)*(1-{p})'
    elif move == 'down':
        y = f'(ih-ih/zoom)*{p}'
    return z, x, y


def conform(plan, c, W, H, fps):
    raw = rel(plan, c['raw'])
    i = probe(raw)
    if not i.get('has_video'):
        die(f"clip {c['id']}: {raw} has no picture")
    F = fps_value(fps)
    N = max(1, round((c['out'] - c['in']) * F))
    D = N / F
    out = clip_file(plan, c)
    out.parent.mkdir(parents=True, exist_ok=True)
    fx, fy = (min(1.0, max(0.0, float(v))) for v in c.get('focus', [0.5, 0.5]))
    move = c.get('move', 'in' if i['image'] else 'none')
    if move not in MOVES:
        die(f"clip {c['id']}: move must be one of {', '.join(MOVES)}")
    zoom = float(c.get('zoom', 0.08))
    notes, vf = [], []

    if i['hdr']:
        if has_filter('zscale'):
            vf.append(tonemap(i))
            notes.append('HDR source tone-mapped to SDR')
        else:
            notes.append('HDR source and this ffmpeg has no zscale: colours will look flat/washed out; '
                         're-export it as SDR (Rec.709) or pick another clip')

    if i['image']:
        src = ['-loop', '1', '-framerate', fps, '-t', f'{D + 0.5:.3f}', '-i', str(raw)]
        speed, ss, pad = 1.0, 0.0, 0.0
    else:
        speed = c.get('speed')
        avail = i['duration']
        if speed is None and avail < D:
            speed = max(0.5, round(avail / D, 3))
            notes.append(f'raw file is {avail:.1f}s for a {D:.2f}s slot: slowed to {speed:.2f}x')
        speed = float(speed or 1.0)
        need = D * speed
        ss = c.get('ss')
        if ss is None:
            ss = max(0.0, (avail - need) / 2)
        ss = float(ss)
        if not 0 <= ss < avail - 0.1:
            die(f"clip {c['id']}: ss {ss}s is outside the raw file ({avail:.2f}s long)")
        short = need - (avail - ss)
        pad = 0.0
        if short > 0.5 / F:
            pad = short / speed + 2 / F
            notes.append(f'{short / speed:.2f}s short even at {speed:.2f}x: the last frame is held (trim the slot or pick a longer clip)')
        src = ['-ss', f'{ss:.3f}', '-t', f'{need + 0.25:.3f}', '-i', str(raw)]
        vf.append(f'setpts=(PTS-STARTPTS)/{speed}')
        vf.append(f'fps={fps}')

    sw, sh = i['width'], i['height']
    up = max(W / sw, H / sh)
    if up > 1.25:
        notes.append(f'{sw}x{sh} upscaled {up:.2f}x: will look soft at {W}x{H}')
    kept = (W * H) / (sw * up * sh * up)
    if kept < 0.6:
        notes.append(f'crop keeps only {kept:.0%} of the frame ({sw}x{sh} into {W}x{H}); check that the subject survives, or set "focus"')

    k = 1 if move == 'none' else (3 if i['image'] else 2)  # supersample before zoompan so the move does not step
    Wk, Hk = W * k, H * k
    f = max(Wk / sw, Hk / sh)
    sw2, sh2 = max(Wk, even(sw * f)), max(Hk, even(sh * f))
    vf.append(f'scale={sw2}:{sh2}:flags=lanczos')
    vf.append(f'crop={Wk}:{Hk}:{(sw2 - Wk) * fx:.0f}:{(sh2 - Hk) * fy:.0f}')
    if move != 'none':
        z, x, y = move_exprs(move, zoom, fx, fy, N)
        vf.append(f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={fps}")
    vf.append('setsar=1')
    if pad:
        vf.append(f'tpad=stop_mode=clone:stop_duration={pad:.3f}')
    vf.append('format=yuv420p')

    audio = ['-an']
    if c.get('keep_audio') and i['has_audio'] and not i['image']:
        audio = ['-c:a', 'aac', '-b:a', '192k', '-af', f'atempo={min(max(speed, 0.5), 2.0)}']
    run(['ffmpeg', '-v', 'error', '-y', *src, '-vf', ','.join(vf), '-frames:v', str(N), '-r', fps,
         '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
         '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', *audio, '-movflags', '+faststart', str(out)])

    sheet = plan['_dir'] / 'work' / 'check' / (out.stem + '.jpg')
    sheet.parent.mkdir(parents=True, exist_ok=True)
    picks = sorted({min(N - 1, round(N * r)) for r in (0.0, 0.35, 0.7, 0.99)})
    sel = '+'.join(f'eq(n\\,{p})' for p in picks)
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(out), '-vf', f"select='{sel}',scale=480:-2,tile={len(picks)}x1:padding=4:color=white",
         '-frames:v', '1', str(sheet)])

    got = probe(out)
    src_desc = 'photo' if i['image'] else f"{sw}x{sh}@{i['fps']} from {ss:.2f}s at {speed:g}x"
    print(f"{c['id']} {c['name']:<18.18} {fmt(c['in'])}-{fmt(c['out'])} ({D:.2f}s)  {src_desc} -> {got['width']}x{got['height']}@{fps_label(got['fps'])}"
          f"{'  move ' + move if move != 'none' else ''}\n   {out}\n   check: {sheet}")
    for n in notes:
        print('   note:', n)
    return notes


def main():
    if len(sys.argv) < 2:
        die(__doc__)
    plan = load_plan(sys.argv[1])
    W, H, fps = size_fps(plan)
    base = plan.get('base')
    base_dur = probe(rel(plan, base))['duration'] if base and rel(plan, base).exists() else None
    report(*check_plan(plan, base_dur))
    ids = sys.argv[2:] or ['all']
    clips = plan['clips'] if ids == ['all'] else [c for c in plan['clips'] if c['id'] in ids]
    if ids != ['all'] and len(clips) != len(ids):
        die(f"no clip with id {sorted(set(ids) - {c['id'] for c in clips})} in the plan")
    done = 0
    for c in clips:
        if c.get('source') == 'shoot':
            continue
        if not c.get('raw'):
            if not c.get('file'):
                print(f"{c['id']} {c['name']}: no \"raw\" file yet, skipped")
            continue
        if not rel(plan, c['raw']).exists():
            print(f"{c['id']} {c['name']}: {c['raw']} not found, skipped")
            continue
        conform(plan, c, W, H, fps)
        done += 1
    print(f'\n{done} clip(s) conformed. Look at every check sheet before delivering.')


if __name__ == '__main__':
    main()
