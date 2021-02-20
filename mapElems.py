"""
mapElems.py:
Define class for accessories and other elements related to towers,
Such as chests, doors, all sorts of walls, merchant, etc.
"""
import pygame
from random import random, randint, choice

from database import NB, DMG_FREQ, PB
from util import InanimSprite, HPBar, Panel, RichButton
from util import getPos, generateShadow

# =========================================================================
# ============================= Coins & Chests ============================
# =========================================================================
class Coin(InanimSprite):
    imgList = []
    shadList = []
    gemImg = None

    def __init__(self, pos, cnt, speed, tgt, typ="coin"): # 参数color:推荐带上透明度RGBA；参数speed:为一个二元组
        if not self.imgList:
            Coin.imgList = [ pygame.image.load("image/coin"+str(i)+".png").convert_alpha() for i in range(6) ]
            Coin.shadList = [ generateShadow(img) for img in Coin.imgList ]
        
        InanimSprite.__init__(self, "coin")
        self.typ = "coin"
        if typ=="gem":
            self.imgList = [ pygame.image.load("image/gem"+str(i)+".png").convert_alpha() for i in range(4) ]
            self.shadList = [ generateShadow(img) for img in self.imgList ]
            self.typ = "gem"
        elif typ.startswith("stone"):
            tag = typ.split("_")[-1]
            self.imgList = [ pygame.image.load(f"image/runestone/{tag}.png").convert_alpha() ] * 2
            self.shadList = [ generateShadow(self.imgList[0]) ] * 2
            self.typ = "stone"
        
        self.imgIndx = 0
        self.image = self.imgList[self.imgIndx]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.top = pos[1]-self.rect.height//2
        self.cnt = cnt
        self.speed = speed
        self.tgt = tgt
    
    def move(self, delay):
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        if not delay%2:
            self._shiftImg()
        # 若还有cnt，则进行散开移动，且减cnt。
        if self.cnt > 0:
            self.cnt -= 1
        # 否则，该质点进入第二状态，追随self.tgt。
        else:
            # 当和tgt重合，将该点删除。
            if pygame.sprite.collide_mask(self, self.tgt):
                self.tgt.receiveExp(1, self.typ)
                self.kill()
                return True
            myPos = getPos(self, 0.5, 0.5)
            tgtPos = getPos(self.tgt, 0.5, 0.5)
            for i in range(2):
                self.speed[i] = ( tgtPos[i] - myPos[i] ) // 12
                if i==1:
                    continue
                if self.speed[i]>0 and self.speed[i]<=3:
                    self.speed[i] = 4
                elif self.speed[i]<0 and self.speed[i]>=-3:
                    self.speed[i] = -4
    
    def _shiftImg(self):
        prePos = [self.rect.left+self.rect.width//2, self.rect.top+self.rect.height//2]
        self.imgIndx = (self.imgIndx+1) % len(self.imgList)
        self.image = self.imgList[self.imgIndx]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = prePos[0]-self.rect.width//2
        self.rect.top = prePos[1]-self.rect.height//2

    def paint(self, canvas):
        shadRect = self.rect.copy()
        shadRect.left -= 8
        canvas.blit(self.shadList[self.imgIndx], shadRect)
        canvas.blit(self.image, self.rect)

# --------------------------------------
class Chest(InanimSprite):

    # constructor: note that y here should be the bottom point of the supply
    def __init__(self, x, y, contains, coord, bg_size, doubleP, tower):
        InanimSprite.__init__(self, "chest")
        self.image = pygame.image.load(f"image/stg{tower.stg}/chest.png").convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x - self.rect.width//2
        self.rect.bottom = y
        self.shad = generateShadow(self.image)
        self.shadRect = self.rect.copy()
        self.shadRect.left -= 6
        self.coord = coord    # 这里的coord是该chest所在的brick的坐标
        self.contains = contains
        # 根据含有物类别不同，给出不同的数量
        if contains in ["coin","gem"]:
            self.number = randint(2,4)
        elif contains in ["fruit", "loadGlove"]:
            self.number = 2 if random()<doubleP else 1
        else:
            self.number = 1
        self.tgtPos = [0,0]   # 箱内物品打开后飞向的目的地，在open时会确定。
        self.bg_size = bg_size
        self.opened = False
        self.tower = tower
        self.getItemSnd = pygame.mixer.Sound("audio/getItem.wav")

    def interact(self, trigger):
        self.open(trigger)

    def open(self, hero):
        if self.opened:    # 打开后仍保持此类在hero的checkList中，只是opened标记为True时，此函数不会执行
            return False
        if not hero.onlayer==self.coord[1]+1: # 如果hero和chest不在同一行，不允许打开。
            return False
        self.getItemSnd.play(0)
        self.opened = True
        hero.checkList.remove(self)
        trPos = [ self.rect.left + self.rect.width//2, self.rect.bottom ]  # 为保证图片位置正确，临时存储之前的位置信息
        self.image = pygame.image.load(f"image/stg{self.tower.stg}/chestOpen.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.left = trPos[0]-self.rect.width//2
        self.rect.bottom = trPos[1]
        self.shad = generateShadow(self.image)
        self.shadRect = self.rect.copy()
        self.shadRect.left -= 6
        hero.eventList.append("chest")
        # 修改相应的hero属性数量，同时设定substance的目的坐标，确定substance的图片
        if self.contains in ["coin","gem"]:
            self.tower.addCoins(self.number, getPos(self,0.5,0.4), hero, item=self.contains)
            return True
        else:
            hero.bagpack.incItem(self.contains, self.number)
            subsImg = hero.bagpack.readItemByName( self.contains )[1]
            # deal inside substance
            substance = ChestContent(self.contains, subsImg, self.number, getPos(self,0.5,0.8), hero.slot.slotDic["bag"][1])
            hero.eventList.append( substance )
            return True
   
    def lift(self, dist):
        self.rect.bottom += dist
        self.shadRect.bottom += dist

    def level(self, dist):
        self.rect.left += dist
        self.shadRect.left += dist

    def paint(self, surface):
        surface.blit(self.shad, self.shadRect)
        surface.blit(self.image, self.rect)

class ChestContent(pygame.sprite.Sprite):
    category = "chestContent"

    def __init__(self, name, image, number, ctr, tgtRect, spacing=10):
        """Produce a list of imgs based on img. Their rects are arranged horrizontally with wanted spacing."""
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.mask = pygame.mask.from_surface(self.image)
        self.rectList = []
        startX = ctr[0]-spacing*(number-1)//2
        for i in range(0, number):
            rect = self.image.get_rect().copy()
            rect.left = startX +i*spacing -rect.width//2
            rect.top = ctr[1] -rect.height//2
            self.rectList.append( rect )
        self.name = name
        self.tgtRect = tgtRect
        self.reached = False
        self.showCnt = 12
    
    def update(self, surface):
        if self.reached:
            self.kill()
            return False
        if self.showCnt:
            for each in self.rectList:
                each.bottom -= min(self.showCnt, 4)
                surface.blit( self.image, each )
            self.showCnt -= 1
        else:
            for each in self.rectList:
                spdX = (self.tgtRect.left+self.tgtRect.width//2-each.left) // 20
                if spdX>0 and spdX<=3:
                    spdX = 4
                elif spdX<0 and spdX>=-3:
                    spdX = -4
                
                spdY = (self.tgtRect.top+self.tgtRect.height//2-each.top) // 20
                if spdX>0 and spdX<=3:
                    spdX = 4
                elif spdX<0 and spdX>=-3:
                    spdX = -4
                
                each.left += spdX
                each.bottom += spdY
                surface.blit( self.image, each )
                if each.colliderect(self.tgtRect):
                #if spdX == 0 and spdY == 0:
                    self.rectList.remove(each)
            if len(self.rectList)<=0:
                self.reached = True
    
    def lift(self, dist):
        for each in self.rectList:
            each.top += dist
    
    def level(self, dist):
        for each in self.rectList:
            each.left += dist


# =========================================================================
# ================================== Walls ================================
# =========================================================================
class Wall(InanimSprite):
    def __init__(self, x, y, cate, stg, coord):
        InanimSprite.__init__(self, cate)
        src = "image/stg"+ str(stg) + "/" + cate + ".png"
        self.image = pygame.image.load(src).convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x
        self.rect.top = y
        self.coord = coord
        # hollowWall拥有额外的close标签
        if self.category=="hollowWall":
            if self.coord[0]<=0:
                self.close="left"
            else:
                self.close="right"

    def paintDecor(self, surface):
        pass

# -----------------------------------------------------
class SpecialWall(Wall):
    def __init__(self, x, y, stg, coord):
        Wall.__init__(self, x, y, "specialWall", stg, coord)
        self.elem = None
        # 这里的special Elements的坐标都是其所在的wall的坐标
        if stg == 1:
            self.elem = BlockFire(x+self.rect.width//2, y, coord)
        elif stg == 2:
            self.elem = BlockStone(x+self.rect.width//2, y, coord)
        elif stg == 3:
            self.clpCnt = 0  # 等待英雄的踩踏中
            self.oriImage = self.image
            self.oriPos = [0,0]
            self.sizeList = []
            rList = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1)
            for i in range(0,10):
                self.sizeList.append( ( int(self.rect.width*rList[i]), int(self.rect.height*rList[i]) ) )
            self.interact = self._interact_stg3
            self.level = self._clpLevel
            self.lift = self._clpLift
        elif stg == 4:
            self.elem = BlockOoze(x+self.rect.width//2, y+4, coord)
        elif stg == 5:
            self.interact = self._interact_stg5
        elif stg == 6:
            self.elem = Fan(x+self.rect.width//2, y+self.rect.width, coord)
        elif stg == 7:
            self.elem = Stabber(x+self.rect.width//2, y, coord)
        elif stg == 0:
            self.tower = None
        
    #def __del__(self):
    #    print("I'm deleted.")
    
    def interact(self, trigger):
        return

    def _interact_stg3(self, trigger):
        self.clpCnt += 1

    def _interact_stg5(self, trigger):
        trigger.moveX(0, trigger.status)

    def erase(self):
        if self.elem:
            self.elem.kill()
        self.kill()
        del self

    def collapse(self, GRAVITY, canvas):
        if self.clpCnt > 0: # >0表示正在下落
            if self.clpCnt==1:
                self.oriPos = [self.rect.left+self.rect.width//2, self.rect.top]
            self.rect.bottom += min(self.clpCnt, GRAVITY)
            canvas.addTrails( [1,2,3], [16,18,20], (30,30,30,230), getPos(self, choice([0.1,0.9]), 0.8) )
            self.clpCnt += 1
            if self.clpCnt >= 100:
                self.clpCnt = - 10
        elif self.clpCnt < 0: # <0表示在倒计时
            if self.clpCnt>=-10:
                self.image = pygame.transform.smoothscale( self.oriImage, self.sizeList[self.clpCnt+10] )
                self.rect = self.image.get_rect()
                self.rect.left = self.oriPos[0] - self.rect.width//2
                self.rect.top = self.oriPos[1]
            self.clpCnt += 1
    
    def _clpLift(self, dist):
        self.rect.bottom += dist
        self.oriPos[1] += dist

    def _clpLevel(self, dist):
        self.rect.left += dist
        self.oriPos[0] += dist

# -----------------------------------------------------
class WebWall(Wall):
    def __init__(self, x, y, stg, coord, fade=False):
        Wall.__init__(self, x, y, "webWall", stg, coord)
        self.oriImage = self.image
        self.imgBroken = pygame.image.load("image/stg2/webWallBroken.png").convert_alpha()
        self.imgPulled = pygame.image.load("image/stg2/webPulled.png").convert_alpha()
        self.valid = True
        self.ctr = [self.rect.left+self.rect.width//2, self.rect.top+self.rect.height//3]  # 黏贴点
        self.bldColor = (255,255,255,255)
        self.onlayer = coord[1]
        self.coin = 0
        self.fade = fade
        self.fadeCnt = 0
        self.health = 0
    
    # 对于英雄来说，被击穿后本web依然会挂在hero的trapper变量上。但仅仅trap效果生效，而没有了重力的限制，因此英雄会下落，造成一种释放开的错觉。
    def stick(self, sprites):
        if not self.valid:  # 已被打破，则失效
            if self.fadeCnt>0:
                self.fadeCnt -= 1
                if self.fadeCnt<=0:
                    self.kill()
            return False
        for hero in sprites:
            if pygame.sprite.collide_mask(self, hero):
                self.image = self.imgPulled
                hero.trapper = self
                if hero.gravity>1:
                    hero.gravity -= 2
                return True
        self.image = self.oriImage
    
    def stun(self, duration):
        pass

    def hitted(self, damage, pushed, dmgType):
        if self.fade:
            self.fadeCnt = 60
        self.valid = False
        self.image = self.imgBroken

    def drawHealth(self, surface):
        pass

    def lift(self, dist):
        self.rect.bottom += dist
        self.ctr[1]

    def level(self, dist):
        self.rect.left += dist
        self.ctr[0] += dist

# -----------------------------------------------------
class SideWall(Wall):
    def __init__(self, x, y, stg, coord, decor=True):
        Wall.__init__(self, x, y, "sideWall", stg, coord)
        self.decor = None
        # 墙壁的装饰：（新设的平台无装饰）
        if decor and random()<0.18:
            self.decor = Decoration( (x+14,x+58), y+62, "sideDecor", stg, (x,y), None, 0 )
    
    def paintDecor(self, surface):
        if self.decor:
            self.decor.paint(surface)

    def erase(self):
        if self.decor:
            self.decor.kill()
        self.kill()
        del self
    
    def lift(self, dist):
        self.rect.bottom += dist
        if self.decor:
            self.decor.lift(dist)

    def level(self, dist):
        self.rect.left += dist
        if self.decor:
            self.decor.level(dist)

# -----------------------------------------------------
class Decoration(InanimSprite):
    imgList = []
    freq = 5   # 图片切换频率，默认为5此刷新切换一次。

    # constructor: If you want a door or hostage, x should be an integer; If you want decorations, x should be a pair of integers (tuple).
    # cate could be either "lineDecor" or "sideDecor"; options should be like ("A", "B", "C"...)
    def __init__(self, x, y, cate, stg, coord, options, freq):
        InanimSprite.__init__(self, cate)
        self.t = 0
        if freq==0:
            self.freq = 5  # 0表示使用默认的5
        else:
            self.freq = freq
        if cate == "lineDecor":
            if stg==4:
                x = [x[0]+6, x[1]-6]
            # 有多种装饰可供选择。尾号为A或B……从options参数中选择一个。
            tail = choice( options )
            self.imgList = [ pygame.image.load("image/stg"+str(stg)+"/"+cate+tail+"0.png").convert_alpha(), pygame.image.load("image/stg"+str(stg)+"/"+cate+tail+"1.png").convert_alpha(), \
                pygame.image.load("image/stg"+str(stg)+"/"+cate+tail+"2.png").convert_alpha(), pygame.image.load("image/stg"+str(stg)+"/"+cate+tail+"1.png").convert_alpha() ]
        elif cate == "sideDecor":
            if stg==4:
                x = [x[0]-14+36, x[1]-58+36]
            self.imgList = [ pygame.image.load("image/stg"+str(stg)+"/"+cate+"0.png").convert_alpha(), pygame.image.load("image/stg"+str(stg)+"/"+cate+"1.png").convert_alpha(), \
                pygame.image.load("image/stg"+str(stg)+"/"+cate+"2.png").convert_alpha(), pygame.image.load("image/stg"+str(stg)+"/"+cate+"1.png").convert_alpha() ]

        # 有一半的可能性会方向相反
        if random()>=0.5:
            self.imgList = [ pygame.transform.flip(self.imgList[0], True, False), pygame.transform.flip(self.imgList[1], True, False),
                pygame.transform.flip(self.imgList[2], True, False), pygame.transform.flip(self.imgList[3], True, False) ]
            x = x[1]
        else:
            x = x[0]
        self.image = self.imgList[0]
        self.indx = 0
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x - self.rect.width//2
        self.rect.top = y - self.rect.height
        self.coord = coord

    def paint(self, surface):
        surface.blit(self.image, self.rect)

        self.t = (self.t + 1) % self.freq
        if not self.t:
            tx = self.rect.left
            ty = self.rect.bottom
            self.indx = ( self.indx+1 ) % len(self.imgList)
            self.image = self.imgList[self.indx]
            self.rect = self.image.get_rect()
            self.rect.left = tx
            self.rect.bottom = ty


# =========================================================================
# ======== Door, merchant & similar sorts of interactable items ===========
# =========================================================================
class Porter(InanimSprite):
    def __init__(self, x, y, cate, stg, font, lgg):
        InanimSprite.__init__(self, cate)
        self.t = 0
        self.lumi = 0
        self.font = font
        self.lgg = lgg
        self.indx = 0
        self.msgList = []
        if cate == "hostage":
            hosMap = {1:"princess", 2:"prince", 3:"wizard", 4:"huntress", 5:"priest", 6:"king"}
            self.imgList = [ pygame.image.load(f"image/{hosMap[stg]}/heroLeft0.png").convert_alpha() ]
            self.shadList = [ generateShadow(img) for img in self.imgList ]
            self.fitImg(x, y)
        elif cate == "statue":
            self.imgList = [ pygame.image.load("image/stg0/statue.png").convert_alpha() ]
            self.shadList = [ generateShadow(img) for img in self.imgList ]
            self.brokeImg = pygame.image.load("image/stg0/statueBroken.png")
            self.brokeImgShad = generateShadow(self.brokeImg)
            self.fitImg(x, y)
        elif cate == "defenseTower":
            self.imgList = [ pygame.image.load("image/props/defenseTower.png").convert_alpha() ]
            self.shadList = [ generateShadow(img) for img in self.imgList ]
            self.fitImg(x, y)
    
    def fitImg(self, x, y):
        self.image = self.imgList[self.indx]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x - self.rect.width//2
        self.rect.bottom = y

    def paint(self, surface):
        self.t = (self.t + 1) % 5
        if not self.t:
            self.indx = ( self.indx+1 ) % len(self.imgList)
            self.fitImg( self.rect.left + self.rect.width//2, self.rect.bottom )
        shadRect = self.rect.copy()
        shadRect.left -= 4
        surface.blit(self.shadList[self.indx], shadRect)
        surface.blit(self.image, self.rect)
        # 显示消息
        for msg in self.msgList:
            txt = self.font[self.lgg].render( msg[self.lgg], True, (255,255,255) )
            rect = txt.get_rect()
            rect.left = self.rect.left+self.rect.width//2-rect.width//2
            rect.bottom = self.rect.bottom - 90
            bg = pygame.Surface( (rect.width, rect.height) ).convert_alpha()
            bg.fill( (0,0,0,180) )
            surface.blit( bg, rect )
            surface.blit( txt, rect )
            self.msgList.remove(msg)
    
    def erase(self):
        self.kill()
        del self

    def interact(self, trigger):
        self.conversation( trigger.keyDic["jumpKey"] )

    def conversation(self, key=0):
        if self.category=="hostage":
            keyNm = "["+pygame.key.name(key).upper()+"]"
            self.msgList.append( ("Press "+keyNm+" Key to take me.","按"+keyNm+"键将我加入队伍。") )

# ------------------------------
class Door(Porter):
    def __init__(self, x, y, cate, stg, font, lgg):
        Porter.__init__(self, x, y, cate, stg, font, lgg)
        self.imgList = [ pygame.image.load("image/stg"+str(stg)+"/doorLocked0.png").convert_alpha(), pygame.image.load("image/stg"+str(stg)+"/doorLocked1.png").convert_alpha() ]
        self.unlockList = [ pygame.image.load("image/stg"+str(stg)+"/door0.png").convert_alpha(), pygame.image.load("image/stg"+str(stg)+"/door1.png").convert_alpha() ]
        self.shadList = [ generateShadow(img) for img in self.imgList ]
        self.fitImg(x, y)
        self.locked = True

    def unlock(self):
        if self.locked:
            self.locked = False
            self.imgList = self.unlockList
    
    def conversation(self, key=0):
        if self.locked:
            self.msgList.append( ("Please eliminate all Area Keepers.","请消灭所有区域守卫。") )
        else:
            if self.category=="exit":
                self.msgList.append( ("Bring hostage here to escape.","将人质引导至这里逃离塔楼。") )
            elif self.category=="door":
                self.msgList.append( (f"Press JUMP Key to enter.","按跳跃键进入。") )

# ------------------------------
class Merchant(Porter):
    def __init__(self, x, y, stg, font, lgg, context):
        ''' context could be 'adventure' or 'endless'. '''
        Porter.__init__(self, x, y, "merchant", stg, font, lgg)
        self.imgList = [ pygame.image.load("image/merchant.png").convert_alpha() ]
        self.shadList = [ generateShadow(img) for img in self.imgList ]
        self.fitImg(x, y)
        self.goods = {-1:None, 0:None, 1:None}  #
        # 根据所在环境设置贩卖的商品内容
        if context=="adventure":
            self.offerDic = {"loadGlove":4, "fruit":24, "spec":30, "ammo":45}
            self.iconList = {"loadGlove":pygame.image.load("image/props/loadGlove.png").convert_alpha(), 
                            "ammo":pygame.image.load("image/props/supAmmo.png").convert_alpha()}
        elif context=="endless":
            self.offerDic = {"loadGlove":4, "fruit":24, "spec":30, "servant":32, "defenseTower":36, "ammo":45}
            self.iconList = {"loadGlove":pygame.image.load("image/props/loadGlove.png").convert_alpha(), 
                            "ammo":pygame.image.load("image/props/supAmmo.png").convert_alpha(), 
                            "servant":pygame.image.load("image/servant/servantLeft0.png").convert_alpha(),
                            "defenseTower":pygame.image.load("image/props/defenseTower.png").convert_alpha()}
        self.offerList = [each for each in self.offerDic]
        self.refreshCost = 2
        self.coinIcon = pygame.transform.smoothscale( pygame.image.load("image/coin0.png"), (22, 24) )
        self.sellSnd = pygame.mixer.Sound("audio/coin.wav")
        self.helloSnd = pygame.mixer.Sound("audio/merchantC.wav")
        # pos parameters.
        self.subW = 116
        self.offsetX = -60
        self.lumi = 120
    
    def initWindow(self, keyDic):
        # Create the Basic Frame for shopping window.
        w, h = (540, 340)
        self.shopWindow = Panel( w, h, self.font, title=("Tour Merchant","旅行商人"))
        self.addSymm( pygame.image.load("image/merchantSlot.png").convert_alpha(), 0, 40 )

        shoppingTip = {
            "left": "["+ pygame.key.name(keyDic["leftKey"]).upper() +"]",
            "right": "["+ pygame.key.name(keyDic["rightKey"]).upper() +"]",
            "purchase": "["+ pygame.key.name(keyDic["itemKey"]).upper() +"]",
            "leave": "["+ pygame.key.name(keyDic["shootKey"]).upper() +"]",
            "refresh": "["+ pygame.key.name(keyDic["bagKey"]).upper() +"]"
        }
        self.addTXT( (shoppingTip["left"]+" Left",shoppingTip["left"]+"左选"), (254,254,254), -165, 140 )
        self.addTXT( (shoppingTip["right"]+" Right",shoppingTip["right"]+"右选"), (254,254,254), -70, 140 )
        self.addTXT( (shoppingTip["purchase"]+" Purchase",shoppingTip["purchase"]+"购买"), (254,254,254), 20, 140 )
        self.addTXT( (f'{shoppingTip["refresh"]} Refresh -{self.refreshCost} coins',f'{shoppingTip["refresh"]}刷新 -{self.refreshCost}金币'), (254,254,254), 145, 140 )

    def sell(self, indx, buyer, canvas):
        gd = self.goods[indx]
        if gd.cost<=buyer.coins:  # enough coin
            self.sellSnd.play(0)
            buyer.coins -= gd.cost
            self.goods[indx] = None
            half_size = [ param//2 for param in canvas.canvas.get_size() ]
            if gd.tag=="ammo":
                buyer.arrowCnt += gd.number
                tgtRect = buyer.slot.slotDic["brand"][1]
                subsImg = self.iconList["ammo"]
            elif gd.tag=="servant":
                return "servant"
            else:
                buyer.bagpack.incItem( gd.tag, gd.number )
                tgtRect = buyer.slot.slotDic["bag"][1]
                subsImg = buyer.bagpack.bagImgList[gd.tag]
            return ChestContent( gd.tag, subsImg, gd.number, half_size, tgtRect )
        else:
            return False
    
    def updateGoods(self, stg, hero, canvas=None):
        for i in self.goods:
            # If it has goods, jump it. Only handle vacant poistions.
            if self.goods[i]:
                continue

            if canvas:
                cx, cy = canvas.canvas.get_size()
                ctrPos = (cx//2+self.subW*i+self.offsetX, cy//2-120)
                canvas.addSpatters(8, [3,4,5], (24,30,32), (255,250,210,250), ctrPos, True)
            
            onshelf = [ self.goods[i].tag for i in self.goods if self.goods[i] ]
            pool = self.offerList.copy()

            while True:
                cate = choice(pool)
                if cate in ["fruit","defenseTower"]:
                    img = hero.bagpack.readItemByName( cate )[1]
                    tag = cate
                elif cate in ["loadGlove","ammo","servant"]:
                    img = self.iconList[cate]
                    tag = cate
                elif cate=="spec":
                    tag = choice( PB[stg] )
                    img = hero.bagpack.readItemByName( tag )[1]
                
                if (tag in onshelf) and (cate in pool):
                    pool.remove(cate)
                else:
                    cost = str( self.offerDic[cate] )
                    button = RichButton(self.subW, self.subW, img, {"default":[cost]*2}, "default", self.font, rgba=(210,200,180,160), align='vertical')
                    button.tag = tag
                    button.cost = int(cost)
                    button.number = 1
                    self.goods[i] = button
                    break
    
    def conversation(self, key=0):
        #keyNm = "["+pygame.key.name(key).upper()+"]"
        self.msgList.append( ("Wanna buy anything? Press Key [Enter].", "想买点什么？[Enter]键交互。") )

    def paint(self, surface):
        self.t = (self.t + 1) % 5
        if not self.t:
            self.indx = ( self.indx+1 ) % len(self.imgList)
            self.fitImg( self.rect.left + self.rect.width//2, self.rect.bottom )
        shadRect = self.rect.copy()
        shadRect.left -= 4
        surface.blit(self.shadList[self.indx], shadRect)
        surface.blit(self.image, self.rect)
        # 显示消息
        for msg in self.msgList:
            txt = self.font[self.lgg].render( msg[self.lgg], True, (255,255,255) )
            rect = txt.get_rect()
            rect.left = self.rect.left+self.rect.width//2-rect.width//2
            rect.bottom = self.rect.bottom - 90
            bg = pygame.Surface( (rect.width, rect.height) ).convert_alpha()
            bg.fill( (0,0,0,180) )
            surface.blit( bg, rect )
            surface.blit( txt, rect )
            self.msgList.remove(msg)
    
    def renderWindow(self, base, stg, buyNum, hero, infoDic, addSymm, addTXT, canvas):
        # to ensure have goods
        self.updateGoods(stg, hero, canvas=canvas)

        baseW, baseH = base.get_size()
        self.shopWindow.paint( base, baseW//2, baseH//2-90, (0,0) )
        for i in range(-1,2):
            x, y = baseW//2+(self.subW+5)*i+self.offsetX, baseH//2-130
            if i==buyNum:
                self.goods[i].add_prompt(hero.bagpack.itemDic[self.goods[i].tag])
                self.goods[i].paint(base, x, y, (x, y))
            else:
                self.goods[i].paint(base, x, y, (0, 0))
            addSymm( self.coinIcon, self.subW*i-25+self.offsetX, -100 )
        # Draw directions.
        curGd = self.goods[buyNum].tag
        if curGd in infoDic:
            explan = infoDic[curGd]
            topAlign = -50
            for line in explan:
                addTXT( line, 1, (255,255,255), self.offsetX, topAlign )
                topAlign += 20

    def addSymm(self, surface, x, y):
        '''Surface对象; x,y为正负（偏离屏幕中心点）像素值，确定了图像的中点坐标'''
        rect = surface.get_rect()
        baseW, baseH = self.shopWindow.surf_orig.get_size()
        rect.left = (baseW - rect.width) // 2 + x
        rect.top = (baseH - rect.height) // 2 + y
        self.shopWindow.surf_orig.blit( surface, rect )

    def addTXT(self, txtList, color, x, y):
        '''x,y为正负（偏离屏幕中心点）像素值，y则确定了文字行矩形的中点坐标（居中对齐）。'''
        txt = self.font[self.lgg].render( txtList[self.lgg], True, color )
        rect = txt.get_rect()
        baseW, baseH = self.shopWindow.surf_orig.get_size()
        rect.left = (baseW - rect.width) // 2 + x
        rect.top = (baseH - rect.height) // 2 + y
        self.shopWindow.surf_orig.blit( txt, rect )


# =========================================================================
# ======================= Chapter feature elements ========================
# =========================================================================
# CP1
class BlockFire(InanimSprite):
    def __init__(self, x, y, coord):
        InanimSprite.__init__(self, "blockFire")
        self.imgList = [ pygame.image.load("image/stg1/fw1.png").convert_alpha(), pygame.image.load("image/stg1/fw2.png").convert_alpha(), 
            pygame.image.load("image/stg1/fw3.png").convert_alpha(), pygame.image.load("image/stg1/fw4.png").convert_alpha(), 
            pygame.image.load("image/stg1/fw2.png").convert_alpha() ]
        self.image = self.imgList[0]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x-self.rect.width//2
        self.rect.bottom = y+12
        self.imgIndx = randint(0,len(self.imgList)-1)
        self.coord = coord
        self.damage = NB["blockFire"]["damage"]
    
    def burn(self, delay, sprites, canvas):
        if not (delay%5):
            # add smoke
            smokePos = ( self.rect.left+self.rect.width//2, self.rect.bottom-10 )
            canvas.addSmoke( 2, (2,4,6), 4, (2,2,2,180), smokePos, 30 )
            # alter img
            self.imgIndx = (self.imgIndx+1) % len(self.imgList)
            lft = self.rect.left
            btm = self.rect.bottom
            self.image = self.imgList[self.imgIndx]
            self.rect = self.image.get_rect()
            self.rect.left = lft
            self.rect.bottom = btm
        if not (delay % DMG_FREQ):
            # 只有hero在这一层时才进行hero的重合check，否则无权进行伤害。
            for hero in sprites:
                if hero.onlayer==self.coord[1]+1 and pygame.sprite.collide_mask(self, hero):
                    hero.hitted(self.damage, 0, "fire")

# CP2
class BlockStone(InanimSprite):
    def __init__(self, x, y, coord):
        InanimSprite.__init__(self, "blockStone")
        self.imgList = [ pygame.image.load("image/stg2/blockStone0.png").convert_alpha(), pygame.image.load("image/stg2/blockStone1.png").convert_alpha() ]
        self.image = self.imgList[0]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x-self.rect.width//2
        self.rect.bottom = y
        self.coord = coord
        self.onlayer = coord[1]+1
        self.bldColor = (210,230,230,240)
        self.health = NB["blockStone"]["health"]
        self.manner = NB["blockStone"]["manner"]
        self.coin = 0
    
    def checkExposion(self, canvas):
        if self.health <= 0:
            canvas.addPebbles(self, 4)
            self.kill()

    def stun(self, duration):
        pass

    def hitted(self, damage, pushed, dmgType):
        self.health -= damage
        # 删除自身的权限由checkExposion()实现
        if self.health < 500:
            tmpPos = [self.rect.left, self.rect.bottom]
            self.image = self.imgList[1]
            self.rect = self.image.get_rect()
            self.rect.left = tmpPos[0]
            self.rect.bottom = tmpPos[1]

    def drawHealth(self, surface):
        pass

# CP4
class BlockOoze(InanimSprite):
    def __init__(self, x, y, coord):
        InanimSprite.__init__(self, "blockOoze")
        self.imgList = [ pygame.image.load("image/stg4/blockOoze0.png").convert_alpha(), pygame.image.load("image/stg4/blockOoze1.png").convert_alpha(), pygame.image.load("image/stg4/blockOoze2.png").convert_alpha(), pygame.image.load("image/stg4/blockOoze3.png").convert_alpha() ]
        self.image = self.imgList[0]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x-self.rect.width//2
        self.rect.bottom = y
        self.coord = coord
        self.imgIndx = 0

    def bubble(self, delay, sprites):
        for hero in sprites:
            # 只有hero在这一层且处于此砖上方才进行hero的重合check，否则无权对hero的stuck进行决定。
            if hero.onlayer==self.coord[1]+1 and pygame.sprite.collide_mask(self, hero):
                hero.trapper = self
        if not (delay % 12):
            lft = self.rect.left
            btm = self.rect.bottom
            self.imgIndx = (self.imgIndx + 1) % len(self.imgList)
            self.image = self.imgList[self.imgIndx]
            self.rect = self.image.get_rect()
            self.rect.left = lft
            self.rect.bottom = btm

class House(Porter):
    def __init__(self, x, y, cate, stg, font, lgg):
        self.imgList = [ pygame.image.load("image/stg4/hut.png").convert_alpha() ]
        self.shadList = [ generateShadow(img) for img in self.imgList ]
        Porter.__init__(self, x, y, cate, stg, font, lgg)
        self.fitImg(x, y)

    def chim(self, canvas):
        if not self.t:
            smokePos = getPos(self,0.7,0.04)
            canvas.addSmoke( 1, (6,8,10), 1, (1,1,1,100), smokePos, 5 )

# CP5
class Totem(InanimSprite):
    def __init__(self, category, wall, onlayer):
        InanimSprite.__init__(self, category)
        if category=="healTotem":
            self.themeColor = (255,250,90,120)
            self.heal = NB[category]["heal"]
            self.coolDown = self.cntFull = 130
        elif category=="battleTotem":
            self.themeColor = (255,90,90,120)
            self.coolDown = self.cntFull = 260
            #self.run = self.btRun
        self.image = pygame.image.load(f"image/stg5/{category}.png")
        self.shad = generateShadow( self.image )
        self.lightSurf = generateShadow( self.image, color=self.themeColor )
        self.snd = pygame.mixer.Sound("audio/healing.wav")
        # Monster attri part
        self.health = NB[category]["health"]
        self.bldColor = (255,200,40,240)
        self.coin = 0
        self.onlayer = onlayer
        self.ltCnt = 0
        # initialize the sprite
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = wall.rect.left+wall.rect.width//2-self.rect.width//2
        self.rect.bottom = wall.rect.top

    def checkExposion(self, canvas):
        if self.health <= 0:
            canvas.addPebbles(self, 4, type="metalDebri")
            pygame.mixer.Sound("audio/wizard/hit.wav").play(0)
            self.kill()
    
    def run(self, monsters, spurtCanvas):
        spurtCanvas.addSmoke( 1, (2,4), 5, (255,250,90,240), getPos(self,0.5,random()), 30 )
        # Check highlight
        if self.ltCnt>0:
            self.ltCnt -= 1
        self.coolDown -= 1
        if self.coolDown<=0:
            # 冷却结束，释放治疗。若未找到，则coolDown一直为0
            for mons in monsters:
                if mons.category!="healTotem" and mons.health < mons.full:
                    #self.tgt = mons
                    tracker = Tracker("healLight", getPos(self,0.5,0.1), mons, (255,250,90,240), self.heal)
                    self.snd.play(0)
                    self.coolDown = randint(self.cntFull-10, self.cntFull+10)    # 投递完成，重置冷却时间
                    self.ltCnt = 20
                    return tracker
            self.coolDown = 0

    def paint(self, surface):
        shadRect = self.rect.copy()
        shadRect.left -= 8
        surface.blit(self.shad, shadRect)
        surface.blit(self.image, self.rect)
        if self.ltCnt>0:
            surface.blit(self.lightSurf, self.rect)

    def stun(self, duration):
        pass

    def hitted(self, damage, pushed, dmgType):
        self.health -= damage
        # 删除自身的权限由checkExposion()实现

    def drawHealth(self, surface):
        pass
    
class Tracker(InanimSprite):
    imgList = []
    shadList = []

    def __init__(self, name, pos, tgt, color, heal): # 参数color:推荐带上透明度RGBA；参数speed:为一个二元组
        if name in ["healLight","battleLight"]:
            InanimSprite.__init__(self, "tracker")
            self.image = pygame.image.load(f"image/stg5/{name}.png").convert_alpha()
            if name=="battleLight":
                self.move = self.btMove
        elif name=="defenseLight":
            InanimSprite.__init__(self, "defenseLight")
            self.image = pygame.image.load(f"image/stg0/{name}.png").convert_alpha()
            self.move = self.dfMove
            self.shooter = None
        else:
            return
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = pos[0]-self.rect.width//2
        self.rect.top = pos[1]-self.rect.height//2
        self.color = color
        self.speed = [0,-1]
        self.tgt = tgt
        self.heal = heal
    
    def move(self, spurtCanvas):
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        spurtCanvas.addTrails([5], [16], self.color, getPos(self,0.5,0.5))
        # 追随tgt，调整速度
        tgt_ctr = getPos(self.tgt, 0.5, 0.5)
        my_ctr = getPos(self, 0.5, 0.5)
        self.speed[0] = (tgt_ctr[0] - my_ctr[0]) // 12
        self.speed[1] = (tgt_ctr[1] - my_ctr[1]) // 12
        # 当和tgt重合，将该点删除。
        if pygame.sprite.collide_mask(self, self.tgt):
            self.tgt.recover(self.heal)
            #self.snd.play(0)
            spurtCanvas.addSpatters(6, (2,4,6), (16,18,20), self.color, getPos(self.tgt,0.5,0.5))
            self.kill()
            del self
            return True
    
    def btMove(self, spurtCanvas):
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        spurtCanvas.addTrails([5], [16], self.color, getPos(self,0.5,0.5))
        # 追随tgt，调整速度
        tgt_ctr = getPos(self.tgt, 0.5, 0.5)
        my_ctr = getPos(self, 0.5, 0.5)
        self.speed[0] = (tgt_ctr[0] - my_ctr[0]) // 12
        self.speed[1] = (tgt_ctr[1] - my_ctr[1]) // 12
        # 当和tgt重合，将该点删除。
        if pygame.sprite.collide_mask(self, self.tgt):
            self.tgt.arrow += 1
            spurtCanvas.addSpatters(6, (2,4,6), (16,18,20), self.color, getPos(self.tgt,0.5,0.5))
            #if self.tgt.arrow>self.tgt.arrowCnt:
            #    self.tgt.arrow = self.tgt.arrowCnt
            self.kill()
            del self
            return True

    def dfMove(self, spurtCanvas):
        self.rect.left += self.speed[0]
        self.rect.top += self.speed[1]
        spurtCanvas.addTrails([5], [10], self.color, getPos(self,0.5,0.5))
        # 追随tgt，调整速度
        tgt_ctr = getPos(self.tgt, 0.5, 0.5)
        my_ctr = getPos(self, 0.5, 0.5)
        self.speed[0] = (tgt_ctr[0] - my_ctr[0]) // 12
        self.speed[1] = (tgt_ctr[1] - my_ctr[1]) // 12
        # 当和tgt重合，将该点删除。
        if pygame.sprite.collide_mask(self, self.tgt):
            if self.tgt.health<=0:
                self.kill()
                del self
                return True
            if self.tgt.hitted(self.heal, 0, "holy"):
                dead = True
            else:
                dead = False
            # 死亡信息
            self.shooter.preyList.append( (getPos(self,0.5,0.5), self.color, 0, dead, self.tgt.coin, False) )
            # 命中目标
            spurtCanvas.addSpatters(6, (2,4,6), (16,18,20), self.color, getPos(self.tgt,0.5,0.5))
            self.kill()
            del self
            return True
    
# CP6
class Fan(InanimSprite):
    def __init__(self, x, y, coord):
        InanimSprite.__init__(self, "fan")
        self.imgList = [ pygame.image.load("image/stg6/fan0.png").convert_alpha(), pygame.image.load("image/stg6/fan1.png").convert_alpha(), pygame.image.load("image/stg6/fan2.png").convert_alpha() ]
        self.image = self.imgList[0]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x-self.rect.width//2
        self.rect.top = y-self.rect.height//2
        self.center = [x,y]
        self.coord = coord
        self.imgIndx = 0

        self.bldColor = (100,80,80,240)
        self.health = NB["fan"]["health"]
        self.damage = NB["fan"]["damage"]
        self.manner = NB["fan"]["manner"]
        self.coin = 0

    def whirl(self, delay, sprites):
        #if self.health<=0:
        #    spurtCanvas.addPebbles(self, 4, type="metalDebri")
        #    self.kill()
        #    return
        if not delay%DMG_FREQ:
            for hero in sprites:
                if pygame.sprite.collide_mask(self, hero):
                    if hero.rect.left+hero.rect.width//2 > self.center[0]:
                        hero.hitted(self.damage, 2, "physical")
                    else:
                        hero.hitted(self.damage, -2, "physical")
        if not (delay % 3):
            self.imgIndx = (self.imgIndx + 1) % len(self.imgList)
            self.image = self.imgList[self.imgIndx]
            self.rect = self.image.get_rect()
            self.rect.left = self.center[0]-self.rect.width//2
            self.rect.top = self.center[1]-self.rect.height//2
    
    def hitted(self, damage, pushed, dmgType):
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.kill()
            return
    
    def drawHealth(self, surface):
        pass
    
    def stun(self, duration):
        pass
    
    def lift(self, dist):
        self.rect.bottom += dist
        self.center[1] += dist
    
    def level(self, dist):
        self.rect.left += dist
        self.center[0] += dist

# CP7
class Stabber(InanimSprite):
    def __init__(self, x, y, coord):
        InanimSprite.__init__(self, "stabber")
        self.image = pygame.image.load("image/stg7/stabber.png").convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.left = x-self.rect.width//2
        self.rect.top = y
        self.coord = coord
        self.cnt = 0
        self.damage = NB["stabber"]["damage"]

    def stab(self, delay, sprites):
        self.cnt = (self.cnt+1) % 180
        if self.cnt >= 100:          # 若cnt<100，表示藏在砖内的状态。cnt>=110时，真正活动、对英雄造成伤害。
            if not delay%DMG_FREQ:
            # 只有hero在这一层时才进行hero的重合check，否则无权进行伤害。
                for hero in sprites:
                    if hero.onlayer==self.coord[1]+1 and pygame.sprite.collide_mask(self, hero):
                        hero.hitted(self.damage, 0, "physical")
            elif self.cnt < 118:     # 向上突刺，100~118，18个cnt
                self.rect.top -= 2
            elif self.cnt < 162:     # 停留
                pass
            else:                    # 向下收回，162~180，18个cnt
                self.rect.top += 2

# CP0 (endless mode)
class Statue(Porter):
    spurtCanvas = None

    def __init__(self, x, y, onlayer, font, lgg):
        Porter.__init__(self, x, y, "statue", 0, font, lgg)
        self.health = self.full = 2100
        self.onlayer = onlayer
        self.hitFeedIndx = 0
        self.preyList = []
        self.checkList = pygame.sprite.Group()
        self.lumi = 90
        self.gravity = 0
        self.aground = True
        # For NPC hero:
        self.bar = HPBar(self.full, blockVol=300, color="orange")
        self.doom = False

    def hitted(self, damage, pushed, dmgType):
        if self.health<=0:
            return
        self.health -= damage
        if (self.health < 0):
            self.health = 0
            self.doom = True
            self.spurtCanvas.addHalo("deadHalo", 180)
            # 音效、爆炸效果
            pygame.mixer.Sound("audio/wizard/hit.wav").play(0)
            self.spurtCanvas.addPebbles(self, 5, type="jadeDebri")
            self.spurtCanvas.addSmoke(1, (3,5,7), 5, (10,10,10,240), getPos(self,random(),random()), 4)
            # Image
            self.imgList = [self.brokeImg]
            self.shadList = [self.brokeImgShad]
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
        # 青烟效果
        if not delay%2:
            spurtCanvas.addSmoke(1, (3,4,6), 5, (100,255,10,200), getPos(self,random(),random()), 4)
        # 其他需要处理的
        if self.hitFeedIndx>0:
            self.hitFeedIndx -= 1
        return 0

    def drawHeads(self, screen):
        if self.health<=0:
            return
        # 画HP & loading条
        if self.hitFeedIndx:
            self.bar.setColor("yellow")
        else:
            self.bar.setColor("orange")
        self.bar.paint(self, screen)

class Pool(InanimSprite):
    bg_size = 0    # 屏幕尺寸
    canvas = None
    rect = None
    surfH = 0
    bubbles = []
    fish = []

    def __init__(self, bg_size, initH, boundaries):  # initH 是游戏开始时pool已有的初始高度，相对于bg_size[1]而言。
        InanimSprite.__init__(self, "pool")
        # initialize the sprite
        self.pool_size = [ boundaries[1]-boundaries[0], initH+20 ]
        self.canvas = pygame.Surface( self.pool_size ).convert_alpha()
        self.rect = self.canvas.get_rect()
        self.rect.left = boundaries[0]
        self.rect.bottom = bg_size[1]
        # blue pool 部分，整个屏幕的大小，只是在渲染时只渲染surfH以下的部分。
        self.blueCv = pygame.Surface( self.pool_size ).convert_alpha()
        self.blueCv.fill( (150,150,240,100) )

        self.surfH = self.pool_size[1]-initH
        self.bubbles = []
        # About Fish.
        self.fishLeft = [pygame.image.load("image/stg0/fish0.png").convert_alpha(), pygame.image.load("image/stg0/fish1.png").convert_alpha()]
        self.fishRight = [pygame.transform.flip(self.fishLeft[0], True,False), pygame.transform.flip(self.fishLeft[1], True,False)]
        self.fish = []
        self.boundaries = [0, self.pool_size[0]]
        # Make 3 fish.
        for i in range(3):
            fs = pygame.sprite.Sprite()
            fs.speed = choice( [1,-1] )
            fs.imgList = self.fishLeft if fs.speed<0 else self.fishRight
            fs.image = fs.imgList[0]
            fs.imgIndx = 0
            fs.rect = fs.image.get_rect()
            # randomize the position
            fs.rect.left = randint(self.boundaries[0], self.boundaries[1]-fs.rect.width)
            fs.rect.top = randint(self.surfH, self.pool_size[1]-20)
            self.fish.append(fs)

    def flow(self, delay, sprites, spurtCanvas):
        if not (delay % 4):
            for each in self.bubbles[::-1]:
                if each[3]=="FLOW":
                    each[1] += each[4]
                    if (each[1]<=self.surfH) and (each in self.bubbles): # bubble浮到顶部，删除
                        self.bubbles.remove(each)
                elif each[3]=="CNT":
                    each[4] -= 1
                    if each[4]==0:
                        self.bubbles.remove(each)
                else:
                    self.bubbles.remove(each)
            if random()<0.4:
                # 生成新气泡（列表形式：[横坐标，纵坐标，半径，"FLOW", 速度]）。
                self.bubbles.append( [randint(0,self.pool_size[0]), self.pool_size[1], randint(1,7), "FLOW", choice([-1,-2])] )
        # 处理🐟。(Fish.swim)
        if not delay%2:
            for fs in self.fish:
                fs.rect.left += fs.speed
                if fs.rect.left<self.boundaries[0] or fs.rect.right>self.boundaries[1]:
                    fs.speed = -fs.speed
                    fs.imgList = self.fishLeft if fs.speed<0 else self.fishRight
                if not (delay % 8):
                    # 生成新气泡（列表形式：[横坐标，纵坐标，半径，"CNT"，倒计时]）。
                    pos = getPos(fs, 0.3+random()*0.4, 0.3+random()*0.4)
                    self.bubbles.append( [pos[0], pos[1], randint(1,3), "CNT", randint(15,21)] )
                    # 切换图片
                    fs.imgIndx = ( fs.imgIndx+1 ) % len(fs.imgList)
                    fs.image = fs.imgList[fs.imgIndx]

    def paint(self, screen):
        self.canvas.fill((0,0,0,0))
        # Paint Fish
        for fs in self.fish:
            self.canvas.blit(fs.image, fs.rect)
        self.canvas.blit( self.blueCv, pygame.Rect( 0, self.surfH, self.pool_size[0], self.pool_size[1] ) )
        pygame.draw.line( self.canvas, (90,90,180,120), (0,self.surfH), (self.pool_size[0],self.surfH), randint(4,6) ) # 液面的深色线
        # Paint Bubbles
        for each in self.bubbles:
            pygame.draw.circle( self.canvas, (90,90,180,120), (each[0],each[1]), each[2] )
        # Blit all to screen.
        screen.blit( self.canvas, self.rect )

