"""Top level game orchestration: state machine, physics stepping,
collision wiring, input, camera, rendering."""
import json
import math
import os
import random

import pygame
import pymunk

from . import config as C
from .audio import Audio
from .camera import Camera
from .grapple import Grapple
from .level_generator import generate_level
from .particles import ParticleSystem
from .player import Player
from .ui import UI

MENU = "menu"
PLAYING = "playing"
PAUSED = "paused"
LEVEL_COMPLETE = "level_complete"

SAVE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "save.json")


def load_save():
    try:
        with open(SAVE_PATH, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"best_level": 0, "best_times": {}}


def save_progress(data):
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


class Game:
    def __init__(self):
        pygame.init()
        self.fullscreen = True
        self.screen = self._make_display(self.fullscreen)
        pygame.display.set_caption("Skibidi Physics")
        self.clock = pygame.time.Clock()
        self.audio = Audio()
        self.ui = UI()
        self.particles = ParticleSystem()
        self.camera = Camera()
        self.save = load_save()

        self.stars = [
            (random.uniform(0, C.SCREEN_WIDTH * 2), random.uniform(0, C.SCREEN_HEIGHT * 0.75),
             random.uniform(1.0, 2.6), random.uniform(0, math.tau))
            for _ in range(150)
        ]

        self.state = MENU
        self.t = 0.0
        self.run_seed = 0
        self.level_index = 0
        self.deaths_this_run = 0
        self.elapsed = 0.0
        self.level_complete_timer = 0.0
        self.is_new_best = False
        self.accumulator = 0.0
        self.move_dir = 0

        self.space = None
        self.level = None
        self.player = None
        self.grapple = None

    # ------------------------------------------------------------ display
    def _make_display(self, fullscreen):
        # SCALED keeps the game logic at a fixed 1280x720 and lets SDL
        # scale that up to whatever the real display resolution is, so
        # fullscreen "just works" on any monitor without touching any
        # world-space or UI coordinates elsewhere in the code. Mouse
        # positions from pygame are already translated back into this
        # logical space, so grapple aiming needs no extra handling.
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else 0)
        try:
            return pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), flags)
        except pygame.error:
            # some drivers/multi-monitor setups choke on FULLSCREEN|SCALED --
            # fall back to a plain window rather than failing to launch.
            self.fullscreen = False
            return pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SCALED)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.screen = self._make_display(self.fullscreen)

    # ------------------------------------------------------------ setup
    def _build_space(self):
        space = pymunk.Space()
        space.gravity = C.GRAVITY
        space.damping = C.SPACE_DAMPING
        space.iterations = 12
        self._register_collisions(space)
        return space

    def _register_collisions(self, space):
        CT = C.CT

        def owner_of(arb, predicate):
            for s in arb.shapes:
                o = getattr(s, "owner", None)
                if o is not None and predicate(o):
                    return o
            return None

        def on_ground_begin(arb, space_, data):
            self.player.ground_contacts += 1
            speed = self.player.body.velocity.length
            if speed > 260:
                px, py = self.player.body.position
                self.particles.dust(px, py + C.PLAYER_RADIUS * 0.6, (200, 205, 225), count=7)
                self.audio.play("land", vol=min(1.0, speed / 900))
                self.camera.add_trauma(min(0.22, speed / 4200))

        def on_ground_sep(arb, space_, data):
            self.player.ground_contacts = max(0, self.player.ground_contacts - 1)

        space.on_collision(int(CT.PLAYER), int(CT.GROUND), begin=on_ground_begin, separate=on_ground_sep)
        space.on_collision(int(CT.PLAYER), int(CT.MOVING), begin=on_ground_begin, separate=on_ground_sep)

        def on_bouncy(arb, space_, data):
            body = self.player.body
            vx, vy = body.velocity
            boost = C.BOUNCY_BOOST + min(320, abs(vy) * 0.35)
            body.velocity = (vx, -boost)
            px, py = body.position
            self.particles.burst(px, py + C.PLAYER_RADIUS, C.COLOR.BOUNCY, count=16,
                                  speed=280, life=0.45, gravity=900, radius=3)
            self.audio.play("bounce")
            self.camera.add_trauma(0.18)

        space.on_collision(int(CT.PLAYER), int(CT.BOUNCY), begin=on_bouncy)

        def on_hazard(arb, space_, data):
            hshape = None
            for s in arb.shapes:
                if s.collision_type == int(CT.HAZARD):
                    hshape = s
            px, py = self.player.body.position
            if hshape is not None:
                hx, hy = hshape.body.position
            else:
                hx, hy = px, py + 40
            direction = pymunk.Vec2d(px - hx, py - hy - 60)
            if self.player.hurt(direction):
                self.particles.burst(px, py, C.COLOR.HAZARD, count=24, speed=340,
                                      life=0.55, gravity=750, radius=3)
                self.audio.play("hurt")
                self.camera.add_trauma(0.45)
                self.deaths_this_run += 1

        space.on_collision(int(CT.PLAYER), int(CT.HAZARD), begin=on_hazard)

        def on_crumble_begin(arb, space_, data):
            self.player.ground_contacts += 1
            o = owner_of(arb, lambda o: hasattr(o, "trigger"))
            if o is not None:
                o.trigger()

        def on_crumble_sep(arb, space_, data):
            self.player.ground_contacts = max(0, self.player.ground_contacts - 1)

        space.on_collision(int(CT.PLAYER), int(CT.CRUMBLE), begin=on_crumble_begin, separate=on_crumble_sep)

        def on_goal(arb, space_, data):
            self.trigger_level_complete()

        space.on_collision(int(CT.PLAYER), int(CT.GOAL), begin=on_goal)

        def on_checkpoint(arb, space_, data):
            o = owner_of(arb, lambda o: hasattr(o, "active"))
            if o is not None and not o.active:
                o.active = True
                self.audio.play("checkpoint")
                px, py = self.player.body.position
                self.particles.burst(px, py, C.COLOR.CHECKPOINT_ACTIVE, count=12,
                                      speed=150, life=0.5, gravity=0, radius=2)

        space.on_collision(int(CT.PLAYER), int(CT.CHECKPOINT), begin=on_checkpoint)

        def on_wind_begin(arb, space_, data):
            o = owner_of(arb, lambda o: hasattr(o, "force"))
            if o is not None and o not in self.player.active_wind_zones:
                self.player.active_wind_zones.append(o)

        def on_wind_sep(arb, space_, data):
            o = owner_of(arb, lambda o: hasattr(o, "force"))
            if o is not None and o in self.player.active_wind_zones:
                self.player.active_wind_zones.remove(o)

        space.on_collision(int(CT.PLAYER), int(CT.WIND_ZONE), begin=on_wind_begin, separate=on_wind_sep)

        def on_gz_begin(arb, space_, data):
            o = owner_of(arb, lambda o: hasattr(o, "gravity"))
            if o is not None:
                self.player.active_gravity_zones.append(o)
                self.audio.play("gravity_flip")

        def on_gz_sep(arb, space_, data):
            o = owner_of(arb, lambda o: hasattr(o, "gravity"))
            if o is not None and o in self.player.active_gravity_zones:
                self.player.active_gravity_zones.remove(o)

        space.on_collision(int(CT.PLAYER), int(CT.GRAVITY_ZONE), begin=on_gz_begin, separate=on_gz_sep)

    # ------------------------------------------------------------ flow
    def start_new_run(self):
        self.run_seed = random.randint(0, 10_000_000)
        self.deaths_this_run = 0
        self.audio.play("select")
        self.start_level(0)
        self.state = PLAYING

    def start_level(self, level_index):
        self.level_index = level_index
        self.space = self._build_space()
        seed = self.run_seed * 1000 + level_index
        self.level = generate_level(self.space, seed, level_index)
        self.player = Player(self.space, *self.level.start_pos)
        self.grapple = Grapple(self.space)
        self.camera.x = self.level.start_pos[0] - C.SCREEN_WIDTH * 0.38
        self.camera.y = self.level.start_pos[1] - C.SCREEN_HEIGHT * 0.52
        self.camera.trauma = 0.0
        self.elapsed = 0.0
        self.level_complete_timer = 0.0
        self.accumulator = 0.0
        self.particles.particles.clear()

    def trigger_level_complete(self):
        if self.level.completed:
            return
        self.level.completed = True
        self.state = LEVEL_COMPLETE
        self.level_complete_timer = 2.0
        self.audio.play("goal")
        self.camera.add_trauma(0.2)
        best_times = self.save.setdefault("best_times", {})
        key = str(self.level_index)
        prev_best = best_times.get(key)
        self.is_new_best = prev_best is None or self.elapsed < prev_best
        if self.is_new_best:
            best_times[key] = self.elapsed
        self.save["best_level"] = max(self.save.get("best_level", 0), self.level_index + 1)
        save_progress(self.save)

    def handle_death_fall(self):
        self.deaths_this_run += 1
        rp = self.level.respawn_point_before(self.player.body.position.x)
        self.grapple.release()
        self.player.teleport(*rp)
        self.camera.add_trauma(0.3)
        self.particles.burst(rp[0], rp[1], (150, 160, 215), count=10, speed=140, life=0.4, gravity=0)

    # ------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.state == MENU:
                    self.start_new_run()
                elif self.state == PLAYING:
                    self.player.request_jump()
            elif event.key == pygame.K_ESCAPE:
                if self.state == PLAYING:
                    self.state = PAUSED
                elif self.state == PAUSED:
                    self.state = PLAYING
            elif event.key == pygame.K_r:
                if self.state in (PLAYING, PAUSED, LEVEL_COMPLETE):
                    self.audio.play("select")
                    self.start_level(self.level_index)
                    self.state = PLAYING
            elif event.key == pygame.K_q and self.state == PAUSED:
                self.state = MENU
            elif event.key in (pygame.K_F11, pygame.K_f):
                self.toggle_fullscreen()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == MENU:
                self.start_new_run()
            elif self.state == PLAYING and event.button == 1:
                self._fire_grapple(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.state == PLAYING and event.button == 1:
                if self.grapple.active:
                    self.audio.play("grapple_release")
                self.grapple.release()
        elif event.type == pygame.MOUSEWHEEL:
            if self.state == PLAYING and self.grapple.active:
                self.grapple.reel(-event.y, 1.0 / C.FPS * 6)

    def _fire_grapple(self, screen_pos):
        world = pymunk.Vec2d(screen_pos[0] + self.camera.x, screen_pos[1] + self.camera.y)
        self.audio.play("grapple_fire")
        if self.grapple.try_fire(self.player.body, world):
            self.audio.play("grapple_attach")
            self.camera.add_trauma(0.08)

    # ------------------------------------------------------------ update
    def physics_step(self, dt):
        self.accumulator += dt
        steps = 0
        while self.accumulator >= C.PHYSICS_DT and steps < C.MAX_SUBSTEPS:
            self._substep(C.PHYSICS_DT)
            self.accumulator -= C.PHYSICS_DT
            steps += 1

    def _substep(self, dt):
        self.player.apply_movement(self.move_dir, dt)
        self.player.update_pre_step(dt, self.space)
        self.space.step(dt)
        if self.player.body.position.y > C.VOID_Y:
            self.handle_death_fall()

    def update(self, dt):
        self.t += dt
        keys = pygame.key.get_pressed()
        self.move_dir = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.move_dir -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.move_dir += 1

        if self.state == PLAYING:
            self.physics_step(dt)
            if self.grapple.active:
                reel_dir = 0
                if keys[pygame.K_w] or keys[pygame.K_UP]:
                    reel_dir -= 1
                if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                    reel_dir += 1
                if reel_dir:
                    self.grapple.reel(reel_dir, dt)
            self.grapple.update(dt)
            self.level.update(dt)
            self.elapsed += dt
            self.camera.follow(self.player.body.position.x, self.player.body.position.y, dt)
            self._emit_trail()
        elif self.state == LEVEL_COMPLETE:
            self.level.update(dt)
            self.camera.follow(self.player.body.position.x, self.player.body.position.y, dt)
            self.level_complete_timer -= dt
            if self.level_complete_timer <= 0:
                self.start_level(self.level_index + 1)
                self.state = PLAYING

        self.camera.update_shake(dt)
        self.particles.update(dt)

    def _emit_trail(self):
        spd = self.player.body.velocity.length
        if spd > 150 and random.random() < 0.5:
            px, py = self.player.body.position
            self.particles.sparkle(px, py, C.COLOR.TRAIL)

    # ------------------------------------------------------------ draw
    def draw(self):
        surf = self.screen
        self._draw_background(surf)

        if self.level is not None and self.state in (PLAYING, PAUSED, LEVEL_COMPLETE):
            self.level.draw(surf, self.camera, self.particles)
            self._draw_grapple(surf)
            self._draw_player(surf)
            self.particles.draw(surf, self.camera)

            best_times = self.save.get("best_times", {})
            best = best_times.get(str(self.level_index))
            self.ui.draw_hud(surf, self.level_index, self.deaths_this_run, self.elapsed,
                              best, self.grapple.active)

            if self.state == PAUSED:
                self.ui.draw_pause(surf)
            elif self.state == LEVEL_COMPLETE:
                self.ui.draw_level_complete(surf, self.elapsed, best, self.is_new_best)

        if self.state == MENU:
            self.ui.draw_menu(surf, self.save.get("best_level", 0), self.t)

    def _draw_background(self, surf):
        top, bottom = C.COLOR.BG_TOP, C.COLOR.BG_BOTTOM
        h = C.SCREEN_HEIGHT
        for y in range(0, h, 4):
            k = y / h
            col = (
                int(top[0] + (bottom[0] - top[0]) * k),
                int(top[1] + (bottom[1] - top[1]) * k),
                int(top[2] + (bottom[2] - top[2]) * k),
            )
            pygame.draw.rect(surf, col, (0, y, C.SCREEN_WIDTH, 4))

        cam_x = self.camera.x if self.level is not None else self.t * 12
        tile = C.SCREEN_WIDTH * 2
        for sx, sy, size, phase in self.stars:
            dx = (sx - cam_x * 0.15) % tile
            if dx > C.SCREEN_WIDTH + 4:
                continue
            twinkle = 0.6 + 0.4 * math.sin(self.t * 2 + phase)
            c = tuple(int(v * twinkle) for v in C.COLOR.STAR)
            pygame.draw.circle(surf, c, (int(dx), int(sy)), max(1, int(size)))

    def _draw_grapple(self, surf):
        g = self.grapple
        if not g.active or g.anchor_point is None:
            return
        p0 = self.camera.to_screen(*self.player.body.position)
        p1 = self.camera.to_screen(*g.anchor_point)
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        cur_dist = (self.player.body.position - g.anchor_point).length
        slack = max(0.0, g.length - cur_dist)
        sag = min(30, slack * 0.5)
        sag_point = (mid[0], mid[1] + sag)
        pygame.draw.line(surf, C.COLOR.ROPE, p0, sag_point, 2)
        pygame.draw.line(surf, C.COLOR.ROPE, sag_point, p1, 2)
        pygame.draw.circle(surf, C.COLOR.ANCHOR, p1, 6)
        pygame.draw.circle(surf, C.COLOR.ANCHOR, p1, 6, 1)

    def _draw_player(self, surf):
        p = self.player
        sx, sy = self.camera.to_screen(*p.body.position)
        r = C.PLAYER_RADIUS
        glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*C.COLOR.PLAYER_GLOW, 90),
                            (glow.get_width() // 2, glow.get_height() // 2), int(r * 2.1))
        surf.blit(glow, (sx - glow.get_width() // 2, sy - glow.get_height() // 2),
                   special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surf, C.COLOR.PLAYER, (sx, sy), r)
        pygame.draw.circle(surf, (255, 255, 255), (sx, sy), r, 2)
        ang = p.body.angle
        dot = (sx + math.cos(ang) * r * 0.6, sy + math.sin(ang) * r * 0.6)
        pygame.draw.circle(surf, (20, 40, 60), dot, 3)
        if p.hurt_cooldown > 0.35:
            ring = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            a = int(160 * (p.hurt_cooldown - 0.35) / 0.3)
            pygame.draw.circle(ring, (255, 90, 90, max(0, a)), (r * 2, r * 2), int(r * 1.6), 3)
            surf.blit(ring, (sx - r * 2, sy - r * 2))

    # ------------------------------------------------------------ loop
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(C.FPS) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)
            if not running:
                break
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()
