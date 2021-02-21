# Project Introduction
Knight Throde is a PC game based on Python (Pygame). More details can be found in the Chinese instruction pdf file.

Our Chinese website of the game: www.knightthrode.cn

# Developer's Account
You can use this public developer's account to log in, so that you can quickly review all the game contents:

Account Name: throde
Password: 123456

But if you want to experience the whole game flow from a player's perspective, you may need to register a new account for yourself. You will start fresh, and unlock chapters/heroes one by one.

# Missing Resources
Resources (three folders-"image", "audio", and "font") could be found from game zip files. 
Download game zip of correct version and place these three folders with codes (12 altogether), then run main.py.

Game v7.4.3 has been released on Steam. You can access all the resources after downloading the game there. For old versions, you can also get full game packages on our game website.

# Updates on Codes for Game v7.4.3
You may find the architecture different from the instruction pdf, big changes include:
1. We split "mapManager" module into three smaller modules: "mapTowers", "mapElems", and "canvas".
2. We make "props" an independent module (from "myHero").
3. We make "specifier" an independent module (from "model").

You can find notes about each module's duty at the beginning of each file.
