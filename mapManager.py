# map generator
import pygame
import math
from random import *

from database import NB, DMG_FREQ
from util import InanimSprite, HPBar, Panel, RichButton
from util import getPos, generateShadow

'''----------------------------------- MAP GENERATORS -------------------------------'''
# ================================================================================
# =============================== Adventure map ==================================
# ================================================================================
class AdventureTower():
    # some properties of the MapManager
    oriPos = (0,0)     # parameters about the screen (px)
    blockSize = 0      # parameters about the block size (px)  EVEN NUMBER RECOMMENDED !
    diameter = 0       # total width of the tower (number)   MUST BE OVER 7 !
    layer = 0          # total layers of the current stage (number), should be an even number
    stg = 1
    area = 0           # default: 0
    boundaries = ()
    
    specialOn = True   # the tag that indicate if we generate special wall in the map
    groupList = {}     # dictionary restoring wallsprite by classified groups {"layer": Group, "layer": Group, ...}，其中-1表示边砖，-3表示装饰物。key全为奇数。
    heightList = {}    # dictionary for the y pixel of each line. 注意，这里存储的是每一行的底部高度，如‘-1’值为basewall的底端.
    porter = None
    backporter = None
    doubleP = 0        # possibility that one chest contains 2 stuffs
    font = None
    lgg = 0

    chestList = None
    elemList = None
    monsters = None
    goalieList = None  # a group to indicate all goalies in this area.
    allElements = {}
    # Constructor of MapManager
    # Area: 0,1,2,3. 
    # -1: (optional)tutorial area; 
    # 0: initial area; 
    # 1: middle area; 
    # 2: link Bridge. 
    # 3: top area. 
    def __init__(self, oriPos, block_size, diameter, layer, stg, area, specialOn, doubleP, font, lgg, areaName, bgColors, bgShape, bg_size):
        if (diameter < 7) or (layer < 0):
            return False
        self.oriPos = oriPos
        self.blockSize = block_size
        self.diameter = diameter
        self.layer = layer
        leftBound = self.oriPos[0] + self.blockSize
        rightBound = self.oriPos[0] + (self.diameter-1)*self.blockSize
        self.boundaries = (leftBound, rightBound)
        self.font = font
        self.lgg = lgg
        self.bg_size = bg_size
        
        self.groupList = {}
        self.groupList["0"] = pygame.sprite.Group()     # prepare to include left & right sideWalls & roofWalls.
        self.groupList["-2"] = pygame.sprite.Group()    # prepare to include lineDecors.
        self.heightList = {}
        self.stg = stg
        self.area = area
        self.name = areaName
        self.specialOn = specialOn
        self.doubleP = doubleP
        # create towerBG
        bgSize = ( self.blockSize*self.diameter, self.blockSize*(self.layer+6) )
        self.towerBG = TowerBG( bgSize, bgColors[0], self.blockSize*1.1, bgColors[1], (self.oriPos[0],self.oriPos[1]+self.blockSize) )
        self.towerBG.addSpots( max(layer+4,10), colors=bgColors[2:], shape=bgShape)
        
        self.elemList = pygame.sprite.Group()        # Special elems attached to special walls.
        self.chestList = pygame.sprite.Group()       # Chests and hostages and alike stuffes.
        self.monsters = pygame.sprite.Group()        # All monsters.
        self.goalieList = pygame.sprite.Group()      # All goalies.
        # All elements of this tower are stored in 5 groups in order to render in different shades of layer.
        self.allElements = {
            "mons0": pygame.sprite.Group(),
            "dec0": pygame.sprite.Group(),     # Including chests & most porters (and linedecors?). Static.
            "mons1": pygame.sprite.Group(),    # Including monsters & other laterly added like bullets. Dynamic.
            "dec1": pygame.sprite.Group(),     # Including walls, column-likes, coins, blockFire-likes & decors. Dynamic.
            "mons2": pygame.sprite.Group()
        }
        self.merchant = None
        self.porter = self.backporter = None
        self.lineScope = (3, self.diameter-4)
        # Store Those casted props but current tower is not active
        self.suspendedProps = []

    def generateMap(self, tutor_on=False):
        self._constructTower(addChest=True)
        # 整个area完成之后，给进出口处增加接口。不同区域的接口要求不同。
        if (self.area==3):
            # 所有章节的3号区域，最后一扇门为整局出口
            for sideWall in self.groupList["0"]:
                self.addInterface( sideWall, 0, "left", "back_door" )    #左侧，连接上一区域
                if self.stg<7:
                    self.addInterface( sideWall, 0, "right", "hostage" )
                self.addInterface( sideWall, self.layer, "right", "exit" )
        else:
            for sideWall in self.groupList["0"]:
                self.addInterface( sideWall, 0, "left", "back_door" )
                self.addInterface( sideWall, self.layer, "right", "door" )
                #self.addInterface( sideWall, self.layer, "left", "merchant_advt")
        # 接口完成后，返回本area的极左位置值。（包括伸出的平台接口计算在内）
        return ( self.oriPos[0]+(self.diameter+2)*self.blockSize, self.oriPos[1]-self.blockSize*self.layer )

    def addChest(self, pixlX, pixlY, coord, rate):
        if random() <= rate:
            supply = Chest(
                pixlX+self.blockSize//2, pixlY-self.blockSize,
                self.supClassify(), coord, self.bg_size, self.doubleP, self 
                )
            self.chestList.add(supply)
    
    def addCoins(self, num, pos, tgt, cList=[20,22,24], item="coin"):
        if num==0:
            return False
        for i in range(0, num, 1):
            randPos = [ randint(pos[0]-1, pos[0]+1), randint(pos[1]-1, pos[1]+1) ]
            speed = [ randint(-2,2), randint(-4,-1) ]
            if item=="coin":
                coin = Coin( randPos, choice( cList ), speed, tgt )
                self.allElements["dec1"].add( coin )
            elif item=="gem":
                coin = Coin( randPos, choice( cList ), speed, tgt, typ="gem" )
                self.allElements["dec1"].add( coin )
    
    def addInterface(self, sideWall, layer, direction, porterCate):
        '''创造塔楼间接口。layer采用的是英雄的一套层数体系（偶数体系）。'''
        # 首先确认是正确的一侧；若是对侧，则直接终止返回。
        if direction=="left":
            if not sideWall.coord[0] == 0:
                return
            ctr = sideWall.rect.left
            x1 = ctr-self.blockSize   # 第一格新砖左坐标
            x2 = ctr-2*self.blockSize # 第二格新砖左坐标
        elif direction=="right":
            if not sideWall.coord[0] == self.diameter-1:
                return
            ctr = sideWall.rect.right
            x1 = ctr
            x2 = ctr+self.blockSize
        # 然后，将两块sideWall向外平移两格，作为封口。
        if sideWall.coord[1] in ( layer, layer+1 ):
            dist = x2-sideWall.rect.left
            sideWall.level( dist )
            sideWall.coord = ( sideWall.coord[0]+round(dist/self.blockSize), sideWall.coord[1] )
            self.towerBG.addPatch( (self.blockSize*2,self.blockSize), (min(ctr,x2),sideWall.rect.bottom), rim=False)
        # 最后进行扩展搭建。
        elif sideWall.coord[1] in ( layer-1, layer+2 ):
            # 上下层必须盖两个
            brick = SideWall( x1, sideWall.rect.top, self.stg, (sideWall.coord[0]+1,sideWall.coord[1]) )
            self.groupList["0"].add(brick)
            # 角上的砖块
            brick = SideWall( x2, sideWall.rect.top, self.stg, (sideWall.coord[0]+1,sideWall.coord[1]) )
            self.groupList["0"].add(brick)
            # 添加上下两行补丁
            self.towerBG.addPatch( (self.blockSize*2,self.blockSize), (min(ctr,x2),sideWall.rect.bottom) )
            # 在接口处建立需要的物品（关卡门或其他东西）🚪
            if sideWall.coord[1]==layer-1:
                if porterCate=="door" or porterCate=="exit":
                    self.porter = Door( ctr, sideWall.rect.top, porterCate, self.stg, self.font, self.lgg )
                    self.chestList.add(self.porter)
                elif porterCate=="back_door":
                    self.backporter = Door( ctr, sideWall.rect.top, "door", self.stg, self.font, self.lgg )
                    if (self.area==-1) or (self.area==0):   # 一旦完成tutor，则不再允许返回
                        pass
                    else:
                        self.backporter.unlock()
                    self.chestList.add(self.backporter)
                elif porterCate=="hostage":
                    port = Porter( ctr, sideWall.rect.top, porterCate, self.stg, self.font, self.lgg )
                    self.chestList.add(port)
                elif porterCate=="merchant":
                    self.merchant = Merchant( ctr, sideWall.rect.top, self.stg, self.font, self.lgg, "endless" )
                    self.chestList.add(self.merchant)
        
    def addNPC(self, category, keyDic, Class=None):
        if category=="merchant":
            npc = Merchant( (self.boundaries[0]+self.boundaries[1])//2, self.getTop(0)+self.blockSize, self.stg, self.font, self.lgg, "adventure")
            npc.initWindow(keyDic)
            self.chestList.add(npc)
            self.merchant = npc
        #elif category=="servant":
        #    # Class should be myHero.Servant
        #    npc = Class( None, [(self.boundaries[0]+self.boundaries[1])//2, self.getTop(0)+self.blockSize], self.font, self.lgg, 0 )
        
    def _wallClassifier(self, y, mode="adventure"):
        '''y should be an odd number'''
        rowWallList = []
        if ( y >= 0 ) and ( y <= self.layer ):
            wallNum = randint( self.lineScope[0], self.lineScope[1] ) # 一行中至少要留两个缺口，至少有3格砖块
            i = 0
            while i < wallNum:
                m = choice(range(1, self.diameter-1))
                if m not in rowWallList:                   # 如果随机数与以前的不重复，则可取，并且i++，否则什么都不执行，继续循环
                    rowWallList.append(m)
                    i = i + 1
            if mode=="adventure":
                if (y==self.layer-1) and (self.diameter-2 not in rowWallList):  # 最高层右侧添1砖
                    rowWallList.append(self.diameter-2)
            elif mode=="endless":
                # 无尽模式中，石像位置必须有砖
                if y==1 and self.diameter//2 not in rowWallList:
                    rowWallList.append( self.diameter//2 )
                # 上层必须留有两块siteWall
                elif y==3 and self.sitePos[0] not in rowWallList:
                    rowWallList.append( self.sitePos[0] )
                elif y==3 and self.sitePos[1] not in rowWallList:
                    rowWallList.append( self.sitePos[1] )
        # 处理layer+1（即roof-1）层：这层要空出来，所以不铺砖
        elif ( y==self.layer+1 ):
            pass
        # 处理-1层或塔顶层(layer+2)：全部铺满砖
        else:
            for num in range(1, self.diameter-1):
                rowWallList.append(num)
        return rowWallList

    def _constructTower(self, addChest=True, hollow_type="adventure"):
        '''用于建立标准的塔楼，可指定是否添加宝箱'''
        # 从地下2层（y=-2）开始，创建各层的砖块
        # note that: y 像素设定为每个wall的 bottom 像素值
        y = -2
        pixlY = self.oriPos[1]+self.blockSize
        while ( y <= self.layer+3 ):          # 包括-2、-1层和layer+3层(roof层)
            self.heightList[str(y)] = pixlY   # 将新一行的位置信息写入HeightList中
            x = 0                             # 每次开始新一行的循环时，都将x置为第 0 格
            pixlX = self.oriPos[0]
            # 首先在groupList中为本行初始化一个group。如果该行是奇数行（1，3，5...）或最顶层（最顶层为layer+2，是偶数）则添加随机数量的wall
            if ( y%2 == 1 ) or ( y == self.layer+2 ):
                self.groupList[ str(y) ] = pygame.sprite.Group() # note that 该 group 的 key 以 y 命名
                rowWallList = self._wallClassifier( y, mode=hollow_type )
                # 第二关还要判断是否有Web。
                if self.stg==2 and self.area>=3 and y>=10 and random()<0.4:
                    hasWeb = True
                else:
                    hasWeb = False
            # 行级循环：
            while x < self.diameter:
                # 1.若为边砖：加入砖 group "0" 中
                if ( (x==0) or (x == self.diameter-1) ):
                    if hollow_type == "adventure":
                        # 如果不为最低2层、不为最高的几层，则有0.6的概率为边砖。
                        if y<=2 or y>=self.layer-1 or random()<0.6:
                            brick = SideWall( pixlX, pixlY-self.blockSize, self.stg, (x,y) )
                        else:
                            brick = Wall( pixlX, pixlY-self.blockSize, "hollowWall", self.stg, (x,y) )
                    elif hollow_type == "endless":
                        if y in [-2,-1,3,7]:
                            brick = SideWall( pixlX, pixlY-self.blockSize, 0, (x,y) )
                        else:
                            brick = Wall( pixlX, pixlY-self.blockSize, "hollowWall", self.stg, (x,y) )
                    self.groupList["0"].add(brick)
                # 2.若为roof层，铺满base砖。
                elif (y == self.layer+3):
                    if hollow_type=="adventure":
                        brick = Wall( pixlX, pixlY-self.blockSize, "baseWall", self.stg, (x,y) )
                    else:
                        brick = Wall( pixlX, pixlY-self.blockSize, "baseWall", 0, (x,y) )
                    self.groupList["0"].add(brick)
                # 3.否则，则为行砖：加入当前行的 group 中
                elif (y%2 == 1):
                    if x in rowWallList:
                        if ( y > 0 and y < self.layer):
                            # 处理行内砖块
                            if self.specialOn and y<(self.layer-1) and random()<=0.12:
                                brick = SpecialWall( pixlX, pixlY-self.blockSize, self.stg, (x,y) )
                                if brick.elem:
                                    self.elemList.add(brick.elem)
                            else:
                                if hollow_type=="adventure":
                                    brick = Wall(pixlX, pixlY-self.blockSize, "lineWall", self.stg, (x,y))
                                else:
                                    brick = Wall(pixlX, pixlY-self.blockSize, "lineWall", 0, (x,y))
                                if random() < 0.16:
                                    decor = Decoration( (pixlX+self.blockSize//2-6, pixlX+self.blockSize//2+6), pixlY-self.blockSize, "lineDecor", self.stg, (x,y), ("A","B"), 0 )
                                    self.groupList["-2"].add(decor)
                                if addChest and self.stg==3:      # 避免第三关中的补给品出现在掉落砖块上
                                    self.addChest( pixlX, pixlY, (x,y), 0.15 )
                            if addChest and (not self.stg==3) and self.area>=0:  # 除去-1号区域（训练营）
                                self.addChest( pixlX, pixlY, (x,y), 0.125 )
                        elif (y <= 0): # 最底层的砖特殊
                            if hollow_type=="adventure":
                                brick = Wall(pixlX, pixlY-self.blockSize, "baseWall", self.stg, (x,y))
                            else:
                                brick = Wall(pixlX, pixlY-self.blockSize, "baseWall", 0, (x,y))
                            if random() < 0.16:
                                decor = Decoration( (pixlX+self.blockSize//2-6, pixlX+self.blockSize//2+6), pixlY-self.blockSize, "lineDecor", self.stg, (x,y), ("A","B"), 0 )
                                self.groupList["-2"].add(decor)
                        self.groupList[ str(y) ].add(brick)
                    # 以下是x不在rowWallList当中的情况。第二关中要铺设webWall：
                    elif self.stg==2 and hasWeb:
                        web = WebWall( pixlX, pixlY-self.blockSize, self.stg, (x,y) )
                        self.elemList.add(web)
                x = x + 1
                pixlX = pixlX + self.blockSize
            y = y + 1
            pixlY = pixlY - self.blockSize
        
    def getTop(self, layer="min"):
        '''search the wall's rect.top according to the given line number'''
        layer = str(layer)
        if (layer.isdigit() or layer.startswith("-")) and (layer in self.heightList):  # 给定了层数
            return self.heightList[layer]-self.blockSize
        elif layer=="min":
            return self.heightList["-2"]-self.blockSize
        elif layer=="max":
            return self.heightList[str(self.layer+3)]-self.blockSize
        return False
        
    def paint(self, screen, heroes=[]):
        height = screen.get_size()[1]
        # 0:背景层
        self.towerBG.paint( screen )
        # 1：怪物后层(某些特殊怪物使用，如爬墙蜘蛛)
        for item in self.allElements["mons0"]:
            if ( item.rect.bottom>=0 ) and ( item.rect.top <= height ):
                item.paint( screen )
        # 2：装饰后层(宝箱+装饰B)
        for item in self.allElements["dec0"]:
            if ( item.rect.bottom>=0 ) and ( item.rect.top <= height ):
                item.paint( screen )
        # 3:怪物中层
        for item in self.allElements["mons1"]:
            if ( item.rect.bottom>=0 ) and ( item.rect.top <= height ):
                item.paint( screen )
        # 4：英雄层
        for hero in heroes:
            hero.paint( screen )
        # 5：装饰前层(砖块+装饰A)
        for item in self.allElements["dec1"]:
            if ( item.rect.bottom>=0 ) and ( item.rect.top <= height ):
                item.paint( screen )
        # 5-2：装饰前层额外层：边砖饰品
        for wall in self.groupList["0"]:
            if ( wall.rect.bottom>=0 ) and ( wall.rect.top <= height ):
                wall.paintDecor( screen )
        # 6：怪物前层(某些特殊怪物使用，如飞行生物)
        for item in self.allElements["mons2"]:
            if ( item.rect.bottom>=0 ) and ( item.rect.top <= height ):
                item.paint( screen )
        # 7: 怪物生命值显示层
        for item in self.monsters:
            if (( item.rect.bottom>=0 ) and ( item.rect.top <= height )) or (hasattr(item, 'activated') and item.activated):
                item.drawHealth( screen )

    def lift(self, dist):
        if dist:
            for h in self.heightList:
                self.heightList[h] = self.heightList[h] + dist
            for grp in self.allElements:
                for item in self.allElements[grp]:
                    item.lift( dist )
            self.towerBG.lift(dist)

    def level(self, dist):
        if dist:
            self.boundaries = ( self.boundaries[0]+dist, self.boundaries[1]+dist )
            for grp in self.allElements:
                for item in self.allElements[grp]:
                    item.level( dist )
            self.towerBG.level(dist)

    chest_dic = {       # 概率分布，左闭右开
        "coin":[0,0.32],
        "gem":[0.32,0.35],

        "loadGlove":[0.35,0.54],
        "fruit": [0.54,0.7], 
        "spec1":[0.7,0.85], 
        "spec2":[0.85,1]
    }
    def supClassify(self):
        '''以一定概率区分 chest内 supply type'''
        number = random()
        for sup_name in self.chest_dic:
            ran = self.chest_dic[sup_name]
            if (ran[0] <= number < ran[1]):
                # Fall in the range, return sup_name
                if sup_name in ["fruit", "loadGlove", "coin", "gem", "ammo"]:
                    return sup_name
                else:
                    if self.stg==1:
                        return choice(["cooler","toothRing"])
                    elif self.stg==2:
                        return choice(["herbalExtract","blastingCap"])
                    elif self.stg==3:
                        return choice(["torch","medicine"])
                    elif self.stg==4:
                        return choice(["copter","pesticide"])
                    elif self.stg==5:
                        return choice(["alcohol","battleTotem"])
                    elif self.stg==6:
                        return choice(["missleGun","simpleArmor"])
                    elif self.stg==7:
                        return "shieldSpell"
    
# ================================================================================
# ================================ 无尽模式 map ===================================
# ================================================================================
class EndlessTower(AdventureTower):
    
    # Constructor of MapManager ------------------------------------------
    def __init__(self, bg_size, block_size, diameter, stg, font, lgg, bgColors, bgShape):
        oriPos = ( (bg_size[0] - diameter*block_size) // 2, bg_size[1]-block_size  )
        #                                                       layer,   area,specialOn,doubleP    areaName
        AdventureTower.__init__(self, oriPos, block_size, diameter, 4, stg, 0, False, 0.1, font, lgg, ("",""), bgColors, bgShape, bg_size)
        self.extLayer = choice( range(2,self.layer,2) )
        self.merchant = None
        self.statue = None
        self.lineScope = (4, self.diameter-4)
        self.siteWalls = []
        #self.sitePos = [self.diameter//3, self.diameter*2//3]
        self.sitePos = [2, self.diameter-1-2]

    def generateMap(self):
        self._constructTower(addChest=False, hollow_type="endless")
        # Make siteWalls
        for line in ["-1","1","3"]:
            for wall in self.groupList[line]:
                if (line=="1" and wall.coord[0]==self.diameter//2):
                    wall.kill()
                    siteWall = SpecialWall(wall.rect.left, wall.rect.top, 0, wall.coord)
                    del wall
                    self.groupList[ line ].add(siteWall)
                elif (line in ["-1","3"] and wall.coord[0] in self.sitePos):
                    wall.kill()
                    siteWall = SpecialWall(wall.rect.left, wall.rect.top, 0, wall.coord)
                    del wall
                    self.groupList[ line ].add(siteWall)
                    self.siteWalls.append(siteWall)
        # 单独设置，且不加入self.chestList。无形的商人
        self.merchant = Merchant( 0, 0, self.stg, self.font, self.lgg, "endless" )
        self.statue = Statue( sum(self.boundaries)//2, self.getTop(layer=1), 2, self.font, self.lgg )

    def rebuildMap(self, canvas, color):
        # 清理所有可能残留的怪物
        for key in ["mons0","mons1","mons2"]:
            for item in self.allElements[key]:
                item.kill()
                del item
        # 逐层清空砖块并重建
        for line in self.groupList:
            if int(line)<=0 or int(line)>self.layer:
                continue
            # Only rebuild lineWall parts
            for wall in self.groupList[line]:
                if wall.category=="specialWall":    # 不删specialwall
                    continue
                canvas.addSpatters(6, (2,4,5), (24,30,36), color, getPos(wall), True)
                wall.kill()
                del wall
            for dec in self.groupList["-2"]:
                dec.kill()
                del dec
            for elem in self.elemList:
                elem.kill()
                del elem
            pixlY = self.heightList[line]
            x = 1         # 每次开始新一行的循环时，都将x置为第 1 格
            pixlX = self.boundaries[0]
            # 重新添加随机数量的wall
            rowWallList = self._wallClassifier( int(line), mode="endless" )
            # 行级循环：
            while x < self.diameter-1:
                if (x in rowWallList):
                    if not (int(line)==3 and x in self.sitePos) and not (int(line)==1 and x==self.diameter//2):    # 不覆盖specialwall
                        brick = Wall(pixlX, pixlY-self.blockSize, "lineWall", 0, (x,int(line)))
                        if random() < 0.5:
                            decor = Decoration( 
                                (pixlX+self.blockSize//2-6, pixlX+self.blockSize//2+6), pixlY-self.blockSize, 
                                "lineDecor", self.stg, (x,int(line)), ("A","B"), 0
                            )
                            self.groupList["-2"].add(decor)
                        self.groupList[ line ].add(brick)
                x = x + 1
                pixlX = pixlX + self.blockSize
        
    def shiftChp(self, canvas, color):
        # Alter the image of hollowWall when shifting chapters.
        for wall in self.groupList["0"]:
            if wall.category=="hollowWall":
                canvas.addSpatters(6, (2,4,5), (24,30,36), color, getPos(wall), True)
                wall.image = pygame.image.load(f"image/stg{self.stg}/hollowWall.png").convert_alpha()
                wall.mask = pygame.mask.from_surface(wall.image)


# =========================================================================
# ================ TowerBG, Coins & other accessories =====================
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
            self.imgList = [ pygame.image.load("image/gem.png").convert_alpha() ] * 2
            self.shadList = [ generateShadow(self.imgList[0]) ] * 2
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
class TowerBG():
    surface = None
    rect = None
    patchList = []
    color = (0,0,0,0)
    rimColor = (0,0,0,0)

    def __init__(self, size, color, rimWidth, rimColor, lbPos):
        self.surface = pygame.Surface( size ).convert_alpha()
        self.surface.fill(color)
        self.rect = self.surface.get_rect()
        self.rect.left = lbPos[0]
        self.rect.bottom = lbPos[1]
        self.color = color
        self.rimColor = rimColor
        self.patchList = []
        # 绘制边框
        pygame.draw.rect( self.surface, rimColor, ((0,0),size), round(rimWidth*2) )

    def addSpots(self, num, colors=[(0,0,0,0)], shape="rect"):
        # 给壁纸增加斑点。可以是rect或circle
        i = 0
        if shape=="rect":
            while i<num:
                pos = ( randint(80,self.rect.width-120), randint(120,self.rect.height-180) )
                pygame.draw.rect( self.surface, choice(colors), ((pos),(60,30)) )
                i += 1
        elif shape=="circle":
            while i<num:
                pos = ( randint(100,self.rect.width-100), randint(120,self.rect.height-180) )
                pygame.draw.circle( self.surface, choice(colors), (pos), randint(10,20) )
                i += 1
    
    def addPatch(self, size, lbPos, rim=True):
        # 当塔楼添加了扩展小平台时，应当使用此函数来给towerBG也增加相应的扩展补丁
        patch = pygame.Surface( size ).convert_alpha()
        #if rim:
        patch.fill(self.rimColor)
        #else:
        #    patch.fill(self.color)
        rect = patch.get_rect()
        rect.left = lbPos[0]
        rect.bottom = lbPos[1]
        self.patchList.append( [patch,rect] )

    def paint(self, screen):
        screen.blit(self.surface, self.rect)
        for patch in self.patchList:
            screen.blit(patch[0], patch[1])

    def lift(self, dist):
        self.rect.top += dist
        for patch in self.patchList:
            patch[1].top += dist

    def level(self, dist):
        self.rect.left += dist
        for patch in self.patchList:
            patch[1].left += dist
    
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
        elif self.contains == "ammo":
            hero.arrowCnt += self.number
            tgtPos = [ hero.slot.ctrDic["brand"][0]+self.bg_size[0]//2, hero.slot.ctrDic["brand"][1]+self.bg_size[1]//2 ]
            subsImg = hero.ammoImg
        else:
            hero.bagpack.incItem(self.contains, self.number)
            tgtPos = [ hero.slot.ctrDic["bag"][0]+self.bg_size[0]//2, hero.slot.ctrDic["bag"][1]+self.bg_size[1]//2 ]
            subsImg = hero.bagpack.readItemByName( self.contains )[1]
        # deal inside substance
        substance = ChestContent(self.contains, subsImg, self.number, getPos(self,0.5,0.8), tgtPos)
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

    def __init__(self, name, image, number, ctr, tgtPos, spacing=10):
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
        self.tgtPos = tgtPos
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
                spdX = ( self.tgtPos[0] - each.left ) // 20
                each.left += spdX
                spdY = ( self.tgtPos[1] - each.bottom ) // 20
                each.bottom += spdY
                surface.blit( self.image, each )
                if spdX == 0 and spdY == 0:
                    self.rectList.remove(each)
            if len(self.rectList)<=0:
                self.reached = True
    
    def lift(self, dist):
        for each in self.rectList:
            each.top += dist
    
    def level(self, dist):
        for each in self.rectList:
            each.left += dist



# ================================================================================
# ============================ Accessaries of the map ============================
# ================================================================================
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

# -----------------------------------------------------------
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

# -----------------------------------------------------------
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

# -----------------------------------------------------------
class SideWall(Wall):
    def __init__(self, x, y, stg, coord):
        Wall.__init__(self, x, y, "sideWall", stg, coord)
        self.decor = None
        # 墙壁的装饰：
        if random() < 0.16:
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

# CP1-------------------------------
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

# CP2-------------------------------
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

# CP4--------------------------------
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

# CP5--------------------------------
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
            self.tgt.health += self.heal
            #self.snd.play(0)
            spurtCanvas.addSpatters(6, (2,4,6), (16,18,20), self.color, getPos(self.tgt,0.5,0.5))
            if self.tgt.health>self.tgt.full:
                self.tgt.health = self.tgt.full
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
    
# CP6--------------------------------
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
    
    def lift(self, dist):
        self.rect.bottom += dist
        self.center[1] += dist
    
    def level(self, dist):
        self.rect.left += dist
        self.center[0] += dist

# CP7--------------------------------
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

# -------------
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


# ========================================================================
# ========================================================================
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
            self.imgList = [ pygame.image.load("image/defenseTower.png").convert_alpha() ]
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
            self.iconList = {"loadGlove":pygame.image.load("image/loadGlove.png").convert_alpha()}
        elif context=="endless":
            self.offerDic = {"loadGlove":4, "fruit":24, "spec":30, "servant":32, "defenseTower":36, "ammo":45}
            self.iconList = {"loadGlove":pygame.image.load("image/loadGlove.png").convert_alpha(), 
                            "servant":pygame.image.load("image/servant/servantLeft0.png").convert_alpha(),
                            "defenseTower":pygame.image.load("image/defenseTower.png").convert_alpha()}
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
            if gd.tag=="supAmmo":
                buyer.arrowCnt += gd.number
                tgtPos = [ buyer.slot.ctrDic["brand"][0]+half_size[0], buyer.slot.ctrDic["brand"][1]+half_size[1] ]
                subsImg = buyer.ammoImg
            elif gd.tag=="servant":
                return "servant"
            else:
                buyer.bagpack.incItem( gd.tag, gd.number )
                tgtPos = [ buyer.slot.ctrDic["bag"][0]+half_size[0], buyer.slot.ctrDic["bag"][1]+half_size[1] ]
                subsImg = buyer.bagpack.bagImgList[gd.tag]
            return ChestContent( gd.tag, subsImg, gd.number, half_size, tgtPos )
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
                if cate=="ammo":
                    tag = "supAmmo"
                    img = hero.ammoImg
                elif cate in ["fruit","defenseTower"]:
                    img = hero.bagpack.readItemByName( cate )[1]
                    tag = cate
                elif cate in ["loadGlove","servant"]:
                    img = self.iconList[cate]
                    tag = cate
                elif cate=="spec":
                    if stg==1:
                        tag = choice(["cooler","toothRing"])
                    elif stg==2:
                        tag = choice(["herbalExtract","blastingCap"])
                    elif stg==3:
                        tag = choice(["torch","medicine"])
                    elif stg==4:
                        tag = choice(["copter","pesticide"])
                    elif stg==5:
                        tag = choice(["alcohol","battleTotem"])
                    elif stg==6:
                        tag = choice(["missleGun","simpleArmor"])
                    elif stg==7:
                        tag = "shieldSpell"
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
    
# ------------------------------
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

# ------------------------------
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
        self.bar = HPBar(self.full, blockVol=30, color="orange")
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



'''----------------------------------- MAP ORNAMENTS -----------------------------------'''
# ===================================================================================
# =========================== 自然现象装饰（雨、雪、雾） ==============================
# ===================================================================================
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

# -------------------------------------------------------------
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

# -------------------------------------------------------------
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

# -------------------------------------------------------------
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

# -------------------------------------------------------------
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


# ============================================================================
# =============================== 溅射效果画布 ================================
# ============================================================================
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
        self.canvas.set_colorkey( (0,0,0) )     # set black as transparent color, generally make the canvas transparent
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

# ----------------------------------------------------------
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

# ----------------------------------------------------------
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
