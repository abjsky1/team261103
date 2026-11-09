# 월평균기온과 호흡기 질환 진료 환자 수 분석
# 출처: 건강보험심사평가원 국민관심질병 통계, 전국 월평균기온 자료
# 사용 자료: 전국월별_기온.csv, 감기·폐렴·비염 진료 엑셀
# 날씨는 2024~2025년 각각 1~12월을 포함한다. 질병 자료와 겹치는 월만 분석한다.
# 감기 파일의 항목은 '급성 상기도감염(감기)'이므로 급성 기관지염으로 해석하지 않는다.

# [1. 공통 전처리]
# 1-1. 기온 CSV를 불러와 연월을 날짜형으로 변환한다. (아래 코드 작성 완료)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm

pd.set_option('display.unicode.east_asian_width', True)

df = pd.read_csv('./temperature_data/전국월별_기온.csv',
                 encoding='cp949',   # 한국어 인코딩으로 읽기
                 skiprows=7)         # 앞의 설명 7줄 건너뛰기

df['년월'] = df['년월'].str.strip()
df['년월'] = pd.to_datetime(df['년월'], format='%m-%y')



# 1-2. 기온 자료에서 연월·월평균기온만 선택한다.
df_temp = df[['년월','평균기온(℃)']]
print(df_temp)
# 1-3. 감기·폐렴·비염 엑셀을 각각 불러오고, 기온 자료와 지역 범위가 일치하는지 확인한다.
#      엑셀 3행은 진료년월, 4행은 지표명, 5행은 전체 합계다.
# 엑셀 파일을 읽기 위한 라이브러리 설치 python -m pip install openpyxl
df_cold = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(감기).xlsx', header=None )


# 1. 성별·연령에서 공백 제거
gender = df_cold.iloc[:, 1].astype(str).str.strip()
age = df_cold.iloc[:, 2].astype(str).str.strip()

# 2. 남·여의 연령별 자료만 선택 (계·소계 제외)
rows = (
    (gender.isin(['남', '여']))
    & (~age.isin(['계', '소계', '', 'nan']))
)

# 3. 네 번째 행에서 '환자수' 열만 찾기
patient_cols = df_cold.columns[
    df_cold.iloc[3].astype(str).str.strip().eq('환자수')
]

# 4. 성별·연령·월별 환자수만 추출
cold = df_cold.loc[rows, [1, 2] + patient_cols.tolist()].copy()

# 5. 열 이름을 성별·연령·진료년월로 변경
months = df_cold.iloc[2].ffill()
cold.columns = ['성별', '연령'] + months.loc[patient_cols].tolist()

# 6. 가로로 나열된 월별 자료를 세로로 변환
cold = cold.melt(
    id_vars=['성별', '연령'],
    var_name='진료년월',
    value_name='환자수'
)

# 7. 날짜와 환자수를 계산 가능한 형식으로 변환
cold['진료년월'] = pd.to_datetime(
    cold['진료년월'].astype(str).str.strip(),
    format='%Y년 %m월'
)
cold['환자수'] = pd.to_numeric(
    cold['환자수'].astype(str)
        .str.replace(',', '', regex=False)
        .str.strip()
)

# 8. 열 순서와 날짜순 정렬
cold = cold[['진료년월', '성별', '연령', '환자수']]
cold = cold.sort_values(
    ['진료년월', '성별', '연령']
).reset_index(drop=True)

print(cold)




# 1-4. 성별구분=계, 연령구분10세=계인 행에서 월별 '환자수'만 추출한다.
#      전체 합계에 성별·연령별 소계를 더하지 않는다.
# 1-5. 가로로 펼쳐진 자료를 질병별 '연월, 환자수' 형태로 바꾼다.
# 1-6. 날짜를 월 단위로 통일하고, 환자 수는 필요한 경우 쉼표·공백을 제거해 숫자형으로 변환한다.
# 1-7. 결측치와 중복 월을 확인한다. 결측치를 임의로 0이나 평균으로 채우지 않는다.
# 1-8. 연월 기준으로 병합하고 날짜순으로 정렬한다. 병합 과정에서 누락된 월도 확인한다.
#      공통 표: 연월 | 월평균기온 | 감기환자수 | 폐렴환자수 | 비염환자수
#      공통 분석 기간: 2024년 1월~2026년 3월
#      가설 1은 사계절 자료가 완전한 2024~2025년, 가설 2는 공통 기간 전체를 사용한다.

# [2. 가설 1: 기온이 비슷한 봄·가을의 감기·폐렴·비염 환자 수 비교]
# 가설: 같은 연도에서 월평균기온이 비슷한 봄(3~5월)과 가을(9~11월)을 비교하면,
#       감기·폐렴·비염 각각의 월별 진료 환자 수는 가을보다 봄에 많을 것이다.
#       성별·연령별로도 같은 경향이 나타나는지 살펴본다.
#       11월을 포함한 가을 전체를 사용하며, 12월은 겨울이므로 이 비교에 포함하지 않는다.


# 2-1. 봄·가을이 모두 있는 2024~2025년에서 봄(3~5월), 가을(9~11월)을 추출한다.
# 1. 비교할 기온 데이터 준비 
temp = df_temp[['년월','평균기온(℃)']].copy()
temp = temp.dropna(subset=['년월','평균기온(℃)']) # 결측치 행제거
# copy() 선택한 데이터를 복사해서 새로운 데이터프레임으로 만듬

# 년월이 Period 형식인 경우에도 처리 timestamp로 변환 / 추후에 추출에 필요함
if isinstance(temp['년월'].dtype, pd.PeriodDtype):
    temp['년월'] = temp['년월'].dt.to_timestamp()
else:
    temp['년월'] = pd.to_datetime(temp['년월'])

# 봄과 가을 자료가 모두 있는 2024~2025년 사용
# isin(내용)  : 내용과 일치하는지 확인   
temp = temp[temp['년월'].dt.year.isin([2024, 2025])].copy()
temp['연도'] = temp['년월'].dt.year

# 2. 봄과 가을 분리
spring = temp[temp['년월'].dt.month.isin([3, 4, 5])].rename(
    columns={'년월': '봄_년월', '평균기온(℃)': '봄_평균기온'}
)

autumn = temp[temp['년월'].dt.month.isin([9, 10, 11])].rename(
    columns={'년월': '가을_년월', '평균기온(℃)': '가을_평균기온'}
)

# 3. 같은 연도의 봄·가을 모든 조합 비교
# 연도가 같은 데이터 끼리 결합
candidates = spring.merge(autumn,
    on='연도',
    how='inner',
    suffixes=('_봄', '_가을')
)
candidates['기온차이'] = (
    candidates['봄_평균기온'] - candidates['가을_평균기온']
).abs()
# 봄과 가을기온의 평균을 빼고 절대값을 '기온차이' 라는 새로운 컬럼을 생성하여 저장

# 기온 차이가 2℃ 이내인 조합을 작은 차이 순으로 정렬 / 오름차순 기본값
candidates = candidates[candidates['기온차이'] <= 2].sort_values(
    ['기온차이', '봄_년월', '가을_년월']
)

# 4. 같은 달이 중복되지 않도록 선택
used_months = set()     # 사용한 날짜 / 중복허용 x
selected = []           # 선택한 행의 인덱스 저장


# iterrows : 데이터프레임을 한 행씩 반복해서 가져오는 함수 
for idx, row in candidates.iterrows():
    spring_month = row['봄_년월']
    autumn_month = row['가을_년월']

    if spring_month in used_months or autumn_month in used_months:
        continue

    selected.append(idx)
    used_months.update([spring_month, autumn_month])

similar_months = candidates.loc[selected].sort_values(
    ['봄_년월', '가을_년월']
).reset_index(drop=True)

# 5. 결과 출력
if similar_months.empty:
    print('기온 차이가 2℃ 이내인 봄·가을 조합이 없습니다.')
else:
    print(similar_months.to_string(index=False))


# 2-4. 비교표를 만든다: 봄 연월·기온·환자수 | 가을 연월·기온·환자수 | 봄-가을 환자 수 차이
# 2-5. 선택된 쌍의 평균 환자 수 차이와 봄 환자 수가 더 많은 쌍의 비율을 구한다.
#      질병별로 따로 계산하고, 성별·연령별 비교에서도 동일한 월 쌍을 사용한다.
#      아래 성별·연령별 합계 그래프는 자료 분포 확인용이며, 봄·가을 차이의 검증 결과는 아니다.
# 2-6. 비교 쌍별 봄·가을 환자 수를 나란한 막대그래프로 그리고 연월·기온을 표시한다.
# 2-7. 평균 차이와 쌍별 결과를 함께 보고 가설 지지 여부를 정리한다.
#      비교 쌍이 없으면 비교 불가, 적으면 탐색적 결과로 기록한다. 기온 외 요인의 영향도 고려한다.
from pathlib import Path

# 이미 선택한 봄·가을 날짜 가져오기
selected_months = pd.concat([
    similar_months['봄_년월'],
    similar_months['가을_년월']
]).drop_duplicates()

patient_list = []

for disease in ['감기', '폐렴', '비염']:
    path = Path(
        f'./질병/국민관심질병_성별연령별10세구간별현황_'
        f'202401_202603({disease}).xlsx'
    )

    raw = pd.read_excel(path, header=None)

    gender = raw.iloc[:, 1].astype(str).str.strip()
    age = raw.iloc[:, 2].astype(str).str.strip()

    # 남·여의 나이대별 자료만 선택 (계·소계 제외)
    rows = (
        gender.isin(['남', '여'])
        & ~age.isin(['계', '소계', '', 'nan'])
    )

    # '환자수' 열만 선택
    patient_cols = raw.columns[
        raw.iloc[3].astype(str).str.strip().eq('환자수')
    ]

    data = raw.loc[rows, [1, 2] + patient_cols.tolist()].copy()

    months = raw.iloc[2].ffill()
    data.columns = ['성별', '연령'] + months.loc[patient_cols].tolist()

    data['성별'] = data['성별'].astype(str).str.strip()
    data['연령'] = data['연령'].astype(str).str.strip()

    # 월별 자료를 세로 형태로 변환
    data = data.melt(
        id_vars=['성별', '연령'],
        var_name='년월',
        value_name='환자수'
    )

    # 기존 날짜와 비교할 수 있도록 형식 통일
    data['년월'] = pd.to_datetime(
        data['년월'].astype(str).str.strip(),
        format='%Y년 %m월'
    )

    data['환자수'] = pd.to_numeric(
        data['환자수'].astype(str)
            .str.replace(',', '', regex=False)
            .str.strip()
    )

    data['질병'] = disease

    # 기온이 비슷한 달에 해당하는 자료만 선택
    data = data[data['년월'].isin(selected_months)].copy()

    patient_list.append(data)

# 세 질병 데이터 합치기
patients = pd.concat(patient_list, ignore_index=True)

patients = patients[
    ['년월', '질병', '성별', '연령', '환자수']
].sort_values(
    ['년월', '질병', '성별', '연령']
).reset_index(drop=True)

# 질병별 데이터
cold = patients[patients['질병'].eq('감기')].copy()
pneumonia = patients[patients['질병'].eq('폐렴')].copy()
rhinitis = patients[patients['질병'].eq('비염')].copy()

# 전체 출력
print(patients.to_string(index=False))

# ================================== 시각화 ===============================================
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'

data = patients.copy()
data['연령'] = data['연령'].str.extract(r'(\d+)')[0].astype(int)

# 질병·나이대·성별로 환자수 합산
summary = data.groupby(
    ['질병', '연령', '성별'], as_index=False
)['환자수'].sum()

# 세 질병 전체 합계도 남녀 구분
total = summary.groupby(
    ['연령', '성별'], as_index=False
)['환자수'].sum()

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

for ax, disease in zip(axes.flat, ['감기', '폐렴', '비염', '전체']):
    plot_data = (
        total if disease == '전체'
        else summary[summary['질병'] == disease]
    )

    sns.barplot(
        data=plot_data,
        x='연령',
        y='환자수',
        hue='성별',
        hue_order=['남', '여'],
        palette={'남': '#3498DB', '여': '#F39C12'},
        ax=ax
    )

    ax.set_title(disease)
    ax.set_xlabel('나이대')
    ax.set_ylabel('환자수 합계 (명)')
    ax.legend(title='성별')

plt.tight_layout()
plt.show()

# [3. 가설 2: 기온 하락 폭과 감기 환자 수의 관계 및 시차 비교]
# 가설: 전월 대비 월평균기온의 하락 폭이 클수록 급성 상기도감염(감기) 진료 환자 수가 많을 것이다.
# 시차 비교: 기온 하락 폭과 당월·다음 달 감기 환자 수의 관계를 비교한다.
# 분석 범위: 2024년 1월~2026년 3월 중 자료가 겹치는 월을 사용한다.
#            2024·2025년의 11·12월도 포함하여 가을에서 겨울로 이어지는 기온 하락을 반영한다.
#            날씨에 이후 월이 있어도 환자 수 자료가 없는 월까지 분석 기간을 늘리지 않는다.
# 3-1. 공통 기간의 월 간격을 확인하고, 빠진 월은 재색인해 전월·다음 달이 실제 달력과 일치하도록 한다.
# 3-2. 전체 월 자료에서 기온 하락 폭을 계산한다: 전월 월평균기온 - 당월 월평균기온
# 3-3. 전체 월 자료에서 다음 달 감기 환자 수 열을 만든다.
#      전월 기온은 shift(1), 다음 달 환자 수는 shift(-1)로 연결한다.
#      기온 하락 월을 먼저 추출하면 달 간격이 어긋나므로 두 변수를 만든 뒤 추출한다.
# 3-4. 기온 하락 폭이 양수이고, 하락 폭·당월·다음 달 환자 수가 모두 있는 기준 월만 선택한다.
#      당월·다음 달 상관관계는 동일한 기준 월로 비교한다.
#      2024년 1월은 전월 기온 부재, 2026년 3월은 다음 달 환자 수 부재로 비교에서 제외된다.
#      12월의 다음 달은 다음 해 1월로 연결한다. 연도별로 나누어 shift하지 않는다.
# 3-5. 분석 개월 수와 두 상관계수를 구한다: 하락 폭-당월 환자수 / 하락 폭-다음 달 환자수
# 3-6. 산점도 2개를 나란히 그리고, 각각 상관계수와 분석 개월 수를 표시한다.
#      x축: 기온 하락 폭 / y축: 당월 또는 다음 달 감기 환자 수
# 3-7. 양의 관계가 나타나는지, 어느 시점의 관계가 더 강한지 비교해 가설과 시차를 해석한다.
#      관측치가 적거나 변수의 변동이 없으면 판단을 보류한다.
#      계절·연휴·유행 등의 영향이 있으므로 인과관계나 확정된 시차로 결론 내리지 않는다.

# [4. 최종 정리]
# 공통 전처리 표, 가설 1 비교표·막대그래프, 가설 2 상관계수·산점도 2개를 준비한다.
# 각 가설의 결과와 분석 한계를 짧게 작성한다.
