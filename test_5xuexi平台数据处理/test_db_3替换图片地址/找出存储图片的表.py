import pymysql
from pymysql.cursors import DictCursor

# 数据库连接配置
db_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def is_image_url(value):
    """判断是否为图片URL"""
    if not value or not isinstance(value, str):
        return False
    return value.strip().startswith('http://d1.5xuexi.com')


def scan_tables_for_image_columns():
    """扫描数据库中所有表，找出存储图片URL的字段"""
    connection = pymysql.connect(**db_config)
    image_columns = []

    try:
        with connection.cursor() as cursor:
            # 1. 获取所有表名
            cursor.execute("SHOW TABLES")
            tables = [row[f"Tables_in_{db_config['database']}"] for row in cursor.fetchall()]

            print(f"共发现 {len(tables)} 张表，开始扫描...")

            # 2. 检查每张表
            for table in tables:
                # 获取表结构信息
                cursor.execute(f"DESCRIBE {table}")
                columns = [row['Field'] for row in cursor.fetchall()]

                # 3. 检查每个字段
                for column in columns:
                    # 只检查文本类型的字段
                    cursor.execute(f"""
                        SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
                    """, (db_config['database'], table, column))
                    data_type = cursor.fetchone()['DATA_TYPE']

                    if data_type.lower() in ('varchar', 'char', 'text', 'longtext', 'mediumtext', 'tinytext'):
                        # 抽样检查该字段内容
                        cursor.execute(f"""
                            SELECT `{column}` FROM `{table}` 
                            WHERE `{column}` IS NOT NULL 
                            AND `{column}` != '' 
                            LIMIT 100
                        """)
                        for row in cursor.fetchall():
                            if is_image_url(row[column]):
                                image_columns.append((table, column))
                                print(f"发现图片字段: 表 {table}.{column}")
                                break  # 找到一个就足够确认了

    except Exception as e:
        print(f"扫描过程中发生错误: {e}")
    finally:
        connection.close()

    return image_columns


def save_results(results, filename='image_columns.txt'):
    """将结果保存到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        if not results:
            f.write("未发现包含图片URL的字段\n")
        else:
            f.write("包含图片URL的字段列表:\n\n")
            for table, column in results:
                f.write(f"表名: {table}\t字段名: {column}\n")
    print(f"\n扫描结果已保存到 {filename}")


if __name__ == "__main__":
    print("开始扫描数据库中的图片字段...")
    image_fields = scan_tables_for_image_columns()

    if image_fields:
        print("\n扫描完成，发现以下包含图片URL的字段:")
        for table, column in image_fields:
            print(f"- {table}.{column}")
    else:
        print("\n未发现包含图片URL的字段")

    save_results(image_fields)