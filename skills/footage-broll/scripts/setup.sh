#!/usr/bin/env bash
# One-time check in the user's project: tools, ffmpeg features, stock API keys. Creates the broll/ working folders.
# usage: bash setup.sh [./broll]
set -e
DIR="${1:-./broll}"
mkdir -p "$DIR"/{inputs/own,raw,out,work}
missing=()
command -v ffmpeg >/dev/null || missing+=("ffmpeg (macOS: brew install ffmpeg; Windows: winget install ffmpeg; Linux: apt install ffmpeg)")
command -v ffprobe >/dev/null || missing+=("ffprobe (comes with ffmpeg)")
command -v python3 >/dev/null || missing+=("python3 (3.9+)")
if [ ${#missing[@]} -gt 0 ]; then printf 'Missing: %s\n' "${missing[@]}"; exit 1; fi
ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' zscale ' || echo "Note: this ffmpeg has no zscale filter, so HDR phone footage cannot be tone-mapped (it will look washed out)."
ffmpeg -v error -f lavfi -i color=s=64x64:d=0.1 -vf drawtext=text=a -f null - 2>/dev/null || echo "Note: this ffmpeg has no drawtext; contact sheets will have no number labels (count cells left to right)."
python3 -c "import faster_whisper" 2>/dev/null && echo "faster-whisper: installed (word timings from audio)" \
  || echo "faster-whisper: not installed. Fine with an SRT/VTT transcript; otherwise: python3 -m pip install faster-whisper"
have_key() { [ -n "${!1}" ] || grep -qs "^\s*\(export \)\?$1=" .env "$DIR/.env" ../.env 2>/dev/null; }
keys=0
for k in PEXELS_API_KEY PIXABAY_API_KEY; do
  if have_key "$k"; then echo "$k: set"; keys=1; else echo "$k: not set"; fi
done
[ $keys = 1 ] || echo "No stock key yet. Free keys: https://www.pexels.com/api/ and https://pixabay.com/api/docs/ (export them, or put KEY=value lines in .env and add .env to .gitignore)."
echo "Ready. Put the video and transcript in $DIR/inputs/, own footage in $DIR/inputs/own/."
