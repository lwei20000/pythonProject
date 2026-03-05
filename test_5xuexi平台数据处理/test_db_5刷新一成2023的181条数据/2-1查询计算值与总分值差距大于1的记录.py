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


def find_inconsistent_scores():
    try:
        # 建立数据库连接
        connection = pymysql.connect(**target_config)

        with connection.cursor() as cursor:
            # 查询所有符合条件的记录
            sql = """
            SELECT 
                id, 
                user_id, 
                course_id, 
                learing_score, 
                exam_score, 
                total_score,
                FLOOR((learing_score * 0.5 + exam_score * 0.5)) AS calculated_score,
                ABS(FLOOR((learing_score * 0.5 + exam_score * 0.5)) - total_score) AS score_diff
            FROM t_user_course
            WHERE deleted = 0
              AND total_score IS NOT NULL
              AND learing_score IS NOT NULL
              AND exam_score IS NOT NULL
            """

            cursor.execute(sql)
            all_results = cursor.fetchall()

            # 筛选出差值绝对值大于1的记录
            results = [row for row in all_results if abs(row['calculated_score'] - row['total_score']) > 1]

            if not results:
                print("没有找到计算值与总分相差大于1的记录")
                return

            # 获取字段名（排除score_diff字段）
            columns = [desc[0] for desc in cursor.description if desc[0] != 'score_diff']

            # 计算每列的最大宽度
            col_widths = []
            for col in columns:
                max_len = len(col)
                for row in results:
                    val_len = len(str(row[col])) if row[col] is not None else 4
                    if val_len > max_len:
                        max_len = val_len
                col_widths.append(max_len + 2)  # 加2作为间距

            # 打印表头
            header = "|".join(f" {col.ljust(col_widths[i] - 1)}" for i, col in enumerate(columns))
            separator = "-" * len(header)

            print(f"找到 {len(results)} 条计算值与总分相差大于1的记录:")
            print(separator)
            print(header)
            print(separator)

            # 打印数据行
            for row in results:
                row_str = "|".join(
                    f" {str(row[col]).ljust(col_widths[i] - 1) if row[col] is not None else 'NULL'.ljust(col_widths[i] - 1)}"
                    for i, col in enumerate(columns)
                )
                print(row_str)

            print(separator)

            # 打印统计信息
            max_diff = max(abs(row['calculated_score'] - row['total_score']) for row in results)
            print(f"最大差值: {max_diff}分")

    except pymysql.Error as e:
        print(f"数据库错误: {e}")
    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    find_inconsistent_scores()