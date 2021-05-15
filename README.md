# Project Introduction
"Knight Throde" is a PC game based on Python (maily Pygame). More development details can be found in the Chinese instruction pdf file.

If you use Wechat, you can subscribe our Official Account: KnightThrode

《焕焕骑士》是一款基于Python（主要为Pygame）开发的单机电脑游戏。更多开发细节可在中文pdf文件中查看。如果您使用微信，您可以订阅我们的官方公众号：KnightThrode。

Game v7.4.3 has been released on Steam. You can access all the resources after downloading the game there. For old versions, you can also get full game packages on our game website.


# Developer/Tester's Account
You can use the given developer/tester's game record file so that you can quickly review all the game contents: record.sav

But if you want to experience the whole game progress from a player's perspective, you may need to remove the given .sav file and then simply start the game (the program will create a new one for you). In this way you will start fresh, and unlock chapters/heroes one by one. 

您可以使用此repo附带的开发者、测试者游戏记录文件：record.sav来游玩，以快速体验所有游戏内容。但如果您希望从玩家的角度体验整个游戏流程，您可以移除所给的.sav文件，然后直接启动游戏（程序会自动为您创建一个新记录）。这样您就可以开始一个全新记录，逐关解锁章节。

# Missing Resources
Resources (three folders-"image", "audio", and "font") could be found from game zip files. 
Download game zip of correct version and place these three folders with codes (12 altogether), then run main.py.


# Updates on Codes for Game v7.4.3
You may find the architecture different from the instruction pdf, big changes include:
1. We split "mapManager" module into three smaller modules: "mapTowers", "mapElems", and "canvas".
2. We make "props" an independent module (from "myHero").
3. We make "specifier" an independent module (from "model").

You can find notes about each module's duty at the beginning of each file.
