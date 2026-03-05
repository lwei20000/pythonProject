import pymysql
from pymysql.cursors import DictCursor
import pandas as pd
import os

# 数据库配置
db_config1 = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

db_config2 = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.26.36.242',
    'database': 'system_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def query_database(db_config):
    """查询单个数据库并返回结果"""
    connection = pymysql.connect(**db_config)
    results = []

    try:
        with connection.cursor() as cursor:
            # 1. 查询major_length=5或tenant_id=10的专业
            sql_major = """
                SELECT major_id, major_name 
                FROM t_major 
                WHERE (major_length = '5' OR tenant_id = 10) 
                AND deleted = 0
            """
            cursor.execute(sql_major)
            majors = cursor.fetchall()

            if not majors:
                print(f"数据库 {db_config['host']} 中没有找到符合条件的专业")
                return []

            major_ids = [m['major_id'] for m in majors]

            # 2. 查询这些专业对应的课程
            sql_major_course = f"""
                SELECT mc.major_id, mc.course_id, m.major_name, c.course_name
                FROM t_major_course mc
                JOIN t_major m ON mc.major_id = m.major_id
                JOIN t_course c ON mc.course_id = c.course_id
                WHERE mc.major_id IN ({','.join(map(str, major_ids))}) 
                AND mc.deleted = 0
            """
            cursor.execute(sql_major_course)
            major_courses = cursor.fetchall()

            if not major_courses:
                print(f"数据库 {db_config['host']} 中没有找到相关课程")
                return []

            course_ids = [mc['course_id'] for mc in major_courses]

            # 3. 查询这些课程的课件
            sql_courseware = f"""
                SELECT cw.courseware_id, cw.course_id, cw.courseware_name, 
                       cw.file_url, c.course_name, m.major_name
                FROM t_courseware cw
                JOIN t_course c ON cw.course_id = c.course_id
                JOIN t_major_course mc ON c.course_id = mc.course_id
                JOIN t_major m ON mc.major_id = m.major_id
                WHERE cw.course_id IN ({','.join(map(str, course_ids))})
                AND cw.deleted = 0
                AND cw.file_url IS NOT NULL
            """
            cursor.execute(sql_courseware)
            coursewares = cursor.fetchall()

            results = coursewares

    finally:
        connection.close()

    return results


def generate_report():
    """生成报告并保存到Excel"""
    print("开始查询数据库...")

    # 查询两个数据库
    print("正在查询第一个数据库...")
    data1 = query_database(db_config1)
    print(f"第一个数据库找到 {len(data1)} 条记录")

    print("正在查询第二个数据库...")
    data2 = query_database(db_config2)
    print(f"第二个数据库找到 {len(data2)} 条记录")

    # 合并结果并去重
    all_data = data1 + data2
    unique_data = []
    seen_urls = set()

    for item in all_data:
        if item['file_url'] not in seen_urls:
            seen_urls.add(item['file_url'])
            unique_data.append(item)

    print(f"合并后共有 {len(unique_data)} 条唯一记录")

    # 准备Excel数据
    excel_data = []
    for item in unique_data:
        excel_data.append([
            item['major_name'],
            item['course_name'],
            item['courseware_name'],
            item['file_url']
        ])

    # 创建DataFrame
    df = pd.DataFrame(excel_data, columns=['专业名称', '课程名称', '课件名称', '文件URL'])

    # 保存到Excel
    output_file = os.path.join(os.getcwd(), 'major_courseware_report.xlsx')
    df.to_excel(output_file, index=False)

    print(f"\n报告已生成，保存到: {output_file}")


if __name__ == "__main__":
    generate_report()