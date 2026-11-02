"""Deliver: a preview of the video with the B-roll cut in, plus TIMING.md, CREDITS.md and, when the plan has
"shoot" rows, SHOTLIST.md (footage for the creator to film themselves). Everything lands in broll/out/.

usage: python3 deliver.py broll/plan.json [--no-preview]
"""
import json, os, pathlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_plan, rel, clip_file, size_fps, check_plan, report, probe, has_filter, tonemap, run, die, fmt,
                    fps_label, LICENCES, is_voiceover)

SOURCE_NAMES = {'stock': 'Stock', 'ai': 'AI-generated', 'own': 'Your footage', 'motion': 'Motion graphic', 'shoot': 'To film'}


def credit_of(plan, c):
    if c.get('credit'):
        return c['credit']
    if c.get('raw'):
        side = rel(plan, c['raw']).with_suffix('.json')
        if side.exists():
            return json.load(open(side))
    return {}


def credit_text(plan, c):
    src, cr = c.get('source', ''), credit_of(plan, c)
    if src == 'stock' and not cr.get('provider'):
        return '**Credit missing**: add a "credit" to this clip in plan.json, or download it with stock.py get'
    if cr.get('provider'):
        prov = cr['provider']
        lic, lic_url = LICENCES.get(prov, (cr.get('licence', 'see source'), cr.get('licence_url', '')))
        who = f"[{cr['author']}]({cr['author_url']})" if cr.get('author_url') else cr.get('author', 'unknown')
        page = f"[{prov}]({cr['page']})" if cr.get('page') else prov
        return f'Video by {who} on {page} · [{lic}]({lic_url})'
    if src == 'ai':
        tool = c.get('tool') or cr.get('tool') or 'an AI video model'
        prompt = (c.get('prompt') or cr.get('prompt') or '').replace('|', '/').replace('\n', ' ')
        return f'AI-generated with {tool}' + (f'. Prompt: “{prompt}”' if prompt else '')
    if src == 'own':
        return f"Your footage ({pathlib.Path(c.get('raw', '')).name})"
    if src == 'motion':
        return 'Motion graphic'
    return cr.get('text', '')


def composite(plan, clips, W, H, fps, base, bi, dest):
    if bi.get('has_video') and not bi.get('image'):
        inputs, audio, k = ['-i', str(base)], ('0:a' if bi['has_audio'] else None), 1
        pre = (tonemap(bi) + ',') if bi.get('hdr') and has_filter('zscale') else ''
    else:  # voiceover: B-roll on black, gaps stay black
        inputs = ['-f', 'lavfi', '-i', f"color=c=black:s={W}x{H}:r={fps}:d={bi['duration']:.3f}", '-i', str(base)]
        audio, k, pre = '1:a', 2, ''
    fc = [f'[0:v]{pre}scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[b]']
    last = 'b'
    for j, c in enumerate(clips):
        inputs += ['-i', str(clip_file(plan, c))]
        a, b = c['in'], c['out']
        fc.append(f'[{k + j}:v]format=yuva420p,scale={W}:{H}:force_original_aspect_ratio=decrease,'
                  f'pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black@0,setsar=1,'
                  f'tpad=stop_mode=clone:stop_duration=1,setpts=PTS-STARTPTS+{a}/TB[c{j}]')
        fc.append(f"[{last}][c{j}]overlay=enable='gte(t,{a})*lt(t,{b})':eof_action=pass[v{j}]")
        last = f'v{j}'
    cmd = ['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(fc), '-map', f'[{last}]']
    if audio:
        cmd += ['-map', audio + '?', '-c:a', 'aac', '-b:a', '192k']
    cmd += ['-c:v', 'libx264', '-crf', '20', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-r', fps, '-t', f"{bi['duration']:.3f}",
            '-movflags', '+faststart', str(dest)]
    run(cmd)


def main():
    args = sys.argv[1:]
    if not args:
        die(__doc__)
    plan = load_plan(args[0])
    W, H, fps = size_fps(plan)
    if not plan.get('base'):
        die('plan.json needs "base": the video (or voiceover) the B-roll goes over')
    base = rel(plan, plan['base'])
    bi = probe(base)
    report(*check_plan(plan, bi['duration']))
    out = plan['_dir'] / 'out'
    out.mkdir(exist_ok=True)
    title = plan.get('title', base.stem)
    shoot = [c for c in plan['clips'] if c.get('source') == 'shoot']
    clips = sorted((c for c in plan['clips'] if c.get('source') != 'shoot'), key=lambda c: c['in'])
    missing = [c for c in clips if not clip_file(plan, c).exists()]
    if missing:
        die('these clips are not conformed yet (run conform.py, or mark them "source": "shoot"): ' +
            ', '.join(f"{c['id']} ({clip_file(plan, c).name})" for c in missing))

    if '--no-preview' not in args and clips:
        dest = out / 'preview.mp4'
        composite(plan, clips, W, H, fps, base, bi, dest)
        print('wrote', dest)

    covered = sum(c['out'] - c['in'] for c in clips)
    rows = ['| # | File | In | Out | Length | Source | Shot | Covers the line |', '|---|---|---|---|---|---|---|---|']
    for c in clips:
        rows.append(f"| {c['id']} | {clip_file(plan, c).name} | {fmt(c['in'])} | {fmt(c['out'])} | {c['out'] - c['in']:.2f}s | "
                    f"{SOURCE_NAMES.get(c.get('source'), c.get('source', ''))} | {c.get('shot', '')} | {c.get('line', '')} |")
    notes = plan.get('notes', [])
    (out / 'TIMING.md').write_text(
        f'# B-roll timing: {title}\n\n'
        f"{len(clips)} clips covering {covered:.1f}s of {bi['duration']:.1f}s ({covered / max(bi['duration'], 0.01):.0%}). "
        f'Each file name ends with its timeline in-point (`0m12s40` = 0:12.40). The clips are already cut to length, '
        f"at {W}x{H} and {fps_label(fps)} fps, with no sound: put them on a track above {'the voiceover' if is_voiceover(plan) else 'your video'} "
        f'at that time. `preview.mp4` is for review only; do the final cut in your editor.\n\n' + '\n'.join(rows) +
        ('\n\n## Notes\n' + '\n'.join('- ' + n for n in notes) if notes else '') + '\n', encoding='utf-8')
    print('wrote', out / 'TIMING.md')

    crows = ['| # | File | Credit |', '|---|---|---|']
    for c in clips:
        crows.append(f"| {c['id']} | {clip_file(plan, c).name} | {credit_text(plan, c)} |")
    used = {credit_of(plan, c).get('provider') for c in clips} - {None}
    ai = [c['id'] for c in clips if c.get('source') == 'ai']
    extra = []
    if used:
        links = ', '.join(f'[{LICENCES[p][0]}]({LICENCES[p][1]})' for p in sorted(used) if p in LICENCES)
        extra.append('## Stock licences\n\nIn short (read the licence itself before paid ads or anything high-stakes): free to use, '
                     'including commercially, and credit is not required, though it is listed above as good practice. You may not '
                     'sell the clips unaltered or as stock, imply that a person or brand shown endorses you, or use people shown in '
                     'a way that is offensive or misleading. Logos and trademarks that appear in a shot are not cleared. ' + links)
    if ai:
        extra.append('## AI-generated footage\n\n' + ('Clip ' if len(ai) == 1 else 'Clips ') + ', '.join(ai) +
                     (' is' if len(ai) == 1 else ' are') + ' AI-generated. YouTube, TikTok and Meta ask creators '
                     'to label realistic AI-generated video when it could be mistaken for real footage; check the platform\'s '
                     'current rule when you upload. Check the generator\'s terms for commercial use on your plan.')
    (out / 'CREDITS.md').write_text(f'# Credits: {title}\n\n' + '\n'.join(crows) + '\n\n' + '\n\n'.join(extra) + '\n', encoding='utf-8')
    print('wrote', out / 'CREDITS.md')

    if shoot:
        o = 'vertical (9:16)' if H > W else 'horizontal (16:9)' if W > H else 'square'
        srows = ['| # | Plays at | Film at least | Shot | Over the line |', '|---|---|---|---|---|']
        for c in shoot:
            srows.append(f"| {c['id']} | {fmt(c['in'])} | {max(5, c['out'] - c['in'] + 3):.0f}s | {c.get('shot', '')} | {c.get('line', '')} |")
        look = plan.get('look')
        (out / 'SHOTLIST.md').write_text(
            f'# Shot list: {title}\n\nThese moments are best shown with your own footage. Film each shot {o}, at {fps_label(fps)} fps or higher, '
            'holding steady for a few seconds longer than listed so there is room to trim. '
            + (f'Aim for this look so it matches the rest: {look}. ' if look else '') +
            'Put the files in `broll/inputs/own/` and they can be cut in the same way as the rest.\n\n' + '\n'.join(srows) + '\n',
            encoding='utf-8')
        print('wrote', out / 'SHOTLIST.md')


if __name__ == '__main__':
    main()
