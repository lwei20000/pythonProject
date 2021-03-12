import jieba
import wordcloud

w = wordcloud.WordCloud(width=1000,
                      height=700,
                      background_color='white',
                      font_path='/System/Library/fonts/PingFang.ttc'
                      )
txt='同济大学（tongji university）,简称"同济"，是中华人民共和国教育部直属院校'
txtlist = jieba.lcut(txt)
string = "".join(txtlist)

w.generate(string)

w.to_file('output4-tongji.png')
