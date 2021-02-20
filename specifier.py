"""
specifier.py:
Specifiers adapt/extend GameModel class to realise unique chapter features.
Specifiers should be managed in GameModel objects.
They also determines what kind of elements to update in different chapters.
"""
from random import random, choice, randint, sample   # will be used in stg3,4,5
import pygame

from myHero import Servant      # will be used in stg1, stg7
from mapElems import ChestContent, WebWall, House, Wall, Totem # will be used in stg2,4,5
import enemy

from database import GRAVITY
from util import getPos


# =====================================
class Stg1Specifier():
    def __init__(self):
        pass

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
                fire = item.update( model.delay, heroes, model.spurtCanvas )
                if fire:
                    model.tower.allElements["mons1"].add(fire)
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
                model.msgManager.addMsg( ("Danger Coming !","危险来临！"), type="ctr", duration=120 )
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):  # moves only if they appears in the screen
            if item.category == "tizilla":
                item.move(model.delay, heroes)
                item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
            elif item.category=="megaTizilla":
                item.move(model.delay, heroes, model.spurtCanvas)
                item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY)
            elif item.category == "dragon":
                fire = item.move(model.delay)
                if fire:
                    model.tower.allElements["mons1"].add(fire)
            elif item.category == "dragonEgg":
                if item.health>0:
                    fire = item.move(model.delay, heroes)
                    if fire:
                        model.tower.allElements["mons1"].add(fire)
                else:
                    dragon = enemy.Dragon(model.tower.heightList[str(item.onlayer)], str(item.onlayer), model.tower.boundaries)
                    dragon.rect.left = item.rect.left
                    item.kill()
                    model.tower.monsters.add( dragon )
                    model.tower.allElements["mons1"].add( dragon )
            elif item.category == "blockFire":
                item.burn(model.delay, heroes, model.spurtCanvas)
            elif item.category == "hellHound":
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(8)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )

    def paint(self, screen):
        return

class Stg2Specifier():
    def __init__(self):
        pass

    def giveBlastingCap(self, hero, bg_size):
        hero.bagpack.incItem("blastingCap", 2)
        startPos = [bg_size[0]//2, 60]
        substance = ChestContent("blastingCap", hero.bagpack.readItemByName("blastingCap")[1], 2, startPos, hero.slot.slotDic["bag"][1])
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
                    web = WebWall( web[1].left+web[1].width//2, web[1].top+web[1].height//2, 2, (0,0), fade=True)
                    model.tower.allElements["dec1"].add(web)
                    model.tower.monsters.add(web)
                    for hero in heroes:
                        hero.checkList.add(web)
            elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
                item.activated = True
                model.msgManager.addMsg( ("Danger Coming !","危险来临！"), type="ctr", duration=120 )
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
            elif item.category == "hellHound":
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(8)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )
            
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
                model.msgManager.addMsg( ("Danger Coming !","危险来临！"), type="ctr", duration=120 )
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
            elif item.category == "hellHound":
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(8)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )

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
            house = House( hut_base.rect.right, hut_base.rect.top+2, "house", tower.stg, tower.font, tower.lgg )
            tower.allElements["dec0"].add(house)           # For drawing and transforming with the map
            tower.groupList[str(hut_base.coord[1]+2)].add(house)        # For hero's jump checkList
            tower.hut_list.append(house)                    # For chim function
            # 随同工作1：替换可能遮住屋顶的砖
            for wall in tower.groupList[str(hut_base.coord[1]+2)]:
                if wall.category in ("lineWall","specialWall") and wall.coord[0] in (hut_base.coord[0], hut_base.coord[0]+1):
                    new_brick = Wall(wall.rect.left,wall.rect.top,"lineWall",4,wall.coord)
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
                model.msgManager.addMsg( ("Danger Coming !","危险来临！"), type="ctr", duration=120 )
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
            elif item.category == "hellHound":
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(8)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )

    def paint(self, screen):
        return

class Stg5Specifier():
    def __init__(self, bg_size, towerList):
        # 1.暴风雪控制器
        self.blizzardGenerator = enemy.blizzardGenerator(bg_size, 1500, 1000)
        # 2.每个区域生成Heal Totem
        totemNum = 3
        for tower in towerList:
            if tower.layer<=6:
                continue
            # 给塔楼增加图腾数量属性
            tower.totemNum = totemNum
            tower.totemList = pygame.sprite.Group()
            # 确定出现的层数
            occList = sample(range(3, tower.layer, 2), totemNum)
            for group in occList:
                wallList = [aWall for aWall in tower.groupList[str(group)]]          # Group转化为list
                wall = choice(wallList)
                totem = Totem("healTotem", wall, group)
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
                model.msgManager.addMsg( ("Danger Coming !","危险来临！"), type="ctr", duration=120 )
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
            elif item.category == "hellHound":
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(8)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )

    def paint(self, screen):
        self.blizzardGenerator.paint(screen)

class Stg6Specifier():
    def __init__(self):
        return

    def addDrip(self, tower):
        # randomly select a  sidewall to place the drip
        rand_x = choice( [0, tower.diameter-1] )
        rand_y = choice( range(4, tower.layer-2, 2))
        hider = None
        for each in tower.groupList["0"]:
            if each.coord[0]==rand_x and each.coord[1]==rand_y:
                hider = each
                break
        #hider = choice(tower.groupList["-1"])
        if hider.coord[0]<=0:
            direction = "right"
            pos = getPos(hider,0.6,0.5)
        else:
            direction = "left"
            pos = getPos(hider,0.4,0.5)
        drip = enemy.Drip(pos, direction)
        tower.allElements["mons0"].add(drip)
        tower.monsters.add(drip)

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
                model.msgManager.addMsg( ("Danger Coming !","危险来临！"), type="ctr", duration=120 )
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
            elif item.category == "drip":
                item.update(model.delay, model.tower.monsters, heroes, model.spurtCanvas)
            elif item.category == "hellHound":
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(8)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )

    def paint(self, screen):
        return
    
class Stg7Specifier():
    def __init__(self, VServant):
        self.boss = None
        self.servant = None
        self.VServant = VServant
        self.reinf_time = 10     # 每局游戏拥有10次增援
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
                self.servant = Servant(hero, self.VServant, getPos(hero,0.5,1), tower.font, tower.lgg, hero.onlayer)
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
                model.msgManager.addMsg( ("Danger Coming !","危险来临！"), type="ctr", duration=120 )
        elif ( item.rect.bottom >= 0 ) and ( item.rect.top <= model.bg_size[1] ):
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
            elif item.category == "hellHound":
                vib = item.fall( model.tower.getTop(item.onlayer), model.tower.groupList, GRAVITY )
                if vib:
                    model._addVib(8)
                item.move( heroes, model.spurtCanvas, model.tower.groupList, vib, GRAVITY )

    def paint(self, screen):
        return
    
class TutorialSpecifier():
    def __init__(self, hero, tower, VServant, tutor_on=True):
        self.tutor_on = tutor_on
        if tutor_on==True:
            self.tutorStep = 1  # 1:move left/right; 2:jump; 3:double jump; 4:shoot; 5:jump down; 6:use item; 7:shift item.
            # Add a servant.
            self.servant = Servant(hero, VServant, [tower.boundaries[1]-120, tower.getTop("-1")], tower.font, tower.lgg, 0)
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
                4: (f"Press [{keyDic['shootKey']}] to shoot. Shoot all ammo!", f"按[{keyDic['shootKey']}]射击。射出所有弹药！"),
                5: (f"Press [{keyDic['downKey']}] to jump down. Get to bottom layer.", f"按[{keyDic['downKey']}]，下跳到最底层。"),
                6: (f"You're injured. Press [{keyDic['itemKey']}] to eat fruit.", f"你受伤了，按[{keyDic['itemKey']}]吃水果补充体力。"),
                7: (f"Press [{keyDic['superKey']}] to cast SuperPower.", f"按[{keyDic['superKey']}]释放超级技能。"),
                8: (f"Done! Press [ENTER] to pause game, then quit.", f"完成了！按[ENTER]暂停游戏，然后即可退出。")
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
        # print tip.
        if (not delay % 60) and self.servant:
            self.servant.talk = [self.tipDic[self.tutorStep][self.servant.lgg], 60]
            if not self.init_snd:
                self.servantSnd[1].play(0)
                self.init_snd = True
        
        if not self.tutor_on:
            return False

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
                if hero.onlayer >= 4 and hero.aground:
                    self._progress(hero, spurtCanvas)
                    hero.arrow = 3
                    return True
            elif self.tutorStep==4:
                if hero.arrow == 0:
                    self._progress(hero, spurtCanvas)
                    return True
            elif self.tutorStep==5:
                # pass if hero is on the lowest layer
                if hero.onlayer==0 and hero.aground:
                    self._progress(hero, spurtCanvas)
                    hero.hitted(150, 0, "physical")   # different dmg in different difficulty.
                    #hero.bagpack.bag["fruit"] += 1
                    return True
            elif self.tutorStep==6:
                # pass if hero's hp bar is full
                if hero.health==hero.full:
                    # immediately charge player's superpower bar
                    hero.chargeSuperPower(hero.superPowerFull)
                    self._progress(hero, spurtCanvas)
                    return True
            elif self.tutorStep==7:
                # pass if hero's superpower bar is empty
                if hero.superPowerCnt==0:
                    self._progress(hero, spurtCanvas)
                    return True
            elif self.tutorStep==8:
                tower.goalieList.remove(self.servant)
                #if self.servant:
                #    self.servant = None
                self.tutor_on = False
                return "OK"
                #return True

    def _progress(self, hero, canvas):
        self.tutorStep += 1
        self.checkCD = 60
        canvas.addSpatters( 12, [3, 4, 5], [16,20,24], (255,210,90), getPos(hero, 0.5, 0.5), False )
        self.progressSnd.play(0)
        self.servantSnd[self.tutorStep].play(0)

    def moveMons(self, model, item, heroes):
        pass

    def paint(self, screen):
        if self.servant:
            self.servant.drawHeads(screen)
