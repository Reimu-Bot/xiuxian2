import random
from datetime import datetime
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from nonebot import require, on_command, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent,
    GroupRequestEvent,
    NoticeEvent,
    MessageSegment
)
from nonebot.log import logger
from ..xiuxian_utils.xiuxian2_handle import XiuxianDateManage, XIUXIAN_IMPART_BUFF
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.item_json import Items
from ..xiuxian_utils.data_source import jsondata
from ..xiuxian_utils.utils import (
    check_user,Txt2Img,markdown,
    get_msg_pic,
    CommandObjectID,
)

items = Items()
cache_level_help = {}
scheduler = require("nonebot_plugin_apscheduler").scheduler
cache_beg_help = {}
sql_message = XiuxianDateManage()  # sql类
xiuxian_impart = XIUXIAN_IMPART_BUFF()
# 重置奇缘
@scheduler.scheduled_job("cron", hour=0, minute=59)
async def xiuxian_beg_():
    sql_message.beg_remake()
    logger.opt(colors=True).info(f"<green>仙途奇缘重置成功！</green>")

__beg_help__ = f"""
详情:
为了让初入仙途的道友们更顺利地踏上修炼之路，特别开辟了额外的机缘
天降灵石，助君一臂之力。
若有心人借此谋取不正之利，必将遭遇天道轮回，异象降临，后果自负。
诸位道友，若不信此言，可自行一试，便知天机不可泄露，天道不容欺。
""".strip()

__invite_help__ = f"""
#邀请奖励帮助:
感谢邀请灵梦加入群聊ヾ(o◕∀◕)ﾉヾ！现在，邀请灵梦进群即可领取200万灵石的奖励，帮助你在修仙之路上更进一步！

**特别提醒**：为了维护群聊的和谐，若因邀请后将灵梦踢出，将会随机扣除150万~230万灵石。希望大家珍惜灵梦的陪伴，感谢理解与支持！
""".strip()

beg_stone = on_command("仙途奇缘", permission=GROUP, priority=7, block=True)
beg_help = on_command("仙途奇缘帮助", permission=GROUP, priority=7, block=True)
invite_help = on_command("修仙邀请帮助", permission=GROUP, priority=7, block=True)
get_invite_reward = on_command("领取邀请奖励", permission=GROUP, priority=7, block=True)
notice_handler = on_notice(priority=5)

# 处理 kick_me 和 invite 类型事件
@notice_handler.handle()
async def handle_kick_invite(event: NoticeEvent):
    # 判断是否为 kick_me 或 invite 事件
    if event.notice_type == "group_increase" and getattr(event, "sub_type", "") == "invite":
        # 处理 invite 事件
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        group_id = event.group_id
        user_id = event.user_id  # 邀请人的 ID
        real_group_id = getattr(event, "real_group_id", None)  # 实际群 ID（可能适配器支持才会存在）
        real_user_id = getattr(event, "real_user_id", None)  # 实际用户 ID
        xiuxian_impart.insert_invite(group_id, user_id, real_group_id, real_user_id)
      #  invite_num = xiuxian_impart.get_invite_num(user_id)
       # if invite_num < 6:
      #     sql_message.update_ls(user_id, 3000000, 1)             
        logger.success(
            f"捕获 invite 事件: group_id={group_id}, user_id={user_id}, real_group_id={real_group_id}, real_user_id={real_user_id}"
        )

    elif event.notice_type == "group_decrease" and getattr(event, "sub_type", "") == "kick_me":
        # 处理 kick_me 事件
        nowtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        group_id = event.group_id
       # user_id = event.user_id  
        real_group_id = getattr(event, "real_group_id", None)  # 实际群 ID
        real_user_id = getattr(event, "real_user_id", None)  # 实际用户 ID
        invite_info = xiuxian_impart.get_ivite_with_gid(group_id)
       # print(invite_info)
        if invite_info:       
            cost = random.randint(1500000, 2300000)
            user_id = invite_info["user_id"]
            sql_message.update_ls(user_id, cost, 2)
           # xiuxian_impart.delete_invite(group_id)        
            # 打印并记录日志
            logger.success(
                f"捕获 kick_me 事件: group_id={group_id}, user_id={user_id}, real_group_id={real_group_id}, real_user_id={real_user_id}"
            )

@invite_help.handle(parameterless=[Cooldown(at_sender=False)])
async def invite_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_beg_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_beg_help[session_id]))
        await beg_help.finish()
    else:
        msg = __invite_help__
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '领取邀请奖励', '领取邀请奖励', True)],  
            [(2, '仙途奇缘', '仙途奇缘', True), (2, '修仙签到', '修仙签到', True)],               
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await invite_help.finish()

@get_invite_reward.handle(parameterless=[Cooldown(at_sender=False)])
async def get_invite_reward_(bot: Bot, event: GroupMessageEvent):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.get_user_id()
    isUser, user_info, msg = check_user(event)   
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await get_invite_reward.finish()  
    invite_num = xiuxian_impart.get_invite_num(user_id)
    ivt_num = user_info["invite_num"]
  #  if  ivt_num <= 5:
 #       invite_num = 5 if invite_num > 5 else invite_num
    if not invite_num or ivt_num >= invite_num:
        msg = f'没有获取到道友的邀请记录哦，快去邀请灵梦吧'
        params_items = [('msg', msg)]               
        buttons = [
            [(0, '邀请灵梦', f'https://bot.q.qq.com/s/f5n2re99n?id=102075800', True)],                
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await get_invite_reward.finish()
        cost = (invite_num - ivt_num) * 2000000
        sql_message.update_ls(user_id, cost, 1) 
        sql_message.update_invite_num(user_id, invite_num - ivt_num, 1)
        msg = f"道友邀请了灵梦加入{invite_num - ivt_num}个群聊 \n获得灵石奖励{cost}枚"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '领取邀请奖励', '领取邀请奖励', True)],  
            [(2, '仙途奇缘', '仙途奇缘', True), (2, '修仙签到', '修仙签到', True)],               
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await get_invite_reward.finish() 
    else:   
        msg = f"道友的邀请奖励已达到上限！可以探索其他精彩玩法，继续享受修仙的乐趣吧！"
        params_items = [('msg', msg)]               
        buttons = [ 
            [(2, '仙途奇缘', '仙途奇缘', True), (2, '修仙签到', '修仙签到', True)],               
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await get_invite_reward.finish()        
        
@beg_help.handle(parameterless=[Cooldown(at_sender=False)])
async def beg_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_beg_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_beg_help[session_id]))
        await beg_help.finish()
    else:
        msg = __beg_help__
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '仙途奇缘', '仙途奇缘', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await beg_help.finish()

@beg_stone.handle(parameterless=[Cooldown(at_sender=False)])
async def beg_stone_(bot: Bot, event: GroupMessageEvent):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.get_user_id()
    isUser, user_info, msg = check_user(event)   
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await beg_stone.finish()     
    user_msg = sql_message.get_user_info_with_id(user_id)
    user_root = user_msg['root_type']
    sect = user_info['sect_id']
    level = user_info['level']
    list_level_all = list(jsondata.level_data().keys())

    create_time = datetime.strptime(user_info['create_time'], "%Y-%m-%d %H:%M:%S.%f")
    now_time = datetime.now()
    diff_time = now_time - create_time
    diff_days = diff_time.days # 距离创建账号时间的天数
      
    sql_message.update_last_check_info_time(user_id) # 更新查看修仙信息时间
    if sect != None and user_root == "伪灵根":
        msg = f"道友已有宗门庇佑，又何必来此寻求机缘呢？"
        await bot.send_group_msg(group_id=event.group_id, message=msg)

    elif user_root in {"轮回道果", "真·轮回道果"}:
        msg = f"道友已是轮回大能，又何必来此寻求机缘呢？"
        await bot.send_group_msg(group_id=event.group_id, message=msg)
    
    elif list_level_all.index(level) >= list_level_all.index(XiuConfig().beg_max_level):
        msg = f"道友已跻身于{user_info['level']}层次的修行之人，可徜徉于四海八荒，自寻机缘与造化矣。"
        await bot.send_group_msg(group_id=event.group_id, message=msg)

    elif diff_days > XiuConfig().beg_max_days:
        msg = f"道友已经过了新手期,不能再来此寻求机缘了。"
        await bot.send_group_msg(group_id=event.group_id, message=msg)

    else:
        stone = sql_message.get_beg(user_id)
        if stone is None:
            msg = '贪心的人是不会有好运的！'
        else:
            msg = random.choice(
    [
        f"在一次深入古老森林的修炼旅程中，你意外地遇到了一位神秘的前辈高人。这位前辈不仅给予了你宝贵的修炼指导，还在临别时赠予了你 {stone} 枚灵石，以表达对你的认可和鼓励。",
        f"某日，在一个清澈的小溪边，一只珍稀的灵兽突然出现在你面前。它似乎对你的气息感到亲切，竟然留下了 {stone} 枚灵石，好像是在对你展示它的友好和感激。",
        f"在一次勇敢的探险中，你发现了一片被遗忘的灵石矿脉。通过采矿获得了 {stone} 枚灵石，这不仅是一次意外的惊喜，也是对你勇气和坚持的奖赏。",
        f"在一个宁静的夜晚，你抬头夜观星象，突然一颗流星划破夜空，落在你的附近。你跟随流星落下的轨迹找到了 {stone} 枚灵石，就像是来自天际的礼物。",
        f"在一次偶然的机会下，你在一座古老的山洞深处发现了一块充满灵气的巨大灵石，将它收入囊中并获得了 {stone} 枚灵石。这块灵石似乎蕴含着古老的力量，让你的修为有了不小的提升。",
        f"在一次探索未知禁地时，你解开了一个古老的阵法，这个阵法守护着数世纪的秘密。当最后一个符文点亮时，阵法缓缓散开，露出了其中藏有的 {stone} 枚灵石。",
        f"在一次河床淘金的经历中，你意外发现了一些隐藏在水流淤泥中的 {stone} 枚灵石。这些灵石对于修炼者来说极为珍贵，而你却在这样一个不经意的时刻发现了它们。这次发现让你更加相信，修炼之路上的每一次机缘都是命运的安排，值得你去珍惜和感激",
        f"在一次偶然的机会下，你在一座古墓的深处发现了一个隐藏的宝藏，其中藏有 {stone} 枚灵石。这些灵石可能是古时某位大能为后人留下的财富，而你，正是那位幸运的发现者。这次发现不仅大大增加了你的修为，也让你对探索古墓和古老传说充满了无尽的好奇和兴趣。",
        f"参加门派举办的比武大会，你凭借着出色的实力和智慧，一路过关斩将，但在最终对决中惜败萧炎。虽败犹荣，作为奖励，门派赠予了你 {stone} 枚灵石，这不仅是对你实力的认可，也是对你未来修炼的支持。",
        f"在一次对古老遗迹的探索中，你解开了一道埋藏已久的谜题。随着最后一个谜题的解开，一个密室缓缓打开，里面藏有的 {stone} 枚灵石作为奖励呈现在你面前。这些灵石对你来说，不仅是物质上的奖励，更是对你智慧和毅力的肯定。",
        f"修炼时，你意外地遇到了一次天降祥瑞的奇观，一朵灵花从天而降，化作了 {stone} 枚灵石落入你的背包中。这次祥瑞不仅让你的修为有了不小的提升，也让你深感天地之大，自己仍需不断努力，探索修炼的更高境界。",
        f"在一次门派分配的任务中，你表现出色，解决了一个困扰门派多时的难题。作为对你贡献的认可，门派特别奖励了你 {stone} 枚灵石。",
        f"一位神秘旅行者传授给你一张古老的地图，据说地图上标记的宝藏正是数量可观的灵石。经过一番冒险和探索，你终于找到了宝藏所在，获得了 {stone} 枚灵石!",
        f"在你帮助一位受伤的异兽后，作为感谢，它送给了你 {stone} 枚灵石。随后踏云而去，修炼之路上的每一个生命都值得尊重和帮助，而善行和仁心，往往能收获意想不到的回报。",
        f"在一次与妖兽的激战中胜出后，你发现了妖兽巢穴中藏有的 {stone} 枚灵石。这些灵石对你的修炼大有裨益，也让你对面对挑战时的勇气和决心有了更深的理解。",
        f"你在一次随机的交易中获得了一个外表不起眼的神秘盒子。当你好奇心驱使下打开它时，发现里面竟是一枚装满灵石的纳戒，收获了 {stone} 枚灵石！",
    ]
)

        params_items = [('msg', msg)]               
        buttons = [
            [(2, '仙途奇缘', '仙途奇缘', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))     

