# 《三国演义》是古代汉语，对于现代汉语的统计看下面的例子

# 导入jieba第三方库
import jieba

# 导入外部文件
f=open("data/关于实施乡村振兴战略的意见.txt","r",encoding='utf-8')

# 读取文件并通过jieba分词
txt=f.read()
words=jieba.lcut(txt)

# 新建映射字典counts
counts={}
for word in words:
    # 这里是限制词语长度
    if len(word) == 4:
        counts[word]=counts.get(word,0)+1

# 转换成列表
items=list(counts.items())

#词频按降序排序
items.sort(key=lambda x:x[1],reverse=True)

#打印输出排名前15的词语
for i in range(15):
    word,count=items[i]
    print("{0:<10}{1:>5}".format(word,count))