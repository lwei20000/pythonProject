import folium
from folium import Marker
location_center = [29.554086685,106.53260803222223]

location_center_temp = [29.554086685,106.53260803222223]

m_1 = folium.Map(location=location_center_temp,
                 tiles='openstreetmap',
                 zoom_start=15,
                 attr='同济大学张子豪',
                 control_scale=True)

# 增加拾取经纬度控件
m_1.add_child(folium.LatLngPopup())

# 在地图上画标记
folium.Marker(
    location=location_center,
    popup='拍照点',
    icon=folium.Icon(color='blue',icon='fa-camera',prefix='fa') # 标记logo，可以从https://fontawesome.com/中跳选
).add_to(m_1)

# 在地图上添加另一个标记
# folium.Marker(
#     location=[31.27861,121.36038],
#     popup='上海地铁十一号线',
#     icon=folium.Icon(color='green',icon='fa-train',prefix='fa')
# ).add_to(m_1)

# 将地图导出为html文件
m_1.save('output/00-重庆.png')

# 展示地图
m_1
