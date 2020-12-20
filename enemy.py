# enemy.py
import pygame
from pygame.image import load
from pygame.transform import flip
from pygame.sprite import collide_mask
import math
from random import *

from database import MB, NB, DMG_FREQ
from util import InanimSprite, HPBar
from util import getPos, rot_center, generateShadow


# NOTE: pygame.transform.flip() is non-destructive
# -------------------------------------------------
def cldList(subject, objList):
    '''Check whether subject collides with any object in the list:
    if yes, invoke hitted() of the collided object.'''
    for each in objList:
        if ( collide_mask( subject, each ) ):
            each.hitted( subject.damage, subject.push, subject.dmgType )
            if hasattr(subject, "dmgType") and subject.dmgType=="freezing":
                each.freeze(1)
            return each   # 返回碰撞对象表示发生碰撞，否则函数最后返回默认值None

def getCld(core, group, cateList):
    '''Assistant function for stone.fall'''
    spriteList = []
    cldList = pygame.sprite.spritecollide(core, group, False, collide_mask)
    for item in cldList:
        if item.category in cateList:
            spriteList.append(item)
    return spriteList

def createCanvas(size, colorKey=(0,0,0)):
    '''为调用者生成一个画布对象。接受参数为画布尺寸和透明色信息（RGB无A），返回画布的surface及其rect。'''
    canvas = pygame.Surface( size ).convert()
    canvas.set_colorkey( colorKey )  # set black as transparent color, generally make the canvas transparent
    cRect = canvas.get_rect()
    cRect.left = 0
    cRect.top = 0
    return (canvas, cRect)

def createImgList(*paths):
    '''为调用者生成一个含左右图片列表的字典并返回。接受参数为左向的图片路径列表。注意使用了收集参数的机制，
    必须要把所有图片路径按顺序传入。如果实际只有一个图片传入，字典中的元素也会是列表，该表中只有一张图。'''
    imgDic = { "left":[], "right":[] }
    # 先建立left图片列表，再依次变换至right图片列表
    for path in paths:
        imgDic["left"].append( load(path).convert_alpha() )
    for img in imgDic["left"]:
        imgDic["right"].append( flip(img, True, False) )
    return imgDic

def getShadLib(imgLib):
    '''根据所给的imgLib转化出相应的阴影shadLib，并返回（适用于monsters）'''
    shadLib = {}
    for name in imgLib:            # 对于每一项动作名称
        shadLib[name] = { "left":[], "right":[] }
        for dir in imgLib[name]:   # 对于该动作的每一方向
            for img in imgLib[name][dir]:
                shadLib[name][dir].append( generateShadow(img) )
    return shadLib

# ========================================================================
#   DIY一个enemy类，此类将提供所有enemy应有的方法和属性，子类可在此基础上扩展
# 初始化需要的参数有：游戏内类别名，血的颜色，体力值，击退位移，价值得分，所在层数。
# ========================================================================
class Monster(InanimSprite):

    # NOTE: 所有的怪物类别都应维护自己的一些媒体静态变量。它们应该只加载一次，然后所有实例都可以使用这些媒体对象，如图片、声音。
    # 以下是monster大类共享的2个共享静态变量。在模式初始化时，由model对象来对这2个值进行初始化。（1表示原生命）
    healthBonus = 1
    # model的spurtcanvas对象，每个monster均应能快速访问，来实现多种效果
    spurtCanvas = None

    def __init__(self, cate, bldColor, push, weight, onlayer, sideGroup=None):
        InanimSprite.__init__(self, cate)   # 首先它应该是一个InanimSprite
        self.bldColor = bldColor            # tuple类型
        self.health = round( MB[cate].health * self.healthBonus )
        self.full = self.health
        self.coin = MB[cate].coin
        self.damage = MB[cate].damage
        self.dmgType = MB[cate].dmgType     # 伤害类型：大部分为物理伤害。
        self.manner = MB[cate].manner       # 行为方式：大部分为地面类型。
        self.armor = MB[cate].armor         # 护甲(伤害减免)：大部分无减伤。

        self.pushList = (-push, push)
        self.push = push
        self.weight = weight
        self.hitBack = 0
        self.realDmgRate = 1-self.armor
        
        self.onlayer = int(onlayer)         # 怪物的onlayer是其所处的砖块的层数。
        self.direction = "left"             # 默认初始朝left。若需自定义，可在monster子类的构造函数中修改本值。
        self.gravity = 0
        self.obstacle = pygame.sprite.Group()
        if sideGroup:
            self.renewObstacle(sideGroup)

        # The followings are parameters about HP bar.
        self.bar = HPBar(self.full)

    def alterSpeed(self, speed):
        self.speed = speed
        if speed > 0:
            self.direction = "right"
        elif speed < 0:
            self.direction = "left"
        self.push = self.pushList[0] if (self.direction=="left") else self.pushList[1]

    def checkHitBack(self, obstacle=False):
        if abs(self.hitBack)>0:
            # NOTE:和fall的处理方式不同。如果和参数中的物体相撞，则尝试保持原位置不变并直接消除hitback效果，而不是移至物体之外。
            if pygame.sprite.spritecollide(self, self.obstacle, False, collide_mask):
                self.hitBack = 0
                return False
            self.rect.left += self.hitBack
            self.hitBack -= self.hitBack//abs(self.hitBack) # 大于0取1，小于零取-1。
            return True
        return False
    
    def fall(self, keyLine, groupList, GRAVITY):
        if self.gravity<GRAVITY:
            self.gravity += 1
        self.rect.bottom += self.gravity
        while ( pygame.sprite.spritecollide(self, self.wallList, False, collide_mask) ):  # 如果和参数中的物体相撞，则尝试纵坐标-1
            self.rect.bottom -= 1
            self.gravity = 0
        if self.rect.top >= keyLine:
            self.onlayer  = max(self.onlayer-2, -1)
            self.initLayer( groupList[str(self.onlayer)], groupList["0"], wallChosen=True )
            # 更新obstacle砖块
            self.renewObstacle(groupList["0"])
    
    def initLayer(self, lineGroup, sideGroup, wallChosen=False):
        '''
        用于确定新一行中的位置及scope。
        param lineGroup: 该行的所有lineWall。
        param sideGroup: Add sidewalls that are of same layer to avoid monsters fall from the top layer.
        '''
        self.wallList = []          # 存储本行的所有砖块。每次初始化一个新实例时，清空此类的wallList
        posList = []                # 辅助列表，用于暂时存储本行砖块的位置（左边线）
        # 若已确定位置，是在下落过程中重新更新layer。
        if wallChosen:
            wall = None          # 此刻monster正下方的wall
            for aWall in lineGroup:   # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
                if aWall.category in ("lineWall","specialWall","baseWall"):
                    self.wallList.append(aWall)
                    posList.append(aWall.rect.left)
                    if aWall.rect.left<getPos(self,0.5,0)[0]<aWall.rect.right:  # 可以落到下一行上，有砖接着
                        wall = aWall
            if not wall:         # 没wall接着，直接返回，继续下落吧！
                return None
        # 否则，是首次生成，直接随机选择生成地。
        else:
            for aWall in lineGroup:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
                self.wallList.append(aWall)
                posList.append(aWall.rect.left)
            wall = choice(self.wallList)
        # 到了这一步，已经得到了wall，好，可以开始计算scope了。
        leftMax = wall.rect.left
        rightMax = wall.rect.right          # note：此处砖块的右坐标即下一砖块的左坐标
        while True:
            if leftMax in posList:          # warmachine比较宽，可以占两格行进
                leftMax -= wall.rect.width
            else:
                leftMax += wall.rect.width  # 将多减的加回来
                break
        while True:
            if rightMax in posList:
                rightMax += wall.rect.width
            else:
                break
        self.scope = (leftMax, rightMax)
        # Add sidewalls of the same layer to wallList
        for each in sideGroup:
            if each.coord[1]==self.onlayer:
                self.wallList.append(each)
        return wall
    
    def renewObstacle(self, sideGroup):
        # 更新obstacle砖块
        self.obstacle.empty()
        for each in sideGroup:
            if each.coord[1] == self.onlayer+1:
                self.obstacle.add(each)

    def detectHero(self, heroes):
        for hero in heroes:
            # 如果有英雄在同一层，则将速度改为朝英雄方向。
            if (hero.onlayer-1)==self.onlayer and ( self.scope[0]<=getPos(hero,0.5,0)[0]<=self.scope[1] ):
                if self.speed*( getPos(hero,0.5,0)[0]-getPos(self,0.5,0)[0] ) < 0:
                    self.alterSpeed(-self.speed)
                return hero
        return None

    def paint(self, surface):
        '''所有monster都应有paint()函数，供外界调用，将自身画在传来的surface上。NOTE:此函数不负责绘制生命条，应该由怪物管理类主动绘制'''
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 8
        surface.blit(self.shad, shadRect)
        surface.blit( self.image, self.rect )
        # 画打击阴影
        if self.hitBack:
            surface.blit( self.shad, self.rect )

    # stun(): similar to hero's freeze()
    def stun(self, duration):
        self.stun_time = duration
    
    def setImg(self, name, indx=0):  # 根据状态名称切换图片。如果是列表，应给出indx值。
        self.image = self.imgLib[name][self.direction][indx]
        self.shad = self.shadLib[name][self.direction][indx]
    
    def drawHealth(self, surface):
        self.bar.paint(self, surface)

    def assignGoalie(self, HPInc):
        # Redefine its health.
        self.full = self.health = round( self.health * HPInc )
        self.bar = HPBar(self.full, color="goldRed", icon=True)

    def hitted(self, damage, pushed, dmgType):
        # decrease health
        self.health -= (damage*self.realDmgRate)
        if self.health <= 0:                # dead。
            self.health = 0
            self.kill()
            return True
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )

class Ajunction(pygame.sprite.Sprite):
    '''此类应附属于某个monster主体而存在。由于是附属物，此类只提供供主物移动位置、替换image的函数接口，需要主物来执行相应的删除工作。'''
    def __init__(self, img, pos):
        pygame.sprite.Sprite.__init__(self)
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.bottom = pos[1] - self.rect.height//2
        self.mask = pygame.mask.from_surface(self.image)

    def updatePos(self, pos):
        self.rect.left = pos[0] - self.rect.width//2
        self.rect.top = pos[1] - self.rect.height//2
    
    def updateImg(self, img):
        trPos = [ self.rect.left + self.rect.width//2, self.rect.top + self.rect.height//2 ]
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]
        self.mask = pygame.mask.from_surface(self.image)

class Boss(Monster):
    '''Boss相比于Monster，拥有一些特殊的行为和属性'''
    def __init__(self, font, cate, bldColor, push, weight, onlayer, sideGroup=None):
        Monster.__init__(self, cate, bldColor, push, weight, onlayer, sideGroup)
        self.activated = False
        self.font = font    # For showing outscreen pos
        self.bar = HPBar(self.full, blockVol=20, barH=14, fixed=True)

    def _tipPosition(self, canvas):
        if (self.rect.top > canvas.rect.height):
            txt = self.font.render( "▼ "+str(self.rect.top-canvas.rect.height), True, (255,255,255) )
            canvas.txtList.append( [txt, "BOTTOM"] )
        elif (self.rect.bottom < 0):
            txt = self.font.render( "▲ "+str(-self.rect.bottom), True, (255,255,255) )
            canvas.txtList.append( [txt, "TOP"] )

    def initLayer(self, groupList):
        """Boss 一般体型较大，有其特殊的处理行砖方式"""
        self.wallList = []
        posList = []                # 辅助列表，用于暂时存储本行砖块的位置（左边线）
        for aWall in groupList[str(self.onlayer)]:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            self.wallList.append(aWall)
            posList.append(aWall.rect.left)
        wall = choice(self.wallList)
        self.initPos = getPos(wall, 0.5, 0)   # 新点，居中
        leftMax = wall.rect.left
        rightMax = wall.rect.right
        while True:
            if (leftMax in posList) or (leftMax-wall.rect.width in posList): # Chicheng比较宽，可以占两格行进
                leftMax -= wall.rect.width
            else:
                leftMax += wall.rect.width
                break
        while True:
            if (rightMax in posList) or (rightMax+wall.rect.width in posList):
                rightMax += wall.rect.width
            else:
                break 
        self.scope = (leftMax-wall.rect.width//2, rightMax+wall.rect.width//2)
        # Add sidewalls of the same layer to wallList
        for each in groupList["0"]:
            if each.coord[1]==self.onlayer:
                self.wallList.append(each)
        return wall

    def assignGoalie(self, HPInc):
        # Redefine its health.
        self.full = self.health = round( self.health * HPInc )
        self.bar = HPBar(self.full, blockVol=20, barH=14, color="goldRed", icon=True, fixed=True)
    
# --------------Endless Mode-------------------
class BiteChest(Monster): 
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, sideGroup, onlayer):
        if not self.imgLib:
            BiteChest.imgLib = {
                "iList": createImgList("image/stg0/biteChest1.png","image/stg0/biteChest0.png","image/stg0/biteChest0.png",
                    "image/stg0/biteChest0.png","image/stg0/biteChest0.png","image/stg0/biteChest0.png", 
                    "image/stg0/biteChest1.png")
            }
            BiteChest.shadLib = getShadLib(BiteChest.imgLib)
        
        # calculate its position
        Monster.__init__(self, "biteChest", (250,210,160), 4, 3, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        self.coin = randint(6,10)

        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.restCnt = self.resetCntFull = 8
        self.alterSpeed( choice([-1,1]) )
        self.rise = ( 1, -8, -13, -16, -13, -8, 1 )

    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)
        if self.imgIndx<len(self.rise)-1:       # 在空中时水平移动
            self.rect.left += self.speed
            if (getPos(self,0.8,0)[0]>=self.scope[1] and self.speed>0) or (getPos(self,0.2,0)[0]<=self.scope[0] and self.speed<0):
                self.alterSpeed( -self.speed )
            if not (delay % 4 ):
                trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom-self.rise[self.imgIndx] ]  # 为保证图片位置正确，临时存储之前的位置信息
                self.imgIndx += 1
                self.setImg("iList",self.imgIndx)
                self.mask = pygame.mask.from_surface(self.image)
                self.rect = self.image.get_rect()
                self.rect.left = trPos[0]-self.rect.width//2
                self.rect.bottom = trPos[1] + self.rise[self.imgIndx]
        else:       # rise最后一下落地，0.33秒停顿
            self.restCnt -= 1
            if self.restCnt<0:
                self.restCnt = self.resetCntFull
                self.imgIndx = 0
        # Bite
        if ( self.coolDown==0 ):
            for each in sprites:
                if collide_mask(self, each):
                    self.coolDown = 36
        elif (self.coolDown > 0):
            self.coolDown -= 1
            if ( self.coolDown == 20 ):
                cldList( self, sprites )

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# ============================================================================
# --------------------------------- Stage1 -----------------------------------
# ============================================================================
class InfernoFire(InanimSprite):
    def __init__(self, bg_size):
        InanimSprite.__init__(self, "infernoFire")
        self.ori_imgList = [load("image/stg1/infernoFire0.png").convert_alpha(), 
            load("image/stg1/infernoFire1.png").convert_alpha(), 
            load("image/stg1/infernoFire2.png").convert_alpha()]
        self.snd = pygame.mixer.Sound("audio/infernoFire.wav")
        self.width = bg_size[0]
        self.height = bg_size[1]
        self.damage = NB["infernoFire"]["damage"]
        self.dmgType = "fire"
        self._reset()

    def update(self, delay, sprites, canvas):
        if self.rect.top<self.height:
            self.rect.left += self.speed[0]
            self.rect.top += self.speed[1]
            color = choice( [(60,10,0,230), (120,40,0,230)] )
            canvas.addTrails( [5,7,9], [21,24,27], color, getPos(self, 0.3+random()*0.4, 0.5+random()*0.2) )
        else:
            self._reset()
            return
        if not delay%DMG_FREQ:
            for each in sprites:
                if ( collide_mask( self, each ) ):
                    if each.rect.left+each.rect.width//2 > self.rect.left+self.rect.width//2:
                        each.hitted(self.damage, 3, self.dmgType)
                        canvas.addSpatters( 4, (2,4,6), (6,7,8), (255,240,0,230), getPos(self, 0.5+random()*0.5, 0.2+random()*0.2), True )
                    else:
                        each.hitted(self.damage, -3, self.dmgType)
                        canvas.addSpatters( 4, (2,4,6), (6,7,8), (255,240,0,230), getPos(self, random()*0.5, 0.2+random()*0.2), False )
        if not (delay % 6):              # 若delay整除6，则切换图片
            self.imgIndx = ( self.imgIndx+1 ) % len(self.imgList)
            self.image = self.imgList[self.imgIndx]
            self.mask = pygame.mask.from_surface(self.image)
    
    def _reset(self):
        self.snd.play(0)
        self.speed = [choice([-4, 4]), 3]
        rot = -125 if self.speed[0]<0 else 125
        self.imgList = [pygame.transform.rotate(each, -rot) for each in self.ori_imgList]
        self.image = self.imgList[0]
        self.imgIndx = 0
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        if self.speed[0]<0:
            self.rect.left = self.width
        else:
            self.rect.right = 0
        self.rect.bottom = randint(-60, self.height//2)

# -----------------------------------
class Gozilla(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            Gozilla.imgLib = {
                "iList": createImgList( "image/stg1/gozilla0.png", "image/stg1/gozilla1.png", 
                    "image/stg1/gozilla0.png", "image/stg1/gozilla2.png" ),
                "attList": createImgList( "image/stg1/gozillaAtt1.png", 
                    "image/stg1/gozillaAtt2.png", 
                    "image/stg1/gozillaAtt3.png", 
                    "image/stg1/gozillaAtt4.png")
            }
            Gozilla.shadLib = getShadLib(Gozilla.imgLib)
        
        # calculate its position
        Monster.__init__(self, "gozilla", (255,0,0,240), 6, 1, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.alterSpeed( choice([1,-1]) )

    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)
        self.rect.left += self.speed
        self.rect.bottom += self.gravity
        if (getPos(self,0.8,0)[0] >= self.scope[1] and self.speed > 0) or (getPos(self,0.2,0)[0] <= self.scope[0] and self.speed < 0):
            self.alterSpeed(-self.speed)
        if not (delay % 8):
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
        if ( self.coolDown==0 ):
            for each in sprites:
                if collide_mask(self, each):
                    self.coolDown = 40
        if (self.coolDown > 0):
            self.coolDown -= 1
            self.cratch( sprites )
        # Check Hero and Turn speed
        self.detectHero(sprites)
    
    def cratch(self, sprites):
        if (self.coolDown <= 22):
            return
        if (self.coolDown >= 36):
            self.attIndx = 0
        elif (self.coolDown >= 32):
            self.attIndx = 1
        elif (self.coolDown >= 29):
            self.attIndx = 2
        elif (self.coolDown >= 26):
            self.attIndx = 3
            if ( self.coolDown == 26 ):
                cldList( self, sprites )
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
        self.setImg("attList",self.attIndx)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# -----------------------------------
class MegaGozilla(Monster):
    imgLib = None
    shadLib = None
    fireSnd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            MegaGozilla.imgLib = {
                "iList": createImgList( "image/stg1/megaGozilla0.png", "image/stg1/megaGozilla1.png", 
                    "image/stg1/megaGozilla0.png", "image/stg1/megaGozilla2.png" ),
                "att": createImgList( "image/stg1/megaGozillaAtt.png"), 
                "alarm": createImgList("image/stg1/megaGozillaAlarm.png")
            }
            MegaGozilla.shadLib = getShadLib(MegaGozilla.imgLib)
            MegaGozilla.fireSnd = pygame.mixer.Sound("audio/megaGozFire.wav")
        
        # calculate its position
        Monster.__init__(self, "megaGozilla", (255,0,0,240), 6, 3, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.alterSpeed( choice([1,-1]) )
        self.airCnt = 0           # indicate if I'm spitting!
        self.hitAccum = 0
    
    def move(self, delay, sprites, canvas):
        self.checkHitBack(obstacle=True)
        if (self.airCnt==0):
            if not (delay%2):
                self.rect.left += self.speed
                self.rect.bottom += self.gravity
                # touch the edge and turn around
                if (getPos(self,0.75,0)[0] >= self.scope[1] and self.speed > 0) or (getPos(self,0.25,0)[0] <= self.scope[0] and self.speed < 0):
                    self.alterSpeed(-self.speed)
                # renew the image of megaGozilla
                if not (delay % 10):
                    trPos = [ self.rect.left+self.rect.width//2, self.rect.bottom ]
                    self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
                    self.setImg("iList",self.imgIndx)
                    self.rect = self.image.get_rect()
                    self.rect.left = trPos[0]-self.rect.width//2
                    self.rect.bottom = trPos[1]
            for hero in sprites:
                heroPos = getPos(hero,0.5,0)
                myPos = getPos(self,0.5,0)
                # 如果有英雄在同一层，则将速度改为朝英雄方向。
                if (hero.onlayer-1)==self.onlayer:
                    # 判断是否需要转向
                    if ( self.scope[0]<=heroPos[0]<=self.scope[1] ):
                        if self.speed*( heroPos[0]-myPos[0] ) < 0:
                            self.alterSpeed(-self.speed)
                            break     # ***这里碰到第一个英雄符合条件就退出了。因此，如果两个英雄同时在一层中，P1总是会被针对，而P2永远不会被选中为目标。
                    # 判断是否需要攻击
                    if (self.speed<0 and -225<=heroPos[0]-myPos[0]<0) or (self.speed>0 and 0<heroPos[0]-myPos[0]<225):
                        self.airCnt = 76
                        self.fireSnd.play(0)
        elif self.airCnt>0:
            self.airCnt -= 1
            if self.airCnt>60:
                self.setImg("alarm")
            else:
                self.setImg("att")
                if self.speed <= 0:
                    spd = [ choice([-3,-4]), choice([-2, -1, 1, 2]) ]
                    startX = 0.34
                elif self.speed > 0:
                    spd = [ choice([3,4]), choice([-2, -1, 1, 2]) ]
                    startX = 0.66
                # 每次刷新均吐出2个气团
                canvas.addAirAtoms( self, 2, getPos(self, startX, 0.37), spd, sprites, "fire" )
    
    def reportHit(self, tgt):
        self.hitAccum += 1
        if self.hitAccum>=12:
            self.hitAccum = 0
            tgt.hitted( self.damage, self.push, "fire" )

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)
    
# -----------------------------------
class Dragon(Monster):
    imgLib = None
    shadLib = None
    fireSnd = None

    def __init__(self, wallHeight, onlayer, boundaries):
        if not self.imgLib:
            Dragon.imgLib = {
                "iList": createImgList("image/stg1/dragonLeft0.png","image/stg1/dragonLeft1.png",
                    "image/stg1/dragonLeft2.png","image/stg1/dragonLeft3.png",
                    "image/stg1/dragonLeft2.png","image/stg1/dragonLeft1.png")
            }
            Dragon.shadLib = getShadLib(Dragon.imgLib)
            Dragon.fireSnd = pygame.mixer.Sound("audio/dragonFire.wav")
        
        # calculate its position
        Monster.__init__(self, "dragon", (255,0,0,240), 0, 1, onlayer)
        self.boundaries = boundaries
        # initialize the sprite
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = randint(boundaries[0], boundaries[1]-self.rect.width)
        self.rect.top = wallHeight - 190
        self.alterSpeed( choice([-1, 1]) )
        self.coolDown = randint(240,480)
        self.upDown = 2

    def move(self, delay):
        self.checkHitBack()
        if not (delay % 20):
            self.rect.top += self.upDown
            self.upDown = - self.upDown
        if not (delay % 6 ):
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
        self.rect.left += self.speed
        if (self.rect.left<=self.boundaries[0] and self.speed < 0) or (self.rect.right>=self.boundaries[1] and self.speed > 0):
            self.alterSpeed(-self.speed)
        # randomly fire
        self.coolDown -= 1
        if self.coolDown<=0:
            self.fireSnd.play(0)
            self.coolDown = randint(120,480)
            return Fire(getPos(self, 0, 1), self.onlayer, -2, 0) if (self.direction=="left") else Fire(getPos(self,0.95,1), self.onlayer, 2, 0)
        return None

    def level(self, dist):
        self.rect.left += dist
        self.boundaries = (self.boundaries[0]+dist, self.boundaries[1]+dist)
    
class Fire(InanimSprite):
    def __init__(self, pos, layer, speed, iniG):
        InanimSprite.__init__(self, "fire")
        self.ori_image = load("image/stg1/fire.png").convert_alpha()
        self.image = self.ori_image.copy()
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]
        self.rect.bottom = pos[1]
        self.mask = pygame.mask.from_surface(self.image)
        self.damage = MB["dragon"].damage
        self.dmgType = MB["dragon"].dmgType
        self.onlayer = int(layer)
        self.gravity = iniG
        self.speed = speed
        self.angle = 0
        if speed>0:
            self.push = 6
        else:
            self.push = -6

    def update(self, delay, sideWalls, downWalls, keyLine, sprites, canvas, bg_size):
        self.rect.left += self.speed
        self.rect.bottom += self.gravity
        canvas.addTrails( [4,5,6], [8,10,12], (240,190,0,220), getPos(self, 0.4+random()*0.3, 0.4+random()*0.3) )
        if cldList( self, sprites ):      # 命中英雄
            self._explode(canvas)
            return None
        if ( pygame.sprite.spritecollide(self, downWalls, False, collide_mask) ) or ( pygame.sprite.spritecollide(self, sideWalls, False, collide_mask) ) or self.rect.top>=bg_size[1] or self.rect.right<=0 or self.rect.left>=bg_size[0]:
            self._explode(canvas)
            return None
        if not (delay % 6):
            if self.speed <= 0:
                self.angle = (self.angle+40) % 360
            else:
                self.angle = (self.angle-40) % 360
            self.image = rot_center(self.ori_image, self.angle)
            if (self.gravity < 5):
                self.gravity += 1
        if ( self.rect.top >= keyLine ):  # 因为只有大于检查，因此只有初始行之下的砖块会与之碰撞
            self.onlayer = max(self.onlayer-2, -1)
        return None

    def _explode(self, canvas):
        canvas.addSpatters( 5, [4,5,6], [18,20,22], (20,10,10,255), getPos(self,0.5,0.8), True )
        canvas.addSmoke(5, (6,8,10), 6, (10,10,10,180), getPos(self,0.5,0.8), 10)
        self.kill()
        del self

#------------------------------------
class DragonEgg(Monster):
    imgLib = None
    shadLib = None
    fireSnd = None
    crushSnd = None

    def __init__(self, wallGroup, sideGroup, onlayer):
        if not self.imgLib:
            DragonEgg.imgLib = {
                "iList": createImgList("image/stg1/dragonEgg.png", "image/stg1/dragonEggBroken.png"),
                "baby": createImgList("image/stg1/eggBaby.png", "image/stg1/eggBabyAtt.png")
            }
            DragonEgg.shadLib = getShadLib(DragonEgg.imgLib)
            DragonEgg.fireSnd = pygame.mixer.Sound("audio/dragonFire.wav")
            DragonEgg.crushSnd = pygame.mixer.Sound("audio/wizard/hit.wav")
        
        # calculate its position
        Monster.__init__(self, "dragonEgg", (250,0,80,240), 0, 4, onlayer, sideGroup)
        # note： 这里bowler的onlayer，以及其stone的onlayer值均为砖的行数，并非自身的行数，使用时不需要-1操作
        self.wallList = []       # 存储本行的所有砖块;
        for aWall in wallGroup:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            self.wallList.append(aWall)
        wall = choice(self.wallList)
        # initialize the sprite
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        # Inner baby dragon
        self.babyR = { "left":[ (0.5,0.04), (0.52,0.06) ], "right":[ (0.5,0.04), (0.48,0.06) ] }    # 分别为左和右时的位置信息
        self.baby = Ajunction( 
                            self.imgLib["baby"][self.direction][0], 
                            getPos(self, self.babyR[self.direction][0][0], 
                            self.babyR[self.direction][0][1]) 
                    )
        self.attCnt = 0
        self.broken = -1    #-1表示健康；0表示打破，等待生成babydragon的瞬间；1表示打破且已生成dragon
        self.barOffset = 30

    def move(self, delay, sprites):
        if self.broken>=0:
            return
        # checkhitback: 仅计算时间，不进行位移
        if abs(self.hitBack)>0:
            self.hitBack -= self.hitBack//abs(self.hitBack)
        # update baby image
        if self.attCnt>0:
            self.attCnt -= 1
            r = self.babyR[self.direction][1]
            bimg = self.imgLib["baby"][self.direction][1]
        else:
            r = self.babyR[self.direction][0]
            bimg = self.imgLib["baby"][self.direction][0]
        self.baby.updateImg( bimg )
        self.baby.updatePos( getPos(self, r[0], r[1]) )
        
        if not (delay % 30 ):
            heroX = choice(sprites).rect.left
            if self.rect.left > heroX:
                self.direction = "left"
            else:
                self.direction = "right"
            # randomly fire
            if not (delay % 60) and random()<0.4:  # Controlling the frequency of fire.
                self.attCnt = 12
                self.fireSnd.play(0)
                if self.direction=="left":
                    return Fire(getPos(self,0.2,0), self.onlayer+2, randint(-3,-1), -2)
                else:
                    return Fire(getPos(self,0.8,0), self.onlayer+2, randint(1,3), -2)

    def hitted(self, damage, pushed, dmgType):
        # decrease health & no hitback
        self.health -= (damage*self.realDmgRate)
        if self.health <= 0:                # broken
            self.health = 0
            self.crushSnd.play(0)
            self.spurtCanvas.addPebbles(self, 6, type="eggDebri")
            # alter image
            self.broken = 0
            trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
            self.setImg("iList", 1)
            self.rect = self.image.get_rect()
            self.rect.left = trPos[0]-self.rect.width//2
            self.rect.bottom = trPos[1]
            # kill baby
            if hasattr(self, 'baby'):
                self.baby.kill()
                del self.baby
            return True

    def paint(self, screen):
        # draw shadow
        shadRect = self.rect.copy()
        shadRect.left -= 8
        screen.blit(self.shad, shadRect)
        # draw baby
        if self.broken<0:
            screen.blit( self.baby.image, self.baby.rect )
        screen.blit( self.image, self.rect )
        # Hit highlight
        if self.hitBack:
            screen.blit( self.shad, self.rect )

# -----------------------------------
class CrimsonDragon(Boss):

    def __init__(self, x, y, onlayer, font):
        # initialize the sprite
        Boss.__init__(self, font, "CrimsonDragon", (255, 0, 0, 240), 0, 3, onlayer)
        self.imgLib = {
            "body": createImgList("image/stg1/DragonBody.png")
        }
        self.shadLib = getShadLib(self.imgLib)
        # ----- body part (the core of the CrimsonDragon) ------
        self.setImg("body")
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = x
        self.rect.top = y
        # ------------- head part --------------
        self.headLeft = [ load("image/stg1/DragonHead0.png").convert_alpha(), load("image/stg1/DragonHead1.png").convert_alpha(), 
            load("image/stg1/DragonHead2.png").convert_alpha() ]
        self.headRight = [ flip(self.headLeft[0], True, False), flip(self.headLeft[1], True, False), 
            flip(self.headLeft[2], True, False) ]
        self.headR = { "left":[ (0,0.6), (0,0.61), (0,0.62) ], "right":[ (1,0.6), (1,0.61), (1,0.62) ] }    # 分别为左和右时的位置信息
        self.head = Ajunction( self.headLeft[2], getPos(self, self.headR[self.direction][0][0], self.headR[self.direction][0][1]) )
        self.headIndx = 0
        # ------------- wing part ----------------
        self.wingLeft = [ load("image/stg1/wing0.png").convert_alpha(), load("image/stg1/wing1.png").convert_alpha(), load("image/stg1/wing2.png").convert_alpha(), load("image/stg1/wing3.png").convert_alpha(), 
            load("image/stg1/wing2.png").convert_alpha(), load("image/stg1/wing1.png").convert_alpha(), load("image/stg1/wing0.png").convert_alpha() ]
        self.wingRight = [ flip(self.wingLeft[0], True, False), flip(self.wingLeft[1], True, False), flip(self.wingLeft[2], True, False), flip(self.wingLeft[3], True, False), 
            flip(self.wingLeft[4], True, False), flip(self.wingLeft[5], True, False), flip(self.wingLeft[6], True, False) ]
        self.wingR = { "left":[ (0.5,-0.3), (0.5,-0.21), (0.5,0.1), (0.5,0.3), (0.5,0.1), (0.5,-0.21), (0.5,-0.3) ], "right":[ (0.5,-0.3), (0.5,-0.21), (0.5,0.1), (0.5,0.3), (0.5,0.1), (0.5,-0.21), (0.5,-0.3) ] }
        self.wing = Ajunction( self.wingLeft[0], getPos(self, self.wingR[self.direction][0][0], self.wingR[self.direction][0][1]) )
        self.wingIndx = 0
        # -------------- tail part ---------------
        self.tailLeft = [ load("image/stg1/tail0.png").convert_alpha(), load("image/stg1/tail1.png").convert_alpha(), load("image/stg1/tail2.png").convert_alpha(), 
            load("image/stg1/tail3.png").convert_alpha(), load("image/stg1/tail2.png").convert_alpha(), load("image/stg1/tail1.png").convert_alpha() ]
        self.tailRight = [ flip(self.tailLeft[0], True, False), flip(self.tailLeft[1], True, False), flip(self.tailLeft[2], True, False), 
            flip(self.tailLeft[3], True, False), flip(self.tailLeft[4], True, False), flip(self.tailLeft[5], True, False) ]
        self.tailR = { "left":[ (0.76,0.84), (0.76,0.84), (0.72,0.84), (0.68,0.84), (0.72,0.84), (0.76,0.84) ], "right":[ (0.24,0.84), (0.24,0.84), (0.28,0.84), (0.32,0.84), (0.28,0.84), (0.24,0.84) ] }
        self.tail = Ajunction( self.tailLeft[0], getPos(self, self.tailR[self.direction][0][0], self.tailR[self.direction][0][1]) )
        self.tailIndx = 0
        # ----------- other attributes -------------------------
        self.cnt = 1600      # count for the loop of shift position
        self.coolDown = 0    # count for attack coolDown
        self.nxt = (0, 0)
        self.growlSnd = pygame.mixer.Sound("audio/redDragonGrowl.wav")
        self.moanSnd = pygame.mixer.Sound("audio/redDragonMoan.wav")
        self.upDown = 3      # 悬停状态身体上下振幅

    def update(self, sprites, canvas):
        self.checkHitBack()
        self._tipPosition(canvas)
        if not (self.cnt % 3):
            if self.shift( self.nxt[0], self.nxt[1] ):
                # 如果处于悬停状态，则随着扇翅上下摆动，and shakes tail。
                if not (self.cnt % 18):
                    self.rect.top += self.upDown
                    self.upDown = - self.upDown
                    self.tailIndx = (self.tailIndx+1)%len(self.tailLeft)
            self.wingIndx = (self.wingIndx+1) % len(self.wingLeft)
            self.setImg("body")
            if self.direction == "left":
                self.head.updateImg( self.headLeft[self.headIndx] )
                self.wing.updateImg( self.wingLeft[self.wingIndx] )
                self.tail.updateImg( self.tailLeft[self.tailIndx] )
            elif self.direction == "right":
                self.head.updateImg( self.headRight[self.headIndx] )
                self.wing.updateImg( self.wingRight[self.wingIndx] )
                self.tail.updateImg( self.tailRight[self.tailIndx] )
            self.mask = pygame.mask.from_surface(self.image)
            self.head.updatePos( getPos(self, self.headR[self.direction][self.headIndx][0], self.headR[self.direction][self.headIndx][1]) )
            self.wing.updatePos( getPos(self, self.wingR[self.direction][self.wingIndx][0], self.wingR[self.direction][self.wingIndx][1]) )
            self.tail.updatePos( getPos(self, self.tailR[self.direction][self.tailIndx][0], self.tailR[self.direction][self.tailIndx][1]) )
        # count down for rage actions.
        self.cnt -= 1
        if self.cnt<=0:
            self.cnt = 1800
        elif self.cnt>=240:
            if not self.cnt%60:
                self.nxt = ( randint(100,640), randint(80,520) )   # randomize a new position
                self.direction = "left" if ( self.nxt[0] < getPos(self, 0.5, 0.5)[0] ) else "right"
        else:
            self.nxt = ( 520, 80 )
            self.direction = "left"
            if not self.cnt%8:
                return self.makeFire( sprites )
        # deal regular fire attack:
        self.headIndx = 0
        if not (self.cnt % 12) and self.coolDown<=0 and random()<0.26:
            self.growlSnd.play(0)
            self.coolDown = 90
            return self.makeFire( sprites )
        elif self.coolDown > 0:
            self.coolDown -= 1
            if self.coolDown >= 84:
                self.headIndx = 1
            elif self.coolDown >= 78:
                self.headIndx = 2
            elif self.coolDown >= 72:
                self.headIndx = 1
        return None
    
    def makeFire(self, sprites):
        tgt = choice( sprites )
        aim = getPos( tgt,0.5,0.5 )
        deltaX = aim[0] - getPos( self.head, 0.5, 0.5 )[0]
        deltaY = aim[1] - getPos( self.head, 0.5, 0.5 )[1]
        time = round( ( deltaX**2 + deltaY**2 )**0.5 / 6 )
        spdX = round( deltaX/time )
        spdY = round( deltaY/time )
        degree = math.degrees( math.atan2(spdY, spdX) )      # 两点线段的弧度值，并弧度转角度
        fire = RedDragonFire( getPos(self.head,0.2,0.6), (spdX, spdY), tgt.onlayer-1, degree ) if self.direction=="left" else RedDragonFire( getPos(self.head,0.8,0.6), (spdX, spdY), tgt.onlayer-1, degree )
        return fire

    def paint(self, screen):
        '''鉴于本对象的构造非常复杂，因此提供一个专门的绘制接口
            给此函数传递一个surface参数，即可在该surface上绘制（blit）完整的本对象'''
        # draw shadow
        shadRect = self.rect.copy()
        shadRect.left -= 12
        screen.blit(self.shad, shadRect)
        # draw self
        screen.blit( self.tail.image, self.tail.rect )
        screen.blit( self.image, self.rect )
        screen.blit( self.head.image, self.head.rect )
        screen.blit( self.wing.image, self.wing.rect )
        # Hit highlight
        if self.hitBack:
            screen.blit( self.shad, self.rect )
        
    def erase(self):
        self.moanSnd.play(0)
        self.head.kill()
        self.wing.kill()
        del self.head, self.wing
        self.kill()
        return True   # dead

    def shift(self, final_x, final_y):
        x = self.rect.left + self.rect.width/2
        y = self.rect.top + self.rect.height/2
        if (x == final_x) or (y == final_y):
            return True   # 表示已到目标
        maxSpan = 8
        spd = 4
        dist = 0
        if (x < final_x):
            dist = math.ceil( (final_x - x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left += dist
        elif (x > final_x):
            dist = math.ceil( (x - final_x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left -= dist
        if (y < final_y):
            dist = math.ceil( (final_y - y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top += dist
        elif (y > final_y):
            dist = math.ceil( (y - final_y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top -= dist
        return False    # 表示未到目标

class RedDragonFire(InanimSprite):
    def __init__(self, pos, spd, layer, degree):   # 参数pos为本对象初始的位置
        InanimSprite.__init__(self, "fire")
        self.imageList = [ pygame.transform.rotate( load("image/stg1/fire.png").convert_alpha(), -degree ), 
            pygame.transform.rotate( load("image/stg1/fire.png").convert_alpha(), degree ) ]
        self.imgIndx = 0
        self.image = self.imageList[0]
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.top = pos[1]-self.rect.height//2
        self.mask = pygame.mask.from_surface(self.image)
        self.speed = spd
        if spd[0]>0:
            self.push = 9
        else:
            self.push = -9
        self.damage = MB["CrimsonDragon"].damage
        self.dmgType = MB["CrimsonDragon"].dmgType
        self.blastSnd = pygame.mixer.Sound("audio/wizard/hit.wav")
        self.onlayer = layer

    def update(self, delay, sideWalls, downWalls, keyLine, sprites, canvas, bg_size):
        if pygame.sprite.spritecollide(self, downWalls, False, collide_mask) or pygame.sprite.spritecollide(self, sideWalls, False, collide_mask):
            self._explode(canvas)
            return "vib"
        # generate some sparks
        canvas.addTrails( [4,5,6], [20,24,28], (240,160,20,210), getPos(self, 0.3+random()*0.4, 0.3+random()*0.4) )
        if not delay%4:
            self.imgIndx = (self.imgIndx+1) % len(self.imageList)
            self.image = self.imageList[self.imgIndx]
            self.mask = pygame.mask.from_surface(self.image)
            canvas.addTrails( [4,5,6], [10,12,14], (120,90,30,190), getPos(self,0.5,0.5) )
        if cldList(self, sprites):
            self._explode(canvas)
            return "vib"
        # move the object
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        return None

    def _explode(self, canvas):
        self.blastSnd.play(0)
        canvas.addExplosion(getPos(self,0.5,0.5), 30, 15)
        canvas.addSmoke( 6, (4, 6, 8), 2, (2,2,2,240), getPos(self,0.5,0.5), 4 )
        self.kill()
        del self
        return

# ===========================================================================
# -------------------------------- Stage 2 ----------------------------------
# ===========================================================================
class Column(InanimSprite):
    def __init__(self, bg_size):
        InanimSprite.__init__(self, "column")
        self.image = load("image/stg2/column.png").convert_alpha()
        self.alarmList = [ load("image/stg2/alarm0.png").convert_alpha(), load("image/stg2/alarm1.png").convert_alpha(), 
            load("image/stg2/alarm2.png").convert_alpha(), load("image/stg2/alarm3.png").convert_alpha(), 
            load("image/stg2/alarm4.png").convert_alpha(), load("image/stg2/alarm5.png").convert_alpha() ]
        self.alarmRect = None
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.width = bg_size[0]
        self.height = bg_size[1]
        self.damage = NB["column"]["damage"]
        self.dmgType = "physical"
        self.speed = 8
        self.aim = [0, 0]     # 当delay重置为0时就获取并更新hero的中心坐标
        self.rect.right = 0
        self.rect.bottom = 0  # 初始位置于屏幕左上角 （每个区域都有一个，因此其他区域的会保持在此处一段时间）
        self.t = 260          # 循环时间周期，可在main中动态调整以改变游戏难度
        self.delay = self.t-30 # index that controll the fall and wait (there would be 0.5 sec before the first fall)
        self.dustCnt = -1
        self.status = None
        self.hitSnd = pygame.mixer.Sound("audio/crush.wav")

    def update(self, sprites, frnLayer, groupList, spurtCanvas):
        self.delay = ( self.delay + 1 ) % self.t
        # 确认目的地 (0为等待目的地的状态)
        if ( self.delay == 0 ):
            tgt = choice(sprites)
            if tgt.aground:
                # 英雄在落地状态，可以进行攻击。但首先需要判断自己的真正落点（必须落在linewall上，不能悬空）。
                self.aim[0] = tgt.rect.left + tgt.rect.width // 2
                self.aim[1] = tgt.rect.bottom
                aimLayer = tgt.onlayer-1   # 这里采用砖块的行数系统（奇数），以方便查找最终落点
                flag = False               # 修改位
                while (not flag) and (str(aimLayer) in groupList):
                    #遍历该层所有行砖，检查是否可以落在该行上
                    for wall in groupList[str(aimLayer)]:
                        if wall.rect.left <= self.aim[0] <= wall.rect.right:
                            self.aim[1] = wall.rect.top
                            flag = True
                            break
                    aimLayer -= 2
            else:
                return
        # 警告阶段 (1~33)
        elif ( 1 <= self.delay < 34 ):
            self.status = "alarm"
            return
        # 开始下落（34时刻reset）
        elif ( self.delay == 34 ):
            if ( frnLayer >= 30 and self.t >= 260 ) or ( frnLayer >= 60 and self.t >= 240 ) or ( frnLayer >= 90 and self.t >= 220 ):
                self.t -= 20
            self.rect.left = self.aim[0] - self.rect.width//2
            self.rect.bottom = 0
            self.status = "falling"
            return
        # 下落中（34时刻以后首先进入falling状态）
        elif (self.status=="falling"):
            self.rect.bottom += self.speed
            if not self.delay%DMG_FREQ:
                for each in sprites:
                    if ( collide_mask( self, each ) ):
                        if each.rect.left+each.rect.width//2 > self.rect.left+self.rect.width//2:
                            each.hitted(self.damage, 3, self.dmgType)
                        else:
                            each.hitted(self.damage, -3, self.dmgType)
            if ( self.rect.bottom >= self.aim[1] ):  # 抵达落点
                self.hitSnd.play(0)
                # 炸开
                spurtCanvas.addPebbles( self, 9 )
                spurtCanvas.addSpatters(6, [3,5,7], [24,28,32], (80,80,110), getPos(self,0.5,0.6), falling=True)
                self.dustCnt = 0
                self.status = "ash"
                return "vib"
        # 抵达落点后
        else:
            if self.dustCnt == 47:
                self.dustCnt = -1
                self.alarmRect = None
            elif (self.dustCnt >= 0) and (self.dustCnt < 47):
                self.alarmRect = self.alarmList[ (self.dustCnt)//8 ].get_rect()  # 获取新的图片的rect
                self.alarmRect.left = self.aim[0] - self.alarmRect.width // 2  # 设定x位置
                self.alarmRect.bottom = self.aim[1]  # 设定y位置
                self.dustCnt += 1
    
    def paint(self, surface):
        if self.status == "falling":
            surface.blit( self.image, self.rect )
        # 特殊阶段额外paint
        if self.status == "alarm":
            pygame.draw.line( surface, (0,160,210), (self.aim[0],0), (self.aim[0],self.aim[1]), randint(1,4))
        elif self.status == "ash" and self.alarmRect:
            surface.blit( self.alarmList[ (self.dustCnt)//8 ], self.alarmRect )

    def lift(self, dist, limit=False):
        self.rect.bottom += dist
        self.aim[1] += dist

    def level(self, dist):
        self.rect.left += dist
        self.aim[0] += dist

# -----------------------------------
class Bat(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, onlayer):
        if not self.imgLib:
            Bat.imgLib = {
                "hang": createImgList("image/stg2/batHang.png"),
                "flyList": createImgList("image/stg2/bat0.png","image/stg2/bat1.png")
            }
            Bat.shadLib = getShadLib(Bat.imgLib)
        
        # calculate its position
        Monster.__init__(self, "bat", (80,10,80,240), 3, 1, onlayer)
        self.wallList = []       # 存储本行的所有砖块; # 每次初始化一个新实例时，清空此类的wallList（否则会在上一个实例的基础上再加！）
        posList = []             # 辅助列表，用于暂时存储本行砖块的位置（左边线）
        for aWall in wallGroup:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            #if not aWall.category == "specialWall":
            self.wallList.append(aWall)
            posList.append(aWall.rect.left)
        if len(self.wallList)==0:
            self.kill()
            return
        wall = choice(self.wallList)
        self.onlayer = int(onlayer)
        self.foot = wall.rect.bottom - 8
        # initialize the sprite ---------------
        self.imgIndx = 0
        self.setImg("hang")
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left + (wall.rect.width-self.rect.width) // 2
        self.rect.top = self.foot
        self.damage = MB["bat"].damage
        self.coolDown = 0
        self.speed = [0, 0]
        self.vib = 2
        self.tgt = None      # tgt将取三类值：None表示休息中；hero对象表示追击敌人；lineWall对象表示从飞行状态转入休息的短暂动作。
    
    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)
        # 睡眠状态。若有hero接近，则将之唤醒。
        if not self.tgt:
            for each in sprites:
                if math.pow( getPos(each,0.5,0.5)[0]-getPos(self,0.5,0.5)[0], 2 ) + math.pow( getPos(each,0.5,0.5)[1]-getPos(self,0.5,0.5)[1], 2 )<100**2:
                    self.tgt = each
                    self.imgIndx = 0
                    break
        # 有tgt的飞行状态，又分为两类：
        else:
            myPos = getPos(self, 0.5, 0.5)
            tgtPos = getPos(self.tgt, 0.5, 0.5)
            # tgt引用的是砖块，表示飞向最近的砖块，并悬停在下面。
            if self.tgt.category in ("lineWall", "specialWall"):
                if ( self.tgt.rect.left < myPos[0] < self.tgt.rect.right ) and ( self.rect.top <= self.foot ):
                    self.tgt = None
                    trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
                    self.setImg("hang")
                    self.rect = self.image.get_rect()
                    self.rect.left = trPos[0]-self.rect.width//2
                    self.rect.bottom = trPos[1]
                    self.imgIndx = 0
                    return
                elif myPos[0] < tgtPos[0]:
                    self.speed[0] = 1
                elif myPos[0] > tgtPos[0]:
                    self.speed[0] = -1
            # tgt引用的是hero，则为追击模式！
            elif self.tgt.category=="hero":
                # 检查：目标死亡；或距离过大，丢失目标
                if (self.tgt.health <= 0) or math.pow( tgtPos[0]-myPos[0], 2 ) + math.pow( tgtPos[1]-myPos[1], 2 )>160**2:
                    if len(self.wallList)==0:
                        self.kill()
                        return
                    # 先初始化为任意一块。
                    w = choice(self.wallList)
                    dist = abs( myPos[0]-getPos(w,0.5,0.5)[0] )
                    self.tgt = w
                    # 比较距离，找出最近的砖块。
                    for each in self.wallList:
                        newDist = abs( myPos[0]-getPos(each,0.5,0.5)[0] )
                        if newDist < dist:
                            dist = newDist
                            self.tgt = each
                    return
                elif not delay%3:       # 继续追击
                    if myPos[0] < tgtPos[0]:
                        self.speed[0] = 1
                    elif myPos[0] > tgtPos[0]:
                        self.speed[0] = -1
                    else:
                        self.speed[0] = 0
            # Move the bat.
            if not delay%2:
                if abs(self.speed[1]) > 6:
                    self.vib = -self.vib
                self.speed[1] += self.vib
                self.rect.left += self.speed[0]
                self.rect.top += self.speed[1]
                # Change image.
                if not (delay % 8):
                    trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
                    self.setImg("flyList",self.imgIndx)
                    self.rect = self.image.get_rect()
                    self.rect.left = trPos[0]-self.rect.width//2
                    self.rect.bottom = trPos[1]
                    self.mask = pygame.mask.from_surface(self.image)    # 更新mask，使得与hero重合的判断更加精确
                    self.imgIndx = (self.imgIndx+1) % len(self.imgLib["flyList"])
            # deal damage.
            if self.coolDown==0:
                for each in sprites:
                    if collide_mask(self, each):
                        self.coolDown = 16
            else:
                if self.coolDown == 12:
                    cldList( self, sprites )
                self.coolDown -= 1

    def lift(self, dist):
        self.rect.bottom += dist
        self.foot += dist

# -----------------------------------
class Golem(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            Golem.imgLib = {
                "iList": createImgList("image/stg2/golemLeft0.png", "image/stg2/golemLeft1.png"),#, "image/stg2/golemLeft2.png"),
                "attList": createImgList("image/stg2/golemLAtt0.png", "image/stg2/golemLAtt1.png"),
                "crushList": createImgList("image/stg2/crush0.png", "image/stg2/crush1.png", "image/stg2/crush2.png")
            }
            Golem.shadLib = getShadLib(Golem.imgLib)
        
        # calculate its position
        Monster.__init__(self, "golem", (240,240,255,240), 8, 4, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.doom = 0
        self.alterSpeed( choice([-1, 1]) )

    def move(self, delay, sprites):
        if self.health>0:
            self.checkHitBack(obstacle=True)
            # 运动
            if not (delay%2):
                self.rect.left += self.speed
                if (getPos(self,0.75,0)[0] >= self.scope[1] and self.speed > 0) or (getPos(self,0.25,0)[0] <= self.scope[0] and self.speed < 0):
                    self.alterSpeed(-self.speed)
                # 更新图片
                if self.coolDown<40 and not ( delay % 20 ):
                    self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
                    self.setImg("iList",self.imgIndx)
            # 检查攻击
            if self.coolDown == 0:
                for each in sprites:
                    if ( collide_mask(self, each) ):
                        self.coolDown = 60
            elif (self.coolDown > 0):
                self.coolDown -= 1
                self.bite(sprites)
        else:
            self.doom += 1
            if self.doom == 22:
                mite1 = Golemite( self.rect, self.scope, "left", self.onlayer, self.obstacle )
                mite2 = Golemite( self.rect, self.scope, "right", self.onlayer, self.obstacle )
                self.kill()
                return ( mite1, mite2 )
            elif self.doom == 15:
                self.setImg("crushList",2)
            elif self.doom == 8:
                self.setImg("crushList",1)
            elif self.doom == 1:
                self.setImg("crushList",0)
                self.spurtCanvas.addPebbles(self, 4)
    
    def bite(self, sprites):
        # deal damage
        if (self.coolDown >= 49):
            self.attIndx = 0    # 60-49蓄力图片
        elif (self.coolDown >= 40):
            self.attIndx = 1    # 48-40咬合图片
            if ( self.coolDown == 48 ):
                cldList( self, sprites )
        else: 
            return
        # switch image
        self.setImg("attList",self.attIndx)
    
    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        if self.health>0:
            self.health -= damage
            if self.health <= 0:
                self.health = 0
                return True
        else:
            return False    # 处于分裂小哥伦的状态，此时不应计算伤害

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

class Golemite(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, rect, scope, direct, onlayer, sideGroup):
        if not self.imgLib:
            Golemite.imgLib = {
                "iList": createImgList("image/stg2/golemiteLeft0.png","image/stg2/golemiteLeft1.png","image/stg2/golemiteLeft0.png","image/stg2/golemiteLeft2.png")
            }
            Golemite.shadLib = getShadLib(Golemite.imgLib)
        
        Monster.__init__(self, "golemite", (240,240,255,240), 4, 2, onlayer, sideGroup)
        self.category = "golem"
        self.scope = scope
        self.imgIndx = 0
        self.setImg("iList",0)
        if direct == "left":
            self.alterSpeed(-1)
        else:
            self.alterSpeed(1)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = rect.left+ rect.width//2 - self.rect.width//2
        self.rect.bottom = rect.bottom
        self.coolDown = 0
        self.doom = 0
    
    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)
        # deal move
        if not delay % 2:
            self.rect.left += self.speed
            if (getPos(self,0.75,0)[0] >= self.scope[1] and self.speed > 0) or (getPos(self,0.25,0)[0] <= self.scope[0] and self.speed < 0):
                self.alterSpeed(-self.speed)
        if not delay % 8:
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
        # deal attack
        if self.coolDown == 0:
            for each in sprites:
                if ( collide_mask(self, each) ):
                    self.coolDown = 60
        if (self.coolDown > 0):
            self.coolDown -= 1
            if ( self.coolDown == 45 ):
                cldList( self, sprites )
            
    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左
            self.hitBack = min( pushed+self.weight, 0 )
        self.health -= damage
        if self.health <= 0:
            self.spurtCanvas.addPebbles(self, 2)
            self.health = 0
            self.kill()
            return True

# -----------------------------------
class Bowler(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, sideGroup, onlayer):
        if not self.imgLib:
            Bowler.imgLib = {
                "iList": createImgList("image/stg2/bowler0.png","image/stg2/bowler0.png","image/stg2/bowler0.png","image/stg2/bowler1.png"),
                "throw": createImgList("image/stg2/bowlerThrow.png")
            }
            Bowler.shadLib = getShadLib(Bowler.imgLib)
        
        # calculate its position
        Monster.__init__(self, "bowler", (10,60,80,240), 0, 4, onlayer, sideGroup)
        # note： 这里bowler的onlayer，以及其stone的onlayer值均为砖的行数，并非自身的行数，使用时不需要-1操作
        self.wallList = []       # 存储本行的所有砖块;
        for aWall in wallGroup:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            self.wallList.append(aWall)
        wall = choice(self.wallList)
        # initialize the sprite
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.stoneList = []

    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)
        if not (delay % 60 ):
            heroX = choice(sprites).rect.left
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
            if self.rect.left > heroX:
                self.direction = "left"
            else:
                self.direction = "right"
            self.setImg("iList",self.imgIndx)
            self.rect = self.image.get_rect()
            self.rect.left = trPos[0]-self.rect.width//2
            self.rect.bottom = trPos[1]

    def throw(self, delay):
        if not (delay % 120) and (random() > 0.5):  # 控制投石频率
            trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
            self.setImg("throw")
            self.rect = self.image.get_rect()
            self.rect.left = trPos[0]-self.rect.width//2
            self.rect.bottom = trPos[1]
            stone = Stone((self.rect.left, self.rect.bottom), self.onlayer, self.direction)
            self.stoneList.append(stone)
            return stone

class Stone(InanimSprite):
    crushSnd = None

    def __init__(self, pos, onlayer, direction):
        if not Stone.crushSnd:
            Stone.crushSnd = pygame.mixer.Sound("audio/wizard/hit.wav")
        InanimSprite.__init__(self, "stone")
        self.coin = 0
        self.bldColor = (160,160,180,240)
        self.weight = 1

        self.image = load("image/stg2/stone.png").convert_alpha()
        self.oriImage = self.image
        self.deg = 0
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.damage = MB["stone"].damage
        self.rect.left = pos[0]
        self.rect.bottom = pos[1]
        self.onlayer = int(onlayer)
        self.gravity = 1
        self.speed = -2 if direction == "left" else 2   # 负数表示向左，正数向右
        self.health = MB["stone"].health      # 每次横向撞击，health-10

    def update(self, delay, sideWalls, downWalls, keyLine, sprites, canvas):
        self.rect.left += self.speed
        # 次数用尽，撞毁
        if ( self.health <= 0 ):
            canvas.addPebbles(self, 4)
            self.crushSnd.play(0)
            self.kill()
            del self
            return
        if not (delay % 4):
            self.deg = (self.deg+20) % 360
            self.image = rot_center(self.oriImage, self.deg) if self.speed <= 0 else rot_center(self.oriImage, -self.deg)
        # 水平撞击
        if not delay%DMG_FREQ:
            for each in sprites:
                if ( collide_mask(self, each) ):
                    pos = getPos(self, 0, 0.6) if self.speed<0 else getPos(self, 1, 0.6)
                    canvas.addSpatters(2, (2,3,4), (6,7,8), (40,40,40,255), pos, False)
                    push = -8 if (self.speed<0) else 8
                    each.hitted(self.damage, push, "physical")
        if ( pygame.sprite.spritecollide(self, sideWalls, False, collide_mask) ) or ( pygame.sprite.spritecollide(self, downWalls, False, collide_mask) ):
            # 和英雄的处理方法一样，尝试纵坐标-4，再看是否还会碰撞。4以内的高度都可以自动滚上去
            self.rect.top -= 4
            if getCld(self, downWalls, ["lineWall","specialWall"]) or getCld(self, sideWalls, ["baseWall","sideWall","hollowWall"]):
                pos = getPos(self, 0, 0.6) if self.speed<0 else getPos(self, 1, 0.6)
                canvas.addSpatters(4, (2,4,6), (6,7,8), (40,40,40,255), pos, True)
                self.rect.top += 4
                self.rect.left -= self.speed
                self.speed = - self.speed
                self.hitted(50, 0, "physical")
        # 下落
        self.rect.bottom += self.gravity
        while ( pygame.sprite.spritecollide(self, downWalls, False, collide_mask) ):
            # 当下落速度达到最大的7时，碰撞降低耐久
            if self.gravity==7:
                self.hitted(100, 0, "physical")
                self.gravity = 1
                self.crushSnd.play(0)
            self.rect.bottom -= 1
            if not ( pygame.sprite.spritecollide(self, downWalls, False, collide_mask) ): # 如果不再和wall有重合
                canvas.addSpatters(1, (2,3,4), (5,6,7), (40,40,40,255), getPos(self,0.5,1), False)
                self.gravity = 1
                return False
        if (self.gravity <= 6):
            self.gravity += 1
        if ( self.rect.top >= keyLine ):
            self.onlayer = max(self.onlayer-2, -1)
    
    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        self.health -= damage
    
    def drawHealth(self, surface):
        pass

# -----------------------------------
class Spider(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, y, onlayer, boundaries_x, boundaries_y):
        if not self.imgLib:
            Spider.imgLib = {
                "body": createImgList("image/stg2/miniSpider0.png", "image/stg2/miniSpider1.png")
            }
            Spider.shadLib = getShadLib(Spider.imgLib)
        
        # calculate its position
        Monster.__init__(self, "spider", (180,10,80,240), 3, 1, onlayer)

        self.scope_x = boundaries_x
        self.scope_y = boundaries_y
        self.imgIndx = 0
        self.setImg("body",0)
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = randint(self.scope_x[0], self.scope_x[1]-self.rect.width)
        self.rect.top = y
        self.speed = [-3,3]     # initial: left, down
        # ----------- other attributes -------------------------
        self.coolDown = 0
        self.doom = 0
        self.cnt = 0         # count for the loop of shift position
        self.coolDown = 0    # count for attack coolDown
        self.webSnd = pygame.mixer.Sound("audio/spitWeb.wav")
        self.upDown = 1
        self.parti = None
        self.haltCnt = randint(20,60)

    def move(self, delay, sprites):
        self.checkHitBack()
        if self.haltCnt>0:
            self.haltCnt -= 1
        # update image and move 
        if not delay % 2:
            # move
            if self.haltCnt==0:
                self.rect.left += self.speed[0]
                if (self.rect.right >= self.scope_x[1] and self.speed[0] > 0) or (self.rect.left <= self.scope_x[0] and self.speed[0] < 0):
                    self.speed[0] = -self.speed[0]                
                self.rect.top += self.speed[1]
                if (self.rect.bottom >= self.scope_y[1] and self.speed[1] > 0) or (self.rect.top <= self.scope_y[0] and self.speed[1] < 0):
                    self.speed[1] = -self.speed[1]
                # 随机停一会或变方向
                if not delay%24 and random()<0.1:
                    dice = random()
                    if dice<0.2:
                        self.haltCnt = 60
                    elif dice<0.6:
                        self.speed[0] = -self.speed[0]
                    else:
                        self.speed[1] = - self.speed[1]
                if not delay%8:
                    self.rect.top += self.upDown
                    self.upDown = -self.upDown
                    # 根据速度方向计算出需要rotate的degree，rotate the image
                    self.imgIndx = (self.imgIndx+1) % len(self.imgLib["body"]["left"])
                    self.setImg("body", indx=self.imgIndx)
                    tmpPos = getPos(self, 0.5, 0.5)
                    degree = math.degrees( math.atan2(self.speed[0], self.speed[1]) )
                    self.image = pygame.transform.rotate( self.image, degree )
                    self.rect = self.image.get_rect()
                    self.rect.left = tmpPos[0]-self.rect.width//2
                    self.rect.top = tmpPos[1]-self.rect.height//2
                    self.shad = pygame.transform.rotate( self.shad, degree )
                    self.mask = pygame.mask.from_surface(self.image)
            if self.speed[0]>0:
                self.direction = "right"
            elif self.speed[0]<0:
                self.direction = "left"
        # Deal Bite.
        if self.coolDown == 0:
            for each in sprites:
                if ( collide_mask(self, each) ):
                    self.coolDown = 45
                    self.haltCnt = 30
        if (self.coolDown > 0):
            self.coolDown -= 1
            if (self.coolDown == 36):
                cldList( self, sprites )

    def lift(self, dist):
        self.rect.bottom += dist
        self.scope_y = (self.scope_y[0]+dist, self.scope_y[1]+dist)

    def level(self, dist):
        self.rect.left += dist
        self.scope_x = (self.scope_x[0]+dist, self.scope_x[1]+dist)
    
    def paint(self, screen):
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 4
        screen.blit(self.shad, shadRect)
        screen.blit( self.image, self.rect )
        # 画打击阴影
        if self.hitBack:
            screen.blit( self.shad, self.rect )
    
# -----------------------------------
class GiantSpider(Boss):

    def __init__(self, y, onlayer, boundaries_x, boundaries_y, font):
        # initialize the sprite
        Boss.__init__(self, font, "GiantSpider", (250,80,120,240), 8, 3, onlayer)
        self.scope_x = boundaries_x
        self.scope_y = boundaries_y
        # ----- body part (the core of the CrimsonDragon) ------
        self.imgLib = {
            "body": createImgList("image/stg2/spiderBody.png"),
            "bite": createImgList("image/stg2/spiderBite.png")
        }
        self.shadLib = getShadLib(self.imgLib)
        self.imgIndx = 0
        self.setImg("body")
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = randint(self.scope_x[0], self.scope_x[1]-self.rect.width)
        self.rect.bottom = y
        self.speed = [-12,12]     # initial: left, down
        # ----------------- legs part ------------------
        self.legLeft = [ load("image/stg2/leg0.png").convert_alpha(), load("image/stg2/leg1.png").convert_alpha(), 
            load("image/stg2/leg0.png").convert_alpha(), flip(load("image/stg2/leg1.png").convert_alpha(), True, False) ]
        self.legRight = [ flip(self.legLeft[0], True, False), flip(self.legLeft[1], True, False), 
            flip(self.legLeft[2], True, False), flip(self.legLeft[3], True, False) ]
        # Spider's legs are a bit complex! Four directions are respectively set up.
        self.legR = { 
            "left":{ "down": [(0.36,0.72), (0.36,0.62), (0.36,0.72), (0.45,0.66)], "up":[(0.3,0.36), (0.4,0.38), (0.3,0.36), (0.36,0.44)] },
            "right": { "down": [(0.62,0.72), (0.62,0.62), (0.62,0.72), (0.62,0.7)], "up":[(0.73,0.36), (0.63,0.36), (0.73,0.36), (0.68,0.38)] }
        }
        theR = self.legR[self.direction]["down"][0]
        self.leg = Ajunction( self.legLeft[2], getPos(self, theR[0], theR[1]) )
        self.legIndx = 0
        # ----------- other attributes -------------------------
        self.coolDown = 0
        self.doom = False
        self.cnt = 0         # count for the loop of shift position
        self.coolDown = 0    # count for attack coolDown
        self.webSnd = pygame.mixer.Sound("audio/spitWeb.wav")
        self.moanSnd = pygame.mixer.Sound("audio/redDragonMoan.wav")
        self.upDown = 1
        self.parti = None
        self.haltCnt = 0

    def move(self, delay, sprites, canvas):
        self.checkHitBack()
        self._tipPosition(canvas)
        
        if self.doom:
            childList = []
            for i in range(8):
                spider = Spider(randint(self.rect.top,self.rect.bottom), self.onlayer, self.scope_x, self.scope_y)
                spider.rect.left = randint(self.rect.left-20, self.rect.right-self.rect.width+20)
                spider.coin = 0
                childList.append(spider)
                canvas.addSpatters(6, (2,4,6), (12,14,16), (255,20,20), getPos(spider,0.5,0.5))
            # dead
            self.moanSnd.play(0)
            self.leg.kill()
            del self.leg
            self.kill()
            return childList
        if self.haltCnt >0:
            self.haltCnt -= 1
        # update image and move 
        if not delay % 2:
            if not delay%6:
                self.rect.top += self.upDown
                self.upDown = -self.upDown
            if not ( delay % 8 ):
                # Randomly spit webs
                if not self.parti and random()<0.05:
                    self.webSnd.play(0)
                    self.haltCnt = 60
                    # filter out those are not hero
                    true_hero = []
                    for each in sprites:
                        if each.category in ("hero","servant"):
                            true_hero.append(each)
                    rect = choice(true_hero).rect.copy()
                    startPos = getPos(self,0.5,0.5)
                    finalPos = [rect.left+rect.width//2, rect.top+rect.height//2]
                    speedX = round( (finalPos[0] - startPos[0]) / 40 )
                    speedY = round( (finalPos[1] - startPos[1]) / 40 )
                    if abs(speedY<=10):  # 距离太远就算了
                        self.parti = [startPos, (speedX, speedY), rect]
                # move
                if self.haltCnt==0:
                    self.rect.left += self.speed[0]
                    if (self.rect.right >= self.scope_x[1] and self.speed[0] > 0) or (self.rect.left <= self.scope_x[0] and self.speed[0] < 0):
                        self.speed[0] = -self.speed[0]
                    if self.speed[0]>0:
                        self.direction = "right"
                    elif self.speed[0]<0:
                        self.direction = "left"
                    
                    self.rect.top += self.speed[1]
                    if (self.rect.bottom >= self.scope_y[1] and self.speed[1] > 0) or (self.rect.top <= self.scope_y[0] and self.speed[1] < 0):
                        self.speed[1] = -self.speed[1]
                    # 随机停一会
                    if random()<0.01:
                        self.haltCnt = 60
                
                    # 根据速度方向计算出需要rotate的degree，rotate the image
                    if self.coolDown>=36:
                        self.setImg("bite")
                    else:
                        self.setImg("body")
                    tmpPos = getPos(self, 0.5, 0.5)
                    degree = math.degrees( math.atan2(self.speed[0], self.speed[1]) )
                    self.image = pygame.transform.rotate( self.image, degree )
                    self.rect = self.image.get_rect()
                    self.rect.left = tmpPos[0]-self.rect.width//2
                    self.rect.top = tmpPos[1]-self.rect.height//2
                    self.shad = pygame.transform.rotate( self.shad, degree )
                    self.mask = pygame.mask.from_surface(self.image)
                    # deal legs:
                    self.legIndx = (self.legIndx+1) % len(self.legLeft)
                    if self.direction == "left":
                        self.leg.updateImg( pygame.transform.rotate( self.legLeft[self.legIndx], degree) )
                    elif self.direction == "right":
                        self.leg.updateImg( pygame.transform.rotate( self.legRight[self.legIndx], degree ) )
            # Set relative position.
            if self.speed[1]>0:
                theR = self.legR[self.direction]["down"][self.legIndx]
            elif self.speed[1]<0:
                theR = self.legR[self.direction]["up"][self.legIndx]
            self.leg.updatePos( getPos(self, theR[0], theR[1]) )
        
        # Deal Bite.
        if self.coolDown == 0:
            for each in sprites:
                if ( collide_mask(self, each) ):
                    self.coolDown = 60
                    self.haltCnt = 30
        if (self.coolDown > 0):
            self.coolDown -= 1
            if (self.coolDown == 42):
                cldList( self, sprites )
        
        # move particle if there is one
        if self.parti:
            pos, speed, rect = self.parti
            self.parti[0] = (pos[0]+speed[0], pos[1]+speed[1])
            canvas.addTrails( [4,5,6], [14,16,18], (250,250,250,210), self.parti[0] )
            if (rect.left<=self.parti[0][0]<=rect.right) and (rect.top<=self.parti[0][1]<=rect.bottom):
                canvas.addSpatters( 5, (2,3,4), (12,14,16), (250,250,250), pos, False)
                del self.parti
                self.parti = None
                return [pos, rect]
    
    def hitted(self, damage, pushed, dmgType):
        # decrease health
        self.health -= (damage*self.realDmgRate)
        if self.health <= 0:                # dead。
            self.doom = True
            self.health = 0
            return True
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )

    def paint(self, screen):
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 4
        screen.blit(self.shad, shadRect)
        screen.blit( self.leg.image, self.leg.rect )
        screen.blit( self.image, self.rect )
        # 画打击阴影
        if self.hitBack:
            screen.blit( self.shad, self.rect )
    
    def lift(self, dist):                   # 所有monster都应可以响应model主函数的调用而竖直方向上移动。
        self.rect.top += dist
        self.scope_y = (self.scope_y[0]+dist, self.scope_y[1]+dist)
    
    def level(self, dist):
        self.rect.left += dist
        self.scope_x = (self.scope_x[0]+dist, self.scope_x[1]+dist)

# ===========================================================================
# -------------------------------- stage3 -----------------------------------
# ===========================================================================
class MistGenerator():
    canvas = None
    canvasRect = None

    def __init__(self, bg_size):
        self.bg_size = bg_size
        self.category = "mist"
        self.mistNum = 4
        # 用两个列表分别存储团状黑雾的中心点坐标、半径和移动速度；光亮物中点坐标和范围。
        self.darks = []
        self.lumis = []      # [ (centerPos, InnerRange), (...) ]
    
    def renew(self, delay, sprites):        
        # 定时检查数量，错开添加以造成错开的效果
        if not delay%240:
            if len(self.darks)<self.mistNum:
                self.generateMist()
        # 更新雾团位置
        for each in self.darks[::-1]:
            rect = each[1]
            if (each[2]<0 and rect.right<=0) or (each[2]>0 and rect.left>=self.bg_size[0]):
                self.darks.remove(each) # 出界可以移除了
            else:
                if delay%2:
                    rect.top += 2
                    rect.left += each[2]
                    each[1] = rect
                else:
                    rect.top -= 2
        # 更新光亮物范围。
        self.lumis.clear()
        for each in sprites:
            if hasattr(each, "lumi") and each.lumi>20:
                ctr = getPos(each, 0.5, 0.5)
                # 营造视野圆圈摇曳效果
                if delay%2:
                    gap = 2
                else:
                    gap = -2
                self.lumis.append( (ctr, each.lumi+gap) )

    def generateMist(self):
        radMax = randint(110,190)
        speed = choice([1,2,3,-1,-2,-3])
        if speed<0: # 从右至左
            core = [self.bg_size[0]+radMax+randint(-10,40), randint(110, self.bg_size[1]-110)]
        else:       # 从左至右
            core = [-radMax+randint(-40,10), randint(110, self.bg_size[1]-110)]
        surf = pygame.Surface( (radMax*2, radMax*2) ).convert_alpha()
        surf.fill((0,0,0,0))
        rect = surf.get_rect()
        rect.left = core[0]-radMax
        rect.top = core[1]-radMax
        alpha = 20  # 最外圈的透明度
        rad = radMax
        for i in range(4):
            pygame.draw.circle( surf, (20,0,10,alpha), (radMax, radMax), rad, 0 )
            rad = max(rad-12, 0)
            alpha = min(alpha+65, 240)  # 最内层透明度上限为240
        self.darks.append( [surf, rect, speed] )
    
    def paint(self, canvas):
        for each in self.darks:
            surf_copy = each[0].copy()   # 复制。对于有lumi覆盖的要加上lumi
            for lumi in self.lumis:
                # 计算光亮点的相对坐标
                lumi_x = lumi[0][0]-each[1].left
                lumi_y = lumi[0][1]-each[1].top
                pygame.draw.circle( surf_copy, (0,0,0,60), (lumi_x,lumi_y), lumi[1], 0 )
                pygame.draw.circle( surf_copy, (0,0,0,0), (lumi_x,lumi_y), lumi[1]-10, 0 )
            canvas.blit(surf_copy, each[1])
        
# -----------------------------------
class Skeleton(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            Skeleton.imgLib = {
                "popList": createImgList("image/stg3/pop0.png","image/stg3/pop1.png","image/stg3/pop2.png", 
                    "image/stg3/pop3.png","image/stg3/pop4.png","image/stg3/pop5.png","image/stg3/pop6.png","image/stg3/pop7.png"),
                "iList": createImgList( "image/stg3/skeletonLeft0.png","image/stg3/skeletonLeft1.png",
                    "image/stg3/skeletonLeft2.png","image/stg3/skeletonLeft1.png" ),
                "att": createImgList("image/stg3/attLeft.png")
            }
            Skeleton.shadLib = getShadLib(Skeleton.imgLib)
        
        # calculate its position
        Monster.__init__(self, "skeleton", (255,255,255,240), 3, 1, onlayer, sideGroup)
        self.wallList = []       # 存储本行的所有砖块; # 每次初始化一个新实例时，清空此类的wallList（否则会在上一个实例的基础上再加！）
        posList = []             # 辅助列表，用于暂时存储本行砖块的位置（左边线）
        for aWall in wallGroup:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            if not aWall.category == "specialWall":  # 排除特殊砖块上生成，造成空的popping操作
                self.wallList.append(aWall)
                posList.append(aWall.rect.left)
        if len(self.wallList) == 0:
            self.kill()
            return None
        wall = choice(self.wallList)
        leftMax = wall.rect.left
        rightMax = wall.rect.right   # note：此处砖块的右坐标即下一砖块的左坐标
        while True:
            if leftMax in posList:
                leftMax -= blockSize
            else:
                leftMax += blockSize # 将多减的加回来
                break
        while True:
            if rightMax in posList:
                rightMax += blockSize
            else:
                break
        self.scope = (leftMax, rightMax)
        # initialize the sprite
        self.imgIndx = 0
        self.setImg("popList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.birth = [wall.rect.left+wall.rect.width//2, wall.rect.top]
        if random()<=0.5:
            self.alterSpeed(-3)
        else:
            self.alterSpeed(3)
        self.lumi = 2
        self.popping = True                    # 出生阶段为True

    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)
        if not (delay % 4): 
            if not self.popping:
                self.rect.left += self.speed   # pop阶段的最后一张图片和移动阶段的第一张图片大小刚好是相等的，完美对接
                if (getPos(self,0.75,0)[0] >= self.scope[1] and self.speed > 0) or (getPos(self,0.25,0)[0] <= self.scope[0] and self.speed < 0):
                    self.alterSpeed(-self.speed)
                if not (delay % 8):
                    # update image
                    tmpPos = getPos(self, 0.5, 1)
                    self.setImg("iList",self.imgIndx)
                    self.mask = pygame.mask.from_surface(self.image)
                    self.rect = self.image.get_rect()
                    self.rect.bottom = tmpPos[1]
                    self.rect.left = tmpPos[0]- self.rect.width//2
                    self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
                if self.coolDown==0:
                    for each in sprites:
                        if ( collide_mask(self, each) ):
                            self.coolDown = 8  # 归在delay整除4的条件下，故实际间隔为8*4 = 32
                else:
                    self.cratch(sprites)
                    self.coolDown -= 1
            elif self.popping:
                self.setImg("popList",self.imgIndx)
                self.rect = self.image.get_rect()
                self.rect.bottom = self.birth[1]
                self.rect.left = self.birth[0]- self.rect.width//2
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["popList"])
                if self.imgIndx == 0:
                    self.popping = False      # 若imgIndx 第一次变为零，则表示完成了一次pop的过程

    def cratch(self, sprites):
        if (self.coolDown >= 4):
            self.setImg("att")
            if ( self.coolDown == 5 ):
                cldList( self, sprites )
    
    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        self.health -= damage
        if self.health <= 0:
            self.kill()
            self.spurtCanvas.addPebbles(self, 4, type="boneDebri")
            return True
    
    def lift(self, dist):
        self.rect.bottom += dist
        self.birth[1] += dist

    def level(self, dist):
        self.rect.left += dist
        self.birth[0] += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# -----------------------------------
class Dead(Monster):
    imgLibMale = None
    imgLibFemale = None
    shadLibMale = None
    shadLibFemale = None
    snd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLibMale:
            Dead.imgLibMale = {
                "iList": createImgList( "image/stg3/deadMale0.png", "image/stg3/deadMale1.png", 
                    "image/stg3/deadMale2.png", "image/stg3/deadMale1.png"),
                "att": createImgList("image/stg3/deadMaleVomit.png")
            }
            Dead.imgLibFemale = {
                "iList": createImgList( "image/stg3/deadFemale0.png", "image/stg3/deadFemale1.png", 
                    "image/stg3/deadFemale2.png", "image/stg3/deadFemale1.png"),
                "att": createImgList("image/stg3/deadFemaleVomit.png")
            }
            Dead.shadLibMale = getShadLib(Dead.imgLibMale)
            Dead.shadLibFemale = getShadLib(Dead.imgLibFemale)
            Dead.snd = pygame.mixer.Sound("audio/vomiSplash.wav")
        
        # calculate its position
        Monster.__init__(self, "dead", (10,10,10,240), 0, 2, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        self.onlayer = int(onlayer)
        # initialize the sprite
        if random()<0.5:
            self.imgLib = self.imgLibMale
            self.shadLib = self.shadLibMale
        else:
            self.imgLib = self.imgLibFemale
            self.shadLib = self.shadLibFemale
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left + (wall.rect.width-self.rect.width) // 2
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.lumi = 3
        if random()<=0.5:
            self.alterSpeed(-2)
        else:
            self.alterSpeed(2)
        self.voming = 0

    def move(self, delay, sprites, canvas):
        self.checkHitBack(obstacle=True)
        if not (delay % 6) and not self.voming: 
            self.rect.left += self.speed
            if (self.rect.right >= self.scope[1] and self.speed > 0) or (self.rect.left <= self.scope[0] and self.speed < 0):
                self.alterSpeed(-self.speed)
            if not (delay % 12):
                self.setImg("iList",self.imgIndx)
                self.mask = pygame.mask.from_surface(self.image)  # 更新rect，使得与hero重合的判断更加精确
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            if random()<0.04:
                for hero in sprites:
                    if -2 < hero.onlayer-self.onlayer+1 < 2:
                        self.snd.play(0)
                        break
                self.voming = 54
            # Check Hero and Turn.
            self.detectHero(sprites)
        if (self.voming > 0):
            self.setImg("att")
            self.voming -= 1
            if (self.voming < 48) and (self.voming%2):  # 警告
                # 每2次刷新均吐出1个气团
                spdX = 7-self.voming//8
                if self.speed <= 0:
                    spd = [ -spdX, 0 ]
                    startX = 0.2
                elif self.speed > 0:
                    spd = [ spdX, 0 ]
                    startX = 0.8
                canvas.addAirAtoms(self, 1, getPos(self, startX, 0.5), spd, 
                                    sprites, "corrosive", btLine=self.rect.bottom)

    def reportHit(self, hero):
        if hasattr(hero,"infected") and hero.infected<0:
            hero.infect()
        hero.hitted( self.damage, 0, self.dmgType )

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# -----------------------------------
class Ghost(Monster):  
    imgLib = None
    shadLib = None

    def __init__(self, XRange, y, onlayer):
        if not self.imgLib:
            Ghost.imgLib = {
                "iList": createImgList("image/stg3/ghost0.png","image/stg3/ghost1.png"),
                "extraList": createImgList("image/stg3/ghost_extra0.png","image/stg3/ghost_extra1.png")
            }
            Ghost.shadLib = getShadLib( Ghost.imgLib )
            Ghost.snd = pygame.mixer.Sound("audio/ghost_resurrect.wav")

        # initialize the sprite
        Monster.__init__(self, "ghost", (255,120,190,120), 6, 0, onlayer)
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = randint( XRange[0], XRange[1] )
        self.rect.top = y

        self.alterSpeed(-1)
        self.coolDown = 0   # count for attack coolDown
        self.tgt = None
        self.nxt = [0, 0]
        self.upDown = 1
        # Parameters about second life
        self.extraLife = 1
        self.cnt = 0        # 被打碎时的复生实时倒计时
        self.returnTime = 50# 倒计时上限

    def move(self, delay, sprites, spurtCanvas):
        self.checkHitBack()
        if self.cnt==0:
            if not (delay % 8 ):
                # 变换图片
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
                self.setImg("iList",self.imgIndx)
                # 飘动
                self.rect.top += self.upDown
                self.upDown = -self.upDown
                # 更新目标位置
                if not self.tgt:
                    self.tgt = choice(sprites)
                    self.nxt = getPos(self.tgt, 0.5, 0.5)
                else:
                    self.nxt = getPos(self.tgt, 0.5, 0.5)
                    self.direction = "left" if ( self.nxt[0] < self.rect.left + self.rect.width/2 ) else "right"
                    if self.tgt.health<=0:
                        self.tgt = None
            # charging motion
            if not (delay % 4):
                self.shift( self.nxt[0], self.nxt[1] )
            if (self.coolDown == 0):
                for each in sprites:
                    if collide_mask(self, each):
                        self.coolDown = 42
            elif self.coolDown > 0:
                self.coolDown -= 1
                if self.coolDown >= 32:
                    #self.setImg("att")
                    if self.direction=="left":
                        self.push = self.pushList[0]
                    else:
                        self.push = self.pushList[1]
                    if self.coolDown == 34:
                        cldList( self, sprites )
        else:
            if self.cnt==self.returnTime:
                spurtCanvas.addSpatters(7, [3,6,9], [20,24,28], self.bldColor, getPos(self,0.5,0.48), falling=False, back=True)
                spurtCanvas.addSpatters(7, [3,6,9], [20,24,28], (255,180,240), getPos(self,0.5,0.52), falling=False, back=True)
            self.cnt -= 1
            if self.cnt==0:
                return "rejoin"
            else:
                return "out"

    def shift(self, final_x, final_y):
        spd = 6
        dist = 0
        x = self.rect.left + self.rect.width/2
        y = self.rect.top + self.rect.height/2
        if (x == final_x) and (y == final_y):
            return True
        if (x < final_x):
            dist = min( math.ceil( (final_x - x)/spd ), 5 )
            self.rect.left += dist
        elif (x > final_x):
            dist = min( math.ceil( (x - final_x)/spd ), 5 )
            self.rect.left -= dist
        if (y < final_y):
            dist = min( math.ceil( (final_y - y)/spd ), 4 )
            self.rect.top += dist
        elif (y > final_y):
            dist = min( math.ceil( (y - final_y)/spd ), 4 )
            self.rect.top -= dist
    
    def hitted(self, damage, pushed, dmgType):
        # decrease health
        self.health -= damage
        if self.health <= 0:        # dead。但是有可能复活
            if self.extraLife>0:
                self.snd.play(0)
                self.health = self.full
                self.extraLife -= 1
                self.cnt = self.returnTime       # 复活倒计时置为returnTime
                self.imgLib = {
                    "iList": Ghost.imgLib["extraList"]
                }
                self.setImg("iList",0)
            else:
                self.health = 0
                self.kill()
                #self.snd.stop()
                return True
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
    
    def paint(self, surface):
        if self.cnt==0:
            # ghost没有阴影！
            surface.blit( self.image, self.rect )
            # 画打击阴影
            if self.hitBack:
                surface.blit( self.shad, self.rect )
    
    def level(self, dist):
        self.rect.left += dist
        self.nxt[0] += dist
    
    def lift(self, dist):
        self.rect.top += dist
        self.nxt[1] += dist
    
# ------------------------------------
class Vampire(Boss):
    sycthe = None
    
    def __init__(self, groupList, onlayer, boundaries, font):
        # initialize the sprite
        Boss.__init__(self, font, "Vampire", (10,30,10,240), 8, 1, onlayer, sideGroup=groupList["0"])
        self.onlayer = int(onlayer)
        self.boundaries = boundaries
        self.initLayer(groupList)
        # initialize the sprite
        self.imgLib = {
            "iList": createImgList( "image/stg3/Vampire0.png", "image/stg3/Vampire1.png" ),
            "attList": createImgList( "image/stg3/VampireAtt0.png", "image/stg3/VampireAtt1.png", "image/stg3/VampireAtt2.png" ),
            "summon": createImgList( "image/stg3/VampireSummon.png" )
        }
        self.shadLib = getShadLib(self.imgLib)
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = self.initPos[0]-self.rect.width//2  # 位于砖块居中
        self.rect.bottom = self.initPos[1]
        # Define scythe. ----------------------------------------
        self.scytheR = { "left":(0.15,0.7, 0), "right":(0.85,0.7, 0) }
        self.scytheAttR = { "left":[ (0.6,0.5, 0), (0.25, 0.69, 1), (0.4,0.87, 1) ], "right":[ (0.4,0.5, 0), (0.75, 0.69, 1), (0.6,0.87, 1) ] }
        self.scytheImg = createImgList( "image/stg3/scythe.png" )
        self.scytheAttImg = createImgList( "image/stg3/scytheAtt0.png", "image/stg3/scytheAtt1.png", "image/stg3/scytheAtt2.png" )
        self.scythe = Ajunction( self.scytheImg["left"][0], getPos(self, self.scytheR["left"][0], self.scytheR["left"][1]) )
        # ----------- other attributes -------------------------
        self.coolDown = 0
        self.maxHealth = self.health
        self.snd = pygame.mixer.Sound("audio/vampireAtt.wav")
        self.laughSnd = pygame.mixer.Sound("audio/vampire_laugh.wav")
        self.alterSpeed( choice([-1,0,1]) )
        self.status = "wandering"          # wandering表示闲逛的状态，alarming表示发现英雄的状态
        self.wpPos = (0, 0, 0)
        self.tgt = None                    # 指示要攻击的英雄
        self.flying = False
        self.lumi = 4
        self.summonCD = 360               # 召唤冷却
        self.upDown = 1
        self.rectList = []
            
    # 这个move()函数是供外界调动的接口，这里仅起根据传入的英雄参数判断状态的作用。判断完成后，修改自身的状态，然后执行相应的函数。
    def move(self, delay, sprites, groupList, canvas):
        self.checkHitBack(obstacle=True)
        self._tipPosition(canvas)
        
        # Effect
        if not delay%2:
            # 身体紫光
            canvas.addSmoke( 1, (2,4,5), 4, (120,10,110,180), getPos(self,0.5,1), 20, speed=[-self.speed,-1] )
            # 眼睛紫光
            for i in (0.4,0.6):
                canvas.addSmoke( 1, (1,2), 6, (190,40,170,180), getPos(self,i,0.38), 5, speed=[0,0] )
        # change layer
        if not (delay%20) and not self.flying and self.status=="wandering" and random()<0.1:
            self.flying = True
            hero = choice( sprites )
            # 向hero所在的层数进逼。由于hero能在的层数一定是合法的，故这里不需要检测层数的合法性（不需边界测试）
            if self.onlayer > 1 and self.onlayer > hero.onlayer-1:   # 注意，这里由于层数体系不一样，要检查self.layer为1时不能减为-1（那就成了sideWall！）
                self.onlayer -= 2
            elif self.onlayer < hero.onlayer-1:
                self.onlayer += 2
            self.initLayer(groupList)           # 计算其在新一行的水平scope        
        # 优先处理 flying $$$$
        if self.flying:
            self.rect.bottom += ( (self.initPos[1]-getPos(self, 0.5, 1)[1]) // 20 )
            self.rect.left += ( (self.initPos[0]-getPos(self, 0.5, 1)[0]) // 20 )
            #以竖直方向为标准，若已抵达(等于或略高于)目标行，则将flying标记为False
            if 0<= (self.initPos[1]-self.rect.bottom) < 20:
                self.rect.bottom = self.initPos[1]
                self.flying = False
        else:
            if not (delay % 20):
                self.rect.top += self.upDown
                self.upDown = - self.upDown
            for hero in sprites:
                # 如果有英雄在同一层，则将速度改为朝英雄方向。(这里的两套体系，英雄的层数为偶数，而怪物用的层数都是奇数)
                if ( (hero.onlayer-1)==self.onlayer and abs( getPos(hero,0.5,0.5)[0]-getPos(self,0.5,0.5)[0] )<=360 ) or self.coolDown>0:
                    self.status = "alarming"
                    self.tgt = hero
                    break     # 这里碰到第一个英雄符合条件就退出了。因此，如果两个英雄同时在一层中，P1总是会被针对，而P2永远不会被选中为目标。问题留着以后修正。
                else:
                    self.status = "wandering"
            if self.status == "wandering":
                # 游荡状态，删除残影
                if self.rectList:
                    self.rectList.pop(0)
                # wander 部分
                if (self.speed):                        # speed!=0，在运动。
                    self.rect.left += self.speed
                    if (getPos(self, 0.7, 1)[0] >= self.scope[1] and self.speed > 0) or (getPos(self, 0.3, 1)[0] <= self.scope[0] and self.speed < 0):
                        self.alterSpeed(-self.speed)
                    if not delay % 20 and random()<0.08:# 随机进入休息状态。
                        self.alterSpeed(0)
                elif not delay % 20 and random()<0.08:  # 否则，在休息。此时若随机数满足条件，进入巡逻状态
                    self.alterSpeed( choice( [1,-1] ) )
                # wander时还会召唤小型生物。
                self.summonCD -= 1
                if self.summonCD <= 36:
                    if self.summonCD == 36:
                        self.laughSnd.play(0)
                    trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
                    self.setImg("summon")
                    self.rect = self.image.get_rect()
                    self.rect.left = trPos[0]-self.rect.width//2
                    self.rect.bottom = trPos[1]
                    if self.summonCD == 0:
                        self.summonCD = 480
                        babe = choice( ["skeleton", "dead", "ghost"] )
                        pos = getPos(self, choice( [0.1,0.9] ), 0)
                        return (babe,pos)
                    return
            elif self.status == "alarming":
                if not self.coolDown:
                    if getPos( self.tgt, 0.5, 0.5 )[0]>getPos( self, 0.5, 0.5 )[0]:
                        self.alterSpeed(1)
                    else:
                        self.alterSpeed(-1)
                #attack部分
                self.rectList.append(self.rect.copy())
                if len(self.rectList)>6:
                    self.rectList.pop(0)
                self.rect.left += self.speed*8
                if self.coolDown==0:
                    for each in sprites:
                        if abs(getPos(self, 0.5, 0.5)[0]-getPos(each, 0.5, 0.5)[0])<60:
                            self.snd.play(0)    # 攻击英雄，咆哮
                            self.speed = 0
                            self.coolDown = 44
                else:
                    self.coolDown -= 1
        # checkImg部分
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
        if self.coolDown <= 0:
            self.wpPos = self.scytheR[self.direction]
            if not (delay % 14 ):
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
            self.scythe.updateImg( self.scytheImg[self.direction][0] )
            self.scythe.updatePos( getPos(self, self.wpPos[0], self.wpPos[1]) )
        else:
            if self.coolDown >= 16:
                attIndx = 0
            elif self.coolDown >= 8:
                attIndx = 1
                for each in sprites:
                    if collide_mask(self.scythe, each):
                        each.hitted( self.damage, self.push, self.dmgType )
                        self.health += self.damage*0.5
                        if self.health > self.maxHealth:
                            self.health = self.maxHealth
            else:
                attIndx = 2
            self.wpPos = self.scytheAttR[self.direction][attIndx]
            self.setImg("attList",attIndx)
            self.scythe.updateImg( self.scytheAttImg[self.direction][attIndx] )
            self.scythe.updatePos( getPos(self, self.wpPos[0], self.wpPos[1]) )
                
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]

    # 此函数用于确定新一行中的位置及scope
    def initLayer(self, groupList):
        self.wallList = []          # 存储本行的所有砖块; # 每次初始化一个新实例时，清空此类的wallList（否则会在上一个实例的基础上再加！）
        posList = []                # 辅助列表，用于暂时存储本行砖块的位置（左边线）
        for aWall in groupList[str(self.onlayer)]:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            self.wallList.append(aWall)
            posList.append(aWall.rect.left)
        if len(self.wallList)==0:
            # dead
            #self.moanSnd.play(0)
            self.kill()
            return
        if self.activated:          # 找新层过程的调用，找最近的砖块。
            dist = float("inf")
            for each in self.wallList:
                newDist = abs( getPos(self,0.5,0.5)[0]-getPos(each,0.5,0.5)[0] )
                if newDist < dist:
                    dist = newDist
                    wall = each
        else:                       # 初始化过程的调用
            wall = choice(self.wallList)
        self.initPos = getPos(wall, 0.5, -0.1)   # 新点，居中，漂浮
        leftMax = wall.rect.left
        rightMax = wall.rect.right  # note：此处砖块的右坐标即下一砖块的左坐标
        while True:
            if leftMax in posList: # warmachine比较宽，可以占两格行进
                leftMax -= wall.rect.width
            else:
                leftMax += wall.rect.width  # 将多减的加回来
                break
        while True:
            if rightMax in posList:
                rightMax += wall.rect.width
            else:
                break
        self.scope = (leftMax, rightMax)
        return wall

    def lift(self, dist):
        self.rect.bottom += dist
        self.initPos[1] += dist

    def level(self, dist):
        self.rect.left += dist
        self.initPos[0] += dist
        self.boundaries = (self.boundaries[0]+dist, self.boundaries[1]+dist)

    # 鉴于本对象的构造非常复杂，因此提供一个专门的绘制接口。给此函数传递一个surface参数，即可在该surface上绘制（blit）完整的本对象
    def paint(self, screen):
        # 画残影
        for rect in self.rectList:
            screen.blit(self.shad, rect)
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 8
        screen.blit(self.shad, shadRect)
        #按层级顺序画weapon和self
        if self.wpPos[2]==0:
            screen.blit( self.scythe.image, self.scythe.rect )
            screen.blit( self.image, self.rect )
        elif self.wpPos[2]==1:
            screen.blit( self.image, self.rect )
            screen.blit( self.scythe.image, self.scythe.rect )
        # 画打击阴影
        if self.hitBack:
            screen.blit( self.shad, self.rect )

# ===========================================================================
# --------------------------------- stage4 ----------------------------------
# ===========================================================================
class Snake(Monster): 
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, sideGroup, onlayer):
        if not self.imgLib:
            Snake.imgLib = {
                "iList": createImgList("image/stg4/snake0.png","image/stg4/snake1.png"),
                "dash": createImgList("image/stg4/snakeDash0.png", "image/stg4/snakeDash1.png")
            }
            Snake.shadLib = getShadLib(Snake.imgLib)
        
        # calculate its position
        Monster.__init__(self, "snake", (250,160,120), 4, 1, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.alterSpeed( choice([-1,1]) )
        self.tgt = None

    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)

        self.tgt = self.detectHero(sprites)
        # move
        if not self.tgt:
            self.rect.left += self.speed
            if (getPos(self,0.75,0)[0]>=self.scope[1] and self.speed>0) or (getPos(self,0.25,0)[0]<=self.scope[0] and self.speed<0):
                self.alterSpeed( -self.speed )
            if not (delay % 10 ):
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
                self.setImg("iList",self.imgIndx)
                self.fitImg()
        else:
            self.rect.left += self.speed*3
            if self.tgt.health<=0:
                self.tgt = None
                return
            if not (delay % 6 ):
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
                self.setImg("dash",self.imgIndx)
                self.fitImg()
            # Attack
            if ( self.coolDown==0 ):
                for each in sprites:
                    if collide_mask(self, each):
                        self.coolDown = 36
            if (self.coolDown > 0):
                self.coolDown -= 1
                if ( self.coolDown == 20 ):
                    cldList( self, sprites )
        
    def fitImg(self):
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]   # 为保证图片位置正确，临时存储之前的位置信息
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# -----------------------------------
class Slime(Monster):  
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            Slime.imgLib = {
                "iList": createImgList("image/stg4/slime0.png","image/stg4/slime1.png","image/stg4/slime2.png",
                    "image/stg4/slime3.png","image/stg4/slime4.png","image/stg4/slime5.png", "image/stg4/slime6.png")
            }
            Slime.shadLib = getShadLib(Slime.imgLib)

        # calculate its position
        Monster.__init__(self, "slime", (0,255,0,240), 4, 1, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.coolDown = 0          
        self.alterSpeed( choice( [-1, 1] ) )
        self.rise = (0,-7,-13,-18,-13,-7,0)
        self.newSlime = None
        self.splitCnt = 3   # 指示本slime仍可分裂的次数。分裂出的slime也获得-1次的cnt。

    def move(self, delay, sprites):
        self.checkHitBack(obstacle=True)
        self.rect.left += self.speed
        if (getPos(self,0.75,0)[0] >= self.scope[1] and self.speed > 0) or (getPos(self,0.25,0)[0] <= self.scope[0] and self.speed < 0):
            self.alterSpeed(-self.speed)
        if not (delay % 5 ):
            trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom-self.rise[self.imgIndx] ]  # 为保证图片位置正确，临时存储之前的位置信息
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
            self.mask = pygame.mask.from_surface(self.image)
            self.rect = self.image.get_rect()
            self.rect.left = trPos[0]-self.rect.width//2
            self.rect.bottom = trPos[1] + self.rise[self.imgIndx]
            # slime应该也能做出反应，但比较迟钝
            if not (delay%60):
                self.detectHero(sprites)
        if ( self.coolDown==0 ):
            for each in sprites:
                if collide_mask(self, each):
                    self.coolDown = 30
        if (self.coolDown > 0):
            self.coolDown -= 1
            if ( self.coolDown == 20 ):
                cldList( self, sprites )
        # If there is a newly generated slime, return it.
        if (self.newSlime):
            newS = self.newSlime
            self.newSlime = None
            return newS
        
    def hitted(self, damage, pushed, dmgType):
        if dmgType == "corrosive":
            damage //= 2
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        self.health -= damage
        if self.health <= 0:   # dead
            self.health = 0
            self.kill()
            return True
        else:                  # hitted but alive, check whether to split another slime.
            if ( ( pushed>0 and self.speed<0 ) or ( pushed<0 and self.speed>0 ) ) and self.splitCnt>0:
                self.splitCnt -= 1
                slime = Slime( self.wallList, self.obstacle, 1, self.onlayer )  # 前两项参数都是不需要的，但为了完整执行init函数，第一项参数传入，第二项设为1.
                # 奖励置为0
                slime.coin = 0
                slime.splitCnt = self.splitCnt
                # Set the properties of the generated slime.
                slime.scope = self.scope  
                slime.imgIndx = self.imgIndx  # 图像相同
                slime.alterSpeed(-self.speed) # 速度相反
                slime.setImg("iList",slime.imgIndx)
                slime.rect = slime.image.get_rect()
                slime.rect.left = getPos(self, 0.5, 0.5)[0] - slime.rect.width//2
                slime.rect.bottom = self.rect.bottom  # 位置相同
                self.newSlime = slime         # 挂到本对象的newSlime变量上，等待下一次刷新调用move的时候上报给model。

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# -----------------------------------
class Nest(Monster):
    imgLib = None
    shadLib = None

    def __init__(self, wallGroup, onlayer):
        if not self.imgLib:
            Nest.imgLib = {
                "eggList": createImgList("image/stg4/nest0.png","image/stg4/nest1.png")
            }
            Nest.shadLib = getShadLib(Nest.imgLib)

        # calculate its position
        Monster.__init__(self, "nest", (255,255,80,240), 0, 0, onlayer)
        self.wallList = []       # 存储本行的所有砖块; # 每次初始化一个新实例时，清空此类的wallList（否则会在上一个实例的基础上再加！）
        posList = []             # 辅助列表，用于暂时存储本行砖块的位置（左边线）
        for aWall in wallGroup:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            self.wallList.append(aWall)
            posList.append(aWall.rect.left)
        wall = choice(self.wallList)
        # initialize the sprite
        self.imgIndx = 0
        self.setImg("eggList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.top = wall.rect.bottom-8  # link more tight with the block (block bottom is not even)

    def move(self, delay, mons):
        if self.health > 0:
            if not (delay % 24 ):
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["eggList"]["left"])
                self.setImg("eggList",self.imgIndx)
                if random() < 0.1:
                    worm = Worm( self.rect.left+self.rect.width//2, self.rect.bottom, self.onlayer )
                    return [worm]
        else:
            pos1 = getPos(self, 0.3, 0.3)
            worm1 = Worm( pos1[0], pos1[1], self.onlayer )
            pos2 = getPos(self, 0.5, 0.6)
            worm2 = Worm( pos2[0], pos2[1], self.onlayer )
            pos3 = getPos(self, 0.7, 0.3)
            worm3 = Worm( pos3[0], pos3[1], self.onlayer )
            self.kill()
            return [ worm1, worm2, worm3 ]

    def hitted(self, damage, pushed, dmgType):
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            return True
    
    def level(self, dist):
        self.rect.left += dist

class Worm(Monster):  
    imgLib = None
    shadLib = None

    def __init__(self, x, y, onlayer):  
        if not self.imgLib:
            Worm.imgLib = {
                "iList": createImgList("image/stg4/worm0.png","image/stg4/worm1.png", 
                    "image/stg4/worm2.png","image/stg4/worm3.png","image/stg4/worm4.png")
            }
            Worm.shadLib = getShadLib(Worm.imgLib)
        
        Monster.__init__(self, "worm", (255,255,10,240), 1, 0, onlayer-2)# 由于掉落下来一定要减一层，所以传入onlayer-2。
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface( self.image )
        self.rect = self.image.get_rect()
        self.rect.left = x-self.rect.width//2
        self.rect.top = y
        if random()<= 0.5:   # 随即决定向左或向右
            self.alterSpeed(-1)
        else:
            self.alterSpeed(1)
        #self.aground = False
        self.doom = 0
        self.lifeSpan = 300

    def move(self, delay, lineWall, keyLine, sideWall, sprites, canvas, GRAVITY):
        self.checkHitBack(obstacle=True)
        # 无论health和lifespan是否有，都要检查下落
        self.fall(lineWall, keyLine, GRAVITY)
        # 若健康的话，检查与英雄的碰撞
        if (self.health>0) and (self.lifeSpan > 0):
            self.lifeSpan -= 1
            # 进行水平运动
            if not (delay % 5):
                self.rect.left += self.speed
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
                self.setImg("iList",self.imgIndx)
                if ( pygame.sprite.spritecollide(self, sideWall, False, collide_mask) ):
                    self.alterSpeed(-self.speed)
            for each in sprites:
                if ( collide_mask(self, each) ):
                    self.health = 0
        else:
            self.doom += 1
            if self.doom == 8:
                self.kill()
            elif self.doom == 7:
                cldList( self, sprites )    # 检查溅射到英雄，造成伤害
            elif self.doom >= 1:
                if self.doom == 1:
                    canvas.addExplosion( getPos(self, 0.5, 0.5), 
                        14, 8, waveColor=self.bldColor, spatColor=self.bldColor, dotD=(8,10,12), smoke=False 
                    )
                self.image = load("image/stg4/worm_boom.png")

    def fall(self, lineWall, keyLine, GRAVITY):
        self.rect.bottom += (GRAVITY-1)
        while ( pygame.sprite.spritecollide(self, lineWall, False, collide_mask) ):      # 如果和参数中的物体重合，则尝试纵坐标-1
            self.rect.bottom -= 1
            #if not ( pygame.sprite.spritecollide(self, lineWall, False, collide_mask) ): # 循环-1，直到不再和任何物体重合为止，进入这个if语句跳出循环
            #    self.aground = True
        if self.rect.top >= keyLine:
            self.onlayer = max(self.onlayer-2, -1)
        
    def hitted(self, damage, pushed, dmgType):
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            return True    # dead

    def drawHealth(self, surface):
        pass

    def level(self, dist):
        self.rect.left += dist

# -----------------------------------
class Fly(Monster):  
    imgLib = None
    shadLib = None

    def __init__(self, XRange, y, onlayer):
        if not self.imgLib:
            Fly.imgLib = {
                "iList": createImgList("image/stg4/flyLeft0.png","image/stg4/flyLeft1.png", 
                    "image/stg4/flyLeft0.png","image/stg4/flyLeft2.png"),
                "att": createImgList("image/stg4/flyAtt.png")
            }
            Fly.shadLib = getShadLib(Fly.imgLib)
            Fly.snd = pygame.mixer.Sound("audio/flapper.wav")

        # initialize the sprite
        Monster.__init__(self, "fly", (0,255,10,240), 6, 1, onlayer)
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.leftBd = XRange[0]
        self.rightBd = XRange[1]
        self.rect.left = randint( XRange[0], XRange[1] )
        self.rect.top = y

        self.alterSpeed(-1)
        self.cnt = 0       # count for the loop of shift position
        self.coolDown = 0    # count for attack coolDown
        self.nxt = [0, 0]

    def move(self, delay, sprites):
        self.checkHitBack()
        if not (delay % 4 ):
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
        # find new position
        if self.cnt == 0:
            self.cnt = 60
            self.nxt = [ randint(self.leftBd, self.rightBd), randint(20, 580) ]  # randomize a new position
            self.direction = "left" if ( self.nxt[0] < self.rect.left + self.rect.width/2 ) else "right"
        # charging motion
        if not (delay % 3):
            self.shift( self.nxt[0], self.nxt[1] )
            self.cnt -= 1
            if random()<0.02:
                self.snd.play(0)
        if (self.coolDown == 0):
            for each in sprites:
                if collide_mask(self, each):
                    self.coolDown = 42
        elif self.coolDown > 0:
            self.coolDown -= 1
            if self.coolDown >= 32:
                self.setImg("att")
                if self.direction=="left":
                    self.push = self.pushList[0]
                else:
                    self.push = self.pushList[1]
                if self.coolDown == 34:
                    cldList( self, sprites )

    def shift(self, final_x, final_y):
        maxSpan = 8
        spd = 4
        dist = 0
        x = self.rect.left + self.rect.width/2
        y = self.rect.top + self.rect.height/2
        if (x == final_x) or (y == final_y):
            return True
        if (x < final_x):
            dist = min( math.ceil( (final_x - x)/spd ), 5 )
            self.rect.left += dist
        elif (x > final_x):
            dist = min( math.ceil( (x - final_x)/spd ), 5 )
            self.rect.left -= dist
        if (y < final_y):
            dist = min( math.ceil( (final_y - y)/spd ), 4 )
            self.rect.top += dist
        elif (y > final_y):
            dist = min( math.ceil( (y - final_y)/spd ), 4 )
            self.rect.top -= dist
    
    def erase(self):
        self.snd.stop()
        self.kill()
        del self

    def level(self, dist):
        self.rect.left += dist
        self.nxt[0] += dist
        self.leftBd += dist
        self.rightBd += dist
    
    def lift(self, dist):
        self.rect.top += dist
        self.nxt[1] += dist

# -----------------------------------
class MutatedFungus(Boss):
    def __init__(self, xRange, y, onlayer, font):
        # initialize the sprite
        Boss.__init__(self, font, "MutatedFungus", (255,190,140,240), 1, 1, onlayer)
        self.xRange = xRange
        # ----- body part (the core of the Python) ------
        self.imgLib = {
            "body": createImgList("image/stg4/fungus.png")
        }
        self.shadLib = getShadLib(self.imgLib)
        self.imgIndx = 0
        self.setImg("body")
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = randint(xRange[0], xRange[1])
        self.rect.bottom = y
        # ------------- tentacle part ----------------
        self.tentLeft = [ pygame.image.load("image/stg4/tentacle0.png").convert_alpha(), pygame.image.load("image/stg4/tentacle1.png").convert_alpha() ]
        self.tentRight = [ pygame.transform.flip(self.tentLeft[0], True, False), pygame.transform.flip(self.tentLeft[1], True, False) ]
        self.tentR = { "left":[ (0.5,1.1), (0.5,1.1) ], "right":[ (0.5,1.1), (0.5,1.1) ] }
        self.tent = Ajunction( self.tentLeft[0], getPos(self, self.tentR[self.direction][0][0], self.tentR[self.direction][0][1]) )
        self.tentIndx = 0
        # ----------- other attributes -------------------------
        #self.fireSnd = pygame.mixer.Sound("audio/MachineGrenade.wav")
        #self.moanSnd = pygame.mixer.Sound("audio/MachineCollapse.wav")
        self.alterSpeed(0)
        self.cnt = 1080      # count for the loop of shift position
        self.coolDown = 0    # count for attack coolDown
        self.nxt = (0, 0)
        self.upDown = 1
        self.releaseInter = 60  # 释放孢子的间隔，可能随着体力降低而加快

    def move(self, delay, heroes):
        self.checkHitBack()
        self._tipPosition(self.spurtCanvas)
        if not self.cnt%4:
            self.spurtCanvas.addSmoke(2, (3,5,7), 5, (200,255,180,250), getPos(self,0.5,random()), 60)
            self.shift( self.nxt[0], self.nxt[1] )
            # 上下摆动
            self.rect.top += self.upDown
            self.upDown = - self.upDown
        # count down for rage actions.
        self.cnt -= 1
        if self.cnt<=0:
            self.cnt = 1480
        else:
            if not self.cnt%60:
                self.nxt = ( randint( self.xRange[0], self.xRange[1] ), randint(40,520) )   # randomize a new position
                self.direction = "left" if ( self.nxt[0] < getPos(self, 0.5, 0.5)[0] ) else "right"
        if not ( delay % 8 ):
            # 更新各组件的图像
            self.setImg("body", self.imgIndx)
            self.mask = pygame.mask.from_surface(self.image)
            self.tentIndx = (self.tentIndx+1) % len(self.tentLeft)
            if self.direction == "left":
                self.tent.updateImg( self.tentLeft[self.tentIndx] )
            elif self.direction == "right":
                self.tent.updateImg( self.tentRight[self.tentIndx] )
        # 不管是什么时候，都应该及时更新ajunction的位置（还会有英雄击退）
        self.tent.updatePos( getPos(self, self.tentR[self.direction][self.tentIndx][0], self.tentR[self.direction][self.tentIndx][1]) )
        # Deal damage with its tentacle.
        if not delay % DMG_FREQ:
            for each in heroes:
                if collide_mask( self.tent, each ):
                    each.hitted( self.damage, self.push, self.dmgType )
        # release miniFungus.
        if not delay%self.releaseInter:
            # Determine tgt and distance
            aim = getPos( choice(heroes), 0.5,0.4 )
            myPos = getPos(self,0.5,0.4)
            delta = [ aim[0]-myPos[0], aim[1]-myPos[1] ]
            spd = [0,0]
            for i in range(2):
                if delta[i]>80:
                    spd[i] = 1
                elif delta[i]<-80:
                    spd[i] = -1
                else:
                    spd[i] = 0
            miniFungus = MiniFungus( [self.rect.left+60,self.rect.right-60], myPos[1], spd )
            return miniFungus

    def paint(self, screen):
        # draw shadow
        shadRect = self.rect.copy()
        shadRect.left -= 12
        screen.blit(self.shad, shadRect)
        # draw self
        screen.blit( self.tent.image, self.tent.rect )
        screen.blit( self.image, self.rect )
        # Hit highlight
        if self.hitBack:
            screen.blit( self.shad, self.rect )
    
    def shift(self, final_x, final_y):
        x = self.rect.left + self.rect.width/2
        y = self.rect.top + self.rect.height/2
        if (x == final_x) or (y == final_y):
            return True   # 表示已到目标
        maxSpan = 4
        spd = 5
        dist = 0
        if (x < final_x):
            dist = math.ceil( (final_x - x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left += dist
        elif (x > final_x):
            dist = math.ceil( (x - final_x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left -= dist
        if (y < final_y):
            dist = math.ceil( (final_y - y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top += dist
        elif (y > final_y):
            dist = math.ceil( (y - final_y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top -= dist
        return False    # 表示未到目标

class MiniFungus(InanimSprite):

    def __init__(self, XRange, y, spd):
        InanimSprite.__init__(self, "miniFungus")
        self.bldColor = (255,190,140,240)
        self.health = MB["miniFungus"].health
        self.coin = 0
        self.push = 0
        self.weight = 0
        self.damage = MB["miniFungus"].damage
        self.dmgType = MB["miniFungus"].dmgType

        self.image = load("image/stg4/miniFungus.png").convert_alpha()
        if random()<0.5:
            self.image = flip(self.image, True, False)
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = randint( XRange[0], XRange[1] )
        self.rect.top = y
        self.speed = list(spd)

    def move(self, delay, sprites, spurtCanvas):
        # 漂浮移动
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        if self.health<=0:
            spurtCanvas.addExplosion( getPos(self,0.5,0.5), 20, 10, waveColor=self.bldColor, spatColor=self.bldColor )
            self.kill()
        if not delay%8:
            spurtCanvas.addTrails([2,3,4], [20,22,24], self.bldColor, getPos(self,random(),0.6))
        # 检查出界
        if self.rect.right<0 or self.rect.left>spurtCanvas.rect.width or self.rect.bottom<0 or self.rect.top>spurtCanvas.rect.height:
            self.health = 0
            self.kill()
        # 千里送人头
        if cldList(self, sprites):
            self.hitted( self.health, 0, "physical")

    def hitted(self, damage, pushed, dmgType):
        # decrease health
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            return True

    def drawHealth(self, surface):
        pass

# ==========================================================================
# ---------------------------------- stage5 --------------------------------
# ==========================================================================
class blizzardGenerator():
    # 借助model的spurtcanvas绘制。自身并不维护一个画布。
    def __init__(self, bg_size, TMin, TMax):
        self.cntDown = 1600
        self.bg_size = bg_size
        self.phase = 0
        self.freqRange = range(TMin, TMax, 50)
    
    def storm(self, sprites, wind, spurtCanvas, phase):
        self.phase = phase
        # 不同区域设置不同的频率。
        if phase == 0:
            self.freqRange = range(1500, 2000, 50)
        if phase == 1:
            self.freqRange = range(1400, 1800, 50)
        elif phase == 2:
            self.freqRange = range(1200, 1600, 50)
        self.cntDown -= 1
        if self.cntDown <= 60:
            spurtCanvas.addFlakes( 3, wind )
            if self.cntDown <= 0:
                for each in sprites:
                    each.freeze(2)
                self.cntDown = choice( self.freqRange )
    
    def paint(self, dist):
        pass

# ----------------------------
class Wolf(Monster):  
    imgLib = None
    shadLib = None
    snd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            Wolf.imgLib = {
                "iList": createImgList("image/stg5/wolf0.png","image/stg5/wolf1.png","image/stg5/wolf2.png",
                    "image/stg5/wolf3.png","image/stg5/wolf4.png","image/stg5/wolf5.png")
            }
            Wolf.shadLib = getShadLib(Wolf.imgLib)
            Wolf.snd = pygame.mixer.Sound("audio/wolf.wav")
        
        # calculate its position
        Monster.__init__(self, "wolf", (255,0,0,240), 8, 1, onlayer, sideGroup)
        self.wallList = []       # 存储本行的所有砖块; # 每次初始化一个新实例时，清空此类的wallList（否则会在上一个实例的基础上再加！）
        posList = []             # 辅助列表，用于暂时存储本行砖块的位置（左边线）
        for aWall in wallGroup:  # 由于spriteGroup不好进行索引/随机选择操作，因此将其中的sprite逐个存入列表中存储
            self.wallList.append(aWall)
            posList.append(aWall.rect.left)
        wall = choice(self.wallList)
        leftMax = wall.rect.left
        rightMax = wall.rect.right       # note：此处砖块的右坐标即下一砖块的左坐标
        tList1 = [ [leftMax,rightMax] ]
        tList2 = [ [leftMax,rightMax] ]
        i1 = 0       # 辅助变量，用于在循环过程中指示当前正在处理列表中的哪一项scope。每当新加一个scope项时，i应+1
        while True:
            if (leftMax-blockSize) in posList:
                leftMax -= blockSize
                tList1[i1][0] = leftMax
            elif (leftMax-2*blockSize) in posList:
                leftMax -= 2*blockSize
                tList1.append( [leftMax,leftMax+blockSize] )
                i1 += 1
            else:
                break
        i2 = 0
        while True:
            if rightMax in posList:
                rightMax += blockSize
                tList2[i2][1] = rightMax
            elif (rightMax+blockSize) in posList:
                rightMax += 2*blockSize
                tList2.append( [rightMax-blockSize,rightMax] )
                i2 += 1
            else:
                break
        tList = tList1+tList2
        self.scopeList = []
        for item in tList:
            if item not in self.scopeList:
                self.scopeList.append(item)
        #另一种去除重复元素的方法是：先转换为集合set（），再转换回列表list（set（））。但由于列表元素（每个item都是list）是不可哈希的，因此不能转换为集合，这里不适合此方法。
        self.scope = (leftMax, rightMax)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left+wall.rect.width//2-self.rect.width//2
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.alterSpeed( choice( [-2, 0, 2] ) )
        self.jumping = False
        self.status = "wandering"          # wandering表示闲逛的状态，alarming表示发现英雄的状态
        self.tgt = None                    # 指示要攻击的英雄

    # 这个move()函数是供外界调动的接口，这里仅起根据传入的英雄参数判断状态的作用。判断完成后，修改自身的状态，然后执行相应的函数。
    def move(self, delay, sprites, spurtCanvas):
        for hero in sprites:
            # 如果有英雄在同一层，则将速度改为朝英雄方向。(这里的两套体系，英雄的层数为偶数，而怪物用的层数都是奇数)
            if (hero.onlayer-1)==self.onlayer and ( self.scope[0]<=getPos(hero,1,0.5)[0] ) and ( getPos(hero,0,0.5)[0]<=self.scope[1] ):
                self.status = "alarming"
                self.tgt = hero
                break      # ***这里碰到第一个英雄符合条件就退出了。因此，如果两个英雄同时在一层中，P1总是会被针对，而P2永远不会被选中为目标。问题留着以后修正。
            else:
                self.status = "wandering"
        if self.status == "wandering":
            self.wander( delay, spurtCanvas )
        elif self.status == "alarming":
            self.attack( sprites )
        self.checkImg(delay)
        self.checkHitBack(obstacle=True)

    def checkImg(self, delay):
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
        # renew the image of the wolf
        notIn = 0
        for scope in self.scopeList:
            if (getPos(self,0.3,1)[0] >= scope[0]) and (getPos(self,0.7,1)[0] <= scope[1]):
                self.jumping = False
                break
            else:
                notIn += 1
        if notIn >= len(self.scopeList):        # 本狼不在任何一个合理的scope内，因此判定是在空中
            self.jumping = True
            self.imgIndx = 3
            self.setImg("iList",self.imgIndx)
        else:
            if self.speed and not (delay % 5 ):
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            elif self.speed==0:
                self.imgIndx = 0
            self.setImg("iList",self.imgIndx)
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]

    def wander(self, delay, canvas):
        if (self.speed):                        # speed!=0，在运动。
            if not self.jumping:
                self.rect.left += self.speed
                if self.imgIndx in (4,5):
                    canvas.addSpatters( 2, (1,2,3), [10,12,14], (255,255,255,210), getPos(self,0.25+random()*0.5,1), True )
            else:
                self.rect.left += self.speed*1.5
            if (getPos(self, 0.7, 1)[0] >= self.scope[1] and self.speed > 0) or (getPos(self, 0.3, 1)[0] <= self.scope[0] and self.speed < 0):
                self.alterSpeed(-self.speed)
            if not self.jumping and not delay % 20 and random()<0.08:
                self.alterSpeed(0)
        elif not delay % 20 and random()<0.08:  # 否则，在休息。此时若随机数满足条件，进入奔跑状态
            self.alterSpeed( choice( [2,-2] ) )
    
    def attack(self, sprites):
        if getPos( self.tgt, 1, 0 )[0]<getPos( self, 0, 0 )[0]:
            self.alterSpeed(-2)
        elif getPos( self.tgt, 0, 0 )[0]>getPos( self, 1, 0 )[0]:
            self.alterSpeed(2)
        if not self.jumping:
            self.rect.left += self.speed * 1.5
        else:
            self.rect.left += self.speed * 2
        if ( self.coolDown==0 ):
            for each in sprites:
                if collide_mask(self, each):
                    self.snd.play(0)           # 撞到英雄，咆哮
                    self.coolDown = 48
        else:
            self.coolDown -= 1
            if ( self.coolDown == 42 ):
                cldList( self, sprites )

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)
        for scp in self.scopeList:
            scp[0] += dist
            scp[1] += dist

# -----------------------------
class IceTroll(Monster):
    imgLib = None
    shadLib = None
    snd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            IceTroll.imgLib = {
                "iList": createImgList("image/stg5/iceTroll0.png","image/stg5/iceTroll1.png",
                    "image/stg5/iceTroll2.png","image/stg5/iceTroll1.png",
                    "image/stg5/iceTroll0.png","image/stg5/iceTroll3.png",
                    "image/stg5/iceTroll4.png","image/stg5/iceTroll3.png"),
                "att": createImgList("image/stg5/iceTrollAtt.png"),
                "alarm": createImgList("image/stg5/alarmLeft.png")
            }
            IceTroll.shadLib = getShadLib(IceTroll.imgLib)
            IceTroll.snd = pygame.mixer.Sound("audio/iceTroll.wav")
        
        # calculate its position
        Monster.__init__(self, "iceTroll", (255,0,0,240), 5, 3, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.damage = MB["iceTroll"].damage
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.alterSpeed( choice([-1,1]) )
        self.airCnt = 0           # indicate if I'm spitting!
        self.hitAccum = 0

    def move(self, delay, sprites, canvas):
        self.checkHitBack(obstacle=True)
        if (self.airCnt==0):
            # Check Hero and Turn.
            if not delay%5:
                for hero in sprites:
                    heroPos = getPos(hero,0.5,0)
                    myPos = getPos(self,0.5,0)
                    # 如果有英雄在同一层，则将速度改为朝英雄方向。
                    if (hero.onlayer-1)==self.onlayer:
                        # 判断是否需要转向
                        if ( self.scope[0]<=heroPos[0]<=self.scope[1] ):
                            if self.speed*( heroPos[0]-myPos[0] ) < 0:
                                self.alterSpeed(-self.speed)
                                break     # ***这里碰到第一个英雄符合条件就退出了。因此，如果两个英雄同时在一层中，P1总是会被针对，而P2永远不会被选中为目标。
                        if (self.speed<0 and -175<=heroPos[0]-myPos[0]<0) or (self.speed>0 and 0<heroPos[0]-myPos[0]<175):  # 开喷
                            self.airCnt = 72
                            self.snd.play(0)
            if not (delay % 2):
                self.rect.left += self.speed
                if (getPos(self,0.8,0)[0] >= self.scope[1] and self.speed > 0) or (getPos(self,0.2,0)[0] <= self.scope[0] and self.speed < 0):
                    self.alterSpeed(-self.speed)
            if not (delay % 8):
                self.setImg("iList",self.imgIndx)
                self.mask = pygame.mask.from_surface(self.image)    # 更新rect，使得与hero重合的判断更加精确
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
        elif (self.airCnt > 0):
            self.airCnt -= 1
            if self.airCnt > 54:
                self.setImg("alarm")
            else:
                self.setImg("att")
                if self.speed <= 0:
                    spd = [ choice([-3,-2]), choice([-3, -2, -1, 1, 2, 3]) ]
                    startX = 0.32
                elif self.speed > 0:
                    spd = [ choice([2,3]), choice([-3, -2, -1, 1, 2, 3]) ]
                    startX = 0.68
                # 每次刷新均吐出2个气团
                canvas.addAirAtoms( self, 2, getPos(self, startX, 0.32), spd, sprites, "freezing" )

    def reportHit(self, tgt):
        self.hitAccum += 1
        if self.hitAccum>=12:
            self.hitAccum = 0
            tgt.hitted( self.damage, self.push, "freezing" )
            tgt.freeze(1)   # 速度-1

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# -----------------------------------
class IceSpirit(Monster):  
    imgLib = None
    shadLib = None

    def __init__(self, XRange, y, onlayer):
        if not self.imgLib:
            IceSpirit.imgLib = {
                "iList": createImgList("image/stg5/iceSpirit.png")
            }
            IceSpirit.shadLib = getShadLib(IceSpirit.imgLib)

        # initialize the sprite
        Monster.__init__(self, "iceSpirit", (160,220,255,200), 0, 1, onlayer)
        self.setImg("iList",0)
        self.ori_image = self.image.copy()
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = randint( XRange[0], XRange[1] )
        self.rect.top = y

        self.alterSpeed(-1)
        self.speed = [0,0]
        self.angle = 0
        self.alterSec = [10,20,30,40]     # 随机在这些刷新次数后偏折方向
        self.cnt = choice(self.alterSec)

    def move(self, delay, sprites, spurtCanvas):
        self.checkHitBack()
        if not (delay % 5 ):
            self.angle = (self.angle+20) % 360
            self.image = rot_center(self.ori_image, self.angle)
            self.mask = pygame.mask.from_surface(self.image)
        # 漂浮移动
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        # 检查目标，偏折方向
        self.cnt -= 1
        if self.cnt<=0:
            self.cnt = choice(self.alterSec)
            tgt = choice(sprites)
            my_ctr = getPos(self, 0.5, 0.5)
            tgt_ctr = getPos(tgt, 0.5, 0.5)
            if my_ctr[0]>tgt_ctr[0] and self.speed[0]>-3:
                self.speed[0] -= 1
            elif my_ctr[0]<tgt_ctr[0] and self.speed[0]<3:
                self.speed[0] += 1
            if my_ctr[1]>tgt_ctr[1] and self.speed[1]>-3:
                self.speed[1] -= 1
            elif my_ctr[1]<tgt_ctr[0] and self.speed[1]<3:
                self.speed[1] += 1
        spurtCanvas.addTrails([2,3,5], [16,20,24], (160,220,255,200), getPos(self,random(),0.6))
        hero = cldList(self, sprites)
        if hero:
            # 千里送人头
            hero.preyList.append( (getPos(self,0.5,0.5), self.bldColor, 0, True, self.coin, False) )
            self.hitted( self.full, 0, "physical")

    def hitted(self, damage, pushed, dmgType):
        # decrease health
        self.health -= (damage*self.realDmgRate)
        if self.health <= 0:                # dead。
            self.health = 0
            self.spurtCanvas.addExplosion( getPos(self,0.5,0.5), 28, 12, waveColor=(180,180,240,240), spatColor=(150,150,220,240) )
            self.kill()
            return True
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )

# -----------------------------------
class Eagle(Monster):  
    imgLib = None
    shadLib = None

    def __init__(self, XRange, y, onlayer):
        if not self.imgLib:
            Eagle.imgLib = {
                "iList": createImgList("image/stg5/eagleLeft0.png","image/stg5/eagleLeft1.png"),
                "att": createImgList("image/stg5/eagleAtt.png")
            }
            Eagle.shadLib = getShadLib(Eagle.imgLib)
            Eagle.snd = pygame.mixer.Sound("audio/eagle.wav")

        # initialize the sprite
        Monster.__init__(self, "eagle", (255,0,0,240), 8, 1, onlayer)
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.leftBd = XRange[0]
        self.rightBd = XRange[1]
        self.rect.left = randint( XRange[0], XRange[1] )
        self.rect.top = y

        self.alterSpeed(-1)
        self.cnt = randint(90, 105)       # count for the loop of charging
        self.charging = False
        self.dealt = False
        self.nxt = [randint(self.leftBd,self.rightBd), randint(y-10, y+10)]
        self.upDown = 2
        self.bufRange = 1.2

    def move(self, delay, sprites, spurtCanvas):
        self.checkHitBack()
        if not self.charging and not (delay % 6 ):  # 没有俯冲时，正常扇翅
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
            self.rect.top += self.upDown
            self.upDown = -self.upDown
        # find tgt and goes to charge
        if self.cnt == 0:
            self.cnt = randint(170, 210)
            # 获取位置数据
            aim = getPos(choice(sprites),0.5,0.5)
            myPos = getPos( self, 0.5, 0.5 )
            # 如果水平距离hero太近，则先飞远
            if abs(aim[0]-myPos[0])<140:
                pos1 = randint(self.leftBd-10,self.leftBd+200)
                pos2 = randint(self.rightBd-200,self.rightBd+10)
                self.nxt = [choice([pos1, pos2]), randint(40,180)]
                self.direction = "left" if ( self.nxt[0] < self.rect.left + self.rect.width/2 ) else "right"
            # 否则，就可以冲冲冲
            else:
                self.snd.play(0)
                self.charging = True
                self.dealt = False
                deltaX = ( aim[0] - myPos[0] )*self.bufRange
                deltaY = ( aim[1] - myPos[1] )*self.bufRange
                self.nxt = [myPos[0]+deltaX, myPos[1]+deltaY]
                self.direction = "left" if ( self.nxt[0] < self.rect.left + self.rect.width/2 ) else "right"
                if self.direction=="left":
                    self.push = self.pushList[0]
                else:
                    self.push = self.pushList[1]
                self.setImg("att")
                self.rect = self.image.get_rect()
                self.rect.left = myPos[0]-self.rect.width//2
                self.rect.top = myPos[1]-self.rect.height//2
                self.mask = pygame.mask.from_surface(self.image)
        # Adjusting position.
        self.shift( self.nxt[0], self.nxt[1] )
        self.cnt -= 1
        if self.charging:
            spurtCanvas.addTrails([2,3,4], [14,16,20], (210,210,220,200), getPos(self,random(),0.7))
            if not self.dealt and cldList( self, sprites ):
                self.dealt = True

    def shift(self, final_x, final_y):
        maxSpan = 4
        spd = 5
        dist = 0
        x = self.rect.left + self.rect.width/2
        y = self.rect.top + self.rect.height/2
        if abs(x-final_x)<maxSpan:
            self.charging = False
            myPos = getPos( self, 0.5, 0.5 )
            self.setImg("iList",self.imgIndx)
            self.rect = self.image.get_rect()
            self.rect.left = myPos[0]-self.rect.width//2
            self.rect.top = myPos[1]-self.rect.height//2
            self.mask = pygame.mask.from_surface(self.image)
        if (x < final_x):
            dist = math.ceil( (final_x - x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left += dist
        elif (x > final_x):
            dist = math.ceil( (x - final_x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left -= dist
        if (y < final_y):
            dist = math.ceil( (final_y - y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top += dist
        elif (y > final_y):
            dist = math.ceil( (y - final_y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top -= dist
    
    def erase(self):
        self.snd.stop()
        self.kill()
        del self

    def level(self, dist):
        self.rect.left += dist
        self.nxt[0] += dist
        self.leftBd += dist
        self.rightBd += dist

    def lift(self, dist):
        self.rect.top += dist
        self.nxt[1] += dist
    
# -----------------------------------
class FrostTitan(Boss):
    summonAct = 90  # 从0-该数表示召唤状态
    def __init__(self, xRange, y, onlayer, font):
        # initialize the sprite
        Boss.__init__(self, font, "FrostTitan", (250,90,80,240), 4, 4, onlayer)
        self.onlayer = int(onlayer)
        # ----- body part (the core of the FrostTitan) ------
        self.imgLib = {
            "body": createImgList("image/stg5/FrostTitan1.png","image/stg5/FrostTitan2.png"),
            "summon": createImgList("image/stg5/FrostTitanSummon.png")
        }
        self.shadLib = getShadLib(self.imgLib)
        self.imgIndx = 0
        self.setImg("body",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.xRange = xRange
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = randint( self.xRange[0], self.xRange[1] ) - self.rect.width//2
        self.rect.top = y
        self.alterSpeed(0)

        self.cnt = 1080      # count for the loop of shift position
        self.coolDown = 0    # count for attack coolDown
        self.nxt = (0, 0)
        self.upDown = 2

    def move(self, delay, sprites, canvas, bg_size):
        self.checkHitBack()
        self._tipPosition(canvas)
        if not self.cnt%4:
            self.spurtCanvas.addSmoke(2, (3,5,7), 5, (210,210,255,250), getPos(self,0.5,random()), 30)
            self.shift( self.nxt[0], self.nxt[1] )
            # 随着扇翅上下摆动
            self.rect.top += self.upDown
            self.upDown = - self.upDown
            if not (self.cnt % 12):
                if self.cnt>self.summonAct:     # 平常状态
                    self.imgIndx = (self.imgIndx+1) % len(self.imgLib["body"])
                    self.setImg("body", self.imgIndx)
                else:           # 召唤状态
                    self.setImg("summon")
                self.mask = pygame.mask.from_surface(self.image)
        # count down for rage actions.
        self.cnt -= 1
        if self.cnt<=0:
            self.cnt = 1580
        else:
            if not self.cnt%60:
                self.nxt = ( randint( self.xRange[0], self.xRange[1] ), randint(40,520) )   # randomize a new position
                self.direction = "left" if ( self.nxt[0] < getPos(self, 0.5, 0.5)[0] ) else "right"
        # deal regular snowball attack:
        if not (self.cnt % 12) and (self.coolDown<=0) and (self.cnt>self.summonAct) and random()<0.2:
            #self.growlSnd.play(0)
            self.coolDown = 120
        elif self.coolDown > 0:
            self.coolDown -= 1
            if self.coolDown in (115, 85):
                return self.makeSnowball( sprites )
        # Create Ice Spirits.
        if self.cnt in (10,35,60):
            myPos = getPos(self,0.1,0.2) if self.direction=="left" else getPos(self,0.9,0.2)
            spirit = IceSpirit(self.xRange, myPos[1], self.onlayer)
            spirit.coin = 0
            spirit.rect.left = myPos[0]-spirit.rect.width//2
            return spirit
        return None
    
    def makeSnowball(self, sprites):
        # Determine tgt and distance
        tgt = choice( sprites )
        aim = getPos( tgt,0.5,0.4 )
        myPos = getPos(self,0.5,0.4)
        deltaX = aim[0] - myPos[0]
        deltaY = aim[1] - myPos[1]
        if deltaX>0:
            spdX = randint(2,5)
        elif deltaX<0:
            spdX = randint(-5,-2)
        else:
            spdX = randint(-1,1)
        if deltaY>0:
            spdY = randint(-9,-3)
        else:
            spdY = randint(-15,-7)
        snowball = SnowBall( myPos, tgt.onlayer-1, (spdX, spdY) )
        return snowball
    
    def paint(self, screen):
        # draw shadow
        shadRect = self.rect.copy()
        shadRect.left -= 12
        screen.blit(self.shad, shadRect)
        # draw self
        screen.blit( self.image, self.rect )
        # Hit highlight
        if self.hitBack:
            screen.blit( self.shad, self.rect )
    
    def shift(self, final_x, final_y):
        x = self.rect.left + self.rect.width/2
        y = self.rect.top + self.rect.height/2
        if (x == final_x) or (y == final_y):
            return True   # 表示已到目标
        maxSpan = 4
        spd = 5
        dist = 0
        if (x < final_x):
            dist = math.ceil( (final_x - x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left += dist
        elif (x > final_x):
            dist = math.ceil( (x - final_x)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.left -= dist
        if (y < final_y):
            dist = math.ceil( (final_y - y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top += dist
        elif (y > final_y):
            dist = math.ceil( (y - final_y)/spd )
            if dist > maxSpan:
                dist = maxSpan
            self.rect.top -= dist
        return False    # 表示未到目标

class SnowBall(pygame.sprite.Sprite):
    def __init__(self, pos, layer, spd, main=True):   # 参数pos为本对象初始的位置
        pygame.sprite.Sprite.__init__(self)
        self.main = main    # 为True表示是大雪球，还可以分成小雪球
        if self.main==True:
            self.oriImage = load("image/stg5/snowball.png").convert_alpha()
        else:
            self.oriImage = pygame.transform.smoothscale( load("image/stg5/snowball.png").convert_alpha(), (45,45) )
        
        self.image = self.oriImage
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.top = pos[1]-self.rect.height//2
        self.mask = pygame.mask.from_surface(self.image)
        self.speed = list(spd)
        self.deg = 0
        if spd[0]>0:
            self.push = 10
        else:
            self.push = -10
        self.damage = MB["FrostTitan"].damage
        self.dmgType = MB["FrostTitan"].dmgType
        self.category = "snowball"
        self.blastSnd = pygame.mixer.Sound("audio/wizard/hit.wav")
        self.onlayer = layer
        self.colorSet = [(200,200,255,240), (180,180,240,240), (150,150,220,240)]

    def move(self, delay, sideWalls, downWalls, keyLine, sprites, canvas, GRAVITY):
        if pygame.sprite.spritecollide(self, downWalls, False, collide_mask) or pygame.sprite.spritecollide(self, sideWalls, False, collide_mask):
            return self.explode(canvas)
        # generate some sparks
        if not delay%2:
            self.deg = (self.deg+20) % 360
            self.image = rot_center(self.oriImage, self.deg) if self.speed[0]<=0 else rot_center(self.oriImage, -self.deg)
            self.mask = pygame.mask.from_surface(self.image)
            canvas.addTrails( [4,5,6], [12,16,20,24,28], choice(self.colorSet), getPos(self, 0.3+random()*0.4, 0.3+random()*0.4) )
        if cldList(self, sprites):
            return self.explode(canvas)
        # move the object
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        if self.speed[1]<GRAVITY-1 and not delay%2:     # 雪球的最大下落速度要稍微慢一些
            self.speed[1] += 1
        return None

    def explode(self, canvas):
        self.blastSnd.play(0)
        canvas.addExplosion(getPos(self,0.5,0.5), 28, 14, waveColor=self.colorSet[1], spatColor=self.colorSet[2])
        self.kill()
        # 若为大雪球，还要分成小雪球
        ballList = []
        if self.main==True:
            for i in range(3):
                pos = getPos(self,0.5,0.5)
                spd = ( randint(-6,6), choice([-8,-7,-6]) )
                ball = SnowBall(pos, self.onlayer, spd, main=False)
                ball.damage //= 3
                ballList.append( ball )
        del self
        return ballList
    
    def paint(self, surface):
        surface.blit( self.image, self.rect )
    
    def lift(self, dist):
        self.rect.bottom += dist

    def level(self, dist):
        self.rect.left += dist
    
# ==========================================================================
# --------------------------------- stage6 ---------------------------------
# ==========================================================================
class Dwarf(Monster):
    imgLib = None
    shadLib = None
    snd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            Dwarf.imgLib = {
                "iList": createImgList("image/stg6/dwarf0.png","image/stg6/dwarf1.png","image/stg6/dwarf2.png","image/stg6/dwarf1.png")
            }
            Dwarf.shadLib = getShadLib(Dwarf.imgLib)
            Dwarf.snd = pygame.mixer.Sound("audio/wolf.wav")
        
        # calculate its position
        Monster.__init__(self, "dwarf", (255,0,0,240), 5, 1, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left+wall.rect.width//2-self.rect.width//2
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.alterSpeed( choice( [-1, 0, 1] ) )
        self.status = "wandering"          # wandering表示闲逛的状态，alarming表示发现英雄的状态
        self.tgt = None                    # 指示要攻击的英雄

    # 这个move()函数是供外界调动的接口，这里仅起根据传入的英雄参数判断状态的作用。判断完成后，修改自身的状态，然后执行相应的函数。
    def move(self, delay, sprites):
        for hero in sprites:
            # 如果有英雄在同一层，则将速度改为朝英雄方向。(这里的两套体系，英雄的层数为偶数，而怪物用的层数都是奇数)
            if (hero.onlayer-1)==self.onlayer and ( self.scope[0]<=getPos(hero,1,0.5)[0] ) and ( getPos(hero,0,0.5)[0]<=self.scope[1] ):
                self.status = "alarming"
                self.tgt = hero
                break     # ***这里碰到第一个英雄符合条件就退出了。因此，如果两个英雄同时在一层中，P1总是会被针对，而P2永远不会被选中为目标。问题留着以后修正。
            else:
                self.status = "wandering"
        if self.status == "wandering":
            self.wander( delay )
        elif self.status == "alarming":
            if getPos( self.tgt, 0.5, 0.5 )[0]>getPos( self, 0.5, 0.5 )[0]:
                self.alterSpeed(1)
            else:
                self.alterSpeed(-1)
            self.attack( sprites )
        self.checkImg(delay)
        self.checkHitBack(obstacle=True)

    def checkImg(self, delay):
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
        # renew the image
        if self.speed and not (delay % 8 ):
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
        elif self.speed == 0:
            self.imgIndx = 0
        self.setImg("iList",self.imgIndx)
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]

    def wander(self, delay):
        if (self.speed):                        # speed!=0，在运动。
            self.rect.left += self.speed
            if (getPos(self, 0.7, 1)[0] >= self.scope[1] and self.speed > 0) or (getPos(self, 0.3, 1)[0] <= self.scope[0] and self.speed < 0):
                self.alterSpeed( -self.speed )
            if not delay % 20 and random()<0.08:
                self.alterSpeed(0)
        elif not delay % 20 and random()<0.08:  # 否则，在休息。此时若随机数满足条件，进入奔跑状态
            self.alterSpeed( choice( [1,-1] ) )
    
    def attack(self, sprites):
        self.rect.left += self.speed * 2
        if ( self.coolDown<=0 ):
            for each in sprites:
                if collide_mask(self, each):
                    self.snd.play(0)    # 撞到英雄，咆哮
                    self.coolDown = 48
        else:
            self.coolDown -= 1
            if ( self.coolDown == 38 ):
                cldList( self, sprites )

    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

# ------------------------------------
class Gunner(Monster):
    imgLib = None
    shadLib = None
    fireSnd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        if not self.imgLib:
            Gunner.imgLib = {
                "iList": createImgList("image/stg6/gunner0.png","image/stg6/gunner1.png"),
                "fire": createImgList("image/stg6/gunnerFire.png")
            }
            Gunner.shadLib = getShadLib(Gunner.imgLib)
            Gunner.fireSnd = pygame.mixer.Sound("audio/gunner.wav")
        
        # calculate its position
        Monster.__init__(self, "gunner", (20,20,20,240), 0, 2, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.attIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left+wall.rect.width//2-self.rect.width//2
        self.rect.bottom = wall.rect.top
        self.eyePos = getPos(self, 0.5, 0.2)
        self.coolDown = 0
        self.snd = pygame.mixer.Sound("audio/wolf.wav")
        self.insp = self.inspRange = 360   # inspRange是原始参数，insp是不断变化的参数
        self.alterSpeed( choice( [-1, 1] ) )
        self.status = "wandering"          # wandering表示闲逛的状态，alarming表示发现英雄的状态
        self.newBullet = None

    # 这个move()函数是供外界调动的接口，这里仅起根据传入的英雄参数判断状态的作用。判断完成后，修改自身的状态，然后执行相应的函数。
    def move(self, delay, sprites, screen):
        self.checkHitBack(obstacle=True)
        for hero in sprites:
            # 如果有英雄在同一层，则将速度改为朝英雄方向。(这里的两套体系，英雄的层数为偶数，而怪物用的层数都是奇数)
            if self.coolDown>0 or \
                ( hero.rect.top<=self.eyePos[1]<=hero.rect.bottom and ( (self.direction=="left" and self.eyePos[0]+self.insp<=getPos(hero,0.5,0.5)[0]<=self.eyePos[0]) or (self.direction=="right" and self.eyePos[0]<=getPos(hero,0.5,0.5)[0]<=self.eyePos[0]+self.insp) ) ):
                self.status = "alarming"
                break     # ***这里碰到第一个英雄符合条件就退出了。因此，如果两个英雄同时在一层中，P1总是会被针对，而P2永远不会被选中为目标。问题留着以后修正。
            else:
                self.status = "wandering"
        if self.status == "wandering":
            self.patrol( delay )
        elif self.status == "alarming" or self.coolDown>0:
            self.speed = 0
            self.fire()
        # renew the image of the gunner; if its speed = 0, do not change image
        trPos = [ self.rect.left+self.rect.width//2, self.rect.bottom ]
        self.setImg("iList",self.imgIndx)
        if self.speed and not (delay % 5 ):
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
        elif 86>=self.coolDown>=83 or 81>=self.coolDown>=78 or 76>=self.coolDown>=73:
            self.setImg("fire")
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]
        self.eyePos = getPos(self, 0.5, 0.2)
        pygame.draw.line( screen, (255,0,0), self.eyePos, (self.eyePos[0]+self.insp,self.eyePos[1]), choice([1,2]) )  # inspecting line

    def patrol(self, delay):
        if (self.speed):                        # speed!=0，在运动。
            self.rect.left += self.speed
            if (getPos(self, 0.7, 1)[0] >= self.scope[1] and self.speed > 0) or (getPos(self, 0.3, 1)[0] <= self.scope[0] and self.speed < 0):
                self.alterSpeed( -self.speed )
            if not delay % 20 and random()<0.08:
                self.speed = 0
        elif not delay % 20 and random()<0.08:  # 否则，在休息。此时若随机数满足条件，进入移动状态。
            self.alterSpeed( choice( [1,-1] ) )
    
    def fire(self):
        if ( self.coolDown<=0 ):
            self.coolDown = 90
            self.fireSnd.play(0)
        if self.coolDown==85 or self.coolDown==80 or self.coolDown==75:
            bullet = GunBullet(getPos(self, 0, 0.4), -5) if self.direction=="left" else GunBullet(getPos(self, 1, 0.4), 5)
            self.newBullet = bullet
        self.coolDown -= 1
    
    def alterSpeed(self, speed):
        self.speed = speed
        if speed > 0:
            self.direction = "right"
            self.insp = self.inspRange
        elif speed < 0:
            self.direction = "left"
            self.insp = -self.inspRange
    
    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        self.health -= damage
        if self.health <= 0:
            self.spurtCanvas.addPebbles(self, 6, type="metalDebri")
            self.kill()
            return True
    
    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

class GunBullet(InanimSprite): 
    imgList = None
    shadList = None

    def __init__(self, pos, spd):
        if not self.imgList:
            tmpImg = load("image/princess/arrow_left.png").convert_alpha()
            GunBullet.imgList = {
                "left": pygame.transform.smoothscale( tmpImg, (8,8) ),
                "right": pygame.transform.smoothscale( flip(tmpImg, True, False), (8,8) )
            }
            GunBullet.shadList = {}
            for dir in GunBullet.imgList:     # 对于该动作的每一方向
                GunBullet.shadList[dir] = generateShadow(GunBullet.imgList[dir])
        
        InanimSprite.__init__(self, "gunBullet")
        self.speed = spd
        if spd > 0:
            self.direction = "right"
            self.push = 5
        else:
            self.direction = "left"
            self.push = -5
        self.image = self.imgList[self.direction]
        self.shade = self.shadList[self.direction]
        self.dmgType = MB["gunner"].dmgType
        self.damage = MB["gunner"].damage
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.top = pos[1]-self.rect.height//2
    
    def update(self, tgts, wallList, screenWidth, canvas):
        self.rect.left += self.speed
        for each in wallList:
            if ( collide_mask(self,each) ):  # 撞墙
                self._explode(canvas)
                return
        if self.rect.left>=screenWidth or self.rect.right<=0: # 出界
            self._explode(canvas)
            return
        elif cldList(self, tgts):
            self._explode(canvas)
            return
    
    def paint(self, surface):
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 4
        surface.blit(self.shade, shadRect)
        surface.blit(self.image, self.rect)
    
    def _explode(self, canvas):
        canvas.addSpatters(4,(2,4),(7,9,10),(20,10,10,240),(self.rect.left+self.rect.width//2,self.rect.top+self.rect.height//2),True)
        self.kill()
        del self

# -----------------------------------
class Lasercraft(Monster):  
    imgLib = None
    shadLib = None

    def __init__(self, align, y, onlayer):
        if not self.imgLib:
            Lasercraft.imgLib = {
                "iList": createImgList("image/stg6/lasercraft0.png","image/stg6/lasercraft1.png", "image/stg6/lasercraft2.png","image/stg6/lasercraft1.png")
            }
            Lasercraft.shadLib = getShadLib(Lasercraft.imgLib)
            Lasercraft.sparkySnd = pygame.mixer.Sound("audio/sparky.wav")

        # initialize the sprite
        Monster.__init__(self, "lasercraft", (110,250,10,240), 6, 1, onlayer)
        self.imgIndx = 0
        self.alterSpeed( choice([-1, 1]) )
        if self.direction == "left":
            self.align = align[1]
            self.limitX = align[0]    # 发射时的激光终点
        else:
            self.align = align[0]
            self.limitX = align[1]
        self.setImg("iList",0)
        # calculate its position
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.left = self.align - self.rect.width//2
        self.rect.top = y
        if self.direction == "left":
            self.muzzle = getPos(self, 0.12, 0.65)  # 发射时的炮口坐标
        else:
            self.muzzle = getPos(self, 0.88, 0.65)
        self.cnt = 0         # count for the loop of shift position
        self.coolDown = 160  # count for attack coolDown
        self.nxt = self.rect.top+self.rect.height//2         # 下一个悬停处的竖坐标
        self.chargeList = [] # 用于存放电磁炮蓄力充能时的充能粒子信息       

    def move(self, delay, sprites, maxLayer):
        if not self.checkHitBack():
            gap = self.align - (self.rect.left+self.rect.width//2)
            if gap:
                self.rect.left = self.rect.left + gap//2
        if not ( delay% 4):
            trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom - self.rect.height//2 ]
            self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
            self.rect = self.image.get_rect()
            self.rect.left = trPos[0]-self.rect.width//2
            self.rect.bottom = trPos[1]+self.rect.height//2
        # charging motion
        if not (delay % 3):
            self.shift( self.nxt )
            self.cnt -= 1
            # find new position
            if self.cnt <= 0:
                self.cnt = randint(80,120)
                tgt = choice(sprites)
                if tgt.onlayer > 2 and tgt.onlayer < maxLayer:
                    self.nxt = tgt.rect.top + tgt.rect.height//2
        # 某科学的电磁炮，发射！
        if self.coolDown==40:
            self.chargeList.clear()
            self.sparkySnd.play(0)
        elif 15 < self.coolDown < 40:  # 蓄力充能阶段
            if random()<0.4:           # 添加新粒子
                r = choice( [2,3,4] )
                XRange = list( range(self.muzzle[0]-50,self.muzzle[0]-30) ) + list( range(self.muzzle[0]+30,self.muzzle[0]+50) )
                YRange = list( range(self.muzzle[1]-50,self.muzzle[1]-30) ) + list( range(self.muzzle[1]+30,self.muzzle[1]+50) )
                pos = [ choice( XRange ), choice( YRange ) ]
                color = choice( [(240,240,255,240),(170,170,255,240),(110,110,250,240)] )
                self.chargeList.append( (r, pos, color) ) 
        elif self.coolDown<15:
            for each in sprites:
                if ( ( self.direction=="right" and getPos(each,0.5,0.5)[0]>self.muzzle[0] ) or ( self.direction=="left" and getPos(each,0.5,0.5)[0]<self.muzzle[0] ) ) and (each.rect.top < self.muzzle[1] < each.rect.bottom): # 被激光击中！！！
                    each.hitted( self.damage, self.push, MB["lasercraft"].dmgType )
            if (self.coolDown <= 0):
                self.coolDown = randint(160,240)
        self.coolDown -= 1

    def shift(self, final_y):
        y = self.rect.top + self.rect.height/2
        if (y == final_y):
            return True
        elif (y < final_y):
            dist = min( math.ceil( (final_y - y)/4 ), 8 )
            self.rect.top += dist
            self.muzzle[1] += dist
        elif (y > final_y):
            dist = min( math.ceil( (y - final_y)/4 ), 8 )
            self.rect.top -= dist
            self.muzzle[1] -= dist
    
    def paint(self, surface):
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 8
        surface.blit(self.shad, shadRect)
        surface.blit(self.image, self.rect)
        # 画打击阴影
        if self.hitBack:
            surface.blit( self.shad, self.rect )
        if self.coolDown<40:
            if self.coolDown>=15:
                for each in self.chargeList:   # 绘制并移动粒子
                    pygame.draw.circle( surface, each[2], each[1], each[0] )  # 充能粒子
                    each[1][0] += (self.muzzle[0]-each[1][0]) // 8
                    each[1][1] += (self.muzzle[1]-each[1][1]) // 8
            else:
                pygame.draw.line( surface, (120,120,250), self.muzzle, (self.limitX,self.muzzle[1]), choice([4,6,8]))   # 开炮！！
            pygame.draw.circle( surface, (120,120,250), self.muzzle, randint(14,20) )   #聚能中心

    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        self.health -= damage
        if self.health <= 0:
            self.spurtCanvas.addPebbles(self, 6, type="metalDebri")
            self.kill()
            return True
    
    def level(self, dist):
        self.rect.left += dist
        self.align += dist
        self.muzzle[0] += dist
        self.limitX += dist

    def lift(self, dist):
        self.rect.top += dist
        self.nxt += dist
        self.muzzle[1] += dist

# ------------------------------------
class WarMachine(Boss):
    arm = None        # 是一个单独的sprite
    packet = None

    def __init__(self, groupList, onlayer, font):
        # initialize the sprite
        Boss.__init__(self, font, "WarMachine", (10,30,10,240), 6, 4, onlayer)
        self.onlayer = int(onlayer)
        self.initLayer(groupList)
        # ----- body part (the core of the WarMachine) ------
        self.imgLib = {
            "bodyList": createImgList("image/stg6/WarMachine0.png","image/stg6/WarMachine1.png")
        }
        self.shadLib = getShadLib(self.imgLib)
        self.imgIndx = 0
        self.setImg("bodyList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = self.initPos[0]-self.rect.width//2
        self.rect.bottom = self.initPos[1]
        self.coolDown = 0           
        self.alterSpeed( choice( [-1, 1] ) )
        # ------------- arm part --------------
        self.armLeft = [ pygame.image.load("image/stg6/arm.png").convert_alpha(), pygame.image.load("image/stg6/armFire.png").convert_alpha() ]
        self.armRight = [ pygame.transform.flip(self.armLeft[0], True, False), pygame.transform.flip(self.armLeft[1], True, False) ]
        self.armR = { "left":[ (0.5,0.4), (0.5,0.4) ], "right":[ (0.5,0.4), (0.5,0.4) ] }     # 分别为左和右时的位置信息
        self.arm = Ajunction( self.armLeft[0], getPos(self, self.armR[self.direction][0][0], self.armR[self.direction][0][1]) )
        self.armIndx = 0
        # ------------- packet part ----------------
        self.pktLeft = [ pygame.image.load("image/stg6/packet.png").convert_alpha(), pygame.image.load("image/stg6/packetBroken.png").convert_alpha() ]
        self.pktRight = [ pygame.transform.flip(self.pktLeft[0], True, False), pygame.transform.flip(self.pktLeft[1], True, False) ]
        self.pktR = { "left":[ (0.75,0.42), (0.75,0.42) ], "right":[ (0.25,0.42), (0.25,0.42) ] }
        self.packet = Ajunction( self.pktLeft[0], getPos(self, self.pktR[self.direction][0][0], self.pktR[self.direction][0][1]) )
        self.pktIndx = 0
        # ----------- other attributes -------------------------
        self.cnt = 0         # count for the loop of shift position
        self.coolDown = 0    # count for attack coolDown
        self.fireSnd = pygame.mixer.Sound("audio/MachineGrenade.wav")
        self.moanSnd = pygame.mixer.Sound("audio/MachineCollapse.wav")
        self.jetting = False
        self.jetImg = [ pygame.image.load("image/stg6/jet0.png").convert_alpha(), pygame.image.load("image/stg6/jet1.png").convert_alpha() ]
        self.jetIndx = 0
        self.msCnt = 0

    def move(self, delay, sprites, canvas, tower):
        self.checkHitBack(obstacle=True)
        self._tipPosition(canvas)
        
        if not ( delay % 2 ):
            #优先处理 jetting 
            if self.jetting:
                self.rect.bottom += ( (self.initPos[1]-getPos(self, 0.5, 1)[1]) // 10 )
                self.rect.left += ( (self.initPos[0]-getPos(self, 0.5, 1)[0]) // 12 )
                #以竖直方向为标准，若已抵达(等于或略高于)目标行，则将jetting标记为False
                if 0<= (self.initPos[1]-self.rect.bottom) < 10:
                    self.rect.bottom = self.initPos[1]
                    self.jetting = False
                self.jetIndx = (self.jetIndx+1) % len(self.jetImg)
            # 然后处理 火箭炮
            elif self.msCnt>0:
                self.msCnt -= 1
                if self.msCnt in (20,30,40):
                    if self.direction=="left":
                        return Missle( getPos(self.arm,0,0.85), self.direction, MB["missle"].damage, choice(sprites) )
                    elif self.direction=="right":
                        return Missle( getPos(self.arm,1,0.85), self.direction, MB["missle"].damage, choice(sprites) )
            # 只有不在jet 且没有发射missle 的时候才可以做自由水平移动
            else:
                self.armIndx = 0  # 重置手势
                self.rect.left += self.speed
                if (self.rect.right >= self.scope[1] and self.speed > 0) or (self.rect.left <= self.scope[0] and self.speed < 0):
                    self.alterSpeed(-self.speed)
                if not delay%6:
                    self.imgIndx = (self.imgIndx+1) % len(self.imgLib["bodyList"]["left"])
            # 更新各组件的图像
            self.setImg("bodyList", self.imgIndx)
            if self.direction == "left":
                self.mask = pygame.mask.from_surface(self.image)
                self.packet.updateImg( self.pktLeft[self.pktIndx] )
                self.arm.updateImg( self.armLeft[self.armIndx] )
            elif self.direction == "right":
                self.mask = pygame.mask.from_surface(self.image)
                self.packet.updateImg( self.pktRight[self.pktIndx] )
                self.arm.updateImg( self.armRight[self.armIndx] )
        # Anyway we should 及时更新ajunction的位置（还有击退）
        self.packet.updatePos( getPos(self, self.pktR[self.direction][self.pktIndx][0], self.pktR[self.direction][self.pktIndx][1]) )
        self.arm.updatePos( getPos(self, self.armR[self.direction][self.armIndx][0], self.armR[self.direction][self.armIndx][1]) )
        # change layer
        if not (delay%60) and self.msCnt==0:
            if random()<0.1:
                self.jetting = True
                # 处理层数。需要在合理的范围内
                psbLayer = [ max(self.onlayer-2,-1), min(self.onlayer+2,tower.layer-1) ]
                self.onlayer = choice( psbLayer )
                self.initLayer(tower.groupList)
            # 随机概率发射火箭炮！
            elif (not self.jetting) and random()<0.16:
                self.armIndx = 1
                self.msCnt = 60
        # Check coolDown and fire the back 榴弹packet.
        if self.coolDown == 0:
            self.coolDown = randint(145,155)
        elif (self.coolDown > 0):
            self.coolDown -= 1
            if self.coolDown in [140,130,120,110]:
                self.fireSnd.play(0)
                return Fire( getPos(self.packet,0.5,0), self.onlayer, randint(-3,3), randint(-6,-4))

    def lift(self, dist):
        self.rect.bottom += dist
        self.initPos[1] += dist
    
    def level(self, dist):
        self.rect.left += dist
        self.initPos[0] += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)

    def paint(self, screen):
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 8
        screen.blit(self.shad, shadRect)
        if self.jetting:
            jetRect = self.jetImg[self.jetIndx].get_rect()
            jetRect.left, jetRect.top = getPos(self, 0.2, 1)
            screen.blit( self.jetImg[self.jetIndx], jetRect )
            jetRect.left, jetRect.top = getPos(self, 0.8, 1)
            screen.blit( self.jetImg[self.jetIndx], jetRect )
        screen.blit( self.image, self.rect )
        # 画打击阴影
        if self.hitBack:
            screen.blit( self.shad, self.rect )
        screen.blit( self.packet.image, self.packet.rect )
        screen.blit( self.arm.image, self.arm.rect )

    def erase(self):
        self.moanSnd.play(0)
        self.packet.kill()
        self.arm.kill()
        del self.packet, self.arm
        self.kill()

class Missle(InanimSprite):
    oriImg = {"left":None, "right":None}
    fullSpd = 5
    blastSnd = None
    launchSnd = None

    def __init__(self, pos, direction, damage, tgt=None):
        if not Missle.oriImg["left"]:
            Missle.oriImg = { "left": load("image/stg6/missle.png").convert_alpha(),
                "right":flip(load("image/stg6/missle.png").convert_alpha(), True, False) }
            Missle.blastSnd = pygame.mixer.Sound("audio/wizard/hit.wav")
            Missle.launchSnd = pygame.mixer.Sound("audio/missle.wav")

        InanimSprite.__init__(self, "missle")
        self.launchSnd.play(0)
        if direction=="right":      # 为方便角度计算，以x向右为正方向、y向上为正方向
            self.speed = [self.fullSpd, 0]
            self.push = 9
        else:
            self.speed = [-self.fullSpd, 0]
            self.push = -9
        self.image = self.oriImg[direction]
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.top = pos[1]-self.rect.height//2
        self.mask = pygame.mask.from_surface(self.image)
        self.damage = damage
        self.health = MB["missle"].health
        self.dmgType = MB["missle"].dmgType
        self.coin = MB["missle"].coin
        self.tgt = tgt
        if not self.tgt:     # no tgt，直接boom
            self.health = 0
        self.bldColor = (10,40,20,240)

    def update(self, delay, canvas):
        if self.health<=0:
            self._explode(canvas)
            return None
        # alter img
        if self.speed[0]>0:
            self.image = self.oriImg["right"]
            canvas.addTrails( [4,6,8], [12,15,18], (200,120,80,220), getPos(self,0.1,0.4+random()*0.3) )
        elif self.speed[0]<0:
            self.image = self.oriImg["left"]
            canvas.addTrails( [4,6,8], [12,15,18], (200,120,80,220), getPos(self,0.9,0.4+random()*0.3) )
        self.mask = pygame.mask.from_surface(self.image)
        # adjust speed
        if not delay%8:
            my_ctr = getPos(self,0.5,0.5)
            tgt_ctr = getPos(self.tgt,0.5,0.5)
            if my_ctr[0]>tgt_ctr[0] and self.speed[0]>-self.fullSpd:
                self.speed[0] -= 1
            elif my_ctr[0]<tgt_ctr[0] and self.speed[0]<self.fullSpd:
                self.speed[0] += 1
            if my_ctr[1]>tgt_ctr[1] and self.speed[1]>-self.fullSpd:
                self.speed[1] -= 1
            elif my_ctr[1]<tgt_ctr[0] and self.speed[1]<self.fullSpd:
                self.speed[1] += 1
            # change push和rotation.
            if self.speed[0]>0:
                self.push = 9
            elif self.speed[0]<0:
                self.push = -9
            else:
                self.push = 0
            canvas.addTrails( [6, 7, 8], [10, 12, 14], (120,100,40,180), getPos(self,0.5,0.5) )
        if cldList(self, [self.tgt]):
            self.rect.left += self.speed[0]
            self.rect.top += self.speed[1]
            self._explode(canvas)
            return "vib"
        # move the object
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]

    def _explode(self, canvas):
        self.blastSnd.play(0)
        canvas.addExplosion(getPos(self,0.5,0.5), 32, 16)
        canvas.addSmoke( 6, (4, 6, 8), 2, (2,2,2,240), getPos(self,0.5,0.5), 4 )
        self.kill()

    def drawHealth(self, surface):
        pass

    def hitted(self, damage, pushed, dmgType):
        self.health -= damage

    def paint(self, surface):
        '''shadRect = self.rect.copy()
        shadRect.left -= 8
        surface.blit( generateShadow(self.image), shadRect )'''
        surface.blit( self.image, self.rect )

# ==========================================================================
# --------------------------------- stage7 ---------------------------------
# ==========================================================================
class Log(InanimSprite):
    fullSpd = 7

    def __init__(self, bg_size, layer, pos):
        InanimSprite.__init__(self, "log")
        self.imgList = { -1:[ load("image/stg7/log0.png").convert_alpha(), load("image/stg7/log1.png").convert_alpha() ],
            1:[flip(load("image/stg7/log0.png").convert_alpha(), True, False), flip(load("image/stg7/log1.png").convert_alpha(), True, False)] }
        self.speed = [ choice([-1,1]), randint(0,self.fullSpd) ]
        self.imgIndx = 0
        self.image = self.imgList[self.speed[0]][self.imgIndx]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.bottom = pos[1]
        self.onlayer = int(layer)
        self.bg_size = bg_size
        self.damage = NB["log"]["damage"]
        self.dmgType = "physical"
        self.hitSnd = pygame.mixer.Sound("audio/log.wav")
        
    def update(self, delay, sprites, groupList, keyline, boundaries, canvas):
        # 造成伤害
        if not delay%DMG_FREQ:
            for each in sprites:
                if collide_mask( self, each ):
                    if each.rect.left+each.rect.width//2 > self.rect.left+self.rect.width//2:
                        each.hitted(self.damage, 5, self.dmgType)
                    else:
                        each.hitted(self.damage, -5, self.dmgType)
        # 处理图片
        if not delay%6:
            self.imgIndx = (self.imgIndx+1) % len(self.imgList[1])
            self.image = self.imgList[self.speed[0]][self.imgIndx]
            self.speed[1] = min(self.speed[1]+1, self.fullSpd)
        # 移动位移
        self.rect.left += self.speed[0]
        self.rect.bottom += self.speed[1]
        canvas.addTrails( [1,2], [6,12,18], (40,80,40,160), getPos(self,choice([0.1,0.9]),0.5) )
        # 发生侧越界，横向改向
        if self.rect.left<boundaries[0] or self.rect.right>boundaries[1]:
            self.speed[0] = -self.speed[0]
        # 发生下碰撞，向上弹起
        if ( str(self.onlayer) in groupList ) and pygame.sprite.spritecollide(self, groupList[str(self.onlayer)], False, collide_mask):
            self.speed[1] = (-self.fullSpd+3)
            self.onlayer -= 2
            if self.rect.bottom>0 and self.rect.top<self.bg_size[1]:
                self.hitSnd.play(0)
                canvas.addPebbles( self, 4 )
                return "vib"
        # 碰撞或越线，发生其一即onlayer-2.
        elif self.rect.top >= keyline:
            self.onlayer -= 2
            if self.onlayer<0:
                canvas.addPebbles( self, 10, type="metalDebri" )
                self.kill()
                del self
                return "vib"

class Guard(Monster):
    imgLib = None
    shadLib = None
    snd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        # calculate its position
        if not self.imgLib:
            Guard.imgLib = {
                "iList": createImgList("image/stg7/guard0.png","image/stg7/guard1.png","image/stg7/guard2.png","image/stg7/guard3.png"),
                "attList": createImgList("image/stg7/att0.png","image/stg7/att1.png","image/stg7/att0.png")
            }
            Guard.shadLib = getShadLib(Guard.imgLib)
            Guard.snd = pygame.mixer.Sound("audio/guardAtt.wav")

        Monster.__init__(self, "guard", (255,0,0,240), 6, 1, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left+wall.rect.width//2-self.rect.width//2
        self.rect.bottom = wall.rect.top
        self.coolDown = 0
        self.alterSpeed( choice([-1,0,1]) )   # 0表示原地不动，负数表示向左移动，正数表示向右移动
        self.status = "wandering"          # wandering表示闲逛的状态，alarming表示发现英雄的状态
        self.tgt = None                    # 指示要攻击的英雄
        # Define shield.
        self.shieldR = { "left":(0.2,0.62), "right":(0.8,0.62) }
        self.shieldImg = createImgList( "image/stg7/shield.png" )
        self.shield = Ajunction( self.shieldImg["left"][0], getPos(self, self.shieldR["left"][0], self.shieldR["left"][1]) )
        # Define spear.
        self.spearR = { "left":(0.15,0.6), "right":(0.85,0.6) }
        self.spearAttR = { "left":(0.08,0.65), "right":(0.92,0.65) }
        self.spearImg = createImgList( "image/stg7/spear.png" )
        self.spearAttImg = createImgList( "image/stg7/spearAtt.png" )
        self.spear = Ajunction( self.spearImg["left"][0], getPos(self, self.spearR["left"][0], self.spearR["left"][1]) )

    # 这个move()函数是供外界调动的接口，这里仅起根据传入的英雄参数判断状态的作用。判断完成后，修改自身的状态，然后执行相应的函数。
    def move(self, delay, sprites):
        for hero in sprites:
            # 如果有英雄在同一层，则将速度改为朝英雄方向。(这里的两套体系，英雄的层数为偶数，而怪物用的层数都是奇数)
            if ( (hero.onlayer-1)==self.onlayer and ( self.scope[0]<=getPos(hero,1,0.5)[0] ) and ( getPos(hero,0,0.5)[0]<=self.scope[1] ) ) or self.coolDown>0:
                self.status = "alarming"
                self.tgt = hero
                break     # ***这里碰到第一个英雄符合条件就退出了。因此，如果两个英雄同时在一层中，P1总是会被针对，而P2永远不会被选中为目标。问题留着以后修正。
            else:
                self.status = "wandering"
        if self.status == "wandering":
            self.wander( delay )
        elif self.status == "alarming":
            self.attack( sprites )
        self.checkImg(delay)
        self.checkHitBack(obstacle=True)

    def checkImg(self, delay):
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]
        # renew the image of the guard
        if self.coolDown==0:
            if self.speed and not (delay % 10 ):
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            elif self.speed == 0:
                self.imgIndx = 0
            self.setImg("iList",self.imgIndx)
            self.spear.updateImg( self.spearImg[self.direction][0] )
            self.spear.updatePos( getPos(self, self.spearR[self.direction][0], self.spearR[self.direction][1]) )
        else:
            self.setImg("attList",self.coolDown // 13)
            self.spear.updateImg( self.spearAttImg[self.direction][0] )
            self.spear.updatePos( getPos(self, self.spearAttR[self.direction][0], self.spearAttR[self.direction][1]) )
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]
        # adjust shield and spear
        self.shield.updateImg( self.shieldImg[self.direction][0] )
        self.shield.updatePos( getPos(self, self.shieldR[self.direction][0], self.shieldR[self.direction][1]) )

    def wander(self, delay):
        if (self.speed):                          # speed!=0，在运动。
            self.rect.left += self.speed
            if (getPos(self, 0.7, 1)[0] >= self.scope[1] and self.speed > 0) or (getPos(self, 0.3, 1)[0] <= self.scope[0] and self.speed < 0):
                self.alterSpeed( -self.speed )
            if not delay % 20 and random()<0.08:  # 随机进入休息状态。
                self.alterSpeed( 0 )
                self.direction = "left" if random()<0.5 else "right"
        elif not delay % 20 and random()<0.08:    # 否则，在休息。此时若随机数满足条件，进入巡逻状态
            self.alterSpeed( choice( [1,-1] ) ) 
    
    def attack(self, sprites):
        if not self.coolDown:
            if getPos( self.tgt, 0.5, 0.5 )[0]>getPos( self, 0.5, 0.5 )[0]:
                self.alterSpeed(1)
            else:
                self.alterSpeed(-1)
        self.rect.left += self.speed * 2
        if self.coolDown==0:
            for each in sprites:
                if abs(getPos(self, 0.5, 0.5)[0]-getPos(each, 0.5, 0.5)[0])<40:
                    self.snd.play(0)    # 攻击英雄，咆哮
                    self.speed = 0
                    self.coolDown = 38
        else:
            self.coolDown -= 1
            if self.coolDown == 20:
                for each in sprites:
                    if collide_mask(self.spear, each):
                        cldList( self, sprites )
    
    def paint(self, screen):
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 8
        screen.blit(self.shad, shadRect)
        screen.blit( self.spear.image, self.spear.rect )
        screen.blit( self.image, self.rect )
        screen.blit( self.shield.image, self.shield.rect )
        # 画打击阴影
        if self.hitBack:
            screen.blit( self.shad, self.rect )
    
    def level(self, dist):
        self.rect.left += dist
        self.spear.rect.left += dist
        self.shield.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)
    
    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        self.bldColor = (255,0,0,240)
        if ( pushed<0 and self.direction=="right" ) or ( pushed>0 and self.direction=="left"):
            self.bldColor = (200,200,200,240)
            damage *= (1-self.armor)        # 原来的20%
        self.health -= max(damage,1)
        if self.health <= 0:       # dead
            self.health = 0
            self.kill()
            return True

# -----------------------------------
class Flamen(Monster):
    imgLib = None
    shadLib = None
    snd = None

    def __init__(self, wallGroup, sideGroup, blockSize, onlayer):
        # calculate its position
        if not self.imgLib:
            Flamen.imgLib = {
                "iList": createImgList("image/stg7/flamen0.png","image/stg7/flamen1.png"),
                "attList": createImgList("image/stg7/flamenAtt0.png","image/stg7/flamenAtt1.png")
            }
            Flamen.shadLib = getShadLib(Flamen.imgLib)
            Flamen.snd = pygame.mixer.Sound("audio/flamenSummon.wav")

        Monster.__init__(self, "flamen", (255,0,0,240), 0, 1, onlayer, sideGroup)
        wall = self.initLayer(wallGroup, sideGroup)
        # initialize the sprite
        self.imgIndx = 0
        self.setImg("iList",0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left+wall.rect.width//2-self.rect.width//2
        self.rect.bottom = wall.rect.top-10
        self.coolDown = 300
        self.alterSpeed( choice([-1,0,1]) )   # 0表示原地不动，负数表示向左移动，正数表示向右移动
        self.tgt = None                       # 指示要攻击的英雄
        self.ctr = [0,0]
        self.chargeList = []
        self.upDown = 2               # 悬停状态身体上下振幅

    # 这个move()函数是供外界调动的接口，这里仅起根据传入的英雄参数判断状态的作用。判断完成后，修改自身的状态，然后执行相应的函数。
    def move(self, delay, sprites):
        if not (delay % 24):
            self.rect.top += self.upDown
            self.upDown = -self.upDown
        self.coolDown -= 1
        # renew the image of the flamen
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom - self.rect.height//2 ]
        if self.coolDown>100:
            if not (delay % 20 ):
                self.imgIndx = (self.imgIndx+1) % len(self.imgLib["iList"]["left"])
            self.setImg("iList",self.imgIndx)
        elif self.coolDown==100 or self.coolDown==10:
            self.setImg("attList",0)
        elif self.coolDown==90:
            self.setImg("attList", 1)
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]+self.rect.height//2
        self.checkHitBack(obstacle=True)

        if self.coolDown<=0:
            self.chargeList.clear()
            self.coolDown = randint(300,720)
        elif self.coolDown>100:                       # 根据coolDown决定标记英雄进行攻击或游荡。
            if (self.speed):                          # speed!=0，在运动。
                if not (delay%2):
                    self.rect.left += self.speed
                    if (getPos(self, 0.7, 1)[0] >= self.scope[1] and self.speed > 0) or (getPos(self, 0.3, 1)[0] <= self.scope[0] and self.speed < 0):
                        self.alterSpeed( -self.speed )
                if not delay % 20 and random()<0.08:  # 随机进入休息状态。
                    self.alterSpeed( 0 )
                    self.direction = "left" if random()<0.5 else "right"
            elif not delay % 20 and random()<0.08:    # 否则，在休息。此时若随机数满足条件，进入游荡状态
                self.alterSpeed( choice( [1,-1] ) ) 
        elif self.coolDown==100:
            self.tgt = choice(sprites)
            self.ctr = getPos(self.tgt, 0.5, -1)
            self.snd.play(0)
            self.alterSpeed(0)
            return SoulBlast(self.ctr, self.tgt.onlayer-1, 60)
    
    def level(self, dist):
        self.rect.left += dist
        self.scope = (self.scope[0]+dist, self.scope[1]+dist)
    
    def lift(self, dist):
        self.rect.bottom += dist
        self.ctr[1] += dist
    
    def hitted(self, damage, pushed, dmgType):
        if pushed>0:   # 向右击退
            self.hitBack = max( pushed-self.weight, 0 )
        elif pushed<0: # 向左击退
            self.hitBack = min( pushed+self.weight, 0 )
        self.health -= max(damage,1)
        if self.health <= 0:       # dead
            self.health = 0
            self.kill()
            return True

class SoulBlast(InanimSprite):
    
    def __init__(self, pos, layer, cnt):
        InanimSprite.__init__(self, "soulBlast")
        self.imgList = [load("image/stg7/soulBlast0.png").convert_alpha(), load("image/stg7/soulBlast1.png").convert_alpha()]
        self.image = self.imgList[0]
        self.imgIndx = 0
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.bottom = pos[1]+self.rect.height//2
        self.mask = pygame.mask.from_surface(self.image)
        self.damage = MB["flamen"].damage
        self.dmgType = MB["flamen"].dmgType
        self.onlayer = int(layer)
        self.push = 0

        self.ctr = pos
        self.cnt = cnt      # 预警倒计时
        self.chargeList = []
        self.snd = pygame.mixer.Sound("audio/priest/hit.wav")
    
    def update(self, delay, sideWalls, downWalls, keyLine, sprites, canvas, bg_size):
        # 蓄力阶段
        if self.cnt>0:
            self.cnt -= 1
            if random()<0.3:      # 某概率添加新粒子
                r = choice( [3,4,5] )
                XRange = list( range(self.ctr[0]-50,self.ctr[0]-30) ) + list( range(self.ctr[0]+30,self.ctr[0]+50) )
                YRange = list( range(self.ctr[1]-50,self.ctr[1]-30) ) + list( range(self.ctr[1]+30,self.ctr[1]+50) )
                pos = [ choice( XRange ), choice( YRange ) ]
                color = choice( [(210,255,210,240),(170,255,170,240),(110,150,110,240)] )
                self.chargeList.append( (r, pos, color) )
        # 下落阶段
        else:
            self.rect.bottom += 4
            canvas.addTrails( [3,5,7], [18,20,24], (20,220,60,240), getPos(self, 0.3+random()*0.4, 0.3+random()*0.4) )
            if not delay%(DMG_FREQ//2):
                if cldList( self, sprites ):      # 命中英雄
                    self._explode(canvas)
                self.imgIndx = (self.imgIndx+1) % len(self.imgList)
                self.image = self.imgList[self.imgIndx]
            if pygame.sprite.spritecollide(self, downWalls, False, collide_mask):
                self._explode(canvas)
                self.kill()
                del self
                return
            else:
                # 只有下方的sideWall会被撞击爆炸
                for each in pygame.sprite.spritecollide(self, sideWalls, False, collide_mask):
                    if each.category=="sideWall" and each.coord[1]<=self.onlayer:
                        self._explode(canvas)
                        self.kill()
                        del self
                        return
            if ( self.rect.top >= keyLine ):    # 只有大于检查，因此只有初始行之下的砖块会与之碰撞
                self.onlayer = max(self.onlayer-2, -1)

    def _explode(self, canvas):
        self.snd.play(0)
        canvas.addWaves( getPos(self, 0.5, 0.5), (60,240,80,240), 30, 15 )
    
    def paint(self, surface):
        if self.cnt>0:
            for each in self.chargeList:  # 绘制并移动粒子
                pygame.draw.circle( surface, each[2], each[1], each[0] )  # 充能粒子
                each[1][0] += (self.ctr[0]-each[1][0]) // 8
                each[1][1] += (self.ctr[1]-each[1][1]) // 8
            pygame.draw.circle( surface, (100,240,100), self.ctr, min(60-self.cnt, 30) )   # 聚能中心
        else:
            surface.blit( self.image, self.rect )

# -----------------------------------
class Assassin(Monster):
    imgLib = None
    shadLib = None
    dashSnd = None
    cldSnd = None

    def __init__(self, XRange, y, onlayer, sideGroup):
        # calculate its position
        if not self.imgLib:
            Assassin.imgLib = {
                "wait": createImgList("image/stg7/assassin0.png"),
                "prepare": createImgList("image/stg7/assassin1.png"),
                "dash": createImgList("image/stg7/assassinAtt.png")
            }
            Assassin.shadLib = getShadLib(Assassin.imgLib)
            Assassin.dashSnd = pygame.mixer.Sound("audio/assassinDash.wav")
            Assassin.cldSnd = pygame.mixer.Sound("audio/assassinCld.wav")
        
        # Search both sidewalls of the given layer
        layerwall = []
        while True:
            for sideWall in sideGroup:
                if sideWall.coord[1] == int(onlayer):
                    layerwall.append(sideWall)
            # when layerwall is empty, adjust the layer to lower level and find again
            # (will finally find one because the lowest 10 layers surely have )
            if layerwall:
                break
            else:
                onlayer = int(onlayer)-2
        wall = choice(layerwall)
        self.XRange = XRange
        Monster.__init__(self, "assassin", (250,0,0,240), 4, 1, onlayer, sideGroup)

        # initialize the sprite
        self._reset()
        self.setImg(self.status,0)
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        if wall.coord[0] == 0:  # left side wall
            self.direction = "right"
            self.rect.left = wall.rect.right
        else:
            self.direction = "left"
            self.rect.right = wall.rect.left
        self.rect.bottom = wall.rect.bottom-4
        self.dashSpd = 10
        self.tgt = None
        self.rectList = []  # stack

    def move(self, delay, sprites, YRange, spurtCanvas):
        self.checkHitBack(obstacle=True)
        self.setImg(self.status)
        if self.status == "wait":
            if len(self.rectList)>0:
                self.rectList.pop(0)
            # going to prepare mode
            self.coolDown -= 1
            if self.coolDown == 0:
                self.status = "prepare"
                self.coolDown = 38
                # find tgt and determine speed
                self.tgt = choice(sprites)
                ctr_a = getPos(self.tgt)
                ctr_b = getPos(self)
                # determine x speed
                if self.direction == "right":
                    self.speed[0] = self.dashSpd
                    self.push = self.pushList[1]
                else:
                    self.speed[0] = -self.dashSpd
                    self.push = self.pushList[0]
                # Draft a y speed according to hero's position
                time1 = round( abs(ctr_a[0]-ctr_b[0]) / self.dashSpd )
                if time1==0:
                    time1 = 1
                self.speed[1] = round( (ctr_a[1]-ctr_b[1]) / time1 )
                # Adjust y speed to reasonable range
                time2 = (self.XRange[1]-self.XRange[0]) / self.dashSpd
                # y速度压缩到[-6, 6]
                if self.speed[1]>6:
                    self.speed[1] = 6
                elif self.speed[1]<-6:
                    self.speed[1] = -6
                # 保证竖直位移不超出范围，否则循环调整。NOTE：YRange[0]是塔楼最低，但像素值最大
                while not ( YRange[1]+80 < ctr_b[1] + time2*self.speed[1] < YRange[0]-80 ): 
                    if self.speed[1] > 0:
                        self.speed[1] -= 1
                    elif self.speed[1] < 0:
                        self.speed[1] += 1
                    else:
                        break
        elif self.status == "prepare":
            # going to dash mode
            self.coolDown -= 1
            if self.coolDown == 0:
                self.dashSnd.play(0)
                self.status = "dash"
                spurtCanvas.addSpatters( 6, [2,3,4], [10,11,12], (240,240,240), getPos(self,0.5,0.6) )
        else:
            # DASHING: add shad
            spurtCanvas.addTrails( [1,2,3], [18,20,22], (240,240,240), getPos(self, 0.5, 0.5) )
            self.rectList.append(self.rect.copy())
            if len(self.rectList)>6:
                self.rectList.pop(0)
            # move
            self.rect.left += self.speed[0]
            self.rect.top += self.speed[1]
            # when dashing, check collision with hero.
            if not delay%DMG_FREQ:
                cldList( self, sprites )
            # check stop.
            if (self.direction=="left" and self.rect.left<self.XRange[0]) or (self.direction=="right" and self.rect.right>self.XRange[1]):
                self.cldSnd.play(0)
                if self.direction=="right":
                    self.direction = "left"
                    self.rect.right = self.XRange[1]
                    spurtCanvas.addSpatters( 8, [2,3,4], [10,11,12], (240,240,240), getPos(self,1,0.6) )
                else:
                    self.direction = "right"
                    self.rect.left = self.XRange[0]
                    spurtCanvas.addSpatters( 8, [2,3,4], [10,11,12], (240,240,240), getPos(self,0,0.6) )
                self._reset()
    
    def _reset(self):
        self.status = "wait"    # wait, prepare, dash
        self.speed = [0,0]
        self.coolDown = randint(20,120)
        
    def paint(self, surface):
        # 画残影
        for rect in self.rectList:
            surface.blit(self.shad, rect)
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 8
        surface.blit(self.shad, shadRect)
        surface.blit( self.image, self.rect )
        # 画打击阴影
        if self.hitBack:
            surface.blit( self.shad, self.rect )

    def level(self, dist):
        self.rect.left += dist
        self.XRange = (self.XRange[0]+dist, self.XRange[1]+dist)

# -----------------------------------
class Chicheng(Boss):

    def __init__(self, groupList, onlayer, font):
        # initialize the sprite
        Boss.__init__(self, font, "Chicheng", (255,0,0,240), 6, 4, onlayer)
        self.onlayer = int(onlayer)
        self.initLayer(groupList)
        self.imgLib = {
            "body": createImgList("image/stg7/ccBody.png"),
            "jump": createImgList("image/stg7/ccJump.png"),
            "knock": createImgList("image/stg7/ccKnock.png")
        }
        self.shadLib = getShadLib(self.imgLib)
        # ----- body part (the core of General Chicheng) ------
        self.setImg("body")
        self.mask = pygame.mask.from_surface(self.image)
        # calculate its position
        self.rect = self.image.get_rect()
        self.rect.left = self.initPos[0]-self.rect.width//2
        self.rect.bottom = self.initPos[1]          
        self.alterSpeed( choice( [-1, 1] ) )
        # ------------- Cloak part ----------------
        self.cloakLeft = [ load("image/stg7/ccCloak0.png").convert_alpha(), load("image/stg7/ccCloak1.png").convert_alpha() ]
        self.cloakRight = [ flip(self.cloakLeft[0], True, False), flip(self.cloakLeft[1], True, False) ]
        self.cloakR = { "left":[ (0.7,0.64), (0.7,0.64) ], "right":[ (0.3,0.64), (0.3,0.64) ] }
        self.cloak = Ajunction( self.cloakLeft[0], getPos(self, self.cloakR[self.direction][0][0], self.cloakR[self.direction][0][1]) )
        self.cloakIndx = 0
        # -------------- weapon part ---------------
        self.weaponLeft = [ load("image/stg7/ccWeapon.png").convert_alpha(), load("image/stg7/ccWeaponJump.png").convert_alpha(), load("image/stg7/ccWeapon.png").convert_alpha() ]
        self.weaponRight = [ flip(self.weaponLeft[0], True, False), flip(self.weaponLeft[1], True, False), flip(self.weaponLeft[2], True, False) ]
        self.weaponR = { "left":[ (0.3,0.84), (0.7,0.4), (0,0.86) ], "right":[ (0.7,0.84), (0.3,0.4), (1,0.86) ] }
        self.weapon = Ajunction( self.weaponLeft[0], getPos(self, self.weaponR[self.direction][0][0], self.weaponR[self.direction][0][1]) )
        self.weaponIndx = 0
        self.weapon.damage = self.damage
        self.weapon.dmgType = self.dmgType
        self.weapon.push = self.push
        # ----------- other attributes -------------------------
        self.cnt = 300      # count for the loop of shift position
        self.alarmTime = 0
        self.knockCnt = 0
        self.dealt = False
        self.combo = 0
        self.mockSnd = pygame.mixer.Sound("audio/chichengMock.wav")
        self.knockSnd = pygame.mixer.Sound("audio/chichengKnock.wav")
        self.threatSnd1 = pygame.mixer.Sound("audio/ccSilent.wav")
        self.jumping = False
        # ---------- silent particle --------------------------
        # [pos, speed, tgtRect, tgthero]
        self.parti = None

    def move(self, sprites, canvas, groupList, knock, GRAVITY):
        self.checkHitBack()
        self._tipPosition(canvas)
        # when knockcnt>0, dealing damage
        if self.knockCnt>0:
            self.knockCnt -= 1
            if not self.dealt:
                if cldList(self, sprites) or cldList(self.weapon, sprites):
                    self.dealt = True
        else:
            # knockCnt = 0的情况，可能的状态有很多
            if knock:         # 刚刚落地瞬间，deal damage
                self.setImg("knock")
                self.weaponIndx = 2
                self.knockCnt = 18
                self.dealt = False
                self.push = self.pushList[0] if self.direction=="left" else self.pushList[1]
                for i in (0.1,0.4,0.6,0.9):
                    canvas.addSpatters(randint(2,6), [4,6,8], [28,32,36], (40,30,30,200), getPos(self, i, 0.9), False)
            elif self.combo>0 and not self.jumping:
                self.takeOff(sprites, groupList, GRAVITY)
                self.combo -= 1
            elif self.jumping:    # 跳跃中
                self.setImg("jump")
                self.weaponIndx = 1
            else:       # 落地完成,正常态
                self.setImg("body")
                self.weaponIndx = 0
                # Randomly implement silent paritcle
                if not self.parti and not self.cnt%5 and random()<0.05:
                    self.threatSnd1.play(0)
                    tgts = [hero for hero in sprites if hero.category=="hero"]
                    tgt_hero = choice(tgts)
                    rect = tgt_hero.slot.slotDic["brand"][1]
                    startPos = getPos(self,0.5,0.5)
                    finalPos = [rect.left+rect.width//2, rect.top+rect.height//2]
                    speedX = round( (finalPos[0] - startPos[0]) / 40 )
                    speedY = round( (finalPos[1] - startPos[1]) / 40 )
                    self.parti = [startPos, (speedX, speedY), rect, tgt_hero]
        # about updating images.
        if not (self.cnt % 2):
            # 身体红光
            canvas.addSmoke( 1, (2,4,6), 5, (180,20,20,180), getPos(self,0.5,random()), 60 )
            # 眼睛的光
            for i in (0.4,0.6):
                canvas.addSmoke( 1, (2,4,6), 6, (180,180,20,180), getPos(self,i,0.3), 5, speed=[0,0] )
            if self.direction == "left":
                self.cloak.updateImg( self.cloakLeft[self.cloakIndx] )
                self.weapon.updateImg( self.weaponLeft[self.weaponIndx] )
            elif self.direction == "right":
                self.cloak.updateImg( self.cloakRight[self.cloakIndx] )
                self.weapon.updateImg( self.weaponRight[self.weaponIndx] )
            self.mask = pygame.mask.from_surface(self.image)
            if not self.cnt%6:
                self.cloakIndx = (self.cloakIndx+1) % len(self.cloakLeft)
        self.cloak.updatePos( getPos(self, self.cloakR[self.direction][self.cloakIndx][0], self.cloakR[self.direction][self.cloakIndx][1]) )
        self.weapon.updatePos( getPos(self, self.weaponR[self.direction][self.weaponIndx][0], self.weaponR[self.direction][self.weaponIndx][1]) )
        # count down for rage actions.
        self.cnt -= 1
        if self.cnt<=0:
            self.cnt = randint(300,320)
        if self.jumping:
            self.rect.left += self.speed    # Only consider x here. y is acted by fall()
        elif not self.jumping and self.cnt==240:
            self.takeOff(sprites, groupList, GRAVITY)
            self.combo = randint(2,4)
        # move particle if there is one
        if self.parti:
            pos, speed, rect, hero = self.parti
            self.parti[0] = (pos[0]+speed[0], pos[1]+speed[1])
            canvas.addTrails( [1,2,3], [14,16,18], (190,30,30,210), self.parti[0] )
            if (rect.left<=self.parti[0][0]<=rect.right) and (rect.top<=self.parti[0][1]<=rect.bottom):
                canvas.addExplosion( [rect.left+rect.width//2, rect.top+rect.height//2], 30, 16, waveColor=(190,30,30,210), spatColor=(190,190,40) )
                hero.arrow = 0
                hero.loading = 0
                del self.parti
                self.parti = None

    def takeOff(self, sprites, groupList, GRAVITY):
        if random()<0.8:
            self.mockSnd.play(0)
        tgt = choice(sprites)
        self.jumping = True
        tgtPos, myPos = getPos(tgt,0.5,1), getPos(self,0.5,1)
        # 目标在下方
        if tgt.onlayer-1<=self.onlayer:
            self.onlayer = tgt.onlayer-1
            self.gravity = -14
            self.alarmTime = self.estimateTime(14, tgtPos[1]-myPos[1], GRAVITY)
        # 否则目标在上方或同行
        else:
            self.onlayer += 2
            self.gravity = -18
            self.alarmTime = self.estimateTime(18, tgtPos[1]-myPos[1], GRAVITY)
        self.initLayer(groupList)
        self.alterSpeed( round( (tgtPos[0]-myPos[0])/self.alarmTime ) )

    def estimateTime(self, upwardSpd, absVertical, GRAVITY):
        absDistY = 0
        for y in range(upwardSpd+1):     # 计算得上升总高度(此过程用时upwardSod减至0)
            absDistY += y
        downY = abs(absVertical) + absDistY  # 下降总位移
        anaSpd = 0
        estTime = upwardSpd
        while downY>0:
            absDistY += anaSpd
            downY -= anaSpd
            anaSpd = min(anaSpd+1, GRAVITY)
            estTime += 1
        return estTime

    def fall(self, keyLine, groupList, GRAVITY):
        if self.gravity<GRAVITY:
            self.gravity += 1
        self.rect.bottom += self.gravity
        if self.gravity<0:      # Still in upward action, don't check fall!
            return
        while ( pygame.sprite.spritecollide(self, self.wallList, False, collide_mask) ):  # 如果和参数中的物体相撞，则尝试纵坐标-1
            self.rect.bottom -= 1
            self.gravity = 0
            if self.jumping:
                self.knockSnd.play(0)
                self.jumping = False
                return "vib"
        if getPos(self, 0, 0.5)[1] > keyLine:
            self.onlayer  = max(self.onlayer-2, -1)
            self.initLayer( groupList )
            # 更新obstacle砖块
            self.renewObstacle(groupList["0"])
                
    def paint(self, screen):
        '''鉴于本对象的构造非常复杂，因此提供一个专门的绘制接口
            给此函数传递一个surface参数，即可在该surface上绘制（blit）完整的本对象'''
        # 画阴影
        shadRect = self.rect.copy()
        shadRect.left -= 12
        screen.blit(self.shad, shadRect)
        # 画本身
        screen.blit( self.weapon.image, self.weapon.rect )
        screen.blit( self.cloak.image, self.cloak.rect )
        screen.blit( self.image, self.rect )
        # 画打击阴影
        if self.hitBack:
            screen.blit( self.shad, self.rect )
        # draw particle 
        if self.parti:
            pygame.draw.circle(screen, (190,30,30), self.parti[0], randint(6,8))
       
    def erase(self):
        self.mockSnd.play(0)
        self.weapon.kill()
        self.cloak.kill()
        del self.weapon, self.cloak
        self.kill()
