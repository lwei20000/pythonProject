import pymysql
from pymysql.cursors import DictCursor
import time

# 数据库连接配置
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def update_inconsistent_scores():
    start_time = time.time()
    try:
        # 建立数据库连接
        connection = pymysql.connect(**target_config)

        with connection.cursor() as cursor:
            # 1. 查询需要更新的记录
            print("[{}] 开始查询需要更新的记录...".format(time.strftime("%Y-%m-%d %H:%M:%S")))
            sql_select = """
            SELECT 
                id, 
                user_id, 
                course_id, 
                learing_score, 
                exam_score, 
                total_score AS old_total_score,
                FLOOR((learing_score * 0.5 + exam_score * 0.5)) AS new_total_score
            FROM t_user_course
            WHERE deleted = 0
              AND total_score IS NOT NULL
              AND learing_score IS NOT NULL
              AND exam_score IS NOT NULL
              AND ABS(FLOOR((learing_score * 0.5 + exam_score * 0.5)) - total_score) > 1
            """

            cursor.execute(sql_select)
            results = cursor.fetchall()

            if not results:
                print("[{}] 没有找到需要更新的记录".format(time.strftime("%Y-%m-%d %H:%M:%S")))
                return

            print("[{}] 找到 {} 条需要更新的记录".format(time.strftime("%Y-%m-%d %H:%M:%S"), len(results)))

            # 2. 执行更新操作
            print("[{}] 开始批量更新记录...".format(time.strftime("%Y-%m-%d %H:%M:%S")))
            updated_count = 0
            batch_size = 100  # 每批更新的数量
            total_batches = (len(results) + batch_size - 1) // batch_size

            for i in range(0, len(results), batch_size):
                batch = results[i:i + batch_size]
                sql_update = """
                UPDATE t_user_course
                SET total_score = CASE id
                    {}
                END
                WHERE id IN ({})
                """.format(
                    "\n".join(["WHEN {} THEN {}".format(row['id'], row['new_total_score']) for row in batch]),
                    ",".join([str(row['id']) for row in batch])
                )

                cursor.execute(sql_update)
                updated_count += len(batch)
                connection.commit()

                # 打印进度
                current_batch = (i // batch_size) + 1
                print("[{}] 已更新批次 {}/{} ({}条)".format(
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    current_batch,
                    total_batches,
                    len(batch)
                ))

            print("[{}] 批量更新完成，共更新 {} 条记录".format(time.strftime("%Y-%m-%d %H:%M:%S"), updated_count))

            # 3. 验证更新结果
            print("[{}] 开始验证更新结果...".format(time.strftime("%Y-%m-%d %H:%M:%S")))
            cursor.execute("""
            SELECT COUNT(*) AS error_count
            FROM t_user_course
            WHERE id IN (%s)
            AND ABS(total_score - FLOOR((learing_score * 0.5 + exam_score * 0.5))) > 1
            """ % ",".join([str(row['id']) for row in results]))

            error_count = cursor.fetchone()['error_count']

            if error_count == 0:
                print("[{}] 验证通过，所有记录更新成功".format(time.strftime("%Y-%m-%d %H:%M:%S")))
            else:
                print("[{}] 警告：发现 {} 条记录更新不成功".format(time.strftime("%Y-%m-%d %H:%M:%S"), error_count))

    except pymysql.Error as e:
        print("[{}] 数据库错误: {}".format(time.strftime("%Y-%m-%d %H:%M:%S"), e))
        if 'connection' in locals():
            connection.rollback()
    finally:
        if 'connection' in locals() and connection:
            connection.close()
        elapsed_time = time.time() - start_time
        print("[{}] 脚本执行完成，耗时 {:.2f} 秒".format(time.strftime("%Y-%m-%d %H:%M:%S"), elapsed_time))


if __name__ == "__main__":
    update_inconsistent_scores()