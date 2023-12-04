# -*- coding: utf-8 -*-
"""
myHero.py:
Define Hero class, as well as bullets, and superpower managers.
Hero class, 총알이나 슈퍼파워 관리하는 클래스
"""

import pygame
# 在myHero模块中，load、flip和collide_mask三个函数使用很频繁，这里导入这两个函数以方便使用（enemy同样）
from pygame.image import load
from pygame.transform import flip
from pygame.sprite import collide_mask
from random import random, randint, choice
import math

import enemy
from mapElems import ChestContent   # will be used in Javelin class
from props import *
from database import GRAVITY, DMG_FREQ, RANGE
from util import InanimSprite, HPBar
from util import getPos, rot_center, generateShadow, getCld


# ==========================================================
# ====================== Hero Object =======================
# ==========================================================
class Hero(InanimSprite):

    # some properties of hero
    name = "knight"
    heroNo = 0
    gender = "Male"
    health = 960
    full = 960
    arrow = 12
    fruit = 1

    speed = 3         # 계산에 사용되는 영웅의 이동 속도(특정 요인에 의해 느려질 수 있음)
    shootNum = 1      # 발사당 발사되는 발사체 수를 나타내는 데 사용됩니다(일부 영웅의 경우 다를 수 있으며 기본값은 1입니다).
    arrowCnt = 12     # 탄약 용량의 상한을 나타냅니다. ShootCnt와 구별된다는 점에 유의하시기 바랍니다. (shootCnt는 애니메이션 타이밍입니다)
    imgIndx = 0
    status = "left"
    activeProps = []  # 모든 활성 소품 목록을 동적으로 저장합니다.
    suspendedProps = [] # 타워 전환으로 인해 중단된 소품 목록입니다.
    coins = 0

    k1 = 0            # 첫 번째 레벨 점프 표시
    k2 = 0            # 두 번째 레벨 점프 표시
    aground = True    ## 영웅이 지상에 있는지 여부를 나타냅니다.
    gravity = 1
    shootCnt = 0      # 射击时更换图片过程的计数
    hitBack = 0       # 부상 넉백 효과, 부상 시 이 값을 넉백 픽셀로 설정합니다(수평 방향으로만)

    wpPos = [0,0,0]   # weapon相对于hero的位置比例：pos[0]表示x坐标比例，pos[1]表示y坐标比例，pos[2]表示层级，0表示weapon在self下层，1表示weapon在self上层。
    hitFeedIndx = 0
    checkList = None   # spriteGroup that stores wall or supply sprites used for checking collide
    preyList = []      # A list to store info of the killed or damaged enemy by this hero. Can be added by checkImg() or hero's bullet. Can be taken by the model loop. 
    eventList = []     # A list to store events info such as getItem.
    talk = []          # Pair: [txt, cnt]

    trapper = None     # 指向当前导致英雄减速、无法跳跃状态的对象，将引用挂在这里
    shootSnd = None
    jmpSnd = None
    image = None
    rect = None
    mask = None
    shad = None        # 阴影
    shadRect = None

    imgSwt = 8         # 行走时图片的切换频率。对于大部分英雄为8，某些英雄可能需要更快切换
    infected = -1      # 可取3个值：-1表示健康；0表示正在感染（感染效果）；1表示已感染
    freezeCnt = 0      # 当前被冰冻减速的倒计时
    bldColor = (255,10,10,210)
    jpCnt = 0
    font = None
    lgg = 0
    onlayer = 0        # indicate which layer hero is. only can be even number

    # Img Buffer: 以下是hero的库信息部分，保存易被修改的hero的原始信息。
    # 这部分在__init__时设置完成后，不允许再被修改。当需要恢复被改变的属性时，可以从这里读取恢复。
    oriSpd = 3           #영웅의 일반적인 이동속도를 나타냅니다.
    oriImgLeftList = []  # hero的行走图片列表
    oriImgRightList = []
    oriImgJumpLeft = None
    oriImgJumpRight = None
    oriImgHittedLeft = None
    oriImgHittedRight = None
    oriWeaponR = {}
    oriWpJumpLeft = None
    oriWpJumpRight = None

    # constructor of hero
    def __init__(self, VHero, dmgReduction, font, lgg, keyDic=None, cate="hero"):
        InanimSprite.__init__(self, cate)
        self.status = "left"
        self.imgIndx = 0
        self.kNum = 13       # 단일 단계 점프의 총 횟수(지면을 떠난 후 가장 높은 지점에 도달할 때까지의 횟수, 일방향 상승 과정)를 계산합니다.
        self.speed = 3
        self.imgSwt = 8
        self.interactiveList = ["chest","specialWall","hostage","door","exit","merchant"]

        self.superPowerFull = 3200  # 超级技能充满所需值
        if VHero.no == 0:
            self.name = "knight"
            self.push = 7
            self.weight = 2
            self.talkDic = { "ammoOut":("화살이 다 떨어졌어요!.","弓箭用完了。"), "shoot":("조심해!","看箭！"),
                "fullCharge":("충전 완료!","准备毁灭！"), "underCharge":("충전이 부족해요...","还需要充能……"), 
                "hitted":("아야!","呃啊！"), "wait":("기다리세요...","下一步应该……"), "follower":("","") }
            # 只保留left方向下的位置数据，根据hero的状态进行区分。right方向下，保持第二项不变，第一项用1去减即可。第三项只可取0或1。
            self.oriWeaponR = {"normal":[ (0.68,0.77,1), (0.63,0.75,1), (0.58,0.73,1), (0.63,0.75,1), (0.58,0.73,1) ], 
                "shoot":[ (0.1,0.62,1), (0.28,0.74,1), (0.5,0.8,1) ], "jump":(0.68,0.68,1), "superPower":(0.53,0.5,1)}
            self.gender = "Male"
        elif VHero.no == 1:
            self.name = "princess"
            self.push = 6
            self.weight = 1
            self.talkDic = { "ammoOut":("No more powder...","没有火药了……"), "shoot":("Taste this!","尝尝这个！"), 
                "fullCharge":("Lock and load!","炮火已上膛！"), "underCharge":("Why not stay beautiful?","为什么不多漂亮一会儿呢？"), 
                "hitted":("Ah!","啊！"), "wait":("I wonder...","我想……"), "follower":("Feel safer with you.","有你在感觉安全多了。") }
            self.oriWeaponR = { "normal":[ (0.35,0.72,1), (0.35,0.74,1), (0.35,0.72,1), (0.35,0.74,1), (0.35,0.72,1) ], 
                "shoot":[ (0.35,0.6,1), (0.35,0.58,1), (0.35,0.58,1) ], "jump":(0.12,0.82,0), "superPower":(0.2,0.65,1)}
            self.gender = "Female"
        elif VHero.no == 2:
            self.name = "prince"
            self.push = 8
            self.weight = 3
            self.talkDic = { "ammoOut":("I need javelins!.","我需要掷枪！"), "shoot":("Get away!","滚开！"), 
                "fullCharge":("Crush them!","碾碎它们！"), "underCharge":("My pony needs a rest.","我的马儿还需要休息。"), 
                "hitted":("Errr!","呃！"), "wait":("Pony's tired?","马儿累了吗？"), "follower":("Can you on earth do this?","你到底行不行啊？") }
            self.oriWeaponR = {"normal":[ (0.4,0.7,1), (0.42,0.69,1), (0.39,0.68,1), (0.42,0.69,1), (0.39,0.68,1) ], 
                "shoot":[ (0.39,0.76,1), (0.41,0.72,1), (0.43,0.7,1) ], "jump":(0.64,0.48,1), "superPower":(0.64,0.48,1)}
            self.kNum += 1
            self.gender = "Male"
        elif VHero.no == 3:
            self.name = "wizard"
            self.push = 6
            self.weight = 2
            self.talkDic = { "ammoOut":("Fire don't reply.","火元素无法召出了。"), "shoot":("Burn...","灼烧吧……"), 
                "fullCharge":("I feel the lightning...","我已感受到了雷电……"), "underCharge":("Calm down, and feel the nature.","冷静下来，才能感受自然。"), 
                "hitted":("Ouch!","呃啊！"), "wait":("Need to ponder...","需要思考一下……"), "follower":("I'll follow you, kid.","我会紧跟着，孩子。") }
            self.oriWeaponR = {"normal":[ (0.09,0.64,0), (0.08,0.62,0), (0.09,0.66,0), (0.1,0.62,0), (0.09,0.66,0) ], 
                "shoot":[ (0.53,0.64,1), (0.49,0.67,1), (0.44,0.78,0) ], "jump":(0.08,0.64,0), "superPower":(0.5,0.45,1)}
            self.gender = "Male"
        elif VHero.no == 4:
            self.name = "huntress"
            self.push = 6
            self.weight = 1
            self.talkDic = { "ammoOut":("Need a rest!","得休息一下。"), "shoot":("Penetrating!","穿刺一切！"), 
                "fullCharge":("Boomerang on the way.","骨镖已就绪。"), "underCharge":("If my dog is here...","要是我的狗狗在这的话……"), 
                "hitted":("That hurts!","好痛！"), "wait":("Miss my hound...","想念我的猎犬了……"), "follower":("You are as brave as my hound!","你和我的猎犬一样勇敢！") }
            self.oriWeaponR = {"normal":[ (0.7,0.6,0), (0.7,0.6,0), (0.7,0.62,0), (0.7,0.6,0), (0.7,0.62,0) ], 
                "shoot":[ (0.7,0.6,0), (0.68,0.62,0), (0.66,0.61,0) ], "jump":(0.69,0.64,0), "superPower":(0.53,0.48,0)}
            self.gender = "Female"
        elif VHero.no == 5:
            self.name = "priest"
            self.push = 6
            self.weight = 1
            self.talkDic = { "ammoOut":("There's no forever power.","没有力量是永恒的。"), "shoot":("For Holy light!","为了圣光！"), 
                "fullCharge":("The Good is about to arrive.","大善即将到来。"), "underCharge":("It needs time to prove pious and kind.","证明虔诚和善良需要时间。"), 
                "hitted":("Ahhh!","啊！"), "wait":("God leads me...","上帝会指引我……"), "follower":("Are you the angle from the heaven?","你是来自天堂的天使吗？") }
            self.oriWeaponR = {"normal":[ (0.27,0.82,0), (0.28,0.82,0), (0.36,0.78,0), (0.28,0.82,0), (0.22,0.77,0) ], 
                "shoot":[ (0.28,0.8,0), (0.22,0.75,0), (0.16,0.64,0) ], "jump":(0.12,0.62,1), "superPower":(0.16,0.64,0)}
            self.gender = "Female"
        elif VHero.no == 6:
            self.name = "king"
            self.push = 8
            self.weight = 2
            self.talkDic = { "ammoOut":("Reloading now!","正在填装！"), "shoot":("Power of King!","国王的力量！"), 
                "fullCharge":("It's time to call my fighters!","是时候召唤我的战士们了！"), "underCharge":("What a previledge to see a king playing!","观赏国王展示，真是至高的荣耀！"), 
                "hitted":("Doc!","医官！"), "wait":("What to do...","接下来怎么做……"), "follower":("I promise you'll be promoted when we get out!","我保证，回去后给你升官！") }
            self.oriWeaponR = {"normal":[ (0.05,0.45,0), (0.04,0.44,0), (0.04,0.46,0), (0.04,0.44,0), (0.04,0.46,0) ], 
                "shoot":[ (0.08,0.55,1), (0.1,0.53,1), (0.12,0.5,0) ], "jump":(0.04,0.46,0), "superPower":(0.05,0.45,0)}
            self.shootNum = 5
            self.serv = None
            self.gender = "Male"
        elif VHero.no == -1:
            self.name = "servant"
            self.push = 6
            self.weight = 1
            self.talkDic = { "ammoOut":("No more powder...","没有火药了……"), "shoot":("Fuck off!","滚吧！"),
                "fullCharge":("Fight!","战斗！"), "underCharge":("Still need to charge...","还需要充能……"), 
                "hitted":("Ah!","啊！"), "wait":("My honor to stand with you.","很荣幸能和您并肩作战。"), 
                "follower":("","") }
            self.oriWeaponR = { "normal":[ (0.13,0.82,1), (0.22,0.81,1), (0.2,0.8,1), (0.24,0.83,1), (0.2,0.8,1) ], 
                "shoot":[ (0.1,0.64,1), (0.12,0.63,1), (0.12,0.63,1) ], "jump":(0.16,0.74,0), "superPower":(0.53,0.5,1)}
            self.gender = "Female"
        self.rDamage = VHero.dmg
        self.arrowCnt = VHero.cnt
        self.critR = round(VHero.crit/100, 2)   # 转化为0-1之间的数
        self.stunR = 0
        self.oriSpd = self.speed
        self.heroNo = VHero.no
        if keyDic:
            self.keyDic = keyDic
        
        # About the bag: -------------------------------------------
        self.bagpack = Bagpack()
        self.activeProps = []
        self.coins = 0
        self.gems = 0
        self.expInc = 0
        self.arrow = self.arrowCnt
        self.jpCnt = 0
        self.dmgReducDic = {
            "basic":dmgReduction, "physical":1, "fire":1, "corrosive":1, "freezing":1, "holy":1
        }   # 调节游戏难度所引起的受伤减少，为百分比。1表示原伤害。
        self.respondKeyDic = {
            "leftKey": lambda delay: self.moveX( delay, "left" ),
            "rightKey": lambda delay: self.moveX( delay, "right" )
        }   # 定义需要连续响应键盘按键的键名和对应的函数列表

        self.ammoCircle = pygame.transform.smoothscale( load("image/ammoCircle.png"), (40, 40) )
        self.lumi = 0           # 明亮半径：在mist中将会起作用
        self.hitBack = 0
        self.spurtCanvas = None
        self.checkList = pygame.sprite.Group()
        self.preyList = []
        self.eventList = []
        self.weaponR = self.oriWeaponR
        self.font = font[lgg]
        self.lgg = lgg
        self.doom = False
        # About HP:---------------------------
        self.health = self.full = VHero.hp
        self.loading = self.LDFull = 180
        self.heal_bonus = 1
        self.bar = HPBar(self.full, barOffset=12, color="green")
        # About SuperPower: ----------------------------------------
        self.superPowerCnt = 0      # 超级技能当前能量值
        self.superPowerFull = VHero.superPowerFull  # 超级技能充满所需值
        self.superPowerCast = 0     # 超级技能释放后图片停留计时
        self.superPowerBar = HPBar(self.superPowerFull, blockVol=450, barOffset=2, color="yellow")
        self.superPowerManager = None
        if VHero.no>=0:
            spicon = load(f"image/{self.name}/superPowerIcon.png").convert_alpha()
            self.superPowerIcon = pygame.transform.smoothscale( spicon, (spicon.get_width()//2, spicon.get_height()//2) )

        # 初始化hero的图片库------------------------------------
        self.oriImgLeftList = [ load("image/"+self.name+"/heroLeft0.png").convert_alpha(), 
            load("image/"+self.name+"/heroLeft2.png").convert_alpha(), load("image/"+self.name+"/heroLeft1.png").convert_alpha(), 
            load("image/"+self.name+"/heroLeft2.png").convert_alpha(), load("image/"+self.name+"/heroLeft3.png").convert_alpha() ]
        self.oriImgRightList = [ flip(self.oriImgLeftList[0], True, False), 
            flip(self.oriImgLeftList[1], True, False), flip(self.oriImgLeftList[2], True, False), 
            flip(self.oriImgLeftList[3], True, False), flip(self.oriImgLeftList[4], True, False) ]
        self.oriImgJumpLeft = load("image/"+self.name+"/jumpLeft.png").convert_alpha()
        self.oriImgJumpRight = flip(self.oriImgJumpLeft, True, False)
        self.oriImgHittedLeft = load("image/"+self.name+"/hittedLeft.png").convert_alpha()
        self.oriImgHittedRight = flip(self.oriImgHittedLeft, True, False)
        self.oriWpJumpLeft = load("image/"+self.name+"/wpJump.png").convert_alpha()
        self.oriWpJumpRight = flip(self.oriWpJumpLeft, True, False)
        self.imgLib = {
            "leftList": self.oriImgLeftList,
            "rightList": self.oriImgRightList,
            "weaponLeft": load("image/"+self.name+"/weapon.png").convert_alpha(),
            "weaponRight": flip(load("image/"+self.name+"/weapon.png").convert_alpha(), True, False),
            "wpMoveLeft": load("image/"+self.name+"/wpMove.png").convert_alpha(),
            "wpMoveRight": flip(load("image/"+self.name+"/wpMove.png").convert_alpha(), True, False),

            "shootLeftList": [ load("image/"+self.name+"/shootLeft0.png").convert_alpha(), 
                load("image/"+self.name+"/shootLeft1.png").convert_alpha(), 
                load("image/"+self.name+"/shootLeft2.png").convert_alpha() ],
            "shootRightList": [ flip(load("image/"+self.name+"/shootLeft0.png").convert_alpha(), True, False), 
                flip(load("image/"+self.name+"/shootLeft1.png").convert_alpha(), True, False), 
                flip(load("image/"+self.name+"/shootLeft2.png").convert_alpha(), True, False) ],
            "wpAttLeft": [ load("image/"+self.name+"/wpAtt0.png").convert_alpha(), 
                load("image/"+self.name+"/wpAtt1.png").convert_alpha(), 
                load("image/"+self.name+"/wpAtt2.png").convert_alpha() ],
            "wpAttRight": [ flip(load("image/"+self.name+"/wpAtt0.png").convert_alpha(), True, False), 
                flip(load("image/"+self.name+"/wpAtt1.png").convert_alpha(), True, False), 
                flip(load("image/"+self.name+"/wpAtt2.png").convert_alpha(), True, False) ],
            
            "superPowerLeft": load("image/"+self.name+"/superPower.png").convert_alpha(),
            "superPowerRight": flip(load("image/"+self.name+"/superPower.png").convert_alpha(), True, False),
            "wpSuperPowerLeft": load("image/"+self.name+"/wpSuperPower.png").convert_alpha(),
            "wpSuperPowerRight": flip(load("image/"+self.name+"/wpSuperPower.png").convert_alpha(), True, False),

            "jumpLeft": self.oriImgJumpLeft,
            "jumpRight": self.oriImgJumpRight,
            "wpJumpLeft": self.oriWpJumpLeft,
            "wpJumpRight": self.oriWpJumpRight,

            "hittedLeft": self.oriImgHittedLeft,
            "hittedRight": self.oriImgHittedRight,

            "infShootLeft": load("image/stg3/dead"+self.gender+"Vomit.png").convert_alpha(),
            "infShootRight": flip(load("image/stg3/dead"+self.gender+"Vomit.png").convert_alpha(), True, False),
            "infLeftList": [load("image/stg3/dead"+self.gender+"Wait.png").convert_alpha(), 
                load("image/stg3/dead"+self.gender+"1.png").convert_alpha(), load("image/stg3/dead"+self.gender+"0.png").convert_alpha(), 
                load("image/stg3/dead"+self.gender+"1.png").convert_alpha(), load("image/stg3/dead"+self.gender+"2.png").convert_alpha() ],
            "infRightList": [flip(load("image/stg3/dead"+self.gender+"Wait.png").convert_alpha(), True, False), 
                flip(load("image/stg3/dead"+self.gender+"1.png").convert_alpha(), True, False), 
                flip(load("image/stg3/dead"+self.gender+"0.png").convert_alpha(), True, False), 
                flip(load("image/stg3/dead"+self.gender+"1.png").convert_alpha(), True, False), 
                flip(load("image/stg3/dead"+self.gender+"2.png").convert_alpha(), True, False) ]
        }
        # generate shadows
        self.shadLib = {}
        for each in self.imgLib:
            if isinstance(self.imgLib[each],list):
                self.shadLib[each] = []
                for img in self.imgLib[each]:
                    self.shadLib[each].append( generateShadow(img) )
            else:
                self.shadLib[each] = generateShadow(self.imgLib[each])
        
        # initialize the position of hero ------------------------------
        self.setImg("leftList", 0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        # Initialize the melee weapon of the hero ----------------------
        self.weapon = enemy.Ajunction( self.imgLib["weaponLeft"], getPos(self, self.weaponR["normal"][0][0], self.weaponR["normal"][0][1]) )
        self.wpPos = [ self.weaponR["normal"][0][0], self.weaponR["normal"][0][1], self.weaponR["normal"][0][2] ]   # 初始化为normal[0]
        # Jump dust imgs -----------------------------------------------
        self.dustList = [load("image/stg2/alarm5.png").convert_alpha(), load("image/stg2/alarm4.png").convert_alpha(), 
            load("image/stg2/alarm3.png").convert_alpha(), load("image/stg2/alarm2.png").convert_alpha(), 
            load("image/stg2/alarm1.png").convert_alpha(), load("image/stg2/alarm0.png").convert_alpha()]

        self.brand = load("image/"+self.name+"/brand.png").convert_alpha()
        self.jmpPos = [0,0]
        self.jmpInfo = ()
        self.jmpCap = (1+self.kNum)*self.kNum //2 # 单次跳跃的上升距离，将在初始化时计算得出

        self.jmpSnd = pygame.mixer.Sound("audio/"+self.name+"/jump.wav")
        self.oriJmpSnd = self.jmpSnd
        self.shootSnd = pygame.mixer.Sound("audio/"+self.name+"/shoot.wav")
        self.oriShootSnd = self.shootSnd
        self.fruitSnd = pygame.mixer.Sound("audio/eatFruit.wav")
        self.injureSnd = pygame.mixer.Sound("audio/injure"+self.gender+".wav")
        # infection related
        self.infSnd = pygame.mixer.Sound("audio/infect"+self.gender+".wav")
        self.infJmp = pygame.mixer.Sound("audio/infJump"+self.gender+".wav")
        self.coinSnd = pygame.mixer.Sound("audio/coin.wav")
        self.reloadSnd = pygame.mixer.Sound("audio/reload.wav")
        self.vomiSnd = pygame.mixer.Sound("audio/vomiSplash.wav")
        # 开场语
        if self.category=="hero":
            VHero.voice.play(0)
            self.superPowerVoice = pygame.mixer.Sound("audio/"+self.name+"/superPowerVoice.wav")

    # 用于重置本元素的位置至所给塔楼的初始位置
    def resetPosition(self, tower, tag="p1", layer="-1", side="left"):
        if side=="left":
            pos_x = tower.boundaries[0]-tower.blockSize
        elif side=="right":
            pos_x = tower.boundaries[1]+tower.blockSize
        elif side=="center":
            pos_x = sum(tower.boundaries)//2
        if tag=="p1":
            pos_x = pos_x-10
        elif tag=="p2":
            pos_x = pos_x+10
        self.rect.left = pos_x-self.rect.width//2
        self.rect.bottom = tower.getTop( str(layer) )-12

    def jump(self, keyLine):
        self.aground = False
        # 一段跳
        if (self.k2==0):
            if (self.k1==1):   # 一段跳刚开始时，获取起跳时的位置
                if random()<0.33: 
                    self.jmpSnd.play(0)
                self.jpCnt = 12
                self.jmpPos[0] = self.rect.left + self.rect.width//2
                self.jmpPos[1] = self.rect.bottom
            self.rect.bottom -= (self.kNum-self.k1)
            self.k1 = (self.k1+1)%(self.kNum+1)
        # 二段跳
        else:
            self.rect.bottom -= (self.kNum-self.k2)
            self.k2 = (self.k2+1)%(self.kNum+1)
        while ( getCld(self, self.checkList, ["sideWall","baseWall","blockStone"]) ):  # 如果和参数中的物体重合，则回退1高度
            self.rect.bottom += 1        # 循环+1，直到不再和任何物体重合为止，跳出循环
            self.k1 = self.k2 = 0
        if ( self.rect.bottom <= keyLine ):
            self.shiftLayer(2, None)
        
    def moveX(self, delay, to):
        # 运动过程中，可取index为[1,2,3,4] 分别对应运动的四张帧图（0为静止）
        if not (delay % self.imgSwt ):
            self.imgIndx += 1
            if self.imgIndx >= len(self.imgLib["leftList"]):
                self.imgIndx = 1
        if to=="left":
            self.status = "left"
            self.rect.left -= self.speed
            self._checkMove( back=-self.speed )
        elif to=="right":
            self.status = "right"
            self.rect.left += self.speed
            self._checkMove( back=self.speed )

    def fall(self, keyLine, newLine, heightList, GRAVITY):
        self.rect.bottom += self.gravity  # 尝试将自身纵坐标减去重力值
        # 获得所有碰撞了的物体对象，并针对每一个碰撞了的item执行相应的响应动作
        for item in pygame.sprite.spritecollide(self, self.checkList, False, collide_mask):
            if item.category in self.interactiveList:
                item.interact(self)
        while getCld(self, self.checkList, ["lineWall","baseWall","specialWall","sideWall","blockStone","house"]):
            if self.gravity>4:  # 速度过大，造成扬灰效果
                self.jpCnt = 12
                self.jmpPos[0] = self.rect.left + self.rect.width//2
                self.jmpPos[1] = self.rect.bottom
            # 如果和参数中的物体重合，则回退1高度
            self.rect.bottom -= 1    # 循环-1，直到不再和任何物体重合为止，跳出循环
            self.aground = True      # 这两个值反复设置没有关系，只要循环结束后保证两个值分别为true和1即可
            self.gravity = 0
        if (self.gravity<GRAVITY):
            self.gravity += 1
        self.renewCheckList(newLine) # 更新self.checkList（跳跃函数中不必更新，只有这里需要更新）
        # 判断是否要向下调整层数.
        if ( self.rect.top >= keyLine ):
            self.shiftLayer(-2, heightList)

    def shiftLayer(self, to, heightList):
        if to<0:
            # 下跳则检查：在最底层不能下跳；# 若英雄高度超过所在行的高度-跳跃距离的一半，则不能下跳（这是为了防止过快连跳）。
            if (self.onlayer<=0) or ( self.rect.bottom < heightList[str(self.onlayer)]-self.jmpCap//2 ):
                return
        self.onlayer += to
        self.aground = False

    def shoot(self, tower, spurtCanvas=None):
        #if (self.shootCnt > 0):     # couldn't shoot too fast! Hero mustn't be shooting.
        #    return
        if self.infected>0:         # infect situation.
            self.shootSnd.play(0)
            self.vomiSnd.play(0)
            self.shootCnt = 40
            return
        if (self.arrow > 0):
            self.shootSnd.play()
            if random() <= 0.2:
                self.talk = [self.talkDic["shoot"][self.lgg], 60]
            if self.status=="left":
                self.hitBack = self.push-self.weight
                pos = getPos(self, 0, 0.54)
                xspd = [-1,-2,-3]
            else:
                self.hitBack = -(self.push-self.weight)
                pos = getPos(self, 1, 0.54)
                xspd = [1,2,3]
            # make ammo object
            if self.name == "knight":
                arrow = Ammo( self, pos, [8,0], category="bullet", bldNum=6, push=6 )
                tower.allElements["mons1"].add(arrow)
            elif self.name == "princess":
                arrow = Ammo( self, pos, [8,0], category="bullet", bldNum=8, push=7 )
                tower.allElements["mons1"].add(arrow)
                if spurtCanvas:                      # bullet特效
                    spurtCanvas.addSpatters( 5, (1,2), (12,14,16), (255,255,0), pos, False, xspd=xspd, yspd=[-1,0,1] )
            elif self.name == "prince":
                arrow = Javelin( self, pos )
                tower.allElements["mons1"].add(arrow)
            elif self.name == "wizard":
                arrow = Fireball( self, pos )
                tower.allElements["mons1"].add(arrow)
            elif self.name == "huntress":
                arrow = Dart( self, pos )
                tower.allElements["mons1"].add(arrow)
            elif self.name == "priest":
                arrow = HolyLight( self, pos )
                tower.allElements["mons1"].add(arrow)
            elif self.name == "king":
                spdList = ( [7,2],[8,1],[8,0],[8,-1],[7,-2] )
                for i in range(0, self.shootNum):
                    arrow = Ammo( self, pos, spdList[i], category="bullet", bldNum=4, push=4, duration=RANGE["SHORT"] )
                    tower.allElements["mons1"].add(arrow)
                if spurtCanvas:                      # bullet打出特效
                    spurtCanvas.addSpatters( 5, (1,2), (12,14,16), (255,255,0), pos, False, xspd=xspd, yspd=[-1,0,1] )
            self.arrow -= 1
        elif self.arrow<=0:
            self.talk = [self.talkDic["ammoOut"][self.lgg], 60]
            self.reloadSnd.play()
        self.shootCnt = 18

    def castSuperPower(self, canvas):
        if self.superPowerCnt<self.superPowerFull:  # not fully charged yet
            self.talk = [self.talkDic["underCharge"][self.lgg], 60]
            return False
        self.superPowerVoice.play(0)
        canvas.addHalo( "holyHalo", 240 )
        if self.name=="knight":
            self.superPowerManager = SuperPowerManagerKnight(self)
        elif self.name=="princess":
            self.superPowerManager = SuperPowerManagerPrincess(self)
        elif self.name=="prince":
            self.superPowerManager = SuperPowerManagerPrince(self)
        elif self.name=="wizard":
            self.superPowerManager = SuperPowerManagerWizard(self)
        elif self.name=="huntress":
            self.superPowerManager = SuperPowerManagerHuntress(self)
        elif self.name=="priest":
            self.superPowerManager = SuperPowerManagerPriest(self)
        elif self.name=="king":
            self.superPowerManager = SuperPowerManagerKing(self)
        self.superPowerCnt = 0
        self.superPowerCast = 30
    
    def chargeSuperPower(self, amount):
        if self.superPowerCnt==self.superPowerFull:
            return
        self.superPowerCnt += amount
        if self.superPowerCnt > self.superPowerFull:
            self.superPowerCnt = self.superPowerFull
            pygame.mixer.Sound("audio/knight/superPowerCast.wav").play(0)
            self.talk = [self.talkDic["fullCharge"][self.lgg], 90]
            if self.spurtCanvas:
                self.spurtCanvas.addSpatters( 12, [3,5,7], [36,42,48], (255,200,100,240), getPos(self,0.5,0.5), False )
        
    def checkImg(self, delay, tower, heroes, key_pressed, spurtCanvas):
        """
        A pipeline to do the following checks and operations:
            1. calculate img cnts and select correct image
            2. respond to the player's ongoing keydown event
            3. check hero's state: freeze, trapped, hitback, infection, etc.
            4. manage hero's bagpack
            5. check and run props & superPowers
        """
        if self.health<=0:
            return 0
        # 画起跳的灰尘
        if self.jpCnt > 0:
            self.jpCnt -= 1
            self.dustRect = self.dustList[ self.jpCnt//2 ].get_rect()
            self.dustRect.left = self.jmpPos[0] - self.dustRect.width // 2
            self.dustRect.bottom = self.jmpPos[1]
            self.jmpInfo = ( self.dustList[ self.jpCnt//2 ], self.dustRect )
        else:
            self.jmpInfo = ()
        # Check when hero is shooting an arrow.
        if ( self.shootCnt > 0 ) and (self.infected<=0):
            if not ( self.shootCnt % 6 ):     # Cnt每次等于6的倍数的时候就更换一次图片
                indx = len(self.imgLib["shootLeftList"]) - self.shootCnt//6  # 指示图片序号的临时变量。工作原理：Cnt=18的时候，imgIndx应该为0；同理，Cnt=12,imgIndx=1；Cnt=6，indx=3。
                if self.status == "left":
                    rht = self.rect.right
                    btm = self.rect.bottom
                    self.setImg("shootLeftList",indx)
                    self.rect = self.image.get_rect()              # 获取新的图片的rect
                    self.rect.right = rht
                    self.rect.bottom = btm
                    self.weapon.updateImg( self.imgLib["wpAttLeft"][indx] ) # weapon的图片序号和wIndx图片序号保持同步。
                    self.wpPos[0] = self.weaponR["shoot"][indx][0]
                elif self.status == "right":
                    lft = self.rect.left
                    btm = self.rect.bottom
                    self.setImg("shootRightList",indx)
                    self.rect = self.image.get_rect()
                    self.rect.left = lft
                    self.rect.bottom = btm
                    self.weapon.updateImg( self.imgLib["wpAttRight"][indx] )
                    self.wpPos[0] = 1 - self.weaponR["shoot"][indx][0]
                self.wpPos[1] = self.weaponR["shoot"][indx][1]
                self.wpPos[2] = self.weaponR["shoot"][indx][2]
            
            self.shootCnt -= 1
        # Check when hero is jumping in the air. Note that the statement "elif" makes that hero's image will be whiping when he whip even in the air.
        elif not self.aground:
            if self.status == "left":
                self.setImg("jumpLeft")
                self.weapon.updateImg( self.imgLib["wpJumpLeft"] )
                self.wpPos[0] = self.weaponR["jump"][0]
            elif self.status == "right":
                self.setImg("jumpRight")
                self.weapon.updateImg( self.imgLib["wpJumpRight"] )
                self.wpPos[0] = 1 - self.weaponR["jump"][0]
            self.wpPos[1] = self.weaponR["jump"][1]
            self.wpPos[2] = self.weaponR["jump"][2]
        # Check when hero is suffering damage.
        elif self.hitFeedIndx > 0:
            if (self.status=="right"):
                self.setImg("hittedRight")
            else:
                self.setImg("hittedLeft")
            self.hitFeedIndx -= 1
        # Check when hero is casting superPower.
        elif self.superPowerCast>0:     # 刚刚施放技能的0.5s内，有施放图片
            self.superPowerCast -= 1
            if (self.status=="right"):
                self.setImg("superPowerRight")
                self.weapon.updateImg( self.imgLib["wpSuperPowerRight"] )
                self.wpPos[0] = 1 - self.weaponR["superPower"][0]
            else:
                self.setImg("superPowerLeft")
                self.weapon.updateImg( self.imgLib["wpSuperPowerLeft"] )
                self.wpPos[0] = self.weaponR["superPower"][0]
            self.setRect()
            self.wpPos[1] = self.weaponR["superPower"][1]
            self.wpPos[2] = self.weaponR["superPower"][2]
        # If hero is not shooting, not jumping and not hurting, he should only be in normal status (static and walking).
        else:
            if self.status == "left":
                self.setImg("leftList",self.imgIndx)
                # Check whether hero is moving. Different pic for moving and standing.
                if self.imgIndx==0:
                    self.weapon.updateImg( self.imgLib["weaponLeft"] )
                else:
                    self.weapon.updateImg( self.imgLib["wpMoveLeft"] )
                self.wpPos[0] = self.weaponR["normal"][self.imgIndx][0]
            elif self.status == "right":
                self.setImg("rightList",self.imgIndx)
                if self.imgIndx==0:
                    self.weapon.updateImg( self.imgLib["weaponRight"] )
                else:
                    self.weapon.updateImg( self.imgLib["wpMoveRight"] )
                self.wpPos[0] = 1 - self.weaponR["normal"][self.imgIndx][0]
            self.wpPos[1] = self.weaponR["normal"][self.imgIndx][1]
            self.wpPos[2] = self.weaponR["normal"][self.imgIndx][2]
            if not delay% 120 and random()<0.24:
                self.talk = [self.talkDic["wait"][self.lgg], 60]
        # Always renew the position of the weapon.
        self.weapon.updatePos( getPos(self, self.wpPos[0], self.wpPos[1]) )
        if self.category=="hero":
            for key_name in self.respondKeyDic:
                if key_pressed[ self.keyDic[key_name] ]:    # 若被摁下，则call该匿名函数
                    if key_name=="shootKey":
                        self.respondKeyDic[key_name](tower.monsters)
                    else:
                        self.respondKeyDic[key_name](delay)
            # Specifically, if not running, set the imgIndx to zero.
            if self.imgIndx>0 and not key_pressed[self.keyDic["leftKey"]] and not key_pressed[self.keyDic["rightKey"]]:
                self.imgIndx = 0
        # deal freezeCnt
        if self.freezeCnt > 0:
            self.freezeCnt -= 1
        else:
            self.speed = self.oriSpd   # 解冻
        # deal stuck if there is a trapper in effect.
        if self.trapper:
            if not collide_mask(self, self.trapper):
                self.trapper = None
            else:
                self.speed = self.oriSpd-2
        # 处理击退位移，如果值不为0的话。
        if abs(self.hitBack)>0:
            if self.hitBack>0:
                realBack = min(self.hitBack, 6)
                self.hitBack -= 1
            elif self.hitBack<0:
                realBack = max(self.hitBack, -6)
                self.hitBack += 1
            self.rect.left += realBack
            self._checkMove( back=realBack )
        # deal infection
        if self.infected == 0:
            self.infected = 1
            spurtCanvas.addSpatters( 12, [3, 4, 5], [12,14,16], (10,10,10,240), getPos(self, 0.5, 0.5), True )
        elif self.infected>0:
            if self.shootCnt > 0:
                self.shootCnt -= 1
                if self.status == "left":
                    rht = self.rect.right
                    btm = self.rect.bottom
                    self.setImg("infShootLeft")
                    self.rect = self.image.get_rect()       # 获取新的图片的rect
                    self.rect.right = rht
                    self.rect.bottom = btm
                elif self.status == "right":
                    lft = self.rect.left
                    btm = self.rect.bottom
                    self.setImg("infShootRight")
                    self.rect = self.image.get_rect()
                    self.rect.left = lft
                    self.rect.bottom = btm
                # 每2次刷新均吐出1个vomi
                if not self.shootCnt%2:
                    spdX = 9-self.shootCnt//8
                    if self.status == "left":
                        spd = [ -spdX, 0 ]
                        startX = 0.2
                    elif self.status == "right":
                        spd = [ spdX, 0 ]
                        startX = 0.8
                    spurtCanvas.addAirAtoms(self, 1, getPos(self, startX, 0.5),
                                            spd, tower.monsters, "corrosive", btLine=self.rect.bottom)
        vib = 0
        # Renew Props.
        for prop in self.activeProps[::-1]:
            if prop.propName == "blastingCap":
                prop.fall( delay, tower.getTop(prop.onlayer), tower.groupList, GRAVITY )
                if prop.work(tower.monsters, tower.groupList["0"], spurtCanvas):
                    vib = max(vib,12)
            elif prop.propName == "torch":
                prop.work(tower.monsters, spurtCanvas)      # 溅射的火星对范围内敌人造成伤害
            elif prop.propName == "battleTotem":
                if not prop.checkExposion(spurtCanvas):     # 检查摧毁
                    tracker = prop.run([self], spurtCanvas)
                    if tracker:
                        tower.allElements["mons1"].add( tracker )
            elif prop.propName == "rustedHorn":
                if prop.work(tower.monsters, heroes):
                    vib = max(vib,8)
            elif prop.propName == "defenseTower":
                if prop not in heroes:
                    heroes.append(prop)
                    self.activeProps.remove(prop)
            else:   # Normal Durable prop.
                prop.work()
        # 超级技能。
        if self.superPowerManager:
            if self.superPowerManager.run(delay, tower, heroes, spurtCanvas):    # 生效阶段，震动屏幕
                vib = max(vib,6)
        return vib
    
    def shiftTower(self, tower, oper="suspend"):
        """ oper='suspend' or 'rejoin' """
        if oper=="suspend":     # 将老tower中的activeprop转为挂起。NOTE:Props 自己会记住owner。
            for prop in self.activeProps[::-1]:
                if prop.propName in ["blastingCap","battleTotem"]:
                    self.activeProps.remove(prop)
                    tower.suspendedProps.append(prop)
        elif oper=="rejoin":    # 将新tower中被挂起的prop转入active
            for prop in tower.suspendedProps[::-1]:
                if prop.user==self:
                    tower.suspendedProps.remove(prop)
                    self.activeProps.append(prop)
        
    def reload(self, delay, spurtCanvas):
        # Check loading listener: When ammos run out and loading is full
        if self.arrow==0 and self.loading==self.LDFull:
            self.loading = 0
            self.reloadSnd.play(0)
        # when loading is not full: Reloading...
        elif self.loading<self.LDFull:
            self.loading += 1
            if self.loading==self.LDFull:
                self.arrow = self.arrowCnt
                self.reloadSnd.play(0)
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (100,100,210,240), getPos(self, 0.5, 0.5), False )

    def useItem(self, spurtCanvas):
        if self.bagpack.bagPt<0:
            return ("가방에 아무 것도 없어요!","你的背包中没有道具！")
        curName = self.bagpack.bagBuf[self.bagpack.bagPt]
        if curName == "fruit":
            if self.infected>=0:
                return ("감염 되었을 땐, 과일을 먹을 수 없어요!.","感染时无法使用。")
            elif self.health == self.full:
                return ("이미 체력이 풀피에요.","当前你的体力值已满。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("fruit")
                self.recover(100)
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (100,255,100,240), getPos(self, 0.5, 0.5), False )
        elif curName == "loadGlove":
            if (self.loading>=self.LDFull-1):
                return ("No need for loading at the time.","当前无需填装。")
            elif self.infected>=0:
                return ("Can't eat fruit when infected.","感染时无法使用。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("loadGlove")
                self.loading = self.LDFull-1
                #spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (100,100,210,240), getPos(self, 0.5, 0.5), False )
        elif curName == "medicine":
            if self.infected <=0 and self.health == self.full:
                return ("You are neither infected nor injured.","你既未感染，也未受伤。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("medicine")
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (100,100,255,240), getPos(self, 0.5, 0.5), False )
                if self.infected <= 0:
                    # 未感染，回复体力
                    self.recover(100)
                else:
                    # 感染，治愈：恢复image和相关属性值
                    self.infected = -1
                    self.imgLib["leftList"] = self.oriImgLeftList
                    self.imgLib["rightList"] = self.oriImgRightList
                    self.imgLib["jumpLeft"] = self.oriImgJumpLeft
                    self.imgLib["jumpRight"] = self.oriImgJumpRight
                    self.imgLib["hittedLeft"] = self.oriImgHittedLeft
                    self.imgLib["hittedRight"] = self.oriImgHittedRight
                    self.imgIndx = 0
                    self.weaponR = self.oriWeaponR
                    self.jmpSnd = self.oriJmpSnd
                    self.shootSnd = self.oriShootSnd
        elif curName == "blastingCap":
            self.fruitSnd.play(0)
            self.bagpack.decItem("blastingCap")
            cap = BlastingCap(self, [-4, -7], self.onlayer) if self.status=="left" else BlastingCap(self, [4, -7], self.onlayer)
            self.activeProps.append( cap )
        elif curName == "battleTotem":
            # 首先检查是否可以放置图腾
            wall = None
            wallList = []
            for aWall in self.checkList:   # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
                # 筛选出当前所在的行砖
                if aWall.category in ("lineWall","specialWall","baseWall") and aWall.coord[1]==self.onlayer-1:
                    wallList.append(aWall)
                    if aWall.rect.left<getPos(self,0.5,0)[0]<aWall.rect.right:  # 可以落到下一行上，有砖接着
                        wall = aWall
            if (not wallList) or (not wall):     # 不能放置图腾，取消效果
                return ("Please place the totem on the ground!","请将图腾放置于地面！")
            self.fruitSnd.play(0)
            self.bagpack.decItem("battleTotem")
            totem = BattleTotem(self, wall, self.onlayer)
            spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], totem.themeColor, getPos(totem, 0.5, 0.5), False )
            self.activeProps.append( totem )
        elif curName == "defenseTower":
            ok = False
            # 检查是否可以放置防御塔
            for wall in DefenseTower.siteWalls:
                if (wall.rect.left<getPos(self,0.5,0)[0]<wall.rect.right) and (wall.coord[1]==self.onlayer-1):
                    if wall.tower:
                        return ("The site has a existing Defense Tower.","该基座已有一个防御塔。")
                    else:
                        # 玩家处于sitewall上，且该砖空余，则可以放置
                        self.fruitSnd.play(0)
                        self.bagpack.decItem("defenseTower")
                        tow = DefenseTower(getPos(wall,0.5,0)[0], wall.rect.top, self.onlayer, self.font, self.lgg, self)
                        spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (120,240,120), getPos(tow, 0.5, 0.5), False )
                        self.activeProps.append( tow )
                        wall.tower = tow
                        ok = True
                        break
            if not ok:     # 不能放置防御塔，取消效果
                return ("Please place the tower on the ground!","请将防御塔放置于基座上！")
        # Create the enduring prop and put it in the activeList.
        elif curName == "torch":
            if self.infected >= 0:
                return ("Can't eat fruit when infected.","感染时无法使用。")
            elif self.oneInEffect("torch"):
                return ("You have a torch working.","你已经有一个火炬在照明。")
            else:
                self.bagpack.decItem("torch")
                self.activeProps.append( Torch(self) )
        elif curName == "copter":
            if self.oneInEffect("copter"):
                return ("You have a copter working.","你已经装有一个竹蜻蜓。")
            else:
                self.bagpack.decItem("copter")
                self.activeProps.append( Copter(self) )
        elif curName == "pesticide":
            if self.oneInEffect("pesticide"):
                return ("You are holding another pesticide spray.","你正持有另一个杀虫喷雾器。")
            else:
                self.bagpack.decItem("pesticide")
                self.activeProps.append( Pesticide(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (100,140,40,240), getPos(self, 0.5, 0.5), False )
        elif curName == "herbalExtract":
            if self.health == self.full:
                return ("Your HP is full at the time.","当前你的体力值已满。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("herbalExtract")
                self.activeProps.append( HerbalExtract(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (80,240,160,240), getPos(self, 0.5, 0.5), False )
        elif curName == "simpleArmor":
            if self.oneInEffect("simpleArmor"):
                return ("You have equiped a armor.","你已经装备了一件简易机甲。")
            else:
                self.bagpack.decItem("simpleArmor")
                self.activeProps.append( SimpleArmor(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (100,140,40,240), getPos(self, 0.5, 0.5), False )
        elif curName == "missleGun":
            if self.oneInEffect("missleGun"):
                return ("You are holding another missle gun.","你正持有另一个火箭炮。")
            else:
                self.bagpack.decItem("missleGun")
                self.activeProps.append( MissleGun(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (100,140,40,240), getPos(self, 0.5, 0.5), False )
        elif curName == "cooler":
            if self.oneInEffect("cooler"):
                return ("You are under the effect of another cooler.","你已有一个清凉饮料在生效。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("cooler")
                self.activeProps.append( Cooler(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (255,255,160,240), getPos(self, 0.5, 0.5), False )
        elif curName == "alcohol":
            if self.oneInEffect("alcohol"):
                return ("You are under the effect of another alcohol.","你已有一个烈酒在生效。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("alcohol")
                self.activeProps.append( Alcohol(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (255,160,160,240), getPos(self, 0.5, 0.5), False )
        elif curName == "toothRing":
            if self.oneInEffect("toothRing"):
                return ("You are under the effect of another toothRing.","你已有一个龙牙之戒在生效。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("toothRing")
                self.activeProps.append( ToothRing(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (180,0,100,240), getPos(self, 0.5, 0.5), False )
        elif curName == "shieldSpell":
            if self.oneInEffect("shieldSpell"):
                return ("You are under the effect of another shield spell.","你已有一个护盾法术在生效。")
            else:
                self.fruitSnd.play(0)
                self.bagpack.decItem("shieldSpell")
                self.activeProps.append( ShieldSpell(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (255,255,160,240), getPos(self, 0.5, 0.5), False )
        elif curName == "rustedHorn":
            if self.oneInEffect("rustedHorn"):
                return ("You are under the effect of another rusted horn.","你已有一个生锈的号角在生效。")
            else:
                self.bagpack.decItem("rustedHorn")
                self.activeProps.append( RustedHorn(self) )
                spurtCanvas.addSpatters( 12, [3, 4, 5], [16,20,24], (255,210,160,240), getPos(self, 0.5, 0.5), False )

    def oneInEffect(self, propName):  # 检测是否有正在生效的某类用品
        for prop in self.activeProps:
            if prop.propName == propName:
                return prop
        return None

    def renewCheckList(self, new, clear=False):    # 动态调节checkList内的检测砖块，以减轻负担
        if clear==True:
            self.checkList.empty()
        else:
            rmvList = ["lineWall","specialWall","house"]#,"baseWall"]
            for each in self.checkList:
                if each.category in rmvList:
                    self.checkList.remove(each)
        for each in new:
            self.checkList.add(each)
    
    def hitted(self, damage, pushed, dmgType):
        if self.health<=0:
            return
        # 检查伤害减轻效果
        damage *= self.dmgReducDic["basic"]
        damage *= self.dmgReducDic[dmgType]
        self.health -= damage
        # Do if hero is dead
        if (self.health <= 0):
            self.health = 0
            self.doom = True
            self.infected = 1   # 借用此flag，不再绘制武器
            if self.category == "hero":
                self.spurtCanvas.addHalo("deadHalo", 180)
            # Change dead image
            self.image = load(f"image/{self.name}/defeat.png").convert_alpha()
            if self.status=="right":
                self.image = flip(self.image, True, False)
            self.setRect()
            return True
        self.hitFeedIndx = 6
        if pushed>0:    # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0:  # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        # 若本对象是玩家操控的英雄而非AI，则对整个频幕进行渲染反馈。
        if self.category == "hero":
            self.spurtCanvas.addHalo( "hitHalo", 180 )
        # 音效
        if self.injureSnd.get_num_channels()==0:
            self.injureSnd.play(0)
        # 以下是硬直效果，取消所有的英雄射箭、二段跳行为
        self.shootCnt = self.k2 = 0
        if random()<0.1:
            self.talk = [self.talkDic["hitted"][self.lgg], 60]

    def recover(self, heal):
        if self.health<=0:
            return
        #self.spurtCanvas.addSpatters(8, (2,3,4), (20,22,24), (10,240,10), getPos(self,0.5,0.4) )
        self.health += heal * self.heal_bonus
        if (self.health > self.full):
            self.health = self.full

    def freeze(self, decre):
        self.freezeCnt = 120
        if self.speed == self.oriSpd:
            self.speed = self.oriSpd - decre
        self.spurtCanvas.addHalo( "frzHalo", 160 )
    
    def infect(self):
        self.infSnd.play(0)
        self.infected = 0     # 置为0，以指示受到感染的瞬间
        self.torchCnt = 0     # 如果感染时有火炬，则将之熄灭
        self.imgLib["leftList"] = self.imgLib["infLeftList"]
        self.imgLib["rightList"] = self.imgLib["infRightList"]
        self.imgIndx = 0
        self.imgLib["jumpLeft"] = self.imgLib["infLeftList"][0]
        self.imgLib["jumpRight"] = self.imgLib["infRightList"][0]
        #self.imgLib["wpJumpLeft"] = self.imgLib["wpHideLeft"]
        #self.imgLib["wpJumpRight"] = self.imgLib["wpHideRight"]
        self.imgLib["hittedLeft"] = self.imgLib["infLeftList"][1]
        self.imgLib["hittedRight"] = self.imgLib["infRightList"][1]
        # sound
        self.jmpSnd = self.infJmp
        self.shootSnd = self.infSnd
    
    def reportHit(self, mons):
        if mons.hitted( 20, 0, "corrosive" )==True:
            self.preyList.append( (getPos(mons,0.5,0.5), mons.bldColor, 0, mons.category, mons.coin, False) )                

    def paint(self, screen):
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 8
        screen.blit(self.shad, shadRect)
        #按层级顺序画weapon和self
        if self.infected>0:
            screen.blit( self.image, self.rect )
        else:
            if self.wpPos[2]==0:
                screen.blit( self.weapon.image, self.weapon.rect )
                screen.blit( self.image, self.rect )
            elif self.wpPos[2]==1:
                screen.blit( self.image, self.rect )
                screen.blit( self.weapon.image, self.weapon.rect )
        # 绘制生效中的道具效果。
        for prop in self.activeProps:
            prop.paint( screen )
        # 绘画跳跃烟尘效果
        if len(self.jmpInfo)>0:
            screen.blit( self.jmpInfo[0], self.jmpInfo[1] )
        # 超级技能
        if self.superPowerManager:
            self.superPowerManager.paint(screen)
        
    def drawHeads(self, screen):
        if self.health<=0:
            return
        # draw HP
        if self.hitFeedIndx:
            self.bar.setColor("lightGreen")
        else:
            self.bar.setColor("green")
        self.bar.paint(self, screen)
        if self.category=="hero":
            # draw loading bar
            self.drawLDBar( screen )
            # draw super power bar
            if self.superPowerCnt==self.superPowerFull:
                self.drawSPBar( screen )
            else:
                self.superPowerBar.paint(self, screen, "superPower")
        # Draw talk.
        if len(self.talk):
            txt = self.font.render( self.talk[0], True, (255,255,255) )
            rect = txt.get_rect()
            rect.left = self.rect.left+self.rect.width//2-rect.width//2
            rect.bottom = self.rect.top-24
            bg = pygame.Surface( (rect.width, rect.height) ).convert_alpha()
            bg.fill( (0,0,0,180) )
            screen.blit( bg, rect )
            screen.blit( txt, rect )
            self.talk[1]-=1
            if self.talk[1]<=0:
                self.talk.clear()
    
    def receiveExp(self, num, typ):
        if typ=="coin":
            self.eventList.append("coin")
            self.coinSnd.play(0)
            self.coins += num
        elif typ=="gem":
            self.coinSnd.play(0)
            self.gems += num
    
    def setImg(self, name, indx=-1):  # 根据状态名称切换图片。如果是列表，要给出indx值。
        if indx==-1:
            self.image = self.imgLib[name]
            self.shad = self.shadLib[name]
        else:
            self.image = self.imgLib[name][indx]
            self.shad = self.shadLib[name][indx]

    def setRect(self):
        tmpPos = [self.rect.left+self.rect.width//2, self.rect.bottom]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = tmpPos[0] - self.rect.width//2
        self.rect.bottom = tmpPos[1]
        
    def drawLDBar(self, surface, height=10):
        '''Shown when hero is reloading. 和monsters类似地，在self上方绘制环形蓝条。'''
        x = self.rect.left+self.rect.width//2 -self.bar.barLen/2   # 中线减去血条长度的一半。
        y = self.rect.top-height
        # 画左侧弹药圆圈
        cRect = self.ammoCircle.get_rect()
        cRect.right = x+2
        cRect.top = y+self.bar.barH//2-cRect.height//2
        surface.blit( self.ammoCircle, cRect)
        # 显示数量信息
        txt = self.font.render( f"{self.arrow}", True, (255,255,255) )
        trect = txt.get_rect()
        trect.left = cRect.left+cRect.width//2-trect.width//2
        trect.top = cRect.top+cRect.height//2-trect.height//2
        surface.blit( txt, trect)
        # 无需填装时不填装
        if self.loading==self.LDFull:
            return False
        ld = max( self.loading, 0 )
        start_angle = math.radians( 90 )
        stop_angle = math.radians( 90+round( 360*(ld/self.LDFull) ) )
        # Colors
        lightColor, color, shadeColor = self.bar.colorSet["blue"]
        pygame.draw.arc(surface, color, cRect, start_angle, stop_angle, width=4)
        return True
    
    def drawSPBar(self, surface, height=10):
        x = self.rect.left+self.rect.width//2 +self.bar.barLen/2   # 中线减去血条长度的一半。
        y = self.rect.top-height
        # 画左侧弹药圆圈
        cRect = self.ammoCircle.get_rect()
        cRect.left = x+2
        cRect.top = y+self.bar.barH//2-cRect.height//2
        surface.blit( self.ammoCircle, cRect)
        # 显示箭矢图标
        irect = self.superPowerIcon.get_rect()
        irect.left = cRect.left+cRect.width//2-irect.width//2
        irect.top = cRect.top+cRect.height//2-irect.height//2
        surface.blit( self.superPowerIcon, irect)
        return True

    def _checkMove(self, back=0):
        for each in self.checkList:
            if ( collide_mask(self, each) ):
                if each.category in ["sideWall","blockStone"]:
                    # 尝试身高坐标-5，再看是否还会碰撞。5以内的高度都可以自动踩上去
                    self.rect.top -= 5
                    if getCld(self, self.checkList, ["sideWall","blockStone"]):
                        self.rect.top += 5
                        self.rect.left -= back
                elif each.category == "hollowWall":
                    if each.close=="left" and self.rect.left<=each.rect.left:
                        self.rect.left += self.speed
                    elif each.close=="right" and self.rect.right>=each.rect.right:
                        self.rect.right -= self.speed
        
    def lift(self, dist):
        self.rect.bottom += dist
        self.jmpPos[1] += dist
        if self.superPowerManager:
            self.superPowerManager.lift(dist)
        for prop in self.activeProps:
            prop.lift(dist)
    
    def level(self, dist):
        self.rect.left += dist
        self.jmpPos[0] += dist
        if self.superPowerManager:
            self.superPowerManager.level(dist)
        for prop in self.activeProps:
            prop.level(dist)
    

# ==========================================================
# ========================= Ammos ==========================
# ==========================================================
class Ammo(InanimSprite):  # 各种ammo的基本原型
    
    def __init__(self, hero, pos, spd, category="bullet", bldNum=0, push=0, duration=RANGE["NORM"]):  # 参数hero为发射者的对象引用。
        # bullet是最原始的子弹模型，函数简单，没有花里胡哨的能力和效果。功能更强的：bulletPlus
        InanimSprite.__init__(self, category)
        self.direct = hero.status
        self.speed = spd
        if self.direct=="left":
            self.speed[0] = -self.speed[0]
        
        src = "image/"+hero.name+"/arrow_left.png" if (hero.name != "wizard") else "image/"+hero.name+"/arrow_left0.png"
        self.image = load(src).convert_alpha()
        if self.direct=="right":
            self.image = flip(self.image, True, False)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()   # initialize the position of the ammo.
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.top = pos[1]-self.rect.height//2
        self.hitSnd = pygame.mixer.Sound("audio/"+hero.name+"/hit.wav")
        self.checkList = pygame.sprite.Group()
        for each in hero.checkList:
            if each.category in ("sideWall", "lineWall", "specialWall", "baseWall"):
                self.checkList.add(each)
        self.damage = hero.rDamage
        self.dmgType = "physical"
        self.bldNum = bldNum
        self.push = push
        self.owner = hero
        # 存在时间。默认为knight：720
        self.duration = duration
        # 是否暴击
        self.crit = True if (random()<hero.critR) else False
        if self.crit:
            self.damage = round(self.damage*1.5)
            self.push = round(self.push*1.5)
            self.bldNum = round(self.bldNum*1.5)
        # 是否眩晕
        self.stun = True if (self.crit or random()<hero.stunR) else False

    def move(self, monsters, canvas, bg_size):
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        self.duration -= abs(self.speed[0])
        if pygame.sprite.spritecollide(self, self.checkList, False, collide_mask) or self.rect.left>bg_size[0] or self.rect.right<0: # 撞上墙壁或砖块
            self.erase(canvas)
            return False
        hitInfo = self.hitMonster(monsters)
        if hitInfo or self.duration<=0:
            self.erase(canvas)
            return hitInfo

    def hitMonster(self, monsters, single=True, r=0, chargeSP=True):
        """
        param single: True表示单一伤害。设为False则会对所有monster进行检测。
        param r: r=0表示单体伤害，r>0则为范围伤害，会对r半径内的所有怪物造成伤害。
        param chargeSP: 造成伤害时是否给英雄充能。
        """
        if r>0:
            formerPos = [self.rect.left+self.rect.width//2, self.rect.top+self.rect.height//2]
            self.image = makeCircle(r)
            self.mask = pygame.mask.from_surface(self.image)
            self.rect = self.image.get_rect()
            self.rect.left = formerPos[0]-self.rect.width//2
            self.rect.top = formerPos[1]-self.rect.height//2
            single = False
        for each in monsters:
            if collide_mask(self, each):
                self.hitSnd.play()
                # 以下封装需要传递给主函数进行击中反馈的信息：
                # 确定击中点的坐标pos
                pos = [ 0, self.rect.top+self.rect.height//2 ]
                if self.direct=="left":
                    pos[0]=self.rect.left
                    realPush = -self.push
                elif self.direct=="right":
                    pos[0]=self.rect.right
                    realPush = self.push
                # 对命中的怪物进行受伤操作，记录其是否死亡的真值（hitted返回True表示死亡）
                if each.hitted(self.damage, realPush, self.dmgType)==True:
                    deadInfo = each.category
                else:
                    deadInfo = False
                    if self.stun:
                        each.stun(30)
                self.owner.preyList.append( (pos, each.bldColor, self.bldNum, deadInfo, each.coin, self.crit) )
                if chargeSP:
                    self.owner.chargeSuperPower(self.damage)
                if single:
                    return True
    
    def _explodeEffect(self, canvas):
        canvas.addSpatters(4, [1,2,3], [8,10,12], [20,20,20,240], getPos(self, 0.5, 0.5), False)

    def erase(self, canvas):
        self._explodeEffect(canvas)
        self.kill()

def makeCircle(r):
    surface = pygame.Surface([2*r, 2*r]).convert_alpha()
    surface.fill((0,0,0,0))
    pygame.draw.circle(surface, (255,255,255),(r,r),r)
    return surface

class Javelin(Ammo):
    def __init__(self, hero, pos):
        Ammo.__init__(self, hero, pos, [6,-3], "bulletPlus", bldNum=4, push=5, duration=RANGE["SHORT"])  # speed[1] can be interpreted as gravity
        self.oriImg = self.image.copy()
        self.rotated = 0

    def fetch(self, bg_size):
        pygame.mixer.Sound("audio/getItem.wav").play(0)
        # 修改owner属性数量，设定substance的目的坐标
        self.owner.arrow += 1
        substance = ChestContent("javelin", self.image, 1, getPos(self,0.5,0.5), self.owner.rect)
        self.owner.eventList.append( substance )
        self.kill()
        del self
        return True
    
    def move(self, delay, monsters, canvas, bg_size, GRAVITY=8):
        if self.speed[0]==0:           # 水平速度为0，表示已经停下，等待被owner重新收集
            if collide_mask(self, self.owner):
                self.fetch(bg_size)
            return False
        self.rect.left += self.speed[0]# 移动
        self.rect.top += self.speed[1]
        self.duration -= abs(self.speed[1])
        if not ( delay % 3 ):          # 3的倍数才旋转、掉落
            if abs(self.rotated) < 80: # 
                if self.speed[0]<0:
                    self.rotated += 5
                elif self.speed[0]>0:
                    self.rotated -= 5
                self.image = rot_center(self.oriImg, self.rotated, subsurf=False)
                self.mask = pygame.mask.from_surface(self.image)
            if self.speed[1]<GRAVITY:  
                self.speed[1] += 1     # 竖直速度增加
        # 撞上墙壁或砖块（stay），或者掉落出界（erase）
        if self.rect.top>bg_size[1]:
            self.erase(canvas)
            return False
        elif pygame.sprite.spritecollide(self, self.checkList, False, collide_mask):
            self._explodeEffect(canvas)
            self.speed[1] = -3
            if self.speed[0]>0:
                self.rotated = -20
                self.speed[0] -= 1
            elif self.speed[0]<0:
                self.rotated = 20
                self.speed[0] += 1
            else:
                self.speed[1] = 0
        # 命中怪物
        if self.hitMonster(monsters) or self.duration<=0:
            self.erase(canvas)

    def _explodeEffect(self, canvas):
        canvas.addSpatters(4, [1,2,3], [8,10,12], [180,180,180,240], getPos(self,0.5,1), True)
    
class Fireball(Ammo):
    def __init__(self, hero, pos):
        Ammo.__init__(self, hero, pos, [6,0], "bulletPlus", bldNum=6, push=5, duration=RANGE["SHORT"])
        self.imgList = [ load("image/"+hero.name+"/arrow_left0.png").convert_alpha(), load("image/"+hero.name+"/arrow_left1.png").convert_alpha() ]
        if self.direct == "right":
            for i in range( len(self.imgList) ):
                self.imgList[i] = flip(self.imgList[i], True, False)
        self.imgIndx = 0
        self.doom = -1
        self.dmgType = "fire"
        
    def move(self, delay, monsters, canvas, bg_size):
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        canvas.addTrails( [1,2,3], [8,10,12], (250,140,100,240), getPos(self, choice([0.4,0.5,0.6]), choice([0.4,0.5,0.6])) )
        self.duration -= abs(self.speed[0])
        # 如果撞上墙壁/砖块或monster，则爆炸。
        if pygame.sprite.spritecollide(self, self.checkList, False, collide_mask) or pygame.sprite.spritecollide(self, monsters, False, collide_mask):
            self.hitSnd.play(0)
            # 继续前进若干个speed[0]，使得爆炸能够影响更深的敌人
            self.rect.left += self.speed[0]*4
            # deal damage
            self.hitMonster(monsters, single=False, r=34)
            self.erase(canvas)
            return
        elif (self.rect.left>bg_size[0]) or (self.rect.right<0) or (self.duration<=0):
            self.erase(canvas)
            return False
        if not delay%6:
            self.imgIndx = (self.imgIndx+1) % len(self.imgList)
            self.image = self.imgList[self.imgIndx]
    
    def _explodeEffect(self, canvas):
        canvas.addExplosion(getPos(self,0.5,0.5), 26, 12)
    
class Dart(Ammo):
    def __init__(self, hero, pos):
        Ammo.__init__(self, hero, pos, [6,0], "bulletPlus", bldNum=2, push=5, duration=RANGE["LONG"])
        self.oriImg = self.image.copy()
        self.rotated = 0
        self.attCnt = 0
    
    def move(self, delay, monsters, canvas, bg_size):
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        self.duration -= abs(self.speed[0])
        if not delay%2:    # 旋转
            if self.speed[0]<0:
                self.rotated += 30
                if self.rotated >=360:
                    self.rotated = 0
            elif self.speed[0]>0:
                self.rotated -= 30
                if self.rotated <= -360:
                    self.rotated = 0
            self.image = rot_center(self.oriImg, self.rotated, subsurf=False)
            self.mask = pygame.mask.from_surface(self.image)
        if pygame.sprite.spritecollide(self, self.checkList, False, collide_mask):
            # 弹回的情况：撞上墙壁或砖块
            self._explodeEffect(canvas)
            self.speed[0] = -self.speed[0]
            self.direct = "left" if self.direct=="right" else "right"
        elif self.rect.left>bg_size[0] or self.rect.right<0 or self.duration<=0:
            # 消失的情况
            self.erase(canvas)
            return False
        self.attCnt += 1
        if not self.attCnt % (DMG_FREQ//2):
            self.hitMonster(monsters, single=False)

class HolyLight(Ammo):
    def __init__(self, hero, pos):
        Ammo.__init__(self, hero, pos, [5,0], "bulletPlus", bldNum=5, push=5)
        self.lastTgt = None
        self.newTgt = None
        self.dmgType = "holy"
        self.dmgDura = 3    # 最多可命中3个目标（弹射2次）
    
    def hitMonster(self, monsters, chargeSP=True):
        for each in monsters:
            if collide_mask(self, each):
                if each == self.lastTgt:
                    continue
                self.hitSnd.play()
                realPush = self.push if self.direct=="right" else -self.push
                dead = each.hitted(self.damage, realPush, "holy")
                if dead:
                    deadInfo = each.category
                else:
                    self.lastTgt = each
                    deadInfo = False
                    if self.crit:
                        each.stun(30)
                pos = getPos(self, 0.5, 0.5)
                self.owner.preyList.append( (pos, each.bldColor, self.bldNum, deadInfo, each.coin, self.crit) )
                if chargeSP:
                    self.owner.chargeSuperPower(self.damage)
                # 处理完一次击中后，伤害减少40点（初始伤害120），检查是否还可追击下一次
                self.damage -= 40
                self.dmgDura -= 1
                if self.dmgDura>0:
                    self.newTgt = None
                    self.duration = RANGE["SHORT"]
                    # find new tgt.
                    for innerEach in monsters:
                        if not innerEach==self.lastTgt and innerEach.rect.bottom>0 and innerEach.rect.top<960:
                            dist = math.pow( getPos(innerEach,0.5,0.5)[0]-getPos(self,0.5,0.5)[0], 2 ) + math.pow( getPos(innerEach,0.5,0.5)[1]-getPos(self,0.5,0.5)[1], 2 )
                            if dist <= (180*180):
                                self.newTgt = innerEach
                                for tgt in self.checkList:
                                    if tgt.category in ("lineWall","specialWall"):
                                        self.checkList.remove(tgt)
                                self.speed[0] = ( getPos(innerEach,0.5,0.5)[0] - getPos( self, 0.5, 0.5 )[0] )//10
                                self.speed[1] = ( getPos(innerEach,0.5,0.5)[1] - getPos( self, 0.5, 0.5 )[1] )//10
                                break
                    # 遍历执行到这里说明没有符合距离要求的对象，故执行删除
                    if not self.newTgt:
                        self.kill()
                        del self
                else:
                    self.kill()
                    del self
                return True

    def move(self, delay, monsters, canvas, bg_size):
        # move the object, and generate a wake to its tail.
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        self.duration -= max( abs(self.speed[0]), abs(self.speed[1]) )
        canvas.addTrails( [1,2,3], [6, 7, 8], (255,192,203,240), getPos(self, choice([0.4,0.5,0.6]), choice([0.4,0.5,0.6])) )
        # No matter what phase it is, when hit wall, stop it.
        if pygame.sprite.spritecollide(self, self.checkList, False, collide_mask): # 撞上墙壁或砖块
            self.hitSnd.play(0)
            self.erase(canvas)
            return False
        elif self.rect.left>bg_size[0] or self.rect.right<0 or self.duration<=0:
            self.erase(canvas)
            return False
        # Deal damage and continue the light when it hit monsters, if hit draw hit effect.
        if self.hitMonster(monsters):
            self._explodeEffect(canvas)

    def _explodeEffect(self, canvas):
        canvas.addWaves( getPos(self, 0.5, 0.5), (255,192,203,240), 20, 12 )
        

# =========================================================
# -------- 脚本hero。冒险模式下的被救者跟班、侍从 -----------
# =========================================================
class Follower(Hero):
    master = None
    secFlag = False

    def __init__(self, pos, VHero, fnt, lgg):
        Hero.__init__(self, VHero, 1, fnt, lgg, cate="follower")
        self.secFlag = False
        self.rect.left = pos[0]
        self.rect.bottom = pos[1]
        self.shootR = 0.6   # 射击点纵向位置

    def activate(self, master, tower):
        self.master = master
        self.keyDic = master.keyDic
        self.onlayer = master.onlayer
        self.dmgReducDic["basic"] = master.dmgReducDic["basic"]
        # RENEW CHECKLIST
        self.renewCheckList(tower.groupList["0"], clear=True)
        self.renewCheckList(tower.chestList)
        self.renewCheckList(tower.elemList)

    def decideAction(self, delay, tower, spurtCanvas):
        # 判断是否抵达最终出口。
        if tower.porter.category=="exit" and (not tower.porter.locked) and collide_mask(self,tower.porter):
            return True
        # 判断是否需要二段跳。
        if ( self.secFlag ) and ( self.k1==self.kNum) and self.k2==0:
            self.secFlag = False
            self.k2 = 1
        # 判断是否要射击
        if (not delay%30):
            # 与任意怪物重合时
            if pygame.sprite.spritecollide(self, tower.monsters, False, collide_mask):
                self.shoot(tower, spurtCanvas)
            # 未重合,检查攻击范围内
            else:
                for mons in tower.monsters:
                    shootPos = getPos(self, 0.5,self.shootR)
                    rvPos = getPos(mons, 0.5,0)
                    # 判断是否要shoot: mons在shoot的攻击范围内。
                    if ( mons.rect.bottom > shootPos[1] > mons.rect.top ):
                        if ( rvPos[0] > self.rect.right ) and self.status=="left":
                            self.status = "right"
                        elif ( rvPos[0] < self.rect.left ) and self.status=="right":
                            self.status = "left"
                        else:
                            self.shoot(tower, spurtCanvas)
        # 如果在master之上，则下跳一层。
        if self.onlayer>self.master.onlayer:
            if not delay%80:
                self.shiftLayer(-2, tower.heightList)
                self.aground = False
        else:
            # 否则若处于同一层或在master之下，则跳跃，并将二段跳的标志设为true。
            if self.onlayer<self.master.onlayer:
                if not self.trapper and self.aground and ( self.k1 == 0 ):
                    self.secFlag = True
                    self.k1 = 1
            if self.rect.left>=self.master.rect.right-10:
                self.moveX(delay, "left")
            elif self.rect.right<=self.master.rect.left+10:
                self.moveX(delay, "right")
        if not delay% 120 and random()<0.24:
            self.talk = [self.talkDic["follower"][self.lgg], 60]
        return False
    
    def checkKeyPressed(self, key_pressed, delay):
        return

    def castSuperPower(self, canvas):
        return 

    def freeze(self, decre):
        self.freezeCnt = 120
        if self.speed == self.oriSpd:
            self.speed = self.oriSpd - decre

class Servant(Hero):
    # some properties of Servant
    talk = []          # Pair: [txt, cnt]
    trapper = None     # 指向当前导致英雄减速、无法跳跃状态的对象，将引用挂在这里
    jmpSnd = None
    infected = -1      # 可取3个值：-1表示健康；0表示正在感染（感染效果）；1表示已感染

    def __init__(self, master, VHero, pos, font, lgg, onlayer):
        #                     basic dmgReduction
        Hero.__init__(self, VHero, 0.7, font, lgg, keyDic=master.keyDic, cate="servant")
        self.master = master
        self.rival = None
        self.secFlag = False
        self.onlayer = onlayer        # indicate which layer hero is. only can be even number
        self.shootR = 0.6   # 射击点纵向位置
        self.nxtMove = ""
        self.hunt_lost = self.hunt_lost_full = 360    # 减为0时，表示当前目标丢失过久/失效，重新寻找目标
        self.interactiveList = ["specialWall"]

        # initialize the position of hero ------------------------------
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.bottom = pos[1]
        self.fd = randint(8,24)     # 和master贴近的距离，每个侍从都不一样，这样能够避免多个侍从重合
    
    def shoot(self, allElements, spurtCanvas=None):
        if self.shootCnt==0:
            self.shootSnd.play()
            if random() <= 0.2:
                self.talk = [self.talkDic["shoot"][self.lgg], 60]
            if self.status=="left":
                self.hitBack = 3
                pos = getPos(self, 0, self.shootR)
                xspd = [-1,-2,-3]
            else:
                self.hitBack = -3
                pos = getPos(self, 1, self.shootR)
                xspd = [1,2,3]
            # make ammo object
            arrow = Ammo( self, pos, [8,0], category="bullet", bldNum=8, push=7 )
            allElements.add(arrow)
            if spurtCanvas:                 # bullet特效
                spurtCanvas.addSpatters( 5, (1,2), (12,14,16), (255,255,0), pos, False, xspd=xspd, yspd=[-1,0,1] )
            self.shootCnt = 18

    def freeze(self, decre):
        self.freezeCnt = 120
        if self.speed == self.oriSpd:
            self.speed = self.oriSpd - decre
    
    def infect(self):
        return
    
    def castSuperPower(self, canvas):
        return
    
    # =========
    def decideAction(self, delay, tower, spurtCanvas):
        # 判断是否需要二段跳。
        if ( self.secFlag ) and ( self.k1==self.kNum) and self.k2==0:
            self.secFlag = False
            self.k2 = 1
        
        # 判断是否要水平移动：
        if self.rival:
            self.hunt_lost -= 1
            if self.hunt_lost <= 0:
                self.rival = None
                return
            if self.rival.health<=0:
                self.rival = None
                return
            # 调整位置，确认在战场中而不是边角
            if (self.rect.left<=tower.boundaries[0]):
                self.moveX(delay, "right")
                return
            elif (self.rect.right>=tower.boundaries[1]):
                self.moveX(delay, "left")
                return

            # 只要和mons重合就射击
            if (not delay%30) and pygame.sprite.spritecollide(self, tower.monsters, False, collide_mask):
                self.shoot(tower.allElements["mons1"], spurtCanvas)
                
            shootPos = getPos(self,0.5,self.shootR)
            rvPos = getPos(self.rival, 0.5, 0)
            # 情况一：如果自身在敌人上方，则下跳。
            if (shootPos[1]<self.rival.rect.top):
                if not delay%60:
                    self.shiftLayer(-2, tower.heightList)
                    self.aground = False
            # 情况二：处于敌人下方，则跳跃。
            elif (shootPos[1]>self.rival.rect.bottom):
                # 情况2.1：一次跳跃即可够着，则普通跳跃。
                if (shootPos[1]-91<=self.rival.rect.bottom):
                    if not self.trapper and self.aground and ( self.k1 == 0 ):
                        self.k1 = 1
                # 情况2.2：离得很远，将二段跳的标志设为true。
                else:
                    layer_no = str(self.onlayer+1)
                    if (layer_no in tower.groupList) and self.aground:
                        # 寻找最近的上一层砖块，并向之移动
                        self._findNearWall(tower, layer_no, shootPos[0], limit=[30,-30])
                    self.moveX(delay, self.nxtMove) # 计算移动方向与实际移动操作分离，是为了使英雄能落在上一层之后再决定下一层的方向
                    # 跳跃并置二段跳为True
                    if not self.trapper and self.aground and ( self.k1 == 0 ):
                        self.secFlag = True
                        self.k1 = 1
            # 处于同一层，略微远离目标。
            else:
                self.nxtMove = ""
                if (0 < self.rect.left-self.rival.rect.right < 12):
                    self.moveX(delay, "right")
                elif (-12 < self.rect.right-self.rival.rect.left < 0):
                    self.moveX(delay, "left")
                else:
                    # 判断是否要shoot:mons在shoot的攻击范围内。
                    if (not delay%30) and ( self.rival.rect.bottom > shootPos[1] > self.rival.rect.top ):
                        if ( rvPos[0] > self.rect.right ) and self.status=="left":
                            self.status = "right"
                        elif ( rvPos[0] < self.rect.left ) and self.status=="right":
                            self.status = "left"
                        else:
                            self.shoot(tower.allElements["mons1"], spurtCanvas)
                            self.hunt_lost = self.hunt_lost_full    # 对目标发动攻击，则重置目标丢失变量
            # 处于落地状态时，微调位置，避免站的太外
            layer_no = str(self.onlayer-1)
            if self.aground and self.rect.bottom>tower.getTop(layer_no):
                self._findNearWall(tower, layer_no, getPos(self,0.5,0)[0])
                self.moveX(delay, self.nxtMove)
        
        # 无目标的情况，则寻找目标，或追寻主人
        else:
            # 如果在master之上，则下跳一层。
            if self.onlayer>self.master.onlayer:
                if not delay%80:
                    self.shiftLayer(-2, tower.heightList)
                    self.aground = False
            else:
                # 否则若处于同一层或在master之下，则跳跃，并将二段跳的标志设为true。
                if self.onlayer<self.master.onlayer:
                    if not self.trapper and self.aground and ( self.k1 == 0 ):
                        self.secFlag = True
                        self.k1 = 1
                if self.rect.left>=self.master.rect.right-self.fd:
                    self.moveX(delay, "left")
                elif self.rect.right<=self.master.rect.left+self.fd:
                    self.moveX(delay, "right")
            # 寻找新的目标
            pool = []
            for mons in tower.monsters:
                if not mons.category in ["blockStone","fan","webWall"] and ( mons.rect.bottom >= 0 ) and ( mons.rect.top <= spurtCanvas.rect.height ):
                    pool.append(mons)
            if pool:
                self.rival = choice(pool)
                self.hunt_lost = self.hunt_lost_full    # 重置[目标丢失变量]
    
    def _findNearWall(self, tower, layer_no, ref_x, limit=[0,0]):
        # 寻找目标行距离ref_x位置最近的砖块，并向之移动
        minDist = (tower.boundaries[1]-tower.boundaries[0])*2   # 初始化为足够大（整个塔楼的直径）
        for wall in tower.groupList[layer_no]:
            dist = getPos(wall,0.5,0)[0] - ref_x
            if abs(dist)<abs(minDist):
                minDist = dist
        if minDist>limit[0]:
            self.nxtMove = "right"
        elif minDist<limit[1]:
            self.nxtMove = "left"
        else:
            self.nxtMove = ""

    def _executeShoot(self):
        pass


# =========================================================
# ----- 超级技能管理器。施放后此管理器同英雄一道checkImg -----
# =========================================================
class SuperPowerManager:
    def __init__(self, hero):
        self.caster = hero      # 施放者
        self.animationTime = 60 # All super power get a 1sec animation

    def run(self):              # 执行效果
        pass

    def paint(self, surface):   # 绘制函数
        pass

    def lift(self, dist):
        return
    
    def level(self, dist):
        return
    
class SuperPowerManagerKnight(SuperPowerManager):
    def __init__(self, hero):
        SuperPowerManager.__init__(self, hero)
        self.arrowCount = 15
        self.arrowList = pygame.sprite.Group()
        self.hitSnd = pygame.mixer.Sound("audio/knight/hit.wav")
        pygame.mixer.Sound("audio/knight/superPowerCast.wav").play(0)
        ori_img = load("image/knight/arrow_left.png").convert_alpha()
        # 生成15支箭
        rad = 400
        startX = getPos(self.caster,0.5,0)[0]-rad//2
        inter = rad//(self.arrowCount+1)
        for i in range(self.arrowCount):
            pos = ( startX, randint(-90,0) )
            arrow = pygame.sprite.Sprite()
            arrow.image = pygame.transform.rotate( ori_img, 90 )
            arrow.rect = arrow.image.get_rect()
            arrow.rect.left, arrow.rect.bottom = pos
            # Speed and hitCount
            arrow.speed = randint(7,10)
            arrow.hitCnt = 3
            self.arrowList.add( arrow )
            startX += inter
        # 前摇的装饰大箭
        self.ani_arrow = pygame.sprite.Sprite()
        self.ani_arrow.image = pygame.transform.rotate( ori_img, 270 )
        self.ani_arrow.rect = arrow.image.get_rect()
        self.ani_arrow.rect.left, self.ani_arrow.rect.bottom = getPos(self.caster, 0.5, 0.5)
        self.ani_arrow.speed = -10

    def run(self, delay, tower, heroes, canvas):
        # 前摇动画
        if self.animationTime>0:
            self.animationTime -= 1
            canvas.addTrails( [2,4,6], [12,14,16], (250,240,0), getPos(self.ani_arrow,0.5,0.9) )
            self.ani_arrow.rect.bottom += self.ani_arrow.speed
            return False
        elif self.animationTime==0:
            del self.ani_arrow
            self.ani_arrow = None
            self.animationTime -= 1
            pygame.mixer.Sound("audio/knight/superPowerEnforce.wav").play(0)
            return False
        else:
            # 真正实现效果
            for arrow in self.arrowList:
                canvas.addTrails( [1,3], [10,12,14], (250,240,0), getPos(arrow,0.5,0.1) )
                arrow.rect.bottom += arrow.speed
                if arrow.rect.top>=720:
                    arrow.kill()
                    del arrow
                    continue
                elif not delay % (DMG_FREQ//2):
                    # Deal Damage
                    for m in tower.monsters:
                        if collide_mask(arrow, m):
                            self.hitSnd.play()
                            # 以下封装需要传递给主函数进行击中反馈的信息：
                            pos = getPos(arrow, 0.5, 1)   # 确定击中点的坐标pos
                            push = choice([-6,6])
                            # 对命中的怪物进行受伤操作，记录其是否死亡的真值（hitted返回True表示死亡）
                            if m.hitted(70, push, "physical")==True:
                                deadInfo = m.category
                            else:
                                deadInfo = False
                            self.caster.preyList.append( (pos, m.bldColor, 6, deadInfo, m.coin, False) )
                            arrow.rect.bottom += arrow.speed//2
                            arrow.hitCnt -= 1
                            if arrow.hitCnt <= 0:
                                arrow.kill()
                                del arrow
                                break
            if len(self.arrowList)<=0:
                # 解绑，并删除自身
                self.caster.superPowerManager = None
                del self
            return True
    
    def paint(self, surface):
        if self.animationTime>0:
            surface.blit(self.ani_arrow.image, self.ani_arrow.rect)
        else:
            for arrow in self.arrowList:
                surface.blit(arrow.image, arrow.rect)

class SuperPowerManagerPrincess(SuperPowerManager):
    def __init__(self, hero):
        SuperPowerManager.__init__(self, hero)
        self.bulletCount = 8
        self.bulletList = pygame.sprite.Group()
        self.hitSnd = pygame.mixer.Sound("audio/princess/hit.wav")
        pygame.mixer.Sound("audio/princess/superPowerCast.wav").play(0)
        self.ori_img = load("image/princess/arrow_left.png").convert_alpha()
        self.hitRad = 80
        self.per_dmg = 140

    def run(self, delay, tower, heroes, canvas):
        # 0.5秒内连续射出6个榴弹。 create grenades.
        if (not delay%4) and self.bulletCount>0:
            if self.caster.status=="left":
                pos = getPos(self.caster, 0.05, 0.6)
                if self.caster.hitBack<3:
                    self.caster.hitBack = 3    # 后坐力：向右后退
            else:
                pos = getPos(self.caster, 0.95, 0.6)
                if self.caster.hitBack>-3:
                    self.caster.hitBack = -3    # 向左后退
            speed = [ randint(4,7), randint(-9,-4) ]
            # avoid critical hit
            ori_critR = self.caster.critR
            self.caster.critR = 0
            bullet = Ammo(self.caster, pos, speed, category="bullet", bldNum=6, push=6)
            self.caster.critR = ori_critR
            bullet.damage = self.per_dmg
            bullet.move = self.moveSP
            # Set its layer
            bullet.onlayer = self.caster.onlayer-1
            tower.allElements["mons1"].add( bullet )
            self.bulletList.add( bullet )
            self.bulletCount -= 1
        # 移动所有已经生成的榴弹
        for bullet in self.bulletList:
            canvas.addTrails( [1,3], [10,12,14], (250,240,0), getPos(bullet,0.5,0.1) )
            # 处理位移和速度
            bullet.rect.left += bullet.speed[0]
            bullet.rect.top += bullet.speed[1]
            if not delay%4:
                bullet.speed[1] = min(bullet.speed[1]+1, 7)
            # 判断层数下落
            if bullet.rect.top>=tower.heightList[str(bullet.onlayer)]:
                bullet.onlayer = max(bullet.onlayer-2, -1)
            # 判断出界
            if bullet.rect.top>=720:
                bullet.kill()
                del bullet
                continue
            else:
                # Check Collision. 与任意墙体发生碰撞，立即爆炸
                if pygame.sprite.spritecollide(bullet, tower.groupList[str(bullet.onlayer)], False) \
                    or pygame.sprite.spritecollide(bullet, tower.groupList["0"], False) or pygame.sprite.spritecollide(bullet, tower.monsters, False):
                    # 继续前进若干个speed，使得爆炸能够影响更深的敌人
                    bullet.rect.left += bullet.speed[0]
                    bullet.rect.top += bullet.speed[1]
                    # deal area damage
                    bullet.hitMonster(tower.monsters, single=False, r=self.hitRad, chargeSP=False)
                    canvas.addExplosion( 
                        getPos(bullet, 0.5,0.5), self.hitRad//2, self.hitRad//5, wFade=3, dotD=(20,22,24)
                    )
                    bullet.kill()
                    del bullet
                    break
        if self.bulletCount<=0 and len(self.bulletList)<=0:
            # 解绑，并删除自身
            self.caster.superPowerManager = None
            del self
        return True

    def moveSP(self, monsters, canvas, bg_size):
        return
    
class SuperPowerManagerPrince(SuperPowerManager):
    def __init__(self, hero):
        SuperPowerManager.__init__(self, hero)
        self.princeList = pygame.sprite.Group()
        self.direction = self.caster.status
        self.wave = 3
        self.ori_img = load("image/prince/heroLeft1.png").convert_alpha()
        self.shad_img = generateShadow( self.ori_img, color=(250,240,0,80) )
        self.fadeSnd = pygame.mixer.Sound("audio/ccSilent.wav")
        pygame.mixer.Sound("audio/prince/superPowerCast.wav").play(0)
    
    def run(self, delay, tower, heroes, canvas):
        # 1秒内连续射出三波分身王子。 create princes.
        if (not delay%20) and self.wave>0:
            for i in range(3):
                prince = pygame.sprite.Sprite()
                if i==0:
                    posY = tower.getTop(self.caster.onlayer+1)
                    prince.onlayer = self.caster.onlayer+2
                elif i==1:
                    posY = tower.getTop(self.caster.onlayer-1)
                    prince.onlayer = self.caster.onlayer
                elif i==2:
                    posY = tower.getTop(self.caster.onlayer-3)
                    prince.onlayer = self.caster.onlayer-2
                if self.direction=="left":
                    posX = tower.boundaries[1]
                    if i==1:
                        posX -= 20
                    else:
                        posX += 20
                    prince.range = tower.boundaries[0]
                    prince.speed = prince.push = -7
                    prince.image = self.ori_img
                    prince.shadow = self.shad_img
                else:
                    posX = tower.boundaries[0]
                    if i==1:
                        posX += 20
                    else:
                        posX -= 20
                    prince.range = tower.boundaries[1]
                    prince.speed = prince.push = 7
                    prince.image = flip(self.ori_img, True, False)
                    prince.shadow = flip(self.shad_img, True, False)
                prince.rect = prince.image.get_rect()
                prince.rect.left, prince.rect.bottom = posX-prince.rect.width//2, posY
                prince.rectList = []    # 残影矩形队列
                self.princeList.add( prince )
            pygame.mixer.Sound("audio/knight/superPowerCast.wav").play(0)
            self.wave -= 1
        # 移动所有已经生成的王子分身
        for prince in self.princeList:
            canvas.addTrails( [1,2,3], [22,24,28], (250,240,0), getPos(prince,0.5,random()) )
            # 处理位移
            prince.rect.left += prince.speed
            prince.rect.bottom = tower.getTop(prince.onlayer-1)
            # paint 残影
            prince.rectList.append( prince.rect.copy() )
            if len(prince.rectList)>7:
                prince.rectList.pop(0)
            # 判断出界
            if (prince.speed<0 and prince.rect.right<=prince.range) or (prince.speed>0 and prince.rect.left>=prince.range):
                canvas.addSpatters(8, [3,5,7], [18,20,22], (255,240,0), getPos(prince,0.5,0.5))
                prince.kill()
                del prince
                continue
            # 碰撞伤害
            elif not delay % DMG_FREQ:
                for m in tower.monsters:
                    if collide_mask(prince, m):
                        if m.hitted(60, prince.push, "physical")==True:
                            deadInfo = m.category
                        else:
                            deadInfo = False
                        self.caster.preyList.append( (getPos(m, 0.5,0.5), m.bldColor, 8, deadInfo, m.coin, False) )  # 无暴击
        if self.wave<=0 and len(self.princeList)<=0:
            self.fadeSnd.play(0)
            # 解绑，并删除自身
            self.caster.superPowerManager = None
            del self
        return True

    def paint(self, surface):
        for prince in self.princeList:
            surface.blit(prince.image, prince.rect)
            for rect in prince.rectList:
                surface.blit(prince.shadow, rect)

    def lift(self, dist):
        for each in self.princeList:
            each.rect.top += dist
    
    def level(self, dist):
        for each in self.princeList:
            each.rect.left += dist
    
class SuperPowerManagerWizard(SuperPowerManager):
    def __init__(self, hero):
        SuperPowerManager.__init__(self, hero)
        self.hitSnd = pygame.mixer.Sound("audio/wizard/hit.wav")
        self.lightningNum = 4
        self.lightningList = []
        self.colorSet = [(240,240,255), (200,200,255), (160,160,255), (80,80,255)]
        self.lastTgt = None     # 用于保证不会连续两次击中同一个目标

    def run(self, delay, tower, heroes, canvas):
        # 1秒内连续施放4道雷击。create lightenings.
        if (not delay%15) and self.lightningNum>0:
            # Find tgt.
            size = canvas.canvas.get_size()
            tmpM = None
            for m in tower.monsters:
                if (0<getPos(m,0,0.5)[1]<size[1]) and (m!=self.lastTgt) and (tmpM==None or m.health>=tmpM.health):
                    tmpM = m
            # In case that no suitable tgt is found:
            if tmpM==None:
                endPos = ( choice(tower.boundaries), randint(80,size[1]-80) )   # 空放时击打塔的两侧
                self.lastTgt = None     # 轮空一次雷击，将lastTgt重置为空
            else:
                endPos = getPos(tmpM, 0.5, 0.5)
            startPos = getPos(self.caster, 0.5, 0.2)
            self.lightningList.append( {"tgt":tmpM, 
                "pointlist1":self.createZapPoints(startPos, endPos, zipDent=20), 
                "pointlist2":self.createZapPoints(startPos, endPos, zipDent=40), 
                "duration":13} )
            self.lightningNum -= 1
            self.hitSnd.play(0)
        # Deal Damage.
        for lightning in self.lightningList[::-1]:
            lightning["duration"] -= 1
            endPos = lightning["pointlist1"][-1]
            # 持续溅射火花
            canvas.addSpatters(3, [2,3,4,5], [24,30,36], choice(self.colorSet), endPos, False)
            if lightning["duration"] <= 0:
                self.lightningList.remove( lightning )
                del lightning
            elif lightning["duration"]==10:
                # Explosion effect.
                if lightning["tgt"]!=None:
                    # Deal Damage.
                    if lightning["tgt"].hitted(340, choice([-7,7]), "fire")==True:
                        deadInfo = lightning["tgt"].category
                        self.lastTgt = None
                    else:
                        deadInfo = False
                        self.lastTgt = lightning["tgt"]
                        lightning["tgt"].stun(30)
                    self.caster.preyList.append( (endPos, lightning["tgt"].bldColor, 8, deadInfo, lightning["tgt"].coin, False) )  # 无暴击
        if self.lightningNum<=0 and len(self.lightningList)<=0:
            # 解绑，并删除自身
            self.caster.superPowerManager = None
            del self
        return True

    def paint(self, surface):
        for lightning in self.lightningList:
            pygame.draw.lines(surface, choice(self.colorSet), False, lightning["pointlist1"], width=3)
            pygame.draw.lines(surface, choice(self.colorSet), False, lightning["pointlist2"], width=4)

    def createZapPoints(self, startPos, endPos, zipDent=20):
        # zipDent: 闪电的折线密度，表示平均每n个像素发生一次偏折
        # 1.determine how many middle points are needed.
        lX = endPos[0]-startPos[0]
        lY = endPos[1]-startPos[1]
        length = max( abs(lX), abs(lY) )
        pNum = length//zipDent if length>zipDent else 1
        # 2.make points.
        pointList = [startPos]
        for i in range(pNum):
            # 确定第i个点的左右范围和上下范围
            rX = startPos[0]+i*lX//pNum
            rY = startPos[1]+i*lY//pNum
            pos = ( randint(rX-zipDent//2, rX+zipDent//2), randint(rY-zipDent//2, rY+zipDent//2) )
            pointList.append( pos )
        pointList.append( endPos )
        return pointList
    
class SuperPowerManagerHuntress(SuperPowerManager):
    def __init__(self, hero):
        SuperPowerManager.__init__(self, hero)
        self.direction = self.caster.status
        self.cover = 4.8*RANGE["LONG"]
        self.covering = 0
        self.ori_img = load("image/huntress/weapon.png").convert_alpha()
        self.hitSnd = pygame.mixer.Sound("audio/knight/hit.wav")
        pygame.mixer.Sound("audio/knight/superPowerCast.wav").play(0)
        # boomerang
        self.boomerang = pygame.sprite.Sprite()
        self.boomerang.image = self.ori_img
        self.boomerang.rect = self.boomerang.image.get_rect()
        self.boomerang.rect.left, self.boomerang.rect.top = getPos(self.caster, 0.2, 0.2)
        self.boomerang.speed = [-9, -2] if self.direction=="left" else [9,-2]
        self.shadList = []
        self.rectList = []
        self.rotated = 0
        self.damage = 80
    
    def run(self, delay, tower, heroes, canvas):
        canvas.addTrails( [1,2,3], [22,24,28], (250,240,0,0), getPos(self.boomerang,0.5,random()) )
        if not delay%2:
            if self.boomerang.speed[0]>0:
                self.rotated += 20
                if self.rotated>=360:
                    self.rotated = 0
            else:
                self.rotated -= 20
                if self.rotated<=-360:
                    self.rotated = 0
            self.boomerang.image = pygame.transform.rotate( self.ori_img, self.rotated )
            self.mask = pygame.mask.from_surface(self.boomerang.image)
        # 处理位移
        self.boomerang.rect.left += self.boomerang.speed[0]
        self.covering += abs(self.boomerang.speed[0])
        self.boomerang.rect.bottom += self.boomerang.speed[1]
        canvas.addTrails( [1,2,3], [16,18,20], (250,240,0), getPos(self.boomerang,random(),random()) )
        # add shad
        if not delay%2:
            self.shadList.append( generateShadow( self.boomerang.image, color=(250,240,0,120) ) )
            self.rectList.append( self.boomerang.rect.copy() )
            if len(self.rectList)>7:
                self.shadList.pop(0)
                self.rectList.pop(0)
                # 判断左右bounce
                if (self.boomerang.speed[0]<0 and self.boomerang.rect.left<=tower.boundaries[0]) or \
                    (self.boomerang.speed[0]>0 and self.boomerang.rect.right>=tower.boundaries[1]):
                    self.boomerang.speed[0] = -self.boomerang.speed[0]
                # 判断上下bounce
                elif (self.boomerang.speed[1]<0 and self.boomerang.rect.top<=self.caster.rect.top-144) or \
                    (self.boomerang.speed[1]>0 and self.boomerang.rect.bottom>=self.caster.rect.top+144):
                    self.boomerang.speed[1] = -self.boomerang.speed[1]
        # 碰撞dmg
        if not delay % (DMG_FREQ//2):
            for m in tower.monsters:
                if collide_mask(self.boomerang, m):
                    self.hitSnd.play(0)
                    if m.hitted(self.damage, self.boomerang.speed[0], "physical")==True:
                        deadInfo = m.category
                    else:
                        deadInfo = False
                        m.stun(30)
                    self.caster.preyList.append( (getPos(m, 0.5,0.5), m.bldColor, 8, deadInfo, m.coin, False) )  # 无暴击
                    #self.caster.chargeSuperPower(self.damage)
        if self.covering>=self.cover:
            self.boomerang.kill()
            canvas.addSpatters(8, [3,5,7], [20,22,24], (255,240,0), getPos(self.boomerang,0.5,0.5))
            del self.boomerang
            self.hitSnd.play(0)
            # 解绑，并删除自身
            self.caster.superPowerManager = None
            del self
            return
        return True

    def paint(self, surface):
        surface.blit(self.boomerang.image, self.boomerang.rect)
        for i in range(len(self.rectList)):
            surface.blit(self.shadList[i], self.rectList[i])

    def lift(self, dist):
        self.boomerang.rect.top += dist
        for rect in self.rectList:
            rect.top += dist
    
    def level(self, dist):
        self.boomerang.rect.left += dist
        for rect in self.rectList:
            rect.left += dist
    
class SuperPowerManagerPriest(SuperPowerManager):
    def __init__(self, hero):
        SuperPowerManager.__init__(self, hero)
        self.per_heal = 80      # 每次回复的量
        self.healCnt = 3        # 快速回复3次
        self.healRad = 260      # 治疗半径（实际计算距离，与显示的圆圈大小无关）
        pygame.mixer.Sound("audio/knight/superPowerCast.wav").play(0)
        self.ori_img = load("image/priest/cross.png").convert_alpha()
        # 金黄圣圈
        self.radius = 10
        self.width = 30
        self.iconList = []
        self.dotList = []

    def run(self, delay, tower, heroes, canvas):
        # update Halo
        self.radius += 7
        self.width = max(self.width-1, 1)
        # Add cross on the edge.
        posCaster = getPos(self.caster, 0.5, 0.5)
        if self.width>1:
            self.makeMark(posCaster, type="cross")
            self.makeMark(posCaster, type="dot")
        # Move Cross/dot.
        for cross in self.iconList[::-1]:
            cross[0].left += cross[2][0]
            cross[0].top += cross[2][1]
            cross[1] = cross[1]-1
            if cross[1]<=0:
                self.iconList.remove(cross)
                del cross
        for dot in self.dotList[::-1]:
            dot[0][0] += dot[2][0]
            dot[0][1] += dot[2][1]
            dot[1] = dot[1]-1
            if dot[1]<=0:
                self.dotList.remove(dot)
                del dot
        # Heal health.
        if (not delay % DMG_FREQ) and (self.healCnt>0):
            for hero in heroes:
                # calculate the distance between hero and self.caster.
                posHero = getPos(hero,0.5,0.5)
                distSquare = (posHero[0]-posCaster[0])**2 + (posHero[1]-posCaster[1])**2
                if distSquare**0.5<self.healRad:
                    hero.recover(self.per_heal)
            self.healCnt -= 1
        if (self.width<=1) and (self.healCnt<=0) and len(self.iconList)==0 and len(self.dotList)==0:
            self.caster.superPowerManager = None
            return

    def paint(self, surface):
        if self.width>1:
            pygame.draw.circle(
                surface, (255,255,10), getPos(self.caster,0.5,0.5), self.radius, self.width
            )
        for rect, cnt, spd in self.iconList:
            surface.blit( self.ori_img, rect )
        for pos, r, spd in self.dotList:
            pygame.draw.circle( surface, (255,255,10), pos, r )

    def makeMark(self, pos, type="cross"):
        # dandomize a position that is on the edge.
        startX = randint(pos[0]-self.radius, pos[0]+self.radius)
        distY = round( ( self.radius**2 - (startX-pos[0])**2 )**0.5 )
        startY = pos[1] + choice([1,-1])*distY
        speedX = 2 if startX>pos[0] else -2
        speedY = 2 if startY>pos[1] else -2
        # make cross/dot.
        if type=="cross":
            crect = self.ori_img.get_rect()
            crect.left = startX-crect.width//2
            crect.top = startY-crect.height//2
            self.iconList.append( [crect, 30, [speedX,speedY] ] )         # rect, cntDown, speed
        elif type=="dot":
            self.dotList.append( [[startX,startY], 18, [speedX,speedY]] )    # Pos, rad, speed
    
class SuperPowerManagerKing(SuperPowerManager):
    VServant = None # set by GameModel

    def __init__(self, hero):
        SuperPowerManager.__init__(self, hero)
        pygame.mixer.Sound("audio/knight/superPowerCast.wav").play(0)
        # if king already has one servant, kill her
        if self.caster.serv:
            while self.caster.serv.health>0:
                self.caster.serv.hitted(self.caster.serv.full, 0, "physical")
            self.caster.serv.kill()
            self.caster.serv = None
        # 前摇的动画
        self.ani_ball = pygame.sprite.Sprite()
        self.ani_ball.image = pygame.image.load("image/stg0/defenseLight.png")
        self.ani_ball.rect = self.ani_ball.image.get_rect()
        self.ani_ball.rect.left, self.ani_ball.rect.bottom = getPos(self.caster,0.5,0.5)
        self.ani_ball.onlayer = self.caster.onlayer-1
        self.ani_ball.speed = -6

    def run(self, delay, tower, heroes, canvas):
        if self.animationTime>0:
            self.animationTime -= 1
            self.ani_ball.rect.top += self.ani_ball.speed
            canvas.addTrails([6],[5],(250,240,0),getPos(self.ani_ball,0.5,0.5))
            # 下落
            if not delay%4:
                self.ani_ball.speed = min(self.ani_ball.speed+1, 5)
            # 判断层数下落
            if self.ani_ball.rect.top>=tower.heightList[str(self.ani_ball.onlayer)]:
                self.ani_ball.onlayer = max(self.ani_ball.onlayer-2, -1)
            # 相撞，立刻结束
            if pygame.sprite.spritecollide(self.ani_ball, tower.groupList[str(self.ani_ball.onlayer)], False) \
                or pygame.sprite.spritecollide(self.ani_ball, tower.groupList["0"], False):
                self.animationTime = 0
        elif self.animationTime<=0:
            servant = Servant(self.caster, self.VServant, getPos(self.ani_ball,0.5,1.5), tower.font, tower.lgg, self.ani_ball.onlayer+1)
            servant.renewCheckList(tower.groupList["0"], clear=True)
            servant.jmpSnd.play(0)      #登场音效
            canvas.addSpatters(8, [3,5,7], [28,32,36], (250,240,0), getPos(servant,0.5,0.5), False)
            heroes.append(servant)
            self.caster.serv = servant
            self.caster.superPowerManager = None
            return

    def paint(self, surface):
        surface.blit(self.ani_ball.image, self.ani_ball.rect)

