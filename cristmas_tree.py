import math
import numpy as np
import pygame

TITLE = "ASCII Christmas Tree"
COLS, ROWS = 180,68
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · F fullscreen · Esc quit"
DIM, ACCENT, SIGN = (96, 104, 122), (255, 196, 98), (170, 168, 196)


TAU = 2 * math.pi
Y0, Y1 = 1.65, -1.25
GROUND = -1.35
T_STAR = 10.5
T_MSG = 12.2
MESSAGE = "MERRY CHRISTMAS 2027"


GOLD = (255, 205, 85)
RED = (235, 65, 75)
GREEN_BOX = (65, 200, 110)
T_GARLAND = [(255, 215, 100), (255, 245, 180)]
T_LIGHTS = [(255, 230, 130), (255, 120, 120), (120, 210, 255), (150, 255, 150)]
T_BALLS = [(225, 50, 60), (245, 195, 75), (210, 215, 225)]

# Градация символов ASCII
RAMP = np.array(list(" .:-=+*#%@"))


def envelope(y):
    u = np.clip((y - Y0) / (Y1 - Y0), 0.0, 1.0)
    return 0.06 + 1.05 * (u**0.92)


class Points:
    def __init__(self):
        self.xyz = []
        self.rgb = []
        self.t_show = []
        self.kind = []
        self.phase = []

    def add(self, pts, col, t_on, kind=0, phase=None):
        n = len(pts)
        if n == 0:
            return
        self.xyz.append(pts)
        if col.ndim == 1:
            col = np.broadcast_to(col, (n, 3))
        self.rgb.append(col)
        if np.ndim(t_on) == 0:
            t_on = np.full(n, t_on)
        self.t_show.append(t_on)
        self.kind.append(np.full(n, kind, dtype=np.int32))
        if phase is None:
            phase = np.zeros(n)
        elif np.ndim(phase) == 0:
            phase = np.full(n, phase)
        self.phase.append(phase)

    def finalize(self):
        self.xyz = np.vstack(self.xyz)
        self.rgb = np.vstack(self.rgb)
        self.t_show = np.concatenate(self.t_show)
        self.kind = np.concatenate(self.kind)
        self.phase = np.concatenate(self.phase)


def fib_sphere(n):
    i = np.arange(n, dtype=float)
    phi = np.arccos(1 - 2 * (i + 0.5) / n)
    theta = np.pi * (1 + 5**0.5) * i
    return np.column_stack(
        [np.sin(phi) * np.cos(theta), np.cos(phi), np.sin(phi) * np.sin(theta)]
    )


def build():
    rng = np.random.default_rng(42)
    q = Points()
    tips = []

    # 1. Ветви и хвоя
    for i, y in enumerate(np.linspace(Y0 + 0.02, Y1 - 0.06, 24)):
        u = (y - Y0) / (Y1 - Y0)
        R = envelope(y) + 0.05
        nb = int(6 + 11 * (1 - u))
        for b in range(nb):
            a = TAU * (b + 0.5 * rng.random()) / nb + i * 0.77
            L = R * rng.uniform(0.85, 1.08)
            n = int(25 + 170 * L)
            s = rng.random(n) ** 0.65
            d = np.array([np.cos(a), 0.0, np.sin(a)])
            side = np.array([-np.sin(a), 0.0, np.cos(a)])
            spread = (0.025 + 0.08 * s)[:, None] * rng.normal(0, 1, (n, 3))

            p = d * s[:, None] * L + side * spread[:, :1]
            p[:, 1] += y - 0.14 * (s**1.3) - 0.03 * s + 0.012 * rng.normal(0, 1, n)
            p[:, 0] += spread[:, 0]
            p[:, 2] += spread[:, 2]

            nrm = (p - np.array([0, y, 0])) / (L + 0.1)
            snow = (s > 0.5) & (rng.random(n) < 0.06) & (nrm[:, 1] > 0.0)
            green = np.array([0.10, 0.48, 0.18]) + np.array([0.12, 0.30, 0.14]) * rng.random((n, 1))
            col = np.where(snow[:, None], np.array([0.88, 0.92, 0.98]), green)

            t_on = 0.4 + 2.6 * u + 0.4 * s
            q.add(p, col, t_on)
            tips.append([d[0] * L, y - 0.17 * L, d[2] * L])

    tips = np.array(tips)

    # 2. Внутренний темный конус
    m = 5000
    y = Y0 + (Y1 - Y0) * (rng.random(m) ** 0.8)
    phi = rng.random(m) * TAU
    out = np.column_stack([np.cos(phi), np.zeros(m), np.sin(phi)])
    r = 0.6 * envelope(y)
    q.add(
        out * r[:, None] + np.column_stack([np.zeros(m), y, np.zeros(m)]),
        np.array([0.05, 0.22, 0.09]),
        0.5 + 2.5 * ((y - Y0) / (Y1 - Y0)),
    )

    # 3. Ствол дерева
    m = 1200
    y = Y1 + (GROUND - Y1) * rng.random(m)
    phi = rng.random(m) * TAU
    n_vec = np.column_stack([np.cos(phi), np.zeros(m), np.sin(phi)])
    bark = 0.75 + 0.25 * np.sign(np.sin(phi * 30 + y * 5))
    r_trunk = 0.11 + 0.03 * ((y - Y1) / (GROUND - Y1))
    q.add(
        n_vec * r_trunk[:, None] + np.column_stack([np.zeros(m), y, np.zeros(m)]),
        np.array([0.42, 0.26, 0.14]) * bark[:, None],
        3.2 + 0.8 * rng.random(m),
    )

    # 4. Золотая спиральная гирлянда
    w = np.linspace(0, 1, 1800)
    turns = 3.6
    yg = Y0 + 0.12 + (Y1 - Y0 - 0.2) * w
    ag = TAU * turns * w + 0.8
    swag = -0.07 * np.abs(np.sin(ag * 2.5))
    rg = envelope(yg) + 0.07
    line = np.column_stack([rg * np.cos(ag), yg + swag, rg * np.sin(ag)])
    for _ in range(3):
        pts_g = line + rng.normal(0, 0.015, line.shape)
        col_g = np.where(
            rng.random((len(pts_g), 1)) < 0.7,
            np.array(T_GARLAND[0]) / 255.0,
            np.array(T_GARLAND[1]) / 255.0,
        )
        q.add(pts_g, col_g, 4.2 + 2.0 * w, kind=1, phase=rng.random(len(pts_g)) * TAU)

    # 5. Елочные шары
    pick_b = rng.choice(len(tips), size=min(65, len(tips)), replace=False)
    bulb = fib_sphere(22)
    for idx in pick_b:
        c = tips[idx] + np.array([0, -0.03, 0])
        k = rng.integers(0, len(T_BALLS))
        base_col = np.array(T_BALLS[k]) / 255.0
        pts_b = c + bulb * 0.042
        stripe = np.sin(bulb[:, 1] * 14 + bulb[:, 0] * 6) > 0
        col_b = np.where(stripe[:, None], base_col, np.array([0.95, 0.95, 0.98]))
        q.add(pts_b, col_b, 6.2 + rng.random() * 1.5, kind=2)

    # 6. Огоньки
    pick_l = rng.choice(len(tips), size=min(140, len(tips)), replace=False)
    light_bulb = fib_sphere(10)
    for idx in pick_l:
        c = tips[idx]
        col_l = np.array(T_LIGHTS[rng.integers(0, len(T_LIGHTS))]) / 255.0
        q.add(
            c + light_bulb * 0.022,
            col_l,
            7.5 + rng.random() * 1.5,
            kind=1,
            phase=rng.random() * TAU,
        )

    # 7. Подарки под елкой
    gifts = [
        (0.0, 1.12, 0.36, 0.26, 0.34, RED, GOLD),
        (1.5, 1.18, 0.26, 0.30, 0.26, GREEN_BOX, RED),
        (2.6, 1.10, 0.34, 0.20, 0.32, GOLD, RED),
        (3.7, 1.18, 0.28, 0.28, 0.28, RED, GREEN_BOX),
        (4.7, 1.12, 0.30, 0.22, 0.30, GREEN_BOX, GOLD),
        (5.6, 1.16, 0.26, 0.24, 0.26, GOLD, RED),
    ]
    for g, dist, w_b, h_b, d_b, box_c, rib_c in gifts:
        n_pts = 950
        u1 = rng.uniform(-0.5, 0.5, n_pts)
        u2 = rng.uniform(-0.5, 0.5, n_pts)
        face = rng.integers(0, 5, n_pts)
        lx = np.select([face == 0, face == 1], [0.5, -0.5], default=u1)
        ly = np.where((face != 2), u2, 0.5)
        lz = np.where((face == 2), u2, np.where((face == 0) | (face == 1), u1, np.select([face == 3, face == 4], [0.5, -0.5], default=u2)))

        on_x = np.abs(lx) < 0.08
        on_z = np.abs(lz) < 0.08
        on_y = np.abs(ly) < 0.09
        is_rib = (on_x & (face != 0) & (face != 1)) | (on_z & (face != 3) & (face != 4)) | (on_y & (face != 2))

        pts_box = np.column_stack([lx * w_b, (ly + 0.5) * h_b, lz * d_b])
        ca, sa = math.cos(g), math.sin(g)
        rot_x = pts_box[:, 0] * ca - pts_box[:, 2] * sa + dist * ca
        rot_z = pts_box[:, 0] * sa + pts_box[:, 2] * ca + dist * sa
        rot_y = pts_box[:, 1] + GROUND

        col_box = np.where(is_rib[:, None], np.array(rib_c) / 255.0, np.array(box_c) / 255.0)
        q.add(np.column_stack([rot_x, rot_y, rot_z]), col_box, 8.8 + rng.random(n_pts) * 1.4)

    # 8. Звезда на макушке
    star_pts = []
    for k in range(5):
        ang1 = TAU * k / 5 + math.pi / 2
        ang2 = ang1 + TAU / 10
        tip = np.array([0.22 * math.cos(ang1), 0.22 * math.sin(ang1), 0.0])
        valley = np.array([0.09 * math.cos(ang2), 0.09 * math.sin(ang2), 0.0])
        for t_s in np.linspace(0, 1, 35):
            for z_off in (-0.03, 0.0, 0.03):
                star_pts.append(tip * t_s + np.array([0, 0, z_off * (1 - t_s)]))
                star_pts.append(valley * t_s + np.array([0, 0, z_off * (1 - t_s)]))
    star_pts = np.array(star_pts) + np.array([0.0, Y0 + 0.16, 0.0])
    q.add(star_pts, np.array(GOLD) / 255.0, T_STAR, kind=1)

    q.finalize()
    return q


def project(pts, yaw, pitch=-0.20, dist=10, fov=2.3):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    x = pts[:, 0] * cy - pts[:, 2] * sy
    z = pts[:, 0] * sy + pts[:, 2] * cy
    y = pts[:, 1] * cp - z * sp
    z2 = pts[:, 1] * sp + z * cp + dist

    z2 = np.maximum(z2, 0.2)
    scale = fov / z2
    return x * scale, -y * scale, z2


class Renderer:
    def __init__(self, cols, rows, target_w, target_h):
        self.cols, self.rows = cols, rows
        # Автоподбор размера ячейки под доступную область экрана
        self.ch = max(6, target_h // rows)
        self.cw = max(4, min(target_w // cols, int(self.ch * 0.65)))
        self.w = self.cols * self.cw
        self.h = self.rows * self.ch
        self.font_px = max(7, int(self.ch * 1.05))

        self.font = pygame.font.SysFont(MONO, self.font_px, bold=True)
        self.hud_font = pygame.font.SysFont(MONO, max(10, int(self.ch * 0.85)))

        atlas = []
        for code in range(32, 127):
            s = pygame.Surface((self.cw, self.ch))
            g = self.font.render(chr(code), True, (255, 255, 255))
            s.blit(g, ((self.cw - g.get_width()) // 2, (self.ch - g.get_height()) // 2))
            atlas.append(pygame.surfarray.array3d(s)[:, :, 0])
        self.atlas = np.stack(atlas)

    def render(self, char_grid, col_grid):
        idx = np.clip(char_grid - 32, 0, 94)
        glyphs = self.atlas[idx]
        rgb = (glyphs[..., None].astype(np.float32) / 255.0) * col_grid[:, :, None, None, :]
        img = rgb.transpose(1, 2, 0, 3, 4).reshape(self.w, self.h, 3).astype(np.uint8)
        return pygame.surfarray.make_surface(img)


def main():
    pygame.init()
    # Определяем разрешение монитора и берем 85% от высоты
    info = pygame.display.Info()
    init_h = int(info.current_h * 0.85)
    init_w = int(init_h * (COLS * 0.65) / ROWS)

    renderer = Renderer(COLS, ROWS, init_w, init_h)
    screen = pygame.display.set_mode((renderer.w, renderer.h), pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    tree = build()

    rng = np.random.default_rng(7)
    n_snow = 220
    snow_x = rng.uniform(-2.2, 2.2, n_snow)
    snow_y = rng.uniform(-1.8, 2.2, n_snow)
    snow_z = rng.uniform(-2.0, 2.0, n_snow)
    snow_spd = rng.uniform(0.25, 0.65, n_snow)

    t = 0.0
    paused = False
    fullscreen = False

    while True:
        dt = clock.tick(30) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                renderer = Renderer(COLS, ROWS, event.w, event.h)
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    t = 0.0
                    tree = build()
                elif event.key == pygame.K_s:
                    pygame.image.save(screen, f"tree_{t:.1f}.png")
                elif event.key == pygame.K_f:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        sw, sh = screen.get_size()
                        renderer = Renderer(COLS, ROWS, sw, sh)
                    else:
                        renderer = Renderer(COLS, ROWS, init_w, init_h)
                        screen = pygame.display.set_mode((renderer.w, renderer.h), pygame.RESIZABLE)

        if not paused:
            t += dt

        char_grid = np.full((ROWS, COLS), 32, dtype=np.int32)
        col_grid = np.zeros((ROWS, COLS, 3), dtype=np.float32)
        z_buf = np.full((ROWS, COLS), 999.0, dtype=np.float32)

        aspect = renderer.w / max(1, renderer.h)
        yaw = t * 0.55

        # 1. Снег
        sy_curr = ((snow_y - t * snow_spd + 1.8) % 4.0) - 1.8
        s_pts = np.column_stack([snow_x, sy_curr, snow_z])
        px, py, pz = project(s_pts, yaw * 0.3)
        sc = ((px / aspect + 0.5) * COLS).astype(int)
        sr = ((py + 0.5) * ROWS).astype(int)
        valid_s = (sc >= 0) & (sc < COLS) & (sr >= 0) & (sr < ROWS)
        for c, r, z in zip(sc[valid_s], sr[valid_s], pz[valid_s]):
            if z < z_buf[r, c]:
                z_buf[r, c] = z
                char_grid[r, c] = ord("*") if z < 4.5 else ord(".")
                col_grid[r, c] = (140, 155, 185)

        # 2. Елка и игрушки
        vis = tree.t_show <= t
        if np.any(vis):
            pts = tree.xyz[vis]
            cols_p = tree.rgb[vis].copy()
            kinds = tree.kind[vis]
            phases = tree.phase[vis]

            blink = 0.65 + 0.35 * np.sin(t * 5.0 + phases)
            cols_p[kinds == 1] *= blink[kinds == 1, None]

            if t >= T_STAR:
                flash = math.exp(-((t - T_STAR) / 1.0) ** 2) * 1.4
                cols_p = np.clip(cols_p + flash * 0.25, 0, 1.3)

            px, py, pz = project(pts, yaw)
            gc = ((px / aspect + 0.5) * COLS).astype(int)
            gr = ((py + 0.5) * ROWS).astype(int)
            valid = (gc >= 0) & (gc < COLS) & (gr >= 0) & (gr < ROWS)

            order = np.argsort(pz[valid])
            gc_v = gc[valid][order]
            gr_v = gr[valid][order]
            pz_v = pz[valid][order]
            col_v = cols_p[valid][order]
            knd_v = kinds[valid][order]

            for c, r, z, rgb, k in zip(gc_v, gr_v, pz_v, col_v, knd_v):
                if z < z_buf[r, c]:
                    z_buf[r, c] = z
                    shade = np.clip(1.45 - (z - 8) * 0.22, 0.35, 1.25)
                    lum = float(np.mean(rgb)) * shade
                    ch_idx = int(np.clip(lum * (len(RAMP) - 1), 1, len(RAMP) - 1))
                    if k == 1:
                        ch_idx = len(RAMP) - 1
                    char_grid[r, c] = ord(RAMP[ch_idx])
                    col_grid[r, c] = np.clip(rgb * shade * 255, 0, 255)

        # 3. Поздравление
        if t >= T_MSG:
            row = ROWS - 6
            c0 = (COLS - len(MESSAGE)) // 2
            shown = min(len(MESSAGE), int((t - T_MSG) * 18))
            char_grid[row - 1 : row + 2, max(0, c0 - 2) : min(COLS, c0 + shown + 2)] = 32
            for i, ch in enumerate(MESSAGE[:shown]):
                if ch == " ":
                    continue
                tint = [RED, GOLD, GREEN_BOX][(i // 2 + int(t * 1.5)) % 3]
                pulse = 0.85 + 0.15 * math.sin(t * 5 + i)
                char_grid[row, c0 + i] = ord(ch)
                col_grid[row, c0 + i] = np.array(tint) * pulse

        screen.fill((0, 0, 0))
        surf = renderer.render(char_grid, col_grid)
        
        sw, sh = screen.get_size()
        screen.blit(surf, ((sw - renderer.w) // 2, (sh - renderer.h) // 2))

        fps_txt = renderer.hud_font.render(f"t {t:5.2f}s", True, DIM)
        hint_txt = renderer.hud_font.render(HINT, True, DIM)
        screen.blit(fps_txt, (sw - fps_txt.get_width() - 10, 8))
        screen.blit(hint_txt, (10, sh - hint_txt.get_height() - 6))

        pygame.display.flip()


if __name__ == "__main__":
    main()