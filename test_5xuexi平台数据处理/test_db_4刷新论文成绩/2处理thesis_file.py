import pymysql
from pymysql.cursors import DictCursor
import json
from datetime import datetime

# 数据库连接配置（目标数据库）
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def convert_thesis_file_to_json():
    """
    功能说明：
    本脚本用于将目标数据库中t_user_major表的thesis_file字段从普通URL转换为JSON格式，
    转换规则如下：

    1. 查询thesis_file以"http://testvod."开头的记录
    2. 获取这些记录的thesis_file和thesis_name字段
    3. 将这两个字段组装成指定的JSON格式：
       [{
           "name": thesis_name,
           "url": thesis_file,
           "status": "success"
       }]
    4. 将JSON字符串更新回thesis_file字段

    注意：
    - 只处理符合条件的记录
    - 保持原始URL不变，不做转换
    - 自动维护update_time字段
    - 使用事务确保数据一致性
    """
    try:
        # 连接目标数据库
        conn = pymysql.connect(**target_config)
        cursor = conn.cursor()

        print(f"{datetime.now()} - 数据库连接成功")

        # 1. 查询符合条件的记录
        query = """
        SELECT id, thesis_file, thesis_name 
        FROM t_user_major 
        WHERE thesis_file LIKE 'http://testvod.%'
        AND thesis_file IS NOT NULL
        """
        cursor.execute(query)
        records = cursor.fetchall()

        print(f"{datetime.now()} - 找到 {len(records)} 条需要更新的记录")

        if not records:
            print(f"{datetime.now()} - 没有需要更新的记录")
            return

        updated_count = 0

        # 2. 对每条记录进行处理
        for record in records:
            try:
                thesis_file = record['thesis_file']
                thesis_name = record['thesis_name'] or "未命名论文"

                # 3. 构建JSON数据
                json_data = [{
                    "name": thesis_name,
                    "url": thesis_file,
                    "status": "success"
                }]

                # 4. 更新数据库
                update_query = """
                UPDATE t_user_major 
                SET thesis_file = %s, 
                    update_time = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                cursor.execute(update_query, (json.dumps(json_data, ensure_ascii=False), record['id']))
                conn.commit()

                updated_count += 1
                print(f"{datetime.now()} - 已更新ID {record['id']} 的记录")

            except Exception as e:
                print(f"{datetime.now()} - 处理ID {record['id']} 时出错: {str(e)}")
                conn.rollback()

        print(f"{datetime.now()} - 更新完成，共处理了 {updated_count} 条记录")

    except Exception as e:
        print(f"{datetime.now()} - 发生错误: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        # 关闭数据库连接
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print(f"{datetime.now()} - 数据库连接已关闭")

if __name__ == "__main__":
    convert_thesis_file_to_json()