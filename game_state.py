"""
game_state.py — Core game logic, shell system, items, health, and turn management.
"""

import random
from enum import Enum, auto


class ShellType(Enum):
    LIVE = "LIVE"
    BLANK = "BLANK"


class ItemType(Enum):
    MAGNIFYING_GLASS = "Magnifying Glass"
    BEER = "Beer"
    CIGARETTE = "Cigarette Pack"
    HANDSAW = "Hand Saw"
    INVERTER = "Inverter"
    HANDCUFFS = "Handcuffs"


class TurnOwner(Enum):
    PLAYER = auto()
    DEALER = auto()


# ──────────────────────────────────────────
# Round difficulty table
# ──────────────────────────────────────────
ROUND_CONFIG = [
    # (live, blank, items_per_player, max_hp)
    (2, 3, 2, 3),   # Round 1
    (3, 3, 3, 4),   # Round 2
    (4, 4, 4, 5),   # Round 3
]


# ──────────────────────────────────────────
class Shotgun:
    def __init__(self):
        self.shells: list[ShellType] = []
        self.sawed = False          # Hand Saw active

    def load(self, live: int, blank: int):
        self.shells = [ShellType.LIVE] * live + [ShellType.BLANK] * blank
        random.shuffle(self.shells)
        self.sawed = False

    def peek(self) -> ShellType | None:
        """Magnifying Glass — look at next shell without removing."""
        return self.shells[0] if self.shells else None

    def eject(self) -> ShellType | None:
        """Beer — remove next shell without firing."""
        return self.shells.pop(0) if self.shells else None

    def fire(self) -> tuple[ShellType | None, int]:
        """
        Fire the gun.
        Returns (shell_type, damage).
        damage is 2 if sawed, else 1 (only for live shells).
        """
        if not self.shells:
            return None, 0
        shell = self.shells.pop(0)
        damage = 0
        if shell == ShellType.LIVE:
            damage = 2 if self.sawed else 1
        self.sawed = False          # saw resets after each shot
        return shell, damage

    def invert_next(self):
        """Inverter — flip first shell type."""
        if self.shells:
            self.shells[0] = (
                ShellType.BLANK
                if self.shells[0] == ShellType.LIVE
                else ShellType.LIVE
            )

    @property
    def live_count(self) -> int:
        return self.shells.count(ShellType.LIVE)

    @property
    def blank_count(self) -> int:
        return self.shells.count(ShellType.BLANK)

    @property
    def is_empty(self) -> bool:
        return len(self.shells) == 0


# ──────────────────────────────────────────
class Player:
    def __init__(self, name: str, max_hp: int):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.items: list[ItemType] = []
        self.cuffed = False         # handcuffs applied

    def take_damage(self, amount: int):
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: int = 1):
        self.hp = min(self.max_hp, self.hp + amount)

    def is_alive(self) -> bool:
        return self.hp > 0

    def add_item(self, item: ItemType):
        self.items.append(item)

    def remove_item(self, item: ItemType) -> bool:
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def has_item(self, item: ItemType) -> bool:
        return item in self.items


ALL_ITEMS = list(ItemType)


def give_random_items(player: Player, count: int):
    for _ in range(count):
        player.add_item(random.choice(ALL_ITEMS))


# ──────────────────────────────────────────
class GameState:

    def __init__(self):
        self.round_index = 0
        self.shotgun = Shotgun()
        self.player: Player | None = None
        self.dealer: Player | None = None
        self.turn: TurnOwner = TurnOwner.PLAYER
        self.message_log: list[str] = []
        self.game_over = False
        self.winner: str | None = None
        self._setup_round()

    def _setup_round(self):
        cfg = ROUND_CONFIG[min(self.round_index, len(ROUND_CONFIG) - 1)]
        live, blank, items_count, max_hp = cfg

        if self.player is None:
            self.player = Player("Player", max_hp)
        else:
            self.player.max_hp = max_hp
            if self.player.hp > max_hp:
                self.player.hp = max_hp

        if self.dealer is None:
            self.dealer = Player("Dealer", max_hp)
        else:
            self.dealer.max_hp = max_hp
            if self.dealer.hp > max_hp:
                self.dealer.hp = max_hp

        self.shotgun.load(live, blank)
        give_random_items(self.player, items_count)
        give_random_items(self.dealer, items_count)
        self.turn = TurnOwner.PLAYER
        self.log(
            f"=== Round {self.round_index + 1} ===  "
            f"Loaded: {live} Live + {blank} Blank shells."
        )

    def log(self, msg: str):
        self.message_log.append(msg)
        if len(self.message_log) > 10:
            self.message_log.pop(0)

    def current_actor(self) -> Player:
        return self.player if self.turn == TurnOwner.PLAYER else self.dealer

    def other_actor(self) -> Player:
        return self.dealer if self.turn == TurnOwner.PLAYER else self.player

    def _end_turn(self, keep_turn: bool = False):
        """Advance to next turn unless keep_turn is True."""
        if keep_turn:
            return

        next_owner = (
            TurnOwner.DEALER if self.turn == TurnOwner.PLAYER else TurnOwner.PLAYER
        )
        next_player = (
            self.dealer if next_owner == TurnOwner.DEALER else self.player
        )
        if next_player.cuffed:
            next_player.cuffed = False
            self.log(f"{next_player.name} is cuffed — turn skipped!")

        else:
            self.turn = next_owner

    def _check_end_conditions(self) -> bool:
        if not self.player.is_alive():
            self.game_over = True
            self.winner = "Dealer"
            self.log("Player is dead! Dealer wins!")
            return True
        if not self.dealer.is_alive():
            self.game_over = True
            self.winner = "Player"
            self.log("Dealer is dead! Player wins!")
            return True
        return False

    def _check_reload(self):
        if self.shotgun.is_empty and not self.game_over:
            self.round_index += 1
            self._setup_round()


    def use_item(self, item: ItemType) -> str:
        actor = self.current_actor()
        if not actor.has_item(item):
            return f"{actor.name} does not have {item.value}."

        msg = ""
        if item == ItemType.MAGNIFYING_GLASS:
            nxt = self.shotgun.peek()
            if nxt:
                msg = f"[Magnifying Glass] Next shell is: {nxt.value}"
            else:
                msg = "[Magnifying Glass] Gun is empty!"
            actor.remove_item(item)

        elif item == ItemType.BEER:
            ejected = self.shotgun.eject()
            if ejected:
                msg = f"[Beer] Ejected a {ejected.value} shell — gone!"
            else:
                msg = "[Beer] Gun was already empty."
            actor.remove_item(item)
            self._check_reload()

        elif item == ItemType.CIGARETTE:
            actor.heal(1)
            msg = f"[Cigarette] {actor.name} healed to {actor.hp}/{actor.max_hp} HP."
            actor.remove_item(item)

        elif item == ItemType.HANDSAW:
            self.shotgun.sawed = True
            msg = "[Hand Saw] Next shot deals DOUBLE damage!"
            actor.remove_item(item)

        elif item == ItemType.INVERTER:
            self.shotgun.invert_next()
            msg = "[Inverter] Next shell type has been flipped!"
            actor.remove_item(item)

        elif item == ItemType.HANDCUFFS:
            other = self.other_actor()
            other.cuffed = True
            msg = f"[Handcuffs] {other.name} will skip their next turn!"
            actor.remove_item(item)

        self.log(msg)
        return msg

    def shoot_self(self) -> str:
        actor = self.current_actor()
        shell, damage = self.shotgun.fire()
        if shell is None:
            self.log("Gun is empty!")
            return "Gun is empty!"
        if shell == ShellType.BLANK:
            msg = f"{actor.name} shot themselves — BLANK. No damage. Keep turn."
            self.log(msg)
            # blank self-shot keeps the turn
            self._check_reload()
            return msg
        else:
            actor.take_damage(damage)
            msg = (
                f"{actor.name} shot themselves — LIVE! "
                f"-{damage} HP  (now {actor.hp}/{actor.max_hp})"
            )
            self.log(msg)
            if not self._check_end_conditions():
                self._end_turn()
                self._check_reload()
            return msg

    def shoot_opponent(self) -> str:
        actor = self.current_actor()
        target = self.other_actor()
        shell, damage = self.shotgun.fire()
        if shell is None:
            self.log("Gun is empty!")
            return "Gun is empty!"
        if shell == ShellType.BLANK:
            msg = f"{actor.name} shot {target.name} — BLANK. No damage."
            self.log(msg)
            self._end_turn()
            self._check_reload()
            return msg
        else:
            target.take_damage(damage)
            msg = (
                f"{actor.name} shot {target.name} — LIVE! "
                f"-{damage} HP  ({target.name} now {target.hp}/{target.max_hp})"
            )
            self.log(msg)
            if not self._check_end_conditions():
                self._end_turn()
                self._check_reload()
            return msg

    # ── Dealer AI ──────────────────────────
    def dealer_ai_action(self) -> str:
        """
        Simple probability-based dealer AI.
        Returns a descriptive string of what the dealer did.
        """
        gun = self.shotgun
        dealer = self.dealer
        player = self.player

        # 1. Try to use valuable items first
        if dealer.has_item(ItemType.MAGNIFYING_GLASS):
            result = self.use_item(ItemType.MAGNIFYING_GLASS)
            # After peeking, dealer will act on next recursive call
            return result

        if dealer.has_item(ItemType.HANDCUFFS) and not player.cuffed:
            result = self.use_item(ItemType.HANDCUFFS)
            return result

        if dealer.hp == 1 and dealer.has_item(ItemType.CIGARETTE):
            result = self.use_item(ItemType.CIGARETTE)
            return result

        total = len(gun.shells)
        if total == 0:
            return "Dealer waits — gun empty."

        live_prob = gun.live_count / total

        # 2. If high live probability — use handsaw then shoot player
        if live_prob >= 0.6:
            if dealer.has_item(ItemType.HANDSAW):
                return self.use_item(ItemType.HANDSAW)
            return self.shoot_opponent()

        # 3. Next shell definitely blank → shoot self (keep turn)
        if gun.live_count == 0:
            return self.shoot_self()

        # 4. If blank guaranteed → shoot self; else shoot player
        if live_prob <= 0.3:
            return self.shoot_self()

        return self.shoot_opponent()
