"""Tiny procedural sound synthesizer -- no audio asset files needed.

Every effect is a short numpy waveform (tone blips / noise bursts with an
envelope) turned into a pygame Sound at import time.
"""
import numpy as np
import pygame

SAMPLE_RATE = 44100


def _stereo(mono: np.ndarray) -> np.ndarray:
    mono = np.clip(mono, -1.0, 1.0)
    data = (mono * 32767.0).astype(np.int16)
    return np.column_stack([data, data])


def _tone(freq, duration, wave="sine", vol=0.5, sweep=0.0, decay=3.0):
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    f = freq + sweep * t
    phase = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
    if wave == "sine":
        sig = np.sin(phase)
    elif wave == "square":
        sig = np.sign(np.sin(phase))
    elif wave == "saw":
        sig = 2.0 * (phase / (2 * np.pi) % 1.0) - 1.0
    else:
        sig = np.sin(phase)
    env = np.exp(-decay * t / max(duration, 1e-6))
    return sig * env * vol


def _noise(duration, vol=0.4, decay=6.0, lowpass=0.0):
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    sig = np.random.uniform(-1, 1, n)
    if lowpass > 0:
        k = max(1, int(lowpass))
        kernel = np.ones(k) / k
        sig = np.convolve(sig, kernel, mode="same")
    env = np.exp(-decay * t / max(duration, 1e-6))
    return sig * env * vol


class Audio:
    """Lazily builds sounds once the mixer is up; silently no-ops if
    audio hardware/driver isn't available (headless envs, CI, etc.)."""

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
            self._build()
            self.enabled = True
        except Exception:
            self.enabled = False

    def _add(self, name, mono):
        snd = pygame.sndarray.make_sound(_stereo(mono))
        self.sounds[name] = snd

    def _build(self):
        self._add("jump", _tone(520, 0.12, "sine", vol=0.35, sweep=380, decay=6))
        self._add("land", _noise(0.08, vol=0.25, decay=14, lowpass=6))
        self._add("bounce", _tone(300, 0.18, "sine", vol=0.45, sweep=520, decay=4))
        self._add("hurt", _tone(180, 0.25, "square", vol=0.35, sweep=-120, decay=4))
        self._add("grapple_fire", _tone(900, 0.08, "square", vol=0.25, sweep=200, decay=8))
        self._add("grapple_attach", _tone(700, 0.1, "sine", vol=0.35, sweep=-100, decay=6))
        self._add("grapple_release", _tone(500, 0.1, "sine", vol=0.25, sweep=250, decay=6))
        self._add("crumble", _noise(0.3, vol=0.3, decay=5, lowpass=10))
        self._add("goal", self._chord())
        self._add("checkpoint", _tone(660, 0.15, "sine", vol=0.3, sweep=440, decay=5))
        self._add("gravity_flip", _tone(220, 0.3, "saw", vol=0.25, sweep=-80, decay=3))
        self._add("select", _tone(500, 0.06, "square", vol=0.25, sweep=300, decay=10))

    def _chord(self):
        parts = [
            _tone(523.25, 0.35, "sine", vol=0.25, decay=3),
            _tone(659.25, 0.35, "sine", vol=0.2, decay=3),
            _tone(783.99, 0.4, "sine", vol=0.22, decay=2.5),
        ]
        n = max(len(p) for p in parts)
        out = np.zeros(n)
        for p in parts:
            out[: len(p)] += p
        return out / 1.4

    def play(self, name, vol=1.0):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(vol)
            snd.play()
