import requests
from qiniu import Auth
from qiniu import BucketManager

# 七牛云配置
qiniu_config = {
    'access_key': '8FEYOjXkSp0UrBV4Uh3lGlEdkCxUh0-xsLVr0bO9',
    'secret_key': 'SG403smIY_rOgDfnBL9CbR0R7ZQQjwUoOpVKbA81'
}


def empty_bucket(bucket_name):
    """清空存储空间中的所有文件"""
    try:
        auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])
        bucket_manager = BucketManager(auth)

        print(f"正在清空存储空间: {bucket_name}")

        # 列举并删除所有文件
        marker = None
        deleted_count = 0
        while True:
            ret, eof, info = bucket_manager.list(bucket_name, marker=marker)
            if ret is None:
                print(f"列举文件失败: {info}")
                break

            # 删除当前批次的文件
            for item in ret.get('items', []):
                key = item['key']
                ret, info = bucket_manager.delete(bucket_name, key)
                if info.status_code == 200:
                    deleted_count += 1
                    print(f"已删除文件: {key} (总计: {deleted_count})")
                else:
                    print(f"删除文件 {key} 失败: {info}")

            marker = ret.get('marker') if ret else None
            if eof or not marker:
                break

        print(f"存储空间 {bucket_name} 已清空，共删除 {deleted_count} 个文件")
        return True

    except Exception as e:
        print(f"清空存储空间时出错: {e}")
        return False


def delete_bucket(bucket_name):
    """使用HTTP API删除指定的七牛云存储空间"""
    try:
        # 初始化Auth对象
        auth = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])

        # 构造请求URL
        url = "http://rs.qiniu.com/drop/" + bucket_name

        # 生成管理token
        access_token = auth.token_of_request(url)

        # 发送请求
        headers = {
            "Authorization": "QBox " + access_token,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(url, headers=headers)

        if response.status_code == 200:
            print(f"成功删除存储空间: {bucket_name}")
            return True
        else:
            print(f"删除存储空间失败: {response.text}")
            return False

    except Exception as e:
        print(f"删除存储空间时出错: {e}")
        return False


if __name__ == "__main__":
    # 指定要删除的bucket名称
    target_bucket = "wisecampus-wait-for-covert "

    # 确认操作
    confirm = input(f"确认要删除存储空间 {target_bucket} 吗？此操作不可恢复！(输入yes继续): ")

    if confirm.lower() == "yes":
        # 先清空空间
        if empty_bucket(target_bucket):
            # 再删除空间
            delete_bucket(target_bucket)
    else:
        print("操作已取消")