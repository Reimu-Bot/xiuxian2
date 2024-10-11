try:
    import ujson as json
except ImportError:
    import json
import re
from pathlib import Path
import random
import os
import math
from nonebot.rule import Rule
from nonebot import get_bots, get_bot ,on_command, require
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    GROUP_ADMIN,
    GROUP_OWNER,
    ActionFailed,
    MessageSegment
)
from ..xiuxian_utils.lay_out import assign_bot, put_bot, layout_bot_dict, Cooldown
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage ,OtherSet, UserBuffDate,
    XIUXIAN_IMPART_BUFF, leave_harm_time
)
from ..xiuxian_config import convert_rank, XiuConfig, JsonConfig
from .makeboss import createboss, createboss_jj
from .bossconfig import get_boss_config, savef_boss
from .old_boss_info import old_boss_info
from ..xiuxian_utils.player_fight import Boss_fight
from ..xiuxian_utils.item_json import Items
items = Items()
from ..xiuxian_utils.utils import (
    number_to, check_user, markdown,
    get_msg_pic, CommandObjectID,
    pic_msg_format, send_msg_handler
)
from .. import DRIVER
# boss定时任务
require('nonebot_plugin_apscheduler')
from nonebot_plugin_apscheduler import scheduler

conf_data = JsonConfig().read_data()
config = get_boss_config()
cache_help = {}
del_boss_id = XiuConfig().del_boss_id
gen_boss_id = XiuConfig().gen_boss_id
group_boss = {}
#groups = config['open']
battle_flag = {}
sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()


def check_rule_bot_boss() -> Rule:  # 消息检测，是超管，群主或者指定的qq号传入的消息就响应，其他的不响应
    async def _check_bot_(bot: Bot, event: GroupMessageEvent) -> bool:
        if (event.sender.role == "admin" or
                event.sender.role == "owner" or
                event.get_user_id() in bot.config.superusers or
                event.get_user_id() in del_boss_id):
            return True
        else:
            return False

    return Rule(_check_bot_)

def check_rule_bot_boss_s() -> Rule:  # 消息检测，是超管或者指定的qq号传入的消息就响应，其他的不响应
    async def _check_bot_(bot: Bot, event: GroupMessageEvent) -> bool:
        if (event.get_user_id() in bot.config.superusers or
                event.get_user_id() in gen_boss_id):
            return True
        else:
            return False

    return Rule(_check_bot_)


create = on_command("生成妖界boss", aliases={"生成妖界Boss", "生成妖界BOSS"}, priority=5,
                    rule=check_rule_bot_boss_s(), block=True)
create_appoint = on_command("生成指定妖界boss", aliases={"生成指定妖界boss", "生成指定妖界BOSS", "生成指定BOSS", "生成指定boss"}, priority=5,
                            rule=check_rule_bot_boss_s())
boss_info = on_command("查询妖界boss", aliases={"查询妖界Boss", "查询妖界BOSS", "查询boss", "妖界Boss查询", "妖界BOSS查询", "boss查询"}, priority=6, permission=GROUP, block=True)
set_group_boss = on_command("妖界boss", aliases={"妖界Boss", "妖界BOSS"}, priority=13,
                            permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER), block=True)
battle = on_command("ss讨伐boss", aliases={"讨伐妖界boss", "ss讨伐Boss", "ss讨伐BOSS", "ss讨伐妖界Boss", "ss讨伐妖界BOSS"}, priority=6,
                    permission=GROUP, block=True)
boss_help = on_command("妖界boss帮助", aliases={"妖界Boss帮助", "妖界BOSS帮助"}, priority=5, block=True)
boss_delete = on_command("ss天罚boss", aliases={"ss天罚妖界boss", "ss天罚Boss", "ss天罚BOSS", "ss天罚妖界Boss", "ss天罚妖界BOSS"}, priority=7,
                         rule=check_rule_bot_boss(), block=True)
boss_delete_all = on_command("ss天罚所有boss", aliases={"ss天罚所有妖界boss", "ss天罚所有Boss", "ss天罚所有BOSS", "ss天罚所有妖界Boss","ss天罚所有妖界BOSS",
                                                  "ss天罚全部boss", "ss天罚全部妖界boss"}, priority=5,
                             rule=check_rule_bot_boss(), block=True)
boss_integral_info = on_command("妖界灵气查看",aliases={"查看妖界灵气", "妖界灵气商店", "妖界商店"} ,priority=10, permission=GROUP, block=True)
boss_integral_use = on_command("妖界灵气兑换", priority=6, permission=GROUP, block=True)

boss_time = config["Boss生成时间参数"]
__boss_help__ = f"""
#妖界Boss帮助信息:
\n>妖风四起，邪气弥漫！各地妖怪横生，苦不堪言。为维护人间安宁，守护天地正义，特召各路道友，共赴除妖降魔之战！击败Boss可获得灵气，收集灵气可兑换各种稀有道具~
\n><qqbot-cmd-input text="查询妖界boss" show="查询妖界boss" reference="false" /> 查询全部妖界Boss,可加Boss编号查询对应Boss信息
\n><qqbot-cmd-input text="讨伐妖界boss" show="讨伐妖界boss" reference="false" /> 讨伐妖界Boss,必须加Boss编号
\n><qqbot-cmd-input text="妖界boss" show="妖界boss帮助" reference="false" /> 获取妖界Boss帮助信息
\n><qqbot-cmd-input text="妖界商店" show="妖界商店" reference="false" /> 查看妖界商店的商品
\n><qqbot-cmd-input text="妖界灵气兑换" show="妖界灵气兑换" reference="false" /> 兑换对应的商品，可以批量购买
\n>每天上午九时生成30-40只随机大境界的妖界Boss
""".strip()


__boss_helps__ = f"""
妖界Boss帮助信息:
指令：
1、生成妖界boss:生成一只随机大境界的妖界Boss,超管权限
2、生成指定妖界boss:生成指定大境界与名称的妖界Boss,超管权限
3、查询妖界boss:查询本群全部妖界Boss,可加Boss编号查询对应Boss信息
4、妖界boss开启、关闭:开启后才可以生成妖界Boss,管理员权限
5、讨伐boss、讨伐妖界boss:讨伐妖界Boss,必须加Boss编号
6、妖界boss帮助、妖界boss:获取妖界Boss帮助信息
7、天罚boss、天罚妖界boss:删除妖界Boss,必须加Boss编号,管理员权限
8、天罚所有妖界boss:删除所有妖界Boss,,管理员权限
9、妖界灵气查看:查看自己的妖界灵气,和妖界灵气兑换商品
10、妖界灵气兑换+编号：兑换对应的商品，可以批量购买
""".strip()

@DRIVER.on_startup
async def read_boss_():
    global group_boss
    group_boss.update(old_boss_info.read_boss_info())
    logger.opt(colors=True).info(f"<green>历史boss数据读取成功</green>")
    
@DRIVER.on_shutdown
async def save_boss_():
    global group_boss
    old_boss_info.save_boss(group_boss)
    logger.opt(colors=True).info(f"<green>boss数据已保存</green>")

@scheduler.scheduled_job("cron", hour=9, minute=0)  # 每天上午9点执行
async def generate_daily_bosses():
    """定时生成世界Boss"""
    group_id = 'worldboss'
    group_boss[group_id] = []  # 清空列表
    boss_count = random.randint(50, 60)  # 随机生成50到60只Boss
    new_bosses = []  # 存储新生成的Boss

    for _ in range(boss_count):
        bossinfo = createboss()
        new_bosses.append(bossinfo)
        group_boss[group_id].append(bossinfo)
        old_boss_info.save_boss(bossinfo)

    logger.opt(colors=True).info(f"<green>已刷新妖界boss</green>")

@boss_help.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __boss_help__ 
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '查询妖界boss', '查询妖界boss', False), (2, '讨伐妖界boss', '讨伐妖界boss', False)],    
        [(2, '妖界商店', '妖界商店', True)],                 
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await boss_help.finish()


@boss_delete.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_delete_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """天罚妖界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip()
    group_id = "worldboss"
    boss_num = re.findall(r"\d+", msg)  # boss编号

    if boss_num:
        boss_num = int(boss_num[0])
    else:
        msg = f"请输入正确的妖界Boss编号!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()
    bosss = None
    try:
        bosss = group_boss[group_id]
    except:
        msg = f"本群尚未生成妖界Boss,请等待妖界boss刷新!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()

    if not bosss:
        msg = f"本群尚未生成妖界Boss,请等待妖界boss刷新!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()

    index = len(group_boss[group_id])

    if not (0 < boss_num <= index):
        msg = f"请输入正确的妖界Boss编号!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete.finish()

    group_boss[group_id].remove(group_boss[group_id][boss_num - 1])
    msg = f"该妖界Boss被突然从天而降的神雷劈中,烟消云散了"
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await boss_delete.finish()


@boss_delete_all.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_delete_all_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """天罚全部妖界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = args.extract_plain_text().strip()
    group_id = "worldboss"
    bosss = None
    try:
        bosss = group_boss[group_id]
    except:
        msg = f"本群尚未生成妖界Boss,请等待妖界boss刷新!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete_all.finish()

    if not bosss:
        msg = f"本群尚未生成妖界Boss,请等待妖界boss刷新!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await boss_delete_all.finish()

    group_boss[group_id] = []
    msg = f"所有的妖界Boss都烟消云散了~~"
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await boss_delete_all.finish()


@battle.handle(parameterless=[Cooldown(stamina_cost = 20, at_sender=False)])
async def battle_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """讨伐世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],                  
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()

    user_id = user_info['user_id']
    sql_message.update_last_check_info_time(user_id) # 更新查看修仙信息时间
    msg = args.extract_plain_text().strip()
    group_id = "worldboss"
    boss_num = re.findall(r"\d+", msg)  # boss编号

    if boss_num:
        boss_num = int(boss_num[0])
    else:
        msg = f"请输入正确的世界Boss编号!"
        sql_message.update_user_stamina(user_id, 20, 1)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查询妖界boss', '查询妖界boss', False), (2, '讨伐妖界boss', '讨伐妖界boss', False)],    
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()
    bosss = None
    try:
        bosss = group_boss[group_id]
    except:
        msg = f"尚未生成妖界Boss,请等待妖界boss刷新!"
        sql_message.update_user_stamina(user_id, 20, 1)
        params_items = [('msg', msg)]               
        buttons = [  
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()

    if not bosss:
        msg = f"尚未生成世界Boss,请等待妖界boss刷新!"
        sql_message.update_user_stamina(user_id, 20, 1)
        params_items = [('msg', msg)]               
        buttons = [ 
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()

    index = len(group_boss[group_id])

    if not (0 < boss_num <= index):
        msg = f"请输入正确的妖界Boss编号!"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查询妖界boss', '查询妖界boss', False), (2, '讨伐妖界boss', '讨伐妖界boss', False)],    
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()

    if user_info['hp'] is None or user_info['hp'] == 0:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)

    if user_info['hp'] <= user_info['exp'] / 10:
        time = leave_harm_time(user_id)
        msg = f"重伤未愈，动弹不得！距离脱离危险还需要{time}分钟！\n"
        msg += f"请道友进行闭关，或者使用药品恢复气血，不要干等，没有自动回血！！！"
        sql_message.update_user_stamina(user_id, 20, 1)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修炼', '修炼', True), (2, '闭关', '闭关', True)],    
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()

    player = {"user_id": None, "道号": None, "气血": None, "攻击": None, "真元": None, '会心': None, '防御': 0}
    userinfo = sql_message.get_user_real_info(user_id)
    user_weapon_data = UserBuffDate(userinfo['user_id']).get_user_weapon_data()

    impart_data = xiuxian_impart.get_user_info_with_id(user_id)
    boss_atk = impart_data['boss_atk'] if impart_data['boss_atk'] is not None else 0
    user_armor_data = UserBuffDate(userinfo['user_id']).get_user_armor_buff_data() #boss战防具会心
    user_main_data = UserBuffDate(userinfo['user_id']).get_user_main_buff_data() #boss战功法会心
    user1_sub_buff_data = UserBuffDate(userinfo['user_id']).get_user_sub_buff_data() #boss战辅修功法信息
    integral_buff = user1_sub_buff_data['integral'] if user1_sub_buff_data is not None else 0
    exp_buff = user1_sub_buff_data['exp'] if user1_sub_buff_data is not None else 0
    
    if  user_main_data != None: #boss战功法会心
        main_crit_buff = user_main_data['crit_buff']
    else:
        main_crit_buff = 0
  
    if  user_armor_data != None: #boss战防具会心
        armor_crit_buff = user_armor_data['crit_buff']
    else:
        armor_crit_buff = 0
    
    if user_weapon_data != None:
        player['会心'] = int(((user_weapon_data['crit_buff']) + (armor_crit_buff) + (main_crit_buff)) * 100)
    else:
        player['会心'] = (armor_crit_buff + main_crit_buff) * 100
    player['user_id'] = userinfo['user_id']
    player['道号'] = userinfo['user_name']
    player['气血'] = userinfo['hp']
    player['攻击'] = int(userinfo['atk'] * (1 + boss_atk))
    player['真元'] = userinfo['mp']
    player['exp'] = userinfo['exp']

    bossinfo = group_boss[group_id][boss_num - 1]
    if bossinfo['jj'] == '零':
        boss_rank = convert_rank((bossinfo['jj']))[0]
    else:
        boss_rank = convert_rank((bossinfo['jj'] + '中期'))[0]
    user_rank = convert_rank(userinfo['level'])[0]
    if boss_rank - user_rank >= 9:
        msg = f"道友已是{userinfo['level']}之人，妄图抢小辈的Boss，可耻！"
        sql_message.update_user_stamina(user_id, 20, 1)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '讨伐妖界boss', '讨伐妖界boss', False)],                    
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()
    if user_rank - boss_rank > 9:
        msg = f"道友的境界{userinfo['level']}，与Boss相差太大，小心废你修为！"
        sql_message.update_user_stamina(user_id, 20, 1)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '讨伐妖界boss', '讨伐妖界boss', False)],                    
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()           
    boss_old_hp = bossinfo['气血']  # 打之前的血量
    more_msg = ''
    battle_flag[group_id] = True
    result, victor, bossinfo_new, get_stone = await Boss_fight(player, bossinfo, bot_id=bot.self_id)
    if victor == "Boss赢了":
        group_boss[group_id][boss_num - 1] = bossinfo_new
        sql_message.update_ls(user_id, get_stone, 1)
        # 新增boss战斗灵气点数
        boss_now_hp = bossinfo_new['气血']  # 打之后的血量
        boss_all_hp = bossinfo['总血量']  # 总血量
        boss_integral = int(((boss_old_hp - boss_now_hp) / boss_all_hp) * 240)
        if boss_integral < 5:  # 摸一下不给
            boss_integral = 0
        if user_info['root'] == "器师":
            boss_integral = int(boss_integral * (1 + (user_rank - boss_rank)))
            points_bonus = int(80 * (user_rank - boss_rank))
            more_msg = f"道友低boss境界{user_rank - boss_rank}层，获得{points_bonus}%灵气加成！"

       # user_boss_fight_info = get_user_boss_fight_info(user_id)
       # user_boss_fight_info['boss_integral'] += boss_integral
        top_user_info = sql_message.get_top1_user()
        top_user_exp = top_user_info['exp']
       # save_user_boss_fight_info(user_id, user_boss_fight_info)
        sql_message.update_boss_score(user_id, boss_integral, 1)
        
        if exp_buff > 0 and user_info['root'] != "器师":
            now_exp = int(((top_user_exp * 0.1) / user_info['exp']) / (exp_buff * (1 / (convert_rank(user_info['level'])[0] + 1))))
            if now_exp > 1000000:
                now_exp = int(1000000 / random.randint(5, 10))
            sql_message.update_exp(user_id, now_exp)
            exp_msg = f"，获得修为{int(now_exp)}点！"
        else:
            exp_msg = f" "
            
        battle_flag[group_id] = False
        msg_content = '\n'.join([node['data']['content'] for node in result if 'content' in node['data']])
        msg = f"```\n{msg_content}\n```"
        msg += f"道友不敌{bossinfo['name']}，重伤逃遁，临逃前收获灵石{get_stone}枚，{more_msg}获得妖界灵气：{boss_integral}点{exp_msg} "
        if user_info['root'] == "器师" and boss_integral < 0:
            msg += f"\n如果出现负灵气，说明你境界太高了，玩器师就不要那么高境界了！！！"        
        params_items = [('msg', msg)] 
        buttons = [
            [(2, '查询妖界boss', '查询妖界boss', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()
    
    elif victor == "群友赢了":
        # 新增boss战斗灵气点数
        boss_all_hp = bossinfo['总血量']  # 总血量
        boss_integral = int((boss_old_hp / boss_all_hp) * 240)
        if user_info['root'] == "器师":
            boss_integral = int(boss_integral * (1 + (user_rank - boss_rank)))
            points_bonus = int(80 * (user_rank - boss_rank))
            more_msg = f"道友低boss境界{user_rank - boss_rank}层，获得{points_bonus}%灵气加成！"
        else:
            if boss_rank - user_rank >= 8:  # 超过太多不给
                boss_integral = 0
                more_msg = f"道友的境界超过boss太多了,不齿！"
                
        top_user_info = sql_message.get_top1_user()
        top_user_exp = top_user_info['exp']
        
        if exp_buff > 0 and user_info['root'] != "器师":
            now_exp = int(((top_user_exp * 0.1) / user_info['exp']) / (exp_buff * (1 / (convert_rank(user_info['level'])[0] + 1))))
            if now_exp > 1000000:
                now_exp = int(1000000 / random.randint(5, 10))
            sql_message.update_exp(user_id, now_exp)
            exp_msg = f"，获得修为{int(now_exp)}点！"
        else:
            exp_msg = f" "
                
        drops_id, drops_info =  boss_drops(user_rank, boss_rank, bossinfo, userinfo)
        if drops_id == None:
            drops_msg = " "
        elif boss_rank < convert_rank('遁一境中期')[0]:           
            drops_msg = f"boss的尸体上好像有什么东西， 凑近一看居然是{drops_info['name']}！ "
            sql_message.send_back(user_info['user_id'], drops_info['id'],drops_info['name'], drops_info['type'], 1)
        else :
            drops_msg = " "
            
        group_boss[group_id].remove(group_boss[group_id][boss_num - 1])
        battle_flag[group_id] = False
        sql_message.update_ls(user_id, get_stone, 1)
       # user_boss_fight_info = get_user_boss_fight_info(user_id)
      #  user_boss_fight_info['boss_integral'] += boss_integral
      #  save_user_boss_fight_info(user_id, user_boss_fight_info)
        sql_message.update_boss_score(user_id, boss_integral, 1)
        msg_content = '\n'.join([node['data']['content'] for node in result if 'content' in node['data']])
        msg = f"```\n{msg_content}\n```"
        msg += f"恭喜道友击败{bossinfo['name']}，收获灵石{get_stone}枚，{more_msg}获得妖界灵气：{boss_integral}点!{exp_msg} {drops_msg}"
        if user_info['root'] == "器师" and boss_integral < 0:
           msg += f"\n如果出现负灵气，说明你这器师境界太高了(如果总妖界灵气为负数，会帮你重置成0)，玩器师就不要那么高境界了！！！"        
        params_items = [('msg', msg)] 
        buttons = [
            [(2, '讨伐妖界boss', '讨伐妖界boss', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await battle.finish()


@boss_info.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_info_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查询世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = "worldboss"
    bosss = None
    try:
        bosss = group_boss[group_id]
    except:
        msg = f"本群尚未生成世界Boss,请等待世界boss刷新!"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查询妖界boss', '查询妖界boss', False), (2, '讨伐妖界boss', '讨伐妖界boss', False)],    
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_info.finish()

    msg = args.extract_plain_text().strip()
    boss_num = re.findall(r"\d+", msg)  # boss编号

    if not bosss:
        msg = f"本群尚未生成世界Boss,请等待世界boss刷新!"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查询妖界boss', '查询妖界boss', False), (2, '讨伐妖界boss', '讨伐妖界boss', False)],    
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_info.finish()

    Flag = False  # True查对应Boss
    if boss_num:
        boss_num = int(boss_num[0])
        index = len(group_boss[group_id])
        if not (0 < boss_num <= index):
            msg = f"请输入正确的世界Boss编号!"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '查询妖界boss', '查询妖界boss', False), (2, '讨伐妖界boss', '讨伐妖界boss', False)],    
                [(2, '妖界商店', '妖界商店', True)],                 
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await boss_info.finish()

        Flag = True

    bossmsgs = ""
    if Flag:  # 查单个Boss信息
        boss = group_boss[group_id][boss_num - 1]
        bossmsgs = f'''
世界Boss:{boss['name']}
境界：{boss['jj']}
总血量：{number_to(boss['总血量'])}
剩余血量：{number_to(boss['气血'])}
攻击：{number_to(boss['攻击'])}
携带灵石：{number_to(boss['stone'])}
        '''
        msg = bossmsgs
        if int(boss["气血"] / boss["总血量"]) < 0.5:
            boss_name = boss["name"] + "_c"
        else:
            boss_name = boss["name"]
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '讨伐此boss', f'讨伐妖界boss{boss_num}', True)],                    
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_info.finish()
    else:
        i = 1
        for boss in bosss:
            bossmsgs += f"\n><qqbot-cmd-input text=\"讨伐妖界boss{i}\" show=\"编号{i}\" reference=\"false\" />    {boss['jj']}Boss：<qqbot-cmd-input text=\"查询妖界boss{i}\" show=\"{boss['name']}\" reference=\"false\" />"
            i += 1
        msg = bossmsgs
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查询妖界boss', '查询妖界boss', False), (2, '讨伐妖界boss', '讨伐妖界boss', False)],    
            [(2, '妖界商店', '妖界商店', True)],                 
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_info.finish()


@create.handle(parameterless=[Cooldown(at_sender=False)])
async def create_(bot: Bot, event: GroupMessageEvent):
    """生成世界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = 'worldboss'

    # 生成 20 到 30 只 Boss
    boss_count = random.randint(30, 40)
    new_bosses = []  # 存储新生成的 Boss

    try:
        group_boss[group_id]
    except KeyError:
        group_boss[group_id] = []

    # 检查是否已达到 Boss 数量上限
    if len(group_boss[group_id]) + boss_count > config['Boss个数上限']:
        msg = f"本群世界Boss已达到上限{config['Boss个数上限']}个，无法继续生成"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await create.finish()

    # 生成 Boss
    for _ in range(boss_count):
        bossinfo = createboss()
        new_bosses.append(bossinfo)
        group_boss[group_id].append(bossinfo)
        old_boss_info.save_boss(bossinfo)

    # 生成成功消息
    boss_names = ', '.join(boss['name'] for boss in new_bosses)  # 获取所有 Boss 名称
    msg = f"已生成{boss_count}只 Boss: {boss_names}，诸位道友请击败 Boss 获得奖励吧!"
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    await create.finish()

@create_appoint.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """生成指定妖界boss"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = str(event.group_id)
    isInGroup = isInGroups(event)
    if not isInGroup:#不在配置表内
        msg = f"本群尚未开启妖界Boss，请联系管理员开启!"
        if XiuConfig().img:
            msg = await pic_msg_format(msg, event)
            pic = await get_msg_pic(msg)
            await create_appoint.finish(MessageSegment.image(pic))
        else:
            await create_appoint.finish(msg, at_sender=False)
    try:
        group_boss[group_id]
    except:
        group_boss[group_id] = []
    if len(group_boss[group_id]) >= config['Boss个数上限']:
        msg = f"本群妖界Boss已达到上限{config['Boss个数上限']}个，无法继续生成"
        if XiuConfig().img:
            msg = await pic_msg_format(msg, event)
            pic = await get_msg_pic(msg)
            await create_appoint.finish(MessageSegment.image(pic))
        else:
            await create_appoint.finish(msg, at_sender=False)
    arg_list = args.extract_plain_text().split()
    if len(arg_list) < 1:
        msg = f"请输入正确的指令，例如：生成指定妖界boss 祭道境 少姜"
        if XiuConfig().img:
            msg = await pic_msg_format(msg, event)
            pic = await get_msg_pic(msg)
            await create_appoint.finish(MessageSegment.image(pic))
        else:
            await create_appoint.finish(msg, at_sender=False)

    boss_jj = arg_list[0]  # 用户指定的境界
    boss_name = arg_list[1] if len(arg_list) > 1 else None  # 用户指定的Boss名称，如果有的话
    
    # 使用提供的境界和名称生成boss信息
    bossinfo = createboss_jj(boss_jj, boss_name)
    if bossinfo is None:
        msg = f"请输入正确的境界，例如：生成指定妖界boss 祭道境"
        if XiuConfig().img:
            msg = await pic_msg_format(msg, event)
            pic = await get_msg_pic(msg)
            await create_appoint.finish(MessageSegment.image(pic))
        else:
            await create_appoint.finish(msg, at_sender=False)
    group_boss[group_id].append(bossinfo)
    msg = f"已生成{bossinfo['jj']}Boss:{bossinfo['name']}，诸位道友请击败Boss获得奖励吧！"
    if XiuConfig().img:
        msg = await pic_msg_format(msg, event)
        pic = await get_msg_pic(msg)
        await create_appoint.finish(MessageSegment.image(pic))
    else:
        await create_appoint.finish(msg, at_sender=False)


@set_group_boss.handle(parameterless=[Cooldown(at_sender=False)])
async def set_group_boss_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """设置群妖界boss开关"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)
    isInGroup = isInGroups(event)  # True在，False不在

    if mode == '开启':
        if isInGroup:
            msg = f"本群已开启妖界Boss,请勿重复开启!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_boss.finish()
        else:    
            info = {
                str(group_id):{
                                "hours":config['Boss生成时间参数']["hours"],
                                "minutes":config['Boss生成时间参数']["minutes"]
                                }
                            }
            config['open'].update(info)
            savef_boss(config)
            msg = f"已开启本群妖界Boss!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_boss.finish()

    elif mode == '关闭':
        if isInGroup:
            try:
                del config['open'][str(group_id)]
            except:
                pass
            savef_boss(config)
            msg = f"已关闭本群妖界Boss!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_boss.finish()
        else:
            msg = f"本群未开启妖界Boss!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_group_boss.finish()

    elif mode == '':
        if str(send_group_id) in groups:
            msg = __boss_help__ + f"非指令:1、拥有定时任务:每{groups[str(send_group_id)]['hours']}小时{groups[str(send_group_id)]['minutes']}分钟生成一只随机大境界的妖界Boss"
        else:
            msg = __boss_help__ 
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await set_group_boss.finish()
    else:
        msg = f"请输入正确的指令:妖界boss开启或关闭!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await set_group_boss.finish()


@boss_integral_info.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_integral_info_(bot: Bot, event: GroupMessageEvent):
    """妖界灵气商店"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
            [(2, '修仙帮助', '修仙帮助', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_integral_info.finish()

    user_id = user_info['user_id']

    user_boss_score = sql_message.get_user_boss_score(user_id)
    if user_boss_score is None:
        user_boss_score = {'boss_integral': 0}  # 初始化为字典
    else:
        user_boss_score.setdefault('boss_integral', 0) 
    boss_integral_shop = config['妖界灵气商品']
    total_items = len(boss_integral_shop)
    items_per_page = 30
    page_num = math.ceil(total_items / items_per_page)

    # 初始化 page 变量
    page = 0
    args = str(event.get_message()).strip().split()
    upbutton = ''
    downbutton = ''

    # 处理命令参数，检查输入的页码
    if len(args) > 1 and args[1].isdigit():
        page = int(args[1]) - 1  # 用户输入的页码减1（因为列表索引从0开始）
    elif len(args) == 1 and args[0].isdigit():
        page = int(args[0]) - 1
    else:
        # 如果用户没有输入页码，默认显示第一页
        page = 0

    # 页码范围限制
    if page < 0:
        page = 0
    if page > 0:
        upbutton = f'妖界灵气商店 {page}'  # 因为索引是从0开始，显示页码要加1
    if page_num > page + 1:
        downbutton = f'妖界灵气商店 {page + 2}'

    # 分页显示的商品
    start_index = page * items_per_page
    end_index = min(start_index + items_per_page, total_items)
    
    l_msg = [f"#道友***{user_info['user_name']}***目前拥有的妖界灵气：{user_boss_score['boss_integral']}点\n编号 物品名称  所需灵气"]
    if boss_integral_shop != {}:
        for k, v in boss_integral_shop.items():
            #msg = f"编号 物品名称  所需灵气:{k}\n\n>"
            msg = f"\n><qqbot-cmd-input text=\"妖界灵气兑换{k}\" show=\"{k}\" reference=\"false\" />    <qqbot-cmd-input text=\"查看物品效果{v['id']}\" show=\"{v['desc']}\" reference=\"false\" />   {v['cost']}   <qqbot-cmd-input text=\"妖界灵气兑换{k}\" show=\"兑换\" reference=\"false\" />"
           # msg += f"所需妖界灵气：{v['cost']}点"
            l_msg.append(msg)
    else:
        l_msg.append(f"妖界灵气商店内空空如也！")
    if page_num > 1:
        msg += f'\n第({page + 1}/{page_num})页  <qqbot-cmd-input text=\"妖界灵气商店\" show=\"跳转\" reference=\"false\" />'        
    msgs = "\n\n".join(l_msg)
    params_items = [('msg', msgs)]
    
    # 初始化按钮列表
    button_list = [
        [(2, '灵气兑换', '灵气兑换', False), (2, '妖界商店', '妖界商店', True)],            
        [(2, '查询妖界boss', '查询妖界boss', True), (2, '查看物品效果', '查看物品效果', False)], 
    ]

    if upbutton != '':
        button_list.append([(2, '⬅️上一页', upbutton, True)])
  #  if page_num > 1:
  #      buttons.append([(2, f'⏺️跳转({page}/{page_num})', f'宗门成员查看', False)])        
    if downbutton != '':
        button_list.append([(2, '➡️下一页', downbutton, True)])

    # 调用 markdown 函数
    data = await markdown(params_items, button_list)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await boss_integral_info.finish()


@boss_integral_use.handle(parameterless=[Cooldown(at_sender=False)])
async def boss_integral_use_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """妖界灵气商店兑换"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_integral_use.finish()

    user_id = user_info['user_id']
    msg = args.extract_plain_text().strip()
    shop_info = re.findall(r"(\d+)\s*(\d*)", msg)

    if shop_info:
        shop_id = int(shop_info[0][0])
        quantity = int(shop_info[0][1]) if shop_info[0][1] else 1
    else:
        msg = f"请输入正确的商品编号！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '妖界灵气兑换', '妖界灵气兑换', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_integral_use.finish()

    boss_integral_shop = config['妖界灵气商品']
    is_in = False
    cost = None
    item_id = None
    if boss_integral_shop:
        for k, v in boss_integral_shop.items():
            if shop_id == int(k):
                is_in = True
                cost = v['cost']
                item_id = v['id']
                break
    else:
        msg = f"妖界灵气商店内空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '妖界灵气兑换', '妖界灵气兑换', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_integral_use.finish()
    if is_in:
        user_boss_score = sql_message.get_user_boss_score(user_id)
        total_cost = cost * quantity
        if user_boss_score['boss_integral'] < total_cost:
            msg = f"道友的妖界灵气不满足兑换条件呢"
            params_items = [('msg', msg)]
            buttons = [
                [(2, '妖界灵气兑换', '妖界灵气兑换', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await boss_integral_use.finish()
        else:
           # user_boss_fight_info['boss_integral'] -= total_cost
           # save_user_boss_fight_info(user_id, user_boss_fight_info)
            sql_message.update_boss_score(user_id, total_cost, 2)
            item_info = Items().get_data_by_item_id(item_id)
            sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], quantity)  # 兑换指定数量
            msg = f"道友成功兑换获得：{item_info['name']}{quantity}个"
            params_items = [('msg', msg)]
            buttons = [
                [(2, '妖界灵气兑换', '妖界灵气兑换', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await boss_integral_use.finish()
    else:
        msg = f"该编号不在商品列表内哦，请检查后再兑换"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '妖界灵气兑换', '妖界灵气兑换', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await boss_integral_use.finish()


def isInGroups(event: GroupMessageEvent):
    return str(event.group_id) in groups


PLAYERSDATA = Path() / "data" / "xiuxian" / "players"


def get_user_boss_fight_info(user_id):
    try:
        user_boss_fight_info = read_user_boss_fight_info(user_id)
    except:
        save_user_boss_fight_info(user_id, user_boss_fight_info)
    return user_boss_fight_info


def read_user_boss_fight_info(user_id):
    user_id = str(user_id)

    FILEPATH = PLAYERSDATA / user_id / "boss_fight_info.json"
    if not os.path.exists(FILEPATH):
        data = {"boss_integral": 0}
        with open(FILEPATH, "w", encoding="UTF-8") as f:
            json.dump(data, f, indent=4)
    else:
        with open(FILEPATH, "r", encoding="UTF-8") as f:
            data = json.load(f)

    # 检查 boss_integral 键值是否为负数
    if "boss_integral" in data and data["boss_integral"] < 0:
        data["boss_integral"] = 0
        with open(FILEPATH, "w", encoding="UTF-8") as f:
            json.dump(data, f, indent=4)

    return data


def save_user_boss_fight_info(user_id, data):
    user_id = str(user_id)

    if not os.path.exists(PLAYERSDATA / user_id):
        logger.opt(colors=True).info("<red>目录不存在，创建目录</green>")
        os.makedirs(PLAYERSDATA / user_id)

    FILEPATH = PLAYERSDATA / user_id / "boss_fight_info.json"
    data = json.dumps(data, ensure_ascii=False, indent=4)
    save_mode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=save_mode, encoding="UTF-8") as f:
        f.write(data)
        f.close()

def get_dict_type_rate(data_dict):
    """根据字典内概率,返回字典key"""
    temp_dict = {}
    for i, v in data_dict.items():
        try:
            temp_dict[i] = v["type_rate"]
        except:
            continue
    key = OtherSet().calculated(temp_dict)
    return key

def get_goods_type():
    data_dict = BOSSDLW['宝物']
    return get_dict_type_rate(data_dict)

def get_story_type():
    """根据概率返回事件类型"""
    data_dict = BOSSDLW
    return get_dict_type_rate(data_dict)

BOSSDLW ={"衣以候": "衣以侯布下了禁制镜花水月，",
    "金凰儿": "金凰儿使用了神通：金凰天火罩！",
    "九寒": "九寒使用了神通：寒冰八脉！",
    "莫女": "莫女使用了神通：圣灯启语诀！",
    "术方": "术方使用了神通：天罡咒！",
    "卫起": "卫起使用了神通：雷公铸骨！",
    "血枫": "血枫使用了神通：混世魔身！",
    "以向": "以向使用了神通：云床九练！",
    "砂鲛": "不说了！开鳖！",
    "神风王": "不说了！开鳖！",
    "鲲鹏": "鲲鹏使用了神通：逍遥游！",
    "天龙": "天龙使用了神通：真龙九变！",
    "历飞雨": "厉飞雨使用了神通：天煞震狱功！",
    "外道贩卖鬼": "不说了！开鳖！",
    "元磁道人": "元磁道人使用了法宝：元磁神山！",
    "博丽灵梦": "你身上带了钱对吧？",    
    "散发着威压的尸体": "尸体周围爆发了出强烈的罡气！"
    }


def boss_drops(user_rank, boss_rank, boss, user_info):
    boss_dice = random.randint(0,100)
    drops_id = None
    drops_info = None
    if boss_rank - user_rank >= 6:
        drops_id = None
        drops_info = None
    
    elif  boss_dice >= 90:
        drops_id,drops_info = get_drops(user_info)
       
    return drops_id, drops_info    
        
def get_drops(user_info):
    """
    随机获取一个boss掉落物
    :param user_info:用户信息类
    :param rift_rank:秘境等级
    :return 法器ID, 法器信息json
    """
    drops_data = items.get_data_by_item_type(['掉落物'])
    drops_id = get_id(drops_data, user_info['level'])
    drops_info = items.get_data_by_item_id(drops_id)
    return drops_id, drops_info

def get_id(dict_data, user_level):
    """根据字典的rank、用户等级、秘境等级随机获取key"""
    l_temp = []
    final_rank = convert_rank(user_level)[0]  # 秘境等级，会提高用户的等级
    pass_rank = convert_rank('搬血境初期')[0]  # 最终等级超过此等级会抛弃
    for k, v in dict_data.items():
        if v["rank"] >= final_rank and (v["rank"] - final_rank) <= pass_rank:
            l_temp.append(k)

    if len(l_temp) == 0:
        return None
    else:
        return random.choice(l_temp)
