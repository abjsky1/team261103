import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm

pd.set_option('display.unicode.east_asian_width', True)

# 기온 데이터 불러오기
df_temp = pd.read_csv('./temperature_data/전국월별_기온.csv',
                 encoding='cp949',   # 한국어 인코딩으로 읽기
                 skiprows=7)         # 앞의 설명 7줄 건너뛰기
print(df_temp.head())
print(df_temp.tail())
df_temp.info()

# 1. 기온 데이터가 비어있는 결측치 행(1건) 제거
df_temp = df_temp.dropna(subset=['평균기온(℃)'])

# 2. '월-연도(1-24)' 문자열을 날짜 타입(2024-01-01)으로 변환
df_temp['년월'] = pd.to_datetime(df_temp['년월'].str.strip(), format='%m-%y').dt.to_period('M')

# 3. 결과 확인
print(df_temp.head())
print(df_temp.tail())
df_temp.info()