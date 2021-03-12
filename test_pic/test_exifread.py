# !pip install exifread pillow folium

import exifread
f = open('data/cq.jpg','rb')
tags = exifread.process_file(f)

Latitude_list = tags['GPS GPSLatitude'].printable[1:-1].replace(', ',',').split(',')
Latitude = eval(Latitude_list[0]) + eval(Latitude_list[1])/60 + eval(Latitude_list[2])/3600
Longitude_list = tags['GPS GPSLongitude'].printable[1:-1].replace(', ',',').split(',')
Longitude = eval(Longitude_list[0]) + eval(Longitude_list[1])/60 + eval(Longitude_list[2])/3600
print('纬度，经度：')
print(str(Latitude) + ',' + str(Longitude))

#打印照片其中一些信息
print('拍摄时间:', tags['EXIF DateTimeOriginal'])
print('照相机制造商：', tags['Image Make'])
print('照相机型号：', tags['Image Model'])
print('照片尺寸：', tags['EXIF ExifImageWidth'], tags['EXIF ExifImageLength'])
