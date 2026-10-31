# Installed skills

Vendored, unmodified copies. Each was reviewed before install (scripts, network
calls, hooks, license); the notes below are what that review found.

## impeccable

- Source: https://github.com/pbakaus/impeccable, commit `df3a4ab`
  (skill v4.8.0, engine 0.1.18), copied from the repo's prebuilt `.claude/` folder.
- License: Apache 2.0.
- Installed: `.claude/skills/impeccable/` and the four `.claude/agents/impeccable-*.md`
  subagents it delegates to.
- Engine: `scripts/impeccable` is a shell launcher. On first use it downloads a
  Rust binary from the repo's GitHub releases into `~/.impeccable/bin/0.1.18/` and
  refuses to run it unless its SHA-256 matches `scripts/engine-checksums.txt`.
- Network: blocked for this repo. Upstream contacts impeccable.style for a daily
  update check, for visual directions when a new design starts (plus an anonymous
  record of the pick), and for direction preview images. `.claude/settings.json`
  turns telemetry and the update check off and points all three addresses at
  `127.0.0.1:9`, which accepts nothing. `.impeccable/config.json` repeats the
  telemetry and update-check opt-outs for runs outside Claude Code. Without the
  catalog, the skill picks directions from its own guidance ("degraded" seed).
  Checked with strace: no connection leaves the machine. Don't run
  `npx impeccable install` or `update`; they download from impeccable.style.
- Not installed: the automatic design-detector hook (upstream `.claude/settings.json`).
  It runs on every Edit/Write and on Stop, outside permission prompts. Without it the
  skill asks for one detector run at the end of a task instead. Opt in per developer
  with `/impeccable hooks on`.

## design-taste-frontend (tasteskill)

- Source: https://github.com/Leonxlnx/taste-skill (site: https://tasteskill.dev),
  commit `12af471` (v2.1.5), copied from `skills/taste-skill/`.
- License: MIT.
- Scripts: plain Node 22+ with no dependencies. `inspect.mjs` and `scenes.mjs` drive
  a local headless Chrome; `assets.mjs` downloads openly licensed images from
  Openverse, Wikimedia Commons, the Met, the Art Institute of Chicago, Internet
  Archive and NASA. No uploads, no telemetry. Draw history goes to
  `~/.taste-skill/history.json`.

## Updating

Re-copy from a newer upstream commit, review the diff, and update the commits above.
