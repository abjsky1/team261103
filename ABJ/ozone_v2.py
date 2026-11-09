# 가설02. 
# 오존이 많아지는 여름에 호흡기 질환 환자수는 늘어날 것이다.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import requests
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
import httpx
import xmltodict
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
import warnings
import os

# 1. 폰트 경로 설정
font_path = r'C:\USERS\ABJSK\APPDATA\LOCAL\MICROSOFT\WINDOWS\FONTS\GMARKETSANSTTFLIGHT.TTF'

# 2. Matplotlib 폰트 매니저에 폰트 강제 추가 (핵심)
fm.fontManager.addfont(font_path)

# 3. 폰트 이름 가져오기 및 글로벌 설정 적용
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)
plt.rcParams['axes.unicode_minus'] = False

# 3. Seaborn 테마 설정에 추출한 font_name 적용 및 마이너스 깨짐 방지
sns.set_theme(font=font_name, rc={'axes.unicode_minus': False}, style='whitegrid')

pd.set_option('display.unicode.east_asian_width', True)


#==========================================================

url = "https://www.airkorea.or.kr/web/realSearch?pMENU_NO=97"

# 표의 1~6번 칸 순서대로 항목 이름
item_names = ["PM10", "PM2.5", "오존", "이산화질소", "일산화탄소", "아황산가스"]

# 2024-01 ~ 2026-03, 27개월
month_list = pd.period_range("2024-01", "2026-03", freq="M")

# 17개 시도: (지역 이름, 시청·도청 도로명 주소)
area_list = [
    ("서울", "서울특별시 중구 세종대로 110"),               # 서울시청
    ("부산", "부산광역시 연제구 중앙대로 1001"),             # 부산시청
    ("대구", "대구광역시 중구 공평로 88"),                   # 대구시청
    ("인천", "인천광역시 남동구 정각로 29"),                 # 인천시청
    ("광주", "광주광역시 서구 내방로 111"),                  # 광주시청
    ("대전", "대전광역시 서구 둔산로 100"),                  # 대전시청
    ("울산", "울산광역시 남구 중앙로 201"),                  # 울산시청
    ("세종", "세종특별자치시 한누리대로 2130"),              # 세종시청
    ("경기", "경기도 수원시 영통구 도청로 30"),              # 경기도청
    ("강원", "강원특별자치도 춘천시 중앙로 1"),              # 강원도청
    ("충북", "충청북도 청주시 상당구 상당로 82"),            # 충북도청
    ("충남", "충청남도 홍성군 홍북읍 충남대로 21"),          # 충남도청
    ("전북", "전북특별자치도 전주시 완산구 노송광장로 10"),     # 전주시청 (도청 측정소 오존 미측정)
    ("전남", "전라남도 목포시 양을로 203"),                  # 목포시청
    ("경북", "경상북도 안동시 풍천면 도청대로 455"),         # 경북도청
    ("경남", "경상남도 창원시 의창구 중앙대로 300"),         # 경남도청
    ("제주", "제주특별자치도 제주시 문연로 6"),              # 제주도청
]


# 측정소 바꾸기: 주소 검색 팝업 → 측정소 목록 → 첫 번째 측정소 사용
async def select_station(page, address):
    # ① 지역명 입력칸 클릭 → 팝업 열림
    async with page.expect_popup() as popup_info:
        await page.click("#s_condition_input3")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    await popup.wait_for_timeout(2000)

    # ② 팝업 검색칸에 주소 입력 후 Enter
    await popup.fill("#keyword", address)
    await popup.press("#keyword", "Enter")
    await popup.wait_for_timeout(2000)

    # ③ 첫 번째 결과 클릭
    await popup.locator("#roadAddrTd1 a").click()
    await popup.wait_for_timeout(1500)

    # ④ 주소입력 버튼 클릭 → 팝업 닫힘
    await popup.locator("a.btn-bl").click()
    await page.wait_for_timeout(2000)

    # ⑤ 지역명 검색 버튼 클릭 → 측정소 목록
    await page.locator('button[onclick^="goAreaSearch"]').click()
    await page.wait_for_timeout(3000)

    # ⑥ 첫 번째 측정소(기본 선택) 이름만 가져오기
    first_row = page.locator("tr:has(input[type='radio'])").first
    chosen_name = (await first_row.locator("td").nth(1).inner_text()).strip()
    print(f"   → 선택: {chosen_name}")

    # ⑦ 측정자료 조회 클릭
    await page.get_by_text("측정자료 조회", exact=True).click()
    await page.wait_for_timeout(3000)

    return chosen_name


# 한 측정소의 27개월 일평균 수집
async def collect_months(page, area_name, station_name):
    area_rows = []

    # 일평균 선택
    daily_radio = page.get_by_label("일평균")
    await daily_radio.check()
    await page.wait_for_timeout(1000)

    for month in month_list:
        # 그 달의 첫날, 마지막 날
        start_date = month.start_time.strftime("%Y-%m-%d")
        end_date = month.end_time.strftime("%Y-%m-%d")
        target_text = str(month)    # 예: "2024-01"

        # 날짜 입력 (사이트의 jQuery 달력 기능 사용)
        await page.evaluate(f"$('#from_date').datepicker('setDate', '{start_date}')")
        await page.evaluate(f"$('#to_date').datepicker('setDate', '{end_date}')")

        # 측정 자료 검색 버튼 클릭
        await page.locator(".btnMoum .btnBlueWhite").click()

        # 표 첫 칸 날짜가 이번 달로 바뀔 때까지 1초씩 최대 10번 기다리기
        for wait_count in range(30):
            await page.wait_for_timeout(1000)
            first_cell = await page.query_selector("#realTable tbody tr td")
            if first_cell is None:
                continue
            first_text = (await first_cell.inner_text()).strip()
            if first_text.startswith(target_text):
                break

        # 표의 모든 줄
        rows = await page.query_selector_all("#realTable tbody tr")

        for row in rows:
            tds = await row.query_selector_all("td")

            # 7칸이 안 되는 줄(자료 없음 안내 등)은 건너뛰기
            if len(tds) < 7:
                continue

            # 0번 칸: 날짜
            date_text = (await tds[0].inner_text()).strip()

            # 이번 달 날짜가 아니면 건너뛰기
            if not date_text.startswith(target_text):
                continue

            one_day = {"지역": area_name, "측정소": station_name, "날짜": date_text}

            # 1~6번 칸: 항목 이름과 짝지어 저장
            for i, name in enumerate(item_names, start=1):
                value_text = await tds[i].inner_text()
                one_day[name] = value_text.strip()

            area_rows.append(one_day)

        print(f"  {month}: 수집 완료")

    return area_rows


# 본 수집: 17개 시도 × 27개월
async def run():
    air_list = []

    async with async_playwright() as p:
        # 페이지 열기 (처음엔 화면이 안 떠서 새로고침까지)
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(3000)
        await page.reload()
        await page.wait_for_timeout(10000)

        for area_name, address in area_list:
            print(f"\n[{area_name}] {address}")

            # 측정소 바꾸기
            station_name = await select_station(page, address)

            # 27개월 수집
            area_rows = await collect_months(page, area_name, station_name)
            air_list.extend(area_rows)

        await browser.close()

    return air_list


# 실행
air_list = asyncio.run(run())
df_air = pd.DataFrame(air_list)

# 숫자로 바꾸기 (빈칸, - 같은 글자는 NaN으로)
for name in item_names:
    df_air[name] = pd.to_numeric(df_air[name], errors="coerce")

# 같은 날짜가 두 번 있으면 평균으로 합치기
df_air = df_air.groupby(["지역", "측정소", "날짜"])[item_names].mean()
df_air = df_air.reset_index()

# 마지막에 한 번에 저장
os.makedirs("./ABJ", exist_ok=True)
df_air.to_csv("./ABJ/대기정보_17개시도_일평균.csv", index=False, encoding="utf-8-sig")
print("저장 완료:", len(df_air), "줄")


df_air.info()


#==============================================================================

# 기온 데이터 불러오기
df_temp = pd.read_csv('./temperature_data/전국월별_기온.csv', encoding='cp949', skiprows=7)         

# 1. 기온 데이터가 비어있는 결측치 행(1건) 제거
df_temp = df_temp.dropna(subset=['평균기온(℃)'])

# 2. '월-연도(1-24)' 문자열을 날짜 타입(2024-01-01)으로 변환
df_temp['년월'] = pd.to_datetime(df_temp['년월'].str.strip(), format='%m-%y').dt.to_period('M')

# 3. 결과 확인
print(df_temp.head())
print(df_temp.tail())
df_temp.info()


# 질병 데이터 불러오기
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 1. 감기 데이터 불러오기
df_cold = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(감기).xlsx')

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_cold.columns = df_cold.iloc[2]
df_cold.columns.name = None

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_cold = df_cold.iloc[3:].reset_index(drop=True)

df_list = []
y = 2024
x = 1
for i in range( ( len(df_cold.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_cold.iloc[:, a:b]
    df_hab = pd.concat([df_cold.iloc[:, 0:3], df_month], axis=1)
    df_hab['년월'] = f'{y}-{x}'
    df_list.append(df_hab)

    x = int(x)
    x += 1

df_cold = pd.concat(df_list, axis=0, ignore_index=True)

df_cold['년월'] = pd.to_datetime(df_cold['년월'].str.strip(), format='%Y-%m').dt.to_period('M')
df_cold['환자수'] = pd.to_numeric( df_cold['환자수'] )
df_cold['내원일수'] = pd.to_numeric( df_cold['내원일수'] )
df_cold['청구건수'] = pd.to_numeric( df_cold['청구건수'] )
df_cold['요양급여비용총액'] = pd.to_numeric( df_cold['요양급여비용총액'] )
df_cold['보험자부담금'] = pd.to_numeric( df_cold['보험자부담금'] )

print(df_cold.head())
print(df_cold.tail())
df_cold.info()


# 1. 기흉 데이터 불러오기
df_pneumothorax = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(기흉).xlsx')

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_pneumothorax.columns = df_pneumothorax.iloc[2]
df_pneumothorax.columns.name = None

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_pneumothorax = df_pneumothorax.iloc[3:].reset_index(drop=True)

df_list = []
y = 2024
x = 1
for i in range( ( len(df_pneumothorax.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_pneumothorax.iloc[:, a:b]
    df_hab = pd.concat([df_pneumothorax.iloc[:, 0:3], df_month], axis=1)
    df_hab['년월'] = f'{y}-{x}'
    df_list.append(df_hab)

    x = int(x)
    x += 1

df_pneumothorax = pd.concat(df_list, axis=0, ignore_index=True)

df_pneumothorax['년월'] = pd.to_datetime(df_pneumothorax['년월'].str.strip(), format='%Y-%m').dt.to_period('M')
df_pneumothorax['환자수'] = pd.to_numeric( df_pneumothorax['환자수'] )
df_pneumothorax['내원일수'] = pd.to_numeric( df_pneumothorax['내원일수'] )
df_pneumothorax['청구건수'] = pd.to_numeric( df_pneumothorax['청구건수'] )
df_pneumothorax['요양급여비용총액'] = pd.to_numeric( df_pneumothorax['요양급여비용총액'] )
df_pneumothorax['보험자부담금'] = pd.to_numeric( df_pneumothorax['보험자부담금'] )

print(df_pneumothorax.head())
print(df_pneumothorax.tail())
df_pneumothorax.info()



# 1. 만성폐쇄성질환COPD 데이터 불러오기
df_copd = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(만성폐쇄성질환COPD).xlsx')

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_copd.columns = df_copd.iloc[2]
df_copd.columns.name = None

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_copd = df_copd.iloc[3:].reset_index(drop=True)

df_list = []
y = 2024
x = 1
for i in range( ( len(df_copd.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_copd.iloc[:, a:b]
    df_hab = pd.concat([df_copd.iloc[:, 0:3], df_month], axis=1)
    df_hab['년월'] = f'{y}-{x}'
    df_list.append(df_hab)

    x = int(x)
    x += 1

df_copd = pd.concat(df_list, axis=0, ignore_index=True)

df_copd['년월'] = pd.to_datetime(df_copd['년월'].str.strip(), format='%Y-%m').dt.to_period('M')
df_copd['환자수'] = pd.to_numeric( df_copd['환자수'] )
df_copd['내원일수'] = pd.to_numeric( df_copd['내원일수'] )
df_copd['청구건수'] = pd.to_numeric( df_copd['청구건수'] )
df_copd['요양급여비용총액'] = pd.to_numeric( df_copd['요양급여비용총액'] )
df_copd['보험자부담금'] = pd.to_numeric( df_copd['보험자부담금'] )

print(df_copd.head())
print(df_copd.tail())
df_copd.info()



# 1. 비염 데이터 불러오기
df_rhinitis = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(비염).xlsx')

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_rhinitis.columns = df_rhinitis.iloc[2]
df_rhinitis.columns.name = None

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_rhinitis = df_rhinitis.iloc[3:].reset_index(drop=True)

df_list = []
y = 2024
x = 1
for i in range( ( len(df_rhinitis.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_rhinitis.iloc[:, a:b]
    df_hab = pd.concat([df_rhinitis.iloc[:, 0:3], df_month], axis=1)
    df_hab['년월'] = f'{y}-{x}'
    df_list.append(df_hab)

    x = int(x)
    x += 1

df_rhinitis = pd.concat(df_list, axis=0, ignore_index=True)

df_rhinitis['년월'] = pd.to_datetime(df_rhinitis['년월'].str.strip(), format='%Y-%m').dt.to_period('M')
df_rhinitis['환자수'] = pd.to_numeric( df_rhinitis['환자수'] )
df_rhinitis['내원일수'] = pd.to_numeric( df_rhinitis['내원일수'] )
df_rhinitis['청구건수'] = pd.to_numeric( df_rhinitis['청구건수'] )
df_rhinitis['요양급여비용총액'] = pd.to_numeric( df_rhinitis['요양급여비용총액'] )
df_rhinitis['보험자부담금'] = pd.to_numeric( df_rhinitis['보험자부담금'] )

print(df_rhinitis.head())
print(df_rhinitis.tail())
df_rhinitis.info()



# 1. 천식 데이터 불러오기
df_asthma = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(천식).xlsx')

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_asthma.columns = df_asthma.iloc[2]
df_asthma.columns.name = None

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_asthma = df_asthma.iloc[3:].reset_index(drop=True)

df_list = []
y = 2024
x = 1
for i in range( ( len(df_asthma.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_asthma.iloc[:, a:b]
    df_hab = pd.concat([df_asthma.iloc[:, 0:3], df_month], axis=1)
    df_hab['년월'] = f'{y}-{x}'
    df_list.append(df_hab)

    x = int(x)
    x += 1

df_asthma = pd.concat(df_list, axis=0, ignore_index=True)

df_asthma['년월'] = pd.to_datetime(df_asthma['년월'].str.strip(), format='%Y-%m').dt.to_period('M')
df_asthma['환자수'] = pd.to_numeric( df_asthma['환자수'] )
df_asthma['내원일수'] = pd.to_numeric( df_asthma['내원일수'] )
df_asthma['청구건수'] = pd.to_numeric( df_asthma['청구건수'] )
df_asthma['요양급여비용총액'] = pd.to_numeric( df_asthma['요양급여비용총액'] )
df_asthma['보험자부담금'] = pd.to_numeric( df_asthma['보험자부담금'] )

print(df_asthma.head())
print(df_asthma.tail())
df_asthma.info()



# 1. 폐렴 데이터 불러오기
df_pneumonia = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(폐렴).xlsx')

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_pneumonia.columns = df_pneumonia.iloc[2]
df_pneumonia.columns.name = None

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_pneumonia = df_pneumonia.iloc[3:].reset_index(drop=True)

df_list = []
y = 2024
x = 1
for i in range( ( len(df_pneumonia.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_pneumonia.iloc[:, a:b]
    df_hab = pd.concat([df_pneumonia.iloc[:, 0:3], df_month], axis=1)
    df_hab['년월'] = f'{y}-{x}'
    df_list.append(df_hab)

    x = int(x)
    x += 1

df_pneumonia = pd.concat(df_list, axis=0, ignore_index=True)

df_pneumonia['년월'] = pd.to_datetime(df_pneumonia['년월'].str.strip(), format='%Y-%m').dt.to_period('M')
df_pneumonia['환자수'] = pd.to_numeric( df_pneumonia['환자수'] )
df_pneumonia['내원일수'] = pd.to_numeric( df_pneumonia['내원일수'] )
df_pneumonia['청구건수'] = pd.to_numeric( df_pneumonia['청구건수'] )
df_pneumonia['요양급여비용총액'] = pd.to_numeric( df_pneumonia['요양급여비용총액'] )
df_pneumonia['보험자부담금'] = pd.to_numeric( df_pneumonia['보험자부담금'] )

print(df_pneumonia.head())
print(df_pneumonia.tail())
df_pneumonia.info()

#==============================================================================


#==========================================================
# 1. 오존: 일평균 → 지역별 월평균 → 전국 월평균
#==========================================================

# 1-1. 크롤링한 일평균 파일 불러오기
df_air = pd.read_csv("./ABJ/대기정보_17개시도_일평균.csv", encoding="utf-8-sig")
df_air.info()

# 1-2. 날짜 → 년월
df_air["날짜"] = pd.to_datetime(df_air["날짜"], format="%Y-%m-%d")
df_air["년월"] = df_air["날짜"].dt.to_period("M")

# 1-3. 지역별 월평균 오존 (빈칸은 빼고 평균)
df_ozone_avg = df_air.groupby(["지역", "년월"], as_index=False)["오존"].mean()
print(df_ozone_avg)

# 1-4. 전국 월평균 오존 (17개 지역을 같은 비중으로)
df_ozone = df_ozone_avg.groupby("년월", as_index=False)["오존"].mean()
print(df_ozone)


#==========================================================
# 2. 질병 6개: 전체 환자수(성별 계, 연령 계)만 뽑기
#==========================================================

# 2-1. 감기
df_cold_total = df_cold[(df_cold["성별구분"] == "계") & (df_cold["연령구분10세"] == "계")]
df_cold_total = df_cold_total[["년월", "환자수"]]
df_cold_total = df_cold_total.rename(columns={"환자수": "감기"})

# 2-2. 기흉
df_pneumothorax_total = df_pneumothorax[(df_pneumothorax["성별구분"] == "계") & (df_pneumothorax["연령구분10세"] == "계")]
df_pneumothorax_total = df_pneumothorax_total[["년월", "환자수"]]
df_pneumothorax_total = df_pneumothorax_total.rename(columns={"환자수": "기흉"})

# 2-3. COPD
df_copd_total = df_copd[(df_copd["성별구분"] == "계") & (df_copd["연령구분10세"] == "계")]
df_copd_total = df_copd_total[["년월", "환자수"]]
df_copd_total = df_copd_total.rename(columns={"환자수": "COPD"})

# 2-4. 비염
df_rhinitis_total = df_rhinitis[(df_rhinitis["성별구분"] == "계") & (df_rhinitis["연령구분10세"] == "계")]
df_rhinitis_total = df_rhinitis_total[["년월", "환자수"]]
df_rhinitis_total = df_rhinitis_total.rename(columns={"환자수": "비염"})

# 2-5. 천식
df_asthma_total = df_asthma[(df_asthma["성별구분"] == "계") & (df_asthma["연령구분10세"] == "계")]
df_asthma_total = df_asthma_total[["년월", "환자수"]]
df_asthma_total = df_asthma_total.rename(columns={"환자수": "천식"})

# 2-6. 폐렴
df_pneumonia_total = df_pneumonia[(df_pneumonia["성별구분"] == "계") & (df_pneumonia["연령구분10세"] == "계")]
df_pneumonia_total = df_pneumonia_total[["년월", "환자수"]]
df_pneumonia_total = df_pneumonia_total.rename(columns={"환자수": "폐렴"})


#==========================================================
# 3. 년월 기준으로 오존 + 질병 6개 합치기
#==========================================================

df = pd.merge(df_ozone, df_cold_total, on="년월", how="inner")
df = pd.merge(df, df_pneumothorax_total, on="년월", how="inner")
df = pd.merge(df, df_copd_total, on="년월", how="inner")
df = pd.merge(df, df_rhinitis_total, on="년월", how="inner")
df = pd.merge(df, df_asthma_total, on="년월", how="inner")
df = pd.merge(df, df_pneumonia_total, on="년월", how="inner")

df.info()       # 27줄이면 정상
print(df)


#==========================================================
# 4. 상관계수 (전체 27개월)
#==========================================================

# 4-1. 상관계수 전체 계산
corr = df[["오존", "감기", "기흉", "COPD", "비염", "천식", "폐렴"]].corr()
print(corr.round(2))

# 4-2. 히트맵
plt.figure(figsize=(10, 8))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, linewidths=0.5)
plt.title("오존과 질병별 환자수 상관관계 (전체 27개월)")
plt.tight_layout()
plt.show()




#==========================================================
# 6. 오존이 많은 달 파악하기
#==========================================================

# 6-1. 월(1~12)만 꺼내기
df["월"] = df["년월"].dt.month

# 6-2. 월별 평균 오존
month_ozone = df.groupby("월", as_index=False)["오존"].mean()
print(month_ozone.round(4))

# 6-3. 오존 많은 달(3~6월)은 빨강, 나머지는 회색
colors = []
for m in month_ozone["월"]:
    if m in [3, 4, 5, 6]:
        colors.append("red")
    else:
        colors.append("gray")

# 6-4. 막대그래프
plt.figure(figsize=(10, 5))
plt.bar(month_ozone["월"], month_ozone["오존"], color=colors, width=0.7)
plt.title("월별 평균 오존 (빨강 = 오존 많은 달 3~6월)")
plt.xlabel("월")
plt.ylabel("오존 (ppm)")
plt.xticks(range(1, 13))        # 가로축에 1~12월 다 표시
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.show()


#==========================================================
# 7. 오존 많은 달(3~6월) 상관계수
#==========================================================

# 7-1. 3~6월만 골라내기
df_high = df[df["월"].isin([3, 4, 5, 6])]
print(df_high)          # 9줄 (2024년 4개월 + 2025년 4개월 + 2026년 3월)

# 7-2. 3~6월 상관계수 전체 계산
corr_high = df_high[["오존", "감기", "기흉", "COPD", "비염", "천식", "폐렴"]].corr()
print(corr_high.round(2))

# 7-3. 히트맵
plt.figure(figsize=(10, 8))
sns.heatmap(corr_high, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, linewidths=0.5)
plt.title("오존과 질병별 환자수 상관관계 (오존 많은 달 3~6월)")
plt.tight_layout()
plt.show()


#==========================================================
# 8. 오존 많은 달 vs 나머지 달: 평균 환자수 비교
#==========================================================

# 8-1. 구분 열 만들기 (처음엔 전부 "나머지 달", 3~6월만 바꾸기)
df["오존구분"] = "나머지 달"
df.loc[df["월"].isin([3, 4, 5, 6]), "오존구분"] = "오존 많은 달(3~6월)"

# 8-2. 구분별 평균 환자수
group_mean = df.groupby("오존구분")[["감기", "기흉", "COPD", "비염", "천식", "폐렴"]].mean()
print(group_mean.round(0))




#==========================================================
# 9. 산점도: 3~6월은 빨강, 나머지 달은 회색
#==========================================================

# 1. 나머지 달만 골라내기 (3~6월은 7번에서 만든 df_high 사용)
df_other = df[df["월"].isin([1, 2, 7, 8, 9, 10, 11, 12])]

# 2. 도화지를 2줄 3칸으로 나누기
fig, axs = plt.subplots(2, 3, figsize=(16, 10))

# 3-1. 감기 (만 명 단위로 보기 위해 10000으로 나눔)
axs[0, 0].scatter(df_other["오존"], df_other["감기"] / 10000, color="gray", alpha=0.6, label="나머지 달")
axs[0, 0].scatter(df_high["오존"], df_high["감기"] / 10000, color="red", alpha=0.8, label="오존 많은 달(3~6월)")
axs[0, 0].set_title(f"감기 (r = {round(corr_ozone.loc['오존', '감기'], 2)})")
axs[0, 0].set_xlabel("오존 (ppm)")
axs[0, 0].set_ylabel("환자수 (만 명)")
axs[0, 0].legend()

# 3-2. 기흉 (환자수가 적어서 명 단위 그대로)
axs[0, 1].scatter(df_other["오존"], df_other["기흉"], color="gray", alpha=0.6)
axs[0, 1].scatter(df_high["오존"], df_high["기흉"], color="red", alpha=0.8)
axs[0, 1].set_title(f"기흉 (r = {round(corr_ozone.loc['오존', '기흉'], 2)})")
axs[0, 1].set_xlabel("오존 (ppm)")
axs[0, 1].set_ylabel("환자수 (명)")

# 3-3. COPD
axs[0, 2].scatter(df_other["오존"], df_other["COPD"] / 10000, color="gray", alpha=0.6)
axs[0, 2].scatter(df_high["오존"], df_high["COPD"] / 10000, color="red", alpha=0.8)
axs[0, 2].set_title(f"COPD (r = {round(corr_ozone.loc['오존', 'COPD'], 2)})")
axs[0, 2].set_xlabel("오존 (ppm)")
axs[0, 2].set_ylabel("환자수 (만 명)")

# 3-4. 비염
axs[1, 0].scatter(df_other["오존"], df_other["비염"] / 10000, color="gray", alpha=0.6)
axs[1, 0].scatter(df_high["오존"], df_high["비염"] / 10000, color="red", alpha=0.8)
axs[1, 0].set_title(f"비염 (r = {round(corr_ozone.loc['오존', '비염'], 2)})")
axs[1, 0].set_xlabel("오존 (ppm)")
axs[1, 0].set_ylabel("환자수 (만 명)")

# 3-5. 천식
axs[1, 1].scatter(df_other["오존"], df_other["천식"] / 10000, color="gray", alpha=0.6)
axs[1, 1].scatter(df_high["오존"], df_high["천식"] / 10000, color="red", alpha=0.8)
axs[1, 1].set_title(f"천식 (r = {round(corr_ozone.loc['오존', '천식'], 2)})")
axs[1, 1].set_xlabel("오존 (ppm)")
axs[1, 1].set_ylabel("환자수 (만 명)")

# 3-6. 폐렴
axs[1, 2].scatter(df_other["오존"], df_other["폐렴"] / 10000, color="gray", alpha=0.6)
axs[1, 2].scatter(df_high["오존"], df_high["폐렴"] / 10000, color="red", alpha=0.8)
axs[1, 2].set_title(f"폐렴 (r = {round(corr_ozone.loc['오존', '폐렴'], 2)})")
axs[1, 2].set_xlabel("오존 (ppm)")
axs[1, 2].set_ylabel("환자수 (만 명)")

# 4. 전체 제목, 여백 정리 후 출력
fig.suptitle("오존과 질병별 환자수 (r = 전체 27개월 상관계수)")
plt.tight_layout()
plt.show()


