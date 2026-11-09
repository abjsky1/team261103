# 가설 2. 전월 대비 기온 하락과 월평균 일교차에 따른 감기·인플루엔자 진료 환자 수 비교

import argparse
from pathlib import Path
import warnings

import numpy as np
import pandas as pd


data_path = Path(__file__).resolve().parent / 'wook'
regions = ['서울', '대전', '광주', '대구', '부산', '인천']
diseases = ['감기', '인플루엔자']

# 실행할 때 지역을 지정하거나 --no-plot으로 표만 볼 수 있다.
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('region', nargs='?', choices=regions, help='생략하면 여섯 지역을 모두 표시합니다.')
parser.add_argument('--top', type=int, choices=[2, 3], default=3, help='상·하위 그룹별 비교 개월 수입니다.')
parser.add_argument('--no-plot', action='store_true', help='터미널에 표만 표시합니다.')
args = parser.parse_args()
display_regions = regions
if args.region:
    display_regions = [args.region]

pd.set_option('display.unicode.east_asian_width', True)
warnings.filterwarnings('ignore', message='Workbook contains no default style', module='openpyxl')

if not args.no_plot:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']


# [1. 날씨 전처리] 지역별 원본 CSV를 읽고 기온 하락과 일교차를 계산한다.
weather_list = []
temperature_columns = ['평균기온(℃)', '평균최저기온(℃)', '평균최고기온(℃)']
for region in display_regions:
    raw_weather = pd.read_csv(data_path / f'2024~2026{region}날씨.csv', encoding='cp949')
    raw_weather.columns = raw_weather.columns.str.strip()
    regional_weather = raw_weather[['년월'] + temperature_columns].copy()
    regional_weather['년월'] = regional_weather['년월'].str.strip()
    regional_weather['년월'] = pd.to_datetime(regional_weather['년월'], format='%m-%y')
    for column in temperature_columns:
        regional_weather[column] = pd.to_numeric(regional_weather[column], errors='coerce')

    # asfreq('MS')로 월초 간격을 맞추고 빠진 월에는 빈 행을 넣는다.
    regional_weather = regional_weather.set_index('년월').sort_index()
    regional_weather = regional_weather.asfreq('MS')
    regional_weather['전월평균기온(℃)'] = regional_weather['평균기온(℃)'].shift(1)

    # 전월 - 당월로 계산하면 양수일 때 기온이 하락했다는 뜻이다.
    # 원본 정밀도인 0.1℃로 맞춰 같은 차이에 부동소수점 오차로 다른 순위가 생기지 않게 한다.
    temperature_drop = regional_weather['전월평균기온(℃)'] - regional_weather['평균기온(℃)']
    regional_weather['하락폭(℃)'] = temperature_drop.round(1)
    # 하락률을 계산할 때 분모인 전월 기온은 절대온도(K)로 바꾼다.
    previous_kelvin = regional_weather['전월평균기온(℃)'] + 273.15
    regional_weather['하락률(%)'] = regional_weather['하락폭(℃)'] / previous_kelvin * 100
    # 원본의 두 열은 일별 최고·최저기온의 월평균이므로 그 차이는 월평균 일교차다.
    temperature_range = regional_weather['평균최고기온(℃)'] - regional_weather['평균최저기온(℃)']
    regional_weather['월평균일교차(℃)'] = temperature_range.round(1)
    lowest_kelvin = regional_weather['평균최저기온(℃)'] + 273.15
    regional_weather['일교차율(%)'] = regional_weather['월평균일교차(℃)'] / lowest_kelvin * 100
    regional_weather['지역'] = region
    weather_list.append(regional_weather.reset_index())

weather = pd.concat(weather_list, ignore_index=True)


# [2. 환자 수 전처리] pr1.py와 같은 방식으로 월별 환자 수를 세로 표로 바꾼다.
patient_list = []
for disease in diseases:
    raw_patients = pd.read_excel(data_path / f'지역별{disease}.xlsx', header=None)

    # 엑셀 3행에서 진료년월을, 4행에서 환자수 열을 찾는다.
    metrics = raw_patients.iloc[3].astype('string').str.strip()
    patient_cols = raw_patients.columns[metrics == '환자수']
    months = raw_patients.iloc[2].ffill()

    region_names = raw_patients.iloc[:, 1].astype('string').str.strip()
    rows = region_names.isin(display_regions)
    disease_patients = raw_patients.loc[rows, [1] + patient_cols.tolist()].copy()
    disease_patients.columns = ['지역'] + months.loc[patient_cols].tolist()
    disease_patients['지역'] = region_names.loc[rows]

    # 월별 환자수 열을 년월과 환자수 두 열로 바꾼다.
    disease_patients = disease_patients.melt(id_vars='지역', var_name='년월', value_name='환자수')
    disease_patients['년월'] = pd.to_datetime(disease_patients['년월'].str.strip(), format='%Y년 %m월')
    patient_counts = disease_patients['환자수'].astype('string').str.strip()
    patient_counts = patient_counts.str.replace(',', '', regex=False)
    # Int64는 환자 수를 정수로 표시하면서 결측치를 유지한다.
    disease_patients['환자수'] = pd.to_numeric(patient_counts, errors='coerce').astype('Int64')
    disease_patients['질병'] = disease
    patient_list.append(disease_patients)

patients = pd.concat(patient_list, ignore_index=True)

# 지역·질병별로 날짜를 정렬하고, 다음 행의 날짜와 환자 수를 현재 행에 가져온다.
next_counts = patients.sort_values('년월').copy()
patient_groups = next_counts.groupby(['지역', '질병'])
next_row_month = patient_groups['년월'].shift(-1)
next_counts['다음달_환자수'] = patient_groups['환자수'].shift(-1)

# 다음 행이 달력상 다음 달일 때만 사용한다. 12월과 이듬해 1월도 이어진다.
next_calendar_month = next_counts['년월'] + pd.offsets.MonthBegin(1)
next_counts.loc[next_row_month != next_calendar_month, '다음달_환자수'] = pd.NA
next_counts = next_counts[['지역', '년월', '질병', '다음달_환자수']]

# 먼저 날씨와 환자 수 자료가 겹치는 월을 고르고, 다음 달 환자 수를 붙인다.
monthly = weather.merge(patients, on=['지역', '년월'], how='inner', validate='one_to_many')
monthly = monthly.merge(next_counts, on=['지역', '년월', '질병'], how='left', validate='one_to_one')


# [3. 지역·질병별 비교] 하락 월의 당월·다음 달 환자 수와 월평균 일교차를 분석한다.
print('[가설 2] 전월 대비 월평균기온의 하락 폭이 클수록 당월 감기 진료 환자 수가 많을 것이다.')
print('환자 수는 요양기관 소재지 기준입니다.')
print('하락률은 전월 절대온도(K) 기준이며, 월평균 일교차는 평균최고기온 - 평균최저기온입니다.')

# 기존 순위상관 분석에서 비교할 열이다.
comparisons = {
    '하락폭·당월': ('하락폭(℃)', '환자수'),
    '하락폭·다음달': ('하락폭(℃)', '다음달_환자수'),
    '하락률·당월': ('하락률(%)', '환자수'),
    '하락률·다음달': ('하락률(%)', '다음달_환자수'),
    '일교차·하락월': ('월평균일교차(℃)', '환자수'),
    '일교차·전체월': ('월평균일교차(℃)', '환자수'),
}
rate_columns = {'전월 대비 기온 하락률': '하락률(%)', '월평균 일교차율': '일교차율(%)'}
patient_columns = ['감기 환자수', '인플루엔자 환자수']
selected_months = []
group_size = args.top

results = []
for region in display_regions:
    regional = monthly[monthly['지역'] == region].sort_values('년월')
    print(f'\n[{region}] 월별 기온과 당월 환자 수')
    weather_columns = [
        '년월', '전월평균기온(℃)', '평균기온(℃)', '하락폭(℃)', '하락률(%)',
        '평균최고기온(℃)', '평균최저기온(℃)', '월평균일교차(℃)', '일교차율(%)',
    ]
    table = regional[weather_columns].drop_duplicates('년월').set_index('년월')
    # 질병별 환자 수를 같은 월의 별도 열로 보여준다.
    counts = regional.pivot(index='년월', columns='질병', values='환자수')
    counts = counts.reindex(columns=diseases).add_suffix(' 환자수')
    table = table.join(counts)
    display = table.round(3)
    display.index = table.index.strftime('%Y-%m')
    print(display.to_string(na_rep='-'))

    # 두 질병의 당월 환자 수가 모두 있는 달에서 같은 월을 골라 비교한다.
    for metric, column in rate_columns.items():
        candidates = table.dropna(subset=[column] + patient_columns)
        if column == '하락률(%)':
            candidates = candidates[candidates[column] > 0]

        if len(candidates) < group_size * 2 or candidates[column].nunique() < 2:
            print(f'{metric} 상·하위 비교에 필요한 자료가 부족합니다.')
            continue

        # 한 번 정렬한 표의 양 끝을 사용해 같은 달을 양쪽에 넣지 않는다.
        ranked = candidates.sort_values([column, '년월'], ascending=[False, True])
        upper = ranked.head(group_size)
        lower = ranked.tail(group_size).sort_values([column, '년월'])
        for group, sample in [('상위', upper), ('하위', lower)]:
            selected = sample[[column] + patient_columns].reset_index()
            selected = selected.rename(columns={column: '변화율(%)'})
            selected['지역'] = region
            selected['지표'] = metric
            selected['구분'] = group
            selected_months.append(selected)

    for disease in diseases:
        data = regional[regional['질병'] == disease]
        # 하락 폭·하락률·일교차와 당월·다음 달 환자 수를 같은 하락 월로 비교한다.
        cooling = data[data['하락폭(℃)'] > 0]
        cooling = cooling.dropna(
            subset=['하락률(%)', '월평균일교차(℃)', '환자수', '다음달_환자수']
        )
        all_months = data.dropna(subset=['월평균일교차(℃)', '환자수'])
        result = {'지역': region, '질병': disease, '하락 월 수': len(cooling), '전체 월 수': len(all_months)}

        for label, (x_column, y_column) in comparisons.items():
            sample = cooling
            if label == '일교차·전체월':
                sample = all_months

            rho = np.nan
            # 3개월 이상이고 두 값에 모두 변동이 있을 때 순위의 상관계수를 구한다.
            values = sample[[x_column, y_column]]
            if len(sample) >= 3 and (values.nunique() > 1).all():
                ranks = values.rank()
                rho = ranks[x_column].corr(ranks[y_column])
            result[label] = rho

        results.append(result)


# [4. 결과 요약] 환자 수 규모가 다른 지역을 합치지 않고 지역별 상관계수를 비교한다.
summary = pd.DataFrame(results)
metrics = list(comparisons)
print('\n[지역·질병별 스피어만 순위상관계수 ρ]')
print('일교차·하락월은 하락 폭과 같은 기준 월을, 일교차·전체월은 자료가 겹치는 전체 월을 사용합니다.')
print(summary.round(3).to_string(index=False, na_rep='산출 불가'))
print('\n[질병별 지역 상관계수의 중앙값]')
print(summary.groupby('질병', sort=False)[metrics].median().round(3).to_string(na_rep='산출 불가'))

cold = summary.loc[summary['질병'] == '감기', '하락폭·당월'].dropna()
positive_count = (cold > 0).sum()
print(f'\n주가설(감기·당월): 분석 가능한 {len(cold)}개 지역 중 {positive_count}개에서 양의 상관이 나타났습니다.')
print('이 상관계수는 관측 자료의 경향을 보여줍니다. 계절성과 유행 시기의 영향이 포함될 수 있습니다.')

# [5. 상·하위 월 비교] 선정 월을 표로 출력하고 지역별 환자 수 평균을 한 장에 표시한다.
if selected_months:
    selected = pd.concat(selected_months, ignore_index=True)
    selected_columns = ['지역', '지표', '구분', '년월', '변화율(%)'] + patient_columns
    display = selected[selected_columns].copy()
    display['년월'] = display['년월'].dt.strftime('%Y-%m')
    print(f'\n[지역·지표별 상위 {group_size}개월과 하위 {group_size}개월]')
    print('하락률은 기온이 내려간 달만, 일교차율은 두 질병의 환자 수가 있는 전체 월을 사용합니다.')
    print('일교차율은 (월평균 최고기온 - 월평균 최저기온) / 월평균 최저기온(K) × 100입니다.')
    print(display.round(3).to_string(index=False))

    averages = selected.groupby(['지역', '지표', '구분'], sort=False)[patient_columns].mean()
    averages = averages.reset_index()
    print('\n[선정된 달의 당월 진료 환자 수 평균]')
    print(averages.round(1).to_string(index=False))

    if not args.no_plot:
        fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.5), sharex='col', sharey=True)
        fig.suptitle('기온 변화율 상·하위 월의 지역별 진료 환자 수', fontsize=20, fontweight='bold', y=0.984)
        first_month = monthly['년월'].min().strftime('%Y-%m')
        last_month = monthly['년월'].max().strftime('%Y-%m')
        fig.text(
            0.5, 0.920, f'{first_month}~{last_month} · 지역별로 선정한 달의 당월 환자 수를 평균',
            ha='center', fontsize=11,
        )
        fig.supxlabel('선정된 달의 평균 진료 환자 수 (명)', y=0.055, fontsize=11)

        upper_color = '#BB6327'
        lower_color = '#39789B'
        positions = np.arange(len(display_regions))[::-1]

        for row, metric in enumerate(rate_columns):
            metric_averages = averages[averages['지표'] == metric]
            upper = metric_averages[metric_averages['구분'] == '상위'].set_index('지역')
            lower = metric_averages[metric_averages['구분'] == '하위'].set_index('지역')
            upper = upper.reindex(display_regions)
            lower = lower.reindex(display_regions)

            for column, disease in enumerate(diseases):
                ax = axes[row, column]
                patient_column = f'{disease} 환자수'
                upper_counts = upper[patient_column].to_numpy(dtype=float, na_value=np.nan)
                lower_counts = lower[patient_column].to_numpy(dtype=float, na_value=np.nan)
                upper_bars = ax.barh(positions + 0.19, upper_counts, height=0.34, color=upper_color)
                lower_bars = ax.barh(positions - 0.19, lower_counts, height=0.34, color=lower_color)
                ax.bar_label(upper_bars, labels=upper[patient_column].map('{:,.0f}'.format), padding=4, fontsize=9)
                ax.bar_label(lower_bars, labels=lower[patient_column].map('{:,.0f}'.format), padding=4, fontsize=9)
                ax.set_yticks(positions, display_regions)
                ax.set_title(f'{metric} · {disease}', fontsize=13, fontweight='bold')
                ax.xaxis.set_major_formatter('{x:,.0f}')
                ax.tick_params(axis='x', labelbottom=True)
                ax.tick_params(axis='y', labelleft=True)
                ax.margins(x=0.19)
                ax.set_axisbelow(True)
                ax.grid(axis='x', alpha=0.23)

        legend = [
            Patch(facecolor=upper_color, label=f'변화율 상위 {group_size}개월'),
            Patch(facecolor=lower_color, label=f'변화율 하위 {group_size}개월'),
        ]
        fig.legend(handles=legend, loc='upper center', bbox_to_anchor=(0.5, 0.900), ncol=2, frameon=False)
        fig.text(0.5, 0.018, '전월 대비 하락률은 기온이 내려간 달끼리 비교', ha='center', fontsize=10)
        fig.tight_layout(rect=(0.015, 0.075, 0.985, 0.915), h_pad=1.8, w_pad=2.0)

        region_suffix = f'_{args.region}' if args.region else ''
        output_path = data_path.parent / f'가설2_상하위{group_size}개월_환자수비교{region_suffix}.png'
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print('그림 저장 위치', output_path)
        plt.show()
