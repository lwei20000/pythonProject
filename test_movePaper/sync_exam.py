import pymysql
import json
import sys
from datetime import datetime

def sync_exam(course_name):
    """
    根据课程名称同步试卷数据
    :param course_name: 课程名称
    :return: 同步结果（字符串）
    """
    # 数据库连接配置（源数据库）
    source_config = {
        'user': 'root',
        'password': 'Yjydev001',
        'host': 'rm-uf61035g89k83p76nlo.mysql.rds.aliyuncs.com',
        'database': 'db_usr',  # 替换为实际的数据库名称
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    # 数据库连接配置（目标数据库）
    target_config = {
        'user': 'root',
        'password': 'wdg@123',
        'host': '120.55.161.50',
        'database': 'db_xuexi',  # 修改为 db_xuexi
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    # 初始化变量
    source_conn = None
    source_cursor = None
    target_conn = None
    target_cursor = None

    try:
        # 连接到源数据库
        source_conn = pymysql.connect(**source_config)
        source_cursor = source_conn.cursor()

        # 查询 exam_paper2 表中的 exam_path 和 answer_card 字段
        query = """
            SELECT ep.exam_path, ep.answer_card  
            FROM exam_paper2 ep, course c, organization org 
            WHERE ep.course_id = c.id 
            AND ep.college_id = org.id 
            AND org.id = 239  # -- 长春大学
            AND c.course_name = %s
        """
        source_cursor.execute(query, (course_name,))

        # 获取所有行的数据
        rows = source_cursor.fetchall()

        # 检查查询结果
        if len(rows) == 0:
            return f"课程 {course_name} 没有找到试卷数据"
        elif len(rows) > 1:
            return f"课程 {course_name} 找到多条记录，请检查数据唯一性"
        else:
            # 获取唯一记录
            exam_path = rows[0]['exam_path']
            answer_card_json = rows[0]['answer_card']

            # 解析 answer_card 字段
            try:
                answer_card_data = json.loads(answer_card_json)  # 解析 JSON 数据
            except json.JSONDecodeError as e:
                return f"JSON 解析错误: {e}"

            # 连接到目标数据库
            target_conn = pymysql.connect(**target_config)
            target_cursor = target_conn.cursor()

            # 校验一：在 t_course 表中按照 course_name 搜索记录
            check_course_query = """
                SELECT course_id 
                FROM t_course 
                WHERE course_name = %s
            """
            target_cursor.execute(check_course_query, (course_name,))
            course_rows = target_cursor.fetchall()

            if len(course_rows) == 0:
                return f"课程 {course_name} 在 t_course 表中不存在"
            elif len(course_rows) > 1:
                return f"课程 {course_name} 在 t_course 表中找到多条记录，请检查数据唯一性"
            else:
                # 获取 course_id
                course_id = course_rows[0]['course_id']

                # 校验二：在 t_paper 表中按照 course_id 搜索记录
                check_paper_query = """
                    SELECT * 
                    FROM t_paper 
                    WHERE course_id = %s
                """
                target_cursor.execute(check_paper_query, (course_id,))
                paper_rows = target_cursor.fetchall()

                if len(paper_rows) > 0:
                    # 删除 t_paper 表中的记录
                    delete_paper_query = """
                        DELETE FROM t_paper 
                        WHERE course_id = %s
                    """
                    target_cursor.execute(delete_paper_query, (course_id,))
                    target_conn.commit()

                # 插入 t_paper 表
                paper_name = course_name  # 试卷名称与课程名称相同
                paper_type = 1
                paper_file = json.dumps([
                    {
                        "name": f"{course_name}.pdf",
                        "url": exam_path,
                        "status": "success"
                    }
                ])
                paper_usage = 1
                deleted = 0
                tenant_id = 7
                create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 插入 t_paper 表
                insert_paper_query = """
                    INSERT INTO t_paper (
                        course_id, paper_name, paper_type, paper_file, 
                        paper_usage, deleted, tenant_id, create_time
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                target_cursor.execute(insert_paper_query, (
                    course_id, paper_name, paper_type, paper_file,
                    paper_usage, deleted, tenant_id, create_time
                ))
                target_conn.commit()

                # 获取插入的 paper_id
                paper_id = target_cursor.lastrowid

                # 检查 t_paper_question 表中是否存在与 paper_id 相关的记录
                check_question_query = """
                    SELECT * 
                    FROM t_paper_question 
                    WHERE paper_id = %s
                """
                target_cursor.execute(check_question_query, (paper_id,))
                question_rows = target_cursor.fetchall()

                if len(question_rows) > 0:
                    print(f"t_paper_question 表中已存在与 paper_id={paper_id} 相关的记录，正在删除...")
                    # 删除 t_paper_question 表中的记录
                    delete_question_query = """
                        DELETE FROM t_paper_question 
                        WHERE paper_id = %s
                    """
                    target_cursor.execute(delete_question_query, (paper_id,))
                    target_conn.commit()

                # 解析 answer_card 数据并插入到 t_paper_question 表
                for question_group in answer_card_data:
                    question_group_type = question_group['questionType']
                    for item in question_group['items']:
                        question_id = item['id']
                        question_order = item['order']
                        question_answer = item['answer']
                        question_score = item['score']
                        item_type = item['type']

                        # 根据规则确定 question_type
                        # 题目类型 1单选，2多选，3判断, 4填空, 5主观题
                        if item_type == 1:
                            if len(question_answer) == 1:
                                question_type = 1  # 单选题
                            else:
                                question_type = 2  # 多选题
                        elif item_type == 3:
                            question_type = 3  # 判断题
                        elif item_type == 4:
                            if "填空题" in question_group_type:
                                question_type = 4  # 填空题
                            else:
                                question_type = 5  # 其他题型
                        else:
                            question_type = 5  # 默认其他题型

                        # 插入 t_paper_question 表
                        insert_question_query = """
                            INSERT INTO t_paper_question (
                                paper_id, question_group, question_type, 
                                question_answer, question_score, question_sort, 
                                tenant_id, create_time
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        target_cursor.execute(insert_question_query, (
                            paper_id, question_group_type, question_type,
                            question_answer, question_score, question_order,
                            tenant_id, create_time
                        ))
                        target_conn.commit()

                return f"课程 {course_name} 的试卷记录已成功插入"

    except pymysql.Error as err:
        return f"数据库连接或查询错误: {err}"

    finally:
        # 关闭游标和连接
        if source_cursor:
            source_cursor.close()
        if source_conn:
            source_conn.close()
        if target_cursor:
            target_cursor.close()
        if target_conn:
            target_conn.close()

if __name__ == '__main__':
    # 从命令行参数获取课程名称
    if len(sys.argv) != 2:
        print("请传入课程名称")
        sys.exit(1)

    course_name = sys.argv[1]
    result = sync_exam(course_name)
    print(result)