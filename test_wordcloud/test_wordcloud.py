import wordcloud

f = open('十四五.txt', encoding='utf-8')
txt = f.read()

w = wordcloud.WordCloud(width=1000,
                            height=700,
                            background_color='white',
                            font_path='/System/Library/fonts/PingFang.ttc'
                            )
w.generate(txt)
w.to_file('output3-sentence1.png')
