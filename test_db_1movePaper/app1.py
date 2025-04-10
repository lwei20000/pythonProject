from flask import Flask, jsonify
import pymysql
import datetime
import threading
import time

app = Flask(__name__)

# 数据库配置
db_config = {
    'user': 'root',
    'password': 'wdg@123',
    #'host': '120.55.161.50',
    'host': '120.26.36.242',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 分批处理参数
BATCH_SIZE = 1000  # 每批处理1000条记录
print_lock = threading.Lock()  # 打印锁


def get_birthday_from_id_card(id_card):
    """从身份证号码中提取生日（优化版）"""
    if not id_card or len(id_card) not in (15, 18):
        return None

    try:
        birth_date_str = id_card[6:14] if len(id_card) == 18 else '19' + id_card[6:12]
        birth_date = datetime.datetime.strptime(birth_date_str, '%Y%m%d').date()
        return birth_date.strftime('%Y-%m-%d')
    except:
        return None


def format_progress(current, total):
    """格式化进度显示"""
    percent = (current / total) * 100
    return f"[{current}/{total} {percent:.1f}%]"


def update_incorrect_birthdays():
    """优化后的批量更新函数"""
    connection = None
    try:
        connection = pymysql.connect(**db_config)
        total_updated = 0

        # 获取总记录数
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM sys_user WHERE id_card IS NOT NULL AND id_card != ''")
            total_records = cursor.fetchone()['total']
            with print_lock:
                print(f"开始处理，共 {total_records} 条记录需要检查", flush=True)

        # 分批处理
        offset = 0
        batch_number = 0
        start_time = time.time()

        while offset < total_records:
            batch_number += 1
            batch_updated = 0
            update_values = []

            try:
                # 1. 获取当前批次数据
                with connection.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT user_id, id_card, birthday 
                        FROM sys_user 
                        WHERE id_card IS NOT NULL AND id_card != ''
                        LIMIT {BATCH_SIZE} OFFSET {offset}
                    """)
                    users = cursor.fetchall()

                # 2. 准备批量更新数据
                for user in users:
                    id_card_birthday = get_birthday_from_id_card(user['id_card'])
                    if id_card_birthday and id_card_birthday != user['birthday']:
                        update_values.append((id_card_birthday, user['user_id']))

                # 3. 执行批量更新（整个批次一个事务）
                if update_values:
                    with connection.cursor() as cursor:
                        cursor.executemany("""
                            UPDATE sys_user
                            SET birthday = %s 
                            WHERE user_id = %s
                        """, update_values)
                        batch_updated = len(update_values)

                    connection.commit()
                    total_updated += batch_updated

                # 4. 打印进度（加锁确保输出完整）
                current_progress = offset + BATCH_SIZE if (offset + BATCH_SIZE) < total_records else total_records
                progress_str = format_progress(current_progress, total_records)

                with print_lock:
                    if update_values:
                        print(f"批次 {batch_number} {progress_str} 更新了 {batch_updated} 条记录", flush=True)
                    else:
                        print(f"批次 {batch_number} {progress_str} 无更新", flush=True)

                # 5. 性能优化：每10批后短暂休息
                if batch_number % 10 == 0:
                    time.sleep(0.1)  # 避免数据库过载

            except Exception as batch_error:
                connection.rollback()
                with print_lock:
                    print(f"批次 {batch_number} 处理失败: {str(batch_error)[:200]}", flush=True)
                # 失败后等待1秒再重试当前批次
                time.sleep(1)
                continue  # 继续尝试当前批次

            offset += BATCH_SIZE

        # 最终统计
        elapsed_time = time.time() - start_time
        with print_lock:
            print(f"\n处理完成！共更新 {total_updated} 条记录", flush=True)
            print(f"总耗时: {elapsed_time:.2f} 秒", flush=True)
            if total_updated > 0:
                print(f"平均速度: {total_updated / elapsed_time:.1f} 条/秒", flush=True)

        return total_updated

    except Exception as e:
        if connection:
            connection.rollback()
        with print_lock:
            print(f"\n处理中断！错误: {str(e)[:200]}", flush=True)
        return 0
    finally:
        if connection:
            connection.close()


@app.route('/update_birthdays', methods=['GET'])
def handle_update_request():
    """Web接口处理"""
    try:
        updated_count = update_incorrect_birthdays()
        return jsonify({
            'status': 'success',
            'message': f'成功更新{updated_count}条记录',
            'updated_count': updated_count
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)[:200]
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)