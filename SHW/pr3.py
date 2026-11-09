import argparse
from pathlib import Path
import warnings
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / 'wook'
REGIONS = ['서울', '대전', '광주', '대구', '부산', '인천']
DISEASES = ['감기', '인플루엔자']
MONTH_KEY = ['지역', '년월']
PATIENT_KEY = MONTH_KEY + ['질병']
PATIENT_DIFFERENCE = '봄-가을_환자수차이'


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--top', type=int, choices=[2, 3], default=3, help='가설 2의 상·하위 그룹별 비교 개월 수입니다.')
parser.add_argument('--no-plot', action='store_true', help='터미널에 표만 표시합니다.')
args = parser.parse_args()
group_size = args.top
plot = not args.no_plot

pd.set_option('display.unicode.east_asian_width', True)
if plot:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']


# ============================================================
# 1. 데이터 처리
# ============================================================

# 1-1. 지역별 기온 CSV를 월별 데이터프레임으로 정리한다.
temperature_columns = ['평균기온(℃)', '평균최저기온(℃)', '평균최고기온(℃)']
weather_frames = []
for region in REGIONS:
    raw_weather = pd.read_csv(DATA_DIR / f'2024~2026{region}날씨.csv', encoding='cp949')
    raw_weather.columns = raw_weather.columns.str.strip()
    region_weather = raw_weather[['년월'] + temperature_columns].copy()

    # '1-24'처럼 적힌 연월을 2024-01-01처럼 해당 월의 첫날로 통일한다.
    region_weather['년월'] = pd.to_datetime(region_weather['년월'].str.strip(), format='%m-%y')

    # 빈칸이나 숫자로 바꿀 수 없는 기온은 NaN으로 남긴다.
    for column in temperature_columns:
        region_weather[column] = pd.to_numeric(region_weather[column], errors='coerce')

    # 월초 간격(MS)으로 다시 배치해 CSV에서 빠진 월도 빈 행으로 남긴다.
    region_weather = region_weather.set_index('년월').sort_index().asfreq('MS').reset_index()
    region_weather['지역'] = region
    weather_frames.append(region_weather)

weather = pd.concat(weather_frames, ignore_index=True)

# 1-2. 전월 기온과 비교해 하락폭, 하락률, 일교차를 계산한다.
# 지역별로 날짜가 정렬돼 있어 shift(1)은 같은 지역의 바로 전 달 값을 가져온다.
# 첫 달과 전월 기온이 비어 있는 달의 하락폭 및 하락률은 결측치로 남는다.
weather['전월평균기온(℃)'] = weather.groupby('지역')['평균기온(℃)'].shift(1)

# 하락폭(℃) = 전월 평균기온 - 당월 평균기온. 양수면 기온이 내려간 달이다.
# 원본 기온의 소수 첫째 자리까지 맞춰 같은 차이가 같은 순위가 되도록 한다.
weather['하락폭(℃)'] = (weather['전월평균기온(℃)'] - weather['평균기온(℃)']).round(1)

# 월평균 일교차(℃) = 일별 최고기온의 월평균 - 일별 최저기온의 월평균.
weather['월평균일교차(℃)'] = (weather['평균최고기온(℃)'] - weather['평균최저기온(℃)']).round(1)

# 비율의 분모는 섭씨에 273.15를 더해 절대온도(K)로 바꾼다.
# 하락률(%) = 하락폭 / 전월 평균기온(K) × 100.
# 일교차율(%) = 월평균 일교차 / 평균최저기온(K) × 100.
previous_kelvin = weather['전월평균기온(℃)'] + 273.15
lowest_kelvin = weather['평균최저기온(℃)'] + 273.15
weather['하락률(%)'] = weather['하락폭(℃)'] / previous_kelvin * 100
weather['일교차율(%)'] = weather['월평균일교차(℃)'] / lowest_kelvin * 100

# 1-3. 질병별 엑셀에서 6개 지역의 월별 환자 수를 뽑는다.
warnings.filterwarnings('ignore', message='Workbook contains no default style', module='openpyxl')
patient_frames = []
for disease in DISEASES:
    raw_patients = pd.read_excel(DATA_DIR / f'지역별{disease}.xlsx', header=None)

    # 엑셀 3행의 병합된 연월 칸을 앞의 값으로 채우고, 4행에서 환자수 열을 찾는다.
    months = raw_patients.iloc[2].ffill()
    metrics = raw_patients.iloc[3].astype('string').str.strip()
    count_columns = raw_patients.columns[metrics.eq('환자수')]
    region_names = raw_patients.iloc[:, 1].astype('string').str.strip()
    region_rows = region_names.isin(REGIONS)

    region_patients = raw_patients.loc[region_rows, [1] + count_columns.tolist()].copy()
    region_patients.columns = ['지역'] + months.loc[count_columns].tolist()
    region_patients['지역'] = region_names[region_rows]

    # 가로로 나열된 월별 열을 세로로 펼쳐 한 행에 지역·연월·질병별 환자 수를 둔다.
    region_patients = region_patients.melt(id_vars='지역', var_name='년월', value_name='환자수')
    region_patients['년월'] = pd.to_datetime(region_patients['년월'].str.strip(), format='%Y년 %m월')
    region_patients['질병'] = disease
    patient_frames.append(region_patients)

patients = pd.concat(patient_frames, ignore_index=True)

# 1-4. 환자 수의 결측치를 처리하고 다음 달 환자 수를 붙인다.
# 쉼표가 들어간 숫자 문자열을 정수로 바꾸고, 빈칸이나 '-'는 결측치로 남긴다.
# Int64는 결측치를 허용하는 판다스의 정수 자료형이다.
count_text = patients['환자수'].astype('string').str.strip().str.replace(',', '', regex=False)
patients['환자수'] = pd.to_numeric(count_text, errors='coerce').astype('Int64')

# 다음 달 자료의 날짜를 한 달 당겨 같은 지역·연월·질병에 연결한다.
# 예를 들어 2025년 1월 환자 수는 2024년 12월의 다음 달 환자 수가 된다.
next_counts = patients.rename(columns={'환자수': '다음달_환자수'})
next_counts['년월'] = next_counts['년월'] - pd.offsets.MonthBegin(1)
patients = patients.merge(next_counts, on=PATIENT_KEY, how='left', validate='one_to_one')

# 1-5. 기온과 환자 수를 지역·연월로 합친다.
# 한 지역의 한 달에 질병별 환자 수를 붙인다. 환자 수가 빠진 월의 기온도 남겨 둔다.
monthly = weather.merge(patients, on=MONTH_KEY, how='left', validate='one_to_many')


# ============================================================
# 2. 가설 1 입증 및 시각화
# ============================================================

# 2-1. 평균기온이 비슷한 봄·가을 월 찾기
# 질병별로 반복된 기온 행을 한 번만 남기고 평균기온이 비어 있는 월을 제외한다.
temp = monthly[MONTH_KEY + ['평균기온(℃)']].drop_duplicates()
temp = temp.dropna(subset=['평균기온(℃)'])
temp = temp[temp['년월'].dt.year.isin([2024, 2025])].copy()
temp['연도'] = temp['년월'].dt.year
spring = temp[temp['년월'].dt.month.isin([3, 4, 5])].rename(
    columns={'년월': '봄_년월', '평균기온(℃)': '봄_평균기온'}
)
autumn = temp[temp['년월'].dt.month.isin([9, 10, 11])].rename(
    columns={'년월': '가을_년월', '평균기온(℃)': '가을_평균기온'}
)
candidates = spring.merge(autumn, on=['지역', '연도'])
# 기온차이(℃) = |봄 월평균기온 - 가을 월평균기온|. 2℃ 이하인 쌍을 고른다.
candidates['기온차이'] = (candidates['봄_평균기온'] - candidates['가을_평균기온']).abs().round(3)
candidates = candidates[candidates['기온차이'] <= 2].sort_values(['기온차이', '봄_년월', '가을_년월'])

# 기온 차이가 작은 조합부터 선택하고 지역별로 같은 달을 한 번만 사용한다.
# 기온 차이가 같으면 봄 날짜, 가을 날짜가 빠른 쌍부터 확인한다.
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

print('\n[가설 1] 기온이 비슷한 봄과 가을의 지역별 진료 환자 수')
print('봄 3~5월 · 가을 9~11월 · 같은 지역과 연도 · 월평균기온 차이 2℃ 이내')
print('환자 수는 요양기관 소재지 기준입니다.')

# 2-2. 선택한 두 달에 질병별 환자 수를 연결한다.
monthly_counts = monthly.loc[monthly['질병'].notna(), PATIENT_KEY + ['환자수']]
# 기온 비교 쌍마다 감기와 인플루엔자 행을 하나씩 만든다.
season_comparisons = pairs.merge(pd.DataFrame({'질병': DISEASES}), how='cross')
for season in ('봄', '가을'):
    season_counts = monthly_counts.rename(columns={'년월': f'{season}_년월', '환자수': f'{season}_환자수'})
    season_comparisons = season_comparisons.merge(
        season_counts, on=['지역', f'{season}_년월', '질병'], how='left', validate='many_to_one'
    )
season_comparisons = season_comparisons.sort_values(['지역', '봄_년월', '가을_년월', '질병'])
# 환자 수 차이(명) = 봄 환자 수 - 가을 환자 수. 양수면 봄 환자 수가 더 많다.
season_comparisons[PATIENT_DIFFERENCE] = season_comparisons['봄_환자수'] - season_comparisons['가을_환자수']

# 2-3. 지역별 비교표와 질병별 요약 출력
for region in REGIONS:
    regional = season_comparisons[season_comparisons['지역'] == region]
    pair_count = (pairs['지역'] == region).sum()
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

    # 두 달의 환자 수가 모두 있는 쌍으로만 평균 차이와 비율을 계산한다.
    valid = regional.dropna(subset=[PATIENT_DIFFERENCE]).copy()
    valid['봄이_더많음'] = valid[PATIENT_DIFFERENCE] > 0
    by_disease = valid.groupby('질병')
    summary = pd.DataFrame(index=pd.Index(DISEASES, name='질병'))
    summary['비교_쌍수'] = by_disease.size().reindex(DISEASES, fill_value=0)
    summary['평균_환자수차이'] = by_disease[PATIENT_DIFFERENCE].mean()
    # 봄이 더 많은 비율(%) = 봄 환자 수가 더 많은 쌍 / 비교 가능한 전체 쌍 × 100.
    # True를 1로 세므로 조건의 평균에 100을 곱하면 이 비율이 된다.
    summary['봄이_더많은_비율'] = by_disease['봄이_더많음'].mean() * 100
    print('\n질병별 요약 (봄 - 가을, 비율 단위 %)')
    print(summary.round(1).to_string(na_rep='자료 없음'))

# 2-4. 봄과 가을의 환자 수를 나란히 그린다.
if plot:
    plot_data = season_comparisons.dropna(subset=[PATIENT_DIFFERENCE])
    fig, axes = plt.subplots(3, 4, figsize=(18, 11), facecolor='white')
    fig.suptitle('기온이 비슷한 봄·가을의 지역별 진료 환자 수', fontsize=21, fontweight='bold', y=0.985)
    fig.text(
        0.5, 0.945,
        '2024~2025년 · 같은 지역과 연도 · 월평균기온 차이 2℃ 이내', ha='center', fontsize=12,
    )
    fig.supylabel('진료 환자 수 (명)', x=0.012, fontsize=12)
    spring_color, autumn_color = '#D9944C', '#4B85AB'

    for region_index, region in enumerate(REGIONS):
        # 한 줄에 최대 두 지역을 배치하고, 한 지역당 질병 두 칸을 사용한다.
        regional = plot_data[plot_data['지역'] == region]
        for disease_index, disease in enumerate(DISEASES):
            ax = axes[region_index // 2, (region_index % 2) * 2 + disease_index]
            data = regional[regional['질병'] == disease]
            ax.set_title(f'{region} · {disease}', fontsize=13, fontweight='bold')
            if data.empty:
                ax.text(0.5, 0.5, '비교 자료 없음', ha='center', va='center', transform=ax.transAxes)
                ax.set_axis_off()
                continue

            positions = np.arange(len(data))
            spring, autumn = data['봄_환자수'], data['가을_환자수']
            spring_bars = ax.bar(positions - 0.22, spring, width=0.40, color=spring_color)
            autumn_bars = ax.bar(positions + 0.22, autumn, width=0.40, color=autumn_color)
            ax.bar_label(spring_bars, labels=spring.map('{:,.0f}'.format), padding=2, fontsize=9)
            ax.bar_label(autumn_bars, labels=autumn.map('{:,.0f}'.format), padding=2, fontsize=9)
            labels = []
            for _, pair in data.iterrows():
                spring_label = f"{pair['봄_년월']:%Y-%m} ({pair['봄_평균기온']:.1f}℃)"
                autumn_label = f"{pair['가을_년월']:%Y-%m} ({pair['가을_평균기온']:.1f}℃)"
                difference = pair[PATIENT_DIFFERENCE]
                labels.append(f'{spring_label}\n{autumn_label}\n차이 {difference:+,}명')
            ax.set_xticks(positions, labels, fontsize=9)
            ax.yaxis.set_major_formatter('{x:,.0f}')
            ax.tick_params(axis='y', labelsize=9)
            ax.margins(y=0.18)
            ax.set_axisbelow(True)
            ax.grid(axis='y', alpha=0.22)

    legend = [Patch(facecolor=spring_color, label='봄'), Patch(facecolor=autumn_color, label='가을')]
    fig.legend(handles=legend, loc='upper center', bbox_to_anchor=(0.5, 0.927), ncol=2, frameon=False)
    fig.text(
        0.5, 0.020,
        '날짜는 봄·가을 순서  |  차이 = 봄 환자 수 - 가을 환자 수  |  세로축 눈금은 그래프마다 다름',
        ha='center', fontsize=10, color='#444444',
    )
    fig.tight_layout(rect=(0.025, 0.042, 0.995, 0.920), h_pad=1.6, w_pad=1.5)
    output_path = SCRIPT_DIR / '가설1_지역별_봄가을_비교.png'
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    print('그림 저장 위치', output_path)


# ============================================================
# 3. 가설 2 입증 및 시각화
# ============================================================

# 3-1. 기온과 질병 자료가 같은 지역·연월에 있는 행을 선택한다.
h2_monthly = monthly.dropna(subset=['질병'])
print('\n[가설 2] 전월 대비 월평균기온의 하락 폭이 클수록 당월 감기 진료 환자 수가 많을 것이다.')
print('환자 수는 요양기관 소재지 기준입니다.')
print('하락률은 전월 절대온도(K) 기준이며, 월평균 일교차는 평균최고기온 - 평균최저기온입니다.')

correlation_metrics = {
    '하락폭·당월': ('하락폭(℃)', '환자수'),
    '하락폭·다음달': ('하락폭(℃)', '다음달_환자수'),
    '하락률·당월': ('하락률(%)', '환자수'),
    '하락률·다음달': ('하락률(%)', '다음달_환자수'),
    '일교차·하락월': ('월평균일교차(℃)', '환자수'),
    '일교차·전체월': ('월평균일교차(℃)', '환자수'),
}
rate_columns = {'전월 대비 기온 하락률': '하락률(%)', '월평균 일교차율': '일교차율(%)'}
patient_columns = [f'{disease} 환자수' for disease in DISEASES]
weather_columns = [
    '년월', '전월평균기온(℃)', '평균기온(℃)', '하락폭(℃)', '하락률(%)',
    '평균최고기온(℃)', '평균최저기온(℃)', '월평균일교차(℃)', '일교차율(%)',
]

# 3-2. 지역별 월별 표를 만들고 변화율 상·하위 월을 선택한다.
selected_months = []
for region in REGIONS:
    regional = h2_monthly[h2_monthly['지역'] == region].sort_values('년월')
    print(f'\n[{region}] 월별 기온과 당월 환자 수')
    table = regional[weather_columns].drop_duplicates('년월').set_index('년월')
    # 질병별 환자 수를 각 열로 펼쳐 같은 달의 기온과 나란히 배치한다.
    counts = regional.pivot(index='년월', columns='질병', values='환자수')
    table = table.join(counts.reindex(columns=DISEASES).add_suffix(' 환자수'))
    display = table.round(3)
    display.index = table.index.strftime('%Y-%m')
    print(display.to_string(na_rep='-'))

    # 두 질병의 환자 수가 모두 있는 달을 같은 기준으로 비교한다.
    for metric, column in rate_columns.items():
        candidates = table.dropna(subset=[column] + patient_columns)
        if column == '하락률(%)':
            candidates = candidates[candidates[column] > 0]
        # 상·하위 두 그룹을 모두 채울 수 있고 변화율이 서로 다른 달이 있어야 한다.
        if len(candidates) < group_size * 2 or candidates[column].nunique() < 2:
            print(f'{metric} 상·하위 비교에 필요한 자료가 부족합니다.')
            continue

        # 한 정렬의 양 끝에서 월을 선택해 상·하위 그룹이 겹치지 않게 한다.
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

# 3-3. 지역·질병별로 기온 변화와 환자 수의 순위상관을 계산한다.
results = []
for region in REGIONS:
    regional = h2_monthly[h2_monthly['지역'] == region].sort_values('년월')
    for disease in DISEASES:
        data = regional[regional['질병'] == disease]
        # 하락 월의 당월·다음 달 상관을 같은 표본으로 비교하기 위해 필요한 값이 모두 있는 월을 고른다.
        cooling = data[data['하락폭(℃)'] > 0].dropna(
            subset=['하락률(%)', '월평균일교차(℃)', '환자수', '다음달_환자수']
        )
        all_months = data.dropna(subset=['월평균일교차(℃)', '환자수'])
        result = {'지역': region, '질병': disease, '하락 월 수': len(cooling), '전체 월 수': len(all_months)}
        for label, (x_column, y_column) in correlation_metrics.items():
            sample = all_months if label == '일교차·전체월' else cooling
            values = sample[[x_column, y_column]]
            rho = np.nan
            # 스피어만 ρ는 두 변수의 값에 순위를 매긴 뒤 구한 피어슨 상관계수다.
            # 같은 값에는 평균 순위를 준다. 3개월 이상이고 두 순위 모두 변동이 있을 때만 계산한다.
            if len(sample) >= 3 and (values.nunique() > 1).all():
                ranks = values.rank()
                rho = ranks[x_column].corr(ranks[y_column])
            result[label] = rho
        results.append(result)

# 3-4. 상관계수와 지역별 결과의 중앙값 출력
summary = pd.DataFrame(results)
print('\n[지역·질병별 스피어만 순위상관계수 ρ]')
print('일교차·하락월은 하락 폭과 같은 기준 월을, 일교차·전체월은 자료가 겹치는 전체 월을 사용합니다.')
print(summary.round(3).to_string(index=False, na_rep='산출 불가'))
print('\n[질병별 지역 상관계수의 중앙값]')
print(summary.groupby('질병', sort=False)[list(correlation_metrics)].median().round(3).to_string(na_rep='산출 불가'))
cold = summary.loc[summary['질병'] == '감기', '하락폭·당월'].dropna()
print(f'\n주가설(감기·당월): 분석 가능한 {len(cold)}개 지역 중 {(cold > 0).sum()}개에서 양의 상관이 나타났습니다.')
print('이 상관계수는 관측 자료의 경향을 보여줍니다. 계절성과 유행 시기의 영향이 포함될 수 있습니다.')

# 3-5. 선정한 월과 상·하위 그룹별 평균 환자 수 출력
if selected_months:
    selected = pd.concat(selected_months, ignore_index=True)
    display = selected[['지역', '지표', '구분', '년월', '변화율(%)'] + patient_columns].copy()
    display['년월'] = display['년월'].dt.strftime('%Y-%m')
    print(f'\n[지역·지표별 상위 {group_size}개월과 하위 {group_size}개월]')
    print('하락률은 기온이 내려간 달만, 일교차율은 두 질병의 환자 수가 있는 전체 월을 사용합니다.')
    print('일교차율은 (월평균 최고기온 - 월평균 최저기온) / 월평균 최저기온(K) × 100입니다.')
    print(display.round(3).to_string(index=False))

    # 각 그룹의 평균 환자 수 = 선정한 달의 환자 수 합계 / 선정한 달 수.
    averages = selected.groupby(['지역', '지표', '구분'], sort=False, as_index=False)[patient_columns].mean()
    print('\n[선정된 달의 당월 진료 환자 수 평균]')
    print(averages.round(1).to_string(index=False))

    # 3-6. 상위 그룹과 하위 그룹의 평균 환자 수를 나란히 그린다.
    if plot:
        first_month = h2_monthly['년월'].min().strftime('%Y-%m')
        last_month = h2_monthly['년월'].max().strftime('%Y-%m')
        period = f'{first_month}~{last_month}'
        fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.5), sharex='col', sharey=True)
        fig.suptitle('기온 변화율 상·하위 월의 지역별 진료 환자 수', fontsize=20, fontweight='bold', y=0.984)
        fig.text(0.5, 0.920, f'{period} · 지역별로 선정한 달의 당월 환자 수를 평균', ha='center', fontsize=11)
        fig.supxlabel('선정된 달의 평균 진료 환자 수 (명)', y=0.055, fontsize=11)
        upper_color, lower_color = '#BB6327', '#39789B'
        positions = np.arange(len(REGIONS))[::-1]

        for row, metric in enumerate(rate_columns):
            metric_averages = averages[averages['지표'] == metric].set_index('지역')
            upper = metric_averages[metric_averages['구분'] == '상위'].reindex(REGIONS)
            lower = metric_averages[metric_averages['구분'] == '하위'].reindex(REGIONS)
            for column, disease in enumerate(DISEASES):
                ax = axes[row, column]
                patient_column = f'{disease} 환자수'
                for group, offset, color in [(upper, 0.19, upper_color), (lower, -0.19, lower_color)]:
                    counts = group[patient_column].to_numpy(dtype=float, na_value=np.nan)
                    bars = ax.barh(positions + offset, counts, height=0.34, color=color)
                    labels = [f'{count:,.0f}' if pd.notna(count) else '' for count in counts]
                    ax.bar_label(bars, labels=labels, padding=4, fontsize=9)
                ax.set_yticks(positions, REGIONS)
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
        output_path = SCRIPT_DIR / f'가설2_상하위{group_size}개월_환자수비교.png'
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print('그림 저장 위치', output_path)

# 두 가설의 그래프를 모두 만든 뒤 함께 보여준다.
if plot:
    plt.show()

print("***********\n**********\n********************")
print(monthly.to_string(index=False))
