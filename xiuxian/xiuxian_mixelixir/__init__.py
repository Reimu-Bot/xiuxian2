import random
import asyncio
import re
import math
from math import ceil
from nonebot import on_command, on_fullmatch
from nonebot.params import CommandArg
from nonebot.params import EventPlainText
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent,
    MessageSegment,
    ActionFailed
)
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, get_player_info, save_player_info, 
    UserBuffDate, XIUXIAN_IMPART_BUFF
)
from ..xiuxian_utils.utils import (
    check_user, send_msg_handler, 
    get_msg_pic, CommandObjectID, markdown
)
from ..xiuxian_utils.item_json import Items
from .mixelixirutil import get_mix_elixir_msg, tiaohe, check_mix, make_dict
from ..xiuxian_config import convert_rank, XiuConfig
from datetime import datetime
from .mix_elixir_config import MIXELIXIRCONFIG
from ..xiuxian_back.back_util import get_user_elixir_back_msg, get_user_yaocai_back_msg
sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()
items = Items()
cache_help = {}

mix_elixir = on_fullmatch("炼丹", priority=17, permission=GROUP, block=True)
mix_make = on_command("配方", priority=5, permission=GROUP, block=True)
elixir_help = on_fullmatch("炼丹帮助", priority=7, permission=GROUP, block=True)
mix_elixir_help = on_fullmatch("炼丹配方帮助", priority=7, permission=GROUP, block=True)
elixir_back = on_command("丹药背包", priority=10, permission=GROUP, block=True)
yaocai_back = on_command("药材背包", priority=10, permission=GROUP, block=True)
yaocai_get = on_command("灵田收取", aliases={"灵田结算"}, priority=8, permission=GROUP, block=True)
my_mix_elixir_info = on_fullmatch("我的炼丹信息", priority=6, permission=GROUP, block=True)
mix_elixir_sqdj_up = on_fullmatch("升级收取等级", priority=6, permission=GROUP, block=True)
mix_elixir_dykh_up = on_fullmatch("升级丹药控火", priority=6, permission=GROUP, block=True)

__elixir_help__ = f"""
#炼丹帮助信息:
\n><qqbot-cmd-input text=\"炼丹\" show=\"炼丹\" reference=\"false\" />:会检测背包内的药材,自动生成配方【一次最多匹配25种药材】
\n><qqbot-cmd-input text=\"配方\" show=\"配方\" reference=\"false\" />:发送配方领取丹药【配方主药.....】
\n><qqbot-cmd-input text=\"炼丹帮助\" show=\"炼丹帮助\" reference=\"false\" />:获取本帮助信息
\n><qqbot-cmd-input text=\"丹药背包\" show=\"丹药背包\" reference=\"false\" />:获取背包内丹药以及炼丹炉信息
\n><qqbot-cmd-input text=\"药材背包\" show=\"药材背包\" reference=\"false\" />:获取背包内药材信息
\n><qqbot-cmd-input text=\"炼丹配方帮助\" show=\"炼丹配方帮助\" reference=\"false\" />:获取炼丹配方帮助
\n><qqbot-cmd-input text=\"灵田收取\" show=\"灵田收取\" reference=\"false\" />:收取洞天福地里灵田的药材
\n><qqbot-cmd-input text=\"我的炼丹信息\" show=\"我的炼丹信息\" reference=\"false\" />:查询自己的炼丹信息
\n><qqbot-cmd-input text=\"升级收取等级\" show=\"升级收取等级\" reference=\"false\" />:每一个等级会增加灵田收取的数量
\n><qqbot-cmd-input text=\"升级丹药控火\" show=\"升级丹药控火\" reference=\"false\" />:每一个等级会增加炼丹的产出数量
"""

__mix_elixir_help__ = f"""
#炼丹配方信息
1、炼丹需要主药、药引、辅药
2、主药和药引控制炼丹时的冷热调和,冷热失和则炼不出丹药
3、草药的类型控制产出丹药的类型 
"""

#https://huggingface.co/spaces/chewing/liandan
@mix_elixir_sqdj_up.handle(parameterless=[Cooldown(at_sender=False)])
async def mix_elixir_sqdj_up_(bot: Bot, event: GroupMessageEvent):
    """收取等级升级"""
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
        await mix_elixir_sqdj_up.finish()
    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        buttons = [
            [(2, '洞天福地购买', '洞天福地购买', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_elixir_sqdj_up.finish()
    SQDJCONFIG = MIXELIXIRCONFIG['收取等级']
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_level = mix_elixir_info['收取等级']
    if now_level >= len(SQDJCONFIG):
        msg = f"道友的收取等级已达到最高等级，无法升级了"
        buttons = [
            [(2, '炼丹', '炼丹', True)],           
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_elixir_sqdj_up.finish()
    next_level_cost = SQDJCONFIG[str(now_level + 1)]['level_up_cost']
    if mix_elixir_info['炼丹经验'] < next_level_cost:
        msg = f"下一个收取等级所需要的炼丹经验为{next_level_cost}点，道友请炼制更多的丹药再来升级吧~"
        buttons = [
            [(2, '炼丹', '炼丹', True)],
            [(2, '丹药背包', '丹药背包', True), (2, '药材背包', '药材背包', True)],            
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_elixir_sqdj_up.finish()
    mix_elixir_info['炼丹经验'] = mix_elixir_info['炼丹经验'] - next_level_cost
    mix_elixir_info['收取等级'] = now_level + 1
    save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
    msg = f"道友的收取等级目前为：{mix_elixir_info['收取等级']}级，可以使灵田收获的药材增加{mix_elixir_info['收取等级']}个！"
    buttons = [
        [(2, '炼丹', '炼丹', True)],
        [(2, '升级收取等级', '升级收取等级', True), (2, '升级丹药控火', '升级丹药控火', True)],            
    ]        
    params_items = [('msg', msg)]       
    # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await mix_elixir_sqdj_up.finish()


@mix_elixir_dykh_up.handle(parameterless=[Cooldown(at_sender=False)])
async def mix_elixir_dykh_up_(bot: Bot, event: GroupMessageEvent):
    """丹药控火升级"""
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
        await mix_elixir_dykh_up.finish()
    user_id = user_info['user_id']
    DYKHCONFIG = MIXELIXIRCONFIG['丹药控火']
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_level = mix_elixir_info['丹药控火']
    if now_level >= len(DYKHCONFIG):
        msg = f"道友的丹药控火等级已达到最高等级，无法升级了"
        buttons = [
            [(2, '炼丹', '炼丹', True)],           
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_elixir_dykh_up.finish()
    next_level_cost = DYKHCONFIG[str(now_level + 1)]['level_up_cost']
    if mix_elixir_info['炼丹经验'] < next_level_cost:
        msg = f"下一个丹药控火等级所需要的炼丹经验为{next_level_cost}点，道友请炼制更多的丹药再来升级吧~"
        buttons = [
            [(2, '炼丹', '炼丹', True)],
            [(2, '丹药背包', '丹药背包', True), (2, '药材背包', '药材背包', True)],            
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_elixir_dykh_up.finish()
    mix_elixir_info['炼丹经验'] = mix_elixir_info['炼丹经验'] - next_level_cost
    mix_elixir_info['丹药控火'] = now_level + 1
    save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
    msg = f"道友的丹药控火等级目前为：{mix_elixir_info['丹药控火']}级，可以使炼丹收获的丹药增加{mix_elixir_info['丹药控火']}个！"
    buttons = [
        [(2, '炼丹', '炼丹', True)],
        [(2, '丹药背包', '丹药背包', True), (2, '药材背包', '药材背包', True)],            
    ]        
    params_items = [('msg', msg)]       
    # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await mix_elixir_dykh_up.finish()


@yaocai_get.handle(parameterless=[Cooldown(stamina_cost = 1, at_sender=False)])
async def yaocai_get_(bot: Bot, event: GroupMessageEvent):
    """灵田收取"""
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
        await yaocai_get.finish()

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        buttons = [
            [(2, '洞天福地购买', '洞天福地购买', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await yaocai_get.finish()
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    GETCONFIG = {
        "time_cost": 48,  # 单位小时
        "加速基数": 0.05
    }
    last_time = mix_elixir_info['收取时间']
    if last_time != 0:
        nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
        timedeff = round((datetime.strptime(nowtime, '%Y-%m-%d %H:%M:%S') - datetime.strptime(last_time,
                                                                                              '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600,
                         2)
        if timedeff >= round(GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['药材速度'])), 2):
            yaocai_id_list = items.get_random_id_list_by_rank_and_item_type(convert_rank(user_info['level'])[0], ['药材'])
            # 加入传承
            impart_data = xiuxian_impart.get_user_info_with_id(user_id)
            impart_reap_per = impart_data['impart_reap_per'] if impart_data is not None else 0
            #功法灵田收取加成
            main_reap = UserBuffDate(user_id).get_user_main_buff_data()
                
            if  main_reap != None: #功法灵田收取加成
                reap_buff = main_reap['reap_buff']
            else:
                reap_buff = 0
            num = mix_elixir_info['灵田数量'] + mix_elixir_info['收取等级'] + impart_reap_per + reap_buff
            msg = ''
            if not yaocai_id_list:
                sql_message.send_back(user_info['user_id'], 3001, '恒心草', '药材', num)  # 没有合适的，保底
                msg += f"道友成功收获药材：恒心草 {num} 个！\n"
            else:
                i = 1
                give_dict = {}
                while i <= num:
                    id = random.choice(yaocai_id_list)
                    try:
                        give_dict[id] += 1
                        i += 1
                    except LookupError:
                        give_dict[id] = 1
                        i += 1
                for k, v in give_dict.items():
                    goods_info = items.get_data_by_item_id(k)
                    msg += f"道友成功收获药材：{goods_info['name']} {v} 个！\n"
                    sql_message.send_back(user_info['user_id'], k, goods_info['name'], '药材', v)
            mix_elixir_info['收取时间'] = nowtime
            save_player_info(user_id, mix_elixir_info, "mix_elixir_info")
            buttons = [
                [(2, '药材背包', '药材背包', True)],
            ]        
            params_items = [('msg', msg)]       
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await yaocai_get.finish()
        else:
            msg = f"道友的灵田还不能收取，下次收取时间为：{round(GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['药材速度'])), 2) - timedeff}小时之后"
            buttons = [
                [(2, '灵田帮助', '灵田帮助', True)],
            ]        
            params_items = [('msg', msg)]       
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await yaocai_get.finish()


@my_mix_elixir_info.handle(parameterless=[Cooldown(at_sender=False)])
async def my_mix_elixir_info_(bot: Bot, event: GroupMessageEvent):
    """我的炼丹信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
            [(2, '修仙帮助', '修仙帮助 ', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await my_mix_elixir_info.finish()
    user_id = user_info['user_id']
    mix_elixir_info = get_player_info(user_id, 'mix_elixir_info')
    l_msg = [f"☆------道友的炼丹信息------☆"]
    msg = f"药材收取等级：{mix_elixir_info['收取等级']}\n"
    msg += f"丹药控火等级：{mix_elixir_info['丹药控火']}\n"
    msg += f"丹药耐药性等级：{mix_elixir_info['丹药耐药性']}\n"
    msg += f"炼丹经验：{mix_elixir_info['炼丹经验']}\n"
    l_msg.append(msg)
    if mix_elixir_info['炼丹记录'] != {}:
        l_msg.append(f"☆------道友的炼丹记录------☆")
        i = 1
        for k, v in mix_elixir_info['炼丹记录'].items():
            msg = f"编号：{i},{v['name']}，炼成次数：{v['num']}次"
            l_msg.append(msg)
            i += 1
    msg = "\n".join(l_msg)        
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '炼丹', '炼丹 ', True)],            
        [(2, '丹药背包', '丹药背包', True), (2, '药材背包', '药材背包', True)], 
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await my_mix_elixir_info.finish()


@elixir_help.handle(parameterless=[Cooldown(at_sender=False)])
async def elixir_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """炼丹帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await elixir_help.finish()
    else:
        msg = __elixir_help__
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '炼丹', '炼丹', True), (2, '灵田收取', '灵田收取', True)],            
            [(2, '配方', '配方', False), (2, '炼丹配方帮助', '炼丹配方帮助', True)],
            [(2, '丹药背包', '丹药背包', True), (2, '药材背包', '药材背包', True)],
            [(2, '升级收取等级', '升级收取等级', True), (2, '升级丹药控火', '升级丹药控火', True)],   
            [(2, '我的炼丹信息', '我的炼丹信息', True)],             
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await elixir_help.finish()


@mix_elixir_help.handle(parameterless=[Cooldown(at_sender=False)])
async def mix_elixir_help_(bot: Bot, event: GroupMessageEvent):
    """炼丹配方帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __mix_elixir_help__
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '炼丹', '炼丹', True), (2, '配方', '配方', False)],            
        [(2, '丹药背包', '丹药背包', True), (2, '药材背包', '药材背包', True)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await mix_elixir_help.finish()


user_ldl_dict = {}
user_ldl_flag = {}


@mix_elixir.handle(parameterless=[Cooldown(cd_time=30, at_sender=False)])
async def mix_elixir_(bot: Bot, event: GroupMessageEvent):
    global user_ldl_dict, user_ldl_flag
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await mix_elixir.finish()
    user_id = user_info['user_id']
    user_back = sql_message.get_back_msg(user_id)
    if user_back is None:
        msg = "道友的背包空空如也，无法炼丹！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '灵田收取', '灵田收取', True)],                        
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await mix_elixir.finish()    
    yaocai_dict = {}
    user_ldl_flag[user_id] = False  # 初始化炼丹炉标志
    for back in user_back:
        if back['goods_type'] == "药材":
            yaocai_dict[back['goods_id']] = items.get_data_by_item_id(back['goods_id'])
            yaocai_dict[back['goods_id']]['num'] = back['goods_num']
        elif back['goods_type'] == "炼丹炉":
            if user_id not in user_ldl_dict:
                user_ldl_dict[user_id] = {}
            user_ldl_dict[user_id][back['goods_id']] = back['goods_name']
            user_ldl_flag[user_id] = True
    
    if yaocai_dict == {}:
        msg = "道友的背包内没有药材，无法炼丹！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '灵田收取', '灵田收取', True)],                        
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await mix_elixir.finish()

    if not user_ldl_flag[user_id]:
        msg = "道友背包内没有炼丹炉，无法炼丹！"
        params_items = [('msg', msg)]               
        buttons = [                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await mix_elixir.finish()

    msg = "正在生成丹方，请稍候..."
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    yaocai_dict = await make_dict(yaocai_dict)
    finall_mix_elixir_msg = await get_mix_elixir_msg(yaocai_dict)
    if finall_mix_elixir_msg == {}:
        msg = "系统未检测到丹方，道友背包内的药材不满足！" 
        params_items = [('msg', msg)]        
        buttons = [ 
            [(2, '灵田收取', '灵田收取', True), (2, '药材背包', '药材背包', True)],         
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_elixir.finish()
    else:
        msg = f"\n道友生成的丹方：\n#☆------药材清单------☆"
        ldl_name = sorted(user_ldl_dict[user_id].items(), key=lambda x: x[0], reverse=False)[0][1]
        l_msg = []
        for k, v in finall_mix_elixir_msg.items():
            goods_info = items.get_data_by_item_id(v['id'])
          #  msg = f"\n道友生成的丹方：\n>☆------药材清单------☆"
           # msg += f"效果：{goods_info['desc']}\n"
            detail_msg = f"\n>名字: <qqbot-cmd-input text=\"查看物品效果{v['id']}\" show=\"{goods_info['name']}\" reference=\"false\" />  <qqbot-cmd-input text=\"配方{v['配方']['配方简写']}丹炉{ldl_name}\" show=\"合成\" reference=\"false\" />"
          #  msg += f"\n>☆------药材清单------☆"
            detail_msg += f"\n>主药：{v['配方']['主药']},{v['配方']['主药_level']}，数量：{v['配方']['主药_num']}"
            detail_msg += f"\n>药引：{v['配方']['药引']},{v['配方']['药引_level']}，数量：{v['配方']['药引_num']}"
            if v['配方']['辅药_num'] != 0:
                detail_msg += f"\n>辅药：{v['配方']['辅药']},{v['配方']['辅药_level']}，数量：{v['配方']['辅药_num']}"
            l_msg.append(detail_msg)
        if len(l_msg) > 51:
            l_msg = l_msg[:50]
        msg += "\n".join(l_msg)            
        params_items = [('msg', msg)]             
        buttons = [  
            [(2, '配方', '配方', False)], 
            [(2, '丹药背包', '丹药背包', True), (2, '药材背包', '药材背包', True)],         
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_elixir.finish()


# 配方
@mix_make.handle(parameterless=[Cooldown(stamina_cost = 3, at_sender=False)])
async def mix_elixir_(bot: Bot, event: GroupMessageEvent, mode: str = EventPlainText()):
    """配方"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.user_id
    pattern = r"主药([\u4e00-\u9fa5]+)(\d+)药引([\u4e00-\u9fa5]+)(\d+)辅药([\u4e00-\u9fa5]+)(\d+)丹炉([\u4e00-\u9fa5]+)+"
    matched = re.search(pattern, mode)
    if matched is None:
        msg = f"请输入正确的配方！"
        params_items = [('msg', msg)]             
        buttons = [  
            [(2, '配方', '配方', False)],         
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mix_make.finish()
    else:
        zhuyao_name = matched.groups()[0]
        zhuyao_num = int(matched.groups()[1])  # 数量一定会有
        check, zhuyao_goods_id = await check_yaocai_name_in_back(user_id, zhuyao_name, zhuyao_num)
        if not check:
            msg = f"请检查药材：{zhuyao_name} 是否在背包中，或者数量是否足够！"
            params_items = [('msg', msg)]             
            buttons = [  
                [(2, '药材背包', '药材背包', True)],         
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await mix_make.finish()
        yaoyin_name = matched.groups()[2]
        yaoyin_num = int(matched.groups()[3])  # 数量一定会有
        check, yaoyin_goods_id = await check_yaocai_name_in_back(user_id, yaoyin_name, yaoyin_num)
        if not check:
            msg = f"请检查药材：{yaoyin_name} 是否在背包中，或者数量是否足够！"
            params_items = [('msg', msg)]             
            buttons = [  
                [(2, '药材背包', '药材背包', True)],         
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await mix_make.finish()
        fuyao_name = matched.groups()[4]
        fuyao_num = int(matched.groups()[5])
        check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num)
        if not check:
            msg = f"请检查药材：{fuyao_name} 是否在背包中，或者数量是否足够！"
            params_items = [('msg', msg)]             
            buttons = [  
                [(2, '药材背包', '药材背包', True)],         
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await mix_make.finish()
        if zhuyao_name == fuyao_name:
            check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num + zhuyao_num)
            if not check:
                msg = f"请检查药材：{zhuyao_name} 是否在背包中，或者数量是否足够！"
                params_items = [('msg', msg)]             
                buttons = [  
                    [(2, '药材背包', '药材背包', True)],         
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await mix_make.finish()
        if yaoyin_name == fuyao_name:
            check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num + yaoyin_num)
            if not check:
                msg = f"请检查药材：{yaoyin_name} 是否在背包中，或者数量是否足够！"
                params_items = [('msg', msg)]             
                buttons = [  
                    [(2, '药材背包', '药材背包', True)],         
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await mix_make.finish()

        ldl_name = matched.groups()[6]
        check, ldl_info = await check_ldl_name_in_back(user_id, ldl_name)
        if not check:
            msg = f"请检查炼丹炉：{ldl_name} 是否在背包中！"
            params_items = [('msg', msg)]             
            buttons = [          
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await mix_make.finish()
        # 检测通过
        zhuyao_info = Items().get_data_by_item_id(zhuyao_goods_id)
        yaoyin_info = Items().get_data_by_item_id(yaoyin_goods_id)
        if await tiaohe(zhuyao_info, zhuyao_num, yaoyin_info, yaoyin_num):  # 调和失败
            msg = f"冷热调和失败！小心炸炉哦~"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await mix_make.finish()
        else:
            elixir_config = {
                str(zhuyao_info['主药']['type']): zhuyao_info['主药']['power'] * zhuyao_num
            }
            fuyao_info = Items().get_data_by_item_id(fuyao_goods_id)
            elixir_config[str(fuyao_info['辅药']['type'])] = fuyao_info['辅药']['power'] * fuyao_num
            is_mix, id = await check_mix(elixir_config)
            if is_mix:
                mix_elixir_info = get_player_info(user_id, 'mix_elixir_info')
                goods_info = Items().get_data_by_item_id(id)
                # 加入传承
                impart_data = xiuxian_impart.get_user_info_with_id(user_id)
                impart_mix_per = impart_data['impart_mix_per'] if impart_data is not None else 0
                #功法炼丹数加成
                main_dan_data = UserBuffDate(user_id).get_user_main_buff_data()
                
                if  main_dan_data != None: #功法炼丹数量加成
                    main_dan = main_dan_data['dan_buff']
                else:
                    main_dan = 0
                #功法炼丹经验加成
                main_dan_exp = UserBuffDate(user_id).get_user_main_buff_data()
                
                if  main_dan_exp != None: #功法炼丹经验加成
                    main_exp = main_dan_exp['dan_exp']
                else:
                    main_exp = 0
                
                num = 1 + ldl_info['buff'] + mix_elixir_info['丹药控火'] + impart_mix_per + main_dan#炼丹数量提升
                msg = f"恭喜道友成功炼成丹药：{goods_info['name']}{num}枚"
                # 背包sql
                sql_message.send_back(user_id, id, goods_info['name'], "丹药", num) #将炼制的丹药加入背包
                sql_message.update_back_j(user_id, zhuyao_goods_id, zhuyao_num) #将消耗的药材从背包中减去
                sql_message.update_back_j(user_id, fuyao_goods_id, fuyao_num)
                sql_message.update_back_j(user_id, yaoyin_goods_id, yaoyin_num)
                try:
                    var = mix_elixir_info['炼丹记录'][id]
                    now_num = mix_elixir_info['炼丹记录'][id]['num'] #now_num 已经炼制的丹药数量
                    if now_num >= goods_info['mix_all']:
                        msg += f"该丹药道友已炼制{now_num}次，无法获得炼丹经验了~"
                    elif now_num + num >= goods_info['mix_all']:
                        exp_num = goods_info['mix_all'] - now_num
                        mix_elixir_info['炼丹经验'] += (goods_info['mix_exp'] +  main_exp) * exp_num
                        msg += f"获得炼丹经验{goods_info['mix_exp'] * exp_num}点"
                    else:
                        mix_elixir_info['炼丹经验'] += (goods_info['mix_exp'] +  main_exp) * num
                        msg += f"获得炼丹经验{(goods_info['mix_exp'] +  main_exp) * num}点"
                    mix_elixir_info['炼丹记录'][id]['num'] += num
                except:
                    mix_elixir_info['炼丹记录'][id] = {}
                    mix_elixir_info['炼丹记录'][id]['name'] = goods_info['name']
                    mix_elixir_info['炼丹记录'][id]['num'] = num
                    mix_elixir_info['炼丹经验'] += (goods_info['mix_exp'] +  main_exp) * num
                    msg += f"获得炼丹经验{(goods_info['mix_exp'] +  main_exp) * num}点"
                save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
                params_items = [('msg', msg)]             
                buttons = [  
                    [(2, '配方', '配方', False)], 
                    [(2, '丹药背包', '丹药背包', True)],         
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await mix_make.finish()
            else:
                msg = f"没有炼成丹药哦~就不扣你药材啦"
                params_items = [('msg', msg)]             
                buttons = [  
                    [(2, '炼丹', '炼丹', True)],         
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await mix_make.finish()


@elixir_back.handle(parameterless=[Cooldown(at_sender=False)])
async def elixir_back_(bot: Bot, event: GroupMessageEvent):
    """丹药背包
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await elixir_back.finish()

    user_id = user_info['user_id']
    msg = get_user_elixir_back_msg(user_id)  # 获取背包信息

    # 定义分页参数
    items_per_page = 30  # 每页显示的丹药数量
    total_items = len(msg)  # 背包中丹药的总数
    page_num = math.ceil(total_items / items_per_page)  # 总页数

    # 初始化页码变量
    page = 0
    args = str(event.get_message()).strip().split()
    upbutton = ''
    downbutton = ''

    # 处理命令参数，检查输入的页码
    if len(args) > 1 and args[1].isdigit():
        page = int(args[1]) - 1  # 用户输入的页码减1（因为索引从0开始）
    elif len(args) == 1 and args[0].isdigit():
        page = int(args[0]) - 1
    else:
        # 如果用户没有输入页码，默认显示第一页
        page = 0

    # 页码范围限制
    if page < 0:
        page = 0
    if page > 0:
        upbutton = f'丹药背包 {page}'  # "上一页" 按钮
    if page_num > page + 1:
        downbutton = f'丹药背包 {page + 2}'  # "下一页" 按钮

    # 分页显示的丹药
    start_index = page * items_per_page
    end_index = min(start_index + items_per_page, total_items)
    current_page_items = msg[start_index:end_index]  # 当前页显示的丹药

    # 构建消息
    display_msg = [f"\n#道友***{user_info['user_name']}***的丹药背包：\n名字  拥有数量"] + current_page_items
    msg = "\n".join(display_msg)

    # 添加分页信息
    if page_num > 1:
        msg += f'\n第({page + 1}/{page_num})页  <qqbot-cmd-input text=\"丹药背包\" show=\"跳转\" reference=\"false\" />'

    # 构建按钮
    buttons = [
        [(2, '炼丹', '炼丹', False), (2, '配方', '配方', False)],
        [(2, '药材背包', '药材背包', True)],        
    ]
    if upbutton:
        buttons.append([(2, '⬅️上一页', upbutton, True)])
    if downbutton:
        buttons.append([(2, '➡️下一页', downbutton, True)])

    # 发送分页消息
    try:
        params_items = [('msg', msg)]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    except ActionFailed:
        await elixir_back.finish("查看背包失败!", reply_message=True)

    await elixir_back.finish()


@yaocai_back.handle(parameterless=[Cooldown(at_sender=False)])
async def yaocai_back_(bot: Bot, event: GroupMessageEvent):
    """药材背包
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await yaocai_back.finish()

    user_id = user_info['user_id']
    msg = get_user_yaocai_back_msg(user_id)  # 获取药材背包信息

    # 定义分页参数
    items_per_page = 20  # 每页显示的药材数量
    total_items = len(msg)  # 背包中药材的总数
    page_num = math.ceil(total_items / items_per_page)  # 总页数

    # 初始化页码变量
    page = 0
    args = str(event.get_message()).strip().split()
    upbutton = ''
    downbutton = ''

    # 处理命令参数，检查输入的页码
    if len(args) > 1 and args[1].isdigit():
        page = int(args[1]) - 1  # 用户输入的页码减1（因为索引从0开始）
    elif len(args) == 1 and args[0].isdigit():
        page = int(args[0]) - 1
    else:
        # 如果用户没有输入页码，默认显示第一页
        page = 0

    # 页码范围限制
    if page < 0:
        page = 0
    if page > 0:
        upbutton = f'药材背包 {page}'  # "上一页" 按钮
    if page_num > page + 1:
        downbutton = f'药材背包 {page + 2}'  # "下一页" 按钮

    # 分页显示的药材
    start_index = page * items_per_page
    end_index = min(start_index + items_per_page, total_items)
    current_page_items = msg[start_index:end_index]  # 当前页显示的药材

    # 构建消息
    display_msg = [f"道友***{user_info['user_name']}***的药材背包："] + current_page_items
    msg = "\n".join(display_msg)

    # 添加分页信息
    if page_num > 1:
        msg += f'\n第({page + 1}/{page_num})页'

    # 构建按钮
    buttons = [
        [(2, '炼丹', '炼丹', False), (2, '配方', '配方', False)],
        [(2, '丹药背包', '丹药背包', True)],        
    ]
    if upbutton:
        buttons.append([(2, '⬅️上一页', upbutton, True)])
    if downbutton:
        buttons.append([(2, '➡️下一页', downbutton, True)])

    try:
        params_items = [('msg', msg)]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    except ActionFailed:
        await yaocai_back.finish("查看背包失败!", reply_message=True)

    await yaocai_back.finish()



async def check_yaocai_name_in_back(user_id, yaocai_name, yaocai_num):
    flag = False
    goods_id = 0
    user_back = sql_message.get_back_msg(user_id)
    for back in user_back:
        if back['goods_type'] == '药材':
            if Items().get_data_by_item_id(back['goods_id'])['name'] == yaocai_name:
                if int(back['goods_num']) >= int(yaocai_num):
                    flag = True
                    goods_id = back['goods_id']
                    break
            else:
                continue
        else:
            continue
    return flag, goods_id


async def check_ldl_name_in_back(user_id, ldl_name):
    flag = False
    goods_info = {}
    user_back = sql_message.get_back_msg(user_id)
    for back in user_back:
        if back['goods_type'] == '炼丹炉':
            if back['goods_name'] == ldl_name:
                flag = True
                goods_info = Items().get_data_by_item_id(back['goods_id'])
                break
            else:
                continue
        else:
            continue
    return flag, goods_info
