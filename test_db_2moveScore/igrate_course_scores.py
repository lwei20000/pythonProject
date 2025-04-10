from flask import Flask, request, jsonify, render_template
import pymysql
from pymysql.cursors import DictCursor
import json

app = Flask(__name__)

# 数据库连接配置（源数据库）
source_config = {
    'user': 'root',
    'password': 'Yjydev001',
    'host': 'rm-uf61035g89k83p76nlo.mysql.rds.aliyuncs.com',
    'database': 'db_usr',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

# 数据库连接配置（目标数据库）
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def get_source_connection():
    return pymysql.connect(**source_config)


def get_target_connection():
    return pymysql.connect(**target_config)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/migrate_course_scores', methods=['POST'])
def migrate_course_scores():
    def update_progress(stage, count, log):
        # 实时发送进度更新
        progress_data = {
            "stage": stage,
            "count": count,
            "log": log
        }
        print(json.dumps(progress_data))  # 在实际应用中可以通过SSE或WebSocket发送

    log_messages = []
    response_data = {
        "status": "success",
        "message": "",
        "logs": [],
        "rows_fetched": 0,
        "rows_inserted": 0,
        "rows_updated": 0
    }

    try:
        # 1. 从源数据库查询数据
        source_conn = get_source_connection()
        target_conn = get_target_connection()

        with source_conn.cursor() as source_cursor:
            sql = """
            select s.id,s.learn_behavior_score as 'learing_progress',
                   s.learn_behavior_score as 'learing_score',
                   if(s.total_score = 0,NULL,if(s.final_score>100,100,s.final_score)) as 'exam_score',
                   if(s.total_score=0,null,if(s.total_score>100,100,s.total_score)) as 'total_score'
            from db_usr.course_schedule s 
            left join enroll_plan ep on ep.id = s.enrollment_id and ep.is_deleted =0
            where s.college_id in(239) and s.course_schedule_type =0 
                  and s.is_deleted =0 and ep.the_year in(2019,2020,2021,2022,2023)
            """
            source_cursor.execute(sql)
            results = source_cursor.fetchall()

            fetched_rows = len(results)
            log_message = f"从源表中取得了 {fetched_rows} 条数据"
            log_messages.append(log_message)
            response_data["rows_fetched"] = fetched_rows
            update_progress("fetch", fetched_rows, log_message)

            if not results:
                log_message = "没有需要迁移的数据"
                log_messages.append(log_message)
                response_data.update({
                    "message": "No data to migrate",
                    "logs": log_messages
                })
                return jsonify(response_data)

            # 2. 将数据插入到目标数据库的临时表
            with target_conn.cursor() as target_cursor:
                # 先清空临时表
                target_cursor.execute("TRUNCATE TABLE t_user_course_1")
                log_message = "已清空临时表 t_user_course_1"
                log_messages.append(log_message)
                update_progress("clear", 0, log_message)

                # 准备插入语句
                insert_sql = """
                INSERT INTO t_user_course_1 
                (id, learing_progress, learing_score, exam_score, total_score)
                VALUES (%(id)s, %(learing_progress)s, %(learing_score)s, %(exam_score)s, %(total_score)s)
                """

                # 批量插入数据
                target_cursor.executemany(insert_sql, results)
                inserted_rows = target_cursor.rowcount
                log_message = f"成功插入 {inserted_rows} 条数据到临时表"
                log_messages.append(log_message)
                response_data["rows_inserted"] = inserted_rows
                update_progress("insert", inserted_rows, log_message)

                # 3. 更新目标表数据
                update_sql = """
                UPDATE t_user_course_1 m, t_user_course t SET 
                t.learing_progress = IF(m.learing_progress > t.learing_progress, m.learing_progress, t.learing_progress),
                t.learing_score = IF(m.learing_score > t.learing_score, m.learing_score, t.learing_score),
                t.exam_score = IF(t.exam_score IS NULL OR m.exam_score > t.exam_score, m.exam_score, t.exam_score),
                t.total_score = IF(t.total_score IS NULL OR m.total_score > t.total_score, m.total_score, t.total_score)
                WHERE m.id = t.id
                """
                target_cursor.execute(update_sql)
                updated_rows = target_cursor.rowcount
                log_message = f"成功更新了目标表中的 {updated_rows} 条记录"
                log_messages.append(log_message)
                response_data["rows_updated"] = updated_rows
                update_progress("update", updated_rows, log_message)

                target_conn.commit()
                log_message = "事务已提交"
                log_messages.append(log_message)
                update_progress("complete", 0, log_message)

                response_data.update({
                    "message": "数据迁移完成",
                    "logs": log_messages
                })
                return jsonify(response_data)

    except Exception as e:
        # 回滚事务
        if 'target_conn' in locals():
            target_conn.rollback()
            log_message = "发生错误，已回滚事务"
            log_messages.append(log_message)
            update_progress("error", 0, log_message)
        log_message = f"错误信息: {str(e)}"
        log_messages.append(log_message)
        update_progress("error", 0, log_message)
        response_data.update({
            "status": "error",
            "message": str(e),
            "logs": log_messages
        })
        return jsonify(response_data), 500

    finally:
        # 关闭连接
        if 'source_conn' in locals():
            source_conn.close()
        if 'target_conn' in locals():
            target_conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8091, debug=True)