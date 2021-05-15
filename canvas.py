"""
canvas.py:
Define two major kinds of canvas: Nature (Nature_Canvas) & SpurtCanvas (Spurt_Canvas).
Nature_Canvas presents nature effects such as rain, snow and ash;
Spurt_Canvas is a more comprehensive canvas that mainly deals three visual effects:
    1. paints spatters of blood, ash, smoke, flying trails, etc.;
    2. shows halos (when hero casts superpower or gets hitted, etc.);
    3. generates some particle-like bullets for certain monsters and heroes.
"""
import pygame
from random import random, randint, choice

from database import DMG_FREQ
from util import getPos


# =========================================================================
# =========================== Natural Canvas ==============================
# =========================================================================
class Nature():

    drops = []     # 储存运动的单个对象（雨、雪、雾团等）
    wind = 0       # 风向（速）
    bg_size = ()   # 窗口的宽高
    canvas = None  # 实际绘制对象的透明画布

    def __init__(self, bg_size, stg, num, wind):
        self.drops = []
        self.bg_size = bg_size
        self.wind = wind                     # 自由变量，可以用作多种用途。

        self.canvas = pygame.Surface(bg_size).convert_alpha()
        self.canvas.set_colorkey( (0,0,0) )  # set black as transparent color, generally make the canvas transparent
        self.rect = self.canvas.get_rect()
        self.rect.left = 0
        self.rect.top = 0
        if stg==1:
            self.addAsh( num, (250,200,0,200), False )
            self.dropType = "ash"
        elif stg==2:
            self.snowDrop( num, (10,30,30,210), [16, 20, 24] )
            self.dropType = "snow"
        elif stg==3:
            self.addAsh( num, (10,0,20,160), False )
            self.dropType = "ash"
        elif stg in (4,7):
            self.rainDrop( num )
            self.dropType = "rain"
        elif stg==5:
            self.snowDrop( num, (255, 255, 255, 160), [4, 5, 6, 7] )
            self.dropType = "snow"
        elif stg==6:
            self.wind = [0,self.bg_size[1]//2]   # 对于第6关，有一个特别的聚集点，作为每次刷新时的初始点（初始值：左侧中间）
            self.count = 60            # 计时器，每隔一段时间（倒计时变0）重置一次火花
            self.addAsh( num, (255,230,20,210), True )
            self.dropType = "spark"
        else:
            self.dropType = "ash"

    def rainDrop(self, num):
        for i in range(0, num, 1):
            thickness = choice( [1, 2] )
            length = choice( [24, 34, 44] )
            startPos = [ randint( 0, self.bg_size[0] ), randint(-self.bg_size[1], 0) ]
            speed = choice( [30, 36, 42] )
            drop = Rain( thickness, length, startPos, speed, self.bg_size )
            self.drops.append( drop )

    def snowDrop(self, num, color, spdList):
        for i in range(0, num, 1):
            radius = choice( [3, 6, 9] )
            startPos = [ randint( 0, self.bg_size[0] ), randint(-self.bg_size[1], 0) ]
            speed = choice( spdList )
            drop = Snow( radius, startPos, speed, color, self.bg_size )
            self.drops.append( drop )

    # spark should be a boolean.
    def addAsh(self, num, color, spark):
        for i in range(0, num, 1):
            if spark:
                radius = choice( [2, 4, 6] )
                drop = Spark( radius, color, self.wind, self.bg_size )
            else:
                radius = choice( [2, 4, 5] )
                drop = Ash( radius, color, self.bg_size  )
            self.drops.append( drop )

    # 供外部调用的更新drops对象的接口
    def update(self, screen):
        self.canvas.fill( (0,0,0,0) )        # 填充透明的黑色（覆盖上一次的绘画记录）
        for each in self.drops:
            each.move( self.wind )
            each.paint( self.canvas )
        if self.dropType == "spark":
            self.count -= 1
            if self.count <= 0:
                newSide = choice( [0, self.bg_size[0]] )    # 随机选择一条出现的边
                self.wind = [ newSide, randint(20,self.bg_size[1]-100) ]
                self.count = 60              # 倒计时重置为60
            else:
                self.wind = 0
        elif self.dropType == "snow" and random()<0.01:
            self.wind = -self.wind
        screen.blit( self.canvas, self.rect )

# ----------------------------------------------------------
class Rain(pygame.sprite.Sprite):
    def __init__(self, thickness, length, startPos, speed, bg_size):  # 参数：雨线的粗细；雨线的长度；雨滴的起始位置
        pygame.sprite.Sprite.__init__(self)
        self.thickness = thickness
        self.length = length
        self.speed = speed
        self.head = startPos
        self.bg_size = bg_size

    def move(self, wind):
        if self.head[1] < self.bg_size[1]:  # 尚在屏幕内，继续下落
            self.head[1] += self.speed
            self.head[0] += wind
        else:
            self.head[1] = 0       # 触底则重置到顶端
            self.head[0] = randint( 0, self.bg_size[0] )
        self.tail = [self.head[0]-wind, self.head[1]-self.length] # 尾部减掉了风速，以保持雨丝倾斜
    
    def paint(self, surface):
        pygame.draw.line( surface, (255,255,255,160), self.head, self.tail, self.thickness )  # 抗锯齿的单个线段

# ----------------------------------------------------------
class Snow(pygame.sprite.Sprite):
    def __init__(self, radius, startPos, speed, color, bg_size):  # 参数：雪花的半径；雪花的起始位置
        pygame.sprite.Sprite.__init__(self)
        self.r = radius
        self.speed = speed
        self.pos = startPos
        self.color = color
        self.bg_size = bg_size

    def move(self, wind):
        if (self.pos[1] < self.bg_size[0]) and (0 < self.pos[0] < self.bg_size[1]):  # 尚在屏幕内，继续下落
            self.pos[1] += self.speed
            self.pos[0] += wind
        else:
            self.pos[1] = 0       # 出界则重置到顶端
            self.pos[0] = randint( 0, self.bg_size[0] )
    
    def paint(self, surface):
        pygame.draw.circle( surface, self.color, self.pos, self.r)

# ----------------------------------------------------------
class Ash(pygame.sprite.Sprite):
    def __init__(self, radius, color, bg_size):  # 参数color:推荐带上透明度RGBA；参数speed:为一个二元组
        pygame.sprite.Sprite.__init__(self)
        self.r = radius
        self.color = color
        self.bg_size = bg_size
        self.pos = [0,0]
        self.reset()
    
    def move(self, wind):
        if (-10 < self.pos[0] < self.bg_size[0]+10) and (-10 < self.pos[1] < self.bg_size[1]+10):  # 尚在屏幕内，继续滚动
            self.pos[0] += self.speed[0]
            self.pos[1] += self.speed[1]
        else:
            self.reset()
    
    def reset(self):      # 初始化本ash的所有状态
        # 随机选择一条出现的边：
        newFrom = randint( 0, 3 )        # 0表示从上，1表示从左，2表示从下，3表示从右
        if newFrom == 0:
            self.pos[0] = randint( 0, self.bg_size[0] )
            self.pos[1] = randint( -10, 0 )
            self.speed = [ randint(-2,2), randint(1,2) ]
        elif newFrom == 1:
            self.pos[0] = randint( -10, 0 )
            self.pos[1] = randint( 0, self.bg_size[1] )
            self.speed = [ randint(1,2), randint(-2,2) ]
        elif newFrom == 2:
            self.pos[0] = randint( 0, self.bg_size[0] )
            self.pos[1] = randint( self.bg_size[1], self.bg_size[1]+10 )
            self.speed = [ randint(-2,2), randint(-2,-1) ]
        elif newFrom == 3:
            self.pos[0] = randint( self.bg_size[0], self.bg_size[0]+10 )
            self.pos[1] = randint( 0, self.bg_size[1] )
            self.speed = [ randint(-2,-1), randint(-2,2) ]
            
    def paint(self, surface):
        pygame.draw.circle( surface, self.color, self.pos, self.r)

# ----------------------------------------------------------
class Spark(Ash):
    def __init__(self, radius, color, startPos, bg_size):
        self.newPos = startPos
        Ash.__init__(self, radius, color, bg_size)
    
    def move(self, newPos):
        if newPos:
            self.newPos = newPos
            self.reset()
        else:
            self.pos[0] += self.speed[0]
            self.pos[1] += self.speed[1]
            if self.speed[1]<24:
                self.speed[1] += 1       # 竖直速度增加，以实现下落效果            
    
    def reset(self):             # 初始化本spark的所有状态
        self.pos = [ self.newPos[0], randint(self.newPos[1]-2, self.newPos[1]+2) ]
        if self.newPos[0] <= 0:
            self.speed = [ choice([2, 3, 4, 5, 6]), choice( range(-8,4,1) ) ]
        elif self.newPos[0] >= self.bg_size[0]:
            self.speed = [ choice([-2, -3, -4, -5, -6]), choice( range(-8,4,1) ) ]


# ========================================================================
# ============================ Spurt Canvas ==============================
# ========================================================================
class SpurtCanvas():

    spatters = None   # 储存运动的单个血滴，或冲击波边界圆
    pebbles = []
    canvas = None     # 实际绘制对象的透明画布
    rect = None
    halos = None      # boss出现时的全屏阴影画布，包括英雄的受伤反馈、冰冻效果等。
    txtList = []

    def __init__(self, bg_size):
        # Initialize the spurtCanvas part.
        self.spatters = pygame.sprite.Group()
        self.pebbles = []
        self.pebbleImg = {
            "pebble": pygame.image.load("image/stg2/pebble.png").convert_alpha(),
            "jadeDebri": pygame.image.load("image/stg0/jadeDebri.png").convert_alpha(),
            "eggDebri": pygame.image.load("image/stg1/eggDebri.png").convert_alpha(),
            "metalDebri": pygame.image.load("image/stg6/metalDebri.png").convert_alpha(),
            "boneDebri": pygame.image.load("image/stg3/boneDebri.png").convert_alpha()
        }
        self.canvas = pygame.Surface(bg_size).convert_alpha()
        self.rect = self.canvas.get_rect()
        self.rect.left = 0
        self.rect.top = 0

        self.txtList = []

        # Initialize the haloCanvas part.
        self.alphaCap = 240
        self.haloWidth = 28
        # For the sake of game's running effect, 5 at most are allowed to be added in one period.
        # Their value follows this format: [running Boolean, current alpha, current fade speed, Basic fade speed, color(rgb)].
        # layout: -----------------
        #         -----------------
        #         ||             ||
        #         -----------------
        #         -----------------
        self.halos = { "monsHalo":None, "hitHalo":None, "frzHalo":None, "holyHalo":None, "deadHalo":None }
        self.canvList = []
        # create surface array
        self.canvList.append( self.createHaloRect( 0, 0, bg_size[0], self.haloWidth ) )  # TopFrame
        self.canvList.append( self.createHaloRect( 0, bg_size[1]-self.haloWidth, bg_size[0], self.haloWidth ) )  # BottomFrame
        self.canvList.append( self.createHaloRect( 0, self.haloWidth, self.haloWidth, bg_size[1]-2*self.haloWidth ) )  # LeftFrame
        self.canvList.append( self.createHaloRect( bg_size[0]-self.haloWidth, self.haloWidth, self.haloWidth, bg_size[1]-2*self.haloWidth ) )  # RightFrame
        for each in self.halos:
            if each == "monsHalo":
                rgb = (40,40,40)
                fadeSpd = 5
            elif each == "hitHalo":
                rgb = (250,10,10)
                fadeSpd = -5
            elif each == "frzHalo":
                rgb = (120,120,250)
                fadeSpd = -1
            elif each == "holyHalo":
                rgb = (250,250,10)
                fadeSpd = -3
            elif each == "deadHalo":
                rgb = (255,255,255)
                fadeSpd = -3
            # Provide a encapsuled way to represent a halo effect around the edge of the screen.
            # radRat should be a List that contains 4 numbers (pixls), indicating 4 different layers of halos.
            # fadeSpd can be either positive or negative, indicating how should overall alpha value of the halo changes.
            self.halos[each] = [False, 0, fadeSpd, fadeSpd, rgb]
    
    def addSpatters(self, num, rList, cList, rgba, pos, falling=False, xspd=[], yspd=[], back=False):
        '''This method provide a encapsuled way to represent a spattering effect from a center point to all directions.
         Falling decides whether using normal spatters or falling spatters.'''
        for i in range(0, num, 1):
            radius = choice( rList )
            cnt = choice( cList ) #[10, 12, 14] )
            randPos = [ randint(pos[0]-1, pos[0]+1), randint(pos[1]-1, pos[1]+1) ]
            speed = []
            if not falling:
                if xspd and yspd:
                    speed = [ choice(xspd), choice(yspd) ]
                else:
                    speed = [ choice([-3, -2, -1, 1, 2, 3]), choice([-3, -2, -1, 1, 2, 3]) ]
            else:
                if xspd and yspd:
                    speed = [ choice(xspd), choice(yspd) ]
                else:
                    speed = [ choice([-2, -1, 0, 1, 2]), choice([-4, -3, -2, -1]) ]
            spatter = Spatter( radius, rgba, randPos, cnt, speed, falling=falling, back=back )
            self.spatters.add( spatter )

    def addSmoke(self, num, rList, fade, rgba, pos, xRange, speed=[0,-1]):
        for i in range(0, num, 1):
            radius = choice( rList )
            randPos = [ randint(pos[0]-xRange, pos[0]+xRange), randint(pos[1]-2, pos[1]+2) ]
            if len(rgba)<=3:
                rgba = [ rgba[0], rgba[1], rgba[2], 240 ]
            smoke = Smoke( radius, rgba, randPos, fade, speed )
            self.spatters.add( smoke )
    
    def addWaves(self, pos, color, initR, initW, rInc=1, wFade=1):
        wave = Wave( initR, color, list(pos), rInc, wFade ) # 最后两项：半径增长速度&圆环变细速度
        self.spatters.add( wave )

    def addAirAtoms(self, owner, num, pos, speed, sprites, cate, btLine=0):
        if cate=="fire":
            colorSet = [(255,69,0,255),(80,20,20,255),(255,158,53,255)]
            cntSet = [50, 54, 58]
        elif cate=="freezing":
            colorSet = [(120,120,160,255),(200,200,240,255),(160,160,200,255)]
            cntSet = [36, 42, 48]
        elif cate=="corrosive":
            r = choice( [5,6,7] )
            color = choice( [(80,60,80,255),(120,100,120,255)] )
            initPos = [ randint(pos[0]-2, pos[0]+2), randint(pos[1]-2, pos[1]+2) ]
            atom = Vomitus( r, color, initPos, speed, sprites, self, owner, btLine+8 )
            self.spatters.add(atom)
            return
        elif cate=="physical":
            r = choice( [6,7,8] )
            colorSet = [(255,210,160,255),(255,200,140,255),(255,240,180,255)]
            cntSet = [68, 72, 72]
            color = choice( colorSet )
            initPos = [ randint(pos[0]-1, pos[0]+1), randint(pos[1]-1, pos[1]+1) ]
            cnt = choice( cntSet )
            atom = AirAtom( r, color, initPos, cnt, speed, sprites, self, owner )
            self.spatters.add(atom)
            return
        for i in range(0, num, 1):
            r = choice( [2,3,5] )
            color = choice( colorSet )
            initPos = [ randint(pos[0]-1, pos[0]+1), randint(pos[1]-1, pos[1]+1) ]
            cnt = choice( cntSet )
            atom = AirAtom( r, color, initPos, cnt, speed, sprites, self, owner )
            self.spatters.add(atom)
    
    def addFlakes(self, num, wind):
        for i in range(0, num, 1):
            if wind>0:  # 向右
                posX = randint(-180, self.rect.width-120)
                speed = (2,7)
            else:
                posX = randint(120, self.rect.width+180)
                speed = (-2,7)
            r = choice( [6,8,10,12] )
            posY = randint(-self.rect.height,0)
            flake = Flake( r, [posX, posY], speed, (250,250,250,250), (self.rect.width,self.rect.height) )
            self.spatters.add(flake)
    
    def addPebbles(self, item, num, type="pebble"):
        # type: "pebble", "eggDebri", "metalDebri", "boneDebri"
        cent_x, cent_y = getPos(item,0.5,0.3)
        for i in range(num):
            # 默认向右
            pebble = self.pebbleImg[type].copy()
            speed = [ randint(0,2), randint(-12,-7) ]
            start_x = randint(cent_x, item.rect.right )
            start_y = randint(cent_y, item.rect.bottom)
            # 一半概率转向左
            if random()<0.5:
                pebble = pygame.transform.flip(pebble, True, False)
                speed[0] = -speed[0]
                start_x = cent_x*2 - start_x
            rect = pebble.get_rect()
            rect.left = start_x - rect.width//2
            rect.top = start_y - rect.height//2
            # surf, rect, speed, 掉落下限, 弹起次数
            self.pebbles.append( [pebble, rect, speed, item.rect.bottom+5, 1] )

    def addTrails(self, rList, cList, rgba, pos):
        radius = choice( rList )
        cnt = choice( cList )
        spatter = Spatter( radius, rgba, list(pos), cnt, [0,0] )
        self.spatters.add( spatter )

    def addExplosion(self, pos, initR, initW, rInc=1, wFade=1, waveColor=(255,160,30,250), spatColor=(2,2,2,220), dotD=(16,18,20), smoke=True):
        '''Specially for explosive flame effect. A formulation
            note that the default parameters are standard for BIG FIRE explosion like crimson dragon in chpter1'''
        self.addWaves( pos, waveColor, initR, initW, rInc=rInc, wFade=wFade )
        self.addSpatters( 8, [3,5,6], dotD, spatColor, pos )
        if smoke:
            self.addSmoke(3, (4,5,6), 1, (40,20,20,120), pos, 4)

    def update(self, screen):
        self.canvas.fill( (0,0,0,0) )           # refill transparent black to overwrite former paints.
        for each in self.spatters:
            each.move()
            each.paint(self.canvas)
        # 处理pebble
        for peb in self.pebbles[::-1]:
            peb[1].left += peb[2][0]
            peb[1].top += peb[2][1]
            if peb[1].bottom >= peb[3]:  # 落地
                if peb[4]>0:    # 弹起
                    peb[4] = peb[4]-1
                    peb[2] = [ peb[2][0], randint(-9, -6) ]
                else:           # 删除
                    self.pebbles.remove(peb)
                    continue
            else:
                peb[2] = [ peb[2][0], min(peb[2][1]+1,5) ]  # fall状态，速度+1
            self.canvas.blit( peb[0], peb[1] )
        # 显示文字
        for txt, pos in self.txtList:
            rect = txt.get_rect()
            rect.left = (self.rect.width-rect.width)//2 # 根据canvas宽度，设定居中
            if pos=="BOTTOM":
                rect.top = self.rect.height-30
            elif pos=="TOP":
                rect.bottom = 30
            self.canvas.blit( txt, rect )
        self.txtList.clear()
        # Paint the whole canvas
        screen.blit( self.canvas, self.rect )
    
    def addHalo(self, haloType, startAlpha):
        if haloType not in self.halos:  # Check to ensure type is in self.halos.
            return False
        if haloType=="monsHalo" and self.halos[haloType][0]==True:        # MonsHalo should not be overlapped.
            return False
        self.halos[haloType][0] = True
        self.halos[haloType][1] = startAlpha
        return True

    def createHaloRect(self, x, y, width, height):
        '''常用的画方格surface函数'''
        surf = pygame.Surface( (width, height) ).convert_alpha()
        rect = surf.get_rect()
        rect.left = x
        rect.top = y
        surf.set_colorkey( (0,0,0) )
        surf.fill( (0,0,0) )
        return (surf, rect)

    def updateHalo(self, screen):
        for each in self.halos:
            if self.halos[each][0]==False:     # 首项标志为False，则跳过
                continue
            # 变化透明度
            if 0 <= self.halos[each][1]+self.halos[each][2] <= self.alphaCap:
                self.halos[each][1] += self.halos[each][2]
            else:
                if self.halos[each][2]>0:               # 如果是增加透明度的过程，在最深阶段不应立即删除，要有一个反向淡化的过程。
                    self.halos[each][2] = -self.halos[each][2]
                else:
                    self.halos[each][2] = self.halos[each][3]   # reset the fade speed
                    self.halos[each][0] = False     # 完成，关闭标志
            # render the frame with relevant color
            r, g, b = self.halos[each][4]
            for pair in self.canvList:
                pair[0].fill( (r, g, b, self.halos[each][1]) )
                screen.blit( pair[0], pair[1])

    def level(self, dist):
        for each in self.spatters:
            each.level(dist)

    def lift(self, dist):
        for each in self.spatters:
            each.lift(dist)

# ---------------------------------------------------------- 
class Spatter(pygame.sprite.Sprite):
    '''Spatter 同时也是最基础的溅射质点类，在其基础上可衍生出许多其他类。
        参数color:推荐带上透明度RGBA；参数speed:为一个二元组；
        cnt是个灵活的变量，在不同的子类中可以被赋予不同的意义和任务。'''
    def __init__(self, radius, color, pos, cnt, speed, falling=False, back=False):
        pygame.sprite.Sprite.__init__(self)
        self.r = radius
        self.color = color
        self.pos = pos
        self.speed = speed
        self.cnt = cnt
        self.falling = falling
        if back:
            self.oriCnt = self.cnt
            self.move = self.move_back
    
    def move(self):
        # 若还有cnt，则进行移动，且减cnt。
        if self.cnt > 0:
            self.pos[0] += self.speed[0]
            self.pos[1] += self.speed[1]
            self.cnt -= 1
            # falling类型还要下落
            if self.falling and self.speed[1]<4 and not self.cnt%4:
                #if self.pos[0]>0:
                #    self.pos[0] -= 1
                #else:
                #    self.pos[0] += 1
                self.speed[1] += 1               # 竖直速度增加，以实现下落效果
        # 否则，该质点应该消散。半径减1.
        elif self.r > 0:
            self.r -= 1
        # 最后，当半径也减至0，将该点删除。
        else:
            self.kill()
            del self
            return True

    def move_back(self):
        '''用于覆盖back类型的move函数'''
        # 若还有cnt，则进行移动，且减cnt。
        if self.cnt > 0:
            self.pos[0] += self.speed[0]
            self.pos[1] += self.speed[1]
            self.cnt -= 1
        elif self.cnt > -self.oriCnt:
            self.pos[0] -= self.speed[0]
            self.pos[1] -= self.speed[1]
            self.cnt -= 1
        # 最后，将该点删除。
        else:
            self.kill()
            del self
            return True
    
    def paint(self, canvas):
        pygame.draw.circle(canvas, self.color, self.pos, self.r)

    def level(self, dist):
        self.pos[0] += dist

    def lift(self, dist):
        self.pos[1] += dist
    
# ----------------------------------------------------------
class Smoke(Spatter):
    # 参数color:推荐带上透明度RGBA；参数speed:为一个二元组；fade是颜色淡化的度，初始化时将被设为cnt。
    def __init__(self, radius, color, pos, fade, speed):
        Spatter.__init__(self, radius, color, pos, fade, speed)
    
    def move(self):
        # 若颜色消失，则删除
        if self.color[3]<=0:
            self.kill()
            del self
            return True
        # 否则，质点移动且颜色淡化
        elif self.color[3]>0:
            self.color = (self.color[0], self.color[1], self.color[2], self.color[3]-self.cnt)
            self.pos[0] += self.speed[0]
            self.pos[1] += self.speed[1]

# ----------------------------------------------------------
class Wave(Spatter):
    # increm是半径增大的幅度，capR是半径的最大值。
    def __init__(self, initR, color, pos, rInc, wFade):
        """
        self.cnt = rInc
        self.speed = wFade
        """
        Spatter.__init__(self, initR, color, pos, rInc, wFade)
        self.width = initR
    
    def move(self):
        # 如果在最大半径以下，则r继续增大。
        # 需要修改
        if self.width>0:
            self.r += self.cnt
            self.width -= self.speed
        else:
            self.kill()
            del self
            return True

    def paint(self, canvas):
        if self.width>0:
            pygame.draw.circle(canvas, self.color, self.pos, self.r, width=self.width)

# particles as attacks for certain monsters and heroes
class AirAtom(Spatter):

    def __init__(self, r, color, initPos, cnt, speed, sprites, canvas, owner):      # 参数speed:为一个二元组
        Spatter.__init__(self, r, color, initPos, cnt, speed)
        self.tgts = sprites
        self.enable = True
        self.canvas = canvas
        self.owner = owner
    
    def move(self):
        if self.cnt > 0:
            self.pos[0] += self.speed[0]
            self.pos[1] += self.speed[1]
            self.cnt -= 1
            if random()<0.5:
                self.speed[1] = - self.speed[1]
            if self.enable and not self.cnt%DMG_FREQ:
                for hero in self.tgts:
                    if (hero.rect.left < self.pos[0] < hero.rect.right) and (hero.rect.top < self.pos[1] < hero.rect.bottom) and (self.enable):
                        self.owner.reportHit(hero)
                        self.canvas.addSpatters(2, (2,3), (12,16,18), self.color, self.pos, False)
                        self.enable = False
        else:
            self.kill()
            del self
            return True

class Vomitus(Spatter):

    def __init__(self, r, color, initPos, speed, sprites, canvas, owner, btLine): # 参数speed:为一个二元组
        Spatter.__init__(self, r, color, initPos, 0, speed)
        self.tgts = sprites
        self.owner = owner
        self.canvas = canvas
        self.btLine = btLine
    
    def move(self):
        if self.pos[1]<self.btLine:
            self.cnt += 1
            if not self.cnt%DMG_FREQ:
                for tgt in self.tgts:
                    if tgt.rect.left < self.pos[0] < tgt.rect.right and tgt.rect.top < self.pos[1] < tgt.rect.bottom:
                        self.owner.reportHit(tgt)
                        if self.speed[0]>0:
                            tgt.hitBack = 1
                        else:
                            tgt.hitBack = -1
                        self.erase()
                        return
            if not self.cnt%2:
                self.pos[0] += self.speed[0]
                self.pos[1] += self.speed[1]
            if self.speed[1]<6 and not self.cnt%3:
                self.speed[1] += 1
        else:
            self.erase()
    
    def erase(self):
        self.canvas.addSpatters(2, (2,3), (3,4), self.color, self.pos, True)
        self.kill()

    def lift(self, dist):
        self.pos[1] += dist
        self.btLine += dist

# for CP5: blizzard
class Flake(Spatter):
    # 参数：雪花的半径；雪花的起始位置；这里将屏幕范围range赋给spatter的cnt变量。
    def __init__(self, radius, startPos, speed, color, range):
        Spatter.__init__( self, radius, color, startPos, range, speed )

    def move(self):
        if (self.pos[1] < self.cnt[1]) and (0 < self.pos[0] < self.cnt[0]):  # 尚在屏幕内，继续下落
            self.pos[1] += self.speed[1]
            self.pos[0] += self.speed[0]
        else:
            self.kill()
            del self
            return True
