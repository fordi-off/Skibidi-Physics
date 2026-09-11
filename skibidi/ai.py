"""A simple reflex-based AI racer.

This is not a pathfinder -- it doesn't know the level layout in advance.
Each frame it just looks a short distance ahead (relative to whichever way
"down" currently is, so gravity-flip corridors work automatically) and
reacts: jump if there's a wall or gap coming up, grab the nearest grapple
anchor if a gap looks too wide to clear on foot. That's enough to make it
a real opponent without needing it to be flawless -- it can still whiff a
jump or misjudge a swing, same as a person would.
"""
import pymunk
from . import config as C

_SOLID = {int(C.CT.GROUND), int(C.CT.MOVING), int(C.CT.CRUMBLE), int(C.CT.BOUNCY)}


class AIController:
    def __init__(self, level, space):
        self.level = level
        self.space = space
        self.grapple_cooldown = 0.0
        self.grapple_hold_timer = 0.0

    def decide(self, player, grapple, dt):
        """Returns (move_dir, want_jump, reel_dir) for this frame."""
        pos = player.body.position
        grav = player.effective_gravity
        down = grav.normalized() if grav.length > 0 else pymunk.Vec2d(0, 1)
        right = pymunk.Vec2d(down.y, -down.x)
        r = C.PLAYER_RADIUS

        move_dir = 1

        # Is there a wall/step immediately in front, at body height?
        wall_ahead = self._hits_solid(pos + right * (r + 6), pos + right * (r + 26))

        # Is there ground to land on further ahead, or a gap (maybe with
        # spikes waiting in it)?
        far = pos + right * 60
        ground_hits = self._query(far + down * -12, far + down * 170)
        ground_ahead = any(h.shape.collision_type in _SOLID for h in ground_hits)
        hazard_ahead = any(h.shape.collision_type == int(C.CT.HAZARD) for h in ground_hits)

        want_jump = bool(player.grounded and (wall_ahead or hazard_ahead or not ground_ahead))

        self.grapple_cooldown = max(0.0, self.grapple_cooldown - dt)
        reel_dir = 0
        if grapple.active:
            self.grapple_hold_timer -= dt
            reel_dir = -1  # reel in a little to build a proper swing
            if self.grapple_hold_timer <= 0 or player.body.velocity.dot(right) > 90:
                grapple.release()
                self.grapple_cooldown = 0.3
        elif not ground_ahead and self.grapple_cooldown <= 0:
            target = self._best_anchor(pos)
            if target is not None and grapple.try_fire(player.body, target):
                self.grapple_hold_timer = 1.1

        return move_dir, want_jump, reel_dir

    def _query(self, a, b):
        return self.space.segment_query(a, b, 2.0, pymunk.ShapeFilter())

    def _hits_solid(self, a, b):
        return any(h.shape.collision_type in _SOLID for h in self._query(a, b))

    def _best_anchor(self, pos):
        best, best_x = None, None
        for anchor in self.level.anchors:
            d = (pymunk.Vec2d(anchor.x, anchor.y) - pos).length
            if anchor.x > pos.x - 10 and d < C.GRAPPLE_MAX_RANGE * 0.92:
                if best is None or anchor.x < best_x:
                    best, best_x = anchor, anchor.x
        return None if best is None else pymunk.Vec2d(best.x, best.y)
