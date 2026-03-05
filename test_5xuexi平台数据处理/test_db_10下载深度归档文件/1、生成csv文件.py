import os
import csv
import logging
from datetime import datetime
from qiniu import Auth, BucketManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QiniuBucketScanner:
    def __init__(self, qiniu_config, csv_file='qiniu_videos.csv'):
        self.access_key = qiniu_config['access_key']
        self.secret_key = qiniu_config['secret_key']
        self.bucket_name = qiniu_config['bucket_name']

        # 初始化认证和Bucket管理器
        self.auth = Auth(self.access_key, self.secret_key)
        self.bucket_manager = BucketManager(self.auth)

        # CSV文件路径
        self.csv_file = csv_file

        # 视频文件扩展名（简化版）
        self.video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.m4v'}

    def get_storage_type_name(self, storage_type):
        """获取存储类型名称（简化版）"""
        # 根据您说的只有两种类型
        if storage_type in [0, 1]:  # 标准存储
            return '标准存储'
        elif storage_type in [2, 3, 4]:  # 低频、归档、深度归档都归为深度归档
            return '深度归档存储'
        else:
            return f'未知类型({storage_type})'

    def get_file_info(self, key):
        """获取文件的详细信息"""
        try:
            # 获取文件信息
            ret, info = self.bucket_manager.stat(self.bucket_name, key)
            if info.status_code != 200:
                logger.warning(f"无法获取文件信息 {key}: {info.status_code}")
                return None

            file_info = {
                'key': key,
                'file_size': ret.get('fsize', 0),
                'mime_type': ret.get('mimeType', ''),
                'put_time': ret.get('putTime', 0),
                'storage_type': ret.get('type', 0),
                'md5': ret.get('md5', ''),
                'status': ret.get('status', 0),
                'file_name': os.path.basename(key)
            }

            return file_info

        except Exception as e:
            logger.error(f"获取文件信息失败 {key}: {str(e)}")
            return None

    def is_video_file(self, filename):
        """检查是否为视频文件"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.video_extensions

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

    def format_put_time(self, put_time):
        """格式化putTime时间戳"""
        if put_time == 0:
            return "未知"

        try:
            # 七牛云的putTime是100纳秒为单位的时间戳，转换为秒
            timestamp = int(put_time) / 10000000
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return "时间格式错误"

    def scan_bucket_files(self, prefix='', limit=1000):
        """扫描存储桶中的文件"""
        logger.info(f"开始扫描存储桶 {self.bucket_name}，前缀: {prefix}")

        all_files = []
        marker = None
        total_count = 0
        video_count = 0

        try:
            while True:
                # 列出文件
                ret, eof, info = self.bucket_manager.list(
                    self.bucket_name,
                    prefix=prefix,
                    marker=marker,
                    limit=limit
                )

                if info.status_code != 200:
                    logger.error(f"列出文件失败: {info.status_code}")
                    break

                if 'items' not in ret:
                    logger.warning("没有找到文件项")
                    break

                batch_files = ret['items']
                batch_count = len(batch_files)
                total_count += batch_count

                logger.info(f"获取到 {batch_count} 个文件，总计 {total_count} 个文件")

                # 处理每个文件
                for item in batch_files:
                    key = item['key']

                    # 只处理视频文件
                    if self.is_video_file(key):
                        file_info = self.get_file_info(key)
                        if file_info:
                            all_files.append(file_info)
                            video_count += 1
                            logger.info(
                                f"找到视频文件[{video_count}]: {key} - {self.format_file_size(file_info['file_size'])} - {self.get_storage_type_name(file_info['storage_type'])}")
                    else:
                        logger.debug(f"跳过非视频文件: {key}")

                # 检查是否还有更多文件
                if eof:
                    logger.info("已扫描完所有文件")
                    break

                # 设置下一个marker
                marker = ret.get('marker')
                if not marker:
                    break

        except Exception as e:
            logger.error(f"扫描存储桶失败: {str(e)}")

        logger.info(f"扫描完成！总共找到 {total_count} 个文件，其中 {video_count} 个视频文件")
        return all_files

    def write_to_csv(self, files):
        """将文件信息写入CSV"""
        if not files:
            logger.warning("没有找到视频文件，不创建CSV文件")
            return False

        try:
            # CSV字段名（简化版）
            fieldnames = [
                'file_name', 'key', 'file_size', 'formatted_size',
                'storage_type', 'storage_type_name', 'put_time',
                'formatted_put_time', 'mime_type', 'md5', 'scan_time'
            ]

            with open(self.csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for file_info in files:
                    # 准备行数据
                    row = {
                        'file_name': file_info['file_name'],
                        'key': file_info['key'],
                        'file_size': file_info['file_size'],
                        'formatted_size': self.format_file_size(file_info['file_size']),
                        'storage_type': file_info['storage_type'],
                        'storage_type_name': self.get_storage_type_name(file_info['storage_type']),
                        'put_time': file_info['put_time'],
                        'formatted_put_time': self.format_put_time(file_info['put_time']),
                        'mime_type': file_info['mime_type'],
                        'md5': file_info['md5'],
                        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    writer.writerow(row)

            logger.info(f"成功写入 {len(files)} 个视频文件信息到 {self.csv_file}")
            return True

        except Exception as e:
            logger.error(f"写入CSV文件失败: {str(e)}")
            return False

    def show_statistics(self, files):
        """显示统计信息"""
        if not files:
            print("没有找到视频文件")
            return

        total_size = sum(f['file_size'] for f in files)
        storage_stats = {}

        for file_info in files:
            storage_type = file_info['storage_type']
            storage_name = self.get_storage_type_name(storage_type)
            if storage_name not in storage_stats:
                storage_stats[storage_name] = {'count': 0, 'size': 0}
            storage_stats[storage_name]['count'] += 1
            storage_stats[storage_name]['size'] += file_info['file_size']

        print("=" * 60)
        print("七牛云存储桶视频文件统计报告")
        print("=" * 60)
        print(f"存储桶名称: {self.bucket_name}")
        print(f"总视频文件数: {len(files)}")
        print(f"总大小: {self.format_file_size(total_size)}")
        print("\n存储类型分布:")
        for storage_name, stats in storage_stats.items():
            percentage = (stats['count'] / len(files)) * 100
            print(
                f"  {storage_name}: {stats['count']} 个文件 ({percentage:.1f}%), 大小: {self.format_file_size(stats['size'])}")
        print("=" * 60)

    def scan_and_export(self, prefix=''):
        """扫描并导出文件信息"""
        logger.info(f"开始扫描存储桶: {self.bucket_name}")

        # 扫描文件
        files = self.scan_bucket_files(prefix=prefix)

        if not files:
            logger.error("没有找到视频文件")
            return False

        # 显示统计信息
        self.show_statistics(files)

        # 写入CSV
        success = self.write_to_csv(files)

        if success:
            logger.info(f"扫描完成！结果已保存到: {self.csv_file}")
            print(f"\nCSV文件已生成: {self.csv_file}")
            print("文件包含以下字段:")
            print(
                "  file_name, key, file_size, formatted_size, storage_type, storage_type_name, put_time, formatted_put_time, mime_type, md5, scan_time")
            return True
        else:
            logger.error("导出失败")
            return False


def main():
    """主函数"""
    # 七牛云配置
    qiniu_config = {
        'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
        'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81',
        'bucket_name': '5xuexi'
    }

    print("七牛云存储桶视频文件扫描工具")
    print("=" * 50)
    print("警告：密钥已硬编码在代码中，建议尽快重置密钥！")
    print("=" * 50)

    # 选择扫描前缀
    prefix = input("请输入要扫描的文件前缀（留空则扫描所有文件）: ").strip()

    # 选择CSV文件名
    csv_file = input("请输入CSV文件名（默认: qiniu_videos.csv）: ").strip()
    if not csv_file:
        csv_file = 'qiniu_videos.csv'

    # 创建扫描器
    scanner = QiniuBucketScanner(qiniu_config, csv_file)

    # 开始扫描
    print(f"\n开始扫描存储桶 {qiniu_config['bucket_name']}...")
    print("这可能需要一些时间，请耐心等待...")

    success = scanner.scan_and_export(prefix)

    if success:
        print(f"\n✅ 扫描完成！结果已保存到: {csv_file}")
    else:
        print("\n❌ 扫描失败，请检查配置和网络连接")


# 直接运行版本（无需交互）
def quick_scan():
    """快速扫描版本"""
    # 七牛云配置
    qiniu_config = {
        'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
        'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81',
        'bucket_name': '5xuexi'
    }

    # 创建扫描器
    scanner = QiniuBucketScanner(qiniu_config, '5xuexi_videos.csv')

    print("开始快速扫描...")
    scanner.scan_and_export()
œ

if __name__ == "__main__":
    # 如果需要交互式操作，使用 main()
    # main()

    # 如果直接运行，使用 quick_scan()
    quick_scan()