# 가설 2 : 전월 대비 기온 하락과 월평균 일교차에 따른 감기·인플루엔자 진료 환자 수 비교.

import argparse
from pathlib import Path
import warnings

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / 'wook'
REGIONS = ('서울', '대전', '광주', '대구', '부산', '인천')
DISEASE_FILES = {'감기': '지역별감기.xlsx', '인플루엔자': '지역별인플루엔자.xlsx'}
MONTH_KEY = ['지역', '년월']
TEMPERATURE = '평균기온(℃)'
LOW = '평균최저기온(℃)'
HIGH = '평균최고기온(℃)'
PREVIOUS = '전월평균기온(℃)'
DROP = '하락폭(℃)'
RATE = '하락률(%)'
RANGE = '월평균일교차(℃)'
PATIENTS = '환자수'
NEXT_PATIENTS = '다음달_환자수'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('region', nargs='?', choices=REGIONS, help='생략하면 여섯 지역을 모두 표시합니다.')
parser.add_argument('--no-plot', action='store_true', help='터미널에 표만 표시합니다.')
args = parser.parse_args()
display_regions = (args.region,) if args.region else REGIONS

pd.set_option('display.unicode.east_asian_width', True)
warnings.filterwarnings('ignore', message='Workbook contains no default style', module='openpyxl')

if not args.no_plot:
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter, MonthLocator
    from matplotlib.ticker import StrMethodFormatter

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']


# [1. 날씨 전처리] 지역별 원본 CSV를 읽고 두 가지 기온 지표를 계산한다.
weather_frames = []
for region in display_regions:
    raw_weather = pd.read_csv(DATA_DIR / f'2024~2026{region}날씨.csv', encoding='cp949')
    raw_weather.columns = raw_weather.columns.str.strip()
    regional_weather = raw_weather[['년월', TEMPERATURE, LOW, HIGH]].copy()
    regional_weather['년월'] = pd.to_datetime(regional_weather['년월'].str.strip(), format='%m-%y')
    for column in (TEMPERATURE, LOW, HIGH):
        regional_weather[column] = pd.to_numeric(regional_weather[column], errors='coerce')

    # 빠진 월을 빈 행으로 두어 직전 관측값을 실제 전월과 혼동하지 않는다.
    regional_weather = regional_weather.set_index('년월').sort_index().asfreq('MS')
    regional_weather[PREVIOUS] = regional_weather[TEMPERATURE].shift(1)
    # 전월 - 당월로 계산하면 양수일 때 기온이 하락했다는 뜻이다.
    # 원본 정밀도인 0.1℃로 맞춰 같은 차이에 부동소수점 오차로 다른 순위가 생기지 않게 한다.
    regional_weather[DROP] = (regional_weather[PREVIOUS] - regional_weather[TEMPERATURE]).round(1)
    # 섭씨 0℃ 부근과 영하에서도 일관된 백분율을 얻도록 전월 기온을 절대온도(K)로 바꾼다.
    regional_weather[RATE] = regional_weather[DROP] / (regional_weather[PREVIOUS] + 273.15) * 100
    # 원본의 두 열은 일별 최고·최저기온의 월평균이므로 그 차이는 월평균 일교차다.
    regional_weather[RANGE] = (regional_weather[HIGH] - regional_weather[LOW]).round(1)
    weather_frames.append(regional_weather.assign(지역=region).reset_index())

weather = pd.concat(weather_frames, ignore_index=True)


# [2. 환자 수 전처리] pr1.py와 같은 방식으로 월별 환자 수를 세로 표로 바꾼다.
patient_frames = []
for disease, filename in DISEASE_FILES.items():
    raw_patients = pd.read_excel(DATA_DIR / filename, header=None)
    # 엑셀 3행은 진료년월, 4행은 지표 이름이다. 환자수 열만 선택한다.
    patient_cols = raw_patients.columns[raw_patients.iloc[3].astype('string').str.strip().eq(PATIENTS)]
    months = raw_patients.iloc[2].ffill().loc[patient_cols]
    region_names = raw_patients.iloc[:, 1].astype('string').str.strip()
    rows = region_names.isin(display_regions)
    disease_patients = raw_patients.loc[rows, patient_cols].copy()
    disease_patients.insert(0, '지역', region_names.loc[rows])
    disease_patients.columns = ['지역', *months]
    disease_patients = disease_patients.melt(id_vars='지역', var_name='년월', value_name=PATIENTS)
    disease_patients['년월'] = pd.to_datetime(disease_patients['년월'].str.strip(), format='%Y년 %m월')
    disease_patients[PATIENTS] = pd.to_numeric(
        disease_patients[PATIENTS].astype('string').str.strip().str.replace(',', '', regex=False),
        errors='coerce',
    ).astype('Int64')
    patient_frames.append(disease_patients.assign(질병=disease))

patients = pd.concat(patient_frames, ignore_index=True)
# 다음 달 환자 수의 날짜를 한 달 당겨 같은 지역·질병의 기준 월에 붙인다.
# 환자 수가 없는 달을 건너뛰지 않고 12월과 이듬해 1월도 연결한다.
next_counts = patients.rename(columns={PATIENTS: NEXT_PATIENTS}).copy()
next_counts['년월'] -= pd.offsets.MonthBegin(1)
monthly = weather.merge(patients, on=MONTH_KEY, how='inner', validate='one_to_many')
monthly = monthly.merge(next_counts, on=[*MONTH_KEY, '질병'], how='left', validate='one_to_one')


# [3. 지역·질병별 비교] 하락 월의 당월·다음 달 환자 수와 월평균 일교차를 분석한다.
print('[가설 2] 전월 대비 월평균기온의 하락 폭이 클수록 당월 감기 진료 환자 수가 많을 것이다.')
print('환자 수는 요양기관 소재지 기준입니다.')
print('하락률은 전월 절대온도(K) 기준이며, 월평균 일교차는 평균최고기온 - 평균최저기온입니다.')
results = []
for region in display_regions:
    regional = monthly.loc[monthly['지역'].eq(region)].sort_values('년월')
    print(f'\n[{region}] 월별 기온과 당월 환자 수')
    weather_columns = ['년월', PREVIOUS, TEMPERATURE, DROP, RATE, HIGH, LOW, RANGE]
    table = regional[weather_columns].drop_duplicates('년월').set_index('년월')
    counts = regional.pivot(index='년월', columns='질병', values=PATIENTS)
    table = table.join(counts.reindex(columns=list(DISEASE_FILES)).add_suffix(' 환자수'))
    display = table.round(3)
    display.index = table.index.strftime('%Y-%m')
    print(display.to_string(na_rep='-'))

    if not args.no_plot:
        fig = plt.figure(num=region, figsize=(15, 9), layout='constrained')
        fig.suptitle(f'{region} | 기온 하락·월평균 일교차와 진료 환자 수')
        grid = fig.add_gridspec(3, 4)

        # 두 기온선을 시간순으로 그리면 같은 달의 세로 간격이 월평균 일교차를 보여준다.
        temperature_ax = fig.add_subplot(grid[0, :])
        temperature_ax.plot(
            table.index, table[HIGH], color='#BD783C', marker='o', markersize=3, label='평균최고기온'
        )
        temperature_ax.plot(
            table.index, table[LOW], color='#39789B', marker='o', markersize=3, label='평균최저기온'
        )
        temperature_ax.fill_between(
            table.index, table[LOW], table[HIGH], color='#77899D', alpha=0.18, label='월평균 일교차'
        )
        temperature_ax.set_title('월별 평균최고·최저기온', loc='left')
        temperature_ax.set_ylabel('기온 (℃)')
        temperature_ax.xaxis.set_major_locator(MonthLocator(interval=3))
        temperature_ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
        temperature_ax.legend(loc='lower right', bbox_to_anchor=(1, 1), ncols=3, borderaxespad=0)
        temperature_ax.grid(axis='y', alpha=0.25)

    for row, disease in enumerate(DISEASE_FILES):
        data = regional.loc[regional['질병'].eq(disease)]
        # 하락 폭·하락률·일교차와 당월·다음 달 환자 수를 같은 하락 월로 비교한다.
        # 임의로 몇 ℃ 이상을 정하지 않고, 전월보다 기온이 내려간 월을 모두 후보로 삼는다.
        cooling = data.loc[data[DROP].gt(0)].dropna(subset=[RATE, RANGE, PATIENTS, NEXT_PATIENTS])
        all_months = data.dropna(subset=[RANGE, PATIENTS])
        comparisons = (
            ('하락폭·당월', DROP, PATIENTS, cooling, True),
            ('하락폭·다음달', DROP, NEXT_PATIENTS, cooling, True),
            ('하락률·당월', RATE, PATIENTS, cooling, False),
            ('하락률·다음달', RATE, NEXT_PATIENTS, cooling, False),
            ('일교차·하락월', RANGE, PATIENTS, cooling, True),
            ('일교차·전체월', RANGE, PATIENTS, all_months, True),
        )
        result = {'지역': region, '질병': disease, '하락 월 수': len(cooling), '전체 월 수': len(all_months)}
        if not args.no_plot:
            plot_slots = (grid[row + 1, column] for column in range(grid.ncols))

        for label, x, y, sample, draw in comparisons:
            rho = float('nan')
            if len(sample) >= 3 and sample[x].nunique() > 1 and sample[y].nunique() > 1:
                # 스피어만 ρ는 값 대신 순위로 비교하므로 유행기의 큰 환자 수에 덜 좌우된다.
                ranks = sample[[x, y]].rank()
                rho = ranks[x].corr(ranks[y])
            result[label] = rho

            if draw and not args.no_plot:
                ax = fig.add_subplot(next(plot_slots))
                ax.scatter(sample[x], sample[y], color='#39789B' if disease == '감기' else '#BD783C', alpha=0.8)
                score = '산출 불가' if pd.isna(rho) else f'ρ = {rho:+.2f}'
                ax.set_title(f'{disease} | {label}\n{score}, n = {len(sample)}')
                ax.set_xlabel(x)
                ax.set_ylabel('다음 달 환자 수 (명)' if y == NEXT_PATIENTS else '당월 환자 수 (명)')
                ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
                ax.grid(axis='y', alpha=0.25)

        results.append(result)


# [4. 결과 요약] 환자 수 규모가 다른 지역을 합치지 않고 지역별 상관계수를 비교한다.
summary = pd.DataFrame(results)
metrics = [label for label, _, _, _, _ in comparisons]
print('\n[지역·질병별 스피어만 순위상관계수 ρ]')
print('일교차·하락월은 하락 폭과 같은 기준 월을, 일교차·전체월은 자료가 겹치는 전체 월을 사용합니다.')
print(summary.round(3).to_string(index=False, na_rep='산출 불가'))
print('\n[질병별 지역 상관계수의 중앙값]')
print(summary.groupby('질병', sort=False)[metrics].median().round(3).to_string(na_rep='산출 불가'))

cold = summary.loc[summary['질병'].eq('감기'), '하락폭·당월'].dropna()
print(f'\n주가설(감기·당월): 분석 가능한 {len(cold)}개 지역 중 {cold.gt(0).sum()}개에서 양의 상관이 나타났습니다.')
print('이 상관계수는 관측 자료의 경향을 보여줍니다. 계절성과 유행 시기의 영향이 포함될 수 있습니다.')

if not args.no_plot:
    plt.show()
