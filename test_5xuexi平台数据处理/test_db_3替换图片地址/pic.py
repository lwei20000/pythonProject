import pymysql
from pymysql.cursors import DictCursor
from qiniu import Auth, put_file, etag
import requests
import os
import uuid
from urllib.parse import urlparse

# 数据库连接配置
# target_config = {
#     'user': 'root',
#     'password': 'wdg@123',
#     'host': '120.55.161.50',
#     'database': 'db_xuexi',
#     'charset': 'utf8mb4',
#     'cursorclass': DictCursor
# }

target_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.26.36.242',
    'database': 'system_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

# 七牛云配置 (请填写您的七牛云配置)
qiniu_config = {
    'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
    'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81',
    'bucket_name': '5xuexi-new-vod',
    'domain': 'http://5xuexi-new-vod.5xuexi.com'  # 例如: 'http://xxx.clouddn.com'
}

def download_image(image_url, local_path):
    """下载图片到本地临时文件"""
    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            print(f"下载失败，HTTP状态码: {response.status_code}")
    except Exception as e:
        print(f"下载图片失败: {str(e)}")
    return False


def upload_to_qiniu(local_path, key):
    """上传文件到七牛云"""
    try:
        q = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])
        token = q.upload_token(qiniu_config['bucket_name'], key, 3600)

        ret, info = put_file(token, key, local_path)
        if info.status_code == 200:
            print(f"上传成功: {key}")
            return True
        else:
            print(f"上传失败: {info}")
            return False
    except Exception as e:
        print(f"上传到七牛云出错: {str(e)}")
        return False


def generate_new_url(key):
    """生成七牛云访问URL"""
    return f"{qiniu_config['domain'].rstrip('/')}/{key}"


def process_course_images():
    # 连接数据库
    connection = pymysql.connect(**target_config)

    try:
        with connection.cursor() as cursor:
            # 1. 查询所有需要处理的记录
            sql = """
            SELECT course_id, course_picture 
            FROM t_course 
            WHERE course_picture IS NOT NULL 
            AND course_picture != ''
            """
            cursor.execute(sql)
            courses = cursor.fetchall()

            total = len(courses)
            print(f"共找到 {total} 条需要处理的记录")

            # 2. 处理每条记录
            for i, course in enumerate(courses, 1):
                course_id = course['course_id']
                old_url = course['course_picture'].strip()

                print(f"\n处理第 {i}/{total} 条记录 - ID: {course_id}")
                print(f"原始URL: {old_url}")

                # 跳过无效URL
                if not old_url.startswith(('http://', 'https://')):
                    print(f"无效的URL格式，跳过: {old_url}")
                    continue

                # 解析原URL获取文件名
                try:
                    parsed = urlparse(old_url)
                    filename = os.path.basename(parsed.path)
                    if not filename:
                        filename = f"{uuid.uuid4().hex}.jpg"
                    else:
                        # 保留原始文件扩展名
                        _, ext = os.path.splitext(filename)
                        if not ext:
                            filename += '.jpg'
                except:
                    filename = f"{uuid.uuid4().hex}.jpg"

                # 临时文件路径
                temp_dir = os.path.join(os.getcwd(), 'temp_images')
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = os.path.join(temp_dir, filename)

                # 下载图片
                if download_image(old_url, temp_file):
                    # 上传到七牛云
                    if upload_to_qiniu(temp_file, filename):
                        # 生成新的URL
                        new_url = generate_new_url(filename)

                        # 更新数据库
                        update_sql = """
                        UPDATE t_course 
                        SET course_picture = %s 
                        WHERE course_id = %s
                        """
                        cursor.execute(update_sql, (new_url, course_id))
                        connection.commit()
                        print(f"更新成功! 新URL: {new_url}")
                    else:
                        print("上传到七牛云失败，跳过此记录")
                else:
                    print("下载图片失败，跳过此记录")

                # 删除临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        connection.rollback()
    finally:
        connection.close()
        print("\n所有处理完成!")
        # 清理临时目录
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass


if __name__ == "__main__":
    # 检查七牛云配置是否填写
    if not all(qiniu_config.values()) or '您的' in qiniu_config['access_key']:
        print("请先填写七牛云配置参数!")
        print("需要配置的参数：access_key, secret_key, bucket_name, domain")
    else:
        process_course_images()