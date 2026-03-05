import pymysql
from pymysql.cursors import DictCursor
import random
import math
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


def update_student_scores():
    """
    功能说明：
    本脚本用于更新目标数据库中指定学号学生的考试成绩，具体逻辑如下：

    1. 对181个指定学号的学生，查询其课程成绩记录
       - 查询条件：exam_score为null或0的记录
       - 查询字段：learing_score, exam_score, total_score

    2. 对查询到的每条记录：
       a. 在70-95之间随机生成exam_score
       b. 按learning_score和exam_score 5:5比例计算total_score(向上取整)
       c. 更新回数据库

    注意：
    - 每个学号可能对应多条课程记录
    - 所有更新操作在事务中执行
    - 自动维护更新时间
    """
    # 181个指定学号
    student_numbers = [
        '202303405', '202303407', '202303408', '202303444', '202303448',
        '202303452', '202303453', '202303456', '202303459', '202303460',
        '202303461', '202303468', '202303482', '202303528', '202303535',
        '202303542', '202303547', '202303548', '202303550', '202303574',
        '202303577', '202303580', '202303582', '202303585', '202303586',
        '202303589', '202303596', '202303597', '202303599', '202303602',
        '202303612', '202303616', '202303621', '202303622', '202303623',
        '202303626', '202303632', '202303651', '202303655', '202303660',
        '202303668', '202303670', '202303685', '202303705', '202303712',
        '202303714', '202303723', '202303724', '202303754', '202303767',
        '202303768', '202303794', '202303818', '202303826', '202303831',
        '202303833', '202303852', '202303858', '202303870', '202303889',
        '202303901', '202303910', '202303911', '202303914', '202303929',
        '202303961', '202303997', '202303998', '202304000', '202304001',
        '202304012', '202304029', '202304049', '202304055', '202304062',
        '202304079', '202304092', '202304102', '202304105', '202304107',
        '202304119', '202304130', '202304134', '202304144', '202304151',
        '202304154', '202304155', '202304156', '202304157', '202304161',
        '202304163', '202304165', '202304168', '202304193', '202304197',
        '202304201', '202304204', '202304223', '202304226', '202304230',
        '202304236', '202304256', '202304262', '202304265', '202304283',
        '202304284', '202304303', '202304328', '202304329', '202304330',
        '202304333', '202304336', '202304360', '202304361', '202304362',
        '202304364', '202304368', '202304374', '202304379', '202304380',
        '202304398', '202304412', '202304425', '202304442', '202304446',
        '202304453', '202304460', '202304464', '202304491', '202304509',
        '202304512', '202304530', '202304531', '202304539', '202304540',
        '202304543', '202304556', '202304557', '202304560', '202304567',
        '202304572', '202304573', '202304589', '202304602', '202304609',
        '202304614', '202304617', '202304621', '202304626', '202304631',
        '202304657', '202304663', '202304677', '202304723', '202304752',
        '202304762', '202304766', '202304768', '202304770', '202304774',
        '202304775', '202304776', '202304784', '202304786', '202304789',
        '202304794', '202304796', '202304809', '202304813', '202304825',
        '202304839', '202304845', '202304851', '202304857', '202304858',
        '202304872', '202304874', '202304901', '202304915', '202304916',
        '202304918', '202304788'
    ]

    try:
        # 连接目标数据库
        conn = pymysql.connect(**target_config)
        cursor = conn.cursor()

        print(f"{datetime.now()} - 数据库连接成功")

        total_updated = 0

        # 遍历每个学号
        for student_number in student_numbers:
            try:
                # 1. 查询该学号的学生课程成绩
                query = """
                SELECT tuc.id, tuc.learing_score, tuc.exam_score, tuc.total_score
                FROM t_user_course tuc, t_user_major tum 
                WHERE tuc.user_id = tum.user_id
                AND (tuc.exam_score IS NULL OR tuc.exam_score = 0)
                AND tum.user_number = %s
                """
                cursor.execute(query, (student_number,))
                records = cursor.fetchall()

                if not records:
                    print(f"{datetime.now()} - 学号 {student_number} 没有需要更新的记录")
                    continue

                # 2. 更新每条课程记录
                for record in records:
                    learning_score = record['learing_score'] or 0

                    # 生成随机考试成绩(70-95)
                    exam_score = random.randint(70, 95)

                    # 计算总成绩(5:5比例，向上取整)
                    total_score = math.ceil(learning_score * 0.5 + exam_score * 0.5)

                    # 更新数据库
                    update_query = """
                    UPDATE t_user_course 
                    SET exam_score = %s,
                        total_score = %s,
                        update_time = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """
                    cursor.execute(update_query, (exam_score, total_score, record['id']))
                    conn.commit()

                    total_updated += 1
                    print(f"{datetime.now()} - 学号 {student_number} 记录ID {record['id']} 已更新: "
                          f"learning_score={learning_score}, exam_score={exam_score}, total_score={total_score}")

            except Exception as e:
                print(f"{datetime.now()} - 处理学号 {student_number} 时出错: {str(e)}")
                conn.rollback()

        print(f"{datetime.now()} - 更新完成，共更新了 {total_updated} 条记录")

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
    update_student_scores()