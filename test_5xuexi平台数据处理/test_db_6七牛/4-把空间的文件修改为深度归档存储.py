import qiniu
from qiniu import Auth, BucketManager
import time
import requests

# 七牛云配置
qiniu_config = {
    'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
    'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81'
}

def change_to_deep_archive(auth, bucket_name):
    """将存储空间中所有文件修改为深度归档存储(类型3)"""
    try:
        bucket_manager = BucketManager(auth)
        changed_count = 0
        skipped_count = 0
        failed_count = 0
        marker = None

        print(f"开始处理存储空间: {bucket_name}")
        print("目标存储类型: 深度归档存储(类型3)")

        while True:
            # 列举文件
            ret, eof, info = bucket_manager.list(bucket_name, marker=marker)
            if ret is None:
                print(f"列举文件失败: {info}")
                break

            items = ret.get('items', [])
            print(f"找到 {len(items)} 个文件，处理中...")

            for item in items:
                key = item['key']
                current_type = item.get('type', 0)

                # 如果已经是深度归档存储则跳过
                if current_type == 3:  # 3表示深度归档存储
                    skipped_count += 1
                    continue

                # 使用七牛的低阶API直接发送修改请求
                entry = f"{bucket_name}:{key}"
                encoded_entry = qiniu.urlsafe_base64_encode(entry)
                url = f"http://rs.qiniu.com/chtype/{encoded_entry}/type/3"  # 使用类型3

                # 生成管理token
                access_token = auth.token_of_request(url)
                headers = {"Authorization": "QBox " + access_token}

                try:
                    response = requests.post(url, headers=headers)
                    if response.status_code == 200:
                        changed_count += 1
                        print(f"成功修改: {key} (总计: {changed_count})", end='\r')
                    else:
                        failed_count += 1
                        print(f"修改失败: {key} - {response.text}")
                except Exception as e:
                    failed_count += 1
                    print(f"请求异常: {key} - {str(e)}")

                # 避免请求过于频繁
                time.sleep(0.2)

            marker = ret.get('marker')
            if eof or not marker:
                break

        print("\n处理完成！")
        print(f"总文件数: {changed_count + skipped_count + failed_count}")
        print(f"成功修改为深度归档存储: {changed_count}")
        print(f"已为深度归档存储跳过: {skipped_count}")
        print(f"修改失败: {failed_count}")

    except Exception as e:
        print(f"处理过程中出错: {e}")


if __name__ == "__main__":
    # 初始化Auth对象
    auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])

    # 指定要修改的bucket名称
    target_bucket = "jj-edu"

    # 确认操作
    confirm = input(f"确认要修改存储空间 {target_bucket} 中所有文件的存储类型为深度归档存储吗？(输入yes继续): ")

    if confirm.lower() == "yes":
        change_to_deep_archive(auth, target_bucket)
    else:
        print("操作已取消")