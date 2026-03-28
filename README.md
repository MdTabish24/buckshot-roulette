# Buckshot Roulette — 3D Panda3D Game

A faithful 3-D recreation of the Buckshot Roulette concept built with **Python 3.12 + Panda3D 1.10**.

## How to Run

```
cd buckshot_roulette
python main.py
```

## Controls

| Control | Action |
|---|---|
| **SHOOT SELF** button | Fire at yourself (blank = keep turn, live = take damage) |
| **SHOOT DEALER** button | Fire at the Dealer |
| **Item buttons** (right side) | Use one of your items |
| **R** | Restart the game |
| **ESC** | Quit |

## Items

| Item | Effect |
|---|---|
| Magnify | Peek at the next shell (Live/Blank) |
| Beer | Eject (discard) the next shell |
| Cigarette | Heal +1 HP |
| Hand Saw | Next shot deals 2× damage |
| Inverter | Flip next shell (Live↔Blank) |
| Handcuffs | Opponent skips their next turn |

## Game Rules

1. Each round loads a mix of **Live** (red) and **Blank** (blue) shells into a pump-action shotgun.
2. You know the *counts* but **not the order**.
3. On your turn: use items OR shoot yourself OR shoot the Dealer.
4. Shooting yourself with a blank = **no damage + keep your turn**.
5. Both players start with 3 HP (increases each round).
6. First to 0 HP loses.
7. When all shells are fired, the gun reloads and a new round begins with more shells and items.

## Files

| File | Purpose |
|---|---|
| `main.py` | Entry point, ShowBase subclass, input handling |
| `game_state.py` | Core logic — shells, HP, items, turn system, dealer AI |
| `scene_builder.py` | Procedural 3-D geometry (no external models needed) |
| `ui_manager.py` | 2-D HUD — HP bars, item buttons, event log |
