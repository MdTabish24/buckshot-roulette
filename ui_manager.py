"""
ui_manager.py — HUD layout matching the game's panel-based design.

LEFT  panel :  Player Name ▸ Player Health ▸ Current Logs ▸ ITEMS title ▸ item slots
RIGHT panel :  Dealer Name ▸ Dealer Health ▸ DEALER'S ITEMS title ▸ item slots
BOTTOM      :  SHOOT YOURSELF · SHOOT DEALER
"""

from direct.gui.DirectGui import (
    DirectButton, DirectFrame, DirectLabel,
)
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, Vec4, LColor, TransparencyAttrib
from game_state import ItemType, TurnOwner


# ────────────────────────────────────────────────────────────────────────────
# Colour palette
# ────────────────────────────────────────────────────────────────────────────
C_PANEL_BG     = (0.06, 0.04, 0.09, 0.88)
C_PANEL_BORDER = (0.30, 0.26, 0.42, 0.95)
C_SLOT_BG      = (0.10, 0.07, 0.14, 0.90)
C_SLOT_BORDER  = (0.40, 0.34, 0.55, 0.85)
C_HP_FILL      = (0.90, 0.18, 0.12, 1.0)
C_HP_BG        = (0.25, 0.10, 0.10, 1.0)
C_HP_DEALER    = (0.92, 0.30, 0.12, 1.0)
C_BTN_BG       = (0.12, 0.09, 0.18, 1.0)
C_BTN_BORDER   = (0.45, 0.38, 0.60, 0.95)
C_TEXT         = (0.95, 0.92, 0.82, 1.0)
C_TEXT_DIM     = (0.62, 0.58, 0.52, 1.0)
C_TITLE        = (0.98, 0.70, 0.18, 1.0)
C_WARN         = (0.98, 0.32, 0.12, 1.0)
C_LIVE         = (0.92, 0.16, 0.12, 1.0)
C_BLANK        = (0.22, 0.48, 0.92, 1.0)
C_LOG_TEXT     = (0.82, 0.78, 0.70, 1.0)

# Layout constants — MUCH BIGGER
PANEL_W   = 0.72            # panel width (was 0.48)
PANEL_PAD = 0.035           # inner padding
MAX_ITEMS = 8
BORDER_W  = 0.012           # border thickness


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def _bordered_frame(parent, x, y, w, h, bg=None, border=None, bw=BORDER_W):
    """Two overlapping frames → faux-border look."""
    bg = bg or C_PANEL_BG
    border = border or C_PANEL_BORDER
    outer = DirectFrame(
        parent=parent,
        frameSize=(0, w, -h, 0),
        frameColor=border,
        pos=(x, 0, y),
    )
    outer.setTransparency(TransparencyAttrib.M_alpha)
    inner = DirectFrame(
        parent=outer,
        frameSize=(bw, w - bw, -(h - bw), -bw),
        frameColor=bg,
        pos=(0, 0, 0),
    )
    inner.setTransparency(TransparencyAttrib.M_alpha)
    return outer, inner


# ────────────────────────────────────────────────────────────────────────────
class UIManager:
    """Owns all 2D GUI widgets. Call update(state) each frame/action."""

    def __init__(self, base, on_shoot_self, on_shoot_opp, on_item_used):
        self.base = base
        self._on_shoot_self = on_shoot_self
        self._on_shoot_opp  = on_shoot_opp
        self._on_item_used  = on_item_used
        self._player_item_labels: list[OnscreenText] = []
        self._player_item_frames: list[DirectFrame] = []
        self._dealer_item_labels: list[OnscreenText] = []
        self._dealer_item_frames: list[DirectFrame] = []
        self._log_labels: list[OnscreenText] = []
        self._item_click_btns: list[DirectButton] = []

        self._build_hud()

    # ══════════════════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════════════════
    def _build_hud(self):
        a2d = self.base.aspect2d

        pw = PANEL_W
        pad = PANEL_PAD
        inner_w = pw - 2 * pad

        # ╔══════════════════════════════════════════════════════╗
        # ║  LEFT PANEL — Player side                           ║
        # ╚══════════════════════════════════════════════════════╝
        lp_x = -1.78
        lp_top = 0.98
        lp_h = 1.96

        self.left_panel_outer, _ = _bordered_frame(
            a2d, lp_x, lp_top, pw, lp_h,
        )

        cy = -pad   # cursor Y inside panel (top-down)

        # ── PLAYER NAME ──────────────────────────────────────────
        name_h = 0.09
        _bordered_frame(
            self.left_panel_outer, pad, cy, inner_w, name_h,
            bg=C_SLOT_BG, border=C_SLOT_BORDER,
        )
        self.player_name_label = OnscreenText(
            parent=self.left_panel_outer,
            text="PLAYER",
            pos=(pad + 0.04, cy - name_h * 0.65),
            scale=0.052,
            fg=C_TEXT, align=TextNode.ALeft, mayChange=True,
        )
        cy -= name_h + 0.03

        # ── PLAYER HEALTH ────────────────────────────────────────
        hp_h = 0.10
        _bordered_frame(
            self.left_panel_outer, pad, cy, inner_w, hp_h,
            bg=C_SLOT_BG, border=C_SLOT_BORDER,
        )
        bar_inset = 0.015
        bar_w = inner_w - 2 * bar_inset
        self.player_hp_bar_bg = DirectFrame(
            parent=self.left_panel_outer,
            frameSize=(0, bar_w, 0, 0.045),
            frameColor=C_HP_BG,
            pos=(pad + bar_inset, 0, cy - hp_h + bar_inset + 0.005),
        )
        self.player_hp_bar = DirectFrame(
            parent=self.left_panel_outer,
            frameSize=(0, bar_w, 0, 0.045),
            frameColor=C_HP_FILL,
            pos=(pad + bar_inset, 0, cy - hp_h + bar_inset + 0.005),
        )
        self.player_hp_text = OnscreenText(
            parent=self.left_panel_outer,
            text="HP: 3 / 3",
            pos=(pad + 0.04, cy - 0.042),
            scale=0.042,
            fg=C_TEXT, align=TextNode.ALeft, mayChange=True,
        )
        self._hp_bar_full_w = bar_w
        cy -= hp_h + 0.03

        # ── CURRENT LOGS ─────────────────────────────────────────
        log_h = 0.32
        _bordered_frame(
            self.left_panel_outer, pad, cy, inner_w, log_h,
            bg=C_SLOT_BG, border=C_SLOT_BORDER,
        )
        self.log_title = OnscreenText(
            parent=self.left_panel_outer,
            text="CURRENT LOGS",
            pos=(pad + 0.04, cy - 0.042),
            scale=0.040,
            fg=C_TITLE, align=TextNode.ALeft, mayChange=True,
        )
        for i in range(5):
            lbl = OnscreenText(
                parent=self.left_panel_outer,
                text="",
                pos=(pad + 0.04, cy - 0.088 - i * 0.048),
                scale=0.034,
                fg=C_LOG_TEXT, align=TextNode.ALeft, mayChange=True,
                wordwrap=18,
            )
            self._log_labels.append(lbl)
        cy -= log_h + 0.03

        # ── ITEMS TITLE ──────────────────────────────────────────
        it_h = 0.085
        _bordered_frame(
            self.left_panel_outer, pad, cy, inner_w, it_h,
            bg=C_SLOT_BG, border=C_SLOT_BORDER,
        )
        self.items_title = OnscreenText(
            parent=self.left_panel_outer,
            text="ITEMS",
            pos=(pad + 0.04, cy - it_h * 0.62),
            scale=0.050,
            fg=C_TITLE, align=TextNode.ALeft, mayChange=True,
        )
        cy -= it_h + 0.018

        # ── MAX ITEMS label ──────────────────────────────────────
        OnscreenText(
            parent=self.left_panel_outer,
            text=f"MAX {MAX_ITEMS} ITEMS ALLOWED",
            pos=(pad + 0.04, cy - 0.028),
            scale=0.036,
            fg=C_TEXT_DIM, align=TextNode.ALeft, mayChange=False,
        )
        cy -= 0.065

        # ── Player item slots ────────────────────────────────────
        slot_h = 0.068
        slot_gap = 0.015
        for i in range(MAX_ITEMS):
            slot_y = cy - i * (slot_h + slot_gap)
            sf, _ = _bordered_frame(
                self.left_panel_outer, pad, slot_y, inner_w, slot_h,
                bg=C_SLOT_BG, border=C_SLOT_BORDER,
            )
            self._player_item_frames.append(sf)

            lbl = OnscreenText(
                parent=self.left_panel_outer,
                text="",
                pos=(pad + 0.04, slot_y - slot_h * 0.62),
                scale=0.038,
                fg=C_TEXT, align=TextNode.ALeft, mayChange=True,
            )
            self._player_item_labels.append(lbl)

            # Invisible click button covering the slot
            btn = DirectButton(
                parent=self.left_panel_outer,
                text="",
                pos=(pad + inner_w * 0.5, 0, slot_y - slot_h * 0.5),
                scale=0.001,
                frameSize=(-inner_w * 500, inner_w * 500, -slot_h * 300, slot_h * 300),
                frameColor=(0, 0, 0, 0),
                relief=1,
                command=self._item_slot_clicked,
                extraArgs=[i],
            )
            btn.setTransparency(TransparencyAttrib.M_alpha)
            btn.hide()
            self._item_click_btns.append(btn)

        # ╔══════════════════════════════════════════════════════╗
        # ║  RIGHT PANEL — Dealer side                          ║
        # ╚══════════════════════════════════════════════════════╝
        rp_x = 1.78 - pw
        rp_top = 0.98
        rp_h = 1.96

        self.right_panel_outer, _ = _bordered_frame(
            a2d, rp_x, rp_top, pw, rp_h,
        )

        ry = -pad

        # ── DEALER NAME ──────────────────────────────────────────
        _bordered_frame(
            self.right_panel_outer, pad, ry, inner_w, name_h,
            bg=C_SLOT_BG, border=C_SLOT_BORDER,
        )
        self.dealer_name_label = OnscreenText(
            parent=self.right_panel_outer,
            text="DEALER",
            pos=(pad + 0.04, ry - name_h * 0.65),
            scale=0.052,
            fg=C_WARN, align=TextNode.ALeft, mayChange=True,
        )
        ry -= name_h + 0.03

        # ── DEALER HEALTH ────────────────────────────────────────
        _bordered_frame(
            self.right_panel_outer, pad, ry, inner_w, hp_h,
            bg=C_SLOT_BG, border=C_SLOT_BORDER,
        )
        self.dealer_hp_bar_bg = DirectFrame(
            parent=self.right_panel_outer,
            frameSize=(0, bar_w, 0, 0.045),
            frameColor=C_HP_BG,
            pos=(pad + bar_inset, 0, ry - hp_h + bar_inset + 0.005),
        )
        self.dealer_hp_bar = DirectFrame(
            parent=self.right_panel_outer,
            frameSize=(0, bar_w, 0, 0.045),
            frameColor=C_HP_DEALER,
            pos=(pad + bar_inset, 0, ry - hp_h + bar_inset + 0.005),
        )
        self.dealer_hp_text = OnscreenText(
            parent=self.right_panel_outer,
            text="HP: 3 / 3",
            pos=(pad + 0.04, ry - 0.042),
            scale=0.042,
            fg=C_TEXT, align=TextNode.ALeft, mayChange=True,
        )
        ry -= hp_h + 0.03

        # ── DEALER'S ITEMS title ─────────────────────────────────
        _bordered_frame(
            self.right_panel_outer, pad, ry, inner_w, it_h,
            bg=C_SLOT_BG, border=C_SLOT_BORDER,
        )
        self.dealer_items_title = OnscreenText(
            parent=self.right_panel_outer,
            text="DEALER'S ITEMS",
            pos=(pad + 0.04, ry - it_h * 0.62),
            scale=0.046,
            fg=C_TITLE, align=TextNode.ALeft, mayChange=True,
        )
        ry -= it_h + 0.018

        # ── MAX ITEMS label (dealer) ─────────────────────────────
        OnscreenText(
            parent=self.right_panel_outer,
            text=f"MAX {MAX_ITEMS} ITEMS ALLOWED",
            pos=(pad + 0.04, ry - 0.028),
            scale=0.036,
            fg=C_TEXT_DIM, align=TextNode.ALeft, mayChange=False,
        )
        ry -= 0.065

        # ── Dealer item slots ────────────────────────────────────
        for i in range(MAX_ITEMS):
            slot_y = ry - i * (slot_h + slot_gap)
            sf, _ = _bordered_frame(
                self.right_panel_outer, pad, slot_y, inner_w, slot_h,
                bg=C_SLOT_BG, border=C_SLOT_BORDER,
            )
            self._dealer_item_frames.append(sf)

            lbl = OnscreenText(
                parent=self.right_panel_outer,
                text="",
                pos=(pad + 0.04, slot_y - slot_h * 0.62),
                scale=0.038,
                fg=C_TEXT_DIM, align=TextNode.ALeft, mayChange=True,
            )
            self._dealer_item_labels.append(lbl)

        # ╔══════════════════════════════════════════════════════╗
        # ║  TOP CENTER — Shell info + Turn                     ║
        # ╚══════════════════════════════════════════════════════╝
        self.shell_info = OnscreenText(
            parent=a2d,
            text="LIVE: 0  |  BLANK: 0",
            pos=(0, 0.94),
            scale=0.052,
            fg=C_TEXT, align=TextNode.ACenter, mayChange=True,
        )
        self.turn_label = OnscreenText(
            parent=a2d,
            text="YOUR TURN  ·  Round 1",
            pos=(0, 0.86),
            scale=0.058,
            fg=C_TITLE, align=TextNode.ACenter, mayChange=True,
        )

        # ╔══════════════════════════════════════════════════════╗
        # ║  BOTTOM CENTER — Action buttons                     ║
        # ╚══════════════════════════════════════════════════════╝
        btn_w = 0.44
        btn_h = 0.10
        btn_y_top = -0.84
        btn_gap = 0.15    # half-gap between buttons

        # SHOOT YOURSELF — bordered box + button text
        self._shoot_self_box, _ = _bordered_frame(
            a2d, -btn_gap - btn_w, btn_y_top, btn_w, btn_h,
            bg=C_BTN_BG, border=C_BTN_BORDER,
        )
        self.btn_shoot_self = DirectButton(
            parent=a2d,
            text="SHOOT YOURSELF",
            pos=(-btn_gap - btn_w * 0.5, 0, btn_y_top - btn_h * 0.42),
            scale=0.055,
            text_scale=1.0,
            frameSize=(-btn_w / 0.11, btn_w / 0.11, -0.45, 0.7),
            frameColor=(0, 0, 0, 0),
            text_fg=C_TEXT,
            relief=1,
            command=self._on_shoot_self,
        )
        self.btn_shoot_self.setTransparency(TransparencyAttrib.M_alpha)

        # SHOOT DEALER — bordered box + button text
        self._shoot_dealer_box, _ = _bordered_frame(
            a2d, btn_gap, btn_y_top, btn_w, btn_h,
            bg=C_BTN_BG, border=C_BTN_BORDER,
        )
        self.btn_shoot_opp = DirectButton(
            parent=a2d,
            text="SHOOT DEALER",
            pos=(btn_gap + btn_w * 0.5, 0, btn_y_top - btn_h * 0.42),
            scale=0.055,
            text_scale=1.0,
            frameSize=(-btn_w / 0.11, btn_w / 0.11, -0.45, 0.7),
            frameColor=(0, 0, 0, 0),
            text_fg=C_TEXT,
            relief=1,
            command=self._on_shoot_opp,
        )
        self.btn_shoot_opp.setTransparency(TransparencyAttrib.M_alpha)

    # ── Item slot click ──────────────────────────────────────────
    def _item_slot_clicked(self, slot_index: int):
        if not hasattr(self, '_current_player_items'):
            return
        if slot_index >= len(self._current_player_items):
            return
        item = self._current_player_items[slot_index]
        self._on_item_used(item)

    # ══════════════════════════════════════════════════════════════════════
    #  UPDATE
    # ══════════════════════════════════════════════════════════════════════
    def update(self, state):
        from game_state import GameState
        gs: GameState = state
        p = gs.player
        d = gs.dealer

        # Shell info
        self.shell_info.setText(
            f"LIVE: {gs.shotgun.live_count}  |  BLANK: {gs.shotgun.blank_count}"
        )

        # Turn / Round
        is_player_turn = gs.turn == TurnOwner.PLAYER
        turn_txt = "YOUR TURN" if is_player_turn else "DEALER'S TURN"
        self.turn_label.setText(f"{turn_txt}  ·  Round {gs.round_index + 1}")
        self.turn_label["fg"] = C_TITLE if is_player_turn else C_WARN

        # Player HP
        self.player_hp_text.setText(f"HP: {p.hp} / {p.max_hp}")
        p_ratio = p.hp / max(p.max_hp, 1)
        self.player_hp_bar["frameSize"] = (0, self._hp_bar_full_w * p_ratio, 0, 0.045)

        # Dealer HP
        self.dealer_hp_text.setText(f"HP: {d.hp} / {d.max_hp}")
        d_ratio = d.hp / max(d.max_hp, 1)
        self.dealer_hp_bar["frameSize"] = (0, self._hp_bar_full_w * d_ratio, 0, 0.045)

        # Action buttons
        show_actions = is_player_turn and not gs.game_over
        for w in (self.btn_shoot_self, self._shoot_self_box,
                  self.btn_shoot_opp, self._shoot_dealer_box):
            w.show() if show_actions else w.hide()

        # Item names
        item_names = {
            ItemType.MAGNIFYING_GLASS: "Magnifying Glass",
            ItemType.BEER:             "Beer",
            ItemType.CIGARETTE:        "Cigarette",
            ItemType.HANDSAW:          "Hand Saw",
            ItemType.INVERTER:         "Inverter",
            ItemType.HANDCUFFS:        "Handcuffs",
        }

        # Player items
        self._current_player_items = list(p.items) if p else []
        for i in range(MAX_ITEMS):
            if i < len(self._current_player_items):
                itm = self._current_player_items[i]
                self._player_item_labels[i].setText(item_names.get(itm, str(itm)))
                self._player_item_labels[i]["fg"] = C_TEXT
                self._item_click_btns[i].show() if show_actions else self._item_click_btns[i].hide()
            else:
                self._player_item_labels[i].setText("")
                self._item_click_btns[i].hide()

        # Dealer items
        d_items = list(d.items) if d else []
        for i in range(MAX_ITEMS):
            if i < len(d_items):
                itm = d_items[i]
                self._dealer_item_labels[i].setText(item_names.get(itm, str(itm)))
            else:
                self._dealer_item_labels[i].setText("")

        # Logs
        logs = gs.message_log[-5:]
        for i, lbl in enumerate(self._log_labels):
            lbl.setText(logs[-(i + 1)] if i < len(logs) else "")

    # ══════════════════════════════════════════════════════════════════════
    #  GAME OVER / FLASH
    # ══════════════════════════════════════════════════════════════════════
    def show_game_over(self, winner: str):
        msg = "YOU WIN!" if winner == "Player" else "YOU LOSE..."
        clr = C_TITLE if winner == "Player" else C_WARN
        OnscreenText(
            text=msg, pos=(0, 0.10), scale=0.20,
            fg=clr, align=TextNode.ACenter,
            shadow=(0, 0, 0, 1), shadowOffset=(0.04, 0.04),
            mayChange=False,
        )
        OnscreenText(
            text="Press R to restart  |  ESC to quit",
            pos=(0, -0.15), scale=0.060,
            fg=C_TEXT, align=TextNode.ACenter,
            mayChange=False,
        )

    def flash_message(self, text: str, duration: float = 2.5):
        lbl = OnscreenText(
            text=text, pos=(0, 0.38), scale=0.072,
            fg=C_TITLE, align=TextNode.ACenter,
            shadow=(0, 0, 0, 1), shadowOffset=(0.03, 0.03),
            mayChange=True,
        )
        from direct.task import Task
        def _remove(t):
            lbl.destroy()
            return Task.done
        self.base.taskMgr.doMethodLater(duration, _remove, "flash_remove")
