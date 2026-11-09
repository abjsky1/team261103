# 가설 1. 기온이 비슷한 봄과 가을의 지역별 호흡기 질환 환자 수 비교

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# /wook경로 밑에있는 파일들을 다 경로로 객체화 함
data_path = Path(__file__).resolve().parent / 'wook'
regions = ['서울', '대전', '광주', '대구', '부산', '인천']
diseases = ['감기', '인플루엔자']
difference_column = '봄-가을_환자수차이'


# 실행할 때 지역을 지정하거나 --no-plot으로 표만 볼 수 있다.
parser = argparse.ArgumentParser(description=__doc__)
# narg ='?' 인자를 0개 또는 1개 입력하도록 설정 / help : 실행시 표시할 설명
parser.add_argument('region', nargs='?', choices=regions, help='생략하면 여섯 지역을 모두 표시합니다.')
# action='store_true' : 해당옵션을 입력했으면 true 아니면 False를 저장
parser.add_argument('--no-plot', action='store_true', help='터미널에 표만 표시합니다.')
args = parser.parse_args()
display_regions = regions
if args.region:
    display_regions = [args.region]

# 터미널에서 한글정렬, 그래프에서 고딕계열 글꼴
pd.set_option('display.unicode.east_asian_width', True)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']


# [1. 날씨 전처리] 지역별 CSV에서 연월과 월평균기온을 읽고 한 표로 합친다.
weather_list = []
for region in regions:
    raw_weather = pd.read_csv(data_path / f'2024~2026{region}날씨.csv', encoding='cp949')
    raw_weather.columns = raw_weather.columns.str.strip()
    regional_weather = raw_weather[['년월', '평균기온(℃)']].copy()
    regional_weather['년월'] = regional_weather['년월'].str.strip()
    regional_weather['년월'] = pd.to_datetime(regional_weather['년월'], format='%m-%y')
    regional_weather['평균기온(℃)'] = pd.to_numeric(regional_weather['평균기온(℃)'], errors='coerce') 
    # errors='coerce' : 결측치 NaN으로 처리 
    regional_weather['지역'] = region
    weather_list.append(regional_weather)

weather = pd.concat(weather_list, ignore_index=True)
weather = weather[['지역', '년월', '평균기온(℃)']].sort_values(['지역', '년월'])


# [2. 날씨 데이터 확인] 합친 날씨 표를 지역별로 나눠 출력한다.
print('[2. 지역별 월평균기온]')
for region in display_regions:
    regional_weather = weather.loc[weather['지역'] == region, ['년월', '평균기온(℃)']].copy()
    regional_weather['년월'] = regional_weather['년월'].dt.strftime('%Y-%m')
    print(f'\n{region}')
    print(regional_weather.to_string(index=False))


# [3. 봄·가을 기온 비교] 2024~2025년에서 같은 지역과 같은 연도의 월을 비교한다.
temp = weather.dropna(subset=['년월', '평균기온(℃)'])
temp = temp[temp['년월'].dt.year.isin([2024, 2025])].copy()
temp['연도'] = temp['년월'].dt.year
spring = temp[temp['년월'].dt.month.isin([3, 4, 5])].rename(
    columns={'년월': '봄_년월', '평균기온(℃)': '봄_평균기온'}
)
autumn = temp[temp['년월'].dt.month.isin([9, 10, 11])].rename(
    columns={'년월': '가을_년월', '평균기온(℃)': '가을_평균기온'}
)

# 같은 지역·연도의 봄과 가을을 모든 조합으로 붙인 뒤, 2℃ 이내만 남긴다.
candidates = spring.merge(autumn, on=['지역', '연도'])
candidates['기온차이'] = (candidates['봄_평균기온'] - candidates['가을_평균기온']).abs().round(3)
candidates = candidates[candidates['기온차이'] <= 2]
candidates = candidates.sort_values(['기온차이', '봄_년월', '가을_년월'])

# 기온 차이가 작은 조합부터 고르고 같은 지역의 한 달은 한 번만 사용한다.
# 지역과 년월을 함께 기록해서 다른 지역의 같은 달은 사용할 수 있게 한다.
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
patient_list = []
for disease in diseases:
    # 첫번째 해에 컬럼명이 있는 구조가 아니기때문에 header=None 사용
    raw_patients = pd.read_excel(data_path / f'지역별{disease}.xlsx', header=None)

    # 엑셀 3행에서 진료년월을, 4행에서 환자수 열을 찾는다.
    metrics = raw_patients.iloc[3].astype('string').str.strip()
    patient_cols = raw_patients.columns[metrics == '환자수']
    months = raw_patients.iloc[2].ffill()

    # 필요한 지역의 행만 남기고 열 이름을 지역과 진료년월로 바꾼다.
    region_names = raw_patients.iloc[:, 1].astype('string').str.strip()
    rows = region_names.isin(regions)
    disease_patients = raw_patients.loc[rows, [1] + patient_cols.tolist()].copy()
    disease_patients.columns = ['지역'] + months.loc[patient_cols].tolist()
    disease_patients['지역'] = region_names.loc[rows]

    # 가로로 나열된 월별 자료를 세로로 바꾼다. melt() 함수 사용
    disease_patients = disease_patients.melt(id_vars='지역', var_name='년월', value_name='환자수')
    disease_patients['년월'] = pd.to_datetime(disease_patients['년월'].str.strip(), format='%Y년 %m월')
    patient_counts = disease_patients['환자수'].astype('string').str.strip()
    patient_counts = patient_counts.str.replace(',', '', regex=False)
    # Int64는 환자 수를 정수로 표시하면서 결측치를 유지한다.
    disease_patients['환자수'] = pd.to_numeric(patient_counts, errors='coerce').astype('Int64')
    disease_patients['질병'] = disease
    patient_list.append(disease_patients)

patients = pd.concat(patient_list, ignore_index=True).sort_values(['지역', '년월', '질병'])
# 지역·년월당 날씨는 한 행이고, 환자 수는 질병별로 여러 행이 연결된다.
monthly = weather.merge(patients, on=['지역', '년월'], how='left', validate='one_to_many')


# [5. 선택된 월의 환자 수 비교] 각 봄·가을 조합에 질병별 환자 수를 붙인다.
comparison_list = []
for disease in diseases:
    counts = monthly.loc[monthly['질병'] == disease, ['지역', '년월', '환자수']]
    spring_counts = counts.rename(columns={'년월': '봄_년월', '환자수': '봄_환자수'})
    autumn_counts = counts.rename(columns={'년월': '가을_년월', '환자수': '가을_환자수'})

    # 지역과 년월이 같은 환자 수를 봄과 가을에 각각 붙인다.
    # left는 환자 수가 비어 있어도 선택한 기온 비교 쌍을 유지한다.
    # many_to_one은 지역·년월별 환자 수가 중복되면 오류로 알려준다.
    disease_comparison = pairs.copy()
    disease_comparison['질병'] = disease
    disease_comparison = disease_comparison.merge(
        spring_counts, on=['지역', '봄_년월'], how='left', validate='many_to_one'
    )
    disease_comparison = disease_comparison.merge(
        autumn_counts, on=['지역', '가을_년월'], how='left', validate='many_to_one'
    )
    comparison_list.append(disease_comparison)

comparisons = pd.concat(comparison_list, ignore_index=True)
comparisons = comparisons.sort_values(['지역', '봄_년월', '가을_년월', '질병'])
comparisons = comparisons.reset_index(drop=True)
comparisons[difference_column] = comparisons['봄_환자수'] - comparisons['가을_환자수']


# [6. 지역별 결과] 환자 수 비교표와 요약을 출력하고 그래프를 그린다.
print('\n[6. 지역별 환자 수 비교 결과]')
print('환자 수는 요양기관 소재지 기준입니다.')
for region in display_regions:
    regional = comparisons[comparisons['지역'] == region]
    pair_count = (pairs['지역'] == region).sum()
    print(f'\n[{region}] 2024~2025년 봄·가을 비교 {pair_count}쌍')
    if regional.empty:
        print('조건을 만족하는 봄·가을 조합이 없습니다.')
        continue

    columns = [
        '질병', '봄_년월', '봄_평균기온', '봄_환자수', '가을_년월',
        '가을_평균기온', '가을_환자수', '기온차이', difference_column,
    ]
    display = regional[columns].copy()
    for column in ('봄_년월', '가을_년월'):
        display[column] = display[column].dt.strftime('%Y-%m')
    print(display.to_string(index=False))

    # 두 계절의 환자 수가 모두 있는 쌍으로 질병별 요약을 구한다.
    valid = regional.dropna(subset=[difference_column]).copy()
    valid['봄이_더많음'] = valid[difference_column] > 0
    by_disease = valid.groupby('질병')

    summary = pd.DataFrame()
    # 환자 수가 없는 질병도 표에 남기고 비교 쌍수는 0으로 표시한다.
    summary['비교_쌍수'] = by_disease.size().reindex(diseases, fill_value=0)
    summary['평균_환자수차이'] = by_disease[difference_column].mean()
    # True는 1, False는 0이므로 평균에 100을 곱하면 봄이 더 많은 쌍의 비율(%)이다.
    summary['봄이_더많은_비율'] = by_disease['봄이_더많음'].mean() * 100
    print('\n질병별 요약 (봄 - 가을, 비율 단위 %)')
    print(summary.round(1).to_string(na_rep='자료 없음'))

    if args.no_plot:
        continue

    # [7. 보고서용 그래프] 6개 지역을 한 장에 표시한다.
if not args.no_plot:
    from matplotlib.patches import Patch

    spring_color = '#D9944C'
    autumn_color = '#4B85AB'
    fig, axes = plt.subplots(3, 4, figsize=(18, 11), facecolor='white')
    fig.suptitle(
        '기온이 비슷한 봄·가을의 지역별 진료 환자 수',
        fontsize=21, fontweight='bold', y=0.985
    )
    fig.text(
        0.5, 0.945, '2024~2025년 · 같은 지역과 연도 · 월평균기온 차이 2℃ 이내',
        ha='center', fontsize=12
    )
    fig.supylabel('진료 환자 수 (명)', x=0.012, fontsize=12)

    plot_data = comparisons.dropna(subset=[difference_column])

    for region_index, region in enumerate(regions):
        # 한 줄에 두 지역을 배치한다. 지역마다 그래프 두 칸을 사용한다.
        row = region_index // 2
        first_column = (region_index % 2) * 2
        regional = plot_data[plot_data['지역'] == region]

        for disease_index, disease in enumerate(diseases):
            ax = axes[row, first_column + disease_index]
            data = regional[regional['질병'] == disease]
            ax.set_title(f'{region} · {disease}', fontsize=13, fontweight='bold')

            if data.empty:
                ax.text(
                    0.5, 0.5, '비교 자료 없음',
                    ha='center', va='center', transform=ax.transAxes
                )
                ax.set_axis_off()
                continue

            positions = np.arange(len(data))
            spring = data['봄_환자수']
            autumn = data['가을_환자수']

            # 봄은 왼쪽, 가을은 오른쪽에 그린다.
            spring_bars = ax.bar(positions - 0.22, spring, width=0.40, color=spring_color)
            autumn_bars = ax.bar(positions + 0.22, autumn, width=0.40, color=autumn_color)
            ax.bar_label(spring_bars, labels=spring.map('{:,.0f}'.format), padding=2, fontsize=9)
            ax.bar_label(autumn_bars, labels=autumn.map('{:,.0f}'.format), padding=2, fontsize=9)

            labels = []
            for _, pair in data.iterrows():
                spring_label = f"{pair['봄_년월']:%Y-%m} ({pair['봄_평균기온']:.1f}℃)"
                autumn_label = f"{pair['가을_년월']:%Y-%m} ({pair['가을_평균기온']:.1f}℃)"
                difference = pair[difference_column]
                labels.append(f'{spring_label}\n{autumn_label}\n차이 {difference:+,}명')

            ax.set_xticks(positions, labels, fontsize=9)
            ax.yaxis.set_major_formatter('{x:,.0f}')
            ax.tick_params(axis='y', labelsize=9)
            ax.margins(y=0.18)
            ax.set_axisbelow(True)
            ax.grid(axis='y', alpha=0.22)

    # 그림 전체에서 범례를 한 번만 표시한다.
    legend = [
        Patch(facecolor=spring_color, label='봄'),
        Patch(facecolor=autumn_color, label='가을'),
    ]
    fig.legend(
        handles=legend, loc='upper center', bbox_to_anchor=(0.5, 0.927),
        ncol=2, frameon=False
    )
    fig.text(
        0.5, 0.020,
        '날짜는 봄·가을 순서  |  차이 = 봄 환자 수 - 가을 환자 수  |  세로축 눈금은 그래프마다 다름',
        ha='center', fontsize=10, color='#444444'
    )
    fig.tight_layout(rect=(0.025, 0.042, 0.995, 0.920), h_pad=1.6, w_pad=1.5)

    output_path = Path(__file__).resolve().parent / '가설1_지역별_봄가을_비교.png'
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    print('그림 저장 위치', output_path)
    plt.show()