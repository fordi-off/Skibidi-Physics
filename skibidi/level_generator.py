"""Procedural level generation.

A level is a chain of hand-designed "section patterns" stitched together
left-to-right with a seeded RNG. Difficulty (gap sizes, hazard density,
which patterns are even allowed) scales with the level index, so level 1
is a gentle ramp and by level 5+ you're swinging over spike pits in a
crosswind while gravity flips on you.
"""
import random
from . import config as C
from .level_elements import (
    Platform, CrumblePlatform, Hazard, WindZone, GravityZone, Anchor,
    Checkpoint, Goal,
)

GROUND_H = 46
MIN_Y = 220
MAX_Y = 650


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class LevelBuilder:
    def __init__(self, space):
        self.space = space
        self.platforms = []
        self.hazards = []
        self.wind_zones = []
        self.gravity_zones = []
        self.anchors = []
        self.checkpoints = []
        self.goal = None
        self.max_x = 0.0

    def platform(self, x, y, w, h=GROUND_H, kind=C.NORMAL):
        p = Platform(self.space, x, y, w, h, kind)
        self.platforms.append(p)
        self.max_x = max(self.max_x, x + w)
        return p

    def moving_platform(self, x, y, w, h, ax, ay, bx, by, speed):
        p = Platform(self.space, x, y, w, h, kind=C.MOVING)
        p.set_patrol(ax + w / 2, ay + h / 2, bx + w / 2, by + h / 2, speed)
        self.platforms.append(p)
        self.max_x = max(self.max_x, max(ax, bx) + w)
        return p

    def crumble(self, x, y, w, h=30):
        p = CrumblePlatform(self.space, x, y, w, h)
        self.platforms.append(p)
        self.max_x = max(self.max_x, x + w)
        return p

    def hazard(self, cx, cy, w, h=26):
        hz = Hazard(self.space, cx, cy, w, h)
        self.hazards.append(hz)
        self.max_x = max(self.max_x, cx + w / 2)
        return hz

    def wind(self, x, y, w, h, fx, fy):
        z = WindZone(self.space, x, y, w, h, fx, fy)
        self.wind_zones.append(z)
        self.max_x = max(self.max_x, x + w)
        return z

    def gravity_zone(self, x, y, w, h, gx, gy):
        z = GravityZone(self.space, x, y, w, h, gx, gy)
        self.gravity_zones.append(z)
        self.max_x = max(self.max_x, x + w)
        return z

    def anchor(self, x, y):
        a = Anchor(self.space, x, y)
        self.anchors.append(a)
        return a

    def checkpoint(self, x, y):
        c = Checkpoint(self.space, x, y)
        self.checkpoints.append(c)
        return c

    def set_goal(self, x, y):
        self.goal = Goal(self.space, x, y)


# ---------------------------------------------------------------- patterns
# Each pattern: (rng, b, x, y, diff, level_idx) -> (new_x, new_y)

def pat_flat(rng, b, x, y, diff, lvl):
    w = rng.randint(170, 260)
    roll = rng.random()
    kind = C.NORMAL
    if roll < 0.15:
        kind = C.ICE
    elif roll < 0.25:
        kind = C.STICKY
    b.platform(x, y, w, GROUND_H, kind)
    return x + w, y


def pat_gap(rng, b, x, y, diff, lvl):
    gap = clamp(75 + diff * 95 + rng.uniform(-15, 20), 60, 200)
    ny = clamp(y + rng.choice([-1, 0, 0, 1]) * rng.randint(20, 70), MIN_Y, MAX_Y)
    nx = x + gap
    w = rng.randint(120, 200)
    b.platform(nx, ny, w, GROUND_H, C.NORMAL)
    return nx + w, ny


def pat_stairs(rng, b, x, y, diff, lvl):
    steps = rng.randint(3, 5)
    d = rng.choice([-1, 1])
    for _ in range(steps):
        x += rng.randint(50, 90)
        y = clamp(y + d * rng.randint(30, 55), MIN_Y, MAX_Y)
        w = rng.randint(90, 140)
        b.platform(x, y, w, GROUND_H, C.NORMAL)
        x += w
    return x, y


def pat_islands(rng, b, x, y, diff, lvl):
    n = rng.randint(4, 6)
    for _ in range(n):
        x += rng.randint(70, 120)
        y = clamp(y + rng.randint(-60, 60), MIN_Y, MAX_Y)
        w = rng.randint(70, 110)
        kind = rng.choice([C.NORMAL, C.NORMAL, C.ICE, C.BOUNCY])
        b.platform(x, y, w, 28, kind)
        x += w
    return x, y


def pat_hazard(rng, b, x, y, diff, lvl):
    w1 = rng.randint(120, 180)
    b.platform(x, y, w1, GROUND_H, C.NORMAL)
    hx = x + w1
    hw = int(clamp(90 + diff * 60 + rng.uniform(-10, 20), 80, 220))
    b.platform(hx, y, hw, GROUND_H, C.NORMAL)
    b.hazard(hx + hw / 2, y - 13, max(30, hw - 16), 26)
    if rng.random() < 0.65:
        b.platform(hx - 10, y - 120, hw + 20, 24, C.NORMAL)
    ex = hx + hw
    w2 = rng.randint(120, 180)
    b.platform(ex, y, w2, GROUND_H, C.NORMAL)
    return ex + w2, y


def pat_wide_gap(rng, b, x, y, diff, lvl):
    gap = clamp(230 + diff * 110 + rng.uniform(-20, 20), 220, 380)
    ay = y - rng.randint(140, 220)
    ax = x + gap / 2
    b.anchor(ax, ay)
    nx = x + gap
    ny = clamp(y + rng.randint(-40, 40), MIN_Y, MAX_Y)
    w = rng.randint(140, 200)
    b.platform(nx, ny, w, GROUND_H, C.NORMAL)
    return nx + w, ny


def pat_wind(rng, b, x, y, diff, lvl):
    length = rng.randint(280, 440)
    strength = 260 + diff * 300
    d = rng.choice([1, 1, -1])
    b.platform(x, y, 90, GROUND_H, C.NORMAL)
    zx = x + 90
    b.wind(zx, y - 240, length, 280, strength * d, 0)
    cx = zx
    end = zx + length - 60
    while cx < end:
        w = rng.randint(55, 95)
        py = clamp(y + rng.randint(-50, 50), MIN_Y, MAX_Y)
        b.platform(cx, py, w, 20, C.ICE if rng.random() < 0.25 else C.NORMAL)
        cx += w + rng.randint(75, 115)
    ex = zx + length
    b.platform(ex, y, 150, GROUND_H, C.NORMAL)
    return ex + 150, y


def pat_gravity(rng, b, x, y, diff, lvl):
    corridor_w = rng.randint(260, 340)
    corridor_h = rng.randint(360, 460)
    b.platform(x, y, 140, GROUND_H, C.NORMAL)
    gx = x + 140
    top_y = y - corridor_h
    b.gravity_zone(gx, top_y, corridor_w, corridor_h, 0, -1500)
    ceiling_y = top_y + 30
    b.platform(gx, ceiling_y, corridor_w, 26, C.NORMAL)
    ex = gx + corridor_w
    b.platform(ex, y, 170, GROUND_H, C.NORMAL)
    return ex + 170, y


def pat_moving(rng, b, x, y, diff, lvl):
    gap = clamp(260 + diff * 100, 260, 420)
    speed = 90 + diff * 70
    w = 90
    b.platform(x, y, 60, GROUND_H, C.NORMAL)
    ax_, ay_ = x + 60, y - 15
    bx_, by_ = x + gap - w, y - 15
    b.moving_platform(ax_, ay_, w, 22, ax_, ay_, bx_, by_, speed)
    nx = x + gap
    w2 = rng.randint(140, 200)
    b.platform(nx, y, w2, GROUND_H, C.NORMAL)
    return nx + w2, y


def pat_crumble(rng, b, x, y, diff, lvl):
    n = rng.randint(3, 5)
    for _ in range(n):
        w = 68
        b.crumble(x, y, w, 30)
        x += w + 16
    w2 = rng.randint(140, 200)
    b.platform(x, y, w2, GROUND_H, C.NORMAL)
    return x + w2, y


def pat_bounce(rng, b, x, y, diff, lvl):
    b.platform(x, y, 120, GROUND_H, C.NORMAL)
    pad_x = x + 45
    b.platform(pad_x, y, 60, 20, C.BOUNCY)
    high_y = clamp(y - rng.randint(230, 330), MIN_Y, MAX_Y)
    landing_x = x + 190
    b.platform(landing_x, high_y, 170, GROUND_H, C.NORMAL)
    return landing_x + 170, high_y


POOL = [
    ("flat", pat_flat, 0, 3),
    ("gap", pat_gap, 0, 3),
    ("stairs", pat_stairs, 0, 2),
    ("islands", pat_islands, 1, 2),
    ("hazard", pat_hazard, 1, 2),
    ("wide_gap", pat_wide_gap, 2, 2),
    ("wind", pat_wind, 2, 2),
    ("moving", pat_moving, 2, 2),
    ("crumble", pat_crumble, 3, 2),
    ("gravity", pat_gravity, 3, 1),
    ("bounce", pat_bounce, 4, 1),
]


def choose_pattern(rng, level_idx, last_name):
    candidates = [c for c in POOL if c[2] <= level_idx]
    filtered = [c for c in candidates if c[0] != last_name] or candidates
    total = sum(c[3] for c in filtered)
    r = rng.uniform(0, total)
    upto = 0.0
    for name, fn, unlock, weight in filtered:
        upto += weight
        if upto >= r:
            return name, fn
    return filtered[-1][0], filtered[-1][1]


class Level:
    def __init__(self, builder, start_pos, width, seed, level_index):
        self.b = builder
        self.start_pos = start_pos
        self.width = width
        self.seed = seed
        self.level_index = level_index
        self.completed = False

    @property
    def platforms(self):
        return self.b.platforms

    @property
    def hazards(self):
        return self.b.hazards

    @property
    def wind_zones(self):
        return self.b.wind_zones

    @property
    def gravity_zones(self):
        return self.b.gravity_zones

    @property
    def anchors(self):
        return self.b.anchors

    @property
    def checkpoints(self):
        return self.b.checkpoints

    @property
    def goal(self):
        return self.b.goal

    def update(self, dt):
        for p in self.platforms:
            p.update(dt)
        for a in self.anchors:
            a.update(dt)
        if self.goal:
            self.goal.update(dt)

    def draw(self, surf, cam, particles):
        for z in self.gravity_zones:
            z.draw(surf, cam, particles)
        for z in self.wind_zones:
            z.draw(surf, cam, particles)
        for c in self.checkpoints:
            c.draw(surf, cam)
        for p in self.platforms:
            p.draw(surf, cam)
        for h in self.hazards:
            h.draw(surf, cam)
        for a in self.anchors:
            a.draw(surf, cam)
        if self.goal:
            self.goal.draw(surf, cam)

    def respawn_point_before(self, x):
        best = None
        for cp in self.checkpoints:
            if cp.active and cp.x <= x + 1:
                if best is None or cp.x > best.x:
                    best = cp
        if best:
            return best.respawn_point
        return self.start_pos


def generate_level(space, seed, level_index):
    rng = random.Random(seed)
    b = LevelBuilder(space)

    x, y = 0, C.GROUND_BASELINE
    start_w = 420
    b.platform(x, y, start_w, GROUND_H, C.NORMAL)
    cp = b.checkpoint(x + start_w - 40, y)
    cp.active = True
    start_pos = (x + 90, y - 70)
    x += start_w

    difficulty = min(1.0, level_index / 8.0)
    n_sections = min(15, 6 + level_index)

    last_name = None
    for i in range(n_sections):
        name, fn = choose_pattern(rng, level_index, last_name)
        last_name = name
        x, y = fn(rng, b, x, y, difficulty, level_index)
        if i % 3 == 2:
            b.checkpoint(x - 15, y)

    final_w = 320
    b.platform(x, y, final_w, GROUND_H, C.NORMAL)
    b.set_goal(x + final_w / 2, y - 100)
    x += final_w

    return Level(b, start_pos, x, seed, level_index)
