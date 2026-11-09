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
    from matplotlib.dates import DateFormatter, MonthLocator
    from matplotlib.lines import Line2D
    from matplotlib.ticker import MaxNLocator

    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 한글 글꼴에서도 음수 눈금의 부호를 표시한다.


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

# 2-4. 지역별로 봄·가을 환자 수 차이를 0 기준선과 가로 점으로 나타낸다.
if plot:
    plot_data = season_comparisons.dropna(subset=[PATIENT_DIFFERENCE])
    fig, axes = plt.subplots(3, 2, figsize=(15.5, 10.8), facecolor='white')
    fig.suptitle('기온이 비슷한 봄·가을의 지역별 진료 환자 수 차이', fontsize=25, fontweight='bold', y=0.985)
    fig.text(
        0.5, 0.936, '2024~2025년 · 같은 지역과 연도 · 월평균기온 차이 2℃ 이내',
        ha='center', fontsize=14, fontweight='bold',
    )
    fig.supxlabel('진료 환자 수 차이 (봄 - 가을, 명)', y=0.054, fontsize=14, fontweight='bold')
    spring_color, autumn_color, equal_color = '#AB5018', '#21658E', '#64748B'
    text_color = '#334155'
    pair_columns = ['봄_년월', '가을_년월']
    disease_styles = [('감기', 0.19, 'o'), ('인플루엔자', -0.19, 'D')]

    for ax, region in zip(axes.flat, REGIONS):
        regional = plot_data[plot_data['지역'] == region]
        ax.set_title(region, loc='left', fontsize=18, fontweight='bold', pad=10)
        if regional.empty:
            ax.text(
                0.5, 0.5, '비교 자료 없음', ha='center', va='center',
                fontsize=12, fontweight='bold', transform=ax.transAxes,
            )
            ax.set_axis_off()
            continue

        # 같은 봄·가을 조합에 두 질병을 열로 배치한다. 환자 수 차이가 없는 칸은 비워 둔다.
        pair_weather = regional.drop_duplicates(subset=pair_columns).set_index(pair_columns)
        differences = regional.pivot(index=pair_columns, columns='질병', values=PATIENT_DIFFERENCE)
        differences = differences.reindex(index=pair_weather.index, columns=DISEASES)
        positions = np.arange(len(pair_weather))[::-1]
        for disease, offset, marker in disease_styles:
            valid = differences[disease].notna()
            values = differences.loc[valid, disease].to_numpy(dtype=int)
            rows = positions[valid.to_numpy()] + offset
            # 봄 - 가을이 양수면 오른쪽에 봄색, 음수면 왼쪽에 가을색으로 표시한다.
            colors = np.full(len(values), equal_color)
            colors[values > 0] = spring_color
            colors[values < 0] = autumn_color
            ax.hlines(rows, 0, values, colors=colors, linewidth=1.7, alpha=0.62)
            ax.scatter(
                values, rows, c=colors, marker=marker, s=46,
                edgecolors='white', linewidths=0.6, zorder=3,
            )
            for value, row, color in zip(values, rows, colors):
                ax.annotate(
                    f'{value:+,}' if value else '0', (value, row),
                    xytext=(-6 if value < 0 else 6, 0), textcoords='offset points',
                    ha='right' if value < 0 else 'left', va='center', fontsize=12, fontweight='bold', color=color,
                )

        labels = []
        for (spring_month, autumn_month), pair in pair_weather.iterrows():
            spring_label = f"봄 {spring_month:%y.%m} · {pair['봄_평균기온']:.1f}℃"
            autumn_label = f"가을 {autumn_month:%y.%m} · {pair['가을_평균기온']:.1f}℃"
            labels.append(f'{spring_label}\n{autumn_label}')
        ax.set_yticks(positions, labels)
        # 지역별로 0이 가운데 오도록 음수와 양수 범위를 같게 잡는다.
        x_limit = max(regional[PATIENT_DIFFERENCE].abs().max(), 1) * 1.38
        ax.set_xlim(-x_limit, x_limit)
        ax.set_ylim(-0.5, len(positions) - 0.5)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
        ax.xaxis.set_major_formatter('{x:,.0f}')
        ax.tick_params(axis='both', length=0, pad=7, labelsize=12, colors=text_color)
        for tick_label in ax.get_xticklabels() + ax.get_yticklabels():
            tick_label.set_fontweight('bold')
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis='x', color='#E2E8F0', linewidth=0.7)
        ax.axvline(0, color='#94A3B8', linewidth=1.0)

    legend = [
        Line2D([], [], color=autumn_color, linewidth=3, label='가을 환자 수가 더 많음'),
        Line2D([], [], color=spring_color, linewidth=3, label='봄 환자 수가 더 많음'),
        Line2D([], [], color=text_color, marker='o', linestyle='none', label='감기'),
        Line2D([], [], color=text_color, marker='D', linestyle='none', label='인플루엔자'),
    ]
    fig.legend(
        handles=legend, loc='upper center', bbox_to_anchor=(0.5, 0.910), ncol=4,
        frameon=False, prop={'size': 13, 'weight': 'bold'},
    )
    fig.text(
        0.5, 0.020,
        '0의 왼쪽은 가을이 더 많고, 오른쪽은 봄이 더 많음  ·  가로축 눈금은 지역별로 다름',
        ha='center', fontsize=12, fontweight='bold', color=text_color,
    )
    fig.tight_layout(rect=(0.022, 0.086, 0.985, 0.863), h_pad=1.8, w_pad=2.0)
    output_path = SCRIPT_DIR / '가설1_지역별_봄가을_비교.png'
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print('그림 저장 위치', output_path)

    # 2-5. 질병별 그림에서는 6개 지역의 월 조합을 한 축에 모아 비교한다.
    region_order = {region: index for index, region in enumerate(REGIONS)}
    for disease, _, marker in disease_styles:
        disease_data = plot_data[plot_data['질병'] == disease].copy()
        if disease_data.empty:
            continue

        disease_data['지역순서'] = disease_data['지역'].map(region_order)
        disease_data = disease_data.sort_values(['지역순서'] + pair_columns).reset_index(drop=True)
        # 지역이 바뀔 때마다 행 사이에 여백을 넣는다.
        previous_region = disease_data['지역'].shift(fill_value='')
        region_groups = disease_data['지역'].ne(previous_region).cumsum()
        rows = np.arange(len(disease_data)) + (region_groups.to_numpy() - 1) * 0.55
        values = disease_data[PATIENT_DIFFERENCE].to_numpy(dtype=int)
        colors = np.full(len(values), equal_color)
        colors[values > 0] = spring_color
        colors[values < 0] = autumn_color

        fig, ax = plt.subplots(figsize=(13.5, 10), facecolor='white')
        fig.suptitle(f'{disease}의 봄·가을 진료 환자 수 차이', fontsize=25, fontweight='bold', y=0.975)
        fig.text(
            0.5, 0.924, '2024~2025년 · 같은 지역과 연도 · 월평균기온 차이 2℃ 이내',
            ha='center', fontsize=14, fontweight='bold',
        )
        fig.legend(
            handles=legend[:2], loc='upper center', bbox_to_anchor=(0.5, 0.898), ncol=2,
            frameon=False, prop={'size': 13, 'weight': 'bold'},
        )

        for region, region_data in disease_data.groupby('지역', sort=False):
            region_rows = rows[region_data.index]
            ax.axhspan(region_rows[0] - 0.48, region_rows[-1] + 0.48, color='#F6F8FB', linewidth=0, zorder=0)
            ax.text(
                -0.44, region_rows.mean(), region, transform=ax.get_yaxis_transform(),
                va='center', fontsize=15, fontweight='bold', color=text_color,
            )

        ax.hlines(rows, 0, values, colors=colors, linewidth=1.7, alpha=0.62)
        ax.scatter(values, rows, c=colors, marker=marker, s=48, edgecolors='white', linewidths=0.6, zorder=3)
        for value, row, color in zip(values, rows, colors):
            ax.annotate(
                f'{value:+,}' if value else '0', (value, row),
                xytext=(-6 if value < 0 else 6, 0), textcoords='offset points',
                ha='right' if value < 0 else 'left', va='center', fontsize=12, fontweight='bold', color=color,
            )

        spring_dates = disease_data['봄_년월'].dt.strftime('%y.%m')
        autumn_dates = disease_data['가을_년월'].dt.strftime('%y.%m')
        spring_temps = disease_data['봄_평균기온'].map('{:.1f}℃'.format)
        autumn_temps = disease_data['가을_평균기온'].map('{:.1f}℃'.format)
        labels = spring_dates + ' (' + spring_temps + ')  /  ' + autumn_dates + ' (' + autumn_temps + ')'
        ax.set_yticks(rows, labels)
        ax.text(-0.44, 1.02, '지역', transform=ax.transAxes, fontsize=13, fontweight='bold', color=text_color)
        ax.text(
            -0.01, 1.02, '봄 월·기온  /  가을 월·기온', transform=ax.transAxes,
            ha='right', fontsize=13, fontweight='bold', color=text_color,
        )

        x_limit = max(np.abs(values).max(), 1) * 1.32
        ax.set_xlim(-x_limit, x_limit)
        ax.set_ylim(rows[-1] + 0.65, -0.65)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
        ax.xaxis.set_major_formatter('{x:,.0f}')
        ax.tick_params(axis='both', length=0, pad=7, labelsize=12, colors=text_color)
        for tick_label in ax.get_xticklabels() + ax.get_yticklabels():
            tick_label.set_fontweight('bold')
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis='x', color='#E2E8F0', linewidth=0.7)
        ax.axvline(0, color='#94A3B8', linewidth=1.0)
        ax.set_xlabel('진료 환자 수 차이 (봄 - 가을, 명)', fontsize=14, fontweight='bold', labelpad=12)
        fig.subplots_adjust(left=0.335, right=0.96, top=0.815, bottom=0.11)

        output_path = SCRIPT_DIR / f'가설1_{disease}_봄가을_차이.png'
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print('그림 저장 위치', output_path)


# ============================================================
# 3. 가설 2 분석 및 시각화
# ============================================================

# 3-1. 기온과 질병 자료가 같은 지역·연월에 있는 행을 선택한다.
h2_monthly = monthly.dropna(subset=['질병'])
print('\n[가설 2] 전월 대비 월평균기온의 하락 폭이 클수록 당월 감기 진료 환자 수가 많을 것이다.')
print('환자 수는 요양기관 소재지 기준입니다.')
print('하락률은 전월 절대온도(K) 기준이며, 월평균 일교차는 평균최고기온 - 평균최저기온입니다.')

cooling_label = '전월 대비 기온 하락률'
range_label = '월평균 일교차율'
rate_columns = {cooling_label: '하락률(%)', range_label: '일교차율(%)'}
# 지표별로 분석할 월 범위를 정한다. True면 기온 하락 월만 사용한다.
correlation_metrics = {
    cooling_label: (rate_columns[cooling_label], True),
    range_label: (rate_columns[range_label], False),
    '전월 대비 기온 하락폭': ('하락폭(℃)', True),
    '월평균 일교차 (하락 월)': ('월평균일교차(℃)', True),
    '월평균 일교차 (전체 유효 월)': ('월평균일교차(℃)', False),
}
patient_timings = {'당월': '환자수', '다음 달': '다음달_환자수'}
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
        if metric == cooling_label:
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

def spearman_rho(values):
    # 두 변수에 평균 순위를 매긴 뒤 피어슨 상관계수를 구한다.
    if len(values) < 3 or (values.nunique() < 2).any():
        return np.nan
    ranks = values.rank()
    return ranks.iloc[:, 0].corr(ranks.iloc[:, 1])


# 3-3. 지역·질병별로 기온 변화와 환자 수의 순위상관을 계산한다.
results = []
for (region, disease), data in h2_monthly.groupby(['지역', '질병'], sort=False):
    for metric, (column, cooling_only) in correlation_metrics.items():
        months = data.loc[data['하락폭(℃)'].gt(0)] if cooling_only else data
        # 같은 지역에서 지표와 두 시점의 환자 수가 모두 있는 기준 월을 사용한다.
        paired = months[[column, *patient_timings.values()]].dropna()
        result = {'지표': metric, '지역': region, '질병': disease, 'n': len(paired)}
        for timing, patient_column in patient_timings.items():
            result[timing] = spearman_rho(paired[[column, patient_column]])
        results.append(result)

# 3-4. 상관계수와 지역별 결과의 중앙값 출력
summary = pd.DataFrame(results, columns=['지표', '지역', '질병', 'n', *patient_timings])
print('\n[지역·질병별 스피어만 순위상관계수 ρ]')
print('n은 계산에 사용한 기준 월 수입니다. 당월과 다음 달은 같은 기준 월을 사용합니다.')
for metric, regional in summary.groupby('지표', sort=False):
    print(f'\n[{metric}]')
    print(regional.drop(columns='지표').round(3).to_string(index=False, na_rep='산출 불가'))
    print('질병별 지역 상관계수의 중앙값')
    medians = regional.groupby('질병', sort=False)[list(patient_timings)].median()
    print(medians.round(3).to_string(na_rep='산출 불가'))
cold = summary.loc[(summary['지표'] == '전월 대비 기온 하락폭') & (summary['질병'] == '감기'), '당월'].dropna()
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

    # 3-6. 지표별로 그림을 나누고, 한 그림 안에서 감기와 인플루엔자를 비교한다.
    if plot:
        first_month = h2_monthly['년월'].min().strftime('%Y-%m')
        last_month = h2_monthly['년월'].max().strftime('%Y-%m')
        period = f'{first_month}~{last_month}'
        positions = np.arange(len(REGIONS))[::-1]
        # 지표·질병마다 색을 달리하고, 진한 색은 상위, 연한 색은 하위 그룹에 사용한다.
        chart_colors = {
            '전월 대비 기온 하락률': {
                '감기': ('#A8461C', '#E9A579'),
                '인플루엔자': ('#275591', '#9ABBE3'),
            },
            '월평균 일교차율': {
                '감기': ('#147268', '#88C7B5'),
                '인플루엔자': ('#6B418F', '#C7AADF'),
            },
        }
        chart_notes = {
            '전월 대비 기온 하락률': '기온이 내려간 달끼리 비교',
            '월평균 일교차율': '두 질병의 당월 환자 수가 있는 전체 월에서 비교',
        }

        for metric in rate_columns:
            fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.8), sharey=True)
            fig.suptitle(f'{metric} 상·하위 월의 진료 환자 수', fontsize=20, fontweight='bold', y=0.975)
            fig.text(0.5, 0.905, f'{period} · 지역별로 선정한 달의 당월 환자 수를 평균', ha='center', fontsize=11)
            fig.supxlabel('선정된 달의 평균 진료 환자 수 (명)', y=0.067, fontsize=11)

            metric_averages = averages[averages['지표'] == metric].set_index('지역')
            upper = metric_averages[metric_averages['구분'] == '상위'].reindex(REGIONS)
            lower = metric_averages[metric_averages['구분'] == '하위'].reindex(REGIONS)
            for ax, disease in zip(axes, DISEASES):
                patient_column = f'{disease} 환자수'
                upper_color, lower_color = chart_colors[metric][disease]
                groups = [('상위', upper, 0.19, upper_color), ('하위', lower, -0.19, lower_color)]
                for label, group, offset, color in groups:
                    counts = group[patient_column].to_numpy(dtype=float, na_value=np.nan)
                    bars = ax.barh(
                        positions + offset, counts, height=0.34, color=color,
                        label=f'{label} {group_size}개월',
                    )
                    labels = [f'{count:,.0f}' if pd.notna(count) else '' for count in counts]
                    ax.bar_label(bars, labels=labels, padding=4, fontsize=9)
                ax.set_yticks(positions, REGIONS)
                ax.set_title(disease, fontsize=14, fontweight='bold', pad=26)
                ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1), ncol=2, frameon=False)
                ax.xaxis.set_major_formatter('{x:,.0f}')
                ax.tick_params(axis='y', labelleft=True)
                ax.margins(x=0.19)
                ax.set_axisbelow(True)
                ax.grid(axis='x', alpha=0.23)

            fig.text(0.5, 0.020, f'{chart_notes[metric]} · 가로축 눈금은 질병별로 다름', ha='center', fontsize=10)
            fig.tight_layout(rect=(0.015, 0.09, 0.985, 0.875), w_pad=2.0)
            metric_name = metric.replace(' ', '')
            output_path = SCRIPT_DIR / f'가설2_{metric_name}_상하위{group_size}개월_환자수비교.png'
            fig.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print('그림 저장 위치', output_path)

# 4. 네 지표의 월별 추이를 실제 단위로 그린다.
reported = h2_monthly.dropna(subset=['환자수'])
if plot and not reported.empty:
    first_month, last_month = reported['년월'].min(), reported['년월'].max()
    trend_months = pd.date_range(first_month, last_month, freq='MS')
    period = f'{first_month:%Y-%m}~{last_month:%Y-%m}'
    trend_panels = [
        (label, weather, column, '%', color)
        for (label, column), color in zip(rate_columns.items(), ['#146496', '#A1511E'])
    ] + [
        (f'{disease} 진료 환자 수', reported.loc[reported['질병'].eq(disease)], '환자수', '명', color)
        for disease, color in zip(DISEASES, ['#147761', '#824984'])
    ]
    fig, axes = plt.subplots(2, 2, num='기온 변화율과 진료 환자 수', figsize=(14, 8.3), sharex=True)
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.17, top=0.82, hspace=0.50, wspace=0.30)
    fig.suptitle('기온 변화율과 진료 환자 수의 월별 추이', fontsize=24, fontweight='bold', y=0.965)
    fig.text(0.5, 0.900, f'{period}  ·  서울·대전·광주·대구·부산·인천의 월별 중앙값', ha='center', fontsize=13)

    for ax, (label, data, column, unit, color) in zip(axes.flat, trend_panels):
        # 같은 6개 지역을 비교할 수 있도록 한 지역이라도 빠진 지표·월은 비워 둔다.
        regional = data.pivot(index='년월', columns='지역', values=column)
        regional = regional.reindex(index=trend_months, columns=REGIONS)
        medians = regional.median(axis=1, skipna=False)
        ax.plot(medians.index, medians, color=color, linewidth=2.0, marker='o', markersize=4)
        ax.set_title(f'{label} ({unit})', loc='left', fontsize=14, color=color, fontweight='bold', pad=10)
        if label == cooling_label:
            ax.axhline(0, color='#64748B', linewidth=0.9)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=unit == '명'))
        ax.yaxis.set_major_formatter('{x:,.0f}' if unit == '명' else '{x:.1f}')
        ax.xaxis.set_major_locator(MonthLocator(bymonth=(1, 4, 7, 10)))
        ax.xaxis.set_major_formatter(DateFormatter('%y.%m'))
        ax.tick_params(axis='x', labelbottom=True)
        ax.tick_params(length=0, pad=7, colors='#334155')
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis='y', color='#E2E8F0')

    date_padding = pd.Timedelta(days=10)
    axes[0, 0].set_xlim(first_month - date_padding, last_month + date_padding)
    fig.text(
        0.5, 0.065,
        '하락률의 양수는 기온 하락, 음수는 상승을 뜻합니다. 전월 기온이 없으면 하락률을 표시하지 않습니다.\n'
        '하락률은 전월 평균기온(K), 일교차율은 당월 평균최저기온(K) 기준입니다. 환자 수는 요양기관 소재지 기준입니다.',
        ha='center', va='center', fontsize=11, color='#334155', linespacing=1.6,
    )
    output_path = SCRIPT_DIR / '지역별_월별_기온변화율.png'
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    print('그림 저장 위치', output_path)

    # 5. 지역 안에서 계산한 상관계수와 표본 수를 표시한다.
    fig, axes = plt.subplots(1, 2, num='기온 변화율과 환자 수의 순위상관', figsize=(14, 8.5), sharey=True)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.78, bottom=0.24, wspace=0.18)
    fig.suptitle('기온 변화율과 진료 환자 수의 지역별 상관관계', fontsize=24, fontweight='bold', y=0.966)
    fig.text(0.5, 0.902, f'{period} 월별 자료  ·  스피어만 순위상관계수 ρ', ha='center', fontsize=13)

    comparisons = pd.MultiIndex.from_product([DISEASES, patient_timings])
    row_labels = [*REGIONS, '지역 중앙값']
    axes[0].set_yticks(range(len(row_labels)), row_labels)
    axes[0].get_yticklabels()[-1].set_fontweight('bold')
    cmap = plt.get_cmap('RdBu_r').with_extremes(bad='#F1F5F9')
    for ax, (metric, sample_label) in zip(axes, [(cooling_label, '기온 하락 월만'), (range_label, '전체 유효 월')]):
        regional = summary.loc[summary['지표'].eq(metric)].set_index(['지역', '질병'])
        coefficients = regional[list(patient_timings)].unstack('질병').swaplevel(axis=1)
        coefficients = coefficients.reindex(index=REGIONS, columns=comparisons)
        counts = regional['n'].unstack('질병').reindex(index=REGIONS, columns=DISEASES, fill_value=0).fillna(0)
        region_counts = coefficients.count()
        coefficients.loc['지역 중앙값'] = coefficients.median()
        heatmap = ax.imshow(coefficients, cmap=cmap, vmin=-1, vmax=1, aspect='auto')

        ax.set_title(f'{metric}  |  {sample_label}', fontsize=14, fontweight='bold', pad=12)
        ax.set_xticks(range(len(comparisons)), [f'{disease}\n{timing}' for disease, timing in comparisons])
        ax.tick_params(axis='both', length=0, pad=8, labelsize=11, colors='#334155')
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.axvline(len(patient_timings) - 0.5, color='white', linewidth=1.8)
        ax.axhline(len(REGIONS) - 0.5, color='#475569', linewidth=1.4)

        for (row, col), value in np.ndenumerate(coefficients.to_numpy()):
            label = f'{value:+.2f}' if np.isfinite(value) else '산출 불가'
            if row < len(REGIONS):
                disease, _ = comparisons[col]
                label = f'{label}\n(n={counts.loc[REGIONS[row], disease]:.0f})'
            else:
                label = f'{label}\n({region_counts.iloc[col]}곳)'
            ax.text(
                col, row, label, ha='center', va='center', fontsize=11,
                fontweight='bold' if row == len(REGIONS) else 'normal',
                color='white' if abs(value) >= 0.68 else '#1E293B',
            )

    colorbar_ax = fig.add_axes((0.34, 0.125, 0.40, 0.021))
    colorbar = fig.colorbar(heatmap, cax=colorbar_ax, orientation='horizontal', ticks=[-1, -0.5, 0, 0.5, 1])
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(length=0, pad=4)
    colorbar.set_label('음의 상관  ←  ρ  →  양의 상관')
    fig.text(
        0.5, 0.038,
        'n은 같은 지역에서 당월·다음 달 자료를 모두 짝지을 수 있는 기준 월 수입니다.\n'
        '지역 중앙값은 지역별 ρ의 중앙값입니다. 계절성과 유행 시기의 영향이 포함될 수 있습니다.',
        ha='center', va='center', fontsize=11, color='#334155', linespacing=1.6,
    )
    output_path = SCRIPT_DIR / '가설2_지역별_기온변화율_환자수_상관관계.png'
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    print('그림 저장 위치', output_path)

if plot:
    plt.show()

print("***********\n**********\n********************")
print(monthly.to_string(index=False))
