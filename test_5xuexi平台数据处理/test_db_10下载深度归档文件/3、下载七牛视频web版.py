#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_file
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import os
import requests
from qiniu import Auth, BucketManager
import threading
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from functools import lru_cache

# 数据库连接配置
db_config = {
    'user': 'root',
    'password': 'wdg@123',
    'host': '120.55.161.50',
    'database': 'db_xuexi',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

# 七牛云配置
qiniu_config = {
    'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
    'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81',
    'bucket_name': '5xuexi',
    'cdn_domain': 'vod.5xuexi.com'
}

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # 禁用JSON美化，提高性能

# 下载目录
DOWNLOAD_DIR = '/Volumes/5学习网课'

# 下载进度存储
download_progress = {}
batch_tasks = {}


class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.connection_pool = []
        self.max_pool_size = 5
        self.lock = threading.Lock()

    def get_connection(self):
        """获取数据库连接（使用连接池）"""
        with self.lock:
            if self.connection_pool:
                return self.connection_pool.pop()
            else:
                return pymysql.connect(**self.config)

    def return_connection(self, conn):
        """归还数据库连接"""
        with self.lock:
            if len(self.connection_pool) < self.max_pool_size:
                self.connection_pool.append(conn)
            else:
                conn.close()

    def get_videos(self, page=1, per_page=2000, storage_type_name=None, down_flag=None):
        """获取视频数据（分页）- 优化查询"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 构建查询条件 - 只查询需要的字段
                where_conditions = []
                params = []

                if storage_type_name and storage_type_name != 'all':
                    where_conditions.append("storage_type_name = %s")
                    params.append(storage_type_name)

                if down_flag is not None and down_flag != 'all':
                    where_conditions.append("down_flag = %s")
                    params.append(int(down_flag))

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                # 计算分页
                offset = (page - 1) * per_page

                # 优化查询：只获取必要的字段
                sql = f"""
                SELECT 
                    id, file_name, file_key, file_size, 
                    storage_type_name, formatted_put_time, 
                    down_flag, local_path, file_status
                FROM xuexi_videos 
                WHERE {where_clause}
                ORDER BY id DESC
                LIMIT %s OFFSET %s
                """
                params.extend([per_page, offset])
                cursor.execute(sql, params)
                videos = cursor.fetchall()

                # 优化计数查询
                count_sql = f"SELECT COUNT(*) as total FROM xuexi_videos WHERE {where_clause}"
                cursor.execute(count_sql, params[:-2])
                total = cursor.fetchone()['total']

                return videos, total
        except Exception as e:
            print(f"数据库查询错误: {e}")
            return [], 0
        finally:
            self.return_connection(conn)

    def update_download_status(self, file_id, success=True, local_path=''):
        """更新下载状态"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                if success:
                    sql = """
                    UPDATE xuexi_videos 
                    SET down_flag = 1, download_time = %s, local_path = %s, 
                        file_status = 'completed', error_message = NULL, 
                        retry_count = 0, updated_at = NOW()
                    WHERE id = %s
                    """
                    cursor.execute(sql, (datetime.now(), local_path, file_id))
                else:
                    sql = """
                    UPDATE xuexi_videos 
                    SET file_status = 'failed', retry_count = IFNULL(retry_count, 0) + 1,
                        last_retry_time = %s, updated_at = NOW()
                    WHERE id = %s
                    """
                    cursor.execute(sql, (datetime.now(), file_id))
                conn.commit()
        except Exception as e:
            print(f"更新数据库失败: {e}")
            if conn:
                conn.rollback()
        finally:
            self.return_connection(conn)

    def get_video_by_id(self, video_id):
        """根据ID获取视频信息"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT id, file_name, file_key, file_size, storage_type_name, 
                       down_flag, local_path
                FROM xuexi_videos 
                WHERE id = %s
                """
                cursor.execute(sql, (video_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"查询视频信息失败: {e}")
            return None
        finally:
            self.return_connection(conn)

    def close_all_connections(self):
        """关闭所有数据库连接"""
        with self.lock:
            for conn in self.connection_pool:
                try:
                    conn.close()
                except:
                    pass
            self.connection_pool.clear()


class QiniuDownloader:
    def __init__(self, qiniu_config, download_dir):
        self.auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])
        self.bucket_name = qiniu_config['bucket_name']
        self.cdn_domain = qiniu_config['cdn_domain']
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)

        # 创建带连接池的会话
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)



    def get_download_url(self, file_key):
        """获取下载URL"""
        base_url = f"http://{self.cdn_domain}/{file_key}"
        return self.auth.private_download_url(base_url, expires=3600)

    def delete_qiniu_file(self, file_key):
        """删除七牛云文件"""
        try:
            bucket_manager = BucketManager(self.auth)
            ret, info = bucket_manager.delete(self.bucket_name, file_key)
            return info.status_code == 200
        except Exception as e:
            print(f"删除七牛云文件失败: {e}")
            return False

    def download_file_with_progress(self, file_record, delete_after_download=False, progress_callback=None):
        """下载单个文件（带进度回调和重试机制）"""
        max_retries = 3
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # 现有的下载逻辑
                file_name = file_record['file_name']
                file_key = file_record['file_key']
                file_size = file_record.get('file_size', 0)

                # 本地文件路径
                local_path = os.path.join(self.download_dir, file_name)

                # 检查文件是否已存在
                if os.path.exists(local_path):
                    try:
                        actual_size = os.path.getsize(local_path)
                        if actual_size == file_size:
                            if progress_callback:
                                progress_callback(100, file_size, file_size, "文件已存在")
                            return True, local_path, "文件已存在"
                    except OSError as e:
                        print(f"检查文件大小失败: {e}")

                # 获取下载URL
                download_url = self.get_download_url(file_key)

                # 下载文件 - 增加连接和读取超时时间
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                #response = requests.get(download_url, stream=True, headers=headers, timeout=(60, 600))  # 增加超时时间
                # 替换原来的 requests.get 调用
                response = self.session.get(download_url, stream=True, headers=headers, timeout=(60, 600))

                response.raise_for_status()

                # 获取文件总大小
                total_size = int(response.headers.get('content-length', file_size))
                if total_size == 0:
                    total_size = file_size

                # 创建目录（如果文件在子目录中）
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                downloaded_size = 0
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            # 计算进度并回调
                            if progress_callback and total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                if progress_callback and (progress % 1 == 0 or downloaded_size % (1024 * 1024) == 0):
                                    progress_callback(progress, downloaded_size, total_size, "下载中")

                # 验证文件大小
                actual_size = os.path.getsize(local_path)
                if total_size > 0 and actual_size != total_size:
                    try:
                        os.remove(local_path)
                    except:
                        pass
                    if progress_callback:
                        progress_callback(0, 0, total_size, "文件大小不匹配")
                    raise Exception(f"文件大小不匹配: {actual_size} != {total_size}")

                # 确保进度显示100%
                if progress_callback and total_size > 0:
                    progress_callback(100, total_size, total_size, "下载完成")

                # 删除七牛云文件
                if delete_after_download:
                    if self.delete_qiniu_file(file_key):
                        if progress_callback:
                            progress_callback(100, total_size, total_size, "下载完成并已删除源文件")
                    else:
                        if progress_callback:
                            progress_callback(100, total_size, total_size, "下载完成但删除源文件失败")

                return True, local_path, "下载成功"

            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"下载失败，正在进行第 {retry_count} 次重试: {e}")
                    time.sleep(2 ** retry_count)  # 指数退避
                    continue
                else:
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                        except:
                            pass
                    error_msg = str(e)
                    if progress_callback:
                        progress_callback(0, 0, file_size, f"下载失败: {error_msg}")
                    return False, None, error_msg
            except requests.exceptions.ConnectionError as e:
                error_msg = f"连接错误: {str(e)}"
                print(f"下载 {file_name} 时发生连接错误: {e}")
                # 重试逻辑
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(2 ** retry_count)
                    continue
                else:
                    if progress_callback:
                        progress_callback(0, 0, file_size, error_msg)
                    return False, None, error_msg

            except requests.exceptions.Timeout as e:
                error_msg = f"下载超时: {str(e)}"
                print(f"下载 {file_name} 时超时: {e}")
                # 重试逻辑
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(2 ** retry_count)
                    continue
                else:
                    if progress_callback:
                        progress_callback(0, 0, file_size, error_msg)
                    return False, None, error_msg


# 初始化管理器
db_manager = DatabaseManager(db_config)
downloader = QiniuDownloader(qiniu_config, DOWNLOAD_DIR)


@app.route('/')
def index():
    """主页 - 显示视频列表（优化性能）"""
    # 获取参数
    page = request.args.get('page', 1, type=int)
    storage_type_name = request.args.get('storage_type_name', 'all')
    down_flag = request.args.get('down_flag', 'all')

    # 限制页码范围
    page = max(1, min(page, 100))  # 最大100页

    # 获取数据
    start_time = time.time()
    videos, total = db_manager.get_videos(
        page=page,
        per_page=2000,
        storage_type_name=storage_type_name,
        down_flag=down_flag
    )

    # 为每个视频添加进度信息
    for video in videos:
        video_id = video['id']
        if video_id in download_progress:
            video['progress'] = download_progress[video_id]
        else:
            video['progress'] = None

    total_pages = max(1, (total + 1999) // 2000)  # 计算总页数

    # 计算加载时间
    load_time = time.time() - start_time
    print(f"页面加载时间: {load_time:.2f}秒")

    return render_template('index.html',
                           videos=videos,
                           page=page,
                           total_pages=total_pages,
                           total=total,
                           storage_type_name=storage_type_name,
                           down_flag=down_flag,
                           load_time=load_time)


@app.route('/download/<int:video_id>', methods=['POST'])
def download_video(video_id):
    """下载单个视频文件"""
    # 获取视频信息
    video = db_manager.get_video_by_id(video_id)
    if not video:
        return jsonify({'success': False, 'message': '视频不存在'})

    # 检查是否已下载
    if video['down_flag'] == 1 and video['local_path'] and os.path.exists(video['local_path']):
        return jsonify({'success': True, 'message': '文件已存在', 'file_path': video['local_path']})

    # 检查存储类型
    requires_confirmation = video['storage_type_name'] != '标准存储'
    delete_after_download = False

    # 如果是非标准存储，需要确认
    if requires_confirmation:
        confirm = request.json.get('confirm', False) if request.is_json else False
        if not confirm:
            return jsonify({
                'success': False,
                'requires_confirmation': True,
                'message': f'该文件存储类型为"{video["storage_type_name"]}"，下载后将删除七牛云文件，确认继续？'
            })
        delete_after_download = True

    # 创建进度跟踪
    download_progress[video_id] = {
        'percent': 0,
        'downloaded': 0,
        'total': video.get('file_size', 0),
        'status': 'pending',
        'message': '等待开始'
    }

    # 进度回调函数
    def progress_callback(percent, downloaded, total, message):
        download_progress[video_id] = {
            'percent': percent,
            'downloaded': downloaded,
            'total': total,
            'status': 'downloading',
            'message': message
        }

    # 在后台执行下载
    def download_in_background():
        try:
            success, local_path, message = downloader.download_file_with_progress(
                video,
                delete_after_download,
                progress_callback
            )

            if success:
                db_manager.update_download_status(video_id, True, local_path)
                download_progress[video_id]['status'] = 'completed'
                download_progress[video_id]['message'] = '下载完成'
            else:
                db_manager.update_download_status(video_id, False)
                download_progress[video_id]['status'] = 'failed'
                download_progress[video_id]['message'] = message

        except Exception as e:
            db_manager.update_download_status(video_id, False)
            download_progress[video_id]['status'] = 'failed'
            download_progress[video_id]['message'] = str(e)

        # 下载完成后，5分钟后清理进度信息
        def cleanup_progress():
            time.sleep(300)  # 5分钟
            if video_id in download_progress:
                del download_progress[video_id]

        threading.Thread(target=cleanup_progress, daemon=True).start()

    # 启动下载线程
    thread = threading.Thread(target=download_in_background)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': '下载任务已开始',
        'download_id': video_id
    })


@app.route('/batch_download', methods=['POST'])
def batch_download():
    """批量下载当前页所有文件"""
    page = request.json.get('page', 1)
    storage_type_name = request.json.get('storage_type_name', 'all')
    down_flag = request.json.get('down_flag', 'all')
    max_workers = min(request.json.get('max_workers', 5), 10)  # 限制最大线程数

    # 获取当前页的所有视频
    videos, total = db_manager.get_videos(
        page=page,
        per_page=2000,
        storage_type_name=storage_type_name,
        down_flag=down_flag
    )

    # 过滤未下载的视频
    undownloaded_videos = [v for v in videos if v['down_flag'] != 1 or not v.get('local_path') or not os.path.exists(
        v.get('local_path', ''))]

    if not undownloaded_videos:
        return jsonify({'success': False, 'message': '当前页没有需要下载的文件'})

    # 创建批量下载任务
    task_id = str(uuid.uuid4())
    batch_tasks[task_id] = {
        'total': len(undownloaded_videos),
        'completed': 0,
        'success': 0,
        'failed': 0,
        'status': 'running',
        'files': {}
    }

    # 初始化每个文件的进度
    for video in undownloaded_videos:
        video_id = video['id']
        batch_tasks[task_id]['files'][video_id] = {
            'percent': 0,
            'downloaded': 0,
            'total': video.get('file_size', 0),
            'status': 'pending',
            'message': '等待开始'
        }
        download_progress[video_id] = batch_tasks[task_id]['files'][video_id]

    # 在后台执行批量下载
    def batch_download_in_background():
        def download_single(video):
            video_id = video['id']

            # 进度回调函数
            def progress_callback(percent, downloaded, total, message):
                batch_tasks[task_id]['files'][video_id] = {
                    'percent': percent,
                    'downloaded': downloaded,
                    'total': total,
                    'status': 'downloading',
                    'message': message
                }
                download_progress[video_id] = batch_tasks[task_id]['files'][video_id]

            try:
                # 检查存储类型决定是否删除源文件
                delete_after_download = video['storage_type_name'] != '标准存储'

                success, local_path, message = downloader.download_file_with_progress(
                    video,
                    delete_after_download,
                    progress_callback
                )

                if success:
                    db_manager.update_download_status(video_id, True, local_path)
                    batch_tasks[task_id]['files'][video_id]['status'] = 'completed'
                    batch_tasks[task_id]['files'][video_id]['message'] = '下载完成'
                    return True, video_id
                else:
                    db_manager.update_download_status(video_id, False)
                    batch_tasks[task_id]['files'][video_id]['status'] = 'failed'
                    batch_tasks[task_id]['files'][video_id]['message'] = message
                    return False, video_id

            except Exception as e:
                db_manager.update_download_status(video_id, False)
                batch_tasks[task_id]['files'][video_id]['status'] = 'failed'
                batch_tasks[task_id]['files'][video_id]['message'] = str(e)
                return False, video_id

        # 使用线程池进行多线程下载
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            future_to_video = {
                executor.submit(download_single, video): video['id']
                for video in undownloaded_videos
            }

            # 处理完成的任务
            for future in as_completed(future_to_video):
                video_id = future_to_video[future]
                try:
                    success, vid = future.result()
                    if success:
                        batch_tasks[task_id]['success'] += 1
                    else:
                        batch_tasks[task_id]['failed'] += 1
                    batch_tasks[task_id]['completed'] += 1
                except Exception as e:
                    batch_tasks[task_id]['failed'] += 1
                    batch_tasks[task_id]['completed'] += 1
                    print(f"文件 {video_id} 下载异常: {e}")

        batch_tasks[task_id]['status'] = 'completed'

        # 任务完成后清理
        def cleanup_task():
            time.sleep(300)  # 5分钟后清理
            if task_id in batch_tasks:
                del batch_tasks[task_id]

        threading.Thread(target=cleanup_task, daemon=True).start()

    # 启动批量下载线程
    thread = threading.Thread(target=batch_download_in_background)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': f'批量下载任务已开始，共{len(undownloaded_videos)}个文件',
        'total_files': len(undownloaded_videos)
    })


@app.route('/progress/<int:video_id>')
def get_progress(video_id):
    """获取单个文件下载进度"""
    progress = download_progress.get(video_id, {})
    return jsonify(progress)


@app.route('/batch_progress/<task_id>')
def get_batch_progress(task_id):
    """获取批量下载任务进度"""
    task = batch_tasks.get(task_id, {})
    return jsonify(task)


@app.route('/view_file')
def view_file():
    """查看文件"""
    file_path = request.args.get('path')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=False)
    return "文件不存在", 404


@app.template_filter('format_size')
def format_size(size_bytes):
    """格式化文件大小过滤器"""
    if not size_bytes:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


@app.template_filter('truncate_path')
def truncate_path(path, length=50):
    """截断路径显示"""
    if not path:
        return ""
    if len(path) <= length:
        return path
    return path[:length // 2] + "..." + path[-(length // 2):]


if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs('templates', exist_ok=True)

    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5003, threaded=True)