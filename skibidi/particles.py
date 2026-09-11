"""Lightweight particle system for dust, sparks, wind streaks, trails..."""
import random
import math
import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "radius",
                 "gravity", "fade", "shrink")

    def __init__(self, x, y, vx, vy, life, color, radius, gravity=0.0,
                 fade=True, shrink=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.radius = radius
        self.gravity = gravity
        self.fade = fade
        self.shrink = shrink

    def update(self, dt):
        self.life -= dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0


class ParticleSystem:
    def __init__(self, max_particles=800):
        self.particles = []
        self.max_particles = max_particles

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        if len(self.particles) > self.max_particles:
            self.particles = self.particles[-self.max_particles:]

    def spawn(self, p):
        self.particles.append(p)

    def burst(self, x, y, color, count=16, speed=220, life=0.5, gravity=600,
              radius=3):
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.3, speed)
            self.spawn(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(life * 0.5, life), color,
                random.uniform(radius * 0.5, radius), gravity=gravity,
            ))

    def dust(self, x, y, color, count=6, dirx=0.0):
        for _ in range(count):
            vx = dirx * random.uniform(20, 90) + random.uniform(-40, 40)
            vy = random.uniform(-60, -10)
            self.spawn(Particle(x, y, vx, vy, random.uniform(0.25, 0.5),
                                 color, random.uniform(1.5, 3.5), gravity=300))

    def wind_streak(self, x, y, color, dirx, dir_y=0.0):
        speed = random.uniform(260, 420)
        self.spawn(Particle(
            x, y, dirx * speed, dir_y * speed + random.uniform(-15, 15),
            random.uniform(0.35, 0.65), color, random.uniform(1.0, 2.2),
            gravity=0.0, shrink=False,
        ))

    def sparkle(self, x, y, color, dirvec=(0, 0)):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(20, 90)
        self.spawn(Particle(
            x, y, math.cos(ang) * spd + dirvec[0] * 0.3,
            math.sin(ang) * spd + dirvec[1] * 0.3,
            random.uniform(0.3, 0.7), color, random.uniform(1.0, 2.5),
            gravity=-40,
        ))

    def draw(self, surf, cam):
        for p in self.particles:
            t = max(0.0, p.life / p.max_life)
            alpha = int(255 * t) if p.fade else 255
            r = max(0.5, p.radius * (t if p.shrink else 1.0))
            sx, sy = cam.to_screen(p.x, p.y)
            if -20 <= sx <= surf.get_width() + 20 and -20 <= sy <= surf.get_height() + 20:
                s = pygame.Surface((int(r * 2) + 2, int(r * 2) + 2), pygame.SRCALPHA)
                col = (*p.color, max(0, min(255, alpha)))
                pygame.draw.circle(s, col, (s.get_width() // 2, s.get_height() // 2), max(1, int(r)))
                surf.blit(s, (sx - s.get_width() // 2, sy - s.get_height() // 2))
