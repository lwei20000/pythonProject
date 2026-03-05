import qiniu
from qiniu import Auth, BucketManager
from collections import defaultdict
import pandas as pd
import os

# 七牛云配置
qiniu_config = {
    'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
    'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81'
}


def get_all_buckets(auth):
    """获取账户下所有bucket"""
    try:
        bucket_manager = BucketManager(auth)
        ret, info = bucket_manager.buckets()
        if ret is not None:
            return ret
        print(f"获取bucket列表失败: {info}")
        return []
    except Exception as e:
        print(f"获取bucket列表时出错: {e}")
        return []


def get_bucket_stats(auth, bucket_name):
    """获取存储空间的统计信息"""
    try:
        bucket_manager = BucketManager(auth)

        total_files = 0
        total_size = 0
        marker = None

        print(f"正在统计存储空间: {bucket_name}")

        while True:
            ret, eof, info = bucket_manager.list(bucket_name, marker=marker)
            if ret is None:
                print(f"列举文件失败: {info}")
                break

            items = ret.get('items', [])
            total_files += len(items)
            total_size += sum(item['fsize'] for item in items)

            print(f"已统计 {total_files} 个文件，当前总大小: {format_size(total_size)}", end='\r')

            marker = ret.get('marker')
            if eof or not marker:
                break

        print()  # 换行
        return {
            'file_count': total_files,
            'total_size': total_size,
            'formatted_size': format_size(total_size)
        }

    except Exception as e:
        print(f"统计存储空间时出错: {e}")
        return None


def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def generate_bucket_report():
    """生成存储空间统计报告"""
    try:
        # 初始化Auth对象
        auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])

        # 获取所有bucket
        buckets = get_all_buckets(auth)
        if not buckets:
            print("账户下没有存储空间或获取失败")
            return None

        # 存储统计结果
        report = {
            'total_buckets': len(buckets),
            'total_files': 0,
            'total_size': 0,
            'buckets': []
        }

        # 遍历所有bucket
        for bucket_name in buckets:
            stats = get_bucket_stats(auth, bucket_name)
            if stats:
                report['buckets'].append({
                    'name': bucket_name,
                    'file_count': stats['file_count'],
                    'total_size': stats['total_size'],
                    'formatted_size': stats['formatted_size']
                })
                report['total_files'] += stats['file_count']
                report['total_size'] += stats['total_size']

        report['formatted_total_size'] = format_size(report['total_size'])
        return report

    except Exception as e:
        print(f"生成报告时出错: {e}")
        return None


def save_to_excel(report, filename="qiniu_bucket_report.xlsx"):
    """将统计结果保存到Excel文件"""
    try:
        # 准备数据
        data = []
        for bucket in report['buckets']:
            data.append([
                bucket['name'],
                bucket['file_count'],
                bucket['total_size'],
                bucket['formatted_size']
            ])

        # 添加汇总行
        data.append([
            "总计",
            report['total_files'],
            report['total_size'],
            report['formatted_total_size']
        ])

        # 创建DataFrame
        df = pd.DataFrame(data, columns=['存储空间名称', '文件数量', '总大小(字节)', '格式化大小'])

        # 保存到Excel
        filepath = os.path.join(os.getcwd(), filename)
        df.to_excel(filepath, index=False)
        print(f"\n统计结果已保存到: {filepath}")

        return filepath
    except Exception as e:
        print(f"保存Excel文件时出错: {e}")
        return None


def print_report(report):
    """打印统计报告"""
    if not report:
        print("未能生成统计报告")
        return

    print("\n七牛云存储空间统计报告")
    print("=" * 70)
    print(f"总存储空间数量: {report['total_buckets']}")
    print(f"总文件数量: {report['total_files']}")
    print(f"总文件大小: {report['formatted_total_size']}")

    print("\n存储空间详细信息:")
    print("-" * 70)
    print(f"{'存储空间名称':<20}{'文件数量':>15}{'总大小':>30}")
    print("-" * 70)

    for bucket in report['buckets']:
        print(f"{bucket['name']:<20}{bucket['file_count']:>15,}{bucket['formatted_size']:>30}")

    print("=" * 70)


if __name__ == "__main__":
    print("正在统计七牛云存储空间信息...")
    report = generate_bucket_report()

    if report:
        print_report(report)
        save_to_excel(report)