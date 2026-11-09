# 가설 1: 지역별로 기온이 비슷한 봄과 가을의 호흡질환 환자수 비교
# 사용할 자료: SHW/wook 안의 날씨 CSV 6개, 지역별 질병 XLSX 4개
# 진행 순서: 한 지역의 날씨 전처리 → 그 지역 환자수 전처리 → 봄·가을 비교 → 다음 지역
# 6개 지역의 기온을 한 표로 합치거나 평균내지 않고 각각 따로 처리한다.
# 함수(def)나 main() 없이 위에서 아래로 실행한다.
# 중간 표는 print(), head(), info()로 확인하며, 전체 표는 지역별 CSV로 저장한다.
# 분석 기간은 날씨·환자수 모두 2024년 1월~2025년 12월이며 같은 연도 안에서만 비교한다.
# 날씨 파일에는 2024년과 2025년 각각 1~12월, 총 24개월의 평균기온이 있어야 한다.
# 필요한 패키지가 없다면 터미널에서 설치: python -m pip install pandas openpyxl matplotlib


# ==================== [0. 실제 파일 경로 확인] ====================

# 0-1. 경로를 다루는 시점에 Path를 불러온다.
from pathlib import Path

# 현재 파일: team261103/SHW/regional_analysis.py
# parent는 SHW 폴더이므로 parent / 'wook'으로 실제 원본 폴더를 지정한다.
# resolve()로 절대 경로를 계산하여 실행 버튼을 누른 위치에 영향을 받지 않도록 한다.
# 프로젝트를 다른 위치로 옮겨도 SHW/wook 폴더 구조를 유지하면 같은 코드로 실행할 수 있다.
script_path = Path(__file__).resolve()
data_path = script_path.parent / 'wook'
result_path = script_path.parents[1] / 'regional_results'

print('\n[0-1] 입력·출력 경로 확인')
print('현재 코드:', script_path)
print('원본 폴더:', data_path)
print('결과 폴더:', result_path)

# 0-2. 실제 파일 이름을 그대로 지정한다.
# 광주 파일 이름은 2024~206광주날씨.csv이다. 원본을 바꾸지 않고 이 이름으로 읽는다.
weather_files = {
    '서울': '2024~2026서울날씨.csv',
    '부산': '2024~2026부산날씨.csv',
    '인천': '2024~2026인천날씨.csv',
    '대구': '2024~2026대구날씨.csv',
    '광주': '2024~206광주날씨.csv',
    '대전': '2024~2026대전날씨.csv',
}

disease_files = {
    '감기': '지역별감기.xlsx',
    '비염': '지역별비염.xlsx',
    '인플루엔자': '지역별인플루엔자.xlsx',
    '천식': '지역별환경성질환_천식.xlsx',
}

# 파일이 빠졌을 때 분석 중간이 아니라 시작할 때 정확한 경로를 알려준다.
for file_name in list(weather_files.values()) + list(disease_files.values()):
    path = data_path / file_name
    print('확인:', path)
    if not path.is_file():
        raise FileNotFoundError(f'원본 파일을 찾을 수 없습니다: {path}')

# 0-3. 원본 파일에 다른 연도가 있어도 아래 두 날짜 안의 자료만 분석·저장한다.
analysis_start = '2024-01-01'
analysis_end = '2025-12-31'

# 이번 조건은 2.0도 '미만'이다. 기온 차이가 정확히 2.0도인 비교 조합은 포함하지 않는다.
max_temperature_difference = 2.0
show_graph = True  # 그래프 창 없이 표와 그림 파일만 저장하려면 False로 변경한다.
print('분석 기간:', analysis_start, '~', analysis_end)


# ==================== [1. 지역별 분석 준비] ====================

# 표를 읽고 전처리하는 시점에 pandas를 불러온다.
import pandas as pd

pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.max_columns', 20)

# 결과를 지역별로 따로 보관한다. 지역 사이에 표를 합치는 작업은 하지 않는다.
# 예: 실행 후 weather_by_region['서울']을 출력하면 서울 날씨만 볼 수 있다.
weather_by_region = {}
patients_by_region = {}
combinations_by_region = {}
comparison_by_region = {}
summary_by_region = {}

# 아래 반복문은 서울의 모든 과정을 마친 뒤 부산, 인천 등의 순서로 진행한다.
# 아래 각 단계는 현재 region에 해당하는 자료만 사용한다.
for region, weather_file in weather_files.items():
    print('\n' + '=' * 90)
    print(f'[{region}] 지역 분석 시작')
    print('=' * 90)

    region_result_path = result_path / region
    region_result_path.mkdir(parents=True, exist_ok=True)


    # ==================== [2. 현재 지역의 날씨 전처리] ====================

    # 2-1. 실제 wook CSV는 cp949이며 첫 행이 바로 열 이름이다.
    # 전국 원본과 다르게 설명 7행이 없으므로 skiprows=7을 사용하지 않는다.
    df = pd.read_csv(data_path / weather_file, encoding='cp949')
    df.columns = df.columns.str.strip()

    print(f'\n[2-1] {region} 날씨 원본')
    print(df.head())
    df.info()

    # 2-2. 분석에 사용할 년월·평균기온만 복사한다.
    # 최저·최고기온을 평균기온과 섞지 않는다.
    df_temp = df[['년월', '평균기온(℃)']].copy()

    # 2-3. wook의 날짜는 1-24, 2-24 형식이다. 먼저 앞뒤 공백을 제거한다.
    # %m-%y는 월-두 자리 연도라는 뜻이다. 1-24는 2024-01-01로 변환된다.
    # errors='coerce'는 변환에 실패한 날짜를 NaT로 만들어 아래에서 확인하게 한다.
    df_temp['년월'] = pd.to_datetime(
        df_temp['년월'].astype('string').str.strip(),
        format='%m-%y', errors='coerce'
    )

    # 2-4. 평균기온을 숫자로 변환한다. 변환되지 않은 값은 NaN으로 남긴다.
    df_temp['평균기온(℃)'] = pd.to_numeric(
        df_temp['평균기온(℃)'].astype('string').str.strip(), errors='coerce'
    )

    print(f'\n[2-4] {region} 날짜·기온 변환 결과')
    print(df_temp.head())
    df_temp.info()

    # 2-5. 결측 행을 먼저 출력한 뒤 분석에서 제외한다. 0이나 평균으로 채우지 않는다.
    missing_weather = df_temp[df_temp[['년월', '평균기온(℃)']].isna().any(axis=1)]
    print(f'\n[2-5] {region} 날짜 또는 평균기온 결측 행')
    print(missing_weather)
    df_temp = df_temp.dropna(subset=['년월', '평균기온(℃)']).copy()

    # 날짜를 변환한 뒤 2024년 1월~2025년 12월만 남긴다.
    # 이 시점부터 봄·가을 추출, 결과 저장, 그래프에 다른 연도가 들어가지 않는다.
    df_temp = df_temp[df_temp['년월'].between(analysis_start, analysis_end)].copy()
    print(f'\n[2-5] {region} 분석 기간 제한: 2024~2025년만 사용')
    print(df_temp.head())
    print(df_temp.tail())

    # 같은 지역에서 같은 월이 두 번 있으면 비교 조합이 부풀려지므로 확인한다.
    duplicate_weather = df_temp[df_temp.duplicated('년월', keep=False)]
    print(f'\n[2-5] {region} 중복 월 확인')
    print(duplicate_weather)
    if not duplicate_weather.empty:
        raise ValueError(f'{region}: 같은 월의 기온이 여러 행입니다. 원본을 확인하세요.')
    if df_temp.empty:
        raise ValueError(f'{region}: 전처리 후 사용할 기온 자료가 없습니다.')

    # 2-6. 지역 열을 추가하고 날짜순으로 정렬한다.
    df_temp['지역'] = region
    df_temp = df_temp[['지역', '년월', '평균기온(℃)']]
    df_temp = df_temp.sort_values('년월').reset_index(drop=True)

    print(f'\n[2-6] {region} 날씨 전처리 완료 — 전체 월 확인')
    print(df_temp.to_string(index=False))
    print('날씨 기간:', df_temp['년월'].min(), '~', df_temp['년월'].max())
    print('날씨 개월 수:', len(df_temp))
    df_temp.info()

    # 원본의 마지막 관측일이 아닌 설정한 24개월 전체를 기준으로 누락을 확인한다.
    # 2024년과 2025년에 각각 1~12월 자료가 모두 있는지 확인한 뒤 비교를 진행한다.
    expected_months = pd.date_range(analysis_start, analysis_end, freq='MS')
    missing_months = expected_months.difference(df_temp['년월'])
    print('날씨 누락 월:', missing_months.strftime('%Y-%m').tolist())
    print('연도별 날씨 개월 수 (각 연도 12개월 필요):')
    print(df_temp.groupby(df_temp['년월'].dt.year).size().reindex([2024, 2025], fill_value=0))
    if not missing_months.empty:
        raise ValueError(
            f'{region}: 2024~2025년의 1~12월 자료를 모두 넣어주세요. '
            f'누락 월: {missing_months.strftime("%Y-%m").tolist()}'
        )
    weather_by_region[region] = df_temp.copy()


    # ==================== [3. 현재 지역의 환자수 전처리] ====================

    # 3-1. 질병 파일 하나에는 여러 시도의 자료가 들어 있다.
    # 성별·연령별 양식이 아니므로 현재 지역 행 하나만 추출한다.
    # 지역 기준은 환자 거주지가 아니라 '요양기관 소재지'라는 점을 해석에 반영한다.
    # 원본의 '계' 행을 지역 행과 합산하지 않는다.
    patient_list = []

    for disease, disease_file in disease_files.items():
        raw = pd.read_excel(data_path / disease_file, header=None)

        print(f'\n[3-1] {region} / {disease} 엑셀 원본 앞부분')
        print(raw.iloc[:8, :8])
        print('원본 크기:', raw.shape)

        # 3-2. 실제 엑셀 구조를 기준으로 읽는다. iloc은 0부터 시작한다.
        # raw.iloc[2]: 진료년월 행 (엑셀 3행)
        # raw.iloc[3]: 환자수·내원일수 등의 지표 행 (엑셀 4행)
        # raw.iloc[:, 1]: 요양기관소재지구분(시도) 열 (엑셀 B열)
        # raw.iloc[3]에서 환자수 열만 고르므로 청구건수·진료비는 가져오지 않는다.
        patient_cols = raw.columns[
            raw.iloc[3].astype(str).str.strip().eq('환자수')
        ]
        region_names = raw.iloc[:, 1].astype(str).str.strip()
        rows = region_names.eq(region)

        print(f'\n[3-2] {region} / {disease} 지역 행 수:', rows.sum())
        print('환자수 월별 열 개수:', len(patient_cols))
        if rows.sum() != 1 or len(patient_cols) == 0:
            raise ValueError(f'{disease_file}: {region} 행 또는 환자수 열을 확인하세요.')

        # 3-3. 현재 지역 이름과 월별 환자수만 남긴다.
        data = raw.loc[rows, [1] + patient_cols.tolist()].copy()
        months = raw.iloc[2].ffill()
        data.columns = ['지역'] + months.loc[patient_cols].tolist()

        print(f'\n[3-3] {region} / {disease} 환자수만 추출 — 앞 6개월')
        print(data.iloc[:, :7].to_string(index=False))

        # 3-4. 가로 월별 표를 세로 표로 바꾼다.
        # 변환 전: 지역 | 2024년 01월 | 2024년 02월 | ...
        # 변환 후: 지역 | 년월 | 환자수
        data = data.melt(id_vars='지역', var_name='년월', value_name='환자수')
        data['년월'] = pd.to_datetime(
            data['년월'].astype(str).str.strip(), format='%Y년 %m월'
        )

        # 환자수도 날씨와 동일하게 2024~2025년만 남긴다.
        # 이후 출력하는 환자수 표, 비교표, 요약표에는 이 기간의 자료만 사용한다.
        data = data[data['년월'].between(analysis_start, analysis_end)].copy()
        data['환자수'] = pd.to_numeric(
            data['환자수'].astype('string').str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        )
        data['질병'] = disease
        data = data[['지역', '년월', '질병', '환자수']].sort_values('년월')

        print(f'\n[3-4] {region} / {disease} 날짜·숫자 변환 결과')
        print(data.head())
        print(data.tail())
        data.info()
        print('환자수 결측 행:')
        print(data[data['환자수'].isna()])
        if data['환자수'].lt(0).any():
            raise ValueError(f'{region}/{disease}: 음수 환자수를 확인하세요.')

        # 같은 월이 중복되면 임의로 합하지 않고 원본을 확인한다.
        if data.duplicated(['지역', '년월', '질병']).any():
            raise ValueError(f'{region}/{disease}: 중복 월이 있습니다.')
        patient_list.append(data)

    # 3-5. 현재 지역의 네 질병만 아래로 이어 붙인다. 다른 지역과는 합치지 않는다.
    patients = pd.concat(patient_list, ignore_index=True)
    patients = patients.sort_values(['질병', '년월']).reset_index(drop=True)
    patients_by_region[region] = patients.copy()

    print(f'\n[3-5] {region} 네 질병 전처리 완료')
    print(patients.head(12))
    print(patients.groupby('질병')['년월'].agg(['min', 'max', 'count']))
    patients.info()


    # ==================== [4. 같은 연도의 봄·가을 기온 비교 조합 찾기] ====================

    # 4-1. 현재 지역 날씨에서 봄(3,4,5월)과 가을(9,10,11월)을 추출한다.
    # 앞에서 기간을 제한했으므로 2024~2025년 자료만 사용한다.
    # 각 연도의 봄 3개월과 가을 3개월을 비교하므로 조건 적용 전에는 연도별 9개 조합이다.
    # 12월은 전체 날씨 표에는 남기지만 봄·가을 비교에는 포함하지 않는다.
    temp = df_temp[['년월', '평균기온(℃)']].copy()
    temp['연도'] = temp['년월'].dt.year
    spring = temp[temp['년월'].dt.month.isin([3, 4, 5])].rename(
        columns={'년월': '봄_년월', '평균기온(℃)': '봄_평균기온'}
    )
    autumn = temp[temp['년월'].dt.month.isin([9, 10, 11])].rename(
        columns={'년월': '가을_년월', '평균기온(℃)': '가을_평균기온'}
    )

    print(f'\n[4-1] {region} 봄 기온')
    print(spring.to_string(index=False))
    print(f'\n[4-1] {region} 가을 기온')
    print(autumn.to_string(index=False))
    print('연도별 가을 개월 수 (9·10·11월, 각 연도 3개월):')
    print(autumn.groupby('연도').size().reindex([2024, 2025], fill_value=0))

    # 4-2. '연도'를 기준으로 연결하여 같은 연도 안에서만 모든 월 조합을 만든다.
    # 예: 2024년 4월과 2024년 10월은 비교하지만 2025년 10월과는 비교하지 않는다.
    # 다른 지역 자료는 현재 temp에 없으므로 지역끼리 섞이지 않는다.
    candidates = spring.merge(autumn, on='연도', how='inner')
    candidates['지역'] = region
    candidates['기온차이'] = (
        candidates['봄_평균기온'] - candidates['가을_평균기온']
    ).abs().round(3)

    # round(3)은 실수 계산 오차 때문에 정확히 2.0도가 1.99999...가 되는 것을 막는다.
    # 원본 기온은 소수 첫째 자리까지 있으므로 이 반올림으로 원본 정밀도를 잃지 않는다.
    print(f'\n[4-2] {region} 같은 연도 내 모든 봄·가을 조합과 기온 차이')
    print(candidates.to_string(index=False))
    print('동일 연도 내 전체 조합 수:', len(candidates))
    print(candidates.groupby('연도').size().reset_index(name='전체_조합수'))

    # 4-3. 절대 기온 차이가 2.0도 미만인 조합을 '전부' 남긴다.
    # 기존 used_months 방식처럼 같은 달의 재사용을 막지 않는다.
    # 따라서 봄의 한 달이 가을의 여러 달과 조건을 만족하면 모두 결과에 들어간다.
    similar_months = candidates[
        candidates['기온차이'] < max_temperature_difference
    ].sort_values(['봄_년월', '가을_년월']).reset_index(drop=True)
    similar_months.insert(0, '비교번호', range(1, len(similar_months) + 1))
    similar_months = similar_months[
        ['지역', '연도', '비교번호', '봄_년월', '봄_평균기온', '가을_년월', '가을_평균기온', '기온차이']
    ]
    combinations_by_region[region] = similar_months.copy()

    print(f'\n[4-3] {region} 기온 차이 2.0도 미만인 모든 비교 조합')
    print(similar_months.to_string(index=False))
    print('조건에 맞는 비교 조합 수:', len(similar_months))
    print('연도별 비교 조합 수 (0이면 조건에 맞는 조합 없음):')
    print(similar_months.groupby('연도').size().reindex([2024, 2025], fill_value=0))

    # 날씨 결과와 환자수는 조건에 맞는 비교 조합 유무와 관계없이 저장한다.
    df_temp.to_csv(region_result_path / '01_날씨_전처리.csv', index=False, encoding='utf-8-sig')
    patients.to_csv(region_result_path / '02_환자수_전처리.csv', index=False, encoding='utf-8-sig')
    candidates.to_csv(region_result_path / '03_봄가을_전체조합.csv', index=False, encoding='utf-8-sig')
    similar_months.to_csv(region_result_path / '04_기온차이_2도미만.csv', index=False, encoding='utf-8-sig')

    if similar_months.empty:
        print(f'{region}: 조건에 맞는 비교 조합이 없어 이 지역의 환자 비교·그래프를 건너뜁니다.')
        continue


    # ==================== [5. 각 비교 조합에 해당하는 환자수 연결] ====================

    # 5-1. 각 질병에 대해 선택된 봄·가을 날짜의 환자수를 연결한다.
    # 현재 지역의 patients만 사용하므로 서울 날씨에 부산 환자수가 붙지 않는다.
    comparison_list = []
    for disease in disease_files:
        monthly_patients = patients[patients['질병'].eq(disease)][['년월', '환자수']].copy()

        spring_patients = monthly_patients.rename(
            columns={'년월': '봄_년월', '환자수': '봄_환자수'}
        )
        autumn_patients = monthly_patients.rename(
            columns={'년월': '가을_년월', '환자수': '가을_환자수'}
        )

        comparison = similar_months.merge(
            spring_patients, on='봄_년월', how='left', validate='many_to_one'
        )
        comparison = comparison.merge(
            autumn_patients, on='가을_년월', how='left', validate='many_to_one'
        )
        comparison['질병'] = disease

        # 5-2. 환자 자료가 없는 월은 NaN으로 남긴다. 0명으로 바꾸지 않는다.
        # 두 자료 모두 이미 2024~2025년으로 제한한 상태다.
        # 기온 조건을 만족해도 양쪽 환자수가 모두 있어야 실제 환자수 비교가 가능하다.
        comparison['환자수_비교가능'] = comparison[['봄_환자수', '가을_환자수']].notna().all(axis=1)
        comparison['봄-가을_환자수차이'] = comparison['봄_환자수'] - comparison['가을_환자수']

        print(f'\n[5-2] {region} / {disease} 기온이 비슷한 달의 환자수 전체 확인')
        print(comparison.to_string(index=False))
        comparison_list.append(comparison)

    # 5-3. 같은 지역의 네 질병 비교표를 모은다.
    comparison = pd.concat(comparison_list, ignore_index=True)
    comparison_by_region[region] = comparison.copy()
    missing_comparison = comparison[~comparison['환자수_비교가능']].copy()
    valid_comparison = comparison[comparison['환자수_비교가능']].copy()

    print(f'\n[5-3] {region} 환자수 누락으로 비교할 수 없는 비교 조합')
    print(missing_comparison[
        ['지역', '질병', '봄_년월', '가을_년월', '봄_환자수', '가을_환자수']
    ].to_string(index=False))
    print('전체 질병별 비교 행:', len(comparison))
    print('환자수 비교 가능 행:', len(valid_comparison))
    print('환자수 비교 불가 행:', len(missing_comparison))
    comparison.info()

    comparison.to_csv(region_result_path / '05_환자수_연결전체.csv', index=False, encoding='utf-8-sig')
    valid_comparison.to_csv(region_result_path / '06_환자수_비교가능.csv', index=False, encoding='utf-8-sig')
    missing_comparison.to_csv(region_result_path / '07_환자수_비교불가.csv', index=False, encoding='utf-8-sig')

    if valid_comparison.empty:
        print(f'{region}: 양쪽 환자수를 모두 확인할 수 없어 요약·그래프를 건너뜁니다.')
        continue


    # ==================== [6. 질병별 차이 요약] ====================

    # 6-1. 양쪽 환자수가 있는 비교 조합에서만 평균 차이와 봄 환자수가 더 많은 비율을 구한다.
    # 차이가 양수면 봄이 많고 음수면 가을이 많다. 0이면 두 달의 환자수가 같다.
    valid_comparison['봄이_더많음'] = valid_comparison['봄-가을_환자수차이'] > 0
    summary = valid_comparison.groupby('질병', as_index=False).agg(
        비교_조합수=('비교번호', 'count'),
        봄_평균환자수=('봄_환자수', 'mean'),
        가을_평균환자수=('가을_환자수', 'mean'),
        평균차이=('봄-가을_환자수차이', 'mean'),
        봄이_더많은_비율=('봄이_더많음', 'mean')
    )
    summary['봄이_더많은_비율'] = summary['봄이_더많은_비율'] * 100
    summary.insert(0, '지역', region)
    summary_by_region[region] = summary.copy()

    print(f'\n[6-1] {region} 질병별 요약 — 비율 단위는 %')
    print(summary.to_string(index=False))
    summary.to_csv(region_result_path / '08_질병별_요약.csv', index=False, encoding='utf-8-sig')

    # 모든 조합을 남겼기 때문에 같은 월의 환자수가 여러 비교 조합에서 반복 사용될 수 있다.
    # 따라서 이 평균은 '선택된 비교 조합의 평균'이며 독립적인 월별 표본의 평균이 아니다.
    # 합계로 고유 환자수를 계산하거나 비교 조합 개수를 독립 표본 수로 해석하지 않는다.
    print('주의: 같은 월이 여러 비교 조합에 들어가므로 요약은 선택된 비교 조합 기준의 탐색 결과입니다.')


    # ==================== [7. 현재 지역의 비교 조합별 그래프] ====================

    # 그래프를 실제로 그리는 시점에 필요한 라이브러리를 불러온다.
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, StrMethodFormatter
    from matplotlib.patches import Patch

    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False

    # 7-1. 날짜를 길게 기울여 쓰는 대신 가로 막대 왼쪽에 수평으로 표시한다.
    # 같은 연도의 봄·가을을 한 줄에 두고 그 아래에 기온을 표시한다.
    # 네 질병은 각각의 패널로 나누고, 모든 패널에서 봄·가을 색상을 통일한다.
    spring_color = '#D9944C'
    autumn_color = '#4B85AB'
    # 11월을 포함해 비교 조합이 늘어나면 그림 높이도 늘려 날짜와 숫자가 겹치지 않게 한다.
    figure_height = max(9, 4 + len(similar_months))
    fig, axes = plt.subplots(2, 2, figsize=(16, figure_height), facecolor='white')

    for ax, disease in zip(axes.flat, disease_files):
        data = valid_comparison[valid_comparison['질병'].eq(disease)].copy()
        data = data.sort_values(['연도', '봄_년월', '가을_년월']).reset_index(drop=True)
        if data.empty:
            ax.text(0.5, 0.5, '비교 가능한 환자수 없음', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(disease, loc='left', fontsize=14)
            ax.set_axis_off()
            continue

        data['비교기간'] = (
            data['연도'].astype(str) + '년  '
            + data['봄_년월'].dt.month.astype(str) + '월 / '
            + data['가을_년월'].dt.month.astype(str) + '월'
            + '\n' + data['봄_평균기온'].astype(str) + '℃ / '
            + data['가을_평균기온'].astype(str) + '℃'
        )

        # 7-2. 같은 비교 조합의 봄·가을 막대를 위아래로 나란히 그린다.
        # 환자수는 평균내지 않고 해당 월의 실제 숫자를 그대로 표시한다.
        positions = list(range(len(data)))
        spring_bars = ax.barh(
            [position - 0.17 for position in positions],
            data['봄_환자수'].astype(float), height=0.28, color=spring_color
        )
        autumn_bars = ax.barh(
            [position + 0.17 for position in positions],
            data['가을_환자수'].astype(float), height=0.28, color=autumn_color
        )

        # 7-3. 막대 끝에는 천 단위 쉼표를 넣은 환자수를 표시한다.
        # 오른쪽 여백을 두어 숫자가 그래프 밖으로 잘리지 않도록 한다.
        ax.bar_label(spring_bars, labels=[f'{value:,.0f}' for value in data['봄_환자수']], padding=6, fontsize=10)
        ax.bar_label(autumn_bars, labels=[f'{value:,.0f}' for value in data['가을_환자수']], padding=6, fontsize=10)
        max_patients = float(data[['봄_환자수', '가을_환자수']].max().max())
        ax.set_xlim(0, max(max_patients * 1.28, 1))
        # 비교 조합이 한두 개여도 막대가 과하게 두꺼워지지 않도록 위아래 여백을 둔다.
        row_padding = max(0, (3 - len(data)) / 2)
        ax.set_ylim(len(data) - 0.5 + row_padding, -0.5 - row_padding)
        ax.set_yticks(positions, labels=data['비교기간'])
        ax.set_title(disease, loc='left', fontsize=15, fontweight='bold', pad=16, color='#253343')
        ax.set_xlabel('진료 환자 수 (명)', fontsize=10, color='#66717D', labelpad=10)

        # 7-4. 눈금은 간결하게 하고 연한 세로 격자만 남긴다.
        # 질병마다 환자수 규모가 달라 패널별 가로축 범위는 따로 사용한다.
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        ax.set_axisbelow(True)
        ax.grid(axis='x', color='#E8ECF0', linewidth=0.8)
        ax.tick_params(axis='y', length=0, pad=12, labelsize=10)
        ax.tick_params(axis='x', length=0, pad=8, labelsize=9, colors='#66717D')
        for side in ['top', 'right', 'left']:
            ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color('#D8DFE6')

    # 7-5. 제목·설명·범례는 그림 전체에 한 번만 표시한다.
    # 비교번호 대신 실제 연도와 월을 보여주어 표를 따로 찾지 않아도 읽을 수 있게 한다.
    fig.suptitle(f'{region} | 봄·가을 호흡질환 비교', x=0.5, y=0.97, fontsize=22, fontweight='bold', color='#253343')
    fig.text(0.5, 0.915, '2024–2025 · 같은 연도 · 월평균기온 차이 2.0℃ 미만', ha='center', fontsize=12, color='#66717D')
    fig.legend(
        handles=[Patch(facecolor=spring_color, label='봄'), Patch(facecolor=autumn_color, label='가을')],
        loc='upper center', bbox_to_anchor=(0.5, 0.89), ncol=2, frameon=False, fontsize=12
    )
    fig.text(0.5, 0.025, '자료: 요양기관 소재지별 월별 진료 환자 수  |  봄 3~5월 · 가을 9~11월  |  질병별 가로축 범위가 다릅니다.',
             ha='center', fontsize=10, color='#66717D')
    fig.subplots_adjust(left=0.15, right=0.97, top=0.79, bottom=0.11, wspace=0.65, hspace=0.6)
    graph_path = region_result_path / '09_봄가을_환자수비교.png'
    fig.savefig(graph_path, dpi=150)
    print(f'\n[7-2] {region} 그래프 저장:', graph_path)

    if show_graph:
        plt.show()
    plt.close(fig)
    print(f'\n[{region}] 분석 완료. 저장 위치:', region_result_path)


# ==================== [8. 전체 실행 확인] ====================

# 각 지역의 결과는 아래처럼 개별적으로 확인할 수 있다.
# print(weather_by_region['서울'])         # 서울 월별 기온
# print(patients_by_region['부산'])        # 부산의 네 질병 월별 환자수
# print(combinations_by_region['대구'])    # 대구의 기온 차이 2.0도 미만인 모든 비교 조합
# print(comparison_by_region['광주'])      # 광주의 선택된 날짜별 환자수와 비교 가능 여부
# print(summary_by_region['대전'])        # 대전 질병별 결과 요약
# 요양기관 소재지 기준이므로 거주지별 질병 발생률로 해석하지 않는다.
# 같은 연도라도 계절별 유행 등 다른 요인이 있으므로 기온만으로 차이의 원인을 단정하지 않는다.
print('\n[8] 6개 지역의 개별 분석 종료')
print('결과 폴더:', result_path)
for region in weather_files:
    print(region, ': 날씨', len(weather_by_region[region]), '개월 / 기온 조건 만족',
          len(combinations_by_region[region]), '비교 조합')
