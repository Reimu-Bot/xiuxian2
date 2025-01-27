try:
    import ujson as json
except ImportError:
    import json
from ..xiuxian_utils.item_json import Items
from ..xiuxian_utils.utils import number_to
from ..xiuxian_utils.xiuxian2_handle import (
    XiuxianDateManage, UserBuffDate, 
    get_weapon_info_msg, get_armor_info_msg,
    get_weapon_info_msg_1, get_armor_info_msg_1,    
    get_player_info, save_player_info, 
    get_sec_msg, get_main_info_msg, get_sub_info_msg
)
from datetime import datetime
import os
from pathlib import Path
from ..xiuxian_config import convert_rank

items = Items()
sql_message = XiuxianDateManage()

YAOCAIINFOMSG = {
    "-1": "性寒",
    "0": "性平",
    "1": "性热",
    "2": "生息",
    "3": "养气",
    "4": "炼气",
    "5": "聚元",
    "6": "凝神",
}
level_mapping = {
    "一品药材": 1,
    "二品药材": 2,
    "三品药材": 3,
    "四品药材": 4,
    "五品药材": 5,
    "六品药材": 6,
    "七品药材": 7,
    "八品药材": 8,
    "九品药材": 9
}

def check_equipment_can_use(user_id, goods_id):
    """
    装备数据库字段：
        good_type -> '装备'
        state -> 0-未使用， 1-已使用
        goods_num -> '目前数量'
        all_num -> '总数量'
        update_time ->使用的时候更新
        action_time ->使用的时候更新
    判断:
        state = 0, goods_num = 1, all_num =1  可使用
        state = 1, goods_num = 1, all_num =1  已使用
        state = 1, goods_num = 2, all_num =2  已装备，多余的，不可重复使用
    顶用：
    """
    flag = False
    back_equipment = sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)
    if back_equipment['state'] == 0:
        flag = True
    return flag


def get_use_equipment_sql(user_id, goods_id):
    """
    使用装备
    返回sql,和法器或防具
    """
    sql_str = []
    item_info = items.get_data_by_item_id(goods_id)
    user_buff_info = UserBuffDate(user_id).BuffInfo
    now_time = datetime.now()
    item_type = ''
    if item_info['item_type'] == "法器":
        item_type = "法器"
        in_use_id = user_buff_info['faqi_buff']
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=1 WHERE user_id={user_id} and goods_id={goods_id}")  # 装备
        if in_use_id != 0:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={in_use_id}")  # 取下原有的

    if item_info['item_type'] == "防具":
        item_type = "防具"
        in_use_id = user_buff_info['armor_buff']
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=1 WHERE user_id={user_id} and goods_id={goods_id}")  # 装备
        if in_use_id != 0:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={in_use_id}")  # 取下原有的

    return sql_str, item_type


def get_no_use_equipment_sql(user_id, goods_id):
    """
    卸载装备
    返回sql,和法器或防具
    """
    item_info = items.get_data_by_item_id(goods_id)
    user_buff_info = UserBuffDate(user_id).BuffInfo
    now_time = datetime.now()
    sql_str = []
    item_type = ""

    # 检查装备类型，并确定要卸载的是哪种buff
    if item_info['item_type'] == "法器":
        item_type = "法器"
        in_use_id = user_buff_info['faqi_buff']
    elif item_info['item_type'] == "防具":
        item_type = "防具"
        in_use_id = user_buff_info['armor_buff']
    else:
        return sql_str, item_type

    # 如果当前装备正被使用，或者存在需要卸载的其他装备
    if goods_id == in_use_id or in_use_id != 0:
        # 卸载当前装备
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={goods_id}")
        # 如果还有其他装备需要卸载（对于法器和防具的情况）
        if in_use_id != 0 and goods_id != in_use_id:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={in_use_id}")

    return sql_str, item_type



def check_equipment_use_msg(user_id, goods_id):
    """
    检测装备是否已用
    """
    user_back = sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)
    state = user_back['state']
    is_use = False
    if state == 0:
        is_use = False
    if state == 1:
        is_use = True
    return is_use


def get_user_main_back_msg(user_id):
    """
    获取背包内的所有物品信息
    """
    l_equipment_msg = []
    l_shenwu_msg = []
    l_shenwu1_msg = [] 
    l_spwp_msg = []     
    l_xiulianitem_msg = []
    l_libao_msg = []
    l_msg = []
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    for user_back in user_backs:
        if user_back['goods_type'] == "装备":
            l_equipment_msg = get_equipment_msg(l_equipment_msg, user_id, user_back['goods_id'], user_back['goods_num'])
 
      #  elif user_back['goods_type'] == "技能":
     #       l_shenwu_msg = get_shenwu_msg(l_shenwu_msg, user_back['goods_id'], user_back['goods_num'])

        elif user_back['goods_type'] == "神物":
            l_shenwu1_msg = get_shenwu_msg1(l_shenwu1_msg, user_back['goods_id'], user_back['goods_num'])

        elif user_back['goods_type'] == "聚灵旗":
            l_xiulianitem_msg = get_jlq_msg(l_xiulianitem_msg, user_back['goods_id'], user_back['goods_num'])
        elif user_back['goods_type'] == "特殊物品":
            l_spwp_msg = get_spwup_msg(l_spwp_msg, user_back['goods_id'], user_back['goods_num'])
        elif user_back['goods_type'] == "礼包":
            l_libao_msg = get_libao_msg(l_libao_msg, user_back['goods_id'], user_back['goods_num'])

    if l_equipment_msg:
        l_msg.append("\n#☆------我的装备------☆")
        for msg in l_equipment_msg:
            l_msg.append(msg)

 #   if l_shenwu_msg:
 #       l_msg.append("\n#☆------技能------☆")
 #       for msg in l_shenwu_msg:
 #           l_msg.append(msg)

    if l_shenwu1_msg:
        l_msg.append("\n#☆------神物------☆")
        for msg in l_shenwu1_msg:
            l_msg.append(msg)

    if l_xiulianitem_msg:
        l_msg.append("\n#☆------修炼物品------☆")
        for msg in l_xiulianitem_msg:
            l_msg.append(msg)
    if l_spwp_msg:
        l_msg.append("\n#☆------特殊物品------☆")
        for msg in l_spwp_msg:
            l_msg.append(msg)
    if l_libao_msg:
        l_msg.append("\n#☆------礼包------☆")
        for msg in l_libao_msg:
            l_msg.append(msg)
    return l_msg


def get_user_elixir_back_msg(user_id):
    """
    获取背包内的丹药信息
    """
    l_elixir_msg = []
    l_ldl_msg = []
    l_msg = []
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    for user_back in user_backs:
        if user_back['goods_type'] == "丹药":
            l_elixir_msg = get_elixir_msg(l_elixir_msg, user_back['goods_id'], user_back['goods_num'])
        elif user_back['goods_type'] == "炼丹炉":
            l_ldl_msg = get_ldl_msg(l_ldl_msg, user_back['goods_id'], user_back['goods_num'])

    if l_ldl_msg:
        l_msg.append("\n#☆------炼丹炉------☆")
    for msg in l_ldl_msg:
        l_msg.append(msg)

    if l_elixir_msg:
        l_msg.append("\n#☆------我的丹药------☆")
        for msg in l_elixir_msg:
            l_msg.append(msg)
    return l_msg

def get_libao_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的礼包信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\n"
    msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg

def get_user_skill_back_msg(user_id):
    """
    获取背包内的技能信息
    """
    l_skill_msg = []
    l_msg = []
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    for user_back in user_backs:
        if user_back['goods_type'] == "技能":
            l_skill_msg = get_skill_msg(l_skill_msg, user_back['goods_id'], user_back['goods_num'])
    if l_skill_msg:
        l_msg.append("\n#☆------拥有技能书------☆")
        for msg in l_skill_msg:
            l_msg.append(msg)
    return l_msg


def get_user_yaocai_back_msg(user_id):
    """
    获取背包内的药材信息，并按品级排序
    """
    l_yaocai_msg = []
    l_msg = []
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    
    for user_back in user_backs:
        if user_back['goods_type'] == "药材":
            l_yaocai_msg = get_yaocai_msg(l_yaocai_msg, user_back['goods_id'], user_back['goods_num'])

    # 按药材品级从高到低排序（"九品药材" -> "一品药材"）
    l_yaocai_msg = sorted(
        l_yaocai_msg,
        key=lambda msg: level_mapping.get(msg['level'], 10),
        reverse=True  # 反转排序，确保九品最高
    )

    if l_yaocai_msg:
        l_msg.append("☆------拥有药材------☆")
        for msg in l_yaocai_msg:
            l_msg.append(msg['info'])  # 这里展示药材的详细信息
    return l_msg


def get_yaocai_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的药材信息，并返回包含格式化命令按钮的字符串
    """
    item_info = items.get_data_by_item_id(goods_id)
    
    # 包含物品名称、品级、数量及命令按钮
    msg = {
        'goods_id': goods_id,
        'name': item_info['name'],
        'level': item_info['level'],
        'info': f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> {item_info['level']} {goods_num}   "
                f"<qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />  "
                f"<qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\" />  "
                f"<qqbot-cmd-input text=\"赠送修仙道具{item_info['name']} {goods_num}\" show=\"增送\" />"
    }
    l_msg.append(msg)
    return l_msg


def get_jlq_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的修炼物品信息，聚灵旗
    """
    item_info = items.get_data_by_item_id(goods_id)
   # msg = f"名字：{item_info['name']}\n"
    msg = f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> {goods_num}  <qqbot-cmd-input text=\"使用{item_info['name']} {goods_num}\" show=\"使用\" />  <qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />"  
 #   msg += f"效果：{item_info['desc']}"
  #  msg += f"\n拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg

def get_spwp_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的修炼物品信息，聚灵旗
    """
    item_info = items.get_data_by_item_id(goods_id)
   # msg = f"名字：{item_info['name']}\n"
    msg = f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> {goods_num}  <qqbot-cmd-input text=\"使用{item_info['name']} {goods_num}\" show=\"使用\" />"  
 #   msg += f"效果：{item_info['desc']}"
  #  msg += f"\n拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg

def get_ldl_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的炼丹炉信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> {goods_num}\n<qqbot-cmd-input text=\"炼丹帮助\" show=\"炼丹\" />  <qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\" />"  
  #  msg = f"名字：{item_info['name']}\n"
  #  msg += f"效果：{item_info['desc']}"
  #  msg += f"\n拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_yaocai_info(yaocai_info):
    """
    获取药材信息
    """
    msg = f"主药 {YAOCAIINFOMSG[str(yaocai_info['主药']['h_a_c']['type'])]}"
    msg += f"{yaocai_info['主药']['h_a_c']['power']}"
    msg += f" {YAOCAIINFOMSG[str(yaocai_info['主药']['type'])]}"
    msg += f"{yaocai_info['主药']['power']}\n"
    msg += f"药引 {YAOCAIINFOMSG[str(yaocai_info['药引']['h_a_c']['type'])]}"
    msg += f"{yaocai_info['药引']['h_a_c']['power']}"
    msg += f"辅药 {YAOCAIINFOMSG[str(yaocai_info['辅药']['type'])]}"
    msg += f"{yaocai_info['辅药']['power']}"

    return msg


def get_equipment_msg(l_msg, user_id, goods_id, goods_num):
    """
    获取背包内的装备信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = ""
    if item_info['item_type'] == '防具':
        msg = get_armor_info_msg_1(goods_id, item_info)
    elif item_info['item_type'] == '法器':
        msg = get_weapon_info_msg_1(goods_id, item_info)
   # msg += f"\n拥有数量:{goods_num}"
    is_use = check_equipment_use_msg(user_id, goods_id)
    if is_use:
        msg += f" {goods_num} <qqbot-cmd-input text=\"换装{item_info['name']}\" show=\"✅已装备\" />  <qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />"
        l_msg.insert(0, msg) 
    else:
        msg += f" {goods_num} <qqbot-cmd-input text=\"使用{item_info['name']}\" show=\"🔃️\" />  <qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />  <qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\"  />"  
        l_msg.append(msg)
    return l_msg


def get_skill_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的技能信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = ""
    if item_info['item_type'] == '神通':
        msg = f"{item_info['level']}神通-{item_info['name']}:"
        msg += get_sec_msg(item_info)
    elif item_info['item_type'] == '功法':
        msg = f"{item_info['level']}功法-"
        msg += get_main_info_msg(goods_id)[1]
    elif item_info['item_type'] == '辅修功法':#辅修功法12
        msg = f"{item_info['level']}辅修功法-"
        msg += get_sub_info_msg(goods_id)[1]
    msg += f" 拥有数量:{goods_num} \n><qqbot-cmd-input text=\"使用{item_info['name']}\" show=\"使用\" />  <qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />   <qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\" />"
    l_msg.append(msg)
    return l_msg


def get_elixir_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的丹药信息
    """
    item_info = items.get_data_by_item_id(goods_id)
 #   msg = f"名字：{item_info['name']}\n"
    msg = f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> 拥有数量：{goods_num}    <qqbot-cmd-input text=\"使用{item_info['name']}\" show=\"使用\" />    \n><qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />   <qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\" />"  
  #  msg += f"效果：{item_info['desc']}\n"
  #  msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg

def get_shenwu_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的神物信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    try:
        desc = item_info['desc']
    except KeyError:
        desc = "这个东西本来会报错让背包出不来，当你看到你背包有这个这个东西的时候请联系超管解决。"
    
    msg = f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> {item_info['level']} {goods_num} <qqbot-cmd-input text=\"使用{item_info['name']}\" show=\"使用\" />  <qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />  <qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\" />"
  #  msg += f"效果：{desc}\n"
 #   msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg

def get_shenwu_msg1(l_msg, goods_id, goods_num):
    """
    获取背包内的神物信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    try:
        desc = item_info['desc']
    except KeyError:
        desc = "这个东西本来会报错让背包出不来，当你看到你背包有这个这个东西的时候请联系超管解决。"
    
    msg = f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> {goods_num} <qqbot-cmd-input text=\"使用{item_info['name']}\" show=\"使用\" />   <qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />   <qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\" />"
  #  msg += f"效果：{desc}\n"
 #   msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg

def get_spwup_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的神物信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    try:
        desc = item_info['desc']
    except KeyError:
        desc = "这个东西本来会报错让背包出不来，当你看到你背包有这个这个东西的时候请联系超管解决。"
    
    msg = f"\n><qqbot-cmd-input text=\"查看物品效果{goods_id}\" show=\"{item_info['name']}\" /> {goods_num} <qqbot-cmd-input text=\"使用{item_info['name']}\" show=\"使用\" />   <qqbot-cmd-input text=\"炼金{item_info['name']} {goods_num}\" show=\"炼金\" />   <qqbot-cmd-input text=\"坊市上架{item_info['name']}\" show=\"坊市\" />"
  #  msg += f"效果：{desc}\n"
 #   msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg

def get_item_id_by_name(item_name):
    for item_id, item_info in items.items():  # 这里使用 items.items() 迭代字典
        if item_info.get("name") == item_name:
            return item_id
    return None 

def get_item_msg(goods_id):
    """
    获取单个物品的消息
    """
    item_info = items.get_data_by_item_id(goods_id)
    if item_info['type'] == '丹药':
        msg = f"{item_info['item_type']}：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    elif item_info['item_type'] == '神物':
        msg = f"{item_info['item_type']}：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"
    
    elif item_info['item_type'] == '神通':
      #  msg = f"名字：{item_info['name']}\n"
        msg = f"{item_info['item_type']}：<qqbot-cmd-input text=\"使用 {item_info['name']}\" show=\"{item_info['name']}\" />  {item_info['level']}"
        msg += f"\n效果：{get_sec_msg(item_info)}"

    elif item_info['item_type'] == '功法':
      #  msg = f"名字：{item_info['name']}\n"
        msg = f"{item_info['item_type']}：<qqbot-cmd-input text=\"使用 {item_info['name']}\" show=\"{item_info['name']}\" />  {item_info['level']}"
        msg += f"\n效果：{get_main_info_msg(goods_id)[1]}"
        
    elif item_info['item_type'] == '辅修功法':#辅修功法11
       # msg = f"名字：{item_info['name']}\n"
        msg = f"{item_info['item_type']}：<qqbot-cmd-input text=\"使用 {item_info['name']}\" show=\"{item_info['name']}\" />   {item_info['level']}"
        msg += f"\n效果：{get_sub_info_msg(goods_id)[1]}"

    elif item_info['item_type'] == '防具':
        msg = get_armor_info_msg(goods_id, item_info)

    elif item_info['item_type'] == '法器':
        msg = get_weapon_info_msg(goods_id, item_info)

    elif item_info['item_type'] == "药材":
        msg = get_yaocai_info_msg(goods_id, item_info)

    elif item_info['item_type'] == "聚灵旗":
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    elif item_info['item_type'] == "炼丹炉":
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"
    elif item_info['item_type'] == "特殊物品":
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    else:
        msg = '不支持的物品'
        
    if 'fusion' in item_info:
        fusion_info = item_info['fusion']
        msg += "\n合成相关信息:\n"
        needed_items = fusion_info.get('need_item', {})
        for item_id, amount_needed in needed_items.items():
            item_name = items.get_data_by_item_id(int(item_id))['name']
            msg += f"需要{amount_needed}个{item_name}\n"
        msg += f"需要灵石：{number_to(int(fusion_info.get('need_stone', 0)))}\n"
        msg += f"需要境界：{fusion_info.get('need_rank', '无')}\n"
        msg += f"需要修为：{number_to(int(fusion_info.get('need_exp', 0)))}\n"
        msg += f"数量限制：{fusion_info.get('limit', '无')}"
        
    return msg


def get_item_msg_rank(goods_id):
    """
    获取单个物品的rank
    """
    item_info = items.get_data_by_item_id(goods_id)
    if item_info['type'] == '丹药':
        msg = item_info['rank']
    elif item_info['item_type'] == '神通':
        msg = item_info['rank']
    elif item_info['item_type'] == '功法':
        msg = item_info['rank']
    elif item_info['item_type'] == '辅修功法':
        msg = item_info['rank']        
    elif item_info['item_type'] == '防具':
        msg = item_info['rank']
    elif item_info['item_type'] == '法器':
        msg = item_info['rank']
    elif item_info['item_type'] == "药材":
        msg = item_info['rank']
    elif item_info['item_type'] == "聚灵旗":
        msg = item_info['rank']
    elif item_info['item_type'] == "炼丹炉":
        msg = item_info['rank']        
    else:
        msg = 520
    return int(msg)


def get_yaocai_info_msg(goods_id, item_info):
    msg = f"{item_info['type']}：<qqbot-cmd-input text=\"炼丹{item_info['name']}\" show=\"{item_info['name']}\" />{item_info['name']}  {item_info['level']}\n"
  #  msg += f"品级：{item_info['level']}\n"
    msg += get_yaocai_info(item_info)
    return msg


def check_use_elixir(user_id, goods_id, num):
    user_info = sql_message.get_user_info_with_id(user_id)
    user_rank = convert_rank(user_info['level'])[0]
    goods_info = items.get_data_by_item_id(goods_id)
    goods_rank = goods_info['rank']
    goods_name = goods_info['name']
    back = sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)
    goods_all_num = back['all_num'] # 数据库里的使用数量
    remaining_limit = goods_info['all_num'] - goods_all_num  # 剩余可用数量
    if goods_info['buff_type'] == "level_up_rate":  # 增加突破概率的丹药
        if goods_rank < user_rank:  # 最低使用限制
            msg = f"丹药：{goods_name}的最低使用境界为{goods_info['境界']}，道友不满足使用条件"
        elif goods_rank - user_rank > 18:  # 最高使用限制
            msg = f"道友当前境界为：{user_info['level']}，丹药：{goods_name}已不能满足道友，请寻找适合道友的丹药吧！"    
        else:  # 检查完毕
            sql_message.update_back_j(user_id, goods_id, num, 1)
            sql_message.update_levelrate(user_id, user_info['level_up_rate'] + goods_info['buff'] * num)
            msg = f"道友成功使用丹药：{goods_name}{num}颗，下一次突破的成功概率提高{goods_info['buff'] * num}%!"

    elif goods_info['buff_type'] == "level_up_big":  # 增加大境界突破概率的丹药
        if goods_rank != user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}，道友不满足使用条件！"
        else:
            if goods_all_num >= goods_info['all_num']:
                msg = f"道友使用的丹药：{goods_name}已经达到丹药的耐药性上限！已经无法使用该丹药了！"    
            else:
                if num > remaining_limit:
                    num = remaining_limit
                    msg = f"道友使用的数量超过了耐药性上限呢，仅使用了{num}颗！"
                else:
                    msg = f"道友成功使用丹药：{goods_name}{num}颗, 下一次突破的成功概率提高{goods_info['buff'] * num}%!"
                sql_message.update_back_j(user_id, goods_id, num, 1)
                sql_message.update_levelrate(user_id, user_info['level_up_rate'] + goods_info['buff'] * num)
             #   msg = f"道友成功使用丹药：{goods_name}{num}颗,下一次突破的成功概率提高{goods_info['buff'] * num}%!"

    elif goods_info['buff_type'] == "hp":  # 回复状态的丹药
        if user_info['root'] == "器师":
            user_max_hp = int(user_info['exp'] / 2)
            user_max_mp = int(user_info['exp'])
            if user_info['hp'] == user_max_hp and user_info['mp'] == user_max_mp:
                msg = f"道友的状态是满的，用不了哦！"
            else:
                buff = goods_info['buff']
                buff = round((0.016 * user_rank + 0.104) * buff , 2)
                recover_hp = int(buff * user_max_hp * num)
                recover_mp = int(buff * user_max_mp * num)
                if user_info['hp'] + recover_hp > user_max_hp:
                    new_hp = user_max_hp  # 超过最大
                else:
                    new_hp = user_info['hp'] + recover_hp
                if user_info['mp'] + recover_mp > user_max_mp:
                    new_mp = user_max_mp
                else:
                    new_mp = user_info['mp'] + recover_mp
                msg = f"道友成功使用丹药：{goods_name}{num}颗，经过境界转化状态恢复了{int(buff * 100 * num)}%!"
                sql_message.update_back_j(user_id, goods_id, num=num ,use_key=1)
                sql_message.update_user_hp_mp(user_id, new_hp, new_mp)
        else:
            if goods_rank < user_rank:  # 使用限制
                msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
            else:
                user_max_hp = int(user_info['exp'] / 2)
                user_max_mp = int(user_info['exp'])
                if user_info['hp'] == user_max_hp and user_info['mp'] == user_max_mp:
                    msg = f"道友的状态是满的，用不了哦！"
                else:
                    buff = goods_info['buff']
                    buff = round((0.016 * user_rank + 0.104) * buff , 2)
                    recover_hp = int(buff * user_max_hp * num)
                    recover_mp = int(buff * user_max_mp * num)
                    if user_info['hp'] + recover_hp > user_max_hp:
                        new_hp = user_max_hp  # 超过最大
                    else:
                        new_hp = user_info['hp'] + recover_hp
                    if user_info['mp'] + recover_mp > user_max_mp:
                        new_mp = user_max_mp
                    else:
                        new_mp = user_info['mp'] + recover_mp
                    msg = f"道友成功使用丹药：{goods_name}{num}颗，经过境界转化状态恢复了{int(buff * 100 * num)}%!"
                    sql_message.update_back_j(user_id, goods_id, num=num ,use_key=1)
                    sql_message.update_user_hp_mp(user_id, new_hp, new_mp)

    elif goods_info['buff_type'] == "all":  # 回满状态的丹药
        if user_info['root'] == "器师":
            user_max_hp = int(user_info['exp'] / 2)
            user_max_mp = int(user_info['exp'])
            if user_info['hp'] == user_max_hp and user_info['mp'] == user_max_mp:
                msg = f"道友的状态是满的，用不了哦！"
            else:
                sql_message.update_back_j(user_id, goods_id, use_key=1)
                sql_message.update_user_hp(user_id)
                msg = f"道友成功使用丹药：{goods_name}1颗,状态已全部恢复!"
        else:
            if goods_rank < user_rank:  # 使用限制
                msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
            else:
                user_max_hp = int(user_info['exp'] / 2)
                user_max_mp = int(user_info['exp'])
                if user_info['hp'] == user_max_hp and user_info['mp'] == user_max_mp:
                    msg = f"道友的状态是满的，用不了哦！"
                else:
                    sql_message.update_back_j(user_id, goods_id, use_key=1)
                    sql_message.update_user_hp(user_id)
                    msg = f"道友成功使用丹药：{goods_name}1颗,状态已全部恢复!"

    elif goods_info['buff_type'] == "atk_buff":  # 永久加攻击buff的丹药
        if user_info['root'] == "器师":
            buff = goods_info['buff'] * num
            sql_message.updata_user_atk_buff(user_id, buff)
            sql_message.update_back_j(user_id, goods_id,num=num, use_key=1)
            msg = f"道友成功使用丹药：{goods_name}{num}颗，攻击力永久增加{buff}点！"
        else:
            if goods_rank < user_rank:  # 使用限制
                msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
            else:
                buff = goods_info['buff'] * num
                sql_message.updata_user_atk_buff(user_id, buff)
                sql_message.update_back_j(user_id, goods_id,num=num, use_key=1)
                msg = f"道友成功使用丹药：{goods_name}{num}颗，攻击力永久增加{buff}点！"

    elif goods_info['buff_type'] == "exp_up":  # 加固定经验值的丹药
        if goods_rank < user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
        else:
            exp = goods_info['buff'] * num
            user_hp = int(user_info['hp'] + (exp / 2))
            user_mp = int(user_info['mp'] + exp)
            user_atk = int(user_info['atk'] + (exp / 10))
            sql_message.update_exp(user_id, exp)
            sql_message.update_power2(user_id)  # 更新战力
            sql_message.update_user_attribute(user_id, user_hp, user_mp, user_atk)  # 这种事情要放在update_exp方法里
            sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
            msg = f"道友成功使用丹药：{goods_name}{num}颗,修为增加{exp}点！"
    else:
        msg = f"该类型的丹药目前暂时不支持使用！"
    return msg


def get_use_jlq_msg(user_id, goods_id):
    user_info = sql_message.get_user_info_with_id(user_id)
    if user_info['blessed_spot_flag'] == 0:
        msg = f"道友还未拥有洞天福地，无法使用该物品"
    else:
        item_info = items.get_data_by_item_id(goods_id)
        user_buff_data = UserBuffDate(user_id).BuffInfo
        if int(user_buff_data['blessed_spot']) >= item_info['修炼速度']:
            msg = f"该聚灵旗的等级不能满足道友的福地了，使用了也没效果"
        else:
            mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
            mix_elixir_info['药材速度'] = item_info['药材速度']
            save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
            sql_message.update_back_j(user_id, goods_id)
            sql_message.updata_user_blessed_spot(user_id, item_info['修炼速度'])
            msg = f"道友洞天福地的聚灵旗已经替换为：{item_info['name']}"
    return msg


def get_shop_data():
    try:
        data = read_shop()  # 尝试读取商店数据
        if not isinstance(data, dict):
            raise ValueError("读取的数据格式不正确")  # 确保读取到的数据是字典类型
    except Exception as e:
        print(f"读取商店数据时发生错误: {e}")
        data = None  # 如果读取失败，将数据设为 None

    if data is not None:
        save_shop(data)  # 只有在读取成功时才保存数据
    else:
        data = {}  # 如果读取失败，返回一个空字典作为兜底
    
    return data  # 返回商店数据


PATH = Path(__file__).parent
FILEPATH = PATH / 'shop.json'


def read_shop():
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def save_shop(data):
    data = json.dumps(data, ensure_ascii=False, indent=4)
    savemode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=savemode, encoding="UTF-8") as f:
        f.write(data)
        f.close()
    return True
