# 가설: 감기 환자 수의 변화는 기온보다 인플루엔자 유행으로 더 잘 설명될 것이다.
# 유행 지표 1: 인플루엔자 의사환자 분율 (질병관리청 감염병포털, 주별, 외래환자 1,000명당, 잠정통계)
# 유행 지표 2: 인플루엔자 검출률 (질병관리청, 공공데이터포털, 주별, 연령별, 검체 중 양성 비율 %)
#             의사환자 분율은 증상 기준의 추정치이므로, 실제 검체 결과인 검출률로 함께 확인한다.
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.linear_model import LinearRegression

# 엑셀 스타일 관련 불필요한 경고 메시지 숨김
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 그래프 한글 폰트 지정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

BLUE = '#2a78d6'

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
    df_month['년월'] = f'{y}-{x:02d}'
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


# 한 주가 두 달에 걸칠 수 있으므로, 주별 값을 7일로 펼친 뒤 달별로 평균 내기
def weekly_to_monthly(df, col):
    df_days = df.loc[df.index.repeat(7)].copy()
    df_days['날짜'] = df_days['주시작일'] + pd.to_timedelta(df_days.groupby(level=0).cumcount(), unit='D')
    df_days['년월'] = df_days['날짜'].dt.to_period('M')
    return df_days.groupby('년월', as_index=False)[col].mean()


# 3. 의사환자 분율 불러오기
df_ili = pd.read_csv('KDH/인플루엔자_주별_의사환자분율.csv')
df_ili['주시작일'] = pd.to_datetime(df_ili['주시작일'])
df_ili_month = weekly_to_monthly(df_ili, '의사환자분율')

# 4. 검출률 불러오기
df_detect = pd.read_csv('KDH/질병관리청_인플루엔자 주별 연령별 검출률_20251228.csv', encoding='utf-8-sig')

# 파일에 전체 값이 없으므로 6개 연령대의 단순 평균을 사용
df_detect = df_detect.groupby(['년도', '주'], as_index=False)['검출률'].mean()

# 의사환자 분율과 같은 주차 달력으로 주 시작일 만들기 (일요일 시작)
first_week = {2024: '2023-12-31', 2025: '2024-12-29'}
df_detect = df_detect[df_detect['년도'].isin(first_week)].reset_index(drop=True)
df_detect['주시작일'] = (pd.to_datetime(df_detect['년도'].map(first_week))
                     + pd.to_timedelta((df_detect['주'] - 1) * 7, unit='D'))
df_detect_month = weekly_to_monthly(df_detect, '검출률')

# 5. 데이터를 년월 기준으로 합치기
merged_data = pd.merge(df_cold, df_temp, on='년월', how='inner')
merged_data = pd.merge(merged_data, df_ili_month, on='년월', how='inner')
merged_data = pd.merge(merged_data, df_detect_month, on='년월', how='left')
merged_data = merged_data.sort_values('년월').reset_index(drop=True)

# 검출률이 있는 24개월만 따로 저장
detect_data = merged_data.dropna(subset=['검출률']).reset_index(drop=True)

print(f"전체 기간: {merged_data['년월'].min()} ~ {merged_data['년월'].max()} ({len(merged_data)}개월)")
print(f"검출률 기간: {detect_data['년월'].min()} ~ {detect_data['년월'].max()} ({len(detect_data)}개월)")
print(merged_data)


# 6. 분석에 쓸 함수
def show_corr(data, col):
    r, p = stats.pearsonr(data[col], data['환자수'])
    print(f"{col}과 감기: r={r:.3f}, p={p:.4f}")
    return r


def adj_r2(data, cols):
    X = data[cols]
    model = LinearRegression()
    model.fit(X, data['환자수'])
    r2 = model.score(X, data['환자수'])
    n = len(data)
    adj = 1 - (1 - r2) * (n - 1) / (n - len(cols) - 1)
    print(f"{' + '.join(cols)}: R²={r2:.3f}, 수정 R²={adj:.3f}")
    return adj


def residual(data, target, control):
    X = data[[control]]
    model = LinearRegression()
    model.fit(X, data[target])
    return data[target] - model.predict(X)


# 편상관: 한 변수의 영향을 뺀 뒤 남은 관계 확인
def show_partial(data, col, control):
    r = np.corrcoef(residual(data, col, control), residual(data, '환자수', control))[0, 1]
    n = len(data)
    t = r * np.sqrt((n - 3) / (1 - r ** 2))
    p = 2 * stats.t.sf(abs(t), n - 3)
    print(f"{control}을 통제한 {col}과 감기: r={r:.3f}, p={p:.4f}")


TEMP = '평균기온(℃)'
ILI = '의사환자분율'
DETECT = '검출률'

# 7. 의사환자 분율을 믿을 수 있는지 확인: 실제 검출률과 함께 움직이는가
print('\n[의사환자 분율과 검출률 비교]')
r_month, p_month = stats.pearsonr(detect_data[ILI], detect_data[DETECT])
print(f"월별: r={r_month:.3f}, p={p_month:.4f}, {len(detect_data)}개월")

week_data = pd.merge(df_detect[['주시작일', '검출률']], df_ili[['주시작일', '의사환자분율']], on='주시작일')
r_week, p_week = stats.pearsonr(week_data[ILI], week_data[DETECT])
print(f"주별: r={r_week:.3f}, p={p_week:.4f}, {len(week_data)}주")

# 8. 가설 검증 1: 의사환자 분율 (27개월)
print('\n[의사환자 분율 모델, 27개월]')
temp_r = show_corr(merged_data, TEMP)
ili_r = show_corr(merged_data, ILI)
ili_scores = [adj_r2(merged_data, [TEMP]), adj_r2(merged_data, [ILI]), adj_r2(merged_data, [TEMP, ILI])]
show_partial(merged_data, TEMP, ILI)
show_partial(merged_data, ILI, TEMP)

# 9. 가설 검증 2: 검출률 (24개월)
print('\n[검출률 모델, 24개월]')
temp_r2 = show_corr(detect_data, TEMP)
detect_r = show_corr(detect_data, DETECT)
detect_scores = [adj_r2(detect_data, [TEMP]), adj_r2(detect_data, [DETECT]), adj_r2(detect_data, [TEMP, DETECT])]
show_partial(detect_data, TEMP, DETECT)
show_partial(detect_data, DETECT, TEMP)

# 그래프 1. 월별 변화: 단위가 달라서 그래프를 4개로 나눔
months = merged_data['년월'].astype(str)
fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
axes[0].plot(months, merged_data['환자수'] / 10000, color=BLUE, marker='o')
axes[0].set_title('감기 환자수 (만 명)')
axes[1].plot(months, merged_data[TEMP], color=BLUE, marker='o')
axes[1].set_title('평균기온 (℃)')
axes[2].plot(months, merged_data[ILI], color=BLUE, marker='o')
axes[2].set_title('인플루엔자 의사환자 분율 (외래환자 1,000명당)')
axes[3].plot(months, merged_data[DETECT], color=BLUE, marker='o')
axes[3].set_title('인플루엔자 검출률 (%, 연령대 단순 평균, 2025-12까지)')
axes[3].tick_params(axis='x', rotation=90)
plt.tight_layout()
plt.savefig('KDH/월별_감기_기온_인플루엔자.png')
plt.show()

# 그래프 2. 기온, 의사환자 분율, 검출률과 감기 환자수 비교
fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
axes[0].scatter(merged_data[TEMP], merged_data['환자수'] / 10000, color=BLUE)
axes[0].set_title(f'평균기온 (r={temp_r:.2f}, 27개월)')
axes[0].set_xlabel('평균기온 (℃)')
axes[0].set_ylabel('월별 감기 환자수 (만 명)')
axes[1].scatter(merged_data[ILI], merged_data['환자수'] / 10000, color=BLUE)
axes[1].set_title(f'의사환자 분율 (r={ili_r:.2f}, 27개월)')
axes[1].set_xlabel('외래환자 1,000명당')
axes[2].scatter(detect_data[DETECT], detect_data['환자수'] / 10000, color=BLUE)
axes[2].set_title(f'검출률 (r={detect_r:.2f}, 24개월)')
axes[2].set_xlabel('검출률 (%)')
plt.tight_layout()
plt.savefig('KDH/기온_인플루엔자_감기_산점도.png')
plt.show()

# 그래프 3. 의사환자 분율과 실제 검출률이 함께 움직이는지 확인
plt.figure(figsize=(7, 5))
plt.scatter(week_data[ILI], week_data[DETECT], color=BLUE)
plt.title(f'주별 의사환자 분율과 검출률 (r={r_week:.2f}, {len(week_data)}주)')
plt.xlabel('의사환자 분율 (외래환자 1,000명당)')
plt.ylabel('검출률 (%)')
plt.tight_layout()
plt.savefig('KDH/의사환자분율_검출률_산점도.png')
plt.show()

# 그래프 4. 모델별 설명력 비교
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharex=True)
for ax, title, labels, scores in [
    (axes[0], '의사환자 분율 모델 (27개월)', ['기온만', '의사환자 분율만', '기온 + 의사환자 분율'], ili_scores),
    (axes[1], '검출률 모델 (24개월)', ['기온만', '검출률만', '기온 + 검출률'], detect_scores),
]:
    ax.barh(labels[::-1], scores[::-1], color=BLUE, height=0.5)
    for i, score in enumerate(scores[::-1]):
        ax.text(score + 0.01, i, f'{score:.3f}', va='center')
    ax.set_title(title)
    ax.set_xlabel('수정 R²')
    ax.set_xlim(0, 0.7)
plt.tight_layout()
plt.savefig('KDH/모델별_설명력_비교.png')
plt.show()
