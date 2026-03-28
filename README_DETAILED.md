# Buckshot Roulette — 3D Game Implementation (Panda3D)

## Project Overview

**Buckshot Roulette** is a full 3D reimplementation of the intense turn-based survival game using **Panda3D** (Python 3D graphics engine). This project transforms the card-based original game into an immersive 3D experience with real-time gun animations, item mechanics, dealer AI, and a complete UI system.

**Genre**: Tactical Survival / Turn-Based Strategy  
**Engine**: Panda3D (Open-source 3D graphics engine)  
**Language**: Python 3  
**Platform**: Windows/Linux/macOS  

---

## Game Concept & Mechanics

### Core Gameplay Loop

In **Buckshot Roulette**, two players (the Player and the Dealer/AI) take turns shooting a shotgun loaded with a randomized mix of **LIVE** and **BLANK** shells at each other.

- **LIVE Shell** = Damage (1 HP normally, 2 HP if Hand Saw was used)
- **BLANK Shell** = No damage, but keeps the turn
- **Each Round**: 3 progressively difficult rounds with increasing shells and items
- **Victory Condition**: Reduce opponent's HP to 0 before being eliminated

### Key Game Features

#### 1. **Shotgun & Shell System**
- Shotgun loads with randomized LIVE and BLANK shells at round start
- Shells are consumed after each shot
- Shell distribution varies per round:
  - **Round 1**: 2 LIVE, 3 BLANK | Max Items: 2 per player | Max HP: 3
  - **Round 2**: 3 LIVE, 3 BLANK | Max Items: 3 per player | Max HP: 4
  - **Round 3**: 4 LIVE, 4 BLANK | Max Items: 4 per player | Max HP: 5

#### 2. **Turn System**
- **PLAYER Turn**: Shoot self or opponent, or use an item
- **DEALER Turn**: AI decides to shoot or use items based on probability
- **Cuffed State**: If handcuffed, skip entire turn
- **Game Over**: When either player reaches 0 HP

#### 3. **Item System**
Six unique items with distinct mechanics and animations:

| Item | Effect | Animation |
|------|--------|-----------|
| **Magnifying Glass** | Peek at next shell (LIVE/BLANK) | Examines gun with lens |
| **Beer** | Eject one shell from gun | Lifts beer, shells eject |
| **Cigarette** | Restore 1 HP | Player/Dealer smokes |
| **Hand Saw** | Next shot deals 2x damage (DOUBLE) | Saws gun barrel |
| **Inverter** | Flip next shell type (LIVE↔BLANK) | LED device flashes |
| **Handcuffs** | Handcuff opponent (skip next turn) | Handcuffs fly toward opponent |

---

## Project Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     BUCKSHOT ROULETTE GAME                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ MAIN.PY (Game Loop & Core Controller)                  │ │
│  │ - Entry point and game state management                │ │
│  │ - Camera control and mouse picking                     │ │
│  │ - Gun animations and interactions                      │ │
│  │ - Turn coordination (player/dealer)                    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            ↓                                  │
│         ┌──────────────────┬──────────────────┐              │
│         ↓                  ↓                  ↓              │
│  ┌────────────────┐ ┌─────────────────┐ ┌──────────────┐   │
│  │ GAME_STATE.PY  │ │ SCENE_BUILDER.PY│ │ UI_MANAGER.PY│   │
│  │                │ │                 │ │              │   │
│  │ • Game Logic   │ │ • 3D Scene Load │ │ • HUD Panels │   │
│  │ • Turn System  │ │ • Lighting      │ │ • Buttons    │   │
│  │ • Dealer AI    │ │ • Environment   │ │ • Health Bar │   │
│  │ • Item Effects │ │ • Gun/Props     │ │ • Item Slots │   │
│  │ • HP/Shells    │ │ • Collision     │ │ • Messages   │   │
│  │ • Round Config │ │   System        │ │              │   │
│  └────────────────┘ └─────────────────┘ └──────────────┘   │
│                                                               │
│         ┌──────────────────────────────────────┐            │
│         ↓                                      ↓            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ITEM_ANIMATIONS.PY                                  │   │
│  │ - 6 Item 3D animations with GLB models             │   │
│  │ - Smooth Lerp transitions                          │   │
│  │ - Per-user positioning (Player vs Dealer)          │   │
│  │ - Particle effects (sparks, smoke, flashes)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### **main.py** — Game Controller & Event Loop
- **Purpose**: Central game loop, input handling, camera control
- **Key Classes**: `BuckshotRoulette(ShowBase)`
- **Responsibilities**:
  - Initialize Panda3D engine
  - Manage camera (FOV, position, targeting)
  - Handle mouse clicks for gun picking
  - Coordinate shooting animations
  - Manage dealer AI turns
  - Synchronize game state with UI/scene updates

**Key Methods**:
- `_pick_up_gun()` / `_put_down_gun()`: Gun interaction
- `_move_gun_to_player_pose()` / `_move_gun_to_dealer_pose()`: Gun positioning for shooting
- `_gun_shoot_anim()`: Shooting animation with recoil
- `_player_shoot_self()` / `_player_shoot_opp()`: Player actions
- `_dealer_turn_task()`: Dealer AI decision-making loop
- `_camera_look_task()`: Smooth camera controls

---

#### **game_state.py** — Game Logic Engine
- **Purpose**: Manages game rules, turn system, AI, and item effects
- **Key Classes**:
  - `Shotgun`: Manages shell state (LIVE/BLANK), peeking, ejecting
  - `Actor`: Represents player or dealer with HP and items
  - `GameState`: Master game controller
  - `Enums`: `ShellType`, `ItemType`, `TurnOwner`

**Core Logic**:
- **Round Configuration** (ROUND_CONFIG): Shell counts, item allowance, max HP per round
- **Shell Management**: Random shuffle, peek, eject, invert mechanics
- **Item Mechanics**: All 6 items fully implemented with game state modifications
- **Dealer AI**: Probability-based decision system:
  - High live probability (≥0.6): Use hand saw, then shoot player
  - Guaranteed blank: Shoot self (keep turn)
  - Medium probability (0.3-0.6): Random choice
  - Low probability (≤0.3): Shoot self
  - Prioritize items: Magnifying glass > handcuffs > cigarette (low HP)

**Key Methods**:
- `shoot_self()` / `shoot_opponent()`: Process shots, handle damage/healing
- `use_item()`: Apply item effects to game state
- `dealer_ai_action()`: AI decision tree
- `check_reload()`: Auto-reload gun when empty

---

#### **scene_builder.py** — 3D Environment & Props
- **Purpose**: Load and construct the 3D game world
- **Key Classes**: `SceneBuilder`
- **Responsibilities**:
  - Load environment GLB (3D room/office model)
  - Auto-scale and axis-convert environment
  - Position game table, dealer, shotgun
  - Setup collision detection (for gun picking)
  - Configure lighting (ambient, directional, point lights)
  - Create shell indicator UI (visual representation of loaded shells)

**3D Assets Loaded**:
- `artcollection_room_with_office.glb`: Main environment
- `table.glb`: Gameplay table
- `1970_gangster_soldier.glb`: Dealer model
- `gun_m1918.glb`: Shotgun model

**Key Positioning**:
- `table_anchor = Point3(0, 1.5, 1.05)`: Table center
- `dealer_anchor = Point3(0, 4.6, 1.65)`: Dealer position
- Camera positioned at `Point3(0, -8.5, 4.0)` looking at table

---

#### **ui_manager.py** — Heads-Up Display (HUD)
- **Purpose**: Render all 2D game interface elements
- **Key Classes**: `UIManager`
- **Layout**:
  - **LEFT Panel**: Player name, HP bar, item slots, logs
  - **RIGHT Panel**: Dealer name, HP bar, item slots
  - **BOTTOM Center**: "SHOOT YOURSELF" and "SHOOT DEALER" buttons
  - **CENTER Top**: Shell counts (LIVE/BLANK remaining)
  - **CENTER**: Turn indicator and game messages

**UI Features**:
- **Colored Borders**: Custom frame system with border thickness
- **Health Bars**: Animated, color-coded (red for player, orange for dealer)
- **Item Grid**: Interactive item slots (clickable to use)
- **Shell Indicators**: Visual circles showing loaded shells (red=LIVE, blue=BLANK)
- **Message System**: Flash text showing game state ("LIVE shot!", "You're cuffed", etc.)
- **Turn Indicator**: Shows whose turn it is

**Color Palette**:
```python
C_PANEL_BG     = (0.06, 0.04, 0.09, 0.88)     # Dark purple background
C_PANEL_BORDER = (0.30, 0.26, 0.42, 0.95)    # Lighter border
C_HP_FILL      = (0.90, 0.18, 0.12, 1.0)     # Red (player)
C_HP_DEALER    = (0.92, 0.30, 0.12, 1.0)     # Orange (dealer)
C_LIVE         = (0.92, 0.16, 0.12, 1.0)     # Red (live shells)
C_BLANK        = (0.22, 0.48, 0.92, 1.0)     # Blue (blank shells)
```

---

#### **item_animations.py** — Item Visual Effects
- **Purpose**: Render smooth 3D animations for all item usage
- **Key Classes**: `ItemAnimator`
- **Features**:
  - Loads actual GLB models for each item
  - Per-user positioning (player vs dealer specific animations)
  - Uses Panda3D Lerp intervals for smooth motion
  - Particle effects (sparks, smoke flashes)
  - Auto-cleanup after animation completes

**6 Item Animations**:

1. **Magnifying Glass**
   - Floats up, examines gun
   - Glow effect pulses during examination
   - Returns after 2+ seconds

2. **Beer Can**
   - Lifts from start position
   - Tilts toward gun
   - Shell ejects with physics
   - Can discards off-screen

3. **Cigarette**
   - Lighter appears, ignites cig
   - Cigarette flies to mouth (camera front for player)
   - 8 smoke puffs burst outward with fade
   - Cigarette disappears

4. **Hand Saw**
   - Positions near gun
   - Sawing motion (back-and-forth) along barrel
   - Spark bursts on each saw stroke
   - Returns with fade-out

5. **Inverter**
   - Device rises and moves to gun
   - LED blinks through color sequence
   - Tech flash effect at climax
   - Disappears

6. **Handcuffs**
   - Rises high above origin
   - Flies toward opponent (player sees them fly to dealer, dealer sees them to player)
   - 360° spinning during flight
   - Flash effect on impact
   - Fade-out

**Animation System**:
- **Sequence**: Ordered animation steps
- **Parallel**: Simultaneous animation effects
- **LerpPosInterval**: Smooth position transitions
- **LerpHprInterval**: Smooth rotation transitions
- **LerpColorScaleInterval**: Fade in/out effects
- **Func**: Call Python functions during animation
- **Wait**: Pause between animation steps

---

## File Structure & Descriptions

```
buckshot_roulette/
├── main.py                          # Entry point; game loop controller (850+ lines)
├── game_state.py                    # Game logic, AI, item mechanics (380+ lines)
├── scene_builder.py                 # 3D environment loading and setup (400+ lines)
├── ui_manager.py                    # HUD panels, buttons, item slots (600+ lines)
├── item_animations.py               # 3D item animation sequences (620+ lines)
├── README.md                        # Original basic README
├── README_DETAILED.md               # This comprehensive guide
│
├── 3D Assets (.glb files):
│   ├── artcollection_room_with_office.glb  # Main environment (room/office)
│   ├── table.glb                           # Game table model
│   ├── gun_m1918.glb                       # Shotgun model (M1918)
│   ├── 1970_gangster_soldier.glb           # Dealer character model
│   ├── styled_magnifying_glass.glb         # Magnifying glass item
│   ├── beer_can.glb                        # Beer can item
│   ├── cigarette_-_daily3d.glb             # Cigarette item
│   ├── old_rusty_handsaw.glb               # Handsaw item
│   ├── handcuffs.glb                       # Handcuffs item
│   └── inverter.glb                        # Inverter device item
│
└── __pycache__/                     # Python bytecode cache (auto-generated)
```

---

## Detailed System Explanations

### 1. **Turn & Game State Management**

**TurnOwner Enum**:
- `PLAYER`: Player's turn (can shoot self/opponent or use item)
- `DEALER`: Dealer's turn (AI makes decisions)

**Game State Transitions**:
```
[GAME START] 
    ↓
[ROUND START - Load Shells & Items]
    ↓
[PLAYER TURN] ← Player can:
                  1. Shoot self
                  2. Shoot opponent
                  3. Use item
    ↓
[DEALER TURN] ← Dealer AI decides based on probabilities
    ↓
[CHECK WIN CONDITION]
    ├─ If player HP = 0 → DEALER WINS
    ├─ If dealer HP = 0 → PLAYER WINS
    ├─ If shells = 0 → NEXT ROUND
    └─ Otherwise → Return to PLAYER TURN
```

**Cuffed Mechanic**:
- When handcuffed, entire turn is skipped
- Message displays: "[Handcuffs] [Player] will skip their next turn!"
- On next turn entry for that player, turn passes immediately

### 2. **Dealer AI Decision Tree**

```python
if dealer_has(MAGNIFYING_GLASS):
    peek_next_shell()
    recursive_ai_call()  # AI acts again after peeking

elif dealer_has(HANDCUFFS) and not player_cuffed:
    use_handcuffs()
    player_skips_next_turn()

elif player_hp == 1 and dealer_has(CIGARETTE):
    use_cigarette()
    dealer_hp += 1

elif shell_count == 0:
    return "Dealer waits — gun empty"

else:
    live_prob = live_count / total_shells
    
    if live_prob >= 0.6:              # High danger
        if dealer_has(HANDSAW):
            use_handsaw()              # Next shot = 2x damage
        shoot_player()
    
    elif live_count == 0:             # Guaranteed blank
        shoot_self()                   # Keep turn alive
    
    elif live_prob <= 0.3:            # Low danger
        shoot_self()                   # Play safe
    
    else:                              # Medium probability
        random_choice(shoot_self, shoot_player)
```

### 3. **Gun Animation System**

**Gun State Machine**:
```
[GUN ON TABLE]
    ↓
[PLAYER CLICKS GUN] → runs _pick_up_gun()
    ↓
[GUN HELD BY CAMERA]
    ├─ Shows near camera front
    ├─ Can rotate with mouse
    └─ Camera tracks gun position
    ↓
[PLAYER AIMS AT TARGET]
    ├─ Gun aims at face (self-shoot)
    └─ Gun aims at player/dealer (opponent-shoot)
    ↓
[PLAYER CLICKS FIRE BUTTON]
    ├─ Shooting animation: Gun jerks back (recoil)
    ├─ Spark effects
    └─ Shell is consumed
    ↓
[GUN RETURNED TO TABLE] → runs _put_down_gun()
    ↓
[GUN ON TABLE AGAIN]
```

**Gun Positioning Details**:

- **For Player Shooting Self** (`_move_gun_to_player_self_pose`):
  - Position: 1.50 units forward from camera, 0.40 right, 0.45 down
  - Rotation: Special handling so gun doesn't rotate weirdly
  - Scale: 0.74× normal size (smaller, closer feel)
  - Duration: 0.72 seconds
  - **Nozzle Point**: Flipped 180° so muzzle points at camera correctly

- **For Dealer Shooting Self** (`_move_gun_to_dealer_pose` with `is_self=True`):
  - Position: Below dealer face (1.65 units down from face point)
  - Rotation: Same flip as player (handle down, nozzle up)
  - Dealer holds gun at own face level
  - Duration: 0.50 seconds

- **For Shooting Opponent** (`_move_gun_to_player_pose`):
  - Position: 1.05 units forward from gun, 0.18 right, 0.14 down
  - Scale: 0.86× normal size
  - Duration: 0.62 seconds
  - Aimed at target's face

**Gun Aim System** (`_gun_aim_hpr`):
- Uses `lookAt()` to point gun barrel at target
- Model-specific rotation fixes:
  - `setH() + 180`: Rotate heading
  - `setP() + 90`: Rotate pitch
  - Conditional roll adjustments based on holder type
- Result: Natural gun orientation regardless of initial model axis

### 4. **Item Mechanics in Depth**

#### **Magnifying Glass**
- **Effect**: Reveal next shell without consuming it
- **Game Logic**: `shotgun.peek()` returns next shell
- **UI**: Message: "[Magnifying Glass] Next shell is: LIVE/BLANK"
- **Animation**: Lens examines gun with glowing effect
- **Dealer AI**: Uses immediately if has (high priority)

#### **Beer**
- **Effect**: Eject one shell (removes from gun permanently)
- **Game Logic**: `shotgun.eject()` pops and returns shell
- **UI**: Message: "[Beer] Ejected a LIVE/BLANK shell — gone!"
- **Side Effect**: Auto-reload triggered if all shells ejected
- **Animation**: Can lifts, shell launches, can discards

#### **Cigarette**
- **Effect**: Heal 1 HP (up to max HP)
- **Game Logic**: `actor.heal(1)` increases HP, capped at max
- **UI**: Message: "[Cigarette] [Actor] healed to X/Y HP"
- **Animation**: Lighter ignites cigarette at mouth, smoke puffs
- **Dealer AI**: Uses if at 1 HP and has cigarettes

#### **Hand Saw**
- **Effect**: Next shot deals 2× damage (DOUBLE)
- **Game Logic**: `shotgun.sawed = True` flag set
- **Mechanics**: On next shot, damage is multiplied by 2 instead of 1
- **UI**: Message: "[Hand Saw] Next shot deals DOUBLE damage!"
- **Animation**: Saw oscillates along barrel with sparks
- **Dealer AI**: Uses before shooting when live probability is high

#### **Inverter**
- **Effect**: Flip next shell (LIVE becomes BLANK, BLANK becomes LIVE)
- **Game Logic**: `shotgun.invert_next()` reverses next shell polarity
- **UI**: Message: "[Inverter] Next shell type has been flipped!"
- **Animation**: Device moves to gun, LED blinks colors, tech flash
- **Dealer AI**: Rare use (not prioritized in current AI)

#### **Handcuffs**
- **Effect**: Handcuff opponent (they skip next turn)
- **Game Logic**: `opponent.cuffed = True` flag set
- **Next Turn**: When cuffed player's turn comes, it immediately skips
- **UI**: Message: "[Handcuffs] [Opponent] will skip their next turn!"
- **Animation**: Handcuffs fly from user toward opponent
- **Dealer AI**: Uses if player not already cuffed and high live probability

### 5. **Camera System**

**Camera Setup** (`_setup_camera`):
- Position: `Point3(0, -6.5, 2.8)` (behind and above table)
- Look-At: `Point3(0, 1.5, 1.4)` (table center)
- FOV: 65° (wide but not distorted; balanced for 3D gameplay)
- Mouse Control: Disabled by default (`disableMouse()`)

**Camera Look Task** (`_camera_look_task`):
- Tracks mouse movement for aim refinement
- Stores yaw/pitch for gun aim calculation
- Mouse sensitivity: 70 units per degree
- Smooth camera following during gun-holding

**Gun-Relative Camera**:
- When gun is held, camera position adjusts ahead of table center
- Gun position is calculated relative to camera's forward vector
- This creates "first-person-like" feel without hiding screen

### 6. **Collision & Picking System**

**Collision Ray Setup** (`_setup_picker`):
- Ray origin: Camera position
- Ray direction: Forward vector from camera
- Collision node: Checks against gun model bounds
- Handler queues: Returns list of intersecting objects

**Gun Picking Mechanics** (`_on_mouse_click`):
1. Cast collision ray from camera through mouse click point
2. If ray hits gun: `_pick_up_gun()` executes
3. Gun now follows player's aiming direction
4. If click on action button: Fire or use item instead

### 7. **Round & Difficulty Progression**

**3-Round Campaign**:

| Round | Live | Blank | Max Items | Max HP |
|-------|------|-------|-----------|---------|
| 1     | 2    | 3     | 2 per person | 3       |
| 2     | 3    | 3     | 3 per person | 4       |
| 3     | 4    | 4     | 4 per person | 5       |

**Per-Round Sequence**:
1. Load shotgun with configured shell count (randomized)
2. Deal items to each player (randomized from available pool)
3. Reset HP to max
4. Clear cuffed state
5. Player turn starts
6. Gameplay loop runs until shells empty or player/dealer dies
7. If both alive and shells empty: Execute reload and repeat
8. If either dies: End round, check if 3 rounds complete
9. If 3 rounds complete: Game over (check who won overall)

### 8. **Animation System (Lerps & Sequences)**

**Panda3D Interval System**:
- **Lerp**: Linear interpolation animation over time
- **Sequence**: Play animations in order (one after another)
- **Parallel**: Play animations simultaneously

**Example: Beer Animation**
```python
Sequence(
    # Lift beer from table
    LerpPosInterval(beer, 0.35, lift_pos, blendType="easeOut"),
    
    # Tilt toward gun (position + rotation parallel)
    Parallel(
        LerpPosInterval(beer, 0.45, gun_pos, blendType="easeInOut"),
        LerpHprInterval(beer, 0.45, rotated_hpr, blendType="easeInOut"),
    ),
    
    # Shell ejects
    Func(lambda: shell.setColorScale(1,1,1,1)),  # Make shell visible
    Parallel(
        LerpPosInterval(shell, 0.4, eject_pos, blendType="easeIn"),
        LerpHprInterval(shell, 0.4, spin_hpr),
    ),
    
    # Wait and discard
    Wait(0.2),
    Parallel(
        LerpPosInterval(beer, 0.35, discard_pos, blendType="easeIn"),
        LerpColorScaleInterval(beer, 0.35, Vec4(1,1,1,0)),  # Fade out
        LerpColorScaleInterval(shell, 0.35, Vec4(1,1,1,0)),
    ),
    
    # Cleanup callback
    Func(self._done, callback),
)
```

---

## Detailed Workflow Examples

### Example 1: Player Uses Magnifying Glass

**User Action**: Click on Magnifying Glass item in left panel  
**Code Flow**:
```
UIManager.on_item_used() 
    ↓
main.py: _player_use_item(ItemType.MAGNIFYING_GLASS)
    ↓
ItemAnimator.play(MAGNIFYING_GLASS, user="player", on_complete=_apply_item_effect)
    ↓
[Animation plays: Magnifier floats, examines gun, glows, returns]
    ↓
_apply_item_effect(ItemType.MAGNIFYING_GLASS)
    ↓
GameState.use_item(MAGNIFYING_GLASS)
    ↓
msg = "[Magnifying Glass] Next shell is: LIVE"
    ↓
UIManager.flash_message(msg, duration=2.0)
    ↓
[UI shows green LIVE indicator in message area]
    ↓
Turn passes to dealer
```

### Example 2: Dealer Shoots Player

**Dealer Turn Triggered**: `_dealer_turn_task()` scheduled  
**Code Flow**:
```
_dealer_turn_task()
    ↓
GameState.dealer_ai_action()
    ├─ Check: Has magnifying glass? NO
    ├─ Check: Has handcuffs and player not cuffed? NO
    ├─ Check: Low HP and has cigarette? NO
    ├─ Calculate: live_prob = 2/5 = 0.4
    ├─ Decision: 0.3 < 0.4 < 0.6 → Moderate probability
    └─ Action: Randomly choose (let's say) shoot_opponent()
    ↓
_move_gun_to_dealer_pose(player_face_point, is_self=False)
    ├─ Position gun below dealer face
    ├─ Aim at player's face (player's camera position)
    └─ Animation duration: 0.50s
    ↓
_gun_shoot_anim(target_pos, after_gun_callback)
    ├─ Gun recoils backward
    ├─ Spark effects fire
    └─ Animation duration: 0.25s
    ↓
after_gun callback executes:
    ├─ Check result: shotgun.fire() → returns LIVE
    ├─ Player is HIT
    ├─ Damage: 1 HP (hand saw not used)
    ├─ Player HP: 3 → 2
    └─ _player_hit_anim() plays (white flash, red vignette)
    ↓
_finish_dealer_turn()
    ├─ Rebuild shell indicators (1 remaining: BLANK)
    ├─ Update UI (health bars, shell count)
    ├─ Flash message: "[LIVE] Dealer shot You! -1 HP"
    └─ Schedule next turn or declare winner
    ↓
Turn back to PLAYER
```

### Example 3: Player Shoots Self & Gets BLANK (Keeps Turn)

**User Action**: Click "SHOOT YOURSELF"  
**Code Flow**:
```
UIManager: on_shoot_self clicked
    ↓
main.py: _player_shoot_self()
    ↓
_move_gun_to_player_self_pose()
    ├─ Position gun 2.80 units forward from camera
    ├─ Rotate so nozzle points at camera (hand down, nozzle up)
    └─ Animation: 0.72s
    ↓
[Player sees gun fly up in front of their face]
    ↓
_gun_shoot_anim(aim_point_player, after_gun)
    ├─ Gun recoils slightly back
    ├─ Spark particle effects
    └─ Animation: 0.25s
    ↓
after_gun callback:
    ├─ Check result: shotgun.fire() → returns BLANK
    ├─ Player NOT hit (0 damage)
    ├─ Player keeps turn (turn remains PLAYER)
    ├─ No damage animation needed
    └─ _finish_player_turn()
    ↓
_finish_player_turn():
    ├─ Rebuild shells (4 remaining: 2 LIVE, 2 BLANK)
    ├─ Update UI
    ├─ Flash message: "[BLANK] You're safe!"
    ├─ Turn still PLAYER (player gets another action)
    └─ Buttons re-enable for next action
    ↓
[Player can shoot again, use item, or pass turn]
```

---

## Technical Details & Dependencies

### External Libraries

```python
# Panda3D (3D Graphics Engine)
from direct.showbase.ShowBase import ShowBase          # Main game loop
from direct.task import Task                           # Task scheduling
from direct.interval.IntervalGlobal import *           # Animation system
from direct.gui.DirectGui import *                     # UI system
from panda3d.core import *                             # Core 3D engine

# Standard Python
import math, random                                     # Math utilities
import sys                                              # System interface
```

### Key Panda3D Components Used

| Component | Purpose |
|-----------|---------|
| `ShowBase` | Main game engine initialization |
| `NodePath` | 3D object wrapper/management |
| `Point3, Vec3, Vec4` | Vector math types |
| `LerpPosInterval` | Position animation |
| `LerpHprInterval` | Rotation animation |
| `Sequence/Parallel` | Animation composition |
| `CollisionRay/Traverser` | Ray-casting for picking |
| `DirectButton/DirectFrame` | UI widgets |
| `TransparencyAttrib` | Alpha blending for UI |
| `LColor` | Color type |

### Python Version Requirements
- **Python 3.8+** (3.10+ recommended)
- **Panda3D 1.10.14+**

### Installation & Running

```bash
# Install Panda3D (one-time)
pip install panda3d

# Navigate to project directory
cd buckshot_roulette

# Run the game
python main.py

# Controls:
# - ESC: Exit game
# - R: Restart game (new campaign)
# - Mouse Move: Look around / Aim gun
# - Mouse Click: Pick up gun (or trigger action with button active)
# - UI Buttons: Shoot Self / Shoot Dealer / Use Items
```

---

## Game Assets (3D Models)

### Environment
- **artcollection_room_with_office.glb** (Main Environment)
  - Custom office/room setting
  - Loaded Y-up, rotated +90° to Z-up for Panda3D
  - Auto-scaled to 18-unit world scale
  - Provides immersive atmosphere

### Character & Props
- **1970_gangster_soldier.glb** (Dealer Model)
  - Positioned at `Point3(0, 4.6, 1.65)` 
  - Dealer character model
  - Anchored for camera positioning

- **table.glb** (Game Table)
  - Positioned at `Point3(0, 1.5, 1.05)`
  - Central gameplay surface
  - Gun spawns/rests here

- **gun_m1918.glb** (Shotgun)
  - Interactive 3D shotgun model
  - Pickable (collision detection)
  - Animatable (smooth Lerps)
  - ~0.5 unit scale on table

### Item Models
- **styled_magnifying_glass.glb** (Magnifying Glass)
  - 1.4-unit target size
  - Glowing effects during use
  - Lens examines gun

- **beer_can.glb** (Beer Can)
  - 1.3-unit target size
  - Shell ejection animation
  - Physics-like projectile

- **cigarette_-_daily3d.glb** (Cigarette)
  - 1.2-unit target size
  - Lighter ignition animation
  - Smoke puff effects

- **old_rusty_handsaw.glb** (Hand Saw)
  - 1.8-unit target size
  - Sawing motion along barrel
  - Spark burst effects

- **handcuffs.glb** (Handcuffs)
  - 2.0-unit target size
  - Flight animation toward opponent
  - 360° spin rotations

- **inverter.glb** (Inverter Device)
  - 1.0-unit target size
  - LED color sequence
  - Tech flash effects

---

## Gameplay Statistics & Balance

### Probability Analysis (Round 1)

**Shell Distribution**: 2 LIVE, 3 BLANK

**Shoot Self Survival Rates**:
- 1st shot: 60% safe (3/5 BLANK)
- Keep shooting self: Expected turns until LIVE ≈ 1.67

**Dealer Decision Impact**:
- If shooting opponent with 40% LIVE probability:
  - Expected damage per turn: 0.4 HP
  - Time to kill player (3 HP): ~7.5 turns average

**Item Economy**:
- Each player gets ~2 items per round (6 total across both)
- Strategic item timing crucial (hand saw vs early magnifying glass)

### Difficulty Ramping

**Round 1** (Easiest):
- 40% shells are LIVE (relatively safe)
- Few items (2 per person)
- Low max HP (3) = quick rounds but forgiving

**Round 2** (Medium):
- 50% shells are LIVE (equal danger)
- More items (3 per person)
- Higher max HP (4)

**Round 3** (Hardest):
- 50% shells still, but cumulative danger
- Most items (4 per person)
- Highest max HP (5) = longer endurance

---

## Known Behaviors & Edge Cases

### Animation Sequencing
- **Gun animation blocking**: While gun is animating, player cannot interact
- **Item animation blocking**: While item animates, no new items can be used
- **Dealer thinking flag**: Prevents concurrent dealer turns

### State Consistency
- **Shell count**: Must always match physical count in game logic
- **Item removal**: Happens immediately after use (GameState side)
- **HP clamping**: Always kept within 0 to max_hp range
- **Turn management**: Strict alternation with special cuffs handling

### Physics-Free Design
- All animations use Lerp (linear interpolation) — deterministic
- No actual physics simulation (shells don't have gravity)
- Collision only used for gun picking (ray-cast based)
- Shooting is instant (no bullet travel time)

---

## Customization & Extension Points

### Change Game Difficulty
Edit `game_state.py` ROUND_CONFIG:
```python
ROUND_CONFIG = [
    (live_count, blank_count, max_items, max_hp),
    ...
]
```

### Modify Dealer AI
Edit `GameState.dealer_ai_action()` method in `game_state.py` to change probabilities or logic.

### Add New Items
1. Add to `ItemType` enum in `game_state.py`
2. Implement game logic in `GameState.use_item()`
3. Create 3D animation in `item_animations.py`
4. Add button in `ui_manager.py`

### Adjust Camera/UI
- **FOV**: Edit `self.camLens.setFov(65)` in `main.py`
- **UI Scale**: Edit `PANEL_W`, `PANEL_PAD` constants in `ui_manager.py`
- **Colors**: Modify `C_*` constants in `ui_manager.py`

### Change Animation Speed
Edit duration parameters in `item_animations.py`:
```python
LerpPosInterval(obj, 0.35, target_pos)  # 0.35 seconds
```

---

## Architecture Patterns Used

1. **Model-View-Controller (MVC)**
   - **Model**: `GameState` (pure game logic)
   - **View**: `UIManager` (2D) + `SceneBuilder` (3D)
   - **Controller**: `main.py` (orchestrates input → game logic → output)

2. **Observer Pattern**
   - UI buttons "observe" for user clicks
   - Callbacks trigger game state changes
   - State changes trigger UI updates

3. **State Machine**
   - Turn system uses enum-based states
   - Game phases (turn, animation, wait)
   - Clear state transitions with guards

4. **Component Pattern**
   - `ItemAnimator` component handles all item visuals
   - Decoupled from game logic
   - Reusable for both player and dealer

5. **Task-Based Scheduling**
   - Long-running operations (dealer thinking) use task scheduler
   - Non-blocking game loop
   - Natural async behavior without coroutines

---

## Performance Considerations

- **3D Rendering**: ~60 FPS on modern hardware (Panda3D optimized)
- **Animation Count**: Max 6 simultaneous Lerps (items + gun)
- **Collision**: Single ray-cast per mouse click (negligible cost)
- **UI**: ~50 widgets total (2D, minimal overhead)
- **Memory**: ~150-200 MB typical (3D models + textures)

---

## Future Enhancement Ideas

1. **Multiplayer**: Network support for two players
2. **Audio**: Sound effects for shots, item usage, UI clicks
3. **Particles**: Advanced visual effects system
4. **Advanced AI**: Difficulty levels, learning player patterns
5. **Statistics**: Track win rate, favorite items, play time
6. **Modding**: Item and model configuration files
7. **Mobile**: Touch input adaptation
8. **VR Support**: Panda3D-to-OpenXR integration

---

## Debugging & Common Issues

**Issue**: Gun not pickable
- **Cause**: Collision traverser not running
- **Fix**: Ensure `_setup_picker()` completes before scene builds

**Issue**: Animations stutter
- **Cause**: Blocking AI task running on main thread
- **Fix**: Use `taskMgr.doMethodLater()` to schedule asynchronously

**Issue**: UI buttons not visible
- **Cause**: Z-ordering (sortOrder) conflicts
- **Fix**: Check `sortOrder` values in `ui_manager.py`

**Issue**: Dealer never shoots
- **Cause**: `dealer_ai_action()` never called or turn not set to DEALER
- **Fix**: Verify `_finish_player_turn()` schedules dealer task

---

## Conclusion

This Buckshot Roulette implementation demonstrates a complete integration of:
- **3D Graphics** (Panda3D scene management)
- **Game Logic** (Turn systems, AI, item mechanics)
- **Animation** (Smooth Lerp-based sequencing)
- **UI/UX** (Information display and interaction)
- **State Management** (Game phases, player states, dealer logic)

The modular architecture allows easy extension and modification while maintaining code clarity and separation of concerns. Each component (game logic, rendering, animation, UI) can be updated independently without affecting others.

**Total Lines of Code**: ~2,500+ (including documentation)  
**Development Complexity**: Medium (good for learning game development)  
**Scalability**: Foundation for larger games (networking, advanced graphics, etc.)

---

**Last Updated**: March 14, 2026  
**Version**: 1.0 (Full Implementation)  
**Status**: Fully Playable 3-Round Campaign
