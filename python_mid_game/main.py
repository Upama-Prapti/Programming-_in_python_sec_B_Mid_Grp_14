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
def draw_boss(surf, e, cam_x, cam_y):
    sx=int(e["x"]-cam_x+W//2); sy=int(e["y"]-cam_y+H//2)
    col=(255,100,100) if e["hit_flash"]>0 else (150,15,15)
    ec=ORANGE if e["enraged"] else RED
    for r in range(45,22,-6):
        pygame.draw.circle(surf,(max(0,80-(45-r)*3),0,0),(sx,sy),r)
    pygame.draw.circle(surf,col,(sx,sy),32)
    pygame.draw.circle(surf,ec,(sx,sy),32,3)
    for i in range(6):
        ang=math.radians(e["spin"]+i*60)
        ax2=sx+int(math.cos(ang)*42); ay2=sy+int(math.sin(ang)*42)
        pygame.draw.line(surf,ec,(sx,sy),(ax2,ay2),5)
        pygame.draw.circle(surf,YELLOW,(ax2,ay2),7)
    for i in range(8):
        ang=math.radians(-e["spin"]*2+i*45)
        pygame.draw.circle(surf,ORANGE,
                           (sx+int(math.cos(ang)*22),sy+int(math.sin(ang)*22)),4)
    core=(255,50,50) if e["enraged"] else (200,20,20)
    pygame.draw.circle(surf,core,(sx,sy),14)
    pygame.draw.circle(surf,WHITE,(sx,sy),6)
    # boss HP bar at top of screen
    bw=500; bx2=W//2-bw//2; by2=10
    pygame.draw.rect(surf,(60,0,0),(bx2,by2,bw,22))
    pygame.draw.rect(surf,RED,(bx2,by2,int(bw*max(0,e["hp"]/e["max_hp"])),22))
    pygame.draw.rect(surf,WHITE,(bx2-1,by2-1,bw+2,24),2)
    lbl=font_small.render("☠  DEMON LORD  ☠",True,RED)
    surf.blit(lbl,(W//2-lbl.get_width()//2,by2+26))
    if e["enraged"]:
        en=font_tiny.render("!! ENRAGED !! DEMONS SWARMING !!",True,ORANGE)
        surf.blit(en,(W//2-en.get_width()//2,by2+46))

# ─────────────────────────────────────────────
#  DRAGON (boss pet) — orbits boss, breathes fire
# ─────────────────────────────────────────────
def make_dragon(boss_x, boss_y):
    return {"kind":"dragon",
            "x":float(boss_x+80),"y":float(boss_y),
            "hp":200,"max_hp":200,
            "speed":2.5,"dmg":20,"score":800,
            "radius":20,"alive":True,
            "anim":0,"angle":0.0,
            "orbit_angle":0.0,  # angle around boss
            "orbit_speed":0.025,
            "orbit_radius":110,
            "shoot_cd":45,"hit_flash":0,
            "fire_trail":[]}   # trail of fire particles

def update_dragon(d, boss, player, bullets):
    d["anim"]=(d["anim"]+1)%30
    if d["hit_flash"]>0: d["hit_flash"]-=1
    if d["shoot_cd"]>0: d["shoot_cd"]-=1

    # orbit around boss
    d["orbit_angle"]+=d["orbit_speed"]
    if boss and boss["alive"]:
        # orbit boss
        target_x=boss["x"]+math.cos(d["orbit_angle"])*d["orbit_radius"]
        target_y=boss["y"]+math.sin(d["orbit_angle"])*d["orbit_radius"]
        # speed toward orbit point
        dx=target_x-d["x"]; dy=target_y-d["y"]
        dist=max(1,math.hypot(dx,dy))
        d["x"]+=dx/dist*d["speed"]*2
        d["y"]+=dy/dist*d["speed"]*2
        d["angle"]=math.atan2(dy,dx)
    else:
        # boss dead — dragon charges player
        move_enemy(d,player["x"],player["y"])
        d["angle"]=math.atan2(player["y"]-d["y"],player["x"]-d["x"])

    # breathe fire at player
    dist_player=math.hypot(player["x"]-d["x"],player["y"]-d["y"])
    if d["shoot_cd"]==0 and dist_player<350:
        ang=math.atan2(player["y"]-d["y"],player["x"]-d["x"])
        # fire burst — 3 fire balls spread
        for off in (-0.15,0,0.15):
            bullets.append(make_bullet(d["x"],d["y"],ang+off,9,d["dmg"],FIRE_COL,False))
        d["shoot_cd"]=50; play(snd_dragon)
        add_particles(d["x"]+math.cos(ang)*25,d["y"]+math.sin(ang)*25,
                      FIRE_COL,10,6,4,20)

    # melee
    if dist_player<d["radius"]+14+5:
        hurt_player(player,d["dmg"]); do_shake(6)

def draw_dragon(surf, d, cam_x, cam_y):
    sx=int(d["x"]-cam_x+W//2); sy=int(d["y"]-cam_y+H//2)
    a=d["anim"]; angle=d["angle"]
    col=(255,180,100) if d["hit_flash"]>0 else DRAGON_G

    # shadow
    pygame.draw.ellipse(surf,(10,20,10),(sx-18,sy+14,36,12))

    # tail (wavy)
    for i in range(4):
        tail_ang=angle+math.pi+math.sin(a*0.3+i)*0.3
        tx2=sx+int(math.cos(tail_ang)*(i+1)*10)
        ty2=sy+int(math.sin(tail_ang)*(i+1)*10)
        r2=max(3,8-i*2)
        pygame.draw.circle(surf,DRAGON_D,(tx2,ty2),r2)

    # body
    pygame.draw.ellipse(surf,col,(sx-16,sy-10,32,22))
    pygame.draw.ellipse(surf,DRAGON_D,(sx-16,sy-10,32,22),2)

    # wings (flap with anim)
    wing_flap=int(math.sin(a*0.4)*8)
    # left wing
    pygame.draw.polygon(surf,(30,100,30),[
        (sx-8,sy),(sx-30,sy-20+wing_flap),(sx-20,sy-6)])
    # right wing
    pygame.draw.polygon(surf,(30,100,30),[
        (sx+8,sy),(sx+30,sy-20+wing_flap),(sx+20,sy-6)])

    # head
    head_x=sx+int(math.cos(angle)*20)
    head_y=sy+int(math.sin(angle)*20)
    pygame.draw.circle(surf,col,(head_x,head_y),10)
    pygame.draw.circle(surf,DRAGON_D,(head_x,head_y),10,2)

    # horn
    horn_ang=angle-math.pi/2
    pygame.draw.line(surf,DRAGON_D,(head_x,head_y),
                     (head_x+int(math.cos(horn_ang)*8),head_y+int(math.sin(horn_ang)*8)),2)

    # glowing eye
    eye_x=head_x+int(math.cos(angle)*5)
    eye_y=head_y+int(math.sin(angle)*5)
    pygame.draw.circle(surf,YELLOW,(eye_x,eye_y),4)
    pygame.draw.circle(surf,FIRE_COL,(eye_x,eye_y),2)

    # fire breath glow when shooting soon
    if d["shoot_cd"]<15:
        glow=int((15-d["shoot_cd"])*10)
        fc=(min(255,glow*3),min(255,glow),0)
        pygame.draw.circle(surf,fc,(head_x,head_y),6)

    draw_hp_bar(surf,d,cam_x,cam_y,bw=40)

# ─────────────────────────────────────────────
#  PRAPTI
# ─────────────────────────────────────────────
prapti_rescued = False
prapti_anim    = 0

def update_prapti(player, boss, dragon):
    global prapti_rescued
    boss_dead   = (boss is None or not boss["alive"])
    dragon_dead = (dragon is None or not dragon["alive"])
    # must kill BOTH boss AND dragon to rescue
    if boss_dead and dragon_dead and not prapti_rescued:
        dist=math.hypot(player["x"]-PRAPTI_X, player["y"]-PRAPTI_Y)
        if dist<80:
            prapti_rescued=True; play(snd_rescued)
            add_particles(PRAPTI_X,PRAPTI_Y,PINK,40,6,5,60)
            add_particles(PRAPTI_X,PRAPTI_Y,WHITE,20,4,3,40)

def draw_prapti(surf, cam_x, cam_y, frame):
    global prapti_anim
    prapti_anim+=1
    if prapti_rescued: return
    sx=int(PRAPTI_X-cam_x+W//2); sy=int(PRAPTI_Y-cam_y+H//2)
    a=prapti_anim
    pulse=abs(math.sin(a*0.05))
    for r in range(30,10,-5):
        gc=(int(255*pulse*(30-r)/20),0,int(200*pulse*(30-r)/20))
        pygame.draw.circle(surf,gc,(sx,sy),r+20)
    pygame.draw.ellipse(surf,(15,10,10),(sx-12,sy+10,24,10))
    leg=int(math.sin(a*0.15)*3)
    pygame.draw.line(surf,(180,100,140),(sx,sy+4),(sx-6,sy+16+leg),3)
    pygame.draw.line(surf,(180,100,140),(sx,sy+4),(sx+6,sy+16-leg),3)
    pygame.draw.circle(surf,(220,100,160),(sx,sy),11)
    pygame.draw.circle(surf,PINK,(sx,sy),11,2)
    pygame.draw.circle(surf,SKIN,(sx,sy-12),9)
    pygame.draw.arc(surf,(180,80,120),(sx-10,sy-24,20,16),0,math.pi,4)
    pygame.draw.circle(surf,(180,80,120),(sx-9,sy-16),4)
    pygame.draw.circle(surf,(180,80,120),(sx+9,sy-16),4)
    pygame.draw.circle(surf,WHITE,(sx-3,sy-12),3)
    pygame.draw.circle(surf,WHITE,(sx+4,sy-12),3)
    pygame.draw.circle(surf,(60,60,180),(sx-3,sy-12),1)
    pygame.draw.circle(surf,(60,60,180),(sx+4,sy-12),1)
    name=font_med.render("PRAPTI",True,PINK)
    surf.blit(name,(sx-name.get_width()//2,sy-70))
    lbl=font_tiny.render("SAVE ME!",True,PINK)
    surf.blit(lbl,(sx-lbl.get_width()//2,sy-48))

# ─────────────────────────────────────────────
#  PICKUPS
# ─────────────────────────────────────────────
all_pickups=[]

def spawn_pickup(x,y):
    if random.random()<0.35:
        kind=random.choice(["ammo","ammo","health","score"])
        all_pickups.append([x,y,kind,random.randint(0,30)])

def update_pickups(player):
    for pk in all_pickups:
        pk[3]+=1
        dist=math.hypot(player["x"]-pk[0],player["y"]-pk[1])
        if dist<28:
            pk.append("dead"); play(snd_pickup)
            if pk[2]=="ammo": player["ammo"]=min(player["max_ammo"],player["ammo"]+20); add_particles(pk[0],pk[1],YELLOW,8,4,3,20)
            elif pk[2]=="health": player["hp"]=min(player["max_hp"],player["hp"]+30); add_particles(pk[0],pk[1],GREEN,8,4,3,20)
            elif pk[2]=="score": player["score"]+=500; add_particles(pk[0],pk[1],YELLOW,8,4,3,20)
    all_pickups[:]=[pk for pk in all_pickups if len(pk)==4]

def draw_pickups(surf,cam_x,cam_y):
    for pk in all_pickups:
        sx=int(pk[0]-cam_x+W//2); sy=int(pk[1]-cam_y+H//2)+int(math.sin(pk[3]*0.1)*4)
        if pk[2]=="ammo":
            pygame.draw.rect(surf,YELLOW,(sx-10,sy-6,20,12)); pygame.draw.rect(surf,WHITE,(sx-10,sy-6,20,12),2)
            surf.blit(font_tiny.render("AMMO",True,YELLOW),(sx-16,sy-22))
        elif pk[2]=="health":
            pygame.draw.line(surf,GREEN,(sx,sy-10),(sx,sy+10),4); pygame.draw.line(surf,GREEN,(sx-10,sy),(sx+10,sy),4)
            surf.blit(font_tiny.render("+HP",True,GREEN),(sx-10,sy-22))
        else:
            pygame.draw.circle(surf,ORANGE,(sx,sy),10); pygame.draw.circle(surf,YELLOW,(sx,sy),10,2)
            surf.blit(font_tiny.render("$500",True,ORANGE),(sx-14,sy-22))

# ─────────────────────────────────────────────
#  MAP DRAWING
# ─────────────────────────────────────────────
def draw_map(surf,cam_x,cam_y):
    stx=max(0,cam_x//TILE-W//TILE//2-1); etx=min(MAP_W,cam_x//TILE+W//TILE//2+2)
    sty=max(0,cam_y//TILE-H//TILE//2-1); ety=min(MAP_H,cam_y//TILE+H//TILE//2+2)
    for ty in range(int(sty),int(ety)):
        for tx in range(int(stx),int(etx)):
            t=tiles[ty][tx]; px=tx*TILE-cam_x+W//2; py=ty*TILE-cam_y+H//2; r=(px,py,TILE,TILE)
            if t==0:
                pygame.draw.rect(surf,FLOOR,r); pygame.draw.rect(surf,(50,40,30),r,1)
            elif t==1:
                pygame.draw.rect(surf,WALL,r)
                for row in range(2):
                    by2=py+row*(TILE//2); off=(TILE//2) if row%2==0 else 0
                    pygame.draw.line(surf,DARK_GREY,(px+off,by2),(px+off,by2+TILE//2),1)
                pygame.draw.rect(surf,DARK_GREY,r,1)
            elif t==2:
                pygame.draw.rect(surf,FLOOR,r); pygame.draw.rect(surf,BROWN,(px+4,py+2,TILE-8,TILE-4))
                pygame.draw.rect(surf,DARK_BROWN,(px+4,py+2,TILE-8,TILE-4),2)
                pygame.draw.circle(surf,(180,140,60),(px+TILE-10,py+TILE//2),3)
            elif t==3:
                pygame.draw.rect(surf,WALL,r); pygame.draw.rect(surf,(60,100,150),(px+6,py+6,TILE-12,TILE-12))
                pygame.draw.line(surf,DARK_GREY,(px+TILE//2,py+6),(px+TILE//2,py+TILE-6),2)
                pygame.draw.line(surf,DARK_GREY,(px+6,py+TILE//2),(px+TILE-6,py+TILE//2),2)
            elif t==4:
                pygame.draw.rect(surf,FLOOR,r); pygame.draw.ellipse(surf,(100,0,0),(px+6,py+8,TILE-12,TILE-16))
            elif t==5:
                pygame.draw.rect(surf,(80,30,30),r); pygame.draw.rect(surf,(100,40,40),(px+4,py+4,TILE-8,TILE-8),2)
            elif t==6:
                pygame.draw.rect(surf,(30,20,8),r)
                for p in range(4):
                    py2=py+p*12
                    if py2<py+TILE:
                        pygame.draw.rect(surf,BRIDGE,(px+2,py2,TILE-4,8))
                        pygame.draw.rect(surf,DARK_BROWN,(px+2,py2,TILE-4,8),1)
                pygame.draw.line(surf,(150,100,40),(px+3,py),(px+3,py+TILE),2)
                pygame.draw.line(surf,(150,100,40),(px+TILE-3,py),(px+TILE-3,py+TILE),2)

# ─────────────────────────────────────────────
#  MINIMAP
# ─────────────────────────────────────────────
def draw_minimap(surf,player,enemies,boss,dragon,frame):
    mmw,mmh=180,130; mmx,mmy=W-mmw-10,10
    mm=pygame.Surface((mmw,mmh)); mm.fill((10,8,6))
    sx=mmw/(MAP_W*TILE); sy=mmh/(MAP_H*TILE)
    for ty in range(MAP_H):
        for tx in range(MAP_W):
            t=tiles[ty][tx]; px=int(tx*TILE*sx); py=int(ty*TILE*sy)
            pw=max(1,int(TILE*sx)); ph=max(1,int(TILE*sy))
            if t==1: col=GREY
            elif t==6: col=BRIDGE
            elif t==2: col=BROWN
            elif t in (0,4,5): col=(45,38,28)
            else: col=(45,38,28)
            pygame.draw.rect(mm,col,(px,py,pw,ph))
    ppx=int(player["x"]*sx); ppy=int(player["y"]*sy)
    pulse=abs(math.sin(frame*0.06))
    pygame.draw.circle(mm,(0,int(150+80*pulse),int(150+80*pulse)),(ppx,ppy),4)
    pygame.draw.circle(mm,WHITE,(ppx,ppy),2)
    for e in enemies: pygame.draw.circle(mm,RED,(int(e["x"]*sx),int(e["y"]*sy)),2)
    if boss and boss["alive"]:
        bp=abs(math.sin(frame*0.1)); bc=(int(200+55*bp),int(60*bp),0)
        pygame.draw.circle(mm,bc,(int(boss["x"]*sx),int(boss["y"]*sy)),6)
    if dragon and dragon["alive"]:
        pygame.draw.circle(mm,DRAGON_G,(int(dragon["x"]*sx),int(dragon["y"]*sy)),4)
    if not prapti_rescued:
        gp=abs(math.sin(frame*0.08)); gc=(int(255*gp),int(100*gp),int(200*gp))
        pygame.draw.circle(mm,gc,(int(PRAPTI_X*sx),int(PRAPTI_Y*sy)),4)
    pygame.draw.rect(mm,(100,70,30),(0,0,mmw,mmh),1)
    surf.blit(mm,(mmx,mmy))
    surf.blit(font_tiny.render("MINIMAP",True,(130,100,60)),
              (mmx+mmw//2-35,mmy+mmh+3))
 def draw_hud(surf,player,wave,enemies,boss,dragon,frame):
    panel=pygame.Surface((W,72)); panel.fill((8,5,4)); surf.blit(panel,(0,H-72))
    pulse=abs(math.sin(frame*0.03))
    pygame.draw.line(surf,(int(120+60*pulse),int(30*pulse),5),(0,H-72),(W,H-72),2)
    hp_w=200; hp_r=player["hp"]/player["max_hp"]
    pygame.draw.rect(surf,(30,0,0),(14,H-58,hp_w,18))
    fc=GREEN if hp_r>0.5 else (ORANGE if hp_r>0.25 else RED)
    pygame.draw.rect(surf,fc,(14,H-58,int(hp_w*hp_r),18))
    pygame.draw.rect(surf,WHITE,(13,H-59,hp_w+2,20),1)
    surf.blit(font_tiny.render(f"HP {int(player['hp'])}/{player['max_hp']}",True,WHITE),(18,H-56))
    ac=YELLOW if player["ammo"]>10 else RED
    surf.blit(font_small.render(f"AMMO: {player['ammo']}",True,ac),(14,H-34))
    sc=font_med.render(f"{player['score']:,}",True,(int(200+55*pulse),int(180+40*pulse),0))
    surf.blit(sc,(W//2-sc.get_width()//2,H-62))
    surf.blit(font_tiny.render(f"SCORE  |  ROOM {wave}",True,ORANGE),(W//2-60,H-30))
    kills_left=len(enemies)+(1 if boss and boss["alive"] else 0)+(1 if dragon and dragon["alive"] else 0)
    surf.blit(font_small.render(f"ENEMIES: {kills_left}",True,RED),(W-220,H-58))
    if prapti_rescued:
        surf.blit(font_small.render("PRAPTI SAFE!",True,PINK),(W-220,H-34))
    elif boss and boss["alive"]:
        db=bool(dragon and dragon["alive"])
        msg="KILL BOSS+DRAGON!" if db else "KILL THE BOSS!"
        surf.blit(font_small.render(msg,True,ORANGE),(W-220,H-34))
    else:
        surf.blit(font_small.render("FIND PRAPTI!",True,(200,180,80)),(W-220,H-34))

def draw_crosshair(surf,mx,my):
    c=(255,220,50)
    pygame.draw.circle(surf,c,(mx,my),16,1)
    pygame.draw.line(surf,c,(mx-22,my),(mx-8,my),2); pygame.draw.line(surf,c,(mx+8,my),(mx+22,my),2)
    pygame.draw.line(surf,c,(mx,my-22),(mx,my-8),2); pygame.draw.line(surf,c,(mx,my+8),(mx,my+22),2)
    pygame.draw.circle(surf,WHITE,(mx,my),2)

# ─────────────────────────────────────────────
#  SPAWN WAVE
# ─────────────────────────────────────────────
def random_floor_far_from(px,py,min_dist=250):
    for _ in range(200):
        tx=random.randint(1,MAP_W-2); ty=random.randint(1,MAP_H-2)
        if tiles[ty][tx] in (0,6):
            ex=tx*TILE+24; ey=ty*TILE+24
            if math.hypot(ex-px,ey-py)>min_dist: return ex,ey
    return random.randint(1,MAP_W-2)*TILE+24, random.randint(1,MAP_H-2)*TILE+24

def spawn_wave(wave,player):
    enemies=[]
    for _ in range(4+wave*3):
        x,y=random_floor_far_from(player["x"],player["y"])
        enemies.append(make_grunt(x,y,wave))
    for _ in range(max(0,wave-1)*2):
        x,y=random_floor_far_from(player["x"],player["y"])
        enemies.append(make_shooter(x,y,wave))
    # Boss + dragon always present — guard Prapti
    boss   = make_boss()
    dragon = make_dragon(BOSS_X, BOSS_Y)
    return enemies, boss, dragon

# ─────────────────────────────────────────────
#  SCREENS
# ─────────────────────────────────────────────
def draw_title(surf,frame):
    surf.fill((8,4,4))
    for i in range(20):
        x=(i*64+frame//2)%W; h=30+int(math.sin(i*1.3+frame*0.02)*20)
        pygame.draw.rect(surf,DARK_RED,(x,0,6,h)); pygame.draw.circle(surf,RED,(x+3,h),4)
    for off in range(8,0,-2):
        t=font_big.render("HELLHOUSE",True,(off*15,0,0))
        surf.blit(t,(W//2-t.get_width()//2+random.randint(-1,1),55))
    t=font_big.render("HELLHOUSE",True,RED); surf.blit(t,(W//2-t.get_width()//2,55))
    sub=font_med.render("Save Prapti From The Darkness",True,(200,150,100))
    surf.blit(sub,(W//2-sub.get_width()//2,162))
    pygame.draw.line(surf,(80,30,20),(80,218),(W-80,218),2)
    col_left=100; col_desc=340; y0=240
    surf.blit(font_med.render("CONTROLS",True,ORANGE),(col_left,y0))
    controls=[("W/S/A/D","Move"),("MOUSE","Aim"),("CLICK","Shoot"),("ESC","Quit")]
    for i,(key,desc) in enumerate(controls):
        y=y0+42+i*38
        kw=font_small.render(key,True,YELLOW)
        pygame.draw.rect(surf,(40,20,5),(col_left-4,y-4,max(kw.get_width()+16,120),kw.get_height()+8))
        pygame.draw.rect(surf,(100,60,20),(col_left-4,y-4,max(kw.get_width()+16,120),kw.get_height()+8),1)
        surf.blit(kw,(col_left+4,y))
        surf.blit(font_small.render("→",True,(100,80,60)),(col_desc-28,y))
        surf.blit(font_small.render(desc,True,WHITE),(col_desc,y))
    pygame.draw.line(surf,(60,25,15),(W//2+40,222),(W//2+40,H-88),1)
    col_right=W//2+60
    surf.blit(font_med.render("OBJECTIVE",True,ORANGE),(col_right,y0))
    objs=[(PINK,"★ Find Prapti (bottom room)"),(RED,"★ Kill Demon Lord + Dragon"),
          (ORANGE,"★ Near boss? All demons swarm!"),(YELLOW,"★ Survive the waves"),
          (GREEN,"★ Grab health & ammo drops")]
    for i,(col,txt) in enumerate(objs):
        surf.blit(font_small.render(txt,True,col),(col_right,y0+42+i*36))
    tips_y=y0+42+len(objs)*36+14
    pygame.draw.rect(surf,(25,8,8),(col_right-8,tips_y-8,W-col_right-60,130))
    pygame.draw.rect(surf,(80,30,20),(col_right-8,tips_y-8,W-col_right-60,130),1)
    surf.blit(font_small.render("TIPS",True,ORANGE),(col_right,tips_y))
    tips=["Boss + Dragon guard Prapti in bottom room",
          "Get near boss and ALL demons swarm you!",
          "Kill the Dragon first — it circles the boss",
          "Dodge dragon fire — it hits hard"]
    for i,tip in enumerate(tips):
        surf.blit(font_tiny.render(f"• {tip}",True,(180,160,140)),(col_right,tips_y+28+i*22))
    pygame.draw.line(surf,(80,30,20),(80,H-88),(W-80,H-88),2)
    legend=[(TEAL,"You"),(RED,"Demons"),(ORANGE,"Boss"),(DRAGON_G,"Dragon"),(PINK,"Prapti")]
    for i,(col,lbl) in enumerate(legend):
        lx=80+i*220
        pygame.draw.circle(surf,col,(lx,H-58),8); pygame.draw.circle(surf,WHITE,(lx,H-58),8,1)
        surf.blit(font_small.render(lbl,True,col),(lx+14,H-66))
    pulse=abs(math.sin(frame*0.04))
    ec=(int(50*pulse),int(200*pulse+55),int(80*pulse))
    enter=font_med.render("PRESS  ENTER  TO  BEGIN",True,ec)
    surf.blit(enter,(W//2-enter.get_width()//2,H-34))
    surf.blit(font_tiny.render("Made by PRAPTI",True,(100,80,60)),(W-150,H-18))

def draw_gameover(surf,player,hi_score,frame,scores_data):
    surf.fill((5,2,2))
    for off in range(6,0,-2):
        t=font_big.render("YOU  DIED",True,(off*20,0,0))
        surf.blit(t,(W//2-t.get_width()//2+random.randint(-2,2),H//2-320+random.randint(-2,2)))
    t=font_big.render("YOU  DIED",True,RED); surf.blit(t,(W//2-t.get_width()//2,H//2-320))

    # this run stats
    bx,by,bw,bh=W//2-200,H//2-240,400,120
    pygame.draw.rect(surf,(20,8,8),(bx,by,bw,bh)); pygame.draw.rect(surf,(100,20,20),(bx,by,bw,bh),2)
    surf.blit(font_med.render(f"Score : {player['score']:,}",True,(180,160,140)),(bx+20,by+12))
    surf.blit(font_med.render(f"Best  : {hi_score:,}",       True,YELLOW),       (bx+20,by+50))
    surf.blit(font_med.render(f"Kills : {player['kills']}",  True,RED),           (bx+20,by+88))

    # leaderboard
    lb = scores_data.get("leaderboard",[])
    lx,ly = W//2-300, H//2-100
    pygame.draw.rect(surf,(15,5,5),(lx-10,ly-10,620,min(10,len(lb))*30+60))
    pygame.draw.rect(surf,(80,20,20),(lx-10,ly-10,620,min(10,len(lb))*30+60),1)
    surf.blit(font_small.render("─── TOP 10 LEADERBOARD ───",True,ORANGE),(lx+80,ly))
    surf.blit(font_tiny.render(f"Total games: {scores_data.get('total_games',0)}   "
                               f"Total kills: {scores_data.get('total_kills',0)}",
                               True,GREY),(lx,ly+22))
    for i,entry in enumerate(lb[:10]):
        medal=["🥇","🥈","🥉"][i] if i<3 else f"#{i+1}"
        col=YELLOW if i==0 else (LIGHT_STONE if i<3 else GREY) if True else GREY
        LIGHT_STONE=(180,170,160)
        col=YELLOW if i==0 else ((200,200,200) if i==1 else ((180,130,80) if i==2 else (140,140,140)))
        line=(f"  {i+1}.  score={entry['score']:<8,}  kills={entry['kills']:<4}  "
              f"wave={entry['wave']:<3}  {entry['result']:<6}  {entry['date']}")
        surf.blit(font_tiny.render(line,True,col),(lx,ly+48+i*26))

    pulse=abs(math.sin(frame*0.06))
    r=font_med.render("ENTER — retry    ESC — quit",True,(int(200+55*pulse),int(80+40*pulse),0))
    surf.blit(r,(W//2-r.get_width()//2,H-50))

def draw_win(surf,player,frame,scores_data):
    surf.fill((4,8,4))
    for _ in range(3):
        pygame.draw.circle(surf,(255,200,255),(random.randint(0,W),random.randint(0,H)),random.randint(1,3))
    pulse=abs(math.sin(frame*0.04))
    tc=(int(50*pulse+200),int(200*pulse+55),int(80*pulse+100))
    t=font_big.render("PRAPTI  IS  SAFE!",True,tc); surf.blit(t,(W//2-t.get_width()//2,60))
    sub=font_med.render("You defeated the Demon Lord and his Dragon!",True,PINK)
    surf.blit(sub,(W//2-sub.get_width()//2,150))

    # this run stats
    bx,by,bw,bh=W//2-200,200,400,110
    pygame.draw.rect(surf,(5,20,5),(bx,by,bw,bh)); pygame.draw.rect(surf,(30,100,30),(bx,by,bw,bh),2)
    surf.blit(font_med.render(f"Final Score:  {player['score']:,}",True,YELLOW),(bx+20,by+15))
    surf.blit(font_med.render(f"Demons Slain: {player['kills']}",  True,RED),   (bx+20,by+58))

    # leaderboard
    lb = scores_data.get("leaderboard",[])
    lx,ly = W//2-300, 330
    pygame.draw.rect(surf,(5,15,5),(lx-10,ly-10,620,min(10,len(lb))*26+60))
    pygame.draw.rect(surf,(20,80,20),(lx-10,ly-10,620,min(10,len(lb))*26+60),1)
    surf.blit(font_small.render("─── TOP 10 LEADERBOARD ───",True,GREEN),(lx+80,ly))
    surf.blit(font_tiny.render(f"Total games: {scores_data.get('total_games',0)}   "
                               f"Total kills: {scores_data.get('total_kills',0)}",
                               True,(120,160,120)),(lx,ly+22))
    for i,entry in enumerate(lb[:10]):
        col=YELLOW if i==0 else ((200,200,200) if i==1 else ((180,130,80) if i==2 else (140,140,140)))
        line=(f"  {i+1}.  score={entry['score']:<8,}  kills={entry['kills']:<4}  "
              f"wave={entry['wave']:<3}  {entry['result']:<6}  {entry['date']}")
        surf.blit(font_tiny.render(line,True,col),(lx,ly+48+i*24))

    r=font_med.render("ENTER — play again    ESC — quit",True,GREEN)
    surf.blit(r,(W//2-r.get_width()//2,H-50))
    surf.blit(font_tiny.render("Made by PRAPTI",True,(80,120,80)),(W-150,H-18))

# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────
def main():
    global prapti_rescued, prapti_anim, all_particles, all_pickups, shake

    state    = "title"
    frame    = 0
    hi_score = 0
    player   = None
    enemies  = []
    boss     = None
    dragon   = None
    bullets  = []
    e_bullets= []
    wave     = 1
    flash_msgs=[]
    session_start = 0   # pygame.time.get_ticks() when game starts

    # load persistent scores
    scores_data = load_scores()
    hi_score    = scores_data["hi_score"]

    def add_flash(txt,col,x=W//2,y=H//2-80):
        flash_msgs.append([txt,col,80,x,y])

    def draw_flashes(surf):
        keep=[]
        for m in flash_msgs:
            m[2]-=1
            if m[2]>0:
                fnt=font_med if m[2]>50 else font_small
                sh=fnt.render(m[0],True,BLACK)
                surf.blit(sh,(m[3]-sh.get_width()//2+2,m[4]-(80-m[2])+2))
                t=fnt.render(m[0],True,m[1])
                surf.blit(t,(m[3]-t.get_width()//2,m[4]-(80-m[2])))
                keep.append(m)
        flash_msgs[:]=keep

    def reset_game():
        nonlocal player,enemies,boss,dragon,bullets,e_bullets,wave,session_start
        global prapti_rescued,prapti_anim,all_particles,all_pickups,shake
        all_particles.clear(); all_pickups.clear(); flash_msgs.clear()
        prapti_rescued=False; prapti_anim=0; shake=0
        player=make_player(); wave=1; bullets=[]; e_bullets=[]
        enemies,boss,dragon=spawn_wave(wave,player)
        session_start=pygame.time.get_ticks()
        add_flash("FIND PRAPTI. KILL THEM ALL.",RED)
        add_flash("BOSS + DRAGON GUARD HER!",ORANGE,W//2,H//2-40)

    pygame.mouse.set_visible(False)

    while True:
        clock.tick(FPS); frame+=1
        keys=pygame.key.get_pressed(); mx,my=pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if state=="title" and ev.key==pygame.K_RETURN:
                    reset_game(); state="playing"
                elif state in ("dead","win") and ev.key==pygame.K_RETURN:
                    hi_score = scores_data["hi_score"]
                    state="title"

        if state=="title":
            draw_title(screen,frame); pygame.display.flip(); continue
        if state=="dead":
            draw_gameover(screen,player,hi_score,frame,scores_data); pygame.display.flip(); continue
        if state=="win":
            draw_win(screen,player,frame,scores_data); pygame.display.flip(); continue

        # ── UPDATE ──────────────────────────────
        cam_x,cam_y=get_camera(player)
        aim_player(player,mx,my,cam_x,cam_y)
        update_player(player,keys)
        if pygame.mouse.get_pressed()[0]:
            player_shoot(player,bullets,mx,my,cam_x,cam_y)

        for b in bullets: update_bullet(b)
        for b in e_bullets: update_bullet(b)
        bullets=[b for b in bullets if b["alive"]]
        e_bullets=[b for b in e_bullets if b["alive"]]

        boss_alive  = boss is not None and boss["alive"]
        boss_x      = boss["x"] if boss else 0
        boss_y      = boss["y"] if boss else 0
        dragon_alive= dragon is not None and dragon["alive"]

        for e in enemies:
            if e["kind"]=="grunt":
                update_grunt(e,player,e_bullets,boss_alive,boss_x,boss_y)
            elif e["kind"]=="shooter":
                update_shooter(e,player,e_bullets,boss_alive,boss_x,boss_y)

        if boss_alive:
            update_boss(boss,player,e_bullets)
        elif boss is not None:
            boss=None

        if dragon_alive:
            update_dragon(dragon,boss,player,e_bullets)
        elif dragon is not None:
            dragon=None
