# 가설 1 : 온도가 비슷한 봄과 가을과 호흡질환의 상관관계

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import StrMethodFormatter


DATA_DIR = Path(__file__).resolve().parent / 'wook'
REGIONS = ('서울', '대전', '광주', '대구', '부산', '인천')
DISEASE_FILES = {
    '감기': '지역별감기.xlsx',
    '인플루엔자': '지역별인플루엔자.xlsx',
}
MONTH_KEY = ['지역', '년월']
TEMPERATURE = '평균기온(℃)'
PATIENT_DIFFERENCE = '봄-가을_환자수차이'


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('region', nargs='?', choices=REGIONS, help='생략하면 여섯 지역을 모두 표시합니다.')
parser.add_argument('--no-plot', action='store_true', help='터미널에 표만 표시합니다.')
args = parser.parse_args()
display_regions = (args.region,) if args.region else REGIONS

pd.set_option('display.unicode.east_asian_width', True)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']


# [1. 날씨 전처리] 지역별 CSV에서 연월과 월평균기온을 읽고 한 표로 합친다.
weather_frames = []
for region in REGIONS:
    raw_weather = pd.read_csv(DATA_DIR / f'2024~2026{region}날씨.csv', encoding='cp949')
    raw_weather.columns = raw_weather.columns.str.strip()
    regional_weather = raw_weather[['년월', TEMPERATURE]].copy()
    regional_weather['년월'] = pd.to_datetime(regional_weather['년월'].str.strip(), format='%m-%y')
    regional_weather[TEMPERATURE] = pd.to_numeric(regional_weather[TEMPERATURE], errors='coerce')
    weather_frames.append(regional_weather.assign(지역=region))

weather = pd.concat(weather_frames, ignore_index=True)
weather = weather[[*MONTH_KEY, TEMPERATURE]].sort_values(MONTH_KEY)


# [2. 날씨 데이터 확인] 합친 날씨 표를 지역별로 나눠 출력한다.
print('[2. 지역별 월평균기온]')
for region in display_regions:
    regional_weather = weather.loc[weather['지역'].eq(region), ['년월', TEMPERATURE]].copy()
    regional_weather['년월'] = regional_weather['년월'].dt.strftime('%Y-%m')
    print(f'\n{region}')
    print(regional_weather.to_string(index=False))


# [3. 봄·가을 기온 비교] 2024~2025년에서 같은 지역과 같은 연도의 월을 비교한다.
temp = weather.dropna(subset=['년월', TEMPERATURE])
temp = temp.loc[temp['년월'].dt.year.isin([2024, 2025])].copy()
temp['연도'] = temp['년월'].dt.year
spring = temp.loc[temp['년월'].dt.month.isin([3, 4, 5])].rename(
    columns={'년월': '봄_년월', TEMPERATURE: '봄_평균기온'}
)
autumn = temp.loc[temp['년월'].dt.month.isin([9, 10, 11])].rename(
    columns={'년월': '가을_년월', TEMPERATURE: '가을_평균기온'}
)
candidates = spring.merge(autumn, on=['지역', '연도'])
candidates['기온차이'] = (candidates['봄_평균기온'] - candidates['가을_평균기온']).abs().round(3)
candidates = candidates.loc[candidates['기온차이'].le(2)].sort_values(
    ['기온차이', '봄_년월', '가을_년월']
)

# 기온 차이가 작은 조합부터 고르고 같은 지역의 한 달은 한 번만 사용한다.
used_months = set()
selected = []
for index, row in candidates.iterrows():
    spring_key = (row['지역'], row['봄_년월'])
    autumn_key = (row['지역'], row['가을_년월'])
    if spring_key in used_months or autumn_key in used_months:
        continue
    selected.append(index)
    used_months.update([spring_key, autumn_key])

pairs = candidates.loc[selected].sort_values(['지역', '봄_년월', '가을_년월'])
print('\n[3. 선택된 봄·가을 기온 비교]')
print('봄 3~5월 / 가을 9~11월 · 같은 지역과 연도 · 월평균기온 차이 2℃ 이내')
display_pairs = pairs.loc[pairs['지역'].isin(display_regions)].drop(columns='연도').copy()
for column in ('봄_년월', '가을_년월'):
    display_pairs[column] = display_pairs[column].dt.strftime('%Y-%m')
if display_pairs.empty:
    print('조건을 만족하는 봄·가을 조합이 없습니다.')
else:
    print(display_pairs.to_string(index=False))


# [4. 환자 수 전처리] 질병별 엑셀을 읽고 지역·연월별로 날씨와 연결한다.
patient_frames = []
for disease, filename in DISEASE_FILES.items():
    raw_patients = pd.read_excel(DATA_DIR / filename, header=None)
    # 엑셀 3행에서 진료년월을, 4행에서 환자수 열을 찾는다.
    patient_cols = raw_patients.columns[raw_patients.iloc[3].astype('string').str.strip().eq('환자수')]
    months = raw_patients.iloc[2].ffill().loc[patient_cols]
    region_names = raw_patients.iloc[:, 1].astype('string').str.strip()
    rows = region_names.isin(REGIONS)
    disease_patients = raw_patients.loc[rows, patient_cols].copy()
    disease_patients.insert(0, '지역', region_names.loc[rows])
    disease_patients.columns = ['지역', *months]
    disease_patients = disease_patients.melt(id_vars='지역', var_name='년월', value_name='환자수')
    disease_patients['년월'] = pd.to_datetime(disease_patients['년월'].str.strip(), format='%Y년 %m월')
    disease_patients['환자수'] = pd.to_numeric(
        disease_patients['환자수'].astype('string').str.strip().str.replace(',', '', regex=False),
        errors='coerce',
    ).astype('Int64')
    patient_frames.append(disease_patients.assign(질병=disease))

patients = pd.concat(patient_frames, ignore_index=True).sort_values([*MONTH_KEY, '질병'])
monthly = weather.merge(patients, on=MONTH_KEY, how='left', validate='one_to_many')


# [5. 선택된 월의 환자 수 비교] 각 봄·가을 조합에 질병별 환자 수를 붙인다.
comparisons = pairs.merge(pd.DataFrame({'질병': list(DISEASE_FILES)}), how='cross')
counts = monthly[['지역', '년월', '질병', '환자수']]
for season in ('봄', '가을'):
    season_counts = counts.rename(columns={'년월': f'{season}_년월', '환자수': f'{season}_환자수'})
    comparisons = comparisons.merge(
        season_counts, on=['지역', f'{season}_년월', '질병'], how='left', validate='many_to_one'
    )
comparisons[PATIENT_DIFFERENCE] = comparisons['봄_환자수'] - comparisons['가을_환자수']


# [6. 지역별 결과] 환자 수 비교표와 요약을 출력하고 그래프를 그린다.
print('\n[6. 지역별 환자 수 비교 결과]')
print('환자 수는 요양기관 소재지 기준입니다.')
for region in display_regions:
    regional = comparisons.loc[comparisons['지역'].eq(region)]
    pair_count = int(pairs['지역'].eq(region).sum())
    print(f'\n[{region}] 2024~2025년 봄·가을 비교 {pair_count}쌍')
    if regional.empty:
        print('조건을 만족하는 봄·가을 조합이 없습니다.')
        continue

    columns = [
        '질병', '봄_년월', '봄_평균기온', '봄_환자수', '가을_년월',
        '가을_평균기온', '가을_환자수', '기온차이', PATIENT_DIFFERENCE,
    ]
    display = regional[columns].copy()
    for column in ('봄_년월', '가을_년월'):
        display[column] = display[column].dt.strftime('%Y-%m')
    print(display.to_string(index=False))

    valid = regional.dropna(subset=[PATIENT_DIFFERENCE])
    summary = valid.assign(봄이_더많음=valid[PATIENT_DIFFERENCE].gt(0)).groupby('질병').agg(
        비교_쌍수=(PATIENT_DIFFERENCE, 'size'),
        평균_환자수차이=(PATIENT_DIFFERENCE, 'mean'),
        봄이_더많은_비율=('봄이_더많음', 'mean'),
    ).reindex(DISEASE_FILES)
    summary['비교_쌍수'] = summary['비교_쌍수'].fillna(0).astype(int)
    summary['봄이_더많은_비율'] *= 100
    print('\n질병별 요약 (봄 - 가을, 비율 단위 %)')
    print(summary.round(1).to_string(na_rep='자료 없음'))

    if args.no_plot:
        continue

    fig, axes = plt.subplots(1, 2, num=region, figsize=(11, 5), layout='constrained')
    fig.suptitle(f'{region} | 기온이 비슷한 봄·가을의 진료 환자 수')
    for ax, disease in zip(axes, DISEASE_FILES):
        ax.set_title(disease)
        data = valid.loc[valid['질병'].eq(disease)]
        if data.empty:
            ax.text(0.5, 0.5, '비교 가능한 환자 수 없음', ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            continue

        labels = [
            f'{spring:%Y-%m} ({spring_temp:g}℃)\n{autumn:%Y-%m} ({autumn_temp:g}℃)'
            for spring, spring_temp, autumn, autumn_temp in data[
                ['봄_년월', '봄_평균기온', '가을_년월', '가을_평균기온']
            ].itertuples(index=False, name=None)
        ]
        positions = range(len(data))
        ax.bar([x - 0.2 for x in positions], data['봄_환자수'], width=0.4, label='봄', color='#D9944C')
        ax.bar([x + 0.2 for x in positions], data['가을_환자수'], width=0.4, label='가을', color='#4B85AB')
        ax.set_xticks(positions, labels)
        ax.set_ylabel('진료 환자 수 (명)')
        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        ax.legend()

if not args.no_plot and plt.get_fignums():
    plt.show()
