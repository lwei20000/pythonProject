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

# 要搜索的URL前缀列表
url_prefixes = [
    'http://vod.5xuexi.com',
    'http://testvod.5xuexi.com'
]


def scan_database_for_urls():
    try:
        # 连接数据库
        connection = pymysql.connect(**target_config)
        cursor = connection.cursor()

        # 获取所有表名
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        # 用于存储结果的字典
        results = {}

        # 遍历所有表
        for table in tables:
            table_name = table[f'Tables_in_{target_config["database"]}']
            results[table_name] = []

            # 获取表的所有列信息
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = cursor.fetchall()

            # 遍历所有列
            for column in columns:
                column_name = column['Field']
                column_type = column['Type']

                # 只检查文本类型的列
                if any(text_type in column_type.lower() for text_type in ['char', 'text', 'varchar']):
                    # 构建查询语句
                    like_conditions = " OR ".join([f"{column_name} LIKE '{prefix}%'" for prefix in url_prefixes])
                    query = f"SELECT COUNT(*) AS count FROM {table_name} WHERE {like_conditions}"

                    try:
                        cursor.execute(query)
                        result = cursor.fetchone()
                        if result['count'] > 0:
                            results[table_name].append(column_name)
                    except Exception as e:
                        print(f"查询表 {table_name} 列 {column_name} 时出错: {e}")

        # 打印结果
        print("\n扫描结果:")
        found_tables = False
        for table_name, columns in results.items():
            if columns:
                found_tables = True
                print(f"表名: {table_name}")
                print(f"包含URL前缀的字段: {', '.join(columns)}")
                print("-" * 50)

        if not found_tables:
            print("没有找到包含指定URL前缀的表")

    except Exception as e:
        print(f"数据库连接或查询出错: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    scan_database_for_urls()