# How Meta Andromeda works: 60 s explainer

Vox-style motion explainer for the team. 16:9, 1920x1080, 30 fps, 60 s, original synthesized soundtrack (copyright-free). Built to read on mute: every point is on screen.

**Concept:** one ad slot, millions of candidates, and a funnel that narrows them to the one ad that wins the slot.

## Script (on-screen)

| Time | Scene | On screen |
|---|---|---|
| 0-6 | Hook | You open Instagram. In milliseconds, Meta has to choose one ad for this slot. |
| 6-14 | The pool | The candidates: tens of millions of ads. Gen-AI tools have helped advertisers make hundreds of millions more. |
| 14-26 | The funnel | Retrieval (tens of millions in, a few thousand out) > Ranking > Auction. Andromeda is step one. |
| 26-36 | What it is | Deep-learning retrieval engine, launched Dec 2024. 10,000x model capacity, +6% recall, +8% ad quality (selected segments). NVIDIA Grace Hopper + Meta MTIA. |
| 36-44 | Oct 2026 upgrade | 1,000,000,000+ ads scored per second, 100x the 2024 system, +2.4% conversions on Facebook since 2025. |
| 44-56 | So what | Old question: which audience should I target? New question: which ad fits this person? Go broad, feed it genuinely different creative concepts, keep Pixel + CAPI clean. |
| 56-60 | End card | Creative is the new targeting. |

## Sources

- Meta Engineering, Dec 2 2024: https://engineering.fb.com/2024/12/02/production-engineering/meta-andromeda-advantage-automation-next-gen-personalized-ads-retrieval/
- Meta Engineering, Oct 28 2026: https://engineering.fb.com/2026/10/28/ml-applications/meta-andromeda-next-gen-ads-retrieval-gpu-co-design/

The "auction" step and the three takeaways are general Meta Ads practice, not quotes from these posts.

## Rebuild

```bash
npm install
pip install playwright pillow numpy scipy
python3 sound.py --bpm 120 --dur 60 --out music.wav --mood soft --drop 6 --riser 34 --end 56.5
python3 render.py video scene.html --out andromeda-explainer.mp4 --audio music.wav
```
