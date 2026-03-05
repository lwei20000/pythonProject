import os
import csv
import logging
import time
import requests
import signal
import sys
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from qiniu import Auth, BucketManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QiniuDownloadManager:
    def __init__(self, qiniu_config, csv_file='5xuexi_videos.csv', download_dir='/Volumes/5学习网课'):
        self.access_key = qiniu_config['access_key']
        self.secret_key = qiniu_config['secret_key']
        self.bucket_name = qiniu_config['bucket_name']
        self.cdn_domain = qiniu_config.get('cdn_domain', 'vod.5xuexi.com')

        # 初始化认证
        self.auth = Auth(self.access_key, self.secret_key)
        self.bucket_manager = BucketManager(self.auth)

        # 文件路径
        self.csv_file = csv_file
        self.download_dir = self.setup_download_dir(download_dir)
        self.state_file = 'download_state.txt'  # 状态记录文件

        # 下载状态
        self.downloaded_count = 0
        self.failed_count = 0
        self.total_size = 0
        self.is_interrupted = False
        self.lock = threading.Lock()  # 线程锁

        # 注册中断信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def setup_download_dir(self, download_path):
        """设置下载目录"""
        # 确保目录存在
        if not os.path.exists(download_path):
            try:
                os.makedirs(download_path, exist_ok=True)
                logger.info(f"创建下载目录: {download_path}")
            except Exception as e:
                logger.error(f"创建目录失败 {download_path}: {e}")
                # 如果创建失败，使用当前目录下的downloads文件夹
                fallback_dir = os.path.join(os.getcwd(), 'downloads')
                os.makedirs(fallback_dir, exist_ok=True)
                logger.info(f"使用备用目录: {fallback_dir}")
                return fallback_dir

        # 检查目录是否可写
        try:
            test_file = os.path.join(download_path, 'test_write.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info(f"下载目录可写: {download_path}")
        except Exception as e:
            logger.error(f"目录不可写 {download_path}: {e}")
            # 如果不可写，使用当前目录下的downloads文件夹
            fallback_dir = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(fallback_dir, exist_ok=True)
            logger.info(f"使用备用目录: {fallback_dir}")
            return fallback_dir

        return download_path

    def signal_handler(self, signum, frame):
        """处理中断信号"""
        logger.info("接收到中断信号，正在保存状态...")
        self.is_interrupted = True
        self.save_download_state()
        sys.exit(1)

    def save_download_state(self):
        """保存下载状态"""
        with self.lock:
            state = {
                'downloaded_count': self.downloaded_count,
                'failed_count': self.failed_count,
                'total_size': self.total_size,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            try:
                with open(self.state_file, 'w') as f:
                    for key, value in state.items():
                        f.write(f"{key}={value}\n")
                logger.info("下载状态已保存")
            except Exception as e:
                logger.error(f"保存状态失败: {e}")

    def load_download_state(self):
        """加载下载状态"""
        if not os.path.exists(self.state_file):
            return None

        try:
            state = {}
            with open(self.state_file, 'r') as f:
                for line in f:
                    key, value = line.strip().split('=', 1)
                    if key in ['downloaded_count', 'failed_count', 'total_size']:
                        state[key] = int(value)
                    else:
                        state[key] = value
            logger.info("下载状态已加载")
            return state
        except Exception as e:
            logger.error(f"加载状态失败: {e}")
            return None

    def read_csv_files(self):
        """读取CSV文件"""
        if not os.path.exists(self.csv_file):
            logger.error(f"CSV文件不存在: {self.csv_file}")
            return []

        files = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    files.append(row)
            logger.info(f"从CSV读取了 {len(files)} 个文件记录")
        except Exception as e:
            logger.error(f"读取CSV失败: {e}")

        return files

    def update_csv_status(self, key, status, error_message='', local_path=''):
        """更新CSV文件中文件的下载状态"""
        try:
            # 读取所有行
            rows = []
            with open(self.csv_file, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                fieldnames = reader.fieldnames

                # 确保必要的字段存在
                required_fields = ['download_status', 'error_message', 'download_time', 'local_path']
                for field in required_fields:
                    if field not in fieldnames:
                        fieldnames.append(field)

                for row in reader:
                    if row['key'] == key:
                        row['download_status'] = status
                        if error_message:
                            row['error_message'] = error_message
                        if status == 'downloaded':
                            row['download_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            row['local_path'] = local_path
                    rows.append(row)

            # 写回文件
            with open(self.csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            logger.debug(f"更新文件状态: {key} -> {status}")

        except Exception as e:
            logger.error(f"更新CSV状态失败 {key}: {e}")

    def get_download_url(self, file_key):
        """获取下载URL"""
        base_url = f"http://{self.cdn_domain}/{file_key}"
        private_url = self.auth.private_download_url(base_url, expires=3600)
        return private_url

    def download_single_file(self, file_info, delete_after_download=False):
        """下载单个文件"""
        key = file_info['key']
        file_name = file_info['file_name']
        file_size = int(file_info.get('file_size', 0))

        # 设置本地保存路径
        local_filename = os.path.join(self.download_dir, file_name)

        # 确保本地目录存在
        local_dir = os.path.dirname(local_filename)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)

        # 检查文件是否已存在且完整（优先检查本地文件）
        if os.path.exists(local_filename):
            existing_size = os.path.getsize(local_filename)
            if existing_size == file_size:
                logger.info(f"文件已存在且完整: {file_name}")
                logger.info(f"文件路径: {local_filename}")
                # 如果CSV中未标记为已下载，则更新状态
                current_status = file_info.get('download_status', '')
                if current_status != 'downloaded':
                    self.update_csv_status(key, 'downloaded', local_path=local_filename)
                return True, "文件已存在"

        # 检查CSV中是否已标记为已下载
        current_status = file_info.get('download_status', '')
        if current_status == 'downloaded':
            logger.info(f"文件已在CSV中标记为已下载，跳过: {file_name}")
            return True, "文件已标记为已下载"

        try:
            # 获取下载URL
            private_url = self.get_download_url(key)

            logger.info(f"开始下载: {file_name} ({self.format_file_size(file_size)})")
            logger.info(f"保存路径: {local_filename}")

            # 设置请求参数
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            timeout = (30, 300)  # 连接超时30秒，读取超时300秒

            # 下载文件
            response = requests.get(private_url, stream=True, headers=headers, timeout=timeout)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', file_size))
            if total_size == 0:
                total_size = file_size

            downloaded_size = 0
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 显示下载进度
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(
                                f"\r[{threading.current_thread().name}] 下载进度: {progress:.1f}% ({downloaded_size}/{total_size} bytes)",
                                end='', flush=True)

                    # 检查是否被中断
                    if self.is_interrupted:
                        raise KeyboardInterrupt("下载被中断")

            # 验证文件大小
            final_size = os.path.getsize(local_filename)
            if final_size != total_size:
                logger.error(f"文件大小不匹配 {file_name}: 期望 {total_size}, 实际 {final_size}")
                os.remove(local_filename)
                return False, f"文件大小不匹配: {final_size}/{total_size}"

            print(f"\n[{threading.current_thread().name}] 下载成功: {file_name}")
            logger.info(f"文件保存到: {local_filename}")

            # 如果选择下载后删除
            if delete_after_download:
                try:
                    ret, info = self.bucket_manager.delete(self.bucket_name, key)
                    if info.status_code == 200:
                        logger.info(f"七牛云文件已删除: {key}")
                    else:
                        logger.warning(f"七牛云文件删除失败: {key}")
                except Exception as e:
                    logger.error(f"删除七牛云文件失败 {key}: {e}")

            # 更新统计和状态（线程安全）
            with self.lock:
                self.downloaded_count += 1
                self.total_size += final_size

            self.update_csv_status(key, 'downloaded', local_path=local_filename)

            return True, "下载成功"

        except KeyboardInterrupt:
            raise  # 重新抛出中断异常
        except requests.exceptions.RequestException as e:
            error_msg = f"下载请求失败: {e}"
            logger.error(f"{error_msg} {file_name}")
            logger.error(f"文件路径: {local_filename}")
            if os.path.exists(local_filename):
                os.remove(local_filename)
            self.update_csv_status(key, 'failed', error_msg)

            with self.lock:
                self.failed_count += 1

            return False, error_msg
        except Exception as e:
            error_msg = f"下载异常: {e}"
            logger.error(f"{error_msg} {file_name}")
            logger.error(f"文件路径: {local_filename}")
            if os.path.exists(local_filename):
                os.remove(local_filename)
            self.update_csv_status(key, 'failed', error_msg)

            with self.lock:
                self.failed_count += 1

            return False, error_msg

    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.2f} {size_names[i]}"

    def get_files_to_download(self, storage_type_name):
        """获取需要下载的文件列表 - 优化跳过逻辑"""
        files = self.read_csv_files()
        if not files:
            return []

        # 过滤指定存储类型且未下载的文件
        files_to_download = []
        skipped_count = 0

        for file in files:
            file_storage_type = file.get('storage_type_name', '')
            download_status = file.get('download_status', '')
            file_name = file.get('file_name', '')

            # 检查存储类型匹配
            if file_storage_type != storage_type_name:
                continue

            # 检查下载状态
            if download_status == 'downloaded':
                skipped_count += 1
                logger.debug(f"跳过已下载文件: {file_name}")
                continue

            # 检查本地文件是否已存在且完整
            local_filename = os.path.join(self.download_dir, file_name)
            file_size = int(file.get('file_size', 0))

            if os.path.exists(local_filename):
                existing_size = os.path.getsize(local_filename)
                if existing_size == file_size:
                    # 文件已存在，更新CSV状态并跳过
                    self.update_csv_status(file['key'], 'downloaded', local_path=local_filename)
                    skipped_count += 1
                    logger.info(f"跳过已存在的完整文件: {file_name}")
                    logger.info(f"文件路径: {local_filename}")
                    continue

            files_to_download.append(file)

        logger.info(
            f"找到 {len(files_to_download)} 个{storage_type_name}文件需要下载，跳过 {skipped_count} 个已下载/已存在文件")
        return files_to_download

    def show_progress(self, total_files, start_time):
        """显示下载进度"""
        while not self.is_interrupted:
            time.sleep(10)
            elapsed_time = time.time() - start_time

            with self.lock:
                downloaded = self.downloaded_count
                failed = self.failed_count
                total_size = self.total_size

            remaining = total_files - downloaded - failed

            if elapsed_time > 0 and downloaded > 0:
                speed = total_size / elapsed_time
                avg_time = elapsed_time / downloaded
                estimated_remaining = remaining * avg_time if remaining > 0 else 0
            else:
                speed = 0
                estimated_remaining = 0

            logger.info(
                f"进度: {downloaded}/{total_files} 成功, {failed} 失败, {remaining} 剩余 | "
                f"速度: {self.format_file_size(speed)}/s | "
                f"剩余时间: {time.strftime('%H:%M:%S', time.gmtime(estimated_remaining))} | "
                f"总大小: {self.format_file_size(total_size)}"
            )

            if downloaded + failed >= total_files or self.is_interrupted:
                break

    def download_files(self, storage_type_name, delete_after_download=False, max_workers=3):
        """下载文件主函数（多线程版本）"""
        # 获取需要下载的文件
        files_to_download = self.get_files_to_download(storage_type_name)
        if not files_to_download:
            logger.info("没有需要下载的文件")
            return

        # 加载之前的状态
        state = self.load_download_state()
        if state:
            self.downloaded_count = state.get('downloaded_count', 0)
            self.failed_count = state.get('failed_count', 0)
            self.total_size = state.get('total_size', 0)
            logger.info(f"从上次中断恢复: 已下载 {self.downloaded_count} 个文件")

        total_files = len(files_to_download)
        start_time = time.time()

        logger.info(f"开始多线程下载 {total_files} 个{storage_type_name}文件，线程数: {max_workers}")
        logger.info(f"下载目录: {self.download_dir}")
        if delete_after_download:
            logger.info("下载完成后将删除七牛云上的文件")

        # 启动进度显示线程
        progress_thread = threading.Thread(
            target=self.show_progress,
            args=(total_files, start_time),
            daemon=True
        )
        progress_thread.start()

        # 使用线程池进行多线程下载
        success_count = 0
        failed_count = 0
        processed_count = 0

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有下载任务
                future_to_file = {
                    executor.submit(self.download_single_file, file_info, delete_after_download): file_info
                    for file_info in files_to_download
                }

                # 处理完成的任务
                for future in as_completed(future_to_file):
                    if self.is_interrupted:
                        break

                    file_info = future_to_file[future]
                    processed_count += 1

                    try:
                        success, message = future.result()
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1

                        # 每处理10个文件保存一次状态
                        if processed_count % 10 == 0:
                            self.save_download_state()
                            logger.info(f"已处理 {processed_count}/{total_files} 个文件")

                    except Exception as e:
                        logger.error(f"处理文件 {file_info['file_name']} 时发生异常: {e}")
                        failed_count += 1

                    # 检查是否所有文件都已处理
                    if processed_count >= total_files:
                        break

        except KeyboardInterrupt:
            logger.info("下载被用户中断")
        finally:
            self.save_download_state()

        # 最终统计
        total_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"下载完成! 总共: {total_files}")
        logger.info(f"成功: {success_count}, 失败: {failed_count}")
        logger.info(f"总耗时: {total_time:.1f} 秒")
        if total_time > 0:
            logger.info(f"平均速度: {self.format_file_size(self.total_size / total_time)}/s")
        logger.info(f"总下载大小: {self.format_file_size(self.total_size)}")
        logger.info("=" * 60)

        # 清理状态文件
        if os.path.exists(self.state_file) and not self.is_interrupted:
            os.remove(self.state_file)
            logger.info("状态文件已清理")


def main():
    """主函数"""
    # 七牛云配置
    qiniu_config = {
        'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
        'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81',
        'bucket_name': '5xuexi',
        'cdn_domain': 'vod.5xuexi.com'
    }

    print("七牛云文件下载工具（多线程版）")
    print("=" * 50)
    print("警告：密钥已硬编码在代码中，建议尽快重置密钥！")
    print("=" * 50)

    # 选择存储类型
    print("请选择要下载的存储类型:")
    print("1. 标准存储")
    print("2. 深度归档存储")

    choice = input("请输入选择 (1-2): ").strip()
    if choice == '1':
        storage_type_name = '标准存储'
    elif choice == '2':
        storage_type_name = '深度归档存储'
    else:
        print("无效选择")
        return

    # 设置线程数
    try:
        max_workers = int(input("请输入线程数量 (默认3): ").strip() or "3")
        max_workers = max(1, min(max_workers, 20))  # 限制在1-20之间
        print(f"设置线程数: {max_workers}")
    except ValueError:
        max_workers = 3
        print(f"使用默认线程数: {max_workers}")

    # 是否删除源文件
    delete_choice = input("下载完成后是否删除七牛云上的文件? (y/N): ").strip().lower()
    delete_after_download = delete_choice in ['y', 'yes', '是']

    # CSV文件选择（默认使用5xuexi_videos.csv）
    csv_file = input("请输入CSV文件名（默认: 5xuexi_videos.csv）: ").strip()
    if not csv_file:
        csv_file = '5xuexi_videos.csv'

    # 使用固定的下载目录
    download_dir = '/Volumes/5学习网课'
    print(f"下载目录固定为: {download_dir}")

    # 创建下载管理器
    downloader = QiniuDownloadManager(qiniu_config, csv_file, download_dir)

    print(f"\n开始多线程下载{storage_type_name}文件...")
    print(f"线程数: {max_workers}")
    print(f"下载目录: {download_dir}")
    print("注意: 可以随时按 Ctrl+C 中断下载，下次会从断点继续")
    print("=" * 50)

    try:
        downloader.download_files(storage_type_name, delete_after_download, max_workers)
        print("✅ 下载任务完成！")
    except Exception as e:
        print(f"❌ 下载任务失败: {e}")


if __name__ == "__main__":
    main()