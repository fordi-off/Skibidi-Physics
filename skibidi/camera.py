"""Follow camera with smoothing and a trauma-based screen shake."""
import random
from . import config as C


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.trauma = 0.0
        self.shake_x = 0.0
        self.shake_y = 0.0

    def follow(self, target_x, target_y, dt, level_min_x=0):
        desired_x = target_x - C.SCREEN_WIDTH * 0.38
        desired_y = target_y - C.SCREEN_HEIGHT * 0.52
        desired_x = max(level_min_x, desired_x)

        smoothing = 1 - pow(0.001, dt)
        self.x += (desired_x - self.x) * smoothing
        self.y += (desired_y - self.y) * smoothing

    def add_trauma(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update_shake(self, dt):
        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - dt * 2.2)
            power = self.trauma ** 2
            self.shake_x = random.uniform(-1, 1) * 24 * power
            self.shake_y = random.uniform(-1, 1) * 24 * power
        else:
            self.shake_x = 0.0
            self.shake_y = 0.0

    def to_screen(self, wx, wy):
        return int(wx - self.x + self.shake_x), int(wy - self.y + self.shake_y)
