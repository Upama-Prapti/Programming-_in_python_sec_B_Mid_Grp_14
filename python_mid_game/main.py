"""
HELLHOUSE — Save Prapti
========================
Mid-term Project — Track 1: Game (Pygame)

Classes:
  Entity        — base for all game objects
  Player        — player character (inherits Entity)
  Demon         — enemy base (inherits Entity)
  GruntDemon    — melee enemy (inherits Demon)
  ShooterDemon  — ranged enemy (inherits Demon)
  BossDemon     — final boss (inherits Demon)
  Girlfriend    — rescue target (inherits Entity)
  Bullet        — projectile
  Pickup        — collectible item
  StorageManager— JSON high-score persistence + CSV session log
  GameEngine    — core game logic (composition of all above)
  UIController  — HUD, minimap, screens
  Spawner       — wave/enemy spawning logic

Features:
  - CRUD on scores (create/read/update/delete via StorageManager)
  - Search scores by player name
  - Sort/filter scores leaderboard
  - Summary report (top-5, average score, total kills)
  - CSV session log auto-generated on each run
  - JSON high-score file survives restart
  - Validation on all file I/O (graceful error handling)
"""

import pygame
import math
import random
import sys
import json
import csv
import os
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════
#  INIT
# ═══════════════════════════════════════════════════════════════════
pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    SOUND_ON = True
except Exception:
    SOUND_ON = False

W, H = 1280, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("HELLHOUSE  |  Save Prapti")
clock = pygame.time.Clock()
FPS = 60

# ── Colours ─────────────────────────────────────────────────────────
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
BLOOD_RED   = (180, 10,  10)
DARK_RED    = (100, 0,   0)
FIRE_ORANGE = (255, 120, 0)
FIRE_YELLOW = (255, 220, 0)
DARK_BROWN  = (40,  25,  10)
MID_BROWN   = (80,  50,  20)
STONE_GREY  = (70,  70,  80)
DARK_STONE  = (40,  40,  50)
LIGHT_STONE = (120, 115, 110)
FLOOR_COL   = (55,  45,  35)
WALL_COL    = (45,  42,  55)
SKIN        = (220, 180, 140)
DARK_SKIN   = (180, 140, 100)
SHIRT_BLUE  = (40,  80,  160)
PANTS_DARK  = (30,  30,  50)
BULLET_COL  = (255, 240, 100)
MUZZLE_COL  = (255, 200, 50)
BLOOD_COL   = (150, 0,   0)
GREEN_HP    = (50,  200, 80)
PINK        = (255, 150, 200)
PURPLE      = (140, 0,   200)
TEAL        = (0,   200, 180)
BRIDGE_COL  = (100, 70,  30)
BRIDGE_DARK = (70,  45,  15)

# ── Fonts ────────────────────────────────────────────────────────────
def load_font(size, bold=False):
    """Load a monospace system font with fallback."""
    for name in ["Consolas", "Courier New", "monospace"]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)

font_title = load_font(80, bold=True)
font_big   = load_font(48, bold=True)
font_med   = load_font(28, bold=True)
font_small = load_font(18)
font_tiny  = load_font(14)

# ── Sound ────────────────────────────────────────────────────────────
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def make_sound(freq=440, dur=0.1, wave='square', vol=0.2, decay=True, sweep=None):
    """Generate a procedural sound using numpy."""
    if not HAS_NUMPY or not SOUND_ON:
        return None
    try:
        sr = 44100
        n  = int(sr * dur)
        f  = np.linspace(freq, sweep, n) if sweep else np.full(n, float(freq))
        ph = np.cumsum(2 * np.pi * f / sr)
        if wave == 'square': w = np.sign(np.sin(ph))
        elif wave == 'noise': w = np.random.uniform(-1, 1, n)
        elif wave == 'saw':   w = 2 * (ph / (2 * np.pi) % 1) - 1
        else:                 w = np.sin(ph)
        if decay:
            w *= np.linspace(1, 0, n) ** 1.2
        w = (w * vol * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([w, w]))
    except Exception:
        return None

snd_shoot   = make_sound(800, 0.07, 'square', 0.20, sweep=200)
snd_shoot2  = make_sound(600, 0.05, 'square', 0.15, sweep=150)
snd_die     = make_sound(120, 0.40, 'noise',  0.35)
snd_hit     = make_sound(200, 0.05, 'noise',  0.15)
snd_pickup  = make_sound(600, 0.15, 'sine',   0.25, sweep=1200)
snd_hurt    = make_sound(180, 0.10, 'noise',  0.25)
snd_rescued = make_sound(440, 0.50, 'sine',   0.30, sweep=880)
snd_growl   = make_sound(80,  0.30, 'square', 0.20, sweep=40)

def play(snd):
    """Play a sound safely."""
    if snd:
        try:
            snd.play()
        except Exception:
            pass

# ── Tile constants ────────────────────────────────────────────────────
TILE_FLOOR  = 0
TILE_WALL   = 1
TILE_DOOR   = 2
TILE_WINDOW = 3
TILE_BLOOD  = 4
TILE_CARPET = 5
TILE_BRIDGE = 6
TILE_SIZE   = 48
MAP_W, MAP_H = 42, 32

# Bridge columns are 13 and 23; corridor rows 6, 12, 18 must be open there
RAW_MAP = [
    "111111111111111111111111111111111111111111",  # 0
    "100000000111000000001110000000011111111111",  # 1
    "105000000111000000001110000000011111111111",  # 2
    "105500000211000000002110000000021111111111",  # 3
    "105000000111000000001110000000011111111111",  # 4
    "100000000111044400001110444000011111111111",  # 5
    "111121111110100111101100211110111111111111",  # 6  open col 13,23
    "100000000000060000000006000000000000000001",  # 7  bridge
    "100000000000060000000006000000000000000001",  # 8
    "100000000000060000000006000000000000000001",  # 9
    "100000000000060000000006000000000000000001",  # 10
    "100000000000060000000006000000000000000001",  # 11
    "111111211110101111111010121111111111111111",  # 12 open col 13,23
    "100000001110000000000000000111000000000001",  # 13
    "100000002110000000000000000211000000000001",  # 14
    "100000001110000000000000000111000000000001",  # 15
    "100000001110000000000000000111000000000001",  # 16
    "100000001110044000000000440111000000000001",  # 17
    "111111101110101111111010101110111111111111",  # 18 open col 13,23
    "100000000000060000000006000000000000000001",  # 19 bridge
    "100000000000060000000006000000000000000001",  # 20
    "100000000000060000000006000000000000000001",  # 21
    "100000000000060000000006000000000000000001",  # 22
    "111121111111111111112111111111112111111111",  # 23
    "100000001100000000000000000011000000000001",  # 24
    "100000002100000000000000000021000000000001",  # 25
    "100000001100000005555000000011000000000001",  # 26
    "100000001100000005555000000011000000000001",  # 27
    "100000001100000000000000000011000000000001",  # 28
    "100000001100000000000000000011000000000001",  # 29
    "100000001100000000000000000011000000000001",  # 30
    "111111111111111111111111111111111111111111",  # 31
]

def parse_map():
    """Parse RAW_MAP strings into a 2D list of tile integers."""
    return [[int(ch) for ch in row] for row in RAW_MAP]


# ═══════════════════════════════════════════════════════════════════
#  STORAGE MANAGER  (Persistence — JSON scores + CSV session log)
# ═══════════════════════════════════════════════════════════════════
class StorageManager:
    """
    Handles all persistence:
      - JSON file for high scores (CRUD + search/sort)
      - CSV file for session logs (auto-generated each run)
    """
    SCORES_FILE = "scores.json"
    LOG_FILE    = "session_log.csv"

    def __init__(self):
        self.scores = []          # list of dicts
        self.session_rows = []    # rows to write to CSV
        self._load_scores()
        self._init_csv()

    # ── JSON CRUD ─────────────────────────────────────────────────
    def _load_scores(self):
        """Load scores from JSON file. Graceful on missing/corrupt file."""
        if not os.path.exists(self.SCORES_FILE):
            self.scores = []
            return
        try:
            with open(self.SCORES_FILE, "r") as f:
                data = json.load(f)
            # Validate each entry
            self.scores = [
                s for s in data
                if isinstance(s, dict)
                and "name" in s and "score" in s and "kills" in s and "date" in s
            ]
        except (json.JSONDecodeError, IOError):
            self.scores = []

    def save_scores(self):
        """Write scores list to JSON file."""
        try:
            with open(self.SCORES_FILE, "w") as f:
                json.dump(self.scores, f, indent=2)
        except IOError as e:
            print(f"[StorageManager] Could not save scores: {e}")

    def add_score(self, name: str, score: int, kills: int, won: bool):
        """Create a new score entry."""
        if not name or not isinstance(score, int):
            return
        entry = {
            "name":  str(name)[:20],
            "score": max(0, score),
            "kills": max(0, kills),
            "won":   won,
            "date":  datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.scores.append(entry)
        self.save_scores()

    def delete_score(self, index: int):
        """Delete a score by index."""
        if 0 <= index < len(self.scores):
            self.scores.pop(index)
            self.save_scores()

    def get_top_scores(self, n=10):
        """Return top-N scores sorted by score descending."""
        return sorted(self.scores, key=lambda s: s["score"], reverse=True)[:n]

    def search_by_name(self, name: str):
        """Search scores by player name (case-insensitive)."""
        name = name.strip().lower()
        return [s for s in self.scores if name in s["name"].lower()]

    def summary_report(self):
        """Return a summary dict: top-5, average score, total kills."""
        if not self.scores:
            return {"top5": [], "avg_score": 0, "total_kills": 0, "total_games": 0}
        top5       = self.get_top_scores(5)
        avg_score  = sum(s["score"] for s in self.scores) / len(self.scores)
        total_kills= sum(s["kills"] for s in self.scores)
        return {
            "top5":        top5,
            "avg_score":   round(avg_score, 1),
            "total_kills": total_kills,
            "total_games": len(self.scores)
        }

    # ── CSV session log ──────────────────────────────────────────
    def _init_csv(self):
        """Create CSV file with headers if it doesn't exist."""
        try:
            exists = os.path.exists(self.LOG_FILE)
            with open(self.LOG_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                if not exists:
                    writer.writerow(["timestamp","name","score","kills","waves","won","duration_s"])
        except IOError as e:
            print(f"[StorageManager] CSV init error: {e}")

    def log_session(self, name, score, kills, waves, won, duration_s):
        """Append a session row to the CSV log."""
        try:
            with open(self.LOG_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    name, score, kills, waves,
                    "YES" if won else "NO",
                    round(duration_s, 1)
                ])
        except IOError as e:
            print(f"[StorageManager] CSV write error: {e}")


# ═══════════════════════════════════════════════════════════════════
#  PARTICLES  (module-level list)
# ═══════════════════════════════════════════════════════════════════
particles = []

def burst(x, y, color, n=15, spd=4, sz=4, life=30, grav=0.05):
    """Spawn n particles at (x,y)."""
    for _ in range(n):
        a = random.uniform(0, math.tau)
        s = random.uniform(spd * 0.3, spd)
        vx, vy = math.cos(a) * s, math.sin(a) * s
        particles.append([x, y, vx, vy, color, sz, life, life, grav])

def update_particles():
    keep = []
    for p in particles:
        p[0] += p[2]; p[1] += p[3]
        p[3] += p[8]; p[2] *= 0.95; p[6] -= 1
        if p[6] > 0:
            keep.append(p)
    particles[:] = keep

def draw_particles(surf, cx, cy):
    for p in particles:
        ratio = p[6] / p[7]
        c = tuple(int(v * ratio) for v in p[4])
        s = max(1, int(p[5] * ratio))
        pygame.draw.circle(surf, c, (int(p[0]-cx), int(p[1]-cy)), s)

def blood_splat(x, y, n=20):
    burst(x, y, BLOOD_COL, n, 4, 4, 40, 0.08)
    burst(x, y, DARK_RED, n//2, 3, 3, 30, 0.06)


# ═══════════════════════════════════════════════════════════════════
#  ENTITY  (base class)
# ═══════════════════════════════════════════════════════════════════
class Entity:
    """Base class for all game objects. Provides position and radius."""
    def __init__(self, x: float, y: float, radius: int = 14):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.alive = True

    def dist_to(self, other) -> float:
        """Euclidean distance to another entity."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def _is_blocked(self, px, py, tiles, r=None):
        """Check if a position collides with walls."""
        if r is None:
            r = self.radius - 4
        for ox, oy in [(-r, -r), (r, -r), (-r, r), (r, r)]:
            tx = int((px + ox) // TILE_SIZE)
            ty = int((py + oy) // TILE_SIZE)
            if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
                t = tiles[ty][tx]
                if t == TILE_WALL or t == TILE_WINDOW:
                    return True
            else:
                return True
        return False

    def move_toward(self, tx, ty, tiles, spd=None):
        """Move entity toward target, respecting walls."""
        if spd is None:
            spd = getattr(self, 'speed', 1.5)
        dx = tx - self.x; dy = ty - self.y
        dist = max(1, math.hypot(dx, dy))
        nx = self.x + dx / dist * spd
        ny = self.y + dy / dist * spd
        if not self._is_blocked(nx, self.y, tiles):
            self.x = nx
        if not self._is_blocked(self.x, ny, tiles):
            self.y = ny
        self.angle = math.atan2(ty - self.y, tx - self.x)


# ═══════════════════════════════════════════════════════════════════
#  BULLET
# ═══════════════════════════════════════════════════════════════════
class Bullet(Entity):
    """A projectile fired by player or enemy."""
    def __init__(self, x, y, angle, spd=14, dmg=25, color=BULLET_COL, friendly=True):
        super().__init__(x, y, radius=4)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd
        self.dmg = dmg
        self.damage = dmg
        self.color = color
        self.friendly = friendly
        self.trail = []

    def update(self, tiles):
        """Move bullet and check wall collision."""
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        tx, ty = int(self.x // TILE_SIZE), int(self.y // TILE_SIZE)
        if 0 <= tx < MAP_W and 0 <= ty < MAP_H:
            t = tiles[ty][tx]
            if t == TILE_WALL or t == TILE_WINDOW:
                self.alive = False
                burst(self.x, self.y, STONE_GREY, 5, 2, 2, 12, 0.1)
        else:
            self.alive = False

    def draw(self, surf, cx, cy):
        """Draw bullet with trail effect."""
        # trail
        for i, (tx, ty) in enumerate(self.trail):
            ratio = (i + 1) / len(self.trail)
            c = tuple(int(v * ratio * 0.6) for v in self.color)
            r = max(1, int(3 * ratio))
            pygame.draw.circle(surf, c, (int(tx - cx), int(ty - cy)), r)
        # bullet head
        sx, sy = int(self.x - cx), int(self.y - cy)
        pygame.draw.circle(surf, WHITE, (sx, sy), 5)
        pygame.draw.circle(surf, self.color, (sx, sy), 3)


# ═══════════════════════════════════════════════════════════════════
#  PLAYER  (inherits Entity)
# ═══════════════════════════════════════════════════════════════════
class Player(Entity):
    """
    Player character. Moves with WASD, aims with mouse, shoots on click.
    Inherits from Entity for position/collision logic.
    """
    MAX_HP   = 120
    MAX_AMMO = 60
    SPEED    = 3.5
    SHOOT_CD = 8

    def __init__(self, x, y):
        super().__init__(x, y, radius=14)
        self.hp = self.MAX_HP
        self.ammo = self.MAX_AMMO
        self.angle = 0.0
        self.shoot_cd = 0
        self.invincible = 0
        self.kills = 0
        self.score = 0
        self.muzzle_flash = 0
        self.footstep = 0
        self.anim = 0

    def take_damage(self, dmg: int):
        """Reduce HP, trigger invincibility frames."""
        if self.invincible > 0:
            return
        self.hp -= dmg
        self.invincible = 40
        play(snd_hurt)
        blood_splat(self.x, self.y, 10)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def shoot(self, bullets: list, mx: int, my: int, cx: int, cy: int):
        """Fire a bullet toward the mouse cursor."""
        if self.shoot_cd > 0 or self.ammo <= 0:
            return
        self.shoot_cd = self.SHOOT_CD
        self.ammo -= 1
        self.muzzle_flash = 6
        # world coordinates of mouse
        wx = mx + cx - W // 2
        wy = my + cy - H // 2
        angle = math.atan2(wy - self.y, wx - self.x)
        angle += random.uniform(-0.04, 0.04)
        # bullet spawns exactly at gun tip
        gun_dist = 26
        bx = self.x + math.cos(self.angle) * gun_dist
        by = self.y + math.sin(self.angle) * gun_dist
        bullets.append(Bullet(bx, by, angle, spd=16, dmg=25))
        play(snd_shoot)
        burst(bx, by, MUZZLE_COL, 8, 5, 3, 12)

    def update(self, keys, tiles):
        """Update player movement, cooldowns."""
        if not self.alive:
            return
        if self.shoot_cd > 0:   self.shoot_cd -= 1
        if self.invincible > 0: self.invincible -= 1
        if self.muzzle_flash > 0: self.muzzle_flash -= 1

        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:   dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:   dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  dx += 1
        if dx and dy:
            dx *= 0.707; dy *= 0.707

        nx = self.x + dx * self.SPEED
        ny = self.y + dy * self.SPEED
        if not self._is_blocked(nx, self.y, tiles, self.radius):
            self.x = nx
        if not self._is_blocked(self.x, ny, tiles, self.radius):
            self.y = ny

        self.anim = (self.anim + 1) % 20
        if dx or dy:
            self.footstep = (self.footstep + 1) % 30

    def update_angle(self, mx, my, cx, cy):
        """Point player toward mouse cursor."""
        wx = mx + cx - W // 2
        wy = my + cy - H // 2
        self.angle = math.atan2(wy - self.y, wx - self.x)

    def draw(self, surf, cx, cy):
        """Draw player sprite at screen position."""
        if not self.alive:
            return
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            return
        sx = int(self.x - cx + W // 2)
        sy = int(self.y - cy + H // 2)

        # shadow
        pygame.draw.ellipse(surf, (20, 15, 10), (sx-14, sy+10, 28, 10))
        # legs
        leg = int(math.sin(self.footstep * 0.4) * 5)
        pygame.draw.line(surf, PANTS_DARK, (sx, sy+4), (sx-7, sy+16+leg), 4)
        pygame.draw.line(surf, PANTS_DARK, (sx, sy+4), (sx+7, sy+16-leg), 4)
        pygame.draw.circle(surf, (20,15,10), (sx-7, sy+18+leg), 4)
        pygame.draw.circle(surf, (20,15,10), (sx+7, sy+18-leg), 4)
        # body
        pygame.draw.circle(surf, SHIRT_BLUE, (sx, sy), 12)
        pygame.draw.circle(surf, (30,60,130), (sx, sy), 12, 2)
        # arm
        ax = sx + int(math.cos(self.angle) * 10)
        ay = sy + int(math.sin(self.angle) * 10)
        pygame.draw.line(surf, DARK_SKIN, (sx, sy), (ax, ay), 5)
        # gun — drawn from arm to gun tip
        gx = sx + int(math.cos(self.angle) * 26)
        gy = sy + int(math.sin(self.angle) * 26)
        pygame.draw.line(surf, (50, 50, 60), (ax, ay), (gx, gy), 5)
        # muzzle flash
        if self.muzzle_flash > 0:
            for r in range(12, 3, -3):
                gc = (min(255, self.muzzle_flash*40), min(255, self.muzzle_flash*20), 0)
                pygame.draw.circle(surf, gc, (gx, gy), r)
        # head
        pygame.draw.circle(surf, SKIN, (sx, sy-12), 10)
        pygame.draw.circle(surf, DARK_SKIN, (sx, sy-12), 10, 1)
        pygame.draw.arc(surf, (40,25,10), (sx-10, sy-24, 20, 16), 0, math.pi, 5)
        edx = int(math.cos(self.angle) * 4)
        edy = int(math.sin(self.angle) * 4)
        pygame.draw.circle(surf, WHITE, (sx+edx-2, sy-12+edy), 3)
        pygame.draw.circle(surf, (30,30,80), (sx+edx-2, sy-12+edy), 1)


# ═══════════════════════════════════════════════════════════════════
#  DEMON BASE  (inherits Entity)
# ═══════════════════════════════════════════════════════════════════
class Demon(Entity):
    """Base enemy class. All demons inherit from this."""
    def __init__(self, x, y, hp=60, spd=1.5, dmg=15, score=100):
        super().__init__(x, y, radius=16)
        self.hp = self.max_hp = hp
        self.speed = spd
        self.damage = dmg
        self.score_val = score
        self.angle = 0.0
        self.shoot_cd = random.randint(60, 180)
        self.anim = random.randint(0, 30)
        self.alert = False
        self.alert_range = 300
        self.path_timer = 0
        self.wander_angle = random.uniform(0, math.tau)
        self.attack_cd = 0
        self.hit_flash = 0

    def take_damage(self, dmg: int) -> bool:
        """Deal damage. Returns True if killed."""
        self.hp -= dmg
        self.hit_flash = 8
        play(snd_hit)
        if self.hp <= 0:
            self.alive = False
            blood_splat(self.x, self.y, 30)
            play(snd_die)
            return True
        return False

    def hp_ratio(self) -> float:
        return max(0.0, self.hp / self.max_hp)

    def draw_hp_bar(self, surf, cx, cy):
        sx = int(self.x - cx + W // 2)
        sy = int(self.y - cy + H // 2)
        bw = 36
        bx = sx - bw // 2
        by = sy - self.radius - 12
        pygame.draw.rect(surf, (60, 0, 0), (bx, by, bw, 5))
        pygame.draw.rect(surf, BLOOD_RED, (bx, by, int(bw * self.hp_ratio()), 5))


# ═══════════════════════════════════════════════════════════════════
#  GRUNT DEMON  (inherits Demon)
# ═══════════════════════════════════════════════════════════════════
class GruntDemon(Demon):
    """Melee demon that charges the player."""
    def __init__(self, x, y, level=1):
        super().__init__(x, y,
                         hp=50 + level*15, spd=1.8 + level*0.2,
                         dmg=12, score=100 + level*20)
        self.c1 = (120, 20, 20)
        self.c2 = (200, 40, 10)

    def update(self, player, tiles, bullets):
        self.anim += 1
        self.attack_cd = max(0, self.attack_cd - 1)
        if self.hit_flash > 0: self.hit_flash -= 1
        dist = self.dist_to(player)
        self.alert = dist < self.alert_range
        if self.alert:
            self.move_toward(player.x, player.y, tiles)
            if dist < self.radius + player.radius + 5 and self.attack_cd == 0:
                player.take_damage(self.damage)
                self.attack_cd = 45
        else:
            self.path_timer += 1
            if self.path_timer > 60:
                self.wander_angle = random.uniform(0, math.tau)
                self.path_timer = 0
            self.move_toward(
                self.x + math.cos(self.wander_angle) * self.speed * 0.5,
                self.y + math.sin(self.wander_angle) * self.speed * 0.5,
                tiles, 0.8)

    def draw(self, surf, cx, cy):
        sx = int(self.x - cx + W//2)
        sy = int(self.y - cy + H//2)
        a = self.anim
        col = (255, 80, 80) if self.hit_flash > 0 else self.c1
        bob = int(math.sin(a * 0.3) * 3)
        pygame.draw.ellipse(surf, (15,8,8), (sx-16, sy+12, 32, 12))
        pygame.draw.circle(surf, col, (sx, sy+bob), 16)
        pygame.draw.circle(surf, self.c2, (sx, sy+bob), 16, 2)
        pygame.draw.polygon(surf, (80,15,15),
            [(sx-8,sy-14+bob),(sx-14,sy-26+bob),(sx-4,sy-18+bob)])
        pygame.draw.polygon(surf, (80,15,15),
            [(sx+8,sy-14+bob),(sx+14,sy-26+bob),(sx+4,sy-18+bob)])
        for ex, ey in [(sx-5, sy-6+bob), (sx+5, sy-6+bob)]:
            pygame.draw.circle(surf, FIRE_ORANGE, (ex, ey), 5)
            pygame.draw.circle(surf, FIRE_YELLOW, (ex, ey), 3)
            pygame.draw.circle(surf, WHITE, (ex, ey), 1)
        cb = int(math.sin(a * 0.5) * 5)
        for side in [-1, 1]:
            cx2 = sx + side*18
            pygame.draw.line(surf, (80,15,15), (sx+side*12, sy+bob), (cx2, sy+cb), 3)
            for i in range(3):
                ang = math.pi/2 + side*i*0.3
                pygame.draw.line(surf, (100,20,20), (cx2, sy+cb),
                    (cx2+int(math.cos(ang)*6), sy+cb+int(math.sin(ang)*6)), 2)
        self.draw_hp_bar(surf, cx, cy)


# ═══════════════════════════════════════════════════════════════════
#  SHOOTER DEMON  (inherits Demon)
# ═══════════════════════════════════════════════════════════════════
class ShooterDemon(Demon):
    """Ranged demon that keeps distance and fires projectiles."""
    def __init__(self, x, y, level=1):
        super().__init__(x, y,
                         hp=40 + level*12, spd=1.2 + level*0.1,
                         dmg=8, score=150 + level*30)
        self.preferred_dist = 200
        self.c1 = (40, 20, 100)
        self.c2 = (100, 40, 200)

    def update(self, player, tiles, bullets):
        self.anim += 1
        if self.hit_flash > 0: self.hit_flash -= 1
        if self.shoot_cd > 0:  self.shoot_cd -= 1
        dist = self.dist_to(player)
        self.alert = dist < self.alert_range
        if self.alert:
            if dist < self.preferred_dist - 20:
                dx = self.x - player.x; dy = self.y - player.y
                d  = max(1, math.hypot(dx, dy))
                self.move_toward(self.x + dx/d*40, self.y + dy/d*40, tiles)
            elif dist > self.preferred_dist + 40:
                self.move_toward(player.x, player.y, tiles)
            if self.shoot_cd == 0 and dist < 350:
                ang = math.atan2(player.y-self.y, player.x-self.x)
                ang += random.uniform(-0.15, 0.15)
                bullets.append(Bullet(self.x, self.y, ang, spd=8,
                                      dmg=self.damage, color=PURPLE, friendly=False))
                self.shoot_cd = random.randint(60, 100)
                play(snd_shoot2)
        else:
            self.path_timer += 1
            if self.path_timer > 80:
                self.wander_angle = random.uniform(0, math.tau)
                self.path_timer = 0
            self.move_toward(
                self.x + math.cos(self.wander_angle)*30,
                self.y + math.sin(self.wander_angle)*30,
                tiles, 0.6)

    def draw(self, surf, cx, cy):
        sx = int(self.x - cx + W//2)
        sy = int(self.y - cy + H//2)
        a = self.anim
        col = (200,120,255) if self.hit_flash > 0 else self.c1
        bob = int(math.sin(a * 0.2) * 6)
        pygame.draw.ellipse(surf, (10,5,20), (sx-14, sy+12, 28, 10))
        pygame.draw.circle(surf, col, (sx, sy+bob), 15)
        pygame.draw.circle(surf, self.c2, (sx, sy+bob), 15, 2)
        for i in range(4):
            tang = a*0.05 + i*math.pi/2
            tx2 = sx + int(math.cos(tang)*12)
            ty2 = sy + bob + 14 + int(math.sin(tang*2)*8)
            pygame.draw.line(surf, self.c2, (sx, sy+bob+12), (tx2, ty2), 3)
        for ex, ey in [(sx-6, sy-4+bob), (sx+6, sy-4+bob), (sx, sy-10+bob)]:
            pygame.draw.circle(surf, PURPLE, (ex, ey), 5)
            pygame.draw.circle(surf, (200,100,255), (ex, ey), 3)
            pygame.draw.circle(surf, WHITE, (ex, ey), 1)
        self.draw_hp_bar(surf, cx, cy)


# ═══════════════════════════════════════════════════════════════════
#  BOSS DEMON  (inherits Demon) — guards Prapti
# ═══════════════════════════════════════════════════════════════════
class BossDemon(Demon):
    """
    Final boss. Guards Prapti and must be killed to rescue her.
    Has 3 attack patterns and enrages at 40% HP.
    """
    # Boss spawn position — right next to Prapti
    SPAWN_X = 21 * TILE_SIZE + 24
    SPAWN_Y = 27 * TILE_SIZE + 24

    def __init__(self):
        super().__init__(self.SPAWN_X, self.SPAWN_Y,
                         hp=600, spd=1.0, dmg=25, score=3000)
        self.radius = 30
        self.enraged = False
        self.spin = 0
        self.shoot_pattern = 0
        self.attack_cd = 0

    def update(self, player, tiles, bullets):
        self.anim += 1
        self.spin += 2
        if self.hit_flash > 0: self.hit_flash -= 1
        if self.shoot_cd > 0:  self.shoot_cd -= 1
        if self.attack_cd > 0: self.attack_cd -= 1

        if not self.enraged and self.hp < self.max_hp * 0.4:
            self.enraged = True
            self.speed = 1.8
            play(snd_growl)
            burst(self.x, self.y, BLOOD_RED, 40, 8, 6, 60)

        dist = self.dist_to(player)
        self.alert = True
        self.move_toward(player.x, player.y, tiles)

        if dist < self.radius + player.radius + 5 and self.attack_cd == 0:
            player.take_damage(self.damage)
            self.attack_cd = 30

        if self.shoot_cd == 0:
            self.shoot_cd = 18 if self.enraged else 32
            pat = self.shoot_pattern
            if pat == 0:
                for i in range(8):
                    ang = math.radians(self.spin + i*45)
                    bullets.append(Bullet(self.x, self.y, ang, spd=6,
                                          dmg=15, color=BLOOD_RED, friendly=False))
            elif pat == 1:
                ang = math.atan2(player.y-self.y, player.x-self.x)
                for off in (-0.2, 0, 0.2):
                    bullets.append(Bullet(self.x, self.y, ang+off, spd=10,
                                          dmg=20, color=FIRE_ORANGE, friendly=False))
            elif pat == 2:
                for i in range(3):
                    ang = math.radians(self.spin*2 + i*120)
                    bullets.append(Bullet(self.x, self.y, ang, spd=7,
                                          dmg=18, color=PURPLE, friendly=False))
            self.shoot_pattern = (self.shoot_pattern + 1) % 3
            play(snd_shoot2)

    def draw(self, surf, cx, cy):
        sx = int(self.x - cx + W//2)
        sy = int(self.y - cy + H//2)
        col = (255,100,100) if self.hit_flash > 0 else (150,15,15)
        ec = FIRE_ORANGE if self.enraged else BLOOD_RED
        for r in range(40, 20, -6):
            pygame.draw.circle(surf, (max(0,80-(40-r)*3),0,0), (sx,sy), r)
        pygame.draw.circle(surf, col, (sx,sy), 30)
        pygame.draw.circle(surf, ec, (sx,sy), 30, 3)
        for i in range(6):
            ang = math.radians(self.spin + i*60)
            ax2 = sx + int(math.cos(ang)*38)
            ay2 = sy + int(math.sin(ang)*38)
            pygame.draw.line(surf, ec, (sx,sy), (ax2,ay2), 4)
            pygame.draw.circle(surf, FIRE_YELLOW, (ax2,ay2), 6)
        for i in range(8):
            ang = math.radians(-self.spin*2 + i*45)
            pygame.draw.circle(surf, FIRE_ORANGE,
                (sx+int(math.cos(ang)*20), sy+int(math.sin(ang)*20)), 4)
        pygame.draw.circle(surf, (255,50,50) if self.enraged else (200,20,20), (sx,sy), 12)
        pygame.draw.circle(surf, WHITE, (sx,sy), 5)
        bw = 80; bx2 = sx - bw//2; by2 = sy - 50
        pygame.draw.rect(surf, (60,0,0), (bx2-1,by2-1,bw+2,11))
        pygame.draw.rect(surf, BLOOD_RED, (bx2,by2,int(bw*self.hp_ratio()),9))
        pygame.draw.rect(surf, WHITE, (bx2-1,by2-1,bw+2,11), 1)
        lbl = font_tiny.render("DEMON LORD", True, BLOOD_RED)
        surf.blit(lbl, (sx-lbl.get_width()//2, by2-16))
        if self.enraged:
            en = font_tiny.render("ENRAGED!", True, FIRE_ORANGE)
            surf.blit(en, (sx-en.get_width()//2, by2-30))


# ═══════════════════════════════════════════════════════════════════
#  GIRLFRIEND  (inherits Entity) — rescue target
# ═══════════════════════════════════════════════════════════════════
class Girlfriend(Entity):
    """
    Prapti — the rescue target.
    Can only be rescued AFTER the boss is dead.
    """
    SPAWN_X = 20 * TILE_SIZE + 24
    SPAWN_Y = 27 * TILE_SIZE + 24

    def __init__(self):
        super().__init__(self.SPAWN_X, self.SPAWN_Y, radius=14)
        self.rescued = False
        self.anim = 0
        self.can_rescue = False   # only True when boss is dead

    def update(self, player, boss_alive: bool):
        """Update rescue state. Can only rescue when boss is dead."""
        self.anim += 1
        self.can_rescue = not boss_alive
        if self.can_rescue and not self.rescued:
            if self.dist_to(player) < 80:
                self.rescued = True
                play(snd_rescued)
                burst(self.x, self.y, PINK, 40, 6, 5, 60)
                burst(self.x, self.y, WHITE, 20, 4, 3, 40)

    def draw(self, surf, cx, cy):
        if self.rescued:
            return
        sx = int(self.x - cx + W//2)
        sy = int(self.y - cy + H//2)
        a = self.anim
        pulse = abs(math.sin(a * 0.05))

        # rescue glow (stronger when boss dead)
        glow_r = int(255*pulse) if self.can_rescue else int(80*pulse)
        glow_b = int(200*pulse) if self.can_rescue else int(60*pulse)
        for r in range(30, 10, -5):
            gc = (glow_r*(30-r)//20, 0, glow_b*(30-r)//20)
            pygame.draw.circle(surf, gc, (sx, sy), r+20)

        pygame.draw.ellipse(surf, (15,10,10), (sx-12, sy+10, 24, 10))
        leg = int(math.sin(a * 0.15) * 3)
        pygame.draw.line(surf, (180,100,140), (sx,sy+4), (sx-6,sy+16+leg), 3)
        pygame.draw.line(surf, (180,100,140), (sx,sy+4), (sx+6,sy+16-leg), 3)
        pygame.draw.circle(surf, (220,100,160), (sx,sy), 11)
        pygame.draw.circle(surf, PINK, (sx,sy), 11, 2)
        pygame.draw.circle(surf, SKIN, (sx,sy-12), 9)
        pygame.draw.arc(surf, (180,80,120), (sx-10,sy-24,20,16), 0, math.pi, 4)
        pygame.draw.circle(surf, (180,80,120), (sx-9,sy-16), 4)
        pygame.draw.circle(surf, (180,80,120), (sx+9,sy-16), 4)
        pygame.draw.circle(surf, WHITE, (sx-3,sy-12), 3)
        pygame.draw.circle(surf, WHITE, (sx+4,sy-12), 3)
        pygame.draw.circle(surf, (60,60,180), (sx-3,sy-12), 1)
        pygame.draw.circle(surf, (60,60,180), (sx+4,sy-12), 1)

        name = font_med.render("PRAPTI", True, PINK)
        surf.blit(name, (sx-name.get_width()//2, sy-72))

        if self.can_rescue:
            lbl = font_small.render("[ PRESS near to RESCUE ]", True, FIRE_YELLOW)
            surf.blit(lbl, (sx-lbl.get_width()//2, sy-50))
        else:
            lbl = font_tiny.render("KILL THE BOSS FIRST!", True, BLOOD_RED)
            surf.blit(lbl, (sx-lbl.get_width()//2, sy-50))


# ═══════════════════════════════════════════════════════════════════
#  PICKUP
# ═══════════════════════════════════════════════════════════════════
class Pickup:
    """Collectible item dropped by demons."""
    def __init__(self, x, y, kind):
        self.x, self.y = x, y
        self.kind = kind
        self.alive = True
        self.anim = random.randint(0, 30)

    def update(self, player):
        self.anim += 1
        if math.hypot(player.x-self.x, player.y-self.y) < 24:
            self.alive = False
            play(snd_pickup)
            if self.kind == 'ammo':
                player.ammo = min(player.MAX_AMMO, player.ammo + 20)
                burst(self.x, self.y, FIRE_YELLOW, 10, 4, 3, 25)
            elif self.kind == 'health':
                player.hp = min(player.MAX_HP, player.hp + 30)
                burst(self.x, self.y, GREEN_HP, 10, 4, 3, 25)
            elif self.kind == 'score':
                player.score += 500
                burst(self.x, self.y, FIRE_YELLOW, 10, 4, 3, 25)

    def draw(self, surf, cx, cy):
        sx = int(self.x - cx + W//2)
        sy = int(self.y - cy + H//2) + int(math.sin(self.anim*0.1)*4)
        if self.kind == 'ammo':
            col = FIRE_YELLOW
            pygame.draw.rect(surf, col, (sx-10,sy-6,20,12))
            pygame.draw.rect(surf, WHITE, (sx-10,sy-6,20,12), 2)
            surf.blit(font_tiny.render("AMMO",True,col),(sx-16,sy-22))
        elif self.kind == 'health':
            col = GREEN_HP
            pygame.draw.rect(surf, col, (sx-3,sy-10,6,20))
            pygame.draw.rect(surf, col, (sx-10,sy-3,20,6))
            surf.blit(font_tiny.render("+HP",True,col),(sx-10,sy-24))
        else:
            pygame.draw.circle(surf, FIRE_ORANGE, (sx,sy), 10)
            pygame.draw.circle(surf, FIRE_YELLOW, (sx,sy), 10, 2)
            surf.blit(font_tiny.render("$500",True,FIRE_ORANGE),(sx-14,sy-22))


# ═══════════════════════════════════════════════════════════════════
#  SPAWNER  (wave management)
# ═══════════════════════════════════════════════════════════════════
class Spawner:
    """Manages enemy wave spawning with increasing difficulty."""
    def __init__(self, tiles, player_start_x, player_start_y):
        self.tiles = tiles
        self.px = player_start_x
        self.py = player_start_y
        self.wave = 0

    def spawn_wave(self, wave_num: int) -> list:
        """Spawn enemies for the given wave. Returns list of demons."""
        demons = []
        for _ in range(4 + wave_num * 3):
            x, y = self._rand_floor()
            demons.append(GruntDemon(x, y, level=wave_num))
        for _ in range(max(0, wave_num - 1) * 2):
            x, y = self._rand_floor()
            demons.append(ShooterDemon(x, y, level=wave_num))
        return demons

    def _rand_floor(self) -> tuple:
        """Find a random floor tile far from player start."""
        for _ in range(1000):
            tx = random.randint(1, MAP_W-2)
            ty = random.randint(1, MAP_H-2)
            if self.tiles[ty][tx] in (TILE_FLOOR, TILE_BRIDGE):
                px = tx * TILE_SIZE + 24
                py = ty * TILE_SIZE + 24
                if math.hypot(px-self.px, py-self.py) > 250:
                    return px, py
        return self.px + 300, self.py + 200


# ═══════════════════════════════════════════════════════════════════
#  SCREEN SHAKE
# ═══════════════════════════════════════════════════════════════════
_shake_amt = 0

def screen_shake(amt=8):
    global _shake_amt
    _shake_amt = max(_shake_amt, amt)

def get_shake():
    global _shake_amt
    if _shake_amt > 0.3:
        ox = random.randint(-int(_shake_amt), int(_shake_amt))
        oy = random.randint(-int(_shake_amt), int(_shake_amt))
        _shake_amt *= 0.82
        return ox, oy
    _shake_amt = 0
    return 0, 0


# ═══════════════════════════════════════════════════════════════════
#  MAP RENDERER
# ═══════════════════════════════════════════════════════════════════
def draw_map(surf, tiles, cx, cy, frame=0):
    """Render visible tiles around the camera."""
    stx = max(0, cx//TILE_SIZE - W//TILE_SIZE//2 - 1)
    etx = min(MAP_W, cx//TILE_SIZE + W//TILE_SIZE//2 + 2)
    sty = max(0, cy//TILE_SIZE - H//TILE_SIZE//2 - 1)
    ety = min(MAP_H, cy//TILE_SIZE + H//TILE_SIZE//2 + 2)

    for ty in range(int(sty), int(ety)):
        for tx in range(int(stx), int(etx)):
            t  = tiles[ty][tx]
            px = tx * TILE_SIZE - cx + W//2
            py = ty * TILE_SIZE - cy + H//2
            rect = (px, py, TILE_SIZE, TILE_SIZE)

            if t == TILE_FLOOR:
                pygame.draw.rect(surf, FLOOR_COL, rect)
                pygame.draw.rect(surf, (50,40,30), rect, 1)

            elif t == TILE_WALL:
                pygame.draw.rect(surf, WALL_COL, rect)
                for brow in range(2):
                    by2 = py + brow*(TILE_SIZE//2)
                    off = (TILE_SIZE//2) if brow%2==0 else 0
                    pygame.draw.line(surf, DARK_STONE, (px+off,by2), (px+off,by2+TILE_SIZE//2), 1)
                pygame.draw.rect(surf, DARK_STONE, rect, 1)
                pygame.draw.line(surf, (60,58,70), (px,py), (px+TILE_SIZE,py), 1)

            elif t == TILE_DOOR:
                pygame.draw.rect(surf, FLOOR_COL, rect)
                pygame.draw.rect(surf, MID_BROWN, (px+4,py+2,TILE_SIZE-8,TILE_SIZE-4))
                pygame.draw.rect(surf, DARK_BROWN, (px+4,py+2,TILE_SIZE-8,TILE_SIZE-4), 2)
                pygame.draw.circle(surf, (180,140,60), (px+TILE_SIZE-10, py+TILE_SIZE//2), 3)

            elif t == TILE_WINDOW:
                pygame.draw.rect(surf, WALL_COL, rect)
                pygame.draw.rect(surf, (60,100,150), (px+6,py+6,TILE_SIZE-12,TILE_SIZE-12))
                pygame.draw.line(surf, DARK_STONE, (px+TILE_SIZE//2,py+6), (px+TILE_SIZE//2,py+TILE_SIZE-6), 2)
                pygame.draw.line(surf, DARK_STONE, (px+6,py+TILE_SIZE//2), (px+TILE_SIZE-6,py+TILE_SIZE//2), 2)
                pygame.draw.line(surf, (100,160,220), (px+8,py+8), (px+14,py+8), 1)

            elif t == TILE_BLOOD:
                pygame.draw.rect(surf, FLOOR_COL, rect)
                pygame.draw.ellipse(surf, (100,0,0), (px+6,py+8,TILE_SIZE-12,TILE_SIZE-16))

            elif t == TILE_CARPET:
                pygame.draw.rect(surf, (80,30,30), rect)
                pygame.draw.rect(surf, (100,40,40), (px+4,py+4,TILE_SIZE-8,TILE_SIZE-8), 2)

            elif t == TILE_BRIDGE:
                pygame.draw.rect(surf, (30,20,8), rect)
                plank_h = 8; plank_gap = 4
                for p in range(TILE_SIZE // (plank_h+plank_gap) + 1):
                    py2 = py + p*(plank_h+plank_gap)
                    if py2 < py + TILE_SIZE:
                        pygame.draw.rect(surf, BRIDGE_COL, (px+2,py2,TILE_SIZE-4,plank_h))
                        pygame.draw.rect(surf, BRIDGE_DARK, (px+2,py2,TILE_SIZE-4,plank_h), 1)
                        pygame.draw.line(surf, (110,75,32), (px+4,py2+2), (px+TILE_SIZE-8,py2+2), 1)
                pygame.draw.line(surf, (150,100,40), (px+3,py), (px+3,py+TILE_SIZE), 2)
                pygame.draw.line(surf, (150,100,40), (px+TILE_SIZE-3,py), (px+TILE_SIZE-3,py+TILE_SIZE), 2)


# ═══════════════════════════════════════════════════════════════════
#  UI CONTROLLER
# ═══════════════════════════════════════════════════════════════════
class UIController:
    """Handles all UI rendering: HUD, minimap, crosshair, screens."""

    @staticmethod
    def draw_hud(surf, player, wave, kills_left, rescued, boss_hp=None, frame=0):
        """Draw the bottom HUD panel."""
        panel = pygame.Surface((W, 72), pygame.SRCALPHA)
        panel.fill((8, 5, 4, 220))
        surf.blit(panel, (0, H-72))
        pulse = abs(math.sin(frame*0.03))
        border_col = (int(120+60*pulse), int(30*pulse), int(10*pulse))
        pygame.draw.line(surf, border_col, (0,H-72), (W,H-72), 2)

        # HP bar
        hp_w = 200; hp_r = player.hp / player.MAX_HP
        bx, by = 14, H-58
        pygame.draw.rect(surf, (30,0,0), (bx,by,hp_w,18))
        fc = GREEN_HP if hp_r>0.5 else (FIRE_ORANGE if hp_r>0.25 else BLOOD_RED)
        pygame.draw.rect(surf, fc, (bx,by,int(hp_w*hp_r),18))
        pygame.draw.rect(surf, WHITE, (bx-1,by-1,hp_w+2,20), 1)
        surf.blit(font_tiny.render(f"HP  {int(player.hp)}/{player.MAX_HP}", True, WHITE), (bx+4, by+2))

        # Ammo
        ammo_col = FIRE_YELLOW if player.ammo > 10 else BLOOD_RED
        for i in range(min(player.ammo, 20)):
            pygame.draw.rect(surf, ammo_col, (bx+i*9, H-32, 6, 10))
        if player.ammo > 20:
            surf.blit(font_tiny.render(f"+{player.ammo-20}", True, ammo_col), (bx+182, H-32))
        surf.blit(font_tiny.render(f"AMMO: {player.ammo}", True, ammo_col), (bx, H-18))

        # Score centre
        sc = font_big.render(f"{player.score:,}", True, (int(200+55*pulse), int(180+40*pulse), 0))
        surf.blit(sc, (W//2-sc.get_width()//2, H-62))
        surf.blit(font_tiny.render("SCORE", True, (180,140,0)), (W//2-20, H-20))
        surf.blit(font_tiny.render(f"ROOM {wave}", True, FIRE_ORANGE), (W//2-22, H-36))

        # Right side
        rx = W-220
        surf.blit(font_small.render(f"DEMONS: {kills_left}", True, BLOOD_RED), (rx, H-58))
        if rescued:
            p2 = abs(math.sin(frame*0.08))
            rc = (int(255*p2), int(150*p2), int(200*p2))
            surf.blit(font_small.render("PRAPTI RESCUED!", True, rc), (rx, H-34))
        else:
            surf.blit(font_small.render("FIND PRAPTI!", True, (200,180,80)), (rx, H-34))
        surf.blit(font_tiny.render(f"Kills: {player.kills}", True, STONE_GREY), (rx, H-16))

        # Boss bar
        if boss_hp is not None:
            bw = 500; bx2 = W//2-bw//2; by2 = 10
            for gw in range(8, 0, -2):
                pygame.draw.rect(surf, (int(80*boss_hp),0,0), (bx2-gw,by2-gw,bw+gw*2,20+gw*2))
            pygame.draw.rect(surf, (60,0,0), (bx2,by2,bw,20))
            pygame.draw.rect(surf, BLOOD_RED, (bx2,by2,int(bw*boss_hp),20))
            pygame.draw.rect(surf, WHITE, (bx2-1,by2-1,bw+2,22), 2)
            bl = font_small.render("☠  DEMON LORD  ☠", True, BLOOD_RED)
            surf.blit(bl, (W//2-bl.get_width()//2, by2+22))

    @staticmethod
    def draw_crosshair(surf, mx, my):
        """Draw crosshair at mouse position."""
        c = (255, 220, 50)
        pygame.draw.circle(surf, c, (mx, my), 16, 1)
        pygame.draw.line(surf, c, (mx-22,my), (mx-8,my), 2)
        pygame.draw.line(surf, c, (mx+8, my), (mx+22,my), 2)
        pygame.draw.line(surf, c, (mx,my-22), (mx,my-8), 2)
        pygame.draw.line(surf, c, (mx,my+8), (mx,my+22), 2)
        pygame.draw.circle(surf, WHITE, (mx,my), 2)

    @staticmethod
    def draw_minimap(surf, tiles, player, demons, boss, gf, frame):
        """Draw the minimap in the top-right corner."""
        mm_w, mm_h = 180, 130
        mm_x, mm_y = W-mm_w-10, 10
        panel = pygame.Surface((mm_w+4, mm_h+28), pygame.SRCALPHA)
        panel.fill((5,4,3,200))
        surf.blit(panel, (mm_x-2, mm_y-2))
        pygame.draw.rect(surf, (100,70,30), (mm_x-2,mm_y-2,mm_w+4,mm_h+28), 1)
        mm = pygame.Surface((mm_w, mm_h))
        mm.fill((10,8,6))
        sx = mm_w/(MAP_W*TILE_SIZE); sy = mm_h/(MAP_H*TILE_SIZE)
        for ty in range(MAP_H):
            for tx in range(MAP_W):
                t  = tiles[ty][tx]
                px = int(tx*TILE_SIZE*sx); py = int(ty*TILE_SIZE*sy)
                pw = max(1,int(TILE_SIZE*sx)); ph = max(1,int(TILE_SIZE*sy))
                if t==TILE_WALL:   col=STONE_GREY
                elif t==TILE_BRIDGE: col=BRIDGE_COL
                elif t==TILE_DOOR:  col=MID_BROWN
                else:               col=(45,38,28)
                pygame.draw.rect(mm, col, (px,py,pw,ph))
        # player
        ppx = int(player.x*sx); ppy = int(player.y*sy)
        pulse = abs(math.sin(frame*0.06))
        pygame.draw.circle(mm, (0,int(150+80*pulse),int(150+80*pulse)), (ppx,ppy), 4)
        pygame.draw.circle(mm, WHITE, (ppx,ppy), 2)
        # demons
        for d in demons:
            pygame.draw.circle(mm, BLOOD_RED, (int(d.x*sx),int(d.y*sy)), 2)
        if boss:
            bp = abs(math.sin(frame*0.1))
            pygame.draw.circle(mm, (int(200+55*bp),int(60*bp),0),
                               (int(boss.x*sx),int(boss.y*sy)), 5)
        if not gf.rescued:
            gp = abs(math.sin(frame*0.08))
            pygame.draw.circle(mm, (int(255*gp),int(100*gp),int(200*gp)),
                               (int(gf.x*sx),int(gf.y*sy)), 4)
        pygame.draw.rect(mm, (80,55,25), (0,0,mm_w,mm_h), 1)
        surf.blit(mm, (mm_x, mm_y))
        surf.blit(font_tiny.render("M I N I M A P", True, (130,100,60)),
                  (mm_x+40, mm_y+mm_h+4))
        legend = [(TEAL,"You"),(BLOOD_RED,"Demon"),(FIRE_ORANGE,"Boss"),(PINK,"Prapti")]
        for i,(lc,lt) in enumerate(legend):
            lx = mm_x + (i%2)*(mm_w//2)
            ly = mm_y + mm_h + 16 + (i//2)*12
            pygame.draw.circle(surf, lc, (lx+4,ly+4), 3)
            surf.blit(font_tiny.render(lt, True, lc), (lx+10,ly-2))

    @staticmethod
    def draw_flash(surf, msgs):
        """Draw flash messages. Each msg = [text,color,timer,x,y]."""
        keep = []
        for m in msgs:
            m[2] -= 1
            if m[2] > 0:
                fnt = font_big if m[2] > 50 else font_med
                sh  = fnt.render(m[0], True, (0,0,0))
                surf.blit(sh, (m[3]-sh.get_width()//2+2, m[4]-(80-m[2])+2))
                t = fnt.render(m[0], True, m[1])
                surf.blit(t,  (m[3]-t.get_width()//2, m[4]-(80-m[2])))
                keep.append(m)
        msgs[:] = keep

    @staticmethod
    def draw_title(surf, frame):
        """Render the title/menu screen."""
        surf.fill((8,4,4))
        for i in range(20):
            x = (i*64 + frame//2) % W
            h = 30 + int(math.sin(i*1.3 + frame*0.02)*20)
            pygame.draw.rect(surf, DARK_RED, (x,0,6,h))
            pygame.draw.circle(surf, BLOOD_RED, (x+3,h), 4)
        for off in range(8,0,-2):
            t = font_title.render("HELLHOUSE", True, (off*15,0,0))
            surf.blit(t,(W//2-t.get_width()//2+random.randint(-1,1),55+random.randint(-1,1)))
        t = font_title.render("HELLHOUSE", True, BLOOD_RED)
        surf.blit(t,(W//2-t.get_width()//2, 55))
        sub = font_big.render("Save Prapti From The Darkness", True, (200,150,100))
        surf.blit(sub,(W//2-sub.get_width()//2, 162))
        pygame.draw.line(surf,(80,30,20),(80,218),(W-80,218),2)
        # Controls
        col_left=100; col_desc=340; y_start=236
        surf.blit(font_med.render("CONTROLS",True,FIRE_ORANGE),(col_left,y_start))
        controls=[("W/S/A/D","Move"),("MOUSE","Aim"),("LEFT CLICK","Shoot"),
                  ("ESC","Quit"),("H","High Scores")]
        for i,(k,d) in enumerate(controls):
            y=y_start+42+i*36
            kw=font_small.render(k,True,FIRE_YELLOW)
            kbw=max(kw.get_width()+16,120)
            pygame.draw.rect(surf,(40,20,5),(col_left-4,y-4,kbw,kw.get_height()+8))
            pygame.draw.rect(surf,(100,60,20),(col_left-4,y-4,kbw,kw.get_height()+8),1)
            surf.blit(kw,(col_left+4,y))
            surf.blit(font_small.render("→",True,(100,80,60)),(col_left+kbw+6,y))
            surf.blit(font_small.render(d,True,WHITE),(col_desc,y))
        # Objectives
        col_right=W//2+60
        pygame.draw.line(surf,(60,25,15),(W//2+40,222),(W//2+40,H-88),1)
        surf.blit(font_med.render("OBJECTIVE",True,FIRE_ORANGE),(col_right,y_start))
        objs=[(PINK,"★  Find Prapti in the house"),
              (BLOOD_RED,"★  Kill all demons each wave"),
              (FIRE_ORANGE,"★  KILL THE BOSS guarding her"),
              (FIRE_YELLOW,"★  Walk near Prapti to rescue"),
              (GREEN_HP,"★  Grab health & ammo drops")]
        for i,(c,txt) in enumerate(objs):
            surf.blit(font_small.render(txt,True,c),(col_right,y_start+42+i*36))
        tips_y=y_start+42+len(objs)*36+12
        pygame.draw.rect(surf,(25,8,8),(col_right-8,tips_y-8,W-col_right-60,110))
        pygame.draw.rect(surf,(80,30,20),(col_right-8,tips_y-8,W-col_right-60,110),1)
        surf.blit(font_small.render("TIPS",True,FIRE_ORANGE),(col_right,tips_y))
        tips=["MINIMAP (top-right) shows all enemies & Prapti",
              "Boss guards Prapti — kill it first to rescue her",
              "Boss appears wave 3+ — dodge the bullet rings"]
        for i,tip in enumerate(tips):
            surf.blit(font_tiny.render(f"• {tip}",True,LIGHT_STONE),(col_right,tips_y+28+i*24))
        pygame.draw.line(surf,(80,30,20),(80,H-88),(W-80,H-88),2)
        legend=[(TEAL,"You"),(BLOOD_RED,"Demons"),(FIRE_ORANGE,"Boss"),(PINK,"Prapti")]
        for i,(c,l) in enumerate(legend):
            lx=100+i*200
            pygame.draw.circle(surf,c,(lx,H-58),8)
            pygame.draw.circle(surf,WHITE,(lx,H-58),8,1)
            surf.blit(font_small.render(l,True,c),(lx+14,H-66))
        pulse=abs(math.sin(frame*0.04))
        ec=(int(50*pulse),int(200*pulse+55),int(80*pulse))
        enter=font_med.render("PRESS  ENTER  TO BEGIN",True,ec)
        surf.blit(enter,(W//2-enter.get_width()//2,H-34))
        surf.blit(font_tiny.render("Made by  PRAPTI",True,(100,80,60)),(W-140,H-18))

    @staticmethod
    def draw_scores(surf, storage: StorageManager, frame):
        """High scores screen with summary report."""
        surf.fill((5,3,3))
        t = font_big.render("HIGH SCORES", True, FIRE_ORANGE)
        surf.blit(t,(W//2-t.get_width()//2, 30))
        pygame.draw.line(surf,(80,30,20),(80,90),(W-80,90),2)
        top = storage.get_top_scores(8)
        headers=["#","NAME","SCORE","KILLS","WON","DATE"]
        col_x=[100,160,380,520,620,720]
        for j,h in enumerate(headers):
            surf.blit(font_small.render(h,True,FIRE_YELLOW),(col_x[j],100))
        pygame.draw.line(surf,(60,40,20),(80,122),(W-80,122),1)
        for i,s in enumerate(top):
            y=130+i*38
            row_col=WHITE if i%2==0 else LIGHT_STONE
            surf.blit(font_small.render(str(i+1),True,FIRE_ORANGE),(col_x[0],y))
            surf.blit(font_small.render(s.get("name","?")[:14],True,row_col),(col_x[1],y))
            surf.blit(font_small.render(f"{s.get('score',0):,}",True,FIRE_YELLOW),(col_x[2],y))
            surf.blit(font_small.render(str(s.get("kills",0)),True,BLOOD_RED),(col_x[3],y))
            won_txt="YES" if s.get("won") else "NO"
            won_col=GREEN_HP if s.get("won") else BLOOD_RED
            surf.blit(font_small.render(won_txt,True,won_col),(col_x[4],y))
            surf.blit(font_tiny.render(s.get("date",""),True,STONE_GREY),(col_x[5],y))
        # Summary
        rep=storage.summary_report()
        pygame.draw.line(surf,(80,30,20),(80,H-180),(W-80,H-180),1)
        surf.blit(font_med.render("SUMMARY REPORT",True,FIRE_ORANGE),(100,H-170))
        summary=[
            f"Total Games: {rep['total_games']}",
            f"Avg Score:   {rep['avg_score']:,}",
            f"Total Kills: {rep['total_kills']}",
        ]
        for i,s in enumerate(summary):
            surf.blit(font_small.render(s,True,LIGHT_STONE),(100,H-140+i*30))
        back=font_med.render("ESC — Back to Menu",True,GREEN_HP)
        surf.blit(back,(W//2-back.get_width()//2,H-30))

    @staticmethod
    def draw_gameover(surf, player, hi_score, frame):
        """Game over screen."""
        surf.fill((5,2,2))
        for off in range(6,0,-2):
            t=font_title.render("YOU DIED",True,(off*20,0,0))
            surf.blit(t,(W//2-t.get_width()//2+random.randint(-2,2),H//2-210+random.randint(-2,2)))
        t=font_title.render("YOU DIED",True,BLOOD_RED)
        surf.blit(t,(W//2-t.get_width()//2,H//2-210))
        bx,by,bw,bh=W//2-200,H//2-80,400,160
        pygame.draw.rect(surf,(20,8,8),(bx,by,bw,bh))
        pygame.draw.rect(surf,(100,20,20),(bx,by,bw,bh),2)
        for i,l in enumerate([f"Score   :  {player.score:,}",
                               f"Best    :  {hi_score:,}",
                               f"Kills   :  {player.kills}"]):
            t=font_med.render(l,True,LIGHT_STONE)
            surf.blit(t,(bx+20,by+20+i*44))
        pulse=abs(math.sin(frame*0.06))
        rc=(int(200+55*pulse),int(80+40*pulse),0)
        r=font_med.render("ENTER — retry    ESC — quit",True,rc)
        surf.blit(r,(W//2-r.get_width()//2,H//2+110))

    @staticmethod
    def draw_win(surf, player, frame):
        """Victory screen."""
        surf.fill((4,8,4))
        for _ in range(3):
            pygame.draw.circle(surf,(255,200,255),
                (random.randint(0,W),random.randint(0,H)),random.randint(1,3))
        pulse=abs(math.sin(frame*0.04))
        tc=(int(50*pulse+200),int(200*pulse+55),int(80*pulse+100))
        t=font_title.render("PRAPTI IS SAFE!",True,tc)
        surf.blit(t,(W//2-t.get_width()//2,H//2-200))
        sub=font_big.render("You saved her from the darkness.",True,PINK)
        surf.blit(sub,(W//2-sub.get_width()//2,H//2-110))
        bx,by,bw,bh=W//2-220,H//2-40,440,120
        pygame.draw.rect(surf,(5,20,5),(bx,by,bw,bh))
        pygame.draw.rect(surf,(30,100,30),(bx,by,bw,bh),2)
        surf.blit(font_med.render(f"Final Score:  {player.score:,}",True,FIRE_YELLOW),(bx+20,by+15))
        surf.blit(font_med.render(f"Demons Slain:  {player.kills}",True,BLOOD_RED),(bx+20,by+59))
        r=font_med.render("ENTER — play again    ESC — quit",True,GREEN_HP)
        surf.blit(r,(W//2-r.get_width()//2,H//2+110))
        surf.blit(font_tiny.render("Made by  PRAPTI",True,(80,120,80)),(W-140,H-18))

    @staticmethod
    def draw_name_input(surf, name, frame):
        """Prompt player to enter their name after game ends."""
        surf.fill((5,3,5))
        t = font_big.render("ENTER YOUR NAME", True, FIRE_ORANGE)
        surf.blit(t,(W//2-t.get_width()//2, H//2-100))
        # input box
        bx,by,bw,bh = W//2-160, H//2-20, 320, 50
        pygame.draw.rect(surf,(30,15,30),(bx,by,bw,bh))
        pygame.draw.rect(surf,FIRE_ORANGE,(bx,by,bw,bh),2)
        cursor = "|" if (frame//20)%2==0 else ""
        nt = font_big.render(name + cursor, True, WHITE)
        surf.blit(nt,(bx+10, by+8))
        hint = font_small.render("Press ENTER to confirm", True, LIGHT_STONE)
        surf.blit(hint,(W//2-hint.get_width()//2, H//2+50))


# ═══════════════════════════════════════════════════════════════════
#  GAME ENGINE  (composition of all systems)
# ═══════════════════════════════════════════════════════════════════
class GameEngine:
    """
    Core game logic. Composes Player, Spawner, Girlfriend, BossDemon,
    Bullet lists, Pickup list, and UIController.
    """
    PLAYER_START_X = 3 * TILE_SIZE + 24
    PLAYER_START_Y = 3 * TILE_SIZE + 24

    def __init__(self, hi_score=0):
        self.tiles    = parse_map()
        self.player   = Player(self.PLAYER_START_X, self.PLAYER_START_Y)
        self.spawner  = Spawner(self.tiles, self.PLAYER_START_X, self.PLAYER_START_Y)
        self.gf       = Girlfriend()
        self.boss     = BossDemon()
        self.bullets  = []    # player bullets
        self.e_bullets= []    # enemy bullets
        self.demons   = []
        self.pickups  = []
        self.flash    = []    # [text,color,timer,x,y]
        self.wave     = 1
        self.state    = "playing"
        self.hi_score = hi_score
        self.frame    = 0
        self.start_time = pygame.time.get_ticks()
        particles.clear()
        self._start_wave()
        self._add_flash("FIND PRAPTI. KILL THEM ALL.", BLOOD_RED)

    def _add_flash(self, txt, col=WHITE, x=W//2, y=H//2-80):
        self.flash.append([txt, col, 80, x, y])

    def _start_wave(self):
        self.demons = self.spawner.spawn_wave(self.wave)
        self._add_flash(f"WAVE {self.wave} — FIGHT!", FIRE_ORANGE)

    @property
    def cam_x(self):
        return int(max(W//2, min(MAP_W*TILE_SIZE-W//2, self.player.x)))

    @property
    def cam_y(self):
        return int(max(H//2, min(MAP_H*TILE_SIZE-H//2, self.player.y)))

    def _spawn_pickup(self, x, y):
        if random.random() < 0.30:
            kind = random.choice(['ammo','ammo','health','score'])
            self.pickups.append(Pickup(x, y, kind))

    def update(self, keys, mx, my):
        """Main update loop."""
        if self.state != "playing":
            return
        self.frame += 1
        p = self.player

        p.update_angle(mx, my, self.cam_x, self.cam_y)
        p.update(keys, self.tiles)

        if pygame.mouse.get_pressed()[0]:
            p.shoot(self.bullets, mx, my, self.cam_x, self.cam_y)

        # bullets
        for b in self.bullets:   b.update(self.tiles)
        for b in self.e_bullets: b.update(self.tiles)
        self.bullets   = [b for b in self.bullets   if b.alive]
        self.e_bullets = [b for b in self.e_bullets if b.alive]

        # pickups
        for pk in self.pickups: pk.update(p)
        self.pickups = [pk for pk in self.pickups if pk.alive]

        # boss (always present near Prapti)
        boss_alive = self.boss is not None and self.boss.alive
        if boss_alive:
            self.boss.update(p, self.tiles, self.e_bullets)
        elif self.boss is not None:
            self.boss = None   # clean up dead boss immediately

        # demons
        all_enemies = self.demons[:]
        if boss_alive:
            all_enemies.append(self.boss)
        for d in all_enemies:
            d.update(p, self.tiles, self.e_bullets)

        # girlfriend — can only rescue when boss dead
        self.gf.update(p, self.boss is not None)

        # player bullets vs enemies
        for b in self.bullets:
            if not b.alive:
                continue
            for d in all_enemies:
                if not d.alive:
                    continue
                if math.hypot(b.x-d.x, b.y-d.y) < d.radius + b.radius:
                    killed = d.take_damage(b.damage)
                    b.alive = False
                    screen_shake(3)
                    if killed:
                        p.score += d.score_val
                        p.kills += 1
                        self._spawn_pickup(d.x, d.y)
                        if d is self.boss:
                            self.boss = None
                            self._add_flash("DEMON LORD SLAIN! RESCUE PRAPTI!", FIRE_ORANGE)
                            screen_shake(18)
                            burst(d.x, d.y, BLOOD_RED, 60, 10, 7, 80, 0.06)
                            burst(d.x, d.y, FIRE_ORANGE, 40, 8, 5, 60)
                    break

        # enemy bullets vs player
        pr = pygame.Rect(p.x-p.radius, p.y-p.radius, p.radius*2, p.radius*2)
        for b in self.e_bullets:
            if b.alive and pr.collidepoint(b.x, b.y):
                p.take_damage(b.damage)
                b.alive = False
                screen_shake(5)

        # clean dead demons
        self.demons = [d for d in self.demons if d.alive]

        # particles
        update_particles()

        # hi score
        if p.score > self.hi_score:
            self.hi_score = p.score

        # death
        if not p.alive:
            self.state = "dead"
            return

        # win — rescued Prapti
        if self.gf.rescued:
            self.state = "win"
            return

        # next wave (only regular demons; boss stays)
        if len(self.demons) == 0:
            self.wave += 1
            self._start_wave()

    def draw(self, surf):
        """Render the game world."""
        cx, cy = self.cam_x, self.cam_y
        surf.fill((15, 10, 8))
        draw_map(surf, self.tiles, cx, cy, self.frame)

        for pk in self.pickups:  pk.draw(surf, cx, cy)
        self.gf.draw(surf, cx, cy)

        for b in self.e_bullets: b.draw(surf, cx, cy)
        for d in self.demons:    d.draw(surf, cx, cy)
        if self.boss and self.boss.alive:
            self.boss.draw(surf, cx, cy)

        for b in self.bullets:   b.draw(surf, cx, cy)
        self.player.draw(surf, cx, cy)
        draw_particles(surf, cx-W//2, cy-H//2)

        boss_hp = (self.boss.hp/self.boss.max_hp) if (self.boss and self.boss.alive) else None
        kills_left = len(self.demons) + (1 if (self.boss and self.boss.alive) else 0)

        UIController.draw_minimap(surf, self.tiles, self.player,
                                  self.demons, self.boss, self.gf, self.frame)
        UIController.draw_hud(surf, self.player, self.wave, kills_left,
                               self.gf.rescued, boss_hp, self.frame)
        UIController.draw_flash(surf, self.flash)

    def session_duration(self) -> float:
        return (pygame.time.get_ticks() - self.start_time) / 1000.0


# ═══════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════
def main():
    """Entry point. Manages screen states and storage."""
    global _shake_amt
    storage = StorageManager()
    pygame.mouse.set_visible(False)

    state      = "title"
    game: GameEngine = None
    frame      = 0
    hi_score   = 0
    player_name= "PLAYER"
    input_name = ""
    pending_game: GameEngine = None   # held while entering name

    # Restore hi_score from saved scores
    top = storage.get_top_scores(1)
    if top:
        hi_score = top[0].get("score", 0)

    while True:
        clock.tick(FPS)
        frame += 1
        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if ev.type == pygame.KEYDOWN:
                # ── name input ─────────────────────────────────
                if state == "name_input":
                    if ev.key == pygame.K_RETURN and input_name.strip():
                        player_name = input_name.strip()[:20]
                        g = pending_game
                        won = (g.state == "win")
                        storage.add_score(player_name, g.player.score,
                                          g.player.kills, won)
                        storage.log_session(player_name, g.player.score,
                                            g.player.kills, g.wave, won,
                                            g.session_duration())
                        hi_score = max(hi_score, g.player.score)
                        state = "win" if won else "dead"
                        game = g
                    elif ev.key == pygame.K_BACKSPACE:
                        input_name = input_name[:-1]
                    elif len(input_name) < 16 and ev.unicode.isprintable():
                        input_name += ev.unicode
                    continue

                # ── global ──────────────────────────────────────
                if ev.key == pygame.K_ESCAPE:
                    if state in ("playing",):
                        state = "title"; game = None; particles.clear()
                    elif state == "scores":
                        state = "title"
                    else:
                        pygame.quit(); sys.exit()

                # ── title ───────────────────────────────────────
                if state == "title":
                    if ev.key == pygame.K_RETURN:
                        particles.clear()
                        game = GameEngine(hi_score)
                        state = "playing"
                    elif ev.key == pygame.K_h:
                        state = "scores"

                # ── playing ─────────────────────────────────────
                elif state == "playing":
                    pass  # keys handled in game.update

                # ── dead / win ──────────────────────────────────
                elif state in ("dead", "win"):
                    if ev.key == pygame.K_RETURN:
                        particles.clear()
                        game = GameEngine(hi_score)
                        state = "playing"

        # ── Update ──────────────────────────────────────────────
        if state == "playing" and game:
            game.update(keys, mx, my)
            # transition to name input when game ends
            if game.state in ("dead", "win") and state == "playing":
                pending_game = game
                input_name   = ""
                state        = "name_input"

        # ── Draw ────────────────────────────────────────────────
        ox, oy = get_shake()

        if state == "title":
            UIController.draw_title(screen, frame)

        elif state == "playing" and game:
            ds = pygame.Surface((W, H))
            game.draw(ds)
            UIController.draw_crosshair(ds, mx, my)
            screen.blit(ds, (ox, oy))

        elif state == "name_input":
            UIController.draw_name_input(screen, input_name, frame)

        elif state == "dead" and game:
            UIController.draw_gameover(screen, game.player, hi_score, frame)

        elif state == "win" and game:
            UIController.draw_win(screen, game.player, frame)

        elif state == "scores":
            UIController.draw_scores(screen, storage, frame)

        pygame.display.flip()


if __name__ == "__main__":
    main()