# -*- coding: utf-8 -*-
"""
플롯매니저.py:
이 모듈은 다음과 같은 모든 메뉴 페이지의 수업 관리를 담당하는 텍스트 및 멀티미디어 자원 관리 모듈입니다.
모험 모드에서 플롯 대화를 트리거하는 추적 상호 작용 관리
몬스터 컬렉션의 데이터 및 인터페이스 관리
히어로북의 데이터 및 인터페이스 관리
네트워킹, 다운로드, 다이아몬드, 룬석 상점, 버튼 설정 등을 위한 데이터 및 인터페이스 관리
"""
from threading import Thread
import pygame
from random import choice, sample

from database import MB, DT, REC_DATA, TB, RB
import database
from util import TextButton, ImgButton, Panel, RichText
from util import generateShadow, drawRect


VERSION = "KT_7.4.3"


# ==============================================================================================
# ==============================================================================================
class Dialogue():
    # Words of Pre Info part ----------------
    chp1_1 = [ ("조심하세요,탑 전체가 용들이 차지하고 있어요.                      흩어진 상자에서 보급품을 구할 수 있습니다.", 
                "请小心，我的英雄！整座塔楼都被龙族占据，你可以从散落的宝箱中获得补给。"), 
                ("다음 구역의 문을 열 수 있도록 구역 키퍼로 표시된 몬스터를              처치해야 합니다.", 
                "务必要击杀那些标记为区域守卫的怪物，只有这样才能开启通往下一区域的大门。")
            ]
    chp1_2 = [ ("Have to face more monsters and worse environment from now on...", 
                "现在开始不得不面对更多怪物和更糟糕的环境了……"), 
                ("I know there's a Tour Merchant in the next tower, pass this area and find him for some help if you need!", 
                "我知道在下一塔楼处有一个旅行商人，请通过这个区域找到他，看看能不能从他那里获得一些帮助！")
            ]
    chp1_3 = [ ("I'm so glad you come! This final area is the home to Crimson Dragon,", 
                "你能来到这里我真是太高兴了！这块最终区域是猩红巨龙的老巢，"), 
                ("Use coolers, fruits, rings... anything you have to defend his fire, and defeat him!", 
                "用上清凉饮料，水果和戒指……你目前拥有的任何道具，抵挡他的火焰，并击败他！") 
            ]

    chp2_1 = [ ("Take these two caps, you'll need them. And watch the falling columns, ",
                "拿着这两个雷管，你会用得着的。还有当心上方的落石，"),
                ("those tough stones wouldn't be anything under your musket, I believe.", 
                "我相信在你的火枪之下，这些坚硬的石头也算不上什么。") 
            ]
    chp2_2 = [ ("There are more those blue giant cave dwellers in this cave- and more rolling rocks coming...", 
                "在这个洞穴里还有更多的这些蓝色大块头穴居人——这也意味着前方还有更多的滚落巨石……"), 
                ("They help construct the spider nest, and spiders provide preys as food for them. What a nostorious pair!", 
                "这些家伙为蜘蛛建造巢穴，而蜘蛛则为他们捕猎提供食物。真是臭名昭著的一对邻居！") 
            ]
    chp2_3 = [ ("I promise to you, my sis. I will never make such stupid adventure alone...", 
                "我向你保证，妹妹，我再也不会一个人搞这种愚蠢的冒险了……"), 
                ("But this time let's finish this crazy one, kill the Giant Spider! Hurray!", 
                "但这次让我们一起完成这次疯狂的冒险，击杀巨型魔蛛！冲啊！") 
            ]

    chp3_1 = [ ("Thanks for coming, kid! This graveyard is loomed under the dark magic,", 
                "谢谢你来救我，孩子！这片墓地现在笼罩在黑魔法之下，"), 
                ("Spooky creatures resurged from the earth. Keep a distance with them, especially those infectious vomits!", 
                "恐怖的生物从地下复活。和它们保持一定距离，尤其是那些具有感染性的呕吐物！") 
            ]
    chp3_2 = [ ("Deeper in the yard, denser the mist. Torches from previous adventurers are available in the chests.", 
                "越往墓地深处，黑暗迷雾就越浓。宝箱中有以往探险者遗落的火炬，"), 
                ("They will help with your sight and luminate a circle area.", 
                "它们能扩大视野，照亮你周遭的一片区域。") 
            ]
    chp3_3 = [ ("Under the cover of darkness, an evil vampire is wandering. She stifles my power of nature.", 
                "在这黑暗之中，有一个吸血鬼在游荡。正是她压制住了我的自然之力。"), 
                ("I need you to find her out and take her down, trace her by the purple smoke around her!", 
                "我需要你把她找出来并消灭，你可以根据她散发的紫色烟雾来追踪她。")
            ]
    
    chp4_1 = [ ("This village is raided by creatures from the forest. Most villagers are gone.", 
                "这个村子受到了雨林生物的侵袭。大多数的村民都逃走了。"), 
                ("As the only remaining hunter here, I need to investigate this. Pollution, it is pollution...", 
                "作为唯一留下的猎人，我需要深入雨林探查此事。是污染，是污染……"), 
            ]
    chp4_2 = [ ("Giant insects, toxic sprouts, overly-bred worms... they are mutated.", 
                "巨型昆虫，剧毒孢子，过度繁殖的蠕虫……它们都变异了。"),
                ("I have no idea about the source of pollution. Maybe it's from human world? Or dark magic?", 
                "我不太清楚污染的源头。也许是来自人类世界？也许是黑魔法？") 
            ]
    chp4_3 = [ ("This is the center of the forest, also the most badly polluted area.", 
                "这里是森林的中心，也是污染最严重的地带。"), 
                ("I feel we are close to the truth... Please help us, eliminate all those disgusting stuffs!", 
                "我感觉我们离真相很近了……请帮助我们，把所有这些恶心的东西都给消灭！") 
            ]
    
    chp5_1 = [ ("Dwellers built some totems over the mountain, which bring health to all the mountain creatures.", 
                "原住民在雪山上建造了许多图腾，这些图腾能够给雪山生灵带去生命和治疗。"), 
                ("Try to destroy them so that make those monsters weaker.", 
                "尽量摧毁这些图腾，从而让那些猛兽好对付些。") 
            ]
    chp5_2 = [ ("Fists of Blizzard is a great impediment here. And eagles like to snap climbers up under its cover.", 
                "间歇的暴风雪是在这里行进的一大阻碍。有些老鹰喜欢在风雪的掩护下偷袭登山者。"),
                ("Cheer up, anyway! Cross this area and reach me! I know where to find our king.", 
                "无论如何请振作起来！穿过这片区域，和我汇合！我知道在哪里能够找到我们的国王。") 
            ]
    chp5_3 = [ ("No prince dare to challenge this ancient Titan. She is the god worshipped by all the dwellers.", 
                "历史上没有一个王子敢挑战前方的冰霜泰坦。她是守所有原住民朝拜的巨神。"), 
                ("But I'm afraid we will have to step on her territory... May holylight bless us!", 
                "但恐怕我们不得不踏上它的领地了……愿圣光庇护我们！"), 
            ]
    
    chp6_1 = [ ("I wanted to shelter here, but the factory has betrayed me.", 
                "我原想在此避难，谁知整坐工厂都叛变了。"), 
                ("Along with the dwarf workers, those battle machines also turn against us.", 
                "更严峻的是，那些侏儒工人操纵的机械装置也与我们为敌了。") 
            ]
    chp6_2 = [ ("The factory has many defensesm, but we can't just end here, my people!", 
                "兵工厂机关重重，但我们绝不能在这里倒下，我的子民！"), 
                ("These helicopters are very hard to tackle, but there's a way! Missle guns can help you a lot.", 
                "激光飞行器是最为棘手的机器，但总会有办法应对！火箭炮能帮到你！") 
            ]
    chp6_3 = [ ("Damn it, they activated the WarMachine! It was originally made to serve me!", 
                "糟了……侏儒工人启动了战争机器！这原本是我命令打造的秘密武器！"), 
                ("Well, let's see how powerful it is in practice...by countering it!", 
                "好吧，让我们看看它在实战中的表现究竟如何……我们与他抗衡！") ]

    chp7_1 = [ ("I admire your gut, brother. You lost your kingdom, your power, your everything.", 
                "我敬畏你的勇气，哥哥。你失去了你的王国，你的权力，你已一无所有。"), 
                ("...But you returned. Look at this majestic, beautiful capital, under my govern.", 
                "……但你竟然回来了。看看这座在我统治下，巍峨美丽的都城吧。") ]
    chp7_2 = [ ("Why can't you just give up and go home? This kingdom need to fight, it need to invade.", 
                "你为什么就不能放下，回家养老呢？这个国家需要战争，需要侵略。"), 
                ("I will bring this land a more promise future. You just need to belive it, Ashiley.", 
                "我会带给这片土地一个更加光明的未来。雅士利，你们所需的，只是相信这一点就可以了。"), 
            ]
    chp7_3 = [ ("You will finally see... I'll show you... Yes, we may need another talk...", 
                "你终将会明白的……我会让你彻底明白的……是啊，看来我们能确实需要再谈一谈……"), 
                ("You bring death to yourself, not me! ou have to know who's the better to rule this kingdom.", 
                "是你自己给自己招致了死亡，不要责怪我！你必须要知道谁才是更适合治理这个国家的人。") 
            ]
    
    tips = [ # general tip
        ("Hero's backpack can hold different items you find in chests.", "你的背包可以容纳从宝箱里获得的不同物品。按切换键"),
        ("Press AlterItem Key to change and UseItem Key to use ", "来切换当前的背包物品，按使用键来使用当前的背包物品。"),
        ("the current available item.", "")
    ], [
        ("It's a good habit to eat up your fruits as soon as you can in", "在墓地里及时把身上携带的水果都吃了是个好习惯。"),
        ("the graveyard. Once you get infected you will have to cry about", "因为一旦不慎感染成了丧尸，即使背包里装着十多个"),
        ("your life despite dozens of fruits in your bagpack.","水果，濒死的时候你也只能望果兴叹了。")
    ], [
        ("If you are not interested in any of the goods the merchant is", "如果你对商人出售的所有商品都不感兴趣，你可以花2个金币"),
        ("selling, pay 2 coins to make him update all.", "让他全部更新一批新货。")
    ], [
        ("Every hero has his or her unique characteristics and strengths.", "每个英雄都有自己独特的属性和长处。他们也都有自己擅长"),
        ("They are always better at some certain cicumstances. It's hard", "应对的场合。很难说谁更厉害——但总有你最喜欢的。"),
        ("to say who's stronger-but it's good to have your favorite.","")
    ], [
        ("Your ammunition is infinite but backpack items are limited.","英雄弹药是无限的，而其他背包物品是有限的，"),
        ("However, you'll need time to reload. A magic glove will speed up the process.","但你需要时间来重新填装。一只神奇手套可以加速填装。")
    ], [
        ("In Adventure Mode when calculating the result of a game, for each 2 coins","在冒险模式中结算游戏结果时，每2枚硬币可以换得1点经验值。"),
        ("you get 1 point of exp. So coin is half value of exp. Endless Mode will not","所以硬币的价值是经验的一半。尽管无尽模式中也可以收集金币，"),
        ("give you exp, although you can also collect coins there.","但他们在游戏最后不会转化为经验。")
    ], [
        (r"Critical damage can be randomly achieved. It deals 150% damage of basic DMG,","暴击伤害会以一定概率随机打出。暴击造成基础伤害的150%，"),
        ("pushes targets back more, and also stuns targets for 0.5 seconds.","击退力更强，还会眩晕目标0.5秒。")
    ], [  # About Adventure Model
        ("In Adventure Model of Heroic Difficulty you will face much stronger", "在“英雄”难度的冒险模式中，你会面对更加凶残、"),
        ("Enemies. Any of high level or good skill is needed.", "更加坚韧的怪物。高等级、好技术，你至少得有一样。")
    ], [
        ("In Adventure Model, only when all the Area Guardians are", "冒险模式中，只有所有被标记的敌人都被消灭后，才能解锁区域"),
        ("eliminated can you access the next area. Check how many Guardians", "门。可以通过左上角的数字来实时查看当前区域还剩下多少个"),
        ("remaining in the current area through upper-left indicator.", "怪物守卫。")
    ], [
        ("In Adventure Model, different tower may have different natural", "冒险模式中，不同的地域会有不同的自然阻碍。"),
        ("impediments. However, you can always find some helpful equipments", "但是你总能从宝箱中发现有用的工具来克服这些困难，"),
        ("from chests to fight against them. Be grateful to former adventurers.","这都要感谢你的前任冒险者们。")
    ], [
        ("In Adventure Model, you can carry the rescued immediately, or", "冒险模式中，你可以直接带上要营救的对象继续冒险，"),
        ("clear up the tower alone and return to get the hostage.", "但是你也可以独自清理出一条前路，然后回来捎上人质。")
    ], [  # About Endless Model
        ("BiteChest is special for Endless Model. It's a bonus!","咬咬宝箱是无尽模式特有的怪物。它其实是个奖励！"),
        ("Cracking it can gain you about 6 to 10 coins.", "打爆它就可以获得约6至10个金币。")
    ], [
        ("In Endless Model, you will come across a stage Boss per 5 waves.", "无尽模式中，每5波就会迎来一只关卡Boss。"),
        ("Killing them rewards you handsome coins!", "击杀它可以获得极为可观的金币奖励！")
    ], [
        ("In Endless Model, you will face more elite enemies and", "无尽模式中，会遇到越来越多的精英怪物，以及愈发"),
        ("tougher impediments- elites don't give you extra coins, though.", "恶劣的环境阻碍——但怪物越强并不意味着更多的金币。")
    ], [
        ("In Endless Model, you can employ a servant as your assistant.","无尽模式中，你可以雇佣一个侍从来协助你战斗。"),
        ("She will kill enemy and earn coins for you. She also wears an armor that","她会杀死怪物，并替你挣得金币。她还穿有一身轻甲，"),
        ("enable her to take reduced damage (30 percents less).","能够帮助她减轻所受的伤害（30%减伤）。")
    ], [
        ("No supply chest is provided in Endless Model. But you can","无尽模式中不会提供任何的补给箱。但你可以在每波结束时"),
        ("buy any item you need from the merchant at the end of each wave.","从商人那里买到任何你需要的物品。")
    ]
    
    #字典，指向所有的关卡信息。
    allPre = { 1:[chp1_1, chp1_2, [], chp1_3, []], 
        2:[chp2_1, chp2_2, [], chp2_3, []], 
        3:[chp3_1, chp3_2, [], chp3_3, []], 
        4:[chp4_1, chp4_2, [], chp4_3, []], 
        5:[chp5_1, chp5_2, [], chp5_3, []], 
        6:[chp6_1, chp6_2, [], chp6_3, []], 
        7:[chp7_1, chp7_2, [], chp7_3, []] }
    preList = []    #只存储当前关卡pre的列表

    # Words of Interaction part -----------------
    propExplan = {
        "ammo":[("For the rest of this challenge,","在本次挑战的剩余时间内，"), ("your hero gains +1 ammo limit.","英雄的弹药容量提升+1。")],
        "fruit":[("[Instant] Basic for treatment.","【即时性物品】回复体力的基本手段。"), ("Recover 10 HP after used.","使用后回复10点体力。")],
        "loadGlove":[("[Instant]","【即时性物品】"), ("Immediately finish loading ammos.","立刻完成投掷物的填装。")],
        "servant":[("Summon a 800HP/50DMG servant","召唤一名800体力值、50伤害值，"),("with 30 percent hit reduction to reinforce you. ","拥有百分之30减伤的侍从来援助你战斗。")],
        "defenseTower":[("[Durable]","【持续性物品】"), ("Help defende monstors!","帮助抵挡入侵的怪物！")],
        
        "cooler":[("[Durable] Can be found in Dragon Castle.","【持续性物品】可发现于巨龙城堡。"), ("For a while prevent 65 percent of fire type damage.","一段时间内，减免受到的火焰伤害的65%。")],
        "toothRing":[("[Durable] Can be found in Dragon Castle.","【持续性物品】可发现于巨龙城堡。"), ("Instantly fill your ammos full and, till your next reload,","立即填满你的弹药，并且直到下一次重新填装"), ("all your normal shoots become critical!","之前，所有的普通射击必定暴击！")], 
        
        "herbalExtract":[("[Durable] Can be found in Underground Cave.","【持续性物品】可发现于地下洞穴。"), ("Slowly recover up to 300 HP with in 5 sec,","在5秒内缓慢恢复至多300点体力，"), ("but will be terminated if hero get hitted.","但是一旦受到伤害，治疗效果便会终止。")], 
        "blastingCap":[("[Instant] Can be found in Underground Cave.","【即时性物品】可发现于地下洞穴。"), ("Cast it out and it will deal 500 explosive damage","扔出后，它将对巨大范围内的所有"), ("to all destructible stuffs within a huge range!","可摧毁物均造成500点巨额伤害！")], 
        
        "torch":[("[Durable] Can be found in Grave Yard.","【持续性物品】可发现于亡灵乐园。"), ("Expands your horizon in dark mist and luminates Area Keepers.","在黑暗迷雾中扩大可见范围，并照亮区域守卫。"), ("Enemies within its range get continuous burned.","范围内的敌人还会受到持续灼伤。")], 
        "medicine":[("[Instant] Can be found in Grave Yard.","【即时性物品】可发现于亡灵乐园。"), ("Cure the infected hero; if user is not infected, ","使用后将治愈受到感染的英雄；如果使用者未感染，"), ("heal 100 HP instead.","改为回复100点体力。")], 
        
        "copter":[("[Durable] Can be found in Ooze Forest.","【持续性物品】可发现于软泥雨林。"), ("Enable user to fly freely for a while.","使英雄获得一段时间的自由飞行能力。")], 
        "pesticide":[("[Durable] Can be found in Ooze Forest.","【持续性物品】可发现于软泥雨林。"), ("Spray pesticide to the air to kill insects!","向空中喷洒杀虫剂来消灭这些昆虫！")], 
        
        "alcohol":[("[Durable] Can be found in Frozen Peak.","【持续性物品】可发现于冰雪孤峰。"), ("For a while prevent 60 percent of freezing type damage,","一段时间内，减免受到的冰冻伤害的60%，"), ("drinker immune to the freezing effect.","并免疫冰冻减速效果。")], 
        "battleTotem":[("[Durable] Can be found in Frozen Peak.","【持续性物品】可发现于冰雪孤峰。"), ("Set a Totem that help you in the battle!","设置一个图腾，帮助你在战斗中更强大！"), ("Regularly supplies you with 1 ammo when in the same area.","处于同一区域时，它会有规律地填充你的弹药。")], 
        
        "simpleArmor":[("[Durable] Can be found in Antique Factory.","【持续性物品】可发现于古旧工厂。"), ("Equiper gain 240 armors to prevent from injury.","获得240点护甲值，保护装备者免于外界伤害。"), ("Actions won't be interrupted until it's broken.","装备期间的行动不再会因受伤而中断。")], 
        "missleGun":[("[Durable] Can be found in Antique Factory.", "【持续性物品】可发现于古旧工厂。"), ("Replace your ammo with 4 missles.","将你的远程武器替换为4枚火箭弹。"), ("Each missle aims at AIR enemy and deals 400 damage.","每枚火箭弹自动瞄准飞行生物，造成400点伤害。")],
        
        "shieldSpell":[("[Durable] Can be found in Riot Capital.","【持续性物品】可发现于动荡王城。"), ("For a while prevent 65 percent of physical type damage.","一段时间内，减免受到的物理伤害的65%。")],
        "rustedHorn":[("[Instant] Can be found in Riot Capital.","【即时性物品】可发现于动荡王城。"), ("Stun enemies in a large range, and for each enemy within range","眩晕大片范围内的敌人，吹号范围内每有一个敌人便"), ("restore 30 HP for all allies.","为所有友方角色回复30点体力。")]
    }
    
    # ====================================================================
    # Constructor of Dialogue Manager ------------------------------------------
    def __init__(self, stg):
        # initialize the properties of the object
        if stg:
            self.preList = self.allPre[stg]
    
    def getPre(self, area):
        if area==-1:
            return []
        else:
            return self.preList[area]


# ==============================================================================================
# ==============================================================================================
class StgManager():
    nameList = [ ("Dragon Castle","恶龙城堡"), ("Gloomy Cave","地下洞穴"), ("Dead Yard","亡灵乐园"), ("Ooze Forest","软泥雨林"),
        ("Frozen Peak","冰雪孤峰"), ("Deserted Factory","古旧工厂"), ("Riot Capital","动荡王城") 
    ]
    infoList = [ [("Stands the grand statue of the king, this storeroom","这个贮藏室内伫立着国王的伟大石像，"), ("is also the favorite target for hatred monsters all over the world.","它也是各地充满仇恨的怪物的首要目标。")],
        [("Used to be a millitary fort of the kindom,","这座堡垒原本是王国边境的军事岗哨，"), ("until occupied by the rude dragon for dwelling.","后来被不讲道理的巨龙占去做了窝。")],
        [("They talk about diamonds in this cave,","人们谈论的都是这座山洞里的钻石、水晶，"), ("but the stones and the dwellers.","却只字不提那些诡异的石头和恐怖的穴居人……")],
        [("Only royal families can be buried here.","只有高贵的皇族才能埋葬在这块墓地中，"), ("Skeletons will imply the history of the kingdom.","数数骷髅的数量就知道王国的历史有多悠久了。")],
        [("Forest outside capital is perfect for hunting,","皇城郊外的这片密林是天然的狩猎场，"), ("only for those who are the best.","但只有最优秀的猎人才能安然归来。")],
        [("North of the kindom is high snow moutains.","王国最北边是常年冰雪的高山，"), ("Princes are sent here for a year before throned.","将任大位的王子一般都会送往这里历练一年。")],
        [("Before the terrible havoc it made weapons,","荒废前，是集造武器、造战车于一体的大型兵工厂，"), (" vehicles, and lovely toys for royal babies.","也会给皇城的小王子、小公主做玩具。")], 
        [("The Capital is built with silver-covered bricks.","皇城的城砖镀上了亮闪闪的白银，"), ("But it never shines in its dark time.","可在黑暗之时只剩下了冰凉与死寂。")]
    ]
    aimList = [
        ("Keep both you and the King Statue safe.","尽可能地保证你和国王石像安全。"),
        ("Lead the trapped Princess out.","引导受困的公主离开塔楼。"),
        ("Lead the trapped Prince out.","引导受困的王子离开塔楼。"),
        ("Lead the trapped Wizard out.","引导受困的法师离开塔楼。"),
        ("Lead the trapped Huntress out.","引导受困的女猎手离开塔楼。"),
        ("Lead the trapped Priest out.","引导受困的牧师离开塔楼。"),
        ("Lead the trapped King out.","引导受困的国王离开塔楼。"),
        ("Defeat the Boss, General Chicheng.","击败章节Boss，赤诚将军。"),
    ]
    # color (RGB)   中性：灰黑         关卡一：红         关卡二：深蓝           关卡三：紫            关卡四：绿          关卡五：浅蓝         关卡六：浅黄          关卡七：灰白
    alp = 220
    themeColor = [ (40,40,40,alp), (200,100,100,alp), (90, 90, 160, alp), (180, 90, 210, alp), (90, 180, 90, alp), (140, 140, 220, alp), (180, 180, 90, alp), (160, 160, 160, alp) ]#, (210, 160, 170, alp) ]
    # 绝对位置     endless     chp1    chp2       chp3        chp4        chp5       chp6       chp7
    compassPos = [(25,-120), (85,-10), (65,-90), (20,-210), (-120,-135), (-140,0), (-65,-40), (-30,-120) ]
    unlock_cost = 50

    # ====================================================================
    # Constructor of StgManager ------------------------------------------
    def __init__(self, width, height, font):
        self.delay = 0
        # 初始化关卡封面
        self.coverList = [pygame.image.load("image/cover1.jpg").convert(), pygame.image.load("image/cover2.jpg").convert(), pygame.image.load("image/cover3.jpg").convert(), 
            pygame.image.load("image/cover4.jpg").convert(), pygame.image.load("image/cover5.jpg").convert(), pygame.image.load("image/cover6.jpg").convert(), 
            pygame.image.load("image/cover7.jpg").convert() ]
        self.endlessCover = pygame.image.load("image/coverEndless.jpg").convert()
        # 封面缩略图
        self.coverAbb = []
        for each in self.coverList:
            coverAbb = pygame.transform.smoothscale( each, (90, 120) )
            self.coverAbb.append( coverAbb )
        # 初始化compass
        self.windowLeft = pygame.Surface( (width//2, height) ).convert_alpha()
        self.compass = pygame.image.load("image/compass.png").convert_alpha()
        self.curPos = list(self.compassPos[0])
        self.windowRight = pygame.Surface( (width//2, height) ).convert_alpha()
        self.windowRight.fill( (0,0,0,120) )
        # 其他图标
        self.difficultyIcon = pygame.image.load("image/selected.png").convert_alpha()
        self.lock = pygame.image.load("image/lock.png").convert_alpha()
        self.starImg = pygame.image.load("image/star.png").convert_alpha()
        self.starVoid = generateShadow(self.starImg, color=(20,20,20,180))

        stoneImgDic = { tag: pygame.image.load(f"image/runestone/{tag}.png") for tag in RB }
        stoneImgDic["VOID"] = pygame.image.load("image/runestone/voidStone.png")
        self.voidStone = ImgButton( stoneImgDic, "VOID", font, labelPos="btm" )
        self.stone_in_use = "VOID"      # should be stone tags

        # difficulty: (-1-incomplete;) 0-easy; 1-normal(default); 2-heroic
        self.diffi = REC_DATA["SYS_SET"]["DIFFI"]
        self.P2in = False            # 初始默认为single，即P2不参战
        # Chapter Settings Panel -----------
        self.panel = Panel(180, 150, font, title=("게임 설정","章节设置"))
        self.panel.addItem( ("- 난이도 -","- 游戏难度 -") )
        self.panel.addItem( TextButton(160,30,
            {0:("쉬움","简单"), 1:("중간","标准"), 2:("어려움","英雄")}, self.diffi, font), tag="diffi"    
        )
        self.panel.addItem( ("- P2 Join -","- 玩家2参战 -") )
        self.panel.addItem( TextButton(160,30,
            {True:("P2 In","P2参战"), False:("P2 Out","P2不参战")}, self.P2in, font), tag="P1P2" 
        )
        # Endless Settings Panel -----------
        self.startChp = 1
        self.panelEndless = Panel(180,150, font, title=("Challenge Settings","挑战设置"))
        self.panelEndless.addItem( ("- Start Chapter -","- 起始章节 -") )
        nameDic = {}
        for i in range(len(self.nameList)):
            nameDic[i+1] = self.nameList[i]
        self.panelEndless.addItem( TextButton(160,30,
            nameDic, self.startChp, font), tag="startChp"
        )
        # unlock guide
        self.unlock_button = TextButton( 120, 30, {"default":("Unlock","解锁")}, 
            "default", font, rgba=(40,120,40,210) )
        self.unlock_guide = RichText( (f"or spend _IMG_{self.unlock_cost}",f"或消耗 _IMG_{self.unlock_cost}"), 
                pygame.image.load("image/gem0.png").convert_alpha(), font) 
        
    def updateCompass(self, nxt):
        self.delay = (self.delay+1)%240
        # Compass
        self.windowLeft.fill( (0,0,0,0) )
        self.curPos[0] += (self.compassPos[nxt][0]-self.curPos[0])//8
        self.curPos[1] += (self.compassPos[nxt][1]-self.curPos[1])//8
        rect = self.compass.get_rect()
        rect.left = self.curPos[0]
        rect.top = self.curPos[1]
        self.windowLeft.blit(self.compass, rect)
    
    def checkChoosable(self, stg):
        # Endless Mode: final chapter should have been passed
        if stg==0 and REC_DATA["CHAPTER_REC"][-1]>0:
            return True
        # Adventure Mode: as long as the chapter has been unlocked
        elif REC_DATA["CHAPTER_REC"][stg-1]>=0:
            return True
        else:
            return False
        
    def purchaseChapter(self, stg):
        # check gems
        if REC_DATA["GEM"] < self.unlock_cost:
            pygame.mixer.Sound("audio/alert.wav").play(0)
            return "lackGem"
        # currently only advent mode will be unlocked this way
        REC_DATA["CHAPTER_REC"][stg-1] = 0
        REC_DATA["GEM"] -= self.unlock_cost
        pygame.mixer.Sound("audio/coin.wav").play(0)
        return "OK"

    def shiftStartChp(self):
        self.startChp = self.startChp%len(self.nameList)+1
        self.panelEndless.updateButton(but_tag="startChp", label_key=self.startChp)
        
    def shiftStone(self):
        li_form = [ tag for tag in REC_DATA["STONE"] ]
        li_form.insert(0, "VOID")

        for i in range( len(li_form) ):    
            if li_form[i]==self.stone_in_use:
                new_indx = (i+1)%len(li_form)
                self.stone_in_use = li_form[new_indx]
                self.voidStone.changeKey(self.stone_in_use)
                return
    
    def get_stone_name(self):
        # 作为按钮标签信息，同时也会显示个数信息
        if self.stone_in_use in RB:
            nm = RB[self.stone_in_use].name
            ct = REC_DATA["STONE"][self.stone_in_use]
            return (f"{nm[0]}({ct})", f"{nm[1]}({ct})")
        else:
            return ("No Runestone","不使用符石")
        
    def decr_stone(self):
        if self.stone_in_use != "VOID":
            REC_DATA["STONE"][self.stone_in_use] -= 1
            if REC_DATA["STONE"][self.stone_in_use] <= 0:
                REC_DATA["STONE"].pop(self.stone_in_use)
                self.stone_in_use = "VOID"
                self.voidStone.changeKey(self.stone_in_use)
    
    def renewRec(self, indx, newVal, gameMod=0):
        # 冒险通关信息，检查、更改信息
        if ( gameMod == 0 ):
            # 这里newVal规定为难度级别值+1（原0-简单，1-标准，2-困难），故比原纪录大则更新。
            if newVal+1 > REC_DATA["CHAPTER_REC"][indx]:
                REC_DATA["CHAPTER_REC"][indx] = newVal+1
                # 若下一章未解锁，则将之解锁（最后一章解锁时，无需考虑后一章）
                if indx < len(self.nameList)-1:
                    if REC_DATA["CHAPTER_REC"][indx+1] <0:
                        REC_DATA["CHAPTER_REC"][indx+1] = 0
                return True
        # EndlessMode，更新分数
        elif (gameMod == 1):
            if newVal>REC_DATA["ENDLESS_REC"]:
                REC_DATA["ENDLESS_REC"] = newVal
                return True
        return False
    
    def getHigh(self):
        return REC_DATA["ENDLESS_REC"]


# ==============================================================================================
# ==============================================================================================
class Collection():

    # Monster Collection部分:------------------------
    monsList = [ None, {}, {}, {}, {}, {}, {}, {} ]   # 分关卡存储所有7关的怪物（访问序号1~7）；其中第0个是未解锁的虚怪兽模型
    card = None
    cardOn = None
    board = None

    cardY = [ -150, 10, 190, 370, 550 ]
    cardRect = []      # 按序保存所有cardrect引用的列表（行优先）
    display = None     # 显示大图查看详情的标记，用于指示应当显示某个坐标的怪物（VMons类型）。None表示不显示。

    # 一些界面的参数，显示元素的窗口。------------------
    subject = { 0:("Chap.1","第1章"), 1:("Chap.2","第2章"), 2:("Chap.3","第3章"), 3:("Chap.4","第4章"), 4:("Chap.5","第5章"), 
        5:("Chap.6","第6章"), 6:("Chap.7","第7章") }
    progress = { 0:("0/0","0/0"), 1:("0/0","0/0"), 2:("0/0","0/0"), 3:("0/0","0/0"), 4:("0/0","0/0"), 
        5:("0/0","0/0"), 6:("0/0","0/0")}
    window = None
    WDRect = None

    # ====================================================================
    # Constructor of Collection ------------------------------------------ 
    def __init__(self, width, height, stgName, font):
        # initialize the properties of the object
        self.curSub = 0
        # 以下是怪物图鉴部分 ----------------------------------------------
        self.stgName = stgName
        self.monsList[0] = VMons( "Unknown",(0,0),["Kill one to collect in adventure model.","在冒险模式中击杀一只此怪物来收集它。"], "lock.png" )
        # CHPT-1
        stg = self.monsList[1]
        stg["tizilla"] = VMons( "tizilla",(1,0),
            ["Many wonder how can Tizilla walk in fire. But no one has answer cause seekers are all eaten up.","很多人好奇弟斯拉为什么可以在火里行走，但始终没有答案，因为去问的人都被吃了。"], "stg1/tizilla0.png" )
        stg["megaTizilla"] = VMons( "megaTizilla",(1,1),
            ["Mature but dull, and more homely-looking. Anyway, you'll be roasted if you dare comment on his nose.","成熟多了，却也变得行动迟缓。比起小时候还丑了许多。如果你胆敢当面这么评论的话，它会把你烤熟。"], "stg1/megaTizilla1.png" )
        stg["dragon"] = VMons( "dragon",(1,2),
            ["Never touch his head for his loveliness. If you insist doing so, tie up his smoking mouth first.","不要看火龙宝宝可爱就上去摸他的脑袋。如果非要这么做，请先把他冒烟的嘴巴捆上。"], "stg1/dragonLeft1.png" )
        stg["dragonEgg"] = VMons( "dragonEgg",(1,3),
            ["Very valuable in the market for its nutritive yolk. Perhaps edible - who knows.","因为营养丰富的卵黄，在市场上能卖很多钱。或许能吃吧——谁知道呢。"], "stg1/dragonEgg_all.png" )
        stg["CrimsonDragon"] = VMons( "CrimsonDragon",(1,4),
            ["You successfully draw her attention. That usually won't be longer than a few secs.","你成功引起了她的注意。通常来说，这不会超过几秒钟。"], "stg1/RedDragon_All.png" )
        # CHPT-2
        stg = self.monsList[2]
        stg["bat"] = VMons( "bat",(2,0),
            ["Lovely sprite of the dark cave. Perfect if they don't hurt you.","幽暗洞穴中可爱的小精灵。如果不伤人就完美了。"], "stg2/bat1.png" )
        stg["golem"] = VMons( "golem",(2,1),
            ["These stuffs are so hard that they can be perfect construction materials.","这些家伙又结实又坚硬，可以当作建造别墅的好材料。"], "stg2/golemLeft0.png" )
        stg["bowler"] = VMons( "bowler",(2,2),
            ["Live in this cave for generations. They use stones to kick out invaders.","他们世世代代生活在这个洞穴里，用滚石击退入侵者。"], "stg2/bowler0.png" )
        stg["spider"] = VMons( "spider",(2,3),
            ["Don't worry- they are not toxic. But it still feels bad if you got biten...","别担心——他们没有毒。但是被咬了还是很疼的！"], "stg2/miniSpider0.png" )
        stg["GiantSpider"] = VMons( "GiantSpider",(2,4),
            ["The most awesome creature in the cave, queen of the spiders. Beaware of her webs!","洞穴中最令人畏惧的生物。是蜘蛛母后。当心她的蛛网！"], "stg2/Spider_All.png" )
        # CHPT-3
        stg = self.monsList[3]
        stg["skeleton"] = VMons( "skeleton",(3,0),
            ["It is as vunerable as a pile of bones -well so is him. But when you get hundreds of them, you end up there.","小骷髅兵脆的像个骨架——好吧他们本来就是。但是他们源源不断地从地下冒出来时，你想逃跑也逃不掉了。"], "stg3/skeletonLeft0.png" )
        stg["dead"] = VMons( "dead",(3,1),
            ["They walk slowly and bite slowly... and you ill quicly. DAMN!","一步两步，一口两口……然后你也成了僵尸。真要命！"], "stg3/deadMale0.png" )
        stg["ghost"] = VMons( "ghost",(3,2),
            ["Floating in the grave yard, as confused as when they are alive. When killed for the first time, they come back with a thinner body- for revenge.","他们在墓园中游荡，就像生前一样的迷茫。在第一次被击碎后，他们拖着更加稀薄的身体回来——为了复仇。"], "stg3/ghost0.png" )
        stg["Vampire"] = VMons( "Vampire",(3,3),
            ["She lives by these souls and feeds the undead. You may understand totally when she steals your blood with her scythe.","靠收割灵魂为生，养活不死生物。当她用镰刀挥向你并吸血时，你会体会的更深。"], "stg3/Vampire_All.png" )
        # CHPT-4
        stg = self.monsList[4]
        stg["snake"] = VMons( "snake",(4,0),
            ["Very sneaky and very aggressive! They will lower themselves to avoid attack.","非常狡猾，极富侵略性！他们会匍匐贴地来躲避敌人的攻击。"], "stg4/snake0.png" )
        stg["slime"] = VMons( "slime",(4,1),
            ["You might feel disgusting, but they are great cleaners of the forest. Once hitted through a fortunate trajectory, you can see one split into two.","你可能会感到很恶心，但它们为这片雨林的清洁做出了巨大贡献。如果你攻击的角度合适，就有机会看到它们分裂出另一只软泥怪。"], "stg4/slime6.png" )
        stg["nest"] = VMons( "nest",(4,2),
            ["It gives birth to worms continuously, which may drop on your head... Surprise, hah?","这堆虫卵会源源不断地孵出小蠕虫，冷不丁掉在你的头上，然后炸开……惊不惊喜，意不意外？"], "stg4/nest0.png" )
        stg["fly"] = VMons( "fly",(4,3),
            ["The Coleopter has the hardest shell, do you have the finest weapon?","硬壳甲虫有世界上最硬的壳，你有世界上最锋利的箭吗？"], "stg4/flyLeft0.png" )
        stg["MutatedFungus"] = VMons( "MutatedFungus",(4,4),
            ["Because of the pollution from human world, it has mutated into a terrible giant floating thing. Its tentacle is dangerous. And toxic sprouts is constantly bred from its surface!","因为来自人类世界的污染，它变异成了一个可怕的漂浮巨物。它的触须很危险，它的表皮还会不断孵化出有毒的孢芽！"], "stg4/MutatedFungus_all.png")
        # CHPT-5
        stg = self.monsList[5]
        stg["wolf"] = VMons( "wolf",(5,0),
            ["Aggressive Snow Wolf lives in the north peak. His fur is very favored by bold hunters.","北方雪山上攻击性极强的雪狼，胆大的猎人最喜欢它那暖和的皮毛。"], "stg5/wolf0.png" )
        stg["iceTroll"] = VMons( "iceTroll",(5,1),
            ["Clumsy and cool, Piercing and powerful.","笨拙而冷酷，无情又强壮。"], "stg5/iceTroll0.png" )
        stg["iceSpirit"] = VMons( "iceSpirit",(5,2),
            ["Floating in the air, following the wind. On collision with any target it will explode and freeze him/her!","漂浮在空中，随着冷风飘。一旦撞上任何目标，它就会爆炸，并冻结他/她！"], "stg5/iceSpirit.png" )
        stg["eagle"] = VMons( "eagle",(5,3),
            ["Flying over the ice mountain, and assaults to the frightened prey!","盘旋在冰川之上，突然俯冲向呆滞的猎物！"], "stg5/eagleLeft0.png" )
        stg["FrostTitan"] = VMons( "FrostTitan",(5,4),
            ["Guardian of the Ice Peak, bring blessing to the villagers and other animals on the mountain. But she hates invadors and will cast huge snowballs to them. It's not that easy to avoid since the balls will split into more.","冰封之巅的守护神，给山上的原住民和其他生灵带去幸福。但是她极其讨厌入侵者，会用巨大的雪球招待他们。她的雪球并非那么容易能够躲过，因为它们会溅射成为更多个！"], "stg5/FrostTitan_all.png" )
        # CHPT-6
        stg = self.monsList[6]
        stg["dwarf"] = VMons( "dwarf",(6,0),
            ["They are small, and they are angry. It's the rigid boss to be blame.","他们身材虽小，却满脸戾气，这都是因为那严苛的工头导致的。"], "stg6/dwarf0.png" )
        stg["gunner"] = VMons( "gunner",(6,1),
            ["Tough robots with powerful machine guns and wide inspection ranges. Lower your head, or turn into grids.","这些坚固的小机器人拥有火力密集的机枪和极大的探测范围。你要么低下头避开它的扫描，要么直面它的红眼然后变成筛子。"], "stg6/gunner0.png" )
        stg["lasercraft"] = VMons( "lasercraft",(6,2),
            ["Basically made out of offcuts, thus not very reliable. Hovers behind the sidewalls, and strike through the blocks... as well as you.","原料基本都是废铜烂铁，所以并非那么牢靠。它们悬停于边墙后方，发射激光击穿墙壁……顺带击穿你。"], "stg6/lasercraft0.png" )
        stg["WarMachine"] = VMons( "WarMachine",(6,3),
            ["Designed by the best mechanic of the kingdom, but never practice in a war yet. Looks clumsy, but he can fly... and launch missles that chase you.","由全王国最优秀的技工设计完成，但还从来没有投入到战场上使用过。虽然看上去有些笨重，但他能飞，还能发射导弹追着你。"], "stg6/WarMachine_All.png" )
        # CHPT-7
        stg = self.monsList[7]
        stg["guard"] = VMons( "guard",(7,0),
            ["Cladded with heavy armors. With spear and shield in hand, he can defend any attack directly to him.","身披重甲，手执长矛和大盾，能防御来自正面的任何攻击！"], "stg7/guard_All.png" )
        stg["flamen"] = VMons( "flamen",(7,1),
            ["Corrupted by the dark magic. Their Soul Blast is now cast toward innocent people, draining them to death.","被黑魔法所腐蚀的王国祭司。她们的灵魂震爆现在扔向了无辜的人们，汲取他们的生命直至死亡。"], "stg7/flamenAtt1.png" )
        stg["assassin"] = VMons( "assassin",(7,2),
            ["Elite and cold assassin serving Chicheng. Dash towards target in an incredible speed.","听命于赤诚的冷血精英女刺客。以恐怖的速度向着目标冲刺。"], "stg7/assassin0.png" )
        stg["Chicheng"] = VMons( "Chicheng",(7,3),
            ["Brother of King Yashiley. Leader of the rebellian. The most powerful general within the kingdom. No one can stop him. Invincible. His heavy arm decrease damage of any kind.","雅士利国王的弟弟，这次叛军的领导者，整个王国势力最强大的将军。没人能阻止他。无敌。他那厚重的铠甲能替他减免任何伤害。"], "stg7/cc_all.png" )
        
        self.card = pygame.transform.smoothscale( pygame.image.load("image/card.png").convert_alpha(), (102, 136) )  # 比例保持3：4
        self.cardOn = pygame.Surface( self.card.get_size() ).convert_alpha()
        self.cardOn.fill( (240,240,240,60) )
        # create the window to display cards.
        self.window = pygame.Surface( (width, height) ).convert_alpha()
        self.width = width
        self.height = height
        self.window.fill( (20, 20, 20, 160) )
        # initialize all cards and their rects.
        for i in (1,2,3,4,5,6,7):     # 逐关地初始化VMons的rect信息。
            x = -230
            for each in self.monsList[i]:
                self.monsList[i][each].rect = self.addSymm( self.card, x, self.cardY[0] )
                x += 115
        
        # Monster Description Card.
        self.panel = Panel(540, 300, font, align="left")
        # Init collection progress
        self.renewProgress()

    def renderWindow(self, pos, font):
        # clear the window canvas.
        self.window.fill( (0,0,0, 0) )
        self.window.fill( (20,20,20, 180) )
        lgg = REC_DATA["SYS_SET"]["LGG"]
        
        # Chapter title
        drawRect( 10, self.cardY[0]+160, self.width-20, 20, (190,190,190,60), self.window )
        self.addTXT(self.stgName[self.curSub][lgg], font[lgg], (250,250,250), self.width//2, self.cardY[0]+170)

        chosen = ()
        # 仅绘制当前章节的怪物
        cp_list = self.monsList[self.curSub+1]
        for each in cp_list:   # monsList[0]是空白mons，从1开始是第一章
            c = cp_list[each].rect
            self.window.blit( self.card, c )    # card背景
            # 把monster图片blit到cardbase上。
            if cp_list[each].acc:
                self.addSymm( cp_list[each].image, c.left+c.width//2-self.width//2, c.top+c.height//2-self.height//2 )
            else:
                self.addSymm( self.monsList[0].image, c.left+c.width//2-self.width//2, c.top+c.height//2-self.height//2 )
            # 若已选中，加一个边框
            if cp_list[each]==self.display:
                pygame.draw.rect( self.window, (255,255,255,200), c, 3 )
            # 若在等待选中时鼠标悬停，高亮显示
            if ( c.left < pos[0] < c.right ) and ( c.top < pos[1] < c.bottom ):
                self.window.blit( self.cardOn, c )
                drawRect( c.left, c.bottom-20, c.width, 20, (255,255,255,180), self.window )
                self.addTXT(cp_list[each].name[lgg], font[lgg], (0,0,0), c.left+c.width//2, c.bottom-10)
                chosen = (self.curSub+1, each)
        # 显示是否是当前正在使用的壁纸。
        '''if i+j*2==REC_DATA["SYS_SET"]["PAPERNO"]:
            self.addSymm( pygame.image.load("image/active.png").convert_alpha(), self.paperX[i]+90, self.paperY[j]+60 )'''
        return chosen
    
    def selectMons(self, i, j, tag=None):
        if not tag:
            self.display = self.monsList[i][j]
            self.panel.clear()
            # Add Name
            self.panel.title = self.display.name
            # Add Attributes
            curMons = self.display.attr
            for item in dir(curMons)[::-1]:
                value = getattr(curMons, item)
                if value:
                    if item=="health":
                        txt = (f"Hitpoint: {value}",f"生命值：{value}")
                        self.panel.addItem( txt )
                    elif item=="damage":
                        txt = (f"Damage: {value}",f"伤害值：{value}")
                        self.panel.addItem( txt )
                    elif item=="dmgType":
                        txt = (f"Damage Type: {value}",f"伤害类型：{DT[value]}")
                        self.panel.addItem( txt )
                    elif item=="armor":
                        txt = (f"Injure Dent: {int(value*100)}%",f"受伤减免：{int(value*100)}%")
                        self.panel.addItem( txt )
                    elif item=="coin":
                        txt = (f"Coin Value: {value}",f"金币价值：{value}")
                        self.panel.addItem( txt )
                    else:
                        continue
            if curMons.child:
                self.panel.addItem( ("Deriva: ","衍生物：") )
                for child in curMons.child:
                    cname = MB[child].name
                    self.panel.addItem( TextButton(140, 28,
                        {"default": cname}, "default", self.panel.font, rgba=(180,120,20,180)),
                        tag=child, inline=True
                    )
            # Desc Txt
            i = 0
            self.panel.addItem( ("","") )
            while i<len(self.display.desc[0]):
                self.panel.addItem( (self.display.desc[0][i], self.display.desc[1][i]) )
                i += 1
        else:
            self.display = MB[tag]
            self.panel.clear()
            # Add Name
            self.panel.title = self.display.name
            # Add Attributes
            for item in dir(self.display)[::-1]:
                value = getattr(self.display, item)
                if value:
                    if item=="health":
                        txt = (f"Hitpoint: {value}",f"生命值：{value}")
                        self.panel.addItem( txt )
                    elif item=="damage":
                        txt = (f"Damage: {value}",f"伤害值：{value}")
                        self.panel.addItem( txt )
                    elif item=="dmgType":
                        txt = (f"Damage Type: {value}",f"伤害类型：{DT[value]}")
                        self.panel.addItem( txt )
                    elif item=="armor":
                        txt = (f"Injure Dent: {int(value*100)}%",f"受伤减免：{int(value*100)}%")
                        self.panel.addItem( txt )
                    elif item=="coin":
                        txt = (f"Coin Value: {value}",f"金币价值：{value}")
                        self.panel.addItem( txt )
                    else:
                        continue
        
    def renewProgress(self):
        for i in self.subject:
            total = 0
            avail = 0
            for each in self.monsList[i+1]:
                total += 1
                if self.monsList[i+1][each].acc:
                    avail += 1
            self.progress[i] = (f"{avail}/{total}", f"{avail}/{total}")
                
    def addSymm(self, image, x, y):    # Surface对象； x，y为正负（偏离中心点）像素值
        rect = image.get_rect()
        rect.left = (self.width - rect.width) // 2 + x
        rect.top = (self.height - rect.height) // 2 + y
        self.window.blit( image, rect )
        return rect                    # 返回图片的位置信息以供更多操作
    
    def addTXT(self, txt, fnt, color, x, y):
        '''本函数是以整个window为坐标（非中点）,这么做是为了能够更直接地在添加图片后对图片进行文字添加。但是x,y坐标是绘画的文本rect的中心。'''
        txt = fnt.render(txt, True, color)
        rect = txt.get_rect()
        rect.left = x - rect.width//2
        rect.top = y - rect.height//2
        self.window.blit( txt, rect )

class VMons():
    def __init__( self, cate, coord, desc, src ):
        self.attr = MB[cate]    # attr为database模块中的Mons结构
        self.name = self.attr.name
        self.image = pygame.image.load("image/"+src).convert_alpha()
        self.rect = None
        # accessiblity (coord 表明了mons在记录文件中的坐标：第几关（行）、该关内第几个（行内偏移）)
        if REC_DATA["MONS_COLLEC"][coord[0]-1][coord[1]]==1:
            self.acc = True
        else:
            self.acc = False
        self.coord = coord
        # 将整段desc文字分割为整齐的多行
        # 0-英文，1-中文
        self.desc = []
        vol = [50, 25]
        for i in [0,1]:
            txt = desc[i]
            self.desc.append( [] )
            while len(txt)>0:
                self.desc[i].append( txt[0:vol[i]] )
                txt = txt[vol[i]:]
            self.desc[i].append( txt )
        # 两种语言进行补齐
        while len(self.desc[0])<len(self.desc[1]):
            self.desc[0].append("")
        while len(self.desc[1])<len(self.desc[0]):
            self.desc[1].append("")

    def collec( self ):
        if self.acc:  # 已经collect则直接返回
            return False
        self.acc = True
        REC_DATA["MONS_COLLEC"][self.coord[0]-1][self.coord[1]]=1
        return True   # 修改成功，返回真值


# ==============================================================================================
# ==============================================================================================
class HeroBook():

    # 按序存储所有VHero，因为编译时还没初始化pygame.display，所以具体构造对象的过程要到代码执行阶段，即放到init函数中去。
    heroList = []

    notFound = None
    # some pointers。
    playerNo = 0         # 0表示指示P1，1表示指示P2
    curHero = []
    bkCnt = 0            # book count: help the animation of turning page
    pointer = 0          # book pointer: help point to the current hero (maybe not decided yet)
    pageSnd = None
    chosenSnd = None
    window = None
    xAlign = 0

    # ====================================================================
    # Constructor of HeroManager -----------------------------------------
    def __init__(self, width, height, panel_font):
        # 检测英雄可用性
        # 英雄解锁：Knight       Prince        Huntress       King
        self.accList = [ True, False, False, False, False, False, False ]
        i = 0   # i指示当前的英雄在accList中的序号。ie.1表示公主是否解锁。
        for stgStar in REC_DATA["CHAPTER_REC"]:
            i += 1
            if int(stgStar)>0 and i<7: # 该关已通过任意难度，则该关卡对应的英雄已解锁
                self.accList[i] = True
        self.heroList = []
        # name, acc,   hp, dmg, rDmg,   desc, note
        self.heroList.append( VHero( 
            0, ("Knight","骑士"), self.accList[0], (960,50), (140,10), (12,1), ("Normal","中"), 3200, 
            (("He's a speechless man who hides all","沉默寡言的骑士，把他一生的话"), 
            ("his words in the buried love towards Princess.","都藏在那颗爱公主的心当中。")), 
            ("Basic hero.","基本英雄。"), ("Justice Shower","正义洗礼"),
            (("Summon 15 arrows falling from the sky,","召唤15支从天而降的箭矢，"), 
            ("each dealing at most 210 DMG.","每支至多造成210点伤害。"))
        ) )
        self.heroList.append( VHero( 
            1, ("Princess","公主"), self.accList[1], (800,40), (200,15), (8,1), ("Normal","中"), 3600,
            (("Beautiful Princess is not only good-looking,","美丽的公主可不只负责美丽，她"), 
            ("but also a good teacher of pain with her rifle.","手里的火枪会让你知道痛字怎么写。")), 
            ("Unlock by completing Stage 1 Dragon Castle.","通过第一关恶龙城堡解锁此英雄。"), ("Grenade Shots","榴弹散射"), 
            (("Fires 8 explosive grenades frontwards quickly,","向前快速发射8枚爆炸性的榴弹，"),
            ("each dealing 180 AREA DMG.","每颗造成180点范围伤害。"))
        ) )
        self.heroList.append( VHero( 
            2, ("Prince","王子"), self.accList[2], (1080,50), (120,10), (16,1), ("Short","短"), 3200, 
            (("Prince's pony gives him tough build; and he","小马是王子的最爱，骑术给予他强健的体魄；"), 
            ("prefers short-ranged javelin - once missed he can","他也喜欢用射程短的标枪，因为当他失手时"), 
            ("fetch it so that not getting too embarrassed.","可以重新捡回来，不至于太过尴尬。")), 
            ("Unlock by completing Stage 2 Stone Cave.","通过第二关地下洞穴解锁此英雄。"), ("Troop Charge","铁骑冲锋"),
            (("Summons 9 phatom riders that charge in line","召唤9个骑兵幻影，成列冲锋，"), 
            ("crushing enemies all the way out.","一直向前碾碎敌人。"))
        ) )
        self.heroList.append( VHero( 
            3, ("Wizard","大法师"), self.accList[3], (840,40), (130,10), (10,1), ("Short","短"), 3200, 
            (("A master of natural elements, and is favored by","运用大自然元素力量的大师，有时也会"), 
            ("the king for his modest knowledge of alchemy.","炼炼丹，因此很受国王的待见。他的火球"), 
            ("His fireball deals extensive damage.","能造成范围伤害。")), 
            ("Unlock by completing Stage 3 Dead Yard.","通过第三关亡灵乐园解锁此英雄。"), ("Lightning Strikes","雷霆之力"),
            (("Casts 4 lightening strikes that deal 320 DMG to enemy","释放4道闪电，命中当前视野内生命值最高的"),
            ("with highest hitpoints within current view and stun it.","敌人，每道闪电造成320点伤害，并将之眩晕。"))
        ) )
        self.heroList.append( VHero( 
            4, ("Huntress","女猎手"), self.accList[4], (800,40), (42,2), (10,1), ("Long","长"), 2900, 
            (("A dart master and skilled climber, as well as","一位飞镖大师、攀岩高手，也是"), 
            ("good friend of strayed animals. Her sharp darts will","流浪动物的爱心伙伴。她的飞镖"), 
            ("penetrate enemies' body, making notable damage!","会穿透敌人，造成出乎意料的效果！")), 
            ("Unlock by completing Stage 4 Ooze Underground.","通过第四关软泥雨林解锁此英雄。"), ("Boomerang","回旋重刃"),
            (("Throws out the huge boomerang that bounces all the way","投掷出巨大的回旋镖，在塔楼内弹射而上，"),
            ("up, quickly clearing and stunning enemies around her.","能够迅速清除并眩晕她周身的敌人。"))
        ) )
        self.heroList.append( VHero( 
            5, ("Priest","牧师"), self.accList[5], (800,40), (120,6), (10,1), ("Normal","中"), 3200, 
            (("The youngest but best priest throughout the kingdom.","她是全王国最年轻却最优秀的女牧师。她的"), 
            ("Her power partly comes from the faith, but mainly from","力量部分来自于信仰，但主要还是来自于紫色"), 
            ("these purple jade stones she collects.","的圣之玉石。")), 
            ("Unlock by completing Stage 5 Frozen Peak.","通过第五关冰雪孤峰解锁此英雄。"), ("Piety Chant","虔诚圣歌"),
            (("Casts a healing ring that heals herself and other", "释放一个能够治疗她自身和其他友军的治疗光圈，"),
            ("allies within it, +240HP per hero instantly.", "迅速为每位英雄友方角色回复240点生命值。"))
        ) )
        self.heroList.append( VHero( 
            6, ("King","国王"), self.accList[6], (920,50), (38,4), (9,1), ("Short","短"), 3600, 
            (("Though elder and fatter these years, he's still","虽然这些年有些老了，也有些胖了，但他"), 
            ("awesome in battle. Quite good at rifle!","仍然是战场上令人敬畏的对手。非常擅用火枪！")),
            ("Unlock by completing Stage 6 Antique Factory.","通过第六关古旧工厂解锁此英雄。"), ("Royal Assist","皇家护卫"),
            (("Summon a Royal Servant to assist you in the battle.","召唤一名皇家侍从协助你进行战斗。"), 
            ("You can only have one servant summoned at the same time.","你同时仅可拥有一名侍从。"))
        ) )
        # 侍从VHero
        self.servantVHero = VHero( -1, ("Servant","侍从"), False, (800,0), (50,0), (1,0), ("Normal", "中"), 3200, 
            (("","")), ("",""), ("-","-"), (("",""))
        )
        self.notFound = pygame.image.load("image/lock.png").convert_alpha()
        self.icons = {
            "HP": pygame.image.load("image/icon_hp.png").convert_alpha(),
            "DMG": pygame.image.load("image/icon_dmg.png").convert_alpha(),
            "CNT": pygame.image.load("image/icon_cnt.png").convert_alpha(),
            "CRIT": pygame.image.load("image/icon_crit.png").convert_alpha(),
            "RNG": pygame.image.load("image/icon_rng.png").convert_alpha()
        }
        # 初始化背景古书的图像
        self.windowSize = (width, height)
        self.xAlign = width//4  # 文字中心位置和width//2之差
        self.book = []
        for i in range(0,5):
            self.book.append( pygame.image.load("image/book"+str(i)+".png").convert_alpha() )
        self.window = pygame.Surface( self.windowSize ).convert_alpha()
        # curHero (heroNo):初始默认为0：骑士; 1：公主
        self.curHero = [ REC_DATA["SYS_SET"]["P1"], REC_DATA["SYS_SET"]["P2"] ]
        self.pointer = self.curHero[self.playerNo] # set pointer to the player1's hero
        self.pageSnd = pygame.mixer.Sound("audio/page.wav")
        self.chosenSnd = pygame.mixer.Sound("audio/victoryHorn.wav")
        # statistics
        self.update_total_level()
        # panel ======================================
        self.panel = Panel(180, 120, panel_font, title=("히어로 선택","出战英雄"))
        h1 = self.heroList[self.curHero[0]]
        self.panel.addItem( 
            RichText( (f"P1 - _IMG_ {h1.name[0]} ",f"P1 - _IMG_ {h1.name[1]}"), 
                self.heroList[self.curHero[0]].brand, panel_font )
        )
        h2 = self.heroList[self.curHero[1]]
        self.panel.addItem( 
            RichText( (f"P2 - _IMG_ {h2.name[0]} ",f"P2 - _IMG_ {h2.name[1]}"), 
                self.heroList[self.curHero[1]].brand, panel_font )
        )
        self.panel.addItem( TextButton(160,30,
            {"default":("Change Heroes","更换英雄")}, "default", panel_font), tag="changeHero" 
        )

    def renderWindow(self, fontBig, fontSmall, pos):
        self.window.fill( (0,0,0,0) )
        hero = self.heroList[self.pointer]
        ys = [-160,-120,-80,-40,0]
        language = REC_DATA["SYS_SET"]["LGG"]
        # Draw BG Rects.
        AttBars = {"HP":None, "DMG":None, "CNT":None, "CRIT":None, "RNG":None, "NULL":None}
        chosenAtt = "NULL"
        AttBars["HP"] = drawRect( self.windowSize[0]//2,ys[0]+285, 240,32, (255,200,170,120), self.window )
        AttBars["DMG"] = drawRect( self.windowSize[0]//2,ys[1]+285, 240,32, (255,200,170,120), self.window )
        AttBars["CNT"] = drawRect( self.windowSize[0]//2,ys[2]+285, 240,32, (255,200,170,120), self.window )
        AttBars["CRIT"] = drawRect( self.windowSize[0]//2,ys[3]+285, 240,32, (255,200,170,120), self.window )
        AttBars["RNG"] = drawRect( self.windowSize[0]//2,ys[4]+285, 240,32, (255,220,190,120), self.window )
        # description frame.
        dscRect = drawRect( self.windowSize[0]//2-220,420, 460,150, (255,220,190,120), self.window )
        # Super Power Board.
        spRect = self.addSymm( hero.spBoard, self.xAlign-100, 70 )

        if self.accList[self.pointer]:
            # Name & level.
            titleTXT = (f"{hero.name[0]} [Level{hero.lvl}]", f"{hero.name[1]} 【等级{hero.lvl}】")
            ttRect = self.addTXT( titleTXT, fontBig, language, (0,0,0), self.xAlign, -250)
            # only draw exp bar when not in max level
            if hero.lvl<len(hero.nxtDic):
                self.drawExp( self.window, self.windowSize[0]//2+self.xAlign-120, ttRect.bottom+8, int(hero.exp), int(hero.nxtLvl), 2 )
                # progress Text
                self.addTXT( (str(hero.exp)+"/"+str(hero.nxtLvl),str(hero.exp)+"/"+str(hero.nxtLvl) ), fontSmall, language, (10,10,10), self.xAlign-20, -220 )
            
            self.addTXT( 
                ( (f"Skill Points: {hero.SP}"),(f"剩余技能点：{hero.SP}") ), fontSmall, language, (60,40,40), 250,-190, align="right"
            )
            # Attributes. Check Mouse Hanging-overs.
            txtHP = ( "Health: "+str(hero.hp), "体力："+str(hero.hp) )
            txtDMG = ( "Damage: "+str(hero.dmg), "伤害："+str(hero.dmg) )
            txtCNT = ( "Count: "+str(hero.cnt), "弹药容量："+str(hero.cnt) )
            txtCRIT = ( "Crit: "+str(hero.crit)+"%", "暴击率："+str(hero.crit)+"%" )
            txtRNG = ( "Range: "+str(hero.range[0]), "射程："+str(hero.range[1]) )
            for each in AttBars:
                if AttBars[each] and ( AttBars[each].left < pos[0] < AttBars[each].right ) and ( AttBars[each].top < pos[1] < AttBars[each].bottom ):
                    chosenAtt = each              # 记录选中的属性项名称.
                    if each=="HP":
                        drawRect( self.windowSize[0]//2+2,ys[0]+287, 236,28, (240,255,240,128), self.window )  # 选中的颜色覆盖
                        txtHPInc = ( f"+{hero.hpInc}",f"+{hero.hpInc}" )
                        self.addTXT( txtHPInc, fontSmall, language, (20,140,20), self.xAlign+30, ys[0], align="left" )
                    elif each=="DMG":
                        drawRect( self.windowSize[0]//2+2,ys[1]+287, 236,28, (240,255,240,128), self.window )
                        txtDMGInc = ( "+"+str(hero.dmgInc),"+"+str(hero.dmgInc) )
                        self.addTXT( txtDMGInc, fontSmall, language, (20,140,20), self.xAlign+30, ys[1], align="left" )
                    elif each=="CNT":
                        drawRect( self.windowSize[0]//2+2,ys[2]+287, 236,28, (240,255,240,128), self.window )
                        txtCNTInc = ( "+"+str(hero.cntInc),"+"+str(hero.cntInc) )
                        self.addTXT( txtCNTInc, fontSmall, language, (20,140,20), self.xAlign+30, ys[2], align="left" )
                    elif each=="CRIT":
                        drawRect( self.windowSize[0]//2+2,ys[3]+287, 236,28, (240,255,240,128), self.window )
                        txtCRITInc = ( "+"+str(hero.critInc)+"%","+"+str(hero.critInc)+"%" )
                        self.addTXT( txtCRITInc, fontSmall, language, (20,140,20), self.xAlign+30, ys[3], align="left" )
                    break
            # Then, draw Attributes icons.
            self.addSymm( self.icons["HP"], self.xAlign-118, ys[0] )
            self.addSymm( self.icons["DMG"], self.xAlign-118, ys[1] )
            self.addSymm( self.icons["CNT"], self.xAlign-118, ys[2] )
            self.addSymm( self.icons["CRIT"], self.xAlign-118, ys[3] )
            self.addSymm( self.icons["RNG"], self.xAlign-118, ys[4] )
            # Then, Write Attributes Infos.
            self.addTXT( txtHP, fontSmall, language, (0,0,0), self.xAlign-90, ys[0], align="left" )
            self.addTXT( txtDMG, fontSmall, language, (0,0,0), self.xAlign-90, ys[1], align="left" )
            self.addTXT( txtCNT, fontSmall, language, (0,0,0), self.xAlign-90, ys[2], align="left")
            self.addTXT( txtCRIT, fontSmall, language, (0,0,0), self.xAlign-90, ys[3], align="left" )
            self.addTXT( txtRNG, fontSmall, language, (0,0,0), self.xAlign-90, ys[4], align="left" )
            # Finally, Write Attributes lvl Infos.
            maxl = hero.ATT_MAX
            self.addTXT( (f"{hero.at_lvls['HP']}/{maxl}", f"{hero.at_lvls['HP']}/{maxl}"), fontSmall, language, (40,40,40), self.xAlign+80, ys[0] )
            self.addTXT( (f"{hero.at_lvls['DMG']}/{maxl}", f"{hero.at_lvls['DMG']}/{maxl}"), fontSmall, language, (40,40,40), self.xAlign+80, ys[1] )
            self.addTXT( (f"{hero.at_lvls['CNT']}/{maxl}", f"{hero.at_lvls['CNT']}/{maxl}"), fontSmall, language, (40,40,40), self.xAlign+80, ys[2] )
            self.addTXT( (f"{hero.at_lvls['CRIT']}/{maxl}", f"{hero.at_lvls['CRIT']}/{maxl}"), fontSmall, language, (40,40,40), self.xAlign+80, ys[3] )
            # Super power.
            self.addSymm( hero.spIcon, self.xAlign-100, 70 )
            self.addTXT( ("SuperPower:","超级技能："), fontSmall, language, (0,0,0), self.xAlign-60, 60, align="left" )
            self.addTXT( hero.spName, fontSmall, language, (0,0,0), self.xAlign-60, 80, align="left" )
            # Description.
            dscY = dscRect.top -self.windowSize[1]//2 +20
            # if hovers on superPower Circle
            if (spRect.left < pos[0] < spRect.right) and (spRect.top < pos[1] < spRect.bottom):
                for statement in hero.spDesc:
                    self.addTXT( statement, fontSmall, language, (0,0,0), 0, dscY)
                    dscY += 24
            else:
                for statement in hero.desc:
                    self.addTXT( statement, fontSmall, language, (0,0,0), 0, dscY)
                    dscY += 24
            
            # check whether the current hero is chosen
            if self.pointer==self.curHero[self.playerNo]:
                self.addSymm( pygame.image.load("image/active.png"), 40, -260 )
        # Unlock condition.
        self.addTXT( hero.note, fontSmall, language, (60,60,60), 0, dscRect.bottom-self.windowSize[1]//2-20)
        return (chosenAtt, AttBars[chosenAtt]) # 返回选中的属性项名称和其rect.
        
    def chooseHero(self):
        if self.accList[self.pointer]: # 选中英雄的情况
            self.chosenSnd.play(0)
            self.heroList[self.pointer].voice.play(0)
            if self.pointer == self.curHero[1-self.playerNo]:           # 如果选中了另一个玩家选的角色
                self.curHero[1-self.playerNo] = self.curHero[self.playerNo]  # 那就将两个角色互换（不能相同！）
            self.curHero[self.playerNo] = self.pointer                  # 设为出战
            # 修改记录
            REC_DATA["SYS_SET"]["P1"] = self.curHero[0]
            REC_DATA["SYS_SET"]["P2"] = self.curHero[1]
            # 修改Panel
            h1 = self.heroList[self.curHero[0]].name
            self.panel.updateText(0, RichText( (f"P1 - _IMG_ {h1[0]} ",f"P1 - _IMG_ {h1[1]}"), 
                self.heroList[self.curHero[0]].brand, self.panel.font )
            )
            h2 = self.heroList[self.curHero[1]].name
            self.panel.updateText(1, RichText( (f"P2 - _IMG_ {h2[0]} ",f"P2 - _IMG_ {h2[1]}"), 
                self.heroList[self.curHero[1]].brand, self.panel.font )
            )
            return True
        return False

    def turnPage(self, next):
        '''next值取1或-1，分别表示下一个或前一个。'''
        if (self.pointer>=6 and next>0) or (self.pointer<=0 and next<0):
            return
        self.pageSnd.play(0)
        self.bkCnt = 8*next
        self.pointer += next

    def turnAnimation(self):
        if self.bkCnt > 0:
            self.bkCnt -= 1
            if self.bkCnt >= 6:
                return ( self.book[1], -42 )
            elif self.bkCnt >= 4:
                return ( self.book[2], -41 )
            elif self.bkCnt >= 2:
                return ( self.book[3], -36 )
            elif self.bkCnt >= 0:
                return ( self.book[4], -12 )
        elif self.bkCnt < 0:
            self.bkCnt += 1
            if self.bkCnt <= -6:
                return ( self.book[4], -12 )
            elif self.bkCnt <= -4:
                return ( self.book[3], -36 )
            elif self.bkCnt <= -2:
                return ( self.book[2], -41 )
            elif self.bkCnt <= 0:
                return ( self.book[1], -42 )
        else:
            return ( self.book[0], 0 )

    def update_total_level(self):
        # 未解锁的不参与计算（视为0）
        lvl_list = [ REC_DATA["HEROES"][i][0] for i in range( len(REC_DATA["HEROES"]) ) if self.accList[i] ]
        self.total_level = sum(lvl_list)

    def addTXT(self, txtList, font, language, color, x, y, align="center"):
        '''xy为正负（偏离屏幕中心点）像素值。确定了文字行的中心坐标。
            align: center 或 left。'''
        txt = font[language].render( txtList[language], True, color )
        rect = txt.get_rect()
        if align=="center":
            rect.left = self.windowSize[1]//2 -rect.width//2 +x
        elif align=="left":
            rect.left = self.windowSize[1]//2 +x
        elif align=="right":
            rect.right = self.windowSize[1]//2 +x
        rect.top = self.windowSize[1]//2 -rect.height//2 +y
        self.window.blit( txt, rect )
        return rect
    
    def addSymm(self, surface, x, y):
        rect = surface.get_rect()
        rect.left = self.windowSize[1]//2 -rect.width//2 +x
        rect.top = self.windowSize[1]//2 -rect.height//2 +y
        self.window.blit( surface, rect )
        return rect

    def drawExp(self, surface, x, y, exp, full, gap, height=20):
        '''x,y均为相对中心点的偏移'''
        color = (190, 80, 70)
        shadeColor = (90, 30, 30)   # 经验条下方的条形阴影的颜色
        # 画外边框（白色底框）
        outRect = pygame.Rect( x, y, 200, height )
        pygame.draw.rect( surface, (240,230,230), outRect )
        # 经验值的长度
        length = (exp/full)*(200-gap*2)
        exp = pygame.Rect( x+gap, y+gap, int(length), height-gap*2 )
        pygame.draw.rect( surface, color, exp )
        shadow = pygame.Rect( x+gap, exp.bottom-gap, int(length), gap )
        pygame.draw.rect( surface, shadeColor, shadow )
        return outRect

class VHero():
    alloSnd = None
    
    def __init__(self, no, name, acc, hp, dmg, cnt, R, superPowerFull, desc, note, spName, spDesc):
        self.no = int(no)
        self.name = name
        self.spName = spName
        self.hp, self.hpInc = hp      # health
        self.dmg, self.dmgInc = dmg   # damage
        self.cnt, self.cntInc = cnt   # count
        self.crit, self.critInc = 10, 5 # critical hit rate (all hero the same, unit:%)
        self.range = R                # shoot range
        self.desc = desc
        self.spDesc = spDesc
        self.superPowerFull = superPowerFull
        self.note = note
        if not VHero.alloSnd:
            VHero.alloSnd = pygame.mixer.Sound("audio/coin.wav")
            VHero.spBoard = pygame.image.load("image/ammoCircle.png").convert_alpha()
        # accessiblity
        self.acc = acc
        self.ATT_MAX = 3             # 单项最多可以升级3次
        # Other (仅侍从无以下属性)
        if self.no>=0:
            tag = name[0].lower()
            self.image = pygame.image.load("image/"+tag+"/"+tag+".png").convert_alpha()
            self.brand = pygame.image.load("image/"+tag+"/brand.png").convert_alpha()
            self.voice = pygame.mixer.Sound("audio/"+tag+"/"+tag+"C.wav")
            self.spIcon = pygame.image.load("image/"+tag+"/superPowerIcon.png").convert_alpha()
            # exp & level information
            lvex = REC_DATA["HEROES"][self.no]
            self.lvl = lvex[0]
            self.exp = lvex[1]
            self.SP = lvex[2]
            # 记录四个属性各自升级的次数
            self.at_lvls = {"HP":lvex[3], "DMG":lvex[4], "CNT":lvex[5], "CRIT":lvex[6]}
            self.hp += self.at_lvls["HP"]*self.hpInc
            self.dmg += self.at_lvls["DMG"]*self.dmgInc
            self.cnt += self.at_lvls["CNT"]*self.cntInc
            self.crit += self.at_lvls["CRIT"]*self.critInc
            # 升级量表。（当前级：升到下一级所需的经验值。）最高可升至第10级。
            self.nxtDic = {1:100, 2:200, 3:400, 4:800, 5:1200, 6:1500, 7:1800, 8:2100, 9:2400, 10:2400}
            self.nxtLvl = self.nxtDic[self.lvl]
        else:
            self.lvl = 1
            self.exp = 0

    def increaseExp(self, num):
        """process exp increasment"""
        # if in max level
        if self.lvl>=len(self.nxtDic):
            return
        self.exp += num
        # check level up
        if self.exp>=self.nxtLvl:
            # if in max level
            if self.lvl>=len(self.nxtDic):
                self.exp = self.nxtLvl = self.nxtDic[int(self.lvl)]
            # normal level up: set nxtLvl amount as next level requirement
            else:
                self.exp -= self.nxtLvl
                self.lvl += 1
                self.SP += 1
                self.nxtLvl = self.nxtDic[int(self.lvl)]
        # 更新英雄等级部分的data structure：lvl，exp，SP
        lvex = REC_DATA["HEROES"][self.no]
        lvex[0] = self.lvl  # 更新等级
        lvex[1] = self.exp  # 更新经验
        lvex[2] = self.SP   # 更新技能点

    def alloSP(self, attri):       # 处理技能点分配
        if self.SP<=0:
            return "lackSP"
        if attri=="RNG":
            return "NULL"
        if self.at_lvls[attri]>=self.ATT_MAX:
            return "attMax"
        self.alloSnd.play(0)
        lvex = REC_DATA["HEROES"][self.no]
        if attri=="HP":
            self.hp += self.hpInc
            lvex[3] += 1
        elif attri == "DMG":
            self.dmg += self.dmgInc
            lvex[4] += 1
        elif attri == "CNT":
            self.cnt += self.cntInc
            lvex[5] += 1
        elif attri == "CRIT":
            self.crit += self.critInc
            lvex[6] += 1
        else:
            return "NULL"
        # 技能点-1
        self.SP -= 1
        lvex[2] -= 1
        # 属性等级+1
        self.at_lvls[attri] = self.at_lvls[attri]+1
        return True

    def addGem(self, num):
        REC_DATA["GEM"] += num


# ==============================================================================================
# ==============================================================================================
class Bazaar():
    yp = 42             # Y的增加距离
    currentKey = ""

    def __init__(self, width, height, fntSet):
        # restore ongoing task
        self.task = TB[ REC_DATA["TASK"][0] ]
        self.task.progress = REC_DATA["TASK"][1]

        self.fntSet = fntSet
        self.taskPanel = Panel( 210, 140, self.fntSet[1], title=("Current Task","当前任务") )
        self.taskPanel.addItem( self.task.descript )
        self.taskPanel.addItem( RichText(
                (f"[Reward] _IMG_{self.task.reward}",f"【报酬】_IMG_{self.task.reward}"), 
                pygame.image.load("image/gem0.png").convert_alpha(), self.fntSet[1]
            ) 
        )
        self.taskPanel.addItem( (f"[Progress] {self.task.progress}/{self.task.num}",f"【进度】 {self.task.progress}/{self.task.num}") )
        self.taskPanel.addItem( TextButton(180, 30,
                    {True:("Claim Reward","领取奖励"), False:("Change Task","更换任务")}, 
                    True if self.task.progress>=self.task.num else False,
                    self.fntSet[1], rgba=(120,120,50,240)), tag="task_upd" 
                )
        self.windowSize = (width, height)
        self.window = pygame.Surface( self.windowSize ).convert_alpha()

        # initialize stone part ====================
        self.reroll_cost = 1    # 刷新商铺所需宝石数
        self.reroll_tip = RichText( 
            (f" _IMG_ {self.reroll_cost}",f" _IMG_ {self.reroll_cost}"), 
            pygame.image.load("image/gem0.png").convert_alpha(), self.fntSet[1]
        )
        self.stonePanels = [RunestonePanel(self.fntSet[1], tag) for tag in RB]
        self.onsale = sample(self.stonePanels, 3)
        self.merchant_woman = pygame.image.load("image/merchant_woman.png").convert_alpha()

        # stone storage panel
        self.myStonePanel = MyStonePanel( self.fntSet[1] )

    def renderWindow(self, fntSet, pos, switchButton):
        self.currentKey = ""

        ## 1.Version Checker
        self.window.fill( (0,0,0,0) )
        language = REC_DATA["SYS_SET"]["LGG"]
        y = 30
        # Title0
        drawRect( 10, y, self.windowSize[0]-20, self.yp, (0,0,0,120), self.window )
        title0 = self.addTXT( language, ["Runestone Stall","符石商铺"], fntSet[2], 0, y )
        # right update button
        mid_y = title0.top+title0.height//2
        switchButton.paint(self.window, self.windowSize[0]-50, mid_y, pos)
        self.reroll_tip.paint(self.window, self.windowSize[0]-105, mid_y)
        y += self.yp

        self.spacing = 190
        
        for i in range(-1,2):
            # paint panel and draw description
            panel = self.onsale[i+1]
            if panel.paint(self.window, self.window.get_width()//2+self.spacing*i, y+100, pos):
                self.addTXT( language, RB[self.onsale[i+1].tag].description, fntSet[1], 0, y+200 )
                self.currentKey = panel.tag

        y += 240
        # my storage.
        wmRect = self.addSymm( self.merchant_woman, 0, self.window.get_height()-140 )
        #self.myStonePanel.paint(self.window, 200, y+100, pos)  # 由main外部绘制

        if ( 0 <= pos[0] <= self.windowSize[0] ):
            if switchButton.hover_on(pos):
                self.currentKey = "reroll"
        
    def buy_stone(self):
        # click on space
        if self.currentKey not in RB:
            pygame.mixer.Sound("audio/alert.wav").play(0)
            return
        # check gems
        if REC_DATA["GEM"] < RB[self.currentKey].cost:
            pygame.mixer.Sound("audio/alert.wav").play(0)
            return "lackGem"
        # increase stone
        try:
            REC_DATA["STONE"][self.currentKey] += 1
        except:
            REC_DATA["STONE"][self.currentKey] = 1
        REC_DATA["GEM"] -= RB[self.currentKey].cost
        self.myStonePanel.update_panel()
        # set the target pos to void (search because all three are unique here)
        for i in range(3):
            if self.onsale[i].tag == self.currentKey:
                self.onsale[i] = RunestonePanel(self.fntSet[1], "")
        pygame.mixer.Sound("audio/coin.wav").play(0)

        return "OK"
    
    def update_task(self, prog_only=False):
        # prog_only: True- only update progress; False- check real action (claim and change)
        if prog_only:
            self.taskPanel.updateText(2, (f"Progress: {self.task.progress}/{self.task.num}",f"进度：{self.task.progress}/{self.task.num}"))
            if self.task.progress>=self.task.num:
                self.taskPanel.updateButton(but_tag="task_upd", label_key=True)
        else:
            # 1. 尝试claim当前Task的reward
            reward = None
            if self.task.claim_reward():
                reward = self.task.reward
            # 2. change new task: chapters that have been unlocked can contribute tasks
            cpComp = [1 if star>=0 else 0 for star in REC_DATA["CHAPTER_REC"]]
            tag_pool = [ tag for tag in list(TB) if TB[tag].pres<=sum(cpComp) and tag!=self.task.tag ]
            new_tag = choice(tag_pool)
            self.task = TB[new_tag]
            # 3. update REC
            REC_DATA["TASK"] = [new_tag, self.task.progress]
            # 4. update task panel
            self.taskPanel.updateText(0, self.task.descript)
            self.taskPanel.updateText(1, RichText(
                    (f"[Reward] _IMG_{self.task.reward}",f"【报酬】_IMG_{self.task.reward}"), 
                    pygame.image.load("image/gem0.png").convert_alpha(), self.fntSet[1]
                ) 
            )
            self.taskPanel.updateText(2, (f"[Progress] {self.task.progress}/{self.task.num}",f"【进度】 {self.task.progress}/{self.task.num}"))
            self.taskPanel.updateButton(but_tag="task_upd", label_key=False)
            return reward

    def reroll(self):
        if REC_DATA["GEM"] >= self.reroll_cost:
            pygame.mixer.Sound("audio/coin.wav").play(0)
            REC_DATA["GEM"] -= self.reroll_cost
            self.onsale = sample(self.stonePanels, 3)
        else:
            pygame.mixer.Sound("audio/alert.wav").play(0)
            return "lackGem"
    
    # General ---------
    def addTXT(self, language, txt, font, x, y, midX=True):
        '''x为正负（偏离window中心线）像素值； y为从上到下的距离'''
        txt = font[language].render( txt[language], True, (255,255,255) )
        rect = txt.get_rect()
        if midX:
            rect.left = (self.windowSize[0]-rect.width) // 2 + x
        else:
            rect.left = x
        rect.top = y
        self.window.blit( txt, rect )
        return rect                   # 返回文字的位置信息以供更多操作

    def addSymm(self, surface, x, y):       # x为正负（偏离中心点）像素值
        rect = surface.get_rect()
        rect.left = (self.windowSize[0]-rect.width)// 2 + x
        rect.top = y - rect.height//2
        self.window.blit( surface, rect )
        return rect                   # 返回图片的位置信息以供更多操作

class RunestonePanel(Panel):
    def __init__(self, font, tag):
        self.tag = tag
        if tag:
            Panel.__init__(self, 170, 180, font, title=RB[tag].name, rgba=(70,60,0,140))
            self.addItem( pygame.image.load(f"image/runestone/{tag}.png").convert_alpha() )
            self.addItem( RichText( (f"_IMG_ {RB[tag].cost}",f"_IMG_ {RB[tag].cost}"), 
                pygame.image.load("image/gem0.png").convert_alpha(), self.font) 
            )
            self.addItem( TextButton(150, 30, {"default":("Purchase","购买")}, "default", font, rgba=(60,120,30,210)), tag="purchase" )
        else:
            Panel.__init__(self, 170, 180, font, title=(" "," "), rgba=(70,60,0,140))

class MyStonePanel(Panel):
    def __init__(self, font):
        Panel.__init__( self, 220, 200, font, title=("My Runstones","我的符石") )#, rgba=(0,0,0,0) )
        self.update_panel()
        # for receiving stones
        self.image = self.surf
        self.mask = pygame.mask.from_surface(self.image)

    def update_panel(self):
        self.clear()
        self.title = ("My Runstones","我的符石")
        for tag in REC_DATA["STONE"]:
            self.addItem( 
                RichText( (f"_IMG_  {RB[tag].name[0]}  {REC_DATA['STONE'][tag]}",f"_IMG_\t{RB[tag].name[1]}\t\t{REC_DATA['STONE'][tag]}"), 
                    pygame.image.load(f"image/runestone/{tag}.png").convert_alpha(), self.font ) 
            )
    
    def receiveExp(self, num, typ):
        # real record is not updated here. On clicking: instantly updated. 
        # This just respond to animation.
        self.update_panel()
        pygame.mixer.Sound("audio/coin.wav").play(0)


# ==============================================================================================
# ==============================================================================================
import requests
from bs4 import BeautifulSoup
import zipfile
import os
import paramiko
import pymysql      # 用于数据库访问
import time         # 用于下载速度计时

class Settings():
    # This is for three modules: settings, version, weblink
    currentKey = ""     # 调整按键设置时用到的两个变量（指针）
    currentRect = None
    chosenKey = ""
    chosenRect = None
    pNo = 1             # 初始为显示玩家1的键位设置
    yp = 40             # Y的增加距离
    but_x = 210         # switch按钮的水平位置

    # Dictionary for storing the key info of two players
    keyDic1 = {}        # i.e. 235,35,36
    keyDic2 = {}
    keyNm = {}          # 当前显示的keyDic里的对应键名(i.e. A, SPACE,[6])
    versInfo = []

    paperList = []     # 壁纸原画信息列表
    subject = { 0:("설정","系统"), 1:("조작키","操作") }

    def __init__(self, width, height, font):
        self.instruction = {"leftOpt":pygame.image.load("image/Next.png"), 
            "rightOpt":pygame.transform.flip( pygame.image.load("image/Next.png"), True, False) }
        self.curSub = 0
        # ===============================================================
        # key dictionary(字典value为按键在pygame中的标识码)
        kd1, kd2 = REC_DATA["KEY_SET"] = [
    [97,100,115,106,107,108,105,119,114],
    [98,109,110,260,261,262,264,273,111]
]
        self.keyDic1 = dict( leftKey=kd1[0], rightKey=kd1[1], downKey=kd1[2], shootKey=kd1[3], jumpKey=kd1[4], superKey=kd1[5], itemKey=kd1[6], bagKey=kd1[7] , reloadKey =kd1[8] )
        self.keyDic2 = dict( leftKey=kd2[0], rightKey=kd2[1], downKey=kd2[2], shootKey=kd2[3], jumpKey=kd2[4], superKey=kd2[5], itemKey=kd2[6], bagKey=kd2[7] , reloadKey =kd1[8] )
        self.renewKeyNm()
        self.chosenKey = self.currentKey = ""
        self.chosenRect = self.currentRect = None
        self.windowSize = (width, height)
        self.window = pygame.Surface( self.windowSize ).convert_alpha()
        # =========版本信息部分=========
        self.newvers = VERSION
        # ==========记录部分===========
        # REC step 1. 从本地./record.sav导入文件（已在database中自动完成）
        self.IDlines = {}
        self.tmp_nickname = REC_DATA["NICK_NAME"]
        self.tmp_game_id = REC_DATA["GAME_ID"]
        # ========wallpaper部分=========
        # 1.从指定路径读取所有jpg文件
        jpg_list = [ f for f in os.listdir("image/titleBG") if os.path.splitext(f)[-1]==".jpg" ]
        #print(jpg_list)
        # 2.过滤文件名不合法的jpg文件，形成本次壁纸集
        self.paperList = []
        for jpg in jpg_list:
            try:
                name_string = jpg.split(".")[0]
                e, EN, CN = name_string.split("_")  # 格式需为*_*_*.jpg
                #print(e,EN,CN)
                assert int(e)>0 and int(e)<8        # 第二位需为数字，且取1-7（自然效果编号）
            except:
                continue
            else:
                # 读取jpg并加入列表中（字典：{壁纸名，特效号，surface对象}）
                self.paperList.append( {"name": (EN, CN), "e": int(e), "p":pygame.image.load(f"image/titleBG/{jpg}")} )
        # 3.判断以往的序号是否超出本次数量范围，若超出则重置为0
        if REC_DATA["SYS_SET"]["PAPERNO"]>=len(self.paperList):
            REC_DATA["SYS_SET"]["PAPERNO"] = 0
    
    # Setting window --
    def renderWindow(self, fntSet, pos, switchButton):
        ## 1.Version Checker
        self.window.fill( (0,0,0,0) )
        self.window.fill( (20,20,20, 180) )
        y = 20
        x = 110  # key和内容距离中线的偏移
        language = REC_DATA["SYS_SET"]["LGG"]
        self.currentKey = ""
        self.currentRect = None

        if self.curSub==0:
            ## 1.Systematic Settings
            drawRect( 10, y, self.windowSize[0]-20, self.yp-6, (120,120,120,120), self.window )
            self.addTXT( language, ("System Settings","系统设置"), fntSet[2], 0, y )
            y += self.yp
            # 语言设置行
            lggRect = self.addTXT( language, ("언어","语言"), fntSet[2], -x, y )
            if language == 0:
                self.addTXT( language, ("영어","英语"), fntSet[2], x, y )
            elif language == 1:
                self.addTXT( language, ("중국어","中文"), fntSet[2], x, y )
            if self.chosenKey=="language":  # 若被选中，将之高亮
                self.drawFrame( lggRect )
                self.addSymm( self.instruction["leftOpt"], x-90, lggRect.top+lggRect.height//2 )
                self.addSymm( self.instruction["rightOpt"], x+90, lggRect.top+lggRect.height//2 )
            y += self.yp
            # 音量设置行
            volRect = self.addTXT( language, ("음악 볼륨","背景音乐音量"), fntSet[2], -x, y )
            self.addTXT( language, ("%d"%REC_DATA["SYS_SET"]["VOL"],"%d"%REC_DATA["SYS_SET"]["VOL"]), fntSet[2], x, y )
            if self.chosenKey=="volume":  # 若被选中，将之高亮
                self.drawFrame( volRect )
                self.addSymm( self.instruction["leftOpt"], x-90, volRect.top+volRect.height//2 )
                self.addSymm( self.instruction["rightOpt"], x+90, volRect.top+volRect.height//2 )
            y += self.yp
            # 显示方式设置行
            dspRect = self.addTXT( language, ("화면","显示方式"), fntSet[2], -x, y )
            if REC_DATA["SYS_SET"]["DISPLAY"]==0:
                self.addTXT( language, ("WINDOW","窗口"), fntSet[2], x, y )
            elif REC_DATA["SYS_SET"]["DISPLAY"]==1:
                self.addTXT( language, ("전체화면","全屏"), fntSet[2], x, y )
            if self.chosenKey=="display":  # 若被选中，将之高亮
                self.drawFrame( dspRect )
                self.addSymm( self.instruction["leftOpt"], x-90, dspRect.top+dspRect.height//2 )
                self.addSymm( self.instruction["rightOpt"], x+90, dspRect.top+dspRect.height//2 )
            y += self.yp
            # 主界面壁纸设置行
            ppRect = self.addTXT( language, ("Wallpaper","主界面壁纸"), fntSet[2], -x, y )
            self.addTXT( language, self.paperList[REC_DATA["SYS_SET"]["PAPERNO"]]["name"], fntSet[2], x, y )
            if self.chosenKey=="paper":  # 若被选中，将之高亮
                self.drawFrame( ppRect )
                self.addSymm( self.instruction["leftOpt"], x-90, ppRect.top+ppRect.height//2 )
                self.addSymm( self.instruction["rightOpt"], x+90, ppRect.top+ppRect.height//2 )
            y += self.yp

            ## 2. Version operation: Title
            drawRect( 10, y, self.windowSize[0]-20, self.yp-6, (120,120,120,120), self.window )
            self.addTXT( language, ["Version Update","版本更新"], fntSet[2], 0, y )
            y += self.yp

            # Content
            self.addTXT( language, ("Game Version","游戏版本"), fntSet[2], -x, y )
            self.addTXT( language, (VERSION,VERSION), fntSet[2], x, y )
            y += self.yp

            # 判断鼠标位置(pos应该由调用者进行了偏移处理)
            if ( 0 <= pos[0] <= self.windowSize[0] ):
                if (lggRect.top < pos[1] < lggRect.bottom ):
                    self.drawFrame( lggRect )
                    self.currentKey = "language"
                    self.currentRect = lggRect
                elif (volRect.top < pos[1] < volRect.bottom ):
                    self.drawFrame( volRect )
                    self.currentKey = "volume"
                    self.currentRect = volRect
                elif (dspRect.top < pos[1] < dspRect.bottom ):
                    self.drawFrame( dspRect )
                    self.currentKey = "display"
                    self.currentRect = dspRect
                elif (ppRect.top < pos[1] < ppRect.bottom ):
                    self.drawFrame( ppRect )
                    self.currentKey = "paper"
                    self.currentRect = ppRect

        elif self.curSub == 1:
            ## 3. Key Settings
            # Title
            drawRect( 10, y, self.windowSize[0]-20, self.yp-6, (120,120,120,120), self.window )
            title0 = self.addTXT( language, ("Player Key [P%d]" %self.pNo,"角色键位【玩家%d】" %self.pNo), fntSet[2], 0, y )
            switchButton.paint(self.window, 50, title0.top+title0.height//2, pos)
            y += self.yp

            # Contents
            k_dict = {
                "key1": {"tag": "leftKey", "name": ("Left","左"), "rect": None}, 
                "key2": {"tag": "rightKey", "name": ("Right","右"), "rect": None}, 
                "key3": {"tag": "downKey", "name": ("Downward","下跳"), "rect": None}, 
                "key4": {"tag": "shootKey", "name": ("Shoot","射击"), "rect": None}, 
                "key5": {"tag": "jumpKey", "name": ("Jump","上跳"), "rect": None}, 
                "key6": {"tag": "superKey", "name": ("Super Power","超级技能"), "rect": None}, 
                "key7": {"tag": "itemKey", "name": ("Use Props","使用道具"), "rect": None}, 
                "key8": {"tag": "bagKey", "name": ("Change Props","切换道具"), "rect": None},
                "key9": {"tag": "reloadKey", "name": ("reload","切换道具"), "rect": None}, 
            }
            for key_n in k_dict:
                k_dict[key_n]["rect"] = self.addTXT( language, k_dict[key_n]["name"], fntSet[2], -x, y )
                self.addTXT( language, (self.keyNm[key_n],self.keyNm[key_n]), fntSet[2], x, y )
                if self.chosenKey==k_dict[key_n]["tag"]:
                    self.drawFrame( k_dict[key_n]["rect"] )
                y += self.yp

            # 判断鼠标位置(pos应该由调用者进行了偏移处理)
            if ( 0 <= pos[0] <= self.windowSize[0] ):
                if switchButton.hover_on(pos):
                    self.currentKey = "keyTitle"
                else:
                    for key_n in k_dict:
                        if ( k_dict[key_n]["rect"].top < pos[1] < k_dict[key_n]["rect"].bottom ):
                            self.drawFrame( k_dict[key_n]["rect"] )
                            self.currentRect = k_dict[key_n]["rect"]
                            self.currentKey = k_dict[key_n]["tag"]

    def drawFrame(self, key):
        rect = ( (20,key.top-2), (self.windowSize[0]-40,key.height+4) )
        pygame.draw.rect( self.window, (240,240,240), rect, 1 )

    def changeKey(self, key):
        kList = []
        if self.pNo == 1:
            self.keyDic1[self.chosenKey] = key
            self.renewKeyNm()
            for each in self.keyDic1:
                kList.append( str(self.keyDic1[each]) )
            REC_DATA["KEY_SET"][0] = kList
        elif self.pNo == 2:
            self.keyDic2[self.chosenKey] = key
            self.renewKeyNm()
            for each in self.keyDic2:
                kList.append( str(self.keyDic2[each]) )
            REC_DATA["KEY_SET"][1] = kList

    def renewKeyNm(self):
        if self.pNo==1:
            ref = self.keyDic1
        elif self.pNo==2:
            ref = self.keyDic2
        # 确保是整数而非字符串
        for key in ref:
            ref[key] = int(ref[key])
        self.keyNm = { "key1":pygame.key.name(ref["leftKey"]).upper(), "key2":pygame.key.name(ref["rightKey"]).upper(), 
            "key3":pygame.key.name(ref["downKey"]).upper(), "key4":pygame.key.name(ref["shootKey"]).upper(), 
            "key5":pygame.key.name(ref["jumpKey"]).upper(), "key6":pygame.key.name(ref["superKey"]).upper(), 
            "key7":pygame.key.name(ref["itemKey"]).upper(), "key8":pygame.key.name(ref["bagKey"]).upper(),
            "key9":pygame.key.name(ref["reloadKey"]).upper() }
    
    def alterPNo(self):
        if self.pNo==1:
            self.pNo = 2
        elif self.pNo==2:
            self.pNo = 1
        self.renewKeyNm()

    
    # General ---------
    def addTXT(self, language, txt, font, x, y, midX=True):
        '''x为正负（偏离window中心线）像素值； y为从上到下的距离'''
        txt = font[language].render( txt[language], True, (255,255,255) )
        rect = txt.get_rect()
        if midX:
            rect.left = (self.windowSize[0]-rect.width) // 2 + x
        else:
            rect.left = x
        rect.top = y
        self.window.blit( txt, rect )
        return rect                   # 返回文字的位置信息以供更多操作

    def addSymm(self, surface, x, y):       # x为正负（偏离中心点）像素值
        rect = surface.get_rect()
        rect.left = (self.windowSize[0]-rect.width)// 2 + x
        rect.top = y - rect.height//2
        self.window.blit( surface, rect )
        return rect                   # 返回图片的位置信息以供更多操作


class AccountButton(Panel):
    def __init__(self, font):
        Panel.__init__(self, 180, 50, font)
        self.portrait = pygame.image.load("image/Princess/brand.png")
        self.portrait = pygame.transform.smoothscale(self.portrait, (48,48))
        self.p_rect = self.portrait.get_rect()
        self.p_rect.left, self.p_rect.top = (1, 1)
        # highlight cover.
        self.hover_surf = pygame.Surface( (self.rect.width-8, self.rect.height-8) ).convert_alpha() # 当悬停时要覆盖的高亮层
        self.hover_surf.fill( (210,210,210,60) )
        # add nick_name & gem number
        self.reset()
        # for receiving gems
        self.image = self.surf
        self.mask = pygame.mask.from_surface(self.image)

    def hover_on(self, pos):
        if ( self.rect.left < pos[0] < self.rect.right ) and ( self.rect.top < pos[1] < self.rect.bottom ):
            return True
        return False
    
    def reset(self):
        self.items.clear()
        # Check GEM
        self.gem_paint = REC_DATA['GEM']
        self.addItem( RichText( (f"| _IMG_{REC_DATA['GEM']}",f"| _IMG_{REC_DATA['GEM']}"), 
            pygame.image.load("image/gem0.png").convert_alpha(), self.font) 
        )

    def paint(self, screen, x, y, pos):
        '''cursor pos will be set to fit offset in this function'''
        # before painting, automatically check whether 
        # gem number showing is correct with database
        if self.gem_paint != REC_DATA['GEM']:
            self.reset()
        
        self._setPos(x, y)
        self.surf.fill( self.bgColor )
        pos = (pos[0]-x+self.rect.width//2, pos[1]-y+self.rect.height//2)
        in_y = 4
        lgg = REC_DATA["SYS_SET"]["LGG"]
        # Paint portrait
        self.surf.blit(self.portrait, self.p_rect)
        # Paint list items.
        for item in self.items:
            if item["type"] == "Text":
                txt = self.font[1].render(item["item"][lgg], True, (255,255,255))
                rect = txt.get_rect()
                rect.left = 4+self.p_rect.width
                rect.top = in_y
                self.surf.blit( txt, rect )
                in_y += max(rect.height, 22)
            elif item["type"] == "RichText":
                item["item"].paint(self.surf, 4+self.p_rect.width+item["item"].rect[lgg].width//2, in_y+item["item"].rect[lgg].height//2)
        screen.blit(self.surf, self.rect)
        # paint bg if hovered on.
        if self.hover_on(pos):
            rect = self.hover_surf.get_rect()
            rect.left = self.rect.left+4
            rect.top = self.rect.top+4
            screen.blit( self.hover_surf, rect )

    def receiveExp(self, num, typ):
        #REC_DATA["GEM"] += 1
        self.reset()
        pygame.mixer.Sound("audio/coin.wav").play(0)
