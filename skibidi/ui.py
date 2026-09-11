"""HUD, menus and overlays."""
import pygame
from . import config as C


class UI:
    def __init__(self):
        pygame.font.init()
        self.font_big = pygame.font.SysFont("consolas,menlo,monospace", 56, bold=True)
        self.font_mid = pygame.font.SysFont("consolas,menlo,monospace", 30, bold=True)
        self.font_small = pygame.font.SysFont("consolas,menlo,monospace", 20)
        self.font_tiny = pygame.font.SysFont("consolas,menlo,monospace", 15)

    def text(self, surf, s, font, pos, color=C.COLOR.HUD_TEXT, shadow=True, center=False,
              align="left"):
        # `center=True` is shorthand for align="center" (kept for existing call sites).
        if center:
            align = "center"

        def _place(rect, p):
            if align == "center":
                rect.center = p
            elif align == "right":
                rect.topright = p
            else:
                rect.topleft = p

        if shadow:
            sh = font.render(s, True, C.COLOR.HUD_SHADOW)
            r = sh.get_rect()
            _place(r, (pos[0] + 2, pos[1] + 2))
            surf.blit(sh, r)
        img = font.render(s, True, color)
        r = img.get_rect()
        _place(r, pos)
        surf.blit(img, r)
        return r

    def format_time(self, t):
        m = int(t // 60)
        s = t - m * 60
        return f"{m:02d}:{s:05.2f}"

    def draw_hud(self, surf, level_index, deaths, elapsed, best_time, grapple_active,
                 ai_present=False, ai_finished=False, player_wins=0, ai_wins=0):
        self.text(surf, f"LEVEL {level_index + 1}", self.font_mid, (24, 18))
        self.text(surf, f"time  {self.format_time(elapsed)}", self.font_small, (24, 62))
        best_s = self.format_time(best_time) if best_time is not None else "--:--.--"
        self.text(surf, f"best  {best_s}", self.font_small, (24, 86))
        self.text(surf, f"falls {deaths}", self.font_small, (24, 110))
        if grapple_active:
            self.text(surf, "GRAPPLED", self.font_small, (C.SCREEN_WIDTH - 24, 18),
                      color=C.COLOR.ANCHOR, align="right")

        if ai_present:
            self.text(surf, f"YOU {player_wins} - {ai_wins} AI", self.font_small,
                      (C.SCREEN_WIDTH - 24, 46), color=C.COLOR.AI_PLAYER, align="right")
            if ai_finished:
                self.text(surf, "the AI reached the goal!", self.font_small,
                          (C.SCREEN_WIDTH - 24, 70), color=C.COLOR.AI_PLAYER, align="right")

        hint = ("A/D or Arrows move   SPACE jump   Mouse: hold to fire grapple, W/S or scroll to reel   "
                "R restart   F11 fullscreen   T toggle AI   Esc pause")
        img = self.font_tiny.render(hint, True, (170, 180, 205))
        surf.blit(img, (24, C.SCREEN_HEIGHT - 30))

    def _panel(self, surf, alpha=170):
        s = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((8, 8, 16, alpha))
        surf.blit(s, (0, 0))

    def draw_menu(self, surf, best_level, t):
        self._panel(surf, 210)
        cx = C.SCREEN_WIDTH // 2
        bob = 6 * __import__("math").sin(t * 2)
        self.text(surf, "SKIBIDI PHYSICS", self.font_big, (cx, 190 + bob),
                   color=C.COLOR.PLAYER, center=True)
        self.text(surf, "a physics puzzle platformer", self.font_small,
                   (cx, 250), color=(180, 190, 220), center=True)

        lines = [
            "Roll, jump, swing and reel your way across procedurally",
            "generated obstacle courses. Wind will push you. Gravity",
            "will flip on you. Grapple across the gaps it makes.",
            "An AI racer runs the same course alongside you -- beat it",
            "to the goal, or bump it off a ledge along the way.",
            "",
            "A / D or Left-Right   -  roll",
            "SPACE / W / Up        -  jump (works on ice too, careful)",
            "Left Mouse (hold)     -  fire & hold grapple rope at cursor",
            "W/S or Scroll         -  reel the rope in / out while grappled",
            "T                     -  toggle the AI racer on/off",
            "R                     -  restart this level",
            "F11                   -  toggle fullscreen",
            "Esc                   -  pause",
        ]
        y = 320
        for ln in lines:
            self.text(surf, ln, self.font_tiny, (cx, y), color=(210, 215, 235), center=True)
            y += 24

        if best_level:
            self.text(surf, f"furthest reached: level {best_level}", self.font_small,
                       (cx, y + 14), color=C.COLOR.GOAL, center=True)
            y += 14

        pulse = 0.5 + 0.5 * __import__("math").sin(t * 4)
        col = tuple(int(c) for c in (
            C.COLOR.GOAL[0] * pulse + 120 * (1 - pulse),
            C.COLOR.GOAL[1] * pulse + 120 * (1 - pulse),
            C.COLOR.GOAL[2] * pulse + 120 * (1 - pulse),
        ))
        self.text(surf, "click or press SPACE to start", self.font_mid,
                   (cx, y + 60), color=col, center=True)

    def draw_pause(self, surf):
        self._panel(surf, 170)
        cx = C.SCREEN_WIDTH // 2
        self.text(surf, "PAUSED", self.font_big, (cx, C.SCREEN_HEIGHT // 2 - 40), center=True)
        self.text(surf, "Esc to resume   R to restart level   Q to quit to menu",
                   self.font_small, (cx, C.SCREEN_HEIGHT // 2 + 30), center=True)

    def draw_level_complete(self, surf, elapsed, best_time, is_new_best):
        self._panel(surf, 150)
        cx = C.SCREEN_WIDTH // 2
        self.text(surf, "LEVEL COMPLETE", self.font_big, (cx, C.SCREEN_HEIGHT // 2 - 60),
                   color=C.COLOR.GOAL, center=True)
        self.text(surf, f"time {self.format_time(elapsed)}", self.font_mid,
                   (cx, C.SCREEN_HEIGHT // 2 + 5), center=True)
        if is_new_best:
            self.text(surf, "NEW BEST!", self.font_small, (cx, C.SCREEN_HEIGHT // 2 + 45),
                       color=C.COLOR.BOUNCY, center=True)
        self.text(surf, "next level starting...", self.font_tiny,
                   (cx, C.SCREEN_HEIGHT // 2 + 80), color=(180, 190, 220), center=True)
