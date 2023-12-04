"""
model.py:
Core module of the whole game: Define Model classes the manage the main game loop.
GameModel controls the image rendering, items updating, collision checks, and end-game checks.
Adventure Mode, Endless Mode, and Tutorial Mode respectively use three different GameModel classes.
These GameModel classes co-work tightly with Specifiers from module specifier.py.

model.py:
게임 전체의 핵심 모듈: 주 게임 루프를 관리하는 Model 클래스를 정의
GameModel은 이미지 렌더링, 아이템 업데이트, 충돌 확인 및 게임 종료 확인을 제어
모험 모드, 무한 모드 및 튜토리얼 모드는 각각 다른 GameModel 클래스를 사용
GameModel 클래스는 specifier.py 모듈의 Specifiers와 긴밀하게 협력하여 작동
"""
import sys
import math
from random import *
import pygame
from pygame.locals import *

import enemy
from mapTowers import AdventureTower, EndlessTower, TutorialTower
from mapElems import ChestContent, Statue, Pool
import myHero
from canvas import SpurtCanvas, Nature
from plotManager import Dialogue

from specifier import * # specifier 모듈을 가져와서 각 장(chapter)에 따라 이 모듈의 기본 "게임 관리자"를 맞춤화합니다.

from database import GRAVITY, MB, CB, RB, PB
from util import ImgButton, TextButton, MsgManager, ImgSwitcher, HPBar
from util import getPos, drawRect


"""
    注：有2个透明画布（surface）在所有元素之上，一是用于画自然元素（如雪，雨）；第二个是画全屏效果和击中时的血的溅射效果。
    Model执行流程：绘图 → 平移 → 英雄动作 → 怪物、子弹等元素动作 → 检查重要事件的触发 → 响应键盘事件 ◀循环

    참고: 모든 요소 위에는 2 개의 투명 캔버스(surface)가 있습니다. 하나는 자연 요소(눈, 비와 같은)를 그리는 데 사용되며, 두 번째는 전체 화면 효과 및 피격 시의 혈흔 효과를 그리는 데 사용됩니다.
    Model 실행 흐름: 그림 그리기 → 이동(평행 이동) → 영웅 동작 → 몬스터, 총알 및 기타 요소 동작 → 중요한 이벤트 트리거 확인 → 키보드 이벤트 응답 ◀ 루프
"""
inner_size = (1000,720) # 실제 카메라 크기입니다. 'Model.screen'이 가상 스크린으로 사용하는 크기입니다.
                        # 프로그램의 전체 창은 'Model.trueScreen'입니다.                                    
                        # 원래 창 너비가 1080px로 설정하면 그림 그리기가 지연될 수 있습니다. 
                        # 1000px로 설정하면 약간의 지연이 발생할 수 있습니다. 그러나 960px로 설정하면 매우 부드러워집니다. (보스 전투 중에도)
                        # 여기서 균형점 980px를 선택합니다: 최대한 많은 게임 화면을 표시하면서 게임 화면이 상대적으로 부드런 상태를 보장합니다.
TICK = 60
DELAY = 240
SCRINT = 36     # screen interval: 화면 이동 속도는 36 픽셀의 각 편차마다 1px의 속도 증가를 나타냅니다 (화면 전체 높이 720px)
PAUSE_SEC = 30  # 짧은 일시 중지 시간의 카운트 다운 지속 시간 (권장 범위: 60 이하)
MONS0 = ["spider", "GiantSpider"]
MONS2 = ["CrimsonDragon", "fly", "MutatedFungus", "eagle", "iceSpirit", "FrostTitan", "assassin"]


# ===================================
# Base Class for the three game modes
class GameModel:
    bg_size = ()          # 화면의 너비와 높이
    blockSize = 72
    language = 0          # 기본적으로 영어로 설정되며, 생성자에서 번역을 설정할 수 있습니다
    fntSet = []
    stg = 1
    delay = DELAY         # 이 변수는 이미지 전환에 지연 시간을 추가하여 게임의 정상 실행에 영향을 미치지 않도록 사용됩니다
    
    msgList = []          # 메시지를 저장하는 리스트 (리스트 내부에 리스트 포함): [ [영웅 이름, 사건, 카운트 다운 (, 스티커)], ... ]
    vibration = 0         # 화면의 진동을 표시하는 카운트입니다.
    screen = None         # 화면 객체의 참조를 저장합니다.
    screenRect = None
    clock = None
    BG = None             # 현재 단계의 환경 배경
    BGRect = None
    tip = []
    translation = [0,0]
    
    nature = None         # 자연 요소의 캔버스
    spurtCanvas = None    # 타격 피드백 및 피 혈흔을 그리는 캔버스 (상상 이상으로 다재다능하고 피만 그릴 수 있는 게 아닙니다)
    music = None          # BGM
    paused = True
    musicOn = True
    gameOn = True         # 게임 루프 플래그, 기본적으로 True이며, 플레이어가 종료를 클릭하거나 게임이 종료될 때 False로 변경됩니다.
    VServant = None       # VServant는 servant 객체를 생성하는 데 사용되는 특수하고 중요한 속성입니다. 이는 main 모듈의 initGameData()에서 설정됩니다.   

    def __init__(self, stg, screen, language, fntSet, monsAcc):

        # self: 자신 (현재 클래스의 인스턴스)
        # stg: 스테이지
        # screen: 화면
        # language: 언어
        # fntSet: 폰트 세트
        # monsAcc: 몬스터 액세스 (몬스터 접근)

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
        # 오른쪽 상단의 컨트롤 및 다른 컨트롤러
        self.menuButton = ImgButton( {"default":pygame.image.load("image/menu.png").convert_alpha()}, "default", self.fntSet[1], labelPos="btm" )
        self.quitButton = ImgButton( {"default":pygame.image.load("image/quit.png").convert_alpha()}, "default", self.fntSet[1], labelPos="btm" )
        self.musicButton = ImgButton( {True:pygame.image.load("image/BGMusic.png").convert_alpha(),
                                    False:pygame.image.load("image/BGMute.png").convert_alpha()}, self.musicOn, self.fntSet[1], labelPos="btm" )
        self.coinIcon = pygame.image.load("image/coin0.png").convert_alpha()
        # SpurtCanvas
        self.spurtCanvas = SpurtCanvas( self.bg_size )
        enemy.Monster.spurtCanvas = self.spurtCanvas
        enemy.Monster.msgList = self.msgList
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
        self.hostage = None
        # statistics about player's performance
        self.stat = {}
        # end screen ----------------------
        self.restartButton = TextButton(200,60, {"default":("Retry","重试")}, "default", self.fntSet[3])
        self.retreatButton = TextButton(200,60, {"default":("Home","主菜单")}, "default", self.fntSet[3])

    def init_BG(self, stg):
        self.BG = pygame.image.load(f"image/stg{stg}/towerBG.jpg").convert_alpha()
        self.BGRect = self.BG.get_rect()
        self.BGRect.left = (self.bg_size[0]-self.BGRect.width) // 2   # 가운데 정렬
        self.BGRect.bottom = self.bg_size[1]                          # 초기로 하단 표



    def init_stone(self, stone):
        print("Using stone: ", stone)
        self.using_stone = stone
        if stone=="loadingStone":
            for hero in self.heroes:
                hero.loading = hero.LDFull = RB[stone].data
            self.msgManager.addMsg( ("Loading Stone has been activated.","填装符石已激活。"), type="ctr", duration=120, 
                                    icon=pygame.image.load("image/runestone/loadingStone.png") )
            
        elif stone=="sacredStone":
            for hero in self.heroes:
                hero.superPowerFull -= round(hero.superPowerFull * RB[stone].data)
                hero.superPowerBar = HPBar(hero.superPowerFull, blockVol=hero.superPowerBar.blockVol, 
                                            barOffset=hero.superPowerBar.barOffset, color="yellow")
            self.msgManager.addMsg( ("Sacred Stone has been activated.","神圣符石已激活。"), type="ctr", duration=120, 
                                    icon=pygame.image.load("image/runestone/sacredStone.png") )
        elif stone=="bloodStone":
            # action happens in Model.collectHitInfo()
            self.HPSteal = RB[stone].data
            self.msgManager.addMsg( ("Blood Stone has been activated.","鲜血符石已激活。"), type="ctr", duration=120, 
                                    icon=pygame.image.load("image/runestone/bloodStone.png") )
            
        elif stone=="terrorStone":
            for hero in self.heroes:
                hero.stunR = RB[stone].data
            self.msgManager.addMsg( ("Terror Stone has been activated.","恐惧符石已激活。"), type="ctr", duration=120, 
                                    icon=pygame.image.load("image/runestone/terrorStone.png") )
            
        elif stone=="hopeStone":
            for hero in self.heroes:
                hero.heal_bonus = RB[stone].data
            self.msgManager.addMsg( ("Hope Stone has been activated.","希望符石已激活。"), type="ctr", duration=120, 
                                    icon=pygame.image.load("image/runestone/hopeStone.png") )
            
        elif stone=="luckyStone":
            for hero in self.heroes:
                for i in range(RB[stone].data):
                    item = choice( ["fruit"] + PB[self.stg] )    # select from fruit+2 chapter props
                    hero.bagpack.incItem(item, 1)
                    startPos = [self.bg_size[0]//2+i*100, 80+i*40]
                    substance = ChestContent(item, hero.bagpack.readItemByName(item)[1], 2, startPos, hero.slot.slotDic["bag"][1])
                    hero.eventList.append( substance )
            self.msgManager.addMsg( ("Lucky Stone has been activated.","幸运符石已激活。"), type="ctr", duration=120, 
                                    icon=pygame.image.load("image/runestone/luckyStone.png") )
            
        else:
            self.msgManager.addMsg( ("No runestone is used.","未使用符石。"), type="ctr", duration=120, 
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
            self.nature = Nature(self.bg_size, self.stg, 8, 1)
        elif self.stg == 2:
            self.nature = Nature(self.bg_size, self.stg, 4, 0)
        elif self.stg == 3:
            self.nature = Nature(self.bg_size, self.stg, 8, 1)
        elif self.stg == 4:
            self.nature = Nature(self.bg_size, self.stg, 18, 0)
        elif self.stg == 5:
            self.nature = Nature(self.bg_size, self.stg, 10, -1)
        elif self.stg == 6:
            self.nature = Nature(self.bg_size, self.stg, 8, 1)
        elif self.stg==7:
            self.nature = Nature(self.bg_size, self.stg, 18, 0)
    
    def _initSideBoard(self):
        '''
        Initialize the shading board of both sides.
        '''
        sideBoard = pygame.image.load("image/sideBoard.png").convert_alpha()
        sideBoardRect = sideBoard.get_rect()
        sideBoardRect.top = 0
        sideBoardRect.right = self.screenRect.left
        self.trueScreen.blit(sideBoard, sideBoardRect)
        sideBoardRect.left = self.screenRect.left + self.screenRect.width-1
        self.trueScreen.blit(sideBoard, sideBoardRect)

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
            self.addTXT( line, 0, (30,30,30), 0, topAlign )
            topAlign += 20
        self.addTXT(["Game paused, press [ENTER] to continue.","游戏已暂停，按【回车】键继续。"],1, (255,255,255), 0,120)
        # handle controllers images and click events -----------------------------------
        if self.musicOn:
            self.musicButton.paint(self.screen, self.bg_size[0]-90, 30, pos, label=("music off","关闭音乐"))
        else:
            self.musicButton.paint(self.screen, self.bg_size[0]-90, 30, pos, label=("music on","开启音乐"))
        self.quitButton.paint(self.screen, self.bg_size[0]-150, 30, pos, label=("quit","放弃"))
            
        return alter
    
    def _resetHeroes(self, onlayer=0, side="left"):
        # 左下的情况：默认值
        # 右上的情况：onlayer=self.tower.layer, side="right"
        # side还可取center
        for hero in self.heroes:
            # Relocate hero
            hero.onlayer = onlayer
            hero.resetPosition( self.tower, layer=onlayer-1, side=side )
            # RENEW CHECKLIST
            hero.renewCheckList(self.tower.groupList["0"], clear=True)
            hero.renewCheckList(self.tower.chestList)
            hero.renewCheckList(self.tower.elemList)
    
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
            # hitted target died.
            if hitInfo[3]:
                # 给rewardee分配金币
                self.tower.addCoins( hitInfo[4], hitInfo[0], rewardee )
                # 若在怪物图鉴中
                if (hitInfo[3] in self.monsAcc):
                    # 吸血效果
                    if self.using_stone=="bloodStone" and hero==rewardee:
                        self.spurtCanvas.addSpatters( 5, [2,3,4], [14,16,18], (190,255,190), getPos(rewardee,0.5,0.4), True )
                        rewardee.recover(self.HPSteal)
                    # 尝试收集该monster: 若已收集，则返回False；否则收集成功，返回True
                    if self.monsAcc[ hitInfo[3] ].collec():
                        self.msgManager.addMsg( ("New monster collected to Collection!","新的怪物已收集至图鉴！") )
                # 计入统计数据
                self._addStat(hitInfo[3])
            # 暴击效果
            if hitInfo[5]:
                self._addVib(4)
        hero.preyList.clear()
    
    # ---- show feedback of hero motion ----
    def showMsg(self):
        for msg in self.msgList:
            if msg[2] == 0:     # 倒计时减为0时从列表删除
                self.msgList.remove(msg)
                continue
            else:
                if self.translation[1]:
                    msg[0] = (msg[0][0], msg[0][1]+self.translation[1])
                elif self.translation[0]:
                    msg[0] = (msg[0][0]+self.translation[0], msg[0][1])
                ctr = ( msg[0][0]-self.bg_size[0]//2, msg[0][1]-self.bg_size[1]//2-(60-msg[2]) )
                if len(msg)==4:
                    self.addTXT( [msg[1]]*2, 0, (0,255,0), ctr[0], ctr[1])      # green
                else:
                    self.addTXT( [msg[1]]*2, 0, (255,255,255), ctr[0], ctr[1])  # white
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
    
    def translate(self, mode="vertical"):
        """
        translate all elements.
        param mode: 'horrizontal' or 'vertical'.
        """
        if mode=="horrizontal":
            # check horrizontal translation (level):
            self.translation[0] = 0
            if self.avgPix2<self.tower.boundaries[0]:
                if self.tower.boundaries[0]<self.blockSize*3:
                    self.translation[0] = 2
            elif self.avgPix2>self.tower.boundaries[1]:
                if self.tower.boundaries[1]>self.bg_size[0]-self.blockSize*3:
                    self.translation[0] = -2
            else:
                gap = ( self.bg_size[0] - (self.tower.boundaries[0]+self.tower.boundaries[1]) ) //2
                if gap:
                    self.translation[0] = min(gap, 2) if gap>0 else max(gap, -2)
            self.tower.level(self.translation[0])
            self.spurtCanvas.level(self.translation[0])
            for each in self.supplyList:
                each.level(self.translation[0])
            for hero in self.heroes:
                hero.level(self.translation[0])
        elif mode=="vertical":
            # check vertical translation (lift):
            gap = self.bg_size[1]//2 - self.avgPix  # 中线减去英雄水平线之差
            if (self.tower.getTop("min")+self.blockSize<=self.bg_size[1] and gap<0) or (self.tower.getTop("max")>=0 and gap>0):
                # 若屏幕下侧已经触塔底还想下降，或上侧已经到塔顶还要上升，都应阻止
                self.translation[1] = 0
            else:
                self.translation[1] = gap//SCRINT if gap>=0 else gap//SCRINT+1
            
            self.tower.lift(self.translation[1])
            self.spurtCanvas.lift(self.translation[1])
            # lift bg paper
            if self.translation[1]>0 and self.BGRect.top<0:
                self.BGRect.top += 1
            elif self.translation[1]<0 and self.BGRect.bottom>self.bg_size[1]:
                self.BGRect.top -= 1
            for each in self.supplyList:
                each.lift(self.translation[1])
            for hero in self.heroes:
                hero.lift(self.translation[1])
        
    def checkVibrate(self):
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
        
    def checkHeroKeyDown(self, hero, key):
        if ( key == hero.keyDic["shootKey"] ):    # 射击
            hero.shoot( self.tower, self.spurtCanvas )
        elif ( key == pygame.K_r):
            hero.reload(self.delay, self.spurtCanvas)
        elif ( key == hero.keyDic["jumpKey"] ):   # 跳跃
            # 若在下一porter处按跳跃键，且封锁已解除，则进入下一区域
            if self.tower.porter and (hero.onlayer >= self.tower.layer) and pygame.sprite.collide_mask(hero, self.tower.porter) \
                and (not self.tower.porter.locked) and self.tower.porter.category=="door":
                self._shiftTower( to=1 )
                # 若进入的是new area，则将区域dialogue加入消息列表。
                if self.curArea not in self.remindedArea:
                    self.remindedArea.append(self.curArea)
                    for msg in self.plotManager.getPre(self.areaList[self.curArea].area):
                        self.msgManager.addMsg( msg, type="dlg" )
            # 否则，在上一porter处按跳跃键，则返回上一区域
            elif self.tower.backporter and (hero.onlayer<=0) and pygame.sprite.collide_mask(hero, self.tower.backporter) \
                and (not self.tower.backporter.locked):
                self._shiftTower( to=-1 )
            # 否则，在人质处按跳跃键，招募人质
            elif self.hostage and pygame.sprite.collide_mask(hero, self.hostage):
                # 将hostage激活，并加入heroes队列（插入队首）。
                self.hostage.activate(hero, self.tower)
                self.heroes.insert(0, self.hostage)
                # 清空原来的归属关系。
                self.hostage.kill()
                self.hostage = None
            # 否则，是正常的跳跃行为
            else:
                if ( hero.k1 > 0 ) and ( hero.k2 == 0 ):
                    hero.k2 = 1
                elif not hero.trapper and hero.aground and ( hero.k1 == 0 ):
                    hero.k1 = 1
        elif ( key == hero.keyDic["superKey"] ):  # 超级技能
            hero.castSuperPower(self.spurtCanvas)
        elif ( key == hero.keyDic["itemKey"] ):   # 使用背包物品
            ret = hero.useItem( self.spurtCanvas )
            if ret:
                self.msgManager.addMsg( ret, urgent=True )
        elif ( key == hero.keyDic["downKey"] ):   # 下跳
            if not hero.oneInEffect("copter"):
                hero.shiftLayer(-2, self.tower.heightList)
                hero.aground = False
        elif ( key == hero.keyDic["bagKey"] ) and len(self.effecter.SSList)==0:     # 切换背包物品
            hero.bagpack.shiftItem()
            self.effecter.addSwitch(hero.slot.bagShad[0], hero.slot.bagShad[1], 1, 50, 0)

    def checkShopKeyDown(self, hero, key):
        if ( key == self.hero.keyDic["leftKey"] ):
            self.buyNum = max(self.buyNum-1, -1)
        elif ( key == self.hero.keyDic["rightKey"] ):
            self.buyNum = min(self.buyNum+1, 1)
        elif ( key == self.hero.keyDic["itemKey"] ):
            res = self.tower.merchant.sell(self.buyNum, self.hero, self.spurtCanvas)
            if res:
                if isinstance(res,str): # 无尽模式特有：购买侍从
                    p = [choice(self.tower.boundaries), self.tower.getTop(self.tower.extLayer+1)]
                    servant = myHero.Servant(self.hero, self.VServant, p, self.fntSet[1], self.language, self.hero.onlayer)
                    servant.renewCheckList(self.tower.groupList["0"])
                    self.heroes.insert(0, servant)
                else:
                    self.supplyList.add( res )
            else:
                self.msgManager.addMsg( ("You don't have enough coins.","你的金币数量不足。"), urgent=True )
        elif ( key == self.hero.keyDic["bagKey"] ):
            if self.hero.coins>=self.tower.merchant.refreshCost:  # coin足够
                self.hero.coins -= self.tower.merchant.refreshCost
                for key in self.tower.merchant.goods:
                    self.tower.merchant.goods[key] = None
                self.tower.merchant.updateGoods(self.stg, self.hero, canvas=self.spurtCanvas)
            else:
                self.msgManager.addMsg( ("You don't have enough coins.","你的金币数量不足。"), urgent=True )

    def paint(self, slotHeroes):
        """
        paint all elements according to specific order.
        param slotHeroes: a list. Contains all heroes whose slots should be painted.
        """
        # Repaint & translate all elements
        self.screen.blit( self.BG, self.BGRect )
        # Repaint this tower and situate heroes
        self.tower.paint(self.screen, heroes=self.heroes)
        # Repaint Natural Impediments of the stage
        self.specifier.paint(self.screen)
        self.spurtCanvas.updateHalo(self.screen)
        # draw hero status info.
        for hero in slotHeroes:
            hero.drawHeads( self.screen )
            if hero.category == "hero":
                hero.slot.paint(self.screen, self.effecter, self.addSymm, self.addTXT)
        
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

# ===================================
# UI object to paint left-bottom corner panel of a hero
class HeroSlot():
    def __init__(self, number, heroRef, VHero, bg_size, coinIcon, extBar=""):
        if number=="p1":    # 此处的基点坐标均为头像栏左上角
            base = (0, bg_size[1]-84)
        elif number=="p2":
            base = (bg_size[0]//2, bg_size[1]-84)
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
        self.coinIcon = coinIcon
        # center Positions of all components
        self.ctrDic = {}
        for item in self.slotDic:
            rect = self.slotDic[item][1]
            self.ctrDic[item] = ( rect.left+rect.width//2-bg_size[0]//2, rect.top+rect.height//2-bg_size[1]//2 )  # 用于适配model的绘图函数addSymm所设定的中心点
    
    def paint(self, screen, effecter, addSymm, addTXT):
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
                    addSymm( itemImg, pos[0], pos[1] )
                    numPos = (pos[0]+10, pos[1]-20)
                    pygame.draw.circle(screen, (255,10,10), (numPos[0]+screen.get_width()//2,numPos[1]+screen.get_height()//2), 8)
                    addTXT( (str(itemNum),str(itemNum)), 1, (255,255,255), numPos[0], numPos[1] )
                effecter.doSwitch( screen )
            elif obj=="coin":
                addSymm( self.coinIcon, self.ctrDic["coin"][0]-20, self.ctrDic["coin"][1] )
                addTXT( (str(self.owner.coins), str(self.owner.coins)), 1, (255,255,255), self.ctrDic["coin"][0]+10, self.ctrDic["coin"][1] )

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

# =================================================================================
# ----------------------------- game running classes ------------------------------
# =================================================================================
class AdventureModel(GameModel):
    towerD = 10
    towerH = 20
    remindedArea = []
    translation = []      # allElements的平移信息
    heroes = []           # 保存hero对象的引用；可能为1个或2个
    tomb = []
    win = False           # 标记最终结果
    curArea = 0
    # 双人模式的特殊变量
    avgPix = 0            # 两者中的较高像素值d
    avgLayer = 0          # 两者中的较高层数
    tower = None
    plotManager = None    # 管理剧情信息
    hostage = None

    def __init__(self, stg, heroList, screen, language, fntSet, diffi, monsDic, VHostage, stone="VOID"):
        """
        heroInfoList: 一个列表，每项是一个hero信息，每一项信息包括heroNo和该hero的keyDic。即形如：[ (heroNo1, keyDic1), (heroNo2, keyDic2) ]。可为1-2个
        monsDic: 当前stage的所有monster名及其VMons对象组成的字典
        """
        GameModel.__init__(self, stg, screen, language, fntSet, monsDic)
        self.init_BG(self.stg)
        self._initNature()

        # Initialize game canvas.
        if self.stg == 1:
            bgColors = ( (200,160,120), (180,140,90), (170,130,80), (190,150,100) )
            bgShape = "rect"
        elif self.stg == 2:
            bgColors = ( (190,210,210), (140,180,180), (110,140,140), (130,160,160) )
            bgShape = "circle"
        elif self.stg == 3:
            bgColors = ( (170,120,190), (100,70,120), (120,70,140), (100,60,120) )
            bgShape = "circle"
        elif self.stg == 4:
            bgColors = ( (130,155,75), (100,135,60), (100,125,75), (100,145,85) )
            bgShape = "circle"
        elif self.stg == 5:
            bgColors = ( (200,160,120), (170,130,80), (170,130,80), (190,150,100) )
            bgShape = "circle"
        elif self.stg == 6:
            bgColors = ( (200,160,120), (180,140,90), (170,130,80), (190,150,100) )
            bgShape = "rect"
        elif self.stg==7:
            bgColors = ( (160,165,170), (100,110,110), (80,100,100), (90,110,110) )
            bgShape = "rect"
        
        # 难度初始化
        if diffi == 0:          # Easy
            dmgReduction = 0.7
            enemy.Monster.healthBonus = 0.7
            doubleP = 0.12
        if diffi == 1:          # Normal
            dmgReduction = 1
            enemy.Monster.healthBonus = 1
            doubleP = 0.1
        elif diffi == 2:        # Heroic
            dmgReduction = 1.5  # 受伤加成
            enemy.Monster.healthBonus = 1.5
            doubleP = 0.08      # chest爆率翻倍的概率
        self.towerH = 14        # 首个区域层数：7，随后每个区域随机+2或保持相同

        # create the map ------------------ 🏯
        self.towerD = 10
        oriPos = ( (self.bg_size[0] - self.towerD*self.blockSize) // 2, self.bg_size[1]-self.blockSize )
        self.areaList = []
        # Determine the specialwall distribution.
        if self.stg in [1,6]:
            specialOn = (False, True, False, True, True)
        else:
            specialOn = (True, True, False, True, True) 
        # Build 5 areas and link them as one big tower.
        for i in range(0,5):
            if i==2:
                sp_pos = (oriPos[0]+self.blockSize, oriPos[1])
                tower = AdventureTower(sp_pos, self.blockSize, self.towerD-2, 4, self.stg, i, False, doubleP, self.fntSet[1], self.language, bgColors, bgShape, self.bg_size)
                tower.generateMap()
                tower.addNPC("merchant", heroList[0][1])
            else:
                tower = AdventureTower(oriPos, self.blockSize, self.towerD, self.towerH, self.stg, i, specialOn[i], doubleP, self.fntSet[1], self.language, bgColors, bgShape, self.bg_size)
                tower.generateMap()
                self.towerH += choice( [0,2] )
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
            self.heroes.insert(0, hero)
        self._resetHeroes(onlayer=0, side="left")
        # Initialize towers, monsters and heroes.
        for tower in self.areaList:
            # add elems of each area to the allElements and hero's checkList.
            for sup in tower.chestList:
                if sup.category == "hostage":
                    # 移除原Porter类型的hostage
                    pos = (sup.rect.left, sup.rect.bottom)
                    tower.chestList.remove(sup)
                    # 将hostage转变为Hero类型对象，并挂在self.hostage上，等待被玩家激活
                    sup = self.hostage = myHero.Follower(pos, VHostage, self.fntSet[1], self.language)
                    tower.chestList.add(self.hostage)
                tower.allElements["dec0"].add(sup)  # 加入supply
            for key in tower.groupList:
                if key=="-2":
                    for brick in tower.groupList[key]:
                        tower.allElements["dec0"].add( brick )   # 装饰
                else:
                    for brick in tower.groupList[key]:
                        tower.allElements["dec1"].add( brick )   # 砖块
            # create monsters for each area, method.
            if tower.area in [0,1,3,4]:
                # making chapter impediments
                if self.stg==1:
                    for i in range(2):
                        f = enemy.InfernoFire(self.bg_size)
                        tower.allElements["mons2"].add( f )
                elif self.stg==2:
                    c = enemy.Column(self.bg_size)
                    tower.allElements["mons1"].add( c )
                elif self.stg==7:
                    pos = ( randint(tower.boundaries[0]+80, tower.boundaries[1]-80), tower.getTop("max") )
                    l = enemy.Log(self.bg_size, tower.layer-1, pos)
                    tower.allElements["mons1"].add( l )
                # making monsters
                for entry in CB[self.stg][tower.area]:
                    if entry==None:
                        continue
                    if entry[0] in (5,6): #Boss or vice-Boss
                        gl = True
                    else:
                        gl = False
                    sl = entry[2] if type(entry[2])==int else tower.layer+int(entry[2])
                    el = entry[3] if type(entry[3])==int else tower.layer+int(entry[3])
                    makeMons( sl, el, entry[1], entry[0], tower, goalie=gl )
            # assign monsters to correct allElements group.
            for minion in tower.monsters:
                if minion.category in MONS2:
                    tower.allElements["mons2"].add(minion)
                elif minion.category in MONS0:
                    tower.allElements["mons0"].add(minion)
                else:
                    tower.allElements["mons1"].add(minion)
            # directly unlock the porter if the area is not kept by keepers
            if len(tower.goalieList)==0:
                tower.porter.unlock()
            # Special chapter items.
            for elem in tower.elemList:
                tower.allElements["dec1"].add(elem)
                if self.stg in (2,6):   # 第二关的monsters加上障碍物大石头、蛛网；第六关的刀扇。
                    tower.monsters.add(elem)
        self.supplyList = pygame.sprite.Group()     # Store all flying supplies objects.
        
        # 章节特殊内容管理器
        if self.stg==1:
            self.specifier = Stg1Specifier()
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
            self.specifier.addDrip( self.areaList[choice([0,1,3,4])] )
        elif self.stg==7:
            self.specifier = Stg7Specifier(self.VServant)
            self.specifier.bind(self.areaList[-1].monsters)
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
        # Play bgm
        if self.stg in (1,2):
            pygame.mixer.music.load(f"audio/stg1-2BG.wav")
        elif self.stg in (3,4):
            pygame.mixer.music.load(f"audio/stg3-4BG.wav")
        else:
            pygame.mixer.music.load(f"audio/stg{self.stg}BG.wav")
        pygame.mixer.music.set_volume(vol/100)
        pygame.mixer.music.play(loops=-1)

        #self.screen.fill( (0, 0, 0) )
        self.tip = choice( self.plotManager.tips )
        self.translation = [0,0]
        
        self._initSideBoard()   # Paint two sideBoards
        pygame.display.flip()
        #self.heroes[0].bagpack.incItem("rustedHorn", 10)
        #self.heroes[0].bagpack.incItem("torch", 10)

        while self.gameOn:
            
            # Repaint all elements.
            self.paint(self.heroes)
            
            pos = pygame.mouse.get_pos()
            pos = (pos[0]-self.screenRect.left, pos[1])     # 从实际窗口转到虚拟窗口的偏差
            
            # If not paused, 以下是 Action Layer ===============================================
            if not self.paused:
                
                # Check if the screen needs to be adjusted.
                self.translate(mode="vertical")

                # check hero's ㅌ & fall, msg.
                self.avgPix = self.avgLayer = valid_hero = 0
                for hero in self.heroes:
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
                        self._collectHitInfo(hero, hero.master)
                        # hero.reload( self.delay, self.spurtCanvas )
                        win = hero.decideAction(self.delay, self.tower, self.spurtCanvas)
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
                                elif item.name in hero.bagpack.itemDic:
                                    self.msgManager.addMsg( hero.bagpack.itemDic[item.name], type="item", urgent=True )
                            else:
                                self.spurtCanvas.addSpatters(3, (1,2,3), (16,18,20), (255,255,0), getPos(hero,0.5,0.4) )
                        hero.eventList.clear()
                        hero.reload2( self.delay, self.spurtCanvas )
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
                if self.tower.porter.locked and len(self.tower.goalieList)==0:
                    self.tower.porter.unlock()
                    self.msgManager.addMsg( ("Door Opened","连接门已开启"), type="ctr", duration=120 )
                # 输赢事件。
                if self.checkFailure():     # 检查所有英雄的情况
                    self.endGame(False, inst=False)
                self._checkEnd()
                
                if self.stg==3:
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
                        self.heroes.insert(0, serv)
                    # 管理滚木
                    self.specifier.manageLogs(self.tower, self.bg_size)

                self.checkVibrate()
                                
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
            self.msgManager.run(self.paused)
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
                            self.checkHeroKeyDown(hero, event.key)
                    # If paused & shopping.
                    elif self.shopping:
                        for hero in self.heroes:
                            if hero.category != "hero":
                                continue
                            self.checkShopKeyDown(hero, event.key)
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
            self.paint(self.heroes+self.tomb)
            
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
                if hero.category != "hero":
                    continue
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
            self.msgManager.run(self.paused)
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
        for tower in self.areaList:
            #print(sys.getrefcount(tower))
            for grp in tower.allElements:
                for each in tower.allElements[grp]:
                    each.kill()
                    del each
        del self.tower, self.areaList

    # --- paint upper banner (contains 4 sections) ---
    def _renderBanner(self, pos):
        # paint 4 background sections and get their rect.
        sect1 = drawRect(0, 10, 100, 40, (0,0,0,180), self.screen)    # Area & Goalie Information.
        sect2 = drawRect(self.bg_size[0]-60, 10, 60, 40, (0,0,0,180), self.screen)  # Pause.
        # give banner info.
        ctr = (sect1.left+sect1.width//2-self.bg_size[0]//2, sect1.top+sect1.height//2-self.bg_size[1]//2)  # 更改为中心坐标系统的中心点参数
        offX, offY = 24, 9
        if self.tower.porter.locked:
            self.addSymm( pygame.image.load("image/goalie.png").convert_alpha(), ctr[0]-offX, ctr[1] )
        else:
            self.addSymm( pygame.image.load("image/active.png").convert_alpha(), ctr[0]-offX, ctr[1] )
        self.addTXT( ("Area","区域"), 1, (255,255,255), ctr[0]+offX, ctr[1]-offY )
        self.addTXT( [f"{self.tower.area+1}/5"]*2, 1, (255,255,255), ctr[0]+offX, ctr[1]+offY )

        ctr = (sect2.left+sect2.width//2, sect2.top+sect2.height//2)
        if not self.paused:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("pause","暂停"))
        else:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("play","继续"))
        
        return (sect1, sect2)


# =================================================================================
class EndlessModel(GameModel):
    towerD = 11
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
        Statue.spurtCanvas = self.spurtCanvas

        # Other Settings
        self.keyDic = keyDic
        self.alertSnd = pygame.mixer.Sound("audio/alert.wav")
        self.rebuildColor = (20,50,20)
        bgColors = ( (170,190,170), (150,180,150), (110,130,110), (100,120,100) )
        bgShape = "rect"
        self.effecter = ImgSwitcher()
        self.msgManager = MsgManager(self.fntSet[1], 0, mode="top")

        enemy.Monster.healthBonus = 1
        self.wave = 0
        self.cntDown = 5
        self.status = "alarm"     # 4 values: alarm/前奏倒计时 -> create/生成怪物 -> battle/等待战斗完成 -> shop/购买 ->循环
        self.tower = EndlessTower(self.bg_size, self.blockSize, self.towerD, stg, self.fntSet[1], self.language, bgColors, bgShape)
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
        self.pool = Pool(self.tower.bg_size, self.tower.blockSize*2-36, self.tower.boundaries)
        self.tower.allElements["dec1"].add(self.pool)
        self.heroes.insert(0, self.tower.statue)
        # create servant
        #initPos = [choice(self.tower.boundaries), self.tower.getTop(self.tower.extLayer+1)]
        #servant = myHero.Servant(self.hero, self.VServant, initPos, self.fntSet[1], self.language, self.hero.onlayer)
        #servant.renewCheckList(self.tower.groupList["0"])
        #self.heroes.insert(0, servant)
        
        self.supplyList = pygame.sprite.Group()     # Store all flying supplies objects.
        # Shopping Section. -----------------------------------
        self.shopping = False
        self.buyNum = 0     # 购买物品时的序号，可取-1,0,1

        self.stg = stg
        self.bondSpecif()
        self._initNature()
        self.endCnt = -1    # -1表示游戏结束条件未触发 # 结束后的动画时间默认为60

        # using stone
        self.init_stone(stone)
        self.msgManager.addMsg( ("Protect the King's Statue! ... and yourself.","保护国王石像！……也保护好自己。") )

    def go(self, horns, heroBook, stgManager, setManager, vol, task):
        pygame.mixer.music.load("audio/stg7BG.wav")    # Play bgm
        pygame.mixer.music.set_volume(vol/100)
        pygame.mixer.music.play(loops=-1)

        self.translation = [0,0]
        self.tip = choice( self.plotManager.tips )
        self.screen.fill( (0, 0, 0) )
        
        self._initSideBoard()   # Paint two sideBoards
        pygame.display.flip()
        # make a queue that stores coming monsters. format: [ballObj, monsObj]
        self.monsQue = []
        # Give one defense tower.
        #self.hero.bagpack.incItem("defenseTower", 1)

        while self.gameOn:
            
            # repaint all elements
            self.paint(self.heroes)

            for ball, pair in self.monsQue:
                self.screen.blit(ball.image, ball.rect)

            pos = pygame.mouse.get_pos()
            pos = (pos[0]-self.screenRect.left, pos[1])     # 从实际窗口转到虚拟窗口的修正

            if not self.paused:
                
                self.avgPix2 = self.hero.rect.left + self.hero.rect.width//2
                self.avgLayer = self.hero.onlayer
                # move all if the screen need to be adjusted.
                self.translate(mode="horrizontal")
                
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
                        elif item.name in self.hero.bagpack.itemDic:
                            self.msgManager.addMsg( self.hero.bagpack.itemDic[item.name], type="item", urgent=True )
                    else:
                        self.spurtCanvas.addSpatters(4, (2,3,4), (18,20,22), (255,255,0), getPos(self.hero,0.5,0.4) )
                self.hero.eventList.clear()
                # self.hero.reload( self.delay, self.spurtCanvas )

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
                        self.heroes.insert(0, serv)
                    # 管理滚木
                    self.specifier.manageLogs(self.tower, self.bg_size)
                
                self.checkVibrate()
                                
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
            self.msgManager.run(self.paused)
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
                            self.checkHeroKeyDown(hero, event.key)
                    elif self.shopping:
                        self.checkShopKeyDown(hero, event.key)
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
            # Repaint all elements.
            self.paint(self.heroes)

            drawRect( 0, 0, self.bg_size[0], self.bg_size[1], stgManager.themeColor[self.stg], self.screen )
            drawRect( 0, 160, self.bg_size[0], 70, (0,0,0,40), self.screen )

            self.addTXT( self.comment, 2, (255,255,255), 0, -180)
            self.addTXT( ("Survived Waves: %d" % self.wave,"本次存活：%d波" % self.wave), 3, (255,255,255), 0, -150)
            self.addTXT( ("Previous best: %d" % stgManager.getHigh(),"历史最佳：%d" % stgManager.getHigh()), 2, (255,255,255), 0, -100)

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
            self.msgManager.run(self.paused)
            self.msgManager.paint(self.screen)

            self.trueScreen.blit(self.screen, self.screenRect)
            pygame.display.flip()   # from buffer area load the pic to the screen
            self.clock.tick(60)

    def bondSpecif(self):
        self.plotManager = Dialogue(self.stg)
        # Select and overlap the moveMons() method & Add Natural Impediments for different stages.
        if self.stg==1:
            self.specifier = Stg1Specifier()
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
                    new_mons = makeMons( self.tower.layer-2, self.tower.layer, 1, 6, self.tower, join=False )[0]
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
                self.msgManager.addMsg( ("Wave clear! Prepare for next one.","怪物清空！采购物品，为下一波做准备。") )
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
        for grp in self.tower.allElements:
            for each in self.tower.allElements[grp]:
                each.kill()
                del each
        del self.tower

    # --- paint upper banner (contains 3 sections) ---
    def _renderBanner(self, pos):
        # paint 4 background sections and get their rect.
        sect1 = drawRect(0, 10, 120, 40, (0,0,0,180), self.screen)     # Current Wave.
        sect2 = drawRect(0, 60, 120, 40, (0,0,0,180), self.screen)     # Next wave count down.
        sect3 = drawRect(self.bg_size[0]-60, 10, 60, 40, (0,0,0,180), self.screen)    # Menu Option.
        # give banner info.
        ctr = (sect1.left+sect1.width//2-self.bg_size[0]//2, sect1.top+sect1.height//2-self.bg_size[1]//2)  # 更改为中心坐标系统的中心点参数
        self.addSymm( pygame.image.load("image/goalie.png").convert_alpha(), sect1.left+20-self.bg_size[0]//2, ctr[1] )
        self.addTXT(("Wave","当前波数"), 1, (255,255,255), ctr[0]+20, ctr[1]-9)
        self.addTXT( [str(self.wave)]*2, 1, (255,255,255), ctr[0]+20, ctr[1]+9)

        ctr = (sect2.left+sect2.width//2-self.bg_size[0]//2, sect2.top+sect2.height//2-self.bg_size[1]//2)  # 更改为中心坐标系统的中心点参数
        self.addSymm( pygame.image.load("image/timer.png").convert_alpha(), sect2.left+20-self.bg_size[0]//2, ctr[1] )
        txtColor = (255,180,180) if self.cntDown<=3 else (180,255,180)
        self.addTXT(("Next In","距离下波"), 1, txtColor, ctr[0]+20, ctr[1]-9)
        self.addTXT( [str(self.cntDown)]*2, 1, txtColor, ctr[0]+20, ctr[1]+9)

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


# =================================================================================
class TutorialModel(GameModel):
    towerD = 10
    towerH = 20
    remindedArea = []
    translation = []      # allElements的平移信息
    heroes = []           # 保存hero对象的引用；可能为1个或2个
    tomb = []
    win = False           # 标记最终结果
    curArea = 0
    # 双人模式的特殊变量
    avgPix = 0            # 两者中的较高像素值d
    avgLayer = 0          # 两者中的较高层数
    tower = None
    plotManager = None

    def __init__(self, heroList, screen, language, fntSet, diffi, monsDic, tutor_on=True, stone="VOID"):
        """
        heroInfoList: 一个列表，每项是一个hero信息，每一项信息包括heroNo和该hero的keyDic。即形如：[ (heroNo1, keyDic1), (heroNo2, keyDic2) ]。可为1-2个
        monsDic: 当前stage的所有monster名及其VMons对象组成的字典
        """
        GameModel.__init__(self, 0, screen, language, fntSet, monsDic)
        self.init_BG(2)
        self.stg = 3
        self._initNature()

        # Initialize game canvas.
        bgColors = ( (170,190,170), (150,180,150), (110,130,110), (100,120,100) )
        bgShape = "rect"
        
        # 难度初始化(normal)
        dmgReduction = 1
        enemy.Monster.healthBonus = 1

        # create the map ------------------ 🏯
        self.towerD = 10
        self.areaList = []
        # make tutorial tower:
        tut_tower = TutorialTower(self.blockSize, self.towerD, self.fntSet[1], self.language, bgColors, bgShape, self.bg_size)
        tut_tower.generateMap()
        self.areaList.append( tut_tower )
        
        self.tower = self.areaList[0]
        # create the hero -----------------
        self.heroes = []
        self.tomb = []
        for each in heroList:      # 根据VHero参数信息生成hero
            hero = myHero.Hero( each[0], dmgReduction, self.fntSet[1], self.language, keyDic=each[1] )
            hero.spurtCanvas = self.spurtCanvas          # In case of injury.
            hero.slot = HeroSlot(each[2], hero, each[0], self.bg_size, self.coinIcon, extBar="LDBar")
            self.heroes.insert(0, hero)
        self._resetHeroes(onlayer=0, side="center")
        # Initialize towers, monsters and heroes.
        for tower in self.areaList:
            # add elems of each area to the allElements and hero's checkList.
            for sup in tower.chestList:
                tower.allElements["dec0"].add(sup)  # 加入supply
            for key in tower.groupList:
                if key=="-2":
                    for brick in tower.groupList[key]:
                        tower.allElements["dec0"].add( brick )   # 装饰
                else:
                    for brick in tower.groupList[key]:
                        tower.allElements["dec1"].add( brick )   # 砖块
            # create monsters for each area, method.
            # if tower.area in [0,1,3,4]:
            #     # making monsters
            #     for entry in CB[self.stg][tower.area]:
            #         if entry==None:
            #             continue
            #         if entry[0] in (5,6): #Boss or vice-Boss
            #             gl = True
            #         else:
            #             gl = False
            #         sl = entry[2] if type(entry[2])==int else tower.layer+int(entry[2])
            #         el = entry[3] if type(entry[3])==int else tower.layer+int(entry[3])
            #         makeMons( sl, el, entry[1], entry[0], tower, goalie=gl )
            # assign monsters to correct allElements group.
            # for minion in tower.monsters:
            #     if minion.category in MONS2:
            #         tower.allElements["mons2"].add(minion)
            #     elif minion.category in MONS0:
            #         tower.allElements["mons0"].add(minion)
            #     else:
            #         tower.allElements["mons1"].add(minion)
            # directly unlock the porter if the area is not kept by keepers
            #if len(tower.goalieList)==0:
            #    tower.porter.unlock()
            # Special chapter items.
            for elem in tower.elemList:
                tower.allElements["dec1"].add(elem)
        self.supplyList = pygame.sprite.Group()     # Store all flying supplies objects.
        
        # 章节特殊内容管理器
        self.specifier = TutorialSpecifier(self.heroes[0], self.areaList[0], self.VServant, tutor_on)
        # Shopping Section. -----------------------------------
        self.shopping = False
        self.buyNum = 0     # 购买物品时的序号，可取-1,0,1
        self.pause_sec = 0

        # Effect Manager.
        self.effecter = ImgSwitcher()
        self.msgManager = MsgManager(self.fntSet[1], self.stg, mode="top")
        # using stone ---------------------------------------
        self.init_stone(stone)

        self.endCnt = -1    # -1表示正常运行

    def go(self, horns, heroBook, stgManager, diffi, vol, task):
        # Play bgm
        pygame.mixer.music.load(f"audio/stg1-2BG.wav")
        pygame.mixer.music.set_volume(vol/100)
        pygame.mixer.music.play(loops=-1)

        self.plotManager = Dialogue(0)
        self.tip = choice( self.plotManager.tips )
        self.translation = [0,0]
        
        self._initSideBoard()   # Paint two sideBoards
        pygame.display.flip()
        #self.heroes[0].bagpack.incItem("rustedHorn", 10)
        #self.heroes[0].bagpack.incItem("torch", 10)

        while self.gameOn:
            
            # Repaint & translate all elements.
            self.paint(self.heroes)
            
            pos = pygame.mouse.get_pos()
            pos = (pos[0]-self.screenRect.left, pos[1])     # 从实际窗口转到虚拟窗口的偏差
            
            # If not paused, 以下是 Action Layer ===============================================
            if not self.paused:
                # move all if the screen need to be adjusted.
                self.translate(mode="vertical")

                # check hero's jump & fall, msg.
                self.avgPix = self.avgLayer = valid_hero = 0
                for hero in self.heroes:
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
                            elif item.name in hero.bagpack.itemDic:
                                self.msgManager.addMsg( hero.bagpack.itemDic[item.name], type="item", urgent=True )
                        else:
                            self.spurtCanvas.addSpatters(3, (1,2,3), (16,18,20), (255,255,0), getPos(hero,0.5,0.4) )
                    hero.eventList.clear()
                    # hero.reload( self.delay, self.spurtCanvas )
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
                # 事件：区域通过。有的怪物（如戈仑石人）存在死亡延迟，故在杀死怪物的时候再判断不准确，需时刻侦听。
                #if self.tower.porter.locked and len(self.tower.goalieList)==0:
                #    self.tower.porter.unlock()
                #    self.msgManager.addMsg( ("Door Opened","连接门已开启"), type="ctr", duration=120 )
                #if self.specifier.tutorStep==len(self.specifier.tipDic) and self.win==False:
                #    self.win = True
                #if pygame.sprite.collide_mask(hero, self.tower.porter) and not self.heroes[0].aground:
                #    self.endGame(self.win, inst=True)
                
                if len(self.heroes)>0:
                    if self.specifier.servant:
                        self.specifier.servant.checkImg(self.delay, self.tower, self.heroes, pygame.key.get_pressed(), self.spurtCanvas)
                    res = self.specifier.progressTutor( self.delay, self.heroes[0], self.tower, self.spurtCanvas )
                    if res=="OK":
                        self.msgManager.addMsg( ("Tutorial Complete!","教程已完成！"), type="ctr", duration=120 )
                        self.win = True
                
                self.checkVibrate()
                                
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
            self.msgManager.run(self.paused)
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
                            self.checkHeroKeyDown(hero, event.key)
                    # If paused & shopping.
                    elif self.shopping:
                        for hero in self.heroes:
                            if hero.category != "hero":
                                continue
                            self.checkShopKeyDown(hero, event.key)
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
                            self.endGame(self.win, inst=True)
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
        
        return self.win
    
    def endGame(self, bool, inst=True):
        '''end game with bool (win-True, lose-False)'''
        self.win = bool
        if inst:
            pygame.mixer.music.fadeout(1000)
            self.msgManager.clear()
            self.gameOn = False
        elif self.endCnt<0:    # 只可触发一次：正常为-1
            self.endCnt = 60

    # ---- clear all elements in the model ----
    def clearAll(self):
        for tower in self.areaList:
            #print(sys.getrefcount(tower))
            for grp in tower.allElements:
                for each in tower.allElements[grp]:
                    each.kill()
                    del each
        del self.tower, self.areaList

    # --- paint upper banner (contains 4 sections) ---
    def _renderBanner(self, pos):
        # paint 4 background sections and get their rect.
        sect1 = drawRect(0, 10, 100, 40, (0,0,0,180), self.screen)    # Area & Goalie Information.
        sect2 = drawRect(self.bg_size[0]-60, 10, 60, 40, (0,0,0,180), self.screen)  # Pause.
        # give banner info.
        ctr = (sect1.left+sect1.width//2-self.bg_size[0]//2, sect1.top+sect1.height//2-self.bg_size[1]//2)  # 更改为中心坐标系统的中心点参数
        offX, offY = 0, 9
        if self.specifier.tutorStep==len(self.specifier.tipDic):
            self.addSymm( pygame.image.load("image/active.png").convert_alpha(), ctr[0], ctr[1] )
        self.addTXT( ("Progress","进度"), 1, (255,255,255), ctr[0], ctr[1]-offY )
        self.addTXT( [f"{self.specifier.tutorStep}/{len(self.specifier.tipDic)}"]*2, 1, (255,255,255), ctr[0], ctr[1]+offY )

        ctr = (sect2.left+sect2.width//2, sect2.top+sect2.height//2)
        if not self.paused:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("pause","暂停"))
        else:
            self.menuButton.paint(self.screen, ctr[0], ctr[1], pos, label=("play","继续"))
        
        return (sect1, sect2)


# ---------------------------------------------------------------------------------
# a function to generate monsters for GameModel.
def makeMons(btmLayer, topLayer, amount, mType, tower, join=True, goalie=False):
    '''
    Will directly fill the given tower's Monster Grouplist.
        btmLayer: the layer that only above which would the minions may appear;
        topLayer: the layer by which the minions would stop appearring;
        amount: the total amount of the monsters. They will be scattered between btmLayer & topLayer;
        mType: (number1,2,3,4)indicates what kind of monster you want to make;
        tower: the mapTower Object Reference that will provide many useful variables for the process;
            it contains a SpriteGroup-type container that you wish to fill up with created minions;
        join: whether you wish to directly add the monster into the tower.monsters.
            If False, this func will return a list of newly created monsters.
        goalie: whether to assign all the generated monsters as goalie?
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
                    minion = enemy.Tizilla(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 2:
                    minion = enemy.MegaTizilla(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 3:
                    minion = enemy.Dragon(tower.heightList[group], group, tower.boundaries)
                elif mType == 4:
                    minion = enemy.DragonEgg(tower.groupList[group], tower.groupList["0"], group)
                elif mType == 5:
                    minion = enemy.HellHound(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 6:    # Boss: Crimson Dragon
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
                    minion = enemy.HellHound(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 6:    # Boss: Giant Spider
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
                elif mType == 5:
                    minion = enemy.HellHound(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 6:    # Boss: Vampire
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
                    minion = enemy.HellHound(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 6:    # Boss: Mutated Fungus
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
                    minion = enemy.HellHound(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 6:    # Boss: Frost Titan
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
                elif mType == 5:
                    minion = enemy.HellHound(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 6:    # Boss: War Machine
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
                elif mType == 5:
                    minion = enemy.HellHound(tower.groupList[group], tower.groupList["0"], tower.blockSize, group)
                elif mType == 6:    # Boss: Chicheng
                    minion = enemy.Chicheng(tower.groupList, group, tower.font[1])
            if join:
                tower.monsters.add(minion)
            else:
                newMons.append(minion)
            if goalie:
                minion.assignGoalie(1)
                tower.goalieList.add( minion )
    return newMons
