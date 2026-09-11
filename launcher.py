"""Game-select launcher: one shared pygame window, a menu to pick between
the two bundled games, each of which owns its own display mode while it's
active and hands control back here when the player backs out."""
import math
import sys

import pygame

MENU_SIZE = (960, 620)

BG_TOP = (10, 12, 26)
BG_BOTTOM = (20, 14, 36)
TEXT = (230, 235, 245)
SUBTEXT = (170, 180, 205)
ACCENT_A = (95, 240, 255)
ACCENT_B = (255, 140, 90)
CARD_BG = (26, 30, 48)
CARD_BG_HOVER = (36, 42, 64)


class GameEntry:
    def __init__(self, title, subtitle, accent, launch_fn):
        self.title = title
        self.subtitle = subtitle
        self.accent = accent
        self.launch_fn = launch_fn
        self.rect = pygame.Rect(0, 0, 0, 0)


class Launcher:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass  # no audio device available -- games degrade gracefully on their own

        self.screen = self._set_menu_display()
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont("consolas,menlo,monospace", 52, bold=True)
        self.font_card = pygame.font.SysFont("consolas,menlo,monospace", 30, bold=True)
        self.font_sub = pygame.font.SysFont("consolas,menlo,monospace", 17)
        self.font_hint = pygame.font.SysFont("consolas,menlo,monospace", 15)

        self.entries = [
            GameEntry("Skibidi Physics",
                      "physics puzzle platformer -- swing, roll, race an AI",
                      ACCENT_A, self._play_skibidi),
            GameEntry("Alien Shooter",
                      "4-wave galaxy invaders -- elite lasers, boss fight",
                      ACCENT_B, self._play_alien),
        ]
        self.selected = 0
        self.t = 0.0

    # ------------------------------------------------------------ games
    def _play_skibidi(self):
        from skibidi.game import Game
        game = Game()
        result = game.run_embedded()
        self._restore_menu_display()
        return result

    def _play_alien(self):
        from alien_shooter.game import AlienShooterGame
        game = AlienShooterGame()
        result = game.run()
        self._restore_menu_display()
        return result

    def _restore_menu_display(self):
        self.screen = self._set_menu_display()

    def _set_menu_display(self):
        # Tear down and rebuild the video subsystem before switching modes:
        # each game sets its own display mode while active, and re-running
        # set_mode() for a different mode later in the same process can
        # leave stale renderer state on some drivers otherwise.
        pygame.display.quit()
        pygame.display.init()
        screen = pygame.display.set_mode(MENU_SIZE)
        pygame.display.set_caption("Game Select")
        return screen

    # ------------------------------------------------------------ layout
    def _layout(self):
        w, h = MENU_SIZE
        card_w, card_h = 380, 300
        gap = 40
        total_w = card_w * len(self.entries) + gap * (len(self.entries) - 1)
        x0 = (w - total_w) // 2
        y0 = 210
        for i, entry in enumerate(self.entries):
            entry.rect = pygame.Rect(x0 + i * (card_w + gap), y0, card_w, card_h)

    # ------------------------------------------------------------ loop
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            self.t += dt
            self._layout()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                        self.selected = (self.selected - 1) % len(self.entries)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                        self.selected = (self.selected + 1) % len(self.entries)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self._launch(self.selected) == "quit":
                            running = False
                elif event.type == pygame.MOUSEMOTION:
                    for i, entry in enumerate(self.entries):
                        if entry.rect.collidepoint(event.pos):
                            self.selected = i
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, entry in enumerate(self.entries):
                        if entry.rect.collidepoint(event.pos):
                            if self._launch(i) == "quit":
                                running = False

            self.draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _launch(self, index):
        return self.entries[index].launch_fn()

    # ------------------------------------------------------------ draw
    def draw(self):
        surf = self.screen
        w, h = MENU_SIZE
        for y in range(0, h, 4):
            k = y / h
            col = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * k) for i in range(3))
            pygame.draw.rect(surf, col, (0, y, w, 4))

        bob = 5 * math.sin(self.t * 1.6)
        title = self.font_title.render("CHOOSE YOUR GAME", True, TEXT)
        surf.blit(title, (w // 2 - title.get_width() // 2, 70 + bob))
        sub = self.font_sub.render("Two games, one launcher -- pick one to play", True, SUBTEXT)
        surf.blit(sub, (w // 2 - sub.get_width() // 2, 140))

        mouse_pos = pygame.mouse.get_pos()
        for i, entry in enumerate(self.entries):
            hovered = entry.rect.collidepoint(mouse_pos) or i == self.selected
            bg = CARD_BG_HOVER if hovered else CARD_BG
            pygame.draw.rect(surf, bg, entry.rect, border_radius=14)
            pygame.draw.rect(surf, entry.accent if hovered else (70, 75, 95), entry.rect, 3, border_radius=14)

            pulse = 0.6 + 0.4 * math.sin(self.t * 3) if hovered else 1.0
            dot_col = tuple(min(255, int(c * pulse)) for c in entry.accent)
            pygame.draw.circle(surf, dot_col, (entry.rect.centerx, entry.rect.y + 60), 26)

            title_txt = self.font_card.render(entry.title, True, TEXT)
            surf.blit(title_txt, (entry.rect.centerx - title_txt.get_width() // 2, entry.rect.y + 110))

            words = entry.subtitle.split(" ")
            lines, line = [], ""
            for word in words:
                trial = (line + " " + word).strip()
                if self.font_sub.size(trial)[0] > entry.rect.w - 40:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            if line:
                lines.append(line)
            ly = entry.rect.y + 160
            for ln in lines:
                sub_txt = self.font_sub.render(ln, True, SUBTEXT)
                surf.blit(sub_txt, (entry.rect.centerx - sub_txt.get_width() // 2, ly))
                ly += 22

            if hovered:
                play_txt = self.font_sub.render("Enter / Click to play", True, entry.accent)
                surf.blit(play_txt, (entry.rect.centerx - play_txt.get_width() // 2, entry.rect.bottom - 34))

        hint = self.font_hint.render("Arrows/Mouse select   Enter/Click play   Esc quit", True, (150, 158, 185))
        surf.blit(hint, (w // 2 - hint.get_width() // 2, h - 34))
