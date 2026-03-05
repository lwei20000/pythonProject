import pymysql
from pymysql.cursors import DictCursor

# 数据库连接配置
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

# 批量处理的大小
BATCH_SIZE = 1000


def update_user_courses():
    try:
        # 连接数据库
        connection = pymysql.connect(**target_config)

        with connection.cursor() as cursor:
            # 查询符合条件的记录总数
            count_query = """
                SELECT COUNT(*) as total 
                FROM t_user_course 
                WHERE exam_score IS NOT NULL 
                AND learing_score < 90
                AND deleted = 0
            """
            cursor.execute(count_query)
            total = cursor.fetchone()['total']
            print(f"找到 {total} 条需要更新的记录")

            # 分批处理
            offset = 0
            updated_count = 0

            while offset < total:
                # 查询当前批次的记录ID
                select_query = """
                    SELECT id 
                    FROM t_user_course 
                    WHERE exam_score IS NOT NULL 
                    AND learing_score < 90
                    AND deleted = 0
                    ORDER BY id
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, (BATCH_SIZE, offset))
                rows = cursor.fetchall()

                if not rows:
                    break

                # 提取ID列表
                ids = [row['id'] for row in rows]

                # 更新当前批次的记录
                update_query = """
                    UPDATE t_user_course 
                    SET learing_progress = 90, 
                        learing_score = 90,
                        update_time = CURRENT_TIMESTAMP
                    WHERE id IN (%s)
                """ % ','.join(['%s'] * len(ids))

                cursor.execute(update_query, ids)
                connection.commit()

                updated_count += len(ids)
                print(f"已更新 {updated_count}/{total} 条记录")

                offset += BATCH_SIZE

            print(f"更新完成，共更新了 {updated_count} 条记录")

    except Exception as e:
        print(f"发生错误: {e}")
        if 'connection' in locals() and connection:
            connection.rollback()
    finally:
        if 'connection' in locals() and connection:
            connection.close()


if __name__ == '__main__':
    update_user_courses()