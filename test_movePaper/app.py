from flask import Flask, request, jsonify, Response
import subprocess
import json

app = Flask(__name__)

@app.route('/sync_exam', methods=['GET', 'POST'])
def sync_exam():
    if request.method == 'POST':
        data = request.json
        course_name = data.get('course_name')
    elif request.method == 'GET':
        course_name = request.args.get('course_name')

    if not course_name:
        return jsonify({"error": "课程名称不能为空"}), 400

    try:
        result = subprocess.run(
            ['python3.7', 'sync_exam.py', course_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            response_data = {
                "message": "同步成功",
                "output": result.stdout
            }
            return Response(
                json.dumps(response_data, ensure_ascii=False),
                content_type='application/json; charset=utf-8'
            )
        else:
            response_data = {
                "error": "同步失败",
                "details": result.stderr
            }
            return Response(
                json.dumps(response_data, ensure_ascii=False),
                content_type='application/json; charset=utf-8',
                status=500
            )

    except Exception as e:
        response_data = {
            "error": str(e)
        }
        return Response(
            json.dumps(response_data, ensure_ascii=False),
            content_type='application/json; charset=utf-8',
            status=500
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)  # 绑定到所有网络接口