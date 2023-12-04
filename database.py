"""
database.py:
Manage game records, and define all statistics and values for game items,
including monsters, tasks, runestones.
"""
from copy import deepcopy   # 深度复制字典
import pickle

GRAVITY = 8     # 物体下落的最大竖直速度
DMG_FREQ = 10   # 持续型伤害的伤害频率

RANGE = {
    "LONG":580, "NORM":470, "SHORT":360
}


# ========================================
# 1. 记录管理
example_rec_strucure = {
        "NICK_NAME": "player0",
        "GAME_ID": 1,

        # -1:locked; 0:unlocked-no star; 1:easy passed; 2:normal passed; 3:hard passed.
        "CHAPTER_REC": [0,-1,-1,-1,-1,-1,-1],  
        "ENDLESS_REC": 0,

        "GEM": 0,
        "TASK": ["A-1", 0],
        "STONE": {},

        "KEY_SET": [
            [97,100,115,106,107,108,105,119,114],
            [98,109,110,260,261,262,264,273,111]
        ],

        "HEROES": [ # 0LVL; 1EXP; 2SP; 3HP; 4DMG; 5CNT; 6CRIT
            [1,0,0,0,0,0,0],
            [1,0,0,0,0,0,0],
            [1,0,0,0,0,0,0],
            [1,0,0,0,0,0,0],
            [1,0,0,0,0,0,0],
            [1,0,0,0,0,0,0],
            [1,0,0,0,0,0,0]
        ],
        "MONS_COLLEC": [    # Stored by Chapter
            [0,0,0,0,0],
            [0,0,0,0,0],
            [0,0,0,0,0],
            [0,0,0,0,0],
            [0,0,0,0,0],
            [0,0,0,0,0],
            [0,0,0,0,0]
        ],
        
        "SYS_SET": {
            "LGG": 0,
            "DIFFI": 0,
            "VOL": 80,
            "DISPLAY": 0,
            "PAPERNO": 0,
            "P1": 0,
            "P2": 1,
            "STG_STOP": 1,
            "MOD_STOP": 0,
            "TUTOR": 1
        }
    }

def load_rec_data():
    # Record Data Structure
    try:
        with open('./record.sav', 'rb') as f:
            REC_DATA = pickle.load(f)
            # new rec item: gem number
            if "GEM" not in REC_DATA:
                REC_DATA["GEM"] = 0
            # new rec item: task obj
            if "TASK" not in REC_DATA:
                REC_DATA["TASK"] = ["A-1", 0]   # tag & prog
            # new rec item: runestones
            if "STONE" not in REC_DATA:
                REC_DATA["STONE"] = {}      # "stone_tag": number
            # rec update:
            if REC_DATA["CHAPTER_REC"][0]<0:
                REC_DATA["CHAPTER_REC"][0] = 0
            #REC_DATA["SYS_SET"]["TUTOR"] = 1
    except FileNotFoundError:
        # create an empty one
        with open('./record.sav', 'wb') as f:
            pickle.dump(example_rec_strucure, f)
        # read again
        with open('./record.sav', 'rb') as f:
            REC_DATA = pickle.load(f)
    return REC_DATA

def clear_rec_data():
    for key in REC_DATA:
        if key!="SYS_SET":
            REC_DATA[key] = deepcopy( example_rec_strucure[key] )

def reload_rec_data():
    with open(f'./record.sav', 'rb') as f:
        new_REC_DATA = pickle.load(f)
        for key in new_REC_DATA:
            if key!="SYS_SET":
                REC_DATA[key] = deepcopy( new_REC_DATA[key] )
        # new rec item: gem number
        if "GEM" not in REC_DATA:
            REC_DATA["GEM"] = 0
        #REC_DATA["GEM"] -= 640
        # new rec item: task obj
        if "TASK" not in REC_DATA:
            REC_DATA["TASK"] = ["A-1", 0]   # tag & prog
        # new rec item: runestones
        if "STONE" not in REC_DATA:
            REC_DATA["STONE"] = {}
        # rec update:
        if REC_DATA["CHAPTER_REC"][0]<0:
            REC_DATA["CHAPTER_REC"][0] = 0
        #REC_DATA["SYS_SET"]["TUTOR"] = 1
        #REC_DATA["CHAPTER_REC"][1] = REC_DATA["CHAPTER_REC"][2] = -1
    
def data2sav():
    with open('./record.data', 'rb') as fd:
        REC_DATA = pickle.load(fd)
    with open('./record.sav', 'wb') as fs:
        pickle.dump(REC_DATA, fs)

# 模块加载时，自动导入数据

REC_DATA = load_rec_data()


# ========================================
# 2. 存储monster基本信息的数据结构
class Mons():
    def __init__(self, health=0, damage=0, dmgType="", 
        armor=0, coin=0, child=[], name=(), manner="GROUND"):
        self.health = health
        self.damage = damage
        self.dmgType = dmgType
        self.armor = armor
        self.coin = coin
        self.child = child
        self.name = name
        self.manner = manner

# Monster Brochure
MB = {
    "Unknown": Mons(name=("Unknown","未知")),
    "biteChest": Mons(health=720, damage=60, dmgType="physical", name=("BiteChest","咬咬宝箱")),

    "tizilla": Mons(health=310, damage=80, dmgType="physical", name=("Tizilla","弟斯拉"), coin=2),
    "megaTizilla": Mons(health=530, damage=30, dmgType="fire", name=("Mega Tizilla","超级弟斯拉"), coin=4),
    "dragon": Mons(health=400, damage=100, dmgType="fire", name=("Baby Dragon","火龙宝宝"), coin=3, manner="AIR"),
    "dragonEgg": Mons(health=270, damage=100, dmgType="fire", name=("Dragon Egg","火龙蛋"), coin=1, child=["dragon"]),
    "hellHound": Mons(health=2400, damage=60, dmgType="physical", name=("Hell Hound","双头地狱犬"), coin=12),
    "CrimsonDragon": Mons(health=4400, damage=120, dmgType="fire", name=("Crimson Dragon","猩红巨龙"), armor=0.3, coin=24, manner="AIR"),

    "bat": Mons(health=120, damage=25, dmgType="physical", name=("Bat","蝙蝠"), coin=1, manner="AIR"),
    "golem": Mons(health=420, damage=80, dmgType="physical", name=("Golem","戈仑石人"), coin=2, child=["golemite"]),
    "golemite": Mons(health=210, damage=40, dmgType="physical", name=("Golemite","小戈仑石人"), coin=1),
    "bowler": Mons(health=460, dmgType="physical", name=("Cave Dweller","穴居人"), coin=3, child=["stone"]),
    "stone": Mons(health=300, damage=30, name=("Rock","滚石")),
    "spider": Mons(health=310, damage=70, dmgType="physical", name=("Spider","小蜘蛛"), coin=2, manner="CRAWL"),
    "GiantSpider": Mons(health=4200, damage=80, dmgType="physical", name=("Giant Spider","巨型魔蛛"), armor=0.3, coin=24, child=["spider"], manner="CRAWL"),

    "skeleton": Mons(health=200, damage=40, dmgType="physical", name=("Skeleton","骷髅兵"), coin=1),
    "dead": Mons(health=360, damage=20, dmgType="corrosive", name=("Walking Dead","丧尸"), coin=2),
    "ghost": Mons(health=410, damage=65, dmgType="physical", name=("Ghost","幽灵"), coin=4, manner="AIR"),
    "Vampire": Mons(health=4000, damage=80, dmgType="physical", name=("Vampire","吸血女巫"), armor=0.3, coin=24, child=["skeleton","dead","ghost"]),

    "snake": Mons(health=300, damage=65, dmgType="corrosive", name=("Tiny Anaconda","小水蟒"), coin=2),
    "slime": Mons(health=280, damage=60, dmgType="corrosive", name=("Slime","软泥怪"), coin=2),
    "nest": Mons(health=550, name=("Eggs","虫卵"), coin=3, child=["worm"]),
    "worm": Mons(health=60, damage=50, name=("Worm","蠕虫"), dmgType="corrosive"),
    "fly": Mons(health=480, damage=70, name=("Crusty Coleopter","硬壳甲虫"), dmgType="physical", coin=3, manner="AIR"),
    "miniFungus": Mons(health=10, damage=40, dmgType="corrosive", name=("Sprout","毒芽"), manner="AIR"),
    "MutatedFungus": Mons(health=4700, damage=30, dmgType="corrosive", name=("Mutated Fungus","异变孢子"), armor=0.3, coin=24, child=["miniFungus"]),

    "wolf": Mons(health=320, damage=90, dmgType="physical", name=("Snow Wolf","雪狼"), coin=2),
    "iceTroll": Mons(health=580, damage=25, dmgType="freezing", name=("Ice Troll","大雪怪"), coin=4),
    "eagle": Mons(health=360, damage=70, dmgType="physical", name=("Peak Eagle","冰川飞鹰"), coin=2, manner="AIR"),
    "iceSpirit": Mons(health=180, damage=90, dmgType="freezing", name=("Ice Spirit","冰晶精灵"), coin=1, manner="AIR"),
    "FrostTitan": Mons(health=4000, damage=72, dmgType="freezing", name=("FrostTitan","冰霜泰坦"), armor=0.3, coin=24, child=["iceSpirit"], manner="AIR"),

    "dwarf": Mons(health=290, damage=50, dmgType="physical", name=("Dwarf Worker","侏儒工人"), coin=2),
    "gunner": Mons(health=540, damage=20, dmgType="physical", name=("Gunner","机枪守卫"), coin=4),
    "lasercraft": Mons(health=360, damage=8, dmgType="fire", name=("Lasercraft","激光飞行器"), coin=2, manner="AIR"),
    "WarMachine": Mons(health=4200, damage=100, dmgType="fire", name=("War Machine","战争机器"), armor=0.3, coin=24, child=["missle"]),
    "missle": Mons(health=10, damage=80, dmgType="physical", name=("Tracking Missle","追踪导弹"), manner="AIR"),

    "guard": Mons(health=340, damage=70, dmgType="physical", name=("Royal Guard","王城卫兵"), armor=0.8, coin=3),
    "flamen": Mons(health=330, damage=30, dmgType="holy", name=("Fallen Flamen","堕落祭司"), coin=2),
    "assassin": Mons(health=360, damage=50, dmgType="physical", name=("Night Assassin","暗夜刺客"), coin=2),
    "Chicheng": Mons(health=4300, damage=100, dmgType="physical", name=("General Qichan","魔将赤诚"), armor=0.3, coin=24)
}


# ========================================
# 3. Chapter Brochure 章节怪物分布图: define monster types and numbers in each area
# Structure: CB[chapter_No][Area_No][monster: cate, num, start, end]
# About start & end: integer-direct layer number; string-indirect, should be computed based on tower.layer
CB = {
    1: {
        0: [ (1,7,0,"0"), (2,3,4,"0"), (3,5,-1,"0"), None, None, None ],
        1: [ (1,6,0,"0"), (2,6,4,"0"), (3,4,-1,"0"), (4,1,0,"-2"), (5,1,"-2","0"), None ],
        3: [ (1,5,0,"0"), (2,5,4,"0"), (3,3,-1,"0"), (4,6,0,"-2"), (5,1,"-2","0"), None ],
        4: [ None, (2,4,4,"0"), (3,2,2,"0"), (4,6,0,"-2"), None, (6,1,"-2","0") ],
        # 1:18*2=32; 2:18*4=72; 3:14*3=42; 4:13*4=52; 5:2*12=24; 6:24; Total:250
    }, 
    2: {
        0: [ (1,7,0,"0"), (2,5,0,"0"), None, None, None, None ],
        1: [ (1,7,0,"0"), (2,7,0,"0"), (3,3,"-6","0"), None, (5,1,"-2","0"), None ],
        3: [ (1,6,0,"0"), (2,5,0,"0"), (3,8,2,"0"), (4,7,2,"-2"), (5,1,"-2","0"), None ],
        4: [ (1,5,0,"0"), (2,6,0,"0"), (3,8,2,"0"), (4,7,2,"-2"), None, (6,1,"-2","0") ],
        # 1:25*1=25; 2:23*4=92; 3:19*3=57; 4:14*2=28; 5:2*12=24; 6:24; Total:250
    },
    3: {
        0: [ (1,8,2,"0"), (2,8,2,"0"), None, None, None, None ],
        1: [ (1,10,2,"0"), (2,10,2,"0"), (3,4,"-6","0"), None, (5,1,"-2","0"), None ],
        3: [ (1,9,0,"0"), (2,10,2,"0"), (3,8,4,"0"), None, (5,1,"-2","0"), None ],
        4: [ (1,9,0,"0"), (2,11,2,"0"), (3,10,4,"0"), None, None, (6,1,"-2","0") ],
        # 1:36*1=36; 2:39*2=78; 3:22*4=88; 5:2*12=24; 6:24; Total:250
    },
    4: {
        0: [ (1,3,2,"0"), (2,4,2,"0"), None, (4,5,2,"0"), None, None ],
        1: [ (1,6,0,"-2"), (2,5,6,"0"), None, (4,6,2,"0"), (5,1,"-2","0"), None ],
        3: [ (1,6,0,"-2"), (2,5,0,"0"), (3,9,2,"0"), (4,6,4,"0"), (5,1,"-2","0"), None ],
        4: [ (1,3,2,"-4"), (2,6,0,"0"), (3,9,2,"0"), (4,7,4,"0"), None, (6,1,"-2","0") ],
        # 1:18*2=36; 2:20*2=40; 3:18*3=54; 4:24*3=72; 5:2*12=24; 6:24; Total:250
    },
    5: {
        0: [ (1,5,2,"0"), (2,4,2,"0"), (3,2,4,"0"), None, None, None ],
        1: [ (1,7,0,"0"), (2,7,2,"0"), (3,6,4,"0"), None, (5,1,"-2","0"), None ],
        3: [ (1,7,0,"0"), (2,6,2,"0"), (3,5,4,"0"), (4,9,4,"0"), (5,1,"-2","0"), None ],
        4: [ (1,7,0,"0"), (2,7,2,"0"), (3,5,4,"0"), (4,9,4,"0"), None, (6,1,"-2","0") ],
        # 1:26*2=52; 2:24*4=96; 3:18*1=18; 4:18*2=36; 5:2*12=24; 6:24; Total:250
    },
    6: {
        0: [ (1,5,2,"0"), (2,4,2,"0"), None, None, None, None ],
        1: [ (1,8,0,"0"), (2,8,2,"0"), None, None, (5,1,"-2","0"), None ],
        3: [ (1,8,0,"0"), (2,8,2,"0"), (3,8,4,"0"), None, (5,1,"-2","0"), None ],
        4: [ (1,9,0,"0"), (2,8,2,"0"), (3,8,4,"0"), None, None, (6,1,"-2","0") ],
        # 1:29*2=58; 2:28*4=112; 3:16*2=32; 5:2*12=24; 6:24; Total:250
    },
    7: {
        0: [ (1,7,2,"0"), (2,7,2,"0"), None, None, None, None ],
        1: [ (1,8,0,"0"), (2,8,0,"0"), None, None, (5,1,"-2","0"), None ],
        3: [ (1,8,0,"0"), (2,8,0,"0"), (3,11,2,"-2"), None, (5,1,"-2","0"), None ],
        4: [ (1,9,0,"0"), (2,9,0,"0"), (3,11,2,"-2"), None, None, (6,1,"-2","0") ],
        # 1:32*3=96; 2:32*2=64; 3:22*2=44; 5:2*12=24; 6:24; Total:252
    }
}


# ========================================
# 4. Natural Element Brochure
NB = {
    "infernoFire": {"damage":32},
    "blockFire": {"damage":16},

    "column": {"damage":50},
    "blockStone": {"health":600, "manner":"GROUND"},

    "healTotem": {"health":400, "heal":80},
    "battleTotem": {"health":400},

    "fan": {"health":100, "damage":50, "manner":"GROUND"},
    "drip": {"health":100, "damage":100, "manner":"AIR"},

    "log": {"damage":30},
    "stabber": {"damage":50}
}


# ========================================
# 5. DamageType Mapping
# All Damage are categorized to 5 types: "physical", "corrosive", "fire", "freezing", "holy".
DT = {
    "physical": "物理伤害",
    "fire": "火焰伤害",
    "corrosive": "腐蚀伤害",
    "freezing": "冰冻伤害",
    "holy": "神圣伤害"
}


# ========================================
# 6. Props Brochure
PB = {
    1: ["cooler","toothRing"],
    2: ["herbalExtract","blastingCap"],
    3: ["torch","medicine"],
    4: ["copter","pesticide"],
    5: ["alcohol","battleTotem"],
    6: ["missleGun","simpleArmor"],
    7: ["shieldSpell","rustedHorn"]
}


# ========================================
# 7. Task System
# 存储Task基本信息的数据结构
class Task():
    def __init__(self, tag, reward, num, tgt, pres, descript):
        self.tag = tag
        self.reward = reward
        self.num = num
        self.tgt = tgt
        self.pres = pres
        # 根据所给信息完善descript模板
        self.descript = list(descript)
        for i in range(len(self.descript)):
            self.descript[i] = self.descript[i].replace( "(num)", str(self.num) )
            if tgt=="chest":
                name = ("chest", "宝箱")
                self.descript[i] = self.descript[i].replace( "(tgt)", name[i] )
            else:
                self.descript[i] = self.descript[i].replace( "(tgt)", MB[self.tgt].name[i] )
        self.progress = 0
    
    def incProgress(self, increm):
        self.progress += increm
        # update rec
        REC_DATA["TASK"][1] += increm
        if self.progress >= self.num:
            self.progress = REC_DATA["TASK"][1] = self.num
            return True # Mission complete
        return False    # Not complete yet

    def claim_reward(self):
        if self.progress == self.num:
            # give gem
            REC_DATA["GEM"] += self.reward
            self.progress = 0
            return True
        return False

# Task Brochure
TB = {
    # Type A: Kill small Monsters
    "A-1": Task("A-1", reward=10, num=25, tgt="tizilla", pres=0, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-2": Task("A-2", reward=10, num=22, tgt="megaTizilla", pres=0, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-3": Task("A-3", reward=12, num=30, tgt="dragon", pres=0, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-4": Task("A-4", reward=10, num=30, tgt="golem", pres=1, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-5": Task("A-5", reward=12, num=22, tgt="bowler", pres=1, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-6": Task("A-6", reward=10, num=25, tgt="dead", pres=2, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-7": Task("A-7", reward=12, num=20, tgt="ghost", pres=2, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-8": Task("A-8", reward=10, num=22, tgt="snake", pres=3, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-9": Task("A-9", reward=10, num=22, tgt="fly", pres=3, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-10": Task("A-10", reward=10, num=25, tgt="wolf", pres=4, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-11": Task("A-11", reward=10, num=22, tgt="iceTroll", pres=4, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-12": Task("A-12", reward=12, num=25, tgt="eagle", pres=4, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-13": Task("A-13", reward=10, num=25, tgt="gunner", pres=5, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-14": Task("A-14", reward=12, num=20, tgt="lasercraft", pres=5, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-15": Task("A-15", reward=10, num=25, tgt="guard", pres=6, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-16": Task("A-16", reward=10, num=25, tgt="flamen", pres=6, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-17": Task("A-17", reward=12, num=22, tgt="assassin", pres=6, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    # Type B: Kill Boss
    "B-1": Task("B-1", reward=15, num=1, tgt="CrimsonDragon", pres=0, descript=["Kill (num) (tgt).","击败(num)次(tgt)。"]),
    "B-2": Task("B-2", reward=15, num=1, tgt="GiantSpider", pres=1, descript=["Kill (num) (tgt).","击败(num)次(tgt)。"]),
    "B-3": Task("B-3", reward=15, num=1, tgt="MutatedFungus", pres=3, descript=["Kill (num) (tgt).","击败(num)次(tgt)。"]),
    "B-4": Task("B-4", reward=15, num=1, tgt="FrostTitan", pres=4, descript=["Kill (num) (tgt).","击败(num)次(tgt)。"]),
    "B-5": Task("B-5", reward=15, num=1, tgt="WarMachine", pres=5, descript=["Kill (num) (tgt).","击败(num)次(tgt)。"]),
    "B-6": Task("B-6", reward=20, num=1, tgt="Chicheng", pres=6, descript=["Kill (num) (tgt).","击败(num)次(tgt)。"]),
    # Type 3: Resource Related
    "C-1": Task("C-1", reward=10, num=30, tgt="chest", pres=0, descript=["Open (num) (tgt).","打开(num)个(tgt)。"]),
}


# ========================================
# 8. Runestone System
# 存储符石的数据结构
class Runestone():
    def __init__(self, tag, name, cost, description, data=None):
        self.tag = tag
        self.name = name
        self.cost = cost
        self.description = description
        self.data = data

# Runestone Brochure
RB = {
    # 圆形类：增强英雄自身属性
    "loadingStone": Runestone( "loadingStone", ("Loading Stone","填装符石"), 16, 
        ("Reduce loading time from 3 secs to 2.5 secs.","填装时间由3秒减少为2.5秒。"), data=150 ),
    "hopeStone": Runestone( "hopeStone", ("Hope Stone","希望符石"), 16, 
        ("Whenever you get healed, heal 60% more.","每当自身受到治疗时，治疗量增加60%。"), data=1.6 ),
    #"rageStone": Runestone( "rageStone", ("Rage Stone","狂暴符石"), 12, 
    #    ("Crit rate +5%。","暴击率+5%。") ),

    # 三角类：对敌人造成控制效果
    "bloodStone": Runestone( "bloodStone", ("Blood Stone","鲜血符石"), 20, 
        ("Restore 7 HP after killing a monster.","击杀一只怪物后，为自身回复7点体力。"), data=7 ),
    "terrorStone": Runestone( "terrorStone", ("Terror Stone","恐惧符石"), 16, 
        (r"Basic damages get 60% chances of stunning targets.","普通伤害具有60%概率造成眩晕效果。"), data=0.6 ), 

    # 方形类：一次性触发效果
    "sacredStone": Runestone( "sacredStone", ("Sacred Stone","神圣符石"), 12, 
        ("Fasten the progress of charging SuperPower by 10%.","超级技能的充能进度加快10%。"), data=0.1 ),
    "luckyStone": Runestone( "luckyStone", ("Lucky Stone","幸运符石"), 12, 
        ("Gain 3 random chapter props or fruits at the beginning.","游戏开始时，随机获得3件章节道具或水果。"), data=3 ),
    #"redemptionStone": Runestone( "redemptionStone", ("Redemption Stone","救赎符石"), 15, 
    #    (r"In first time dying, restore HP to 20%.","首次濒死时，将体力回复至20%继续战斗。") ),
}