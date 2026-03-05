import pandas as pd
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


# 加载Excel文件
def load_excel_file(file_path):
    """加载Excel文件中的URL列表"""
    try:
        df = pd.read_excel(file_path)
        return df['文件URL'].tolist()
    except Exception as e:
        print(f"加载Excel文件失败: {e}")
        return []


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

        files.extend([item['key'] for item in ret.get('items', [])])

        marker = ret.get('marker')
        if eof or not marker:
            break

    return files


# 移动文件到深度归档存储
def move_to_deep_archive(auth, file_key):
    """将文件移动到深度归档存储(类型3)"""
    try:
        # 使用七牛API修改存储类型
        entry = f"{qiniu_config['bucket_name']}:{file_key}"
        encoded_entry = qiniu.urlsafe_base64_encode(entry)
        url = f"http://rs.qiniu.com/chtype/{encoded_entry}/type/3"

        # 生成管理token
        access_token = auth.token_of_request(url)
        headers = {"Authorization": "QBox " + access_token}

        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f"移动文件失败: {file_key} - {response.text}")
            return False
    except Exception as e:
        print(f"移动文件时出错: {file_key} - {str(e)}")
        return False


def process_files():
    """处理文件移动任务"""
    # 1. 加载Excel文件中的URL
    excel_file = 'major_courseware_report.xlsx'
    excel_urls = load_excel_file(excel_file)
    if not excel_urls:
        print("Excel文件中没有找到URL数据")
        return

    # 提取URL中的文件名作为基准
    base_files = set()
    for url in excel_urls:
        if pd.notna(url) and isinstance(url, str):
            parsed = urlparse(url)
            base_files.add(parsed.path.lstrip('/'))

    print(f"Excel中找到 {len(base_files)} 个基准文件")

    # 2. 初始化七牛云认证
    auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])

    # 3. 获取七牛云空间中的所有文件
    qiniu_files = get_qiniu_files(auth)
    print(f"七牛云空间中找到 {len(qiniu_files)} 个文件")

    # 4. 找出需要移动的文件
    files_to_move = [f for f in qiniu_files if f not in base_files]
    print(f"需要移动到深度归档的文件数量: {len(files_to_move)}")

    if not files_to_move:
        print("没有需要移动的文件")
        return

    # 5. 确认操作
    confirm = input(f"确认要将 {len(files_to_move)} 个文件移动到深度归档存储吗？(输入yes继续): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        return

    # 6. 执行移动操作
    success_count = 0
    for i, file_key in enumerate(files_to_move, 1):
        if move_to_deep_archive(auth, file_key):
            success_count += 1
            print(f"成功移动: {file_key} ({i}/{len(files_to_move)})", end='\r')
        time.sleep(0.2)  # 避免请求过于频繁

    print(f"\n移动完成！成功移动 {success_count} 个文件到深度归档存储")


if __name__ == "__main__":
    process_files()