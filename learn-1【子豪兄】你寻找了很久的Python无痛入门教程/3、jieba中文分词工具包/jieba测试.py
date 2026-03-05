import jieba

jieba.add_word('科学院大学')
jieba.lcut('中国科学院大学的学生', cut_all=True)