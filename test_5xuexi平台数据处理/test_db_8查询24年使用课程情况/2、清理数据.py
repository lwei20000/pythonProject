import pandas as pd
import re

# 读取Excel文件
df = pd.read_excel('统计.xlsx', header=None)

# 创建两个空列表来存储处理后的数据
cleaned_courses = []
row_counts = []

# 处理每一行数据
for item in df.iloc[:, 0]:
    # 使用正则表达式分割课程名和行数
    match = re.match(r'(.+?)\s*-\s*(\d+)行', str(item))

    if match:
        course_name = match.group(1)
        row_count = match.group(2)

        # 去掉课程名中的数字和英文字母
        cleaned_name = re.sub(r'[a-zA-Z0-9_]', '', course_name)

        cleaned_courses.append(cleaned_name)
        row_counts.append(row_count)
    else:
        # 如果格式不匹配，保留原值
        cleaned_courses.append(str(item))
        row_counts.append('')

# 创建新的DataFrame
result_df = pd.DataFrame({
    '课程名': cleaned_courses,
    '行数': row_counts
})

# 保存到新的Excel文件
result_df.to_excel('统计_处理结果.xlsx', index=False)

print("处理完成！结果已保存到 统计_处理结果.xlsx")