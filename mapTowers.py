"""
mapTowers.py:
Define tower class of different categories,
Such as tower map for adventure mode, for endless mode, etc.
This module uses most of components in mapElems module.
"""
import pygame
from random import random, randint, choice

from mapElems import *
from database import PB
from util import getPos


# ================================================================================
# =============================== Adventure map ==================================
# ================================================================================
class AdventureTower():
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
    # Area: -1:(optional)tutorial area; 0; 1:Goalie; 2:link Bridge; 3:Goalie; 4:Boss.
    def __init__(self, oriPos, block_size, diameter, layer, stg, area, specialOn, doubleP, font, lgg, bgColors, bgShape, bg_size):
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

    def generateMap(self):
        self._constructTower(addChest=True)
        # 整个area完成之后，给进出口处增加接口。不同区域的接口要求不同。
        if (self.area==4):
            # 所有章节的4号区域，最后一扇门为整局出口
            for sideWall in self.groupList["0"]:
                self.addInterface( sideWall, 0, "left", "back_door" )    #左侧，连接上一区域
                if self.stg<7:
                    self.addInterface( sideWall, 0, "right", "hostage" )
                self.addInterface( sideWall, self.layer, "right", "exit" )
        else:
            for sideWall in self.groupList["0"]:
                self.addInterface( sideWall, 0, "left", "back_door" )
                self.addInterface( sideWall, self.layer, "right", "door" )
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
            speed = [ randint(-2,2), randint(-5,-2) ]
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
            brick = SideWall( x1, sideWall.rect.top, self.stg, (sideWall.coord[0]+1,sideWall.coord[1]), decor=False )
            self.groupList["0"].add(brick)
            # 角上的砖块
            brick = SideWall( x2, sideWall.rect.top, self.stg, (sideWall.coord[0]+1,sideWall.coord[1]), decor=False )
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
                # 1.若为边砖sidewall：加入砖 group "0" 中
                if ( (x==0) or (x == self.diameter-1) ):
                    if hollow_type == "adventure" or hollow_type == "practice":
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
                    elif hollow_type == "practice":
                        brick = SideWall( pixlX, pixlY-self.blockSize, 0, (x,y) )
                    self.groupList["0"].add(brick)
                # 2.若为roof层，铺满base砖。
                elif (y == self.layer+3):
                    if hollow_type=="adventure":
                        brick = Wall( pixlX, pixlY-self.blockSize, "baseWall", self.stg, (x,y) )
                    else:
                        brick = Wall( pixlX, pixlY-self.blockSize, "baseWall", 0, (x,y) )
                    self.groupList["0"].add(brick)
                # 3.否则为行砖linewall：加入当前行的 group 中
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
                                self.addChest( pixlX, pixlY, (x,y), 0.13 )
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
        "coin":[0,0.36],
        "gem":[0.36,0.4],   # 0.04

        "loadGlove":[0.4,0.55],     # 0.15
        "fruit": [0.55,0.7],        # 0.15
        "spec1":[0.7,0.85],         # 0.15
        "spec2":[0.85,1],           # 0.15
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
                    return choice( PB[self.stg] )
    
# ================================================================================
# ================================ Endless map ===================================
# ================================================================================
class EndlessTower(AdventureTower):
    
    # Constructor of MapManager ------------------------------------------
    def __init__(self, bg_size, block_size, diameter, stg, font, lgg, bgColors, bgShape):
        oriPos = ( (bg_size[0] - diameter*block_size) // 2, bg_size[1]-block_size  )
        #                                                       layer,   area,specialOn,doubleP
        AdventureTower.__init__(self, oriPos, block_size, diameter, 4, stg, 0, False, 0.1, font, lgg, bgColors, bgShape, bg_size)
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

# ================================================================================
# =============================== Tutorial map ===================================
# ================================================================================
class TutorialTower(AdventureTower):
    # Constructor of MapManager ------------------------------------------
    def __init__(self, block_size, diameter, font, lgg, bgColors, bgShape, bg_size):
        oriPos = ( (bg_size[0] - diameter*block_size) // 2, bg_size[1]-block_size  )
        #                                                       layer,stg,area,specialOn,doubleP
        AdventureTower.__init__(self, oriPos, block_size, diameter, 4, 0, 0, False, 0.1, font, lgg, bgColors, bgShape, bg_size)
        self.statue = None

    def generateMap(self):
        self._constructTower(addChest=False, hollow_type="practice")
        #self.statue = Statue( sum(self.boundaries)//2, self.getTop(layer=1), 2, self.font, self.lgg )
        #for sideWall in self.groupList["0"]:
            # right exit
            #self.addInterface( sideWall, self.layer, "right", "exit" )


# --------------------------------------
# background generator for any tower -------
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

