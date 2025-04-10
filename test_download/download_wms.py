from sentinelhub import CRS, BBox, MimeType, SentinelHubRequest, SHConfig, DataCollection, MimeType, WcsRequest, WmsRequest
from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    DownloadRequest,
    MimeType,
    MosaickingOrder,
    SentinelHubDownloadClient,
    SentinelHubRequest,
    bbox_to_dimensions,
)
import cv2
import os

#from utils import plot_image
import pdb

#https://sentinelhub-py.readthedocs.io/en/latest/examples/ogc_request.html
#https://forum.sentinel-hub.com/t/using-wms-request-to-get-tiff-but-failed/1221


# Write your credentials here if you haven't already put them into config.toml
CLIENT_ID = 'd395855d-f2cd-418e-91e5-b37c4a14da77'
CLIENT_SECRET = '(fI#-Nn0g7TkP0HQ7nUWlt_8|CdY[LOsqqte_jC?'

config = SHConfig()
if CLIENT_ID and CLIENT_SECRET:
    config.sh_client_id = CLIENT_ID
    config.sh_client_secret = CLIENT_SECRET
if config.instance_id == "":
    print("Warning! To use OGC functionality of Sentinel Hub, please configure the `instance_id`.")
    config.instance_id = "1e913aa2-e9ed-41c0-b4b5-c22b25aa9f1a"

xmin, ymin, xmax, ymax = 114.412778-0.025, 37.531389-0.025,114.412778+0.025,37.531389+0.025
betsiboka_coords_wgs84 = (xmin, ymin, xmax, ymax)
#betsiboka_coords_wgs84 = (46.16, -16.15, 46.51, -15.58)
resolution = 1
#pdb.set_trace()
betsiboka_bbox = BBox(bbox=betsiboka_coords_wgs84, crs=CRS.WGS84)
betsiboka_size = bbox_to_dimensions(betsiboka_bbox, resolution=resolution)
max_len = max(betsiboka_size[0], betsiboka_size[1])
ratio = 2500/max_len
betsiboka_size = (int(betsiboka_size[0]*ratio), int(betsiboka_size[1]*ratio))

#time_interval = ('2016-01-01', '2023-07-01')
time_interval = ('2016-01-01', '2023-07-01')  # 时间范围



wms_bands_request = WmsRequest(
    data_folder="test_dir",
    data_collection=DataCollection.SENTINEL2_L1C,
    layer="MYSELF_B2348",
    bbox=betsiboka_bbox,
    time=time_interval,
    width=betsiboka_size[0],
    height=betsiboka_size[1],
    config=config,
    image_format=MimeType.TIFF,

    #responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
)

#pdb.set_trace()
wms_bands_request.save_data()

#import tifffile as tf
#path = "/Users/liangdas/遥感数据下载/test_dir/1b62fcdaa42e7fd4f5e767aaaa6b7ddf/response.tiff"
#img_tf = tf.imread(path)
#img_tf.shape

#wms_true_color_img = wms_bands_request.get_data()
#cv2.imwrite('color_img.jpg', wms_true_color_img[-1])
#pdb.set_trace()