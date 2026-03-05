#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import threading
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from qiniu import Auth
import requests
from tqdm import tqdm
import signal
import sys

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


class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.connection_pool = []
        self.lock = threading.Lock()
        self.max_connections = 20

    def get_connection(self):
        """获取数据库连接"""
        with self.lock:
            if self.connection_pool:
                return self.connection_pool.pop()
            else:
                return pymysql.connect(**self.config)

    def return_connection(self, conn):
        """归还数据库连接"""
        with self.lock:
            if len(self.connection_pool) < self.max_connections:
                self.connection_pool.append(conn)
            else:
                conn.close()

    def get_undownloaded_files(self, storage_type_name):
        """获取未下载的文件记录"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT id, file_name, file_key, file_size, formatted_size, 
                       storage_type, storage_type_name, mime_type, md5
                FROM xuexi_videos 
                WHERE storage_type_name = %s 
                  AND (down_flag IS NULL OR down_flag = 0)
                  AND (file_status IN ('pending', 'failed') OR file_status IS NULL)
                ORDER BY file_size DESC
                """
                cursor.execute(sql, (storage_type_name,))
                return cursor.fetchall()
        except Exception as e:
            print(f"数据库查询失败: {e}")
            return []
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
            conn.rollback()
        finally:
            self.return_connection(conn)

    def set_downloading_status(self, file_id):
        """设置文件状态为下载中"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "UPDATE xuexi_videos SET file_status = 'downloading' WHERE id = %s"
                cursor.execute(sql, (file_id,))
                conn.commit()
        except Exception as e:
            print(f"设置下载状态失败: {e}")
            conn.rollback()
        finally:
            self.return_connection(conn)

    def close_all_connections(self):
        """关闭所有数据库连接"""
        with self.lock:
            for conn in self.connection_pool:
                conn.close()
            self.connection_pool.clear()


class QiniuDownloader:
    def __init__(self, qiniu_config, download_dir='/Volumes/5学习网课'):
        self.auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])
        self.bucket_name = qiniu_config['bucket_name']
        self.cdn_domain = qiniu_config['cdn_domain']
        self.download_dir = download_dir

        # 创建下载目录
        os.makedirs(download_dir, exist_ok=True)

        # 统计信息
        self.stats = {
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'total_size': 0
        }
        self.stats_lock = threading.Lock()
        self.is_interrupted = False

        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """处理中断信号"""
        print("\n正在停止下载...")
        self.is_interrupted = True

    def get_download_url(self, file_key):
        """获取下载URL"""
        base_url = f"http://{self.cdn_domain}/{file_key}"
        return self.auth.private_download_url(base_url, expires=3600)

    def delete_qiniu_file(self, file_key):
        """删除七牛云文件"""
        from qiniu import BucketManager
        try:
            bucket_manager = BucketManager(self.auth)
            ret, info = bucket_manager.delete(self.bucket_name, file_key)
            return info.status_code == 200
        except Exception:
            return False

    def check_local_file(self, file_name, expected_size):
        """检查本地文件是否存在且完整"""
        local_path = os.path.join(self.download_dir, file_name)
        if os.path.exists(local_path):
            actual_size = os.path.getsize(local_path)
            if actual_size == expected_size:
                return True, local_path
        return False, local_path

    def download_file(self, file_record, db_manager, delete_after_download=False):
        """下载单个文件"""
        if self.is_interrupted:
            return False, "下载被中断"

        file_id = file_record['id']
        file_name = file_record['file_name']
        file_key = file_record['file_key']
        file_size = file_record.get('file_size', 0)

        # 检查文件是否已存在
        file_exists, local_path = self.check_local_file(file_name, file_size)
        if file_exists:
            db_manager.update_download_status(file_id, True, local_path)
            with self.stats_lock:
                self.stats['skipped'] += 1
                self.stats['total_size'] += file_size
            return True, "文件已存在"

        # 设置下载中状态
        db_manager.set_downloading_status(file_id)

        # 创建进度条
        pbar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=file_name[:40].ljust(40),
            leave=False
        )

        try:
            # 获取下载URL
            download_url = self.get_download_url(file_key)

            # 下载文件
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(download_url, stream=True, headers=headers, timeout=(30, 300))
            response.raise_for_status()

            downloaded_size = 0
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.is_interrupted:
                        raise KeyboardInterrupt()

                    if chunk:
                        f.write(chunk)
                        chunk_size = len(chunk)
                        downloaded_size += chunk_size
                        pbar.update(chunk_size)

            pbar.close()

            # 验证文件大小
            actual_size = os.path.getsize(local_path)
            if file_size > 0 and actual_size != file_size:
                os.remove(local_path)
                raise Exception(f"文件大小不匹配: {actual_size} != {file_size}")

            # 更新数据库
            db_manager.update_download_status(file_id, True, local_path)

            # 删除七牛云文件
            if delete_after_download:
                self.delete_qiniu_file(file_key)

            # 更新统计
            with self.stats_lock:
                self.stats['downloaded'] += 1
                self.stats['total_size'] += actual_size

            return True, "下载成功"

        except Exception as e:
            pbar.close()
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass

            db_manager.update_download_status(file_id, False)

            with self.stats_lock:
                self.stats['failed'] += 1

            return False, str(e)

    def format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def download_files(self, file_records, db_manager, delete_after_download=False, max_workers=5):
        """多线程下载文件"""
        if not file_records:
            print("没有需要下载的文件")
            return

        total_files = len(file_records)
        total_size = sum(f.get('file_size', 0) for f in file_records)
        start_time = time.time()

        print(f"开始下载 {total_files} 个文件，总大小: {self.format_size(total_size)}")
        print(f"线程数: {max_workers}, 下载目录: {self.download_dir}")
        if delete_after_download:
            print("下载完成后将删除七牛云文件")
        print("-" * 60)

        # 使用线程池下载
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务
                future_to_file = {
                    executor.submit(self.download_file, file, db_manager, delete_after_download): file
                    for file in file_records
                }

                # 处理结果
                for future in as_completed(future_to_file):
                    if self.is_interrupted:
                        break

                    file_record = future_to_file[future]
                    try:
                        future.result(timeout=3600)  # 1小时超时
                    except Exception as e:
                        print(f"\n文件下载异常: {file_record['file_name']} - {e}")

        except KeyboardInterrupt:
            print("\n下载被用户中断")

        # 显示最终统计
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("下载完成统计:")
        print(f"总文件数: {total_files}")
        print(f"成功下载: {self.stats['downloaded']}")
        print(f"跳过文件: {self.stats['skipped']}")
        print(f"失败文件: {self.stats['failed']}")
        print(f"总大小: {self.format_size(self.stats['total_size'])}")
        print(f"总耗时: {time.strftime('%H:%M:%S', time.gmtime(elapsed_time))}")
        if elapsed_time > 0:
            print(f"平均速度: {self.format_size(self.stats['total_size'] / elapsed_time)}/s")
        print("=" * 60)


def main():
    """主函数"""
    print("七牛云文件下载工具")
    print("=" * 50)

    # 选择存储类型
    storage_choices = {
        '1': '标准存储',
        '2': '深度归档存储',
        '3': '归档存储',
        '4': '低频存储'
    }

    print("请选择存储类型:")
    for key, value in storage_choices.items():
        print(f"{key}. {value}")

    choice = input("请输入选择 (1-4): ").strip()
    if choice not in storage_choices:
        print("无效选择")
        return

    storage_type = storage_choices[choice]

    # 设置线程数
    try:
        max_workers = int(input("请输入线程数 (默认5): ").strip() or "5")
        max_workers = max(1, min(max_workers, 20))
    except ValueError:
        max_workers = 5

    # 是否删除源文件
    delete_choice = input("下载后是否删除七牛云文件? (y/N): ").strip().lower()
    delete_after_download = delete_choice in ['y', 'yes']

    if delete_after_download:
        confirm = input("确认删除七牛云文件? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            delete_after_download = False

    # 初始化
    db_manager = DatabaseManager(db_config)
    downloader = QiniuDownloader(qiniu_config, '/Volumes/5学习网课')

    # 获取文件列表
    print(f"\n正在查询 {storage_type} 文件...")
    files = db_manager.get_undownloaded_files(storage_type)

    if not files:
        print("没有找到需要下载的文件")
        return

    print(f"找到 {len(files)} 个文件需要下载")

    # 开始下载
    try:
        downloader.download_files(files, db_manager, delete_after_download, max_workers)
    finally:
        db_manager.close_all_connections()


if __name__ == "__main__":
    main()