import pymysql
from pymysql.cursors import DictCursor

# 数据库配置
source_config = {
    'user': 'root',
    'password': 'Yjydev001',
    'host': 'rm-uf61035g89k83p76nlo.mysql.rds.aliyuncs.com',
    'database': 'db_usr',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def update_scores():
    try:
        # 连接数据库
        source_conn = pymysql.connect(**source_config)
        target_conn = pymysql.connect(**target_config)

        with source_conn.cursor() as source_cursor, target_conn.cursor() as target_cursor:
            batch_size = 1000  # 每批处理1000条
            offset = 0
            total_updated = 0

            while True:
                # 1. 获取当前批次的target记录
                target_cursor.execute(
                    "SELECT id, learing_score, exam_score FROM t_user_course "
                    "LIMIT %s OFFSET %s",
                    (batch_size, offset)
                )
                target_records = target_cursor.fetchall()

                if not target_records:
                    break  # 无更多数据，退出循环

                print(f"处理批次 {offset // batch_size + 1}，共 {len(target_records)} 条记录")

                # 2. 批量获取对应的source数据（直接通过id匹配）
                target_ids = [r['id'] for r in target_records]
                source_cursor.execute(
                    "SELECT id, learn_behavior_score, final_score "
                    "FROM course_schedule "
                    "WHERE id IN %s AND is_deleted = 0",  # 直接通过id关联
                    (target_ids,)
                )
                source_data = {r['id']: r for r in source_cursor.fetchall()}

                # 3. 在内存中比较并生成更新语句
                updates = []
                for target in target_records:
                    if target['id'] in source_data:
                        source = source_data[target['id']]
                        new_learing = target['learing_score'] or 0
                        new_exam = target['exam_score'] or 0
                        need_update = False

                        # 比较学习行为成绩
                        if source['learn_behavior_score'] > new_learing:
                            new_learing = source['learn_behavior_score']
                            need_update = True

                        # 比较结业成绩
                        if source['final_score'] > new_exam:
                            new_exam = source['final_score']
                            need_update = True

                        if need_update:
                            updates.append((new_learing, new_exam, target['id']))

                # 4. 批量执行更新
                if updates:
                    target_cursor.executemany(
                        "UPDATE t_user_course "
                        "SET learing_score=%s, exam_score=%s, update_time=CURRENT_TIMESTAMP "
                        "WHERE id=%s",
                        updates
                    )
                    batch_updated = len(updates)
                    total_updated += batch_updated
                    print(f"本批次更新 {batch_updated} 条，累计更新 {total_updated} 条")

                offset += batch_size
                target_conn.commit()  # 提交当前批次

            print(f"全部完成！总更新 {total_updated} 条记录")

    except Exception as e:
        print(f"处理出错: {e}")
        if 'target_conn' in locals():
            target_conn.rollback()
    finally:
        source_conn.close()
        target_conn.close()


if __name__ == "__main__":
    update_scores()