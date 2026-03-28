"""
scene_builder.py
Loads GLB environment and builds gameplay props for Buckshot Roulette.
"""

import json
import os
import struct

from panda3d.core import (
    AmbientLight,
    BitMask32,
    CollisionHandlerQueue,
    CollisionNode,
    CollisionRay,
    CollisionTraverser,
    DirectionalLight,
    LColor,
    NodePath,
    Point3,
    PointLight,
    TransparencyAttrib,
    Vec4,
)


class SceneBuilder:
    """Build the 3D scene and expose references used by gameplay/UI."""

    def __init__(self, render: NodePath, base):
        self.render = render
        self.base = base
        self.environment_np: NodePath | None = None
        self.table_root: NodePath | None = None
        self.dealer_root: NodePath | None = None
        self.shotgun_np: NodePath | None = None
        self.shell_indicators: list[NodePath] = []
        self.env_min: Point3 | None = None
        self.env_max: Point3 | None = None
        self.table_anchor = Point3(0, 1.5, 1.05)
        self.dealer_anchor = Point3(0, 4.6, 1.65)
        self.table_half_x = 0.65
        self.table_half_y = 0.65

    def build(self):
        self._build_environment_from_glb()
        self._build_table_dealer_shotgun()
        self._setup_lighting()

    def _build_environment_from_glb(self):
        """
        Load user GLB environment from workspace root.
        Auto-center and auto-scale so camera/gameplay coordinates still work.
        """
        model_path = "artcollection_room_with_office.glb"
        # Force reload so replacing the file with the same name still shows new GLB.
        env = self.base.loader.loadModel(model_path, noCache=True)

        if env.isEmpty():
            raise FileNotFoundError(f"Could not load environment model: {model_path}")

        env.reparentTo(self.render)

        # This GLB is authored in Y-up; convert to Panda3D's Z-up space.
        # +90 keeps floor/ceiling orientation correct for this asset.
        env.setHpr(0, 90, 0)

        bounds = env.getTightBounds()
        if bounds and bounds[0] is not None and bounds[1] is not None:
            min_b, max_b = bounds
            size = max_b - min_b
            largest = max(size.x, size.y, size.z, 1.0)

            # Normalize environment to a usable gameplay scale.
            target_largest = 18.0
            scale = target_largest / largest
            env.setScale(scale)

            # Recompute bounds after scaling for precise placement.
            min_b2, max_b2 = env.getTightBounds()
            center2 = (min_b2 + max_b2) * 0.5
            env.setPos(-center2.x, -center2.y, -min_b2.z)
        else:
            env.setPos(0, 0, 0)
            env.setScale(1.0)

        # GLB/PBR materials render correctly with auto-shader.
        env.setShaderAuto()
        # Mild boost so dark textures are still visible in this game lighting setup.
        env.setColorScale(1.25, 1.25, 1.25, 1.0)
        env.setTwoSided(True)
        self.environment_np = env

        final_bounds = env.getTightBounds()
        if final_bounds and final_bounds[0] is not None and final_bounds[1] is not None:
            self.env_min, self.env_max = final_bounds

    def _compute_anchors(self):
        """Place table/dealer in a sensible area based on environment bounds."""
        if self.env_min is None or self.env_max is None:
            self.table_anchor = Point3(0, -1.25, 1.35)
            self.dealer_anchor = Point3(0, 1.0, 0.35)
            return

        min_b = self.env_min
        max_b = self.env_max
        center_x = (min_b.x + max_b.x) * 0.5
        center_y = (min_b.y + max_b.y) * 0.5
        floor_z = self._sample_floor_z(center_x, center_y, fallback_z=min_b.z)

        # Pull table slightly toward player POV while staying room-centered.
        table_y = center_y - 1.25
        table_z = floor_z + 0.95
        self.table_anchor = Point3(center_x, table_y, table_z)
        self.dealer_anchor = Point3(center_x, table_y + 2.0, floor_z)

    def _sample_floor_z(self, x: float, y: float, fallback_z: float) -> float:
        """Raycast down on room geometry and return floor height near (x, y)."""
        if self.environment_np is None:
            return fallback_z

        geom_paths = self.environment_np.findAllMatches("**/+GeomNode")
        if geom_paths.getNumPaths() == 0:
            return fallback_z

        probe_mask = BitMask32.bit(29)
        original_masks = []
        for i in range(geom_paths.getNumPaths()):
            geom_node = geom_paths.getPath(i).node()
            original_masks.append((geom_node, geom_node.getIntoCollideMask()))
            geom_node.setIntoCollideMask(probe_mask)

        start_z = (self.env_max.z + 2.0) if self.env_max is not None else (fallback_z + 8.0)
        traverser = CollisionTraverser("floor_probe")
        queue = CollisionHandlerQueue()
        ray_node = CollisionNode("floor_probe_ray")
        ray_node.setFromCollideMask(probe_mask)
        ray_node.setIntoCollideMask(BitMask32.allOff())
        ray_node.addSolid(CollisionRay(x, y, start_z, 0, 0, -1))
        ray_np = self.render.attachNewNode(ray_node)

        try:
            traverser.addCollider(ray_np, queue)
            traverser.traverse(self.render)
            if queue.getNumEntries() == 0:
                return fallback_z
            return max(queue.getEntry(i).getSurfacePoint(self.render).z for i in range(queue.getNumEntries()))
        finally:
            ray_np.removeNode()
            for geom_node, mask in original_masks:
                geom_node.setIntoCollideMask(mask)

    def get_recommended_camera_pose(self) -> tuple[Point3, Point3]:
        """Return (camera_position, look_at) adapted to the loaded GLB bounds."""
        if self.env_min is None or self.env_max is None:
            return Point3(0, -8.5, 4.0), Point3(0, 1.5, 1.4)

        min_b = self.env_min
        max_b = self.env_max
        center_x = (min_b.x + max_b.x) * 0.5
        depth = max(3.0, max_b.y - min_b.y)
        cam_pos = Point3(center_x, self.table_anchor.y - max(5.5, depth * 0.28), 5.5)
        look_at = Point3(self.table_anchor.x, self.table_anchor.y, self.table_anchor.z + 0.65)
        return cam_pos, look_at

    def _make_box_model(self, sx: float, sy: float, sz: float, color: Vec4, name: str) -> NodePath:
        """Simple helper using Panda3D built-in cube model."""
        box = self.base.loader.loadModel("models/box")
        box.setName(name)
        box.clearTexture()
        box.setTextureOff(1)
        box.setMaterialOff(1)
        box.setScale(sx, sy, sz)
        box.setColor(color)
        box.reparentTo(self.render)
        box.setTwoSided(True)
        return box

    def _load_table_glb(self, tx: float, ty: float) -> float:
        """
        Load table.glb, apply Y-up→Z-up rotation, scale proportionally,
        and place it at (tx, ty) with an explicit top-surface height target.
        Returns the Z coordinate of the table's top surface in game units.
        This avoids sinking below the visible floor when model min-z is not the real floor.
        """
        TARGET_TABLE_HEIGHT = 2.2
        TABLE_TOP_Z = self.table_anchor.z

        table = self.base.loader.loadModel("table.glb", noCache=True)
        if table.isEmpty():
            # Fallback: flat procedural slab
            fb = self._make_box_model(2.5, 1.3, 0.08, Vec4(0.42, 0.24, 0.10, 1), "table_fallback")
            fb.setPos(tx, ty, 1.06)
            self.table_root = fb
            self.table_half_x = 2.5
            self.table_half_y = 1.3
            return 1.14

        table.reparentTo(self.render)

        # Same Y-up → Z-up axis fix used for the room
        table.setHpr(0, 90, 0)
        mn0, mx0 = table.getTightBounds()
        raw_height = max(0.01, mx0.z - mn0.z)
        table_scale = max(0.18, min(3.5, TARGET_TABLE_HEIGHT / raw_height))
        table.setScale(table_scale)

        # Position by desired top height, not by model min-z.
        mn, mx = table.getTightBounds()
        z_shift = TABLE_TOP_Z - mx.z
        table.setPos(tx, ty, z_shift)

        table.setShaderAuto()
        table.setColorScale(1.35, 1.35, 1.35, 1.0)
        table.setTransparency(TransparencyAttrib.M_none)
        table.setTwoSided(True)
        self.table_root = table

        # Update table_anchor Z to actual top surface
        mn2, mx2 = table.getTightBounds()
        top_z = mx2.z
        self.table_anchor = Point3(tx, ty, top_z)
        self.table_half_x = max(0.24, (mx2.x - mn2.x) * 0.5)
        self.table_half_y = max(0.24, (mx2.y - mn2.y) * 0.5)
        return top_z

    def _build_static_glb_copy(self, src_path: str, dst_path: str) -> str | None:
        """
        Build a safe static GLB copy by stripping animation data.
        Some dealer exports crash Panda3D's loader when animations are present.
        """
        if not os.path.exists(src_path):
            return None

        try:
            if os.path.exists(dst_path) and os.path.getmtime(dst_path) >= os.path.getmtime(src_path):
                return dst_path

            with open(src_path, "rb") as fh:
                data = fh.read()

            if len(data) < 20:
                return None

            magic, version, _length = struct.unpack_from("<4sII", data, 0)
            if magic != b"glTF" or version != 2:
                return None

            offset = 12
            json_chunk = None
            bin_chunk = None
            while offset + 8 <= len(data):
                chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
                offset += 8
                chunk_data = data[offset: offset + chunk_len]
                offset += chunk_len
                if chunk_type == 0x4E4F534A:  # JSON
                    json_chunk = chunk_data
                elif chunk_type == 0x4E4942:  # BIN
                    bin_chunk = chunk_data

            if json_chunk is None:
                return None

            gltf = json.loads(json_chunk.decode("utf-8").rstrip(" \t\r\n\0"))
            gltf.pop("animations", None)

            new_json = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
            while len(new_json) % 4 != 0:
                new_json += b" "

            new_bin = bin_chunk or b""
            while len(new_bin) % 4 != 0:
                new_bin += b"\0"

            total_len = 12 + 8 + len(new_json) + (8 + len(new_bin) if new_bin else 0)
            out = bytearray()
            out += struct.pack("<4sII", b"glTF", 2, total_len)
            out += struct.pack("<II", len(new_json), 0x4E4F534A)
            out += new_json
            if new_bin:
                out += struct.pack("<II", len(new_bin), 0x4E4942)
                out += new_bin

            with open(dst_path, "wb") as fh:
                fh.write(out)
            return dst_path
        except Exception:
            return None

    def _pick_dealer_model_path(self) -> str | None:
        """Select a stable dealer model path from available files."""
        if os.path.exists("1970_gangster_soldier.glb"):
            return "1970_gangster_soldier.glb"
        if os.path.exists("new dealer.glb"):
            return "new dealer.glb"
        if os.path.exists("dealer.glb"):
            safe_copy = self._build_static_glb_copy("dealer.glb", "dealer_static.glb")
            if safe_copy and os.path.exists(safe_copy):
                return safe_copy
            return "dealer.glb"
        if os.path.exists("dealer_static.glb"):
            return "dealer_static.glb"
        if os.path.exists("the_dealer__buckshot_roulette.glb"):
            return "the_dealer__buckshot_roulette.glb"
        return None

    def _load_dealer_glb(self, dx: float, dy: float, floor_z: float) -> NodePath | None:
        """Load dealer GLB behind the table; return None when unavailable."""
        dealer_path = self._pick_dealer_model_path()
        if dealer_path is None:
            return None

        dealer = self.base.loader.loadModel(dealer_path, noCache=True)
        if dealer.isEmpty():
            return None

        dealer.reparentTo(self.render)
        dealer.setHpr(0, 90, 0)

        mn0, mx0 = dealer.getTightBounds()
        dealer_size = mx0 - mn0
        geom_count = dealer.findAllMatches("**/+GeomNode").getNumPaths()
        # Reject GLBs that are mostly scattered scene props instead of a character.
        if dealer_size.z <= 0.05 or (geom_count <= 2 and max(dealer_size.x, dealer_size.y) > dealer_size.z * 1.25):
            dealer.removeNode()
            return None

        raw_height = max(0.01, mx0.z - mn0.z)
        dealer_scale = max(0.003, min(6.0, 4.5 / raw_height))
        dealer.setScale(dealer_scale)

        mn, mx = dealer.getTightBounds()
        center_x = (mn.x + mx.x) * 0.5
        center_y = (mn.y + mx.y) * 0.5
        dealer.setPos(dx - center_x, dy - center_y, floor_z + 0.24 - mn.z)
        dealer.setShaderAuto()
        dealer.setColorScale(1.75, 1.75, 1.75, 1.0)
        dealer.setTransparency(TransparencyAttrib.M_none)
        dealer.setTwoSided(True)
        return dealer

    def _load_gun_glb(self, tx: float, ty: float, top_z: float) -> NodePath | None:
        """Load gun GLB and rest it on table top; return None when unavailable."""
        gun = self.base.loader.loadModel("gun_m1918.glb", noCache=True)
        if gun.isEmpty():
            return None

        gun.reparentTo(self.render)
        # This asset is Z-forward in source; rotate to lie naturally on the table.
        gun.setHpr(180, 90, 0)

        mn0, mx0 = gun.getTightBounds()
        span_xy = max(0.01, max(mx0.x - mn0.x, mx0.y - mn0.y))
        raw_height = max(0.01, mx0.z - mn0.z)
        target_span = max(2.2, min(3.5, self.table_half_y * 3.2))
        target_height = 0.72
        gun_scale = max(0.03, min(2.2, min(target_span / span_xy, target_height / raw_height)))
        gun.setScale(gun_scale)

        mn, mx = gun.getTightBounds()
        center_x = (mn.x + mx.x) * 0.5
        center_y = (mn.y + mx.y) * 0.5
        gun_x = tx
        gun_y = ty - self.table_half_y * 0.06
        gun_z = top_z + 0.015 - mn.z
        gun.setPos(gun_x - center_x, gun_y - center_y, gun_z)
        gun.setShaderAuto()
        gun.setColorScale(1.25, 1.25, 1.25, 1.0)
        gun.setTwoSided(True)
        return gun

    def _build_table_dealer_shotgun(self):
        suit_c    = Vec4(0.12, 0.10, 0.16, 1)
        skin_c    = Vec4(0.86, 0.74, 0.62, 1)
        gun_wood  = Vec4(0.45, 0.25, 0.10, 1)
        gun_metal = Vec4(0.62, 0.62, 0.66, 1)

        self._compute_anchors()
        tx = self.table_anchor.x
        ty = self.table_anchor.y

        # ── Table: loaded from GLB ───────────────────────────────
        tz = self._load_table_glb(tx, ty)   # tz = table top surface Z

        # ── Dealer (block figure behind the table) ───────────────
        dx = self.dealer_anchor.x
        dy = ty + max(1.95, self.table_half_y + 1.25)
        dealer_floor_z = self._sample_floor_z(dx, dy, fallback_z=tz - 0.95)
        self.dealer_anchor = Point3(dx, dy, dealer_floor_z)

        dealer_np = self._load_dealer_glb(dx, dy, dealer_floor_z)
        if dealer_np is None:
            torso = self._make_box_model(0.35, 0.2, 0.45, suit_c, "dealer_torso")
            torso.setPos(dx, dy, tz + 0.22)

            head = self._make_box_model(0.22, 0.16, 0.18, skin_c, "dealer_head")
            head.setPos(dx, dy, tz + 0.72)

            for ex in (-0.07, 0.07):
                eye = self._make_box_model(0.03, 0.01, 0.03, Vec4(0.95, 0.1, 0.1, 1), "dealer_eye")
                eye.setPos(dx + ex, dy - 0.16, tz + 0.74)
            self.dealer_root = torso
        else:
            self.dealer_root = dealer_np

        # ── Shotgun lying on table surface ───────────────────────
        gun_np = self._load_gun_glb(tx, ty, tz)
        if gun_np is None:
            gz = tz + 0.04   # resting height on table

            stock = self._make_box_model(0.07, 0.55, 0.05, gun_wood, "shotgun_stock")
            stock.setPos(tx, ty + 0.55, gz)

            recv = self._make_box_model(0.08, 0.2, 0.06, gun_metal, "shotgun_receiver")
            recv.setPos(tx, ty - 0.02, gz + 0.01)

            barrel = self._make_box_model(0.05, 0.72, 0.04, gun_metal, "shotgun_barrel")
            barrel.setPos(tx, ty - 0.62, gz + 0.02)
            self.shotgun_np = stock
        else:
            self.shotgun_np = gun_np

    def rebuild_shell_indicators(self, shells: list):
        """Draw colored shell markers on table: red=live, blue=blank."""
        for np in self.shell_indicators:
            np.removeNode()
        self.shell_indicators.clear()

        from game_state import ShellType

        total = len(shells)
        if total == 0:
            return

        spacing = max(0.08, min(0.14, self.table_half_x * 0.22))
        start_x = -(total - 1) * spacing * 0.5
        shell_y = self.table_anchor.y - self.table_half_y * 0.32
        shell_z = self.table_anchor.z + 0.08

        for i, shell in enumerate(shells):
            color = Vec4(0.95, 0.16, 0.12, 1) if shell == ShellType.LIVE else Vec4(0.2, 0.48, 0.95, 1)
            dot = self._make_box_model(0.03, 0.03, 0.03, color, "shell_dot")
            dot.setPos(self.table_anchor.x + start_x + i * spacing, shell_y, shell_z)
            self.shell_indicators.append(dot)

    def _setup_lighting(self):
        # Clear old lights in case of restart.
        self.render.clearLight()

        amb = AmbientLight("ambient")
        amb.setColor(LColor(0.42, 0.40, 0.45, 1))
        self.render.setLight(self.render.attachNewNode(amb))

        key = DirectionalLight("key_light")
        key.setColor(LColor(0.85, 0.78, 0.70, 1))
        key_np = self.render.attachNewNode(key)
        key_np.setHpr(-25, -35, 0)
        self.render.setLight(key_np)

        fill = DirectionalLight("fill_light")
        fill.setColor(LColor(0.35, 0.38, 0.50, 1))
        fill_np = self.render.attachNewNode(fill)
        fill_np.setHpr(50, -15, 0)
        self.render.setLight(fill_np)

        dealer_glow = PointLight("dealer_light")
        dealer_glow.setColor(LColor(0.9, 0.12, 0.12, 1))
        dealer_glow.setAttenuation((1, 0.08, 0.02))
        dealer_np = self.render.attachNewNode(dealer_glow)
        dealer_np.setPos(self.dealer_anchor.x, self.dealer_anchor.y, self.dealer_anchor.z + 1.6)
        self.render.setLight(dealer_np)

        table_light = PointLight("table_light")
        table_light.setColor(LColor(0.18, 0.68, 0.22, 1))
        table_light.setAttenuation((1, 0.09, 0.03))
        table_np = self.render.attachNewNode(table_light)
        table_np.setPos(self.table_anchor.x, self.table_anchor.y, self.table_anchor.z + 1.95)
        self.render.setLight(table_np)
