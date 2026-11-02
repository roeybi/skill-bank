"""Search and download free stock video from Pexels and Pixabay.

Keys (both free): PEXELS_API_KEY from https://www.pexels.com/api/ and PIXABAY_API_KEY from https://pixabay.com/api/docs/
Set them as environment variables or as KEY=value lines in a .env file (this folder or a parent). One key is enough.

usage:
  python3 stock.py search "florist tying bouquet" --out broll/work/stock/01 [--orientation landscape|portrait|square]
                   [--size 1920x1080] [--min-dur 4] [--n 12] [--provider pexels,pixabay]
      -> candidates.json + sheet.jpg (numbered thumbnails) in --out, and a table on stdout
  python3 stock.py get pexels:1234567 --out broll/raw/01-bouquet.mp4 [--size 1920x1080]
      -> the smallest rendition that covers --size, plus broll/raw/01-bouquet.json with the credit
"""
import concurrent.futures as cf, json, os, pathlib, shutil, sys, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LICENCES, die, run, label

UA = {'User-Agent': 'footage-broll/1.0 (+https://github.com/roeybi/skill-bank)'}
PROVIDERS = {'pexels': 'PEXELS_API_KEY', 'pixabay': 'PIXABAY_API_KEY'}


def load_keys():
    keys = {p: os.environ.get(k, '').strip() for p, k in PROVIDERS.items()}
    d = pathlib.Path.cwd().resolve()
    for folder in [d, *d.parents][:5]:
        env = folder / '.env'
        if env.is_file():
            for line in env.read_text(encoding='utf-8', errors='ignore').splitlines():
                k, _, v = line.strip().partition('=')
                for p, name in PROVIDERS.items():
                    if k.strip().removeprefix('export ').strip() == name and not keys[p]:
                        keys[p] = v.strip().strip('"\'')
    return keys


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='ignore')[:200]
        hint = {401: 'the API key was rejected', 403: 'the API key was rejected or lacks access', 429: 'rate limited; wait a minute'}.get(e.code, '')
        die(f'{url.split("?")[0]} returned HTTP {e.code} {hint}: {body}')
    except urllib.error.URLError as e:
        die(f'could not reach {url.split("?")[0]}: {e.reason}')


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    tmp = pathlib.Path(str(dest) + '.part')
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.replace(dest)


# ---- normalise both APIs to one shape -------------------------------------------------------------
def from_pexels(v):
    files = [{'url': f['link'], 'w': f['width'], 'h': f['height'], 'fps': f.get('fps')}
             for f in v.get('video_files', []) if f.get('file_type') == 'video/mp4' and f.get('width') and f.get('link')]
    return {'key': f"pexels:{v['id']}", 'provider': 'Pexels', 'id': v['id'], 'page': v.get('url'),
            'author': (v.get('user') or {}).get('name', ''), 'author_url': (v.get('user') or {}).get('url', ''),
            'duration': v.get('duration') or 0, 'thumb': v.get('image'), 'tags': v.get('tags') or [], 'files': files}


def from_pixabay(v):
    files = [{'url': f['url'], 'w': f['width'], 'h': f['height'], 'fps': None}
             for f in (v.get('videos') or {}).values() if f.get('url') and f.get('width')]
    thumb = next((f.get('thumbnail') for f in (v.get('videos') or {}).values() if f.get('thumbnail')), None)
    return {'key': f"pixabay:{v['id']}", 'provider': 'Pixabay', 'id': v['id'], 'page': v.get('pageURL'),
            'author': v.get('user', ''), 'author_url': f"https://pixabay.com/users/{v.get('user', '')}-{v.get('user_id', '')}/",
            'duration': v.get('duration') or 0, 'thumb': thumb, 'tags': [t.strip() for t in (v.get('tags') or '').split(',') if t.strip()],
            'files': files}


def search_pexels(key, q, orientation, n, W, H):
    p = {'query': q, 'per_page': min(80, n * 2)}
    if min(W, H) >= 1000:  # Pexels 'size' is a minimum: large = 4K, medium = Full HD
        p['size'] = 'large' if min(W, H) >= 2000 else 'medium'
    if orientation:
        p['orientation'] = orientation
    return [from_pexels(v) for v in get_json('https://api.pexels.com/videos/search?' + urllib.parse.urlencode(p), {'Authorization': key}).get('videos', [])]


def search_pixabay(key, q, orientation, n, W, H):
    p = {'key': key, 'q': q[:100], 'per_page': max(3, min(200, n * 3)), 'video_type': 'film', 'safesearch': 'true'}
    return [from_pixabay(v) for v in get_json('https://pixabay.com/api/videos/?' + urllib.parse.urlencode(p)).get('hits', [])]


def lookup(key, keys):
    prov, _, vid = key.partition(':')
    prov = {'px': 'pexels', 'pb': 'pixabay'}.get(prov, prov)
    if prov not in PROVIDERS or not vid.isdigit():
        die(f'"{key}" is not a candidate key; use the form pexels:123456 or pixabay:123456 from the search table')
    if not keys[prov]:
        die(f'{PROVIDERS[prov]} is not set')
    if prov == 'pexels':
        return from_pexels(get_json(f'https://api.pexels.com/videos/videos/{vid}', {'Authorization': keys['pexels']}))
    hits = get_json('https://pixabay.com/api/videos/?' + urllib.parse.urlencode({'key': keys['pixabay'], 'id': vid})).get('hits', [])
    if not hits:
        die(f'pixabay:{vid} not found')
    return from_pixabay(hits[0])


def best_file(files, W, H):
    """Smallest rendition that still covers W x H after a centre crop; else the largest there is."""
    if not files:
        return None
    covering = [f for f in files if max(W / f['w'], H / f['h']) <= 1.0]
    return min(covering, key=lambda f: f['w'] * f['h']) if covering else max(files, key=lambda f: f['w'] * f['h'])


def orient(w, h):
    return 'portrait' if h > w * 1.05 else 'landscape' if w > h * 1.05 else 'square'


def parse_size(s):
    try:
        w, h = s.lower().split('x')
        return int(w), int(h)
    except ValueError:
        die(f'--size must look like 1920x1080, not "{s}"')


def opt(args, k, d=None):
    return args[args.index(k) + 1] if k in args and args.index(k) + 1 < len(args) else d


def no_keys():
    die('no stock API key found. Both are free:\n'
        '  Pexels:  sign up at https://www.pexels.com/api/  -> export PEXELS_API_KEY=...\n'
        '  Pixabay: sign up at https://pixabay.com/api/docs/ -> export PIXABAY_API_KEY=...\n'
        'or put those lines in a .env file in the project folder (and add .env to .gitignore). '
        'Ask the user to set them; do not paste keys into the chat.')


def cmd_search(args):
    q = args[0]
    out = pathlib.Path(opt(args, '--out') or die('--out is required'))
    W, H = parse_size(opt(args, '--size', '1920x1080'))
    orientation = opt(args, '--orientation') or orient(W, H)
    min_dur = float(opt(args, '--min-dur', 0))
    n = int(opt(args, '--n', 12))
    want = [p.strip() for p in opt(args, '--provider', 'pexels,pixabay').split(',')]
    keys = load_keys()
    active = [p for p in want if keys.get(p)]
    if not active:
        no_keys()
    results = {p: (search_pexels if p == 'pexels' else search_pixabay)(keys[p], q, orientation, n, W, H) for p in active}
    # keep relevance order per provider, drop what cannot work, interleave providers
    for p in results:
        results[p] = [c for c in results[p] if c['files'] and c['duration'] >= min_dur
                      and orient(max(f['w'] for f in c['files']), max(f['h'] for f in c['files'])) == orientation]
    cands, i = [], 0
    while len(cands) < n and any(i < len(r) for r in results.values()):
        cands += [r[i] for r in results.values() if i < len(r)]
        i += 1
    cands = cands[:n]
    if not cands:
        die(f'no {orientation} results >= {min_dur}s for "{q}". Try a simpler query (concrete noun + action), '
            'another orientation, or a shorter --min-dur.')
    out.mkdir(parents=True, exist_ok=True)
    thumbs = out / 'thumbs'
    shutil.rmtree(thumbs, ignore_errors=True)
    thumbs.mkdir()

    def cell(k_c):
        k, c = k_c
        top = max(c['files'], key=lambda f: f['w'] * f['h'])
        c.update({'n': k, 'max': [top['w'], top['h']], 'upscale': round(max(W / top['w'], H / top['h']), 2)})
        cw, ch = (320, 180) if orientation == 'landscape' else (180, 320) if orientation == 'portrait' else (240, 240)
        raw = thumbs / f'raw{k:02d}'
        try:
            download(c['thumb'], raw)
            src = ['-i', str(raw)]
        except Exception:
            src = ['-f', 'lavfi', '-i', f'color=gray:s={cw}x{ch}']
        res = '4K' if min(top['w'], top['h']) >= 2000 else f"{min(top['w'], top['h'])}p"
        tag = f"{k}  {round(c['duration'])}s {res}"
        run(['ffmpeg', '-v', 'error', '-y', *src, '-frames:v', '1', '-vf',
             f"scale={cw}:{ch}:force_original_aspect_ratio=decrease,pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color=black{label(tag, 18)}",
             str(thumbs / f'{k:03d}.png')])
        raw.unlink(missing_ok=True)

    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(cell, enumerate(cands, 1)))
    cols = 4 if orientation != 'portrait' else 6
    rows = -(-len(cands) // cols)
    run(['ffmpeg', '-v', 'error', '-y', '-framerate', '1', '-i', str(thumbs / '%03d.png'), '-vf',
         f'tile={cols}x{rows}:padding=4:color=white', '-frames:v', '1', str(out / 'sheet.jpg')])
    json.dump({'query': q, 'orientation': orientation, 'size': [W, H], 'candidates': cands}, open(out / 'candidates.json', 'w'), indent=1)
    print(f'"{q}"  {orientation}  ({", ".join(active)})  sheet: {out / "sheet.jpg"} (cells numbered left to right, top to bottom)')
    print(f"{'n':>2}  {'key':18} {'len':>5} {'max res':>10} {'upscale':>7}  author / tags")
    for c in cands:
        warn = '  <- soft' if c['upscale'] > 1.25 else ''
        up = f"{c['upscale']}x" if c['upscale'] > 1 else 'none'
        print(f"{c['n']:>2}  {c['key']:18} {c['duration']:>4}s {c['max'][0]:>5}x{c['max'][1]:<5} {up:>7}  "
              f"{c['author'][:24]} / {', '.join(c['tags'][:4])}{warn}")


def cmd_get(args):
    key = args[0]
    out = pathlib.Path(opt(args, '--out') or die('--out is required'))
    W, H = parse_size(opt(args, '--size', '1920x1080'))
    c = lookup(key, load_keys())
    f = best_file(c['files'], W, H) or die(f'{key} has no downloadable MP4')
    out.parent.mkdir(parents=True, exist_ok=True)
    download(f['url'], out)
    lic, lic_url = LICENCES[c['provider']]
    credit = {'source': 'stock', 'provider': c['provider'], 'key': c['key'], 'page': c['page'], 'author': c['author'],
              'author_url': c['author_url'], 'licence': lic, 'licence_url': lic_url, 'file': [f['w'], f['h']], 'duration': c['duration']}
    json.dump(credit, open(out.with_suffix('.json'), 'w'), indent=1)
    up = max(W / f['w'], H / f['h'])
    print(f"saved {out}  {f['w']}x{f['h']}  {c['duration']}s  by {c['author']} on {c['provider']}  (credit -> {out.with_suffix('.json')})")
    if up > 1.25:
        print(f'warning: the largest rendition is {f["w"]}x{f["h"]}; it will be upscaled {up:.2f}x and look soft at {W}x{H}')


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ('search', 'get'):
        die(__doc__)
    (cmd_search if a[0] == 'search' else cmd_get)(a[1:])


if __name__ == '__main__':
    main()
