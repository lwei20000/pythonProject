"""
脚本功能说明：
本脚本用于在两个MySQL数据库之间同步论文成绩及相关信息，具体逻辑如下：
1、从目标数据库(db_xuexi.t_user_major)中查询所有thesis_score为空的记录

2、对于每条记录，使用学号(user_number)作为查询条件：
a. 在源数据库(db_usr)中联合查询student_graduation_thesis和student_number表
b. 获取论文成绩(score)、论文URL(thesis_url)和论文标题(title)

3、将查询到的论文信息更新回目标数据库的对应记录中：
a. thesis_score 更新为查询到的 score
b. thesis_file 更新为查询到的 thesis_url
c. thesis_name 更新为查询到的 title
自动维护update_time字段为当前时间

创建时间：2025-5-7
作者：梁威
版本：1.0
"""


import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime

# 数据库连接配置（源数据库）
source_config = {
    'user': 'root',
    'password': 'Yjydev001',
    'host': 'rm-uf61035g89k83p76nlo.mysql.rds.aliyuncs.com',
    'database': 'db_usr',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

# 数据库连接配置（目标数据库）
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def sync_thesis_info():
    try:
        # 连接源数据库
        source_conn = pymysql.connect(**source_config)
        source_cursor = source_conn.cursor()

        # 连接目标数据库
        target_conn = pymysql.connect(**target_config)
        target_cursor = target_conn.cursor()

        print(f"{datetime.now()} - 数据库连接成功")

        # 1. 从目标数据库查询所有thesis_score为空的记录
        query = "SELECT id, user_number FROM t_user_major WHERE thesis_score IS NULL AND user_number IS NOT NULL"
        target_cursor.execute(query)
        records = target_cursor.fetchall()

        print(f"{datetime.now()} - 找到 {len(records)} 条需要更新的记录")

        if not records:
            print(f"{datetime.now()} - 没有需要更新的记录")
            return

        updated_count = 0

        # 2. 对每条记录进行处理
        for record in records:
            user_number = record['user_number']
            target_id = record['id']

            try:
                # 3. 在源数据库中查询论文信息
                thesis_query = """
                SELECT sgt.score, sgt.thesis_url, sgt.title 
                FROM db_usr.student_graduation_thesis sgt,
                     db_usr.student_number sn
                WHERE sgt.end_user_id = sn.end_user_id 
                AND sgt.college_id = 239
                AND sgt.score IS NOT NULL
                AND sn.student_code = %s
                """
                source_cursor.execute(thesis_query, (user_number,))
                thesis_info = source_cursor.fetchone()

                if thesis_info:
                    # 4. 更新目标数据库中的记录
                    update_query = """
                    UPDATE t_user_major 
                    SET thesis_score = %s, 
                        thesis_file = %s, 
                        thesis_name = %s,
                        update_time = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """
                    target_cursor.execute(update_query, (
                        thesis_info['score'],
                        thesis_info['thesis_url'],
                        thesis_info['title'],
                        target_id
                    ))
                    target_conn.commit()
                    updated_count += 1
                    print(f"{datetime.now()} - 已更新学号 {user_number} 的记录(ID: {target_id})")
                else:
                    print(f"{datetime.now()} - 学号 {user_number} 在源数据库中未找到论文信息")

            except Exception as e:
                print(f"{datetime.now()} - 处理学号 {user_number} 时出错: {str(e)}")
                target_conn.rollback()

        print(f"{datetime.now()} - 同步完成，共更新了 {updated_count} 条记录")

    except Exception as e:
        print(f"{datetime.now()} - 发生错误: {str(e)}")
        if 'target_conn' in locals():
            target_conn.rollback()
    finally:
        # 关闭数据库连接
        if 'source_cursor' in locals():
            source_cursor.close()
        if 'source_conn' in locals():
            source_conn.close()
        if 'target_cursor' in locals():
            target_cursor.close()
        if 'target_conn' in locals():
            target_conn.close()
        print(f"{datetime.now()} - 数据库连接已关闭")


if __name__ == "__main__":
    sync_thesis_info()