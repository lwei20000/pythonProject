import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

# 数据库连接配置
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.26.36.242',
    'database': 'system_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def connect_db():
    """连接数据库"""
    try:
        connection = pymysql.connect(**target_config)
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None


def search_course_id(course_name, cursor):
    """根据课程名搜索course_id，如果有多条匹配只取第一条"""
    try:
        # 先尝试精确匹配
        query = "SELECT course_id FROM t_course WHERE course_name = %s AND deleted = 0 LIMIT 1"
        cursor.execute(query, (course_name,))
        result = cursor.fetchone()

        if result:
            return result['course_id']

        # 如果精确匹配失败，尝试模糊匹配（只取第一条）
        query = "SELECT course_id FROM t_course WHERE course_name LIKE %s AND deleted = 0 LIMIT 1"
        cursor.execute(query, (f'%{course_name}%',))
        result = cursor.fetchone()

        return result['course_id'] if result else None

    except Exception as e:
        print(f"搜索课程ID失败: {e}")
        return None


def calculate_total_duration(course_id, cursor):
    """计算指定课程的所有课件duration总和"""
    try:
        query = """
        SELECT SUM(duration) as total_duration 
        FROM t_courseware 
        WHERE course_id = %s AND deleted = 0 AND duration IS NOT NULL
        """
        cursor.execute(query, (course_id,))
        result = cursor.fetchone()
        return result['total_duration'] if result and result['total_duration'] is not None else 0
    except Exception as e:
        print(f"计算课件时长失败: {e}")
        return 0


def format_duration(seconds):
    """将秒数格式化为时分秒"""
    if not seconds:
        return "0秒"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"


def main():
    # 读取处理后的Excel文件
    try:
        # 尝试读取Excel文件
        df = pd.read_excel('统计_处理结果.xlsx')
        print(f"成功读取Excel文件，共{len(df)}行数据")

        # 查看列名和数据
        print("Excel文件的列名:", df.columns.tolist())
        print("前5行数据:")
        print(df.head())

    except Exception as e:
        print(f"读取Excel文件失败: {e}")
        # 如果读取失败，尝试无列名方式读取
        try:
            df = pd.read_excel('统计_处理结果.xlsx', header=None)
            if len(df.columns) >= 2:
                df.columns = ['课程名', '行数']
            else:
                df.columns = ['课程名']
            print("使用无列名方式成功读取Excel文件")
            print("前5行数据:")
            print(df.head())
        except Exception as e2:
            print(f"无列名方式读取也失败: {e2}")
            return

    # 连接数据库
    connection = connect_db()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            results = []

            for index, row in df.iterrows():
                # 获取课程名（第一列）
                if '课程名' in df.columns:
                    course_name = row['课程名']
                else:
                    course_name = row.iloc[0] if len(row) > 0 else ''

                # 获取原行数（第二列，如果有）
                if '行数' in df.columns:
                    original_row_count = row['行数']
                else:
                    original_row_count = row.iloc[1] if len(row) > 1 else ''

                print(f"正在处理第{index + 1}/{len(df)}行: {course_name}")

                # 搜索course_id（只取第一条匹配记录）
                course_id = search_course_id(course_name, cursor)

                if course_id:
                    # 计算课件duration总和
                    total_duration = calculate_total_duration(course_id, cursor)
                    formatted_duration = format_duration(total_duration)

                    results.append({
                        '课程名': course_name,
                        '原行数': original_row_count,
                        'course_id': course_id,
                        '总时长(秒)': total_duration,
                        '格式化时长': formatted_duration,
                        '状态': '成功'
                    })
                    print(f"  - 找到课程ID: {course_id}, 总时长: {formatted_duration}")
                else:
                    results.append({
                        '课程名': course_name,
                        '原行数': original_row_count,
                        'course_id': None,
                        '总时长(秒)': 0,
                        '格式化时长': '0秒',
                        '状态': '未找到对应课程'
                    })
                    print(f"  - 未找到对应课程")

            # 创建结果DataFrame
            result_df = pd.DataFrame(results)

            # 保存到新的Excel文件
            output_file = '课程课件时长统计结果.xlsx'
            result_df.to_excel(output_file, index=False)
            print(f"\n处理完成！结果已保存到 {output_file}")

            # 统计结果
            success_count = len([r for r in results if r['状态'] == '成功'])
            not_found_count = len([r for r in results if r['状态'] == '未找到对应课程'])

            # 计算总时长统计
            total_duration_seconds = sum(r['总时长(秒)'] for r in results)
            total_duration_formatted = format_duration(total_duration_seconds)

            print(f"成功处理: {success_count} 条")
            print(f"未找到课程: {not_found_count} 条")
            print(f"所有课程总时长: {total_duration_formatted} ({total_duration_seconds}秒)")

            # 显示前几个成功的结果
            success_results = [r for r in results if r['状态'] == '成功']
            if success_results:
                print("\n前5个成功处理的结果:")
                for i, result in enumerate(success_results[:5]):
                    print(f"  {i + 1}. {result['课程名']} - ID:{result['course_id']} - {result['格式化时长']}")

    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection.close()


if __name__ == "__main__":
    main()