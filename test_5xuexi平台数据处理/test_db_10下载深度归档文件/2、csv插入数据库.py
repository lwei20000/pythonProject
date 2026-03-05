import csv
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

# CSV文件路径
csv_file_path = '5xuexi_videos.csv'


def create_table(cursor):
    """创建视频信息表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS xuexi_videos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        file_name VARCHAR(500) NOT NULL,
        file_key VARCHAR(500) NOT NULL,
        file_size BIGINT,
        formatted_size VARCHAR(50),
        storage_type TINYINT,
        storage_type_name VARCHAR(50),
        put_time BIGINT,
        formatted_put_time DATETIME,
        mime_type VARCHAR(100),
        md5 VARCHAR(32),
        scan_time DATETIME,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_file_name (file_name(100)),
        INDEX idx_storage_type (storage_type),
        INDEX idx_put_time (formatted_put_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    cursor.execute(create_table_sql)
    print("表创建成功或已存在")


def parse_csv_value(value):
    """处理CSV中的空值和特殊字符"""
    if value is None or value == '':
        return None
    # 去除可能的空格和特殊字符
    return str(value).strip()


def parse_datetime(datetime_str):
    """解析日期时间字符串"""
    if not datetime_str:
        return None
    try:
        # 处理可能的日期时间格式
        from datetime import datetime
        # 尝试多种格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        return None
    except:
        return None


def insert_data_from_csv(cursor, connection, csv_file_path):
    """从CSV文件插入数据，每100条提交一次事务"""
    inserted_count = 0
    skipped_count = 0
    batch_size = 100

    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
            # 跳过可能的BOM字符
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    # 解析数据
                    file_name = parse_csv_value(row.get('file_name', ''))
                    file_key = parse_csv_value(row.get('key', ''))

                    # 跳过空文件名
                    if not file_name or not file_key:
                        skipped_count += 1
                        continue

                    # 处理文件大小
                    file_size_str = parse_csv_value(row.get('file_size', ''))
                    file_size = int(file_size_str) if file_size_str and file_size_str.isdigit() else None

                    formatted_size = parse_csv_value(row.get('formatted_size', ''))

                    # 处理存储类型
                    storage_type_str = parse_csv_value(row.get('storage_type', ''))
                    storage_type = int(storage_type_str) if storage_type_str and storage_type_str.isdigit() else None

                    storage_type_name = parse_csv_value(row.get('storage_type_name', ''))

                    # 处理时间戳
                    put_time_str = parse_csv_value(row.get('put_time', ''))
                    put_time = int(put_time_str) if put_time_str and put_time_str.isdigit() else None

                    formatted_put_time_str = parse_csv_value(row.get('formatted_put_time', ''))
                    formatted_put_time = parse_datetime(formatted_put_time_str)

                    mime_type = parse_csv_value(row.get('mime_type', ''))
                    md5 = parse_csv_value(row.get('md5', ''))

                    scan_time_str = parse_csv_value(row.get('scan_time', ''))
                    scan_time = parse_datetime(scan_time_str)

                    # 插入SQL
                    insert_sql = """
                    INSERT INTO xuexi_videos 
                    (file_name, file_key, file_size, formatted_size, storage_type, 
                     storage_type_name, put_time, formatted_put_time, mime_type, md5, scan_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    cursor.execute(insert_sql, (
                        file_name, file_key, file_size, formatted_size, storage_type,
                        storage_type_name, put_time, formatted_put_time, mime_type, md5, scan_time
                    ))

                    inserted_count += 1

                    # 每插入100条提交一次事务
                    if inserted_count % batch_size == 0:
                        connection.commit()
                        print(f"已插入并提交 {inserted_count} 条记录...")

                except Exception as e:
                    print(f"插入记录时出错: {row.get('file_name', 'Unknown')}, 错误: {str(e)}")
                    skipped_count += 1
                    continue

            # 提交最后一批不足100条的记录
            if inserted_count % batch_size != 0:
                connection.commit()
                print(f"提交最后一批 {inserted_count % batch_size} 条记录")

        return inserted_count, skipped_count

    except FileNotFoundError:
        print(f"CSV文件未找到: {csv_file_path}")
        return 0, 0
    except Exception as e:
        print(f"读取CSV文件时出错: {str(e)}")
        # 出错时回滚未提交的事务
        connection.rollback()
        return 0, 0


def main():
    connection = None
    try:
        # 连接数据库
        connection = pymysql.connect(**target_config)
        cursor = connection.cursor()

        print("数据库连接成功")

        # 创建表
        create_table(cursor)

        # 插入数据
        print("开始插入数据...")
        inserted_count, skipped_count = insert_data_from_csv(cursor, connection, csv_file_path)

        print(f"数据插入完成！")
        print(f"成功插入: {inserted_count} 条记录")
        print(f"跳过记录: {skipped_count} 条")

        # 查询总记录数
        cursor.execute("SELECT COUNT(*) as total FROM xuexi_videos")
        total_count = cursor.fetchone()['total']
        print(f"表中总记录数: {total_count} 条")

    except Exception as e:
        print(f"操作失败: {str(e)}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("数据库连接已关闭")


if __name__ == "__main__":
    main()