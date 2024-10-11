import re
import random
import asyncio
import math
from datetime import datetime
from nonebot.typing import T_State
from typing import List, Tuple
from ..xiuxian_utils.lay_out import assign_bot, Cooldown, assign_bot_group
from nonebot import require, on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GROUP_ADMIN,
    GROUP_OWNER,
    GroupMessageEvent,
    MessageSegment,
    ActionFailed
)
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot.params import CommandArg
from ..xiuxian_utils.data_source import jsondata
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, XiuxianJsonDate, OtherSet,
    UserBuffDate, XIUXIAN_IMPART_BUFF, leave_harm_time, get_experience_and_delete_old_data
)
from ..xiuxian_config import XiuConfig, JsonConfig, convert_rank
from ..xiuxian_utils.utils import (
    check_user,
    markdown,
    markdown_s,
    get_old_user_id,
    check_user_type,
    get_msg_pic, number_to,
    CommandObjectID,
    Txt2Img, send_msg_handler
)
from ..xiuxian_utils.item_json import Items
items = Items()

# 定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler
cache_help = {}
cache_level_help = {}
sql_message = XiuxianDateManage()  # sql类
#sql_message_a = XiuxianDateTransfer()
xiuxian_impart = XIUXIAN_IMPART_BUFF()

run_xiuxian = on_fullmatch("我要修仙", priority=8, permission=GROUP, block=True)
restart = on_fullmatch("重入仙途", permission=GROUP, priority=7, block=True)
sign_in = on_fullmatch("修仙签到", priority=13, permission=GROUP, block=True)
help_in = on_fullmatch("修仙帮助", priority=12, permission=GROUP, block=True)
vip_get = on_command("修仙兑换", priority=6, permission=GROUP, block=True)
close_xiuxian = on_fullmatch("修仙开关", priority=12, permission=GROUP, block=True)
helps_in = on_fullmatch("修行帮助", priority=12, permission=GROUP, block=True)
newhelps_in = on_fullmatch("新手攻略", priority=12, permission=GROUP, block=True)
rank = on_command("排行榜", aliases={"修仙排行榜", "sss灵石排行榜", "战力排行榜", "境界排行榜", "宗门排行榜"},
                  priority=7, permission=GROUP, block=True)
remaname = on_command("修改道号", priority=5, permission=GROUP, block=True)
get_gift = on_fullmatch("sss领取修仙礼包", priority=6, permission=GROUP, block=True)
level_up = on_fullmatch("突破", priority=6, permission=GROUP, block=True)
level_up_dr = on_fullmatch("渡厄突破", priority=7, permission=GROUP, block=True)
level_up_drjd = on_command("渡厄金丹突破", aliases={"金丹突破"}, priority=7, permission=GROUP, block=True)
level_up_zj = on_fullmatch("直接突破",  priority=7, permission=GROUP, block=True)
mew_hongbao = on_command("修仙发红包", priority=6, permission=GROUP, block=True)
open_hongbao = on_command("修仙抢红包", priority=6, permission=GROUP, block=True)
give_stone = on_command("送灵石", priority=5, permission=GROUP, block=True)
steal_stone = on_command("ss偷灵石", aliases={"ss飞龙探云手"}, priority=4, permission=GROUP, block=True)
gm_command = on_command("xf神秘力量", permission=SUPERUSER, priority=10, block=True)
gmm_command = on_command("xf轮回力量", permission=SUPERUSER, priority=10, block=True)
cz = on_command('xf创造力量', permission=SUPERUSER, priority=15,block=True)
gm_command_tili = on_command("xf增加体力", permission=SUPERUSER, priority=10, block=True)
refresh_gift = on_command("刷新修仙礼包次数", permission=SUPERUSER, priority=10, block=True)
rob_stone = on_command("打劫", aliases={"拿来吧你"}, priority=5, permission=GROUP, block=True)
restate = on_command("重置状态", permission=SUPERUSER, priority=12, block=True)
set_xiuxian = on_command("那么就启用修仙功能", aliases={'那么就禁用修仙功能'}, permission=GROUP, priority=5, block=True)
user_leveluprate = on_command('我的突破概率', aliases={'突破概率'}, priority=5, permission=GROUP, block=True)
user_stamina = on_command('我的体力', aliases={'修仙体力'}, priority=5, permission=GROUP, block=True)
xiuxian_updata_level = on_fullmatch('修仙适配', priority=15, permission=GROUP, block=True)
xiuxian_uodata_data = on_fullmatch('更新记录', priority=15, permission=GROUP, block=True)
lunhui = on_fullmatch('轮回重修帮助', priority=15, permission=GROUP, block=True)
level_help = on_command('境界列表', priority=15, permission=GROUP,block=True)
level_helps = on_command('灵根列表', priority=15, permission=GROUP,block=True)
level_helpss = on_command('品阶列表', priority=15, permission=GROUP,block=True)

__xiuxian_notes__ = f"""
\n```\n☆------------[修仙菜单]------------☆\n```
#修炼
\n><qqbot-cmd-input text="修炼" show="修炼" reference="false" /> | <qqbot-cmd-input text="修改道号" show="改名" reference="false" /> | <qqbot-cmd-input text="修仙签到" show="签到" reference="false" /> | <qqbot-cmd-input text="闭关" show="闭关" reference="false" /> | <qqbot-cmd-input text="突破" show="突破" reference="false" /> | <qqbot-cmd-input text="我的状态" show="状态" reference="false" /> | <qqbot-cmd-input text="双修 " show="双修 道号" reference="false" /> | <qqbot-cmd-input text="打劫" show="打劫 道号" reference="false" /> | <qqbot-cmd-input text="送灵石" show="送灵石 金额 道号" reference="false" /> | <qqbot-cmd-input text="切磋" show="切磋 道号" reference="false" />
\n#修仙排行榜
\n><qqbot-cmd-input text="修仙排行榜" show="修仙" reference="false" /> | <qqbot-cmd-input text="灵石排行榜" show="灵石" reference="false" /> | <qqbot-cmd-input text="战力排行榜" show="战力" reference="false" /> | <qqbot-cmd-input text="宗门排行榜" show="宗门" reference="false" /> | <qqbot-cmd-input text="境界列表" show="境界" reference="false" /> | <qqbot-cmd-input text="灵根列表" show="灵根" reference="false" /> | <qqbot-cmd-input text="品阶列表" show="品阶" reference="false" /> 
\n#仙界物品
\n><qqbot-cmd-input text="查看修仙界物品功法" show="功法" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品辅修功法" show="辅修功法" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品神通" show="神通" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品丹药" show="丹药" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品合成丹药" show="合成丹药" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品法器" show="法器" reference="false" /> | <qqbot-cmd-input text="查看修仙界物品防具" show="防具" reference="false" /> 
\n#秘境
\n><qqbot-cmd-input text="探索秘境" show="探索秘境" reference="false" /> | <qqbot-cmd-input text="秘境结算" show="秘境结算" reference="false" /> | <qqbot-cmd-input text="终止探索秘境" show="终止探索秘境" reference="false" />
\n#灵庄
\n><qqbot-cmd-input text="灵庄信息" show="灵庄信息" reference="false" /> | <qqbot-cmd-input text="灵庄存灵石" show="存灵石 灵石数" reference="false" /> | <qqbot-cmd-input text="灵庄取灵石" show="取灵石 灵石数" reference="false" /> | <qqbot-cmd-input text="灵庄升级会员" show="灵庄升级" reference="false" /> | <qqbot-cmd-input text="灵庄结算" show="结算利息" reference="false" /> | <qqbot-cmd-input text="送灵石" show="送灵石" reference="false" /> | <qqbot-cmd-input text="修仙发红包" show="修仙发红包" reference="false" />
\n#宗门
\n><qqbot-cmd-input text="宗门帮助" show="宗门帮助" reference="false" /> | <qqbot-cmd-input text="我的宗门" show="我的宗门" reference="false" /> | <qqbot-cmd-input text="宗门列表" show="宗门列表" reference="false" />
\n#坊市交易
\n><qqbot-cmd-input text="坊市帮助" show="坊市帮助" reference="false" /> | <qqbot-cmd-input text="查看坊市" show="查看坊市" reference="false" /> | <qqbot-cmd-input text="仙市集会" show="仙市集会" reference="false" /> | <qqbot-cmd-input text="我的背包" show="我的背包" reference="false" /> | <qqbot-cmd-input text="炼金" show="炼金 物品" reference="false" /> | <qqbot-cmd-input text="赠送修仙道具" show="赠送物品" reference="false" />
\n#悬赏令
\n><qqbot-cmd-input text="悬赏令刷新" show="刷新悬赏" reference="false" /> | <qqbot-cmd-input text="悬赏令终止" show="终止悬赏" reference="false" /> | <qqbot-cmd-input text="悬赏令结算" show="结算悬赏" reference="false" /> | <qqbot-cmd-input text="悬赏令接取" show="悬赏令接取 编号" reference="false" /> 
\n#灵田炼丹
\n><qqbot-cmd-input text="灵田帮助" show="灵田帮助" reference="false" /> | <qqbot-cmd-input text="炼丹帮助" show="炼丹帮助" reference="false" />
\n#除妖Boss
\n><qqbot-cmd-input text="查询妖界boss" show="Boss列表" reference="false" /> | <qqbot-cmd-input text="讨伐妖界boss" show="讨伐妖界boss" reference="false" /> | <qqbot-cmd-input text="妖界商店" show="妖界商店" reference="false" /> | <qqbot-cmd-input text="妖界灵气兑换" show="灵气兑换" reference="false" />
\n#传承卡图
\n><qqbot-cmd-input text="传承抽卡" show="传承抽卡" reference="false" /> | <qqbot-cmd-input text="传承背包" show="传承背包" reference="false" /> | <qqbot-cmd-input text="传承卡图" show="传承卡图" reference="false" />
\n<qqbot-cmd-input text="新手攻略" show="新手攻略" reference="false" /> | <qqbot-cmd-input text="782240197" show="官方Q群" reference="false" /> | <qqbot-cmd-input text="赞助灵梦" show="赞助灵梦" reference="false" /> \n<qqbot-cmd-input text="领取抽卡次数" show="点击领取国庆限定礼包" reference="false" /> 
\n<qqbot-cmd-input text="修仙开关" show="修仙开关" reference="false" />：群管理员开启/关闭修仙功能。
""".strip()

#\n<qqbot-cmd-input text="赞助灵梦" show="赞助灵梦" reference="false" /> 
#\n><qqbot-cmd-input text="查看修仙界物品功法" show="功法" reference="false" />世界BOSS:发送 世界boss帮助 获取 
#\n><qqbot-cmd-input text="查看修仙界物品功法" show="功法" reference="false" />传承系统:发送 传承帮助/虚神界帮助 获取
__xiuxian_helps__ = f"""
#修行帮助：
\n><qqbot-cmd-input text="我要修仙" show="我要修仙" reference="false" />:进入修仙模式
\n><qqbot-cmd-input text="我的修仙信息" show="我的修仙信息" reference="false" />:获取修仙数据
\n><qqbot-cmd-input text="重入仙途" show="重入仙途" reference="false" />:重置灵根数据,每次{XiuConfig().remake}灵石
\n><qqbot-cmd-input text="修改道号" show="修改道号" reference="false" />:修改你的道号,首次修改无法费用，以后每次20万灵石。
\n><qqbot-cmd-input text="突破" show="突破" reference="false" />:修为足够后,可突破境界（一定几率失败）
\n><qqbot-cmd-input text="闭关" show="闭关" reference="false" />：闭关增加修为
\n><qqbot-cmd-input text="修仙排行榜" show="排行榜" reference="false" />:修仙排行榜,灵石排行榜,战力排行榜,宗门排行榜
\n><qqbot-cmd-input text="我的状态" show="我的状态" reference="false" />:查看当前HP,我的功法：查看当前技能
\n><qqbot-cmd-input text="宗门帮助" show="宗门系统" reference="false" />:发送 宗门帮助 获取
\n><qqbot-cmd-input text="灵庄帮助" show="灵庄系统" reference="false" />:发送 灵庄帮助 获取
\n><qqbot-cmd-input text="灵田帮助" show="灵田帮助" reference="false" />：发送 灵田帮助 查看
\n><qqbot-cmd-input text="坊市帮助" show="背包坊市" reference="false" />：发送 坊市帮助 获取
\n><qqbot-cmd-input text="秘境帮助" show="秘境系统" reference="false" />:发送 秘境帮助 获取
\n><qqbot-cmd-input text="炼丹帮助" show="炼丹帮助" reference="false" />:炼丹功能
\n><qqbot-cmd-input text="轮回重修帮助" show="轮回重修" reference="false" />:发送 轮回重修帮助 获取
\n><qqbot-cmd-input text="合成" show="仙器合成" reference="false" />:发送 合成xx 获取，目前开放合成的仙器为天罪
\n<qqbot-cmd-input text="仙途奇缘帮助" show="仙途奇缘" reference="false" />:新手福利，领取灵石 
\n<qqbot-cmd-input text="修仙签到" show="修仙签到" reference="false" />:每日获取灵石
""".strip()

__newxiuxian_helps__ = f"""
#新人攻略：
初入修仙可以每天<qqbot-cmd-input text="修仙签到" show="修仙签到" reference="false" />  <qqbot-cmd-input text="仙途奇缘" show="仙途奇缘" reference="false" />领取灵石 
加入心仪的宗门后，
可以学习宗门功法和神通
领丹药（渡厄丹是必需品）
领丹药最低职位是内门弟子
每日必做：<qqbot-cmd-input text="宗门帮助" show="宗门任务" reference="false" />，<qqbot-cmd-input text="悬赏令帮助" show="悬赏令" reference="false" />，<qqbot-cmd-input text="双修" show="双修" reference="false" />，<qqbot-cmd-input text="秘境帮助" show="秘境" reference="false" />。
重入仙途为刷灵根，新人最好不要刷。器师修炼无修为增长。
""".strip()

__close_xiuxian__ = f"""
可能有的群觉得修仙很刷屏，群管理员可以在本群设置开启/关闭修仙功能。
如无反应可能需要升级QQ客户端至最新版。
""".strip()


__xiuxian_updata_data__ = f"""
详情：
#更新2024.8.18
1.修仙上线了
""".strip()

__level_help__ = f"""
                       --境界列表--
           祭道境——仙帝境——准帝境——仙王境
           真仙境——至尊境——遁一境——斩我境
           虚道境——天神境——圣祭境——真一境
           神火境——尊者境——列阵境——铭纹境
           化灵境——洞天境——搬血境——江湖人
""".strip()

__level_helps__ = f"""
                       --灵根列表--
               轮回——异界——机械——混沌
           融——超——龙——天——异——真——伪
""".strip()

__level_helpss__ = f"""
                       --功法品阶--
                           无上
                         仙阶极品
                   仙阶上品——仙阶下品
                   天阶上品——天阶下品
                   地阶上品——地阶下品
                   玄阶上品——玄阶下品
                   黄阶上品——黄阶下品
                   人阶上品——人阶下品
                       --法器品阶--
                           无上
                         极品仙器
                   上品仙器——下品仙器
                   上品通天——下品通天
                   上品纯阳——下品纯阳
                   上品法器——下品法器
                   上品符器——下品符器
""".strip()

class PM_HONGBAO:
    def __init__(self):
        self.hb_score = {}
        self.hb_use_score = {}
        self.hb_num = {}
        self.hb_use_num = {}
        self.hb_open_user = {}

    def insert_hongbao(self, kouling, score, num):
        self.hb_score[kouling] = score
        self.hb_num[kouling] = num
        self.hb_open_user[kouling] = []

    def open_hongbao(self, kouling, use_score, openuser):
        self.hb_use_score[kouling] = self.hb_use_score.get(kouling, 0) + use_score
        self.hb_use_num[kouling] = self.hb_use_num.get(kouling, 0) + 1
        self.hb_open_user[kouling].append(openuser)
    
    def get_hongbao(self, kouling):
        score = self.hb_score[kouling] if self.hb_score.get(kouling) is not None else 0
        use_score = self.hb_use_score[kouling] if self.hb_use_score.get(kouling) is not None else 0
        num = self.hb_num[kouling] if self.hb_num.get(kouling) is not None else 0
        use_num = self.hb_use_num[kouling] if self.hb_use_num.get(kouling) is not None else 0
        openuser = self.hb_open_user[kouling] if self.hb_open_user.get(kouling) is not None else []
        return score,use_score,num,use_num,openuser
    
    def hongbao_off(self, kouling):
        self.hb_score[kouling] = 0
        self.hb_use_score[kouling] = 0
        self.hb_use_num[kouling] = 0
        self.hb_num[kouling] = 0
        self.hb_open_user[kouling] = []
    
pmhongbao = PM_HONGBAO()

# 重置每日签到
@scheduler.scheduled_job("cron", hour=0, minute=0)
async def xiuxian_sing_():
    sql_message.sign_remake()
    logger.opt(colors=True).info(f"<green>每日修仙签到重置成功！</green>")




@xiuxian_uodata_data.handle(parameterless=[Cooldown(at_sender=False)])
async def mix_elixir_help_(bot: Bot, event: GroupMessageEvent):
    """更新记录"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg = __xiuxian_updata_data__
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await xiuxian_uodata_data.finish()


@run_xiuxian.handle(parameterless=[Cooldown(at_sender=False)])
async def run_xiuxian_(bot: Bot, event: GroupMessageEvent):
    """加入修仙"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    user_id = event.get_user_id()
    user_name = user_id
    root, root_type = XiuxianJsonDate().linggen_get()  # 获取灵根，灵根类型
    rate = sql_message.get_root_rate(root_type)  # 灵根倍率
    power = 100 * float(rate)  # 战力=境界的power字段 * 灵根的rate字段
    create_time = str(datetime.now())
    is_new_user, msg = sql_message.create_user(
        user_id, root, root_type, int(power), create_time, user_name
    )
  #  expp = sql_message_a(experience, user_id)
  #  sql_message.update_ls(user_id, expp, 1)
  #  msg_1 = "你获得了{expp}灵石"
  #  msg = msg + msg_1
    try:
        if is_new_user:
            old_user_id = await get_old_user_id(user_id)
            if old_user_id:
        # 查询旧数据库并删除数据
                experience = get_experience_and_delete_old_data(old_user_id)

                # 将 experience 转换为灵石
                stones = experience * 50
                if stones > 0:
                    msg_1 = f"\n✨道友原有境界非凡，凭借累积的深厚修为，成功转化获得{stones}枚灵石，助您攀登更高的修真境界！✨"
                    msg = msg + msg_1
                # 更新新数据库中的灵石数量
                    sql_message.update_ls(user_id, stones, 1)
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '修炼', '修炼', True), (2, '闭关', '闭关', True)],
                [(2, '修改道号', '修改道号', False)] 
            ]
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            
            isUser, user_msg, msg = check_user(event)
            if user_msg['hp'] is None or user_msg['hp'] == 0 or user_msg['hp'] == 0:
                sql_message.update_user_hp(user_id)
            await asyncio.sleep(1)
            msg = "耳边响起一个神秘人的声音：不要忘记仙途奇缘！!\n不知道怎么玩的话可以发送 修仙帮助 喔！！"
            params_items = [('msg', msg)]               
            buttons = [                
                [(2, '仙途奇缘', '仙途奇缘', True), (2, '修仙帮助', '修仙帮助', True)] 
            ]
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))            
        else:
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '修炼', '修炼', True), (2, '闭关', '闭关', True)],
                [(2, '修改道号', '修改道号', False)]  
            ]
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))   
    except ActionFailed:
        await run_xiuxian.finish("修仙界网络堵塞，发送失败!", reply_message=True)


@sign_in.handle(parameterless=[Cooldown(at_sender=False)])
async def sign_in_(bot: Bot, event: GroupMessageEvent):
    """修仙签到"""
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
        await sign_in.finish()
    user_id = user_info['user_id']
    result = sql_message.get_sign(user_id)
    msg = result
    buttons = [[(2, '✅修仙签到', '修仙签到', True)]]    
    params_items = [('msg', msg)]
    data = await markdown(params_items, buttons)
    try:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await sign_in.finish()
    except ActionFailed:
        await sign_in.finish("修仙界网络堵塞，发送失败!", reply_message=True)


@help_in.handle(parameterless=[Cooldown(at_sender=False)])
async def help_in_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """修仙帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await help_in.finish()
    else:
        font_size = 32
        title = "修仙菜单"
        msg = __xiuxian_notes__
        buttons = [
            [(2, '✅修行', '修行帮助', True), (2, '✅秘境', '秘境帮助', True)],
            [(2, '✅灵庄', '灵庄帮助', True), (2, '✅炼丹', '炼丹帮助', True)],
            [(2, '✅宗门', '宗门帮助', True), (2, '✅坊市', '坊市帮助', True)],
            [(2, '✅悬赏', '悬赏令帮助', True), (2, '✅灵田', '灵田帮助', True)],
            [(2, '✅除妖', '妖界boss帮助', True), (2, '✅传承', '传承帮助', True)]
        ]
        
        params_items = [('msg', msg)]
        
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))      
        await help_in.finish()


@helps_in.handle(parameterless=[Cooldown(at_sender=False)])
async def helps_in_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """修行帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await help_in.finish()
    else:
        font_size = 32
        title = "修行菜单"
        msg = __xiuxian_helps__
        buttons = [
            [(2, '✅修行', '修行帮助', True), (2, '✅秘境', '秘境帮助', True)],
            [(2, '✅灵庄', '灵庄帮助', True), (2, '✅炼丹', '炼丹帮助', True)],
            [(2, '✅宗门', '宗门帮助', True), (2, '✅交易', '交易帮助', True)],
            [(2, '✅悬赏', '悬赏帮助', True), (2, '✅功法', '灵田帮助', True)],
            [(2, '✅除妖', '妖界boss帮助', True), (2, '✅传承', '传承帮助', True)]
        ]
        
        params_items = [('msg', msg)]
        
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))       
        await help_in.finish()

@newhelps_in.handle(parameterless=[Cooldown(at_sender=False)])
async def helps_in_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """修行帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await help_in.finish()
    else:
        font_size = 32
        title = "新人攻略"
        msg = __newxiuxian_helps__
        buttons = [
            [(2, '修仙签到', '修仙签到', True), (2, '仙途奇缘', '仙途奇缘', True)],
            [(2, '重入仙途', '重入仙途', True)],
        ]
        
        params_items = [('msg', msg)]
        
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))       
        await help_in.finish()

@close_xiuxian.handle(parameterless=[Cooldown(at_sender=False)])
async def close_xiuxian_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """修仙开关"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
        await help_in.finish()
    else:
        font_size = 32
        title = "修行菜单"
        msg = __close_xiuxian__
        params_items = [('msg', msg)]               
        buttons = [
            [(1, '启用修仙', '那么就启用修仙功能 ', True), (1, '禁用修仙', '那么就禁用修仙功能 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown_s(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))        
        await close_xiuxian.finish()

@level_help.handle(parameterless=[Cooldown(at_sender=False)])
async def level_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """境界帮助"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_level_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_level_help[session_id]))
        await level_help.finish()
    else:
        font_size = 32
        title = "境界帮助"
        msg = __level_help__
        buttons = [
            [(2, '✅灵根列表', '灵根列表', True), (2, '✅品阶列表', '品阶列表', True)],
            [(2, '✅境界列表', '境界列表', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)        
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_help.finish()

@level_helps.handle(parameterless=[Cooldown(at_sender=False)])
async def level_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """灵根列表"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_level_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_level_help[session_id]))
        await level_help.finish()
    else:
        font_size = 32
        title = "灵根列表"
        msg = __level_helps__
        buttons = [
            [(2, '✅灵根列表', '灵根列表', True), (2, '✅品阶列表', '品阶列表', True)],
            [(2, '✅境界列表', '境界列表', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)        
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_helps.finish()

@level_helpss.handle(parameterless=[Cooldown(at_sender=False)])
async def level_help_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
    """品阶列表"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    if session_id in cache_level_help:
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_level_help[session_id]))
        await level_help.finish()
    else:
        font_size = 32
        title = "品阶列表"
        msg = __level_helpss__
        buttons = [
            [(2, '✅灵根列表', '灵根列表', True), (2, '✅品阶列表', '品阶列表', True)],
            [(2, '✅境界列表', '境界列表', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)        
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_helpss.finish()

@restart.handle(parameterless=[Cooldown(at_sender=False)])
async def restart_(bot: Bot, event: GroupMessageEvent, state: T_State):
    """刷新灵根信息"""
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
        await restart.finish()

    if user_info['stone'] < XiuConfig().remake:
        msg = "你的灵石还不够呢，快去赚点灵石吧！"
        params_items = [('msg', msg)]               
        buttons = [            
            [(2, '重入仙途', '重入仙途', False)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await restart.finish()

    state["user_id"] = user_info['user_id']  # 将用户信息存储在状态中

    linggen_options = []
    for _ in range(10):
        name, root_type = XiuxianJsonDate().linggen_get()
        linggen_options.append((name, root_type))

    selected_name, selected_root_type = random.choice(linggen_options)
  #  msg = f"你随机获得的灵根是: {selected_name} ({selected_root_type})\n"

    # 更新用户的灵根信息
    msg = sql_message.ramaker(selected_name, selected_root_type, user_info['user_id'])

    try:
        params_items = [('msg', msg)]               
        buttons = [            
            [(2, '重入仙途', '重入仙途', False)],
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
    except ActionFailed:
        await bot.send_group_msg(group_id=event.group_id, message="修仙界网络堵塞，发送失败!")
    await restart.finish()


@rank.handle(parameterless=[Cooldown(at_sender=False)])
async def rank_(bot: Bot, event: GroupMessageEvent):
    """排行榜"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    message = str(event.message)
    rank_msg = r'[\u4e00-\u9fa5]+'
    message = re.findall(rank_msg, message)
    if message:
        message = message[0]
    if message in ["排行榜", "修仙排行榜", "境界排行榜", "修为排行榜"]:
        p_rank = sql_message.realm_top()
        msg = f"✨位面境界排行榜TOP50✨\n"
        num = 0
        for i in p_rank:
            num += 1
            msg += f"\n>第{num}位  <qqbot-cmd-input text=\"切磋 {i[0]}\" show=\"{i[0]}\" reference=\"false\" />  {i[1]}, 修为{number_to(i[2])}\n"
        buttons = [
            [(2, '✅境界排行榜', '境界排行榜', True), (2, '✅灵石排行榜', '灵石排行榜', True)],
            [(2, '✅战力排行榜', '战力排行榜', True), (2, '✅宗门排行榜', '宗门排行榜', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)        
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await rank.finish()
    elif message == "灵石排行榜":
        a_rank = sql_message.stone_top()
        msg = f"✨位面灵石排行榜TOP50✨\n"
        num = 0
        for i in a_rank:
            num += 1
            msg += f"\n>第{num}位   <qqbot-cmd-input text=\"切磋 {i[0]}\" show=\"{i[0]}\" reference=\"false\" />   灵石：{number_to(i[1])}枚\n"
        buttons = [
            [(2, '✅境界排行榜', '境界排行榜', True), (2, '✅灵石排行榜', '灵石排行榜', True)],
            [(2, '✅战力排行榜', '战力排行榜', True), (2, '✅宗门排行榜', '宗门排行榜', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)        
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await rank.finish()
    elif message == "战力排行榜":
        c_rank = sql_message.power_top()
        msg = f"✨位面战力排行榜TOP50✨\n"
        num = 0
        for i in c_rank:
            num += 1
            msg += f"\n>第{num}位   <qqbot-cmd-input text=\"切磋 {i[0]}\" show=\"{i[0]}\" reference=\"false\" />   战力：{number_to(i[1])}\n"
        buttons = [
            [(2, '✅境界排行榜', '境界排行榜', True), (2, '✅灵石排行榜', '灵石排行榜', True)],
            [(2, '✅战力排行榜', '战力排行榜', True), (2, '✅宗门排行榜', '宗门排行榜', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)        
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await rank.finish()
    elif message in ["宗门排行榜", "宗门建设度排行榜"]:
        s_rank = sql_message.scale_top()
        msg = f"✨位面宗门建设排行榜TOP50✨\n"
        num = 0
        for i in s_rank:
            num += 1
            msg += f"\n>第{num}位   <qqbot-cmd-input text=\"加入宗门 {i[1]}\" show=\"{i[1]}\" reference=\"false\" />   建设度：{number_to(i[2])}\n"
            if num == 50:
                break
        buttons = [
            [(2, '✅境界排行榜', '境界排行榜', True), (2, '✅灵石排行榜', '灵石排行榜', True)],
            [(2, '✅战力排行榜', '战力排行榜', True), (2, '✅宗门排行榜', '宗门排行榜', True)],
        ]        
        params_items = [('msg', msg)]       
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)        
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await rank.finish()


@remaname.handle(parameterless=[Cooldown(at_sender=False)])
async def remaname_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """修改道号"""
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
        await remaname.finish()
    user_id = user_info['user_id']
    username = user_info['user_name'] 
    user_name = args.extract_plain_text().strip()
    len_username = len(user_name.encode('gbk'))

    blocked_words = ["涉及国家机密", "共产党", "xjp", "习近平", "中共", "独立", "李德胜", "毛泽东", "江泽民", "蛤", "熊"]  # 在这里添加你需要的屏蔽词

    # 检查道号是否包含屏蔽词
    if any(bad_word in user_name for bad_word in blocked_words):
        msg = "道友的道号有位仙道，请重新修改！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '✅修改道号', '修改道号', False)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await remaname.finish()

    # 正则表达式限制
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9]+$', user_name):
        msg = "道友的道号有违仙道，请重新修改！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '✅修改道号', '修改道号', False)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await remaname.finish()
        
    if len_username > 20:
        msg = f"修行之路，道号宜简不宜繁，请<qqbot-cmd-input text=\"修改道号\" show=\"缩短您的道号\" reference=\"false\" />后再行尝试，以映修仙初心！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '✅修改道号', '修改道号', False)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await remaname.finish()
    elif len_username < 1:
        msg = f"道友确定要改名无名？还请三思。"        
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '✅修改道号', '修改道号', False)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await remaname.finish()
    
    if not username or username == str(user_id):
        # 更新用户名
        msg = sql_message.update_user_name(user_id, user_name)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '✅修改道号', '修改道号', False), (2, '✅我的状态', '我的状态', True)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await remaname.finish()        

    else:   # 获取用户灵石数量
        user_stones = user_info['stone']
        
        if user_stones < 200000:
            msg = f"修改道号所需灵石：200000，道友<qqbot-cmd-input text=\"我的灵石\" show=\"灵石\" reference=\"false\" />不足，暂时无法修改。"
            params_items = [('msg', msg)]
            buttons = [
                [(2, '✅修改道号', '修改道号', False)],
            ]
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await remaname.finish()
        else:
            # 扣除 20 万灵石
            sql_message.update_ls(user_id, 200000, 2)     
            msg = sql_message.update_user_name(user_id, user_name)
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '✅修改道号', '修改道号', False), (2, '✅我的状态', '我的状态', True)],
            ]
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await remaname.finish()


@level_up.handle(parameterless=[Cooldown(at_sender=False)])
async def level_up_(bot: Bot, event: GroupMessageEvent):
    """突破"""
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
        await level_up.finish()
    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    user_leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    level_cd = user_msg['level_up_cd']
    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
           # sql_message.update_user_stamina(user_id, 5, 1)
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await level_up.finish()
    else:
        pass

    level_name = user_msg['level']  # 用户境界
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    items = Items()
    pause_flag = False
    elixir_name = None
    elixir_desc = None
    if user_backs is not None:
        for back in user_backs:
            if int(back['goods_id']) == 1999:  # 检测到有对应丹药
                pause_flag = True
                elixir_name = back['goods_name']
                elixir_desc = items.get_data_by_item_id(1999)['desc']
                break
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破概率提升，别忘了还有渡厄突破
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    if pause_flag:
        msg = f"由于检测到背包有丹药：{elixir_name}，效果：{elixir_desc}，突破已经准备就绪\n请发送 ，<qqbot-cmd-input text=\"渡厄突破\" show=\"渡厄突破\" reference=\"false\" /> 或 <qqbot-cmd-input text=\"直接突破\" show=\"直接突破\" reference=\"false\" />来选择是否使用丹药突破！\n本次突破概率为：{level_rate + user_leveluprate + number}% "
        params_items = [('msg', msg)]               
        buttons = [[(2, '渡厄突破', '渡厄突破', True), (2, '直接突破', '直接突破', True)]]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        if XiuConfig().img:
            pic = await img.save(title, msg)
            cache_help[session_id] = pic
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_up.finish()
    else:
        msg = f"由于检测到背包没有【渡厄丹】，突破已经准备就绪\n请发送，<qqbot-cmd-input text=\"直接突破\" show=\"直接突破\" reference=\"false\" />来突破！请注意，本次突破失败将会损失部分修为！\n本次突破概率为：{level_rate + user_leveluprate + number}% "
        params_items = [('msg', msg)]               
        buttons = [[(2, '直接突破', '直接突破', True), (2, '修炼', '修炼', True)]]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons) 
        if XiuConfig().img:
            pic = await img.save(title, msg)
            cache_help[session_id] = pic
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_up.finish()


@level_up_zj.handle(parameterless=[Cooldown(at_sender=False)])
async def level_up_zj_(bot: Bot, event: GroupMessageEvent):
    """直接突破"""
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
        await level_up_zj.finish()
    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    level_cd = user_msg['level_up_cd']
    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
          #  sql_message.update_user_stamina(user_id, 6, 1)
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '修炼', '修炼', True), (2, '闭关', '闭关', True)]
            ]
            # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            if XiuConfig().img:
                pic = await img.save(title, msg)
                cache_help[session_id] = pic
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await level_up_zj.finish()
    else:
        pass
    level_name = user_msg['level']  # 用户境界
    exp = user_msg['exp']  # 用户修为
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破概率提升，别忘了还有渡厄突破
    main_exp_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破扣修为减少
    exp_buff = main_exp_buff['exp_buff'] if main_exp_buff is not None else 0
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    le = OtherSet().get_type(exp, level_rate + leveluprate + number, level_name)
    if isinstance(le, str) and "修为不足以突破" in le:
        params_items = [('msg', le)]
        buttons = [
            [(2, '修炼', '修炼', True), (2, '闭关', '闭关', True)],
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_up_zj.finish()    
    if le == "失败":
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        # 失败惩罚，随机扣减修为
        percentage = random.randint(
            XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit
        )
        now_exp = int(int(exp) * ((percentage / 100) * (1 - exp_buff))) #功法突破扣修为减少
        sql_message.update_j_exp(user_id, now_exp)  # 更新用户修为
        nowhp = user_msg['hp'] - (now_exp / 2) if (user_msg['hp'] - (now_exp / 2)) > 0 else 1
        nowmp = user_msg['mp'] - now_exp if (user_msg['mp'] - now_exp) > 0 else 1
        sql_message.update_user_hp_mp(user_id, nowhp, nowmp)  # 修为掉了，血量、真元也要掉
        update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
            level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
        sql_message.update_levelrate(user_id, leveluprate + update_rate)
        msg = f"道友突破失败,境界受损,修为减少{now_exp}，下次突破成功率增加{update_rate}%，道友不要放弃！请继续<qqbot-cmd-input text=\"修炼\" show=\"修炼\" reference=\"false\" />后再来突破。"
        params_items = [('msg', msg)]               
        buttons = []
        data = await markdown(params_items, buttons)
        if XiuConfig().img:
            pic = await img.save(title, msg)
            cache_help[session_id] = pic
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_up_zj.finish()

    elif type(le) == list:
        # 突破成功
        sql_message.updata_level(user_id, le[0])  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        msg = f"恭喜道友突破{le[0]}成功！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修炼', '修炼', True), (2, '闭关', '闭关', True)],
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        if XiuConfig().img:
            pic = await img.save(title, msg)
            cache_help[session_id] = pic
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_up_zj.finish()
    else:
        # 最高境界
        msg = le
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await level_up_zj.finish()


@level_up_drjd.handle(parameterless=[Cooldown(at_sender=False)])
async def level_up_drjd_(bot: Bot, event: GroupMessageEvent):
    """渡厄 金丹 突破"""
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
        await level_up_drjd.finish()
    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    level_cd = user_msg['level_up_cd']
    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
         #   sql_message.update_user_stamina(user_id, 4, 1)
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '修炼', '修炼', True)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await level_up_drjd.finish()
    else:
        pass
    elixir_name = "渡厄金丹"
    level_name = user_msg['level']  # 用户境界
    exp = user_msg['exp']  # 用户修为
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    user_leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破概率提升
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    le = OtherSet().get_type(exp, level_rate + user_leveluprate + number, level_name)
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    pause_flag = False
    if user_backs is not None:
        for back in user_backs:
            if int(back['goods_id']) == 1998:  # 检测到有对应丹药
                pause_flag = True
                elixir_name = back['goods_name']
                break

    if not pause_flag:
        msg = f"道友突破需要使用{elixir_name}，但您的背包中没有该丹药！"
       # sql_message.update_user_stamina(user_id, 4, 1)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '直接突破', '直接突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_drjd.finish()

    if isinstance(le, str) and "修为不足以突破" in le:
        params_items = [('msg', le)]
        buttons = [
            [(2, '修炼', '修炼', True), (2, '闭关', '闭关', True)],           
        ]
        data = await markdown(params_items, buttons)
        if XiuConfig().img:
            pic = await img.save(title, le)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await level_up_zj.finish()  

    if le == "失败":
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        if pause_flag:
            # 使用丹药减少的sql
            sql_message.update_back_j(user_id, 1998, use_key=1)
            now_exp = int(int(exp) * 0.1)
            sql_message.update_exp(user_id, now_exp)  # 渡厄金丹增加用户修为
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"道友突破失败，但是使用了丹药{elixir_name}，本次突破失败不扣除修为反而增加了一成，下次突破成功率增加{update_rate}%！！"
        else:
            # 失败惩罚，随机扣减修为
            percentage = random.randint(
                XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit
            )
            main_exp_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破扣修为减少
            exp_buff = main_exp_buff['exp_buff'] if main_exp_buff is not None else 0
            now_exp = int(int(exp) * ((percentage / 100) * exp_buff))
            sql_message.update_j_exp(user_id, now_exp)  # 更新用户修为
            nowhp = user_msg['hp'] - (now_exp / 2) if (user_msg['hp'] - (now_exp / 2)) > 0 else 1
            nowmp = user_msg['mp'] - now_exp if (user_msg['mp'] - now_exp) > 0 else 1
            sql_message.update_user_hp_mp(user_id, nowhp, nowmp)  # 修为掉了，血量、真元也要掉
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"没有检测到{elixir_name}，道友突破失败,境界受损,修为减少{now_exp}，下次突破成功率增加{update_rate}%，道友不要放弃！请继续<qqbot-cmd-input text=\"修炼\" show=\"修炼\" reference=\"false\" />后再来突破。"
        params_items = [('msg', msg)]               
        buttons = []
        data = await markdown(params_items, buttons)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '渡厄金丹突破', '渡厄金丹突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_drjd.finish()

    elif type(le) == list:
        # 突破成功
        sql_message.updata_level(user_id, le[0])  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        now_exp = min(int(int(exp) * 0.1), 50000000) 
        sql_message.update_exp(user_id, now_exp)  # 渡厄金丹增加用户修为
        msg = f"恭喜道友突破{le[0]}成功，因为使用了渡厄金丹，修为也增加了{now_exp}！！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '渡厄金丹突破', '渡厄金丹突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_drjd.finish()
    else:
        # 最高境界
        msg = le
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '渡厄金丹突破', '渡厄金丹突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_drjd.finish()


@level_up_dr.handle(parameterless=[Cooldown(at_sender=False)])
async def level_up_dr_(bot: Bot, event: GroupMessageEvent):
    """渡厄 突破"""
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
        await level_up_dr.finish()
    user_id = user_info['user_id']
    if user_info['hp'] is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    level_cd = user_msg['level_up_cd']
    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = f"目前无法突破，还需要{XiuConfig().level_up_cd - (cd // 60)}分钟"
          #  sql_message.update_user_stamina(user_id, 8, 1)
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '修炼', '修炼', True)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await level_up_dr.finish()
    else:
        pass
    elixir_name = "渡厄丹"
    level_name = user_msg['level']  # 用户境界
    exp = user_msg['exp']  # 用户修为
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    user_leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破概率提升
    number = main_rate_buff['number'] if main_rate_buff is not None else 0
    le = OtherSet().get_type(exp, level_rate + user_leveluprate + number, level_name)
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    pause_flag = False
    if user_backs is not None:
        for back in user_backs:
            if int(back['goods_id']) == 1999:  # 检测到有对应丹药
                pause_flag = True
                elixir_name = back['goods_name']
                break
    
    if not pause_flag:
        msg = f"道友突破需要使用{elixir_name}，但您的背包中没有该丹药！"
      #  sql_message.update_user_stamina(user_id, 8, 1)
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '直接突破', '直接突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_dr.finish()

    if le == "失败":
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        if pause_flag:
            # todu，丹药减少的sql
            sql_message.update_back_j(user_id, 1999, use_key=1)
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"道友突破失败，但是使用了丹药{elixir_name}，本次突破失败不扣除修为下次突破成功率增加{update_rate}%，道友不要放弃！"
        else:
            # 失败惩罚，随机扣减修为
            percentage = random.randint(
                XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit
            )
            main_exp_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破扣修为减少
            exp_buff = main_exp_buff['exp_buff'] if main_exp_buff is not None else 0
            now_exp = int(int(exp) * ((percentage / 100) * (1 - exp_buff)))
            sql_message.update_j_exp(user_id, now_exp)  # 更新用户修为
            nowhp = user_msg['hp'] - (now_exp / 2) if (user_msg['hp'] - (now_exp / 2)) > 0 else 1
            nowmp = user_msg['mp'] - now_exp if (user_msg['mp'] - now_exp) > 0 else 1
            sql_message.update_user_hp_mp(user_id, nowhp, nowmp)  # 修为掉了，血量、真元也要掉
            update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
                level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
            sql_message.update_levelrate(user_id, user_leveluprate + update_rate)
            msg = f"没有检测到{elixir_name}，道友突破失败,境界受损,修为减少{now_exp}，下次突破成功率增加{update_rate}%，道友不要放弃！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '渡厄突破', '渡厄突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_dr.finish()

    elif type(le) == list:
        # 突破成功
        sql_message.updata_level(user_id, le[0])  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        msg = f"恭喜道友突破{le[0]}成功"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '渡厄突破', '渡厄突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_dr.finish()
    else:
        # 最高境界
        msg = le
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '渡厄突破', '渡厄突破', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await level_up_dr.finish()
        

@user_leveluprate.handle(parameterless=[Cooldown(at_sender=False)])
async def user_leveluprate_(bot: Bot, event: GroupMessageEvent):
    """我的突破概率"""
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
        await user_leveluprate.finish()
    user_id = user_info['user_id']
    user_msg = sql_message.get_user_info_with_id(user_id)  # 用户信息
    leveluprate = int(user_msg['level_up_rate'])  # 用户失败次数加成
    level_name = user_msg['level']  # 用户境界
    level_rate = jsondata.level_rate_data()[level_name]  # 
    main_rate_buff = UserBuffDate(user_id).get_user_main_buff_data()#功法突破概率提升
    number =  main_rate_buff['number'] if main_rate_buff is not None else 0
    msg = f"道友下一次突破成功概率为{level_rate + leveluprate + number}%"
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await user_leveluprate.finish()


@user_stamina.handle(parameterless=[Cooldown(at_sender=False)])
async def user_stamina_(bot: Bot, event: GroupMessageEvent):
    """我的体力信息"""
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
        await user_stamina.finish()
    msg = f"当前体力：{user_info['user_stamina']}"
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await user_stamina.finish()


@give_stone.handle(parameterless=[Cooldown(at_sender=False)])
async def give_stone_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """送灵石"""
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
        await give_stone.finish()
    user_id = user_info['user_id']
    user_stone_num = user_info['stone']
    give_qq = None  # 艾特的时候存到这里
    msg_text = args.extract_plain_text().strip()
    msg_parts = msg_text.split()

    try:
        stone_num_match = msg_parts[0]  # 获取灵石数量
        stone_num = int(stone_num_match) if stone_num_match else 0
        nick_name = msg_parts[1] if len(msg_parts) > 1 else None  # 获取道号（如果有的话）
        if stone_num <= 0:
            raise ValueError("灵石数量必须为正数")

    except (ValueError, IndexError) as e:  # 捕获异常并处理
        msg = f"请输入正确的灵石数量！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '送灵石', '送灵石', False)],            
        ]
        # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await give_stone.finish()
    give_stone_num = stone_num
    if int(give_stone_num) > int(user_stone_num):
        msg = f"道友的灵石不够，请重新输入！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '送灵石', '送灵石', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await give_stone.finish()

    if nick_name:
        give_message = sql_message.get_user_info_with_name(nick_name)
        if give_message:
            if give_message['user_name'] == user_info['user_name']:
                msg = f"请不要送灵石给自己！"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '送灵石', '送灵石', False)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await give_stone.finish()
            else:
                sql_message.update_ls(user_id, give_stone_num, 2)  # 减少用户灵石
                give_stone_num2 = int(give_stone_num) * 0.2
                num = int(give_stone_num) - int(give_stone_num2)
                sql_message.update_ls(give_message['user_id'], num, 1)  # 增加用户灵石
                msg = f"道友***{user_info['user_name']}***共赠送{number_to(int(give_stone_num))}枚灵石给{give_message['user_name']}道友！收取手续费{int(give_stone_num2)}枚"
                params_items = [('msg', msg)]               
                buttons = [
                    [(2, '送灵石', '送灵石', False)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
                await give_stone.finish()
        else:
            msg = f"对方未踏入修仙界，不可赠送！"
            params_items = [('msg', msg)]               
            buttons = [
                [(2, '送灵石', '送灵石', False)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
            await give_stone.finish()

    else:
        msg = f"未获到对方信息，请输入正确的道号！"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '送灵石', '送灵石', False)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await give_stone.finish()


# 偷灵石
@steal_stone.handle(parameterless=[Cooldown(stamina_cost=10, at_sender=False)])
async def steal_stone_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
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
        await steal_stone.finish()

    user_id = user_info['user_id']
    steal_user = None
    steal_user_stone = None
    user_stone_num = user_info['stone']
    steal_qq = None  # 存储要偷的人的名字
    coststone_num = XiuConfig().tou
    
    if int(coststone_num) > int(user_stone_num):
        msg = f"道友的偷窃准备(灵石)不足，请打工之后再切格瓦拉！"
        sql_message.update_user_stamina(user_id, 10, 1)
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await steal_stone.finish()

    # 尝试从消息中获取目标名字或ID
    for arg in args:
        if arg.type in ["text", "at"]:
            steal_qq = arg.data.get('text', '').strip()
            break

    if not steal_qq:
        msg = f"对方未踏入修仙界，不要对杂修出手！"
        params_items = [('msg', msg)]               
        buttons = [
            [(1, '启用修仙', '那么就启用修仙功能 ', True), (1, '禁用修仙', '那么就禁用修仙功能 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await steal_stone.finish()

    if steal_qq:
        if steal_qq == user_info['user_name']:
            msg = f"请不要偷自己刷成就！"
            sql_message.update_user_stamina(user_id, 10, 1)
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await steal_stone.finish()
        else:
    # 根据名字或ID查找用户
            steal_user = sql_message.get_user_info_with_name(steal_qq) 
            if steal_user:
                steal_user_stone = steal_user['stone']

                steal_success = random.randint(0, 100)
                result = OtherSet().get_power_rate(user_info['power'], steal_user['power'])
                if isinstance(result, int):
                    if int(steal_success) > result:
                        sql_message.update_ls(user_id, coststone_num, 2)  # 减少手续费
                        sql_message.update_ls(steal_user['user_id'], coststone_num, 1)  # 增加被偷的人的灵石
                        msg = f"道友偷窃失手了，被对方发现然后被派去博丽神社义务劳工！赔款{coststone_num}灵石"
                        if XiuConfig().img:
                            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                        else:
                            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await steal_stone.finish()
                    get_stone = random.randint(int(XiuConfig().tou_lower_limit * steal_user_stone),
                                               int(XiuConfig().tou_upper_limit * steal_user_stone))
                    if int(get_stone) > int(steal_user_stone):
                        sql_message.update_ls(user_id, steal_user_stone, 1)  # 增加偷到的灵石
                        sql_message.update_ls(steal_user['user_id'], steal_user_stone, 2)  # 减少被偷的人的灵石
                        msg = f"***{steal_user['user_name']}***道友已经被榨干了~"
                        if XiuConfig().img:
                            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                        else:
                            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await steal_stone.finish()
                    else:
                        sql_message.update_ls(user_id, get_stone, 1)  # 增加偷到的灵石
                        sql_message.update_ls(steal_user['user_id'], get_stone, 2)  # 减少被偷的人的灵石
                        msg = f"共偷取***{steal_user['user_name']}***道友{number_to(get_stone)}枚灵石！"
                        if XiuConfig().img:
                            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                        else:
                            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await steal_stone.finish()
                else:
                    msg = result
                    if XiuConfig().img:
                        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                    else:
                        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await steal_stone.finish()
            else:
                msg = f"对方未踏入修仙界，不要对杂修出手！"
                params_items = [('msg', msg)]               
                buttons = [
                    [(1, '启用修仙', '那么就启用修仙功能 ', True), (1, '禁用修仙', '那么就禁用修仙功能 ', True)],            
                ]
               # 调用 markdown 函数生成数据
                data = await markdown_s(params_items, buttons)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
                await steal_stone.finish()




# GM加灵石
@gm_command.handle(parameterless=[Cooldown(at_sender=False)])
async def gm_command_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg_text = args.extract_plain_text().strip()
    msg_parts = msg_text.split()

    try:
        stone_num_match = msg_parts[0]  # 获取灵石数量
        give_stone_num = int(stone_num_match) if stone_num_match else 0
        nick_name = msg_parts[1] if len(msg_parts) > 1 else None  # 获取道号（如果有的话）

        if nick_name:
            # 如果提供了道号，给指定用户发放灵石
            give_message = sql_message.get_user_info_with_name(nick_name)
            if give_message:
                sql_message.update_ls(give_message['user_id'], give_stone_num, 1)
                await bot.send_group_msg(group_id=send_group_id, message=f"共赠送{give_stone_num}枚灵石给***{give_message['user_name']}***道友！")
            else:
                await bot.send_group_msg(group_id=send_group_id, message="对方未踏入修仙界，不可赠送！")
        else:
            gift_min_level = 1000

            sql_message.update_ls_all_s(give_stone_num, gift_min_level)
            msg = f"全服通告：赠送所有化灵境初期等级以上的用户{give_stone_num}灵石，请注意查收！"
            await bot.send_group_msg(group_id=send_group_id, message=msg)
    except Exception as e:
        await bot.send_group_msg(group_id=send_group_id, message=f"发生错误: {str(e)}")
        
@gm_command_tili.handle(parameterless=[Cooldown(at_sender=False)])
async def gm_command_tili_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    msg_text = args.extract_plain_text().strip()
    msg_parts = msg_text.split()

    try:
        stone_num_match = msg_parts[0]  # 获取灵石数量
        give_stone_num = int(stone_num_match) if stone_num_match else 0
        nick_name = msg_parts[1] if len(msg_parts) > 1 else None  # 获取道号（如果有的话）

        if nick_name:
            # 如果提供了道号，给指定用户发放灵石
            give_message = sql_message.get_user_info_with_name(nick_name)
            if give_message:
                sql_message.update_user_stamina(give_message['user_id'], give_stone_num, 1)
                await bot.send_group_msg(group_id=send_group_id, message=f"共赠送{give_stone_num}枚灵石给***{give_message['user_name']}***道友！")
            else:
                await bot.send_group_msg(group_id=send_group_id, message="对方未踏入修仙界，不可赠送！")
        else:
            gift_min_level = 1000

            sql_message.update_all_users_stamina(give_stone_num, gift_min_level)
            msg = f"全服通告：赠送所有化灵境初期等级以上的用户{give_stone_num}灵石，请注意查收！"
            await bot.send_group_msg(group_id=send_group_id, message=msg)
    except Exception as e:
        await bot.send_group_msg(group_id=send_group_id, message=f"发生错误: {str(e)}")        

# GM刷新礼包
@refresh_gift.handle(parameterless=[Cooldown(at_sender=False)])
async def grefresh_gift_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    sql_message.reset_all_gift_nums()
    msg = f"已刷新礼包次数。"
    await bot.send_group_msg(group_id=send_group_id, message=msg)
    await refresh_gift.finish()
    
@cz.handle(parameterless=[Cooldown(at_sender=False)])
async def cz_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """创造力量"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    give_qq = None  # 艾特的时候存到这里
    msg = args.extract_plain_text().split()
    
    if not msg:
        msg = f"请输入正确指令！例如：创造力量 物品 数量 道友"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await cz.finish()
    
    goods_name = msg[0]
    goods_id = -1
    goods_type = None
    
    for k, v in items.items.items():
        if goods_name == v['name']:
            goods_id = k
            goods_type = v['type']
            break
    
    goods_num = int(msg[1]) 
    give_qq = msg[2] if len(msg) > 2 else None
    #flag = msg[3]
    if give_qq:
        give_user = sql_message.get_user_info_with_name(give_qq)
        if give_user:
            if goods_num < 0:  # 检查是否为负数
                positive_goods_num = abs(goods_num)
                sql_message.update_back_j(give_user['user_id'], goods_id, positive_goods_num)
                msg = f"***{give_user['user_name']}***道友获得了系统赠送的{goods_name}个{goods_num}！(扣除)"
            else:        
                sql_message.send_back(give_user['user_id'], goods_id, goods_name, goods_type, goods_num)
                msg = f"***{give_user['user_name']}***道友获得了系统赠送的{goods_name}个{goods_num}！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        else:
            msg = f"对方未踏入修仙界，不可赠送！"
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    else:
        all_users = sql_message.get_all_user_id()
        for user_id in all_users:
            sql_message.send_back(user_id, goods_id, goods_name, goods_type, goods_num)  # 给每个用户发送物品
        msg = f"全服通告：赠送所有用户{goods_name}{goods_num}个,请注意查收！"        
        await bot.send_group_msg(group_id=send_group_id, message=msg) 
        await cz.finish()
    



#GM改灵根
@gmm_command.handle()
async def gmm_command_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    give_qq = None  # 艾特的时候存到这里
    msg = args.extract_plain_text().strip()
    command_args = msg.split()    
    if not args:
        msg = f"请输入正确指令！例如：轮回力量 道号 (1混沌,2融合,3超,4龙,5天,6千世,7万世,8异界)"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await gm_command.finish()

    root_key = command_args[1]
    user_name = command_args[0]
    rootname = command_args[2]
    give_user = sql_message.get_user_info_with_name(user_name)
    if give_user:
        root_name = sql_message.update_root(give_user['user_id'], root_key, rootname)
        sql_message.update_power2(give_user['user_id'])
        msg = f"***{give_user['user_name']}***道友的灵根已变更为{root_name}！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await gmm_command.finish()
    else:
        msg = f"对方未踏入修仙界，不可修改！"
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await gmm_command.finish()


@rob_stone.handle(parameterless=[Cooldown(stamina_cost = 25, at_sender=False)])
async def rob_stone_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """抢劫
            player1 = {
            "NAME": player,
            "HP": player,
            "ATK": ATK,
            "COMBO": COMBO
        }"""
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
        await rob_stone.finish()
    user_id = user_info["user_id"]
    is_type, msg = check_user_type(user_id, 0)    
    if not is_type:
        # 用户不在闲暇状态，发送对应提示信息
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '打劫', '打劫', False)]  # 假设有一个“查看详情”功能
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await rob_stone.finish()  
    user_mes = sql_message.get_user_info_with_id(user_id)
    give_qq = None  # 艾特的时候存到这里
    for arg in args:
        if arg.type in ["text"]:
            give_qq = arg.data.get('text', '').strip()
    player1 = {"user_id": None, "道号": None, "气血": None, "攻击": None, "真元": None, '会心': None, '爆伤': None, '防御': 0}
    player2 = {"user_id": None, "道号": None, "气血": None, "攻击": None, "真元": None, '会心': None, '爆伤': None, '防御': 0}
    user_2 = sql_message.get_user_info_with_name(give_qq)
    is_type, msg = check_user_type(user_2['user_id'], 0)    
    if not is_type:
        # 用户不在闲暇状态，发送对应提示信息
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '打劫', '打劫', False)]  # 假设有一个“查看详情”功能
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await rob_stone.finish()      
    if user_mes and user_2:
        if user_info['root'] == "器师":
            msg = f"目前职业无法抢劫！"
            sql_message.update_user_stamina(user_id, 25, 1)
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await rob_stone.finish()
       
        if give_qq:
            if give_qq == user_info['user_name']:
          #  if str(give_qq) == str(user_id):          
                msg = f"请不要打劫自己刷成就！"
                sql_message.update_user_stamina(user_id, 25, 1)
                if XiuConfig().img:
                    pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                else:
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

            if user_2['root'] == "器师":
                msg = f"对方职业无法被抢劫！"
               # sql_message.update_user_stamina(user_id, 15, 1)
                if XiuConfig().img:
                    pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                    await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                else:
                    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                await rob_stone.finish()

            if user_2:
                if user_info['hp'] is None:
                    # 判断用户气血是否为None
                    sql_message.update_user_hp(user_id)
                    user_info = sql_message.get_user_info_with_name(user_id)
                if user_2['hp'] is None:
                    sql_message.update_user_hp(user_2['user_id'])
                    user_2 = sql_message.get_user_info_with_name(give_qq)

                if user_2['hp'] <= user_2['exp'] / 20:
                    time_2 = leave_harm_time(int(user_2['user_id']))
                    msg = f"对方重伤藏匿了，无法抢劫！距离对方脱离生命危险还需要{time_2}分钟！"
                    sql_message.update_user_stamina(user_id, 25, 1)
                    if XiuConfig().img:
                        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                    else:
                        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await rob_stone.finish()

                if user_info['hp'] <= user_info['exp'] / 20:
                    time_msg = leave_harm_time(user_id)
                    msg = f"重伤未愈，动弹不得！距离脱离生命危险还需要{time_msg}分钟！"
                    msg += f"请道友进行闭关，或者使用药品恢复气血，不要干等，没有自动回血！！！"
                    sql_message.update_user_stamina(user_id, 25, 1)
                    if XiuConfig().img:
                        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                    else:
                        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await rob_stone.finish()
                    
                impart_data_1 = xiuxian_impart.get_user_info_with_id(user_id)
                player1['user_id'] = user_info['user_id']
                player1['道号'] = user_info['user_name']
                player1['气血'] = user_info['hp']
                player1['攻击'] = user_info['atk']
                player1['真元'] = user_info['mp']
                player1['会心'] = int(
                    (0.01 + impart_data_1['impart_know_per'] if impart_data_1 is not None else 0) * 100)
                player1['爆伤'] = int(
                    1.5 + impart_data_1['impart_burst_per'] if impart_data_1 is not None else 0)
                user_buff_data = UserBuffDate(user_id)
                user_armor_data = user_buff_data.get_user_armor_buff_data()
                if user_armor_data is not None:
                    def_buff = int(user_armor_data['def_buff'])
                else:
                    def_buff = 0
                player1['防御'] = def_buff

                impart_data_2 = xiuxian_impart.get_user_info_with_id(user_2['user_id'])
                player2['user_id'] = user_2['user_id']
                player2['道号'] = user_2['user_name']
                player2['气血'] = user_2['hp']
                player2['攻击'] = user_2['atk']
                player2['真元'] = user_2['mp']
                player2['会心'] = int(
                    (0.01 + impart_data_2['impart_know_per'] if impart_data_2 is not None else 0) * 100)
                player2['爆伤'] = int(
                    1.5 + impart_data_2['impart_burst_per'] if impart_data_2 is not None else 0)
                user_buff_data = UserBuffDate(user_2['user_id'])
                user_armor_data = user_buff_data.get_user_armor_buff_data()
                if user_armor_data is not None:
                    def_buff = int(user_armor_data['def_buff'])
                else:
                    def_buff = 0
                player2['防御'] = def_buff

                result, victor = OtherSet().player_fight(player1, player2)
                await send_msg_handler(bot, event, '决斗场', bot.self_id, result)
                if victor == player1['道号']:
                    foe_stone = user_2['stone']
                    if foe_stone > 0:
                        sql_message.update_ls(user_id, int(foe_stone * 0.1), 1)
                        sql_message.update_ls(int(user_2['user_id']), int(foe_stone * 0.1), 2)
                        exps = int(user_2['exp'] * 0.005)
                        sql_message.update_exp(user_id, exps)
                        sql_message.update_j_exp(int(user_2['user_id']), exps / 2)
                        msg = f"大战一番，战胜对手，获取灵石{number_to(foe_stone * 0.1)}枚，修为增加{number_to(exps)}，对手修为减少{number_to(exps / 2)}"
                        if XiuConfig().img:
                            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                        else:
                            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await rob_stone.finish()
                    else:
                        exps = int(user_2['exp'] * 0.005)
                        sql_message.update_exp(user_id, exps)
                        sql_message.update_j_exp(int(user_2['user_id']), exps / 2)
                        msg = f"大战一番，战胜对手，结果对方是个穷光蛋，修为增加{number_to(exps)}，对手修为减少{number_to(exps / 2)}"
                        if XiuConfig().img:
                            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                        else:
                            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await rob_stone.finish()

                elif victor == player2['道号']:
                    mind_stone = user_info['stone']
                    if mind_stone > 0:
                        sql_message.update_ls(user_id, int(mind_stone * 0.1), 2)
                        sql_message.update_ls(int(user_2['user_id']), int(mind_stone * 0.1), 1)
                        exps = int(user_info['exp'] * 0.005)
                        sql_message.update_j_exp(user_id, exps)
                        sql_message.update_exp(int(user_2['user_id']), exps / 2)
                        msg = f"大战一番，被对手反杀，损失灵石{number_to(mind_stone * 0.1)}枚，修为减少{number_to(exps)}，对手获取灵石{number_to(mind_stone * 0.1)}枚，修为增加{number_to(exps / 2)}"
                        if XiuConfig().img:
                            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                        else:
                            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await rob_stone.finish()
                    else:
                        exps = int(user_info['exp'] * 0.005)
                        sql_message.update_j_exp(user_id, exps)
                        sql_message.update_exp(int(user_2['user_id']), exps / 2)
                        msg = f"大战一番，被对手反杀，修为减少{number_to(exps)}，对手修为增加{number_to(exps / 2)}"
                        if XiuConfig().img:
                            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                        else:
                            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                        await rob_stone.finish()

                else:
                    msg = f"发生错误，请检查后台！"
                    if XiuConfig().img:
                        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
                    else:
                        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
                    await rob_stone.finish()

    else:
        msg = f"对方未踏入修仙界，不可对凡人出手抢劫！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await rob_stone.finish()


@restate.handle(parameterless=[Cooldown(at_sender=False)])
async def restate_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """重置用户状态。
    单用户：重置状态@xxx
    多用户：重置状态"""
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
        await restate.finish()
    give_qq = None  # 艾特的时候存到这里
    for arg in args:
        if arg.type == "at":
            give_qq = arg.data.get("qq", "")
    if give_qq:
        sql_message.restate(give_qq)
        msg = f"{give_qq}用户信息重置成功！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await restate.finish()
    else:
        sql_message.restate()
        msg = f"所有用户信息重置成功！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await restate.finish()


@set_xiuxian.handle()
async def open_xiuxian_(bot: Bot, event: GroupMessageEvent):
    """群修仙开关配置"""
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    group_msg = str(event.message)
    group_id = str(event.group_id)
    conf_data = JsonConfig().read_data()

    if "禁用" in group_msg:
        if group_id in conf_data["group"]:
            msg = "当前群聊修仙模组已禁用，请勿重复操作！"
            params_items = [('msg', msg)]               
            buttons = [
                [(1, '启用修仙', '那么就启用修仙功能 ', True)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown_s(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await set_xiuxian.finish()
        JsonConfig().write_data(1, group_id)
        msg = "当前群聊修仙模组已禁用！请联系群聊管理员开启！"
        params_items = [('msg', msg)]               
        buttons = [
            [(1, '启用修仙', '那么就启用修仙功能 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown_s(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await set_xiuxian.finish()

    elif "启用" in group_msg:
        if group_id not in conf_data["group"]:
            msg = "当前群聊修仙模组已启用，请勿重复操作！！"
            params_items = [('msg', msg)]               
            buttons = [
                [(1, '禁用修仙', '那么就禁用修仙功能 ', True)],            
            ]
           # 调用 markdown 函数生成数据
            data = await markdown_s(params_items, buttons)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
            await set_xiuxian.finish()
        JsonConfig().write_data(2, group_id)
        msg = "当前群聊修仙基础模组已启用！如需关闭，请联系群聊管理员！"
        params_items = [('msg', msg)]               
        buttons = [
            [(1, '禁用修仙', '那么就禁用修仙功能 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown_s(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await set_xiuxian.finish()
    else:
        msg = "指令错误，请联系群聊管理员！"
        params_items = [('msg', msg)]               
        buttons = [
            [(1, '启用修仙', '那么就启用修仙功能 ', True), (1, '禁用修仙', '那么就禁用修仙功能 ', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown_s(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await set_xiuxian.finish()


@xiuxian_updata_level.handle(parameterless=[Cooldown(at_sender=False)])
async def xiuxian_updata_level_(bot: Bot, event: GroupMessageEvent):
    """将修仙1的境界适配到修仙2"""
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
        await xiuxian_updata_level.finish()
    level_dict={
        "练气境":"搬血境",
        "筑基境":"洞天境",
        "结丹境":"化灵境",
        "元婴境":"铭纹境",
        "化神境":"列阵境",
        "炼虚境":"尊者境",
        "合体境":"神火境",
        "大乘境":"真一境",
        "渡劫境":"圣祭境",
        "半步真仙":"天神境中期",
        "真仙境":"虚道境",
        "金仙境":"斩我境",
        "太乙境":"遁一境"
    }
    level = user_info['level']
    user_id = user_info['user_id']
    if level == "半步真仙":
        level = "天神境中期"
    else:
        try:
            level = level_dict.get(level[:3]) + level[-2:]
        except:
            level = level
    sql_message.updata_level(user_id=user_id,level_name=level)
    msg = '境界适配成功成功！'
    if XiuConfig().img:
        pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
    else:
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await xiuxian_updata_level.finish()

@mew_hongbao.handle(parameterless=[Cooldown(10, at_sender=False)])
async def hander_mew_hongbao(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mew_hongbao.finish()

    args = args.extract_plain_text().strip()
    args_list = args.split()

    if len(args_list) < 3:
        msg = f'请输入 <qqbot-cmd-input text=\"修仙发红包\" show=\"修仙发红包\" reference=\"false\" />[红包口令][红包金额][红包数量] 用空格分隔'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修仙发红包', '修仙发红包 ', False)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await mew_hongbao.finish()

    # 参数解析和检查
    kouling = args_list[0]
    if not args_list[1].isdigit() or not args_list[2].isdigit():
        await bot.send_group_msg(group_id=int(send_group_id), message='红包金额和数量应为数字')
        await mew_hongbao.finish()

    score = int(args_list[1])
    num = int(args_list[2])
    uid = user_info['user_id']

    if score < 1:
        await bot.send_group_msg(group_id=int(send_group_id), message='红包金额需要大于0')
        await mew_hongbao.finish()

    if num < 1:
        await bot.send_group_msg(group_id=int(send_group_id), message='红包数量需要大于0')
        await mew_hongbao.finish()

    if num > score:
        await bot.send_group_msg(group_id=int(send_group_id), message='红包数量需要大于红包金额')
        await mew_hongbao.finish()

    my_score = user_info['stone']
    if score > my_score:
        await bot.send_group_msg(group_id=int(send_group_id), message=f'您的金币小于{score}，红包发放失败')
        await mew_hongbao.finish()

    fee = int(score * 0.2)
    net_score = score - fee

    if net_score <= 0:
        await bot.send_group_msg(group_id=int(send_group_id), message='扣除手续费后红包金额小于等于0，红包发放失败')
        await mew_hongbao.finish()

    hbscore, use_score, hbnum, use_num, openuser = pmhongbao.get_hongbao(kouling)
    if hbscore > 0:
        await bot.send_group_msg(group_id=int(send_group_id), message=f'红包口令重复，红包发放失败')
        await mew_hongbao.finish()

    # 插入红包信息和更新金币
    try:
        pmhongbao.insert_hongbao(kouling, net_score, num)
        sql_message.update_ls(uid, score, 2)
        msg = f'红包发放成功，红包口令：{kouling}。请输入 修仙抢红包 {kouling}开始吧。'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    except Exception as e:
        await bot.send_group_msg(group_id=int(send_group_id), message=f'红包发放过程中出现错误：{str(e)}')

    await mew_hongbao.finish() 

@open_hongbao.handle(parameterless=[Cooldown(10, at_sender=False)])    
async def hander_open_hongbao(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
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
        await open_hongbao.finish()
    args = args.extract_plain_text().strip()
    args_list = args.split()
    uid = user_info['user_id']
    if len(args_list) < 1:
        return await bot.send_group_msg(group_id=int(send_group_id), message='请输入 修仙抢红包 [红包口令]')
        await open_hongbao.finish()
    kouling = args_list[0]
    score,use_score,num,use_num,openuser = pmhongbao.get_hongbao(kouling)
    if uid in openuser:
        return await bot.send_group_msg(group_id=int(send_group_id), message='您已经抢过该红包')
        await open_hongbao.finish()
    if score == 0:
        return await bot.send_group_msg(group_id=int(send_group_id), message='红包口令无效或该红包已被抢完')
        await open_hongbao.finish()
        
    name = user_info['user_name']
    last_score = score - use_score
    last_num = int(num) - int(use_num)
    max_score = (last_score/last_num)*1.5
    if last_num == 0 or last_score == 0:
        return await bot.send(group_id=int(send_group_id), message='该红包已被抢完')
        await open_hongbao.finish()
    if last_num == 1:
        get_score = last_score
    else:
        get_score = int(math.floor(random.uniform(1, max_score)))
    sql_message.update_ls(uid, get_score, 1)
    pmhongbao.open_hongbao(kouling,get_score,uid)
    if last_num == 1:
        pmhongbao.hongbao_off(kouling)
    msg = f'恭喜【{name}】道友！您抢到了{get_score}金币，红包剩余数量{last_num - 1}，剩余金额{last_score - get_score}'
  #  buttons = [
  #      Button('抢红包', f'pm抢红包{kouling}', '抢红包', action=1),
 #   ]
    await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    await open_hongbao.finish()
    
    
@get_gift.handle(parameterless=[Cooldown(at_sender=False)])
async def get_gift_(bot: Bot, event: GroupMessageEvent):
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
        await get_gift.finish()  
    user_id = user_info['user_id']
    # 首先判断是否满足创建宗门的三大条件
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
               
    propname = "渡厄丹"
    propnum = 50  
    scorenum = 2000000
    gift_info = sql_message.get_gift_info(user_info['user_id'])
 #   msg = "礼包领取已结束，祝您中秋国庆快乐！"
 #   params_items = [('msg', msg)]               
 #   buttons = [
 #       [(2, '修炼', '修炼', True)],            
#    ]
   # 调用 markdown 函数生成数据
 #   data = await markdown(params_items, buttons)
 #   await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
 #   await get_gift.finish()  
    
    if gift_info == 0:
        sql_message.update_ls(user_info['user_id'], scorenum, 1)  # 发放300万灵石
       # sql_message.send_back(user_info['user_id'], 1999, "渡厄丹", "丹药", 10, 1)  # 发放物品
        sql_message.update_gift(user_info['user_id'], 1)  # 更新领取状态
        msg = f'亲爱的群友们，在这国庆佳节之际，庆祝祖国的繁荣富强。在这充满欢庆的日子里，灵梦为各位训练家准备了小小礼物，发放灵石{scorenum}枚！祝各位国庆快乐！φ（￣∇￣o）'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '使用物品', f'使用{propname}', False), (2, '查看物品', '查看物品效果 1999', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await get_gift.finish()    
    else:
        msg = "真是贪心！您已经领取过该礼品，无法再次领取。"
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修炼', '修炼', True)],            
        ]
       # 调用 markdown 函数生成数据
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data})) 
        await get_gift.finish()  

@vip_get.handle(parameterless=[Cooldown(at_sender=False)])
async def vip_get_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '我要修仙', '我要修仙 ', True)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await vip_get.finish()
    args = args.extract_plain_text().strip()
    args_list = args.split()
    if len(args_list) < 2:
        msg = f'请输入 <qqbot-cmd-input text=\"修仙兑换\" show=\"修仙兑换\" reference=\"false\" />[兑换码][道号] 用空格分隔'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修仙兑换', '修仙兑换 ', False)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await vip_get.finish()
    kouling = args_list[0]
    user_name = args_list[1]
    user_info = sql_message.get_user_info_with_name(user_name)
    if user_info is None:
        msg = f'修仙界未有此道号的道友，还请道友再仔细检查！'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修仙兑换', '修仙兑换 ', False)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await vip_get.finish()    
    user_id = user_info['user_id']   
    valid_kouling = "abcxf"  # 替换为您设定的有效兑换码
    if kouling != valid_kouling:
        msg = f'无效的兑换码，还请道友再仔细检查！'
        params_items = [('msg', msg)]               
        buttons = [
            [(2, '修仙兑换', '修仙兑换 ', False)],            
        ]
        data = await markdown(params_items, buttons)
        await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment("markdown", {"data": data}))
        await vip_get.finish()    

    try:
        sql_message.update_vip(user_id, 1)  # 每次增加 30 天
        days = sql_message.check_vip_status(user_id) # 获取剩余有效期
        leftdays = days + 1
        msg = f'兑换成功，您已成为尊贵的VIP会员。有效期还有{leftdays}天'
        await bot.send_group_msg(group_id=int(send_group_id), message=msg)
    except Exception as e:
        await bot.send_group_msg(group_id=int(send_group_id), message=f'发放过程中出现错误：{str(e)}，请联系管理员！') 