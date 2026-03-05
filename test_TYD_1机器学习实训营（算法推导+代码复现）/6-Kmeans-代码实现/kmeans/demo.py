import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from k_means import KMeans



data = pd.read_csv('../data/iris.csv')
iris_types = ['SETOSA','VERSICOLOR','VIRGINICA']

x_axis = 'petal_length'
y_axis = 'petal_width'

plt.figure(figsize=(12,5))
plt.subplot(1,2,1)
for iris_type in iris_types:
    plt.scatter(data[x_axis][data['class']==iris_type],data[y_axis][data['class']==iris_type],label = iris_type)
plt.title('label known')
plt.legend()

plt.subplot(1,2,2)
plt.scatter(data[x_axis][:],data[y_axis][:])
plt.title('label unknown')
plt.show()

num_examples = data.shape[0]
# .reshape(num_examples, 2)
# 将数据明确地转换为 num_examples 行、2 列 的二维数组；
# 每一行代表一个样本；
# 每一列是一个特征（如花萼长度和宽度）；
# 备注：虽然data[[x_axis,y_axis]].values已经是 (num_examples, 2) 的结构，但有时会因为某些操作导致数组被“扁平化”或维度变化，使用 .reshape() 是为了确保最终输入给 K-Means 模型的数据格式正确
x_train = data[[x_axis,y_axis]].values.reshape(num_examples,2) #  数据集

#指定好训练所需的参数
num_clusters = 3
max_iteritions = 50

k_means = KMeans(x_train,num_clusters)
centroids,closest_centroids_ids = k_means.train(max_iteritions)

# 对比结果
plt.figure(figsize=(12,5))
plt.subplot(1,2,1)
for iris_type in iris_types:
    plt.scatter(data[x_axis][data['class']==iris_type],data[y_axis][data['class']==iris_type],label = iris_type)
plt.title('label known')
plt.legend()

plt.subplot(1,2,2)
for centroid_id, centroid in enumerate(centroids):
    current_examples_index = (closest_centroids_ids == centroid_id).flatten()
    # data[x_axis][current_examples_index]意思是：从 data 中取出列名是 x_axis 的那一列数据，并根据 current_examples_index 筛选出特定样本的数据。
    # current_examples_index是类似[True, False, True, False, ...]的布尔数组
    plt.scatter(data[x_axis][current_examples_index],data[y_axis][current_examples_index],label = centroid_id)

for centroid_id, centroid in enumerate(centroids):
    plt.scatter(centroid[0],centroid[1],c='red',marker = 'x')
plt.legend()    
plt.title('label kmeans')
plt.show()


