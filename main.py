# Knight_Throde
"""
main.py:
Entrance of the whole game, runs the main menu of the game.
Control the actions of program beginning and ending.
Manage all UIs, menu pages such as settings, herobooks, chapter choosing page, etc.
They are all organized in a class called God.
"""
import sys, os, traceback
#import psutil
import time
from random import randint, choice
import pygame
from pygame.locals import *
import pickle

from database import REC_DATA   # 载入这一module的同时则会读取本地./record.sav
import model
from mapElems import Coin
from canvas import SpurtCanvas, Nature
import plotManager
from util import ImgButton, TextButton, RichButton, Panel, MsgManager, ImgSwitcher, TextBox, RichText


# ======================================================================
bg_size = width, height = 1280, 720  #或1280*800(均为16:10)
PLATFORM = "self"   # "self" or "steam". Treat differently on account.


# ======================================================================
class God():

    def __init__(self):
        '''====initialize window, screen and read records.======'''
        pygame.init()
        pygame.mouse.set_cursor(*pygame.cursors.tri_left)        # arrow(default), diamond, broken_x, tri_left, tri_right
        # Check display mode
        self.setDisplay()
        pygame.display.set_caption(f"Knight Throde {plotManager.VERSION.split('_')[-1]}")

        '''====font set========'''
        self.fntSet = [ ( pygame.font.Font("font/ebangkok.ttf", 14), pygame.font.Font("font/cHeiti.ttf", 14) ), 
            ( pygame.font.Font("font/ebangkok.ttf", 18), pygame.font.Font("font/cHeiti.ttf", 18) ), 
            ( pygame.font.Font("font/ebangkok.ttf", 24), pygame.font.Font("font/cHeiti.ttf", 24) ), 
            ( pygame.font.Font("font/ebangkok.ttf", 32), pygame.font.Font("font/cHeiti.ttf", 32) ) ]
        # music and sound -----------------------------------------------
        self.soundList = [ pygame.mixer.Sound("audio/victoryHorn.wav"), pygame.mixer.Sound("audio/gameOver.wav"), pygame.mixer.Sound("audio/click.wav") ]
        # 返回按钮 & 界面选项等控件 --------------------------------------
        self.mainTitle = [ pygame.image.load("image/titleE.png").convert_alpha(), pygame.image.load("image/titleC.png").convert_alpha() ]

        self.embed = bg_size[0]         # 向左嵌入部分的横坐标，初始为屏幕横长，表示全部在屏幕外
        self.embedFinal = round(bg_size[0]*0.45)
        self.embedSpd = 6               # 左右滑动的比例系数，作分母，越小越快

        # 初始化游戏的数据和管理对象
        self.initGameData()

        if PLATFORM=="self":
            # 检查账号登录状态
            if REC_DATA["GAME_ID"]==1:
                # 本地记录为1（默认初始ID），即未登陆
                self.page = "login"         # 进入登录/注册/游客页
            else:
                # ID值不为1，则之前已登陆，可直接登陆
                self.page = "index"         # 可取7个值：index, stgChoosing, collection, heroBook, settings, bazaar, login
                self.setManager.transmitFile(op="download")   # 访问服务器，并下载.rec写入到本地
        elif PLATFORM=="steam":
            # steam 平台不需要程序自己管理账号
            self.page = "index"
        
        self.backPosY = 56      # 返回按钮的纵坐标 
        self.setNature( self.setManager.paperList[REC_DATA["SYS_SET"]["PAPERNO"]]["e"] )    # 关卡的特殊自然装饰（雨雪等）
        self.spurtCanvas = SpurtCanvas(bg_size)
    
    def initGameData(self):
        # 三大用户交互管理助手
        if PLATFORM=="self":
            self.tbManager = plotManager.TextBoxManager(self.fntSet[1])
            self.tbManager.add_text_box( "username", (200,24), (width//2-100,height//2-45), self.fntSet[1][1],
                                        label=("Username: ","用户名："), descript=("No more than 12 characters.","不得多于12个字符。") )
            self.tbManager.add_text_box( "password", (200,24), (width//2-100,height//2+15), self.fntSet[1][1],
                                        label=("Password: ","密码："), descript=("Must be 6 to 12 characters.","须为6至12个字符。") )
        elif PLATFORM=="steam":
            pass

        self.imgSwitcher = ImgSwitcher()
        self.msgManager = MsgManager(self.fntSet[1], 1)  # stg=1
        # ===============================================================
        # =========== 宏观关卡信息、英雄书、图鉴、设置管理大类 =============
        self.setManager = plotManager.Settings( bg_size[0]-self.embedFinal-20, bg_size[1]-180, self.fntSet[2], platf=PLATFORM )
        if self.setManager.updateFlag==0:
            self.msgManager.alert("update")
        elif self.setManager.updateFlag==-1:
            self.msgManager.alert("failure")

        self.stgManager = plotManager.StgManager(580, 160, self.fntSet[1])
        self.heroBook = plotManager.HeroBook(bg_size[0]-self.embedFinal, bg_size[1]-120, self.fntSet[1])
        model.GameModel.VServant = self.heroBook.servantVHero    # Set the gamemodel's VServant.
        self.collection = plotManager.Collection(
                            bg_size[0]-self.embedFinal-20, bg_size[1]-190, self.stgManager.nameList, self.fntSet[1]
                        )
        # Bazaar ========================================================
        self.bazaar = plotManager.Bazaar(bg_size[0]-self.embedFinal-12, bg_size[1]-140, self.fntSet)

        self.curStg = REC_DATA["SYS_SET"]["STG_STOP"]    # 当前关卡标记，默认为1
        self.choosable = self.stgManager.checkChoosable(self.curStg)
        # Account & ID part =============================================
        self.accPanel = Panel(180, 150, self.fntSet[1], title=("Personal Account","个人账号"))
        if PLATFORM=="self":
            self.accPanel.addItem( (f"Game ID: {REC_DATA['GAME_ID']}",f"游戏ID：{REC_DATA['GAME_ID']}") )
            self.accPanel.addItem( (f"Total Level: {self.heroBook.total_level}",f"英雄总等级：{self.heroBook.total_level}") )
            self.accPanel.addItem( TextButton(160, 30,
                        {"default":("Reset Password","修改密码")}, "default", self.fntSet[1], rgba=(40,140,40,210)), tag="set_pwd"
                    )
            self.accPanel.addItem( TextButton(160, 30,
                        {"default":("Log Out","退出登录")}, "default", self.fntSet[1], rgba=(140,40,40,210)), tag="log_out"
                    )
            self.operat = "login"
        else:
            self.accPanel.addItem( (f"Total Level: {self.heroBook.total_level}",f"英雄总等级：{self.heroBook.total_level}") )

        self.shiftChapter(0)
    
    def go(self):
        clock = pygame.time.Clock()
        edge = 1
        edgePlus = 1

        self.indexButtons = {
            # -- 主游戏按钮.
            "advt": RichButton(150, 150, pygame.image.load("image/menu5.png").convert_alpha(), 
                        {1:("Chapters","选择章节")}, 1, self.fntSet[2]
                    ),
            # -- 左侧菜单选项
            "left1": RichButton(160, 70, pygame.image.load("image/menu1.png").convert_alpha(), 
                        {1:("Album","图鉴")}, 1, self.fntSet[1], align='horizontal'
                    ),
            "left2": RichButton(160, 70, pygame.image.load("image/menu2.png").convert_alpha(), 
                        {1:("Heroes","英雄书")}, 1, self.fntSet[1], align='horizontal'
                    ),
            "left3": RichButton(160, 70, pygame.image.load("image/menu3.png").convert_alpha(), 
                        {1:("Settings","综合设置")}, 1, self.fntSet[1], align='horizontal'
                    ),
            "left4": RichButton(160, 70, pygame.image.load("image/menu4.png").convert_alpha(), 
                        {1:("Bazaar","市集")}, 1, self.fntSet[1], align='horizontal'
                    ),
        }

        if PLATFORM=="self":
            self.indexButtons["account"] = plotManager.AccountButton( self.fntSet[1], mode="all" )
            # Login界面所需按钮
            self.registerButton = TextButton( 160, 40, {"log":("Register","注册"), "reset":("Cancel","取消")}, 
                "log", self.fntSet[2], rgba=(40,40,120,210) )
            self.loginButton = TextButton(160, 40, {"log":("Log in","登录"), "reset":("Confirm","确认")}, 
                "log", self.fntSet[2], rgba=(40,120,40,210) )
        else:
            self.indexButtons["account"] = plotManager.AccountButton( self.fntSet[1], mode="no_name" )
        # 主界面是否展开账户栏
        accShow = False
        
        self.gemList = pygame.sprite.Group()
        
        self.imgButtons = {
            "back": ImgButton( {"default":pygame.image.load("image/back.png").convert_alpha()}, "default", self.fntSet[0], labelPos="top" ),
            "quit": ImgButton( {"default":pygame.image.load("image/quit.png").convert_alpha()}, "default", self.fntSet[0], labelPos="btm" ),
            "switch": ImgButton( {"default":pygame.image.load("image/switch.png").convert_alpha()}, "default", self.fntSet[0], labelPos="top" ),
            "practice": ImgButton( {"default":pygame.image.load("image/camp.png").convert_alpha()}, "default", self.fntSet[0], labelPos="top" )
        }
        self.slide_status = ""

        while True:

            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.load("audio/stg7BG.wav")  # Play bgm
                pygame.mixer.music.set_volume(REC_DATA["SYS_SET"]["VOL"]/100)
                pygame.mixer.music.play(loops=-1)
            
            # wall paper
            self.addSymm(self.setManager.paperList[REC_DATA["SYS_SET"]["PAPERNO"]]["p"], 0, 0)
            # 上下页眉页脚
            #self.drawRect( 0, 0, bg_size[0], 60, self.stgManager.themeColor[0] )
            self.drawRect( 0, bg_size[1]-60, bg_size[0], 60, self.stgManager.themeColor[0] )
            ctrX = self.embed//2-bg_size[0]//2
            # Game Name Title
            self.addSymm(self.mainTitle[REC_DATA["SYS_SET"]["LGG"]], ctrX, -230 )

            pos = pygame.mouse.get_pos()
            
            # Account Panel
            self.indexButtons["account"].paint(self.screen, width//2-540, height//2-330, pos)

            # =================================================
            # =================== 菜单界面 =====================
            if ( self.page == "index" ):
                if self.slide_status!="":
                    self.slide_status = ""
                
                self.imgButtons["quit"].paint( self.screen, self.embed-45, 30, pos )

                for label in self.indexButtons:
                    if label=="advt":
                        self.indexButtons["advt"].paint(self.screen, width//2+540, height//2+210, pos)
                        if self.indexButtons[label].hover_on(pos):
                            self.addTXT( ("Explore various towers and rescue those trapped heroes!","探索不同的地图，营救困在其中的英雄！"), self.fntSet[1], 0, 0.925 )
                            self.addTXT( ("Or defend the King's statue as long as you can!","或保卫国王石像，挑战你的极限能力！"), self.fntSet[1], 0, 0.955 )
                    elif label=="left1":
                        self.indexButtons["left1"].paint(self.screen, width//2-540, height//2+20, pos)
                        if self.indexButtons[label].hover_on(pos):
                            self.addTXT( ("Check the monsters you have met.","查看你所收集的所有怪物信息。"), self.fntSet[1], 0, 0.93 )
                    elif label=="left2":
                        self.indexButtons["left2"].paint(self.screen, width//2-540, height//2+95, pos)
                        if self.indexButtons[label].hover_on(pos):
                            self.addTXT( ("Check or change the hero embatled.","查看英雄信息或更换出战英雄。"), self.fntSet[1], 0, 0.93 )
                    elif label=="left3":
                        self.indexButtons["left3"].paint(self.screen, width//2-540, height//2+170, pos)
                        if self.indexButtons[label].hover_on(pos):
                            self.addTXT( ("Key settings, systematic settings, version update and other contents.","系统设置，游戏键位修改，以及版本更新等内容。"), self.fntSet[1], 0, 0.93 )
                    elif label=="left4":
                        self.indexButtons["left4"].paint(self.screen, width//2-540, height//2+245, pos)
                        if self.indexButtons[label].hover_on(pos):
                            self.addTXT( ("Purchase Runestones to enhence your ability in the battle.","购买符石，增强你在战斗中的力量。"), self.fntSet[1], 0, 0.93 )
                    elif label=="account":
                        if self.indexButtons[label].hover_on(pos) and REC_DATA["GAME_ID"]==1:
                            self.addTXT( ("Click to log in or register an account, which is necessary to save your records online.","点击登录或注册一个游戏账号，游戏账号能够联网保存你的游戏进度。"), self.fntSet[1], 0, 0.93 )
                
                if accShow:
                    acc_on = self.accPanel.paint(self.screen, 100,145, pos)
                
                if self.imgButtons["quit"].hover_on(pos):
                    self.addTXT( ("Save and quit the game.","保存并退出游戏。"), self.fntSet[1], 0, 0.93 )
                
                # 右上角任务信息
                task_upd = self.bazaar.taskPanel.paint(self.screen, width-120,140, pos)
                # 任务图标
                bazRect = self.bazaar.taskPanel.rect
                self.addSymm(pygame.image.load("image/menu.png"), bazRect.left+10-width//2, bazRect.top+12-height//2)

                # 若在下载，显示下载信息
                if self.setManager.downloader:
                    prog = self.setManager.downloader.progress["prog"]
                    self.indexButtons["left3"].add_prompt( ("Download"+prog, "已下载"+prog) )
                    if prog=='100%':
                        self.setManager.closeDownload()
                # 提示更新/更新完成
                elif (self.setManager.updateFlag==0 and not self.setManager.downloader) or (self.setManager.updateFlag==2):
                    self.indexButtons["left3"].add_prompt(("New Update","版本可更新"))
                # 英雄可分配SP
                for each in self.heroBook.heroList:
                    if each.SP>0:
                        self.indexButtons["left2"].add_prompt(("Unused SP","点数可分配"))
                        break
                # 显示章节剧情进度
                but = self.indexButtons["advt"].rect
                # only count those chapters have been passed at any difficulty
                cpComp = [1 if star>0 else 0 for star in REC_DATA["CHAPTER_REC"]]
                cpTot = len(REC_DATA['CHAPTER_REC'])
                self.addTXT( (f"Completed: {sum(cpComp)}/{cpTot}", f"已完成章节：{sum(cpComp)}/{cpTot}"), 
                    self.fntSet[0], but.left+but.width//2-bg_size[0]//2, 0.656 )

                # handle the key events
                for event in pygame.event.get():  # 必不可少的部分，否则事件响应会崩溃
                    if ( event.type == QUIT ):
                        pygame.quit()
                        sys.exit()
                    elif ( event.type == KEYDOWN ):
                        pass
                    elif ( event.type == pygame.MOUSEBUTTONUP ): 
                        self.soundList[2].play(0)
                        if accShow and not acc_on:
                            accShow = False
                        if self.indexButtons["advt"].hover_on(pos):
                            if REC_DATA["SYS_SET"]["MOD_STOP"]==0:
                                self.setNature( self.curStg )
                            else:
                                self.setNature( 3 )
                            self.page = "stgChoosing"
                            self.slide_status = "in"
                        elif self.indexButtons["left1"].hover_on(pos):
                            self.page = "collection"
                            self.slide_status = "in"
                            self.collection.renewProgress()
                        elif self.indexButtons["left2"].hover_on(pos):
                            self.page = "heroBook"
                            self.slide_status = "in"
                        elif self.indexButtons["left3"].hover_on(pos):
                            self.page = "settings"
                            self.slide_status = "in"
                        elif self.indexButtons["left4"].hover_on(pos):
                            self.page = "bazaar"
                            self.slide_status = "in"
                            self.bazaar.myStonePanel.update_panel()
                        elif task_upd:
                            # 更新任务（可能包含两种操作：领取奖励并更换，或直接更换）
                            gems = self.bazaar.update_task()
                            if gems:
                                self.addGems(gems, (self.bazaar.taskPanel.rect.left, self.bazaar.taskPanel.rect.bottom), self.indexButtons["account"] )
                        elif self.imgButtons["quit"].hover_on(pos):
                            #self.setManager.qList.append("shutDown#")
                            pygame.quit()
                            sys.exit()
                        elif PLATFORM=="self":
                            # 自平台账号相关操作
                            if self.indexButtons["account"].hover_on(pos):
                                if REC_DATA["GAME_ID"] == 1:  # 开始登陆
                                    self.page = "login"
                                else:       # 退出登陆
                                    accShow = True
                                    self.heroBook.update_total_level()
                            elif accShow and acc_on:    # 退出登陆
                                if acc_on.tag=="set_pwd":
                                    self.registerButton.draw_text(label_key="reset")
                                    self.loginButton.draw_text(label_key="reset")
                                    self.operat = "reset_pwd"
                                    self.page = "login"
                                elif acc_on.tag=="log_out":
                                    self.setManager.logout()
                                    self.registerButton.draw_text(label_key="log")
                                    self.loginButton.draw_text(label_key="log")
                                    self.operat = "login"
                                    self.initGameData()
                                    self.indexButtons["account"].reset()
                                    accShow = False
                        else:
                            # steam版账号相关操作
                            if self.indexButtons["account"].hover_on(pos):
                                accShow = True
                                self.heroBook.update_total_level()
            # =================================================
            # =================== 选关界面 =====================
            elif ( self.page == "stgChoosing" ):

                if REC_DATA["SYS_SET"]["MOD_STOP"]==0:
                    mid = self.paint_right_panel(pos, self.curStg, title=("Adventure Mode","冒险模式"))
                elif REC_DATA["SYS_SET"]["MOD_STOP"]==1:
                    mid = self.paint_right_panel(pos, 0, title=("Endless Mode","无尽模式"))
                
                if self.slide_status=="" or self.slide_status=="in":
                    
                    self.imgButtons["switch"].paint(self.screen, self.embed+120, self.backPosY,
                                                    pos, label=("Change Mode","切换模式") )    # 切换箭头
                    self.imgButtons["practice"].paint(self.screen, self.embed+640, self.backPosY,
                                                    pos, label=("Practice","训练营") )      # training camp
                    if REC_DATA["SYS_SET"]["TUTOR"]==1: # 建议教程
                        img_rec = self.imgButtons["practice"].rect
                        pygame.draw.circle( self.screen, (255,0,0), (img_rec.right,img_rec.top), 7, 0 )

                    if REC_DATA["SYS_SET"]["MOD_STOP"]==0:
                        if self.stgManager.diffi==2:    # 冒险英雄难度深色
                            self.drawRect( self.embed+15, 75, max(bg_size[0]-self.embed-30, 0), bg_size[1]-150, (0,0,0,45) )
                        elif self.stgManager.diffi==0:
                            self.drawRect( self.embed+15, 75, max(bg_size[0]-self.embed-30, 0), bg_size[1]-150, (240,240,240,45) )
                        self.stgManager.updateCompass(self.curStg)  # Compass

                        # 下方左右window
                        r1 = self.addSymm(self.stgManager.windowLeft, mid-145, bg_size[1]//2-62-90)
                        r2 = self.addSymm(self.stgManager.windowRight, mid+145, bg_size[1]//2-62-90)

                        # 关卡封面及前后缩略图
                        leftC = rightC = coverRect = None
                        if len(self.imgSwitcher.SSList)==0:
                            # 左
                            if not (self.curStg == 1):
                                leftC = self.addSymm(self.stgManager.coverAbb[self.curStg-2], mid-140, 0 )
                                if ( leftC.left < pos[0] < leftC.right ) and ( leftC.top < pos[1] < leftC.bottom ):
                                    self.drawRect( leftC.left, leftC.top, leftC.width, leftC.height, (255,255,255,60) )
                                pygame.draw.rect( self.screen, (20,20,20), leftC, 1 )
                            # 右
                            if not ( self.curStg == len(self.stgManager.nameList) ):
                                rightC = self.addSymm(self.stgManager.coverAbb[self.curStg], mid+140, 0 )
                                if ( rightC.left < pos[0] < rightC.right ) and ( rightC.top < pos[1] < rightC.bottom ):
                                    self.drawRect( rightC.left, rightC.top, rightC.width, rightC.height, (255,255,255,60) )
                                pygame.draw.rect( self.screen, (20,20,20), rightC, 1 )
                            # 中
                            coverRect = self.drawCover(self.stgManager.coverList[self.curStg-1], self.stgManager.nameList[self.curStg-1], pos, mid, edge)
                            # draw 3 stars
                            if self.choosable:
                                for i in range(1,4):
                                    if i <= REC_DATA["CHAPTER_REC"][self.curStg-1]:
                                        self.addSymm(self.stgManager.starImg, mid+(i-2)*36, -220 )
                                    else:
                                        self.addSymm(self.stgManager.starVoid, mid+(i-2)*36, -220 )
                                # 下方章节介绍
                                self.addTXT( self.stgManager.infoList[self.curStg][0], self.fntSet[1], mid, 0.925 )
                                self.addTXT( self.stgManager.infoList[self.curStg][1], self.fntSet[1], mid, 0.955 )
                            # UNLOCK BUTTON: if its previous chapter is unlocked, this chapter can be purchased with gems
                            if self.unlockBut:
                                self.stgManager.unlock_button.paint(self.screen, width//2+mid+60, 480, pos)
                                self.stgManager.unlock_guide.paint(self.screen, width//2+mid-60, 480)
                        # 章节设置面板
                        in_but = self.stgManager.panel.paint(self.screen, self.embed-95, 320, pos)
                        # mission task
                        self.addTXT(("[Chapter Mission]","【章节任务】"), self.fntSet[1], mid+145, 0.72, rgb=(255,255,255))
                        self.addTXT(self.stgManager.aimList[self.curStg], self.fntSet[1], mid+145, 0.75, rgb=(255,255,255))
                    
                    elif REC_DATA["SYS_SET"]["MOD_STOP"] == 1:
                        self.stgManager.updateCompass(0)    # Compass

                        # 下方左右window
                        r1 = self.addSymm(self.stgManager.windowLeft, mid-145, bg_size[1]//2-62-90)
                        r2 = self.addSymm(self.stgManager.windowRight, mid+145, bg_size[1]//2-62-90)

                        coverRect = self.drawCover(self.stgManager.endlessCover, ("Statue Guardian","石像守卫者"), pos, mid, edge)
                        # 其他呈现的信息
                        self.drawRect( coverRect.left, coverRect.top, coverRect.width, 24, (255,255,255,120) )
                        self.addTXT( 
                            ("Longest Surival: %d Wave(s)" %REC_DATA["ENDLESS_REC"],"最高存活波数：%d波"%REC_DATA["ENDLESS_REC"]), 
                            self.fntSet[1], mid, 0.2, rgb=(0,0,0) 
                        )
                        if self.choosable:
                            # 下方章节介绍
                            self.addTXT( self.stgManager.infoList[0][0], self.fntSet[1], mid, 0.925 )
                            self.addTXT( self.stgManager.infoList[0][1], self.fntSet[1], mid, 0.955 )
                        # Currently endless mode cannot be purchased!
                        # 挑战设置面板
                        in_but = self.stgManager.panelEndless.paint(self.screen, self.embed-95, 320, pos)
                        # mission task
                        self.addTXT(("[Chapter Mission]","【章节任务】"), self.fntSet[1], mid+145, 0.72, rgb=(255,255,255))
                        self.addTXT(self.stgManager.aimList[0], self.fntSet[1], mid+145, 0.75, rgb=(255,255,255))
                    
                    # 英雄书设置
                    hr_but = self.heroBook.panel.paint(self.screen, self.embed-95, 460, pos)

                    # 符石使用
                    self.stgManager.voidStone.paint(self.screen, r2.right-40, r2.bottom-40, 
                                                    pos, label=self.stgManager.get_stone_name())
                    
                    # compass wave
                    if len(self.spurtCanvas.spatters)<=0:
                        ctr = r1.left+r1.width//2
                        self.spurtCanvas.addWaves( (ctr,580), (255,255,255,250), 16, 14 )
                    # natural decoration:
                    self.imgSwitcher.doSwitch(self.screen)
                    self.spurtCanvas.update(self.screen)
                    self.spurtCanvas.updateHalo(self.screen)
                    # 波动效果
                    if not self.stgManager.delay%5:
                        edge += edgePlus
                        if edge>=5 or edge<=1:
                            edgePlus = -edgePlus

                    # handle the key events
                    if self.slide_status=="":
                        for event in pygame.event.get():  # 必不可少的部分，否则事件响应会崩溃
                            if ( event.type == QUIT ):
                                pygame.quit()
                                sys.exit()
                            elif ( event.type == KEYDOWN ):
                                if REC_DATA["SYS_SET"]["MOD_STOP"]==0 and len(self.imgSwitcher.SSList)==0:
                                    if ( event.key == pygame.K_a ):     # prior
                                        self.soundList[2].play(0)
                                        self.shiftChapter(-1, coverRect, leftC, rightC)
                                    elif ( event.key == pygame.K_d ):   # next
                                        self.soundList[2].play(0)
                                        self.shiftChapter(+1, coverRect, leftC, rightC)
                                if ( event.key == pygame.K_RETURN ):
                                    self.soundList[2].play(0)
                                    res = self.startChapter()       # 若章节不可进入或有任何问题，则会返回字符串消息
                                    if res:
                                        self.msgManager.alert(res)
                            elif event.type == pygame.MOUSEBUTTONUP:
                                if hr_but:
                                    if hr_but.tag=="changeHero":
                                        self.page = "heroBook"
                                        self.slide_status = "in"
                                        self.embed = bg_size[0]
                                    break
                                if REC_DATA["SYS_SET"]["MOD_STOP"]==0:
                                    if in_but:
                                        self.soundList[2].play(0)
                                        if in_but.tag=="diffi":
                                            self.stgManager.diffi = (self.stgManager.diffi+1) % 3
                                            # 更新按钮文字
                                            self.stgManager.panel.updateButton(but_tag="diffi", label_key=self.stgManager.diffi)
                                            REC_DATA["SYS_SET"]["DIFFI"] = self.stgManager.diffi
                                        elif in_but.tag=="P1P2":
                                            if self.heroBook.accList[1]==True:
                                                self.stgManager.P2in = not self.stgManager.P2in
                                                self.stgManager.panel.updateButton(but_tag="P1P2", label_key=self.stgManager.P2in)
                                            else:
                                                self.msgManager.alert("false2P")
                                    else:
                                        if leftC and ( leftC.left < pos[0] < leftC.right ) and ( leftC.top < pos[1] < leftC.bottom ):
                                            self.shiftChapter(-1, coverRect, leftC, rightC)
                                        elif rightC and ( rightC.left < pos[0] < rightC.right ) and ( rightC.top < pos[1] < rightC.bottom ):
                                            self.shiftChapter(+1, coverRect, leftC, rightC)
                                        elif self.unlockBut and self.stgManager.unlock_button.hover_on(pos):
                                            res = self.stgManager.purchaseChapter(self.curStg)
                                            if res=="lackGem":
                                                self.msgManager.alert("lackGem")
                                            elif res=="OK":
                                                self.shiftChapter(0)
                                            break
                                elif REC_DATA["SYS_SET"]["MOD_STOP"]==1:
                                    if in_but:
                                        self.soundList[2].play(0)
                                        if in_but.tag=="startChp":
                                            # 切换无尽模式初始章节
                                            self.stgManager.shiftStartChp()
                                if self.imgButtons["back"].hover_on(pos):
                                    self.soundList[2].play(0)
                                    self.setNature( self.setManager.paperList[REC_DATA["SYS_SET"]["PAPERNO"]]["e"] )
                                    self.slide_status = "out"
                                elif self.imgButtons["switch"].hover_on(pos):
                                    self.soundList[2].play(0)
                                    REC_DATA["SYS_SET"]["MOD_STOP"] = (REC_DATA["SYS_SET"]["MOD_STOP"]+1)%2
                                    if REC_DATA["SYS_SET"]["MOD_STOP"]==1: # 从冒险切换至无尽
                                        self.setNature(3)
                                        self.choosable = self.stgManager.checkChoosable(0)
                                    else:       # 从无尽切换至冒险
                                        self.setNature(self.curStg)
                                        self.choosable = self.stgManager.checkChoosable(self.curStg)
                                elif self.imgButtons["practice"].hover_on(pos):
                                    self.soundList[2].play(0)
                                    self.startPractice()
                                elif coverRect and ( coverRect.left < pos[0] < coverRect.right ) and ( coverRect.top < pos[1] < coverRect.bottom ):
                                    res = self.startChapter()       # 若章节不可进入或有任何问题，则会返回字符串消息
                                    if res:
                                        self.msgManager.alert(res)
                                elif self.stgManager.voidStone.hover_on(pos):
                                    self.soundList[2].play(0)
                                    self.stgManager.shiftStone()
            # ===============================================
            # ================== 图鉴收藏 ====================
            elif ( self.page == "collection" ):
                mid = self.paint_right_panel(pos, 0, title=("Monster Brochure","怪物图鉴"))
                
                if self.slide_status=="" or self.slide_status=="in":
                    # Print title labels.
                    titleList = []
                    i = 0
                    per_w, per_h = 85, 50
                    left = mid -per_w * len(self.collection.subject)//2     # left是第一个标题的左侧。
                    for title in self.collection.subject:
                        if title == self.collection.curSub:
                            bg_rect = self.drawRect( bg_size[0]//2+left+i*per_w, 80, per_w, per_h, (20,20,20,180) )
                        else:
                            bg_rect = self.drawRect( bg_size[0]//2+left+i*per_w, 80, per_w, per_h, (0,0,0,0) )
                        # 检查鼠标是否在最新加入的title rect内
                        if ( bg_rect.left < pos[0] < bg_rect.right ) and ( bg_rect.top < pos[1] < bg_rect.bottom ):
                            bg_rect = self.drawRect( bg_size[0]//2+left+i*per_w, 80, per_w, per_h, (120,120,120,180) )
                        titleList.append( bg_rect )
                        self.addTXT( self.collection.subject[title], self.fntSet[1], left+i*per_w+per_w//2, 0.12 )
                        self.addTXT( self.collection.progress[title], self.fntSet[0], left+i*per_w+per_w//2, 0.15 )
                        i += 1

                    # check all cards whether chosed ---------------------------
                    windowRect = self.addSymm(self.collection.window, mid, 35)    # 将window渲染到screen上
                    innerPos = (pos[0]-windowRect.left, pos[1]-windowRect.top)
                    # 绘制窗口。
                    chosenCd = self.collection.renderWindow( innerPos, self.fntSet[0] )   # 内部渲染刷新，并返回内部退出纽位置
                    
                    # 下方说明
                    self.addTXT( ("For HEROIC Difficulty, HP & PW +50% .","【英雄】难度下，生命和伤害均+50%。"), self.fntSet[1], mid, 0.925 )
                    self.addTXT( ("For EASY Difficulty, HP & PW -30%.","【简单】难度下，生命和伤害均-30%。"), self.fntSet[1], mid, 0.955 )
                    if self.collection.display:
                        in_but = self.collection.panel.paint(self.screen, self.embed+310, 490, pos)
                        #self.imgButtons["quit"].paint(self.screen, self.collection.panel.rect.right, self.collection.panel.rect.top, pos)
                    else:
                        self.addTXT( ("Select a card to show its description.","点击一个卡片，显示其描述。"), self.fntSet[1], mid, 0.66 )
                        self.addTXT( ("Values presented are under the NORMAL Difficulty.","显示的属性值均为“标准”难度下的数值。"), self.fntSet[1], mid, 0.69 )

                    if self.slide_status=="":
                        # handle the key events
                        for event in pygame.event.get():    # 必不可少的部分，否则事件响应会崩溃。
                            if event.type == QUIT:
                                pygame.quit()
                                sys.exit()
                            elif ( event.type == KEYDOWN ):
                                pass
                            elif event.type == pygame.MOUSEBUTTONUP:    # 鼠标单击事件。
                                if (event.button == 1):
                                    # check title.
                                    titleClicked = False
                                    for title in titleList:
                                        if ( title.left < pos[0] < title.right ) and ( title.top < pos[1] < title.bottom ):
                                            self.soundList[2].play(0)
                                            self.collection.curSub = titleList.index(title)
                                            titleClicked = True
                                    if titleClicked:    # Title clicked, should not respond to the click on cards.
                                        continue
                                    if self.imgButtons["back"].hover_on(pos):
                                        self.soundList[2].play(0)
                                        self.collection.display = None
                                        self.slide_status = "out"
                                    # Check monster cards.
                                    else:
                                        if self.collection.display:
                                            if in_but:
                                                self.collection.selectMons(0, 0, tag=in_but.tag)
                                            # 展示monster's detial的情况下，退出按钮被点击
                                            #elif self.imgButtons["quit"].hover_on(pos):
                                            #    self.collection.display = None
                                            #    del self.stgManager.panel.items
                                            #    self.stgManager.panel.items = []
                                        if chosenCd:
                                            i, each = chosenCd
                                            if self.collection.monsList[i][each].acc:
                                                self.collection.selectMons(i, each)
                                            else:
                                                self.msgManager.alert("notFound")
            # ===============================================
            # ================== 英雄  书 ====================
            elif ( self.page == "heroBook" ):
                pgInfo = self.heroBook.turnAnimation()
                mid = self.paint_right_panel(pos, 0, title=("Player 1","角色1") if self.heroBook.playerNo==0 else ("Player 2","角色2"),
                                                bg=pgInfo[0], bg_pos=pgInfo[1])

                if self.slide_status=="" or self.slide_status=="in":
                    # 切换箭头
                    self.imgButtons["switch"].paint(self.screen, self.embed+120, self.backPosY,
                                                        pos, label=("Change Player","切换角色") )
                    
                    # ------- Draw content. ---------
                    # Image.
                    if self.heroBook.accList[self.heroBook.pointer]:
                        self.addSymm(self.heroBook.heroList[self.heroBook.pointer].image, mid-110, -100 )
                    else:
                        self.addSymm(self.heroBook.notFound, mid-110, -100 )
                    windowRect = self.addSymm(self.heroBook.window, mid, 10) # 将window渲染到screen上
                    innerPos = (pos[0]-windowRect.left, pos[1]-windowRect.top)
                    attrPair = self.heroBook.renderWindow( self.fntSet[2], self.fntSet[1], innerPos )

                    if attrPair[1] and attrPair[0] != "RNG":
                        if attrPair[0]=="HP":
                            self.addTXT( ("The max hit point of the hero.","英雄的体力值上限。"), self.fntSet[1], mid, 0.925 )
                        elif attrPair[0]=="DMG":
                            self.addTXT( ("Basic damage of ammo per hit.","每发弹药的每次命中基础伤害。"), self.fntSet[1], mid, 0.925 )
                        elif attrPair[0]=="CNT":
                            self.addTXT( ("Max volume of ammo per loading.","每次填装后的弹药数量上限。"), self.fntSet[1], mid, 0.925 )
                        elif attrPair[0]=="CRIT":
                            self.addTXT( (r"Chance of making critical damage (150% basic damage + stun).","造成暴击伤害的概率（150%倍基础伤害+眩晕）。"), self.fntSet[1], mid, 0.925 )
                        self.addTXT( ("Allocate one SP to strengthen the item. (Level up the hero to gain SP)","消耗一个技能点以强化该属性。（技能点通过升级英雄获得）"), self.fntSet[1], mid, 0.955 )
                                        
                    if self.slide_status=="":
                        # Handle the key events.
                        for event in pygame.event.get():  # 必不可少的部分，否则事件响应会崩溃
                            if ( event.type == QUIT ):
                                pygame.quit()
                                sys.exit()
                            elif ( event.type == KEYDOWN ):
                                if ( event.key == pygame.K_a ):
                                    self.heroBook.turnPage(-1)
                                elif ( event.key == pygame.K_d ):
                                    self.heroBook.turnPage(1)
                                elif ( event.key == pygame.K_RETURN ):
                                    if not self.heroBook.chooseHero():
                                        self.msgManager.alert("falseHero")
                            elif event.type == pygame.MOUSEBUTTONUP:
                                if self.imgButtons["back"].hover_on(pos):
                                    self.soundList[2].play(0)
                                    self.heroBook.pointer = self.heroBook.curHero[self.heroBook.playerNo]     # 索引重置为出战的英雄
                                    self.slide_status = "out"
                                # 检查若为alter player:
                                elif self.imgButtons["switch"].hover_on(pos):
                                    self.soundList[2].play(0)
                                    if self.heroBook.accList[1]==True:
                                        self.heroBook.playerNo = ( self.heroBook.playerNo+1 ) % 2
                                    else:
                                        self.msgManager.alert("false2P")
                                # 在有chosen Attribute Bar的情况下点击鼠标。只要attrPair不为空，就证明此时鼠标悬停在该bar上方。
                                elif self.heroBook.accList[self.heroBook.pointer] and attrPair[1]:
                                    res = self.heroBook.heroList[self.heroBook.pointer].alloSP(attrPair[0])
                                    if type(res)==str:
                                        self.msgManager.alert(res)
            # ================================================
            # ================= 综合设置 ======================
            elif ( self.page == "settings" ):
                mid = self.paint_right_panel(pos, 0, title=("Settings & Update","设置和更新"))
                
                if self.slide_status=="" or self.slide_status=="in":
                    # Print title labels.
                    titleList = []
                    i = 0
                    per_w, per_h = 160, 40
                    left = mid -per_w * len(self.setManager.subject)//2     # left是第一个标题的左侧。
                    for title in self.setManager.subject:
                        if title == self.setManager.curSub:
                            bg_rect = self.drawRect( bg_size[0]//2+left+i*per_w, 80, per_w, per_h, (20,20,20,180) )
                        else:
                            bg_rect = self.drawRect( bg_size[0]//2+left+i*per_w, 80, per_w, per_h, (0,0,0,0) )
                        # 检查鼠标是否在最新加入的title rect内
                        if ( bg_rect.left < pos[0] < bg_rect.right ) and ( bg_rect.top < pos[1] < bg_rect.bottom ):
                            bg_rect = self.drawRect( bg_size[0]//2+left+i*per_w, 80, per_w, per_h, (120,120,120,180) )
                        titleList.append( bg_rect )
                        self.addTXT( self.setManager.subject[title], self.fntSet[1], left+i*per_w+per_w//2, 0.12 )
                        i += 1
                    
                    windowRect = self.addSymm(self.setManager.window, mid, 30)
                    self.setManager.renderWindow( self.fntSet, 
                            (pos[0]-windowRect.left, pos[1]-windowRect.top), self.imgButtons["switch"] )
                    
                    #显示下方提示
                    if self.setManager.currentKey == "keyTitle":
                        self.addTXT( ("Alter the current player to set his/her keys.","变更当前显示的玩家以修改其键位。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey == "language":
                        self.addTXT( ("Set both the written and verbal language of the game.","设置游戏的显示和语音语言。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey == "volume":
                        self.addTXT( ("Set the BGM's volume of the game.","设置游戏背景音乐的音量。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey == "display":
                        self.addTXT( ("Change the display mode of the game.","更改游戏的显示方式。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey == "paper":
                        self.addTXT( ("Set the wall paper of the index page.","设置首页的壁纸。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey == "download":
                        self.addTXT( ("Start downloading new version.","开始下载新版本。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey == "cancel":
                        self.addTXT( ("Once canceled, the downloading have to be restart next time.","取消后，再次下载需要重新开始。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey == "checkAgain":
                        self.addTXT( ("Check game version again.","重新检测游戏版本。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.currentKey and self.setManager.pNo == 1:
                        if self.setManager.currentKey == "leftKey":
                            self.addTXT( ("The key is also effective for shifting PRIOR item in any menu.","该键位也用于在菜单中切换至 前一项。"), self.fntSet[1], mid, 0.93 )
                        elif self.setManager.currentKey == "rightKey":
                            self.addTXT( ("The key is also effective for shifting NEXT item in any menu.","该键位也用于在菜单中切换至 后一项。"), self.fntSet[1], mid, 0.93 )
                        elif self.setManager.currentKey == "downKey":
                            self.addTXT( ("The key is also effective for rolling DOWN in any menu.","该键位也用于在菜单中 向下滚动。"), self.fntSet[1], mid, 0.93 )
                        elif self.setManager.currentKey == "bagKey":
                            self.addTXT( ("The key is also effective for rolling UP in any menu.","该键位也用于在菜单中 向上滚动。"), self.fntSet[1], mid, 0.93 )
                    elif self.setManager.downloader:
                        self.addTXT( ("Downloading in the back end, you can play game normally.","下载在后台进行，你可以正常进行游戏。"), self.fntSet[1], mid, 0.93 )

                    if self.slide_status=="":
                        # handle the key events
                        for event in pygame.event.get():  # 必不可少的部分，否则事件响应会崩溃
                            if ( event.type == QUIT ):
                                pygame.quit()
                                sys.exit()
                            elif ( event.type == KEYDOWN ):
                                if self.setManager.chosenKey == "language":
                                    if ( event.key == pygame.K_a ):
                                        REC_DATA["SYS_SET"]["LGG"] = (REC_DATA["SYS_SET"]["LGG"]-1) % 2
                                    elif ( event.key == pygame.K_d ):
                                        REC_DATA["SYS_SET"]["LGG"] = (REC_DATA["SYS_SET"]["LGG"]+1) % 2
                                    # 所有button的文字替换
                                    for label in self.indexButtons:
                                        if not label=="account":
                                            self.indexButtons[label].draw_text()
                                    # 所有panel内部button的文字替换
                                    for pan in [self.stgManager.panel, self.stgManager.panelEndless, self.heroBook.panel, self.collection.panel, 
                                                self.bazaar.taskPanel, self.accPanel]:
                                        pan.updateButton()
                                    for each in self.bazaar.stonePanels:
                                        each.updateButton()
                                    # 一个单独textbutton的文字替换
                                    self.stgManager.unlock_button.draw_text()
                                elif self.setManager.chosenKey == "volume":
                                    if ( event.key == pygame.K_a ) and ( REC_DATA["SYS_SET"]["VOL"]> 0 ):
                                        REC_DATA["SYS_SET"]["VOL"] -= 10
                                    elif ( event.key == pygame.K_d ) and ( REC_DATA["SYS_SET"]["VOL"]< 100):
                                        REC_DATA["SYS_SET"]["VOL"] += 10
                                    # adjust the volume
                                    pygame.mixer.music.set_volume(REC_DATA["SYS_SET"]["VOL"]/100)
                                    #for snd in self.soundList:
                                    #    snd.set_volume(REC_DATA["SYS_SET"]["VOL"]/100)
                                elif self.setManager.chosenKey == "display":
                                    if ( event.key == pygame.K_a ) or ( event.key == pygame.K_d ):
                                        REC_DATA["SYS_SET"]["DISPLAY"] = (REC_DATA["SYS_SET"]["DISPLAY"]+1) %2
                                        self.setDisplay()
                                elif self.setManager.chosenKey == "paper":
                                    if ( event.key == pygame.K_a ):
                                        REC_DATA["SYS_SET"]["PAPERNO"] -= 1
                                    elif ( event.key == pygame.K_d ):
                                        REC_DATA["SYS_SET"]["PAPERNO"] += 1
                                    REC_DATA["SYS_SET"]["PAPERNO"] %= len(self.setManager.paperList)
                                    self.setNature( self.setManager.paperList[REC_DATA["SYS_SET"]["PAPERNO"]]["e"] )
                                elif self.setManager.chosenKey == "keyTitle":
                                    pass
                                # 剩下的其他情况只有键位设置（如果已经选中rect的话）
                                elif self.setManager.chosenRect:
                                    if ( event.key == pygame.K_RETURN ):   # return保留为暂停/继续，不能让玩家设置
                                        self.msgManager.alert("illegalKey")
                                        continue
                                    self.setManager.changeKey(event.key)
                            elif ( event.type == pygame.MOUSEBUTTONUP ):
                                # check title.
                                titleClicked = False
                                for title in titleList:
                                    if ( title.left < pos[0] < title.right ) and ( title.top < pos[1] < title.bottom ):
                                        self.soundList[2].play(0)
                                        self.setManager.curSub = titleList.index(title)
                                        titleClicked = True
                                if titleClicked:    # Title clicked, should not respond to the click on cards.
                                    continue
                                
                                if self.imgButtons["back"].hover_on(pos):
                                    self.soundList[2].play(0)
                                    self.slide_status = "out"
                                    self.setManager.chosenKey = ""
                                    self.setManager.chosenRect = None
                                elif (event.button==1):
                                    self.setManager.chosenKey = self.setManager.currentKey
                                    self.setManager.chosenRect = self.setManager.currentRect
                                    self.soundList[2].play(0)
                                    if self.setManager.chosenKey == "keyTitle":
                                        self.setManager.alterPNo()
                                    elif self.setManager.chosenKey=="download":
                                        self.setManager.startDownload()
                                    elif self.setManager.chosenKey=="cancel":
                                        self.setManager.closeDownload(complete=False)
                                    elif self.setManager.chosenKey=="checkAgain":
                                        self.setManager.checkVersion()
                                        if self.setManager.updateFlag==0:
                                            self.msgManager.alert("update")
                                        elif self.setManager.updateFlag==-1:
                                            self.msgManager.alert("failure")
                            elif event.type == pygame.MOUSEBUTTONDOWN:  # 鼠标滚轮滚动事件。
                                pass
            # ================================================
            # ================= 市集系统 ======================
            elif ( self.page == "bazaar" ):
                mid = self.paint_right_panel(pos, 0, title=("Capital Bazaar","王城市集"))
                
                if self.slide_status=="" or self.slide_status=="in":
                    windowRect = self.addSymm(self.bazaar.window, mid, 0)
                    self.bazaar.renderWindow( self.fntSet, (pos[0]-windowRect.left, pos[1]-windowRect.top), self.imgButtons["switch"] )
                    self.bazaar.myStonePanel.paint(self.screen, windowRect.left+200, windowRect.bottom-160, pos)
                    
                    if self.bazaar.currentKey == "reroll":
                        self.addTXT( (f"Spend {self.bazaar.reroll_cost} gems, change a new batch of runestones.",f"花费{self.bazaar.reroll_cost}宝石，更换一批新的符石。"), self.fntSet[1], mid, 0.93 )

                    # handle the key events
                    if self.slide_status=="":
                        for event in pygame.event.get():  # 必不可少的部分，否则事件响应会崩溃
                            if ( event.type == QUIT ):
                                pygame.quit()
                                sys.exit()
                            elif ( event.type == KEYDOWN ):
                                pass
                            elif ( event.type == pygame.MOUSEBUTTONUP ):
                                if self.imgButtons["back"].hover_on(pos):
                                    self.soundList[2].play(0)
                                    self.slide_status = "out"
                                    self.setManager.chosenKey = ""
                                    self.setManager.chosenRect = None
                                elif (event.button==1):
                                    if self.bazaar.currentKey == "reroll":
                                        res = self.bazaar.reroll()
                                        if res=="lackGem":
                                            self.msgManager.alert("lackGem")
                                    else:
                                        res = self.bazaar.buy_stone()
                                        if res=="OK":
                                            self.addStones(tag=self.bazaar.currentKey, pos=pos, tgt=self.bazaar.myStonePanel)
                                        elif res=="lackGem":
                                            self.msgManager.alert("lackGem")
            # ===============================================
            # ================== 登陆注册 ====================
            elif ( self.page == "login" ):
                # 绘制背景板和标题文字
                baseRect = self.drawRect( width//2-240, height//2-140, 480, 280, (40,40,40,180) )
                title = self.drawRect( baseRect.left+10, baseRect.top+10, baseRect.width-20, 40, (20,20,20,180) )
                self.addTXT(("Account Center","账号中心"), self.fntSet[2], 0, 0.32)

                if self.operat == "login":
                    # 绘制文本框
                    self.tbManager.paint(self.screen, ["username","password"])

                    # button
                    self.registerButton.paint(self.screen, width//2-100, height//2+110, pos)
                    self.loginButton.paint(self.screen, width//2+100, height//2+110, pos)
                    # 右上Guest Login
                    self.imgButtons["quit"].paint( self.screen, title.right, title.top, pos, label=("Guest Player","游客试玩") )

                elif self.operat == "reset_pwd":
                    # 绘制文本框
                    self.tbManager.paint(self.screen, ["password"])

                    self.addTXT( ("You are resetting your password.","您正在修改密码。"), self.fntSet[1], 0, 0.41 )
                    self.addTXT( ("New one should be different from the previous one.","新的密码需要与上一个不同。"), self.fntSet[1], 0, 0.44 )
                    # button
                    self.registerButton.paint(self.screen, width//2-100, height//2+110, pos)
                    self.loginButton.paint(self.screen, width//2+100, height//2+110, pos)

                self.addTXT( ("Basic English/Chinese characters are accepted for all boxes.",
                        "所有文本框仅接受基本英文字符和中文字符（生僻字除外）。"), 
                        self.fntSet[1], 0, 0.925 )
                self.addTXT( ("If you forget the password, email [throde1998@163.com] or contact us on Wechat [KnightThrode].",
                        "如果您忘记了密码，可发送邮件至【throde1998@163.com】，或通过微信公众号【KnightThrode】留言联系我们。"), 
                        self.fntSet[1], 0, 0.955 )

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        # 调用文本框键盘按下事件
                        if self.tbManager.safe_key_down(event):
                            # 按下回车，所有输入框失去焦点
                            self.tbManager.set_active("")
                    elif event.type == pygame.MOUSEBUTTONUP:
                        # every time click the button, refocus the textboxes.
                        self.tbManager.set_active(self.tbManager.hover_on(pos))
                        # execute actions
                        if self.operat == "login":
                            if self.registerButton.hover_on(pos):
                                self.confirmInput("register")
                            elif self.loginButton.hover_on(pos):
                                self.confirmInput("login")
                            elif self.imgButtons["quit"].hover_on(pos):
                                # 用户要求以游客身份登录
                                self.page = "index"
                                self.tbManager.reset( ["username","password"] )
                                self.indexButtons["account"].reset()
                        elif self.operat == "reset_pwd":
                            if self.registerButton.hover_on(pos):   # 取消
                                self.tbManager.reset( ["password"] )
                                self.page = "index"
                            elif self.loginButton.hover_on(pos):
                                self.confirmInput("reset_pwd")
            
            # move flying gems
            for gem in self.gemList:
                gem.move( delay=0 )
                gem.paint(self.screen)
            # Nature Effect.
            self.nature.update(self.screen)
            # Message Window.
            self.msgManager.run()
            self.msgManager.paint(self.screen)
            pygame.display.flip()
            clock.tick(60)
    
    def paint_right_panel(self, pos, color_n, title=(), bg=None, bg_pos=()):
        mid = self.embed//2
        # left and right side panel
        #self.drawRect( 0, 0, self.embed, bg_size[1], (60,60,60,120) )
        self.drawRect( self.embed, 60, max(bg_size[0]-self.embed, 0), bg_size[1]-120, self.stgManager.themeColor[color_n] )
        # bg image
        if bg:
            self.addSymm(bg, mid, bg_pos)
        # upper and lower banner
        self.drawRect( self.embed, 0, max(bg_size[0]-self.embed, 0), 60, self.stgManager.themeColor[0] )
        self.drawRect( self.embed, bg_size[1]-60, max(bg_size[0]-self.embed, 0), 60, self.stgManager.themeColor[0] )
        # title
        if title:
            self.addTXT( title, self.fntSet[2], mid, 0.03 )
        # back arrow
        self.imgButtons["back"].paint(self.screen, self.embed+50, self.backPosY, pos, label=("Back","返回主界面") )

        # move and check slide embed
        if self.embed>self.embedFinal and self.slide_status=="in":
            self.embed -= max( round((self.embed-self.embedFinal)/self.embedSpd), 2)
            if self.embed <= self.embedFinal:
                self.slide_status = ""
        elif self.embed<bg_size[0] and self.slide_status=="out":
            self.embed += max( round((bg_size[0]-self.embed)/self.embedSpd), 2)
            if self.embed >= bg_size[0]:
                self.page = "index"
        
        return mid

    def confirmInput(self, operation):
        # 无账号，注册
        if operation=="register":
            # 检查注册格式
            if len(self.tbManager.get_text("username"))>12 or len(self.tbManager.get_text("username"))<1:
                self.msgManager.alert("passAlarm")
                self.tbManager.set_alarm(["username"])
                return
            # 检查网络（同时下载所需数据）
            if not self.setManager.checkAccount(self.tbManager.get_text("username"), "nickname"):
                self.msgManager.alert("failure")
                return
            # 尝试检查nickname是否存在
            if self.setManager.accExist==True:
                self.msgManager.alert("nicknameEx")
                self.tbManager.set_alarm(["username"])
                return
            # 至此，账号已无问题，检查密码格式
            if not 6<=len(self.tbManager.get_text("password"))<=12:
                self.msgManager.alert("passAlarm")
                self.tbManager.set_alarm(["password"])
                self.tbManager.reset(["password"])
                return
            # 检查全部通过
            res = self.setManager.register_account(self.tbManager.get_text("password"))
            if res != "OK":
                self.msgManager.alert(res)
        
        # 已有账号，登录
        elif operation=="login":
            # 检查网络
            if self.setManager.checkAccount(self.tbManager.get_text("username"), "nickname")==False:
                self.msgManager.alert("failure")
                return
            # 检查账号是否存在
            if self.setManager.accExist==False:
                self.msgManager.alert("nicknameNotEx")
                self.tbManager.set_alarm(["username"])
                return
            # 检查password是否匹配（若正确则直接登录完成）
            if not self.setManager.checkAccount(self.tbManager.get_text("password"), "password"):
                # 密码错误，清空并提示
                self.msgManager.alert("falsePassword")
                self.tbManager.set_alarm(["password"])
                self.tbManager.reset(["password"])
                return
        
        # 已登录状态，修改密码
        elif operation=="reset_pwd":
            # 检查网络
            if self.setManager.checkAccount(self.tbManager.get_text("username"), "nickname")==False:
                self.msgManager.alert("failure")
                return
            # 检查密码格式
            if not 6<=len(self.tbManager.get_text("password"))<=12:
                self.msgManager.alert("passAlarm")
                self.tbManager.set_alarm(["password"])
                self.tbManager.reset(["password"])
                return
            # 检查全部通过，发送重置密码
            res = self.setManager.reset_account("password", self.tbManager.get_text("password"))
            if res == "OK":
                self.msgManager.alert(res)
            else:
                self.msgManager.alert(res)
                self.tbManager.set_alarm(["password"])
                self.tbManager.reset(["password"])
                return
            
        self.page = "index"
        self.indexButtons["account"].reset()
        # 文件和数据下载完成后，更新程序中的数据
        self.initGameData()

    def shiftChapter(self, to, coverRect=None, leftC=None, rightC=None):
        if len(self.imgSwitcher.SSList)>0:
            return
        if to==-1:
            if (self.curStg == 1):
                return
            self.imgSwitcher.addSwitch(self.stgManager.coverList[self.curStg-1], coverRect, 0.4, 120, 30, time=6)   # 向右退位
            self.imgSwitcher.addSwitch(self.stgManager.coverAbb[self.curStg-2], leftC, 3.1, 120, -30, time=6)       # 左侧上位
        elif to==1:
            if ( self.curStg == len(self.stgManager.nameList) ):
                return
            self.imgSwitcher.addSwitch(self.stgManager.coverList[self.curStg-1], coverRect, 0.4, -120, 30, time=6)  # 向左退位
            self.imgSwitcher.addSwitch(self.stgManager.coverAbb[self.curStg], rightC, 3.1, -120, -30, time=6)       # 右侧上位
        self.curStg += to
        # save chpter stop info.
        REC_DATA["SYS_SET"]["STG_STOP"] = self.curStg
        self.setNature(self.curStg)
        self.choosable = self.stgManager.checkChoosable(self.curStg)
        self.unlockBut = True if (REC_DATA["SYS_SET"]["MOD_STOP"]==0) and (not self.choosable) and (REC_DATA["CHAPTER_REC"][self.curStg-2]>=0) else False

    def startChapter(self):
        if not self.choosable:
            return "falseStg"
        
        try:
            going = True
            if REC_DATA["SYS_SET"]["MOD_STOP"] == 0:
                if self.curStg>6:
                    hostage = None
                # 判断p1所选英雄是否与人质重合。
                elif self.heroBook.heroList[self.heroBook.curHero[0]].no==self.curStg:
                    hostage = self.heroBook.heroList[0]
                else:
                    hostage = self.heroBook.heroList[self.curStg]
                # 玩家英雄信息。
                if not self.stgManager.P2in:
                    playerList = [ (self.heroBook.heroList[self.heroBook.curHero[0]],self.setManager.keyDic1,"p1") ]
                else:
                    playerList = [ (self.heroBook.heroList[self.heroBook.curHero[0]],self.setManager.keyDic1,"p1"), 
                        (self.heroBook.heroList[self.heroBook.curHero[1]],self.setManager.keyDic2,"p2") ]
                # 正式进入游戏循环：
                #self.setManager.changeProcessState("adventure")
                #print(">>章节开始前",psutil.Process(os.getpid()).memory_info().rss)
                while going:
                    # Note: accList会在model中直接被操作。
                    mod = model.AdventureModel( self.curStg, playerList, self.screen, REC_DATA["SYS_SET"]["LGG"], self.fntSet, 
                                                self.stgManager.diffi, self.collection.monsList[self.curStg], 
                                                hostage, stone=self.stgManager.stone_in_use )
                    # 返回的going：True表示winning，False表示failing. (由go()函数最后的conclusion界面确定。)
                    going = mod.go( self.soundList, self.heroBook, self.stgManager, self.stgManager.diffi, REC_DATA["SYS_SET"]["VOL"], self.bazaar.task )
                    mod.clearAll()  # 清除主要元素，释放内存
                    del mod
                    # 结算符石数量
                    self.stgManager.decr_stone()
                #self.setManager.changeProcessState("index")
                #print(">>章节结束",psutil.Process(os.getpid()).memory_info().rss)
            elif REC_DATA["SYS_SET"]["MOD_STOP"] == 1:
                pygame.mixer.music.fadeout(1000)
                #self.setManager.changeProcessState("endless")
                #print(">>章节开始前",psutil.Process(os.getpid()).memory_info().rss)
                while going:
                    # 从已选择的章节开始
                    mod = model.EndlessModel( self.stgManager.startChp, self.setManager.keyDic1, self.screen, REC_DATA["SYS_SET"]["LGG"], 
                                            self.fntSet, self.collection.monsList[self.curStg], 
                                            self.heroBook.heroList[self.heroBook.curHero[0]], stone=self.stgManager.stone_in_use )
                    going = mod.go( self.soundList, self.heroBook, self.stgManager, self.setManager, REC_DATA["SYS_SET"]["VOL"], self.bazaar.task )
                    mod.clearAll()
                    del mod
                    # 结算符石数量
                    self.stgManager.decr_stone()
                #self.setManager.changeProcessState("index")
                #print(">>章节结束",psutil.Process(os.getpid()).memory_info().rss)
            # 每次章节结束后，都更新主界面任务栏状态
            self.bazaar.update_task(prog_only=True)
        except:
            self.msgManager.alert( "NULL" )
            print(traceback.format_exc())
    
    def startPractice(self):
        playerList = [ (self.heroBook.heroList[self.heroBook.curHero[0]],self.setManager.keyDic1,"p1") ]
        mod = model.TutorialModel( playerList, self.screen, REC_DATA["SYS_SET"]["LGG"], self.fntSet, 
                                    self.stgManager.diffi, self.collection.monsList[self.curStg], 
                                    tutor_on=True, stone=self.stgManager.stone_in_use )#bool(REC_DATA["SYS_SET"]["TUTOR"])
        res = mod.go( self.soundList, self.heroBook, self.stgManager, self.stgManager.diffi, REC_DATA["SYS_SET"]["VOL"], self.bazaar.task )
        # 教程已完成，可以关闭推荐，从1置为0（1表示待完成）
        if res==True and REC_DATA["SYS_SET"]["TUTOR"]==1:
            REC_DATA["SYS_SET"]["TUTOR"] = 0
        mod.clearAll()
        del mod
        # 结算符石数量
        self.stgManager.decr_stone()

    def drawCover(self, cover, chpName, pos, mid, edge):
        coverRect = self.addSymm(cover, mid, -40 )
        if ( coverRect.left < pos[0] < coverRect.right ) and ( coverRect.top < pos[1] < coverRect.bottom ):
            self.drawRect( coverRect.left, coverRect.top, coverRect.width, coverRect.height, (255,255,255,60) )
        # 关卡序号和关卡名
        self.drawRect( coverRect.left, coverRect.bottom-100, coverRect.width, 70, (0,0,0,110) )
        if REC_DATA["SYS_SET"]["MOD_STOP"]==0:
            self.addTXT( (f"CHAPTER {self.curStg}",f"第{self.curStg}章"), self.fntSet[2], mid, 0.555 )
        elif REC_DATA["SYS_SET"]["MOD_STOP"]==1:
            self.addTXT( (f"EXTRA CHAPTER",f"特殊章节"), self.fntSet[2], mid, 0.555 )
        # 关卡可选，则给出关卡名；否则加上灰色幕布和锁🔒
        if self.choosable:
            self.addTXT( chpName, self.fntSet[3], mid, 0.6 )
        else:
            self.drawRect( coverRect.left, coverRect.top, coverRect.width, coverRect.height, self.stgManager.themeColor[0] )
            self.addSymm(self.stgManager.lock, mid, -40 )
            if REC_DATA["SYS_SET"]["MOD_STOP"]==0:
                self.addTXT( (f"Complete CHAP. {self.curStg-1} to unlock",f"通过第{self.curStg-1}章以解锁本章"), self.fntSet[1], mid, 0.61 ) # 关卡名处用这句提示代替
            elif REC_DATA["SYS_SET"]["MOD_STOP"]==1:
                self.addTXT( (f"Complete CHAP. 7 to unlock",f"通过第7章以解锁本模式"), self.fntSet[1], mid, 0.61 ) # 关卡名处用这句提示代替
        # 边框
        pygame.draw.rect( self.screen, (250,250,250), coverRect, 1 )
        edgeRect = ( (coverRect.left-edge,coverRect.top-edge), (coverRect.width+2*edge,coverRect.height+2*edge) )
        pygame.draw.rect( self.screen, (0,0,0), edgeRect, 1 )
        return coverRect
        
    def setNature(self, stg):
        '''# Shift nature effect according to stg. Varies according to self.curStg.'''
        self.nature = None
        if stg in (1,3):  # 漂浮粒子
            self.nature = Nature(bg_size, stg, 10, 1)
        elif stg == 2:      # 下落碎石
            self.nature = Nature(bg_size, stg, 5, 0)
        elif stg in (4,7):  # 雨水
            self.nature = Nature(bg_size, stg, 18, 0)
        elif stg == 5:      # 雪花
            self.nature = Nature(bg_size, stg, 11, -1)
        elif stg == 6:      # 电焊花火
            self.nature = Nature(bg_size, stg, 8, 1)
        
    def addGems(self, num, pos, tgt, cList=[20,22,24]):
        if num==0:
            return False
        for i in range(0, num):
            randPos = [ randint(pos[0]-1, pos[0]+1), randint(pos[1]-1, pos[1]+1) ]
            speed = [ randint(-2,2), randint(-4,-1) ]
            gem = Coin( randPos, choice( cList ), speed, tgt, typ="gem" )
            self.gemList.add( gem )
    
    def addStones(self, tag, pos, tgt):
        stone = Coin( list(pos), cnt=22, speed=[0,-4], tgt=tgt, typ=f"stone_{tag}")
        self.gemList.add(stone)
    
    def setDisplay(self):
        if REC_DATA["SYS_SET"]["DISPLAY"]==0:
            self.screen = pygame.display.set_mode( (bg_size) )
        elif REC_DATA["SYS_SET"]["DISPLAY"]==1:
            self.screen = pygame.display.set_mode( (bg_size), pygame.FULLSCREEN|pygame.HWSURFACE )

    def addSymm(self, surface, x, y):       # Surface对象； x，y为正负（偏离中心点）像素值
        rect = surface.get_rect()
        rect.left = (width - rect.width) // 2 + x
        rect.top = (height - rect.height) // 2 + y
        self.screen.blit( surface, rect )
        return rect                   # 返回图片的位置信息以供更多操作

    def addTXT(self, txt, font, x, y, rgb=(255,255,255)):
        '''txt文本内容(各语言的同义元组)；rgb（0，0，0）； x为正负（偏离中心线）像素值； y为0-1的百分数'''
        txt = font[REC_DATA["SYS_SET"]["LGG"]].render(txt[REC_DATA["SYS_SET"]["LGG"]], True, rgb)
        rect = txt.get_rect()
        rect.left = (width - rect.width) // 2 + x
        rect.top = height * y
        self.screen.blit( txt, rect )
        return rect                   # 返回文字的位置信息以供更多操作
        
    def drawRect(self, x, y, width, height, rgba):
        surf = pygame.Surface( (width, height) ).convert_alpha()
        rect = surf.get_rect()
        rect.left = x
        rect.top = y
        surf.fill( rgba )
        self.screen.blit( surf, rect )
        return rect


# ======================================================================
# invoke main() & start the program if this is the main module
if __name__ == "__main__":
    try:
        theGod = God()
        theGod.go()
    except SystemExit:
        # 系统正常退出
        pass
    finally:
        with open('./record.sav', 'wb') as f:
            pickle.dump(REC_DATA, f)
        if PLATFORM=="self":
            # 结束游戏时，上传记录至云端
            if REC_DATA["GAME_ID"] != 1:
                theGod.setManager.transmitFile(op="upload")
                print(">> Saving Record (sysexit)...")
                time.sleep(0.5)
        pygame.quit()
