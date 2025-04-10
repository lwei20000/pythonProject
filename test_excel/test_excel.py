import pandas as pd

df = pd.read_excel("未来宝_信息收集页面_20211109165438.xlsx")

print("获取到所有的值:\n{0}".format(df)) #格式化输出

df = df.drop_duplicates(subset=['组织机构代码/三证合一码'], keep='last', inplace=False)

print("获取到所有的值:\n{0}".format(df)) #格式化输出

df.to_excel('去重文件.xlsx')

