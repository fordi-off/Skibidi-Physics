"""The controllable ball."""
import math
import pymunk
from . import config as C


class Player:
    def __init__(self, space, x, y, is_ai=False):
        moment = pymunk.moment_for_circle(C.PLAYER_MASS, 0, C.PLAYER_RADIUS)
        self.body = pymunk.Body(C.PLAYER_MASS, moment)
        self.body.position = (x, y)
        self.shape = pymunk.Circle(self.body, C.PLAYER_RADIUS)
        self.shape.friction = C.PLAYER_FRICTION
        self.shape.elasticity = C.PLAYER_ELASTICITY
        self.shape.collision_type = int(C.CT.PLAYER)
        # The human and the AI racer pass through each other -- a race,
        # not a shoving match, so the AI can never bump you off a ledge.
        # (The grapple hook separately refuses to target CT.PLAYER shapes
        # at all, so this filter isn't needed for that.)
        all_masks = pymunk.ShapeFilter.ALL_MASKS()
        if is_ai:
            self.shape.filter = pymunk.ShapeFilter(categories=C.CATEGORY_AI,
                                                     mask=all_masks ^ C.CATEGORY_HUMAN)
        else:
            self.shape.filter = pymunk.ShapeFilter(categories=C.CATEGORY_HUMAN,
                                                     mask=all_masks ^ C.CATEGORY_AI)
        self.shape.owner = self
        space.add(self.body, self.shape)
        self.is_ai = is_ai

        self.ground_contacts = 0
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.hurt_cooldown = 0.0
        self.on_ice = False
        self.active_gravity_zones = []  # stack; last one wins
        self.active_wind_zones = []
        self.alive_time = 0.0
        self.visual_angle = 0.0
        self.squash = 1.0  # 1.0 = normal, used for a little landing squash/stretch

    @property
    def grounded(self):
        return self.ground_contacts > 0

    @property
    def effective_gravity(self):
        if self.active_gravity_zones:
            return self.active_gravity_zones[-1].gravity
        return pymunk.Vec2d(*C.GRAVITY)

    def request_jump(self):
        self.jump_buffer_timer = C.JUMP_BUFFER

    def apply_movement(self, move_dir, dt):
        vel = self.body.velocity
        grounded = self.grounded
        control = 1.0 if grounded else C.AIR_CONTROL
        if move_dir != 0:
            # push along the direction of "right" relative to current gravity
            grav = self.effective_gravity
            if grav.length > 0:
                down = grav.normalized()
            else:
                down = pymunk.Vec2d(0, 1)
            right = pymunk.Vec2d(down.y, -down.x)
            force = right * move_dir * C.MOVE_FORCE * control
            along_speed = vel.dot(right)
            if move_dir * along_speed < C.MAX_MOVE_SPEED:
                self.body.apply_force_at_world_point(force, self.body.position)

    def update_pre_step(self, dt, space):
        # timers
        self.alive_time += dt
        if self.grounded:
            self.coyote_timer = C.COYOTE_TIME
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        self.hurt_cooldown = max(0.0, self.hurt_cooldown - dt)

        can_jump = self.coyote_timer > 0.0
        wants_jump = self.jump_buffer_timer > 0.0
        jumped = False
        if can_jump and wants_jump:
            grav = self.effective_gravity
            up = -grav.normalized() if grav.length > 0 else pymunk.Vec2d(0, -1)
            vel = self.body.velocity
            vel_along_up = vel.dot(up)
            new_vel = vel - up * vel_along_up + up * C.JUMP_SPEED
            self.body.velocity = new_vel
            self.coyote_timer = 0.0
            self.jump_buffer_timer = 0.0
            jumped = True

        # apply zone forces (gravity zones + wind) each physics substep
        extra = pymunk.Vec2d(0, 0)
        if self.active_gravity_zones:
            zone_g = self.active_gravity_zones[-1].gravity
            extra += (zone_g - pymunk.Vec2d(*C.GRAVITY))
        for wz in self.active_wind_zones:
            extra += wz.force / self.body.mass
        if extra.length > 0:
            self.body.apply_force_at_world_point(extra * self.body.mass, self.body.position)

        return jumped

    def hurt(self, direction):
        if self.hurt_cooldown > 0:
            return False
        self.hurt_cooldown = C.HURT_COOLDOWN
        d = direction
        if d.length < 1e-6:
            d = pymunk.Vec2d(0, -1)
        else:
            d = d.normalized()
        self.body.velocity = d * C.HURT_KNOCKBACK
        return True

    def teleport(self, x, y):
        self.body.position = (x, y)
        self.body.velocity = (0, 0)
        self.body.angular_velocity = 0
        self.active_gravity_zones.clear()
        self.active_wind_zones.clear()
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.hurt_cooldown = 0.3
