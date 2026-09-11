"""The grapple hook -- fire a rope at anything solid and swing.

Implemented as a pymunk SlideJoint (a rope, not a rigid rod): the player
can be anywhere up to `max` units from the anchor point, and the joint only
pulls taut once that distance is reached. Reeling in/out changes `max`
live, which is what lets you climb or lower yourself mid-swing.
"""
import pymunk
from . import config as C

# Only these are legitimate things to hook onto. Without this filter the
# raycast happily snags on invisible gameplay sensors (wind zones, gravity
# zones, checkpoints, the goal pole) since segment_query doesn't care about
# a shape's `sensor` flag -- that made firing the grapple near one of those
# zones silently grab empty air instead of the ground behind it.
_GRAPPLE_TARGETS = {
    int(C.CT.GROUND), int(C.CT.MOVING), int(C.CT.CRUMBLE),
    int(C.CT.BOUNCY), int(C.CT.ANCHOR),
}


class Grapple:
    def __init__(self, space):
        self.space = space
        self.active = False
        self.anchor_body = None
        self.anchor_point = None
        self.joint = None
        self.length = 0.0
        self.hook_progress = 1.0  # 0..1 visual "shoot" animation

    def try_fire(self, player_body, target_world):
        origin = player_body.position
        to_target = target_world - origin
        dist = to_target.length
        if dist < 1e-3:
            return False
        direction = to_target.normalized()
        end = origin + direction * min(dist, C.GRAPPLE_MAX_RANGE)

        filt = pymunk.ShapeFilter(group=1)  # matches player's group -> skip self
        hits = self.space.segment_query(origin, end, 2.0, filt)
        valid = [h for h in hits if h.shape is not None and h.shape.collision_type in _GRAPPLE_TARGETS]
        if not valid:
            return False
        hit = min(valid, key=lambda h: h.alpha)

        point = hit.point
        length = (point - origin).length
        if length < C.GRAPPLE_MIN_FIRE_DISTANCE:
            return False  # too close -- would create a violent, useless short leash

        self.release()

        self.anchor_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.anchor_body.position = point
        self.space.add(self.anchor_body)

        self.length = max(C.GRAPPLE_MIN_LENGTH, length)

        self.joint = pymunk.SlideJoint(
            player_body, self.anchor_body, (0, 0), (0, 0), 0.0, self.length
        )
        self.joint.collide_bodies = False
        self.joint.max_bias = 800
        self.joint.error_bias = pow(1.0 - 0.3, 60.0)
        self.space.add(self.joint)

        self.anchor_point = point
        self.active = True
        self.hook_progress = 0.0
        return True

    def release(self):
        if self.joint is not None:
            if self.joint in self.space.constraints:
                self.space.remove(self.joint)
            self.joint = None
        if self.anchor_body is not None:
            if self.anchor_body in self.space.bodies:
                self.space.remove(self.anchor_body)
            self.anchor_body = None
        self.active = False
        self.anchor_point = None

    def reel(self, direction, dt):
        """direction: -1 reel in (shorten), +1 reel out (lengthen)."""
        if not self.active or self.joint is None:
            return
        self.length += direction * C.GRAPPLE_REEL_SPEED * dt
        self.length = max(C.GRAPPLE_MIN_LENGTH, min(self.length, C.GRAPPLE_MAX_RANGE))
        self.joint.max = self.length

    def update(self, dt):
        if self.hook_progress < 1.0:
            self.hook_progress = min(1.0, self.hook_progress + dt * 8.0)
