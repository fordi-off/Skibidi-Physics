"""Global constants and tuning values for Skibidi Physics."""
from enum import IntEnum

# --- Window / loop ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
PHYSICS_DT = 1.0 / 240.0     # fixed physics substep
MAX_SUBSTEPS = 8              # clamp so a lag spike can't blow up the sim

# --- World ---
GRAVITY = (0.0, 1500.0)       # y-down world, "down" is positive y
VOID_Y = 1350                 # absolute world y -- falling past this respawns you
GROUND_BASELINE = 560

# --- Player / ball ---
PLAYER_RADIUS = 17
PLAYER_MASS = 4.5
PLAYER_FRICTION = 0.85
PLAYER_ELASTICITY = 0.15
MOVE_FORCE = 5200.0
AIR_CONTROL = 0.45
MAX_MOVE_SPEED = 420.0
JUMP_SPEED = 580.0
COYOTE_TIME = 0.11            # seconds you can still jump after leaving ground
JUMP_BUFFER = 0.12            # seconds a jump press is remembered before landing
HURT_KNOCKBACK = 820.0
HURT_COOLDOWN = 0.65
BOUNCY_BOOST = 900.0

# --- Grapple ---
GRAPPLE_MAX_RANGE = 430.0
GRAPPLE_MIN_LENGTH = 40.0
GRAPPLE_MIN_FIRE_DISTANCE = 70.0  # refuse to hook something this close -- avoids a
                                    # degenerate short leash that violently fights momentum
GRAPPLE_REEL_SPEED = 260.0     # px/sec when holding reel in/out
GRAPPLE_LAUNCH_SPEED = 40.0    # projectile speed of the hook itself (visual + logical)

# --- Surfaces ---
ICE_FRICTION = 0.02
STICKY_FRICTION = 3.0
NORMAL_FRICTION = 0.9
CRUMBLE_DELAY = 0.35

# --- Space damping (air resistance) ---
SPACE_DAMPING = 0.9985

# --- Collision filter categories (separate from collision_type) ---
# Used only to keep the human and the AI racer from physically colliding
# with each other -- both still collide normally with every level shape.
CATEGORY_HUMAN = 1 << 0
CATEGORY_AI = 1 << 1

# --- Collision types ---
class CT(IntEnum):
    PLAYER = 1
    GROUND = 2
    HAZARD = 3
    GOAL = 4
    CRUMBLE = 5
    ANCHOR = 6
    WIND_ZONE = 7
    GRAVITY_ZONE = 8
    CHECKPOINT = 9
    BOUNCY = 10
    MOVING = 11
    HOOK = 12

# --- Platform "kinds" (visual + physical flavor) ---
NORMAL = "normal"
ICE = "ice"
STICKY = "sticky"
BOUNCY = "bouncy"
CRUMBLE = "crumble"
MOVING = "moving"

# --- Colors ---
class COLOR:
    BG_TOP = (10, 12, 26)
    BG_BOTTOM = (22, 16, 40)
    STAR = (140, 150, 210)

    PLAYER = (95, 240, 255)
    PLAYER_GLOW = (40, 130, 160)
    TRAIL = (95, 200, 255)

    AI_PLAYER = (255, 140, 90)
    AI_GLOW = (160, 80, 40)
    AI_TRAIL = (255, 170, 120)
    AI_ROPE = (255, 200, 170)

    GROUND = (58, 74, 107)
    GROUND_EDGE = (110, 150, 210)
    ICE = (178, 232, 255)
    ICE_EDGE = (230, 250, 255)
    STICKY = (150, 110, 60)
    STICKY_EDGE = (210, 160, 90)
    BOUNCY = (255, 95, 168)
    BOUNCY_EDGE = (255, 190, 220)
    CRUMBLE = (170, 110, 70)
    CRUMBLE_EDGE = (230, 170, 110)
    MOVING = (170, 220, 90)
    MOVING_EDGE = (220, 255, 150)

    HAZARD = (255, 71, 87)
    HAZARD_EDGE = (255, 170, 170)

    GOAL = (255, 209, 102)
    GOAL_EDGE = (255, 240, 200)

    WIND = (120, 220, 210)
    GRAVITY_ZONE = (150, 100, 255)

    ANCHOR = (255, 220, 120)
    ROPE = (230, 230, 240)

    CHECKPOINT_ACTIVE = (120, 255, 170)
    CHECKPOINT_INACTIVE = (90, 100, 130)

    HUD_TEXT = (230, 235, 245)
    HUD_SHADOW = (5, 5, 10)
