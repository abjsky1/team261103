# 가설: 감기 환자 수의 변화는 기온보다 인플루엔자 유행으로 더 잘 설명될 것이다.
# 유행 지표 1: 인플루엔자 의사환자 분율 (질병관리청 감염병포털, 주별, 외래환자 1,000명당, 잠정통계)
# 유행 지표 2: 인플루엔자 검출률 (질병관리청, 공공데이터포털, 주별, 연령별, 검체 중 양성 비율 %)
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# 엑셀 스타일 관련 불필요한 경고 메시지 숨김
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 그래프 한글 폰트 지정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 1. 기온 데이터 불러오기
df_temp = pd.read_csv('./temperature_data/전국월별_기온.csv',
                      encoding='cp949',   # 한국어 인코딩으로 읽기
                      skiprows=7)         # 앞의 설명 7줄 건너뛰기
df_temp = df_temp.dropna(subset=['평균기온(℃)'])
df_temp['년월'] = pd.to_datetime(df_temp['년월'].str.strip(), format='%m-%y').dt.to_period('M')
df_temp = df_temp[['년월', '평균기온(℃)']]

# 2. 감기 데이터 불러오기
df_disease = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(감기).xlsx')

# 2번 행을 컬럼 이름으로 쓰고, 3번 행부터 본문 데이터로 사용
df_disease.columns = df_disease.iloc[2]
df_disease = df_disease.iloc[3:].reset_index(drop=True)

# 옆으로 5개 열씩 있는 월별 데이터를 아래로 이어 붙이기
df_list = []
y = 2024
x = 1
for i in range((len(df_disease.columns) - 3) // 5):
    a = 3 + (i * 5)

    df_month = df_disease.iloc[:, [1, 2, a]].copy()
    df_month.columns = ['성별구분', '연령구분10세', '환자수']

    if x < 10:
        df_month['년월'] = f'{y}-0{x}'
    else:
        df_month['년월'] = f'{y}-{x}'
    df_list.append(df_month)

    x += 1
    if x > 12:
        x = 1
        y += 1

df_all = pd.concat(df_list, axis=0, ignore_index=True)
df_all['년월'] = pd.to_datetime(df_all['년월'], format='%Y-%m').dt.to_period('M')
df_all['환자수'] = df_all['환자수'].astype(int)

# 월별 전국 합계 행만 사용
df_cold = df_all[(df_all['성별구분'] == '계') & (df_all['연령구분10세'] == '계')]
df_cold = df_cold[['년월', '환자수']]

# 3. 의사환자 분율 불러오기
df_ili = pd.read_csv('KDH/인플루엔자_주별_의사환자분율.csv')
df_ili['주시작일'] = pd.to_datetime(df_ili['주시작일'])

# 절기는 36주에 시작하므로, 36주 이후는 앞 연도이고 그 전은 뒤 연도
df_ili['년도'] = np.where(df_ili['주차'] >= 36, df_ili['절기'].str[:4], df_ili['절기'].str[5:])
df_ili['년도'] = df_ili['년도'].astype(int)

# 4. 검출률 불러오기
df_detect = pd.read_csv('KDH/질병관리청_인플루엔자 주별 연령별 검출률_20251228.csv', encoding='utf-8-sig')

# 파일에 전체 값이 없으므로 6개 연령대의 단순 평균을 사용
df_detect = df_detect.groupby(['년도', '주'], as_index=False)['검출률'].mean()
df_detect = df_detect.rename(columns={'주': '주차'})

# 5. 같은 연도, 같은 주차끼리 합치기
df_week = pd.merge(df_ili, df_detect, on=['년도', '주차'], how='left')

# 주 시작일이 속한 달로 묶어서 월평균 구하기
df_week['년월'] = df_week['주시작일'].dt.to_period('M')
df_flu = df_week.groupby('년월', as_index=False)[['의사환자분율', '검출률']].mean()

# 6. 년월 기준으로 합치기
merged_data = pd.merge(df_cold, df_temp, on='년월', how='inner')
merged_data = pd.merge(merged_data, df_flu, on='년월', how='inner')
merged_data = merged_data.sort_values('년월').reset_index(drop=True)

# 검출률이 있는 24개월만 따로 저장
detect_data = merged_data.dropna(subset=['검출률']).reset_index(drop=True)

print(f"의사환자 분율 기간: {merged_data['년월'].min()} ~ {merged_data['년월'].max()} ({len(merged_data)}개월)")
print(f"검출률 기간: {detect_data['년월'].min()} ~ {detect_data['년월'].max()} ({len(detect_data)}개월)")
print(merged_data)

# 7. 의사환자 분율이 실제 검출률과 함께 움직이는지 확인
week_data = df_week.dropna(subset=['검출률'])
print('주별 의사환자 분율과 검출률의 상관계수:', round(week_data['의사환자분율'].corr(week_data['검출률']), 3))
print('월별 의사환자 분율과 검출률의 상관계수:', round(detect_data['의사환자분율'].corr(detect_data['검출률']), 3))

# 8. 상관계수 확인
print('[27개월 상관계수]')
print(merged_data[['환자수', '평균기온(℃)', '의사환자분율']].corr().round(3))
print('[24개월 상관계수]')
print(detect_data[['환자수', '평균기온(℃)', '검출률']].corr().round(3))

# 9. 회귀 모델 비교
# 의사환자 분율 (27개월)
Y = merged_data['환자수']
X1 = merged_data[['평균기온(℃)']]
X2 = merged_data[['의사환자분율']]
X3 = merged_data[['평균기온(℃)', '의사환자분율']]

model1 = LinearRegression()
model1.fit(X1, Y)
model2 = LinearRegression()
model2.fit(X2, Y)
model3 = LinearRegression()
model3.fit(X3, Y)

print('[의사환자 분율 모델, 27개월]')
print('기온만 R²:', round(r2_score(Y, model1.predict(X1)), 3))
print('의사환자 분율만 R²:', round(r2_score(Y, model2.predict(X2)), 3))
print('기온 + 의사환자 분율 R²:', round(r2_score(Y, model3.predict(X3)), 3))

# 검출률 (24개월)
Y = detect_data['환자수']
X1 = detect_data[['평균기온(℃)']]
X2 = detect_data[['검출률']]
X3 = detect_data[['평균기온(℃)', '검출률']]

model1 = LinearRegression()
model1.fit(X1, Y)
model2 = LinearRegression()
model2.fit(X2, Y)
model3 = LinearRegression()
model3.fit(X3, Y)

print('[검출률 모델, 24개월]')
print('기온만 R²:', round(r2_score(Y, model1.predict(X1)), 3))
print('검출률만 R²:', round(r2_score(Y, model2.predict(X2)), 3))
print('기온 + 검출률 R²:', round(r2_score(Y, model3.predict(X3)), 3))

# 10. 기온이 비슷한 달끼리 비교
# 기온 구간을 나눈 뒤, 같은 구간 안에서 유행이 높은 달과 낮은 달의 감기 환자수를 비교
merged_data['기온구간'] = '중간'
merged_data.loc[merged_data['평균기온(℃)'] < 5, '기온구간'] = '낮음'
merged_data.loc[merged_data['평균기온(℃)'] >= 20, '기온구간'] = '높음'

# 구간마다 그 구간의 중앙값을 기준으로 유행 높음, 낮음 나누기
merged_data['구간중앙값'] = merged_data.groupby('기온구간')['의사환자분율'].transform('median')
merged_data['유행구분'] = np.where(merged_data['의사환자분율'] >= merged_data['구간중앙값'], '유행 높음', '유행 낮음')

result = merged_data.groupby(['기온구간', '유행구분'])['환자수'].agg(['count', 'mean'])
print('[기온 구간별 비교, 의사환자 분율 기준]')
print(result.round(0))

# 같은 유행 구분 안에서 기온에 따른 차이도 확인
merged_data['유행기준'] = np.where(merged_data['의사환자분율'] >= merged_data['의사환자분율'].median(), '유행 높음', '유행 낮음')
result2 = merged_data.groupby(['유행기준', '기온구간'])['환자수'].agg(['count', 'mean'])
print('[유행 수준별 비교, 전체 중앙값 기준]')
print(result2.round(0))

# 그래프 1. 월별 변화: 단위가 달라서 그래프를 4개로 나눔
months = merged_data['년월'].astype(str)
fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
axes[0].plot(months, merged_data['환자수'] / 10000, color='#2a78d6', marker='o')
axes[0].set_title('감기 환자수 (만 명)')
axes[1].plot(months, merged_data['평균기온(℃)'], color='#2a78d6', marker='o')
axes[1].set_title('평균기온 (℃)')
axes[2].plot(months, merged_data['의사환자분율'], color='#2a78d6', marker='o')
axes[2].set_title('인플루엔자 의사환자 분율 (외래환자 1,000명당)')
axes[3].plot(months, merged_data['검출률'], color='#2a78d6', marker='o')
axes[3].set_title('인플루엔자 검출률 (%, 연령대 단순 평균, 2025-12까지)')
axes[3].tick_params(axis='x', rotation=90)
plt.tight_layout()
plt.savefig('KDH/kdh3_월별_변화.png')
plt.show()

# 그래프 2. 의사환자 분율과 검출률 비교
plt.figure(figsize=(7, 5))
plt.scatter(week_data['의사환자분율'], week_data['검출률'], color='#2a78d6')
plt.title('주별 의사환자 분율과 검출률')
plt.xlabel('의사환자 분율 (외래환자 1,000명당)')
plt.ylabel('검출률 (%)')
plt.tight_layout()
plt.savefig('KDH/kdh3_의사환자분율_검출률.png')
plt.show()

# 그래프 3. 기온 구간별 유행 높음, 낮음 비교
chart = result['mean'].unstack() / 10000
chart = chart.loc[['낮음', '중간', '높음'], ['유행 낮음', '유행 높음']]
chart.plot(kind='bar', figsize=(8, 5), color=['#2a78d6', '#eb6834'], rot=0)
plt.title('기온이 비슷한 달끼리 비교한 월평균 감기 환자수')
plt.xlabel('기온 구간 (낮음: 5℃ 미만, 높음: 20℃ 이상)')
plt.ylabel('월평균 감기 환자수 (만 명)')
plt.legend(title='')
plt.tight_layout()
plt.savefig('KDH/kdh3_기온구간별_비교.png')
plt.show()
