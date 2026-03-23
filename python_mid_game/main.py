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
def aim_player(p, mx, my, cam_x, cam_y):
    wx = mx + cam_x - W//2
    wy = my + cam_y - H//2
    p["angle"] = math.atan2(wy - p["y"], wx - p["x"])

def player_shoot(p, bullets, mx, my, cam_x, cam_y):
    if p["shoot_cd"] > 0 or p["ammo"] <= 0: return
    p["shoot_cd"] = 8; p["ammo"] -= 1; p["muzzle"] = 6
    wx = mx + cam_x - W//2; wy = my + cam_y - H//2
    angle = math.atan2(wy-p["y"], wx-p["x"]) + random.uniform(-0.05,0.05)
    bullets.append(make_bullet(p["x"], p["y"], angle, 14, 25, YELLOW, True))
    play(snd_shoot)
    gx = p["x"] + math.cos(angle)*24
    gy = p["y"] + math.sin(angle)*24
    add_particles(gx, gy, ORANGE, 6, 5, 3, 10)

def hurt_player(p, dmg):
    if p["inv_cd"] > 0: return
    p["hp"] -= dmg; p["inv_cd"] = 40
    play(snd_hurt)
    add_particles(p["x"], p["y"], BLOOD, 10, 4, 4, 30)
    if p["hp"] <= 0: p["hp"] = 0; p["alive"] = False

def draw_player(surf, p, cam_x, cam_y):
    if not p["alive"]: return
    if p["inv_cd"] > 0 and (p["inv_cd"]//4)%2 == 0: return
    sx = int(p["x"]-cam_x+W//2); sy = int(p["y"]-cam_y+H//2)
    pygame.draw.ellipse(surf,(20,15,10),(sx-14,sy+10,28,10))
    leg = int(math.sin(p["foot"]*0.4)*5)
    pygame.draw.line(surf,(30,30,50),(sx,sy+4),(sx-7,sy+16+leg),4)
    pygame.draw.line(surf,(30,30,50),(sx,sy+4),(sx+7,sy+16-leg),4)
    pygame.draw.circle(surf,(20,15,10),(sx-7,sy+18+leg),4)
    pygame.draw.circle(surf,(20,15,10),(sx+7,sy+18-leg),4)
    pygame.draw.circle(surf,BLUE,(sx,sy),12)
    pygame.draw.circle(surf,(30,60,130),(sx,sy),12,2)
    angle = p["angle"]
    ax = sx+int(math.cos(angle)*10); ay = sy+int(math.sin(angle)*10)
    pygame.draw.line(surf,SKIN,(sx,sy),(ax,ay),5)
    gx = sx+int(math.cos(angle)*24); gy = sy+int(math.sin(angle)*24)
    pygame.draw.line(surf,(50,50,60),(ax,ay),(gx,gy),4)
    if p["muzzle"] > 0:
        for r in range(10,2,-3):
            gc=(min(255,p["muzzle"]*40),min(255,p["muzzle"]*20),0)
            pygame.draw.circle(surf,gc,(gx,gy),r)
    pygame.draw.circle(surf,SKIN,(sx,sy-12),10)
    pygame.draw.circle(surf,(180,140,100),(sx,sy-12),10,1)
    pygame.draw.arc(surf,(40,25,10),(sx-10,sy-24,20,16),0,math.pi,5)
    edx=int(math.cos(angle)*4); edy=int(math.sin(angle)*4)
    pygame.draw.circle(surf,WHITE,(sx+edx-2,sy-12+edy),3)
    pygame.draw.circle(surf,(30,30,80),(sx+edx-2,sy-12+edy),1)

# ─────────────────────────────────────────────
#  BULLETS
# ─────────────────────────────────────────────
def make_bullet(x, y, angle, speed, dmg, color, friendly):
    return {"x":x,"y":y,
            "vx":math.cos(angle)*speed,
            "vy":math.sin(angle)*speed,
            "dmg":dmg,"color":color,
            "friendly":friendly,"alive":True,"trail":[]}

def update_bullet(b):
    b["trail"].append((b["x"],b["y"]))
    if len(b["trail"])>6: b["trail"].pop(0)
    b["x"]+=b["vx"]; b["y"]+=b["vy"]
    tx=int(b["x"]//TILE); ty=int(b["y"]//TILE)
    if 0<=tx<MAP_W and 0<=ty<MAP_H:
        t=tiles[ty][tx]
        if t==1 or t==3:
            b["alive"]=False
            add_particles(b["x"],b["y"],GREY,5,2,2,10)
    else:
        b["alive"]=False

def draw_bullet(surf, b, cam_x, cam_y):
    for i,(tx,ty) in enumerate(b["trail"]):
        a=(i+1)/len(b["trail"])
        col=tuple(int(v*a*0.5) for v in b["color"])
        pygame.draw.circle(surf,col,(int(tx-cam_x),int(ty-cam_y)),max(1,int(3*a)))
    sx=int(b["x"]-cam_x); sy=int(b["y"]-cam_y)
    pygame.draw.circle(surf,WHITE,(sx,sy),4)
    pygame.draw.circle(surf,b["color"],(sx,sy),3)

# ─────────────────────────────────────────────
#  ENEMY MOVEMENT HELPER
# ─────────────────────────────────────────────
def move_enemy(e, tx, ty, spd=None):
    if spd is None: spd = e["speed"]
    dx=tx-e["x"]; dy=ty-e["y"]; dist=max(1,math.hypot(dx,dy))
    nx=e["x"]+dx/dist*spd; ny=e["y"]+dy/dist*spd; r=e["radius"]-4
    corners=[(-r,-r),(r,-r),(-r,r),(r,r)]
    if not any(is_wall(nx+ox,e["y"]+oy) for ox,oy in corners): e["x"]=nx
    if not any(is_wall(e["x"]+ox,ny+oy) for ox,oy in corners): e["y"]=ny

def hurt_enemy(e, dmg):
    e["hp"]-=dmg; e["hit_flash"]=8; play(snd_hit)
    if e["hp"]<=0:
        e["alive"]=False
        add_particles(e["x"],e["y"],BLOOD,25,5,5,40)
        add_particles(e["x"],e["y"],DARK_RED,10,3,3,30)
        play(snd_die); return True
    return False

def draw_hp_bar(surf, e, cam_x, cam_y, bw=36):
    sx=int(e["x"]-cam_x+W//2); sy=int(e["y"]-cam_y+H//2)
    bx=sx-bw//2; by=sy-e["radius"]-12
    rat=max(0,e["hp"]/e["max_hp"])
    pygame.draw.rect(surf,(60,0,0),(bx,by,bw,5))
    pygame.draw.rect(surf,RED,(bx,by,int(bw*rat),5))

# ─────────────────────────────────────────────
#  GRUNT DEMON
# ─────────────────────────────────────────────
def make_grunt(x, y, level=1):
    return {"kind":"grunt","x":x,"y":y,
            "hp":50+level*15,"max_hp":50+level*15,
            "speed":1.8+level*0.2,"dmg":12,"score":100+level*20,
            "radius":16,"alive":True,"anim":random.randint(0,20),
            "shoot_cd":random.randint(60,180),"attack_cd":0,"hit_flash":0,
            "wander_angle":random.uniform(0,math.tau),"wander_timer":0,
            "surround_angle":random.uniform(0,math.tau)}  # angle for surround formation

def update_grunt(e, player, bullets, boss_alive, boss_x, boss_y):
    e["anim"]=(e["anim"]+1)%20
    e["attack_cd"]=max(0,e["attack_cd"]-1)
    if e["hit_flash"]>0: e["hit_flash"]-=1
    dist_player=math.hypot(player["x"]-e["x"],player["y"]-e["y"])

    # SURROUND MODE: if player is near boss (within 350px) and boss alive
    # all grunts swarm in formation around player
    if boss_alive:
        dist_to_boss = math.hypot(boss_x-player["x"], boss_y-player["y"])
        if dist_to_boss < 350:
            # surround: each demon takes a different angle around player
            e["surround_angle"] += 0.02  # slowly rotate formation
            surround_dist = 100
            tx = player["x"] + math.cos(e["surround_angle"]) * surround_dist
            ty = player["y"] + math.sin(e["surround_angle"]) * surround_dist
            move_enemy(e, tx, ty, e["speed"] * 1.5)  # faster surround
            if dist_player < e["radius"]+player["radius"]+5 and e["attack_cd"]==0:
                hurt_player(player, e["dmg"]+5)  # extra damage in surround
                e["attack_cd"]=30
            return

    # Normal AI
    if dist_player < 300:
        move_enemy(e, player["x"], player["y"])
        if dist_player < e["radius"]+player["radius"]+5 and e["attack_cd"]==0:
            hurt_player(player, e["dmg"]); e["attack_cd"]=45
    else:
        e["wander_timer"]+=1
        if e["wander_timer"]>60:
            e["wander_angle"]=random.uniform(0,math.tau); e["wander_timer"]=0
        wx=e["x"]+math.cos(e["wander_angle"])*30
        wy=e["y"]+math.sin(e["wander_angle"])*30
        move_enemy(e,wx,wy,0.8)

def draw_grunt(surf, e, cam_x, cam_y):
    sx=int(e["x"]-cam_x+W//2); sy=int(e["y"]-cam_y+H//2); a=e["anim"]
    col=(255,80,80) if e["hit_flash"]>0 else (120,20,20)
    bob=int(math.sin(a*0.3)*3)
    pygame.draw.ellipse(surf,(15,8,8),(sx-16,sy+12,32,12))
    pygame.draw.circle(surf,col,(sx,sy+bob),16)
    pygame.draw.circle(surf,(200,40,10),(sx,sy+bob),16,2)
    pygame.draw.polygon(surf,(80,15,15),[(sx-8,sy-14+bob),(sx-14,sy-26+bob),(sx-4,sy-18+bob)])
    pygame.draw.polygon(surf,(80,15,15),[(sx+8,sy-14+bob),(sx+14,sy-26+bob),(sx+4,sy-18+bob)])
    for ex,ey in [(sx-5,sy-6+bob),(sx+5,sy-6+bob)]:
        pygame.draw.circle(surf,ORANGE,(ex,ey),5)
        pygame.draw.circle(surf,YELLOW,(ex,ey),3)
        pygame.draw.circle(surf,WHITE,(ex,ey),1)
    draw_hp_bar(surf,e,cam_x,cam_y)

# ─────────────────────────────────────────────
#  SHOOTER DEMON
# ─────────────────────────────────────────────
def make_shooter(x, y, level=1):
    return {"kind":"shooter","x":x,"y":y,
            "hp":40+level*12,"max_hp":40+level*12,
            "speed":1.2+level*0.1,"dmg":8,"score":150+level*30,
            "radius":16,"alive":True,"anim":random.randint(0,20),
            "shoot_cd":random.randint(60,120),"attack_cd":0,"hit_flash":0,
            "wander_angle":random.uniform(0,math.tau),"wander_timer":0,
            "surround_angle":random.uniform(0,math.tau)}

def update_shooter(e, player, bullets, boss_alive, boss_x, boss_y):
    e["anim"]=(e["anim"]+1)%20
    if e["hit_flash"]>0: e["hit_flash"]-=1
    if e["shoot_cd"]>0: e["shoot_cd"]-=1
    dist_player=math.hypot(player["x"]-e["x"],player["y"]-e["y"])

    # SURROUND MODE near boss
    if boss_alive:
        dist_to_boss=math.hypot(boss_x-player["x"],boss_y-player["y"])
        if dist_to_boss < 350:
            e["surround_angle"]+=0.015
            surround_dist=160
            tx=player["x"]+math.cos(e["surround_angle"])*surround_dist
            ty=player["y"]+math.sin(e["surround_angle"])*surround_dist
            move_enemy(e,tx,ty,e["speed"]*1.3)
            # shoot from surround position
            if e["shoot_cd"]==0 and dist_player<250:
                angle=math.atan2(player["y"]-e["y"],player["x"]-e["x"])+random.uniform(-0.1,0.1)
                bullets.append(make_bullet(e["x"],e["y"],angle,8,e["dmg"]+3,PURPLE,False))
                e["shoot_cd"]=40; play(snd_enemy)
            return

    # Normal AI
    if dist_player<320:
        if dist_player<160:
            dx=e["x"]-player["x"]; dy=e["y"]-player["y"]
            d=max(1,math.hypot(dx,dy))
            move_enemy(e,e["x"]+dx/d*40,e["y"]+dy/d*40)
        elif dist_player>220:
            move_enemy(e,player["x"],player["y"])
        if e["shoot_cd"]==0 and dist_player<300:
            angle=math.atan2(player["y"]-e["y"],player["x"]-e["x"])+random.uniform(-0.15,0.15)
            bullets.append(make_bullet(e["x"],e["y"],angle,7,e["dmg"],PURPLE,False))
            e["shoot_cd"]=random.randint(60,100); play(snd_enemy)
    else:
        e["wander_timer"]+=1
        if e["wander_timer"]>80: e["wander_angle"]=random.uniform(0,math.tau); e["wander_timer"]=0
        move_enemy(e,e["x"]+math.cos(e["wander_angle"])*30,
                     e["y"]+math.sin(e["wander_angle"])*30,0.6)

def draw_shooter(surf, e, cam_x, cam_y):
    sx=int(e["x"]-cam_x+W//2); sy=int(e["y"]-cam_y+H//2); a=e["anim"]
    col=(200,120,255) if e["hit_flash"]>0 else (40,20,100)
    bob=int(math.sin(a*0.2)*6)
    pygame.draw.ellipse(surf,(10,5,20),(sx-14,sy+12,28,10))
    pygame.draw.circle(surf,col,(sx,sy+bob),15)
    pygame.draw.circle(surf,PURPLE,(sx,sy+bob),15,2)
    for i in range(4):
        tang=a*0.05+i*math.pi/2
        tx2=sx+int(math.cos(tang)*12); ty2=sy+bob+14+int(math.sin(tang*2)*8)
        pygame.draw.line(surf,PURPLE,(sx,sy+bob+12),(tx2,ty2),3)
    for ex2,ey2 in [(sx-6,sy-4+bob),(sx+6,sy-4+bob),(sx,sy-10+bob)]:
        pygame.draw.circle(surf,PURPLE,(ex2,ey2),5)
        pygame.draw.circle(surf,(200,100,255),(ex2,ey2),3)
        pygame.draw.circle(surf,WHITE,(ex2,ey2),1)
    draw_hp_bar(surf,e,cam_x,cam_y)

# ─────────────────────────────────────────────
#  BOSS DEMON — guards Prapti
# ─────────────────────────────────────────────
def make_boss():
    return {"kind":"boss",
            "x":float(BOSS_X),"y":float(BOSS_Y),
            "hp":600,"max_hp":600,
            "speed":1.0,"dmg":28,"score":3000,
            "radius":32,"alive":True,
            "anim":0,"spin":0,
            "shoot_cd":0,"attack_cd":0,"hit_flash":0,
            "pattern":0,"enraged":False,
            "roar_cd":0}

def update_boss(e, player, bullets):
    e["anim"]=(e["anim"]+1)%60
    e["spin"]=(e["spin"]+2)%360
    if e["hit_flash"]>0: e["hit_flash"]-=1
    if e["shoot_cd"]>0: e["shoot_cd"]-=1
    if e["attack_cd"]>0: e["attack_cd"]-=1
    if e["roar_cd"]>0: e["roar_cd"]-=1

    if not e["enraged"] and e["hp"]<e["max_hp"]*0.4:
        e["enraged"]=True; e["speed"]=2.2
        add_particles(e["x"],e["y"],RED,50,10,7,70)
        do_shake(14); play(snd_roar)

    dist=math.hypot(player["x"]-e["x"],player["y"]-e["y"])
    move_enemy(e,player["x"],player["y"])

    # melee
    if dist<e["radius"]+player["radius"]+5 and e["attack_cd"]==0:
        hurt_player(player,e["dmg"]); e["attack_cd"]=25; do_shake(8)

    # roar every 5s — warns surround incoming
    if e["roar_cd"]==0:
        e["roar_cd"]=300
        play(snd_roar)
        add_particles(e["x"],e["y"],ORANGE,30,8,5,50)

    # shooting patterns — faster when enraged
    cd=15 if e["enraged"] else 28
    if e["shoot_cd"]==0:
        e["shoot_cd"]=cd
        pat=e["pattern"]
        if pat==0:   # 8-way ring
            for i in range(8):
                ang=math.radians(e["spin"]+i*45)
                bullets.append(make_bullet(e["x"],e["y"],ang,7,16,RED,False))
        elif pat==1: # aimed triple
            ang=math.atan2(player["y"]-e["y"],player["x"]-e["x"])
            for off in (-0.25,0,0.25):
                bullets.append(make_bullet(e["x"],e["y"],ang+off,10,22,ORANGE,False))
        elif pat==2: # spiral
            for i in range(4):
                ang=math.radians(e["spin"]*2+i*90)
                bullets.append(make_bullet(e["x"],e["y"],ang,8,18,PURPLE,False))
        elif pat==3: # cross burst (enraged only)
            if e["enraged"]:
                for i in range(12):
                    ang=math.radians(i*30)
                    bullets.append(make_bullet(e["x"],e["y"],ang,6,14,RED,False))
            else:
                ang=math.atan2(player["y"]-e["y"],player["x"]-e["x"])
                bullets.append(make_bullet(e["x"],e["y"],ang,11,25,ORANGE,False))
        e["pattern"]=(e["pattern"]+1)%4
        play(snd_enemy)
