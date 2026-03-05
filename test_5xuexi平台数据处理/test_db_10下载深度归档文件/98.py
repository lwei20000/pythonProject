import requests
import os
from qiniu import Auth


def download_qiniu_video(qiniu_config, file_key, local_path=None):
    """
    下载七牛云存储中的视频文件

    Args:
        qiniu_config: 七牛云配置字典
        file_key: 文件在七牛云中的key
        local_path: 本地保存路径，默认为当前目录
    """
    # 创建七牛云认证对象
    q = Auth(qiniu_config['access_key'], qiniu_config['secret_key'])

    # 构建下载URL
    base_url = f"http://{qiniu_config.get('cdn_domain', 'vod.5xuexi.com')}/{file_key}"

    # 生成私有下载链接（有效期3600秒）
    private_url = q.private_download_url(base_url, expires=3600)

    # 设置本地保存路径
    if local_path is None:
        local_path = os.path.basename(file_key)

    try:
        # 下载文件
        response = requests.get(private_url, stream=True)
        response.raise_for_status()

        # 获取文件总大小
        total_size = int(response.headers.get('content-length', 0))

        # 写入文件
        with open(local_path, 'wb') as f:
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    # 显示下载进度
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\r下载进度: {progress:.1f}% ({downloaded_size}/{total_size} bytes)", end='')

        print(f"\n文件下载完成: {local_path}")
        return True

    except Exception as e:
        print(f"下载失败: {e}")
        return False


if __name__ == "__main__":
    # 七牛云配置（请使用重置后的新密钥）
    qiniu_config = {
        'access_key': 'YOUR_NEW_ACCESS_KEY',  # 请替换为重置后的access_key
        'secret_key': 'YOUR_NEW_SECRET_KEY',  # 请替换为重置后的secret_key
        'bucket_name': '5xuexi',
        'cdn_domain': 'vod.5xuexi.com'
    }

    # 要下载的文件key
    file_key = "downloads/3DMAX环境艺术设计_02第一章_01第1节.mp4"

    # 执行下载
    download_qiniu_video(qiniu_config, file_key)