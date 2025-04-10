import json
import os, shutil
import pdb

if __name__=="__main__":
    src_tiff_dir = "/Users/liangdas/遥感数据下载/test_dir"
    des_tiff_dir = "/Users/liangdas/遥感数据下载/test_dir_rename"

    lines = os.listdir(src_tiff_dir)
    for line in lines:
        one_folder = os.path.join(src_tiff_dir, line)
        json_path = os.path.join(one_folder, "request.json")
        tiff_path = os.path.join(one_folder, "response.tiff")

        #pdb.set_trace()
        if not os.path.exists(json_path) or not os.path.exists(tiff_path):
            continue
        with open(json_path,'r', encoding='UTF-8') as f:
            json_content = json.load(f)
        if "request" not in json_content.keys():
            continue
        if "url" not in json_content["request"].keys():
            continue
        url = json_content["request"]["url"]
        if "TIME=" not in url:
            continue
        time_part = url.split("TIME=")[-1]
        if "&" not in time_part:
            continue
        #pdb.set_trace()
        time_str = time_part.split("&")[0]
        time_str = time_str.split("%2F")[0]
        time_str = time_str.replace("%3A", "_")

        des_tiff_path = os.path.join(des_tiff_dir, "%s.tiff"%(time_str))
        des_json_path = des_tiff_path.replace(".tiff", ".json")
        shutil.copy(tiff_path, des_tiff_path)
        shutil.copy(json_path, des_json_path)












