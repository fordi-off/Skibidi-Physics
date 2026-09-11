"""Physical + visual level pieces: platforms, hazards, zones, goal..."""
import math
import pygame
import pymunk
from . import config as C


def _poly_screen_points(shape, cam):
    body = shape.body
    pts = []
    for v in shape.get_vertices():
        wx, wy = body.local_to_world(v)
        pts.append(cam.to_screen(wx, wy))
    return pts


class Platform:
    """A static (or kinematic, for 'moving') rectangular platform."""

    def __init__(self, space, x, y, w, h, kind=C.NORMAL):
        self.kind = kind
        self.w, self.h = w, h
        self.kinematic = kind == C.MOVING
        body_type = pymunk.Body.KINEMATIC if self.kinematic else pymunk.Body.STATIC
        self.body = pymunk.Body(body_type=body_type)
        self.body.position = (x + w / 2, y + h / 2)
        # small corner radius: keeps a fast-moving circular player from
        # snagging on a perfect 90-degree ledge corner and getting trapped
        # bouncing in place against a step.
        self.shape = pymunk.Poly.create_box(self.body, (w, h), radius=3.0)
        self.shape.friction = self._friction()
        self.shape.elasticity = 0.05
        self.shape.collision_type = int(C.CT.MOVING if self.kinematic else C.CT.GROUND)
        if kind == C.BOUNCY:
            self.shape.collision_type = int(C.CT.BOUNCY)
        self.shape.platform_kind = kind
        self.shape.owner = self
        space.add(self.body, self.shape)

        # motion state, used only for kind == MOVING
        self.point_a = pymunk.Vec2d(x + w / 2, y + h / 2)
        self.point_b = self.point_a
        self.speed = 0.0
        self.target = self.point_b

    def _friction(self):
        return {
            C.ICE: C.ICE_FRICTION,
            C.STICKY: C.STICKY_FRICTION,
        }.get(self.kind, C.NORMAL_FRICTION)

    def set_patrol(self, ax, ay, bx, by, speed):
        self.point_a = pymunk.Vec2d(ax, ay)
        self.point_b = pymunk.Vec2d(bx, by)
        self.body.position = self.point_a
        self.speed = speed
        self.target = self.point_b

    def update(self, dt):
        if not self.kinematic:
            return
        pos = self.body.position
        to_target = self.target - pos
        dist = to_target.length
        if dist < 4:
            self.target = self.point_a if self.target == self.point_b else self.point_b
            to_target = self.target - pos
            dist = to_target.length
        if dist > 1e-6:
            self.body.velocity = to_target.normalized() * self.speed
        else:
            self.body.velocity = (0, 0)

    def color(self):
        return {
            C.ICE: (C.COLOR.ICE, C.COLOR.ICE_EDGE),
            C.STICKY: (C.COLOR.STICKY, C.COLOR.STICKY_EDGE),
            C.BOUNCY: (C.COLOR.BOUNCY, C.COLOR.BOUNCY_EDGE),
            C.MOVING: (C.COLOR.MOVING, C.COLOR.MOVING_EDGE),
        }.get(self.kind, (C.COLOR.GROUND, C.COLOR.GROUND_EDGE))

    def draw(self, surf, cam):
        pts = _poly_screen_points(self.shape, cam)
        if max(p[0] for p in pts) < -50 or min(p[0] for p in pts) > surf.get_width() + 50:
            return
        fill, edge = self.color()
        pygame.draw.polygon(surf, fill, pts)
        pygame.draw.polygon(surf, edge, pts, 2)
        if self.kind == C.BOUNCY:
            cx = sum(p[0] for p in pts) / 4
            cy = min(p[1] for p in pts)
            pygame.draw.line(surf, edge, (cx - 10, cy + 6), (cx, cy - 2), 2)
            pygame.draw.line(surf, edge, (cx, cy - 2), (cx + 10, cy + 6), 2)


class CrumblePlatform(Platform):
    """Platform that starts falling apart shortly after being touched."""

    def __init__(self, space, x, y, w, h):
        super().__init__(space, x, y, w, h, kind=C.CRUMBLE)
        self.shape.collision_type = int(C.CT.CRUMBLE)
        self.triggered = False
        self.timer = C.CRUMBLE_DELAY
        self.removed = False
        self.fade = 1.0
        self.space_ref = space

    def trigger(self):
        self.triggered = True

    def update(self, dt):
        if self.triggered and not self.removed:
            self.timer -= dt
            if self.timer <= 0:
                self.removed = True
                if self.body in self.space_ref.bodies:
                    self.space_ref.remove(self.body, self.shape)
        elif self.removed:
            self.fade = max(0.0, self.fade - dt * 2.2)

    def draw(self, surf, cam):
        if self.removed and self.fade <= 0:
            return
        pts = _poly_screen_points_local(self, cam)
        alpha = int(255 * (0.5 if self.triggered and not self.removed else 1.0) * (self.fade if self.removed else 1.0))
        alpha = max(0, min(255, alpha))
        fill, edge = self.color()
        s = pygame.Surface((self.w + 4, self.h + 4), pygame.SRCALPHA)
        local_pts = [(p[0] - min(pp[0] for pp in pts) + 2, p[1] - min(pp[1] for pp in pts) + 2) for p in pts]
        pygame.draw.polygon(s, (*fill, alpha), local_pts)
        pygame.draw.polygon(s, (*edge, alpha), local_pts, 2)
        ox = min(p[0] for p in pts) - 2
        oy = min(p[1] for p in pts) - 2
        surf.blit(s, (ox, oy))


def _poly_screen_points_local(platform, cam):
    # crumble platform keeps its own body/shape position even after removal
    # from the space, so we compute screen points from cached geometry.
    body = platform.body
    pts = []
    for v in platform.shape.get_vertices():
        wx, wy = body.local_to_world(v)
        pts.append(cam.to_screen(wx, wy))
    return pts


class Hazard:
    """A row of spikes. Solid, but marked as damaging on contact."""

    def __init__(self, space, x, y, w, h=26):
        self.w, self.h = w, h
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        self.shape = pymunk.Poly.create_box(self.body, (w, h), radius=1)
        self.shape.friction = 0.6
        self.shape.elasticity = 0.0
        self.shape.collision_type = int(C.CT.HAZARD)
        self.shape.owner = self
        space.add(self.body, self.shape)

    def draw(self, surf, cam):
        cx, cy = cam.to_screen(*self.body.position)
        n = max(2, int(self.w // 18))
        step = self.w / n
        top = cy - self.h / 2
        base = cy + self.h / 2
        for i in range(n):
            x0 = cx - self.w / 2 + i * step
            tri = [(x0, base), (x0 + step * 0.5, top), (x0 + step, base)]
            pygame.draw.polygon(surf, C.COLOR.HAZARD, tri)
            pygame.draw.polygon(surf, C.COLOR.HAZARD_EDGE, tri, 1)


class Zone:
    """Base class for a sensor region (wind / gravity)."""

    def __init__(self, space, x, y, w, h, collision_type):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x + w / 2, y + h / 2)
        self.shape = pymunk.Poly.create_box(self.body, (w, h))
        self.shape.sensor = True
        self.shape.collision_type = int(collision_type)
        self.shape.owner = self
        space.add(self.body, self.shape)

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


class WindZone(Zone):
    def __init__(self, space, x, y, w, h, fx, fy):
        super().__init__(space, x, y, w, h, C.CT.WIND_ZONE)
        self.force = pymunk.Vec2d(fx, fy)
        self._t = 0.0

    def draw(self, surf, cam, particles):
        self._t += 1
        x0, y0 = cam.to_screen(self.x, self.y)
        x1, y1 = cam.to_screen(self.x + self.w, self.y + self.h)
        if x1 < -40 or x0 > surf.get_width() + 40:
            return
        s = pygame.Surface((max(1, x1 - x0), max(1, y1 - y0)), pygame.SRCALPHA)
        s.fill((*C.COLOR.WIND, 18))
        surf.blit(s, (x0, y0))
        import random
        if random.random() < 0.55:
            wx = self.x + random.uniform(0, self.w)
            wy = self.y + random.uniform(0, self.h)
            dirv = self.force.normalized() if self.force.length > 0 else pymunk.Vec2d(1, 0)
            particles.wind_streak(wx, wy, C.COLOR.WIND, dirv.x, dirv.y)


class GravityZone(Zone):
    def __init__(self, space, x, y, w, h, gx, gy):
        super().__init__(space, x, y, w, h, C.CT.GRAVITY_ZONE)
        self.gravity = pymunk.Vec2d(gx, gy)
        self._t = 0.0

    def draw(self, surf, cam, particles):
        x0, y0 = cam.to_screen(self.x, self.y)
        x1, y1 = cam.to_screen(self.x + self.w, self.y + self.h)
        if x1 < -40 or x0 > surf.get_width() + 40:
            return
        s = pygame.Surface((max(1, x1 - x0), max(1, y1 - y0)), pygame.SRCALPHA)
        s.fill((*C.COLOR.GRAVITY_ZONE, 26))
        surf.blit(s, (x0, y0))
        import random
        if random.random() < 0.4:
            wx = self.x + random.uniform(0, self.w)
            wy = self.y + random.uniform(0, self.h)
            g = self.gravity.normalized() if self.gravity.length > 0 else pymunk.Vec2d(0, 1)
            particles.sparkle(wx, wy, C.COLOR.GRAVITY_ZONE, (-g.x * 40, -g.y * 40))


class Anchor:
    """A grapple-friendly point. Visual + sensor (doesn't block movement)."""

    def __init__(self, space, x, y, radius=9):
        self.x, self.y, self.radius = x, y, radius
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        self.shape = pymunk.Circle(self.body, radius)
        self.shape.sensor = True
        self.shape.collision_type = int(C.CT.ANCHOR)
        self.shape.owner = self
        space.add(self.body, self.shape)
        self._t = 0.0

    def update(self, dt):
        self._t += dt

    def draw(self, surf, cam):
        sx, sy = cam.to_screen(self.x, self.y)
        pulse = 3 + 2 * math.sin(self._t * 4)
        pygame.draw.circle(surf, C.COLOR.ANCHOR, (sx, sy), self.radius, 2)
        pygame.draw.circle(surf, C.COLOR.ANCHOR, (sx, sy), int(self.radius * 0.35 + pulse * 0.3))


class Checkpoint:
    def __init__(self, space, x, y, w=24, h=90):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        self.shape = pymunk.Poly.create_box(self.body, (w, h))
        self.shape.sensor = True
        self.shape.collision_type = int(C.CT.CHECKPOINT)
        self.shape.owner = self
        space.add(self.body, self.shape)
        self.active = False
        self.respawn_point = (x, y - h / 2 - C.PLAYER_RADIUS - 2)

    def draw(self, surf, cam):
        col = C.COLOR.CHECKPOINT_ACTIVE if self.active else C.COLOR.CHECKPOINT_INACTIVE
        x0, y0 = cam.to_screen(self.x - self.w / 2, self.y - self.h / 2)
        x1, y1 = cam.to_screen(self.x + self.w / 2, self.y + self.h / 2)
        pygame.draw.line(surf, col, (x0 + (x1 - x0) / 2, y0), (x0 + (x1 - x0) / 2, y1), 3)
        pygame.draw.circle(surf, col, (x0 + (x1 - x0) // 2, y0), 6)


class Goal:
    def __init__(self, space, x, y, h=140):
        self.x, self.y, self.h = x, y, h
        self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.body.position = (x, y)
        self.shape = pymunk.Poly.create_box(self.body, (18, h))
        self.shape.sensor = True
        self.shape.collision_type = int(C.CT.GOAL)
        self.shape.owner = self
        space.add(self.body, self.shape)
        self._t = 0.0

    def update(self, dt):
        self._t += dt

    def draw(self, surf, cam):
        base = cam.to_screen(self.x, self.y + self.h / 2)
        top = cam.to_screen(self.x, self.y - self.h / 2)
        pygame.draw.line(surf, C.COLOR.GOAL_EDGE, base, top, 5)
        wave = math.sin(self._t * 5) * 6
        flag = [
            (top[0], top[1]),
            (top[0] + 46, top[1] + 14 + wave * 0.4),
            (top[0], top[1] + 30),
        ]
        pygame.draw.polygon(surf, C.COLOR.GOAL, flag)
        pygame.draw.polygon(surf, C.COLOR.GOAL_EDGE, flag, 2)
