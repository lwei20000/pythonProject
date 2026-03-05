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

# 存储类型常量
STORAGE_CLASS_STANDARD = 0  # 标准存储
STORAGE_CLASS_INFREQUENT = 1  # 低频存储
STORAGE_CLASS_ARCHIVE = 2  # 归档存储
STORAGE_CLASS_DEEP_ARCHIVE = 3  # 深度归档存储


def get_storage_class_name(storage_class):
    """获取存储类型名称"""
    names = {
        0: "标准存储",
        1: "低频存储",
        2: "归档存储",
        3: "深度归档存储"
    }
    return names.get(storage_class, "未知存储类型")


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
            'type': item.get('type', 0),
            'mimeType': item.get('mimeType', ''),
            'fsize': item.get('fsize', 0)
        } for item in ret.get('items', [])])

        marker = ret.get('marker')
        if eof or not marker:
            break

    return files


def restore_from_deep_archive(auth, file_key):
    """将深度归档文件解冻"""
    try:
        entry = f"{qiniu_config['bucket_name']}:{file_key}"
        encoded_entry = qiniu.urlsafe_base64_encode(entry)
        url = f"http://rs.qiniu.com/restoreAr/{encoded_entry}/freezeAfterDays/1"

        access_token = auth.token_of_request(url)
        headers = {"Authorization": "QBox " + access_token}

        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            print(f"解冻指令已发送: {file_key}")
            return True
        else:
            print(f"解冻文件失败: {file_key} - {response.text}")
            return False
    except Exception as e:
        print(f"解冻文件时出错: {file_key} - {str(e)}")
        return False


def change_storage_class(auth, file_key, target_storage_class=STORAGE_CLASS_STANDARD):
    """修改文件的存储类型"""
    try:
        entry = f"{qiniu_config['bucket_name']}:{file_key}"
        encoded_entry = qiniu.urlsafe_base64_encode(entry)

        # 构建修改存储类型的URL
        url = f"http://rs.qiniu.com/chtype/{encoded_entry}/type/{target_storage_class}"

        access_token = auth.token_of_request(url)
        headers = {"Authorization": "QBox " + access_token}

        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            print(f"存储类型修改成功: {file_key} -> {get_storage_class_name(target_storage_class)}")
            return True
        else:
            print(f"存储类型修改失败: {file_key} - {response.text}")
            return False
    except Exception as e:
        print(f"修改存储类型时出错: {file_key} - {str(e)}")
        return False


def wait_for_restore_completion(auth, file_key, max_wait_time=3600):
    """等待文件解冻完成"""
    print(f"等待文件解冻: {file_key}")

    start_time = time.time()
    check_interval = 30  # 每30秒检查一次

    while time.time() - start_time < max_wait_time:
        try:
            # 获取文件状态
            bucket_manager = BucketManager(auth)
            ret, info = bucket_manager.stat(qiniu_config['bucket_name'], file_key)

            if ret is not None:
                current_type = ret.get('type', 0)
                if current_type != STORAGE_CLASS_DEEP_ARCHIVE:
                    print(f"文件解冻完成: {file_key}")
                    return True

            print(f"文件仍在解冻中... 已等待 {int(time.time() - start_time)} 秒")
            time.sleep(check_interval)

        except Exception as e:
            print(f"检查文件状态时出错: {str(e)}")
            time.sleep(check_interval)

    print(f"文件解冻等待超时: {file_key}")
    return False


def restore_and_change_storage_by_pattern():
    """根据文件名模式解冻文件并修改存储类型"""
    pattern = input("请输入要查询的文件名模式（支持模糊匹配）: ").strip()
    if not pattern:
        print("文件名模式不能为空")
        return

    auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])
    qiniu_files = get_qiniu_files(auth)
    print(f"七牛云空间中找到 {len(qiniu_files)} 个文件")

    # 筛选出深度归档文件并匹配文件名模式
    target_files = [
        file_info for file_info in qiniu_files
        if file_info['type'] == STORAGE_CLASS_DEEP_ARCHIVE and pattern in file_info['key']
    ]

    print(f"找到 {len(target_files)} 个深度归档文件匹配模式 '{pattern}'")

    if not target_files:
        print("没有找到匹配的深度归档文件")
        return

    # 显示匹配的文件列表
    print("\n匹配的文件列表:")
    for i, file_info in enumerate(target_files, 1):
        print(f"{i}. {file_info['key']} (大小: {file_info['fsize']} bytes)")

    # 确认操作
    confirm = input(f"\n确认要解冻这 {len(target_files)} 个文件并修改为标准存储吗？(输入yes继续): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    # 执行解冻和修改存储类型操作
    success_restore_count = 0
    success_change_count = 0

    for i, file_info in enumerate(target_files, 1):
        print(f"\n处理文件 ({i}/{len(target_files)}): {file_info['key']}")

        # 1. 解冻文件
        if restore_from_deep_archive(auth, file_info['key']):
            success_restore_count += 1
            print(f"✓ 解冻指令发送成功")

            # 2. 等待解冻完成
            if wait_for_restore_completion(auth, file_info['key']):
                # 3. 修改存储类型为标准存储
                if change_storage_class(auth, file_info['key'], STORAGE_CLASS_STANDARD):
                    success_change_count += 1
                    print(f"✓ 存储类型修改成功")
                else:
                    print(f"✗ 存储类型修改失败")
            else:
                print(f"✗ 文件解冻未完成，跳过修改存储类型")
        else:
            print(f"✗ 解冻失败")

        time.sleep(1)  # 避免请求过于频繁

    print(f"\n操作完成！")
    print(f"成功解冻文件: {success_restore_count}/{len(target_files)}")
    print(f"成功修改存储类型: {success_change_count}/{len(target_files)}")


def restore_and_change_specific_file():
    """解冻特定文件并修改存储类型"""
    filename = input("请输入要解冻的完整文件名: ").strip()
    if not filename:
        print("文件名不能为空")
        return

    auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])
    qiniu_files = get_qiniu_files(auth)

    target_file = None
    for file_info in qiniu_files:
        if file_info['key'] == filename and file_info['type'] == STORAGE_CLASS_DEEP_ARCHIVE:
            target_file = file_info
            break

    if not target_file:
        print(f"未找到文件 '{filename}' 或该文件不是深度归档状态")
        return

    print(f"找到文件: {filename}")
    print(f"当前存储类型: {get_storage_class_name(target_file['type'])}")
    print(f"文件大小: {target_file['fsize']} bytes")

    confirm = input(f"\n确认要解冻文件并修改为标准存储吗？(输入yes继续): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    # 执行操作
    print(f"\n开始处理文件: {filename}")

    # 1. 解冻文件
    if restore_from_deep_archive(auth, filename):
        print(f"✓ 解冻指令发送成功")

        # 2. 等待解冻完成
        if wait_for_restore_completion(auth, filename):
            # 3. 修改存储类型为标准存储
            if change_storage_class(auth, filename, STORAGE_CLASS_STANDARD):
                print(f"✓ 操作完成！文件已解冻并修改为标准存储")
            else:
                print(f"✗ 存储类型修改失败")
        else:
            print(f"✗ 文件解冻未完成")
    else:
        print(f"✗ 解冻失败")


def batch_change_existing_files():
    """批量修改已解冻文件的存储类型为标准存储"""
    pattern = input("请输入要查询的文件名模式（支持模糊匹配）: ").strip()
    if not pattern:
        print("文件名模式不能为空")
        return

    auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])
    qiniu_files = get_qiniu_files(auth)

    # 筛选出非标准存储的文件
    target_files = [
        file_info for file_info in qiniu_files
        if pattern in file_info['key'] and file_info['type'] != STORAGE_CLASS_STANDARD
    ]

    if not target_files:
        print(f"没有找到匹配的非标准存储文件")
        return

    print(f"找到 {len(target_files)} 个非标准存储文件匹配模式 '{pattern}':")
    for i, file_info in enumerate(target_files, 1):
        print(f"{i}. {file_info['key']} ({get_storage_class_name(file_info['type'])})")

    confirm = input(f"\n确认要将这些文件修改为标准存储吗？(输入yes继续): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    success_count = 0
    for i, file_info in enumerate(target_files, 1):
        print(f"处理文件 ({i}/{len(target_files)}): {file_info['key']}")

        if change_storage_class(auth, file_info['key'], STORAGE_CLASS_STANDARD):
            success_count += 1
            print(f"✓ 修改成功")
        else:
            print(f"✗ 修改失败")

        time.sleep(0.5)

    print(f"\n操作完成！成功修改 {success_count}/{len(target_files)} 个文件")


if __name__ == "__main__":
    print("请选择操作模式:")
    print("1. 模糊查询并解冻多个文件，然后修改为标准存储")
    print("2. 解冻特定文件并修改为标准存储")
    print("3. 批量修改已解冻文件的存储类型为标准存储")

    choice = input("请输入选择 (1, 2 或 3): ").strip()

    if choice == '1':
        restore_and_change_storage_by_pattern()
    elif choice == '2':
        restore_and_change_specific_file()
    elif choice == '3':
        batch_change_existing_files()
    else:
        print("无效的选择")

#影视美学
#保险学
#成本管理会计