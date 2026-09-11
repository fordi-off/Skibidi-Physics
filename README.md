# Skibidi Physics

`python main.py` opens a launcher menu with two games in it:

- **Skibidi Physics** — a physics-based puzzle platformer in the spirit of
  *Getting Over It* and gravity-flip games: you're a ball, the world is
  built out of raw pymunk geometry, and the whole game is about reading
  momentum, not pixel-perfect platforming. Every level is procedurally
  generated and gets meaner as you go.
- **Alien Shooter** — a 4-wave Galaxy Invaders-style shooter. Waves 1-3
  are alien formations (elite laser-eyed enemies mix in from wave 2);
  wave 4 is the boss, who alternates between a cucumber-projectile
  barrage and a sweeping telegraphed laser wall. Beat it and you get a
  victory screen with a button back to the launcher.

Both games share one pygame window and hand control back to the launcher
menu when you back out (`Esc`) rather than closing the app.

Built with **pygame** for rendering/input and **pymunk** (Chipmunk2D) for
Skibidi Physics' simulation.

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

## Controls -- Skibidi Physics

| Action | Key |
|---|---|
| Move | `A`/`D` or arrow keys |
| Jump | `Space` / `W` / `Up` (has coyote time + jump buffering) |
| Fire / hold grapple | Left mouse button, aimed at the cursor |
| Reel rope in / out | `W`/`S` or arrow keys while grappled, or scroll wheel |
| Restart level | `R` |
| Toggle AI racer | `T` |
| Toggle fullscreen | `F11` (or `F`) |
| Pause / back to game select | `Esc` |

## Controls -- Alien Shooter

| Action | Key |
|---|---|
| Move ship | `Left`/`Right` or `A`/`D` |
| Shoot | `Space` |
| Pause | `P` |
| Restart after game over | `R` |
| Back to game select | `Esc` |

## Custom textures

Drop a PNG at any of these paths and it's picked up automatically, no code
changes needed -- everything falls back to a procedural placeholder if the
file isn't there:

| File | Used for |
|---|---|
| `skibidi/assets/ball_face.png` | the player's ball in Skibidi Physics (circle-masked, spins with the ball) |
| `alien_shooter/assets/elite_enemy.png` | the elite alien's sprite (laser attack, has a health bar) |
| `alien_shooter/assets/cucumber.png` | the boss's projectile |

## Project layout

```
main.py                  entry point -- opens the launcher
launcher.py               game-select menu; owns the shared pygame window
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
  assets/                 ball_face.png goes here
alien_shooter/
  game.py                 4-wave campaign, elite enemy, boss, victory screen
  assets/                 sprites; cucumber.png / elite_enemy.png go here
```

Skibidi Physics progress (furthest level reached, best times per level) is
saved locally to `save.json` next to `main.py`.
