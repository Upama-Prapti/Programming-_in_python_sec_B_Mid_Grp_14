import pygame
import math
import random
import sys
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
#  SCORES & SESSION LOG FILES
# ─────────────────────────────────────────────
SCORES_FILE  = "scores.json"
SESSION_FILE = "sessionlogs.txt"

def load_scores():
    """Load scores.json — returns dict with hi_score and leaderboard list."""
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, "r") as f:
                data = json.load(f)
                return data
        except:
            pass
    # default structure
    return {
        "hi_score": 0,
        "total_games": 0,
        "total_kills": 0,
        "leaderboard": []   # list of {score, kills, wave, result, date}
    }

def save_scores(data):
    """Write scores.json to disk."""
    try:
        with open(SCORES_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[scores] Could not save: {e}")

def log_session(score, kills, wave, result, duration_sec):
    """Append one line to sessionlogs.txt."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = (f"[{timestamp}]  result={result:<6}  score={score:<8,}  "
                f"kills={kills:<4}  wave={wave:<3}  time={duration_sec:.0f}s\n")
        with open(SESSION_FILE, "a") as f:
            f.write(line)
    except Exception as e:
        print(f"[session] Could not log: {e}")

def update_scores(scores_data, score, kills, wave, result):
    """Update leaderboard and hi_score in the scores dict."""
    scores_data["total_games"]  += 1
    scores_data["total_kills"]  += kills
    if score > scores_data["hi_score"]:
        scores_data["hi_score"] = score
    # add to leaderboard
    entry = {
        "score": score,
        "kills": kills,
        "wave":  wave,
        "result": result,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    scores_data["leaderboard"].append(entry)
    # keep only top 10 by score
    scores_data["leaderboard"].sort(key=lambda x: x["score"], reverse=True)
    scores_data["leaderboard"] = scores_data["leaderboard"][:10]
    return scores_data

# ─────────────────────────────────────────────
#  INIT
# ─────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

W, H   = 1280, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("HELLHOUSE | Save Prapti")
clock  = pygame.time.Clock()
FPS    = 60

# ─────────────────────────────────────────────
#  COLOURS
# ─────────────────────────────────────────────
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
RED        = (180, 10,  10)
DARK_RED   = (100, 0,   0)
ORANGE     = (255, 120, 0)
YELLOW     = (255, 220, 0)
GREEN      = (50,  200, 80)
PINK       = (255, 150, 200)
PURPLE     = (140, 0,   200)
TEAL       = (0,   200, 180)
BROWN      = (80,  50,  20)
DARK_BROWN = (40,  25,  10)
GREY       = (70,  70,  80)
DARK_GREY  = (40,  40,  50)
FLOOR      = (55,  45,  35)
WALL       = (45,  42,  55)
SKIN       = (220, 180, 140)
BLUE       = (40,  80,  160)
BLOOD      = (150, 0,   0)
BRIDGE     = (100, 70,  30)
DRAGON_G   = (20,  140, 40)   # dragon green
DRAGON_D   = (10,  80,  20)   # dark dragon
FIRE_COL   = (255, 80,  0)    # dragon fire

# ─────────────────────────────────────────────
#  FONTS
# ─────────────────────────────────────────────
font_big   = pygame.font.SysFont("Consolas", 72, bold=True)
font_med   = pygame.font.SysFont("Consolas", 32, bold=True)
font_small = pygame.font.SysFont("Consolas", 20)
font_tiny  = pygame.font.SysFont("Consolas", 15)

# ─────────────────────────────────────────────
#  SOUND
# ─────────────────────────────────────────────
def make_beep(freq=440, dur=0.08, vol=0.2):
    try:
        import numpy as np
        sr = 44100
        n  = int(sr * dur)
        t  = np.linspace(0, dur, n)
        w  = np.sign(np.sin(2 * np.pi * freq * t))
        w  = (w * np.linspace(1,0,n) * vol * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([w, w]))
    except:
        return None

snd_shoot   = make_beep(700,  0.06, 0.18)
snd_enemy   = make_beep(400,  0.06, 0.12)
snd_die     = make_beep(100,  0.35, 0.30)
snd_hit     = make_beep(250,  0.05, 0.15)
snd_pickup  = make_beep(800,  0.12, 0.20)
snd_rescued = make_beep(500,  0.40, 0.25)
snd_hurt    = make_beep(200,  0.08, 0.20)
snd_roar    = make_beep(60,   0.50, 0.35)
snd_dragon  = make_beep(120,  0.20, 0.25)

def play(snd):
    if snd:
        try: snd.play()
        except: pass

# ─────────────────────────────────────────────
#  MAP
#  0=floor 1=wall 2=door 3=window 4=blood 5=carpet 6=bridge
# ─────────────────────────────────────────────
TILE  = 48
MAP_W = 42
MAP_H = 32

MAP = [
    "111111111111111111111111111111111111111111",
    "100000000111000000001110000000011111111111",
    "105000000111000000001110000000011111111111",
    "105500000211000000002110000000021111111111",
    "105000000111000000001110000000011111111111",
    "100000000111044400001110444000011111111111",
    "111121111110100111101100211110111111111111",
    "100000000000060000000006000000000000000001",
    "100000000000060000000006000000000000000001",
    "100000000000060000000006000000000000000001",
    "100000000000060000000006000000000000000001",
    "100000000000060000000006000000000000000001",
    "111111211110101111111010121111111111111111",
    "100000001110000000000000000111000000000001",
    "100000002110000000000000000211000000000001",
    "100000001110000000000000000111000000000001",
    "100000001110000000000000000111000000000001",
    "100000001110044000000000440111000000000001",
    "111111101110101111111010101110111111111111",
    "100000000000060000000006000000000000000001",
    "100000000000060000000006000000000000000001",
    "100000000000060000000006000000000000000001",
    "100000000000060000000006000000000000000001",
    "111121111111111111112111111111112111111111",
    "100000001100000000000000000011000000000001",
    "100000002100000000000000000021000000000001",
    "100000001100000005555000000011000000000001",
    "100000001100000005555000000011000000000001",
    "100000001100000000000000000011000000000001",
    "100000001100000000000000000011000000000001",
    "100000001100000000000000000011000000000001",
    "111111111111111111111111111111111111111111",
]

tiles = [[int(c) for c in row] for row in MAP]

# Boss + Prapti location (same room — bottom section centre)
BOSS_X    = 20 * TILE + 24
BOSS_Y    = 26 * TILE + 24
PRAPTI_X  = 20 * TILE + 24
PRAPTI_Y  = 28 * TILE + 24

def is_wall(x, y):
    tx = int(x // TILE)
    ty = int(y // TILE)
    if tx < 0 or ty < 0 or tx >= MAP_W or ty >= MAP_H:
        return True
    t = tiles[ty][tx]
    return t == 1 or t == 3

# ─────────────────────────────────────────────
#  PARTICLES
# ─────────────────────────────────────────────
all_particles = []

def add_particles(x, y, color, count=12, speed=4, size=4, life=30):
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        spd   = random.uniform(speed * 0.3, speed)
        vx    = math.cos(angle) * spd
        vy    = math.sin(angle) * spd
        all_particles.append([x, y, vx, vy, life, life,
                               color[0], color[1], color[2], size])

def update_particles():
    for p in all_particles:
        p[0] += p[2]; p[1] += p[3]
        p[3] += 0.06; p[2] *= 0.96; p[4] -= 1
    all_particles[:] = [p for p in all_particles if p[4] > 0]

def draw_particles(surf, cam_x, cam_y):
    for p in all_particles:
        ratio = p[4] / p[5]
        col   = (int(p[6]*ratio), int(p[7]*ratio), int(p[8]*ratio))
        size  = max(1, int(p[9] * ratio))
        sx    = int(p[0] - cam_x + W//2)
        sy    = int(p[1] - cam_y + H//2)
        pygame.draw.circle(surf, col, (sx, sy), size)

# ─────────────────────────────────────────────
#  SCREEN SHAKE
# ─────────────────────────────────────────────
shake = 0

def do_shake(amt=8):
    global shake
    shake = max(shake, amt)

def get_shake_offset():
    global shake
    if shake > 0.3:
        ox = random.randint(-int(shake), int(shake))
        oy = random.randint(-int(shake), int(shake))
        shake *= 0.82
        return ox, oy
    shake = 0
    return 0, 0

# ─────────────────────────────────────────────
#  CAMERA
# ─────────────────────────────────────────────
def get_camera(player):
    cx = int(max(W//2, min(MAP_W*TILE - W//2, player["x"])))
    cy = int(max(H//2, min(MAP_H*TILE - H//2, player["y"])))
    return cx, cy

# ─────────────────────────────────────────────
#  PLAYER
# ─────────────────────────────────────────────
def make_player():
    return {
        "x": 3*TILE+24, "y": 3*TILE+24,
        "hp": 120, "max_hp": 120,
        "ammo": 60, "max_ammo": 60,
        "angle": 0.0,
        "shoot_cd": 0, "inv_cd": 0,
        "alive": True, "kills": 0, "score": 0,
        "anim": 0, "foot": 0, "muzzle": 0,
        "radius": 14,
    }

def move_player(p, keys):
    dx = dy = 0
    if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:   dy += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:   dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  dx += 1
    if dx and dy: dx *= 0.707; dy *= 0.707
    spd = 3.5
    nx = p["x"] + dx*spd; ny = p["y"] + dy*spd
    r  = p["radius"] - 2
    corners = [(-r,-r),(r,-r),(-r,r),(r,r)]
    if not any(is_wall(nx+ox, p["y"]+oy) for ox,oy in corners): p["x"] = nx
    if not any(is_wall(p["x"]+ox, ny+oy) for ox,oy in corners): p["y"] = ny
    p["anim"] = (p["anim"]+1) % 20
    if dx or dy: p["foot"] = (p["foot"]+1) % 30

def update_player(p, keys):
    if not p["alive"]: return
    if p["shoot_cd"] > 0: p["shoot_cd"] -= 1
    if p["inv_cd"]   > 0: p["inv_cd"]   -= 1
    if p["muzzle"]   > 0: p["muzzle"]   -= 1
    move_player(p, keys)