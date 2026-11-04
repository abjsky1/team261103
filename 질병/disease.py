# 판다스에서 .xlsx 파일을 읽으려면 전용 엔진인 openpyxl이 추가로 설치
# pip install openpyxl

import warnings
import pandas as pd

# 질병 데이터 불러오기
# 엑셀 스타일 관련 불필요한 경고 메시지 숨김
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 1. 질병 데이터 불러오기
df_disease = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(감기).xlsx')

print(df_disease.head())
print(df_disease.tail())
df_disease.info()

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_disease.columns = df_disease.iloc[2]
print(df_disease.head())
print(df_disease.tail())
df_disease.info()

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_disease = df_disease.iloc[3:].reset_index(drop=True)
print(df_disease.head())
print(df_disease.tail())
df_disease.info()

df_list = []
y = 2024
x = 1
for i in range( ( len(df_disease.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_disease.iloc[:, a:b]
    df_temp = pd.concat([df_disease.iloc[:, 0:3], df_month], axis=1)
    df_temp['년월'] = f'{y}-{x}'
    df_list.append(df_temp)

    x = int(x)
    x += 1

df_disease = pd.concat(df_list, axis=0, ignore_index=True)

print(df_disease.head())
print(df_disease.tail())
df_disease.info()

df_disease['년월'] = pd.to_datetime(df_disease['년월'].str.strip(), format='%Y-%m').dt.to_period('M')

print(df_disease.head())
print(df_disease.tail())
df_disease.info()