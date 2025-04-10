import numpy as np

# 第2、3两行换位置
a=np.arange(25).reshape(5,5)
a[[1,2],:] = a[[2,1],:]
print("第2、3两行换位置\n",a)

# 第3、4两列换位置
a=np.arange(25).reshape(5,5)
a[:,[3,4]] = a[:,[4,3]]
print("第3、4两列换位置\n",a)

# 奇数=-1
a=np.arange(25).reshape(5,5)
a[a % 2 == 1] = -1
print("奇数=-1\n",a)

# 对角线=0
a=np.arange(25).reshape(5,5)
i=[0,1,2,3,4]
a[i,i] = 0
print("对角线=0\n",a)



a=np.tile(np.arange(5),(5,1))
print("每行数字都是0～4的5*5矩阵--顺序\n",a)

a=np.random.randint(0,5,size=(5,5))
print("每行数字都是0～4的5*5矩阵--乱序\n",a)






