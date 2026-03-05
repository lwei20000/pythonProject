import numpy as np

class KMeans:
    def __init__(self,data,num_clustres):
        self.data = data
        self.num_clustres = num_clustres
        
    def train(self,max_iterations):
        #1.先随机选择K个中心点
        centroids = KMeans.centroids_init(self.data,self.num_clustres)
        #2.开始训练
        num_examples = self.data.shape[0]
        closest_centroids_ids = np.empty((num_examples,1))
        for _ in range(max_iterations):
            #3得到当前每一个样本点到K个中心点的距离，找到最近的
            closest_centroids_ids = KMeans.centroids_find_closest(self.data,centroids)
            #4.进行中心点位置更新
            centroids = KMeans.centroids_compute(self.data,closest_centroids_ids,self.num_clustres)
        return centroids,closest_centroids_ids
                
    @staticmethod    
    def centroids_init(data,num_clustres):
        num_examples = data.shape[0]
        random_ids = np.random.permutation(num_examples) #对所有数据进行随机排序
        centroids = data[random_ids[:num_clustres],:]  #取前K个数据作为初始中心点
        return centroids #返回K个初始中心点

    @staticmethod 
    def centroids_find_closest(data,centroids):
        num_examples = data.shape[0] #样本总数
        num_centroids = centroids.shape[0] #中心点总数
        closest_centroids_ids = np.zeros((num_examples,1))
        for example_index in range(num_examples):
            distance = np.zeros((num_centroids,1))
            for centroid_index in range(num_centroids):
                distance_diff = data[example_index,:] - centroids[centroid_index,:] #样本向量-中心点向量
                distance[centroid_index] = np.sum(distance_diff**2) #计算距离（欧式距离）
            closest_centroids_ids[example_index] = np.argmin(distance)
        return closest_centroids_ids

    @staticmethod
    def centroids_compute(data,closest_centroids_ids,num_clustres):
        num_features = data.shape[1]
        centroids = np.zeros((num_clustres,num_features)) # 此行意思：每个族一个新中心点，中心点与data维度一样。
        for centroid_id in range(num_clustres):
            # 得到一个布尔数组，表示哪些样本属于当前簇。
            # 例如：[[True], [False], [True]]
            closest_ids = closest_centroids_ids == centroid_id # 得到一个布尔数组，表示哪些样本属于当前簇。
            # .flatten()
            # 把二维布尔数组转换成一维。
            # 例如：[True, False, True]
            # data[closest_ids.flatten(), :]
            # 使用布尔索引提取属于该簇的所有样本。
            # 例如：[[1.0, 2.0], [5.0, 6.0]]
            # np.mean(..., axis=0)
            # 对这些样本在每一列（即每个特征）上取平均值。
            # 返回一个形状为(num_features, )
            # 的向量，作为新的聚类中心。
            centroids[centroid_id] = np.mean(data[closest_ids.flatten(),:],axis=0) # axis=0 表示按列求均值；axis=1 表示按行求均值
        return centroids
                
            
        
        
        