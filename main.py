"""
main.py — Entry point for Buckshot Roulette (Panda3D).
Run:  python main.py
"""

import math
import sys
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.interval.IntervalGlobal import (
    LerpPosInterval, LerpHprInterval, LerpScaleInterval,
    LerpQuatInterval,
    LerpColorScaleInterval,
    Sequence, Parallel, Func, Wait,
)
from direct.gui.DirectGui import DirectFrame
from panda3d.core import (
    BitMask32,
    CollisionHandlerQueue,
    CollisionNode,
    CollisionRay,
    CollisionTraverser,
    TransparencyAttrib,
    WindowProperties, Point3, LColor, Vec3, Vec4,
)

from game_state import GameState, TurnOwner, ItemType
from scene_builder import SceneBuilder
from ui_manager import UIManager
from item_animations import ItemAnimator


# ─────────────────────────────────────────────────────────────────
class BuckshotRoulette(ShowBase):

    def __init__(self):
        super().__init__()
        self._ctrl_held = False
        self._mouse_sensitivity = 70.0
        self._yaw = 0.0
        self._pitch = 0.0
        self._gun_picked_up = False
        self._gun_original_pos = None
        self._gun_original_hpr = None
        self._gun_original_scale = None
        self._gun_anim_playing = False
        self._pending_putdown_cb = None
        self._gun_table_pos = None
        self._gun_table_hpr = None
        self._gun_table_scale = None
        self._gun_table_pos = None
        self._gun_table_hpr = None
        self._gun_table_scale = None
        self._pending_putdown_cb = None
        self._shoot_anim_playing = False
        self._setup_window()
        self._setup_camera()
        self._setup_picker()

        # Game state
        self.gs = GameState()

        # 3-D scene
        self.scene = SceneBuilder(self.render, self)
        self.scene.build()
        self._apply_scene_camera_pose()
        self.scene.rebuild_shell_indicators(self.gs.shotgun.shells)
        self._make_gun_pickable()
        self._cache_gun_table_pose()
        self._cache_gun_table_pose()

        # Item animation system
        self._item_animator = ItemAnimator(self, self.scene)

        # 2-D HUD
        self.ui = UIManager(
            self,
            on_shoot_self=self._player_shoot_self,
            on_shoot_opp=self._player_shoot_opp,
            on_item_used=self._player_use_item,
        )
        self.ui.update(self.gs)

        # Dealer is thinking flag
        self._dealer_thinking = False

        # Key bindings
        self.accept("escape", sys.exit)
        self.accept("r", self._restart)
        self.accept("control", self._ctrl_press)
        self.accept("control-up", self._ctrl_release)
        self.accept("mouse1", self._on_mouse_click)

        # Ambient music-like pulsing light task
        self.taskMgr.add(self._pulse_task, "pulse_dealer_light")
        self.taskMgr.add(self._camera_look_task, "camera_look")

    # ── Window / Camera ───────────────────
    def _setup_window(self):
        props = WindowProperties()
        props.setTitle("Buckshot Roulette  —  3D")
        props.setSize(1280, 720)
        props.setCursorHidden(False)
        self.win.requestProperties(props)
        self.setBackgroundColor(0.03, 0.02, 0.05, 1)
        self.disableMouse()

    def _setup_camera(self):
        self.camera.setPos(0, -6.5, 2.8)
        self.camera.lookAt(Point3(0, 1.5, 1.4))
        self._yaw = self.camera.getH()
        self._pitch = self.camera.getP()
        # Zoom out naturally with FOV without moving camera mathematically into walls
        self.camLens.setFov(75)

    def _apply_scene_camera_pose(self):
        cam_pos, look_at = self.scene.get_recommended_camera_pose()
        self.camera.setPos(cam_pos)
        self.camera.lookAt(look_at)
        self._yaw = self.camera.getH()
        self._pitch = self.camera.getP()

    def _center_mouse(self):
        if self.win is None:
            return False
        x = int(self.win.getProperties().getXSize() / 2)
        y = int(self.win.getProperties().getYSize() / 2)
        return self.win.movePointer(0, x, y)

    # ── CTRL-based camera look ────────────
    def _ctrl_press(self):
        self._ctrl_held = True
        props = WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)
        self._center_mouse()

    def _ctrl_release(self):
        self._ctrl_held = False
        props = WindowProperties()
        props.setCursorHidden(False)
        self.win.requestProperties(props)

    def _camera_look_task(self, task):
        if not self._ctrl_held or self.win is None:
            return Task.cont
        if not self.win.getProperties().getForeground():
            return Task.cont

        props = self.win.getProperties()
        cx = int(props.getXSize() / 2)
        cy = int(props.getYSize() / 2)
        ptr = self.win.getPointer(0)
        dx_pixels = ptr.getX() - cx
        dy_pixels = ptr.getY() - cy

        # If pointer cannot be centered (window focus issue), skip update to avoid drift.
        if not self._center_mouse():
            return Task.cont

        if dx_pixels == 0 and dy_pixels == 0:
            return Task.cont

        self._yaw -= dx_pixels * 0.18
        self._pitch = max(-65.0, min(65.0, self._pitch - dy_pixels * 0.18))
        self.camera.setHpr(self._yaw, self._pitch, 0)
        return Task.cont

    # ── 3D Object Picker ──────────────────
    def _setup_picker(self):
        """Set up collision ray for mouse picking 3D objects."""
        self._picker_traverser = CollisionTraverser("picker")
        self._picker_queue = CollisionHandlerQueue()
        self._picker_node = CollisionNode("mouseRay")
        self._picker_mask = BitMask32.bit(1)
        self._picker_node.setFromCollideMask(self._picker_mask)
        self._picker_node.setIntoCollideMask(BitMask32.allOff())
        self._picker_ray = CollisionRay()
        self._picker_node.addSolid(self._picker_ray)
        self._picker_np = self.camera.attachNewNode(self._picker_node)
        self._picker_traverser.addCollider(self._picker_np, self._picker_queue)

    def _make_gun_pickable(self):
        """Tag the gun NodePath so the picker ray can detect it."""
        gun_np = self.scene.shotgun_np
        if gun_np is None or gun_np.isEmpty():
            return
        gun_np.setTag("pickable", "gun")
        # Set collision mask on all geometry so ray can hit it
        for geom in gun_np.findAllMatches("**/+GeomNode"):
            geom.node().setIntoCollideMask(self._picker_mask)
        # Also set on root in case it has geometry
        if gun_np.node().getNumChildren() == 0:
            gun_np.node().setIntoCollideMask(self._picker_mask)

    def _cache_gun_table_pose(self):
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            return
        self._gun_table_pos = gun.getPos()
        self._gun_table_hpr = gun.getHpr()
        self._gun_table_scale = gun.getScale()

    def _on_mouse_click(self):
        """Handle left mouse click — check if gun was clicked."""
        if self._ctrl_held:
            return
        if self._gun_anim_playing:
            return

        if not self.mouseWatcherNode.hasMouse():
            return

        mpos = self.mouseWatcherNode.getMouse()
        self._picker_ray.setFromLens(self.camNode, mpos.getX(), mpos.getY())
        self._picker_traverser.traverse(self.render)

        if self._picker_queue.getNumEntries() == 0:
            return

        self._picker_queue.sortEntries()
        for i in range(self._picker_queue.getNumEntries()):
            entry = self._picker_queue.getEntry(i)
            picked_np = entry.getIntoNodePath()
            # Walk up to find the tagged ancestor
            target = picked_np
            while not target.isEmpty() and target != self.render:
                if target.getTag("pickable") == "gun":
                    if self._gun_picked_up:
                        self._put_down_gun()
                    else:
                        self._pick_up_gun()
                    return
                target = target.getParent()

    # ── Gun Pickup Animation ─────────────
    def _pick_up_gun(self):
        """Animate the gun being picked up to player's hand view."""
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            return

        self._gun_anim_playing = True

        # Save original transform
        self._gun_original_pos = gun.getPos()
        self._gun_original_hpr = gun.getHpr()
        self._gun_original_scale = gun.getScale()

        # Calculate target position: in front of camera, slightly down and right
        cam_pos = self.camera.getPos()
        cam_hpr = self.camera.getHpr()

        # Get forward direction from camera
        h_rad = math.radians(cam_hpr.getX())
        p_rad = math.radians(cam_hpr.getY())
        forward = Vec3(
            -math.sin(h_rad) * math.cos(p_rad),
            math.cos(h_rad) * math.cos(p_rad),
            math.sin(p_rad),
        )
        right = Vec3(math.cos(h_rad), math.sin(h_rad), 0)

        # Position gun: 2 units forward, 0.5 right, 0.8 down from camera
        target_pos = Point3(
            cam_pos.getX() + forward.getX() * 2.0 + right.getX() * 0.5,
            cam_pos.getY() + forward.getY() * 2.0 + right.getY() * 0.5,
            cam_pos.getZ() - 0.8,
        )

        # Target rotation: gun pointing forward (aiming direction)
        target_hpr = Point3(cam_hpr.getX() + 180, 0, 0)

        # Scale the gun a bit for held view
        held_scale = self._gun_original_scale * 1.2

        pickup_seq = Sequence(
            # Phase 1: Lift gun off table
            Parallel(
                LerpPosInterval(gun, 0.35,
                    Point3(gun.getX(), gun.getY(), gun.getZ() + 1.0),
                    blendType="easeInOut"),
            ),
            # Phase 2: Move gun to hand position
            Parallel(
                LerpPosInterval(gun, 0.45, target_pos, blendType="easeInOut"),
                LerpHprInterval(gun, 0.45, target_hpr, blendType="easeInOut"),
                LerpScaleInterval(gun, 0.45, held_scale, blendType="easeInOut"),
            ),
            Func(self._on_pickup_complete),
        )
        pickup_seq.start()

    def _on_pickup_complete(self):
        self._gun_picked_up = True
        self._gun_anim_playing = False
        self.ui.flash_message("Gun picked up! Click gun again to put down.", duration=2.0)

    def _put_down_gun(self, callback=None):
        """Animate gun back to its original position on the table."""
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            return
        if self._gun_original_pos is None:
            return

        self._pending_putdown_cb = callback
        self._gun_anim_playing = True

        putdown_seq = Sequence(
            # Phase 1: Lift slightly
            LerpPosInterval(gun, 0.2,
                Point3(gun.getX(), gun.getY(), gun.getZ() + 0.3),
                blendType="easeIn"),
            # Phase 2: Move back to table
            Parallel(
                LerpPosInterval(gun, 0.4, self._gun_original_pos, blendType="easeInOut"),
                LerpHprInterval(gun, 0.4, self._gun_original_hpr, blendType="easeInOut"),
                LerpScaleInterval(gun, 0.4, self._gun_original_scale, blendType="easeInOut"),
            ),
            Func(self._on_putdown_complete),
        )
        putdown_seq.start()

    def _on_putdown_complete(self):
        self._gun_picked_up = False
        self._gun_anim_playing = False
        if self._pending_putdown_cb:
            cb = self._pending_putdown_cb
            self._pending_putdown_cb = None
            cb()

    # ── Shooting hit animations ───────────
    def _is_blocked(self):
        return self._item_animator.animating or self._shoot_anim_playing or self._gun_anim_playing

    # ── Gun shoot animation ─────────────────
    def _aim_point_player(self) -> Point3:
        cam = self.camera
        cam_pos = cam.getPos(self.render)
        cam_quat = cam.getQuat(self.render)
        up = cam_quat.getUp()
        # Chest-level target near camera so self-shot points back toward player.
        return Point3(
            cam_pos.x - up.x * 0.12,
            cam_pos.y - up.y * 0.12,
            cam_pos.z - up.z * 0.12,
        )

    def _dealer_face_point(self) -> Point3:
        dealer = self.scene.dealer_root
        if dealer is not None and not dealer.isEmpty():
            try:
                mn, mx = dealer.getTightBounds()
                if mn is not None and mx is not None:
                    return Point3(
                        (mn.x + mx.x) * 0.5,
                        (mn.y + mx.y) * 0.5,
                        mn.z + (mx.z - mn.z) * 0.88,
                    )
            except Exception:
                pass
        d = self.scene.dealer_anchor
        return Point3(d.x, d.y, d.z + 1.72)

    def _aim_point_dealer(self) -> Point3:
        return self._dealer_face_point()

    def _gun_aim_hpr(self, origin: Point3, target: Point3, holder: str = "player"):
        """Return corrected HPR so the model's muzzle axis points at target naturally."""
        aim_np = self.render.attachNewNode(f"aim_{holder}")
        aim_np.setPos(origin)
        aim_np.lookAt(target, Vec3(0, 0, 1))

        # Model-specific axis correction: without this the gun appears upright/sideways.
        
        if holder in ("player_self", "dealer_self"):
            # For self-shot, the target is the face.
            # Base rotation to aim correctly
            aim_np.setH(aim_np.getH() + 180)
            aim_np.setP(aim_np.getP() + 90)
            # Flip upside down so handle is pointing down and nozzle is pointing towards face
            # By default it seems to hold it backward/upside-down for self.
            aim_np.setR(aim_np.getR() + 180)
            
            if holder == "player_self":
                aim_np.setR(aim_np.getR() + 25)
                # Twist pitch slightly so we see more of the barrel
                aim_np.setP(aim_np.getP() - 10)
        else:
            aim_np.setH(aim_np.getH() + 180)
            aim_np.setP(aim_np.getP() + 90)
            # Slight roll tilt to mimic a hand-held grip.
            if holder == "dealer":
                aim_np.setR(aim_np.getR() - 10)
            else:
                aim_np.setR(aim_np.getR() + 8)
                
        hpr = aim_np.getHpr()
        aim_np.removeNode()
        return hpr

    def _gun_shoot_anim(self, target_pos: Point3, callback):
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            if callback:
                callback()
            return
        if self._gun_anim_playing:
            if callback:
                callback()
            return

        self._gun_anim_playing = True

        start_pos = gun.getPos()
        start_quat = gun.getQuat(self.render)
        start_scale = gun.getScale()

        # Aim orientation toward target using model-axis corrected pose.
        aim_hpr = self._gun_aim_hpr(start_pos, target_pos, holder="player")
        aim_np = self.render.attachNewNode("aim_tmp")
        aim_np.setPos(start_pos)
        aim_np.setHpr(aim_hpr)
        aim_quat = aim_np.getQuat(self.render)
        to_target = target_pos - start_pos
        if to_target.lengthSquared() < 1e-8:
            to_target = Vec3(0, 1, 0)
        else:
            to_target.normalize()
        aim_np.removeNode()

        # Move to a clearer firing pose before recoil, so the barrel visibly lines up.
        lift_pos = Point3(
            start_pos.x + to_target.x * 0.42,
            start_pos.y + to_target.y * 0.42,
            start_pos.z + 0.10,
        )
        recoil_pos = Point3(
            lift_pos.x - to_target.x * 0.18,
            lift_pos.y - to_target.y * 0.18,
            lift_pos.z - to_target.z * 0.18,
        )

        seq = Sequence(
            # Lift + aim
            Parallel(
                LerpPosInterval(gun, 0.42, lift_pos, blendType="easeOut"),
                LerpQuatInterval(gun, 0.50, aim_quat, blendType="easeInOut"),
                LerpScaleInterval(gun, 0.50, start_scale, blendType="easeInOut"),
            ),
            # Recoil
            LerpPosInterval(gun, 0.20, recoil_pos, blendType="easeOut"),
            LerpPosInterval(gun, 0.28, lift_pos, blendType="easeIn"),
            # Return to original pose
            Parallel(
                LerpPosInterval(gun, 0.50, start_pos, blendType="easeInOut"),
                LerpQuatInterval(gun, 0.50, start_quat, blendType="easeInOut"),
                LerpScaleInterval(gun, 0.50, start_scale, blendType="easeInOut"),
            ),
            Func(lambda: setattr(self, "_gun_anim_playing", False)),
            Func(callback) if callback else Func(lambda: None),
        )
        seq.start()

    def _move_gun_to_player_pose(self, target_pos: Point3, callback=None):
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            if callback:
                callback()
            return

        cam = self.camera
        cam_pos = cam.getPos(self.render)
        cam_quat = cam.getQuat(self.render)
        forward = cam_quat.getForward()
        right = cam_quat.getRight()
        up = cam_quat.getUp()

        pos = Point3(
            cam_pos.x + forward.x * 1.05 + right.x * 0.18 - up.x * 0.14,
            cam_pos.y + forward.y * 1.05 + right.y * 0.18 - up.y * 0.14,
            cam_pos.z + forward.z * 1.05 + right.z * 0.18 - up.z * 0.14,
        )

        hpr = self._gun_aim_hpr(pos, target_pos, holder="player")

        base_scale = self._gun_table_scale if self._gun_table_scale is not None else gun.getScale()
        scale = base_scale * 0.86
        self._move_gun_to_pose(pos, hpr, scale, 0.62, callback)

    def _move_gun_to_player_self_pose(self, callback=None):
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            if callback:
                callback()
            return

        cam = self.camera
        cam_pos = cam.getPos(self.render)
        cam_quat = cam.getQuat(self.render)
        forward = cam_quat.getForward()
        right = cam_quat.getRight()
        up = cam_quat.getUp()

        # Place the gun comfortably visible in front, angled nicely so we see the nozzle and the side.
        # Far enough so it doesn't clip behind the camera POV!
        pos = Point3(
            cam_pos.x + forward.x * 2.80 + right.x * 0.35 - up.x * 0.50,
            cam_pos.y + forward.y * 2.80 + right.y * 0.35 - up.y * 0.50,
            cam_pos.z + forward.z * 2.80 + right.z * 0.35 - up.z * 0.50,
        )

        target = self._aim_point_player()
        hpr = self._gun_aim_hpr(pos, target, holder="player_self")
        base_scale = self._gun_table_scale if self._gun_table_scale is not None else gun.getScale()
        scale = base_scale * 0.74
        self._move_gun_to_pose(pos, hpr, scale, 0.72, callback)

    def _move_gun_to_pose(self, pos: Point3, hpr, scale, duration: float = 0.25, callback=None):
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            if callback:
                callback()
            return
        if self._gun_anim_playing:
            if callback:
                callback()
            return
        self._gun_anim_playing = True

        aim_np = self.render.attachNewNode("move_pose_tmp")
        aim_np.setPos(pos)
        aim_np.setHpr(hpr)
        target_quat = aim_np.getQuat(self.render)
        aim_np.removeNode()

        seq = Sequence(
            Parallel(
                LerpPosInterval(gun, duration, pos, blendType="easeInOut"),
                LerpQuatInterval(gun, duration, target_quat, blendType="easeInOut"),
                LerpScaleInterval(gun, duration, scale, blendType="easeInOut"),
            ),
            Func(lambda: setattr(self, "_gun_anim_playing", False)),
            Func(callback) if callback else Func(lambda: None),
        )
        seq.start()

    def _return_gun_to_table(self, callback=None):
        if self._gun_table_pos is None or self._gun_table_hpr is None or self._gun_table_scale is None:
            if callback:
                callback()
            return
        self._move_gun_to_pose(self._gun_table_pos, self._gun_table_hpr, self._gun_table_scale, 0.25, callback)

    def _move_gun_to_dealer_pose(self, target_pos: Point3, is_self=False, callback=None):
        gun = self.scene.shotgun_np
        if gun is None or gun.isEmpty():
            if callback:
                callback()
            return
        face = self._dealer_face_point()
        # Niche kiya taaki dealer ke hath ke level pe rahe (AUR ZYADA NICHE - lowered drastically)
        pos = Point3(face.x + 0.15, face.y - 0.25, face.z - 1.65)
        holder_type = "dealer_self" if is_self else "dealer"
        hpr = self._gun_aim_hpr(pos, target_pos, holder=holder_type)
        scale = self._gun_table_scale if self._gun_table_scale is not None else gun.getScale()
        self._move_gun_to_pose(pos, hpr, scale, 0.50, callback)

    def _player_hit_anim(self, callback):
        """White flash → blur clears: player was shot with LIVE round."""
        self._shoot_anim_playing = True
        overlay = DirectFrame(
            parent=self.aspect2d,
            frameSize=(-3, 3, -2, 2),
            frameColor=(1, 1, 1, 1),
            sortOrder=100,
        )
        overlay.setTransparency(TransparencyAttrib.M_alpha)
        # Red vignette on edges
        red_edge = DirectFrame(
            parent=self.aspect2d,
            frameSize=(-3, 3, -2, 2),
            frameColor=(0.9, 0.1, 0.05, 0.6),
            sortOrder=101,
        )
        red_edge.setTransparency(TransparencyAttrib.M_alpha)
        red_edge.setColorScale(1, 1, 1, 0)

        seq = Sequence(
            # Hold white flash
            Wait(0.25),
            # Show red pain edge
            Parallel(
                LerpColorScaleInterval(overlay, 0.4, Vec4(1, 1, 1, 0.3), blendType="easeOut"),
                LerpColorScaleInterval(red_edge, 0.3, Vec4(1, 1, 1, 0.6)),
            ),
            # Fade red
            LerpColorScaleInterval(red_edge, 0.5, Vec4(1, 1, 1, 0), blendType="easeOut"),
            # Clear blur/white fully
            LerpColorScaleInterval(overlay, 0.6, Vec4(1, 1, 1, 0), blendType="easeOut"),
            Func(lambda: overlay.removeNode()),
            Func(lambda: red_edge.removeNode()),
            Func(self._end_shoot_anim),
            Func(callback),
        )
        seq.start()

    def _dealer_hit_anim(self, callback):
        """Dealer falls fully backward then slowly gets back up."""
        dealer = self.scene.dealer_root
        if dealer is None or dealer.isEmpty():
            callback()
            return

        self._shoot_anim_playing = True
        orig_pos = dealer.getPos()
        orig_hpr = dealer.getHpr()

        # Fall BACKWARD: away from player (Y+), down to near floor (Z-), tilt back heavily
        fall_pos = Point3(orig_pos.x, orig_pos.y + 2.0, orig_pos.z - 1.5)
        # Reverse pitch direction — negative = tilt backward away from player
        fall_hpr = Point3(orig_hpr.x, orig_hpr.y - 70, orig_hpr.z)

        seq = Sequence(
            # Recoil jolt — hit impact pushes back slightly
            LerpPosInterval(dealer, 0.06,
                Point3(orig_pos.x, orig_pos.y + 0.3, orig_pos.z + 0.1),
                blendType="easeOut"),
            # Fall backward completely — pura let jaana
            Parallel(
                LerpPosInterval(dealer, 0.55, fall_pos, blendType="easeIn"),
                LerpHprInterval(dealer, 0.55, fall_hpr, blendType="easeIn"),
            ),
            # Lie flat on ground
            Wait(1.0),
            # Slowly get back up — struggle to stand
            Parallel(
                LerpPosInterval(dealer, 0.5,
                    Point3(orig_pos.x, orig_pos.y + 0.8, orig_pos.z - 0.5),
                    blendType="easeOut"),
                LerpHprInterval(dealer, 0.5,
                    Point3(orig_hpr.x, orig_hpr.y - 30, orig_hpr.z),
                    blendType="easeOut"),
            ),
            # Final stand up fully
            Parallel(
                LerpPosInterval(dealer, 0.7, orig_pos, blendType="easeOut"),
                LerpHprInterval(dealer, 0.7, orig_hpr, blendType="easeOut"),
            ),
            Wait(0.2),
            Func(self._end_shoot_anim),
            Func(callback),
        )
        seq.start()

    def _end_shoot_anim(self):
        self._shoot_anim_playing = False

    # ── Player actions ────────────────────
    def _player_shoot_self(self):
        if self.gs.game_over or self.gs.turn != TurnOwner.PLAYER:
            return
        if self._is_blocked():
            return
        msg = self.gs.shoot_self()

        target = self._aim_point_player()

        def after_action_pose():
            if "LIVE" in msg:
                self._player_hit_anim(lambda: self._post_action(msg))
            else:
                self._post_action(msg)

        def after_gun():
            self._return_gun_to_table(after_action_pose)

        self._move_gun_to_player_self_pose(lambda: self._gun_shoot_anim(target, after_gun))

    def _player_shoot_opp(self):
        if self.gs.game_over or self.gs.turn != TurnOwner.PLAYER:
            return
        if self._is_blocked():
            return
        msg = self.gs.shoot_opponent()

        target = self._aim_point_dealer()

        def after_action_pose():
            if "LIVE" in msg:
                self._dealer_hit_anim(lambda: self._post_action(msg))
            else:
                self._post_action(msg)

        def after_gun():
            self._return_gun_to_table(after_action_pose)

        self._move_gun_to_player_pose(target, lambda: self._gun_shoot_anim(target, after_gun))

    def _player_use_item(self, item: ItemType):
        if self.gs.game_over or self.gs.turn != TurnOwner.PLAYER:
            return
        if self._is_blocked():
            return
        self._item_animator.play(item, user="player", on_complete=lambda: self._apply_item_effect(item))

    def _apply_item_effect(self, item: ItemType):
        """Called after item animation finishes — apply actual game logic."""
        msg = self.gs.use_item(item)
        self._post_action(msg)

    def _post_action(self, msg: str):
        """Called after any player or dealer action."""
        self.scene.rebuild_shell_indicators(self.gs.shotgun.shells)
        self.ui.update(self.gs)
        if msg:
            self.ui.flash_message(msg, duration=2.0)

        if self.gs.game_over:
            self.ui.show_game_over(self.gs.winner)
            return

        if self.gs.turn == TurnOwner.DEALER and not self._dealer_thinking:
            self._dealer_thinking = True
            self.taskMgr.doMethodLater(1.6, self._dealer_turn_task, "dealer_turn")

    def _dealer_turn_task(self, task):
        """AI takes its action; may chain multiple actions in one turn."""
        if self.gs.game_over or self.gs.turn != TurnOwner.DEALER:
            self._dealer_thinking = False
            return Task.done

        # If player is holding the gun, force putdown before dealer acts
        if self._gun_picked_up:
            if self._gun_anim_playing:
                task.delayTime = 0.1
                return Task.again
            self._put_down_gun(lambda: self.taskMgr.doMethodLater(0.1, self._dealer_turn_task, "dealer_turn"))
            return Task.done

        msg = self.gs.dealer_ai_action()

        # Check if a LIVE shot happened
        player_hit = "LIVE" in msg and "shot Player" in msg
        dealer_self_hit = "LIVE" in msg and "shot themselves" in msg

        shot_player = "shot Player" in msg
        shot_self = "shot themselves" in msg

        if shot_player or shot_self:
            target = self._aim_point_player() if shot_player else self._aim_point_dealer()

            def after_gun():
                if player_hit:
                    # Player was shot → white flash, then continue
                    self._player_hit_anim(lambda: self._return_gun_to_table(lambda: self._finish_dealer_turn(msg)))
                elif dealer_self_hit:
                    # Dealer shot themselves LIVE → dealer falls, then continue
                    self._dealer_hit_anim(lambda: self._return_gun_to_table(lambda: self._finish_dealer_turn(msg)))
                else:
                    # Blank shot → proceed normally (schedule next dealer action if needed)
                    self._return_gun_to_table(lambda: self._finish_dealer_turn(msg))

            self._move_gun_to_dealer_pose(target, is_self=shot_self, callback=lambda: self._gun_shoot_anim(target, after_gun))
            return Task.done

        # Detect item usage:
        from game_state import ItemType
        used_item = None
        if "[Magnifying" in msg: used_item = ItemType.MAGNIFYING_GLASS
        elif "[Cigarette]" in msg: used_item = ItemType.CIGARETTE
        elif "[Hand Saw]" in msg: used_item = ItemType.HANDSAW
        elif "[Handcuffs]" in msg: used_item = ItemType.HANDCUFFS
        elif "[Beer]" in msg: used_item = ItemType.BEER
        elif "[Inverter]" in msg: used_item = ItemType.INVERTER

        if used_item:
            self._item_animator.play(used_item, user="dealer", on_complete=lambda: self._finish_dealer_turn(msg))
            return Task.done

        # No item/shot happened or unrecognized (e.g. wait message)
        return self._continue_dealer_turn(msg, task)

    def _finish_dealer_turn(self, msg):
        """After a hit animation finishes during dealer’s turn."""
        self.scene.rebuild_shell_indicators(self.gs.shotgun.shells)
        self.ui.update(self.gs)
        if msg:
            self.ui.flash_message(msg, duration=1.8)

        if self.gs.game_over:
            self.ui.show_game_over(self.gs.winner)
            self._dealer_thinking = False
            return

        if self.gs.turn == TurnOwner.DEALER:
            self.taskMgr.doMethodLater(1.4, self._dealer_turn_task, "dealer_turn")
        else:
            self._dealer_thinking = False

    def _continue_dealer_turn(self, msg, task):
        """Normal dealer turn continuation (no hit animation needed)."""
        self.scene.rebuild_shell_indicators(self.gs.shotgun.shells)
        self.ui.update(self.gs)
        if msg:
            self.ui.flash_message(msg, duration=1.8)

        if self.gs.game_over:
            self.ui.show_game_over(self.gs.winner)
            self._dealer_thinking = False
            return Task.done

        if self.gs.turn == TurnOwner.DEALER:
            task.delayTime = 1.4
            return Task.again

        self._dealer_thinking = False
        return Task.done

    # ── Restart ───────────────────────────
    def _restart(self):
        # Rebuild everything from scratch
        self.render.getChildren().detach()
        self.aspect2d.getChildren().detach()

        self._gun_picked_up = False
        self._gun_original_pos = None
        self._gun_original_hpr = None
        self._gun_original_scale = None
        self._gun_anim_playing = False
        self._shoot_anim_playing = False

        self.gs = GameState()
        self.scene = SceneBuilder(self.render, self)
        self.scene.build()
        self._apply_scene_camera_pose()
        self.scene.rebuild_shell_indicators(self.gs.shotgun.shells)
        self._make_gun_pickable()
        self._item_animator = ItemAnimator(self, self.scene)

        self.ui = UIManager(
            self,
            on_shoot_self=self._player_shoot_self,
            on_shoot_opp=self._player_shoot_opp,
            on_item_used=self._player_use_item,
        )
        self.ui.update(self.gs)
        self._dealer_thinking = False

    # ── Ambient pulse light ────────────────
    def _pulse_task(self, task):
        t = task.time
        # Make the red dealer point light pulse slightly
        pln = self.render.find("**/dealer_light")
        if not pln.isEmpty():
            v = 0.5 + 0.5 * math.sin(t * 1.2)
            pln.node().setColor(LColor(0.4 + 0.35 * v, 0.02, 0.02, 1))
        return Task.cont


# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    game = BuckshotRoulette()
    game.run()
