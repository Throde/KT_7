import sys
import psutil, os
import math
from random import *
import pygame
from pygame.locals import *

import enemy
import mapManager
import myHero
from plotManager import Dialogue

from database import GRAVITY, MB
from util import ImgButton, TextButton, MsgManager, ImgSwitcher
from util import getPos, drawRect

"""
    有2个透明画布（surface）在所有元素之上，一是用于画自然元素（如雪，雨）；第二个是画全屏效果和击中时的血的溅射效果。
    注：由于冒险模式和休闲模式中英雄一定是从第0层初始化的，而这两个模式的sideWall和baseWall都在tower的-1 Group中，因此不需要额外添加到hero.checkList中。
    游戏一开始，就会有fall函数将之添加到hero的checkList中。

    Model执行流程：绘图 → 平移 → 英雄动作 → 怪物动作 → 自然阻碍动作 → 触发事件 → 键盘事件 ◀
"""
inner_size = (960,720)  # 游戏内屏幕的尺寸。注意，所有model中的self.screen均为此虚拟屏幕，游戏正确窗口是self.trueScreen。
                        # 窗口原宽1080px会导致绘画卡顿；1000px略显卡顿；960十分流畅（即使在Boss战也很流畅）。
                        # 这里选取平衡点980：尽可能多的显示游戏画面；同时保证游戏画面相对流畅。
TICK = 60
DELAY = 240
SCRINT = 36     # screen interval:屏幕的移动速度，表示每多偏差36像素增加1px速度(整个屏幕720px高)
PAUSE_SEC = 30  # 短暂停时的倒计时时长（建议范围：60以内）
MONS0 = ["spider", "GiantSpider"]
MONS2 = ["CrimsonDragon", "fly", "MutatedFungus", "eagle", "iceSpirit", "FrostTitan", "assassin"]


# =================================
# Base Class for the two game
class GameModel:
    bg_size = ()          # 屏幕的宽高
    blockSize = 72
    language = 0          # 初始默认为英文，可在构造函数中设定
    fntSet = []
    stg = 1
    delay = DELAY         # 延时变量，用于在不影响游戏正常运行的情况下给图片切换增加延迟
    
    msgList = []          # 用于存储消息的列表（列表包含列表）：[ [heroName, incident, cntDown (,sticker)], ... ]
    vibration = 0         # Cnt to indicate the vibration of the screen.
    screen = None         # 保存屏幕对象的引用
    screenRect = None
    clock = None
    BG = None             # 当前关卡的环境背景
    BGRect = None
    tip = []
    translation = [0,0]
    
    nature = None         # 自然元素的画布
    spurtCanvas = None    # 击中反馈溅血的画布（比想象中的更万能！不只是能画血噢😄）
    music = None          # bgm （Sound对象）
    paused = True
    musicOn = True
    gameOn = True         # 游戏循环标志，默认为True，玩家点击退出或游戏结束时变为False
    VServant = None       # VServant用于创建servant对象，是特殊且重要的属性。由main模块的initGameData()设置。   

    def __init__(self, stg, screen, language, fntSet, monsAcc):
        self.stg = stg
        self.language = language
        self.fntSet = fntSet
        self.monsAcc = monsAcc
        # About True & Virtual Screen
        self.screen = pygame.Surface( inner_size )
        self.screenRect = self.screen.get_rect()
        self.screenRect.left = (screen.get_width()-self.screenRect.width)//2
        self.screenRect.top = 0
        self.bg_size = self.screen.get_size()
        self.trueScreen = screen
        # 右上角的控件及其他控制器
        self.menuButton = ImgButton( {"default":pygame.image.load("image/menu.png").convert_alpha()}, "default", self.fntSet[1], labelPos="btm" )
        self.quitButton = ImgButton( {"default":pygame.image.load("image/quit.png").convert_alpha()}, "default", self.fntSet[1], labelPos="btm" )
        self.musicButton = ImgButton( {True:pygame.image.load("image/BGMusic.png").convert_alpha(),
                                    False:pygame.image.load("image/BGMute.png").convert_alpha()}, self.musicOn, self.fntSet[1], labelPos="btm" )
        self.coinIcon = pygame.image.load("image/coin0.png").convert_alpha()
        # SpurtCanvas
        self.spurtCanvas = mapManager.SpurtCanvas( self.bg_size )
        enemy.Monster.spurtCanvas = self.spurtCanvas
        # Other
        self.clock = pygame.time.Clock()
        self.gameOn = True
        self.paused = True
        self.nature = None
        self.tower = None
        self.vibration = 0
        self.tip = []
        self.translation = [0,0]
        self.comment = ("","")
        myHero.SuperPowerManagerKing.VServant = self.VServant
        # statistics about player's performance
        self.stat = {}
        # end screen ----------------------
        self.restartButton = TextButton(200,60, {"default":("Retry","重试")}, "default", self.fntSet[3])
        self.retreatButton = TextButton(200,60, {"default":("Home","主菜单")}, "default", self.fntSet[3])

    def init_BG(self, stg):
        # 场景背景
        self.BG = pygame.image.load(f"image/stg{stg}/towerBG.jpg").convert_alpha()
        self.BGRect = self.BG.get_rect()
        self.BGRect.left = (self.bg_size[0]-self.BGRect.width) // 2 # 居中
        self.BGRect.bottom = self.bg_size[1]                  # 初始显示底部

    def init_stone(self, stone):
        print("Using stone: ", stone)
        self.using_stone = stone
        if stone=="loadingStone":
            for hero in self.heroes:
                hero.loading = hero.LDFull = 150
            self.msgManager.addMsg( ("Loading Stone has been activated.","填装符石已激活。"), urgent=True, 
                                    icon=pygame.image.load("image/runestone/loadingStone.png") )
        elif stone=="sacredStone":
            for hero in self.heroes:
                hero.superPowerCast += 1
            self.msgManager.addMsg( ("Sacred Stone has been activated.","神圣符石已激活。"), urgent=True, 
                                    icon=pygame.image.load("image/runestone/sacredStone.png") )
        elif stone=="bloodStone":
            # 于model类的collectHitInfo方法中实现
            self.HPSteal = 6
            self.msgManager.addMsg( ("Blood Stone has been activated.","鲜血符石已激活。"), urgent=True, 
                                    icon=pygame.image.load("image/runestone/bloodStone.png") )
        elif stone=="hopeStone":
            for hero in self.heroes:
                hero.heal_bonus = 1.5
            self.msgManager.addMsg( ("Hope Stone has been activated.","希望符石已激活。"), urgent=True, 
                                    icon=pygame.image.load("image/runestone/hopeStone.png") )
        else:
            self.msgManager.addMsg( ("No runestone is used.","未使用符石。"), urgent=True, 
                                    icon=pygame.image.load("image/runestone/voidStone.png") )
        
    def _addVib(self, dura):
        # NOTE: dura should be an even number.
        if self.vibration>dura: # 若当前的震动时长更长，则忽视本次请求
            return
        if self.vibration%2==0:
            self.vibration = dura   # 当前为偶数，则直接替换
        else:
            self.vibration = dura+1 # 否则为奇数，则需要保持奇数，才能保证最后位置恢复
    
    def _initNature(self):
        if self.stg == 1:
            self.nature = mapManager.Nature(self.bg_size, self.stg, 8, 1)
        elif self.stg == 2:
            self.nature = mapManager.Nature(self.bg_size, self.stg, 4, 0)
        elif self.stg == 3:
            self.nature = mapManager.Nature(self.bg_size, self.stg, 8, 1)
        elif self.stg == 4:
            self.nature = mapManager.Nature(self.bg_size, self.stg, 18, 0)
        elif self.stg == 5:
            self.nature = mapManager.Nature(self.bg_size, self.stg, 10, -1)
        elif self.stg == 6:
            self.nature = mapManager.Nature(self.bg_size, self.stg, 8, 1)
        elif self.stg==7:
            self.nature = mapManager.Nature(self.bg_size, self.stg, 18, 0)
    
    def _renderPause(self, pos):
        drawRect( 0, 0, self.bg_size[0], self.bg_size[1], (0,0,0,160), self.screen )
        # tip area. 
        tipRect = drawRect( self.bg_size[0]//2-240, self.bg_size[1]//2+140, 480, 90, (230,200,140,180), self.screen )
        alter = False
        if ( tipRect.left < pos[0] < tipRect.right ) and (tipRect.top < pos[1] < tipRect.bottom ):
            drawRect( self.bg_size[0]//2-235, self.bg_size[1]//2+145, 470, 80, (240,220,160,150), self.screen )
            alter = True
        topAlign = 155
        for line in self.tip:
            self.addTXT( line, 1, (30,30,30), 0, topAlign )
            topAlign += 20
        self.addTXT(["Game paused, press [ENTER] to continue.","游戏已暂停，按【回车】键继续。"],1, (255,255,255), 0,120)
        # handle controllers images and click events -----------------------------------
        if self.musicOn:
            self.musicButton.paint(self.screen, self.bg_size[0]-90, 30, pos, label=("music off","关闭音乐"))
        else:
            self.musicButton.paint(self.screen, self.bg_size[0]-90, 30, pos, label=("music on","开启音乐"))
        self.quitButton.paint(self.screen, self.bg_size[0]-150, 30, pos, label=("quit","放弃"))
            
        return alter
    
    def _endSettle(self):
        # Either paused or not, jobs to be done
        for each in self.supplyList:
            each.update(self.screen)
        for item in self.tower.allElements["dec1"]:
            if item.category=="coin":
                item.move( self.delay )
            else:
                self.specifier.moveMons( self, item, self.heroes )
        # 再一次单独绘制分配中的coins
        for item in self.tower.allElements["dec1"]:
            if item.category=="coin":
                item.paint( self.screen )
        self.nature.update(self.screen)
        
    def _collectHitInfo(self, hero, rewardee):
        for hitInfo in hero.preyList:
            self.spurtCanvas.addSpatters( hitInfo[2], [2, 3, 4], [10, 12, 14], hitInfo[1], hitInfo[0], True )
            if hitInfo[3]:     # hitted target died.
                # 给rewardee分配金币
                self.tower.addCoins( hitInfo[4], hitInfo[0], rewardee )
                # 若在怪物图鉴中
                if (hitInfo[3] in self.monsAcc):
                    # 吸血效果
                    if self.using_stone=="bloodStone" and hero==rewardee:
                        self.spurtCanvas.addSpatters( 5, [2, 3, 4], [10, 12, 14], (200,255,200), getPos(rewardee,0.5,0.4), True )
                        rewardee.recover(self.HPSteal)
                    # 尝试收集该monster: 若已收集，则返回False；否则收集成功，返回True
                    if self.monsAcc[ hitInfo[3] ].collec():
                        self.msgManager.addMsg( ("New monster collected to Collection!","新的怪物已收集至图鉴！") )
                # 计入统计数据
                self._addStat(hitInfo[3])
            # 暴击效果
            if hitInfo[5]:
                self._addVib(4)
                self.msgList.append( [hitInfo[0], "crit", 60] )
        hero.preyList.clear()
    
    # ---- show feedback of hero motion ----
    def showMsg(self):
        for msg in self.msgList:
            if msg[2] == 0: # 倒计时减为0时从列表删除
                self.msgList.remove(msg)
                continue
            else:
                if msg[1]=="crit":
                    if self.translation[1]:
                        msg[0] = (msg[0][0], msg[0][1]+self.translation[1])
                    elif self.translation[0]:
                        msg[0] = (msg[0][0]+self.translation[0], msg[0][1])
                    ctr = ( msg[0][0]-self.bg_size[0]//2, msg[0][1]-self.bg_size[1]//2-(60-msg[2]) )
                    self.addTXT( ( "Crit!", "暴击！" ), 0, (255,255,255), ctr[0], ctr[1])
                    msg[2] -= 1      # 消息显示倒计时-1
    
    def _addStat(self, name):
        # 计入统计数据
        try:
            self.stat[ name ] += 1
        except:
            self.stat[ name ] = 1
        
    def reportTask(self, task):
        for item in self.stat:
            if item==task.tgt:
                task.incProgress(self.stat[item])
    
    def addSymm(self, surface, x, y, base=None):
        '''Surface对象; x,y为正负（偏离屏幕中心点）像素值，确定了图像的中点坐标'''
        base = base if base else self.screen
        rect = surface.get_rect()
        baseW, baseH = base.get_size()
        rect.left = (baseW - rect.width) // 2 + x
        rect.top = (baseH - rect.height) // 2 + y
        base.blit( surface, rect )
        return rect   # 返回图片的位置信息以供更多操作

    def addTXT(self, txtList, fntSize, color, x, y, base=None):
        '''x,y为正负（偏离屏幕中心点）像素值，确定了文字行的左上角坐标。这样改动是为了和addSymm()函数保持一个相对统一的系统。'''
        base = base if base else self.screen
        txt = self.fntSet[fntSize][self.language].render( txtList[self.language], True, color )
        rect = txt.get_rect()
        baseW, baseH = base.get_size()
        rect.left = (baseW - rect.width) // 2 + x
        rect.top = (baseH - rect.height) // 2 + y
        base.blit( txt, rect )
        return rect

# =================================
class HeroSlot():
    def __init__(self, number, heroRef, VHero, bg_size, coinIcon, extBar=""):
        if number=="p1":    # 此处的基点坐标均为头像栏左上角
            base = (80, bg_size[1]-84)
        elif number=="p2":
            base = (bg_size[0]//2+80, bg_size[1]-84)
        self.owner = heroRef
        self.VHero = VHero
        self.slotDic = {}
        self.slotDic["brand"] = self.createSurf( base[0], base[1], (0,0), imgPath="image/heroSlot_brand.png" )
        # 分配exp时的虚拟接受surface对象
        self.image, self.rect = self.slotDic["brand"]
        self.mask = pygame.mask.from_surface(self.image)
        #self.slotDic["lvl"] = self.createSurf( base[0], base[1]+66, (84,18) )

        self.bagShad = self.createSurf(base[0]+84, base[1]+38, (45,60), color=(255,255,180,150))
        self.slotDic["bag"] = self.createSurf( base[0]+84, base[1]+18, (0,0), imgPath="image/bagBoard.png" )
        self.slotDic["coin"] = self.createSurf( base[0]+5, base[1]-24, (75,24) )
        # slot for super power
        self.slotDic["superPower"] = self.createSurf( base[0]-76, base[1], (0,0), imgPath="image/ammoCircle.png" )
        self.coinIcon = coinIcon
        self.superPowerIcon = pygame.image.load( f"image/{self.owner.name}/superPowerIcon.png" ).convert_alpha()
        self.superPowerBG = self.createSurf( base[0]-76, base[1]+54, (72,32) )
        # center Positions of all components
        self.ctrDic = {}
        for item in self.slotDic:
            rect = self.slotDic[item][1]
            self.ctrDic[item] = ( rect.left+rect.width//2-bg_size[0]//2, rect.top+rect.height//2-bg_size[1]//2 )  # 用于适配model的绘图函数addSymm所设定的中心点
        

    def paint(self, screen, effecter, addSymm, addTXT):
        nxtImg = nxtRect = bagRect = None
        for obj in self.slotDic:
            surf, rect = self.slotDic[obj]
            screen.blit( surf, rect )
            if obj=="brand":
                addSymm( self.owner.brand, self.ctrDic["brand"][0], self.ctrDic["brand"][1] )
            #elif obj=="lvl":
            #    addTXT( (f"Ammo Vol:{self.owner.arrowCnt}", f"弹药容量：{self.owner.arrowCnt}"), 0, (255,255,255), self.ctrDic["lvl"][0], self.ctrDic["lvl"][1] )
            elif obj=="bag":    # 陈列所有背包中的物品
                OFFSET = self.owner.bagpack.page*self.owner.bagpack.pageLen
                for j in range( self.owner.bagpack.getPageVol() ):     # j为0-背包每页最大容量
                    itemNum, itemImg = self.owner.bagpack.readItemByPt(j+OFFSET)
                    pos = (self.ctrDic["bag"][0]-100+j*50, self.ctrDic["bag"][1])
                    if j+OFFSET==self.owner.bagpack.bagPt and len(effecter.SSList)==0:
                        rect = self.bagShad[1]
                        rect.left = pos[0]-rect.width//2+screen.get_width()//2
                        rect.top = pos[1]-rect.height//2+screen.get_height()//2
                        addSymm( self.bagShad[0], pos[0], pos[1] )
                    bagRect = addSymm( itemImg, pos[0], pos[1] )
                    numPos = (pos[0]+10, pos[1]-20)
                    pygame.draw.circle(screen, (255,10,10), (numPos[0]+screen.get_width()//2,numPos[1]+screen.get_height()//2), 8)
                    addTXT( (str(itemNum),str(itemNum)), 1, (255,255,255), numPos[0], numPos[1] )
                effecter.doSwitch( screen )
            elif obj=="coin":
                addSymm( self.coinIcon, self.ctrDic["coin"][0]-20, self.ctrDic["coin"][1] )
                addTXT( (str(self.owner.coins), str(self.owner.coins)), 1, (255,255,255), self.ctrDic["coin"][0]+10, self.ctrDic["coin"][1] )
            elif obj=="HPBar":
                self.drawBar( screen, content="HPBar" )
            elif obj=="superPower":
                # 图标
                addSymm( self.superPowerIcon, self.ctrDic["superPower"][0], self.ctrDic["superPower"][1] )
                # 冷却进度条
                if self.owner.superPowerCnt>0:
                    time2wait = max( self.owner.superPowerCoolTime-self.owner.superPowerCnt, 0 )
                    start_angle = math.radians( 90 )
                    stop_angle = math.radians( 90+round( 360*(time2wait/self.owner.superPowerCoolTime) ) )
                    pygame.draw.arc(screen, (255,255,10,0), self.slotDic["superPower"][1], start_angle, stop_angle, width=4)
                elif self.owner.superPowerCast>0:
                    pygame.draw.arc(screen, (255,255,10,0), self.slotDic["superPower"][1], math.radians( 90 ), math.radians( 450 ), width=3)
                # 文字
                screen.blit( self.superPowerBG[0], self.superPowerBG[1] )
                addTXT( (str(self.owner.superPowerCast), str(self.owner.superPowerCast)), 1, (255,255,255), self.ctrDic["superPower"][0], self.ctrDic["superPower"][1]+24 )
                addTXT( self.owner.superPowerName, 0, (255,255,255), self.ctrDic["superPower"][0], self.ctrDic["superPower"][1]+38 )
        return (nxtImg, nxtRect, bagRect)

    def createSurf(self, left, top, size, imgPath="", color=(0,0,0,180)):
        if imgPath:
            surf = pygame.image.load( imgPath ).convert_alpha()
        else:
            surf = pygame.Surface( size ).convert_alpha()
            surf.fill( color )
        rect = surf.get_rect()
        rect.left = left
        rect.top = top
        return (surf, rect)
    
    def receiveExp(self, num, typ):
        # Coin convert to experience
        self.owner.expInc += 1
        self.VHero.increaseExp(1)
        self.VHero.alloSnd.play(0)

# ==========================================================================================================
# ------------------------------------ stage running class -------------------------------------------------
# ==========================================================================================================
class AdventureModel(GameModel):
    towerD = 10           # 单人模式为10（默认），双人模式为11
    towerH = 60
    remindedArea = []
    translation = []      # allElements的平移信息
    heroes = []           # 保存hero对象的引用；可能为1个或2个
    tomb = []
    win = False           # 标记最终结果
    curArea = 0
    # 双人模式下的特殊变量
    avgPix = 0          # 两者中的较高像素值d
    avgLayer = 0          # 两者中的较高层数
    tower = None
    plotManager = None    # 管理剧情信息
    msgStick = {}
    hostage = None

    def __init__(self, stg, heroList, screen, language, fntSet, diffi, monsDic, VHostage, tutor_on=False, stone="VOID"):
        """
        heroInfoList: 一个列表，每项是一个hero信息，每一项信息包括heroNo和该hero的keyDic。即形如：[ (heroNo1, keyDic1), (heroNo2, keyDic2) ]。可为1-2个
        monsDic: 当前stage的所有monster名及其VMons对象组成的字典
        """
        GameModel.__init__(self, stg, screen, language, fntSet, monsDic)
        self.init_BG(self.stg)
        self._initNature()

        # Initialize game canvas.
        if self.stg == 1:
            areaName = ( ("Bottom Castle","城堡底部"), ("Middle Castle","城堡中部"), ("Corridor","连廊"), ("Top Castle","城堡顶部") )
            bgColors = ( (200,160,120), (180,140,90), (170,130,80), (190,150,100) )
            bgShape = "rect"
        elif self.stg == 2:
            areaName = ( ("Outer Cave","洞穴外部"),  ("Inner Cave","洞穴内部"), ("Tunnel","矿道"), ("Spider Nest","蜘蛛巢穴") )
            bgColors = ( (190,210,210), (140,180,180), (110,140,140), (130,160,160) )
            bgShape = "circle"
        elif self.stg == 3:
            areaName = ( ("Outer Yard","墓地外围"), ("Misty Part","迷雾区域"), ("Track","小径"), ("Daunting Core","恐惧深渊") )
            bgColors = ( (170,120,190), (100,70,120), (120,70,140), (100,60,120) )
            bgShape = "circle"
        elif self.stg == 4:
            areaName = ( ("Forest Edge","雨林边缘"), ("Insect Dom","虫类领域"), ("Track","小径"), ("Tropical Dom","雨林深处") )
            bgColors = ( (110,135,75), (90,115,60), (100,125,75), (100,145,85) )
            bgShape = "circle"
        elif self.stg == 5:
            areaName = ( ("Mount Foot","雪山山麓"), ("Mountain Ridge","雪山山脊"), ("Tunnel","隧道"), ("Frozen Peak","冰封之巅") )
            bgColors = ( (200,160,120), (170,130,80), (170,130,80), (190,150,100) )
            bgShape = "circle"
        elif self.stg == 6:
            areaName = ( ("Factory Lobby","工厂前堂"), ("Iron Workshop","钢铁车间"), ("Passage","通道"), ("Storage Room","贮藏室") )
            bgColors = ( (200,160,120), (180,140,90), (170,130,80), (190,150,100) )
            bgShape = "rect"
        elif self.stg==7:
            areaName = ( ("Bottom City","都城底部"), ("Middle City","都城中部"), ("Bridge","连桥"), ("Imperial Palace","都城皇宫") )
            bgColors = ( (160,165,170), (100,110,110), (80,100,100), (90,110,110) )
            bgShape = "rect"
        
        # 难度初始化
        if diffi == 0:          # Easy
            dmgReduction = 0.7
            enemy.Monster.healthBonus = 0.7
            doubleP = 0.12
            goalieR = 0.12
        if diffi == 1:          # Normal
            dmgReduction = 1
            enemy.Monster.healthBonus = 1
            doubleP = 0.1
            goalieR = 0.15
        elif diffi == 2:        # Heroic
            dmgReduction = 1.5  # 受伤加成
            enemy.Monster.healthBonus = 1.5
            doubleP = 0.08      # chest爆率翻倍的概率
            goalieR = 0.25      # goalie概率
        self.towerH = 22

        # create the map ------------------ 🏯
        if len(heroList)>1:
            self.towerD = 11
        oriPos = ( (self.bg_size[0] - self.towerD*self.blockSize) // 2, self.bg_size[1]-self.blockSize )
        self.areaList = []
        # If there should be a tutorial start:
        if self.stg==1 and (tutor_on):
            tut_tower = mapManager.AdventureTower(oriPos, self.blockSize, self.towerD, 4, self.stg, -1, False, doubleP, self.fntSet[1], self.language, ("Tutorial","训练场"), bgColors, bgShape, self.bg_size)
            tut_tower.generateMap()
            self.areaList.append( tut_tower )
        # Determine the specialwall distribution.
        if self.stg in [1,6]:
            specialOn = (False, True, False, True)
        else:
            specialOn = (True, True, False, True)
        # Build 5 areas and link them as one big tower.
        for i in range(0,4):
            if i==2:
                sp_pos = (oriPos[0]+self.blockSize, oriPos[1])
                tower = mapManager.AdventureTower(sp_pos, self.blockSize, self.towerD-2, 4, self.stg, i, False, doubleP, self.fntSet[1], self.language, areaName[i], bgColors, bgShape, self.bg_size)
                tower.generateMap()
                tower.addNPC("merchant", heroList[0][1])
            else:
                tower = mapManager.AdventureTower(oriPos, self.blockSize, self.towerD, self.towerH+i*2, self.stg, i, specialOn[i], doubleP, self.fntSet[1], self.language, areaName[i], bgColors, bgShape, self.bg_size)
                tower.generateMap( tutor_on=tutor_on )
            self.areaList.append(tower)
        
        self.curArea = 0    # 意义为列表指针，而不是所指向的tower的area值。0即表示第一个tower。
        self.tower = self.areaList[self.curArea]
        self.hostage = None
        # create the hero -----------------🐷
        self.heroes = []
        self.tomb = []
        for each in heroList:      # 根据VHero参数信息生成hero
            hero = myHero.Hero( each[0], dmgReduction, self.fntSet[1], self.language, keyDic=each[1] )
            hero.spurtCanvas = self.spurtCanvas          # In case of injury.
            hero.slot = HeroSlot(each[2], hero, each[0], self.bg_size, self.coinIcon, extBar="LDBar")
            self.heroes.append(hero)
        self._resetHeroes(onlayer=0, side="left")
        # Initialize towers, monsters and heroes.
        for tower in self.areaList:
            # add elems of each area to the allElements and hero's checkList.
            for sup in tower.chestList:
                if sup.category == "hostage":      # 选出hostage挂在self.hostage上，并设置其VHero所需的信息
                    self.hostage = sup
                    self.hostage.hp = VHostage.hp
                    self.hostage.dmg = VHostage.dmg
                    self.hostage.cnt = VHostage.cnt
                    self.hostage.no = VHostage.no
                    self.hostage.lvl = VHostage.lvl
                    self.hostage.crit = VHostage.crit
                    self.hostage.voice = VHostage.voice
                    self.hostage.spName = VHostage.spName
                tower.allElements["dec0"].add(sup)  # 加入supply
            for key in tower.groupList:
                if key=="-2":
                    for brick in tower.groupList[key]:
                        tower.allElements["dec0"].add( brick )   # 装饰
                else:
                    for brick in tower.groupList[key]:
                        tower.allElements["dec1"].add( brick )   # 砖块
            # create monsters for each area, method.
            if (self.stg==1):
                if tower.area in [0,1,3]:
                    for i in range(2):
                        f = enemy.InfernoFire(self.bg_size)
                        tower.allElements["mons2"].add( f )
                    if tower.area == 0:
                        makeMons( 0, tower.layer, 11, 1, tower )    # 11*2=22
                        makeMons( 6, tower.layer, 6, 2, tower )     # 6*3=18
                        makeMons( -1, tower.layer, 7, 3, tower )    # 7*3=21
                        #makeMons( 10, 12, 1, 5, tower )
                    elif tower.area == 1:
                        makeMons( 0, tower.layer, 11, 1, tower )    # 11*2=22
                        makeMons( 4, tower.layer, 8, 2, tower )     # 8*3=24
                        makeMons( -1, tower.layer, 5, 3, tower )    # 5*3=15
                        makeMons( 0, tower.layer-2, 6, 4, tower )   # 6*2=12 (+6*3=18)
                    elif tower.area == 3:
                        makeMons( 10, tower.layer, 8, 2, tower )    # 8*3=24
                        makeMons( 4, tower.layer, 10, 3, tower )    # 10*3=30
                        makeMons( 0, tower.layer-2, 10, 4, tower )  # 10*2=20 (+10*3=30)
                        makeMons( 18, 20, 1, 5, tower )             # 24
                                                                    # Total Max: 280
            elif (self.stg==2):
                if tower.area in [0,1,3]:
                    c = enemy.Column(self.bg_size)
                    tower.allElements["mons1"].add( c )
                    if tower.area == 0:
                        makeMons( 0, tower.layer, 16, 1, tower )    # 16*1=16
                        makeMons( 0, tower.layer, 12, 2, tower )    # 12*2=24 (+12*2*1=24)
                        makeMons( tower.layer-6, tower.layer, 2, 3, tower )    # 2*3=6
                        #makeMons( 0, 2, 1, 5, tower )
                    elif tower.area == 1:
                        makeMons( 0, tower.layer, 11, 1, tower )    # 11*1=11
                        makeMons( 0, tower.layer, 9, 2, tower )     # 9*2=18 (+9*2*1=18)
                        makeMons( 2, tower.layer, 10, 3, tower )    # 10*3=30
                        makeMons( 2, tower.layer-2, 8, 4, tower)    # 8*2=16
                    elif tower.area == 3:
                        makeMons( 0, tower.layer, 7, 1, tower )     # 7*1=7
                        makeMons( 0, tower.layer, 9, 2, tower )     # 9*2=18 (+9*2*1=18)
                        makeMons( 2, tower.layer, 10, 3, tower )    # 10*3=30
                        makeMons( 2, tower.layer-2, 10, 4, tower)   # 10*2=20
                        makeMons( 18, 20, 1, 5, tower )             # 24
                                                                    # Total Max: 280
            elif (self.stg==3):
                if tower.area == 0:
                    makeMons( 2, tower.layer, 18, 1, tower )    # 18*1=18
                    makeMons( 2, tower.layer, 20, 2, tower )    # 20*2=40
                    #makeMons( 2, 4, 1, 5, tower )
                elif tower.area == 1:
                    makeMons( 0, tower.layer, 13, 1, tower )    # 13*1=13
                    makeMons( 2, tower.layer, 18, 2, tower )    # 18*2=36
                    makeMons( 4, tower.layer, 11, 3, tower )    # 11*4=44
                elif tower.area == 3:
                    makeMons( 0, tower.layer, 15, 1, tower )    # 15*1=15
                    makeMons( 2, tower.layer, 17, 2, tower )    # 17*2=34
                    makeMons( 4, tower.layer, 14, 3, tower )    # 14*4=56
                    makeMons( 18, 20, 1, 5, tower )             # 24
                                                                # Total Max: 280
            elif (self.stg==4):
                if tower.area == 0:
                    makeMons( 0, tower.layer-2, 8, 1, tower)    # Snake 8*2=16
                    makeMons( 6, tower.layer, 7, 2, tower )     # Slime 7*2=14
                    makeMons( 2, tower.layer, 9, 4, tower )     # Fly 8*3=24
                elif tower.area == 1:
                    makeMons( 0, tower.layer-2, 8, 1, tower)    # 8*2=16
                    makeMons( 0, tower.layer, 10, 2, tower )    # 10*2=20
                    makeMons( 2, tower.layer, 10, 3, tower )    # 10*3=30
                    makeMons( 4, tower.layer, 12, 4, tower )    # 12*3=36
                elif tower.area == 3:
                    makeMons( 2, tower.layer-4, 3, 1, tower)    # 3*2=6
                    makeMons( 0, tower.layer, 11, 2, tower )    # 11*2=22
                    makeMons( 2, tower.layer, 11, 3, tower )    # 11*3=33
                    makeMons( 4, tower.layer, 13, 4, tower )    # 13*3=39
                    makeMons( 16, 18, 1, 5, tower )             # Boss: 24
                                                                # Total Max: 280
            elif (self.stg==5):
                if tower.area == 0:
                    makeMons( 0, tower.layer, 13, 1, tower )    # 13*2=26
                    makeMons( 2, tower.layer, 10, 2, tower )    # 10*4=40
                    makeMons( 4,tower.layer, 9, 3, tower )      # 9*1=9
                    #makeMons( 6, 8, 1, 5, tower )
                elif tower.area == 1:
                    makeMons( 0, tower.layer, 12, 1, tower )    # 12*2=24
                    makeMons( 2, tower.layer, 11, 2, tower )    # 11*4=44
                    makeMons( 4, tower.layer, 7, 3, tower )     # 7*1=7
                    makeMons( 4, tower.layer, 10, 4, tower )    # 10*2=20
                elif tower.area == 3:
                    makeMons( 0, tower.layer, 11, 1, tower )    # 11*2=22
                    makeMons( 2, tower.layer, 9, 2, tower )     # 9*4=36
                    makeMons( 6,tower.layer, 6, 3, tower )      # 6*1=6
                    makeMons( 4, tower.layer, 11, 4, tower )    # 11*2=22
                    makeMons( 18, 20, 1, 5, tower )             # 24
                                                                # Total Max: 280
            elif (self.stg==6):
                if tower.area == 0:
                    makeMons( 0, tower.layer, 14, 1, tower )    # 14*2=28
                    makeMons( 2, tower.layer, 12, 2, tower )    # 12*4=48
                    #makeMons( 2, 4, 1, 5, tower )
                elif tower.area == 1:
                    makeMons( 0, tower.layer, 13, 1, tower )    # 13*2=26
                    makeMons( 2, tower.layer, 11, 2, tower )    # 11*4=44
                    makeMons( 4, tower.layer, 9, 3, tower )     # 9*2=18
                elif tower.area == 3:
                    makeMons( 0, tower.layer, 14, 1, tower )    # 14*2=28
                    makeMons( 2, tower.layer, 12, 2, tower )    # 12*4=48
                    makeMons( 4, tower.layer, 8, 3, tower )     # 8*2=16
                    makeMons( 20, 22, 1, 5, tower )             # 24
                                                                # Total Max: 280
            elif (self.stg==7):
                if tower.area in [0,1,3]:
                    pos = ( randint(tower.boundaries[0]+80, tower.boundaries[1]-80), tower.getTop("max") )
                    l = enemy.Log(self.bg_size, tower.layer-1, pos)
                    tower.allElements["mons1"].add( l )
                    if tower.area == 0:
                        #makeMons( 2, 4, 1, 5, tower )
                        makeMons( 0, tower.layer, 14, 1, tower )    # 14*3=42
                        makeMons( 0, tower.layer, 13, 2, tower )    # 13*2=26
                    elif tower.area == 1:
                        makeMons( 0, tower.layer, 13, 1, tower )    # 13*3=39
                        makeMons( 0, tower.layer, 13, 2, tower )    # 13*2=26
                        makeMons( 2, tower.layer-2, 12, 3, tower)   # 12*2=24
                    elif tower.area==3:
                        makeMons( 0, tower.layer, 15, 1, tower )    # 15*3=45
                        makeMons( 0, tower.layer, 15, 2, tower )    # 15*2=30
                        makeMons( 2, tower.layer-2, 14, 3, tower)   # 14*2=28
                        makeMons( 22, 24, 1, 5, tower )             # 24
                                                                    # Total Max: 284 (Currently players can hardly collect all)
            # randomly assign some area blocker.
            i = 0
            for minion in tower.monsters:
                i += 1
                if minion.category in MONS2:
                    tower.allElements["mons2"].add(minion)
                elif minion.category in MONS0:
                    tower.allElements["mons0"].add(minion)
                else:
                    tower.allElements["mons1"].add(minion)
                if random()<goalieR or ( i==len(tower.monsters) and len(tower.goalieList)==0 ):
                    tower.goalieList.add( minion )
                    minion.assignGoalie(1)
            # 处理特殊区域物品。要放在区域守卫的指定之后，否则如大石头、刀扇也会被指定为goalie。
            for elem in tower.elemList:
                tower.allElements["dec1"].add(elem)
                if self.stg in (2,6):   # 第二关的monsters加上障碍物大石头、蛛网；第六关的刀扇。
                    tower.monsters.add(elem)
        self.supplyList = pygame.sprite.Group()     # Store all flying supplies objects.
        
        # 章节特殊内容管理器
        if self.stg==1:
            self.specifier = Stg1Specifier(self.heroes[0], self.areaList[0], tutor_on, self.VServant)
        elif self.stg==2:
            self.specifier = Stg2Specifier()
            # 分配初始blasting Cap
            for hero in self.heroes:
                self.specifier.giveBlastingCap(hero, self.bg_size)
        elif self.stg==3:
            self.specifier = Stg3Specifier(self.bg_size)
        elif self.stg==4:
            self.specifier = Stg4Specifier()
            for tower in self.areaList:
                if tower.area!=2:
                    self.specifier.altMap(tower)
        elif self.stg==5:
            self.specifier = Stg5Specifier(self.bg_size, self.areaList)
        elif self.stg==6:
            self.specifier = Stg6Specifier()
        elif self.stg==7:
            self.specifier = Stg7Specifier(self.VServant)
            self.specifier.bind(self.areaList[3].monsters)
        # Shopping Section. -----------------------------------
        self.shopping = False
        self.buyNum = 0     # 购买物品时的序号，可取-1,0,1
        self.pause_sec = 0

        # Plot Manager & Effect Manager.
        self.plotManager = Dialogue( stg )
        self.effecter = ImgSwitcher()
        self.msgManager = MsgManager(self.fntSet[1], self.stg, mode="top")
        # using stone ---------------------------------------
        self.init_stone(stone)

        self.remindedArea = [0]    # 存储已加载过关卡对话的区域。
        for msg in self.plotManager.getPre(self.areaList[self.curArea].area):
            self.msgManager.addMsg( msg, type="dlg" )
        self.endCnt = -1    # -1表示正常运行

    def go(self, horns, heroBook, stgManager, diffi, vol, task):
        if self.stg in (2,3):
            pygame.mixer.music.load(f"audio/stg2-3BG.wav")
        else:
            pygame.mixer.music.load(f"audio/stg{self.stg}BG.wav")  # Play bgm
        pygame.mixer.music.set_volume(vol/100)
        pygame.mixer.music.play(loops=-1)
        self.screen.fill( (0, 0, 0) )
        self.tip = choice( self.plotManager.tips )
        self.translation = [0,0]
        # Paint two sideBoards
        sideBoard = pygame.image.load("image/sideBoard.png")
        sideBoardRect = sideBoard.get_rect()
        sideBoardRect.top = 0
        sideBoardRect.right = self.screenRect.left
        self.trueScreen.blit(sideBoard, sideBoardRect)
        sideBoardRect.left = self.screenRect.left + self.screenRect.width -1
        self.trueScreen.blit(sideBoard, sideBoardRect)
        pygame.display.flip()
        #self.heroes[0].bagpack.incItem("simpleArmor", 2)
        #self.heroes[0].bagpack.incItem("missleGun", 3)

        while self.gameOn:
            
            # Repaint & translate all elements.
            self.screen.blit( self.BG, self.BGRect )
            # Repaint this tower and situate heroes.
            self.tower.paint(self.screen, heroes=self.heroes)
            # Repaint Natural Impediments of the stage.
            self.specifier.paint(self.screen)
            self.spurtCanvas.updateHalo(self.screen)
            
            pos = pygame.mouse.get_pos()
            pos = (pos[0]-self.screenRect.left, pos[1])     # 从实际窗口转到虚拟窗口的偏差
            # draw hero status info.
            for hero in self.heroes:
                hero.drawHeads( self.screen )
                if hero.category == "hero":
                    nxtImg, nxtRect, bagRect = hero.slot.paint(self.screen, self.effecter, self.addSymm, self.addTXT)
            
            # If not paused, 以下是 Action Layer ===============================================
            if not self.paused:
                
                # Check if the screen needs to be adjusted.
                # level:
                gap = ( self.bg_size[0] - (self.tower.boundaries[0]+self.tower.boundaries[1]) ) //2
                if not gap:
                    self.translation[0] = 0
                else:
                    self.translation[0] = max(gap//8, 1) if gap>0 else min(gap//8+1, -1)
                # lift:
                gap = self.bg_size[1]//2 - self.avgPix  # 中线减去英雄水平线之差
                if (self.tower.layer>0) and ( (self.tower.getTop("min")+self.blockSize<self.bg_size[1] and gap<0) or (self.tower.getTop("max")>0 and gap>0) ):
                    # 在长塔的情况下，若已经触底还想下降，或已经到顶还要上升，都应阻止
                    self.translation[1] = 0
                else:
                    self.translation[1] = gap//SCRINT if gap>=0 else gap//SCRINT+1
                
                self.tower.lift(self.translation[1])
                # lift bg paper
                if self.translation[1]>0 and self.BGRect.top<0:
                    self.BGRect.top += 1
                elif self.translation[1]<0 and self.BGRect.bottom>self.bg_size[1]:
                    self.BGRect.top -= 1
                
                # 所有tower都应该水平移动，以保持相对水平位置，避免造成出入口处的冲突。
                for tower in self.areaList:
                    tower.level(self.translation[0])
                self.spurtCanvas.level(self.translation[0])
                self.spurtCanvas.lift(self.translation[1])
                for each in self.supplyList:
                    each.level(self.translation[0])
                    each.lift(self.translation[1])

                # check hero's jump & fall, msg.
                self.avgPix = self.avgLayer = valid_hero = 0
                for hero in self.heroes:
                    hero.level(self.translation[0])
                    hero.lift(self.translation[1])
                    # 若处于跳跃状态，则执行跳跃函数
                    if hero.k1 > 0:
                        hero.jump( self.tower.getTop(hero.onlayer+1) )
                    # 否则，执行掉落函数
                    else:
                        fallChecks = self.tower.groupList[str(hero.onlayer-1)]
                        hero.fall(self.tower.getTop(hero.onlayer-1), fallChecks, self.tower.heightList, GRAVITY)
                    # decide the image of Hero
                    # key.get_pressed(): get the list including the boolean status of all keys
                    vib = hero.checkImg( self.delay, self.tower, self.heroes, pygame.key.get_pressed(), self.spurtCanvas )
                    self._addVib(vib)
                    if hero.category != "servant":
                        self.avgPix += getPos(hero, 0.5, 0.5)[1]
                        self.avgLayer += hero.onlayer
                        valid_hero += 1
                    # 这里特殊地处理follower。执行完后直接结束循环，因为follower不显示获得exp和物品。
                    if hero.category == "follower":
                        win = hero.decideAction(self.delay, self.tower.heightList, self.tower.monsters, self.tower.porter)
                        if win:
                            self.endGame(True, inst=True)

                        continue
                    elif hero.category == "servant":
                        hero.decideAction(self.delay, self.tower, self.spurtCanvas)
                        self._collectHitInfo(hero, hero.master)
                    else:
                        # 从hero的preyList信息列表中取击中信息。
                        self._collectHitInfo(hero, hero)
                        # 从hero的eventList事件列表中取事件信息，并将these newly opened chests加入self.msgList中。
                        for item in hero.eventList:
                            if item=="chest":
                                # 计入统计数据
                                self._addStat("chest")
                            elif item!="coin":
                                self.supplyList.add( item )
                                self.spurtCanvas.addSpatters(8, (2,3,4), (20,22,24), (10,240,10), getPos(hero,0.5,0.4) )
                                if item.name=="ammo":
                                    self.msgManager.addMsg( ("Your ammo capacity gains +1 !","你的弹药容量+1！"), urgent=True )
                                else:
                                    self.msgManager.addMsg( hero.bagpack.itemDic[item.name], type="item", urgent=True )
                            else:
                                self.spurtCanvas.addSpatters(3, (1,2,3), (16,18,20), (255,255,0), getPos(hero,0.5,0.4) )
                        hero.eventList.clear()
                        hero.reload( self.delay, self.spurtCanvas )
                valid_hero = max(valid_hero, 1)
                self.avgPix = self.avgPix//valid_hero
                self.avgLayer = self.avgLayer//valid_hero
                
                for item in self.tower.allElements["mons0"]:
                    self.specifier.moveMons(self, item, self.heroes)
                for item in self.tower.allElements["mons1"]:
                    # 分关卡处理所有的敌人（自然阻碍和怪兽）。由于是覆盖的函数，需要给self参数。
                    self.specifier.moveMons( self, item, self.heroes )
                    # 处理投掷物：投掷物的move函数将返回三种情况：1.返回False，表示未命中；2.返回包含两个元素的元组，含义分别为投掷物的方向“right”或“left”，以及投掷物击中的坐标（x，y）；
                    # 3.返回包含三个元素的元组，第三个元组为标志命中目标是否死亡。
                    if item.category=="bullet":
                        item.move(self.tower.monsters, self.spurtCanvas, self.bg_size)
                    elif item.category=="bulletPlus":
                        item.move(self.delay, self.tower.monsters, self.spurtCanvas, self.bg_size)
                    elif item.category == "tracker":
                        item.move(self.spurtCanvas)
                for item in self.tower.allElements["mons2"]:
                    self.specifier.moveMons( self, item, self.heroes )
                for item in self.tower.allElements["dec1"]:
                    if item.category=="coin":
                        item.move( self.delay )
                    else:
                        self.specifier.moveMons( self, item, self.heroes )
                
                # check big events.
                # 事件1：区域通过。有的怪物（如戈仑石人）存在死亡延迟，故在杀死怪物的时候再判断不准确，需时刻侦听。
                if self.tower.area<=len(self.areaList) and len(self.tower.goalieList)==0 and self.tower.porter.locked:
                    self.tower.porter.unlock()
                    self.msgManager.addMsg( ("The Area is unblocked!","区域封锁已解除！") )
                # 输赢事件。
                if self.checkFailure():     # 检查所有英雄的情况
                    self.endGame(False, inst=False)
                self._checkEnd()
                
                if self.stg==1:
                    if len(self.heroes)>0:
                        self.specifier.progressTutor( self.delay, self.heroes[0], self.tower, self.spurtCanvas )
                elif self.stg==3:
                    self.specifier.addSkeleton(self.delay, self.tower, self.avgLayer)
                    self.specifier.updateMist(self.delay, self.tower, self.heroes, self.curArea)
                elif self.stg==4:
                    if hasattr(self.tower,"hut_list"):
                        for hut in self.tower.hut_list:
                            hut.chim(self.spurtCanvas)
                    if self.tower.area!=2:
                        self.specifier.generateSprout(self.delay, self.tower, self.bg_size)
                elif self.stg==5:
                    self.specifier.updateBlizzard(self.heroes, self.nature.wind, self.spurtCanvas, self.curArea)
                    self.specifier.checkTotem(self.tower, self.msgManager)
                elif self.stg==7:
                    # 检查输赢
                    if self.specifier.checkWin():
                        self.endGame( True, inst=False )
                    # 增援侍从
                    serv = self.specifier.reinforce(self.heroes[0], self.tower, self.spurtCanvas, self.msgManager)
                    if serv:
                        self.heroes.append(serv)
                    # 管理滚木
                    self.specifier.manageLogs(self.tower, self.bg_size)

                # General actions that should be done when not paused.
                if self.vibration > 0:
                    if (self.vibration % 2 == 0):
                        flunc = 4                        
                    else:
                        flunc = -4
                    self.tower.lift(flunc)
                    self.tower.level(flunc)
                    for hero in self.heroes:
                        hero.lift(flunc)
                        hero.level(flunc)
                    self.vibration -= 1
                                
            # When Paused
            else:
                # 暂停方式一：倒计时，自动计算
                if self.pause_sec>0:
                    self.pause_sec -= 1
                    # 若倒计时结束，终止暂停状态
                    if self.pause_sec==0:
                        self.paused= False
                    # 计算透明度alpha值
                    alpha = max( min(PAUSE_SEC*4, 255) - (PAUSE_SEC-self.pause_sec)*3, 0 )
                    drawRect( 0, 0, self.bg_size[0], self.bg_size[1], (0,0,0,alpha), self.screen )
                # 暂停方式二：彻底暂停，等待玩家唤醒
                else:
                    alter = self._renderPause(pos)
                    # Shopping screen.
                    if self.shopping:
                        self.tower.merchant.renderWindow(
                            self.screen, self.stg, self.buyNum, self.heroes[0], self.plotManager.propExplan, 
                            self.addSymm, self.addTXT, self.spurtCanvas
                        )
            
            # Either paused or not, jobs to be done
            for each in self.supplyList:
                each.update(self.screen)
            self.spurtCanvas.update(self.screen)
            self.nature.update(self.screen)
            # Banner.
            bannerTuple = self._renderBanner(pos)
            menu = bannerTuple[-1]
            # Show Message.
            self.msgManager.run()
            self.msgManager.paint(self.screen)
            self.showMsg()

            # 一次性的鼠标点击或按键事件
            for event in pygame.event.get():
                if ( event.type == QUIT ):
                    pygame.quit()
                    sys.exit()
                elif ( event.type == KEYDOWN ):
                    if not self.paused:
                        for hero in self.heroes:
                            if hero.category != "hero" or hero.health<=0:
                                continue
                            if ( event.key == hero.keyDic["shootKey"] ):    # 射击
                                hero.shoot( self.tower, self.spurtCanvas )
                            elif ( event.key == hero.keyDic["jumpKey"] ):   # 跳跃
                                # 若在下一porter处按跳跃键，且封锁已解除，则进入下一区域
                                if (hero.onlayer >= self.tower.layer) and self.tower.porter and ( pygame.sprite.collide_mask(hero, self.tower.porter) ) \
                                    and (not self.tower.porter.locked) and self.tower.porter.category=="door":
                                    self._shiftTower( to=1 )
                                    # 若进入的是new area，则将区域dialogue加入消息列表。
                                    if self.curArea not in self.remindedArea:
                                        self.remindedArea.append(self.curArea)
                                        for msg in self.plotManager.getPre(self.areaList[self.curArea].area):
                                            self.msgManager.addMsg( msg, type="dlg" )
                                # 否则，在上一porter处按跳跃键，则返回上一区域
                                elif (hero.onlayer<=0) and self.tower.backporter and ( pygame.sprite.collide_mask(hero, self.tower.backporter) ) \
                                    and (not self.tower.backporter.locked):
                                    self._shiftTower( to=-1 )
                                # 否则，在人质处按跳跃键，招募人质
                                elif self.hostage and pygame.sprite.collide_mask(hero, self.hostage):
                                    # 将hostage变为一个hero并加入heroes队列（插入队首）。
                                    pos = (self.hostage.rect.left, self.hostage.rect.bottom)
                                    follower = myHero.Follower(pos, self.hostage, hero, self.fntSet[1], self.language)
                                    # RENEW CHECKLIST
                                    follower.renewCheckList(self.tower.groupList["0"], clear=True)
                                    follower.renewCheckList(self.tower.chestList)
                                    follower.renewCheckList(self.tower.elemList)
                                    self.heroes.insert(0, follower)
                                    # 已经被带起，将原来的hostage删除。
                                    self.hostage.kill()
                                    self.hostage = None
                                # 否则，是正常的跳跃行为
                                else:
                                    if ( hero.k1 > 0 ) and ( hero.k2 == 0 ):
                                        hero.k2 = 1
                                    elif not hero.trapper and hero.aground and ( hero.k1 == 0 ):
                                        hero.k1 = 1
                            elif ( event.key == hero.keyDic["superKey"] ):  # 超级技能
                                hero.castSuperPower(self.spurtCanvas)
                            elif ( event.key == hero.keyDic["itemKey"] ):   # 使用背包物品
                                ret = hero.useItem( self.spurtCanvas )
                                if ret:
                                    self.msgManager.addMsg( ret, urgent=True )
                            elif ( event.key == hero.keyDic["downKey"] ):   # 下跳
                                if not hero.oneInEffect("copter"):
                                    hero.shiftLayer(-2, self.tower.heightList)
                                    hero.aground = False
                            elif ( event.key == hero.keyDic["bagKey"] ) and len(self.effecter.SSList)==0:     # 切换背包物品
                                hero.bagpack.shiftItem()
                                self.effecter.addSwitch(hero.slot.bagShad[0], hero.slot.bagShad[1], 1, 50, 0)
                    # If paused & shopping.
                    elif self.shopping:
                        for hero in self.heroes:
                            if hero.category != "hero":
                                continue
                            if ( event.key == hero.keyDic["leftKey"] ):
                                self.buyNum = max(self.buyNum-1, -1)
                            elif ( event.key == hero.keyDic["rightKey"] ):
                                self.buyNum = min(self.buyNum+1, 1)
                            elif ( event.key == hero.keyDic["itemKey"] ):
                                res = self.tower.merchant.sell(self.buyNum, hero, self.spurtCanvas )
                                if res:
                                    self.supplyList.add( res )
                                else:
                                    self.msgManager.addMsg( ("You don't have enough coins.","你的金币数量不足。"), urgent=True )
                            elif ( event.key == hero.keyDic["bagKey"] ):
                                if hero.coins>=self.tower.merchant.refreshCost:  # coin足够
                                    hero.coins -= self.tower.merchant.refreshCost
                                    for key in self.tower.merchant.goods:
                                        self.tower.merchant.goods[key] = None
                                    self.tower.merchant.updateGoods(self.stg, hero, canvas=self.spurtCanvas)
                                else:
                                    self.msgManager.addMsg( ("You don't have enough coins.","你的金币数量不足。"), urgent=True )
                    # other: merely paused.
                    if ( event.key == pygame.K_RETURN ):
                        # 在非等待切换地图时，才能响应暂停操作
                        if self.pause_sec==0:
                            self.paused = not self.paused
                            self.tip = choice( self.plotManager.tips )
                            # 检测是否与商人交互
                            if self.tower.merchant and pygame.sprite.collide_mask(self.heroes[0], self.tower.merchant):
                                self.shopping = self.paused
                                if self.paused:
                                    self.tower.merchant.helloSnd.play(0)
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    if ( menu.left < pos[0] < menu.right ) and ( menu.top < pos[1] < menu.bottom ):
                        self.paused = not self.paused
                        self.tip = choice( self.plotManager.tips )
                        # 检测是否与商人交互
                        if self.tower.merchant and pygame.sprite.collide_mask(self.heroes[0], self.tower.merchant):
                            self.shopping = self.paused
                            if self.paused:
                                self.tower.merchant.helloSnd.play(0)
                    if self.paused:
                        if alter:
                            self.tip = choice( self.plotManager.tips )
                        elif self.quitButton.hover_on(pos):  # quit game
                            self.comment = ("You give up the adventure.","你放弃了本次冒险。")
                            self.endGame(False, inst=True)
                        elif self.musicButton.hover_on(pos):
                            if self.musicOn:
                                pygame.mixer.music.fadeout(1000)
                                self.musicOn = False
                            else:
                                pygame.mixer.music.play(loops=-1)
                                self.musicOn = True
                            self.musicButton.changeKey(self.musicOn)


            self.trueScreen.blit(self.screen, self.screenRect)
            pygame.display.flip()   # from buffer area load the pic to the screen
            self.delay = (self.delay+1) % DELAY
            self.clock.tick(TICK)
        
        # ===================================================================
        # Game Loop ended，Render Stage Over Screen
        self.reportTask(task)
        self.msgManager.addMsg( (f"TASK: {task.descript[0]} ({task.progress}/{task.num})",f"任务：{task.descript[1]} ({task.progress}/{task.num})"), urgent=True )

        if self.win:
            horns[0].play(0)
            if self.stg<len(heroBook.accList) and not heroBook.accList[self.stg]:
                heroBook.accList[self.stg] = True    # win, 下一关的英雄角色解锁 ✔herobook
                heroBook.heroList[self.stg].acc = True
            # 修改关卡通过信息
            stgManager.renewRec(self.stg-1, diffi, gameMod=0)
            if self.stg<7:
                newHero = heroBook.heroList[self.stg]
                self.comment = (f"New hero {newHero.name[0]} is now accessible.",f"新英雄 {newHero.name[1]} 已解锁。")
        else:
            horns[1].play(0)

        while True:
            # Repaint & translate all elements.
            self.screen.blit( self.BG, self.BGRect )
            # Repaint this tower and situate heroes.
            self.tower.paint(self.screen, heroes=self.heroes)
            # Repaint Natural Impediments of the stage.
            self.specifier.paint(self.screen)
            
            pos = pygame.mouse.get_pos()
            pos = (pos[0]-self.screenRect.left, pos[1])     # 从实际窗口转到虚拟窗口的修正
            # Conclusion panel.
            drawRect( 0, 0, self.bg_size[0], self.bg_size[1], stgManager.themeColor[self.stg], self.screen )
            drawRect( 0, 160, self.bg_size[0], 70, (0,0,0,40), self.screen )
            # 绘制其他信息
            if self.win:
                if self.stg<7:
                    self.addSymm(newHero.image, 0, 20)
                    self.addTXT( self.comment, 2, (255,255,255), 0, -180)
                self.addTXT( ("Chapter Completed!","章节完成！"), 3, (255,255,255), 0, -150)
            else:
                self.addTXT( self.comment, 2, (255,255,255), 0, -180)
                self.addTXT( ("Mission Failed.","任务失败。"), 3, (255,255,255), 0, -150)
            
            # Other necessary infos.
            settled = True      # 结算标志。为False表示仍在结算exp中。
            # hero status info. # 不论胜负，都计算经验值获得。
            for hero in self.heroes+self.tomb:
                hero.drawHeads( self.screen )
                if hero.category != "hero":
                    continue
                nxtImg, nxtRect, bagRect = hero.slot.paint(self.screen, self.effecter, self.addSymm, self.addTXT)
                # level and exp.
                vHero = heroBook.heroList[hero.heroNo]  # 从heroBook的列表中取VHero类型
                # 结算钻石
                if hero.gems>0:
                    vHero.addGem(hero.gems)
                    hero.gems = 0
                # 结算金币-》经验
                brandRect = hero.slot.slotDic["brand"][1]
                bar = heroBook.drawExp( self.screen, brandRect.right+1, brandRect.top+1, int(vHero.exp), int(vHero.nxtLvl), 1, height=16 )
                expTXT = ( "EXP +"+str(hero.expInc),"经验+"+str(hero.expInc) )
                self.addTXT( expTXT, 0, (40,20,20), bar.left+bar.width//2-self.bg_size[0]//2, bar.top+bar.height//2-self.bg_size[1]//2 )
                if hero.coins>=2:
                    # 存在hero的coin数仍然很多，需要继续结算
                    settled = False
                    coinRect = hero.slot.slotDic["coin"][1]
                    # 每次结算2枚coin，但是只增加1点exp
                    hero.coins -= 2
                    self.tower.addCoins(1, [coinRect.left, coinRect.top], hero.slot, cList=[8,9,10])
            
            # 结算完成，允许下一步操作
            if settled:
                self.restartButton.paint( self.screen, self.bg_size[0]//2-110, 530, pos)
                self.retreatButton.paint( self.screen, self.bg_size[0]//2+110, 530, pos)
            self._endSettle()

            for event in pygame.event.get():  # 必不可少的部分，否则事件响应会崩溃
                if ( event.type == QUIT ):
                    pygame.quit()
                    sys.exit()
                elif ( event.type == pygame.MOUSEBUTTONUP ):
                    if self.restartButton.hover_on(pos):
                        horns[2].play(0)
                        return True     # 返回True，则main中的循环继续
                    elif self.retreatButton.hover_on(pos):
                        horns[2].play(0)
                        return False    # 返回False，则结束main中的循环
            
            # Show Message.
            self.msgManager.run()
            self.msgManager.paint(self.screen)

            self.trueScreen.blit(self.screen, self.screenRect)
            pygame.display.flip()   # from buffer area load the pic to the screen
            self.clock.tick(TICK)

    def checkFailure(self): 
        '''检查任何英雄的死亡情况。check whether game fails when a hero dies'''
        for hero in self.heroes[::-1]:
            if hero.category=="hero":
                if not hero.doom:
                    continue
                hero.doom = False
                # 检查列表中是否还有另一个hero
                for each in self.heroes:
                    if each.category=="hero" and each!=hero:   # 发现存活的其他hero，游戏继续。
                        self.heroes.remove(hero)        # 死亡的hero加入tomb，以供计算经验
                        self.tomb.append(hero)
                        self.tower.allElements["mons1"].add(hero)   # 同时加入塔楼中，以继续绘制和level & lift
                        return False
                self.comment = ("You died.","你已阵亡。")
                return True         # 执行到此处，说明游戏失败
            elif hero.category=="follower" and hero.doom:      # 要营救的对象死亡，结束游戏，但继续留在heroes中。
                self.comment = ("The protege died.","保护对象已阵亡。")
                return True
            else:
                if hero.health<=0:
                    self.heroes.remove(hero)
                    del hero
                    return False
    
    def endGame(self, bool, inst=True):
        '''end game with bool (win-True, lose-False)'''
        self.win = bool
        if inst:
            pygame.mixer.music.fadeout(1000)
            self.msgManager.clear()
            self.gameOn = False
        elif self.endCnt<0:    # 只可触发一次：正常为-1
            self.endCnt = 60
        
    def _checkEnd(self):
        if self.endCnt>0:
            self.endCnt -= 1
            if self.endCnt==0:
                pygame.mixer.music.fadeout(1000)
                self.msgManager.clear()
                self.gameOn = False

    def _resetHeroes(self, onlayer=0, side="left"):
        # 左下的情况：默认值
        # 右上的情况：onlayer=self.tower.layer, side="right"
        for hero in self.heroes:
            # Relocate hero
            hero.onlayer = onlayer
            hero.resetPosition( self.tower, layer=onlayer-1, side=side )
            # RENEW CHECKLIST
            hero.renewCheckList(self.tower.groupList["0"], clear=True)
            hero.renewCheckList(self.tower.chestList)
            hero.renewCheckList(self.tower.elemList)

    def _shiftTower(self, to=1):
        for hero in self.heroes:
            hero.shiftTower(self.tower, oper="suspend")
        self.curArea += to
        self.tower = self.areaList[self.curArea]
        if to==1:
            self._resetHeroes(onlayer=0, side="left")
        elif to==-1:
            self._resetHeroes(onlayer=self.tower.layer, side="right")
        self.paused = True
        self.pause_sec = PAUSE_SEC
        # 告知新塔楼，调整生效中的道具状态
        for hero in self.heroes:
            hero.shiftTower(self.tower, oper="rejoin")

    # ---- clear all elements in the model ----
    def clearAll(self):
        #print("高峰内存占用",psutil.Process(os.getpid()).memory_info().rss)
        for tower in self.areaList:
            #print(sys.getrefcount(tower))
            for grp in tower.allElements:
                for each in tower.allElements[grp]:
                    each.kill()
                    del each
        del self.tower, self.areaList
        #print(">删除塔楼后",psutil.Process(os.getpid()).memory_info().rss)

    # --- paint upper banner (contains 4 sections) ---
    def _renderBanner(self, pos):
        # paint 4 background sections and get their rect.
        sect1 = drawRect(0, 10, 140, 40, (0,0,0,180), self.screen)    # Goalie Information.
        sect2 = drawRect(0, 60, 70, 40, (0,0,0,180), self.screen)  # Area Name.
        sect3 = drawRect(self.bg_size[0]-60, 10, 60, 40, (0,0,0,180), self.screen)  # Pause.
        # give banner info.
        ctr = (sect1.left+sect1.width//2-self.bg_size[0]//2, sect1.top+sect1.height//2-self.bg_size[1]//2)  # 更改为中心坐标系统的中心点参数
        self.addTXT( self.tower.name, 2, (255,255,255), ctr[0], ctr[1] )

        ctr = (sect2.left+sect2.width//2-self.bg_size[0]//2, sect2.top+sect2.height//2-self.bg_size[1]//2)
        self.addSymm( pygame.image.load("image/goalie.png").convert_alpha(), ctr[0], ctr[1] )
        self.addTXT( ( str(len(self.tower.goalieList)), str(len(self.tower.goalieList)) ), 2, (255,255,255), ctr[0], ctr[1])

        ctr = (sect3.left+sect3.width//2, sect3.top+sect3.height//2)
        if not self.paused:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("pause","暂停"))
        else:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("play","继续"))
        
        return (sect1, sect2, sect3)


# ==========================================================================================================
# ------------------------------------ stage running class -------------------------------------------------
# ==========================================================================================================
class EndlessModel(GameModel):
    towerD = 11
    msgStick = None
    msgList = []
    keyDic = []
    monsters = None

    hero = None
    tower = None
    nature = None
    plotManager = None
    monsBroc = {      # mons生成手册：记录每个stg生成哪些小mons。
        1: (1,2,3,4),
        2: (1,2,3,4),
        3: (1,2,3),
        4: (1,2,3,4),
        5: (1,2,3,4),
        6: (1,2,3),
        7: (1,2,3)
    }
    # 特别party波：       超哥   巨投   幽灵   甲虫   飞鹰    机枪   刺客
    specialBroc = [ (), (2,8), (3,6), (3,6), (4,8), (4,8), (2,8), (3,8) ]
    # 每项为(精英率，体力加成率)。超出最大的均以最大为准。
    phase = { 1:(0,1), 2:(0.1,1.1), 3:(0.2,1.1), 4:(0.3,1.1), 5:(0.4,1.1), 6:(0.4,1.2), 7:(0.5,1.2), 
        8:(0.6,1.2), 9:(0.6,1.3), 10:(0.6,1.4), 11:(0.6,1.5), 12:(0.7,1.5), 13:(0.8,1.5), 14:(0.8,1.6),
        15:(0.9,1.6), 16:(1,1.6) }
    wave = 0
    cntDown = 0
    cycle = 5   # waves per chapter

    def __init__(self, stg, keyDic, screen, language, fntSet, monsDic, VHero, stone="VOID"):
        GameModel.__init__(self, 0, screen, language, fntSet, monsDic)
        self.init_BG(2)
        mapManager.Statue.spurtCanvas = self.spurtCanvas

        # Other Settings
        self.keyDic = keyDic
        self.alertSnd = pygame.mixer.Sound("audio/alert.wav")
        self.rebuildColor = (20,50,20)
        bgColors = ( (170,190,170), (150,180,150), (110,130,110), (100,120,100) )
        bgShape = "rect"
        self.effecter = ImgSwitcher()
        self.msgManager = MsgManager(self.fntSet[1], 2, mode="top")

        enemy.Monster.healthBonus = 1
        self.wave = 0
        self.cntDown = 5
        self.status = "alarm"     # 4 values: alarm/前奏倒计时 -> create/生成怪物 -> battle/等待战斗完成 -> shop/购买 ->循环
        self.tower = mapManager.EndlessTower(self.bg_size, self.blockSize, self.towerD, stg, self.fntSet[1], self.language, bgColors, bgShape)
        self.tower.generateMap()
        myHero.DefenseTower.siteWalls = self.tower.siteWalls
        # create the hero
        self.hero = myHero.Hero(VHero, 1, self.fntSet[1], self.language, keyDic=self.keyDic)
        self.hero.resetPosition( self.tower, tag="p1", layer=self.tower.extLayer-1, side="center" )
        self.hero.onlayer = self.tower.extLayer
        self.hero.spurtCanvas = self.spurtCanvas
        self.hero.slot = HeroSlot("p1", self.hero, VHero, self.bg_size, self.coinIcon, extBar="LDBar")
        self.hero.renewCheckList(self.tower.groupList["0"])
        self.heroes = [self.hero]

        self.tower.merchant.initWindow(self.hero.keyDic)
        self.fitTower()
        # Add Pool
        self.pool = mapManager.Pool(self.tower.bg_size, self.tower.blockSize*2-36, self.tower.boundaries)
        self.tower.allElements["dec1"].add(self.pool)
        self.heroes.insert(0, self.tower.statue)
        # create servant
        initPos = [choice(self.tower.boundaries), self.tower.getTop(self.tower.extLayer+1)]
        servant = myHero.Servant(self.hero, self.VServant, initPos, self.fntSet[1], self.language, self.hero.onlayer)
        servant.renewCheckList(self.tower.groupList["0"])
        self.heroes.insert(0, servant)
        
        self.supplyList = pygame.sprite.Group()     # Store all flying supplies objects.
        # Shopping Section. -----------------------------------
        self.shopping = False
        self.buyNum = 0     # 购买物品时的序号，可取-1,0,1

        self.stg = stg
        self.bondSpecif()
        self._initNature()
        self.endCnt = -1   # -1表示游戏结束条件未触发 # 结束后的动画时间默认为60

        # using stone
        self.init_stone(stone)
        self.msgManager.addMsg( ("Protect the King's Statue! ... and yourself.","保护国王石像！……也保护好自己。") )

    def go(self, horns, heroBook, stgManager, setManager, vol, task):
        pygame.mixer.music.load("audio/stg7BG.wav")    # Play bgm
        pygame.mixer.music.set_volume(vol/100)
        pygame.mixer.music.play(loops=-1)
        self.tip = choice( self.plotManager.tips )
        self.screen.fill( (0, 0, 0) )
        # Paint two sideBoards
        sideBoard = pygame.image.load("image/sideBoard.png").convert_alpha()
        sideBoardRect = sideBoard.get_rect()
        sideBoardRect.top = 0
        sideBoardRect.right = self.screenRect.left
        self.trueScreen.blit(sideBoard, sideBoardRect)
        sideBoardRect.left = self.screenRect.left + self.screenRect.width-1
        self.trueScreen.blit(sideBoard, sideBoardRect)
        pygame.display.flip()
        # make a queue that stores coming monsters. format: [ballObj, monsObj]
        self.monsQue = []
        # Give one defense tower.
        self.hero.bagpack.incItem("defenseTower", 1)

        while self.gameOn:
            
            # repaint all elements
            self.screen.blit( self.BG, self.BGRect )
            self.tower.paint(self.screen, heroes=self.heroes)
            self.specifier.paint(self.screen)
            self.spurtCanvas.updateHalo(self.screen)
            for ball, pair in self.monsQue:
                self.screen.blit(ball.image, ball.rect)

            pos = pygame.mouse.get_pos()
            pos = (pos[0]-self.screenRect.left, pos[1])     # 从实际窗口转到虚拟窗口的修正
            # draw hero status info
            for hero in self.heroes:
                hero.drawHeads(self.screen)
            self.hero.slot.paint(self.screen, self.effecter, self.addSymm, self.addTXT)

            if not self.paused:
                
                # move all if the screen need to be adjusted.
                translation = 0
                if self.hero.rect.left<self.tower.boundaries[0]:
                    if self.tower.boundaries[0]<self.blockSize*3:
                        translation = 2
                elif self.hero.rect.right>self.tower.boundaries[1]:
                    if self.tower.boundaries[1]>self.bg_size[0]-self.blockSize*3:
                        translation = -2
                else:
                    gap = ( self.bg_size[0] - (self.tower.boundaries[0]+self.tower.boundaries[1]) ) //2
                    if gap:
                        translation = min(gap, 2) if gap>0 else max(gap, -2)
                self.tower.level(translation)
                for hero in self.heroes:
                    hero.level(translation)
                
                self.avgLayer = self.hero.onlayer
                # == New Wave Generation Part::===
                if not self.delay%60:
                    self.executeSec()
                
                for item in self.tower.allElements["mons0"]:
                    self.specifier.moveMons(self, item, self.heroes)
                for item in self.tower.allElements["mons1"]:
                    if item.category=="biteChest":
                        item.move( self.delay, self.heroes )
                    elif item.category=="bullet":
                        item.move(self.tower.monsters, self.spurtCanvas, self.bg_size)
                    elif item.category=="bulletPlus":
                        item.move(self.delay, self.tower.monsters, self.spurtCanvas, self.bg_size)
                    elif item.category == "tracker":
                        item.move(self.spurtCanvas)
                    else:
                        self.specifier.moveMons( self, item, self.heroes )
                for item in self.tower.allElements["mons2"]:
                    self.specifier.moveMons(self, item, self.heroes)
                    if item.category=="defenseLight":
                        item.move(self.spurtCanvas)
                for item in self.tower.allElements["dec1"]:
                    if item.category=="coin":
                        item.move( self.delay )
                    elif item.category=="pool":
                        sprites = []
                        for hero in self.heroes:
                            sprites.append(hero)
                        for each in self.tower.monsters:
                            sprites.append(each)
                        self.pool.flow( self.delay, sprites, self.spurtCanvas )
                    else:
                        self.specifier.moveMons( self, item, self.heroes )
                    
                
                # decide the image of Hero
                for hero in self.heroes:
                    vib = hero.checkImg( self.delay, self.tower, self.heroes, pygame.key.get_pressed(), self.spurtCanvas )
                    self._addVib(vib)
                    self._collectHitInfo(hero, self.hero)
                    if hero.category in ["hero","servant"]:
                        # check jump and fall:
                        if hero.k1 > 0:
                            hero.jump( self.tower.getTop( hero.onlayer+1 ) )
                        else:
                            fallChecks = self.tower.groupList[str(hero.onlayer-1)]
                            hero.fall(self.tower.getTop(hero.onlayer-1), fallChecks, self.tower.heightList, GRAVITY)
                        if hero.category=="servant":
                            hero.decideAction(self.delay, self.tower, self.spurtCanvas)
                        
                # 从hero的eventList事件列表中取事件信息。
                for item in self.hero.eventList:
                    if item!="coin":
                        self.supplyList.add( item )
                        self.spurtCanvas.addSpatters(8, (3,4,5), (20,22,24), (10,240,10), getPos(self.hero,0.5,0.4) )
                        if item.name=="ammo":
                            self.msgManager.addMsg( ("Your ammo capacity gains +1 !","你的弹药容量+1！"), urgent=True )
                        else:
                            self.msgManager.addMsg( self.hero.bagpack.itemDic[item.name], type="item", urgent=True )
                    else:
                        self.spurtCanvas.addSpatters(4, (2,3,4), (18,20,22), (255,255,0), getPos(self.hero,0.5,0.4) )
                self.hero.eventList.clear()
                self.hero.reload( self.delay, self.spurtCanvas )

                # 检查各关自然阻碍和特殊机制。
                if self.stg==1:
                    pass
                elif self.stg==3:
                    self.specifier.addSkeleton(self.delay, self.tower, self.hero.onlayer)
                    self.specifier.updateMist(self.delay, self.tower, self.heroes, 0)
                elif self.stg==5:
                    self.specifier.updateBlizzard([self.hero], self.nature.wind, self.spurtCanvas, 0)
                elif self.stg==7:
                    # 增援侍从
                    serv = self.specifier.reinforce(self.hero, self.tower, self.spurtCanvas, self.msgManager)
                    if serv:
                        self.heroes.append(serv)
                    # 管理滚木
                    self.specifier.manageLogs(self.tower, self.bg_size)
                
                if self.vibration > 0:
                    if (self.vibration % 2 == 0):
                        flunc = 4                        
                    else:
                        flunc = -4
                    self.tower.lift(flunc)
                    self.hero.lift(flunc)
                    self.vibration -= 1
                                
                # check Big Events.
                for wall in self.tower.siteWalls:
                    if wall.tower and wall.tower.health<=0:
                        wall.tower = None
                for each in self.heroes[::-1]:
                    if each.category=="servant" and each.health<=0:
                        self.heroes.remove(each)
                        each.kill()
                        del each
                        self.msgManager.addMsg( ("Your servant has died!","你的侍从阵亡！") )
                    elif each.category=="statue" and each.doom:
                        self.msgManager.addMsg( ("Statue has been destroyed!","石像已被摧毁！") )
                    elif each.category=="defenseTower" and each.health<=0:
                        self.heroes.remove(each)
                        each.kill()
                        del each
                        self.msgManager.addMsg( ("Defense Tower is desroyed!","防御塔被摧毁！") )
                self._checkEnd()
                self._updateMonsFall()

            # 暂停状态
            else:
                alter = self._renderPause(pos)
                # Shopping screen.
                if self.shopping:
                    self.tower.merchant.renderWindow(
                        self.screen, self.stg, self.buyNum, self.hero, self.plotManager.propExplan, 
                        self.addSymm, self.addTXT, self.spurtCanvas
                    )

            # Job to be done regardless paused or not.
            for each in self.supplyList:
                each.update(self.screen)
            self.spurtCanvas.update(self.screen)
            self.nature.update(self.screen)
            # Render Banner and Msg.
            self._renderBanner(pos)
            self.msgManager.run()
            self.msgManager.paint(self.screen)
            self.showMsg()
            
            # 一次性的鼠标点击或按键事件
            for event in pygame.event.get():
                if ( event.type == QUIT ):
                    pygame.quit()
                    sys.exit()
                elif ( event.type == KEYDOWN ):
                    if not self.paused:
                        if self.hero.health>0:    # 活着才能运动！
                            if ( event.key == self.keyDic["shootKey"] ):    #射击
                                self.hero.shoot( self.tower, self.spurtCanvas )
                            elif ( event.key == self.keyDic["jumpKey"] ):    #跳跃
                                if ( self.hero.k1 > 0 ) and ( self.hero.k2 == 0 ):
                                    self.hero.k2 = 1
                                if not self.hero.trapper and (self.hero.aground) and ( self.hero.k1 == 0 ):
                                    self.hero.k1 = 1
                            elif ( event.key == self.hero.keyDic["superKey"] ):   # 超级技能
                                self.hero.castSuperPower(self.spurtCanvas)
                                if self.hero.name=="king":
                                    servant = myHero.Servant(self.hero, self.VServant, getPos(self.hero,0.5,1), self.tower.font, self.tower.lgg, self.hero.onlayer)
                                    servant.renewCheckList(self.tower.groupList["0"], clear=True)
                                    servant.jmpSnd.play(0) #登场音效
                                    self.spurtCanvas.addSpatters(8, [3,5,7], [28,32,36], (240,210,30), getPos(servant,0.5,0.5), False)
                                    self.heroes.append(servant)
                            elif ( event.key == self.keyDic["itemKey"] ):    #使用背包物品
                                ret = self.hero.useItem( self.spurtCanvas )
                                if ret:
                                    self.msgManager.addMsg( ret, urgent=True )
                            elif ( event.key == self.keyDic["downKey"] ):    #下跳
                                if not self.hero.oneInEffect( "copter" ):
                                    self.hero.shiftLayer(-2, self.tower.heightList)
                                    hero.aground = False
                            elif ( event.key == self.keyDic["bagKey"] )and len(self.effecter.SSList)==0:     #切换背包物品
                                self.hero.bagpack.shiftItem()
                                self.effecter.addSwitch(self.hero.slot.bagShad[0], self.hero.slot.bagShad[1], 1, 50, 0)
                    elif self.shopping:
                        if ( event.key == self.hero.keyDic["leftKey"] ):
                            self.buyNum = max(self.buyNum-1, -1)
                        elif ( event.key == self.hero.keyDic["rightKey"] ):
                            self.buyNum = min(self.buyNum+1, 1)
                        elif ( event.key == self.hero.keyDic["itemKey"] ):
                            res = self.tower.merchant.sell(self.buyNum, self.hero, self.spurtCanvas)
                            if res:
                                if isinstance(res,str):
                                    p = [choice(self.tower.boundaries), self.tower.getTop(self.tower.extLayer+1)]
                                    servant = myHero.Servant(self.hero, self.VServant, p, self.fntSet[1], self.language, self.hero.onlayer)
                                    servant.renewCheckList(self.tower.groupList["0"])
                                    self.heroes.insert(0, servant)
                                else:
                                    self.supplyList.add( res )
                            else:
                                self.msgManager.addMsg( ("You don't have enough coins.","你的金币数量不足。"), urgent=True )
                        elif ( event.key == self.hero.keyDic["bagKey"] ):
                            if self.hero.coins>=self.tower.merchant.refreshCost:  # coin足够
                                self.hero.coins -= self.tower.merchant.refreshCost
                                for key in self.tower.merchant.goods:
                                    self.tower.merchant.goods[key] = None
                                self.tower.merchant.updateGoods(self.stg, self.hero, canvas=self.spurtCanvas)
                            else:
                                self.msgManager.addMsg( ("You don't have enough coins.","你的金币数量不足。"), urgent=True )
                    if ( event.key == pygame.K_RETURN ):
                        self.paused = not self.paused
                        self.tip = choice( self.plotManager.tips )
                        if self.shopping:           # 检测是否与商人交互
                            self.shopping = False
                elif event.type == pygame.MOUSEBUTTONUP:        # 鼠标事件
                    if self.menuButton.hover_on(pos):
                        self.paused = not self.paused
                        self.tip = choice( self.plotManager.tips )
                        if self.shopping:       # 检测是否与商人交互
                            self.shopping = False
                    elif self.paused:
                        if alter:
                            self.tip = choice( self.plotManager.tips )
                        elif self.quitButton.hover_on(pos):  # 退出（放弃）当前stg.
                            self.comment = ("You give up the challenge.","你放弃了本次挑战。")
                            pygame.mixer.music.fadeout(1000)
                            self.msgManager.clear()
                            self.gameOn = False
                        elif self.musicButton.hover_on(pos):
                            if self.musicOn:
                                pygame.mixer.music.fadeout(1000)
                                self.musicOn = False
                            else:
                                pygame.mixer.music.play(loops=-1)
                                self.musicOn = True
                            self.musicButton.changeKey(self.musicOn)
            
            self.trueScreen.blit(self.screen, self.screenRect)
            pygame.display.flip()   # from buffer area load the pic to the screen
            self.delay = (self.delay+1) % DELAY
            self.clock.tick(TICK)
        
        # ===================================================================
        # Game Loop 结束，渲染 Stage Over 界面。
        self.reportTask(task)
        self.msgManager.addMsg( (f"TASK: {task.descript[0]} ({task.progress}/{task.num})",f"任务：{task.descript[1]} ({task.progress}/{task.num})"), urgent=True )

        if stgManager.renewRec(0, self.wave, gameMod=1):    # Return True means a new high record.
            horns[0].play(0)
            self.comment = ("New highest!","新的最高纪录！")    # 会覆盖死亡信息
        
        # 将wave转化为exp。从屏幕左上角发出。
        self.tower.addCoins(self.wave, [60, 40], self.hero.slot, cList=[8,9,10])
        
        while True:
            # Repaint & translate all elements.
            self.screen.blit( self.BG, self.BGRect )
            # Repaint this tower and situate heroes.
            self.tower.paint(self.screen, heroes=self.heroes)
            # Repaint Natural Impediments of the stage.
            self.specifier.paint(self.screen)

            drawRect( 0, 0, self.bg_size[0], self.bg_size[1], stgManager.themeColor[self.stg], self.screen )
            drawRect( 0, 160, self.bg_size[0], 70, (0,0,0,40), self.screen )

            self.addTXT( self.comment, 2, (255,255,255), 0, -180)
            self.addTXT( ("Survived Waves: %d" % self.wave,"本次存活：%d波" % self.wave), 3, (255,255,255), 0, -150)
            self.addTXT( ("Previous best: %d" % stgManager.getHigh(),"历史最佳：%d" % stgManager.getHigh()), 2, (255,255,255), 0, -100)

            self.hero.slot.paint(self.screen, self.effecter, self.addSymm, self.addTXT)
            # level and exp.
            vHero = heroBook.heroList[self.hero.heroNo]  # 从heroBook的列表中取VHero类型。
            brandRect = self.hero.slot.slotDic["brand"][1]
            bar = heroBook.drawExp( self.screen, brandRect.right+1, brandRect.top+1, int(vHero.exp), int(vHero.nxtLvl), 1, height=16 )
            expTXT = ( "EXP +"+str(self.hero.expInc),"经验+"+str(self.hero.expInc) )
            self.addTXT( expTXT, 0, (40,20,20), bar.left+bar.width//2-self.bg_size[0]//2, bar.top+bar.height//2-self.bg_size[1]//2 )

            # two Basic Buttons.
            pos = pygame.mouse.get_pos()
            pos = (pos[0]-self.screenRect.left, pos[1])     # 从实际窗口转到虚拟窗口的修正
            
            # 结算完成，允许下一步操作
            self.restartButton.paint( self.screen, self.bg_size[0]//2-110, 530, pos)
            self.retreatButton.paint( self.screen, self.bg_size[0]//2+110, 530, pos)
            self._endSettle()
            
            for event in pygame.event.get():  # 必不可少的部分，否则事件响应会崩溃
                if ( event.type == QUIT ):
                    pygame.quit()
                    sys.exit()
                elif ( event.type == pygame.MOUSEBUTTONUP ):
                    if self.restartButton.hover_on(pos):
                        horns[2].play(0)
                        return True     # 返回True，则main中的循环继续
                    elif self.retreatButton.hover_on(pos):
                        horns[2].play(0)
                        return False    # 返回False，则结束main中的循环
            
            # Show Message.
            self.msgManager.run()
            self.msgManager.paint(self.screen)

            self.trueScreen.blit(self.screen, self.screenRect)
            pygame.display.flip()   # from buffer area load the pic to the screen
            self.clock.tick(60)

    def bondSpecif(self):
        self.plotManager = Dialogue(self.stg)
        # Select and overlap the moveMons() method & Add Natural Impediments for different stages.
        if self.stg==1:
            self.specifier = Stg1Specifier(self.hero, self.tower, False, self.VServant)
            for i in range(2):
                f = enemy.InfernoFire(self.bg_size)
                self.tower.allElements["mons2"].add(f)
        elif self.stg==2:
            self.specifier = Stg2Specifier()
            # 分配初始blasting Cap
            self.specifier.giveBlastingCap(self.hero, self.bg_size)
            c = enemy.Column(self.bg_size)
            self.tower.allElements["mons1"].add(c)
        elif self.stg==3:
            self.specifier = Stg3Specifier(self.bg_size)
        elif self.stg==4:
            self.specifier = Stg4Specifier()
            #self.specifier.altMap(self.tower)
            #self.specifier.addPool(self.tower)
        elif self.stg==5:
            self.specifier = Stg5Specifier(self.bg_size, [self.tower])
        elif self.stg==6:
            self.specifier = Stg6Specifier()
        elif self.stg==7:
            self.specifier = Stg7Specifier(self.VServant)
        
    def _checkEnd(self):
        if (self.endCnt==-1) and ( self.hero.doom or self.tower.statue.doom ):
            self.endCnt = 60
            if self.hero.doom:
                self.comment = ("You died.","你已阵亡。")
                self.hero.doom = False      # 信息已得到，归位
            elif self.tower.statue.doom:
                self.comment = ("The Statue is destroyed.","石像已被摧毁。")
                self._addVib(12)
                self.tower.statue.doom = False
        if self.endCnt>0:
            self.endCnt -= 1
            if self.endCnt==0:
                pygame.mixer.music.fadeout(1000)
                self.msgManager.clear()
                self.gameOn = False
    
    # executeSec函数：在每个整秒被调用，执行并检查怪物数量、秒数计算、怪物生成。
    def executeSec(self):
        if self.status == "alarm":
            self.cntDown -= 1
            # alert 3 sec
            self.alertSnd.play(0)
            self.spurtCanvas.addHalo("monsHalo", self.spurtCanvas.alphaCap)
            # recover some health for statue
            if self.cntDown==3:
                self.spurtCanvas.addWaves(getPos(self.tower.statue),(10,255,10),24,8,rInc=2)
                self.tower.statue.recover(250)
                self.msgManager.addMsg( ("Statue has restored 250 points of duration.","石像恢复了250点耐久度。") )
            if self.cntDown == 0:
                self.status = "create"
                self.wave += 1
                # At each beginning of wave, Rebuild Map
                self.tower.rebuildMap(self.spurtCanvas, self.rebuildColor)
                self.fitTower()
                if self.wave in self.phase:
                    self.msgManager.addMsg( ("Tougher Monsters are coming!","更强的怪物即将到来！") )
                #if self.stg in (2,6):
                #    for elem in self.tower.elemList:
                #        self.tower.monsters.add(elem)
                if not self.wave%self.cycle:
                    self.cntDown = 6    # 留出一次生成的时间
                else:
                    self.cntDown = 14   # normal: reset to 14 secs
        elif self.status == "create":
            self.cntDown -= 1
            # 5以上的范围，每次都生成一只随机怪物
            if self.cntDown>=5:
                # Boss Wave
                if not self.wave%self.cycle:
                    new_mons = makeMons( self.tower.layer-2, self.tower.layer, 1, 5, self.tower, join=False )[0]
                    self.monsQue.append( [self._makeMonsFall(new_mons), new_mons] )
                else:
                    # Add chapter Monsters:
                    if random()>=0.12:
                        # One wave before boss battle: party wave!
                        if not (self.wave+1)%self.cycle:
                            ind = self.specialBroc[self.stg]
                            new_mons = makeMons( 0, self.tower.layer, 1, ind[0], self.tower, join=False )[0]
                            self.monsQue.append( [self._makeMonsFall(new_mons), new_mons] )
                        # else: Normal wave
                        else:
                            select = choice(self.monsBroc[self.stg])
                            new_mons = makeMons( 0, self.tower.layer, 1, select, self.tower, join=False )[0]
                            self.monsQue.append( [self._makeMonsFall(new_mons), new_mons] )
                    # Add bonus chest:
                    else:
                        line = choice( ["-1","1","3"] )
                        mons = enemy.BiteChest(self.tower.groupList[line], self.tower.groupList["0"], line)
                        self.monsQue.append( [self._makeMonsFall(mons), mons] )
            else:
                self.status = "battle"
        elif self.status == "battle":
            ended = True
            # Check whether all monsters (with coin value) all eliminated
            for mons in self.tower.monsters:
                if mons.category in MB:
                    ended = False
                    break
            if ended==True: # check active coins if no monsters are found
                for item in self.tower.allElements["dec1"]:
                    if item.category=="coin":
                        ended = False
                        break
            if ended:
                self.tower.merchant.helloSnd.play(0)
                self.paused = True
                self.shopping = True
                self.status = "shop"
                self.msgManager.addMsg( ("Wave clear! Do purchase and prepare for next one.","怪物清空！你可以采购物品，为下一波做准备。") )
                self.tower.merchant.helloSnd.play(0)
        elif self.status == "shop":
            if not self.shopping:
                self.status = "alarm"   # 购物结束，进入下一波的前奏
                # Check next chapter of waves
                if not self.wave%self.cycle:     # 每个chapter含有cycle 个wave
                    self.tower.stg = self.tower.stg%7 + 1   # 共7个chapter，故循环数为7
                    self.stg = self.tower.stg
                    self._initNature()
                    self.bondSpecif()
                    self.tower.shiftChp(self.spurtCanvas, self.rebuildColor)
    
    def _makeMonsFall(self, mons):
        pygame.mixer.Sound("audio/ccSilent.wav").play()
        ball = pygame.sprite.Sprite()
        # show 3 sizes according to different build
        ball.image = pygame.image.load("image/stg5/battleLight.png")
        if mons.health <= 200:
            ball.image = pygame.transform.smoothscale(ball.image, (18,19))
        elif mons.health >= 420:
            ball.image = pygame.transform.smoothscale(ball.image, (38,39))
        ball.rect = ball.image.get_rect()
        ball.rect.left = getPos(mons,0.5,0)[0]
        ball.rect.bottom = 0
        return ball

    def _updateMonsFall(self):
        for pair in self.monsQue[::-1]:
            ball, mons = pair
            if ball.rect.bottom>=mons.rect.bottom:
                # add to tower.monsters
                self.tower.monsters.add(mons)
                # Assign Elite
                rat, buf = self.phase[min( self.wave, len(self.phase) )]
                if mons.category in MONS2:
                    if mons not in self.tower.allElements["mons2"]:
                        self.tower.allElements["mons2"].add(mons)
                        if random() < rat:
                            mons.assignGoalie(buf)
                elif mons.category in MONS0:
                    if mons not in self.tower.allElements["mons0"]:
                        self.tower.allElements["mons0"].add(mons)
                        if random() < rat:
                            mons.assignGoalie(buf)
                elif mons.category not in ["blockStone", "fan", "webWall"]:
                    if mons not in self.tower.allElements["mons1"]:
                        self.tower.allElements["mons1"].add(mons)
                        if random() < rat:
                            mons.assignGoalie(buf)
                self.monsQue.remove(pair)
            else:
                self.spurtCanvas.addSmoke(1, [4,5], 8, mons.bldColor, getPos(ball,0.5,0.5), 2)
                speed = (mons.rect.bottom-ball.rect.bottom)//12
                if speed>8:
                    speed = 8
                elif speed<=1:
                    speed = 2
                ball.rect.bottom += speed

    # ---- clear all elements in the current stg ---
    def clearAll(self):
        #print("高峰内存占用",psutil.Process(os.getpid()).memory_info().rss)
        for grp in self.tower.allElements:
            for each in self.tower.allElements[grp]:
                each.kill()
                del each
        del self.tower
        #print("删除塔楼后",psutil.Process(os.getpid()).memory_info().rss)

    # --- paint upper banner (contains 3 sections) ---
    def _renderBanner(self, pos):
        # paint 4 background sections and get their rect.
        sect1 = drawRect(0, 10, 140, 40, (0,0,0,180), self.screen)     # Current Wave.
        sect2 = drawRect(0, 60, 160, 40, (0,0,0,180), self.screen)     # Next wave count down.
        sect3 = drawRect(self.bg_size[0]-60, 10, 60, 40, (0,0,0,180), self.screen)    # Menu Option.
        # give banner info.
        ctr = (sect1.left+sect1.width//2-self.bg_size[0]//2, sect1.top+sect1.height//2-self.bg_size[1]//2)  # 更改为中心坐标系统的中心点参数
        self.addSymm( pygame.image.load("image/goalie.png").convert_alpha(), sect1.left+20-self.bg_size[0]//2, ctr[1] )
        self.addTXT(("Wave %d" % self.wave,"第%d波" % self.wave), 2, (255,255,255), ctr[0]+20, ctr[1])

        ctr = (sect2.left+sect2.width//2-self.bg_size[0]//2, sect2.top+sect2.height//2-self.bg_size[1]//2)  # 更改为中心坐标系统的中心点参数
        self.addSymm( pygame.image.load("image/timer.png").convert_alpha(), sect2.left+20-self.bg_size[0]//2, ctr[1] )
        txtColor = (255,180,180) if self.cntDown<=3 else (180,255,180)
        self.addTXT(("Next In: %d" % self.cntDown,"距离下波：%d" % self.cntDown), 1, txtColor, ctr[0]+20, ctr[1])

        ctr = (sect3.left+sect3.width//2, sect3.top+sect3.height//2)
        if not self.paused:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("pause","暂停"))
        else:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("play","继续"))
        
        return (sect1, sect2, sect3)
    
    def fitTower(self):
        for sup in self.tower.chestList:
            self.tower.allElements["dec0"].add(sup)             # 加入supply
            self.hero.checkList.add(sup)
        for key in self.tower.groupList:
            if key=="-2":
                for brick in self.tower.groupList[key]:
                    self.tower.allElements["dec0"].add( brick )     # 加入decs
            else:
                for brick in self.tower.groupList[key]:
                    self.tower.allElements["dec1"].add( brick )     # 加入walls
        for elem in self.tower.elemList:
            self.tower.allElements["dec1"].add(elem)
            self.hero.checkList.add(elem)
    

# ===================================== 分STG的Specifier群 ========================================
# 需要额外传入heroes参数是因为要可在两个model内均可用，但两个函数的hero引用方式不同
class Stg1Specifier():
    def __init__(self, hero, tower, tutor_on, VServant):
        self.tutor_on = tutor_on
        if tutor_on==True:
            self.tutorStep = 1  # 1:move left/right; 2:jump; 3:double jump; 4:shoot; 5:jump down; 6:use item; 7:shift item.
            # Add a servant.
            self.servant = myHero.Servant(hero, VServant, [tower.boundaries[1]-120, tower.getTop("-1")], tower.font, tower.lgg, 0)
            self.servant.renewCheckList(tower.groupList["0"])
            tower.allElements["mons1"].add(self.servant)
            tower.goalieList.add(self.servant)  # 加入goalie以关闭进入下一区域的入口
            # 确定键位名称。数字转名字
            keyDic = {}
            for key_name in hero.keyDic:
                keyDic[key_name] = pygame.key.name(hero.keyDic[key_name]).upper()
            self.tipDic = {
                1: (f"Press [{keyDic['leftKey']}] or [{keyDic['rightKey']}] to move toward me.", f"按[{keyDic['leftKey']}]或[{keyDic['rightKey']}]向我移动。"),
                2: (f"Press [{keyDic['jumpKey']}] to jump.", f"按[{keyDic['jumpKey']}]进行跳跃。"),
                3: (f"Double [{keyDic['jumpKey']}] to jump higher. Get to top layer.", f"连续按[{keyDic['jumpKey']}]，上跳到最顶层。"),
                4: (f"Press [{keyDic['shootKey']}] to shoot. Shoot all ammo!", f"按[{keyDic['shootKey']}]射击。试着射出所有弹药！"),
                5: (f"Press [{keyDic['downKey']}] to jump down. Get to bottom layer.", f"按[{keyDic['downKey']}]，下跳到最底层。"),
                6: (f"You're injured. Press [{keyDic['itemKey']}] to eat fruit.", f"你受伤了，按[{keyDic['itemKey']}]使用水果补充体力。"),
                7: (f"Press [{keyDic['bagKey']}] to shift current item.", f"按[{keyDic['bagKey']}]切换当前的背包物品。"),
                8: (f"You can also press [{keyDic['superKey']}] to cast SuperPower. Good luck!", f"你还可以按[{keyDic['superKey']}]释放超级技能。祝你好运！")
            }
            self.checkCD = 60   # 引入检测冷却时间，避免过快判断，结束教程步骤
            # Snds
            self.progressSnd = pygame.mixer.Sound("audio/eatFruit.wav")
            self.servantSnd = [
                None,
                pygame.mixer.Sound("audio/tutorial/tut1.wav"),
                pygame.mixer.Sound("audio/tutorial/tut2.wav"),
                pygame.mixer.Sound("audio/tutorial/tut3.wav"),
                pygame.mixer.Sound("audio/tutorial/tut4.wav"),
                pygame.mixer.Sound("audio/tutorial/tut5.wav"),
                pygame.mixer.Sound("audio/tutorial/tut6.wav"),
                pygame.mixer.Sound("audio/tutorial/tut7.wav"),
                pygame.mixer.Sound("audio/tutorial/tut8.wav")
            ]
        self.init_snd = False   # 标记第一次语音提示是否播放

    def progressTutor(self, delay, hero, tower, spurtCanvas):
        # Only tutorial tower works. (-1 tower)
        if (not self.tutor_on) or tower.area>=0:
            return False
        # print tip.
        if (not delay % 60) and self.servant:
            self.servant.talk = [self.tipDic[self.tutorStep][self.servant.lgg], 60]
            if not self.init_snd:
                self.servantSnd[1].play(0)
                self.init_snd = True
        
        # check point.
        if self.checkCD>0:
            self.checkCD -= 1
        else:
            if self.tutorStep==1:
                # Check if player touched servant.
                if pygame.sprite.collide_mask(hero, self.servant):
                    self._progress(hero, spurtCanvas)
                    return True
            elif self.tutorStep==2:
                if hero.k1==hero.kNum:
                    self._progress(hero, spurtCanvas)
                    return True
            elif self.tutorStep==3:
                if hero.onlayer >= 4:
                    self._progress(hero, spurtCanvas)
                    hero.arrow = 3
                    return True
            elif self.tutorStep==4:
                if hero.arrow == 0:
                    self._progress(hero, spurtCanvas)
                    return True
            elif self.tutorStep==5:
                if hero.onlayer==0:
                    self._progress(hero, spurtCanvas)
                    hero.hitted(5, 0, "physical")   # Actually 6 dmg in heroic difficulty.
                    hero.bagpack.bag["fruit"] += 1
                    return True
            elif self.tutorStep==6:
                if hero.health==hero.full:
                    self._progress(hero, spurtCanvas)
                    return True
            elif self.tutorStep==7:
                self._progress(hero, spurtCanvas)
                return True
            elif self.tutorStep==8:
                tower.goalieList.remove(self.servant)
                if self.servant:
                    self.servant = None
                    return self.tipDic[self.tutorStep]
                return True

    def _progress(self, hero, canvas):
        self.tutorStep += 1
        self.checkCD = 60
        canvas.addSpatters( 12, [3, 4, 5], [16,20,24], (255,210,90), getPos(hero, 0.5, 0.5), False )
        self.progressSnd.play(0)
        self.servantSnd[self.tutorStep].play(0)
    
    def moveMons(self, model, item, heroes):
        if item.category == "infernoFire":
            item.update( model.delay, heroes, model.spurtCanvas )
        elif item.category == "fire":
            vib = item.update(model.delay, model.tower.groupList["0"], model.tower.groupList[str(item.onlayer)], model.tower.getTop(item.onlayer)+model.blockSize, heroes, model.spurtCanvas, model.bg_size ) 
            if vib == "vib":
                model._addVib(6)
        elif item.category == "CrimsonDragon":
            if item.activated:
                model.spurtCanvas.addHalo( "monsHalo", 0 )
                fire = item.update( heroes, model.spurtCanvas )
                if fire:
                    model.tower.allElements["mons1"].add(fire)
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):  # moves only if they appears in the screen
            if item.category == "gozilla":
                item.move(model.delay, heroes)
                item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
            elif item.category=="megaGozilla":
                item.move(model.delay, heroes, model.spurtCanvas)
                item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY)
            elif item.category == "dragon":
                fire = item.move(model.delay)
                if fire:
                    model.tower.allElements["mons1"].add(fire)
            elif item.category == "dragonEgg":
                if item.broken==0:
                    dragon = enemy.Dragon(model.tower.heightList[str(item.onlayer)], str(item.onlayer), model.tower.boundaries)
                    dragon.rect.left = item.rect.left
                    model.tower.monsters.remove( item )
                    model.tower.goalieList.remove( item )
                    model.tower.monsters.add( dragon )
                    model.tower.allElements["mons1"].add( dragon )
                    item.broken = 1
                elif item.broken<0: # broken<0表示健康
                    fire = item.move(model.delay, heroes)
                    if fire:
                        model.tower.allElements["mons1"].add(fire)
            elif item.category == "blockFire":
                item.burn(model.delay, heroes, model.spurtCanvas)

    def paint(self, screen):
        if self.tutor_on and self.servant:
            self.servant.drawHeads(screen)
        return

class Stg2Specifier():
    def __init__(self):
        pass

    def giveBlastingCap(self, hero, bg_size):
        hero.bagpack.incItem("blastingCap", 2)
        startPos = [bg_size[0]//2, 60]
        tgtPos = [ hero.slot.ctrDic["bag"][0]+bg_size[0]//2, hero.slot.ctrDic["bag"][1]+bg_size[1]//2 ]
        substance = mapManager.ChestContent("blastingCap", hero.bagpack.readItemByName("blastingCap")[1], 2, startPos, tgtPos)
        hero.eventList.append( substance )
    
    def moveMons(self, model, item, heroes):
        if item.category == "column":
            vib = item.update( heroes, model.avgLayer, model.tower.groupList, model.spurtCanvas )
            if vib:
                model._addVib(6)
        elif item.category == "stone":
            item.update(model.delay, model.tower.groupList["0"], model.tower.groupList[str(item.onlayer)], model.tower.getTop(item.onlayer)+model.tower.blockSize, heroes, model.spurtCanvas)
        elif item.category == "GiantSpider":
            if item.activated:
                model.spurtCanvas.addHalo( "monsHalo", 0 )
                web = item.move( model.delay, heroes, model.spurtCanvas )
                if isinstance(web, list) and len(web)>2:
                    for child in web:
                        model.tower.allElements["mons0"].add(child)
                        model.tower.monsters.add(child)
                elif web:
                    web = mapManager.WebWall( web[1].left+web[1].width//2, web[1].top+web[1].height//2, 2, (0,0), fade=True)
                    model.tower.allElements["dec1"].add(web)
                    model.tower.monsters.add(web)
                    for hero in heroes:
                        hero.checkList.add(web)
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
            if item.category == "bat":
                item.move( model.delay, heroes )
            elif item.category == "golem":
                more = item.move( model.delay, heroes )
                if more:
                    for each in more:
                        model.tower.monsters.add( each )
                        model.tower.allElements["mons1"].add( each )
                if item.doom and ( item in model.tower.monsters ):
                    model.tower.monsters.remove(item)
            elif item.category == "bowler":
                item.move(model.delay, heroes)
                stone = item.throw(model.delay)
                if stone:
                    model.tower.allElements["mons1"].add(stone)
                    model.tower.monsters.add(stone)
            elif item.category == "webWall":
                if not item.valid and ( item in model.tower.monsters ):
                    model.tower.monsters.remove(item)
                else:
                    item.stick(heroes)
            elif item.category == "blockStone":
                item.checkExposion(model.spurtCanvas)
            elif item.category == "spider":
                item.move( model.delay, heroes )
            
    def paint(self, screen):
        return

class Stg3Specifier():
    def __init__(self, bg_size):
        self.mistGenerator = enemy.MistGenerator(bg_size)
        
    def addSkeleton(self, delay, tower, avgLayer):
        # 每隔一段时间在屏幕范围内生成一波骷髅兵
        if not ( delay % 80 ):
            for line in range(avgLayer-3, avgLayer+3):  # 起点，终点，变hero的偶数为groupList的奇数（hero.onlayer +- 4 - 1）
                if ( line%2 ) and ( 0 < line < tower.layer-1 ) and len(tower.monsters)<60 and ( random() < 0.1 ):
                    skeleton = enemy.Skeleton(tower.groupList[str(line)], tower.groupList["0"], tower.blockSize, line)
                    if hasattr(skeleton, 'rect'):
                        skeleton.coin = 0
                        tower.monsters.add(skeleton)
                        tower.allElements["mons1"].add(skeleton)
                    else:
                        del skeleton

    def updateMist(self, delay, tower, heroes, curArea):
        # 需要照亮的物体：包括门、商人和玩家
        sprites = [tower.porter]
        if tower.merchant:
            sprites.append(tower.merchant)
        self.mistGenerator.renew( delay, sprites+heroes )
        # 更新雾团数量
        if curArea == 0:
            self.mistGenerator.mistNum = 4
        elif curArea in (1,2):
            self.mistGenerator.mistNum = 5
        else:
            self.mistGenerator.mistNum = 6

    def moveMons(self, model, item, heroes):
        if item.category == "Vampire":
            if item.activated:
                model.spurtCanvas.addHalo( "monsHalo", 0 )
                babe = item.move( model.delay, heroes, model.tower.groupList, model.spurtCanvas )
                if babe:      # create more minion.
                    if babe[0] == "skeleton":
                        mini = enemy.Skeleton(model.tower.groupList[str(item.onlayer)], model.tower.groupList["0"], model.tower.blockSize, item.onlayer)
                        mini.birth[0] = babe[1][0]
                    elif babe[0] == "dead":
                        mini = enemy.Dead(model.tower.groupList[str(item.onlayer)], model.tower.groupList["0"], model.tower.blockSize, item.onlayer)
                        mini.rect.left = babe[1][0]
                    elif babe[0] == "ghost":
                        mini = enemy.Ghost( model.tower.boundaries, babe[1][1], item.onlayer )
                        mini.rect.left = babe[1][0]
                    mini.coin = 0   # 召唤物coin价值为0
                    model.spurtCanvas.addSpatters( 5, [3, 4], [9, 10, 11], (80,10,80,255), babe[1], True )
                    model.tower.monsters.add( mini )
                    model.tower.allElements["mons1"].add( mini )
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
        elif item.category == "specialWall" and hasattr(item, "clpCnt"):    # In case of endless model
            item.collapse( GRAVITY, model.spurtCanvas )
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
            if item.category == "skeleton":
                if not item.popping:
                    item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                item.move( model.delay, heroes )
            elif item.category == "dead":
                item.move( model.delay, heroes, model.spurtCanvas )
                item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
            elif item.category == "ghost":
                signal = item.move(model.delay, heroes, model.spurtCanvas)
                if signal=="rejoin" and item not in model.tower.monsters:
                    model.tower.monsters.add( item )
                elif signal=="out" and item in model.tower.monsters:
                    model.tower.monsters.remove( item )

    def paint(self, screen):
        self.mistGenerator.paint(screen)
    
class Stg4Specifier():
    def __init__(self):
        pass

    def altMap(self, tower):
        # 1 - Add Hut. First, check all the cluster of sequential 3 walls
        tower.hut_list = list()
        wall_clusters = self.get_wall_cluster(tower, n=2)
        for i in range(2):
            if not wall_clusters:
                continue
            clust = choice(wall_clusters)
            hut_base = clust[0]     # 以左砖为准
            house = mapManager.House( hut_base.rect.right, hut_base.rect.top+2, "house", tower.stg, tower.font, tower.lgg )
            tower.allElements["dec0"].add(house)           # For drawing and transforming with the map
            tower.groupList[str(hut_base.coord[1]+2)].add(house)        # For hero's jump checkList
            tower.hut_list.append(house)                    # For chim function
            # 随同工作1：替换可能遮住屋顶的砖
            for wall in tower.groupList[str(hut_base.coord[1]+2)]:
                if wall.category in ("lineWall","specialWall") and wall.coord[0] in (hut_base.coord[0], hut_base.coord[0]+1):
                    new_brick = mapManager.Wall(wall.rect.left,wall.rect.top,"lineWall",4,wall.coord)
                    wall.kill()
                    new_brick.image = pygame.image.load("image/stg4/lineWall_alt.png").convert_alpha()
                    new_brick.mask = pygame.mask.from_surface(new_brick.image)
                    tower.allElements["dec1"].add(new_brick)    # For paint out and transform with the map
                    tower.groupList[str(new_brick.coord[1])].add(new_brick)
            # 随同工作2：将被遮盖的decor和chest重新加入Group，使之visible(NOTE:后期更新可以直接删除，hut自己会动态给出两个宝箱)
            for item in tower.allElements["dec0"]:
                if (item.category in ["chest","lineDecor"]) and (item.coord[1]==hut_base.coord[1]) and \
                    (item.coord[0] in [hut_base.coord[0],hut_base.coord[0]+1]):
                    tower.allElements["dec0"].remove(item)
                    tower.allElements["dec1"].add(item)
            wall_clusters.remove(clust)
        # 2 - random替换linewall
        for item in tower.allElements["dec1"]:
            if item.category=="lineWall" and random()<0.12:
                item.image = pygame.image.load("image/stg4/lineWall_alt.png").convert_alpha()
                item.mask = pygame.mask.from_surface(item.image)
    
    def get_wall_cluster(self, tower, n=3):
        cluster_list = []
        for line in tower.groupList:
            if 0<int(line)<tower.layer-2:
                cluster = []
                for wall in tower.groupList[line]:
                    if not cluster:     # 候选列表为空，则直接添加
                        cluster.append(wall)
                    elif wall.coord[0]==cluster[-1].coord[0]+1:
                        cluster.append(wall)
                    # Full
                    if len(cluster)>=n:
                        cluster_list.append(cluster.copy())
                        cluster = []
        return cluster_list
    
    def generateSprout(self, delay, tower, bg_size):
        if delay%120:
            return
        startPos = [choice([0,bg_size[0]]), randint(60,bg_size[1]-60)]
        spd = [0,0]
        if startPos[0]==0:
            spd[0] = 1
        else:
            spd[0] = -1
        if startPos[1]<bg_size[0]//2:
            spd[1] = randint(0,1)
        else:
            spd[1] = randint(-1,0)
        sprout = enemy.MiniFungus( [startPos[0]-10,startPos[0]], startPos[1], spd )
        tower.allElements["mons2"].add(sprout)
        tower.monsters.add(sprout)
    
    def moveMons(self, model, item, heroes):
        if item.category == "MutatedFungus":
            if item.activated:
                model.spurtCanvas.addHalo( "monsHalo", 0 )
                miniFung = item.move( model.delay, heroes )
                if miniFung:
                    model.tower.allElements["mons2"].add(miniFung)
                    model.tower.monsters.add(miniFung)
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
            if item.category == "snake":
                item.move( model.delay, heroes )
            elif item.category == "slime":
                new = item.move(model.delay, heroes)
                if new:
                    model.tower.monsters.add(new)
                    model.tower.allElements["mons1"].add(new)
            elif item.category == "fly":
                item.move(model.delay, heroes)
            elif item.category == "worm":
                keyLine = model.tower.getTop(item.onlayer)
                item.move( model.delay, model.tower.groupList[str(item.onlayer)], keyLine, model.tower.groupList["0"], heroes, model.spurtCanvas, GRAVITY )
            elif item.category == "nest":
                more = item.move( model.delay, model.tower.monsters )
                if more:
                    for each in more:
                        model.tower.monsters.add( each )
                        model.tower.allElements["mons1"].add( each )
            elif item.category == "blockOoze":
                item.bubble( model.delay, heroes )
            elif item.category == "miniFungus":
                item.move(model.delay, heroes, model.spurtCanvas)
            elif item.category == "house":
                item.chim(model.spurtCanvas)
            elif item.category == "Python":
                item.move( model.delay )

    def paint(self, screen):
        return

class Stg5Specifier():
    def __init__(self, bg_size, towerList):
        # 1.暴风雪控制器
        self.blizzardGenerator = enemy.blizzardGenerator(bg_size, 1500, 1000)
        # 2.每个区域生成Heal Totem
        totemNum = 4
        for tower in towerList:
            if tower.layer<=6:
                continue
            # 给塔楼增加图腾数量属性
            tower.totemNum = totemNum
            tower.totemList = pygame.sprite.Group()
            # 确定出现的层数
            occList = sample(range(5, tower.layer, 2), totemNum)
            for group in occList:
                wallList = [aWall for aWall in tower.groupList[str(group)]]          # Group转化为list
                wall = choice(wallList)
                totem = mapManager.Totem("healTotem", wall, group)
                tower.monsters.add( totem )
                tower.allElements["mons1"].add( totem )
                tower.totemList.add( totem )
            totemNum += 1
    
    def updateBlizzard(self, heroes, wind, spurtCanvas, curArea):
        self.blizzardGenerator.storm(heroes, wind, spurtCanvas, curArea)

    def checkTotem(self, tower, msgManager):
        if not hasattr(tower, "totemNum"):
            return
        if len(tower.totemList)<tower.totemNum:
            tower.totemNum -= 1
            if tower.totemNum<=0:
                msgManager.addMsg( ("All [Heal Totem] in this area are destroyed!","本区域内的所有【治疗图腾】全部摧毁！") )
            else:
                msgManager.addMsg( (f"You've destroyed a [Heal Totem]! {tower.totemNum} more.",f"已摧毁一个【治疗图腾】！剩余{tower.totemNum}个。") )
            
    def moveMons(self, model, item, heroes):
        if item.category == "FrostTitan":
            if item.activated:
                model.spurtCanvas.addHalo( "monsHalo", 0 )
                snowball = item.move( model.delay, heroes, model.spurtCanvas, model.bg_size )
                if isinstance(snowball, enemy.SnowBall):
                    model.tower.allElements["mons2"].add(snowball)
                elif isinstance(snowball, enemy.IceSpirit):
                    model.tower.allElements["mons2"].add(snowball)
                    model.tower.monsters.add(snowball)
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
        elif item.category == "snowball":
            balls = item.move(
                model.delay, model.tower.groupList["0"], model.tower.groupList[str(item.onlayer)], 
                model.tower.getTop(item.onlayer)+model.blockSize, heroes, model.spurtCanvas, GRAVITY
            ) 
            if balls:
                model._addVib(6)
                for each in balls:
                    model.tower.allElements["mons2"].add( each )
        elif item.category == "healTotem":
            if not item.checkExposion(model.spurtCanvas):   # 检查摧毁
                tracker = item.run(model.tower.monsters, model.spurtCanvas)
                if tracker:
                    model.tower.allElements["mons1"].add( tracker )
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
            if item.category == "wolf":
                item.move(model.delay, heroes, model.spurtCanvas)
            elif item.category == "iceTroll":
                item.move(model.delay, heroes, model.spurtCanvas)
            elif item.category == "eagle":
                item.move(model.delay, heroes, model.spurtCanvas)
            elif item.category == "iceSpirit":
                item.move(model.delay, heroes, model.spurtCanvas)

    def paint(self, screen):
        self.blizzardGenerator.paint(screen)

class Stg6Specifier():
    def __init__(self):
        return

    def moveMons(self, model, item, heroes):
        if item.category == "fire":  # Warmachine's fireball.
            item.update(model.delay, model.tower.groupList["0"], model.tower.groupList[str(item.onlayer)], model.tower.getTop(item.onlayer)+model.tower.blockSize, heroes, model.spurtCanvas, model.bg_size ) 
        elif item.category == "missle":
            item.update(model.delay, model.spurtCanvas)
        elif item.category == "WarMachine":
            if item.activated:
                model.spurtCanvas.addHalo( "monsHalo", 0 )
                fire = item.move( model.delay, heroes, model.spurtCanvas, model.tower )
                if fire:
                    model.tower.allElements["mons1"].add(fire)
                    model._addVib(2)
                    if fire.category=="missle":
                        model.tower.monsters.add( fire )
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
        elif item.category == "gunBullet":
            item.update(heroes, model.tower.groupList["0"], model.bg_size[0], model.spurtCanvas)
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):  # moves only if the item appears in the screen
            if item.category == "dwarf":
                item.move(model.delay, heroes)
            elif item.category == "gunner":
                item.move(model.delay, heroes, model.screen)
                item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                # 拾取bullet，加入all然后清空。
                if item.newBullet:
                    model.tower.allElements["mons1"].add(item.newBullet)
                    item.newBullet = None
            elif item.category == "lasercraft":
                item.move(model.delay, heroes, model.tower.layer)
            elif item.category == "fan":
                item.whirl(model.delay, heroes)

    def paint(self, screen):
        return
    
class Stg7Specifier():
    def __init__(self, VServant):
        self.boss = None
        self.servant = None
        self.VServant = VServant
        self.reinf_time = 10     # 每局游戏拥有11次增援
        self.serv_cnt = self.serv_cnt_full = 240    # 增援倒计时
        self.log_cnt = self.log_cnt_full = 1120

    def bind(self, monsters):
        for mons in monsters:
            if mons.category=="Chicheng":
                self.boss = mons
                break
        if not self.boss:
            return False
        return True

    def checkWin(self):
        if self.boss.health<=0:
            return True
        else:
            return False

    def reinforce(self, hero, tower, canvas, msgManager):
        if self.serv_cnt>0:
            self.serv_cnt -= 1
            if self.serv_cnt==0:
                self.servant = myHero.Servant(hero, self.VServant, getPos(hero,0.5,1), tower.font, tower.lgg, hero.onlayer)
                self.servant.renewCheckList(tower.groupList["0"], clear=True)
                self.servant.jmpSnd.play(0) #登场音效
                self.reinf_time -= 1
                canvas.addSpatters(8, [3,5,7], [28,32,36], (240,210,30), getPos(self.servant,0.5,0.5), False)
                msgManager.addMsg( ("New Reinforce Arrived!","新的增援已抵达！") )
                return self.servant
        elif self.servant and (self.servant.health<=0):
            canvas.addExplosion( getPos(self.servant, 0.5, 0.5), 30, 16 )
            msgManager.addMsg( (f"Your servant died! Remaining Reinforce times: {self.reinf_time}",f"你的侍从阵亡！剩余增援次数：{self.reinf_time}") )
            if self.reinf_time>0:
                self.serv_cnt = self.serv_cnt_full   # 开启重置倒计时
            self.servant = None
        return None

    def manageLogs(self, tower, bg_size):
        if tower.area==2:
            return
        if self.log_cnt>0:
            self.log_cnt -= 1
            if self.log_cnt==0:
                pos = ( randint(tower.boundaries[0]+80, tower.boundaries[1]-80), tower.getTop("max") )
                l = enemy.Log(bg_size, tower.layer-1, pos)
                tower.allElements["mons1"].add( l )
                self.log_cnt = randint(self.log_cnt_full-100, self.log_cnt_full+100)
    
    def moveMons(self, model, item, heroes):
        if item.category == "log":
            vib = item.update(model.delay, heroes, model.tower.groupList, model.tower.getTop(item.onlayer), model.tower.boundaries, model.spurtCanvas)
            if vib:
                model._addVib(6)
        elif item.category == "soulBlast":
            item.update(model.delay, 
                model.tower.groupList["0"], 
                model.tower.groupList[str(item.onlayer)], 
                model.tower.getTop(item.onlayer)+model.blockSize, 
                heroes, 
                model.spurtCanvas, 
                model.bg_size )
        elif item.category == "Chicheng":
            if item.activated:
                model.spurtCanvas.addHalo( "monsHalo", 0 )
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(12)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):  # moves only if the gozilla appears in the screen
            if item.category == "stabber":
                item.stab(model.delay, heroes )
            elif item.category == "guard":
                item.move(model.delay, heroes)
                item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
            elif item.category == "flamen":
                soulBlast = item.move(model.delay, heroes)
                if soulBlast:
                    model.tower.allElements["mons1"].add(soulBlast)
            elif item.category == "assassin":
                YRange = (model.tower.getTop("min"), model.tower.getTop("max"))
                item.move(model.delay, heroes, YRange, model.spurtCanvas)

    def paint(self, screen):
        return
    
# ------------------------------------------------------------------------------------------
def makeMons(btmLayer, topLayer, amount, mType, tower, join=True):
    '''
    Will directly fill the given tower's Monster Grouplist.
        btmLayer: the layer that only above which would the minions may appear;
        topLayer: the layer by which the minions would stop appearring;
        amount: the total amount of the monsters. They will be scattered between btmLayer & topLayer;
        mType: (number1,2,3,4)indicates what kind of monster you want to make;
        tower: the mapManager Object Reference that will provide many useful variables for the process;
            it contains a SpriteGroup-type container that you wish to fill up with created minions;
        join: whether you wish to directly add the monster into the tower.monsters.
            If False, this func will return a list of newly created monsters.
    '''
    # 首先在所给区间生成随机数列并进行抽取。
    # 注意：合理的tower层数为奇数，若为偶数则修正起点为奇数。
    if (btmLayer%2==0):
        btmLayer += 1
    numList = range(btmLayer, topLayer, 2)
    occList = []
    # 若amount数量大于可用层数，则将多余的重新抽取插入结果中。（即一层会出现两个）。
    while True:
        if amount>len(numList):
            occList += sample(numList, len(numList))
            amount -= len(numList)
        else:
            occList += sample(numList, amount)
            break
    # 针对occList结果制作monsters。
    newMons = []
    for group in occList:
        group = str(group)
        # deal every chosen layer; group is the key (str of layer number)
        if len(tower.groupList[group])>0:
            stg = tower.stg
            if ( stg==1 ):
                if mType == 1:
                    minion = enemy.Gozilla(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 2:
                    minion = enemy.MegaGozilla(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    minion = enemy.Dragon(tower.heightList[group], group, tower.boundaries)
                elif mType == 4:
                    minion = enemy.DragonEgg(tower.groupList[group], tower.groupList["0"], group)
                elif mType == 5:       # Crimson Dragon
                    x = tower.oriPos[0] + tower.diameter*tower.blockSize
                    y = tower.getTop(group)+tower.blockSize
                    minion = enemy.CrimsonDragon(x, y, group, tower.font[1])
            elif ( stg==2 ):
                if mType == 1:
                    minion = enemy.Bat(tower.groupList[group], group)
                if mType == 2:
                    minion = enemy.Golem(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    minion = enemy.Bowler(tower.groupList[group], tower.groupList["0"], group)
                elif mType == 4:
                    scope_y = ( tower.getTop("max"), tower.getTop("min") )
                    minion = enemy.Spider(tower.heightList[group], group, tower.boundaries, scope_y)
                elif mType == 5:
                    scope_y = ( tower.getTop("max"), tower.getTop("min") )
                    minion = enemy.GiantSpider(tower.heightList[group], group, tower.boundaries, scope_y, tower.font[1])
            elif ( stg==3 ):
                if mType == 1:
                    minion = enemy.Skeleton(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                    if not minion:
                        continue
                elif mType == 2:
                    minion = enemy.Dead(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    XRange = (tower.boundaries[0], tower.boundaries[1])
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.Ghost( XRange, y, group )
                elif mType == 5:    # boss - Vampire
                    minion = enemy.Vampire(tower.groupList, group, tower.boundaries, tower.font[1])
            elif ( stg==4 ):
                if mType == 1:
                    minion = enemy.Snake(tower.groupList[group], tower.groupList["0"], group)
                elif mType == 2:
                    minion = enemy.Slime(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    minion = enemy.Nest(tower.groupList[group], group)
                elif mType == 4:
                    XRange = (tower.boundaries[0], tower.boundaries[1])
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.Fly( XRange, y, group )
                elif mType == 5:
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.MutatedFungus(tower.boundaries, y, group, tower.font[1])
            elif ( stg==5 ):
                if mType == 1:
                    minion = enemy.Wolf(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 2:
                    minion = enemy.IceTroll(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    XRange = (tower.boundaries[0], tower.boundaries[1])
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.IceSpirit( XRange, y, group )
                elif mType == 4:
                    XRange = (tower.boundaries[0], tower.boundaries[1])
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.Eagle( XRange, y, group )
                elif mType == 5:
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.FrostTitan(tower.boundaries, y, group, tower.font[1])
            elif ( stg==6 ):
                if mType == 1:
                    minion = enemy.Dwarf(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 2:
                    minion = enemy.Gunner(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    XRange = (tower.boundaries[0]-tower.blockSize*2, tower.boundaries[1]+tower.blockSize*2)
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.Lasercraft( XRange, y, group )
                elif mType == 5:        # boss - War Machine
                    minion = enemy.WarMachine(tower.groupList, group, tower.font[1])
            elif ( stg==7 ):
                if mType == 1:
                    minion = enemy.Guard(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 2:
                    minion = enemy.Flamen(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    XRange = (tower.boundaries[0], tower.boundaries[1])
                    y = tower.getTop(int(group))+tower.blockSize
                    minion = enemy.Assassin( XRange, y, group, tower.groupList["0"] )
                elif mType == 5:        # Chicheng
                    minion = enemy.Chicheng(tower.groupList, group, tower.font[1])
            if join:
                tower.monsters.add(minion)
            else:
                newMons.append(minion)
    return newMons
