import qiniu
from qiniu import Auth, BucketManager
import requests
import time
from urllib.parse import urlparse

# 七牛云配置
qiniu_config = {
    'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
    'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81',
    'bucket_name': '5xuexi'
}


# 获取七牛云空间中的所有文件
def get_qiniu_files(auth):
    """获取七牛云指定空间中的所有文件"""
    bucket_manager = BucketManager(auth)
    files = []
    marker = None

    while True:
        ret, eof, info = bucket_manager.list(qiniu_config['bucket_name'], marker=marker)
        if ret is None:
            print(f"列举文件失败: {info}")
            break

        files.extend([{
            'key': item['key'],
            'type': item.get('type', 0)  # 存储类型：0-标准，1-低频，2-归档，3-深度归档
        } for item in ret.get('items', [])])

        marker = ret.get('marker')
        if eof or not marker:
            break

    return files


# 解冻深度归档文件
def restore_from_deep_archive(auth, file_key):
    """将深度归档文件解冻"""
    try:
        # 使用七牛API解冻文件
        entry = f"{qiniu_config['bucket_name']}:{file_key}"
        encoded_entry = qiniu.urlsafe_base64_encode(entry)
        url = f"http://rs.qiniu.com/restoreAr/{encoded_entry}/freezeAfterDays/1"

        # 生成管理token
        access_token = auth.token_of_request(url)
        headers = {"Authorization": "QBox " + access_token}

        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f"解冻文件失败: {file_key} - {response.text}")
            return False
    except Exception as e:
        print(f"解冻文件时出错: {file_key} - {str(e)}")
        return False


def restore_files_by_pattern():
    """根据文件名模式解冻文件"""
    # 1. 获取要查询的文件名模式
    pattern = input("请输入要查询的文件名模式（支持模糊匹配）: ").strip()
    if not pattern:
        print("文件名模式不能为空")
        return

    # 2. 初始化七牛云认证
    auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])

    # 3. 获取七牛云空间中的所有文件
    qiniu_files = get_qiniu_files(auth)
    print(f"七牛云空间中找到 {len(qiniu_files)} 个文件")

    # 4. 筛选出深度归档文件并匹配文件名模式
    deep_archive_files = [
        file_info for file_info in qiniu_files
        if file_info['type'] == 3 and pattern in file_info['key']
    ]

    print(f"找到 {len(deep_archive_files)} 个深度归档文件匹配模式 '{pattern}'")

    if not deep_archive_files:
        print("没有找到匹配的深度归档文件")
        return

    # 显示匹配的文件列表
    print("\n匹配的文件列表:")
    for i, file_info in enumerate(deep_archive_files, 1):
        print(f"{i}. {file_info['key']}")

    # 5. 确认操作
    confirm = input(f"\n确认要解冻这 {len(deep_archive_files)} 个文件吗？(输入yes继续): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    # 6. 执行解冻操作
    success_count = 0
    for i, file_info in enumerate(deep_archive_files, 1):
        if restore_from_deep_archive(auth, file_info['key']):
            success_count += 1
            print(f"成功解冻: {file_info['key']} ({i}/{len(deep_archive_files)})")
        else:
            print(f"解冻失败: {file_info['key']}")

        time.sleep(0.2)  # 避免请求过于频繁

    print(f"\n解冻完成！成功解冻 {success_count} 个文件")


def restore_specific_file():
    """解冻特定文件"""
    # 1. 获取要解冻的完整文件名
    filename = input("请输入要解冻的完整文件名: ").strip()
    if not filename:
        print("文件名不能为空")
        return

    # 2. 初始化七牛云认证
    auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])

    # 3. 获取七牛云空间中的所有文件
    qiniu_files = get_qiniu_files(auth)

    # 4. 查找特定文件
    target_file = None
    for file_info in qiniu_files:
        if file_info['key'] == filename and file_info['type'] == 3:
            target_file = file_info
            break

    if not target_file:
        print(f"未找到文件 '{filename}' 或该文件不是深度归档状态")
        return

    # 5. 确认操作
    confirm = input(f"确认要解冻文件 '{filename}' 吗？(输入yes继续): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    # 6. 执行解冻操作
    if restore_from_deep_archive(auth, filename):
        print(f"成功解冻文件: {filename}")
    else:
        print(f"解冻文件失败: {filename}")


if __name__ == "__main__":
    print("请选择操作模式:")
    print("1. 模糊查询并解冻多个文件")
    print("2. 解冻特定文件")

    choice = input("请输入选择 (1 或 2): ").strip()

    if choice == '1':
        restore_files_by_pattern()
    elif choice == '2':
        restore_specific_file()
    else:
        print("无效的选择")



#影视美学
#保险学
#成本管理会计
