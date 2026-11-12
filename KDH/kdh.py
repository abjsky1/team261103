import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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

# 전국 수증기압, 상대습도 파일
data = pd.read_csv('KDH\\OBS_ASOS_MNH_20261104175908.csv')

# 일시별로 전부 평균값으로 새 데이터 생성
global_data = data.groupby('일시', as_index=False).agg(
    전국평균수증기압=('평균수증기압(hPa)', 'mean'),
    전국평균상대습도=('평균상대습도(%)', 'mean')
)
global_data['일시'] = pd.to_datetime(global_data['일시'].str.strip(), format='%Y-%m').dt.to_period('M')
df_temp = pd.read_csv('./temperature_data/전국월별_기온.csv',
                 encoding='cp949',   # 한국어 인코딩으로 읽기
                 skiprows=7)         # 앞의 설명 7줄 건너뛰기
df_temp['년월'] = pd.to_datetime(df_temp['년월'].str.strip(), format='%m-%y').dt.to_period('M')
df = df_temp[['년월', '평균기온(℃)']]

df = df.rename(columns={'년월':'일시'})
# AH = (216.7 * e) / (T + 273.15) , 이 때 e는 수증기압 , T는 기온
merged_data = pd.merge(global_data, df, on='일시', how='inner')
merged_data['전국평균절대습도'] = merged_data['전국평균수증기압'] * 216.7 / (merged_data['평균기온(℃)'] + 273.15)
print(merged_data)

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# 월별 전국 합계 행만 사용
df_total = df_disease[(df_disease['성별구분'] == '계') & (df_disease['연령구분10세'] == '계')]
df_total = df_total[['년월', '환자수']].rename(columns={'년월': '일시'})
df_total['환자수'] = df_total['환자수'].astype(int)   # 현재 object 타입이라 변환 필요

merged_data = pd.merge(merged_data, df_total, on='일시', how='inner')

X1 = merged_data[['평균기온(℃)']]
X2 = merged_data[['전국평균절대습도']]
X3 = merged_data[['평균기온(℃)', '전국평균절대습도']]
Y = merged_data['환자수']

model1 = LinearRegression()
model1.fit(X1, Y)
model1_pred = model1.predict(X1)
model2 = LinearRegression()
model2.fit(X2, Y)
model2_pred = model2.predict(X2)
model3 = LinearRegression()
model3.fit(X3, Y)
model3_pred = model3.predict(X3)

print("평균기온모델 ", r2_score(Y, model1_pred))
print("평균절대습도 ", r2_score(Y, model2_pred))
print("평균기온 + 평균절대습도 ", r2_score(Y, model3_pred))


# 상관계수 확인
print(merged_data[['평균기온(℃)', '전국평균절대습도', '전국평균상대습도', '환자수']].corr())

# 기온, 상대습도를 중앙값 기준으로 나누기
temp_median = merged_data['평균기온(℃)'].median()
humid_median = merged_data['전국평균상대습도'].median()
merged_data['기온구분'] = np.where(merged_data['평균기온(℃)'] < temp_median, '추움', '더움')
merged_data['습도구분'] = np.where(merged_data['전국평균상대습도'] < humid_median, '건조', '습함')

# 조건별 개월 수와 월평균 환자수
result = merged_data.groupby(['기온구분', '습도구분'])['환자수'].agg(['count', 'mean'])
print(result)

increase = (result.loc[('추움', '건조'), 'mean'] / result.loc[('더움', '습함'), 'mean'] - 1) * 100
print(f"춥고 건조한 달이 덥고 습한 달보다 환자가 {increase:.1f}% 많음")

# 그래프 (한글 폰트 지정)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 1. 월별 변화: 단위가 달라서 그래프를 3개로 나눔
months = merged_data['일시'].astype(str)
fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
axes[0].plot(months, merged_data['환자수'], marker='o')
axes[0].set_title('감기 환자수 (명)')
axes[1].plot(months, merged_data['평균기온(℃)'], marker='o')
axes[1].set_title('평균기온 (℃)')
axes[2].plot(months, merged_data['전국평균절대습도'], marker='o')
axes[2].set_title('절대습도 (g/m³)')
axes[2].tick_params(axis='x', rotation=90)
plt.tight_layout()
plt.savefig('KDH/월별_환자수_기온_절대습도.png')
plt.show()

# 2. 조건별 월평균 환자수
order = [('추움', '건조'), ('추움', '습함'), ('더움', '건조'), ('더움', '습함')]
labels = ['춥고 건조', '춥고 습함', '덥고 건조', '덥고 습함']
plt.figure(figsize=(8, 5))
plt.bar(labels, result.loc[order, 'mean'])
plt.title('기상 조건별 월평균 감기 환자수')
plt.ylabel('월평균 환자수 (명)')
plt.tight_layout()
plt.savefig('KDH/기상조건별_환자수.png')
plt.show()


