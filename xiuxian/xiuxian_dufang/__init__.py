import random
from re import I
from typing import Any, Tuple
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from nonebot import on_regex, on_command
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    MessageEvent,
    GroupMessageEvent,
    MessageSegment
)
from nonebot.params import RegexGroup
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.utils import (
    check_user,  markdown,
    get_msg_pic,
    CommandObjectID
)
cache_help = {}
sql_message = XiuxianDateManage()  # sql类

__dufang_help__ = f"""
\n>你是萌新，缺乏资源吗？
\n>你是大佬，无所事事吗？
\n>你是赌狗，抽蛋囊中羞涩？
\n>你是欧皇，次次一发入魂？
\n>你莫非怀才不遇，渴望一鸣惊人？
\n>你难道高手寂寞，孤独但求一败？
\n>快来金银阁试试手气呢?!
\n>竞猜指令：
\n>金银阁<qqbot-cmd-input text="金银阁大" show="大" reference="false" />/<qqbot-cmd-input text="金银阁小" show="小" reference="false" />/<qqbot-cmd-input text="金银阁奇" show="奇" reference="false" />/<qqbot-cmd-input text="金银阁偶" show="偶" reference="false" /> 请在指令后面加上灵石数量
\n><qqbot-cmd-input text="金银阁猜" show="金银阁猜数字" reference="false" />灵石数量 猜的数字(1，2，3，4，5，6，8，9，10)
\n#灵梦温馨提示：竞猜有风险，下手需谨慎！
""".strip()
dufang = on_command("s金银阁", permission=GROUP, priority=7, block=True)
guess_stone = on_command("s鉴石", permission=GROUP, priority=7, block=True)
dufang_help = on_command("s金银阁帮助", permission=GROUP, priority=7, block=True)
dufang = on_regex(
    r"(s金银阁)(大|小|奇|偶|猜)\s?(\d+)\s?(\d+)?",
    flags=I,
    permission=GROUP,
   # permission=GROUP and (SUPERUSER),    
    block=True
)

@dufang_help.handle(parameterless=[Cooldown(at_sender=False)])
async def dufang_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await dufang_help.finish()
    else:
        msg = __dufang_help__
        params_items = [('msg', msg)] 
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang_help.finish()


@guess_stone.handle(parameterless=[Cooldown(cd_time=XiuConfig().dufang_cd, at_sender=False)])
async def guess_stone_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    isUser, user_info, msg = check_user(event)
    user_id = user_info['user_id']
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await guess_stone.finish()

    user_message = sql_message.get_user_info_with_id(user_id)
    msg_text = args.extract_plain_text().strip()
    msg_parts = msg_text.split()
    if not msg_parts:
        msg = f"#【鉴石秘技】\n>    在修仙的世界里，灵石不仅是修行者们最宝贵的财富之一，更是通往更高境界的关键。然而，灵石之中往往蕴含着未知的秘密--有的灵石看似平凡无奇，却可能蕴藏着巨大的潜力;有的灵石外表华丽，实则一文不值。只有真正的鉴石大师才能洞察其中的奥秘。\n    当你使用「鉴石」指令时，将会尝试揭示灵石中的潜在能量。如果你的运气足够好，或许能发现那些隐藏在普通灵石中的惊人价值，甚至获得更多的灵石作为奖励。但若是运气不佳，也可能导致灵石失去原有的价值，甚至造成一定的损失。\n\n指令(最低境界要求【神火境初期】):鉴石 [灵石数量]\n【注意事项】\n- 鉴石是一项充满不确定性的活动，务必谨慎行事\n- 仅限达到一定境界的修行者方可尝试，以免因修为不足而遭受反噬，\n- 鉴石过程中，可能会触发各种意外事件，增加鉴石的趣味性和挑战"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要鉴石', '鉴石', False)],              
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await guess_stone.finish()    
    price_num = msg_parts[0]  # 获取灵石数量
    price = int(price_num) if price_num else 0

    if price <= 0:
        msg = "请输入正确的正数金额进行鉴石！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要鉴石', '鉴石', False)],              
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await guess_stone.finish()    
    if int(user_message['stone']) < price:
        msg = "道友的灵石不足，无法进行鉴石！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要鉴石', '鉴石', False)],              
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
     #   await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await guess_stone.finish()


    # 设置不同倍数对应的成功概率
    probabilities = {
        1: 0.2,  # 1倍返还成功率 20%
        2: 0.1,  # 2倍返还成功率 10%
        5: 0.01,  # 5倍返还成功率 1%
        10: 0.005  # 10倍返还成功率 0.5%
    }

    # 按概率确定返还倍数
    random_value = random.random()
    if random_value < probabilities[10]:
        multiplier = 10
    elif random_value < probabilities[10] + probabilities[5]:
        multiplier = 5
    elif random_value < probabilities[10] + probabilities[5] + probabilities[2]:
        multiplier = 2
    elif random_value < probabilities[10] + probabilities[5] + probabilities[2] + probabilities[1]:
        multiplier = 1
    else:
        multiplier = 0  # 鉴石失败，返还0倍

    # 判断鉴石结果
    if multiplier > 0:
        # 鉴石成功，按倍数返还灵石
        return_amount = price * multiplier
        sql_message.update_ls(user_id, return_amount, 1)  # 返还倍数金额
        if multiplier == 1:
            msg = f"道道友细细抚摸着灵石，感受到其中微弱的灵气涌动，虽然它并不显山露水，但依然是一颗珍贵的修行之物。随着一声清脆的裂响，这颗灵石轻微泛光，虽不璀璨，但稳稳地为你带来了回报。收获{return_amount}块灵石。"
        elif multiplier == 2:
            msg = f"此石初看平淡无奇，但道友目光如炬，竟察觉到其中藏有微妙玄机。你小心翼翼地敲击着石身，忽然，一声轻响之后，灵石内部似有神光乍现，竟然成功鉴得异石！收获{return_amount}块灵石！"
        elif multiplier == 5:
            msg = f"灵石在你手中突然一颤，仿佛呼应着你内心的渴望，一股无法言喻的力量蓬勃而出。伴随着灵石的绚丽破裂，耀眼的光芒一瞬间充斥整个空间，所有人都屏息凝神！灵石中竟蕴含着无尽能量，共获得{return_amount}块灵石！"
        elif multiplier == 10:
            msg = f"道友缓缓将手放在这块看似平凡的灵石之上，心中却隐隐感受到它与众不同的波动。就在你以为不过如此时，突然，灵石爆发出一阵夺目的强光，仿佛天际降临的神秘力量在石中涌动！随着灵石的破裂，你眼前的一切都被神光所笼罩！这是世所罕见的奇迹，道友竟然成功获得{return_amount}块灵石！！此等运势实乃修行者梦寐以求的天赐，今日你所见，怕是数百年难得一遇的造化！"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '再鉴石', '鉴石', False)],              
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
       # await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await guess_stone.finish()
    else:
        # 鉴石失败，扣除灵石
        sql_message.update_ls(user_id, price, 2)  # 扣除金额
        msg = f"手中灵石虽有模样，却未能展现出应有的奇迹，眼见它缓缓失去光泽，仿佛是一块再普通不过的石头。道友鉴石失败，损失灵石{price}块。相信道友下次定能再创佳绩，重振雄风！"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '再鉴石', '鉴石', False)],              
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
      #  await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await guess_stone.finish()

@dufang.handle(parameterless=[Cooldown(cd_time=XiuConfig().dufang_cd, at_sender=False)])
async def dufang_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    isUser, user_info, msg = check_user(event)
    user_id = user_info['user_id']
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await dufang.finish()

    user_message = sql_message.get_user_info_with_id(user_id)

    if args[1] is None:
        msg = f"请输入正确的指令，金银阁(大/小/奇/偶)(金额) 金银阁猜(金额) 猜的数字。 例如金银阁大10、金银阁奇10、金银阁猜10 3"
        params_items = [('msg', msg)] 
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()

    price = args[2]  # 300
    mode = args[1]  # 大、小、奇、偶、猜
    mode_num = 0
    if mode == '猜':
        mode_num = args[3]  # 猜的数值
        if str(mode_num) not in ['1', '2', '3', '4', '5', '6', '7', '8', '9','10']:
            msg = f"请输入正确的指令，金银阁(大/小/奇/偶)(金额) 金银阁猜(金额) 猜的数字。 例如金银阁大100、金银阁奇100、金银阁猜100 3"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '猜数字', '金银阁猜', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await dufang.finish()
    price_num = int(price)

    if int(user_message['stone']) < price_num:
        msg = "道友的灵石不足，请重新考虑！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()
    elif price_num == 0:
        msg = "走开走开，没钱也敢来这！"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()

    value = random.randint(1, 10)
    result = f"[CQ:dice,value={value}]"

    if value >= 6 and str(mode) == "大":
        sql_message.update_ls(user_id, price_num, 1)
      #  await bot.send_group_msg(group_id=int(send_group_id), message=result)
        msg = f"最终结果为{value}，你猜对了，收获灵石{price_num}块"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()
        
    elif value <= 5 and str(mode) == "小":
        sql_message.update_ls(user_id, price_num, 1)
       # await bot.send_group_msg(group_id=int(send_group_id), message=result)
        msg = f"最终结果为{value}，你猜对了，收获灵石{price_num}块"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()
    elif value %2==1 and str(mode) == "奇":
        sql_message.update_ls(user_id, price_num, 1)
     #   await bot.send_group_msg(group_id=int(send_group_id), message=result)
        msg = f"最终结果为{value}，你猜对了，收获灵石{price_num}块"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()
    elif value %2==0 and str(mode) == "偶":
        sql_message.update_ls(user_id, price_num, 1)
        msg = f"最终结果为{value}，你猜对了，收获灵石{price_num}块"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()
    elif str(value) == str(mode_num) and str(mode) == "猜":
        sql_message.update_ls(user_id, price_num * 5, 1)
        msg = f"最终结果为{value}，你猜对了，收获灵石{price_num * 5}块"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()
    else:
        sql_message.update_ls(user_id, price_num, 2)
        msg = f"最终结果为{value}，你猜错了，损失灵石{price_num}块"
        params_items = [('msg', msg)]  
        buttons = [
            [(2, '猜数字', '金银阁猜', False)], 
            [(2, '大', '金银阁大', False), (2, '小', '金银阁小', False)], 
            [(2, '偶', '金银阁偶', False), (2, '奇', '金银阁奇', False)],              
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await dufang.finish()