import asyncio
import random
import math
import time
import pytz
from math import ceil
from datetime import datetime
from collections import Counter
from nonebot import on_command, require, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    MessageSegment,
    GROUP_ADMIN,
    GROUP_OWNER,
    ActionFailed
)
from ..xiuxian_utils.lay_out import assign_bot, assign_bot_group, Cooldown, CooldownIsolateLevel
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from .back_util import (
    get_user_main_back_msg, check_equipment_can_use,
    get_use_equipment_sql, get_shop_data, save_shop,
    get_item_msg, get_item_id_by_name, get_item_msg_rank, check_use_elixir,
    get_use_jlq_msg, get_no_use_equipment_sql
)
from .backconfig import get_auction_config, savef_auction, remove_auction_item
from ..xiuxian_utils.item_json import Items
from ..xiuxian_utils.utils import (
    check_user, get_msg_pic, 
    send_msg_handler, CommandObjectID,
    Txt2Img, number_to, markdown
)
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, get_weapon_info_msg, get_armor_info_msg,
    get_sec_msg, get_main_info_msg, get_sub_info_msg, UserBuffDate
)
from ..xiuxian_config import XiuConfig, convert_rank

items = Items()
config = get_auction_config()
groups = config['open']  # list，群交流会使用
auction = {}
AUCTIONSLEEPTIME = 120  # 拍卖初始等待时间（秒）
cache_help = {}
auction_offer_flag = False  # 拍卖标志
AUCTIONOFFERSLEEPTIME = 30  # 每次拍卖增加拍卖剩余的时间（秒）
auction_offer_time_count = 0  # 计算剩余时间
auction_offer_all_count = 0  # 控制线程等待时间
auction_time_config = config['拍卖会定时参数'] # 定时配置
sql_message = XiuxianDateManage()  # sql类
# 定时任务
set_auction_by_scheduler = require("nonebot_plugin_apscheduler").scheduler
reset_day_num_scheduler = require("nonebot_plugin_apscheduler").scheduler
end_auction_by_scheduler = require("nonebot_plugin_apscheduler").scheduler
down_exchange_day_scheduler = require("nonebot_plugin_apscheduler").scheduler
shopinfo = on_command("坊市商品信息", priority=8, permission=GROUP, block=True)
add_gongfa_gacha = on_command("抽取技能书", priority=8, permission=GROUP, block=True)
add_zhuangbei_gacha = on_command("抽取装备", priority=8, permission=GROUP, block=True)
back_to_database = on_command("转移交易数据", priority=8, permission=GROUP, block=True)
goods_re_root = on_command("炼金", priority=6, permission=GROUP, block=True)
goods_allre_root = on_command("一键炼金", priority=6, permission=GROUP, block=True)
send_goods = on_command("赠送修仙道具", priority=6, permission=GROUP, block=True)
send_yaocai_all = on_command("一键赠送药材", priority=6, permission=GROUP, block=True)
shop = on_command("坊市查看", aliases={"查看坊市"}, priority=8, permission=GROUP, block=True)
view_item = on_command("查看物品效果", aliases={"查看物品功效"}, priority=8, permission=GROUP, block=True)
view_item_name = on_command("查看修仙物品", priority=8, permission=GROUP, block=True)
myshop = on_command("我的坊市", aliases={"查看我的坊市"}, priority=8, permission=GROUP, block=True)
auction_view = on_command("仙市集会", aliases={"查看仙市集会"}, priority=8, permission=GROUP, block=True)
view_auction_item = on_command("拍卖品详情", aliases={"拍卖品详情查看"}, priority=8, permission=GROUP, block=True)
shop_added = on_command("坊市上架", priority=10, permission=GROUP, block=True)
shop_added_by_admin = on_command("系统坊市上架", priority=5, permission=SUPERUSER, block=True)
get_double_yaocai = on_command("刷新重复药材", priority=5, permission=SUPERUSER, block=True)
shop_off = on_command("坊市下架", priority=5, permission=GROUP, block=True)
shop_off_all = on_fullmatch("清空坊市", priority=3, permission=SUPERUSER, block=True)
main_back = on_command('我的背包', aliases={'我的物品'}, priority=10, permission=GROUP, block=True)
use = on_command("确认使用", priority=15, permission=GROUP, block=True)
confirm_use = on_command("使用", priority=15, permission=GROUP, block=True)
no_use_zb = on_command("换装", priority=5, permission=GROUP, block=True)
buy = on_command("坊市购买", priority=5, block=True)
auction_added = on_command("aaa提交拍卖品", aliases={"拍卖品提交"}, priority=10, permission=GROUP, block=True)
auction_withdraw = on_command("aaa撤回拍卖品", aliases={"拍卖品撤回"}, priority=10, permission=GROUP, block=True)
set_auction = on_command("aaa群拍卖会", priority=4, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER), block=True)
creat_auction = on_fullmatch("a举行拍卖会", priority=5, permission=GROUP and SUPERUSER, block=True)
offer_auction = on_command("拍卖", priority=5, permission=GROUP, block=True)
back_help = on_command("交易帮助", aliases={"坊市帮助", "坊市"}, priority=8, permission=GROUP, block=True)
xiuxian_sone = on_fullmatch("我的灵石", priority=4, permission=GROUP, block=True)
chakan_wupin = on_command("查看修仙界物品", priority=25, permission=GROUP, block=True)

__back_help__ = f"""
#坊市指令：
\n><qqbot-cmd-input text="抽取技能书" show="抽取技能书" reference="false" />：花费灵石获取技能书（1000万一次）
\n><qqbot-cmd-input text="抽取装备" show="抽取装备" reference="false" />：花费灵石获取装备（1000万一次）
\n><qqbot-cmd-input text="我的灵石" show="我的灵石" reference="false" />：查看我的灵石
\n><qqbot-cmd-input text="我的背包" show="我的背包" reference="false" />：查看我的背包
\n><qqbot-cmd-input text="使用" show="使用 物品名字" reference="false" />：使用+物品名字：使用物品,可批量使用
\n><qqbot-cmd-input text="换装" show="换装 装备名字" reference="false" />：换装+装备名字：卸载目标装备
\n><qqbot-cmd-input text="坊市购买" show="坊市购买 物品编号" reference="false" />：购买坊市内的物品。
\n><qqbot-cmd-input text="坊市查看" show="坊市查看" reference="false" />：查询坊市在售物品，交易有20%手续费。
\n><qqbot-cmd-input text="坊市查看" show="坊市筛选" reference="false" />：筛选查询坊市在售物品，指令：坊市查看 丹药/装备/技能/炼丹炉/聚灵旗/神物 物品名称（可选）
\n><qqbot-cmd-input text="仙市集会" show="仙市集会" reference="false" />：查询将在仙市集会拍卖的物品
\n><qqbot-cmd-input text="坊市上架" show="坊市上架" reference="false" /> 物品 金额，上架背包内的物品,最低金额50w。
\n><qqbot-cmd-input text="提交拍卖品" show="提交拍卖品" reference="false" /> 物品 金额，上架背包内的物品,最低金额随意。
\n><qqbot-cmd-input text="坊市下架" show="坊市下架 物品编号" reference="false" />：下架坊市内的物品！
\n><qqbot-cmd-input text="拍卖 " show="拍卖 金额" reference="false" />：对本次拍卖会的物品进行拍卖
\n><qqbot-cmd-input text="炼金" show="炼金 物品名字" reference="false" />：将物品炼化为灵石。
\n><qqbot-cmd-input text="送灵石" show="送灵石" reference="false" />：赠送道友灵石，有15%手续费。
\n><qqbot-cmd-input text="赠送修仙道具" show="赠送物品" reference="false" />：赠送道友物品。手续费较高，请谨慎赠送。
\n><qqbot-cmd-input text="修仙发红包" show="修仙发红包" reference="false" />：土豪给群友发红包，有20%手续费。
\n>查看修仙界物品:支持类型【<qqbot-cmd-input text="查看修仙界物品 功法" show="功法" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品 神通" show="神通" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品 丹药" show="丹药" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品 合成丹药" show="合成丹药" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品 法器" show="法器" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品 防具" show="防具" reference="false" />】
非指令：
每天{auction_time_config['hours']}点生成一场<qqbot-cmd-input text="仙市集会" show="拍卖会" reference="false" />
""".strip()

#\n><qqbot-cmd-input text="金银阁帮助" show="金银阁" reference="false" />：要来金银阁试试手气吗？！
__back_helps__ = f"""
指令：
1、我的灵石：查看我的灵石
2、使用+物品名字：使用物品,可批量使用
3、换装+装备名字：卸载目标装备
4、坊市购买+物品编号:购买坊市内的物品，可批量购买
5、坊市查看、查看坊市:查询坊市在售物品
6、查看拍卖品、仙市集会:查询将在拍卖品拍卖的玩家物品
7、坊市上架:坊市上架 物品 金额，上架背包内的物品,最低金额50w，可批量上架
8、提交拍卖品:提交拍卖品 物品 金额，上架背包内的物品,最低金额随意，可批量上架(需要超管重启机器人)
9、系统坊市上架:系统坊市上架 物品 金额，上架任意存在的物品，超管权限
10、坊市下架+物品编号：下架坊市内的物品，管理员和群主可以下架任意编号的物品！
11、群交流会开启、关闭:开启/关闭拍卖行功能，管理员指令，注意：会在机器人所在的全部已开启此功能的群内通报拍卖消息
12、拍卖+金额：对本次拍卖会的物品进行拍卖
13、炼金+物品名字：将物品炼化为灵石,支持批量炼金和绑定丹药炼金
14、背包帮助:获取背包帮助指令
15、查看修仙界物品:支持类型【功法|神通|丹药|合成丹药|法器|防具】
16、清空坊市
非指令：
定时生成拍卖会,每天{auction_time_config['hours']}点生成一场拍卖会
""".strip()

# 重置丹药每日使用次数
@reset_day_num_scheduler.scheduled_job("cron", hour=23, minute=59, )
async def reset_day_num_scheduler_():
    sql_message.day_num_reset()
    logger.opt(colors=True).info(f"<green>每日丹药使用次数重置成功！</green>")

@set_auction_by_scheduler.scheduled_job("cron", hour=14, minute=57)
async def set_auction_by_scheduler_():
    global auction, auction_offer_flag, auction_offer_all_count, auction_offer_time_count
    
    # 调用函数删除所有拍卖物品
    try:
        sql_message.remove_all_auctions()
        logger.opt(colors=True).info(f"<green>所有拍卖品信息已成功移除！</green>")
    except Exception as e:
        logger.opt(colors=True).info(f"<red>拍卖品删除失败：{e}</red>")
        return
    
    auction_items = []
    try:
        auction_id_list = get_auction_id_list()
        auction_count = random.randint(20, 30)  # 随机挑选系统拍卖品数量
        auction_ids = random.sample(auction_id_list, auction_count)
        
        for auction_id in auction_ids:
            item_info = items.get_data_by_item_id(auction_id)
            item_quantity = 1
            if item_info['type'] in ['神物', '丹药']:
                item_quantity = random.randint(1, 3)  # 如果是丹药的话随机挑1-3个
            start_price = get_auction_price_by_id(auction_id)['start_price']
            newtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status = 1
            seller_id = 0
            string = "一二三四五六七八九"
            random_list = random.sample(list(string), 5)
            auctionid = ''.join(random_list)
            auction_items.append((auctionid, auction_id, seller_id, 1, start_price, False, newtime, 0, status))
        
        # 将生成的拍卖品插入数据库
        sql_message.insert_auction_items(auctionid, seller_id, auction_items, newtime, 0, status)
    except LookupError:
        logger.opt(colors=True).info("<red>获取不到拍卖物品的信息，请检查配置文件！</red>")
        return

        
@end_auction_by_scheduler.scheduled_job("cron", hour=22, minute=5)  # 修正定时任务
async def end_auction_by_scheduler_():
    global auction, auction_offer_time_count
    logger.opt(colors=True).info(f"<green>野生的大世界定时拍卖会结束了！！！</green>")

    # 获取所有拍卖数据，假设 sql_message.get_all_auction_data() 返回所有拍卖记录
    auction_results = sql_message.get_all_auction_data()

    # 去重，确保每个拍卖ID只处理一次
    seen_auctions = set()
    filtered_auction_results = [auction for auction in auction_results if auction['auctionid'] not in seen_auctions and not seen_auctions.add(auction['auctionid'])]

    # 遍历去重后的拍卖结果
    for idx, auction in enumerate(filtered_auction_results):
        auctionid = auction['auctionid']
        auction_id = auction['auction_id']
        item_quantity = auction['item_quantity']
        start_price = auction['start_price']
        user_id = auction['user_id']
        seller_id = auction['seller_id']
        status = auction['status']
        quantity = auction['item_quantity']
        is_user_auction = auction['is_user_auction']  # 获取是否是用户发起的拍卖
        
        # 获取物品名称，假设 items.get_data_by_item_id 返回物品字典
        item_data = items.get_data_by_item_id(str(auction_id))  
        item_name = item_data.get('name', '未知物品')
        item_type = item_data.get('type', '未知类型')

        # 获取用户信息，假设返回字典
        final_user_info = sql_message.get_user_info_with_id(user_id)

        # 如果用户存在且灵石足够支付起拍价 * 数量
     #   if final_user_info and final_user_info['stone'] >= (int(start_price) * quantity):
            # 用户支付成功
        if int(user_id) != 0:
            sql_message.update_ls(user_id, int(start_price) * quantity, 2)  # 扣除用户灵石
            if item_type == '炼丹炉':  # 检查物品类型
                sql_message.send_back(user_id, auction_id, item_name, item_type, quantity, 1)  # 特殊处理
            else:
                sql_message.send_back(user_id, auction_id, item_name, item_type, quantity) 
            logger.info(f"系统拍卖完成，物品 {item_name} 已交给买家 {user_id}")
        else:
            logger.info(f"流拍了")
            
        if is_user_auction == "Yes":
            auction_earnings = int(start_price) * quantity * 0.7  # 70% 给卖家
            sql_message.update_ls(seller_id, auction_earnings, 1)  # 卖家增加收入
            logger.info(f"卖家 {seller_id} 收到了 {auction_earnings} 枚灵石的拍卖收入")

    logger.opt(colors=True).info(f"正在更新所有拍卖品的状态为已完成")
    sql_message.update_all_auction_status(2)

# 每日1点执行交易所7天无销售商品自动下架
@down_exchange_day_scheduler.scheduled_job("cron", hour=2, minute=0, )
async def down_exchange_day_scheduler_():
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
 #   if now.hour not in [0]:
 #       return
    findtime = math.ceil(time.time()) - 259200
    exchange_list = sql_message.get_exchange_list_time(findtime)
    if exchange_list == 0:
        logger.opt(colors=True).info(f"今日无超时寄售商品，无需下架")
        return
    down_num = 0
    for exchange_info in exchange_list:
        sql_message.send_back(exchange_info[1], exchange_info[3], exchange_info[2], exchange_info[4], exchange_info[5])
        sql_message.delete_exchange(exchange_info[0])
        down_num += 1
    logger.opt(colors=True).info(f"今日已执行{down_num}件交易所超期商品下架")

@back_help.handle(parameterless=[Cooldown(at_sender=False)])
async def back_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """背包帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await back_help.finish()
    else:
        msg = __back_help__
        title = ''
        font_size = 32
        img = Txt2Img(font_size)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],            
            [(2, '坊市购买', '坊市购买', False), (2, '坊市查看', '坊市查看', True)],
            [(2, '我的背包', '我的背包', True), (2, '仙市集会', '仙市集会', True)],
           # [(2, '金银阁', '金银阁帮助', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await back_help.finish()

@confirm_use.handle(parameterless=[Cooldown(at_sender=False)])
async def confirm_use_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """确认使用"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg_text = args.extract_plain_text().strip()
    
    if not msg_text:
        msg = '道友要使用什么？ 请提供使用物品。自行在指令前加上‘确认’二字。示例：确认使用修士道袍'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '确认使用', f'确认使用', False)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        return  # 结束处理
    args = msg_text.split()   
    if len(args) < 1:
        msg = '道友要使用什么？ 请提供使用物品。自行在指令前加上‘确认’二字。示例：确认使用修士道袍'
    else:
        goods = args[0]
        msg = f'请自行在指令前加上‘确认’二字，示例：**确认使用{goods}**'
        
        params_items = [('msg', msg)]               
        buttons = [
            [(2, f'确认使用{goods}', f'确认使用{goods}', False)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))    
    await confirm_use.finish()

@back_to_database.handle(parameterless=[Cooldown(at_sender=False)])
async def back_to_database_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """转移数据"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_id = "worldexchange"
    shop_data = get_shop_data()
    
    # 遍历数据
    for exchangeid, item in shop_data.items():
        # 确保每个 item 是字典实例
        if isinstance(item, dict):
            user_id = item.get('user_id')
            goods_name = item.get('goods_name')
            goods_id = item.get('goods_id')
            goods_type = item.get('goods_type')
            price = item.get('price')
            user_name = item.get('user_name')
            stock = item.get('stock')
            uptime = math.ceil(time.time())
            
            # 将数据插入数据库
            sql_message.new_exchange(exchangeid, user_id, goods_name, goods_id, goods_type, price, user_name, stock, uptime)

    # 反馈总结信息
    success_msg = "所有商品导入成功！"
    params_items = [('msg', success_msg)]               
    buttons = [
        [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],
    ]
    
    # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)   
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await back_to_database.finish()

@xiuxian_sone.handle(parameterless=[Cooldown(at_sender=False)])
async def xiuxian_sone_(bot: Bot, event: GroupMessageEvent):
    """我的灵石信息"""
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
        await xiuxian_sone.finish()
    msg = f"当前灵石：{user_info['stone']:,} | ({number_to(user_info['stone'])})"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '我的状态', '我的状态', True)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await xiuxian_sone.finish()


buy_lock = asyncio.Lock()


@buy.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def buy_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """购物"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await buy.finish()

    args = args.extract_plain_text().strip().split()
    if len(args) < 1:
        # 没有输入任何参数
        msg = "请输入正确指令！例如：坊市购买 物品编号 数量"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市购买', '坊市购买', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await buy.finish()
    exchangeid = args[0]
    user_id = user_info['user_id']
    exchange_info = sql_message.get_exchange_info(exchangeid)
    #print(exchange_info)
    if exchangeid == 0 or not isinstance(exchange_info, (list, tuple)):
        msg = "请输入正确指令或者物品已售出！例如：坊市购买 物品编号 数量"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市购买', '坊市购买', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await buy.finish()
    if len(args) == 2:
        try:
            buy_num = int(args[1])
        except ValueError:
            msg = "请输入正确指令！例如：坊市购买 物品编号 数量"
            params_items = [('msg', msg)]
            buttons = [
                [(2, '坊市购买', '坊市购买', False)],
            ]
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await buy.finish()
    else:
        buy_num = 1
    if buy_num < 1: 
        msg = "请输入正确指令或者物品已售出！例如：坊市购买 物品编号 数量" 
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市购买', '坊市购买', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await buy.finish()
    if buy_num > int(exchange_info[3]):
        msg = f'坊市中物品数量不足{buy_num}，请重新输入数量'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市购买', '坊市购买', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await buy.finish()

    need_score = buy_num * int(exchange_info[4])
    my_score = user_info['stone']
    if need_score > my_score:
        msg = f'购买{buy_num}件{exchange_info[0]}需要灵石{need_score}，您的灵石不足'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市购买', '坊市购买', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await buy.finish()        
    if buy_num == int(exchange_info[3]):
        sql_message.delete_exchange(exchangeid)
    else:
        sql_message.update_exchange(exchangeid, 0 - buy_num)
    shop_goods_id = exchange_info[2]
    shop_goods_name = exchange_info[0]
    shop_goods_type = exchange_info[1]
    sql_message.update_ls(user_id, need_score, 2)
    sql_message.send_back(user_id, shop_goods_id, shop_goods_name, shop_goods_type, buy_num)

    service_charge = int(need_score * 0.2)  # 手续费20%
    give_stone = need_score - service_charge
    shop_user_id = exchange_info[5]
    msg = f"道友成功购买{buy_num}个{shop_goods_name}，消耗灵石{need_score:,}枚！,坊市收取手续费：{service_charge:,}枚灵石！"
    sql_message.update_ls(shop_user_id, give_stone, 1)
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '坊市购买', '坊市购买', False), (2, '坊市查看', '坊市查看', True)],            
        [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await buy.finish()


@shopinfo.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def shopinfo_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """坊市商品信息"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shopinfo.finish()

    args = args.extract_plain_text().strip().split()
    if len(args) < 1:
        # 没有输入任何参数
        msg = "请输入正确指令！例如：坊市商品信息 物品编号"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市商品信息', '坊市商品信息', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shopinfo.finish()
    exchangeid = args[0]
    user_id = user_info['user_id']
    exchange_info = sql_message.get_exchange_info(exchangeid)
    #print(exchange_info)
    if exchangeid == 0 or not isinstance(exchange_info, (list, tuple)):
        msg = "请输入正确指令或者物品已售出！例如：坊市购买 物品编号"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市商品信息', '坊市商品信息', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shopinfo.finish()

    goods_id = exchange_info[2]        
    msg = get_item_msg(goods_id)
    msg += f'\n#商品单价：{exchange_info[4]}\n#商品数量：{exchange_info[3]}'
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '购买此商品', f'坊市购买{exchangeid}', False)],
    ]
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await shopinfo.finish() 

@shop.handle(parameterless=[Cooldown(at_sender=False)])
async def shop_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """坊市查看"""
    # 分配 bot 和群组 ID
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg_text = args.extract_plain_text().strip()
    args = msg_text.split()
    upbutton = ''
    downbutton = '' 
    if len(args) > 0:
        if args[0].isdigit():
            page = int(args[0]) - 1
            exchangenum,exchange_list = sql_message.get_exchange_list(page)
            page_num = math.floor(exchangenum / 30) + 1
            if page > 0:
                upbutton = f'坊市查看{page}'
            if page_num > page + 1:
                downbutton = f'坊市查看{page+2}'
        else:
            goods_type = args[0]
            if goods_type not in ['装备','技能','丹药', '药材', '炼丹炉', '聚灵旗', '神物']:
                msg = '请输入正确的类型 装备 技能 丹药 药材 炼丹炉 聚灵旗 神物'
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '装备', '坊市查看 装备', False), (2, '技能', '坊市查看 技能', False)],            
                    [(2, '丹药', '坊市查看 丹药', False), (2, '药材', '坊市查看 药材', False)],
                    [(2, '炼丹炉', '坊市查看 炼丹炉', False), (2, '聚灵旗', '坊市查看 聚灵旗', False)], 
                    [(2, '神物', '坊市查看 神物', False)],                     
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await buy.finish()                
            if len(args) == 1:
                page = 0
                exchangenum,exchange_list = sql_message.get_exchange_list_goods_type(goods_type,page)
                page_num = math.floor(exchangenum / 30) + 1
                if page > 0:
                    upbutton = f'坊市查看{goods_type} {page}'
                if page_num > page + 1:
                    downbutton = f'坊市查看{goods_type} {page+2}' 
            else:
                if args[1].isdigit():
                    page = int(args[1]) - 1
                    exchangenum,exchange_list = sql_message.get_exchange_list_goods_type(goods_type,page)
                    page_num = math.floor(exchangenum / 30) + 1
                    if page > 0:
                        upbutton = f'坊市查看{goods_type} {page}'
                    if page_num > page + 1:
                        downbutton = f'坊市查看{goods_type} {page+2}'  
                else:
                    goods_name = args[1]  
                    page = 0
                    if len(args) == 2:
                        exchangenum,exchange_list = sql_message.get_exchange_list_goods_name(goods_type,goods_name,page)
                        page_num = math.floor(exchangenum / 30) + 1
                        if page > 0:
                            upbutton = f'坊市查看{goods_type} {goods_name} {page}'
                        if page_num > page + 1:
                            downbutton = f'坊市查看{goods_type} {goods_name} {page+2}'
                    if len(args) == 3:
                        page = int(args[2]) - 1
                        exchangenum,exchange_list = sql_message.get_exchange_list_goods_name(goods_type,goods_name,page)
                        page_num = math.floor(exchangenum / 30) + 1
                        if page > 0:
                            upbutton = f'坊市查看{goods_type} {goods_name} {page}'
                        if page_num > page + 1:
                            downbutton = f'坊市查看{goods_type} {goods_name} {page+2}'    
    else:
        page = 0
        exchangenum,exchange_list = sql_message.get_exchange_list(page)
        page_num = math.floor(exchangenum / 30) + 1
        if page > 0:
            upbutton = f'坊市查看{page}'
        if page_num > page + 1:
            downbutton = f'坊市查看{page+2}'                            

    if exchangenum == 0:
        msg = "坊市目前空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市查看', '坊市查看', True)],            
            [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop.finish()

    msg = f"#不鼓励不保障任何线下交易行为，如有风险，灵梦不承担任何责任哦！\n当前坊市中的商品：\n商品编号  类型  名称  单价  数量\n"
    for exchangeinfo in exchange_list:
        msg += f'\n><qqbot-cmd-input text=\"坊市商品信息{exchangeinfo[0]}\" show=\"{exchangeinfo[0]}\" reference=\"false\" /> {exchangeinfo[1]} <qqbot-cmd-input text=\"查看修仙物品{exchangeinfo[2]}\" show=\"{exchangeinfo[2]}\" reference=\"false\" /> {number_to(exchangeinfo[5])} {exchangeinfo[4]}'
    if page_num > 1:
        msg += f'\n第({page + 1}/{page_num})页  <qqbot-cmd-input text=\"坊市查看 \" show=\"跳转\" reference=\"false\" />'

    params_items = [('msg', msg)]
    
    # 初始化按钮列表
    button_list = [
        [(2, '💰坊市上架', '坊市上架', False), (2, '💰坊市下架', '坊市下架', False)],            
        [(2, '💰坊市购买', '坊市购买', False), (2, '💰我的坊市', '我的坊市', True)],
        [(2, '💰坊市筛选', '坊市查看', False)], 
    ]

    if upbutton != '':
        button_list.append([(2, '⬅️上一页', upbutton, True)])
  #  if page_num > 1:
  #      buttons.append([(2, f'⏺️跳转({page}/{page_num})', f'宗门成员查看', False)])        
    if downbutton != '':
        button_list.append([(2, '➡️下一页', downbutton, True)])
    data = await markdown(params_items, button_list)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await shop.finish()



@myshop.handle(parameterless=[Cooldown(at_sender=False)])
async def myshop_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看我的坊市"""
    # 分配 bot 和群组 ID
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]
        buttons = [
            [(2, '我要修仙', '我要修仙', True)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await myshop.finish()

    msg_text = args.extract_plain_text().strip()
    args = msg_text.split()
    upbutton = ''
    downbutton = '' 
    user_id = user_info['user_id']
    if len(args) > 0:
        page = int(args[0]) - 1
        exchangenum,exchange_list = sql_message.get_exchange_list_my(user_id,page)
        page_num = math.floor(exchangenum / 30) + 1
        if page > 0:
            upbutton = f'我的坊市{page}'
        if page_num > page + 1:
            downbutton = f'我的坊市{page+2}'
    else:
        page = 0
        exchangenum,exchange_list = sql_message.get_exchange_list_my(user_id,page)
        page_num = math.floor(exchangenum / 30) + 1
        if page > 0:
            upbutton = f'我的坊市{page}'
        if page_num > page + 1:
            downbutton = f'我的坊市{page+2}'
    if exchangenum == 0:
        msg = f"你在坊市中没有上架任何物品！"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '坊市上架', '坊市上架', False)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await myshop.finish()


    msg = f"#你在坊市中的商品：\n商品编号  类型  名称  单价  数量\n\n>"
    for exchangeinfo in exchange_list:
        msg += (f"<qqbot-cmd-input text=\"坊市购买{exchangeinfo[0]}\" show=\"{exchangeinfo[0]}\" reference=\"false\" /> {exchangeinfo[2]} "
                f"<qqbot-cmd-input text=\"查看修仙物品{exchangeinfo[1]}\" show=\"{exchangeinfo[1]}\" reference=\"false\" /> "
                f"{number_to(exchangeinfo[3])} {exchangeinfo[4]} <qqbot-cmd-input text=\"坊市下架{exchangeinfo[0]}\" show=\"下架\" reference=\"false\" />\n")

    if page_num > 1:
        msg += f'\n第({page + 1}/{page_num})页   <qqbot-cmd-input text=\"我的坊市 \" show=\"跳转\" reference=\"false\" />'

    params_items = [('msg', msg)]
    
    # 初始化按钮列表
    button_list = [
        [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],
        [(2, '坊市购买', '坊市购买', False), (2, '我的坊市', '我的坊市', True)],
        [(2, '坊市帮助', '坊市帮助', True), (2, '坊市查看', '坊市查看', True)],
    ]

    if upbutton != '':
        button_list.append([(2, '⬅️上一页', upbutton, True)])
  #  if page_num > 1:
  #      buttons.append([(2, f'⏺️跳转({page}/{page_num})', f'宗门成员查看', False)])        
    if downbutton != '':
        button_list.append([(2, '➡️下一页', downbutton, True)])
    data = await markdown(params_items, button_list)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await myshop.finish()


@shop_added_by_admin.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_added_by_admin_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """系统上架坊市"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    args = args.extract_plain_text().split()
    if not args:
        msg = "请输入正确指令！例如：系统坊市上架 物品 金额"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()
    goods_name = args[0]
    goods_id = -1
    for k, v in items.items.items():
        if goods_name == v['name']:
            goods_id = k
            break
        else:
            continue
    if goods_id == -1:
        msg = "不存在物品：{goods_name}的信息，请检查名字是否输入正确！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()
    price = None
    try:
        price = args[1]
    except LookupError:
        msg = "请输入正确指令！例如：系统坊市上架 物品 金额"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()
    try:
        price = int(price)
        if price < 0:
            msg = "请不要设置负数！"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await shop_added_by_admin.finish()
        if price > 2147483647:
            msg = "坊市上架商品的价格不得超过2147483647！"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await shop_added_by_admin.finish()            
    except LookupError:
        msg = "请输入正确的金额！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()

    try:
        var = args[2]
        msg = "请输入正确指令！例如：系统坊市上架 物品 金额"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_added_by_admin.finish()
    except LookupError:
        pass

    group_id = "worldexchange"
    shop_data = get_shop_data()
    if shop_data == {}:
        shop_data = {}
    goods_info = items.get_data_by_item_id(goods_id)

    id_ = len(shop_data) + 1
    shop_data[group_id][id_] = {}
    shop_data[group_id][id_]['user_id'] = 0
    shop_data[group_id][id_]['goods_name'] = goods_name
    shop_data[group_id][id_]['goods_id'] = goods_id
    shop_data[group_id][id_]['goods_type'] = goods_info['type']
    shop_data[group_id][id_]['desc'] = get_item_msg(goods_id)
    shop_data[group_id][id_]['price'] = price
    shop_data[group_id][id_]['user_name'] = '系统'
    save_shop(shop_data)
    msg = f"物品：{goods_name}成功上架坊市，金额：{price}枚灵石！"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '坊市上架', '坊市上架 ', False), (2, '坊市下架', '坊市下架 ', False)],            
        [(2, '坊市购买', '坊市购买 ', False), (2, '坊市帮助', '坊市帮助 ', True)],
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await shop_added_by_admin.finish()


@shop_added.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def shop_added_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """用户上架坊市"""
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
        await shop_added.finish()
    if user_info['stone'] < 0:
        msg = "道友还有负债，禁止进入坊市！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修仙签到', '修仙签到', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shop_added.finish()         
    user_id = user_info['user_id']
    exchangenum,exchange_list = sql_message.get_exchange_list_my(user_id)
    if exchangenum > 10:
        msg = f'每位道友上架坊市的物品数量不得超过10件。'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的坊市', '我的坊市', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shop_added.finish() 
    args = args.extract_plain_text().split()
    goods_name = args[0] if len(args) > 0 else None
    fb_props = ['寒铁铸心炉', '雕花紫铜炉', '寒铁铸心炉',]  # 添加更多道具名称以禁止上架
    if goods_name in fb_props:
        msg = f'道具{goods_name}无法上架坊市。'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shop_added.finish()      
    price_str = args[1] if len(args) > 1 else "500000"  # 默认为500000
    quantity_str = args[2] if len(args) > 2 else "1"  # 默认为1
    if len(args) < 2:
        # 没有输入任何参数
        msg = "请输入正确指令！例如：坊市上架 物品 金额 可选参数为(数量,默认1)"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],            
            [(2, '坊市购买', '坊市购买', False), (2, '坊市查看', '坊市查看', True)],
            [(2, '坊市帮助', '坊市帮助', True), (2, '我的坊市', '我的坊市', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shop_added.finish()
    elif len(args) == 2:
        goods_name, price_str = args[0], args[1]
        quantity_str = "1"
    else:
        # 提供了物品名称、价格和数量
        goods_name, price_str, quantity_str = args[0], args[1], args[2]

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,dict
    if back_msg is None:
        msg = "道友的背包空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False)],                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop_added.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    goods_bind_num = None
    for back in back_msg:
        if goods_name == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_state = back['state']
            goods_num = back['goods_num']
            goods_bind_num = back['bind_num']
            break
    if not in_flag:
        msg = f"请检查该道具 {goods_name} 是否在背包内！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True)],                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop_added.finish()
    price = None
    
    # 解析价格
    try:
        price = int(price_str)
        if price <= 0:
            raise ValueError("坊市上架商品的价格必须为正数！道友不得胡闹！")
        if price > 1145141919810:
            raise ValueError("坊市上架商品的价格不能超过 1145141919810！")            
    except ValueError as e:
        msg = f"请输入正确的金额: {str(e)}"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False)],                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop_added.finish()
    # 解析数量
    try:
        quantity = int(quantity_str)
        if quantity <= 0 or quantity > goods_num:  # 检查指定的数量是否合法
            raise ValueError("数量必须为正数或者小于等于你拥有的物品数!")
    except ValueError as e:
        msg = f"请输入正确的数量: {str(e)}"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False)],                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop_added.finish()
    price = max(price, 500000)  # 最低价格为50w
    if goods_type == "装备" and int(goods_state) == 1 and goods_num - quantity < 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法上架！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '卸载装备', f'换装{goods_name}', True)],                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop_added.finish() 
        
    if int(goods_num) <= int(goods_bind_num):
        msg = "该物品是绑定物品，无法上架！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False)],                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop_added.finish()        
        
    if goods_type == "聚灵旗" or goods_type == "炼丹炉":
        if user_info['root'] == "器师" :
            pass
        else:
            msg = "道友职业无法上架！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '重入仙途', '重入仙途', False)],                       
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await shop_added.finish() 

    string = "0123456789"
    random_list = random.sample(list(string), 9)
    exchangeid = ''.join(random_list)        

    user_name = user_info['user_name'] 
    stock = quantity
    sql_message.update_back_j(user_id, goods_id, num = quantity)
    now_time = math.ceil(time.time())
    sql_message.new_exchange(exchangeid, user_id, goods_name, goods_id, goods_type, price, user_name, stock, now_time)
    msg = f"物品：{goods_name}成功上架坊市，金额：{number_to(price)}枚灵石，数量{quantity}！"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', f'坊市下架 {exchangeid}', False)],            
        [(2, '坊市购买', f'坊市购买 {exchangeid}', False), (2, '坊市查看', '坊市查看', True)],
        [(2, '坊市帮助', '坊市帮助', True), (2, '我的坊市', '我的坊市', True)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await shop_added.finish()

@send_goods.handle(parameterless=[Cooldown(at_sender=False)])
async def send_goods_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """赠送物品"""
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
        await send_goods.finish()
    if user_info['stone'] < 0:
        msg = "道友还有负债，还想送别人物品？"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修仙签到', '修仙签到', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()         
    user_id = user_info['user_id']
    args = args.extract_plain_text().split()
    if not args or len(args) < 3:
        msg = "请输入要赠送的物品，数量和道友。例如：赠送修仙道具 物品 数量 道友"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish() 
    goods_name = args[0]
    fb_props = ['寒铁铸心炉', '雕花紫铜炉', '寒铁铸心炉', '圣诞礼物（2024）']  # 添加更多道具名称以禁止上架
    if goods_name in fb_props:
        msg = f'道具{goods_name}无法赠送。'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()         
    try:
        give_name = args[2]
        num = int(args[1])
    except ValueError:
        msg = f'请输入要赠送的物品，数量和道友。例如：赠送修仙道具 物品 数量 道友'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    give_info = sql_message.get_user_info_with_name(give_name)
    if give_info is None:
        msg = "仙界物品不得给予凡人。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()   
    give_id = give_info['user_id']        
    if back_msg is None:
        msg = "道友的背包空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    goods_bind_num = None    
    for back in back_msg:
        if goods_name == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_state = back['state']
            goods_num = back['goods_num']
            goods_bind_num = back['bind_num']
            break
    if not in_flag:
        msg = f"请检查该道具 {goods_name} 是否在背包内！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()

    if int(goods_num) <= int(goods_bind_num):
        msg = "该物品是绑定物品，无法赠送！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],                       
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_goods.finish()
    if get_item_msg_rank(goods_id) == 520:
        msg = "此类物品不支持！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()

    # 检查输入的数量是否在允许范围内
    if 1 <= int(args[1]) <= int(goods_num):
        price = int(9000000 - get_item_msg_rank(goods_id) * 100000) / 4 * num

        # 检查价格是否为正值
        if price <= 0:
            msg = f"赠送失败。数量必须在 1 到 {goods_num} 之间，请重新输入。"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '赠送修仙道具', '赠送修仙道具', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await send_goods.finish()

    else:
        # 如果输入的数量无效，则给出提示
        msg = f"赠送失败，道友背包内没有这么多{goods_name}。数量必须在 1 到 {goods_num} 之间，请重新输入。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()
    if goods_type == "装备" and int(goods_state) == 1 and goods_num - num < 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法赠送，请减少数量"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '卸载装备', f'换装{goods_name}', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()
    if price > user_info["stone"]:
        msg = f"道友的灵石只有{user_info['stone']},不足以支付手续费，无法赠送。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await send_goods.finish()
    sql_message.update_back_j(user_id, goods_id, num=num)
    sql_message.update_ls(user_id, price, 2)
    sql_message.send_back(give_id, back['goods_id'], goods_name, back['goods_type'], num, 0)
    msg = f"道友消耗{price:,}枚灵石，把物品：{goods_name} 数量：{num} 赠送给了{give_name}！"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '赠送修仙道具', '赠送修仙道具', False)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await send_goods.finish()

@send_yaocai_all.handle(parameterless=[Cooldown(at_sender=False)])
async def send_yaocai_all_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """一键赠送药材"""
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
        await send_yaocai_all.finish()
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    current_hour = now.hour
    if not (1 <= current_hour < 8):
        msg = "请在丑时到卯时之间一键赠送。"
        params_items = [('msg', msg)]
        buttons = []
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_yaocai_all.finish()        
    if user_info['stone'] < 0:
        msg = "道友还有负债，还想送别人物品？"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '修仙签到', '修仙签到', True)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_yaocai_all.finish()
    user_id = user_info['user_id']
    args = args.extract_plain_text().split()
    if not args or len(args) < 1:
        msg = "请输入要赠送道友。例如：一键赠送药材 道友"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '一键赠送药材', '一键赠送药材', False)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_yaocai_all.finish()
    give_name = args[0]

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    give_info = sql_message.get_user_info_with_name(give_name)
    if give_info is None:
        msg = "仙界物品不得给予凡人。"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '一键赠送药材', '一键赠送药材', False)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_yaocai_all.finish()
    give_id = give_info['user_id']
    if int(give_id) == int(user_id):
        msg = "笨蛋，不可赠送给自己！"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '一键赠送药材', '一键赠送药材', False)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_yaocai_all.finish()
    if back_msg is None:
        msg = "道友的背包空空如也！"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '我的背包', '我的背包', True)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_yaocai_all.finish()
    yaocai_list = sql_message.get_all_yaocai_by_user(user_id)
    # print(yaocai_list)
    total_price = 0
    valid_yaocai = []  # 存储有效的药材信息，用于后续更新数据库

    for yaocai_info in yaocai_list:
        goods_name = yaocai_info['goods_name']
        goods_id = yaocai_info['goods_id']
        goods_type = yaocai_info['goods_type']
        goods_state = yaocai_info['state']
        goods_num = yaocai_info['goods_num']
        if goods_num <= 0:
         #   print(f"无效的数量: {goods_num} 对于 {goods_name}")
            continue
        goods_bind_num = yaocai_info['bind_num']
        if goods_bind_num > 0:
          #  print(f"绑定物品: {goods_num} 对于 {goods_name}")
            continue
        price = int(9000000 - get_item_msg_rank(goods_id) * 100000) / 4 * goods_num
        if price <= 0:
            msg = f"赠送失败。手续费必须为正。"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '赠送修仙道具', '赠送修仙道具', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await send_goods.finish()        
        valid_yaocai.append(yaocai_info)
        total_price += price
    if total_price > user_info["stone"]:
        msg = f"道友的灵石只有{user_info['stone']},不足以支付手续，无法一键赠送。请单独赠送"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '赠送修仙道具', '赠送修仙道具', False)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await send_yaocai_all.finish()

    # 灵石足够，更新数据库
    sql_message.update_ls(user_id, total_price, 2)
    for yaocai_info in valid_yaocai:
        goods_id = yaocai_info['goods_id']
        goods_num = yaocai_info['goods_num']
        goods_name = yaocai_info['goods_name']
        goods_type = yaocai_info['goods_type']
        sql_message.update_back_j(user_id, goods_id, num=goods_num)
        sql_message.send_back(give_id, goods_id, goods_name, goods_type, goods_num, 0)

    msg = f"道友消耗{total_price:,}枚灵石，把药材一键赠送给了{give_name}！"
    params_items = [('msg', msg)]
    buttons = [
        [(2, '一键赠送药材', '一键赠送药材', False)],
    ]
    # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await send_yaocai_all.finish()
    
@get_double_yaocai.handle(parameterless=[Cooldown(at_sender=False)])
async def get_double_yaocai_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    double_list = sql_message.get_duplicate_records()
    print(double_list)

@goods_allre_root.handle(parameterless=[Cooldown(at_sender=False)])
async def goods_allre_root_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """一键炼金"""
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
        await goods_allre_root.finish()

    user_id = user_info['user_id']
    args = args.extract_plain_text().replace("+", " ").split()

    # 如果没有输入命令，提示用户输入
    if not args:
        msg = "一键炼金会炼化道友背包中所有仙极以下的装备或技能，还请三思！\n如确实需要，请选择需要一键炼化的物品类别（装备/技能）！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '装备', '一键炼金装备', False), (2, '技能', '一键炼金技能', False)],             
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_allre_root.finish()
    mode = args[0]  # 获取用户输入的命令
    if mode == "技能":
        goods_type_to_process = "技能"  # 只处理技能物品
    elif mode == "装备":
        goods_type_to_process = "装备"  # 只处理装备物品
    else:
        # 如果命令不匹配，返回提示信息
        msg = "道友请输入正确的命令！\n一键炼金装备 或 一键炼金技能"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '装备', '一键炼金装备', False), (2, '技能', '一键炼金技能', False)],             
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_allre_root.finish()

    # 获取背包中的物品
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息, list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True)],            
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_allre_root.finish()

    # 获取所有符合条件的物品
    valid_goods = []
    for back in back_msg:
        goods_name = back['goods_name']
        goods_type = back['goods_type']
        goods_id = back['goods_id']
        goods_state = back['state']
        goods_num = back['goods_num']
        
        item_info = items.get_data_by_item_id(goods_id)
        if goods_type == goods_type_to_process:

            if goods_type == "装备":
                if item_info['level'] in ["无上仙器", "极品仙器", "世界之源", "音之精灵", "万魔之始", "夏之花·无尽爱", "救援之力", "神州往事", "生息之源", "轻盈之杏","新春限定","心动缔结","传递之薪","空想之灵","满天星·无尽夏"]:
                    continue  # 排除这些装备
            elif goods_type == "技能":
                if item_info['level'] in ["仙阶极品", "无上仙法", "无上神通"]:
                    continue  # 排除这些技能
            valid_goods.append(back)

    if not valid_goods:
        msg = f"道友的背包中没有可炼化的{goods_type_to_process}物品！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True)],            
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_allre_root.finish()

    # 进行一键炼金操作
    total_price = 0
    for item in valid_goods:
        #print(f'item:{item}')
        goods_id = item['goods_id']
        goods_name = item['goods_name']
        if item['state'] == 1:
            goods_num = item['goods_num'] - 1
        else:
            goods_num = item['goods_num']
        
        #price = int(9000000 - get_item_msg_rank(goods_id) * 100000) * goods_num
        price = int((convert_rank('江湖好手')[0] + 5) * 100000 - get_item_msg_rank(goods_id) * 100000) * goods_num
        if price <= 0:
            continue  # 价格为零的物品跳过
        
        total_price += price
        
        # 更新背包和灵石数据
        sql_message.update_back_j(user_id, goods_id, num=goods_num)
        sql_message.update_ls(user_id, price, 1)

    if total_price > 0:
        msg = f"道友一键炼金成功，累计获得 {total_price:,} 枚灵石！"
    else:
        msg = "没有可用的物品进行炼金！"
    
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '装备', '一键炼金装备', False), (2, '技能', '一键炼金技能', False)],             
    ]
    # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await goods_allre_root.finish()

@goods_re_root.handle(parameterless=[Cooldown(at_sender=False)])
async def goods_re_root_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """炼金"""
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
        await goods_re_root.finish()
    user_id = user_info['user_id']
    args = args.extract_plain_text().replace("+", " ").split()
    if not args:
        msg = "道友想要炼化什么？请输入要炼化的物品！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '炼金', '炼金', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_re_root.finish()
    goods_name = args[0]
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_re_root.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    for back in back_msg:
        if goods_name == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_state = back['state']
            goods_num = back['goods_num']
            break
    if not in_flag:
        msg = f"请检查该道具 {goods_name} 是否在背包内！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_re_root.finish()

    if goods_type == "装备" and int(goods_state) == 1 and int(goods_num) == 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法炼金！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '卸载装备', f'换装{goods_name}', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_re_root.finish()

    if get_item_msg_rank(goods_id) == 520:
        msg = "此类物品不支持！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '炼金', '炼金', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_re_root.finish()
    num = 1
    if len(args) > 1:
        try:
            input_num = int(args[1])
            if 1 <= input_num <= int(goods_num):
                num = input_num
            else:
                msg = f"道友炼化的数量不正确，数量应介于 1 和 {goods_num} 之间。"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '重新输入数量', '重新输入数量', False)],            
                ]
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await goods_re_root.finish()
        except ValueError:
            msg = "请输入一个有效的数字作为数量。"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '重新输入数量', '重新输入数量', False)],            
            ]
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await goods_re_root.finish()
    price = int((convert_rank('江湖好手')[0] + 5) * 100000 - get_item_msg_rank(goods_id) * 100000) * num
    if price <= 0:
        msg = f"物品：{goods_name}炼金失败，凝聚{price:,}枚灵石！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '炼金', '炼金', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await goods_re_root.finish()

    sql_message.update_back_j(user_id, goods_id, num=num)
    sql_message.update_ls(user_id, price, 1)
    msg = f"物品：{goods_name} 数量：{num} 炼金成功，凝聚{price:,}枚灵石！"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '炼金', '炼金', False)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await goods_re_root.finish()


@shop_off.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_off_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """下架商品"""
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
        await shop_off.finish()
    input_args = args.extract_plain_text().replace("+", " ").split()    
    user_id = user_info['user_id']
   # print(user_id)
    if len(input_args) != 1:
        msg = f'请输入 <qqbot-cmd-input text=\"坊市下架\" show=\"坊市下架\" reference=\"false\" />[物品交易编号]'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市下架', '坊市下架 ', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shop_off.finish() 
    exchangeid = input_args[0].strip()         
    exchange_info = sql_message.get_exchange_info(exchangeid)
   # print(exchange_info)
    if exchange_info == 0:
        msg = "请输入正确指令或者物品已售出！例如：坊市下架 物品编号"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市下架', '坊市下架', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shop_off.finish()
        
    if int(exchange_info[5]) != user_id:
        msg = "此物并非道友所有，不得贪恋！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市下架', '坊市下架', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await shop_off.finish()    
    
    shop_goods_id = exchange_info[2]
    shop_goods_name = exchange_info[0]
    shop_goods_type = exchange_info[1]
    buy_num = exchange_info[3]
    seller_id = exchange_info[5]
    sql_message.send_back(seller_id, shop_goods_id, shop_goods_name, shop_goods_type, buy_num)
    msg = f"成功下架物品：{shop_goods_name}！"
    sql_message.delete_exchange(exchangeid)
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],        
        [(2, '坊市查看', '坊市查看', True)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await shop_off.finish()

    if event.sender.role == "admin" or event.sender.role == "owner" or event.get_user_id() in bot.config.superusers:
        if seller_id == 0:  # 这么写为了防止bot.send发送失败，不结算
            msg = f"成功下架物品：{shop_goods_name}！"
            sql_message.delete_exchange(exchangeid)
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await shop_off.finish()
        else:
            sql_message.send_back(seller_id, shop_goods_id, shop_goods_name, shop_goods_type, buy_num)
            msg1 = f"道友上架的{buy_num}个{shop_goods_name}已被管理员{user_info['user_name']}下架！"
            sql_message.delete_exchange(exchangeid)
            try:
                if XiuConfig().img:
                    pic = await get_msg_pic(f"@{shop_user_name}\n" + msg1)
                    await bot.send(event=event, message=MessageSegment.image(pic))
                else:
                    await bot.send(event=event, message=Message(msg1))
            except ActionFailed:
                pass

    else:
        msg = "此物并非道友所有，不得贪恋！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '坊市上架', '坊市上架', False), (2, '坊市下架', '坊市下架', False)],        
            [(2, '坊市查看', '坊市查看', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await shop_off.finish()


@auction_withdraw.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def auction_withdraw_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """用户撤回拍卖品"""
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
        await auction_withdraw.finish()


    config = get_auction_config()
    user_auctions = config.get('user_auctions', [])

    if not user_auctions:
        msg = f"拍卖会目前没有道友提交的物品！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_withdraw.finish()

    arg = args.extract_plain_text().strip()
    auction_index = int(arg) - 1
    if auction_index < 0 or auction_index >= len(user_auctions):
        msg = f"请输入正确的编号"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_withdraw.finish()

    auction = user_auctions[auction_index]
    goods_name, details = list(auction.items())[0]
    if details['user_id'] != user_info['user_id']:
        msg = f"这不是你的拍卖品！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_withdraw.finish()

    sql_message.send_back(details['user_id'], details['id'], goods_name, details['goods_type'], details['quantity'])
    user_auctions.pop(auction_index)
    config['user_auctions'] = user_auctions
    savef_auction(config)

    msg = f"成功撤回拍卖品：{goods_name}x{details['quantity']}！"
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    await auction_withdraw.finish()


@main_back.handle(parameterless=[Cooldown(cd_time=1, at_sender=False)])
async def main_back_(bot: Bot, event: GroupMessageEvent):
    """我的背包分页查看"""
    
    # 分配 bot 和群组 ID
    bot, send_group_id = await assign_bot(bot=bot, event=event)

    # 检查用户状态
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await main_back.finish()
    
    user_id = user_info['user_id']
    msg = get_user_main_back_msg(user_id)  # 获取用户背包物品信息
    total_items = len(msg)  # 背包物品总数
    items_per_page = 30  # 每页显示的物品数
    page_num = math.ceil(total_items / items_per_page)  # 总页数

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
        page = 0  # 默认显示第一页

    # 页码范围限制
    if page < 0:
        page = 0
    if page > 0:
        upbutton = f'我的背包 {page}'  # 上一页按钮
    if page_num > page + 1:
        downbutton = f'我的背包 {page + 2}'  # 下一页按钮

    # 分页显示的商品
    start_index = page * items_per_page
    end_index = min(start_index + items_per_page, total_items)    

    # 构建显示背包物品的消息
    msg = [f"道友***{user_info['user_name']}***的背包，持有灵石：{(user_info['stone']):,}枚 \n物品名称   物品品阶    物品数量"] + msg[start_index:end_index]
    if page_num > 1:
        msg.append(f'\n第({page + 1}/{page_num})页  <qqbot-cmd-input text=\"我的背包\" show=\"跳转\" />')       

    # 初始化按钮列表
    buttons = [
        [(2, '使用物品', '使用', False), (2, '换装装备', '换装', False)],
        [(2, '药材背包', '药材背包', True), (2, '丹药背包', '丹药背包', True)],
        [(2, '我的功法', '我的功法', True), (2, '坊市上架', '坊市上架', False)],  
        [(2, '一键炼金', '一键炼金', False), (2, '赠送', '赠送修仙道具', False)],        
    ]

    # 添加上一页和下一页按钮
    if upbutton != '':
        buttons.append([(2, '⬅️上一页', upbutton, True)])
    if downbutton != '':
        buttons.append([(2, '➡️下一页', downbutton, True)])

    # 构建 markdown 消息并发送
    try:
        params_items = [('msg', "\n".join(msg))]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    except ActionFailed:
        await main_back.finish("查看背包失败!", reply_message=True)

    await main_back.finish()


@view_item.handle(parameterless=[Cooldown(at_sender=False)])
async def view_item_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看物品效果"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    args = args.extract_plain_text().split()
  
   # goods_id = get_item_id_by_name(goods_name)
    if not args:
        msg = f"请输入要查看的物品id。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查看物品效果', '查看物品效果', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await view_item.finish()
    goods_id = args[0]         
    try:
        msg = get_item_msg(goods_id)
    except KeyError:
        # 如果物品 ID 不存在，捕获 KeyError 并提示用户
        msg = f"修仙界未找到此物品。还望道友仔细确认输入物品id。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查看物品效果', '查看物品效果', False)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await view_item.finish()        
    # 获取物品详细信息
    msg = get_item_msg(goods_id)
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '查看物品效果', '查看物品效果', False)],
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await view_item.finish() 

@view_item_name.handle(parameterless=[Cooldown(at_sender=False)])
async def view_item_name_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看修仙物品"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    args = args.extract_plain_text().split() 
    if not args:
        msg = "请输入要查看的物品名称。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查看修仙物品', '查看修仙物品', False)],            
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await view_item_name.finish()    
    goods_name = args[0]
    goods_id = -1
    goods_type = None
    
    for k, v in items.items.items():
        if goods_name == v['name']:
            goods_id = k
            goods_type = v['type']
            break    
    try:
        msg = get_item_msg(goods_id)
    except KeyError:
        # 如果物品 ID 不存在，捕获 KeyError 并提示用户
        msg = f"修仙界未找到此物品。还望道友仔细确认输入物品名称。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '查看修仙物品', '查看修仙物品', False)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await view_item_name.finish()        
    # 获取物品详细信息
    msg = get_item_msg(goods_id)
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '使用此道具', f'使用{goods_name}', False)],
        [(2, '查看修仙物品', '查看修仙物品', False)],
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await view_item_name.finish() 

@view_auction_item.handle(parameterless=[Cooldown(at_sender=False)])
async def view_auction_item_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看拍卖品详情"""
    # 分配机器人和获取群组ID
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    
    # 检查用户信息
    isUser, user_info, msg = check_user(event)
    
    # 解析指令参数，获取 auctionid
    args = args.extract_plain_text().split()
    if not args or len(args) == 0:
        msg = f"道友想查看哪个拍卖品？请输入拍卖品详情 拍卖编号"
        params_items = [('msg', msg)]               
        buttons = [          
            [(2, '拍卖品详情', '拍卖品详情', False)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await view_auction_item.finish()    
    auctionid = args[0] 
    
    # 获取拍卖品和拍卖状态
    auction_items = sql_message.get_auction_info_by_auctionid(auctionid)
   # print(auction_items)
    goods_id = auction_items.get('auction_id')
    userid = auction_items['user_id']
    seller_id = auction_items.get('seller_id')    
    user_info = sql_message.get_user_info_with_id(userid)    
    price = auction_items.get('start_price')
    auction_status = sql_message.get_auction_status()  # 获取拍卖状态
    user_info = sql_message.get_user_info_with_id(userid)
    user_name = user_info.get('user_name') if user_info else "未知的道友" 
    if auction_status == 2:  # 拍卖结束
       # if user_name == "未知的道友":
        if userid == seller_id:
            msg = (
                f"编号 {auctionid} 的拍卖品流拍了。\n"
                f"{get_item_msg(goods_id)}"
            )        
        elif seller_id:  # 检查 seller_id 是否存在
            if seller_id != '0':  # 如果 user_id 不是 '0'
                seller_info = sql_message.get_user_info_with_id(seller_id)
                seller_name = seller_info['user_name']                
                msg = (
                    f"编号 {auctionid} 拍卖物品信息：\n"
                    f"最终价为 {price:,} 灵石\n恭喜***{user_info['user_name']}***道友成功拍卖获得***{seller_name}***道友的拍卖品：\n"
                    f"{get_item_msg(goods_id)}"
                )
            else:  # 如果 user_id 是 '0'
                msg = (
                    f"编号 {auctionid} 拍卖物品信息：\n"
                    f"最终价为 {price:,} 灵石\n恭喜{user_info['user_name']}道友成功拍卖获得：\n"
                    f"{get_item_msg(goods_id)}"
                )
    else:  # 拍卖进行中
        msg = (
            f"编号 {auctionid} 拍卖物品信息：\n"
            f"{get_item_msg(goods_id)}\n"
            f"当前价为 {price:,} 灵石"
        )
        
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '竞价此物', f'拍卖{auctionid}', False)],            
        [(2, '仙市集会', '仙市集会', True)],
    ]
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await view_auction_item.finish()


@no_use_zb.handle(parameterless=[Cooldown(at_sender=False)])
async def no_use_zb_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """卸载物品（只支持装备）
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
        await no_use_zb.finish()
    user_id = user_info['user_id']
    arg = args.extract_plain_text().strip()

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await no_use_zb.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    for back in back_msg:
        if arg == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            break
    if not in_flag:
        msg = f"请检查道具 {arg} 是否在背包内！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用道具', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await no_use_zb.finish()

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            sql_str, item_type = get_no_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, 0)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, 0)
            msg = f"成功卸载装备{arg}！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '使用装备', '使用', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await no_use_zb.finish()
        else:
            msg = "装备没有被使用，无法卸载！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '使用装备', '使用', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await no_use_zb.finish()
    else:
        msg = "目前只支持卸载装备！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '卸下装备', '换装', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await no_use_zb.finish()


@use.handle(parameterless=[Cooldown(at_sender=False)])
async def use_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """使用物品
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
        await use.finish()
    user_id = user_info['user_id']
    args = args.extract_plain_text().split()  
    if not args:
        msg = "道友想要使用什么？！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用道具', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()
    arg = args[0]
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,dict
    if back_msg is None:
        msg = "道友的背包空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用道具', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_num = None
    for back in back_msg:
        if arg == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_num = back['goods_num']
            break
    if not in_flag:
        msg = f"请检查该道具 {arg} 是否在背包内！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用道具', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            msg = "该装备已被装备，请勿重复装备！"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await use.finish()
        else:  # 可以装备
            sql_str, item_type = get_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, goods_id)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, goods_id)
            msg = f"成功装备{arg}！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '使用装备', '使用', False), (2, '卸下装备', '换装', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await use.finish()
    elif goods_type == "技能":
        user_buff_info = UserBuffDate(user_id).BuffInfo
        skill_info = items.get_data_by_item_id(goods_id)
        skill_type = skill_info['item_type']
        if skill_type == "神通":
            if int(user_buff_info['sec_buff']) == int(goods_id):
                msg = f"道友已学会该神通：{skill_info['name']}，请勿重复学习！"
            else:  # 学习sql
                sql_message.update_back_j(user_id, goods_id)
                sql_message.updata_user_sec_buff(user_id, goods_id)
                msg = f"恭喜道友学会神通：{skill_info['name']}！"
        elif skill_type == "功法":
            if int(user_buff_info['main_buff']) == int(goods_id):
                msg = f"道友已学会该功法：{skill_info['name']}，请勿重复学习！"
            else:  # 学习sql
                sql_message.update_back_j(user_id, goods_id)
                sql_message.updata_user_main_buff(user_id, goods_id)
                msg = f"恭喜道友学会功法：{skill_info['name']}！"
        elif skill_type == "辅修功法": #辅修功法1
            if int(user_buff_info['sub_buff']) == int(goods_id):
                msg = f"道友已学会该辅修功法：{skill_info['name']}，请勿重复学习！"
            else:#学习sql
                sql_message.update_back_j(user_id, goods_id)
                sql_message.updata_user_sub_buff(user_id, goods_id)
                msg = f"恭喜道友学会辅修功法：{skill_info['name']}！"
        else:
            msg = "发生未知错误！"

        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用道具', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()
    elif goods_type == "特殊物品":
        num = 1
        try:
            if len(args) > 1 and 1 <= int(args[1]) <= int(goods_num):
                num = int(args[1])
            elif len(args) > 1 and int(args[1]) > int(goods_num):
                msg = f"道友背包中的{arg}数量不足，当前仅有{goods_num}个！"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '使用道具', '使用', False)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await use.finish()
        except ValueError:
            num = 1
        if goods_id == 20000:
            sql_message.reset_mijing(user_id)
            sql_message.update_back_j(user_id, goods_id, num=num)
            msg = f"道友的秘境探索次数已刷新，请前往秘境探索吧！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '探索秘境', '探索秘境', False)],            
            ]
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await use.finish()
        if goods_id == 20001:
            sql_message.reset_work_num(user_id)
            sql_message.update_back_j(user_id, goods_id, num=num)
            msg = f"道友的悬赏令刷新次数已更新，请前往领取悬赏令吧！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '悬赏令', '悬赏令', False)],            
            ]
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await use.finish()
    elif goods_type == "丹药":
        num = 1
        try:
            if len(args) > 1 and 1 <= int(args[1]) <= int(goods_num):
                num = int(args[1])
            elif len(args) > 1 and int(args[1]) > int(goods_num):
                msg = f"道友背包中的{arg}数量不足，当前仅有{goods_num}个！"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '使用道具', '使用', False)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await use.finish()
        except ValueError:
            num = 1
        msg = check_use_elixir(user_id, goods_id, num)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用丹药', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()
    elif goods_type =="神物":
        num = 1
        try:
            if len(args) > 1 and 1 <= int(args[1]) <= int(goods_num):
                num = int(args[1])
            elif len(args) > 1 and int(args[1]) > int(goods_num):
                msg = f"道友背包中的{arg}数量不足，当前仅有{goods_num}个！"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '使用神物', '使用', False)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        except ValueError:
            num = 1
        goods_info = items.get_data_by_item_id(goods_id)
        user_info = sql_message.get_user_info_with_id(user_id)
        user_rank = convert_rank(user_info['level'])[0]
        goods_rank = goods_info['rank']
        goods_name = goods_info['name']
        if goods_rank < user_rank:  # 使用限制
                msg = f"神物：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
                params_items = [('msg', msg)]      
                buttons =[]  
                # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await use.finish()
        else:
                if isinstance(goods_info['buff'], list):
                    # 在buff范围内随机选择一个值
                    exp = random.randint(goods_info['buff'][0], goods_info['buff'][1]) * num
                else:
                    # 直接使用buff的值
                    exp = goods_info['buff'] * num
                user_hp = int(user_info['hp'] + (exp / 2))
                user_mp = int(user_info['mp'] + exp)
                user_atk = int(user_info['atk'] + (exp / 10))
                sql_message.update_exp(user_id, exp)
                sql_message.update_power2(user_id)  # 更新战力
                sql_message.update_user_attribute(user_id, user_hp, user_mp, user_atk)  # 这种事情要放在update_exp方法里
                sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
                msg = f"道友成功使用神物：{goods_name} {num}个 ,修为增加{exp}点！"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '使用神物', '使用', False)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await use.finish()
        
    elif goods_type =="礼包":
        num = 1
        try:
            if len(args) > 1 and 1 <= int(args[1]) <= int(goods_num):
                num = int(args[1])
            elif len(args) > 1 and int(args[1]) > int(goods_num):
                msg = f"道友背包中的{arg}数量不足，当前仅有{goods_num}个！"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '使用礼包', '使用', False),(2, '查看修仙物品', '查看物品', False)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await use.finish()
        except ValueError:
            num = 1
        goods_info = items.get_data_by_item_id(goods_id)
        user_info = sql_message.get_user_info_with_id(user_id)
      #  user_rank = convert_rank(user_info['level'])[0]
        goods_name = goods_info['name']
        msg_parts = []
        for i in range(1, 7):
            buff_key = f'buff_{i}'
            name_key = f'name_{i}'
            type_key = f'type_{i}'
            amount_key = f'amount_{i}'
            if name_key in goods_info:
                goods_name = goods_info[name_key]
                goods_amount = goods_info.get(amount_key, 1) * num
                if goods_name == "灵石":
                    key = 1 if goods_amount > 0 else 2
                    sql_message.update_ls(user_id, abs(goods_amount), key)
                    if goods_amount > 0:
                        msg_parts.append(f"获得灵石{goods_amount}枚")
                    else:
                        msg_parts.append(f"灵石被收走了{abs(goods_amount)}枚呢，好可惜！")
                else:
                    buff_id = goods_info.get(buff_key)
                    goods_type = goods_info.get(type_key, "未知类型")
                    if buff_id is not None:
                        sql_message.send_back(user_id, buff_id, goods_name, goods_type, goods_amount, 0)
                    msg_parts.append(f'<qqbot-cmd-input text=\"查看修仙物品{goods_name}\" show=\"{goods_name}\" />{goods_amount}个') 
        sql_message.update_back_j(user_id, goods_id, num, 0)
        msg = f"道友打开了{num}个{goods_info['name']},里面居然是" + "、".join(msg_parts)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用礼包', '使用', False),(2, '查看物品', '查看修仙物品', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()
        
    elif goods_type == "聚灵旗":
        msg = get_use_jlq_msg(user_id, goods_id)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用聚灵旗', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()
    else:
        msg = '该类型物品调试中，未开启！'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用道具', '使用', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await use.finish()

@auction_view.handle(parameterless=[Cooldown(at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def auction_view_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """仙市集会"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    group_id = str(event.group_id)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await auction_view.finish()
    

    config = get_auction_config()
   # user_auctions = config.get('user_auctions', [])
    user_auctions = sql_message.get_all_auction_data()  
    auction_status_msg = ""
  #  if not user_auctions:
  #      msg = "拍卖会目前没有道友提交的物品！"
  #      if XiuConfig().img:
 #           pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
 #           await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
 #       else:
 #           await bot.send_group_msg(group_id=int(send_group_id), message=msg)
  #      await auction_view.finish()
    auction_status = user_auctions[0]["status"]
    if auction_status == 1:
        auction_status_msg = "进行中"
    else:
        auction_status_msg = "已结束"
    auction_list_msg = f"仙市集会每天下午15点开启，21点59结束。请道友们留意时间。负债会有功能限制，请谨慎竞拍。\n本次仙市集会: **{auction_status_msg}**\n编号  名称  物品类型  拍卖单价  数量\n"

    for idx, auction in enumerate(user_auctions):
        auction_id = auction.get('auction_id', 0)
        item_quantity = auction.get('item_quantity')        
        item_info = items.get_data_by_item_id(auction_id)
        goods_name = item_info['name'] 
        goods_type = item_info.get('item_type', '未知类型')        
        start_price = auction.get('start_price', 0)
        aid = auction.get('auctionid', 0)
        auction_list_msg += f'\n><qqbot-cmd-input text=\"拍卖 {aid}\" show=\"{aid}\" reference=\"false\" />  <qqbot-cmd-input text=\"拍卖品详情{aid}\" show=\"{goods_name}\" reference=\"false\" />  {goods_type}  {start_price:,}枚灵石  {item_quantity}'

    # 生成 markdown 数据
    params_items = [('msg', auction_list_msg)]  # 确保拍卖信息包含在消息中
    buttons = [
        [(2, '出价竞拍', '拍卖', False), (2, '提交拍卖品', '提交拍卖品', False)], 
        [(2, '拍卖品详情', '拍卖品详情', False)],          
    ]
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
    await auction_view.finish()


@creat_auction.handle(parameterless=[Cooldown(at_sender=False)])
async def creat_auction_(bot: Bot, event: GroupMessageEvent):
    global auction, auction_offer_flag, auction_offer_all_count, auction_offer_time_count
    group_id = str(event.group_id)
    bot = await assign_bot_group(group_id=group_id)
    isUser, user_info, msg = check_user(event)
    
    # 检查用户是否有效
    if not isUser:
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()


    # 检查当前是否有正在进行的拍卖
    if auction:
        msg = "本群已存在一场拍卖会，请等待拍卖会结束！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    auction_items = []  # 存储拍卖物品
    try:

        # 获取系统拍卖品
        auction_id_list = get_auction_id_list()
        auction_count = random.randint(15, 20)  # 随机挑选系统拍卖品数量
        auction_ids = random.sample(auction_id_list, auction_count)
        for auction_id in auction_ids:
            item_info = items.get_data_by_item_id(auction_id)
            item_quantity = 1
            if item_info['type'] in ['神物', '丹药']:
                item_quantity = random.randint(1, 3)  # 如果是丹药的话随机挑1-3个
            start_price = get_auction_price_by_id(auction_id)['start_price']
            newtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status = 1
            string = "一二三四五六七八九"
            random_list = random.sample(list(string), 5)
            auctionid = ''.join(random_list)
            auction_items.append((auctionid, auction_id, 0, 1, start_price, False, newtime, 0, status))
        
        sql_message.insert_auction_items(auctionid, 0, auction_items, newtime, 0, status)
    except LookupError:
        msg = f"获取不到拍卖物品的信息，请检查配置文件！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()


@offer_auction.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GLOBAL)])
async def offer_auction_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """拍卖"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
  #  global auction, auction_offer_flag, auction_offer_all_count, auction_offer_time_count
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await offer_auction.finish()


    msg_text = args.extract_plain_text().strip()
    msg_parts = msg_text.split()
    if len(msg_parts) < 2:
        msg = "请提供拍卖编号和出价竞拍价格。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '出价竞拍', '拍卖', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))  
        await offer_auction.finish()        
    auctionid = msg_parts[0]  
    price = msg_parts[1] 
    
    try:
        price = int(price)
    except ValueError:
        msg = f"请发送正确的灵石数量"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '出价竞拍', '拍卖', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await offer_auction.finish()
    auction_status = sql_message.get_auction_status()  # 假设有此方法返回当前拍卖的状态
   # print(f"Auction status: {auction_status}")
    if auction_status == 2:
        msg = f"今日的拍卖会已结束，无法再出价。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '仙市集会', '仙市集会', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await offer_auction.finish() 
    auction = sql_message.get_auction_info_by_auctionid(auctionid)
    now_price = auction['start_price']
    min_price = int(now_price * 0.05)  # 最低加价5%
    if price <= 0 or price <= auction['start_price'] or price > user_info['stone']:
        msg = f"走开走开，别捣乱！小心清空你灵石捏"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '出价竞拍', f'拍卖{auctionid}', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await offer_auction.finish()
    if price - now_price < min_price:
        msg = f"拍卖不得少于当前出价竞拍价的5%，目前最少加价为：{min_price:,}灵石，目前出价竞拍价为：{auction['start_price']:,}!"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '出价竞拍', f'拍卖{auctionid}', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await offer_auction.finish()

  #  auction_offer_flag = True  # 有人拍卖
  #  auction_offer_time_count += 1
 #   auction_offer_all_count += 1

    auction['user_id'] = user_info['user_id']
    auction['start_price'] = price

    logger.opt(colors=True).info(f"<green>{user_info['user_name']}({auction['user_id']})竞价了！！</green>")

    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if str(user_info['user_id']) == str(auction['seller_id']).strip():
        msg = f"道友不得捣乱拍卖会，禁止提价自己的拍卖品。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '出价竞拍', '拍卖', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await offer_auction.finish()
    else:
        sql_message.update_auction_info(auction['start_price'], now_time, auction['user_id'], auctionid)
        msg = f"***{user_info['user_name']}***道友出价：{price:,}枚灵石！" 
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '出价竞拍', '拍卖', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await offer_auction.finish()


@auction_added.handle(parameterless=[Cooldown(1.4, isolate_level=CooldownIsolateLevel.GROUP)])
async def auction_added_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """用户提交拍卖品"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    group_id = str(event.group_id)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await auction_added.finish()


    seller_id = user_info['user_id']
    args = args.extract_plain_text().split()
    goods_name = args[0] if len(args) > 0 else None
    price_str = args[1] if len(args) > 1 else "1000000"
    quantity_str = args[2] if len(args) > 2 else "1"
    auction_status = sql_message.get_auction_status()  # 假设有此方法返回当前拍卖的状态
   # print(f"Auction status: {auction_status}")
    if auction_status == 2:  # 假设状态2表示拍卖已结束
        msg = f"当前拍卖会已结束，无法提交拍卖品。"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await auction_added.finish()
    if not goods_name:
        msg = f"请输入正确指令！例如：提交拍卖品 物品 金额 数量"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '提交拍卖品', '提交拍卖品', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await auction_added.finish()

    back_msg = sql_message.get_back_msg(seller_id)  # 获取背包信息
    if back_msg is None:
        msg = f"道友的背包空空如也！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '仙市集会', '仙市集会', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await auction_added.finish()

    # 物品是否存在于背包中
    in_flag = False
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    goods_bind_num = None
    for back in back_msg:
        if goods_name == back['goods_name']:
            in_flag = True
            goods_id = back['goods_id']
            goods_type = back['goods_type']
            goods_state = back['state']
            goods_num = back['goods_num']
            goods_bind_num = back['bind_num']
            break

    if not in_flag:
        msg = f"请检查该道具 {goods_name} 是否在背包内！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我的背包', '我的背包', True), (2, '我的功法', '我的功法', True)],  
            [(2, '药材背包', '药材背包', True)],             
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await auction_added.finish()

    stone = user_info['stone']
    try:
        price = int(price_str)
        quantity = int(quantity_str)
        if 0 < price < 1000000:
            price = 1000000        
        if price <= 0 or quantity <= 0 or quantity > goods_num:
            raise ValueError("价格和数量必须为正数，或者超过了你拥有的数量!")
        if stone < price * 0.2:
            raise ValueError("道友的灵石不足，无法提交拍卖品到仙市集会。")
    except ValueError as e:
        msg = f"请输入正确的金额和数量: {str(e)}"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '提交拍卖品', '提交拍卖品', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await auction_added.finish()

    if goods_type == "装备" and int(goods_state) == 1 and int(goods_num) == 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法提交！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '卸载装备', f'换装 {goods_name}', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await auction_added.finish()

 #   if int(goods_num) <= int(goods_bind_num):
 #       msg = f"该物品是绑定物品，无法提交！"
 #       if XiuConfig().img:
 #           pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
 #           await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
 #       else:
 #           await bot.send_group_msg(group_id=int(send_group_id), message=msg)
 #       await auction_added.finish()
    if goods_type == "聚灵旗" or goods_type == "炼丹炉":
        if user_info['root'] == "器师":
            pass
        else:
            msg = f"道友职业无法上架拍卖品！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '重入仙途', '重入仙途', True)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await auction_added.finish()

    config = get_auction_config()
    
    string = "一二三四五六七八九"
    random_list = random.sample(list(string), 5)
    auctionid = ''.join(random_list)
    is_user_auction = "Yes"
    item_quantity = quantity
    start_price = price
    auction_id = goods_id
   # user_id = seller_id
    cost = price * quantity * 0.2
    newtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql_message.update_ls(seller_id, cost, 2)
    sql_message.update_back_j(seller_id, goods_id, num=quantity)    
    sql_message.update_auction_info_byid(auctionid, auction_id, seller_id, item_quantity, start_price, is_user_auction, newtime, seller_id, 1)
    msg = f"成功扣除道友灵石{cost}。道友的拍卖品：{goods_name}成功提交，底价：{price:,}枚灵石，数量：{quantity}"
   # msg += f"\n下次拍卖将优先拍卖道友的拍卖品！！！"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '提交拍卖品', '提交拍卖品', False)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await auction_added.finish()


@set_auction.handle(parameterless=[Cooldown(at_sender=False)])
async def set_auction_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """群拍卖会开关"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)
    is_in_group = is_in_groups(event)  # True在，False不在

    if mode == '开启':
        if is_in_group:
            msg = "本群已开启群拍卖会，请勿重复开启!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()
        else:
            config['open'].append(group_id)
            savef_auction(config)
            msg = "已开启群拍卖会"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()

    elif mode == '关闭':
        if is_in_group:
            config['open'].remove(group_id)
            savef_auction(config)
            msg = "已关闭本群拍卖会!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()
        else:
            msg = "本群未开启群拍卖会!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()

    else:
        msg = __back_help__
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await set_auction.finish()


@chakan_wupin.handle(parameterless=[Cooldown(at_sender=False)])
async def chakan_wupin_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看修仙界所有物品列表"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    args = args.extract_plain_text().strip()
    list_tp = []
    if args not in ["功法", "辅修功法", "神通", "丹药", "合成丹药", "法器", "防具"]:
        msg = "请输入正确类型【功法|辅修功法|神通|丹药|合成丹药|法器|防具】！！！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '功法', '查看修仙界物品功法', True), (2, '辅修功法', '查看修仙界物品辅修功法 ', True)],            
            [(2, '神通', '查看修仙界物品神通 ', True), (2, '丹药', '查看修仙界物品丹药 ', True)], 
            [(2, '法器', '查看修仙界物品法器 ', True), (2, '防具', '查看修仙界物品防具 ', True)], 
            [(2, '合成丹药', '查看修仙界物品合成丹药 ', True)],             
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await chakan_wupin.finish()
    else:
        if args == "功法":
            gf_data = items.get_data_by_item_type(['功法'])
            for x in gf_data:
                name = gf_data[x]['name']
                rank = gf_data[x]['level']
                msg = f"\n>※{rank}:<qqbot-cmd-input text=\"查看物品效果{x}\" show=\"{name}\" reference=\"false\" />"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                                "content": msg}})
        elif args == "辅修功法":
            gf_data = items.get_data_by_item_type(['辅修功法'])
            for x in gf_data:
                name = gf_data[x]['name']
                rank = gf_data[x]['level']
                msg = f"\n>※{rank}:<qqbot-cmd-input text=\"查看物品效果{x}\" show=\"{name}\" reference=\"false\" />"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                                "content": msg}})
        elif args == "神通":
            st_data = items.get_data_by_item_type(['神通'])
            for x in st_data:
                name = st_data[x]['name']
                rank = st_data[x]['level']
                msg = f"\n>※{rank}:<qqbot-cmd-input text=\"查看物品效果{x}\" show=\"{name}\" reference=\"false\" />"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                                "content": msg}})
        elif args == "丹药":
            dy_data = items.get_data_by_item_type(['丹药'])
            for x in dy_data:
                name = dy_data[x]['name']
                rank = dy_data[x]['境界']
                desc = dy_data[x]['desc']
                msg = f"\n>※{rank}丹药:<qqbot-cmd-input text=\"查看物品效果{x}\" show=\"{name}\" reference=\"false\" />"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                                "content": msg}})
        elif args == "合成丹药":
            hcdy_data = items.get_data_by_item_type(['合成丹药'])
            for x in hcdy_data:
                name = hcdy_data[x]['name']
                rank = hcdy_data[x]['境界']
                desc = hcdy_data[x]['desc']
                msg = f"\n>※{rank}合成丹药:<qqbot-cmd-input text=\"查看物品效果{x}\" show=\"{name}\" reference=\"false\" />"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                                "content": msg}})
        elif args == "法器":
            fq_data = items.get_data_by_item_type(['法器'])
            skip_ids = {15485, 15484, 15483, 15482, 15481, 15480, 15479, 15477, 15476, 15475, 15474, 15473, 15472, 15471, 15470, 15469}
            for x in fq_data:
                item_id = int(x)                 
                if item_id in skip_ids:
                    continue              
                name = fq_data[x]['name']
                rank = fq_data[x]['level']
                msg = f"\n>※{rank}:<qqbot-cmd-input text=\"查看物品效果{x}\" show=\"{name}\" reference=\"false\" />"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                                "content": msg}})
        elif args == "防具":
            fj_data = items.get_data_by_item_type(['防具'])
            skip_ids = {6107, 6096, 6097, 6098, 6100, 6102, 6103, 6104}
            for x in fj_data:
                item_id = int(x)                 
                if item_id in skip_ids:
                    continue               
                name = fj_data[x]['name']
                rank = fj_data[x]['level']
                msg = f"\n>※{rank}:<qqbot-cmd-input text=\"查看物品效果{x}\" show=\"{name}\" reference=\"false\" />"
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                                "content": msg}})
        try:
            params_items = [('msg', "\n\n".join([item["data"]["content"] for item in list_tp]))]
            buttons = [
                [(2, '功法', '查看修仙界物品功法', True), (2, '辅修功法', '查看修仙界物品辅修功法 ', True)],            
                [(2, '神通', '查看修仙界物品神通 ', True), (2, '丹药', '查看修仙界物品丹药 ', True)], 
                [(2, '法器', '查看修仙界物品法器 ', True), (2, '防具', '查看修仙界物品防具 ', True)], 
                [(2, '合成丹药', '查看修仙界物品合成丹药 ', True)],
            ]                
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        except ActionFailed:
            msg = "未知原因，查看失败!"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await chakan_wupin.finish()


@shop_off_all.handle(parameterless=[Cooldown(60, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_off_all_(bot: Bot, event: GroupMessageEvent):
    """坊市清空"""
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
        await shop_off_all.finish()
    group_id = str(event.group_id)
    shop_data = get_shop_data(group_id)
    if shop_data[group_id] == {}:
        msg = "坊市目前空空如也！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await shop_off_all.finish()

    msg = "正在清空,稍等！"
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)

    list_msg = []
    msg = ""
    num = len(shop_data[group_id])
    for x in range(num):
        x = num - x
        if shop_data[group_id][str(x)]['user_id'] == 0:  # 这么写为了防止bot.send发送失败，不结算
            msg += f"成功下架系统物品：{shop_data[group_id][str(x)]['goods_name']}!\n"
            del shop_data[group_id][str(x)]
            save_shop(shop_data)
        else:
            sql_message.send_back(shop_data[group_id][str(x)]['user_id'], shop_data[group_id][str(x)]['goods_id'],
                                  shop_data[group_id][str(x)]['goods_name'],
                                  shop_data[group_id][str(x)]['goods_type'], shop_data[group_id][str(x)]['stock'])
            msg += f"成功下架{shop_data[group_id][str(x)]['user_name']}的{shop_data[group_id][str(x)]['stock']}个{shop_data[group_id][str(x)]['goods_name']}!\n"
            del shop_data[group_id][str(x)]
            save_shop(shop_data)
    shop_data[group_id] = reset_dict_num(shop_data[group_id])
    save_shop(shop_data)
    list_msg.append(
                    {"type": "node", "data": {"name": "执行清空坊市ing", "uin": bot.self_id,
                                              "content": msg}})
    try:
        await send_msg_handler(bot, event, list_msg)
    except ActionFailed:
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await shop_off_all.finish()


def reset_dict_num(dict_):
    i = 1
    temp_dict = {}
    for k, v in dict_.items():
        temp_dict[i] = v
        temp_dict[i]['编号'] = i
        i += 1
    return temp_dict


def get_user_auction_id_list():
    user_auctions = config['user_auctions']
    user_auction_id_list = []
    for auction in user_auctions:
        for k, v in auction.items():
            user_auction_id_list.append(v['id'])
    return user_auction_id_list

def get_auction_id_list():
    auctions = config['auctions']
    auction_id_list = []
    for k, v in auctions.items():
        auction_id_list.append(v['id'])
    return auction_id_list

def get_user_auction_price_by_id(id):
    user_auctions = config['user_auctions']
    user_auction_info = None
    for auction in user_auctions:
        for k, v in auction.items():
            if int(v['id']) == int(id):
                user_auction_info = v
                break
        if user_auction_info:
            break
    return user_auction_info

def get_auction_price_by_id(id):
    auctions = config['auctions']
    auction_info = None
    for k, v in auctions.items():
        if int(v['id']) == int(id):
            auction_info = v
            break
    return auction_info


def is_in_groups(event: GroupMessageEvent):
    return str(event.group_id) in groups


def get_auction_msg(auction_id):
    item_info = items.get_data_by_item_id(auction_id)
    _type = item_info['type']
    msg = None
    if _type == "装备":
        if item_info['item_type'] == "防具":
            msg = get_armor_info_msg(auction_id, item_info)
        if item_info['item_type'] == '法器':
            msg = get_weapon_info_msg(auction_id, item_info)

    if _type == "技能":
        if item_info['item_type'] == '神通':
            msg = f"{item_info['level']}-{item_info['name']}:\n"
            msg += f"效果：{get_sec_msg(item_info)}"
        if item_info['item_type'] == '功法':
            msg = f"{item_info['level']}-{item_info['name']}\n"
            msg += f"效果：{get_main_info_msg(auction_id)[1]}"
        if item_info['item_type'] == '辅修功法': #辅修功法10
            msg = f"{item_info['level']}-{item_info['name']}\n"
            msg += f"效果：{get_sub_info_msg(auction_id)[1]}"
            
    if _type == "神物":
        msg = f"{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    if _type == "丹药":
        msg = f"{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    return msg

@add_gongfa_gacha.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def add_gongfa_gacha_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """抽取功法"""
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
        await add_gongfa_gacha.finish()
    args = args.extract_plain_text().strip().split()
    uid = user_info['user_id']
    gacha_DUNDCORE = 10000000  #单抽所需金币
    if len(args) == 1:
        if args[0].isdigit():
            gachanum = int(args[0])
        else:
            gachanum = 1
    else:
        gachanum = 1 
    
    if gachanum > 100:
        gachanum = 100

    need_score = gacha_DUNDCORE*gachanum
    my_score = user_info['stone']

    if need_score>my_score:
        msg = f'抽卡需要灵石{need_score}枚\n道友的灵石不足：{my_score}，无法获得道具哦'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '抽取技能书', '抽取技能书', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await add_gongfa_gacha.finish()        

    results = []
    goods_type = ["功法", "辅修功法", "神通"]
    itemlist = items.get_data_by_item_type(goods_type)
    level_weights = {
                "人阶下品": 1000,
                "人阶上品": 1000,
                "黄阶下品": 550,
                "黄阶上品": 500,
                "玄阶下品": 450,
                "玄阶上品": 400,
                "地阶下品": 300,
                "地阶上品": 200,
                "天阶下品": 100,
                "天阶上品": 50,
                "仙阶下品": 15,
                "仙阶上品": 10,
                "仙阶极品": 5,
                "无上仙法": 0,
                "无上神通": 0
            }
    
    total_weight = sum(level_weights[item["level"]] for item in itemlist.values())  # 总权重，基于物品的等级权重

    for _ in range(gachanum):
        # 生成一个随机数，范围从1到总权重
        random_weight = random.randint(1, total_weight)

        # 根据随机数选择物品
        running_total = 0
        selected_item = None
        for item_key, item in itemlist.items():
            running_total += level_weights[item["level"]]  # 累加当前物品的权重
            if random_weight <= running_total:
                selected_item = item
                break
        
        # 添加抽中的物品到结果
        if selected_item:
            results.append(selected_item["name"])

    # 对结果进行统计
    result_count = Counter(results)
    # 构造输出信息
    get_gachalist = ""
    for propname, propnum in result_count.items():
        showicon = ""
        item_id = None  # 初始化 item_id
        for item_key, item in itemlist.items():
            if propname == item["name"]:  # 匹配物品名称
                item_id = item_key  # 获取物品 ID
                if item["level"] in ["仙阶下品", "仙阶上品"]:  # 仙阶极品等级
                    showicon = "🎉"
                elif item["level"] == "仙阶极品":  # 无上仙法等级
                    showicon = "🎉🎉"                     
                elif item["level"] in ["无上神通", "无上仙法"]:  # 无上仙法等级
                    showicon = "🎉🎉🎉"            
                break
        sql_message.send_back(uid, int(item_key), item["name"], item["type"], int(propnum))
        get_gachalist += f"\n\n><qqbot-cmd-input text=\"查看物品效果{item_id}\" show=\"{propname}\" reference=\"false\" /> [{item['item_type']}]  [{item['level']}] {propnum}个{showicon}"
    last_score = my_score - need_score
    sql_message.update_ls(uid, need_score, 2)   
   # sql_message.send_back(uid, int(item_id), item["name"], item["type"], int(propnum))
    msg = f"道友***{user_info['user_name']}***消耗{need_score}灵石，剩余灵石{last_score}\n累计抽取{gachanum}次获得的技能书为：{get_gachalist}"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '抽取技能书', '抽取技能书', False)],[(2, '抽取装备', '抽取装备', False)],             
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await add_gongfa_gacha.finish()
    
    
@add_zhuangbei_gacha.handle(parameterless=[Cooldown(1.4, at_sender=False, isolate_level=CooldownIsolateLevel.GROUP)])
async def add_zhuangbei_gacha_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """抽取装备"""
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
        await add_gongfa_gacha.finish()
    args = args.extract_plain_text().strip().split()
    uid = user_info['user_id']
    gacha_DUNDCORE = 10000000  #单抽所需金币
    if len(args) == 1:
        if args[0].isdigit():
            gachanum = int(args[0])
        else:
            gachanum = 1
    else:
        gachanum = 1 
    
    if gachanum > 100:
        gachanum = 100

    need_score = gacha_DUNDCORE*gachanum
    my_score = user_info['stone']

    if need_score>my_score:
        msg = f'抽卡需要灵石{need_score}枚\n道友的灵石不足：{my_score}，无法获得装备哦'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '抽取装备', '抽取装备', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await add_gongfa_gacha.finish()        

    results = []
    goods_type = ["法器", "防具"]
    itemlist = items.get_data_by_item_type(goods_type)
    level_weights = {
                "下品符器": 1000,
                "上品符器": 1000,
                "下品法器": 550,
                "下品玄器": 550,
                "上品玄器": 550,
                "上品法器": 500,
                "下品纯阳": 500,
                "上品纯阳": 500,
                "下品纯阳法器": 450,
                "上品纯阳法器": 400,
                "下品通天法器": 300,
                "下品通天": 300,
                "上品通天": 300,
                "上品通天法器": 300,
                "下品仙器": 50,
                "上品仙器": 50,
                "极品仙器": 10,
                "无上仙器": 5,
                "世界之源": 0,
                "万魔之始": 0,   
                "夏之花·无尽爱": 0,
                "满天星·无尽夏": 0,
                "生息之源": 0,
                "空想之灵": 0,
                "传递之薪": 0,
                "轻盈之杏": 0,
                "救援之力": 0,
                "神州往事": 0,
                "新春限定": 0,
                "心动缔结": 0,
                "世界之源": 0,
                "音之精灵": 0
            }
    
    total_weight = sum(level_weights[item["level"]] for item in itemlist.values())  # 总权重，基于物品的等级权重

    for _ in range(gachanum):
        # 生成一个随机数，范围从1到总权重
        random_weight = random.randint(1, total_weight)

        # 根据随机数选择物品
        running_total = 0
        selected_item = None
        for item_key, item in itemlist.items():
            running_total += level_weights[item["level"]]  # 累加当前物品的权重
            if random_weight <= running_total:
                selected_item = item
                break
        
        # 添加抽中的物品到结果
        if selected_item:
            results.append(selected_item["name"])

    # 对结果进行统计
    result_count = Counter(results)
    # 构造输出信息
    get_gachalist = ""
    for propname, propnum in result_count.items():
        showicon = ""
        item_id = None  # 初始化 item_id
        for item_key, item in itemlist.items():
            if propname == item["name"]:  # 匹配物品名称
                item_id = item_key  # 获取物品 ID
                if item["level"] in ["上品仙器"]:  # 仙阶极品等级
                    showicon = "🎉"
                elif item["level"] == "极品仙器":  # 无上仙法等级
                    showicon = "🎉🎉"                     
                elif item["level"] in ["无上仙器"]:  # 无上仙法等级
                    showicon = "🎉🎉🎉"            
                break
        sql_message.send_back(uid, int(item_key), item["name"], item["type"], int(propnum))
        get_gachalist += f"\n\n><qqbot-cmd-input text=\"查看物品效果{item_id}\" show=\"{propname}\" reference=\"false\" /> [{item['item_type']}]  [{item['level']}] {propnum}个{showicon}"
    last_score = my_score - need_score
    sql_message.update_ls(uid, need_score, 2)   
   # sql_message.send_back(uid, int(item_id), item["name"], item["type"], int(propnum))
    msg = f"道友***{user_info['user_name']}***消耗{need_score}灵石，剩余灵石{last_score}\n累计抽取{gachanum}次获得的装备为：{get_gachalist}"
    params_items = [('msg', msg)]               
    buttons = [
        [(2, '抽取装备', '抽取装备', False)],[(2, '抽取技能书', '抽取技能书', False)],              
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await add_gongfa_gacha.finish()
