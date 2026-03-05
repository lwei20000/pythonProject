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

def process_exam_scores():
    try:
        # 建立数据库连接
        connection = pymysql.connect(**target_config)

        with connection.cursor() as cursor:
            # 1. 搜索出所有exam_score大于100分的记录
            select_query = """
                SELECT id, user_id, course_id, exam_score, total_score
                FROM t_user_course 
                WHERE exam_score > 100 AND deleted = 0
            """
            cursor.execute(select_query)
            records = cursor.fetchall()

            if not records:
                print("没有找到exam_score大于100分的记录")
                return

            print("找到以下exam_score大于100分的记录：")
            for record in records:
                print(f"ID: {record['id']}, 用户ID: {record['user_id']}, 课程ID: {record['course_id']}, 考试成绩: {record['exam_score']},总成绩: {record['total_score']}")

            # 2. 将这些记录的exam_score更新为100
            # update_query = """
            #     UPDATE t_user_course
            #     SET exam_score = 100
            #     WHERE exam_score > 100 AND deleted = 0
            # """
            # cursor.execute(update_query)
            # affected_rows = cursor.rowcount
            # connection.commit()

            print(f"\n成功更新了{affected_rows}条记录的exam_score为100")

    except pymysql.Error as e:
        print(f"数据库操作出错: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    process_exam_scores()