import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm

pd.set_option('display.unicode.east_asian_width', True)

df = pd.read_csv('./temperature_data/전국월별_기온.csv',
                 encoding='cp949',   # 한국어 인코딩으로 읽기
                 skiprows=7)         # 앞의 설명 7줄 건너뛰기
print(df.head())

df['날짜'] = df['날짜'].str.strip()
df['날짜'] = pd.to_datetime(df['날짜'])

print(df.head())
df.info()