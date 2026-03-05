# 定义文档读取方法
def getText():
    txt = open('data/哈姆雷特.txt','r').read()
    txt = txt.lower()    #将所有文本中的英文全部换为小写字母
    for ch in '!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~':
        txt = txt.replace(ch, ' ')  #将文本中的特殊字符替换为空格
    return txt

# 读取文档
hamletTxt = getText()

# 分割文档
words = hamletTxt.split()

# 统计
counts = {}
for word in words:
    counts[word] = counts.get(word,0) + 1

# 转程list列表
items = list(counts.items())

# 进行排序
items.sort(key = lambda x:x[1], reverse = True)

# 输出最高词频的10个单词
for i in range(10):
    word, count = items[i]
    print('{0:<10}{1:>5}'.format(word, count))
