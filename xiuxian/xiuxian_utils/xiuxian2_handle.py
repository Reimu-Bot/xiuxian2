try:
    import ujson as json
except ImportError:
    import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from nonebot.log import logger
from .data_source import jsondata
from ..xiuxian_config import XiuConfig, convert_rank
from .. import DRIVER
from .item_json import Items
from .xn_xiuxian_impart_config import config_impart
from .xn_xiuxian_impart_config import config_impart
from .xiuxian_data import 灵根_data ,突破概率_data

WORKDATA = Path() / "data" / "xiuxian" / "work"
PLAYERSDATA = Path() / "data" / "xiuxian" / "players"
DATABASE = Path() / "data" / "xiuxian"
DATABASEOLD = Path() / "data" / "xiuxian"
DATABASE_IMPARTBUFF = Path() / "data" / "xiuxian"
SKILLPATHH = DATABASE / "功法"
WEAPONPATH = DATABASE / "装备"
xiuxian_num = "578043031" # 这里其实是修仙1作者的QQ号
impart_num = "123451234"
items = Items()
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')


class XiuxianDateManage:
    global xiuxian_num
    _instance = {}
    _has_init = {}

    def __new__(cls):
        if cls._instance.get(xiuxian_num) is None:
            cls._instance[xiuxian_num] = super(XiuxianDateManage, cls).__new__(cls)
        return cls._instance[xiuxian_num]

    def __init__(self):
        if not self._has_init.get(xiuxian_num):
            self._has_init[xiuxian_num] = True
            self.database_path = DATABASE
            if not self.database_path.exists():
                self.database_path.mkdir(parents=True)
                self.database_path /= "xiuxian.db"
                self.conn = sqlite3.connect(self.database_path, check_same_thread=False)
            else:
                self.database_path /= "xiuxian.db"
                self.conn = sqlite3.connect(self.database_path, check_same_thread=False)
            logger.opt(colors=True).info(f"<green>修仙数据库已连接！</green>")
            self._check_data()

    def close(self):
        self.conn.close()
        logger.opt(colors=True).info(f"<green>修仙数据库关闭！</green>")

    def _check_data(self):
        """检查数据完整性"""
        c = self.conn.cursor()

        for i in XiuConfig().sql_table:
            if i == "user_xiuxian":
                try:
                    c.execute(f"select count(1) from {i}")
                    c.execute("PRAGMA table_info(user_xiuxian)")
                    columns = [col[1] for col in c.fetchall()]                   
                    if 'sign_count' not in columns:
                        c.execute("ALTER TABLE user_xiuxian ADD COLUMN sign_count INTEGER DEFAULT 0")
                    if 'is_shuangxiu' not in columns:
                        c.execute("ALTER TABLE user_xiuxian ADD COLUMN is_shuangxiu INTEGER DEFAULT 0")   
                    if 'is_mijing' not in columns:
                        c.execute("ALTER TABLE user_xiuxian ADD COLUMN is_mijing INTEGER DEFAULT 0")                         
                    if 'invite_num' not in columns:
                        c.execute("ALTER TABLE user_xiuxian ADD COLUMN invite_num INTEGER DEFAULT 0")                                                 
                except sqlite3.OperationalError:
                    c.execute("""CREATE TABLE "user_xiuxian" (
      "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
      "user_id" INTEGER NOT NULL,
      "sect_id" INTEGER DEFAULT NULL,
      "sect_position" INTEGER DEFAULT NULL,
      "stone" integer DEFAULT 0,
      "root" TEXT,
      "root_type" TEXT,
      "level" TEXT,
      "power" integer DEFAULT 0,
      "create_time" integer,
      "is_sign" integer DEFAULT 0,
      "is_beg" integer DEFAULT 0,
      "is_ban" integer DEFAULT 0,
      "exp" integer DEFAULT 0,
      "user_name" TEXT DEFAULT NULL,
      "level_up_cd" integer DEFAULT NULL,
      "level_up_rate" integer DEFAULT 0,
      "sign_count" integer DEFAULT 0,
      "is_shuangxiu" integer DEFAULT 0,
      "is_mijing" integer DEFAULT 0,
      "invite_num" integer DEFAULT 0        
    );""")
            elif i == "user_cd":
                try:
                    c.execute(f"select count(1) from {i}")
                except sqlite3.OperationalError:
                    c.execute("""CREATE TABLE "user_cd" (
  "user_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  "type" integer DEFAULT 0,
  "create_time" integer DEFAULT NULL,
  "scheduled_time" integer,
  "last_check_info_time" integer DEFAULT NULL
);""")
            elif i == "sects":
                try:
                    # 检查表中是否有记录，验证表存在
                    c.execute(f"SELECT count(1) FROM {i}")
                except sqlite3.OperationalError:
                    # 如果表不存在，创建表
                    c.execute("""
                    CREATE TABLE "sects" (
                        "sect_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        "sect_name" TEXT NOT NULL,
                        "sect_owner" INTEGER,
                        "sect_scale" INTEGER NOT NULL,
                        "sect_used_stone" INTEGER,
                        "sect_fairyland" INTEGER
                    );
                    """)
                else:
                    try:
                        # 尝试检查 sect_memo 列是否存在
                        c.execute("SELECT sect_memo FROM sects LIMIT 1")
                    except sqlite3.OperationalError:
                        # 如果没有这个列，添加 sect_memo 列
                        c.execute("ALTER TABLE sects ADD COLUMN sect_memo TEXT")
                      #  print("Added sect_memo column as TEXT")
                      
            elif i == "back":
                try:
                    c.execute(f"select count(1) from {i}")
                except sqlite3.OperationalError:
                    c.execute("""CREATE TABLE "back" (
  "user_id" INTEGER NOT NULL,
  "goods_id" INTEGER NOT NULL,
  "goods_name" TEXT,
  "goods_type" TEXT,
  "goods_num" INTEGER,
  "create_time" TEXT,
  "update_time" TEXT,
  "remake" TEXT,
  "day_num" INTEGER DEFAULT 0,
  "all_num" INTEGER DEFAULT 0,
  "action_time" TEXT,
  "state" INTEGER DEFAULT 0
);""")

            elif i == "BuffInfo":
                try:
                    c.execute(f"select count(1) from {i}")
                except sqlite3.OperationalError:
                    c.execute("""CREATE TABLE "BuffInfo" (
  "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
  "user_id" INTEGER DEFAULT 0,
  "main_buff" integer DEFAULT 0,
  "sec_buff" integer DEFAULT 0,
  "faqi_buff" integer DEFAULT 0,
  "fabao_weapon" integer DEFAULT 0,
  "sub_buff" integer DEFAULT 0
);""")

        try:
            c.execute(f"SELECT count(1) FROM bank")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE "bank" (
                    "user_id" TEXT DEFAULT 0,
                    "savestone" INTEGER DEFAULT 0,
                    "savetime" TEXT,
                    "banklevel" INTEGER DEFAULT 0                    
                );
            """)
            logger.opt(colors=True).info("<green>bank 表已创建！</green>")

        try:
            c.execute(f"SELECT count(1) FROM dungeon")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE "dungeon" (
                    "user_id" TEXT NOT NULL PRIMARY KEY,
                    "floor" INTEGER NOT NULL,
                    "num" INTEGER DEFAULT 0                  
                );
            """)
            logger.opt(colors=True).info("<green>dungeon 表已创建！</green>")

        try:
            c.execute(f"SELECT count(1) FROM boss")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE "boss" (
                    "user_id" TEXT DEFAULT 0,
                    "boss_integral" INTEGER DEFAULT 0                    
                );
            """)
            logger.opt(colors=True).info("<green>bank 表已创建！</green>")
            
        try:
            c.execute(f"SELECT count(1) FROM auction")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE "auction" (
                    "auctionid" TEXT NOT NULL PRIMARY KEY,
                    "auction_id" INTEGER,
                    "seller_id" TEXT DEFAULT 0,
                    "item_quantity" INTEGER DEFAULT 0,                    
                    "start_price" INTEGER DEFAULT 0, 
                    "is_user_auction" TEXT,
                    "newtime" TEXT,
                    "user_id" TEXT DEFAULT 0,
                    "status" INTEGER DEFAULT 1
                );
            """)
            logger.opt(colors=True).info("<green>auction 表已创建！</green>")  

        try:
            c.execute(f"SELECT count(1) FROM Fangshi")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE "Fangshi" (
                    "exchangeid" TEXT NOT NULL PRIMARY KEY,
                    "user_id" TEXT,
                    "goods_name" TEXT,
                    "goods_id" INTEGER,
                    "goods_type" TEXT,                    
                    "price" INTEGER, 
                    "user_name" TEXT,
                    "stock" INTEGER,
                    "uptime" INTEGER NOT NULL
                );
            """)
            logger.opt(colors=True).info("<green>auction 表已创建！</green>")  

        try:
            c.execute(f"SELECT count(1) FROM GIFT")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE IF NOT EXISTS GIFT(
                    "user_id" TEXT NOT NULL,
                    "NUM" INT NOT NULL,
                     PRIMARY KEY(user_id));
            """)
            logger.opt(colors=True).info("<green>auction 表已创建！</green>") 

        try:
            c.execute(f"SELECT count(1) FROM user_tasks")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_tasks(
                    "user_id" TEXT NOT NULL,
                    "task_name" TEXT,
                    "task_content" TEXT,
                    "task_type" TEXT,                    
                     PRIMARY KEY(user_id));
            """)
            logger.opt(colors=True).info("<green>auction 表已创建！</green>") 

        try:
            c.execute(f"SELECT count(1) FROM rift")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE IF NOT EXISTS rift(
                    "rift_name" TEXT NOT NULL,
                    "rift_rank" integer DEFAULT NULL,
                    "rift_count" integer DEFAULT NULL,
                    "rift_time" integer DEFAULT NULL, 
                    "user_id" TEXT NOT NULL,
                     PRIMARY KEY(user_id));                    
            """)
            logger.opt(colors=True).info("<green>auction 表已创建！</green>") 

        try:
            c.execute(f"SELECT count(1) FROM VIP")
        except sqlite3.OperationalError:
            c.execute("""
                CREATE TABLE IF NOT EXISTS VIP(
                    "user_id" TEXT NOT NULL,
                    "start_time" integer DEFAULT NULL,
                    "finish_time" integer DEFAULT NULL,
                     PRIMARY KEY(user_id));
            """)
            logger.opt(colors=True).info("<green>auction 表已创建！</green>")             
            
        for i in XiuConfig().sql_user_xiuxian:
            try:
                c.execute(f"select {i} from user_xiuxian")
            except sqlite3.OperationalError:
                logger.opt(colors=True).info("<yellow>sql_user_xiuxian有字段不存在，开始创建\n</yellow>")
                sql = f"ALTER TABLE user_xiuxian ADD COLUMN {i} INTEGER DEFAULT 0;"
                logger.opt(colors=True).info(f"<green>{sql}</green>")
                c.execute(sql)

        for d in XiuConfig().sql_user_cd:
            try:
                c.execute(f"select {d} from user_cd")
            except sqlite3.OperationalError:
                logger.opt(colors=True).info("<yellow>sql_user_cd有字段不存在，开始创建</yellow>")
                sql = f"ALTER TABLE user_cd ADD COLUMN {d} INTEGER DEFAULT 0;"
                logger.opt(colors=True).info(f"<green>{sql}</green>")
                c.execute(sql)

        for s in XiuConfig().sql_sects:
            try:
                c.execute(f"select {s} from sects")
            except sqlite3.OperationalError:
                logger.opt(colors=True).info("<yellow>sql_sects有字段不存在，开始创建</yellow>")
                sql = f"ALTER TABLE sects ADD COLUMN {s} INTEGER DEFAULT 0;"
                logger.opt(colors=True).info(f"<green>{sql}</green>")
                c.execute(sql)

        for m in XiuConfig().sql_buff:
            try:
                c.execute(f"select {m} from BuffInfo")
            except sqlite3.OperationalError:
                logger.opt(colors=True).info("<yellow>sql_buff有字段不存在，开始创建</yellow>")
                sql = f"ALTER TABLE BuffInfo ADD COLUMN {m} INTEGER DEFAULT 0;"
                logger.opt(colors=True).info(f"<green>{sql}</green>")
                c.execute(sql)

        for b in XiuConfig().sql_back:
            try:
                c.execute(f"select {b} from back")
            except sqlite3.OperationalError:
                logger.opt(colors=True).info("<yellow>sql_back有字段不存在，开始创建</yellow>")
                sql = f"ALTER TABLE back ADD COLUMN {b} INTEGER DEFAULT 0;"
                logger.opt(colors=True).info(f"<green>{sql}</green>")
                c.execute(sql)
        
        # 检查并更新 last_check_info_time 列的记录
        c.execute(f"""UPDATE user_cd
SET last_check_info_time = ?
WHERE last_check_info_time = '0' OR last_check_info_time IS NULL
        """, (current_time,))

        self.conn.commit()

    @classmethod
    def close_dbs(cls):
        XiuxianDateManage().close()

    def _create_user(self, user_id: str, root: str, type: str, power: str, create_time, user_name) -> None:
        """在数据库中创建用户并初始化"""
        c = self.conn.cursor()
        sql = f"INSERT INTO user_xiuxian (user_id,stone,root,root_type,level,power,create_time,user_name,exp,sect_id,sect_position,user_stamina) VALUES (?,0,?,?,'江湖好手',?,?,?,100,NULL,NULL,?)"
        c.execute(sql, (user_id, root, type, power, create_time, user_name,XiuConfig().max_stamina))
        self.conn.commit()

    def get_user_info_with_id(self, user_id):
        """根据USER_ID获取用户信息,不获取功法加成"""
        cur = self.conn.cursor()
        sql = f"select * from user_xiuxian WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None
        
    def get_user_info_with_name(self, user_id):
        """根据user_name获取用户信息"""
        cur = self.conn.cursor()
        sql = f"select * from user_xiuxian WHERE user_name=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def get_max_id(self):
        """获取 user_xiuxian 表中最大的 id"""
        cur = self.conn.cursor()
        # SQL查询语句，获取最大 id
        sql = "SELECT MAX(id) FROM user_xiuxian"
        cur.execute(sql)
        result = cur.fetchone()  # 获取查询结果的第一行

        if result and result[0] is not None:
            return result[0]  # 返回最大的 id
        else:
            return None  # 如果表中没有记录，返回 None

    def update_invite_num(self, user_id, invite_num, key):
        """更新邀请  1为增加，2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = f"UPDATE user_xiuxian SET invite_num=invite_num+? WHERE user_id=?"
            cur.execute(sql, (invite_num, user_id))
            self.conn.commit()
        elif key == 2:
            sql = f"UPDATE user_xiuxian SET invite_num=invite_num-? WHERE user_id=?"
            cur.execute(sql, (invite_num, user_id))
            self.conn.commit()

    def get_user_boss_score(self, user_id):
        """根据USER_ID获取用户信息，包括boss_integral"""
        cur = self.conn.cursor()
        sql = f"select * from boss WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def create_rift_info(self, rift_name, rift_rank, rift_count, rift_time, user_id):
        """插入秘境信息"""    
        sql = 'INSERT OR REPLACE INTO rift (rift_name, rift_rank, rift_count, rift_time, user_id) VALUES (?, ?, ?, ?, ?)'
        cur = self.conn.cursor()
        cur.execute(sql, (rift_name, rift_rank, rift_count, rift_time, user_id))  # 传递参数
        self.conn.commit()

    def get_rift_info(self, rift_name):
        """获取秘境信息"""    
        cur = self.conn.cursor()
        sql = f"select user_id from rift WHERE rift_name=?"
        cur.execute(sql, (rift_name,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def get_rift_count(self):
        """获取 rift 表的记录数"""
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM rift")
        count = c.fetchone()[0]  # 获取计数的结果
        return count

    def list_all_user_ids(self):
        """列出 rift 表中的所有 user_id"""
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM rift")
        user_ids = c.fetchall()  # 获取所有结果
        return [user_id[0] for user_id in user_ids]

    def delete_rifts(self, uid):
        """删除 rift 表中的所有数据"""
        c = self.conn.cursor()
        try:
            c.execute("DELETE FROM rift WHERE user_id = ?", (uid,))
            self.conn.commit()  # 提交更改
            logger.info("数据已成功删除。")
            return True  # 返回成功状态
        except sqlite3.Error as e:
            logger.error(f"删除数据时出错: {e}")
            return False  # 返回失败状态

    def has_rift_info(self, user_id):
        """检查是否存在秘境信息"""
        cur = self.conn.cursor()
        sql = f"select * from rift WHERE user_id = ?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def create_user_sect_task(self, user_id, task_name, task_content, task_type):
        """插入或更新宗门任务"""    
        sql = 'INSERT OR REPLACE INTO user_tasks (user_id, task_name, task_content, task_type) VALUES (?, ?, ?, ?)'
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, task_name, task_content, task_type))  # 传递参数
        self.conn.commit()

    def delete_user_sect_task(self, user_id, task_type):
        """根据 user_id 和 task_type 删除宗门任务"""    
        sql = 'DELETE FROM user_tasks WHERE user_id = ? AND task_type = ?'
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, task_type))  # 传递参数
        self.conn.commit()

    def get_task_info(self, user_id, task_type):
        """获取任务信息"""    
        cur = self.conn.cursor()
        sql = f"select * from user_tasks WHERE user_id=? AND task_type=?"
        cur.execute(sql, (user_id, task_type))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def get_user_vip(self, user_id):
        """根据USER_ID获取用户vip信息"""
        cur = self.conn.cursor()
        sql = f"select * from VIP WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def update_vip(self, user_id, key):
        """
        更新或删除用户的 vip 数据。
        :param user_id: 用户ID
        :param key: 操作类型 (1: 增加finish_time 30天, 2: 删除该用户的所有数据)
        """
        cur = self.conn.cursor()  # 创建游标
        cur.execute("SELECT finish_time FROM VIP WHERE user_id=?", (user_id,))
        result = cur.fetchone()

        if result is None:  # 用户不存在，插入新用户
            if key == 1:
                # 当前时间加上 30 天
                start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                finish_time = (datetime.now() + timedelta(days=31)).strftime('%Y-%m-%d %H:%M:%S.%f')
                cur.execute("INSERT INTO VIP (user_id, start_time, finish_time) VALUES (?, ?, ?)", (user_id, start_time, finish_time))
            elif key == 2:
                pass
        else:  # 用户已存在
            if key == 1:
                # 获取当前时间
                current_time = datetime.now()

                # 解析数据库中的 finish_time
                db_finish_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S.%f")

                # 判断 finish_time 是否大于当前时间
                if db_finish_time > current_time:
                    # 如果 finish_time 已经大于当前时间，增加 30 天
                    finish_time = (db_finish_time + timedelta(days=31)).strftime('%Y-%m-%d %H:%M:%S.%f')
                else:
                    # 如果 finish_time 小于当前时间，设置为当前时间 + 30 天
                    finish_time = (current_time + timedelta(days=31)).strftime('%Y-%m-%d %H:%M:%S.%f')

                # 更新数据库中的 finish_time
                sql = "UPDATE VIP SET finish_time=? WHERE user_id=?"
                cur.execute(sql, (finish_time, user_id))
            elif key == 2:
                # 删除该用户的所有数据
                cur.execute("DELETE FROM VIP WHERE user_id=?", (user_id,))

    def check_vip_status(self, user_id):
        """
        获取用户的剩余 VIP 有效期（天数）。
        :param user_id: 用户ID
        :return: 剩余有效期（天数），如果用户不存在或已过期，则返回 0。
        """
        cur = self.conn.cursor()  # 创建游标
        cur.execute("SELECT finish_time FROM VIP WHERE user_id=?", (user_id,))
        result = cur.fetchone()

        # 获取 finish_time
        current_time = datetime.now()

        if result:  # 如果用户存在
            finish_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S.%f")

            if current_time < finish_time:
                remaining_days = (finish_time - current_time).days  # 计算剩余天数
                return remaining_days  # 返回剩余天数
            else:
                return 0  # VIP已过期
        else:
            return 0                

    def update_boss_score(self, user_id, boss_integral, key):
        """
        更新或插入用户的 boss 积分。
        :param user_id: 用户ID
        :param boss_integral: 积分值
        :param key: 操作类型 (1: 增加积分, 2: 减少积分)
        """
        cur = self.conn.cursor()  # 创建游标
        cur.execute("SELECT boss_integral FROM boss WHERE user_id=?", (user_id,))
        result = cur.fetchone()

        if result is None:  # 用户不存在，插入新用户
            if key == 1:
                # 插入新用户并设置初始积分
                cur.execute("INSERT INTO boss (user_id, boss_integral) VALUES (?, ?)", (user_id, boss_integral))
            elif key == 2:
                # 如果减少积分，确保初始积分为0
                cur.execute("INSERT INTO boss (user_id, boss_integral) VALUES (?, ?)", (user_id, 0 - boss_integral))
        else:  # 用户已存在，更新积分
            if key == 1:
                sql = "UPDATE boss SET boss_integral=boss_integral+? WHERE user_id=?"
                cur.execute(sql, (boss_integral, user_id))
            elif key == 2:
                sql = "UPDATE boss SET boss_integral=boss_integral-? WHERE user_id=?"
                cur.execute(sql, (boss_integral, user_id))

        self.conn.commit() 

    def new_exchange(self, exchangeid, user_id, goods_name, goods_id, goods_type, price, user_name, stock, uptime):
        """插入或更新坊市物品"""
        sql = 'INSERT OR REPLACE INTO Fangshi (exchangeid, user_id, goods_name, goods_id, goods_type, price, user_name, stock, uptime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        cur = self.conn.cursor()
        cur.execute(sql, (exchangeid, user_id, goods_name, goods_id, goods_type, price, user_name, stock, uptime))  # 传递参数
        self.conn.commit()

    def get_exchange_list_my(self, user_id, page=0):
        num = 30
        startnum = num * page
        try:
            cur = self.conn.cursor()
            
            # 使用参数化查询来避免SQL注入
            sql = """
            SELECT exchangeid, goods_name, goods_type, price, stock, goods_id
            FROM Fangshi 
            WHERE stock > 0 AND user_id = ? 
            ORDER BY goods_name ASC, price ASC 
            LIMIT ?, ?
            """
            
            # 执行查询，并将参数传递
            cur.execute(sql, (user_id, startnum, num))
            r = cur.fetchall()  # 获取查询结果

            if r:
                # 执行计数查询，使用参数化
                count_sql = "SELECT COUNT(exchangeid) AS exchangenum FROM Fangshi WHERE stock > 0 AND user_id = ?"
                cur.execute(count_sql, (user_id,))
                num_result = cur.fetchone()  # 获取总数
                return num_result[0], r  # 返回总数和结果列表
            else:
                return 0, []  # 返回空列表
        except Exception as e:
            print(f'查找表发生错误: {e}')  # 增强调试信息
            raise
        finally:
            cur.close()  # 确保游标关闭

    def get_exchange_list_time(self, findtime):
        try:
            cur = self.conn.cursor()
            
            sql = """
            SELECT exchangeid, user_id, goods_name, goods_id, goods_type, stock 
            FROM Fangshi 
            WHERE uptime < ?
            """
            
            # 执行查询，并将参数传递
            cur.execute(sql, (findtime,))
            r = cur.fetchall()  # 获取查询结果
            
            if r:
                return r  # 返回结果
            else:
                return []  # 返回空列表
        except Exception as e:
            print(f'查找表发生错误: {e}')  # 增强调试信息
            raise
        finally:
            cur.close()  # 确保游标关闭


    def get_exchange_list_goods_type(self, goods_type, page=0):
        num = 30
        startnum = num * page
        try:
            cur = self.conn.cursor()
            
            # 使用参数化查询来避免SQL注入
            sql = """
            SELECT exchangeid, goods_type, goods_name,goods_id, stock, price 
            FROM Fangshi 
            WHERE stock > 0 AND goods_type = ? 
            ORDER BY goods_name ASC, price ASC 
            LIMIT ?, ?
            """
            # 执行查询，并将参数传递
            cur.execute(sql, (goods_type, startnum, num))
            r = cur.fetchall()
            
            if r:
                # 执行计数查询，使用参数化
                cursornum = cur.execute("SELECT COUNT(exchangeid) AS exchangenum FROM Fangshi WHERE stock > 0 AND goods_type = ?", (goods_type,))
                num_result = cursornum.fetchone()  # 获取总数
                return num_result[0], r  # 返回总数和结果列表
            else:
                return 0, []  # 返回空列表
        except Exception as e:
            print(f'查找表发生错误: {e}')  # 增强调试信息
            raise
        finally:
            cur.close()  # 确保游标关闭
            
    def get_exchange_list_goods_name(self, goods_type, goods_name, page=0):
        num = 30
        startnum = num * page
        try:
            cur = self.conn.cursor()
            
            # 使用参数化查询来避免SQL注入
            sql = """
            SELECT exchangeid, goods_type, goods_name, goods_id, stock, price 
            FROM Fangshi 
            WHERE stock > 0 AND goods_type = ? AND goods_name = ? 
            ORDER BY goods_name ASC, price ASC 
            LIMIT ?, ?
            """
            
            # 执行查询并传递参数
            cur.execute(sql, (goods_type, goods_name, startnum, num))
            r = cur.fetchall()

            if r:
                # 执行计数查询，使用参数化
                count_sql = "SELECT COUNT(exchangeid) AS exchangenum FROM Fangshi WHERE stock > 0 AND goods_type = ? AND goods_name = ?"
                cur.execute(count_sql, (goods_type, goods_name))
                num_result = cur.fetchone()  # 获取总数
                return num_result[0], r  # 返回结果
            else:
                return 0, []  # 返回空列表
        except Exception as e:
            print(f'查找表发生错误: {e}')  # 增加强调调试信息
            raise
        finally:
            cur.close()  # 确保游标关闭

    def get_exchange_list(self, page=0):
        num = 30
        startnum = num * page
        try:
            cur = self.conn.cursor()
            
            # 直接将startnum和num嵌入SQL字符串中
            sql = f"""
            SELECT exchangeid, goods_type, goods_name, goods_id, stock, price 
            FROM Fangshi 
            WHERE stock > 0 
            ORDER BY goods_name ASC, price ASC 
            LIMIT {startnum}, {num}
            """
            cur.execute(sql)  # 不需要参数化

            r = cur.fetchall()
            if r:
                # 执行计数查询
                cur.execute("SELECT COUNT(exchangeid) AS exchangenum FROM Fangshi WHERE stock > 0")
                num_result = cur.fetchone()  # 获取总数
                return num_result[0], r  # 返回总数和结果列表
            else:
                return 0, []  # 返回空列表
        except Exception as e:
            print(f'查找表发生错误: {e}')  # 增加错误信息输出
            raise
        finally:
            cur.close()  # 确保游标关闭

    def get_exchange_info(self, exchangeid):
        try:
            cur = self.conn.cursor()
            
            # 使用参数化查询来避免SQL注入
            sql = """
            SELECT goods_name, goods_type, goods_id, stock, price, user_id 
            FROM Fangshi 
            WHERE exchangeid = ?
            """
            
            # 执行查询并传递参数
            cur.execute(sql, (exchangeid,))
            r = cur.fetchall()
            
            if r:
                return r[0]  # 返回查询到的第一条记录
            else:
                return 0  # 返回0表示没有找到
        except Exception as e:
            print(f'查找表发生错误: {e}')  # 输出错误信息以供调试
            raise
        finally:
            cur.close()  # 确保游标关闭
          
    def delete_exchange(self, exchangeid):
        try:
            cur = self.conn.cursor()
            
            # 使用参数化查询来避免SQL注入
            sql = "DELETE FROM Fangshi WHERE exchangeid = ?"
            cur.execute(sql, (exchangeid,))  # 传递参数
            self.conn.commit()  # 提交更改
        except Exception as e:
            print(f'删除操作发生错误: {e}')  # 输出错误信息以供调试
            raise
        finally:
            cur.close()  # 确保游标关闭

    def update_exchange(self, exchangeid, stock):
        exchange_num = sql_message.get_exchange_num(exchangeid)
        
        if exchange_num is None:
            raise ValueError(f'没有找到 ID 为 {exchangeid} 的记录')  # 处理未找到的情况

        now_num = int(exchange_num) + stock  # 假设 stock 是要增加的数量

        try:
            cur = self.conn.cursor()
            
            # 使用参数化查询来避免SQL注入
            sql = "UPDATE Fangshi SET stock = ? WHERE exchangeid = ?"
            cur.execute(sql, (now_num, exchangeid))  # 传递参数
            self.conn.commit()  # 提交更改
        except Exception as e:
            print(f'更新操作发生错误: {e}')  # 输出错误信息以供调试
            raise
        finally:
            cur.close()  # 确保游标关闭


    def get_exchange_num(self, exchangeid):
        try:
            cur = self.conn.cursor()
            sql = "SELECT stock FROM Fangshi WHERE exchangeid = ?"
            cur.execute(sql, (exchangeid,))  # 传递参数
            result = cur.fetchone()  # 获取一条结果
            
            if result is not None:
                return result[0]  # 返回库存数量
            else:
                return None  # 如果没有找到记录，返回 None
        except Exception as e:
            print(f'获取库存操作发生错误: {e}')  # 输出错误信息以供调试
            raise
        finally:
            cur.close()  # 确保游标关闭
 
    def update_all_users_stamina(self, max_stamina, stamina_recovery_rate):
        """体力未满用户更新体力值"""
        cur = self.conn.cursor()
        sql = f"""
            UPDATE user_xiuxian
            SET user_stamina = MIN(user_stamina + ?, ?)
            WHERE user_stamina < ?
        """
        cur.execute(sql, (stamina_recovery_rate, max_stamina, max_stamina))
        self.conn.commit()

    def update_user_stamina(self, user_id, stamina_change, key):
        """更新用户体力值 1为增加，2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = f"UPDATE user_xiuxian SET user_stamina=user_stamina+? WHERE user_id=?"
            cur.execute(sql, (stamina_change, user_id))
            self.conn.commit()
        elif key == 2:
            sql = f"UPDATE user_xiuxian SET user_stamina=user_stamina-? WHERE user_id=?"
            cur.execute(sql, (stamina_change, user_id))
            self.conn.commit()
 
    def get_user_real_info(self, user_id):
        """根据USER_ID获取用户信息,获取功法加成"""
        cur = self.conn.cursor()
        sql = f"select * from user_xiuxian WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = cur.description
            user_data_dict = final_user_data(result, columns)
            return user_data_dict
        else:
            return None
            
    def new_gift_info(self, user_id):
        """插入或更新礼物信息，若没有则初始化为0"""
        sql = 'INSERT OR REPLACE INTO GIFT (user_id, NUM) VALUES (?, ?)'
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, 0))  # 传递参数
        self.conn.commit()

    def get_gift_info(self, user_id):
        """获取礼物信息，如果不存在则初始化为0并返回"""
        sql = 'SELECT NUM FROM GIFT WHERE user_id = ?'
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))  # 传递参数
        result = cur.fetchone()  # 使用 fetchone 而不是 fetchall 因为只需要一个结果
        if result:
            return result[0]
        else:
            self.new_gift_info(user_id)
            return 0  # 初始化返回 0

    def update_gift(self, user_id, num):
        """更新礼物数量"""
        sql = 'UPDATE GIFT SET NUM = ? WHERE user_id = ?'
        cur = self.conn.cursor()
        cur.execute(sql, (num, user_id))  # 传递参数
        self.conn.commit()

    def reset_all_gift_nums(self):
        """重置所有用户的礼物数量为0"""
        sql = 'UPDATE GIFT SET NUM = ?'
        cur = self.conn.cursor()
        cur.execute(sql, (0,))  # 将所有 NUM 值更新为 0
        self.conn.commit()
        logger.opt(colors=True).info("<green>所有用户的 NUM 值已重置为 0！</green>")
       

    def get_sect_info(self, sect_id):
        """
        通过宗门编号获取宗门信息
        :param sect_id: 宗门编号
        :return:
        """
        cur = self.conn.cursor()
        sql = f"select * from sects WHERE sect_id=?"
        cur.execute(sql, (sect_id,))
        result = cur.fetchone()
        if result:
            sect_id_dict = dict(zip((col[0] for col in cur.description), result))
            return sect_id_dict
        else:
            return None
        
    def get_sect_owners(self):
        """获取所有宗主的 user_id"""
        cur = self.conn.cursor()
        sql = f"SELECT user_id FROM user_xiuxian WHERE sect_position = 0"
        cur.execute(sql)
        result = cur.fetchall()
        return [row[0] for row in result]
    
    def get_elders(self):
        """获取所有长老的 user_id"""
        cur = self.conn.cursor()
        sql = f"SELECT user_id FROM user_xiuxian WHERE sect_position = 1"
        cur.execute(sql)
        result = cur.fetchall()
        return [row[0] for row in result]

    def get_users_by_sect_and_position(self, sect_id, sect_position):
        """获取特定宗门和特定职位的所有 user_id"""
        cur = self.conn.cursor()
        sql = f"SELECT user_id FROM user_xiuxian WHERE sect_position = ? AND sect_id = ?"
        cur.execute(sql, (sect_position, sect_id))
        result = cur.fetchall()
        return [row[0] for row in result]  

    def create_user(self, user_id, *args):
        """校验用户是否存在"""
        cur = self.conn.cursor()
        sql = f"select * from user_xiuxian WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if not result:
            self._create_user(user_id, args[0], args[1], args[2], args[3], args[4]) # root, type, power, create_time, user_name
            self.conn.commit()
            welcome_msg = f"欢迎进入修仙世界 \n如想修改灵根请输入<qqbot-cmd-input text=\"重入仙途\" show=\"重入仙途\" />重入仙途。\n强烈建议道友使用<qqbot-cmd-input text=\"修改道号 \" show=\"修改道号\" />改个心仪的道号，道号为战斗唯一标识符。\n你的灵根：{args[0]} \n类型：{args[1]} \n你的战力：{args[2]} \n当前境界：江湖好手"
            return True, welcome_msg
        else:
            return False, f"道友您已迈入修仙世界，输入<qqbot-cmd-input text=\"修仙帮助\" show=\"修仙帮助\" /> \n开始您的修仙之旅吧！如想修改灵根请输入<qqbot-cmd-input text=\"重入仙途\" show=\"重入仙途\" />重入仙途。\n强烈建议道友使用<qqbot-cmd-input text=\"修改道号 \" show=\"修改道号\" />改个心仪的道号，道号为战斗唯一标识符。" 

    def get_sign(self, user_id):
        """获取用户签到信息"""
        cur = self.conn.cursor()
        # 查询用户的签到信息，包括是否已签到和签到次数
        sql = "SELECT is_sign, sign_count FROM user_xiuxian WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()

        if not result:
            return "修仙界没有你的足迹，输入 '我要修仙' 加入修仙世界吧！"
        
        # 如果今天还没有签到
        elif result[0] == 0:
            user_vip_days = sql_message.check_vip_status(user_id)  # 确认 VIP 状态
            if user_vip_days > 0:  # 检查用户是否为 VIP
                ls = random.randint(XiuConfig().sign_in_lingshi_lower_limit, XiuConfig().sign_in_lingshi_upper_limit) * 2
                vip_message = "由于您是月卡用户，可享受双倍灵石奖励！"
            else:        
                ls = random.randint(XiuConfig().sign_in_lingshi_lower_limit, XiuConfig().sign_in_lingshi_upper_limit)
                vip_message = ""  

            new_sign_count = result[1] + 1  # 增加签到次数
            spls = 66666666  # 特别奖励的灵石数目

            # 如果累计签到超过100次，给予特别奖励
            if new_sign_count == 100:
                sql2 = "UPDATE user_xiuxian SET is_sign=1, stone=stone+?, sign_count=sign_count+1 WHERE user_id=?"
                cur.execute(sql2, (spls, user_id))
                self.conn.commit()
                return f"仙途漫漫，今日您又迈出了一步。恭喜你，累积签到已达{new_sign_count}次。天赐祥瑞，获赠{spls}块灵石，以助您修行之路更加顺畅!"
            else:
                sql2 = "UPDATE user_xiuxian SET is_sign=1, stone=stone+?, sign_count=sign_count+1 WHERE user_id=?"
                cur.execute(sql2, (ls, user_id))
                self.conn.commit()
                return f"签到成功！{vip_message}，获取{ls}块灵石！已签到{new_sign_count}次。"
       
        # 如果已经签到过
        elif result[0] == 1:
            return "贪心的人是不会有好运的！"
        
    def get_beg(self, user_id):
        """获取仙途奇缘信息"""
        cur = self.conn.cursor()
        sql = f"select is_beg from user_xiuxian WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result[0] == 0:
            ls = random.randint(XiuConfig().beg_lingshi_lower_limit, XiuConfig().beg_lingshi_upper_limit)
            sql2 = f"UPDATE user_xiuxian SET is_beg=1,stone=stone+? WHERE user_id=?"
            cur.execute(sql2, (ls,user_id))
            self.conn.commit()
            return ls
        elif result[0] == 1:
            return None

    def ramaker(self, lg, type, user_id):
        """洗灵根"""
        cur = self.conn.cursor()
        sql = f"UPDATE user_xiuxian SET root=?,root_type=?,stone=stone-? WHERE user_id=?"
        cur.execute(sql, (lg, type, XiuConfig().remake, user_id))
        self.conn.commit()

        self.update_power2(user_id) # 更新战力
        return f"逆天之行，重获新生，新的灵根为：{lg}，类型为：{type}"

    def get_root_rate(self, name):
        """获取灵根倍率"""
        data = jsondata.root_data()
        return data[name]['type_speeds']

    def get_level_power(self, name):
        """获取境界倍率|exp"""
        data = jsondata.level_data()
        return data[name]['power']
    
    def get_level_cost(self, name):
        """获取炼体境界倍率"""
        data = jsondata.exercises_level_data()
        return data[name]['cost_exp'], data[name]['cost_stone']

    def update_power2(self, user_id) -> None:
        """更新战力"""
        UserMessage = self.get_user_info_with_id(user_id)
        cur = self.conn.cursor()
        level = jsondata.level_data()
        root = jsondata.root_data()
        sql = f"UPDATE user_xiuxian SET power=round(exp*?*?,0) WHERE user_id=?"
        cur.execute(sql, (root[UserMessage['root_type']]["type_speeds"], level[UserMessage['level']]["spend"], user_id))
        self.conn.commit()

    def update_ls(self, user_id, price, key):
        """更新灵石  1为增加，2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = f"UPDATE user_xiuxian SET stone=stone+? WHERE user_id=?"
            cur.execute(sql, (price, user_id))
            self.conn.commit()
        elif key == 2:
            sql = f"UPDATE user_xiuxian SET stone=stone-? WHERE user_id=?"
            cur.execute(sql, (price, user_id))
            self.conn.commit()

    def update_shuangxiu(self, user_id=None, is_shuangxiu=None, key=None, reset_all=False):
        """更新双修次数，1为增加，2为减少，reset_all为True时重置为0"""
        cur = self.conn.cursor()

        if reset_all:
            # 将所有用户的 is_shuangxiu 设置为 0
            sql = "UPDATE user_xiuxian SET is_shuangxiu = 0"
            cur.execute(sql)
        else:
            if key == 1:
                sql = "UPDATE user_xiuxian SET is_shuangxiu = is_shuangxiu + ? WHERE user_id = ?"
                cur.execute(sql, (is_shuangxiu, user_id))
            elif key == 2:
                sql = "UPDATE user_xiuxian SET is_shuangxiu = is_shuangxiu - ? WHERE user_id = ?"
                cur.execute(sql, (is_shuangxiu, user_id))
        
        self.conn.commit()

    def update_mijing(self, user_id=None, is_mijing=None, key=None, reset_all=False):
        """更新双修次数，1为增加，2为减少，reset_all为True时重置为0"""
        cur = self.conn.cursor()

        if reset_all:
            # 将所有用户的 is_mijing 设置为 0
            sql = "UPDATE user_xiuxian SET is_mijing = 0"
            cur.execute(sql)
        else:
            if key == 1:
                sql = "UPDATE user_xiuxian SET is_mijing = is_mijing + ? WHERE user_id = ?"
                cur.execute(sql, (is_mijing, user_id))
            elif key == 2:
                sql = "UPDATE user_xiuxian SET is_mijing = is_mijing - ? WHERE user_id = ?"
                cur.execute(sql, (is_mijing, user_id))
        
        self.conn.commit()

    def update_root1(self, user_id, key):
        """更新灵根  1为混沌,2为融合,3为超,4为龙,5为天,6为千世,7为万世"""
        cur = self.conn.cursor()
        if int(key) == 1:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, ("全属性灵根", "混沌灵根", user_id))
            root_name = "混沌灵根"
            self.conn.commit()
            
        elif int(key) == 2:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, ("融合万物灵根", "融合灵根", user_id))
            root_name = "融合灵根"
            self.conn.commit()
            
        elif int(key) == 3:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, ("月灵根", "超灵根", user_id))
            root_name = "超灵根"
            self.conn.commit()
            
        elif int(key) == 4:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, ("言灵灵根", "龙灵根", user_id))
            root_name = "龙灵根"
            self.conn.commit()
            
        elif int(key) == 5:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, ("金灵根", "天灵根", user_id))
            root_name = "天灵根"
            self.conn.commit()
            
        elif int(key) == 6:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, ("轮回千次不灭，只为臻至巅峰", "轮回道果", user_id))
            root_name = "轮回道果"
            self.conn.commit()
            
        elif int(key) == 7:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, ("轮回万次不灭，只为超越巅峰", "真·轮回道果", user_id))
            root_name = "真·轮回道果"
            self.conn.commit()

        return root_name  # 返回灵根名称

    def update_root(self, user_id, key, rootname):
        """更新灵根  1为混沌,2为融合,3为超,4为龙,5为天,6为千世,7为万世,8为异世,9为机械"""
        cur = self.conn.cursor()
        if int(key) == 1:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "混沌灵根", user_id))
            root_name = "混沌灵根"
            self.conn.commit()
            
        elif int(key) == 2:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "融合灵根", user_id))
            root_name = "融合灵根"
            self.conn.commit()
            
        elif int(key) == 3:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "超灵根", user_id))
            root_name = "超灵根"
            self.conn.commit()
            
        elif int(key) == 4:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "龙灵根", user_id))
            root_name = "龙灵根"
            self.conn.commit()
            
        elif int(key) == 5:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "天灵根", user_id))
            root_name = "天灵根"
            self.conn.commit()
            
        elif int(key) == 6:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "轮回道果", user_id))
            root_name = "轮回道果"
            self.conn.commit()
            
        elif int(key) == 7:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "真·轮回道果", user_id))
            root_name = "真·轮回道果"
            self.conn.commit()
            
        elif int(key) == 8:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "异世界之力", user_id))
            root_name = "异世界之力"
            self.conn.commit()

        elif int(key) == 9:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "机械核心", user_id))
            root_name = "机械核心"
            self.conn.commit()            

        elif int(key) == 10:
            sql = f"UPDATE user_xiuxian SET root=?,root_type=? WHERE user_id=?"
            cur.execute(sql, (rootname, "生命的尽头", user_id))
            root_name = "生命的尽头"
            self.conn.commit() 

        return root_name  # 返回灵根名称

    def update_ls_all(self, price):
        """所有用户增加灵石"""
        cur = self.conn.cursor()
        sql = f"UPDATE user_xiuxian SET stone=stone+?"
        cur.execute(sql, (price,))
        self.conn.commit()

    def update_ls_all_s(self, price, min_level):
        """给达到 gift_min_level 或以上等级的用户增加灵石"""
        cur = self.conn.cursor()

        # 只更新满足 gift_min_level 条件的用户
        sql = f"""
        UPDATE user_xiuxian 
        SET stone = stone + ? 
        WHERE exp >= ?
        """
        cur.execute(sql, (price, min_level))
        self.conn.commit()
    
    def get_exp_rank(self, user_id):
        """修为排行"""
        sql = f"select rank from(select user_id,exp,dense_rank() over (ORDER BY exp desc) as 'rank' FROM user_xiuxian) WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        return result

    def get_stone_rank(self, user_id):
        """灵石排行"""
        sql = f"select rank from(select user_id,stone,dense_rank() over (ORDER BY stone desc) as 'rank' FROM user_xiuxian) WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        return result
    
    def get_ls_rank(self):
        """灵石排行榜"""
        sql = f"SELECT user_id,stone FROM user_xiuxian  WHERE stone>0 ORDER BY stone DESC LIMIT 5"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result

    def sign_remake(self):
        """重置签到"""
        sql = f"UPDATE user_xiuxian SET is_sign=0"
        cur = self.conn.cursor()
        cur.execute(sql, )
        self.conn.commit()

    def beg_remake(self):
        """重置仙途奇缘"""
        sql = f"UPDATE user_xiuxian SET is_beg=0"
        cur = self.conn.cursor()
        cur.execute(sql, )
        self.conn.commit()

    def new_dungeon(self, user_id):
        """插入或更新妖塔"""
        sql = 'INSERT OR REPLACE INTO dungeon (user_id, floor, num) VALUES (?, ?, ?)'
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, 0, 0))  # 传递参数
        self.conn.commit()

    def update_dungeon(self, user_id, dungeon_num, cishu):
        """更新妖界塔"""
        cur = self.conn.cursor()
        sql = f"UPDATE dungeon SET floor=?, num=? WHERE user_id=?"
        cur.execute(sql, (dungeon_num, cishu, user_id))
        self.conn.commit()

    def get_dungeon_info(self, user_id):
        try:
            cur = self.conn.cursor()
            
            # 使用参数化查询来避免SQL注入
            sql = """
            SELECT floor, num 
            FROM dungeon 
            WHERE user_id = ?
            """
            cur.execute(sql, (user_id,))
            r = cur.fetchall()
            
            if r:
                return r[0]  
            else:
                self.new_dungeon(user_id)            
                return 0  # 返回0表示没有找到
        except Exception as e:
            print(f'查找表发生错误: {e}') 
            raise
        finally:
            cur.close()  

    def get_dungeon_list(self):
        """妖界塔排行榜"""
        sql = f"SELECT user_id,floor FROM dungeon WHERE floor>0 ORDER BY floor DESC LIMIT 50"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result

    def ban_user(self, user_id):
        """小黑屋"""
        sql = f"UPDATE user_xiuxian SET is_ban=1 WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_user_name(self, user_id, user_name):
        """更新用户道号"""
        cur = self.conn.cursor()
        get_name = f"select user_name from user_xiuxian WHERE user_name=?"
        cur.execute(get_name, (user_name,))
        result = cur.fetchone()
        if result:
            return f"道号既定，修行已久，然天地法则，变动不居。提醒道友，已有其他道友取得该道号，请<qqbot-cmd-input text=\"修改道号\" show=\"重新获取\" /> ！"
        else:
            sql = f"UPDATE user_xiuxian SET user_name=? WHERE user_id=?"

            cur.execute(sql, (user_name, user_id))
            self.conn.commit()
            return f'道友***{user_name}***，穿越时空的秘境，触摸宇宙的脉动，汝之道号今朝蜕变，如星辰重生，于神秘幽暗中绽放无尽光芒。'

    def updata_level_cd(self, user_id):
        """更新破镜CD"""
        sql = f"UPDATE user_xiuxian SET level_up_cd=? WHERE user_id=?"
        cur = self.conn.cursor()
        now_time = datetime.now()
        cur.execute(sql, (now_time, user_id))
        self.conn.commit()
    
    def update_last_check_info_time(self, user_id):
        """更新查看修仙信息时间"""
        sql = "UPDATE user_cd SET last_check_info_time = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        now_time = datetime.now()
        cur.execute(sql, (now_time, user_id))
        self.conn.commit()

    def get_last_check_info_time(self, user_id):
        """获取最后一次查看修仙信息时间"""
        cur = self.conn.cursor()
        sql = "SELECT last_check_info_time FROM user_cd WHERE user_id = ?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
           return datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S.%f')
        else:
            return None
        
    
    def updata_level(self, user_id, level_name):
        """更新境界"""
        sql = f"UPDATE user_xiuxian SET level=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (level_name, user_id))
        self.conn.commit()


    def get_user_cd(self, user_id):
        """
        获取用户操作CD
        :param user_id: QQ
        :return: 用户CD信息的字典
        """
        sql = f"SELECT * FROM user_cd  WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_cd_dict = dict(zip(columns, result))
            return user_cd_dict
        else:
            self.insert_user_cd(user_id)
            return None

    def insert_user_cd(self, user_id) -> None:
        """
        添加用户至CD表
        :param user_id: qq
        :return:
        """
        sql = f"INSERT INTO user_cd (user_id) VALUES (?)"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()


    def create_sect(self, user_id, sect_name) -> None:
        """
        创建宗门
        :param user_id:qq
        :param sect_name:宗门名称
        :return:
        """
        sql = f"INSERT INTO sects(sect_name, sect_owner, sect_scale, sect_used_stone) VALUES (?,?,0,0)"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_name, user_id))
        self.conn.commit()

    def update_sect_name(self, sect_id, sect_name) -> None:
        """
        修改宗门名称
        :param sect_id: 宗门id
        :param sect_name: 宗门名称
        :return: 返回是否更新成功的标志，True表示更新成功，False表示更新失败（已存在同名宗门）
        """
        cur = self.conn.cursor()
        get_sect_name = f"select sect_name from sects WHERE sect_name=?"
        cur.execute(get_sect_name, (sect_name,))
        result = cur.fetchone()
        if result:
            return False
        else:
            sql = f"UPDATE sects SET sect_name=? WHERE sect_id=?"
            cur = self.conn.cursor()
            cur.execute(sql, (sect_name, sect_id))
            self.conn.commit()
            return True

    def get_sect_info_by_qq(self, user_id):
        """
        通过用户qq获取宗门信息
        :param user_id:
        :return:
        """
        cur = self.conn.cursor()
        sql = f"select * from sects WHERE sect_owner=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            sect_onwer_dict = dict(zip(columns, result))
            return sect_onwer_dict
        else:
            return None

    def get_sect_info_by_id(self, sect_id):
        """
        通过宗门id获取宗门信息
        :param sect_id:
        :return:
        """
        cur = self.conn.cursor()
        sql = f"select * from sects WHERE sect_id=?"
        cur.execute(sql, (sect_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            sect_dict = dict(zip(columns, result))
            return sect_dict
        else:
            return None
        

    def update_usr_sect(self, user_id, usr_sect_id, usr_sect_position):
        """
        更新用户信息表的宗门信息字段
        :param user_id:
        :param usr_sect_id:
        :param usr_sect_position:
        :return:
        """
        sql = f"UPDATE user_xiuxian SET sect_id=?,sect_position=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (usr_sect_id, usr_sect_position, user_id))
        self.conn.commit()

    def update_sect_owner(self, user_id, sect_id):
        """
        更新宗门所有者
        :param user_id:
        :param usr_sect_id:
        :return:
        """
        sql = f"UPDATE sects SET sect_owner=? WHERE sect_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, sect_id))
        self.conn.commit()

    def get_highest_contrib_user_except_current(self, sect_id, current_owner_id):
        """
        获取指定宗门的贡献最高的人，排除当前宗主
        :param sect_id: 宗门ID
        :param current_owner_id: 当前宗主的ID
        :return: 贡献最高的人的ID，如果没有则返回None
        """
        cur = self.conn.cursor()
        sql = """
        SELECT user_id
        FROM user_xiuxian
        WHERE sect_id = ? AND sect_position = 1 AND user_id != ?
        ORDER BY sect_contribution DESC
        LIMIT 1
        """
        cur.execute(sql, (sect_id, current_owner_id))
        result = cur.fetchone()
        if result:
            return result
        else:
            return None


    def get_all_sect_id(self):
        """获取全部宗门id"""
        sql = "SELECT sect_id FROM sects"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        if result:
            return result
        else:
            return None

    def get_all_user_id(self):
        """获取全部用户id"""
        sql = "SELECT user_id FROM user_xiuxian"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        if result:
            return [row[0] for row in result]
        else:
            return None


    def in_closing(self, user_id, the_type):
        """
        更新用户操作CD
        :param user_id: qq
        :param the_type: 0:无状态  1:闭关中  2:历练中
        :return:
        """
        now_time = None
        if the_type == 1:
            now_time = datetime.now()
        elif the_type == 0:
            now_time = 0
        elif the_type == 2:
            now_time = datetime.now()
        sql = "UPDATE user_cd SET type=?,create_time=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (the_type, now_time, user_id))
        self.conn.commit()


    def update_exp(self, user_id, exp):
        """增加修为"""
        sql = "UPDATE user_xiuxian SET exp=exp+? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (int(exp), user_id))
        self.conn.commit()

    def update_j_exp(self, user_id, exp):
        """减少修为"""
        sql = "UPDATE user_xiuxian SET exp=exp-? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (int(exp), user_id))
        self.conn.commit()

    def del_exp_decimal(self, user_id, exp):
        """去浮点"""
        sql = "UPDATE user_xiuxian SET exp=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (int(exp), user_id))
        self.conn.commit()

    
    def realm_top(self):
        """境界排行榜前50"""
        rank_mapping = {rank: idx for idx, rank in enumerate(convert_rank('江湖好手')[1])}
    
        sql = """SELECT user_name, level, exp FROM user_xiuxian 
            WHERE user_name IS NOT NULL
            ORDER BY exp DESC, (CASE level """
    
        for level, value in sorted(rank_mapping.items(), key=lambda x: x[1], reverse=True):
            sql += f"WHEN '{level}' THEN '{value:02}' "
    
        sql += """ELSE level END) ASC LIMIT 50"""
    
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result

    def update_all_auction_status(self, status):
        """
        更新所有拍卖品的状态信息
        :param status: 新的拍卖状态 (例如: '1', '0' 等)
        """
        cur = self.conn.cursor()
        
        # 更新所有拍卖品状态的 SQL 语句
        update_query = '''
        UPDATE auction
        SET status = ?
        '''
        
        # 执行更新
        try:
            cur.execute(update_query, (status,))
            self.conn.commit()  # 提交事务
            print(f"所有拍卖品的状态已成功更新为 {status}！")
        except sqlite3.Error as e:
            print(f"数据库更新失败：{e}")
            self.conn.rollback()  # 回滚事务
        finally:
            cur.close()

    def remove_all_auctions(self):
        """
        移除所有拍卖品信息
        """
        cur = self.conn.cursor()
        
        # 移除所有拍卖品的 SQL 语句
        delete_query = '''
        DELETE FROM auction
        '''
        
        # 执行删除操作
        try:
            cur.execute(delete_query)
            self.conn.commit()  # 提交事务
            print("所有拍卖品信息已成功移除！")
        except sqlite3.Error as e:
            print(f"数据库操作失败：{e}")
            self.conn.rollback()  # 回滚事务
        finally:
            cur.close()
        

    def update_auction_info(self, start_price, newtime, user_id, auctionid):
        """
        更新单个拍卖信息
        :param start_price: 起始价格
        :param newtime: 新的时间
        :param user_id: 用户 ID
        :param auction_id: 拍卖 ID
        """
        cur = self.conn.cursor()
        
        # 更新数据的 SQL 语句
        update_query = '''
        UPDATE auction
        SET start_price = ?, newtime = ?, user_id = ?
        WHERE auctionid = ?
        '''
        
        # 执行更新
        try:
            cur.execute(update_query, (start_price, newtime, user_id, auctionid))
            self.conn.commit()  # 提交事务
            print("拍卖品信息已成功更新！")
        except sqlite3.Error as e:
            print(f"数据库更新失败：{e}")
            self.conn.rollback()  # 回滚事务
        finally:
            cur.close()

    def update_auction_info_byid(self, auctionid, auction_id, seller_id, item_quantity, start_price, is_user_auction, newtime,user_id, status=1):
        """
        插入或更新单个拍卖信息
        :param auctionid: 拍卖 ID
        :param seller_id: 卖家 ID
        :param start_price: 起始价格
        :param is_user_auction: 是否为用户拍卖
        :param newtime: 新的时间
        :param status: 状态 (默认为 1)
        """
        cur = self.conn.cursor()
        
        # 插入或更新拍卖数据的 SQL 语句
        update_query = '''
        INSERT OR REPLACE INTO auction (auctionid, auction_id, seller_id, item_quantity, start_price, is_user_auction, newtime, user_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        # 执行更新
        try:
            cur.execute(update_query, (auctionid, auction_id, seller_id, item_quantity, start_price, is_user_auction, newtime, user_id, status))
            self.conn.commit()  # 提交事务
            print("拍卖品信息已成功更新！")
        except sqlite3.Error as e:
            print(f"数据库更新失败：{e}")
            self.conn.rollback()  # 回滚事务
        finally:
            cur.close()

    def get_user_auction_info(self):
        """获取所有 is_user_auction 为 'Yes' 的物品的完整信息"""
        cur = self.conn.cursor()
        # SQL 查询语句：获取 is_user_auction 为 'Yes' 的所有物品
        sql = "SELECT * FROM auction WHERE is_user_auction = 'Yes'"
        cur.execute(sql)
        result = cur.fetchall()
        # 返回所有符合条件的物品信息
        return result


        
    def insert_auction_items(self, auctionid, seller_id, auction_items: list, newtime: str, user_id: str, status):
        """
        将拍卖品信息插入到数据库中的 auction 表中。
        
        参数:
            auction_items (list): 包含多个拍卖品信息的列表，每项是一个元组，包含
                                  (auction_id, seller_id, item_quantity, start_price, is_user_auction, newtime, user_id)。
            newtime (str): 拍卖品生成的时间，格式为 'YYYY-MM-DD HH:MM:SS'。
            user_id (str): 用户的唯一标识符。
        """
        
        # 打开数据库连接并创建游标
        cur = self.conn.cursor()
        
        try:
            # 插入数据的SQL语句
            insert_query = '''
            INSERT OR REPLACE INTO auction (auctionid, auction_id, seller_id, item_quantity, start_price, is_user_auction, newtime, user_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # 批量插入 auction_items 数据
            cur.executemany(insert_query, auction_items)
            
            # 提交事务
            self.conn.commit()
            print(f"成功插入 {len(auction_items)} 条拍卖品记录。")
        
        except Exception as e:
            # 如果插入失败，输出错误并回滚事务
            print(f"插入拍卖品数据时出错: {e}")
            self.conn.rollback()
        
        finally:
            # 关闭游标
            cur.close()
            
    def get_auction_info_by_auctionid(self, auctionid):
        """
        通过 auctionid 获取拍卖信息
        :param auctionid: 拍卖编号
        :return: 拍卖信息的字典或 None
        """
        cur = self.conn.cursor()  # 创建游标
        sql = f"SELECT * FROM auction WHERE auctionid=?"  # SQL 查询语句
        cur.execute(sql, (auctionid,))  # 执行查询
        result = cur.fetchone()  # 获取单条记录
        
        if result:
            # 获取列名，并将结果转化为字典
            columns = [column[0] for column in cur.description]
            auction_dict = dict(zip(columns, result))
            return auction_dict  # 返回字典形式的拍卖信息
        else:
            return None  # 如果没有找到，返回 None

    def get_auction_status(self):
        """获取当前拍卖的状态"""
        cur = self.conn.cursor()
        try:
            # 假设 auction 表中有一个 status 字段表示拍卖状态
            cur.execute("SELECT status FROM auction ORDER BY auctionid DESC LIMIT 1")
            row = cur.fetchone()
            
            if row:
                return row[0]  # 返回当前拍卖状态
            else:
                return "拍卖会当前没有任何记录！"

        except sqlite3.OperationalError as e:
            return f"数据库操作失败: {str(e)}"
        finally:
            cur.close()

            

    def get_all_auction_data(self):
        """获取 auction 表中的全部信息"""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM auction")
            rows = cur.fetchall()  
            if rows:
                columns = [column[0] for column in cur.description]
                auction_data_list = [dict(zip(columns, row)) for row in rows]
                return auction_data_list
            else:
                return "拍卖会当前没有任何记录！"

        except sqlite3.OperationalError as e:
            return f"数据库操作失败: {str(e)}"
        finally:
            cur.close()


    def update_savestone(self, user_id: str, amount: int, key: int):
        """
        更新银行存款灵石数量
        :param user_id: 用户ID
        :param amount: 存取金额
        :param key: 1为增加（存），2为减少（取）
        """
        cur = self.conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')    
        if key == 1:  # 存入灵石
            sql = "UPDATE bank SET savestone =savestone+?, savetime=? WHERE user_id=?"
            cur.execute(sql, (amount, current_time, user_id))
            self.conn.commit()
            
        elif key == 2:  # 取出灵石
            sql = "UPDATE bank SET savestone =savestone-?, savetime=? WHERE user_id=?"
            cur.execute(sql, (amount, current_time, user_id))
            self.conn.commit()

    def get_bankinfo(self, user_id):
        """根据USER_ID获取用户银行信息"""
        cur = self.conn.cursor()
        sql = f"SELECT * FROM bank WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result: 
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            # 用户不存在，创建一个新用户
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            user_dict = {
                'user_id': user_id,
                'savestone': 0,
                'savetime': current_time,
                'banklevel': 1  # 假设banklevel的默认值为1
            }
            # 插入新用户记录到数据库
            cur.execute('''
                INSERT INTO bank (user_id, savestone, savetime, banklevel)
                VALUES (?, ?, ?, ?)
            ''', (user_dict['user_id'], user_dict['savestone'], user_dict['savetime'], user_dict['banklevel']))
            self.conn.commit()

            return user_dict

    def update_bankinfo(self, user_id: str, savestone: int, savetime: str, banklevel: int):
        """
        更新用户的银行信息，包括灵石存储数量(savestone)、存储时间(savetime)和银行等级(banklevel)。
        
        参数:
            user_id (str): 用户的唯一标识符。
            savestone (int): 用户当前的灵石存储数量。
            savetime (str): 用户灵石存入的时间，格式为 'YYYY-MM-DD HH:MM:SS'。
            banklevel (int): 用户的银行会员等级。
        """
        cur = self.conn.cursor()
        
        # 更新 savestone, savetime 和 banklevel
        cur.execute('''
            UPDATE bank
            SET savestone = ?, savetime = ?, banklevel = ?
            WHERE user_id = ?
        ''', (savestone, savetime, banklevel, user_id))
        
        self.conn.commit()

    def update_banklevel(self, user_id, new_level):
        """
        更新用户的银行等级 (banklevel)。
        
        参数:
            user_id (str): 用户的唯一标识符。
            new_level (int): 用户的新银行等级。
        """
        cur = self.conn.cursor()

        # 更新用户的银行等级
        cur.execute('''
            UPDATE bank
            SET banklevel = ?
            WHERE user_id = ?
        ''', (new_level, user_id))
        self.conn.commit()

    def update_banksavetime(self, user_id, savetimes):
        """
        更新用户的银行等级 (banklevel)。
        
        参数:
            user_id (str): 用户的唯一标识符。
            savetimes (int): 用户的新银行等级。
        """
        cur = self.conn.cursor()

        # 更新用户的银行等级
        cur.execute('''
            UPDATE bank
            SET savetime = ?
            WHERE user_id = ?
        ''', (savetimes, user_id))
        self.conn.commit() 

    def stone_top(self):
        """这也是灵石排行榜"""
        sql = f"SELECT user_name,stone FROM user_xiuxian WHERE user_name is NOT NULL ORDER BY stone DESC LIMIT 50"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result

    def power_top(self):
        """战力排行榜"""
        sql = f"SELECT user_name,power FROM user_xiuxian WHERE user_name is NOT NULL ORDER BY power DESC LIMIT 50"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result

    def scale_top(self):
        """
        宗门建设度排行榜
        :return:
        """
        sql = f"SELECT sect_id, sect_name, sect_scale FROM sects WHERE sect_owner is NOT NULL ORDER BY sect_scale DESC"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result


    def get_all_sects(self):
        """
        获取所有宗门信息
        :return: 宗门信息字典列表
        """
        sql = f"SELECT * FROM sects WHERE sect_owner is NOT NULL"
        cur = self.conn.cursor()
        cur.execute(sql)
        result = cur.fetchall()
        results = []
        columns = [column[0] for column in cur.description]
        for row in result:
            sect_dict = dict(zip(columns, row))
            results.append(sect_dict)
        return results

    def get_all_sects_with_member_count(self):
        """
        获取所有宗门及其各个宗门成员数，并按sect_scale的数字排列
        """
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                s.sect_id, 
                s.sect_name, 
                s.sect_scale, 
                (SELECT user_name FROM user_xiuxian WHERE user_id = s.sect_owner) as user_name, 
                COUNT(ux.user_id) as member_count
            FROM 
                sects s
            LEFT JOIN 
                user_xiuxian ux 
            ON 
                s.sect_id = ux.sect_id
            GROUP BY 
                s.sect_id
            ORDER BY 
                s.sect_scale DESC  -- 根据sect_scale升序排列, 可以改为DESC实现降序排列
        """)
        results = cur.fetchall()
        return results


    def update_user_is_beg(self, user_id, is_beg):
        """
        更新用户的最后奇缘时间

        :param user_id: 用户ID
        :param is_beg: 'YYYY-MM-DD HH:MM:SS'
        """
        cur = self.conn.cursor()
        sql = "UPDATE user_xiuxian SET is_beg=? WHERE user_id=?"
        cur.execute(sql, (is_beg, user_id))
        self.conn.commit()


    def get_top1_user(self):
        """
        获取修为第一的用户
        """
        cur = self.conn.cursor()
        sql = f"select * from user_xiuxian ORDER BY exp DESC LIMIT 1"
        cur.execute(sql)
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            top1_dict = dict(zip(columns, result))
            return top1_dict
        else:
            return None
        

    def donate_update(self, sect_id, stone_num):
        """宗门捐献更新建设度及可用灵石"""
        sql = f"UPDATE sects SET sect_used_stone=sect_used_stone+?,sect_scale=sect_scale+? WHERE sect_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (stone_num, stone_num * 1, sect_id))
        self.conn.commit()

    def update_sect_used_stone(self, sect_id, sect_used_stone, key):
        """更新宗门灵石储备  1为增加,2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = f"UPDATE sects SET sect_used_stone=sect_used_stone+? WHERE sect_id=?"
            cur.execute(sql, (sect_used_stone, sect_id))
            self.conn.commit()
        elif key == 2:
            sql = f"UPDATE sects SET sect_used_stone=sect_used_stone-? WHERE sect_id=?"
            cur.execute(sql, (sect_used_stone, sect_id))
            self.conn.commit()

    def update_sect_materials(self, sect_id, sect_materials, key):
        """更新资材  1为增加,2为减少"""
        cur = self.conn.cursor()

        if key == 1:
            sql = f"UPDATE sects SET sect_materials=sect_materials+? WHERE sect_id=?"
            cur.execute(sql, (sect_materials, sect_id))
            self.conn.commit()
        elif key == 2:
            sql = f"UPDATE sects SET sect_materials=sect_materials-? WHERE sect_id=?"
            cur.execute(sql, (sect_materials, sect_id))
            self.conn.commit()

    def get_all_sects_id_scale(self):
        """
        获取所有宗门信息
        :return
        :result[0] = sect_id   
        :result[1] = 建设度 sect_scale,
        :result[2] = 丹房等级 elixir_room_level 
        """
        sql = f"SELECT sect_id, sect_scale, elixir_room_level FROM sects WHERE sect_owner is NOT NULL ORDER BY sect_scale DESC"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result

    def get_all_users_by_sect_id(self, sect_id):
        """
        获取宗门所有成员信息
        :return: 成员列表
        """
        sql = f"SELECT * FROM user_xiuxian WHERE sect_id = ? ORDER BY sect_contribution DESC"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_id,))
        result = cur.fetchall()
        results = []
        for user in result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, user))
            results.append(user_dict)
        return results

    def do_work(self, user_id, the_type, sc_time=None):
        """
        更新用户操作CD
        :param sc_time: 任务
        :param user_id: qq
        :param the_type: 0:无状态  1:闭关中  2:历练中  3:探索秘境中
        :param the_time: 本次操作的时长
        :return:
        """
        now_time = None
        if the_type == 1:
            now_time = datetime.now()
        elif the_type == 0:
            now_time = 0
        elif the_type == 2:
            now_time = datetime.now()
        elif the_type == 3:
            now_time = datetime.now()

        sql = f"UPDATE user_cd SET type=?,create_time=?,scheduled_time=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (the_type, now_time, sc_time, user_id))
        self.conn.commit()

    def update_levelrate(self, user_id, rate):
        """更新突破成功率"""
        sql = f"UPDATE user_xiuxian SET level_up_rate=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (rate, user_id))
        self.conn.commit()

    def update_user_attribute(self, user_id, hp, mp, atk):
        """更新用户HP,MP,ATK信息"""
        sql = f"UPDATE user_xiuxian SET hp=?,mp=?,atk=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (hp, mp, atk, user_id))
        self.conn.commit()

    def update_user_hp_mp(self, user_id, hp, mp):
        """更新用户HP,MP信息"""
        sql = f"UPDATE user_xiuxian SET hp=?,mp=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (hp, mp, user_id))
        self.conn.commit()

    def update_user_sect_contribution(self, user_id, sect_contribution):
        """更新用户宗门贡献度"""
        sql = f"UPDATE user_xiuxian SET sect_contribution=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_contribution, user_id))
        self.conn.commit()

    def update_user_hp(self, user_id):
        """重置用户hp,mp信息"""
        sql = f"UPDATE user_xiuxian SET hp=exp/2,mp=exp,atk=exp/10 WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_user_hp2(self, user_id):
        """重置用户hp,mp信息"""
        sql = f"UPDATE user_xiuxian SET hp=ROUND(exp*0.65, 0), mp=ROUND(exp*1.2, 0), atk=ROUND(exp*0.12, 0) WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_user_hp3(self, user_id):
        """重置用户hp,mp信息"""
        sql = f"UPDATE user_xiuxian SET hp=ROUND(exp*0.85, 0), mp=ROUND(exp*1.5, 0), atk=ROUND(exp*0.15, 0) WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def restate(self, user_id=None):
        """重置所有用户状态或重置对应人状态"""
        if user_id is None:
            sql = f"UPDATE user_xiuxian SET hp=exp/2,mp=exp,atk=exp/10"
            cur = self.conn.cursor()
            cur.execute(sql, )
            self.conn.commit()
        else:
            sql = f"UPDATE user_xiuxian SET hp=exp/2,mp=exp,atk=exp/10 WHERE user_id=?"
            cur = self.conn.cursor()
            cur.execute(sql, (user_id,))
            self.conn.commit()

    def auto_recover_hp(self):
        """自动回血函数"""
        sql = f"SELECT user_id, exp, hp FROM user_xiuxian WHERE hp < exp/2"
        cur = self.conn.cursor()
        users = cur.fetchall()
        
        for user in users:
            user_id, exp, hp = user
            sql = f"UPDATE user_xiuxian SET hp=hp + ?*0.001 WHERE user_id=?"
            cur.execute(sql, (exp, user_id))
        
        self.conn.commit()
    
    def get_back_msg(self, user_id):
        """获取用户背包信息"""
        sql = f"SELECT * FROM back WHERE user_id=? and goods_num >= 1"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchall()
        if not result:
            return None
    
        columns = [column[0] for column in cur.description]
        results = []
        for row in result:
            back_dict = dict(zip(columns, row))
            results.append(back_dict)
        return results


    def goods_num(self, user_id, goods_id):
        """
        判断用户物品数量
        :param user_id: 用户qq
        :param goods_id: 物品id
        :return: 物品数量
        """
        sql = "SELECT num FROM back WHERE user_id=? and goods_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, goods_id))
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            return 0

    def get_all_user_exp(self, level):
        """查询所有对应大境界玩家的修为"""
        sql = f"SELECT exp FROM user_xiuxian  WHERE level like '{level}%'"
        cur = self.conn.cursor()
        cur.execute(sql, )
        result = cur.fetchall()
        return result

    def update_user_atkpractice(self, user_id, atkpractice):
        """更新用户攻击修炼等级"""
        sql = f"UPDATE user_xiuxian SET atkpractice={atkpractice} WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_user_sect_task(self, user_id, sect_task):
        """更新用户宗门任务次数"""
        sql = f"UPDATE user_xiuxian SET sect_task=sect_task+? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_task, user_id))
        self.conn.commit()

    def sect_task_reset(self):
        """重置宗门任务次数"""
        sql = f"UPDATE user_xiuxian SET sect_task=0"
        cur = self.conn.cursor()
        cur.execute(sql, )
        self.conn.commit()

    def update_sect_scale_and_used_stone(self, sect_id, sect_used_stone, sect_scale):
        """更新宗门灵石、建设度"""
        sql = f"UPDATE sects SET sect_used_stone=?,sect_scale=? WHERE sect_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (sect_used_stone, sect_scale, sect_id))
        self.conn.commit()

    def update_sect_elixir_room_level(self, sect_id, level):
        """更新宗门丹房等级"""
        sql = f"UPDATE sects SET elixir_room_level=? WHERE sect_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (level, sect_id))
        self.conn.commit()

    def update_user_sect_elixir_get_num(self, user_id):
        """更新用户每日领取丹药领取次数"""
        sql = f"UPDATE user_xiuxian SET sect_elixir_get=1 WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def sect_elixir_get_num_reset(self):
        """重置宗门丹药领取次数"""
        sql = f"UPDATE user_xiuxian SET sect_elixir_get=0"
        cur = self.conn.cursor()
        cur.execute(sql, )
        self.conn.commit()

    def update_sect_memo(self, sect_id, memo):
        """更新宗门当前的宗训"""
        sql = f"UPDATE sects SET sect_memo=? WHERE sect_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (memo, sect_id))
        self.conn.commit()   

    def update_sect_mainbuff(self, sect_id, mainbuffid):
        """更新宗门当前的主修功法"""
        sql = f"UPDATE sects SET mainbuff=? WHERE sect_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (mainbuffid, sect_id))
        self.conn.commit()

    def update_sect_secbuff(self, sect_id, secbuffid):
        """更新宗门当前的神通"""
        sql = f"UPDATE sects SET secbuff=? WHERE sect_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (secbuffid, sect_id))
        self.conn.commit()

    def initialize_user_buff_info(self, user_id):
        """初始化用户buff信息"""
        sql = f"INSERT INTO BuffInfo (user_id,main_buff,sec_buff,faqi_buff,fabao_weapon) VALUES (?,0,0,0,0)"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def get_user_buff_info(self, user_id):
        """获取用户buff信息"""
        sql = f"select * from BuffInfo WHERE user_id =?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            buff_dict = dict(zip(columns, result))
            return buff_dict
        else:
            return None
        
    def updata_user_main_buff(self, user_id, id):
        """更新用户主功法信息"""
        sql = f"UPDATE BuffInfo SET main_buff = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()
    
    def updata_user_sub_buff(self, user_id, id): #辅修功法3
        """更新用户辅修功法信息"""
        sql = f"UPDATE BuffInfo SET sub_buff = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()
    
    def updata_user_sec_buff(self, user_id, id):
        """更新用户副功法信息"""
        sql = f"UPDATE BuffInfo SET sec_buff = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_faqi_buff(self, user_id, id):
        """更新用户法器信息"""
        sql = f"UPDATE BuffInfo SET faqi_buff = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_fabao_weapon(self, user_id, id):
        """更新用户法宝信息"""
        sql = f"UPDATE BuffInfo SET fabao_weapon = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_armor_buff(self, user_id, id):
        """更新用户防具信息"""
        sql = f"UPDATE BuffInfo SET armor_buff = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (id, user_id,))
        self.conn.commit()

    def updata_user_married_to(self, user_id, user_name):
        """更新用户结婚信息"""
        sql = f"UPDATE user_xiuxian SET married_to = ? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_name, user_id,))
        self.conn.commit()

    def updata_user_atk_buff(self, user_id, buff):
        """更新用户永久攻击buff信息"""
        sql = f"UPDATE BuffInfo SET atk_buff=atk_buff+? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (buff, user_id,))
        self.conn.commit()

    def updata_user_blessed_spot(self, user_id, blessed_spot):
        """更新用户洞天福地等级"""
        sql = f"UPDATE BuffInfo SET blessed_spot=? WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (blessed_spot, user_id,))
        self.conn.commit()

    def update_user_blessed_spot_flag(self, user_id):
        """更新用户洞天福地是否开启"""
        sql = f"UPDATE user_xiuxian SET blessed_spot_flag=1 WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def update_user_blessed_spot_name(self, user_id, blessed_spot_name):
        """更新用户洞天福地的名字"""
        sql = f"UPDATE user_xiuxian SET blessed_spot_name=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (blessed_spot_name, user_id,))
        self.conn.commit()

    def day_num_reset(self):
        """重置丹药每日使用次数"""
        sql = f"UPDATE back SET day_num=0 WHERE goods_type='丹药'"
        cur = self.conn.cursor()
        cur.execute(sql, )
        self.conn.commit()

    def reset_work_num(self, user_id=None):
        """重置用户悬赏令刷新次数"""
        if user_id:
            # 如果传入了 user_id，则只更新该用户的 work_num
            sql = "UPDATE user_xiuxian SET work_num=0 WHERE user_id = ?"
            cur = self.conn.cursor()
            cur.execute(sql, (user_id,))
        else:
            # 如果没有传入 user_id，则更新所有用户的 work_num
            sql = "UPDATE user_xiuxian SET work_num=0"
            cur = self.conn.cursor()
            cur.execute(sql)
        self.conn.commit()

    def reset_mijing(self, user_id):
        """重置用户悬赏令刷新次数"""
        sql = "UPDATE user_xiuxian SET is_mijing=0 WHERE user_id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        self.conn.commit()

    def get_work_num(self, user_id):
        """获取用户悬赏令刷新次数"""
        sql = f"SELECT work_num FROM user_xiuxian WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            work_num = result[0]
        return work_num
    
    def update_work_num(self, user_id, work_num):
        sql = f"UPDATE user_xiuxian SET work_num=? WHERE user_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (work_num, user_id,))
        self.conn.commit()


    def send_back(self, user_id, goods_id, goods_name, goods_type, goods_num, bind_flag=0):
        """
        插入物品至背包
        :param user_id: 用户qq
        :param goods_id: 物品id
        :param goods_name: 物品名称
        :param goods_type: 物品类型
        :param goods_num: 物品数量
        :param bind_flag: 是否绑定物品,0-非绑定,1-绑定
        :return: None
        """
        now_time = datetime.now()
        # 检查物品是否存在，存在则update
        cur = self.conn.cursor()
        back = self.get_item_by_good_id_and_user_id(user_id, goods_id)
        if back:
            # 判断是否存在，存在则update
            if bind_flag == 1:
                bind_num = back['bind_num'] + goods_num
            else:
                bind_num = back['bind_num']
            goods_nums = back['goods_num'] + goods_num
            sql = f"UPDATE back set goods_num=?,update_time=?,bind_num={bind_num} WHERE user_id=? and goods_id=?"
            cur.execute(sql, (goods_nums, now_time, user_id, goods_id))
            self.conn.commit()
        else:
            # 判断是否存在，不存在则INSERT
            if bind_flag == 1:
                bind_num = goods_num
            else:
                bind_num = 0
            sql = f"""
                    INSERT INTO back (user_id, goods_id, goods_name, goods_type, goods_num, create_time, update_time, bind_num)
            VALUES (?,?,?,?,?,?,?,?)"""
            cur.execute(sql, (user_id, goods_id, goods_name, goods_type, goods_num, now_time, now_time, bind_num))
            self.conn.commit()


    def get_item_by_good_id_and_user_id(self, user_id, goods_id):
        """根据物品id、用户id获取物品信息"""
        sql = f"select * from back WHERE user_id=? and goods_id=?"
        cur = self.conn.cursor()
        cur.execute(sql, (user_id, goods_id))
        result = cur.fetchone()
        if not result:
            return None
    
        columns = [column[0] for column in cur.description]
        item_dict = dict(zip(columns, result))
        return item_dict


    def update_back_equipment(self, sql_str):
        """更新背包,传入sql"""
        logger.opt(colors=True).info(f"<green>执行的sql:{sql_str}</green>")
        cur = self.conn.cursor()
        cur.execute(sql_str)
        self.conn.commit()

    def reset_user_drug_resistance(self, user_id):
        """重置用户耐药性"""
        sql = f"UPDATE back SET all_num=0 where goods_type='丹药' and user_id={user_id}"
        cur = self.conn.cursor()
        cur.execute(sql, )
        self.conn.commit()

    def update_back_j(self, user_id, goods_id, num=1, use_key=0):
        """
        使用物品
        :num 减少数量  默认1
        :use_key 是否使用，丹药使用才传 默认0
        """
        back = self.get_item_by_good_id_and_user_id(user_id, goods_id)
        if back['goods_type'] == "丹药" and use_key == 1:  # 丹药要判断耐药性、日使用上限
            if back['bind_num'] >= 1:
                bind_num = back['bind_num'] - num  # 优先使用绑定物品
            else:
                bind_num = back['bind_num']
            day_num = back['day_num'] + num
            all_num = back['all_num'] + num
        else:
            bind_num = back['bind_num']
            day_num = back['day_num']
            all_num = back['all_num']
        goods_num = back['goods_num'] - num
        now_time = datetime.now()
        sql_str = f"UPDATE back set update_time='{now_time}',action_time='{now_time}',goods_num={goods_num},day_num={day_num},all_num={all_num},bind_num={bind_num} WHERE user_id={user_id} and goods_id={goods_id}"
        cur = self.conn.cursor()
        cur.execute(sql_str)
        self.conn.commit()

def get_experience_and_delete_old_data(old_user_id):
    # 连接到老的数据库
    conn = sqlite3.connect(DATABASEOLD / "xiuxiandata.db")  # 替换为老数据库的实际路径
    cursor = conn.cursor()

    # 查询旧用户的经验值
    cursor.execute("SELECT experience FROM xiuxiandb WHERE user_id=?", (old_user_id,))
    result = cursor.fetchone()
    
    # 删除旧数据库中的记录
    cursor.execute("DELETE FROM xiuxiandb WHERE user_id=?", (old_user_id,))
    conn.commit()
    conn.close()

    # 如果找到经验值，则返回，否则返回0
    experience = result[0] if result else 0
    return abs(experience)  # 将经验值转为正数
 

class XiuxianJsonDate:
    def __init__(self):
        pass

    def beifen_linggen_get(self):
        lg = random.choice(灵根_data)
        return lg['name'], lg['type']

    def level_rate(self, level):
        return 突破概率_data[0][level]

    def linggen_get(self):
        """获取灵根信息"""
        data = 灵根_data
        rate_dict = {}
        for i, v in data.items():
            rate_dict[i] = v["type_rate"]
        lgen = OtherSet().calculated(rate_dict)
        if data[lgen]["type_flag"]:
            flag = random.choice(data[lgen]["type_flag"])
            root = random.sample(data[lgen]["type_list"], flag)
            msg = ""
            for j in root:
                if j == root[-1]:
                    msg += j
                    break
                msg += (j + "、")

            return msg + '属性灵根', lgen
        else:
            root = random.choice(data[lgen]["type_list"])
            return root, lgen



class OtherSet(XiuConfig):

    def __init__(self):
        super().__init__()

    def set_closing_type(self, user_level):
        list_all = len(self.level) - 1
        now_index = self.level.index(user_level)
        if list_all == now_index:
            need_exp = 0.001
        else:
            is_updata_level = self.level[now_index + 1]
            need_exp = XiuxianDateManage().get_level_power(is_updata_level)
        return need_exp

    def get_type(self, user_exp, rate, user_level):
        list_all = len(self.level) - 1
        now_index = self.level.index(user_level)
        if list_all == now_index:
            return "道友已是最高境界，无法突破！"

        is_updata_level = self.level[now_index + 1]
        need_exp = XiuxianDateManage().get_level_power(is_updata_level)

        # 判断修为是否足够突破
        if user_exp >= need_exp:
            pass
        else:
            return f"道友的修为不足以突破！距离下次突破需要{need_exp - user_exp}修为！突破境界为：{is_updata_level} 请道友继续<qqbot-cmd-input text=\"修炼\" show=\"修炼\" />后再来突破。"

      #  success_rate = True if random.randint(0, 100) < rate else False
        if rate >= 100:
            success_rate = True
        else:
            success_rate = random.randint(0, 100) < rate
        if success_rate:
            return [self.level[now_index + 1]]
        else:
            return '失败'

    def calculated(self, rate: dict) -> str:
        """
        根据概率计算，轮盘型
        :rate:格式{"数据名":"获取几率"}
        :return: 数据名
        """

        get_list = []  # 概率区间存放

        n = 1
        for name, value in rate.items():  # 生成数据区间
            value_rate = int(value)
            list_rate = [_i for _i in range(n, value_rate + n)]
            get_list.append(list_rate)
            n += value_rate

        now_n = n - 1
        get_random = random.randint(1, now_n)  # 抽取随机数

        index_num = None
        for list_r in get_list:
            if get_random in list_r:  # 判断随机在那个区间
                index_num = get_list.index(list_r)
                break

        return list(rate.keys())[index_num]

    def date_diff(self, new_time, old_time):
        """计算日期差"""
        if isinstance(new_time, datetime):
            pass
        else:
            new_time = datetime.strptime(new_time, '%Y-%m-%d %H:%M:%S.%f')

        if isinstance(old_time, datetime):
            pass
        else:
            old_time = datetime.strptime(old_time, '%Y-%m-%d %H:%M:%S.%f')

        day = (new_time - old_time).days
        sec = (new_time - old_time).seconds

        return (day * 24 * 60 * 60) + sec

    def get_power_rate(self, mind, other):
        power_rate = mind / (other + mind)
        if power_rate >= 0.8:
            return "道友偷窃小辈实属天道所不齿！"
        elif power_rate <= 0.05:
            return "道友请不要不自量力！"
        else:
            return int(power_rate * 100)

    def player_fight(self, player1: dict, player2: dict):
        """
        回合制战斗
        type_in : 1 为完整返回战斗过程（未加）
        2：只返回战斗结果
        数据示例：
        {"道号": None, "气血": None, "攻击": None, "真元": None, '会心':None}
        """
        msg1 = "{}发起攻击，造成了{}伤害\n"
        msg2 = "{}发起攻击，造成了{}伤害\n"

        play_list = []
        suc = None
        if player1['气血'] <= 0:
            player1['气血'] = 1
        if player2['气血'] <= 0:
            player2['气血'] = 1
        while True:
            player1_gj = int(round(random.uniform(0.95, 1.05), 2) * player1['攻击'])
            if random.randint(0, 100) <= player1['会心']:
                player1_gj = int(player1_gj * player1['爆伤'])
                msg1 = "{}发起会心一击，造成了{}伤害\n"

            player2_gj = int(round(random.uniform(0.95, 1.05), 2) * player2['攻击'])
            if random.randint(0, 100) <= player2['会心']:
                player2_gj = int(player2_gj * player2['爆伤'])
                msg2 = "{}发起会心一击，造成了{}伤害\n"

            play1_sh: int = int(player1_gj * (1 - player2['防御']))
            play2_sh: int = int(player2_gj * (1 - player1['防御']))

            play_list.append(msg1.format(player1['道号'], play1_sh))
            player2['气血'] = player2['气血'] - play1_sh
            play_list.append(f"{player2['道号']}剩余血量{player2['气血']}")
            XiuxianDateManage().update_user_hp_mp(player2['user_id'], player2['气血'], player2['真元'])

            if player2['气血'] <= 0:
                play_list.append(f"{player1['道号']}胜利")
                suc = f"{player1['道号']}"
                XiuxianDateManage().update_user_hp_mp(player2['user_id'], 1, player2['真元'])
                break

            play_list.append(msg2.format(player2['道号'], play2_sh))
            player1['气血'] = player1['气血'] - play2_sh
            play_list.append(f"{player1['道号']}剩余血量{player1['气血']}\n")
            XiuxianDateManage().update_user_hp_mp(player1['user_id'], player1['气血'], player1['真元'])

            if player1['气血'] <= 0:
                play_list.append(f"{player2['道号']}胜利")
                suc = f"{player2['道号']}"
                XiuxianDateManage().update_user_hp_mp(player1['user_id'], 1, player1['真元'])
                break
            if player1['气血'] <= 0 or player2['气血'] <= 0:
                play_list.append("逻辑错误！！！")
                break

        return play_list, suc

    def send_hp_mp(self, user_id, hp, mp):
        user_msg = XiuxianDateManage().get_user_info_with_id(user_id)
        if user_msg['root_type'] == '轮回道果':
            max_hp = int(user_msg['exp'] * 0.65)
            max_mp = int(user_msg['exp'] * 1.2)
        elif user_msg['root_type'] == '真·轮回道果':
            max_hp = int(user_msg['exp'] * 0.85)
            max_mp = int(user_msg['exp'] * 1.5)

        else:        
            max_hp = int(user_msg['exp'] / 2)
            max_mp = int(user_msg['exp'])

        msg = []
        hp_mp = []

        if user_msg['hp'] < max_hp:
            if user_msg['hp'] + hp < max_hp:
                new_hp = user_msg['hp'] + hp
                msg.append(f',回复气血：{hp}')
            else:
                new_hp = max_hp
                msg.append(',气血已回满！')
        else:
            new_hp = user_msg['hp']
            msg.append('')

        if user_msg['mp'] < max_mp:
            if user_msg['mp'] + mp < max_mp:
                new_mp = user_msg['mp'] + mp
                msg.append(f',回复真元：{mp}')
            else:
                new_mp = max_mp
                msg.append(',真元已回满！')
        else:
            new_mp = user_msg['mp']
            msg.append('')

        hp_mp.append(new_hp)
        hp_mp.append(new_mp)
        hp_mp.append(user_msg['exp'])

        return msg, hp_mp



sql_message = XiuxianDateManage()  # sql类
items = Items()


def final_user_data(user_data, columns):
    """传入用户当前信息、buff信息,返回最终信息"""
    user_dict = dict(zip((col[0] for col in columns), user_data))
    
    # 通过字段名称获取相应的值
    impart_data = xiuxian_impart.get_user_impart_info_with_id(user_dict['user_id'])
    if impart_data is None:
        xiuxian_impart._create_user(user_dict['user_id'])
    impart_data = xiuxian_impart.get_user_impart_info_with_id(user_dict['user_id'])
    impart_hp_per = impart_data['impart_hp_per'] if impart_data is not None else 0
    impart_mp_per = impart_data['impart_mp_per'] if impart_data is not None else 0
    impart_atk_per = impart_data['impart_atk_per'] if impart_data is not None else 0
    
    user_buff_data = UserBuffDate(user_dict['user_id']).BuffInfo
    
    armor_atk_buff = 0
    if int(user_buff_data['armor_buff']) != 0:
        armor_info = items.get_data_by_item_id(user_buff_data['armor_buff'])
        armor_atk_buff = armor_info['atk_buff']
        
    weapon_atk_buff = 0
    if int(user_buff_data['faqi_buff']) != 0:
        weapon_info = items.get_data_by_item_id(user_buff_data['faqi_buff'])
        weapon_atk_buff = weapon_info['atk_buff']
    
    main_buff_data = UserBuffDate(user_dict['user_id']).get_user_main_buff_data()
    main_hp_buff = main_buff_data['hpbuff'] if main_buff_data is not None else 0
    main_mp_buff = main_buff_data['mpbuff'] if main_buff_data is not None else 0
    main_atk_buff = main_buff_data['atkbuff'] if main_buff_data is not None else 0
    
    # 改成字段名称来获取相应的值
    user_dict['hp'] = int(user_dict['hp'] * (1 + main_hp_buff + impart_hp_per))
    user_dict['mp'] = int(user_dict['mp'] * (1 + main_mp_buff + impart_mp_per))
    user_dict['atk'] = int((user_dict['atk'] * (user_dict['atkpractice'] * 0.04 + 1) * (1 + main_atk_buff) * (
            1 + weapon_atk_buff) * (1 + armor_atk_buff)) * (1 + impart_atk_per)) + int(user_buff_data['atk_buff'])
    
    return user_dict

@DRIVER.on_shutdown
async def close_db():
    XiuxianDateManage().close()


# 这里是虚神界部分
class XIUXIAN_IMPART_BUFF:
    global impart_num
    _instance = {}
    _has_init = {}

    def __new__(cls):
        if cls._instance.get(impart_num) is None:
            cls._instance[impart_num] = super(XIUXIAN_IMPART_BUFF, cls).__new__(cls)
        return cls._instance[impart_num]

    def __init__(self):
        if not self._has_init.get(impart_num):
            self._has_init[impart_num] = True
            self.database_path = DATABASE_IMPARTBUFF
            if not self.database_path.exists():
                self.database_path.mkdir(parents=True)
                self.database_path /= "xiuxian_impart.db"
                self.conn = sqlite3.connect(self.database_path)
                # self._create_file()
            else:
                self.database_path /= "xiuxian_impart.db"
                self.conn = sqlite3.connect(self.database_path)
            logger.opt(colors=True).info(f"<green>xiuxian_impart数据库已连接!</green>")
            self._check_data()

    def close(self):
        self.conn.close()
        logger.opt(colors=True).info(f"<green>xiuxian_impart数据库关闭!</green>")

    def _create_file(self) -> None:
        """创建数据库文件"""
        c = self.conn.cursor()
        c.execute('''CREATE TABLE xiuxian_impart
                           (NO            INTEGER PRIMARY KEY UNIQUE,
                           USERID         TEXT     ,
                           level          INTEGER  ,
                           root           INTEGER
                           );''')
        c.execute('''''')
        c.execute('''''')
        self.conn.commit()

    def _check_data(self):
        """检查数据完整性"""
        c = self.conn.cursor()

        for i in config_impart.sql_table:
            if i == "xiuxian_impart":
                try:
                    c.execute(f"select count(1) from {i}")
                except sqlite3.OperationalError:
                    c.execute(f"""CREATE TABLE "xiuxian_impart" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" integer DEFAULT 0,
    "impart_hp_per" integer DEFAULT 0,
    "impart_atk_per" integer DEFAULT 0,
    "impart_mp_per" integer DEFAULT 0,
    "impart_exp_up" integer DEFAULT 0,
    "boss_atk" integer DEFAULT 0,
    "impart_know_per" integer DEFAULT 0,
    "impart_burst_per" integer DEFAULT 0,
    "impart_mix_per" integer DEFAULT 0,
    "impart_reap_per" integer DEFAULT 0,
    "impart_two_exp" integer DEFAULT 0,
    "stone_num" integer DEFAULT 0,
    "exp_day" integer DEFAULT 0,
    "wish" integer DEFAULT 0
    );""")
        try:
            c.execute(f"SELECT count(1) FROM INVITE")
        except sqlite3.OperationalError:
            c.execute('''CREATE TABLE IF NOT EXISTS INVITE (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        real_group_id INTEGER,
                        real_user_id INTEGER,
                        timestamp integer DEFAULT 0
                    );''')
            logger.opt(colors=True).info("<green>INVITE 表已创建！</green>")
            
        for s in config_impart.sql_table_impart_buff:
            try:
                c.execute(f"select {s} from xiuxian_impart")
            except sqlite3.OperationalError:
                sql = f"ALTER TABLE xiuxian_impart ADD COLUMN {s} integer DEFAULT 0;"
                logger.opt(colors=True).info(f"<green>{sql}</green>")
                logger.opt(colors=True).info(f"<green>xiuxian_impart数据库核对成功!</green>")
                c.execute(sql)

        self.conn.commit()

    @classmethod
    def close_dbs(cls):
        XIUXIAN_IMPART_BUFF().close()

    def create_user(self, user_id):
        """校验用户是否存在"""
        cur = self.conn.cursor()
        sql = f"select * from xiuxian_impart WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if not result:
            return False
        else:
            return True

    def _create_user(self, user_id: str) -> None:
        """在数据库中创建用户并初始化"""
        if self.create_user(user_id):
            pass
        else:
            c = self.conn.cursor()
            sql = f"INSERT INTO xiuxian_impart (user_id, impart_hp_per, impart_atk_per, impart_mp_per, impart_exp_up ,boss_atk,impart_know_per,impart_burst_per,impart_mix_per,impart_reap_per,impart_two_exp,stone_num,exp_day,wish) VALUES(?, 0, 0, 0, 0 ,0, 0, 0, 0, 0 ,0 ,0 ,0, 0)"
            c.execute(sql, (user_id,))
            self.conn.commit()

    def get_user_impart_info_with_id(self, user_id):
        """根据USER_ID获取用户impart_buff信息"""
        cur = self.conn.cursor()
        sql = f"select * from xiuxian_impart WHERE user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def insert_invite(self, group_id, user_id, real_group_id=None, real_user_id=None):
        """插入事件数据"""
        c = self.conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            c.execute('''
                SELECT 1 FROM INVITE WHERE group_id = ? AND user_id = ?
            ''', (group_id, user_id))
            records = c.fetchone()

            if records:
                return False  # 返回 False 表示未插入        
            c.execute('''
                INSERT INTO INVITE (group_id, user_id, real_group_id, real_user_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (group_id, user_id, real_group_id, real_user_id, timestamp))
            self.conn.commit()  
            return True  # 返回 True 表示插入成功
        except sqlite3.Error as e:
            self.conn.rollback()  # 回滚事务，确保数据库状态一致
            return False
        finally:
            c.close()        

    def get_ivite_with_gid(self, group_id):
        """根据USER_ID获取用户信息,不获取功法加成"""
        cur = self.conn.cursor()
        sql = f"select * from INVITE WHERE group_id=?"
        cur.execute(sql, (group_id,))
        result = cur.fetchone()
        if result:
            columns = [column[0] for column in cur.description]
            user_dict = dict(zip(columns, result))
            return user_dict
        else:
            return None

    def delete_invite(self, group_id):
        """根据 user_id 删除邀请"""    
        sql = 'DELETE FROM INVITE WHERE group_id = ?'
        cur = self.conn.cursor()
        cur.execute(sql, (group_id,))  
        self.conn.commit()

    def get_invite_num(self, user_id):
        """
        获取特定 user_id 在 INVITE 表中的总条数
        """
        sql = "SELECT count(1) FROM INVITE WHERE user_id = ?"
        cur = self.conn.cursor()  # 获取游标
        try:
            cur.execute(sql, (user_id,))  # 传递参数执行查询
            result = cur.fetchone()
            # 返回 user_id 的总条数
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"查询时发生错误: user_id={user_id}, 错误信息: {e}")
            return 0
        finally:
            cur.close()  # 确保游标被关闭        

    def update_impart_hp_per(self, impart_num, user_id):
        """更新impart_hp_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_hp_per=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_hp_per(self, impart_num, user_id):
        """add impart_hp_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_hp_per=impart_hp_per+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_atk_per(self, impart_num, user_id):
        """更新impart_atk_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_atk_per=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_atk_per(self, impart_num, user_id):
        """add  impart_atk_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_atk_per=impart_atk_per+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_mp_per(self, impart_num, user_id):
        """impart_mp_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_mp_per=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_mp_per(self, impart_num, user_id):
        """add impart_mp_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_mp_per=impart_mp_per+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_exp_up(self, impart_num, user_id):
        """impart_exp_up"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_exp_up=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_exp_up(self, impart_num, user_id):
        """add impart_exp_up"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_exp_up=impart_exp_up+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_boss_atk(self, impart_num, user_id):
        """boss_atk"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET boss_atk=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_boss_atk(self, impart_num, user_id):
        """add boss_atk"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET boss_atk=boss_atk+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_know_per(self, impart_num, user_id):
        """impart_know_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_know_per=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_know_per(self, impart_num, user_id):
        """add impart_know_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_know_per=impart_know_per+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_burst_per(self, impart_num, user_id):
        """impart_burst_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_burst_per=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_burst_per(self, impart_num, user_id):
        """add impart_burst_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_burst_per=impart_burst_per+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_mix_per(self, impart_num, user_id):
        """impart_mix_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_mix_per=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_mix_per(self, impart_num, user_id):
        """add impart_mix_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_mix_per=impart_mix_per+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_reap_per(self, impart_num, user_id):
        """impart_reap_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_reap_per=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_reap_per(self, impart_num, user_id):
        """add impart_reap_per"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_reap_per=impart_reap_per+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_two_exp(self, impart_num, user_id):
        """更新双修"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_two_exp=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_two_exp(self, impart_num, user_id):
        """add impart_two_exp"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET impart_two_exp=impart_two_exp+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_impart_wish(self, impart_num, user_id):
        """更新抽卡次数"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET wish=? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def add_impart_wish(self, impart_num, user_id):
        """增加抽卡次数"""
        cur = self.conn.cursor()
        sql = f"UPDATE xiuxian_impart SET wish=wish+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def update_stone_num(self, impart_num, user_id, type_):
        """更新结晶数量"""
        if type_ == 1:
            cur = self.conn.cursor()
            sql = f"UPDATE xiuxian_impart SET stone_num=stone_num+? WHERE user_id=?"
            cur.execute(sql, (impart_num, user_id))
            self.conn.commit()
            return True
        if type_ == 2:
            cur = self.conn.cursor()
            sql = f"UPDATE xiuxian_impart SET stone_num=stone_num-? WHERE user_id=?"
            cur.execute(sql, (impart_num, user_id))
            self.conn.commit()
            return True

    def update_impart_stone_all(self, impart_stone):
        """所有用户增加结晶"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET stone_num=stone_num+?"
        cur.execute(sql, (impart_stone,))
        self.conn.commit()

    def add_impart_exp_day(self, impart_num, user_id):
        """add impart_exp_day"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET exp_day=exp_day+? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True

    def use_impart_exp_day(self, impart_num, user_id):
        """use impart_exp_day"""
        cur = self.conn.cursor()
        sql = "UPDATE xiuxian_impart SET exp_day=exp_day-? WHERE user_id=?"
        cur.execute(sql, (impart_num, user_id))
        self.conn.commit()
        return True


def leave_harm_time(user_id):
    """重伤恢复时间"""
    hp_speed = 25
    user_mes = sql_message.get_user_info_with_id(user_id)
    level = user_mes['level']
    level_rate = sql_message.get_root_rate(user_mes['root_type']) # 灵根倍率
    realm_rate = jsondata.level_data()[level]["spend"] # 境界倍率
    main_buff_data = UserBuffDate(user_id).get_user_main_buff_data() # 主功法数据
    main_buff_rate_buff = main_buff_data['ratebuff'] if main_buff_data else 0 # 主功法修炼倍率
    
    try:
       time = int(((user_mes['exp'] / 1.5) - user_mes['hp']) / ((XiuConfig().closing_exp * level_rate * realm_rate * (
                    1 + main_buff_rate_buff)) * hp_speed))
    except ZeroDivisionError:
        time = "无穷大"
    except OverflowError:
        time = "溢出"
    return time


async def impart_check(user_id):
    if XIUXIAN_IMPART_BUFF().get_user_impart_info_with_id(user_id) is None:
        XIUXIAN_IMPART_BUFF()._create_user(user_id)
        return XIUXIAN_IMPART_BUFF().get_user_impart_info_with_id(user_id)
    else:
        return XIUXIAN_IMPART_BUFF().get_user_impart_info_with_id(user_id)
    
xiuxian_impart = XIUXIAN_IMPART_BUFF()

@DRIVER.on_shutdown
async def close_db():
    XIUXIAN_IMPART_BUFF().close()


# 这里是buff部分
class BuffJsonDate:

    def __init__(self):
        """json文件路径"""
        self.mainbuff_jsonpath = SKILLPATHH / "主功法.json"
        self.secbuff_jsonpath = SKILLPATHH / "神通.json"
        self.gfpeizhi_jsonpath = SKILLPATHH / "功法概率设置.json"
        self.weapon_jsonpath = WEAPONPATH / "法器.json"
        self.armor_jsonpath = WEAPONPATH / "防具.json"

    def get_main_buff(self, id):
        return readf(self.mainbuff_jsonpath)[str(id)]

    def get_sec_buff(self, id):
        return readf(self.secbuff_jsonpath)[str(id)]

    def get_gfpeizhi(self):
        return readf(self.gfpeizhi_jsonpath)

    def get_weapon_data(self):
        return readf(self.weapon_jsonpath)

    def get_weapon_info(self, id):
        return readf(self.weapon_jsonpath)[str(id)]

    def get_armor_data(self):
        return readf(self.armor_jsonpath)

    def get_armor_info(self, id):
        return readf(self.armor_jsonpath)[str(id)]


class UserBuffDate:
    def __init__(self, user_id):
        """用户Buff数据"""
        self.user_id = user_id

    @property
    def BuffInfo(self):
        """获取最新的 Buff 信息"""
        return get_user_buff(self.user_id)

    def get_user_main_buff_data(self):
        main_buff_data = None
        buff_info = self.BuffInfo
        main_buff_id = buff_info.get('main_buff', 0)
        if main_buff_id != 0:
            main_buff_data = items.get_data_by_item_id(main_buff_id)
        return main_buff_data
    
    def get_user_sub_buff_data(self):
        sub_buff_data = None
        buff_info = self.BuffInfo
        sub_buff_id = buff_info.get('sub_buff', 0)
        if sub_buff_id != 0:
            sub_buff_data = items.get_data_by_item_id(sub_buff_id)
        return sub_buff_data

    def get_user_sec_buff_data(self):
        sec_buff_data = None
        buff_info = self.BuffInfo
        sec_buff_id = buff_info.get('sec_buff', 0)
        if sec_buff_id != 0:
            sec_buff_data = items.get_data_by_item_id(sec_buff_id)
        return sec_buff_data

    def get_user_weapon_data(self):
        weapon_data = None
        buff_info = self.BuffInfo
        weapon_id = buff_info.get('faqi_buff', 0)
        if weapon_id != 0:
           # num = XiuxianDateManage.goods_num(self.user_id, weapon_id)         
          #  if num >= 1:
            weapon_data = items.get_data_by_item_id(weapon_id)  
        return weapon_data

    def get_user_armor_buff_data(self):
        armor_buff_data = None
        buff_info = self.BuffInfo
        armor_buff_id = buff_info.get('armor_buff', 0)
        if armor_buff_id != 0:
           # num = XiuxianDateManage.goods_num(self.user_id, weapon_id)         
           # if num >= 1:
            armor_buff_data = items.get_data_by_item_id(armor_buff_id)
        return armor_buff_data


def get_weapon_info_msg(weapon_id, weapon_info=None):
    """
    获取一个法器(武器)信息msg
    :param weapon_id:法器(武器)ID
    :param weapon_info:法器(武器)信息json,可不传
    :return 法器(武器)信息msg
    """
    msg = ''
    if weapon_info is None:
        weapon_info = items.get_data_by_item_id(weapon_id)
    atk_buff_msg = f"提升{round(weapon_info['atk_buff'] * 100)}%攻击力！" if weapon_info['atk_buff'] != 0 else ''
    crit_buff_msg = f"提升{round(weapon_info['crit_buff'] * 100)}%会心率！" if weapon_info['crit_buff'] != 0 else ''
    crit_atk_msg = f"提升{round(weapon_info['critatk'] * 100)}%会心伤害！" if weapon_info['critatk'] != 0 else ''
    # def_buff_msg = f"提升{int(weapon_info['def_buff'] * 100)}%减伤率！" if weapon_info['def_buff'] != 0 else ''
    def_buff_msg = f"{'提升' if weapon_info['def_buff'] > 0 else '降低'}{int(abs(weapon_info['def_buff']) * 100)}%减伤率！" if weapon_info['def_buff'] != 0 else ''
    zw_buff_msg = f"装备专属武器时提升伤害！！" if weapon_info['zw'] != 0 else ''
    mp_buff_msg = f"降低真元消耗{round(weapon_info['mp_buff'] * 100)}%！" if weapon_info['mp_buff'] != 0 else ''
  #  msg += f"名字：{weapon_info['name']}\n"
    msg += f"\n{weapon_info['item_type']}：<qqbot-cmd-input text=\"使用{weapon_info['name']}\" show=\"{weapon_info['name']}\" /> {weapon_info['level']}"
    msg += f"\n效果：{atk_buff_msg}{crit_buff_msg}{crit_atk_msg}{def_buff_msg}{mp_buff_msg}{zw_buff_msg}\n\n>{weapon_info['desc']}"
    return msg

def get_weapon_info_msg_1(weapon_id, weapon_info=None):
    """
    获取一个法器(武器)信息msg
    :param weapon_id:法器(武器)ID
    :param weapon_info:法器(武器)信息json,可不传
    :return 法器(武器)信息msg
    """
    msg = ''
    if weapon_info is None:
        weapon_info = items.get_data_by_item_id(weapon_id)
    atk_buff_msg = f"提升{round(weapon_info['atk_buff'] * 100)}%攻击力！" if weapon_info['atk_buff'] != 0 else ''
    crit_buff_msg = f"提升{round(weapon_info['crit_buff'] * 100)}%会心率！" if weapon_info['crit_buff'] != 0 else ''
    crit_atk_msg = f"提升{round(weapon_info['critatk'] * 100)}%会心伤害！" if weapon_info['critatk'] != 0 else ''
    def_buff_msg = f"{'提升' if weapon_info['def_buff'] > 0 else '降低'}{int(abs(weapon_info['def_buff']) * 100)}%减伤率！" if weapon_info['def_buff'] != 0 else ''
    zw_buff_msg = f"装备专属武器时提升伤害！！" if weapon_info['zw'] != 0 else ''
    mp_buff_msg = f"降低真元消耗{round(weapon_info['mp_buff'] * 100)}%！" if weapon_info['mp_buff'] != 0 else ''
  #  msg += f"名字：{weapon_info['name']}\n"
    msg += f"\n><qqbot-cmd-input text=\"查看物品效果{weapon_id}\" show=\"{weapon_info['name']}\" /> {weapon_info['level']}"
 #   msg += f"\n>效果：{atk_buff_msg}{crit_buff_msg}{crit_atk_msg}{def_buff_msg}{mp_buff_msg}{zw_buff_msg}"
    return msg

def get_armor_info_msg(armor_id, armor_info=None):
    """
    获取一个法宝(防具)信息msg
    :param armor_id:法宝(防具)ID
    :param armor_info;法宝(防具)信息json,可不传
    :return 法宝(防具)信息msg
    """
    msg = ''
    if armor_info is None:
        armor_info = items.get_data_by_item_id(armor_id)
    def_buff_msg = f"提升{round(armor_info['def_buff'] * 100)}%减伤率！"
    atk_buff_msg = f"提升{round(armor_info['atk_buff'] * 100)}%攻击力！" if armor_info['atk_buff'] != 0 else ''
    crit_buff_msg = f"提升{round(armor_info['crit_buff'] * 100)}%会心率！" if armor_info['crit_buff'] != 0 else ''
 #   msg += f"物品名称   物品品阶   \n"
    msg += f"\n{armor_info['item_type']}：<qqbot-cmd-input text=\"查看物品效果{armor_id}\" show=\"{armor_info['name']}\" /> {armor_info['level']} "
    msg += f"\n效果：{def_buff_msg}{atk_buff_msg}{crit_buff_msg}\n\n>{armor_info['desc']}"
    return msg

def get_armor_info_msg_1(armor_id, armor_info=None):
    """
    获取一个法宝(防具)信息msg
    :param armor_id:法宝(防具)ID
    :param armor_info;法宝(防具)信息json,可不传
    :return 法宝(防具)信息msg
    """
    msg = ''
    if armor_info is None:
        armor_info = items.get_data_by_item_id(armor_id)
    def_buff_msg = f"提升{round(armor_info['def_buff'] * 100)}%减伤率！"
    atk_buff_msg = f"提升{round(armor_info['atk_buff'] * 100)}%攻击力！" if armor_info['atk_buff'] != 0 else ''
    crit_buff_msg = f"提升{round(armor_info['crit_buff'] * 100)}%会心率！" if armor_info['crit_buff'] != 0 else ''
 #   msg += f"物品名称   物品品阶   \n"
    msg += f"\n><qqbot-cmd-input text=\"查看物品效果{armor_id}\" show=\"{armor_info['name']}\" /> {armor_info['level']}"
 #   msg += f"\n>效果：{def_buff_msg}{atk_buff_msg}{crit_buff_msg}"
    return msg

def get_main_info_msg(id):
    mainbuff = items.get_data_by_item_id(id)
    hpmsg = f"提升{round(mainbuff['hpbuff'] * 100, 0)}%气血" if mainbuff['hpbuff'] != 0 else ''
    mpmsg = f"，提升{round(mainbuff['mpbuff'] * 100, 0)}%真元" if mainbuff['mpbuff'] != 0 else ''
    atkmsg = f"，提升{round(mainbuff['atkbuff'] * 100, 0)}%攻击力" if mainbuff['atkbuff'] != 0 else ''
    ratemsg = f"，提升{round(mainbuff['ratebuff'] * 100, 0)}%修炼速度" if mainbuff['ratebuff'] != 0 else ''
    
    cri_tmsg = f"，提升{round(mainbuff['crit_buff'] * 100, 0)}%会心率" if mainbuff['crit_buff'] != 0 else ''
    def_msg = f"，{'提升' if mainbuff['def_buff'] > 0 else '降低'}{round(abs(mainbuff['def_buff']) * 100, 0)}%减伤率" if mainbuff['def_buff'] != 0 else ''
    dan_msg = f"，增加炼丹产出{round(mainbuff['dan_buff'])}枚" if mainbuff['dan_buff'] != 0 else ''
    dan_exp_msg = f"，每枚丹药额外增加{round(mainbuff['dan_exp'])}炼丹经验" if mainbuff['dan_exp'] != 0 else ''
    reap_msg = f"，提升药材收取数量{round(mainbuff['reap_buff'])}个" if mainbuff['reap_buff'] != 0 else ''
    exp_msg = f"，突破失败{round(mainbuff['exp_buff'] * 100, 0)}%经验保护" if mainbuff['exp_buff'] != 0 else ''
    critatk_msg = f"，提升{round(mainbuff['critatk'] * 100, 0)}%会心伤害" if mainbuff['critatk'] != 0 else ''
    two_msg = f"，增加{round(mainbuff['two_buff'])}次双修次数" if mainbuff['two_buff'] != 0 else ''
    number_msg = f"，提升{round(mainbuff['number'])}%突破概率" if mainbuff['number'] != 0 else ''
    
    clo_exp_msg = f"，提升{round(mainbuff['clo_exp'] * 100, 0)}%闭关经验" if mainbuff['clo_exp'] != 0 else ''
    clo_rs_msg = f"，提升{round(mainbuff['clo_rs'] * 100, 0)}%闭关生命回复" if mainbuff['clo_rs'] != 0 else ''
    random_buff_msg = f"，战斗时随机获得一个战斗属性" if mainbuff['random_buff'] != 0 else ''
    ew_msg =  f"，使用专属武器时伤害增加50%！" if mainbuff['ew'] != 0 else ''
    msg = f"{mainbuff['name']}: {hpmsg}{mpmsg}{atkmsg}{ratemsg}{cri_tmsg}{def_msg}{dan_msg}{dan_exp_msg}{reap_msg}{exp_msg}{critatk_msg}{two_msg}{number_msg}{clo_exp_msg}{clo_rs_msg}{random_buff_msg}{ew_msg}！"
    return mainbuff, msg

def get_sub_info_msg(id): #辅修功法8
    subbuff = items.get_data_by_item_id(id)
    submsg = ""
    if subbuff['buff_type'] == '1':
        submsg = "提升" + subbuff['buff'] + "%攻击力"
    if subbuff['buff_type'] == '2':
        submsg = "提升" + subbuff['buff'] + "%暴击率"
    if subbuff['buff_type'] == '3':
        submsg = "提升" + subbuff['buff'] + "%暴击伤害"
    if subbuff['buff_type'] == '4':
        submsg = "提升" + subbuff['buff'] + "%每回合气血回复"
    if subbuff['buff_type'] == '5':
        submsg = "提升" + subbuff['buff'] + "%每回合真元回复"
    if subbuff['buff_type'] == '6':
        submsg = "提升" + subbuff['buff'] + "%气血吸取"
    if subbuff['buff_type'] == '7':
        submsg = "提升" + subbuff['buff'] + "%真元吸取"
    if subbuff['buff_type'] == '8':
        submsg = "给对手造成" + subbuff['buff'] + "%中毒"
    if subbuff['buff_type'] == '9':
        submsg = f"提升{subbuff['buff']}%气血吸取,提升{subbuff['buff2']}%真元吸取"

    stone_msg  = "提升{}%boss战灵石获取".format(round(subbuff['stone'] * 100, 0)) if subbuff['stone'] != 0 else ''
    integral_msg = "，提升{}点boss战积分获取".format(round(subbuff['integral'])) if subbuff['integral'] != 0 else ''
    jin_msg = "禁止对手吸取" if subbuff['jin'] != 0 else ''
    drop_msg = "，提升boss掉落率" if subbuff['drop'] != 0 else ''
    fan_msg = "使对手发出的debuff失效" if subbuff['fan'] != 0 else ''
    break_msg = "获得战斗破甲" if subbuff['break'] != 0 else ''
    exp_msg = "，增加战斗获得的修为" if subbuff['exp'] != 0 else ''
    

    msg = f"{subbuff['name']}：{submsg}{stone_msg}{integral_msg}{jin_msg}{drop_msg}{fan_msg}{break_msg}{exp_msg}"
    return subbuff, msg

def get_user_buff(user_id):
    BuffInfo = sql_message.get_user_buff_info(user_id)
    if BuffInfo is None:
        sql_message.initialize_user_buff_info(user_id)
        return sql_message.get_user_buff_info(user_id)
    else:
        return BuffInfo


def readf(FILEPATH):
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def get_sec_msg(secbuffdata):
    msg = None
    if secbuffdata is None:
        msg = "无"
        return msg
    hpmsg = f"，消耗当前血量{int(secbuffdata['hpcost'] * 100)}%" if secbuffdata['hpcost'] != 0 else ''
    mpmsg = f"，消耗真元{int(secbuffdata['mpcost'] * 100)}%" if secbuffdata['mpcost'] != 0 else ''

    if secbuffdata['skill_type'] == 1:
        shmsg = ''
        for value in secbuffdata['atkvalue']:
            shmsg += f"{value}倍、"
        if secbuffdata['turncost'] == 0:
            msg = f"攻击{len(secbuffdata['atkvalue'])}次，造成{shmsg[:-1]}伤害{hpmsg}{mpmsg}，释放概率：{secbuffdata['rate']}%"
        else:
            msg = f"连续攻击{len(secbuffdata['atkvalue'])}次，造成{shmsg[:-1]}伤害{hpmsg}{mpmsg}，休息{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
    elif secbuffdata['skill_type'] == 2:
        msg = f"持续伤害，造成{secbuffdata['atkvalue']}倍攻击力伤害{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
    elif secbuffdata['skill_type'] == 3:
        if secbuffdata['bufftype'] == 1:
            msg = f"增强自身，提高{secbuffdata['buffvalue']}倍攻击力{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
        elif secbuffdata['bufftype'] == 2:
            msg = f"增强自身，提高{secbuffdata['buffvalue'] * 100}%减伤率{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%"
    elif secbuffdata['skill_type'] == 4:
        msg = f"封印对手{hpmsg}{mpmsg}，持续{secbuffdata['turncost']}回合，释放概率：{secbuffdata['rate']}%，命中成功率{secbuffdata['success']}%"

    return msg


def get_player_info(user_id, info_name):
    player_info = None
    if info_name == "mix_elixir_info":  # 灵田信息
        mix_elixir_infoconfigkey = ["收取时间", "收取等级", "灵田数量", '药材速度', "丹药控火", "丹药耐药性", "炼丹记录", "炼丹经验"]
        nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
        MIXELIXIRINFOCONFIG = {
            "收取时间": nowtime,
            "收取等级": 0,
            "灵田数量": 1,
            '药材速度': 0,
            "丹药控火": 0,
            "丹药耐药性": 0,
            "炼丹记录": {},
            "炼丹经验": 0
        }
        try:
            player_info = read_player_info(user_id, info_name)
            for key in mix_elixir_infoconfigkey:
                if key not in list(player_info.keys()):
                    player_info[key] = MIXELIXIRINFOCONFIG[key]
            save_player_info(user_id, player_info, info_name)
        except:
            player_info = MIXELIXIRINFOCONFIG
            save_player_info(user_id, player_info, info_name)
    return player_info


def read_player_info(user_id, info_name):
    user_id = str(user_id)
    FILEPATH = PLAYERSDATA / user_id / f"{info_name}.json"
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def save_player_info(user_id, data, info_name):
    user_id = str(user_id)

    if not os.path.exists(PLAYERSDATA / user_id):
        logger.opt(colors=True).info(f"<green>用户目录不存在，创建目录</green>")
        os.makedirs(PLAYERSDATA / user_id)

    FILEPATH = PLAYERSDATA / user_id / f"{info_name}.json"
    data = json.dumps(data, ensure_ascii=False, indent=4)
    save_mode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=save_mode, encoding="UTF-8") as f:
        f.write(data)
        f.close()