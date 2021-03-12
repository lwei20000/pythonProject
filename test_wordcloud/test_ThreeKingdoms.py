import jieba

content = open('data/三国演义.txt', 'r', encoding='utf-8').read()
words = jieba.lcut(content)  # 分词
excludes = {'将军', '却说', '令人', '赶来', '徐州', '不见', '下马', '喊声', '因此', '未知', '大败', '百姓', '大事', '一军', '之后', '接应', '起兵', '成都',
            '原来', '江东', '正是', '忽然', '原来', '大叫', '上马', '天子', '一面', '太守', '不如', '忽报', '后人', '背后', '先主', '此人', '城中', '然后',
            '大军', '何不', '先生', '何故', '夫人', '不如', '先锋', '二人', '不可', '如何', '荆州', '不能', '如此', '主公', '军士', '商议', '引兵', '次日',
            '大喜', '魏兵', '军马', '于是', '东吴', '今日', '左右', '天下', '不敢', '陛下', '人马', '不知', '都督', '汉中', '一人', '众将', '后主', '只见',
            '蜀兵'}  # 排除的词汇
counts = {}
for word in words:
    if len(word) == 1:  # 排除单个字符的分词结果
        continue
    elif word == '孔明' or word == '孔明曰':
        real_word = '诸葛亮'
    elif word == '云长' or word == '关公曰' or word == '关公':
        real_word = '关羽'
    elif word == '玄德' or word == '玄德曰':
        real_word = '刘备'
    elif word == '孟德' or word == '丞相':
        real_word = '曹操'
    else:
        real_word = word
        counts[real_word] = counts.get(real_word, 0) + 1

for word in excludes:
    del (counts[word])

hist = list(counts.items())  # [(key:value),(key:value)]
hist.sort(key=lambda x: x[1], reverse=True)

for i in range(15):
    print("{:<8}{:>5}".format(hist[i][0], hist[i][1]))