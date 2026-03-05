import pymysql
from pymysql.cursors import DictCursor
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import sys

# 数据库连接配置
target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.26.36.242',
    'database': 'system_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def export_paper_answer_sheet(paper_id, output_filename=None):
    """
    导出指定试卷的答题卡到Excel文档
    """
    try:
        connection = pymysql.connect(**target_config)

        with connection.cursor() as cursor:
            # 获取试卷信息
            cursor.execute("SELECT paper_name FROM t_paper WHERE paper_id = %s AND deleted = 0", (paper_id,))
            paper_info = cursor.fetchone()

            if not paper_info:
                print(f"错误：未找到试卷ID为 {paper_id} 的试卷")
                return False

            paper_name = paper_info['paper_name']

            # 获取题目
            cursor.execute("""
                SELECT question_type, question_title, question_options, 
                       question_answer, question_analysis, question_score, question_sort
                FROM t_paper_question 
                WHERE paper_id = %s 
                ORDER BY question_sort
            """, (paper_id,))

            questions = cursor.fetchall()

            if not questions:
                print(f"错误：试卷没有题目")
                return False

            # 创建Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "答题卡"

            # 表头
            headers = ['题型标题', '题目类型', '题目名称', '题目选项', '分数', '答案', '解析']
            ws.append(headers)

            # 表头样式
            for col in range(1, 8):
                ws.cell(1, col).font = Font(bold=True)

            # 题目类型映射
            type_mapping = {
                1: ('单项选择题', '单选题'),
                2: ('多项选择题', '多选题'),
                3: ('判断是非题', '判断题'),
                4: ('填空题', '填空题'),
                5: ('问答题', '主观题')
            }

            # 添加数据
            for q in questions:
                type_title, q_type = type_mapping.get(q['question_type'], ('其他题型', '未知'))

                # 处理答案
                answer = str(q['question_answer'])
                if q['question_type'] == 3:  # 判断题
                    if answer.upper() in ['TRUE', 'T', '1', '对', '正确']:
                        answer = '对'
                    else:
                        answer = '错'

                ws.append([
                    type_title,
                    q_type,
                    q['question_title'] or '',
                    q['question_options'] or '',
                    q['question_score'],
                    answer,
                    q['question_analysis'] or ''
                ])

            # 设置列宽
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 10
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 30
            ws.column_dimensions['E'].width = 8
            ws.column_dimensions['F'].width = 20
            ws.column_dimensions['G'].width = 40

            # 生成文件名
            if not output_filename:
                import re
                clean_name = re.sub(r'[<>:"/\\|?*]', '', paper_name)
                output_filename = f"答题卡_{clean_name}_{paper_id}.xlsx"

            wb.save(output_filename)
            print(f"成功导出: {output_filename}")
            print(f"试卷: {paper_name}")
            print(f"题目数量: {len(questions)}")
            return True

    except Exception as e:
        print(f"错误: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()


# 使用示例
if __name__ == "__main__":
    if len(sys.argv) > 1:
        paper_id = int(sys.argv[1])
        filename = sys.argv[2] if len(sys.argv) > 2 else None
        export_paper_answer_sheet(paper_id, filename)
    else:
        # 默认导出试卷53207
        paper_id = 52974
        export_paper_answer_sheet(paper_id)