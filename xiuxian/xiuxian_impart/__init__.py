import os
import base64
from pathlib import Path
import random
import time
from nonebot import on_command, on_fullmatch
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.typing import T_Handler
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    MessageSegment,
    ActionFailed
)
from ..xiuxian_utils.lay_out import assign_bot, Cooldown
from ..xiuxian_utils.data_source import jsondata
from ..xiuxian_utils.utils import (
    check_user,
    markdown,
    get_msg_pic, send_msg_handler,
    CommandObjectID
)
from .impart_uitls import impart_check, get_rank, re_impart_data
from .impart_data import impart_data_json
from ..xiuxian_config import XiuConfig
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, XiuxianJsonDate, OtherSet, 
    UserBuffDate, XIUXIAN_IMPART_BUFF
)

from .. import NICKNAME

xiuxian_impart = XIUXIAN_IMPART_BUFF()


sql_message = XiuxianDateManage()

cache_help = {}
img_path = Path() / os.getcwd() / "data" / "xiuxian" / "card"
time_img = ["花园百花", "花园温室", "画屏春-倒影", "画屏春-繁月", "画屏春-花临",
            "画屏春-皇女", "画屏春-满桂", "画屏春-迷花", "画屏春-霎那", "画屏春-邀舞"]

get_drawgift = on_command("领取抽卡次数", priority=16, permission=GROUP, block=True)
gm_command_draw = on_command("xf增加抽卡", permission=SUPERUSER, priority=10, block=True)
impart_draw_s = on_command("礼包传承抽卡", priority=16, permission=GROUP, block=True)
impart_draw = on_command("传承抽卡", priority=16, permission=GROUP, block=True)
impart_back = on_command("传承背包", aliases={"我的传承背包"}, priority=15, permission=GROUP, block=True)
impart_info = on_command("传承信息", aliases={"我的传承信息", "我的传承"}, priority=10, permission=GROUP, block=True)
impart_help = on_command("传承帮助", aliases={"虚神界帮助"}, priority=8, permission=GROUP, block=True)
re_impart_load = on_fullmatch("加载传承数据", priority=45, permission=GROUP, block=True)
impart_img = on_command("传承卡图", aliases={"传承卡片"}, priority=50, permission=GROUP, block=True)
__impart_help__ = f"""
传承帮助信息:
指令:
\n><qqbot-cmd-input text=\"传承抽卡\" show=\"传承抽卡\" reference=\"false\" />传承抽卡:花费1000w灵石获取一次传承卡片(抽到的卡片被动加成)
\n><qqbot-cmd-input text=\"传承背包\" show=\"传承背包\" reference=\"false\" />传承背包:获取传承全部信息
\n><qqbot-cmd-input text=\"加载传承数据\" show=\"加载传承数据\" reference=\"false\" />加载传承数据:重新从卡片中加载所有传承属性(数据显示有误时可用)
\n><qqbot-cmd-input text=\"传承卡图\" show=\"传承卡图\" reference=\"false\" />传承卡图:加上卡片名字获取传承卡牌原画
\n<qqbot-cmd-input text="领取抽卡次数" show="领取抽卡次数" reference="false" /> 
"""


__impart_helps__ = f"""
传承帮助信息:
指令:
1、传承抽卡:花费10颗思恋结晶获取一次传承卡片(抽到的卡片被动加成)
2、传承信息:获取传承主要信息
3、传承背包:获取传承全部信息
4、加载传承数据:重新从卡片中加载所有传承属性(数据显示有误时可用)
5、传承卡图:加上卡片名字获取传承卡牌原画
6、投影虚神界:将自己的分身投影到虚神界,将可被所有地域的道友挑战
7、虚神界列表:查找虚神界里所有的投影
8、虚神界对决:输入虚神界人物编号即可与对方对决,不输入编号将会与{NICKNAME}进行对决
9、虚神界修炼:加入对应的修炼时间,即可在虚神界修炼
思恋结晶获取方式:虚神界对决【俄罗斯轮盘修仙版】
双方共6次机会,6次中必有一次暴毙
获胜者将获取10颗思恋结晶并不消耗虚神界对决次数
失败者将获取5颗思恋结晶并且消耗一次虚神界对决次数
每天有三次虚神界对决次数
"""

@impart_help.handle(parameterless=[Cooldown(at_sender=False)])
async def impart_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """传承帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await impart_help.finish()
    else:
        msg = __impart_help__
        params_items = [('msg', msg)]               
        buttons = [           
            [(2, '传承抽卡', '传承抽卡', True), (2, '传承背包', '传承背包', True)],
            [(2, '传承卡图', '传承卡图', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await impart_help.finish()


@impart_img.handle(parameterless=[Cooldown(at_sender=False)])
async def impart_img_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """传承卡图"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    img_name = args.extract_plain_text().strip()
    img = img_path / (img_name + ".png")  # 使用原始字符串拼接路径
    if not img.exists():
        msg = f"没有找到此卡图！请确认卡图名字。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '传承卡图', '传承卡图', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    else:
        # 读取图片并转换为Base64
        with open(img, "rb") as image_file:
            base64_str = base64.b64encode(image_file.read()).decode('utf-8')
        
        # 构造Base64格式的图片消息
        base64_image = f"base64://{base64_str}"
        
        # 发送图片消息
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(base64_image))
        await impart_img.finish()


@impart_draw.handle(parameterless=[Cooldown(at_sender=False)])
async def impart_draw_(bot: Bot, event: GroupMessageEvent):
    """传承抽卡"""
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
        await impart_draw.finish()

    user_id = user_info['user_id']
    impart_data_draw = await impart_check(user_id)
    stone = user_info['stone']
    if stone is None:
        msg = f"发生未知错误，多次尝试无果请联系作者！"
        params_items = [('msg', msg)]               
        buttons = [           
            [(2, '传承背包', '传承背包', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await impart_draw.finish()
    if stone < 10000000:
        msg = f"道友所拥有的灵石数为{stone},不足以抽卡！"
        params_items = [('msg', msg)]               
        buttons = [           
            [(2, '传承背包', '传承背包', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await impart_draw.finish()
    else:
        if get_rank(user_id):
            img_list = impart_data_json.data_all_keys()
            reap_img = None
            try:
                reap_img = random.choice(img_list)
            except:
                msg = f"请检查卡图数据完整！"
                params_items = [('msg', msg)]               
                buttons = [           
                    [(2, '加载传承数据', '加载传承数据', True)],
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await impart_draw.finish()
            list_tp = []
            if impart_data_json.data_person_add(user_id, reap_img):
                msg = f""
                msg += f"检测到传承背包已经存在卡片{reap_img}\n"
              #  msg += f"已转化为2880分钟闭关时间\n"
              #  msg += f"累计共获得3540分钟闭关时间!"
                msg += f"抽卡10次结果如下\n"

                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": msg}})
                if XiuConfig().merge_forward_send:
                    img = MessageSegment.image(img_path / str(reap_img + ".png"))
                else:
                    img = str(reap_img)
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": img}})
                random.shuffle(time_img)
                for x in time_img[:9]:
                    if XiuConfig().merge_forward_send:
                        img = MessageSegment.image(img_path / str(x + ".png"))
                    else:
                        img = str(x)
                    list_tp.append(
                        {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                                  "content": img}})
                try:
                    msgs = "\n".join([item["data"]["content"] for item in list_tp])
                    params_items = [('msg', msgs)]

                    # 初始化按钮列表
                    button_list = [
                        [(2, '礼包传承抽卡', '礼包传承抽卡', True)],
                        [(2, '传承抽卡', '传承抽卡', False)], 
                    ]

                    # 调用 markdown 函数生成数据
                    data = await markdown(params_items, button_list)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                except ActionFailed:
                    msg = f"未知原因，抽卡失败!"
                    params_items = [('msg', msg)]               
                    buttons = [           
                        [(2, '传承抽卡', '传承抽卡', True)],
                    ]
                   # 调用 markdown 函数生成数据
                    data = await markdown(params_items, buttons)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                    await impart_draw.finish()
                xiuxian_impart.add_impart_exp_day(3540, user_id)
                sql_message.update_ls(user_id, 10000000, 2)
                xiuxian_impart.update_impart_wish(0, user_id)
                # 更新传承数据
                await re_impart_data(user_id)
                await impart_draw.finish()
            else:
                msg = f""
              #  msg += f"累计共获得660分钟闭关时间!"
                msg += f"抽卡10次结果如下：\n获得新的传承卡片：：<qqbot-cmd-input text=\"传承卡图 {reap_img}\" show=\"{reap_img}\" reference=\"false\" />\n"
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": msg}})
                if XiuConfig().merge_forward_send:
                    img = MessageSegment.image(img_path / str(reap_img + ".png"))
                else:
                    img = str(reap_img)
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": img}})
                random.shuffle(time_img)
                for x in time_img[:9]:
                    if XiuConfig().merge_forward_send:
                        img = MessageSegment.image(img_path / str(x + ".png"))
                    else:
                        img = str(x)
                    list_tp.append(
                        {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                                  "content": img}})
                try:
                    msgs = "\n".join([item["data"]["content"] for item in list_tp])
                    params_items = [('msg', msgs)]

                    # 初始化按钮列表
                    button_list = [
                        [(2, '礼包传承抽卡', '礼包传承抽卡', True)],
                        [(2, '传承抽卡', '传承抽卡', False)], 
                    ]

                    # 调用 markdown 函数生成数据
                    data = await markdown(params_items, button_list)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                except ActionFailed:
                    msg = f"消息发送失败，抽卡失败!"
                    params_items = [('msg', msg)]               
                    buttons = [           
                        [(2, '传承抽卡', '传承抽卡', True)],
                    ]
                   # 调用 markdown 函数生成数据
                    data = await markdown(params_items, buttons)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                    await impart_draw.finish()
                xiuxian_impart.add_impart_exp_day(660, user_id)
                sql_message.update_ls(user_id, 10000000, 2)
                xiuxian_impart.update_impart_wish(0, user_id)
                # 更新传承数据
                await re_impart_data(user_id)
                await impart_draw.finish()
        else:
            list_tp = []
            msg = f""
         #   msg += f"累计共获得660分钟闭关时间!"
            msg += f"抽卡10次结果如下!\n"
            list_tp.append(
                {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                          "content": msg}})
            random.shuffle(time_img)
            for x in time_img:
                if XiuConfig().merge_forward_send:
                    img = MessageSegment.image(img_path / str(x + ".png"))
                else:
                    img = str(x)
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": img}})
            try:
                msgs = "\n".join([item["data"]["content"] for item in list_tp])
                params_items = [('msg', msgs)]

                # 初始化按钮列表
                button_list = [
                    [(2, '礼包传承抽卡', '礼包传承抽卡', True)],
                    [(2, '传承抽卡', '传承抽卡', False)], 
                ]

                # 调用 markdown 函数生成数据
                data = await markdown(params_items, button_list)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            except ActionFailed:
                msg = f"未知原因，抽卡失败!"
                params_items = [('msg', msg)]               
                buttons = [           
                    [(2, '传承抽卡', '传承抽卡', True)],
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await impart_draw.finish()
            xiuxian_impart.add_impart_exp_day(660, user_id)
            sql_message.update_ls(user_id, 10000000, 2)
            xiuxian_impart.add_impart_wish(10, user_id)
            await impart_draw.finish()


@impart_draw_s.handle(parameterless=[Cooldown(at_sender=False)])
async def impart_draw_s_(bot: Bot, event: GroupMessageEvent):
    """赠送传承抽卡"""
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
        await impart_draw_s.finish()

    user_id = user_info['user_id']
    impart_data_draw = await impart_check(user_id)
    if impart_data_draw is None:
        msg = f"发生未知错误，多次尝试无果请联系管理员！"
        params_items = [('msg', msg)]               
        buttons = [           
            [(2, '传承背包', '传承背包', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await impart_draw_s.finish()
    if impart_data_draw['stone_num'] < 10:
        msg = f"抽取数量不足10次,无法抽卡!"
        params_items = [('msg', msg)]               
        buttons = [           
            [(2, '传承背包', '传承背包', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await impart_draw_s.finish()
    else:
        if get_rank(user_id):
            img_list = impart_data_json.data_all_keys()
            reap_img = None
            try:
                reap_img = random.choice(img_list)
            except:
                msg = f"请检查卡图数据完整！"
                params_items = [('msg', msg)]               
                buttons = [           
                    [(2, '加载传承数据', '加载传承数据', True)],
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await impart_draw_s.finish()
            list_tp = []
            if impart_data_json.data_person_add(user_id, reap_img):
                msg = f""
                msg += f"检测到传承背包已经存在卡片{reap_img}\n"
             #   msg += f"已转化为2880分钟闭关时间\n"
             #   msg += f"累计共获得3540分钟闭关时间!"
                msg += f"抽卡10次结果如下\n"

                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": msg}})
                if XiuConfig().merge_forward_send:
                    img = MessageSegment.image(img_path / str(reap_img + ".png"))
                else:
                    img = str(reap_img)
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": img}})
                random.shuffle(time_img)
                for x in time_img[:9]:
                    if XiuConfig().merge_forward_send:
                        img = MessageSegment.image(img_path / str(x + ".png"))
                    else:
                        img = str(x)
                    list_tp.append(
                        {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                                  "content": img}})
                try:
                    msgs = "\n".join([item["data"]["content"] for item in list_tp])
                    params_items = [('msg', msgs)]

                    # 初始化按钮列表
                    button_list = [
                        [(2, '礼包传承抽卡', '礼包传承抽卡', True)],
                        [(2, '传承抽卡', '传承抽卡', False)], 
                    ]

                    # 调用 markdown 函数生成数据
                    data = await markdown(params_items, button_list)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                except ActionFailed:
                    msg = f"未知原因，抽卡失败!"
                    if XiuConfig().img:
                        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                    else:
                        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await impart_draw_s.finish()
                xiuxian_impart.add_impart_exp_day(3540, user_id)
                xiuxian_impart.update_stone_num(10, user_id, 2)
                xiuxian_impart.update_impart_wish(0, user_id)
                # 更新传承数据
                await re_impart_data(user_id)
                await impart_draw_s.finish()
            else:
                msg = f""
            #    msg += f"累计共获得660分钟闭关时间!"
                msg += f"抽卡10次结果如下：\n获得新的传承卡片：<qqbot-cmd-input text=\"传承卡图 {reap_img}\" show=\"{reap_img}\" reference=\"false\" />\n"
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": msg}})
                if XiuConfig().merge_forward_send:
                    img = MessageSegment.image(img_path / str(reap_img + ".png"))
                else:
                    img = str(reap_img)
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": img}})
                random.shuffle(time_img)
                for x in time_img[:9]:
                    if XiuConfig().merge_forward_send:
                        img = MessageSegment.image(img_path / str(x + ".png"))
                    else:
                        img = str(x)
                    list_tp.append(
                        {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                                  "content": img}})
                try:
                    msgs = "\n".join([item["data"]["content"] for item in list_tp])
                    params_items = [('msg', msgs)]

                    # 初始化按钮列表
                    button_list = [
                        [(2, '礼包传承抽卡', '礼包传承抽卡', True)],
                        [(2, '传承抽卡', '传承抽卡', False)], 
                    ]

                    # 调用 markdown 函数生成数据
                    data = await markdown(params_items, button_list)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                except ActionFailed:
                    msg = f"消息发送失败，抽卡失败!"
                    params_items = [('msg', msg)]               
                    buttons = [           
                        [(2, '传承抽卡', '传承抽卡', True)],
                    ]
                   # 调用 markdown 函数生成数据
                    data = await markdown(params_items, buttons)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                    await impart_draw_s.finish()
                xiuxian_impart.add_impart_exp_day(660, user_id)
                xiuxian_impart.update_stone_num(10, user_id, 2)
                xiuxian_impart.update_impart_wish(0, user_id)
                # 更新传承数据
                await re_impart_data(user_id)
                await impart_draw_s.finish()
        else:
            list_tp = []
            msg = f""
          #  msg += f"累计共获得660分钟闭关时间!"
            msg += f"抽卡10次结果如下!\n"
            list_tp.append(
                {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                          "content": msg}})
            random.shuffle(time_img)
            for x in time_img:
                if XiuConfig().merge_forward_send:
                    img = MessageSegment.image(img_path / str(x + ".png"))
                else:
                    img = str(x)
                list_tp.append(
                    {"type": "node", "data": {"name": f"道友{user_info['user_name']}的传承抽卡", "uin": bot.self_id,
                                              "content": img}})
            try:
                msgs = "\n".join([item["data"]["content"] for item in list_tp])
                params_items = [('msg', msgs)]

                # 初始化按钮列表
                button_list = [
                    [(2, '礼包传承抽卡', '礼包传承抽卡', True)],
                    [(2, '传承抽卡', '传承抽卡', False)], 
                ]

                # 调用 markdown 函数生成数据
                data = await markdown(params_items, button_list)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            except ActionFailed:
                msg = f"未知原因，抽卡失败!"
                params_items = [('msg', msg)]               
                buttons = [           
                    [(2, '礼包传承抽卡', '礼包传承抽卡', True)],
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await impart_draw_s.finish()
            xiuxian_impart.add_impart_exp_day(660, user_id)
            xiuxian_impart.update_stone_num(10, user_id, 2)
            xiuxian_impart.add_impart_wish(10, user_id)
            await impart_draw_s.finish()


@get_drawgift.handle(parameterless=[Cooldown(at_sender=False)])
async def get_drawgift_(bot: Bot, event: GroupMessageEvent):
    """领取礼包"""
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
        await get_drawgift.finish()  
    user_id = user_info['user_id']
    level = user_info['level']
    list_level_all = list(jsondata.level_data().keys())
    if (list_level_all.index(level) < list_level_all.index(XiuConfig().gift_min_level)):
        msg = f"领取礼包境界最低要求为{XiuConfig().gift_min_level}，道友请多多修炼才是！"
        params_items = [('msg', msg)]
        buttons = [
            [(2, '修炼', '修炼', True)],                        
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await create_sect.finish()    
    current_timestamp = time.time()
    # 设置截止时间（2024年10月7日的时间戳）
    end_timestamp = time.mktime(time.strptime("2024-10-07", "%Y-%m-%d"))

    if current_timestamp > end_timestamp:   
        msg = "礼包领取已结束，祝您中秋国庆快乐！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修炼', '修炼', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await get_gift.finish()    
    impart_data_draw = await impart_check(user_id)    
    scorenum = 50
    propname = "渡厄丹"
    propnum = 10 
    gift_info = sql_message.get_gift_info(user_info['user_id'])  
    
    if gift_info == 0:
       # sql_message.update_ls(user_info['user_id'], scorenum, 1)  # 发放300万灵石
        sql_message.send_back(user_id, 1999, "渡厄丹", "丹药", propnum, 0)  # 发放物品
        xiuxian_impart.update_stone_num(scorenum, user_id, 1)
        sql_message.update_gift(user_info['user_id'], 1)  # 更新领取状态
        msg = f'亲爱的道友们，在这国庆佳节之际，庆祝祖国的繁荣富强。在这充满欢庆的日子里，灵梦为各位道友准备了小小礼物，发放{propname}{propnum}个，传承抽卡次数{scorenum}次。祝各位国庆快乐！φ（￣∇￣o）'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '礼包传承抽卡', '礼包传承抽卡', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await get_drawgift.finish()    
    else:
        msg = "真是贪心！您已经领取过该礼品，无法再次领取。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '传承帮助', '传承帮助', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await get_drawgift.finish()

# GM加抽卡
@gm_command_draw.handle(parameterless=[Cooldown(at_sender=False)])
async def gm_command_draw_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg_text = args.extract_plain_text().strip()
    msg_parts = msg_text.split()

    try:
        stone_num_match = msg_parts[0]  # 获取抽卡数量
        give_stone_num = int(stone_num_match) if stone_num_match else 0
        nick_name = msg_parts[1] if len(msg_parts) > 1 else None  # 获取道号（如果有的话）

        if nick_name:
            # 如果提供了道号，给指定用户发放灵石
            give_message = sql_message.get_user_info_with_name(nick_name)
            if give_message:
                xiuxian_impart.update_stone_num(give_stone_num, give_message['user_id'], 1)
                await bot.send_group_msg(group_id=send_group_id, message=f"共赠送{give_stone_num}次抽卡给***{give_message['user_name']}***道友！")
            else:
                await bot.send_group_msg(group_id=send_group_id, message="对方未踏入修仙界，不可赠送！")
        else:
            gift_min_level = 20

            xiuxian_impart.update_impart_stone_all(give_stone_num)
            msg = f"全服通告：赠送所有化灵境初期等级以上的用户{give_stone_num}抽卡次数，请注意查收！"
            await bot.send_group_msg(group_id=send_group_id, message=msg)
    except Exception as e:
        await bot.send_group_msg(group_id=send_group_id, message=f"发生错误: {str(e)}")


@impart_back.handle(parameterless=[Cooldown(at_sender=False)])
async def impart_back_(bot: Bot, event: GroupMessageEvent):
    """传承背包"""
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
        await impart_back.finish()
    user_id = user_info['user_id']
    impart_data_draw = await impart_check(user_id)
    if impart_data_draw is None:
        msg = f"发生未知错误，多次尝试无果请找作者！"
        params_items = [('msg', msg)]               
        buttons = [           
            [(2, '传承抽卡', '传承抽卡', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await impart_back.finish()

    list_tp = []
    img = None
    #思恋结晶：{impart_data_draw['stone_num']}颗
    txt_back = f"""--道友***{user_info['user_name']}***的传承物资--
抽卡次数：{impart_data_draw['wish']}/90次
"""
    txt_tp = f"""--道友***{user_info['user_name']}***的传承总属性--
攻击提升:{int(impart_data_draw['impart_atk_per'] * 100)}%
气血提升:{int(impart_data_draw['impart_hp_per'] * 100)}%
真元提升:{int(impart_data_draw['impart_mp_per'] * 100)}%
会心提升：{int(impart_data_draw['impart_know_per'] * 100)}%
会心伤害提升：{int(impart_data_draw['impart_burst_per'] * 100)}%
闭关经验提升：{int(impart_data_draw['impart_exp_up'] * 100)}%
炼丹收获数量提升：{impart_data_draw['impart_mix_per']}颗
灵田收取数量提升：{impart_data_draw['impart_reap_per']}颗
每日双修次数提升：{impart_data_draw['impart_two_exp']}次
boss战攻击提升:{int(impart_data_draw['boss_atk'] * 100)}%
道友拥有的传承卡片如下:
"""
#累计闭关时间：{impart_data_draw['exp_day']}分钟
    list_tp.append(
        {"type": "node", "data": {"name": f"道友***{user_info['user_name']}***的传承背包", "uin": bot.self_id,
                                  "content": txt_back}})
    list_tp.append(
        {"type": "node", "data": {"name": f"道友***{user_info['user_name']}***的传承背包", "uin": bot.self_id,
                                  "content": txt_tp}})

    img_tp = impart_data_json.data_person_list(user_id)
    
    for x in range(len(img_tp)):
        if XiuConfig().merge_forward_send:
            img = MessageSegment.image(img_path / str(img_tp[x] + ".png"))
        else:
            img = str(img_tp[x])
        list_tp.append(
        {"type": "node", "data": {"name": f"道友***{user_info['user_name']}***的传承背包", "uin": bot.self_id,
                                  "content": f"\n><qqbot-cmd-input text=\"传承卡图 {img}\" show=\"{img}\" reference=\"false\" />"}}
    )
    
    try:
        # 提取每个节点的内容部分并连接成字符串
        msgs = "\n\n".join([item["data"]["content"] for item in list_tp])
        params_items = [('msg', msgs)]
        
        # 初始化按钮列表
        button_list = [
            [(2, '传承卡图', '传承卡图', True), (2, '传承背包', '传承背包', True)],
            [(2, '传承抽卡', '传承抽卡', False)], 
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, button_list)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    except ActionFailed:
        msg = f"获取传承背包数据失败！"
        params_items = [('msg', msg)]               
        buttons = [           
            [(2, '传承抽卡', '传承抽卡', True)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await impart_back.finish()
  #  params_items = [('msg', msg)]               
  #  buttons = [           
  #      [(2, '传承抽卡', '传承抽卡', True), (2, '传承背包', '传承背包', True)],
  #      [(2, '传承卡图', '传承卡图', False)],            
  #  ]
   # 调用 markdown 函数生成数据
  #  data = await markdown(params_items, buttons)
  #  await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))         
  #  await impart_back.finish()


@re_impart_load.handle(parameterless=[Cooldown(at_sender=False)])
async def re_impart_load_(bot: Bot, event: GroupMessageEvent):
    """加载传承数据"""
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
        await re_impart_load.finish()
    user_id = user_info['user_id']
    impart_data_draw = await impart_check(user_id)
    if impart_data_draw is None:
        msg = f"发生未知错误，多次尝试无果请找作者！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await re_impart_load.finish()
    # 更新传承数据
    info = await re_impart_data(user_id)
    if info:
        msg = f"传承数据加载完成！"
    else:
        msg = f"传承数据加载失败！"
    params_items = [('msg', msg)]               
    buttons = [           
        [(2, '传承背包', '传承背包', True)],           
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await re_impart_load.finish()


@impart_info.handle(parameterless=[Cooldown(at_sender=False)])
async def impart_info_(bot: Bot, event: GroupMessageEvent):
    """传承信息"""
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
        await impart_info.finish()
    user_id = user_info['user_id']
    impart_data_draw = await impart_check(user_id)
    if impart_data_draw is None:
        msg = f"发生未知错误，多次尝试无果请找作者！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await impart_info.finish()

    msg = f"""--道友{user_info['user_name']}的传承物资--
抽卡次数：{impart_data_draw['wish']}/90次
    """
    #累计闭关时间：{impart_data_draw['exp_day']}分钟
    params_items = [('msg', msg)]               
    buttons = [           
        [(2, '传承卡图', '传承卡图', False), (2, '传承背包', '传承背包', True)],
        [(2, '传承抽卡', '传承抽卡', False)],            
    ]
   # 调用 markdown 函数生成数据
    data = await markdown(params_items, buttons)
    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    await impart_info.finish()

#思恋结晶：{impart_data_draw['stone_num']}颗

