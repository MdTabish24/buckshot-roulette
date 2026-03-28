"""
item_animations.py — 3D animations using actual GLB models for items.
"""
import math, random
from direct.interval.IntervalGlobal import (
    LerpPosInterval, LerpHprInterval, LerpScaleInterval,
    LerpColorScaleInterval, LerpColorInterval,
    Sequence, Parallel, Func, Wait,
)
from panda3d.core import Point3, Vec3, Vec4, NodePath, TransparencyAttrib, GeomVertexReader, Quat


class ItemAnimator:
    def __init__(self, base, scene):
        self.base = base
        self.render = base.render
        self.scene = scene
        self._animating = False
        self._temp: list[NodePath] = []
        self._seq = None

    @property
    def animating(self):
        return self._animating

    # ── helpers ────────────────────────────────────────────────
    def _box(self, sx, sy, sz, color, name="p"):
        b = self.base.loader.loadModel("models/box")
        b.setName(name); b.clearTexture(); b.setTextureOff(1); b.setMaterialOff(1)
        b.setScale(sx, sy, sz); b.setColor(color)
        b.reparentTo(self.render); b.setTwoSided(True); b.setShaderAuto()
        self._temp.append(b)
        return b

    def _disc(self, radius, thickness, color, name="disc"):
        try:
            d = self.base.loader.loadModel("smiley")
        except Exception:
            return self._box(radius, radius, thickness, color, name)
        d.setName(name); d.clearTexture(); d.setTextureOff(1); d.setMaterialOff(1)
        d.setScale(radius, radius, thickness); d.setColor(color)
        d.reparentTo(self.render); d.setTwoSided(True); d.setShaderAuto()
        self._temp.append(d)
        return d

    def _load_glb(self, path, target_size=0.5, name="item", axis_fix=True, center="bottom"):
        """Load a GLB model, optionally axis-fix, auto-scale, and center."""
        try:
            raw = self.base.loader.loadModel(path, noCache=True)
            if raw is None or raw.isEmpty():
                print(f"[ItemAnim] FAILED to load: {path}")
                return None
        except Exception as e:
            print(f"[ItemAnim] Exception loading {path}: {e}")
            return None

        print(f"[ItemAnim] Loaded OK: {path}")

        # Create wrapper under render
        wrapper = self.render.attachNewNode(name + "_wrap")
        raw.reparentTo(wrapper)
        if axis_fix:
            raw.setHpr(0, 90, 0)  # Y-up → Z-up

        # Scale to target size
        try:
            mn, mx = wrapper.getTightBounds()
            size = mx - mn
            largest = max(size.x, size.y, size.z, 0.001)
            raw.setScale(target_size / largest)
        except Exception:
            raw.setScale(target_size * 0.5)

        # Center: move child so wrapper origin = model center/bottom
        try:
            mn2, mx2 = wrapper.getTightBounds()
            cx = (mn2.x + mx2.x) * 0.5
            cy = (mn2.y + mx2.y) * 0.5
            if center == "center":
                cz = (mn2.z + mx2.z) * 0.5
            else:
                cz = mn2.z
            raw.setX(raw.getX() - cx)
            raw.setY(raw.getY() - cy)
            raw.setZ(raw.getZ() - cz)
        except Exception:
            pass  # keep as-is if centering fails

        wrapper.setShaderAuto()
        wrapper.setTwoSided(True)
        wrapper.setColorScale(1.4, 1.4, 1.4, 1.0)
        self._temp.append(wrapper)
        return wrapper

    def _boost_visibility(self, node: NodePath, opaque=False):
        if node is None or node.isEmpty():
            return
        node.setShaderAuto()
        node.setTwoSided(True)
        node.setColorScale(1.9, 1.9, 1.9, 1.0)
        node.setLightOff(1)
        if opaque:
            node.setTransparency(TransparencyAttrib.M_none)

    def _face_camera(self, node: NodePath, h_off=0.0, p_off=0.0, r_off=0.0):
        if node is None or node.isEmpty():
            return
        cam = self.base.camera
        node.lookAt(cam)
        node.setHpr(node.getH() + h_off, node.getP() + p_off, node.getR() + r_off)

    def _collect_vertices_world(self, node: NodePath, limit: int = 5000):
        pts = []
        for np in node.findAllMatches("**/+GeomNode"):
            geom_node = np.node()
            mat = np.getMat(self.render)
            for gi in range(geom_node.getNumGeoms()):
                geom = geom_node.getGeom(gi)
                vdata = geom.getVertexData()
                if vdata is None:
                    continue
                reader = GeomVertexReader(vdata, "vertex")
                while not reader.isAtEnd():
                    v = reader.getData3()
                    pts.append(mat.xformPoint(v))
                    if len(pts) >= limit:
                        return pts
        return pts

    def _auto_roll_handle_down(self, node: NodePath):
        if node is None or node.isEmpty():
            return
        pts = self._collect_vertices_world(node)
        if not pts:
            return

        # Center in world space
        center = Vec3(0, 0, 0)
        for p in pts:
            center += p
        center /= len(pts)

        fwd = node.getQuat(self.render).getForward()
        if fwd.lengthSquared() < 1e-6:
            return
        fwd.normalize()

        down = Vec3(0, 0, -1)
        down_proj = down - fwd * down.dot(fwd)
        if down_proj.lengthSquared() < 1e-6:
            return
        down_proj.normalize()

        # Build plane basis (u, v) perpendicular to fwd
        up = Vec3(0, 0, 1)
        u = fwd.cross(up)
        if u.lengthSquared() < 1e-6:
            u = fwd.cross(Vec3(1, 0, 0))
        if u.lengthSquared() < 1e-6:
            return
        u.normalize()
        v = fwd.cross(u)
        v.normalize()

        # Find direction of maximum radius in the lens plane (handle direction)
        max_r2 = -1.0
        ang = 0.0
        for p in pts:
            rel = p - center
            x = rel.dot(u)
            y = rel.dot(v)
            r2 = x * x + y * y
            if r2 > max_r2:
                max_r2 = r2
                ang = math.atan2(y, x)

        handle_dir = (u * math.cos(ang) + v * math.sin(ang))
        if handle_dir.lengthSquared() < 1e-6:
            return
        handle_dir.normalize()

        dot = max(-1.0, min(1.0, handle_dir.dot(down_proj)))
        angle = math.degrees(math.acos(dot))
        # Determine sign using right-hand rule around fwd
        if handle_dir.cross(down_proj).dot(fwd) < 0:
            angle = -angle

        if abs(angle) < 0.01:
            return

        rot = Quat()
        rot.setFromAxisAngle(angle, fwd)
        node.setQuat(self.render, rot * node.getQuat(self.render))

    def _cleanup(self):
        for n in self._temp:
            if not n.isEmpty(): n.removeNode()
        self._temp.clear()
        self._animating = False

    def _done(self, cb):
        self._cleanup()
        if cb: cb()

    def _simple_load(self, path, target_size, name):
        """Load GLB with centering + axis fix (more reliable for mixed assets)."""
        # Historically this was a raw loader, but some GLBs had off-center origins
        # or inverted normals. Reuse the safer loader to keep items visible.
        return self._load_glb(path, target_size=target_size, name=name)

    def _tpos(self, dx=0, dy=0, dz=0):
        t = self.scene.table_anchor
        return Point3(t.x+dx, t.y+dy, t.z+dz)

    def _gpos(self, dx=0, dy=0, dz=0):
        g = self.scene.shotgun_np
        if g and not g.isEmpty():
            p = g.getPos()
            return Point3(p.x+dx, p.y+dy, p.z+dz)
        return self._tpos(dx, dy, dz+0.15)

    def _dpos(self, dx=0, dy=0, dz=0):
        d = self.scene.dealer_anchor
        return Point3(d.x+dx, d.y+dy, d.z+dz)

    # ── dispatch ──────────────────────────────────────────────
    def play(self, item_type, user="player", on_complete=None):
        from game_state import ItemType
        if self._animating: return
        self._animating = True
        fn = {
            ItemType.MAGNIFYING_GLASS: lambda cb: self._magnifying_glass(cb, user),
            ItemType.BEER: lambda cb: self._beer(cb, user),
            ItemType.CIGARETTE: lambda cb: self._cigarette(cb, user),
            ItemType.HANDSAW: lambda cb: self._handsaw(cb, user),
            ItemType.INVERTER: lambda cb: self._inverter(cb, user),
            ItemType.HANDCUFFS: lambda cb: self._handcuffs(cb, user),
        }.get(item_type)
        if fn: fn(on_complete)
        else:
            self._animating = False
            if on_complete: on_complete()

    # ══════════════════════════════════════════════════════════
    # 1. MAGNIFYING GLASS — styled_magnifying_glass.glb
    # ══════════════════════════════════════════════════════════
    def _magnifying_glass(self, cb, user="player"):
        # Smaller scale + tighter offsets so it doesn't dwarf the gun
        mg = self._load_glb("styled_magnifying_glass.glb", target_size=1.4, name="magnifying",
                            axis_fix=False, center="center")
        if mg is None:
            mg = self._box(0.35, 0.35, 1.0, Vec4(0.75, 0.58, 0.18, 1), "mg_fb")
        self._boost_visibility(mg, opaque=True)

        glow = self._disc(0.50, 0.06, Vec4(1, 1, 0.7, 0), "mg_glow")
        glow.setTransparency(TransparencyAttrib.M_alpha)

        if user == "dealer":
            start = self._tpos(0, 0.5, 0.2)
            high = self._tpos(0, 0.2, 0.6)
            examine = self._gpos(0.0, 0.2, 0.4) 
        else:
            # Slightly left/down so the gun sits inside the lens
            start = self._gpos(-0.04, -0.08, 0.34)
            high = self._gpos(-0.02, -0.04, 0.95)
            examine = self._gpos(-0.06, -0.22, 0.56)

        mg.setPos(start)
        glow.setPos(start)

        # Make lens face the camera, then auto-roll so handle points downward
        if user == "player":
            self._face_camera(mg, p_off=-90.0)
            self._auto_roll_handle_down(mg)
        else:
            # Face dealer instead
            mg.lookAt(self._dpos(0, 0, 1.8), Vec3(0,0,1))
            mg.setP(mg.getP() - 90)

        base_hpr = mg.getHpr()

        self._seq = Sequence(
            LerpPosInterval(mg, 0.5, high, blendType="easeOut"),
            Wait(0.2),
            LerpPosInterval(mg, 0.5, examine, blendType="easeInOut"),
            Parallel(
                LerpHprInterval(mg, 0.4, Point3(base_hpr.x+15, base_hpr.y+10, base_hpr.z)),
                Sequence(
                    Func(lambda: glow.setPos(examine)),
                    LerpColorScaleInterval(glow, 0.15, Vec4(1,1,0.7,0.9)),
                    LerpColorScaleInterval(glow, 0.15, Vec4(1,1,0.7,0)),
                    LerpColorScaleInterval(glow, 0.15, Vec4(1,1,0.7,0.85)),
                    LerpColorScaleInterval(glow, 0.15, Vec4(1,1,0.7,0)),
                ),
            ),
            Wait(0.3),
            Parallel(
                LerpPosInterval(mg, 0.5, high, blendType="easeIn"),
                LerpColorScaleInterval(mg, 0.5, Vec4(1,1,1,0)),
            ),
            Func(self._done, cb),
        )
        self._seq.start()

    # ══════════════════════════════════════════════════════════
    # 2. BEER — beer_can.glb
    # ══════════════════════════════════════════════════════════
    def _beer(self, cb, user="player"):
        beer = self._load_glb("beer_can.glb", target_size=1.3, name="beer")
        if beer is None:
            beer = self._box(0.12, 0.12, 0.42, Vec4(0.45,0.28,0.08,1), "beer_fb")

        # Ejected shell
        shell = self._box(0.06, 0.06, 0.16, Vec4(0.85,0.3,0.1,1), "shell")
        shell.setColorScale(1,1,1,0)

        if user == "dealer":
            s = self._tpos(0.55, 0.5, 0.08)
            lift = self._dpos(0.2, 0.2, 1.4)
            discard = self._tpos(-0.7, 0.5, -0.5)
        else:
            s = self._tpos(0.55, 0.15, 0.08)
            lift = self._tpos(0.55,0.15,0.85)
            discard = self._tpos(-0.7,0.5,-0.5)

        beer.setPos(s)
        shell.setPos(self._gpos(0, -0.15, 0.15))
        gn = self._gpos(0.15, -0.1, 0.55) if user == "player" else self._gpos(0.15, 0.1, 0.55)

        self._seq = Sequence(
            # Lift
            LerpPosInterval(beer, 0.35, lift, blendType="easeOut"),
            # Tilt toward gun
            Parallel(
                LerpPosInterval(beer, 0.45, gn, blendType="easeInOut"),
                LerpHprInterval(beer, 0.45, Point3(beer.getH(), beer.getP()-45, beer.getR()), blendType="easeInOut"),
            ),
            # Shell ejects
            Func(lambda: shell.setColorScale(1,1,1,1)),
            Parallel(
                LerpPosInterval(shell, 0.4, self._tpos(0.3,-0.4,0.08), blendType="easeIn"),
                LerpHprInterval(shell, 0.4, Point3(90,45,0)),
            ),
            Wait(0.2),
            # Discard
            Parallel(
                LerpPosInterval(beer, 0.35, discard, blendType="easeIn"),
                LerpHprInterval(beer, 0.35, Point3(60,120,0)),
                LerpColorScaleInterval(beer, 0.35, Vec4(1,1,1,0)),
                LerpColorScaleInterval(shell, 0.35, Vec4(1,1,1,0)),
            ),
            Func(self._done, cb),
        )
        self._seq.start()

    # ══════════════════════════════════════════════════════════
    # 3. CIGARETTE — cigarette_-_daily3d.glb
    # ══════════════════════════════════════════════════════════
    def _cigarette(self, cb, user="player"):
        # Orient so the cigarette faces the camera (end-cap toward player)
        cig = self._load_glb("cigarette_-_daily3d.glb", target_size=1.2, name="cig",
                             axis_fix=False, center="center")
        if cig is None:
            cig = self._box(0.035, 0.035, 0.28, Vec4(0.95,0.92,0.85,1), "cig_fb")
        else:
            if user == "player":
                self._face_camera(cig, h_off=90.0)
            else:
                cig.lookAt(self._dpos(0,0,1.72))
                cig.setH(cig.getH() + 90)

        # Lighter
        lighter = self._box(0.07, 0.045, 0.14, Vec4(0.3,0.3,0.35,1), "ltr")
        flame = self._box(0.03, 0.03, 0.07, Vec4(1,0.7,0.1,0.9), "flm")
        flame.setTransparency(TransparencyAttrib.M_alpha)
        flame.setColorScale(1,1,1,0)

        if user == "dealer":
            s = self._tpos(0.4, 0.4, 0.08)
            lifted = self._dpos(0.2, 0.3, 1.2)
            cp = self._dpos(0, 0, 1.6)
            mouth = Point3(cp.x, cp.y-0.2, cp.z-0.1)
        else:
            s = self._tpos(-0.4, -0.2, 0.08)
            lifted = self._tpos(-0.4, -0.2, 0.75)
            cp = self.base.camera.getPos()
            mouth = Point3(cp.x, cp.y+1.8, cp.z-0.5)

        cig.setPos(s)
        if user == "dealer":
            lighter.setPos(self._tpos(0.55, 0.4, 0.08))
        else:
            lighter.setPos(self._tpos(-0.55, -0.15, 0.08))

        lnear = Point3(lifted.x+0.15, lifted.y, lifted.z+0.1)

        # Smoke puffs
        smokes = []
        for i in range(8):
            sm = self._disc(0.08, 0.08, Vec4(0.78,0.78,0.78,0.55), f"sm{i}")
            sm.setTransparency(TransparencyAttrib.M_alpha)
            sm.setColorScale(1,1,1,0); sm.setPos(mouth)
            smokes.append(sm)

        smoke_par = []
        for i, sm in enumerate(smokes):
            a = i*45; dx=0.35*math.cos(math.radians(a)); dy=0.25*math.sin(math.radians(a))
            dz=0.2+random.uniform(0,0.25)
            smoke_par.append(Sequence(
                Wait(i*0.06),
                Func(lambda s=sm: s.setColorScale(1,1,1,0.55)),
                Parallel(
                    LerpPosInterval(sm, 0.9, Point3(mouth.x+dx,mouth.y+dy,mouth.z+dz), blendType="easeOut"),
                    LerpScaleInterval(sm, 0.9, 0.28, blendType="easeOut"),
                    LerpColorScaleInterval(sm, 0.9, Vec4(1,1,1,0)),
                ),
            ))

        self._seq = Sequence(
            # Pick up cig + lighter
            Parallel(
                LerpPosInterval(cig, 0.3, lifted, blendType="easeOut"),
                LerpPosInterval(lighter, 0.3, Point3(lnear.x,lnear.y,lnear.z-0.1), blendType="easeOut"),
            ),
            # Lighter flick
            Parallel(
                LerpPosInterval(lighter, 0.2, lnear, blendType="easeOut"),
                Sequence(
                    Func(lambda: flame.setPos(lnear.x,lnear.y,lnear.z+0.08)),
                    LerpColorScaleInterval(flame, 0.12, Vec4(1,1,1,0.95)),
                ),
            ),
            Wait(0.3),
            # Hide lighter
            Parallel(
                LerpColorScaleInterval(lighter, 0.2, Vec4(1,1,1,0)),
                LerpColorScaleInterval(flame, 0.2, Vec4(1,1,1,0)),
            ),
            # Bring to mouth
            LerpPosInterval(cig, 0.4, mouth, blendType="easeInOut"),
            Func(self._face_camera, cig, 90.0, 0.0, 0.0),
            Wait(0.3),
            # Exhale smoke
            Parallel(*smoke_par),
            Wait(0.25),
            # Fade out
            LerpColorScaleInterval(cig, 0.3, Vec4(1,1,1,0)),
            Func(self._done, cb),
        )
        self._seq.start()

    # ══════════════════════════════════════════════════════════
    # 4. HAND SAW — old_rusty_handsaw.glb
    # ══════════════════════════════════════════════════════════
    def _handsaw(self, cb, user="player"):
        saw = self._load_glb("old_rusty_handsaw.glb", target_size=1.8, name="saw")
        if saw is None:
            saw = self._box(0.03, 0.50, 0.16, Vec4(0.72,0.73,0.76,1), "saw_fb")

        s = self._tpos(0.5, 0.3, 0.08) if user == "dealer" else self._tpos(0.5, -0.3, 0.08)
        saw.setPos(s)
        gc = self._gpos(0, 0.08, 0.18)

        # Sparks
        sparks = []
        for i in range(12):
            sp = self._box(0.02,0.02,0.02, Vec4(1,0.85,0.2,1), f"sp{i}")
            sp.setColorScale(1,1,1,0); sp.setPos(gc)
            sparks.append(sp)

        def burst():
            for sp in sparks:
                sp.setPos(gc); sp.setColorScale(1,1,1,1); sp.setScale(0.02)
                t = Point3(gc.x+random.uniform(-0.45,0.45), gc.y+random.uniform(-0.25,0.25), gc.z+random.uniform(0.1,0.55))
                Sequence(Parallel(
                    LerpPosInterval(sp, 0.35, t, blendType="easeOut"),
                    LerpColorScaleInterval(sp, 0.35, Vec4(1,1,1,0)),
                )).start()

        # Sawing positions (along gun barrel)
        saw_base_hpr = Point3(saw.getH(), saw.getP(), saw.getR())
        sf = Point3(gc.x, gc.y-0.30, gc.z)
        sb = Point3(gc.x, gc.y+0.30, gc.z)

        self._seq = Sequence(
            # Pick up
            LerpPosInterval(saw, 0.3, self._tpos(0.5,0.3,0.75), blendType="easeOut"),
            # Move to gun
            LerpPosInterval(saw, 0.38, gc, blendType="easeInOut"),
            # Sawing strokes
            LerpPosInterval(saw, 0.18, sf),
            Func(burst),
            LerpPosInterval(saw, 0.18, sb),
            Func(burst),
            LerpPosInterval(saw, 0.18, sf),
            Func(burst),
            LerpPosInterval(saw, 0.15, gc),
            Wait(0.2),
            # Return and fade
            Parallel(
                LerpPosInterval(saw, 0.35, s, blendType="easeIn"),
                LerpColorScaleInterval(saw, 0.35, Vec4(1,1,1,0)),
            ),
            Func(self._done, cb),
        )
        self._seq.start()

    # ══════════════════════════════════════════════════════════
    # 5. INVERTER — inverter.glb
    # ══════════════════════════════════════════════════════════
    def _inverter(self, cb, user="player"):
        dev = self._load_glb("inverter.glb", target_size=1.0, name="inv")
        if dev is None:
            dev = self._box(0.18, 0.12, 0.22, Vec4(0.15,0.12,0.28,1), "inv_fb")

        # LED + flash effects
        led = self._box(0.04, 0.04, 0.04, Vec4(0.2,0.8,1.0,1), "led")
        flash = self._disc(0.35, 0.35, Vec4(0.4,0.7,1.0,0), "fl")
        flash.setTransparency(TransparencyAttrib.M_alpha)

        if user == "dealer":
            s = self._tpos(0.4, 0.5, 0.08)
            lift = self._tpos(0.4, 0.5, 0.7)
            gt = self._gpos(0.12, 0.15, 0.40)
        else:
            s = self._tpos(0.4, -0.3, 0.08)
            lift = self._tpos(0.4, -0.3, 0.7)
            gt = self._gpos(0.12, -0.15, 0.40)

        dev.setPos(s)
        led.setPos(s.x, s.y, s.z+0.25)
        lt = Point3(gt.x, gt.y, gt.z+0.25)
        flash.setPos(gt)

        self._seq = Sequence(
            # Pick up
            Parallel(
                LerpPosInterval(dev, 0.3, lift, blendType="easeOut"),
                LerpPosInterval(led, 0.3, Point3(lift.x, lift.y, lift.z+0.25), blendType="easeOut"),
            ),
            # Move to gun
            Parallel(
                LerpPosInterval(dev, 0.4, gt, blendType="easeInOut"),
                LerpPosInterval(led, 0.4, lt, blendType="easeInOut"),
            ),
            # LED blinks + flash
            Parallel(
                Sequence(
                    LerpColorInterval(led, 0.1, Vec4(1,0.2,0.2,1)),
                    LerpColorInterval(led, 0.1, Vec4(0.2,0.8,1,1)),
                    LerpColorInterval(led, 0.1, Vec4(1,0.2,0.2,1)),
                    LerpColorInterval(led, 0.1, Vec4(0.2,1,0.3,1)),
                    LerpColorInterval(led, 0.1, Vec4(1,1,0.2,1)),
                ),
                Sequence(
                    Wait(0.25),
                    LerpColorScaleInterval(flash, 0.1, Vec4(1,1,1,0.8)),
                    LerpColorScaleInterval(flash, 0.18, Vec4(1,1,1,0)),
                ),
            ),
            Wait(0.2),
            # Lower back
            Parallel(
                LerpPosInterval(dev, 0.35, s, blendType="easeIn"),
                LerpPosInterval(led, 0.35, Point3(s.x,s.y,s.z+0.25), blendType="easeIn"),
                LerpColorScaleInterval(dev, 0.35, Vec4(1,1,1,0)),
                LerpColorScaleInterval(led, 0.35, Vec4(1,1,1,0)),
            ),
            Func(self._done, cb),
        )
        self._seq.start()

    # ══════════════════════════════════════════════════════════
    # 6. HANDCUFFS — handcuffs.glb
    # ══════════════════════════════════════════════════════════
    def _handcuffs(self, cb, user="player"):
        cuffs = self._load_glb("handcuffs.glb", target_size=2.0, name="handcuffs",
                               axis_fix=False, center="center")
        if cuffs is None:
            cuffs = self._box(0.35, 0.20, 0.10, Vec4(0.68,0.68,0.72,1), "cuffs_fb")
        self._boost_visibility(cuffs, opaque=True)

        flash = self._disc(0.40, 0.40, Vec4(0.9,0.9,1.0,0), "cf")
        flash.setTransparency(TransparencyAttrib.M_alpha)

        # Start based on user towards opponent
        if user == "dealer":
            start = self._dpos(0, 0.2, 1.2)
            # Throw towards player (camera)
            cp = self.base.camera.getPos()
            target = Point3(cp.x, cp.y+2.0, cp.z-0.5)
        else:
            start = self._gpos(0, 0, 0.5)
            target = self._dpos(0, -0.4, 0.8)
        cuffs.setPos(start)

        if user == "dealer":
            high = Point3(start.x, start.y, start.z + 1.0)
            wrist = target
        else:
            high = self._gpos(0, 0, 2.0)
            wrist = self._dpos(0, -0.5, 1.5)

        self._seq = Sequence(
            # Float up high
            LerpPosInterval(cuffs, 0.4, high, blendType="easeOut"),
            Wait(0.2),
            # Fly toward opponent
            LerpPosInterval(cuffs, 0.6, wrist, blendType="easeInOut"),
            # Snap + flash
            Func(lambda: flash.setPos(wrist)),
            Parallel(
                LerpColorScaleInterval(flash, 0.12, Vec4(1,1,1,0.9)),
                LerpScaleInterval(cuffs, 0.12, cuffs.getScale() * 0.85),
            ),
            LerpColorScaleInterval(flash, 0.15, Vec4(1,1,1,0)),
            Wait(0.5),
            # Fade
            LerpColorScaleInterval(cuffs, 0.4, Vec4(1,1,1,0)),
            Func(self._done, cb),
        )
        self._seq.start()
