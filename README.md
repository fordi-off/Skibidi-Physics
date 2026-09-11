# Skibidi Physics

A physics-based puzzle platformer in the spirit of *Getting Over It* and
gravity-flip games: you're a ball, the world is built out of raw pymunk
geometry, and the whole game is about reading momentum, not pixel-perfect
platforming. There are no hand-authored levels — every run is procedurally
generated and gets meaner as you go.

Built with **pygame** for rendering/input and **pymunk** (Chipmunk2D) for
the physics simulation.

## Run it

```bash
pip install -r requirements.txt
python main.py
```

## What makes it tick

- **Momentum is the whole game.** You roll and jump; there's no air-brake.
  Commit to a jump at full speed and you're committed to where it lands.
- **A real rope, not a grapple-teleport.** The hook is a pymunk `SlideJoint`
  — a rope with slack, not a rigid rod. It only pulls taut once you're at
  its full length, which is what makes swinging feel like swinging. Reel it
  in or out mid-swing (`W`/`S` or scroll) to climb, drop, or add momentum.
- **Wind zones** push you continuously while you're inside them — sometimes
  as a tailwind that carries you over a gap you couldn't otherwise clear,
  sometimes as a headwind you have to fight or swing above.
- **Gravity-flip corridors.** Walk into one and gravity itself reorients —
  the ceiling becomes the floor until you walk back out. These show up from
  level 4 onward.
- **Surface variety**: ice (near-zero friction, you *will* slide), sticky
  mud (the opposite), trampolines (a real velocity-based bounce, not just
  high elasticity), crumbling platforms that start collapsing the instant
  you land on them, and moving platforms you have to time.
- **Checkpoints, not lives.** Falling into the void doesn't restart the
  level — it drops you at the last checkpoint you crossed. Hazards
  (spikes) don't kill you outright either; they knock you back hard. Death
  is rare, momentum loss is the real punishment.
- **Every level is generated from a seed** built from a chain of section
  "patterns" (gap jumps, staircases, floating islands, spike fields, wide
  grapple-only gaps, wind tunnels, gravity corridors, crumbling bridges,
  moving-platform gaps, bounce-pad chains). Which patterns are even allowed
  to appear scales up with the level index, so level 1 is a gentle ramp and
  by level 5+ you're swinging over spikes in a crosswind while gravity
  flips on you.
- Every sound effect is synthesized on the fly with numpy (no audio
  assets) — short procedural blips and noise bursts shaped with an
  envelope.
- **Race an AI.** A second ball runs the same procedurally generated course
  alongside you. It's not a pathfinder with the map memorized — each frame
  it just looks a short distance ahead (relative to whichever way "down"
  currently is, so it handles gravity-flip corridors on its own) and reacts:
  jumps over walls, gaps and spikes, and grabs the nearest grapple anchor
  when a gap looks too wide to clear on foot. It can whiff a jump or misjudge
  a swing, same as you can — it's an opponent, not an oracle. It runs on the
  same physics you do and passes through you rather than shoving you off
  ledges, so it's a race, not a wrestling match. The level only actually
  advances when *you* reach the goal; the AI beating you there just costs
  you that heat on the scoreboard. Toggle it off entirely with `T`.

## Controls

| Action | Key |
|---|---|
| Move | `A`/`D` or arrow keys |
| Jump | `Space` / `W` / `Up` (has coyote time + jump buffering) |
| Fire / hold grapple | Left mouse button, aimed at the cursor |
| Reel rope in / out | `W`/`S` or arrow keys while grappled, or scroll wheel |
| Restart level | `R` |
| Toggle AI racer | `T` |
| Toggle fullscreen | `F11` (or `F`) |
| Pause | `Esc` |

## Project layout

```
main.py                  entry point
skibidi/
  config.py               tuning constants, colors, collision types
  game.py                 state machine, physics stepping, input, rendering
  player.py               the ball: movement, jumping, gravity-relative control
  ai.py                   reflex-based AI racer (lookahead + grapple logic)
  grapple.py              the rope mechanic (pymunk SlideJoint)
  level_elements.py       platforms, hazards, wind/gravity zones, goal, etc.
  level_generator.py      seeded procedural section-pattern generator
  camera.py               follow camera + trauma-based screen shake
  particles.py            lightweight particle system
  audio.py                numpy-synthesized sound effects
  ui.py                   HUD, menu, pause and level-complete overlays
```

Progress (furthest level reached, best times per level) is saved locally to
`save.json` next to `main.py`.
