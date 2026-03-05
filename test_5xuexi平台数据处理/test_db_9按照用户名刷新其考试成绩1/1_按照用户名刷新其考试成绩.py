import pymysql
from pymysql.cursors import DictCursor
import random
import getpass
import math

# 数据库连接配置
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def connect_database():
    """连接数据库"""
    try:
        connection = pymysql.connect(**target_config)
        return connection
    except pymysql.Error as e:
        print(f"数据库连接失败: {e}")
        return None


def find_user_by_name(connection, realname):
    """根据姓名查找用户ID"""
    try:
        with connection.cursor() as cursor:
            sql = "SELECT user_id, username, realname FROM sys_user WHERE realname = %s AND deleted = 0"
            cursor.execute(sql, (realname,))
            result = cursor.fetchall()
            return result
    except pymysql.Error as e:
        print(f"查询用户失败: {e}")
        return []


def get_user_courses(connection, user_id):
    """根据用户ID获取所有课程记录"""
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT id, user_id, course_id, learing_progress, learing_score, exam_score, total_score 
            FROM t_user_course 
            WHERE user_id = %s AND deleted = 0
            """
            cursor.execute(sql, (user_id,))
            return cursor.fetchall()
    except pymysql.Error as e:
        print(f"查询用户课程失败: {e}")
        return []


def update_course_scores(connection, course_records):
    """更新课程成绩并重新计算总分（向下取整）"""
    updated_count = 0

    try:
        with connection.cursor() as cursor:
            for record in course_records:
                course_id = record['id']
                learning_score = record['learing_score'] or 0
                exam_score = record['exam_score'] or 0

                # 检查是否需要更新exam_score
                need_update = False
                if record['exam_score'] is None or record['exam_score'] == 0:
                    # 生成78-92之间的随机数
                    new_exam_score = random.randint(78, 92)
                    exam_score = new_exam_score
                    need_update = True

                # 重新计算总分（学习分数和考试分数各占50%，向下取整）
                if record['learing_score'] is not None and record['learing_score'] > 0:
                    # 计算总分并向下取整
                    total_score_calculated = (learning_score * 0.5) + (exam_score * 0.5)
                    new_total_score = math.floor(total_score_calculated)  # 向下取整

                    # 只有当需要更新exam_score或者总分需要重新计算时才执行更新
                    if need_update or new_total_score != (record['total_score'] or 0):
                        update_sql = """
                        UPDATE t_user_course 
                        SET exam_score = %s, total_score = %s, update_time = CURRENT_TIMESTAMP 
                        WHERE id = %s
                        """
                        cursor.execute(update_sql, (exam_score, new_total_score, course_id))
                        updated_count += 1
                        print(
                            f"更新记录ID {course_id}: exam_score={exam_score}, total_score={new_total_score} (计算值: {total_score_calculated:.2f})")

        # 提交事务
        connection.commit()
        return updated_count

    except pymysql.Error as e:
        connection.rollback()
        print(f"更新成绩失败: {e}")
        return 0


def main():
    """主函数"""
    # 获取用户输入的姓名
    realname = input("请输入要查询的用户姓名: ").strip()

    if not realname:
        print("姓名不能为空！")
        return

    # 连接数据库
    print("正在连接数据库...")
    connection = connect_database()
    if not connection:
        return

    try:
        # 根据姓名查找用户
        print(f"正在查找用户: {realname}")
        users = find_user_by_name(connection, realname)

        if not users:
            print(f"未找到姓名为 '{realname}' 的用户")
            return

        if len(users) > 1:
            print(f"找到多个姓名为 '{realname}' 的用户:")
            for i, user in enumerate(users, 1):
                print(f"{i}. 用户ID: {user['user_id']}, 用户名: {user['username']}, 姓名: {user['realname']}")

            # 让用户选择具体的用户
            while True:
                try:
                    choice = int(input("请选择要操作的用户编号: "))
                    if 1 <= choice <= len(users):
                        selected_user = users[choice - 1]
                        break
                    else:
                        print("请输入有效的编号")
                except ValueError:
                    print("请输入数字")
        else:
            selected_user = users[0]

        user_id = selected_user['user_id']
        print(f"选择用户: ID={user_id}, 姓名={selected_user['realname']}")

        # 获取用户的所有课程记录
        print("正在获取用户课程记录...")
        course_records = get_user_courses(connection, user_id)

        if not course_records:
            print("该用户没有课程记录")
            return

        print(f"找到 {len(course_records)} 条课程记录")

        # 筛选需要更新的记录
        records_to_update = []
        for record in course_records:
            if record['exam_score'] is None or record['exam_score'] == 0:
                records_to_update.append(record)

        if not records_to_update:
            print("没有需要更新的记录（所有记录的exam_score都已存在且不为0）")
            return

        print(f"找到 {len(records_to_update)} 条需要更新的记录")

        # 显示将要更新的记录预览
        print("\n将要更新的记录预览:")
        for record in records_to_update[:5]:  # 只显示前5条作为预览
            print(f"课程ID: {record['course_id']}, 学习进度: {record['learing_progress']}%, "
                  f"学习分数: {record['learing_score']}, 考试分数: {record['exam_score']}")

        if len(records_to_update) > 5:
            print(f"... 还有 {len(records_to_update) - 5} 条记录")

        # 确认是否继续
        confirm = input("\n是否继续更新？(y/n): ").strip().lower()
        if confirm != 'y':
            print("操作已取消")
            return

        # 更新成绩
        print("开始更新成绩...")
        updated_count = update_course_scores(connection, records_to_update)

        print(f"成功更新 {updated_count} 条记录")

    finally:
        connection.close()
        print("数据库连接已关闭")


if __name__ == "__main__":
    main()