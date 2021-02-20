"""
props.py:
Define all kinds of props in game, as well as the bagpack manager for hero.
Classes in this module is organised in the order of chapters.
"""
import pygame
# 在此模块中，load、flip和collide_mask三个函数使用很频繁，直接导入它们以方便使用
from pygame.image import load
from pygame.transform import flip
from pygame.sprite import collide_mask
import math
from random import random, randint, choice

from enemy import Missle    # for MissleGun in Chapter6
from mapElems import Totem, Tracker, Porter
from database import DMG_FREQ
from util import InanimSprite, HPBar
from util import getPos, generateShadow, getCld


# ==========================================================
# ========= Bagpack Object for Prop Management =============
# ==========================================================
class Bagpack():
    def __init__(self):
        self.itemDic = { "ammo":("Ammo Vol-Up","弹药扩容"), "fruit":("Fruit","水果"), 
            "medicine":("Medicine","治愈血清"), "torch":("Torch","火把"), "copter":("Copter","竹蜻蜓"), "herbalExtract":("Herbal Extract","灵草精华"), 
            "simpleArmor":("Simple Armor","简易机甲"), "missleGun":("Missle Gun", "火箭发射器"), "cooler":("Cooler","清凉圣水"), 
            "blastingCap":("Blasting Cap","爆破雷管"), "shieldSpell":("Shield Spell","护盾法术"), "toothRing":("Tooth Ring","龙牙之戒"), 
            "battleTotem":("Battle Totem","战斗图腾"), "alcohol":("Alcohol","烈酒"), "pesticide":("Pesticide","杀虫喷雾"), "rustedHorn":("Rusted Horn","生锈的号角"), 

            "loadGlove":("Quick-fix Glove","快速填装手套"), "defenseTower":("Magic Defense","玉石防御塔"), "coin":("Coin","金币"), "servant":("Lit-Armor Serv.","轻甲侍从") }
        
        self.bag = {}   # store all items in the form of dictionary. It doesnot support index, so a buffer is needed.
        for each in self.itemDic:
            if each not in ("ammo", "coin", "servant"):
                self.bag[each] = 0
        
        self.bagImgList = {}
        for item in self.bag:
            self.bagImgList[item] = load("image/props/"+item+".png").convert_alpha()
        
        self.bagBuf = []    # a buffer for hero.bag, dynamically renew itself each fresh, only store items that hero has.
        # Initialize the buffer with only 2 "fruit".
        self.bag["fruit"] = 2
        self.bagBuf.append( "fruit" )
        self.bagPt = 0      # A pointer that indicates the current item in the bag buffer.
        # Page Info.
        self.page = 0
        self.pageLen = 5
    
    def incItem(self, name, number):
        self.bag[name] += number
        # 如是全新的项，还要添加到缓冲区
        if name not in self.bagBuf:
            self.bagBuf.append( name )
            if self.bagPt <0:
                self.bagPt = 0

    def decItem(self, name):
        self.bag[name] -= 1
        # 如数值变为0，则从缓冲区删除
        if self.bag[name] == 0:
            # 是最后一项，还要将指针前移
            if name==self.bagBuf[-1]:
                self.bagPt -= 1
            self.bagBuf.remove(name)

    def shiftItem(self):
        if len(self.bagBuf)>1:
            self.bagPt = (self.bagPt+1) % len(self.bagBuf)
            # Check whether to shift page.
            if not self.bagPt%self.pageLen:
                if len(self.bagBuf)>(self.page+1)*self.pageLen:
                    self.page += 1
                else:
                    self.page = 0

    def getPageVol(self):
        if len(self.bagBuf)>=self.pageLen*(self.page+1):
            return self.pageLen
        else:
            return len(self.bagBuf)%self.pageLen
        
    def readItemByName(self, name):
        # 根据item名字，返回其数量和图片
        return (self.bag[name], self.bagImgList[name])

    def readItemByPt(self, pt=-1):
        # 返回当前缓冲区的指定物品数量和图片
        if pt==-1 or pt>=len(self.bagBuf):  # 若下标超界，亦视作-1
            curName = self.bagBuf[self.bagPt]
        else:
            curName = self.bagBuf[pt]
        return (self.bag[curName], self.bagImgList[curName])


# ==========================================================
# ====================== Bag Props =========================
# ==========================================================
class Prop(object):
    def __init__(self, propName, duration, user):
        self.propName = propName  # 道具名称。
        self.duration = duration  # 道具耐久，同时还可用作计数器。
        self.user = user          # 使用者对象的引用（Hero实例）。

    def work(self):
        pass

    def erase(self):
        if self in self.user.activeProps:
            self.user.activeProps.remove(self)
        del self

    def lift(self, dist):
        return
    
    def level(self, dist):
        return
    
# CP 1
class Cooler(Prop):
    def __init__(self, user):
        Prop.__init__(self, "cooler", 1320, user)
        # Draw canvas (shield).
        size = max(self.user.rect.width, self.user.rect.height)
        self.canvas = pygame.Surface( (size, size) ).convert_alpha()
        self.canvas.fill( (0,0,0,0) )
        self.rect = self.canvas.get_rect()
        pygame.draw.circle( self.canvas, (255,255,200,100), (self.rect.width//2,self.rect.height//2), self.rect.height//2 )
        userC = getPos(self.user, 0.5, 0.5)
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        # 修改特定伤害减轻效果65%
        self.user.dmgReducDic["fire"] = 0.35

    def work(self):
        self.duration -= 1
        if self.duration <= 0:
            self.user.dmgReducDic["fire"] = 1   # 重置为1
            self.erase()
            return
        # update Position.
        pos = getPos(self.user, 0.5, 0.5)
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2
        
    def paint(self, surface):
        # 效果快结束时闪烁以提示。
        if self.duration<=100:
            if self.duration%10 > 6:
                return
        surface.blit( self.canvas, self.rect )

class ToothRing(Prop):
    def __init__(self, user):
        Prop.__init__(self, "toothRing", 0, user)
        self.critDots = []
        self.ori_critR = self.user.critR
        self.user.critR = 1     # 暴击率置为100%
        # 立刻将弹药拉满、填装状态取消
        self.user.arrow = self.user.arrowCnt
        self.user.loading = self.user.LDFull

    def work(self):
        if not self.duration % 4:
            # 处理已有的点。
            for dot in self.critDots:
                dot[1] -= 1
                if dot[1] == 0:
                    self.critDots.remove(dot)
            # 添加一个治愈点（圆形）。
            pos = getPos( self.user, random(), random() )
            critDot = [ pos, choice((5,6)) ]   # 分别是位置和半径。
            self.critDots.append(critDot)
        # 每当进入填装模式时，结束效果。
        if self.user.loading == 0:
            self.user.critR = self.ori_critR    # 暴击率重置为正常值
            self.erase()
            return

    def paint(self, surface):
        for dot in self.critDots:
            pygame.draw.circle( surface, (200,10,120), dot[0], dot[1]+1 )
            pygame.draw.circle( surface, (180,0,100), dot[0], dot[1] )


# CP 2
class HerbalExtract(Prop):
    def __init__(self, user):
        Prop.__init__(self, "herbalExtract", 300, user)
        self.cureDots = []
        self.user.bar.barBG.fill( (180,255,240,210) )

    def work(self):
        self.duration -= 1
        if not self.duration % 4:
            # 处理已有的点。
            for dot in self.cureDots:
                dot[1] -= 1
                if dot[1] == 0:
                    self.cureDots.remove(dot)
            # 添加一个治愈点（圆形）。
            pos = getPos( self.user, random(), random() )
            cureDot = [ pos, choice((5,6)) ]   # 分别是位置和半径。
            self.cureDots.append(cureDot)
        if not self.duration % 10:
            # 给英雄回血。
            self.user.recover(10)
            if self.user.health >= self.user.full:
                self.duration = 0
        # 如果效果用完，或者英雄受到伤害，则终止回复效果。
        if self.duration <= 0 or self.user.hitFeedIndx:
            self.user.bar.barBG.fill( (255,255,255,210) )
            self.erase()
            return

    def paint(self, surface):
        for dot in self.cureDots:
            pygame.draw.circle( surface, (60,240,210), dot[0], dot[1]+1 )
            pygame.draw.circle( surface, (30,190,160), dot[0], dot[1] )

class BlastingCap(Prop, InanimSprite):
    snd = None

    def __init__(self, owner, speed, onlayer):
        if not BlastingCap.snd:
            BlastingCap.snd = pygame.mixer.Sound("audio/blastcap.wav")
        
        Prop.__init__(self, "blastingCap", 90, owner)
        InanimSprite.__init__(self, "blastingCap")
        self.image = load("image/props/blastingCapCasted.png").convert_alpha()
        self.alarm = generateShadow(self.image, (255,5,5,80))
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        x, y = getPos(owner, 0.5, 0.6)
        self.rect.left = x-self.rect.width//2
        self.rect.top = y-self.rect.height//2
        self.rad = 220
        self.damage = 500
        self.speed = speed
        self.onlayer = onlayer  # 体系和hero一致
        self.bounce = 2         # 落地弹跳次数

    def work(self, sprites, sideWalls, canvas):
        self.duration -= 1
        # Horrizontal Move
        self.rect.left += self.speed[0]
        if pygame.sprite.spritecollide(self, sideWalls, False, collide_mask):
            self.speed[0] = -self.speed[0]
        # explode
        if self.duration == 0:
            self.snd.play(0)
            pos1 = getPos(self, 0.5,0.5)
            # draw explosion waves
            canvas.addExplosion( 
                pos1, self.rad*2//3, self.rad//2, rInc=4, wFade=8, dotD=(52,56,60)
            )
            # deal damages
            for each in sprites:
                pos2 = getPos(each, 0.5,0.5)
                dist_sq = (pos2[0]-pos1[0])**2 + (pos2[1]-pos1[1])**2
                if dist_sq < self.rad**2:
                # 对命中的怪物进行受伤操作，记录其是否死亡的真值（hitted返回True表示死亡）
                    if each.hitted(self.damage, 0, "fire")==True:
                        deadInfo = each.category
                    else:
                        deadInfo = False
                    self.user.preyList.append( (pos2, each.bldColor, 8, deadInfo, each.coin, False) )  # 道具爆炸，无暴击
            self.kill()
            self.erase()
            return "vib"
    
    def fall(self, delay, keyLine, groupList, GRAVITY):
        if not delay%2 and self.speed[1]<GRAVITY:
            self.speed[1] += 1
        self.rect.top += self.speed[1]
        FLAG = False
        while ( pygame.sprite.spritecollide(self, groupList[str(self.onlayer+1)], False, collide_mask) ):  # 如果和参数中的物体相撞，则尝试纵坐标-1
            FLAG = True
            self.rect.bottom -= 1
            self.speed[1] = 0
        if FLAG and self.bounce>0:
            self.bounce -= 1
            self.speed[1] = -4
            self.speed[0] = self.speed[0]//2
        if self.rect.top >= keyLine:
            self.onlayer = max(self.onlayer-2, -2)
    
    def paint(self, screen):
        screen.blit(self.image, self.rect)
        if self.duration<40:
            screen.blit(self.alarm, self.rect)


# CP 3
class Torch(Prop):
    def __init__(self, user):  # 火炬的燃烧这里采用任意的图片，因此不设置图片的循环标记。
        Prop.__init__(self, "torch", 1900, user)
        self.imgLeft = [ load("image/props/torchOn0.png").convert_alpha(), load("image/props/torchOn1.png").convert_alpha(),
            load("image/props/torchOn2.png").convert_alpha(), load("image/props/torchOn1.png").convert_alpha() ]
        self.imgRight = [ flip(self.imgLeft[0], True, False), flip(self.imgLeft[1], True, False), 
            flip(self.imgLeft[2], True, False), flip(self.imgLeft[3], True, False) ]
        self.posR = (0.6,0.65)    # 只保留左向时的位置信息
        self.image = self.imgLeft[2]
        self.rect = self.image.get_rect()
        userC = getPos(self, self.posR[0], self.posR[1])
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        # 伤害信息
        self.per_dmg = 10

    def work(self, monsters, canvas):
        self.duration -= 1
        self.user.lumi = min(132, self.duration)
        if self.duration <= 0:
            self.erase()
            return
        # Update Image.
        if not (self.duration % 3):
            if self.user.status=="left":
                self.image = choice(self.imgLeft)
            elif self.user.status=="right":
                self.image = choice(self.imgRight)
            self.rect = self.image.get_rect()
            self.mask = pygame.mask.from_surface(self.image)
        # update Position.
        xR = self.posR[0] if self.user.status=="left" else 1-self.posR[0]
        pos = getPos(self.user, xR, self.posR[1])
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2
        # deal damages
        if not self.duration % DMG_FREQ:
            canvas.addSpatters( 3, [2,3,4], [24,26,28], (255,210,10,240), pos, True )
            for each in monsters:
                pos2 = getPos(each, 0.5,0.5)
                dist_sq = (pos2[0]-pos[0])**2 + (pos2[1]-pos[1])**2
                if dist_sq < self.user.lumi**2:
                    if each.hitted(self.per_dmg, 0, "fire")==True:
                        deadInfo = each.category
                    else:
                        deadInfo = False
                    self.user.preyList.append( (pos2, each.bldColor, 8, deadInfo, each.coin, False) )  # 无暴击

    def paint(self, surface):
        surface.blit( self.image, self.rect )


# CP 4
class Copter(Prop):
    def __init__(self, user):
        Prop.__init__(self, "copter", 860, user)
        self.imgLeft = [ load("image/props/copter0.png").convert_alpha(), load("image/props/copter1.png").convert_alpha(),
            load("image/props/copter2.png").convert_alpha() ]
        self.imgRight = [ flip(self.imgLeft[0], True, False), flip(self.imgLeft[1], True, False), 
            flip(self.imgLeft[2], True, False) ]
        self.posR = (0.5,0.05)
        self.imgIndx = 0
        self.image = self.imgLeft[self.imgIndx]
        self.rect = self.image.get_rect()
        userC = getPos(self, self.posR[0], self.posR[1])
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        # substitute user's 相关函数。
        self.oriJump = self.user.jump
        self.oriFall = self.user.fall
        self.user.respondKeyDic["jumpKey"] = lambda delay: self.moveY(delay, -3)
        self.user.respondKeyDic["downKey"] = lambda delay: self.moveY(delay, 3)
        self.user.jump = self.jumpFly
        self.user.fall = self.fallFly

    def work(self):
        self.duration -= 1
        if self.duration<=100:
            self.user.spurtCanvas.addSmoke(1,(3,4,5),5,(10,10,10,150),getPos(self,0.5,random()),4)
            if self.duration <= 0:
                self.user.jump = self.oriJump
                self.user.fall = self.oriFall
                self.user.respondKeyDic.pop("jumpKey")
                self.user.respondKeyDic.pop("downKey")
                self.erase()
                return
        # Update Image.
        if not (self.duration % 3):
            self.imgIndx = (self.imgIndx+1) % len(self.imgLeft)
            if self.user.status=="left":
                self.image = self.imgLeft[self.imgIndx]
            elif self.user.status=="right":
                self.image = self.imgRight[self.imgIndx]
            self.rect = self.image.get_rect()
        # update Position.
        xR = self.posR[0] if self.user.status=="left" else 1-self.posR[0]
        pos = getPos(self.user, xR, self.posR[1])
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2

    def paint(self, surface):
        surface.blit( self.image, self.rect )
    
    # Redefine the moving methods of the hero. (for flying)
    def jumpFly(self, keyLine):
        self.user.aground = False
        while ( getCld(self.user, self.user.checkList, ["sideWall","baseWall","blockStone"]) ):  # 如果和参数中的物体重合，则回退1高度
            self.user.rect.bottom += 1        # 循环+1，直到不再和任何物体重合为止，跳出循环
        if ( self.user.rect.bottom <= keyLine ):
            self.user.shiftLayer(2, None)
    
    def fallFly(self, keyLine, newLine, heightList, GRAVITY):
        self.user.rect.bottom += self.user.gravity  # 尝试将自身纵坐标减去重力值
        # 获得所有碰撞了的物体对象，并针对每一个碰撞了的item执行相应的响应动作。这里不会触发特殊砖块的效果。
        for item in pygame.sprite.spritecollide(self.user, self.user.checkList, False, collide_mask):
            if item.category in self.user.interactiveList:
                item.interact(self.user)
        # 飞行状态不重复下落，逐步减缓重力。
        if self.user.gravity>0:
            self.user.gravity -= 1
        # 如果和参数中的物体重合，则回退1高度
        while getCld(self.user, self.user.checkList, ["baseWall","specialWall","sideWall","blockStone","house"]):
            self.user.aground = True
            self.user.rect.bottom -= 1    # 循环-1，直到不再和任何物体重合为止
        self.user.renewCheckList(newLine) # 更新self.checkList（跳跃函数中不必更新，只有这里需要更新）
        # 判断是否要向下调整层数.
        if ( self.user.rect.top >= keyLine ):
            self.user.shiftLayer(-2, heightList)

    def moveY(self, delay, to):
        self.user.lift(to)
        if to<0:
            self.user.k1 = 1   # 为了能够执行jump函数，检查向上调整层数
        elif to>0:
            self.user.k1 = 0   # 为了能够执行fall函数，检查向下调整层数
    
class Pesticide(Prop):
    def __init__(self, user):
        Prop.__init__(self, "pesticide", 52, user)
        # Equip Sound:
        pygame.mixer.Sound("audio/mecha.wav").play(0)
        self.spraySnd = pygame.mixer.Sound("audio/pesticide.wav")
        self.imgLeft = load("image/props/pesticideEquiped.png").convert_alpha()
        self.imgRight = flip(self.imgLeft, True, False)
        self.posR = (0.5,0.55)
        self.image = self.imgLeft
        self.rect = self.image.get_rect()
        userC = getPos(self, self.posR[0], self.posR[1])
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        self.accum = self.accumFull = 6
        # 修改、替换user的相关函数。
        self.oriArrow = self.user.arrow
        self.user.loading = self.user.LDFull
        self.user.arrow = self.duration
        self.oriShoot = self.user.shoot
        self.user.shoot = lambda tower, canvas: 1    # set to void function
        self.user.respondKeyDic["shootKey"] = lambda monsters: self.shootPesticide(monsters)

    def work(self):
        if self.duration <= 0:      # pesticide used up，还原各属性
            self.user.arrow = self.oriArrow
            self.user.shoot = self.oriShoot
            self.user.respondKeyDic.pop("shootKey")
            self.erase()
            return
        if self.user.status=="left":
            self.image = self.imgLeft
        elif self.user.status=="right":
            self.image = self.imgRight
        self.rect = self.image.get_rect()
        # update Position.
        xR = self.posR[0] if self.user.status=="left" else 1-self.posR[0]
        pos = getPos(self.user, xR, self.posR[1])
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2

    def shootPesticide(self, monsters):
        if (self.user.arrow > 0) and (self.user.shootCnt == 0):
            if self.spraySnd.get_num_channels()==0:
                self.spraySnd.play()
            if random() <= 0.1:
                self.user.talk = [self.user.talkDic["shoot"][self.user.lgg], 60]
            if self.user.status=="left":
                posx = 0.1
                spd = [ choice([-2,-3,-4]), choice([-3,-2,-1,1,2,3]) ]
            else:
                posx = 0.9
                spd = [ choice([2,3,4]), choice([-3,-2,-1,1,2,3]) ]
            # make ammo object
            for i in range(2):
                self.user.spurtCanvas.addAirAtoms(self.user, 2, getPos(self,posx,0.4+random()*0.2), 
                    spd, monsters, "physical")
            self.accum -= 1
            if self.accum<=0:
                self.user.arrow -= 1
                self.duration -= 1
                self.accum = self.accumFull

    def paint(self, surface):
        surface.blit( self.image, self.rect )


# CP 5
class Alcohol(Prop):
    def __init__(self, user):
        Prop.__init__(self, "alcohol", 1320, user)
        # Draw canvas (shield).
        size = max(self.user.rect.width, self.user.rect.height)
        self.canvas = pygame.Surface( (size, size) ).convert_alpha()
        self.canvas.fill( (0,0,0,0) )
        self.rect = self.canvas.get_rect()
        pygame.draw.circle( self.canvas, (255,120,120,100), (self.rect.width//2,self.rect.height//2), self.rect.height//2 )
        userC = getPos(self.user, 0.5, 0.5)
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        # 修改、替换user的相关函数
        self.user.dmgReducDic["freezing"] = 0.4
        self.oriFreeze = self.user.freeze
        self.user.freeze = self.freezeAlcohol

    def work(self):
        self.duration -= 1
        if self.duration <= 0:
            self.user.freeze = self.oriFreeze
            self.user.dmgReducDic["freezing"] = 1
            self.erase()
            return
        # update Position.
        pos = getPos(self.user, 0.5, 0.5)
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2

    def freezeAlcohol(self, decre):
        return
        
    def paint(self, surface):
        # 效果快结束时闪烁以提示。
        if self.duration<=100:
            if self.duration%10 > 6:
                return
        surface.blit( self.canvas, self.rect )

class BattleTotem(Prop, Totem):
    def __init__(self, user, wall, onlayer):
        Prop.__init__(self, "battleTotem", 0, user)
        Totem.__init__(self, "battleTotem", wall, onlayer)

    def run(self, heroes, spurtCanvas):
        spurtCanvas.addSmoke( 1, (2,4), 5, (255,90,90,240), getPos(self,0.5,random()), 30 )
        # Check highlight
        if self.ltCnt>0:
            self.ltCnt -= 1
        self.coolDown -= 1
        if self.coolDown<=0:
            # 冷却结束，释放治疗。若未找到，则coolDown一直为0
            for hero in heroes:
                if hero.category=="hero" and hero.arrow < hero.arrowCnt:
                    self.tgt = hero
                    tracker = Tracker("battleLight", getPos(self,0.5,0.1), hero, (255,250,90,240), 1)
                    self.snd.play(0)
                    self.coolDown = randint(self.cntFull-10, self.cntFull+10)    # 投递完成，重置冷却时间
                    self.ltCnt = 20
                    return tracker
            self.coolDown = 0

    def lift(self, dist):
        self.rect.bottom += dist
    
    def level(self, dist):
        self.rect.left += dist
    

# CP 6
class SimpleArmor(Prop):
    def __init__(self, user):
        Prop.__init__(self, "simpleArmor", 240, user)
        # Equip Sound:
        pygame.mixer.Sound("audio/mecha.wav").play(0)
        self.imgLeft = load("image/props/simpleArmorEquiped.png").convert_alpha()
        self.imgRight = flip(self.imgLeft, True, False)
        self.posR = (0.5,0.55)
        self.image = self.imgLeft
        self.rect = self.image.get_rect()
        userC = getPos(self, self.posR[0], self.posR[1])
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        # 修改、替换user的相关函数。
        self.oriBldColor = self.user.bldColor
        self.user.bldColor = (90,90,90,210)
        self.oriHitted = self.user.hitted
        self.user.hitted = self.hittedArmor
        # The followings are parameters about Duration bar.
        self.blockLen = self.user.bar.blockLen
        self.gap = self.user.bar.gap
        barGaps = ( math.ceil( self.duration//10/self.user.bar.blockVol )-1)*self.gap +self.gap*2 # 格子中间及两端间隔的数量。
        self.barLen = self.duration//10*(self.blockLen//self.user.bar.blockVol) + barGaps     # 计算血条总长度
        self.barH = self.user.bar.barH

    def work(self):
        if self.duration <= 0:
            self.user.hitted = self.oriHitted
            self.user.bldColor = self.oriBldColor
            self.erase()
            return
        if self.user.status=="left":
            self.image = self.imgLeft
        elif self.user.status=="right":
            self.image = self.imgRight
        self.rect = self.image.get_rect()
        # update Position.
        xR = self.posR[0] if self.user.status=="left" else 1-self.posR[0]
        pos = getPos(self.user, xR, self.posR[1])
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2

    def hittedArmor(self, damage, pushed, dmgType):
        self.duration -= damage * self.user.dmgReducDic["basic"]
        if pushed>0:    # 向右击退
            self.user.hitBack = max( pushed-self.user.weight, 0 )
        elif pushed<0:  # 向左击退
            self.user.hitBack = min( pushed+self.user.weight, 0 )
        if random()<0.1:
            self.user.talk = [self.user.talkDic["hitted"][self.user.lgg], 60]
        
    def paint(self, surface):
        surface.blit( self.image, self.rect )
        # 以上是画装甲，以下是画血条。
        health = max( self.duration//10, 0 )
        color, shadeColor = (90, 90, 90), (10, 10, 10)     # 灰色
        x = self.user.rect.left+self.user.rect.width//2 -self.user.bar.barLen/2   # 中线减去血条长度的一半。
        y = self.user.rect.top-self.user.bar.barOffset
        # 画内部血格
        offset = 0           # 用于计算每个方格的偏移值
        while (health > 0):
            w = min(self.blockLen, health)
            block = pygame.Rect( x+self.gap+offset, y+self.gap, w, self.barH-self.gap*2 )
            shadow = pygame.Rect( x+self.gap+offset, block.bottom-self.gap*2, w, self.gap*2 )
            pygame.draw.rect( surface, color, block )
            pygame.draw.rect( surface, shadeColor, shadow )
            health -= self.user.bar.blockVol
            offset += (self.blockLen+self.gap)

class MissleGun(Prop):
    def __init__(self, user):
        Prop.__init__(self, "missleGun", 4, user)
        # Equip Sound:
        pygame.mixer.Sound("audio/mecha.wav").play(0)
        self.imgLeft = load("image/props/missleGunEquiped.png").convert_alpha()
        self.imgRight = flip(self.imgLeft, True, False)
        self.posR = (0.5,0.55)
        self.image = self.imgLeft
        self.rect = self.image.get_rect()
        userC = getPos(self, self.posR[0], self.posR[1])
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        # 修改、替换user的相关函数。
        self.oriArrow = self.user.arrow
        self.user.arrow = self.duration
        self.oriShoot = self.user.shoot
        self.user.shoot = self.shootMissle

    def work(self):
        if self.duration <= 0:      # missles used up，还原各属性
            self.user.arrow = self.oriArrow
            self.user.shoot = self.oriShoot
            self.erase()
            return
        if self.user.status=="left":
            self.image = self.imgLeft
        elif self.user.status=="right":
            self.image = self.imgRight
        self.rect = self.image.get_rect()
        # update Position.
        xR = self.posR[0] if self.user.status=="left" else 1-self.posR[0]
        pos = getPos(self.user, xR, self.posR[1])
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2

    def shootMissle(self, tower, spurtCanvas=None):
        if (self.user.arrow > 0) and (self.user.shootCnt == 0):
            if random() <= 0.2:
                self.user.talk = [self.user.talkDic["shoot"][self.user.lgg], 60]
            if self.user.status=="left":
                pos = getPos(self, 0, 0.5)
                self.user.hitBack = 6
            else:
                pos = getPos(self, 1, 0.5)
                self.user.hitBack = -6
            # make ammo object
            scrnList = []
            goalieList = []
            for each in tower.monsters:
                if (each.rect.bottom>0) and (each.rect.top<2*self.user.rect.bottom):  # 大致地估算是否在屏幕范围内。
                    # 优先攻击非地面生物
                    if each.manner!="GROUND" or each.manner=="CRAWL":
                        goalieList.append(each)
                    else:
                        scrnList.append(each)
            if len(goalieList)>0:
                tgt = choice(goalieList)
            elif len(scrnList)>0:
                tgt = choice(scrnList)
            else:
                tgt = None
            missle = Missle( pos, self.user.status, 400, tgt )
            tower.allElements["mons1"].add(missle)
            self.user.arrow -= 1
            self.duration -= 1
        
    def paint(self, surface):
        surface.blit( self.image, self.rect )


# CP 7 ---------------------------
class ShieldSpell(Prop):
    def __init__(self, user):
        Prop.__init__(self, "shieldSpell", 1320, user)
        # Draw canvas (shield).
        size = max(self.user.rect.width, self.user.rect.height)
        self.canvas = pygame.Surface( (size, size) ).convert_alpha()
        self.canvas.fill( (0,0,0,0) )
        self.rect = self.canvas.get_rect()
        pygame.draw.circle( self.canvas, (200,255,255,100), (self.rect.width//2,self.rect.height//2), self.rect.height//2 )
        userC = getPos(self.user, 0.5, 0.5)
        self.rect.left = userC[0] - self.rect.width//2
        self.rect.bottom = userC[1] - self.rect.height//2
        # 修改、替换user的相关函数。
        self.user.dmgReducDic["physical"] = 0.35

    def work(self):
        self.duration -= 1
        if self.duration <= 0:
            self.user.dmgReducDic["physical"] = 1
            self.erase()
            return
        # update Position.
        pos = getPos(self.user, 0.5, 0.5)
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2

    def paint(self, surface):
        # 效果快结束时闪烁以提示。
        if self.duration<=100:
            if self.duration%10 > 6:
                return
        surface.blit( self.canvas, self.rect )

class RustedHorn(Prop):
    def __init__(self, user):
        Prop.__init__(self, "rustedHorn", 45, user)
        self.per_heal = 30      # 对于每名生效的敌人，为己方回复的HP
        self.healRad = 320      # 治疗和眩晕半径（实际计算距离，与显示的圆圈大小无关）
        self.stun_dur = 120     # 眩晕时长：2秒
        pygame.mixer.Sound("audio/rustedHorn.wav").play(0)
        # 黄色光圈
        self.radius = 25
        self.width = self.duration
        self.dotList = []
        self.stuned_mons = []
        self.ctr = getPos(self.user, 0.5, 0.5)

    def work(self, monsters, heroes):
        self.duration -= 1
        if self.duration <= 0:
            self.erase()
            return
        # update Halo
        self.radius += 7
        self.width = max(self.width-1, 0)
        # Add dot on the edge.
        posCaster = getPos(self.user, 0.5, 0.5)
        if self.width>1:
            self.makeMark(posCaster)
        # Move dot.
        for dot in self.dotList[::-1]:
            dot[0][0] += dot[2][0]
            dot[0][1] += dot[2][1]
            dot[1] = dot[1]-1
            if dot[1]<=0:
                self.dotList.remove(dot)
                del dot
        # Deal effect on three phases.
        if not (self.duration+1) % 15:      # 15, 30, 45依次向外扩张，共计算3次
            i = (self.duration+1) // 15
            num = 0
            # 1. Deal stun.
            for each in monsters:
                if each in self.stuned_mons or each.coin==0:    # 已计算过，跳过。
                    continue
                # 计算离吹号中心的距离
                pos2 = getPos(each, 0.5,0.5)
                dist_sq = (pos2[0]-self.ctr[0])**2 + (pos2[1]-self.ctr[1])**2
                if dist_sq < (self.healRad//i)**2 and dist_sq:
                    # 在范围内，眩晕
                    each.stun(self.stun_dur)
                    num += 1
                    self.stuned_mons.append(each)
            # 2. Heal heroes.
            for hero in heroes:
                # calculate the distance between hero and self.user.
                posHero = getPos(hero,0.5,0.5)
                distSquare = (posHero[0]-self.ctr[0])**2 + (posHero[1]-self.ctr[1])**2
                if distSquare**0.5<self.healRad:
                    hero.recover( self.per_heal*num )
            return "vib"
    
    def paint(self, surface):
        if self.width>1:
            pygame.draw.circle( surface, (255,220,20), getPos(self.user,0.5,0.5), self.radius, self.width )
        for pos, r, spd in self.dotList:
            pygame.draw.circle( surface, (255,220,20), pos, r )
    
    def makeMark(self, pos):
        # dandomize a position that is on the edge.
        startX = randint(pos[0]-self.radius, pos[0]+self.radius)
        distY = round( ( self.radius**2 - (startX-pos[0])**2 )**0.5 )
        startY = pos[1] + choice([1,-1])*distY
        speedX = 2 if startX>pos[0] else -2
        speedY = 2 if startY>pos[1] else -2
        # make dot.
        self.dotList.append( [[startX,startY], 24, [speedX,speedY]] )    # Pos, rad, speed


# CP 0 (ENDLESS MODE) ---------------------------
class DefenseTower(Prop, Porter):
    siteWalls = []

    def __init__(self, x, y, onlayer, font, lgg, user):
        Prop.__init__(self, "defenseTower", 0, user)
        Porter.__init__(self, x, y, "defenseTower", 0, font, lgg)
        self.health = self.full = 1500
        self.onlayer = onlayer
        self.hitFeedIndx = 0
        self.preyList = []
        self.checkList = pygame.sprite.Group()
        self.lumi = 90
        self.gravity = 0
        self.aground = True
        self.shootCnt = 0
        # For NPC hero:
        self.bar = HPBar(self.full, blockVol=300, color="orange")
        self.snd = pygame.mixer.Sound("audio/healing.wav")

    def hitted(self, damage, pushed, dmgType):
        if self.health<=0:
            return
        self.health -= damage
        if (self.health < 0):
            self.health = 0
            # 音效
            pygame.mixer.Sound("audio/wizard/hit.wav").play(0)
            return True
        self.hitFeedIndx = 6

    def recover(self, heal):
        if self.health<=0:
            return
        #self.spurtCanvas.addSpatters(8, (2,3,4), (20,22,24), (10,240,10), getPos(self,0.5,0.4) )
        self.health += heal
        if (self.health > self.full):
            self.health = self.full
    
    def freeze(self, decre):
        return
    
    def infect(self):
        return

    def checkImg(self, delay, tower, heroes, key_pressed, spurtCanvas):
        if self.health<=0:
            spurtCanvas.addPebbles(self, 5, type="jadeDebri")
            spurtCanvas.addSmoke(1, (3,5,7), 5, (10,10,10,240), getPos(self,0.5,random()), 2)
            self.erase()
            return 0
        # 青烟效果
        if not delay%2:
            spurtCanvas.addSmoke(1, (2,3,5), 5, (100,255,10,200), getPos(self,0.5,0.95), 30)
        # 发射光弹
        if self.shootCnt>0:
            self.shootCnt -= 1
        else:
            # 冷却结束，寻找目标。若未找到，则shootCnt一直为0
            for mons in tower.monsters:
                if mons.health>0:
                    tracker = Tracker("defenseLight", getPos(self,0.5,0.1), mons, (255,250,90,240), 40)
                    tracker.shooter = self
                    self.snd.play(0)
                    self.shootCnt = 42    # 发射完成，重置冷却时间
                    tower.allElements["mons2"].add( tracker )
                    break
        # 其他需要处理的
        if self.hitFeedIndx>0:
            self.hitFeedIndx -= 1
        return 0

    def drawHeads(self, screen):
        # 画HP
        if self.hitFeedIndx:
            self.bar.setColor("yellow")
        else:
            self.bar.setColor("orange")
        self.bar.paint(self, screen)

    def lift(self, dist):
        self.rect.bottom += dist
    
    def level(self, dist):
        self.rect.left += dist
