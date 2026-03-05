import os
import logging
from qiniu import Auth, BucketManager
import requests
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QiniuDeepArchiveDownloader:
    def __init__(self, qiniu_config):
        self.access_key = qiniu_config['access_key']
        self.secret_key = qiniu_config['secret_key']
        self.bucket_name = qiniu_config['bucket_name']

        # 初始化认证和Bucket管理器
        self.auth = Auth(self.access_key, self.secret_key)
        self.bucket_manager = BucketManager(self.auth)

        # 下载目录
        self.download_dir = 'qiniu_downloads'
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def get_all_deep_archive_files(self):
        """获取所有深度归档文件"""
        logger.info("开始获取所有深度归档文件列表...")

        marker = None
        deep_archive_files = []
        total_files = 0

        while True:
            # 使用正确的list方法
            try:
                # list方法的参数顺序：bucket, prefix, marker, limit, delimiter
                ret, eof, info = self.bucket_manager.list(
                    self.bucket_name,
                    None,  # prefix
                    marker,
                    1000,  # limit
                    None  # delimiter
                )
            except Exception as e:
                logger.error(f"列出文件失败: {e}")
                break

            if ret is None:
                logger.error(f"获取文件列表失败: {info}")
                break

            items = ret.get('items', [])
            total_files += len(items)
            logger.info(f"已扫描 {total_files} 个文件...")

            # 过滤出深度归档文件
            for item in items:
                # 深度归档文件的存储类型通常是2或3
                # 1-标准存储，2-低频存储，3-归档存储，4-深度归档存储
                storage_type = item.get('type', 0)
                if storage_type in [2, 3, 4]:  # 低频、归档、深度归档
                    deep_archive_files.append({
                        'key': item['key'],
                        'hash': item['hash'],
                        'fsize': item['fsize'],
                        'mimeType': item.get('mimeType', ''),
                        'putTime': item.get('putTime', 0),
                        'type': storage_type
                    })

            if eof:
                break

            marker = ret.get('marker', None)
            if not marker:
                break

        # 按存储类型分类统计
        type_count = {}
        for file in deep_archive_files:
            file_type = file['type']
            type_count[file_type] = type_count.get(file_type, 0) + 1

        logger.info(f"找到 {len(deep_archive_files)} 个待处理文件")
        for storage_type, count in type_count.items():
            type_name = self.get_storage_type_name(storage_type)
            logger.info(f"  存储类型 {storage_type}({type_name}): {count} 个文件")

        return deep_archive_files

    def get_storage_type_name(self, storage_type):
        """获取存储类型名称"""
        type_map = {
            0: '标准存储',
            1: '标准存储',
            2: '低频存储',
            3: '归档存储',
            4: '深度归档存储'
        }
        return type_map.get(storage_type, f'未知类型({storage_type})')

    def restore_archive_file(self, key):
        """恢复深度归档文件"""
        try:
            # 使用正确的restore_ar方法
            ret, info = self.bucket_manager.restore_ar(
                self.bucket_name,
                key,
                freeze_after_days=7
            )

            if info.status_code == 200:
                logger.info(f"文件恢复指令发送成功: {key}")
                return True
            else:
                logger.warning(f"文件恢复失败 {key}: 状态码 {info.status_code}")
                return False

        except Exception as e:
            logger.error(f"恢复文件异常 {key}: {str(e)}")
            return False

    def download_single_file(self, key):
        """下载单个文件"""
        local_filename = os.path.join(self.download_dir, key)

        # 确保本地目录存在
        local_dir = os.path.dirname(local_filename)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # 如果文件已存在，跳过下载
        if os.path.exists(local_filename):
            file_size = os.path.getsize(local_filename)
            logger.info(f"文件已存在，跳过下载: {key} ({file_size} bytes)")
            return True

        try:
            # 获取下载URL - 使用正确的域名格式
            # 对于归档文件，可能需要使用特定的域名
            base_url = f'http://{self.bucket_name}.z0.glb.qiniu.com/{key}'

            # 生成私有下载链接
            private_url = self.auth.private_download_url(base_url, expires=3600)

            logger.info(f"开始下载: {key}")

            # 下载文件
            response = requests.get(private_url, stream=True, timeout=300)
            response.raise_for_status()

            file_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

            # 验证文件大小
            if os.path.exists(local_filename):
                actual_size = os.path.getsize(local_filename)
                if file_size > 0 and actual_size != file_size:
                    logger.error(f"文件大小不匹配 {key}: 期望 {file_size}, 实际 {actual_size}")
                    os.remove(local_filename)
                    return False

            logger.info(f"文件下载成功: {key} -> {local_filename} ({actual_size} bytes)")
            return True

        except Exception as e:
            logger.error(f"下载文件失败 {key}: {str(e)}")
            # 如果下载失败，删除可能不完整的文件
            if os.path.exists(local_filename):
                os.remove(local_filename)
            return False

    def delete_single_file(self, key):
        """删除单个文件"""
        try:
            ret, info = self.bucket_manager.delete(self.bucket_name, key)
            if info.status_code == 200:
                logger.info(f"文件删除成功: {key}")
                return True
            else:
                logger.error(f"文件删除失败: {key} - 状态码 {info.status_code}")
                return False
        except Exception as e:
            logger.error(f"删除文件异常 {key}: {str(e)}")
            return False

    def process_files_batch(self, batch_size=10):
        """批量处理文件"""
        # 1. 获取所有需要处理的文件
        files_to_process = self.get_all_deep_archive_files()

        if not files_to_process:
            logger.info("没有找到需要处理的文件")
            return

        total_files = len(files_to_process)
        logger.info(f"开始处理 {total_files} 个文件，批次大小: {batch_size}")

        success_count = 0
        failed_count = 0

        # 2. 分批处理
        for i in range(0, total_files, batch_size):
            batch = files_to_process[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_files + batch_size - 1) // batch_size

            logger.info(f"处理第 {batch_num}/{total_batches} 批，本批 {len(batch)} 个文件")

            batch_success = 0
            batch_failed = 0

            for file_info in batch:
                key = file_info['key']
                storage_type = file_info['type']
                type_name = self.get_storage_type_name(storage_type)

                logger.info(f"处理文件: {key} ({type_name})")

                try:
                    # 恢复文件（如果是归档或深度归档）
                    if storage_type in [3, 4]:  # 归档或深度归档需要恢复
                        if not self.restore_archive_file(key):
                            logger.error(f"恢复失败，跳过: {key}")
                            batch_failed += 1
                            continue

                        # 等待恢复完成（深度归档恢复需要时间）
                        logger.info(f"等待文件恢复: {key} - 等待60秒")
                        time.sleep(60)

                    # 下载文件
                    if not self.download_single_file(key):
                        logger.error(f"下载失败: {key}")
                        batch_failed += 1
                        continue

                    # 删除云端文件
                    if not self.delete_single_file(key):
                        logger.error(f"删除失败: {key}")
                        batch_failed += 1
                    else:
                        batch_success += 1
                        logger.info(f"成功处理: {key}")

                    # 文件间间隔
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"处理文件异常 {key}: {str(e)}")
                    batch_failed += 1
                    continue

            success_count += batch_success
            failed_count += batch_failed

            logger.info(f"第 {batch_num} 批完成: 成功 {batch_success}, 失败 {batch_failed}")

            # 批次间间隔
            if i + batch_size < total_files:
                wait_time = 5
                logger.info(f"等待 {wait_time} 秒后继续下一批...")
                time.sleep(wait_time)

        logger.info(f"处理完成! 总共: {total_files}, 成功: {success_count}, 失败: {failed_count}")

    def run(self):
        """主执行函数"""
        try:
            logger.info("开始七牛云文件下载任务")
            logger.info(f"存储桶: {self.bucket_name}")
            logger.info(f"下载目录: {self.download_dir}")

            # 使用批量处理流程
            self.process_files_batch(batch_size=5)  # 先小批量测试

            logger.info("所有文件处理完成！")

        except Exception as e:
            logger.error(f"执行过程中发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())


# 主程序
if __name__ == "__main__":
    # 七牛云配置
    qiniu_config = {
        'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
        'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81',
        'bucket_name': '5xuexi'
    }

    # 安全提醒
    print("警告：密钥已硬编码在代码中，建议使用环境变量或配置文件！")
    print("开始执行文件下载任务...")

    # 创建下载器并执行
    downloader = QiniuDeepArchiveDownloader(qiniu_config)
    downloader.run()