# database.py
from copy import deepcopy   # 深度复制字典
import pickle

GRAVITY = 7     # 物体下落的最大竖直速度
DMG_FREQ = 10   # 持续型伤害的伤害频率

RANGE = {
    "LONG":580, "NORM":470, "SHORT":360
}

# ========================================
# 记录管理
example_rec_strucure = {
        "NICK_NAME": "player0",
        "GAME_ID": 1,

        "CHAPTER_REC": [-1,-1,-1,-1,-1,-1,-1],
        "ENDLESS_REC": 0,

        "GEM": 0,
        "TASK": ["A-1", 0],
        "STONE": {},

        "KEY_SET": [
            [97,100,115,106,107,108,105,119],
            [98,109,110,260,261,262,264,273]
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
            "LGG": 1,
            "DIFFI": 0,
            "VOL": 100,
            "DISPLAY": 0,
            "PAPERNO": 1,
            "P1": 0,
            "P2": 1,
            "STG_STOP": 1,
            "MOD_STOP": 0,
            "TUTOR": 0
        }
    }

def load_rec_data():
    # Record Data Structure
    try:
        with open('./record.data', 'rb') as f:
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
    except FileNotFoundError:
        # create an empty one
        with open('./record.data', 'wb') as f:
            pickle.dump(example_rec_strucure, f)
        # read again
        with open('./record.data', 'rb') as f:
            REC_DATA = pickle.load(f)
    return REC_DATA

def clear_rec_data():
    for key in REC_DATA:
        if key!="SYS_SET":
            REC_DATA[key] = deepcopy( example_rec_strucure[key] )

def reload_rec_data():
    with open(f'./record.data', 'rb') as f:
        new_REC_DATA = pickle.load(f)
        for key in new_REC_DATA:
            if key!="SYS_SET":
                REC_DATA[key] = deepcopy( new_REC_DATA[key] )
        # new rec item: gem number
        if "GEM" not in REC_DATA:
            REC_DATA["GEM"] = 0
        #REC_DATA["GEM"] = 800
        # new rec item: task obj
        if "TASK" not in REC_DATA:
            REC_DATA["TASK"] = ["A-1", 0]   # tag & prog
        # new rec item: runestones
        if "STONE" not in REC_DATA:
            REC_DATA["STONE"] = {}
    
# 模块加载，自动导入数据
REC_DATA = load_rec_data()



# ========================================
# 存储monster基本信息的数据结构
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
    "biteChest": Mons(health=600, damage=60, dmgType="physical", name=("BiteChest","咬咬宝箱")),

    "gozilla": Mons(health=300, damage=80, dmgType="physical", name=("Gozilla","小哥斯拉"), coin=2),
    "megaGozilla": Mons(health=440, damage=25, dmgType="fire", name=("Mega Gozilla","超级哥斯拉"), coin=3),
    "dragon": Mons(health=400, damage=100, dmgType="fire", name=("Baby Dragon","火龙宝宝"), coin=3, manner="AIR"),
    "dragonEgg": Mons(health=360, damage=100, dmgType="fire", name=("Dragon Egg","火龙蛋"), coin=2, child=["dragon"]),
    "CrimsonDragon": Mons(health=4200, damage=140, dmgType="fire", name=("Crimson Dragon","猩红巨龙"), armor=0.3, coin=24, manner="AIR"),

    "bat": Mons(health=120, damage=25, dmgType="physical", name=("Bat","蝙蝠"), coin=1, manner="AIR"),
    "golem": Mons(health=420, damage=80, dmgType="physical", name=("Golem","戈仑石人"), coin=2, child=["golemite"]),
    "golemite": Mons(health=210, damage=40, dmgType="physical", name=("Golemite","小戈仑石人"), coin=1),
    "bowler": Mons(health=460, dmgType="physical", name=("Cave Dweller","穴居人"), coin=3, child=["stone"]),
    "stone": Mons(health=300, damage=30, name=("Rock","滚石")),
    "spider": Mons(health=310, damage=70, dmgType="physical", name=("Spider","小蜘蛛"), coin=2, manner="CRAWL"),
    "GiantSpider": Mons(health=4000, damage=80, dmgType="physical", name=("Giant Spider","巨型魔蛛"), armor=0.3, coin=24, manner="CRAWL"),

    "skeleton": Mons(health=200, damage=40, dmgType="physical", name=("Skeleton","骷髅兵"), coin=1),
    "dead": Mons(health=360, damage=20, dmgType="corrosive", name=("Walking Dead","丧尸"), coin=2),
    "ghost": Mons(health=430, damage=70, dmgType="physical", name=("Ghost","幽灵"), coin=4, manner="AIR"),
    "Vampire": Mons(health=3800, damage=80, dmgType="physical", name=("Vampire","吸血女巫"), armor=0.3, coin=24, child=["skeleton","dead","ghost"]),

    "snake": Mons(health=300, damage=60, dmgType="corrosive", name=("Tiny Anaconda","小水蟒"), coin=2),
    "slime": Mons(health=280, damage=60, dmgType="corrosive", name=("Slime","软泥怪"), coin=2),
    "nest": Mons(health=550, name=("Eggs","虫卵"), coin=3, child=["worm"]),
    "worm": Mons(health=60, damage=50, name=("Worm","蠕虫"), dmgType="corrosive"),
    "fly": Mons(health=480, damage=70, name=("Crusty Coleopter","硬壳甲虫"), dmgType="physical", coin=3, manner="AIR"),
    "miniFungus": Mons(health=10, damage=40, dmgType="corrosive", name=("Sprout","毒芽"), manner="AIR"),
    "MutatedFungus": Mons(health=4400, damage=40, dmgType="corrosive", name=("Mutated Fungus","异变孢子"), armor=0.3, coin=24, child=["miniFungus"]),

    "wolf": Mons(health=320, damage=90, dmgType="physical", name=("Snow Wolf","雪狼"), coin=2),
    "iceTroll": Mons(health=580, damage=25, dmgType="freezing", name=("Ice Troll","大雪怪"), coin=4),
    "eagle": Mons(health=360, damage=70, dmgType="physical", name=("Peak Eagle","冰川飞鹰"), coin=2, manner="AIR"),
    "iceSpirit": Mons(health=180, damage=90, dmgType="freezing", name=("Ice Spirit","冰晶精灵"), coin=1, manner="AIR"),
    "FrostTitan": Mons(health=3800, damage=75, dmgType="freezing", name=("FrostTitan","冰霜泰坦"), armor=0.3, coin=24, child=["iceSpirit"], manner="AIR"),

    "dwarf": Mons(health=290, damage=50, dmgType="physical", name=("Dwarf Worker","侏儒工人"), coin=2),
    "gunner": Mons(health=510, damage=20, dmgType="physical", name=("Gunner","机枪守卫"), coin=4),
    "lasercraft": Mons(health=360, damage=8, dmgType="fire", name=("Lasercraft","激光飞行器"), coin=2, manner="AIR"),
    "WarMachine": Mons(health=4000, damage=100, dmgType="fire", name=("War Machine","战争机器"), armor=0.3, coin=24, child=["missle"]),
    "missle": Mons(health=10, damage=90, dmgType="physical", name=("Tracking Missle","追踪导弹"), manner="AIR"),

    "guard": Mons(health=340, damage=70, dmgType="physical", name=("Royal Guard","王城卫兵"), armor=0.8, coin=3),
    "flamen": Mons(health=330, damage=30, dmgType="holy", name=("Fallen Flamen","堕落祭司"), coin=2),
    "assassin": Mons(health=360, damage=50, dmgType="physical", name=("Night Assassin","暗夜刺客"), coin=2),
    "Chicheng": Mons(health=4000, damage=100, dmgType="physical", name=("General Qichan","魔将赤诚"), armor=0.3, coin=24)
}

# Natural Element Brochure ===============
NB = {
    "infernoFire": {"damage":30},
    "blockFire": {"damage":16},

    "column": {"damage":50},
    "blockStone": {"health":600, "manner":"GROUND"},

    "healTotem": {"health":400, "heal":80},
    "battleTotem": {"health":400},

    "fan": {"health":100, "damage":50, "manner":"GROUND"},

    "log": {"damage":30},
    "stabber": {"damage":50}
}

# DamageType Mapping =====================
# All Damage are categorized to 5 types:
# "physical", "corrosive", "fire", "freezing", "holy".
DT = {
    "physical": "物理伤害",
    "fire": "火焰伤害",
    "corrosive": "腐蚀伤害",
    "freezing": "冰冻伤害",
    "holy": "神圣伤害"
}

# Task System ===========================
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
    "A-1": Task("A-1", reward=10, num=25, tgt="gozilla", pres=0, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-2": Task("A-2", reward=10, num=22, tgt="megaGozilla", pres=0, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-3": Task("A-3", reward=10, num=30, tgt="dragon", pres=0, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-4": Task("A-4", reward=10, num=30, tgt="golem", pres=1, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-5": Task("A-5", reward=10, num=22, tgt="bowler", pres=1, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-6": Task("A-6", reward=10, num=25, tgt="dead", pres=2, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-7": Task("A-7", reward=10, num=20, tgt="ghost", pres=2, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-8": Task("A-8", reward=10, num=22, tgt="snake", pres=3, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-9": Task("A-9", reward=10, num=20, tgt="nest", pres=3, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-10": Task("A-10", reward=10, num=22, tgt="fly", pres=3, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-11": Task("A-11", reward=10, num=25, tgt="wolf", pres=4, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-12": Task("A-12", reward=10, num=22, tgt="iceTroll", pres=4, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-13": Task("A-13", reward=10, num=25, tgt="eagle", pres=4, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-14": Task("A-14", reward=10, num=25, tgt="gunner", pres=5, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-15": Task("A-15", reward=10, num=20, tgt="lasercraft", pres=5, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-16": Task("A-16", reward=10, num=25, tgt="guard", pres=6, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-17": Task("A-17", reward=10, num=25, tgt="flamen", pres=6, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
    "A-18": Task("A-18", reward=10, num=20, tgt="assassin", pres=6, descript=["Kill (num) (tgt).","击杀(num)只(tgt)。"]),
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

# Runestone System ======================
# 存储符石的数据结构
class Runestone():
    def __init__(self, tag, name, cost, description):
        self.tag = tag
        self.name = name
        self.cost = cost
        self.description = description

# Runestone Brochure
RB = {
    "loadingStone": Runestone( "loadingStone", ("Loading Stone","填装符石"), 20, 
        ("Reduce loading time from 3 secs to 2.5 secs.","填装时间由3秒减少为2.5秒。") ),
    "sacredStone": Runestone( "sacredStone", ("Sacred Stone","神圣符石"), 15, 
        ("Gain one more SuperPower count in a game.","超级技能可用次数+1。") ),
    "bloodStone": Runestone( "bloodStone", ("Blood Stone","鲜血符石"), 25, 
        ("Restore 6 HP after killing a monster.","击杀一只怪物后，为自身回复6点体力。") ),
    #"terrorStone": Runestone( "terrorStone", ("Terror Stone","恐惧符石"), 20, 
    #    ("Critic damage deals 0.5 secs of dizziness.","暴击伤害附带眩晕0.5秒效果。") ),
    #"redemptionStone": Runestone( "redemptionStone", ("Redemption Stone","救赎符石"), 20, 
    #    (r"In first time dying, restore HP to 20%.","首次濒死时，将体力回复至20%继续战斗。") ),
    "hopeStone": Runestone( "hopeStone", ("Hope Stone","希望符石"), 20, 
        ("Whenever you get healed, heal 50% more.","每当自身受到治疗时，治疗量增加50%。") )
}