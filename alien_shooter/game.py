"""
ALIEN SHOOTER - a Galaxy Invaders style 2D game.

Refactored to run embedded inside the combined launcher (see launcher.py):
no module-level pygame.init()/display calls, no pygame.quit()/sys.exit() --
AlienShooterGame().run() creates its own window, plays until the user backs
out or the game ends, and returns "menu" or "quit" for the launcher to act on.

Campaign: exactly 4 waves. Waves 1-3 are alien formations (elite "laser"
enemies start mixing in from wave 2). Wave 4 is the boss, who alternates
between a cucumber-projectile barrage and a sweeping telegraphed laser
wall. Beating the boss shows a victory screen with a button back to the
launcher's menu.

Controls:
  ENTER                   - start / continue from this game's own title screen
  LEFT / RIGHT or A / D   - move ship
  SPACE                   - shoot
  P                       - pause
  R                       - restart after game over
  ESC                     - back to the game-select menu
"""

import math
import os
import random

import pygame

# ---------------------------------------------------------------------------
# Constants (safe at import time -- no pygame calls that need a display)
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 800, 700
FPS = 60
FINAL_WAVE = 4

BLACK = (5, 5, 15)
WHITE = (255, 255, 255)
GREEN = (60, 220, 100)
RED = (230, 60, 60)
YELLOW = (240, 210, 60)
CYAN = (80, 220, 240)
PURPLE = (170, 90, 220)
GRAY = (120, 120, 140)
ORANGE = (250, 150, 50)
LASER_RED = (255, 40, 60)

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

PLAYER_SIZE = (98, 120)
BOSS_SIZE = (230, 230)
PLAYER_BULLET_SIZE = (36, 25)
ENEMY_BULLET_SIZE = (22, 42)
CUCUMBER_SIZE = (34, 34)
ELITE_SIZE = (70, 92)
PEPPER_SIZES = {"grunt": (48, 48), "tank": (64, 64), "scout": (40, 40)}
HEAL_SIZE = (34, 34)
HP_ICON_SIZE = (30, 22)

# Populated by _load_assets() the first time a game actually starts --
# deliberately NOT loaded at import time, since pygame.Surface.convert_alpha()
# needs a display mode to already exist, and this module may be imported by
# the launcher before any window is open.
_ASSETS_LOADED = False
FONT_BIG = FONT_MED = FONT_SMALL = None
PLAYER_IMG = PLAYER_IMG_FLASH = BOSS_IMG = BOSS_IMG_FLASH = None
PLAYER_BULLET_IMG = HP_ICON_IMG = ENEMY_BULLET_IMG = HEAL_IMG = None
CUCUMBER_IMG = None
ALIEN_IMAGES = {}
stars = []


def load_image(filename, size=None):
    path = os.path.join(ASSET_DIR, filename)
    img = pygame.image.load(path).convert_alpha()
    if size:
        img = pygame.transform.smoothscale(img, size)
    return img


def load_image_or_placeholder(filename, placeholder_fn, size):
    """Loads assets/<filename> if it exists; otherwise builds a procedural
    stand-in via placeholder_fn(size). Drop the real PNG into this game's
    assets/ folder later and it's picked up automatically, no code changes."""
    path = os.path.join(ASSET_DIR, filename)
    if os.path.exists(path):
        return load_image(filename, size)
    return placeholder_fn(size)


def make_cucumber_placeholder(size):
    """A stylized cucumber-slice: green rind, pale flesh, seed ring."""
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    r = min(w, h) / 2
    pygame.draw.circle(surf, (60, 130, 50), (int(cx), int(cy)), int(r))
    pygame.draw.circle(surf, (210, 235, 170), (int(cx), int(cy)), int(r * 0.82))
    pygame.draw.circle(surf, (150, 200, 110), (int(cx), int(cy)), int(r * 0.82), max(1, int(r * 0.08)))
    n = 8
    for i in range(n):
        ang = (i / n) * math.tau
        sx = cx + math.cos(ang) * r * 0.45
        sy = cy + math.sin(ang) * r * 0.45
        seed = pygame.Surface((int(r * 0.32), int(r * 0.16)), pygame.SRCALPHA)
        pygame.draw.ellipse(seed, (235, 245, 210), seed.get_rect())
        seed = pygame.transform.rotate(seed, math.degrees(ang))
        surf.blit(seed, seed.get_rect(center=(sx, sy)))
    pygame.draw.circle(surf, (40, 90, 35), (int(cx), int(cy)), int(r), max(1, int(r * 0.06)))
    return surf


def make_elite_placeholder(size):
    """A stand-in "stronger enemy" bust: blue armored suit, glowing red
    laser eyes -- swap in assets/elite_enemy.png for the real portrait."""
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    body = pygame.Rect(int(w * 0.12), int(h * 0.42), int(w * 0.76), int(h * 0.58))
    pygame.draw.rect(surf, (30, 60, 130), body, border_radius=int(w * 0.15))
    pygame.draw.rect(surf, (210, 175, 90), body, max(1, int(w * 0.035)), border_radius=int(w * 0.15))
    head_r = w * 0.28
    head_c = (w / 2, h * 0.28)
    pygame.draw.circle(surf, (230, 190, 150), head_c, head_r)
    hair = pygame.Rect(0, 0, int(head_r * 2.1), int(head_r * 1.2))
    hair.center = (head_c[0], head_c[1] - head_r * 0.35)
    pygame.draw.ellipse(surf, (90, 65, 45), hair)
    eye_dy = -head_r * 0.05
    for dx in (-head_r * 0.38, head_r * 0.38):
        glow = pygame.Surface((int(head_r), int(head_r)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 60, 60, 120), (glow.get_width() // 2, glow.get_height() // 2),
                            glow.get_width() // 2)
        surf.blit(glow, (head_c[0] + dx - glow.get_width() / 2, head_c[1] + eye_dy - glow.get_height() / 2),
                   special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surf, (255, 210, 210), (int(head_c[0] + dx), int(head_c[1] + eye_dy)), max(2, int(head_r * 0.16)))
        pygame.draw.circle(surf, (255, 30, 30), (int(head_c[0] + dx), int(head_c[1] + eye_dy)), max(1, int(head_r * 0.09)))
    return surf


def _load_assets():
    """Loads every image/font used by this game. Must only be called after
    a pygame display mode exists (AlienShooterGame.run() guarantees that)."""
    global _ASSETS_LOADED, FONT_BIG, FONT_MED, FONT_SMALL
    global PLAYER_IMG, PLAYER_IMG_FLASH, BOSS_IMG, BOSS_IMG_FLASH
    global PLAYER_BULLET_IMG, HP_ICON_IMG, ENEMY_BULLET_IMG, HEAL_IMG, CUCUMBER_IMG
    global ALIEN_IMAGES, stars
    if _ASSETS_LOADED:
        return

    FONT_BIG = pygame.font.SysFont("consolas", 64, bold=True)
    FONT_MED = pygame.font.SysFont("consolas", 32, bold=True)
    FONT_SMALL = pygame.font.SysFont("consolas", 20)

    PLAYER_IMG = load_image("player.png", PLAYER_SIZE)
    BOSS_IMG = load_image("boss.png", BOSS_SIZE)
    PLAYER_IMG_FLASH = PLAYER_IMG.copy()
    PLAYER_IMG_FLASH.fill((255, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
    BOSS_IMG_FLASH = BOSS_IMG.copy()
    BOSS_IMG_FLASH.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)

    PLAYER_BULLET_IMG = load_image("player_ammo.png", PLAYER_BULLET_SIZE)
    HP_ICON_IMG = load_image("player_ammo.png", HP_ICON_SIZE)
    ENEMY_BULLET_IMG = pygame.transform.rotate(load_image("enemy_ammo.png", ENEMY_BULLET_SIZE), 180)
    HEAL_IMG = load_image("heal.png", HEAL_SIZE)
    CUCUMBER_IMG = load_image_or_placeholder("cucumber.png", make_cucumber_placeholder, CUCUMBER_SIZE)

    pepper_base = {k: load_image("enemy.png", size) for k, size in PEPPER_SIZES.items()}

    def tinted(img, color):
        out = img.copy()
        out.fill(color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        return out

    elite_img = load_image_or_placeholder("elite_enemy.png", make_elite_placeholder, ELITE_SIZE)
    elite_flash = elite_img.copy()
    elite_flash.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)

    ALIEN_IMAGES = {
        "grunt": {"normal": pepper_base["grunt"], "flash": tinted(pepper_base["grunt"], (255, 255, 255))},
        "tank": {"normal": tinted(pepper_base["tank"], (200, 160, 255)), "flash": tinted(pepper_base["tank"], (255, 255, 255))},
        "scout": {"normal": tinted(pepper_base["scout"], (255, 240, 150)), "flash": tinted(pepper_base["scout"], (255, 255, 255))},
        "elite": {"normal": elite_img, "flash": elite_flash},
    }

    stars = [Star() for _ in range(120)]
    _ASSETS_LOADED = True


# ---------------------------------------------------------------------------
# Starfield background
# ---------------------------------------------------------------------------
class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_W)
        self.y = random.randint(0, SCREEN_H)
        self.speed = random.uniform(0.5, 3)
        self.size = random.choice([1, 1, 1, 2])

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_H:
            self.y = 0
            self.x = random.randint(0, SCREEN_W)

    def draw(self, surf):
        shade = int(120 + self.speed * 40)
        shade = min(shade, 255)
        pygame.draw.circle(surf, (shade, shade, shade), (int(self.x), int(self.y)), self.size)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.w, self.h = PLAYER_SIZE
        self.x = SCREEN_W // 2 - self.w // 2
        self.y = SCREEN_H - 150
        self.speed = 7
        self.lives = 3
        self.cooldown = 0
        self.cooldown_max = 14
        self.alive = True
        self.hit_flash = 0
        self.power = 1  # weapon power level

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.speed
        self.x = max(0, min(SCREEN_W - self.w, self.x))
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1

    def shoot(self, bullets):
        if self.cooldown == 0:
            cx = self.x + self.w // 2
            if self.power == 1:
                bullets.append(Bullet(cx, self.y, -10, CYAN, kind="player"))
            elif self.power == 2:
                bullets.append(Bullet(cx - 10, self.y, -10, CYAN, kind="player"))
                bullets.append(Bullet(cx + 10, self.y, -10, CYAN, kind="player"))
            else:
                bullets.append(Bullet(cx, self.y, -10, CYAN, kind="player"))
                bullets.append(Bullet(cx - 14, self.y + 6, -10, CYAN, dx=-2, kind="player"))
                bullets.append(Bullet(cx + 14, self.y + 6, -10, CYAN, dx=2, kind="player"))
            self.cooldown = self.cooldown_max

    def draw(self, surf):
        cx = self.x + self.w // 2
        glow_r = random.randint(4, 8)
        pygame.draw.circle(surf, ORANGE, (int(cx), int(self.y + self.h)), glow_r)
        img = PLAYER_IMG_FLASH if (self.hit_flash > 0 and self.hit_flash % 10 < 5) else PLAYER_IMG
        surf.blit(img, (int(self.x), int(self.y)))


# ---------------------------------------------------------------------------
# Bullets
# ---------------------------------------------------------------------------
class Bullet:
    def __init__(self, x, y, vy, color, dx=0, kind="player", img=None):
        self.x = x
        self.y = y
        self.vy = vy
        self.dx = dx
        self.color = color
        self.kind = kind
        self.img = img if img is not None else (PLAYER_BULLET_IMG if kind == "player" else ENEMY_BULLET_IMG)
        self.w = self.img.get_width()
        self.h = self.img.get_height()
        self.dead = False

    def update(self):
        self.y += self.vy
        self.x += self.dx
        if self.y < -30 or self.y > SCREEN_H + 30:
            self.dead = True

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    def draw(self, surf):
        surf.blit(self.img, (int(self.x - self.w / 2), int(self.y - self.h / 2)))


# ---------------------------------------------------------------------------
# Telegraphed laser beam -- used by elite aliens and the boss's sweep attack
# ---------------------------------------------------------------------------
class Laser:
    def __init__(self, x, w, warn_frames=45, fire_frames=18, delay=0, color=LASER_RED):
        self.x = x
        self.w = w
        self.warn_frames = warn_frames
        self.fire_frames = fire_frames
        self.t = -delay
        self.color = color
        self.dead = False

    @property
    def warning(self):
        return 0 <= self.t < self.warn_frames

    @property
    def firing(self):
        return self.t >= self.warn_frames

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), 0, self.w, SCREEN_H)

    def update(self):
        self.t += 1
        if self.t > self.warn_frames + self.fire_frames:
            self.dead = True

    def draw(self, surf):
        if self.t < 0:
            return
        if self.warning:
            pulse = 0.5 + 0.5 * math.sin(self.t * 0.6)
            line_w = max(2, int(self.w * 0.12))
            s = pygame.Surface((line_w, SCREEN_H), pygame.SRCALPHA)
            s.fill((*self.color, int(90 + 90 * pulse)))
            surf.blit(s, (int(self.x - line_w / 2), 0))
        elif self.firing:
            s = pygame.Surface((self.w, SCREEN_H), pygame.SRCALPHA)
            s.fill((*self.color, 110))
            surf.blit(s, (int(self.x - self.w / 2), 0), special_flags=pygame.BLEND_RGBA_ADD)
            core_w = max(3, int(self.w * 0.3))
            pygame.draw.rect(surf, WHITE, (int(self.x - core_w / 2), 0, core_w, SCREEN_H))


# ---------------------------------------------------------------------------
# Enemies (Aliens)
# ---------------------------------------------------------------------------
class Alien:
    TYPES = {
        "grunt": {"color": GREEN, "hp": 1, "score": 10, "w": 48, "h": 48},
        "tank": {"color": PURPLE, "hp": 3, "score": 30, "w": 64, "h": 64},
        "scout": {"color": YELLOW, "hp": 1, "score": 15, "w": 40, "h": 40},
        "elite": {"color": (90, 140, 255), "hp": 8, "score": 200, "w": ELITE_SIZE[0], "h": ELITE_SIZE[1]},
    }

    def __init__(self, x, y, kind="grunt"):
        self.kind = kind
        data = self.TYPES[kind]
        self.color = data["color"]
        self.hp = data["hp"]
        self.max_hp = data["hp"]
        self.score = data["score"]
        self.w = data["w"]
        self.h = data["h"]
        self.x = x
        self.y = y
        self.base_x = x
        self.t = random.uniform(0, math.pi * 2)
        self.dead = False
        self.hit_flash = 0
        self.laser_cooldown = random.randint(90, 180) if kind == "elite" else None

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, dx, dy, wobble=True):
        self.base_x += dx
        self.y += dy
        self.t += 0.08
        self.x = self.base_x + (math.sin(self.t) * 6 if wobble else 0)
        if self.hit_flash > 0:
            self.hit_flash -= 1

    def hit(self):
        self.hp -= 1
        self.hit_flash = 6
        if self.hp <= 0:
            self.dead = True
            return True
        return False

    def draw(self, surf):
        imgs = ALIEN_IMAGES[self.kind]
        img = imgs["flash"] if self.hit_flash > 0 else imgs["normal"]
        surf.blit(img, (int(self.x), int(self.y)))
        if self.max_hp > 1:
            bar_w = self.w
            pygame.draw.rect(surf, RED, (self.x, self.y - 8, bar_w, 4))
            pygame.draw.rect(surf, GREEN, (self.x, self.y - 8, bar_w * (self.hp / self.max_hp), 4))


class Boss:
    def __init__(self, wave):
        self.w, self.h = BOSS_SIZE
        self.x = SCREEN_W // 2 - self.w // 2
        self.y = -self.h - 20
        self.target_y = 60
        self.max_hp = 90 + wave * 20
        self.hp = self.max_hp
        self.dir = 1
        self.speed = 3
        self.dead = False
        self.hit_flash = 0
        self.shoot_cooldown = 0
        self.laser_sweep_cooldown = 240
        self.t = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, bullets, lasers, player):
        if self.y < self.target_y:
            self.y += 2
            return
        self.t += 1
        self.x += self.dir * self.speed
        if self.x <= 20 or self.x + self.w >= SCREEN_W - 20:
            self.dir *= -1
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Attack 1: cucumber barrage, aimed loosely at the player
        self.shoot_cooldown -= 1
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = 35
            cx = self.x + self.w // 2
            cy = self.y + self.h
            target_x = player.x + player.w / 2
            angle_dx = (target_x - cx) / 80
            for off in (-30, 0, 30):
                bullets.append(Bullet(cx + off, cy, 6, RED, dx=angle_dx, kind="enemy", img=CUCUMBER_IMG))

        # Attack 2: a sweeping wall of telegraphed lasers -- a distinct
        # pattern from the barrage, forces lateral movement instead of gap-dodging
        self.laser_sweep_cooldown -= 1
        if self.laser_sweep_cooldown <= 0:
            self.laser_sweep_cooldown = 420
            n = 5
            spacing = SCREEN_W / (n + 1)
            for i in range(n):
                x = spacing * (i + 1)
                lasers.append(Laser(x, w=46, warn_frames=55, fire_frames=22, delay=i * 8))

    def hit(self, dmg=1):
        self.hp -= dmg
        self.hit_flash = 6
        if self.hp <= 0:
            self.dead = True
            return True
        return False

    def draw(self, surf):
        img = BOSS_IMG_FLASH if (self.hit_flash > 0 and self.hit_flash % 4 < 2) else BOSS_IMG
        surf.blit(img, (int(self.x), int(self.y)))
        bar_w = 300
        bar_x = SCREEN_W // 2 - bar_w // 2
        pygame.draw.rect(surf, GRAY, (bar_x, 20, bar_w, 14), border_radius=4)
        pygame.draw.rect(surf, RED, (bar_x, 20, bar_w * (self.hp / self.max_hp), 14), border_radius=4)
        pygame.draw.rect(surf, WHITE, (bar_x, 20, bar_w, 14), 2, border_radius=4)


# ---------------------------------------------------------------------------
# Power-ups
# ---------------------------------------------------------------------------
class PowerUp:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind  # "power" or "heal"
        self.w = self.h = 30
        self.dead = False

    def update(self):
        self.y += 2
        if self.y > SCREEN_H:
            self.dead = True

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def draw(self, surf):
        if self.kind == "heal":
            surf.blit(HEAL_IMG, (int(self.x), int(self.y)))
        else:
            pygame.draw.rect(surf, ORANGE, self.rect, border_radius=4)
            pygame.draw.rect(surf, WHITE, self.rect, 2, border_radius=4)
            txt = FONT_SMALL.render("P", True, BLACK)
            surf.blit(txt, (self.x + 9, self.y + 4))


# ---------------------------------------------------------------------------
# Particles (explosions)
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, 5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(15, 30)
        self.color = color
        self.size = random.randint(2, 4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= 1

    def draw(self, surf):
        if self.life > 0:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.size)


def spawn_explosion(particles, x, y, color, count=18):
    for _ in range(count):
        particles.append(Particle(x, y, color))


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class AlienShooterGame:
    """Embeddable version of the game. Call run() to play; it creates its
    own window, blocks until the player exits, and returns "menu" or "quit"
    without ever calling pygame.quit()/sys.exit() itself."""

    def __init__(self):
        self.screen = None
        self.clock = None
        self.state = "menu"
        self.score = 0
        self.wave = 1

    def _ensure_display(self):
        # Tear down and rebuild the video subsystem before switching modes --
        # avoids stale-renderer failures on some drivers when this game and
        # the launcher (or Skibidi's SCALED display) hand the window back
        # and forth in the same process.
        pygame.display.quit()
        pygame.display.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Alien Shooter")
        self.clock = pygame.time.Clock()

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.enemy_bullets = []
        self.lasers = []
        self.aliens = []
        self.particles = []
        self.powerups = []
        self.score = 0
        self.wave = 1
        self.state = "playing"
        self.formation_dir = 1
        self.formation_speed = 1.0
        self.boss = None
        self.spawn_wave()
        self.transition_timer = 0
        self.back_button_rect = None

    def spawn_wave(self):
        self.aliens = []
        rows = min(3 + self.wave // 2, 5)
        cols = 7
        elite_quota = {1: 0, 2: 1, 3: 2}.get(self.wave, 0)
        cells = [(r, c) for r in range(rows) for c in range(cols)]
        elite_cells = set()
        if elite_quota:
            front_row_cells = [rc for rc in cells if rc[0] == 0]
            elite_cells = set(random.sample(front_row_cells, min(elite_quota, len(front_row_cells))))

        for (r, c) in cells:
            x = 60 + c * 95
            y = 55 + r * 78
            if (r, c) in elite_cells:
                kind = "elite"
            else:
                roll = random.random()
                if r == 0 and self.wave >= 2:
                    kind = "tank" if roll < 0.25 else "grunt"
                elif roll < 0.15:
                    kind = "scout"
                else:
                    kind = "grunt"
            self.aliens.append(Alien(x, y, kind))
        self.formation_speed = 1.0 + self.wave * 0.15
        self.boss = None

    def spawn_boss(self):
        self.boss = Boss(self.wave)

    def update(self):
        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        self.player.update(keys)
        if keys[pygame.K_SPACE]:
            self.player.shoot(self.bullets)

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if not b.dead]

        for b in self.enemy_bullets:
            b.update()
        self.enemy_bullets = [b for b in self.enemy_bullets if not b.dead]

        for l in self.lasers:
            l.update()
        self.lasers = [l for l in self.lasers if not l.dead]

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        for pu in self.powerups:
            pu.update()
        self.powerups = [p for p in self.powerups if not p.dead]

        if self.boss:
            self.boss.update(self.enemy_bullets, self.lasers, self.player)
        else:
            self.update_formation()
            self.enemy_random_shoot()

        self.check_collisions()

        if self.player.lives <= 0:
            self.state = "gameover"

        if not self.boss and not self.aliens and self.state == "playing":
            self.state = "level_clear"
            self.transition_timer = 90

    def update_formation(self):
        if not self.aliens:
            return
        min_x = min(a.base_x for a in self.aliens)
        max_x = max(a.base_x + a.w for a in self.aliens)
        dx = self.formation_dir * self.formation_speed
        dy = 0
        if max_x + dx > SCREEN_W - 10 or min_x + dx < 10:
            self.formation_dir *= -1
            dy = 14
        for a in self.aliens:
            a.update(dx, dy)
            if a.y + a.h > self.player.y:
                self.state = "gameover"

    def enemy_random_shoot(self):
        shooters = [a for a in self.aliens if a.kind != "elite"]
        if random.random() < 0.02 + self.wave * 0.002 and shooters:
            shooter = random.choice(shooters)
            cx = shooter.x + shooter.w / 2
            cy = shooter.y + shooter.h
            self.enemy_bullets.append(Bullet(cx, cy, 6, RED, kind="enemy"))

        for a in self.aliens:
            if a.kind != "elite":
                continue
            a.laser_cooldown -= 1
            if a.laser_cooldown <= 0:
                a.laser_cooldown = random.randint(160, 240)
                self.lasers.append(Laser(a.x + a.w / 2, w=44, warn_frames=50, fire_frames=16))

    def check_collisions(self):
        for bullet in self.bullets:
            if bullet.dead:
                continue
            for alien in self.aliens:
                if alien.dead:
                    continue
                if bullet.rect.colliderect(alien.rect):
                    bullet.dead = True
                    if alien.hit():
                        self.score += alien.score
                        spawn_explosion(self.particles, alien.x + alien.w / 2, alien.y + alien.h / 2, alien.color)
                        if random.random() < 0.12:
                            kind = "power" if random.random() < 0.6 else "heal"
                            self.powerups.append(PowerUp(alien.x, alien.y, kind))
                    break
            if self.boss and not self.boss.dead and bullet.rect.colliderect(self.boss.rect):
                bullet.dead = True
                if self.boss.hit():
                    spawn_explosion(self.particles, self.boss.x + self.boss.w / 2, self.boss.y + self.boss.h / 2, RED, 50)
                    self.score += 1000
                    self.boss = None
                    if self.wave >= FINAL_WAVE:
                        self.state = "victory"

        self.aliens = [a for a in self.aliens if not a.dead]

        for bullet in self.enemy_bullets:
            if bullet.dead:
                continue
            if bullet.rect.colliderect(self.player.rect) and self.player.hit_flash == 0:
                bullet.dead = True
                self.player.lives -= 1
                self.player.hit_flash = 40
                spawn_explosion(self.particles, self.player.x + self.player.w / 2, self.player.y + self.player.h / 2, ORANGE)

        for laser in self.lasers:
            if laser.firing and laser.rect.colliderect(self.player.rect) and self.player.hit_flash == 0:
                self.player.lives -= 1
                self.player.hit_flash = 40
                spawn_explosion(self.particles, self.player.x + self.player.w / 2, self.player.y + self.player.h / 2, LASER_RED)

        for alien in self.aliens:
            if alien.rect.colliderect(self.player.rect) and self.player.hit_flash == 0:
                alien.dead = True
                self.player.lives -= 1
                self.player.hit_flash = 40
                spawn_explosion(self.particles, alien.x, alien.y, alien.color)
        self.aliens = [a for a in self.aliens if not a.dead]

        for pu in self.powerups:
            if pu.rect.colliderect(self.player.rect):
                pu.dead = True
                if pu.kind == "power":
                    self.player.power = min(3, self.player.power + 1)
                else:
                    self.player.lives += 1

    def next_wave(self):
        self.wave += 1
        self.bullets.clear()
        self.enemy_bullets.clear()
        self.lasers.clear()
        if self.wave >= FINAL_WAVE:
            self.spawn_boss()
            self.aliens = []
        else:
            self.spawn_wave()
        self.state = "playing"

    # ------------------------------------------------------------ drawing
    def draw(self, surf):
        surf.fill(BLACK)
        for s in stars:
            s.update()
            s.draw(surf)

        if self.state == "menu":
            self.draw_menu(surf)
            return

        if self.state in ("playing", "paused", "level_clear", "victory"):
            self.player.draw(surf)
            for a in self.aliens:
                a.draw(surf)
            if self.boss:
                self.boss.draw(surf)
            for b in self.bullets:
                b.draw(surf)
            for b in self.enemy_bullets:
                b.draw(surf)
            for l in self.lasers:
                l.draw(surf)
            for pu in self.powerups:
                pu.draw(surf)
            for p in self.particles:
                p.draw(surf)
            self.draw_hud(surf)

        if self.state == "paused":
            self.draw_center_text(surf, "PAUSED", "Press P to resume")
        elif self.state == "level_clear":
            self.draw_center_text(surf, f"WAVE {self.wave} CLEAR!", "Get ready...")
        elif self.state == "gameover":
            self.player.draw(surf)
            for p in self.particles:
                p.draw(surf)
            self.draw_hud(surf)
            self.draw_center_text(surf, "GAME OVER", f"Score: {self.score}   Press R to restart, Esc for menu")
        elif self.state == "victory":
            self.draw_victory(surf)

    def draw_hud(self, surf):
        score_txt = FONT_MED.render(f"Score: {self.score}", True, WHITE)
        surf.blit(score_txt, (15, 10))
        wave_label = "BOSS" if self.boss else f"{min(self.wave, FINAL_WAVE)}/{FINAL_WAVE}"
        wave_txt = FONT_MED.render(f"Wave: {wave_label}", True, WHITE)
        surf.blit(wave_txt, (SCREEN_W - wave_txt.get_width() - 15, 10))
        for i in range(self.player.lives):
            x = 15 + i * (HP_ICON_SIZE[0] + 6)
            y = SCREEN_H - HP_ICON_SIZE[1] - 10
            surf.blit(HP_ICON_IMG, (x, y))
        power_txt = FONT_SMALL.render(f"Weapon Lvl: {self.player.power}", True, CYAN)
        surf.blit(power_txt, (SCREEN_W // 2 - power_txt.get_width() // 2, SCREEN_H - 26))

    def draw_center_text(self, surf, big, small):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surf.blit(overlay, (0, 0))
        big_txt = FONT_BIG.render(big, True, YELLOW)
        surf.blit(big_txt, (SCREEN_W // 2 - big_txt.get_width() // 2, SCREEN_H // 2 - 60))
        small_txt = FONT_MED.render(small, True, WHITE)
        surf.blit(small_txt, (SCREEN_W // 2 - small_txt.get_width() // 2, SCREEN_H // 2 + 20))

    def draw_victory(self, surf):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))
        big_txt = FONT_BIG.render("VICTORY!", True, GREEN)
        surf.blit(big_txt, (SCREEN_W // 2 - big_txt.get_width() // 2, SCREEN_H // 2 - 150))
        score_txt = FONT_MED.render(f"Final Score: {self.score}", True, WHITE)
        surf.blit(score_txt, (SCREEN_W // 2 - score_txt.get_width() // 2, SCREEN_H // 2 - 70))

        btn_w, btn_h = 280, 60
        btn = pygame.Rect(SCREEN_W // 2 - btn_w // 2, SCREEN_H // 2 + 10, btn_w, btn_h)
        mouse_over = btn.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, (60, 200, 120) if mouse_over else (40, 150, 90), btn, border_radius=10)
        pygame.draw.rect(surf, WHITE, btn, 2, border_radius=10)
        label = FONT_MED.render("BACK TO MENU", True, BLACK if mouse_over else WHITE)
        surf.blit(label, (btn.centerx - label.get_width() // 2, btn.centery - label.get_height() // 2))
        self.back_button_rect = btn

        hint = FONT_SMALL.render("or press Enter / Space", True, GRAY)
        surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, btn.bottom + 16))

    def draw_menu(self, surf):
        title_txt = FONT_BIG.render("ALIEN SHOOTER", True, GREEN)
        surf.blit(title_txt, (SCREEN_W // 2 - title_txt.get_width() // 2, 120))

        ship_x = SCREEN_W // 2 - PLAYER_SIZE[0] // 2
        surf.blit(PLAYER_IMG, (ship_x, 230))

        play_txt = FONT_MED.render("ENTER  -  Play", True, WHITE)
        surf.blit(play_txt, (SCREEN_W // 2 - play_txt.get_width() // 2, 430))
        quit_txt = FONT_MED.render("ESC  -  Back to menu", True, WHITE)
        surf.blit(quit_txt, (SCREEN_W // 2 - quit_txt.get_width() // 2, 475))

        info_txt = FONT_SMALL.render(f"{FINAL_WAVE} waves, then the boss. Watch for elite aliens' laser eyes.",
                                      True, (200, 210, 230))
        surf.blit(info_txt, (SCREEN_W // 2 - info_txt.get_width() // 2, 535))
        hint_txt = FONT_SMALL.render("Move: Arrows / A-D     Shoot: Space     Pause: P", True, GRAY)
        surf.blit(hint_txt, (SCREEN_W // 2 - hint_txt.get_width() // 2, SCREEN_H - 40))

    # ------------------------------------------------------------ loop
    def run(self):
        """Blocks until the player exits this game. Returns "menu" (go back
        to the launcher's game-select screen) or "quit" (close the app)."""
        self._ensure_display()
        # Assets are reloaded every time this game is (re)entered rather
        # than cached across the whole process: _ensure_display() just tore
        # down and rebuilt the video subsystem, which can invalidate
        # Surfaces created against the previous display on some drivers.
        global _ASSETS_LOADED
        _ASSETS_LOADED = False
        _load_assets()
        self.state = "menu"
        self.back_button_rect = None

        result = "menu"
        running = True
        while running:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    result = "quit"
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        result = "menu"
                        running = False
                    elif event.key == pygame.K_RETURN and self.state == "menu":
                        self.reset()
                    elif event.key == pygame.K_p and self.state in ("playing", "paused"):
                        self.state = "paused" if self.state == "playing" else "playing"
                    elif event.key == pygame.K_r and self.state == "gameover":
                        self.reset()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.state == "victory":
                        result = "menu"
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and self.state == "victory":
                    if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                        result = "menu"
                        running = False

            if self.state == "level_clear":
                self.transition_timer -= 1
                if self.transition_timer <= 0:
                    self.next_wave()

            self.update()
            self.draw(self.screen)
            pygame.display.flip()

        return result
