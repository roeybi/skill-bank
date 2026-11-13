#!/usr/bin/env python3
"""Original, copyright-free music bed + UI sound effects, synthesized with numpy.

  python3 sound.py --bpm 120 --dur 15 --out music.wav \
      --drop 0 --riser 12 --end 14.5 --sfx "click@0.5,whoosh@2.0,pop@4.0,hit@8.0"

--drop    second where drums come in (0 = from the start)
--riser   second where a noise riser starts (it peaks on the next downbeat after it)
--end     second of the final hit; music rings out after it
--sfx     comma list of kind@seconds; kinds: click, pop, whoosh, hit, tick, swoosh-up
--key     root note, e.g. A, C#, F (minor key), default A
--mood    "drive" (four-on-the-floor, default) or "soft" (light kick on 1 and 3, long bass notes)
"""
import argparse
import wave
import numpy as np

SR = 44100
NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
         "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n, a=0.002, d=0.2, shape=4.0):
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    return att * np.exp(-shape * t / max(d, 1e-4))


def lp(x, cutoff):
    # one-pole low-pass, vectorised enough for short sounds
    from scipy.signal import lfilter
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)


def hp(x, cutoff):
    return x - lp(x, cutoff)


def kick(n=int(0.45 * SR)):
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, 0.001, 0.38, 5) * 0.95


def clap(n=int(0.25 * SR)):
    x = hp(rng.standard_normal(n), 900)
    e = env(n, 0.001, 0.12, 6)
    for k in (0.011, 0.022):
        i = int(k * SR); e[i:] += env(n - i, 0.001, 0.06, 8) * 0.6
    return x * e * 0.35


def hat(n=int(0.06 * SR), open_=False):
    if open_:
        n = int(0.22 * SR)
    x = hp(rng.standard_normal(n), 7000)
    return x * env(n, 0.0005, 0.05 if not open_ else 0.18, 6) * 0.18


def pluck(freq, n):
    t = np.arange(n) / SR
    saw = 2 * ((t * freq) % 1) - 1
    saw2 = 2 * ((t * freq * 1.006) % 1) - 1
    x = lp((saw + saw2) * 0.5, 2400)
    return x * env(n, 0.003, 0.35, 5)


def bass(freq, n):
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)
    e = np.clip(t / 0.005, 0, 1) * np.clip((n / SR - t) / 0.02, 0, 1)
    return x * e * 0.42


def pad(freqs, n):
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t + i) + 0.4 * np.sin(2 * np.pi * f * 2.003 * t)
            for i, f in enumerate(freqs))
    e = np.clip(t / 0.4, 0, 1) * np.clip((n / SR - t) / 0.4, 0, 1)
    return lp(x, 1400) * e * 0.05


def riser(n):
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    seg = 2048
    for i in range(0, n, seg):
        c = 400 + 9000 * (i / n) ** 2
        out[i:i + seg] = hp(lp(x[i:i + seg], c), c * 0.3)
    return out * (t / t[-1]) ** 2 * 0.35


SFX = {
    "click": lambda: hp(rng.standard_normal(int(0.03 * SR)), 2500) * env(int(0.03 * SR), 0.0003, 0.01, 6) * 0.5,
    "tick": lambda: np.sin(2 * np.pi * 2200 * np.arange(int(0.04 * SR)) / SR) * env(int(0.04 * SR), 0.0005, 0.015, 6) * 0.3,
    "pop": lambda: np.sin(2 * np.pi * np.cumsum(900 * np.exp(-np.arange(int(0.12 * SR)) / SR * 30) + 300) / SR)
                   * env(int(0.12 * SR), 0.001, 0.07, 5) * 0.45,
    "whoosh": lambda: _sweep(0.45, 300, 4000, down=True),
    "swoosh-up": lambda: _sweep(0.5, 300, 6000, down=False),
    "hit": lambda: (kick(int(0.9 * SR)) * 0.9 + np.concatenate([lp(rng.standard_normal(int(0.5 * SR)), 3000)
                    * env(int(0.5 * SR), 0.001, 0.4, 5) * 0.25, np.zeros(int(0.4 * SR))])),
}


def _sweep(sec, f0, f1, down):
    n = int(sec * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    seg = 1024
    for i in range(0, n, seg):
        p = i / n
        c = f1 + (f0 - f1) * p if down else f0 + (f1 - f0) * p
        out[i:i + seg] = hp(lp(x[i:i + seg], c), c * 0.4)
    t = np.arange(n) / n
    return out * np.sin(np.pi * t) ** 1.5 * 0.45


def place(buf, sound, at, gain=1.0):
    i = int(round(at * SR))
    if i >= len(buf) or i + len(sound) <= 0:
        return
    s = sound[max(0, -i):]
    i = max(0, i)
    j = min(len(buf), i + len(s))
    buf[i:j] += s[:j - i] * gain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bpm", type=float, default=120)
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--out", default="music.wav")
    ap.add_argument("--drop", type=float, default=0.0)
    ap.add_argument("--riser", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--sfx", default="")
    ap.add_argument("--key", default="A")
    ap.add_argument("--mood", default="drive", choices=["drive", "soft"])
    ap.add_argument("--no-music", action="store_true", help="sound effects only")
    a = ap.parse_args()

    beat = 60.0 / a.bpm
    end = a.end if a.end is not None else a.dur - beat
    total = a.dur + 0.0
    music = np.zeros(int(total * SR) + SR)
    sfx = np.zeros_like(music)
    root = 45 + NOTES[a.key]  # A2-ish
    prog = [0, -4, 3, -2]      # i  VI  III  VII  (minor)
    if not a.no_music:
        nbeats = int(end / beat)
        for b in range(nbeats):
            t = b * beat
            bar = b // 4
            deg = prog[bar % 4]
            if t >= a.drop - 1e-6 and a.mood == "drive":
                place(music, kick(), t)
                if b % 4 in (1, 3):
                    place(music, clap(), t)
            if a.mood == "soft" and b % 2 == 0:
                place(music, kick(int(0.3 * SR)) * 0.4, t)
            place(music, hat(), t + beat / 2)
            if b % 2 == 1:
                place(music, hat(open_=True), t + beat / 2, 0.6)
            if t >= a.drop - 1e-6:
                if a.mood == "drive":   # pumping off-beat bass
                    place(music, bass(hz(root + deg), int(beat * 0.45 * SR)), t + beat / 2)
                elif b % 2 == 0:        # soft: long notes on beats 1 and 3
                    place(music, bass(hz(root + deg), int(beat * 1.8 * SR)), t, 0.8)
            if b % 4 == 0:
                chord = [hz(root + 24 + deg + x) for x in (0, 3, 7)]
                place(music, pad(chord, int(4 * beat * SR)), t)
            if b % 2 == 0:
                for k, iv in enumerate((0, 7, 12)):
                    place(music, pluck(hz(root + 24 + deg + iv), int(0.3 * SR)), t + k * beat / 4, 0.18)
        if a.riser is not None:
            peak = (int(a.riser / (4 * beat)) + 1) * 4 * beat
            place(music, riser(int((peak - a.riser) * SR)), a.riser)
        place(music, SFX["hit"](), end, 0.9)
        place(music, pad([hz(root + 24 + x) for x in (0, 3, 7, 12)], int(1.6 * SR)), end, 1.4)
    for item in filter(None, [s.strip() for s in a.sfx.split(",")]):
        kind, at = item.split("@")
        place(sfx, SFX[kind.strip()](), float(at))

    mix = music * 0.8 + sfx
    mix = mix[:int(total * SR)]
    fade = int(0.35 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(mix)) or 1
    mix = np.tanh(mix / peak * 1.2) / np.tanh(1.2) * 0.89
    st = np.stack([mix, mix], axis=1)
    st[:, 0] = np.roll(st[:, 0], 8)  # tiny width
    pcm = (st * 32767).astype("<i2")
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {a.out}: {total:.2f}s at {a.bpm:g} BPM, key {a.key} minor, mood {a.mood}")


if __name__ == "__main__":
    main()
