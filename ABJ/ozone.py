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

# ============================================================================================

# 크롤링으로 데이터 가져오기.

# url = "https://www.airkorea.or.kr/web/realSearch?pMENU_NO=97"

# async def date_test():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()
#         await page.goto(url)
#         await page.wait_for_timeout(3000)
#         await page.reload()
#         await page.wait_for_timeout(10000)

#         daily_radio = page.get_by_label("일평균")
#         await daily_radio.check()
#         await page.wait_for_timeout(1000)

#         # 방법 1: 사람처럼 키보드로 한 글자씩 타이핑
#         await page.click("#from_date")
#         await page.keyboard.press("Control+A")
#         await page.keyboard.press("Backspace")
#         await page.keyboard.type("20240101", delay=100)
#         await page.keyboard.press("Escape")
#         print("방법1:", await page.input_value("#from_date"))

#         # 방법 2: 사이트의 jQuery 달력 기능으로 날짜 설정
#         await page.evaluate("$('#from_date').datepicker('setDate', '2024-01-01')")
#         await page.evaluate("$('#to_date').datepicker('setDate', '2024-01-31')")
#         print("방법2:", await page.input_value("#from_date"), "~", await page.input_value("#to_date"))

#         # 방법 3: 자바스크립트로 값을 넣고 '바뀌었다'고 알리기
#         await page.evaluate("""
#             const box = document.querySelector('#from_date');
#             box.value = '2024-01-01';
#             box.dispatchEvent(new Event('change', { bubbles: true }));
#         """)
#         print("방법3:", await page.input_value("#from_date"))

#         # 검색해서 표의 날짜 범위 확인
#         await page.locator(".btnMoum .btnBlueWhite").click()
#         await page.wait_for_timeout(3000)
#         rows = await page.query_selector_all("#realTable tbody tr")
#         first_td = await rows[0].query_selector("td")
#         last_td = await rows[-1].query_selector("td")
#         print("표의 날짜 범위:", await first_td.inner_text(), "~", await last_td.inner_text(), f"({len(rows)}줄)")

#         await page.wait_for_timeout(5000)
#         await browser.close()

# asyncio.run(date_test())

#==================================================================================================================

# url = "https://www.airkorea.or.kr/web/realSearch?pMENU_NO=97"

# # 표의 1~6번 칸 순서대로 항목 이름
# item_names = ["PM10", "PM2.5", "오존", "이산화질소", "일산화탄소", "아황산가스"]

# # 2024-01 ~ 2026-03, 27개월
# month_list = pd.period_range("2024-01", "2026-03", freq="M")

# async def run():
#     air_list = []

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()
#         await page.goto(url)
#         await page.wait_for_timeout(3000)
#         await page.reload()
#         await page.wait_for_timeout(10000)

#         # 2. '일평균' 선택
#         daily_radio = page.get_by_label("일평균")
#         await daily_radio.check()
#         print("일평균 선택됨:", await daily_radio.is_checked())
#         await page.wait_for_timeout(1000)

#         # 3. 한 달씩 반복
#         for month in month_list:
#             # 3-1. 그 달의 첫날, 마지막 날
#             start_date = month.start_time.strftime("%Y-%m-%d")
#             end_date = month.end_time.strftime("%Y-%m-%d")

#             # 3-2. 날짜 입력 (사이트의 jQuery 달력 기능 사용)
#             await page.evaluate(f"$('#from_date').datepicker('setDate', '{start_date}')")
#             await page.evaluate(f"$('#to_date').datepicker('setDate', '{end_date}')")

#             # 3-3. 측정 자료 검색 버튼 클릭
#             await page.locator(".btnMoum .btnBlueWhite").click()
#             await page.wait_for_timeout(3000)

#             # 3-4. 표의 모든 줄
#             rows = await page.query_selector_all("#realTable tbody tr")

#             # 3-5. 줄마다 날짜 + 6개 항목 꺼내기
#             month_count = 0
#             for row in rows:
#                 tds = await row.query_selector_all("td")

#                 # 날짜 + 6개 항목 = 7칸이 안 되는 줄은 건너뛰기
#                 if len(tds) < 7:
#                     continue

#                 # 0번 칸: 날짜
#                 date_text = await tds[0].inner_text()
#                 one_day = {"날짜": date_text.strip()}

#                 # 1~6번 칸: 항목 이름과 짝지어 저장
#                 for i, name in enumerate(item_names, start=1):
#                     value_text = await tds[i].inner_text()
#                     one_day[name] = value_text.strip()

#                 air_list.append(one_day)
#                 month_count += 1

#             # 3-6. 확인용 출력: 몇 일 모았는지, 표의 날짜 범위
#             first_td = await rows[0].query_selector("td")
#             last_td = await rows[-1].query_selector("td")
#             first_text = await first_td.inner_text()
#             last_text = await last_td.inner_text()
#             print(f"{month}: {month_count}일 수집 ({last_text} ~ {first_text})")

#         await browser.close()

#     return air_list

# air_list = asyncio.run(run())
# # print(len(air_list))
# # print(air_list[:3])


# df_air = pd.DataFrame(air_list)

# print(df_air.head())
# print(df_air.tail())
# df_air.info()

# df_air['PM10'] = pd.to_numeric( df_air['PM10'] )
# df_air['PM2.5'] = pd.to_numeric( df_air['PM2.5'] )
# df_air['오존'] = pd.to_numeric( df_air['오존'] )
# df_air['이산화질소'] = pd.to_numeric( df_air['이산화질소'] )
# df_air['일산화탄소'] = pd.to_numeric( df_air['일산화탄소'] )
# df_air['아황산가스'] = pd.to_numeric( df_air['아황산가스'] )

# df_air['년월'] = pd.to_datetime(df_air['날짜'].str.strip(), format='%Y-%m-%d').dt.to_period('M')

# df_air= df_air.groupby("년월", as_index=False)[item_names].mean()

# print(df_air.head())
# print(df_air.tail())
# df_air.info()

#==================================================================================

# start_url = "https://www.airkorea.or.kr/web/sidoQualityCompare?itemCode=10007&pMENU_NO=101"

# async def check():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()

#         # 1. 페이지 열기 (아까처럼 새로고침까지)
#         await page.goto(start_url)
#         await page.wait_for_timeout(3000)
#         await page.reload()
#         await page.wait_for_timeout(5000)

#         # 2. '월별' 선택
#         monthly_radio = page.get_by_label("월별")
#         await monthly_radio.check()
#         print("월별 선택됨:", await monthly_radio.is_checked())

#         # 3. 드롭다운에 어떤 달들이 있는지 (앞 3개, 뒤 3개)
#         option_list = await page.query_selector_all("#month option")
#         print("선택 가능한 달 개수:", len(option_list))
#         for option in option_list[:3] + option_list[-3:]:
#             text = await option.inner_text()
#             value = await option.get_attribute("value")
#             print("  글자:", text, "/ value:", value)

#         # 4. 2024년 01월 선택
#         await page.select_option("#month", label="2024년 01월")
#         await page.wait_for_timeout(1000)

#         # 5. 검색 버튼이 몇 개 잡히는지 확인 후 클릭
#         search_button = page.locator(".btnMoum button", has_text="검색")
#         print("검색 버튼 개수:", await search_button.count())
#         await search_button.click()
#         await page.wait_for_timeout(3000)

#         # 6. 표의 제목 줄 (지역 이름들)
#         header_list = await page.query_selector_all("#sidoTable_thead th")
#         header_text = []
#         for th in header_list:
#             text = await th.inner_text()
#             header_text.append(text.strip())
#         print("제목 줄:", header_text)

#         # 7. 표의 데이터 줄 (앞 4칸만)
#         rows = await page.query_selector_all("#sidoTable tr")
#         for row in rows:
#             tds = await row.query_selector_all("td")
#             row_text = []
#             for td in tds[:4]:
#                 text = await td.inner_text()
#                 row_text.append(text.strip())
#             print("데이터 줄:", row_text)

#         await page.wait_for_timeout(3000)
#         await browser.close()

# asyncio.run(check())


#==================================================================================
# url = "https://www.airkorea.or.kr/web/realSearch?pMENU_NO=97"

# # 테스트용 2곳: (지역 이름, 시청 도로명 주소)
# area_list = [
#     ("서울", "서울특별시 중구 세종대로 110"),       # 서울시청
#     ("부산", "부산광역시 연제구 중앙대로 1001"),     # 부산시청
# ]


# # 측정소 바꾸기: 주소 검색 팝업 → 측정소 목록 → 도시대기 선택
# async def select_station(page, address):
#     # ① 지역명 입력칸 클릭 → 팝업 열림
#     async with page.expect_popup() as popup_info:
#         await page.click("#s_condition_input3")
#     popup = await popup_info.value
#     await popup.wait_for_load_state()
#     await popup.wait_for_timeout(2000)

#     # ② 팝업 검색칸에 주소 입력 후 Enter
#     await popup.fill("#keyword", address)
#     await popup.press("#keyword", "Enter")
#     await popup.wait_for_timeout(2000)

#     # ③ 첫 번째 결과 클릭
#     await popup.locator("#roadAddrTd1 a").click()
#     await popup.wait_for_timeout(1500)

#     # ④ 주소입력 버튼 클릭 → 팝업 닫힘
#     await popup.locator("a.btn-bl").click()
#     await page.wait_for_timeout(2000)

#     # ⑤ 지역명 검색 버튼 클릭 → 측정소 목록
#     await page.locator('button[onclick^="goAreaSearch"]').click()
#     await page.wait_for_timeout(3000)

#     # ⑥ 측정소 목록에서 첫 번째 '도시대기' 고르기
#     station_rows = await page.query_selector_all("tr:has(input[type='radio'])")
#     chosen_name = None

#     for row in station_rows:
#         tds = await row.query_selector_all("td")
#         if len(tds) < 5:
#             continue

#         # 0: 선택, 1: 측정소명, 2: 주소, 3: 거리, 4: 측정망
#         name = (await tds[1].inner_text()).strip()
#         distance = (await tds[3].inner_text()).strip()
#         network = (await tds[4].inner_text()).strip()
#         print(f"   후보: {name} / {distance} / {network}")

#         if chosen_name is None and network == "도시대기":
#             radio = await row.query_selector("input[type='radio']")
#             await radio.check()
#             chosen_name = name

#     # 도시대기가 하나도 없으면 첫 번째(기본 선택) 측정소 사용
#     if chosen_name is None and len(station_rows) > 0:
#         first_tds = await station_rows[0].query_selector_all("td")
#         chosen_name = (await first_tds[1].inner_text()).strip()

#     print(f"   → 선택: {chosen_name}")

#     # ⑦ 측정자료 조회 클릭
#     await page.get_by_text("측정자료 조회", exact=True).click()
#     await page.wait_for_timeout(3000)

#     return chosen_name


# # 테스트: 2곳만 측정소 선택이 잘 되는지 확인
# async def station_test():
#     async with async_playwright() as p:
#         # 페이지 열기 (처음엔 화면이 안 떠서 새로고침까지)
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()
#         await page.goto(url)
#         await page.wait_for_timeout(3000)
#         await page.reload()
#         await page.wait_for_timeout(10000)

#         for area_name, address in area_list:
#             print(area_name, address)
#             await select_station(page, address)

#         # 결과 화면을 눈으로 볼 수 있게 5초 기다렸다가 닫기
#         await page.wait_for_timeout(5000)
#         await browser.close()


# asyncio.run(station_test())


#==================================================================================

# url = "https://www.airkorea.or.kr/web/realSearch?pMENU_NO=97"

# # 표의 1~6번 칸 순서대로 항목 이름
# item_names = ["PM10", "PM2.5", "오존", "이산화질소", "일산화탄소", "아황산가스"]

# # 2024-01 ~ 2026-03, 27개월
# month_list = pd.period_range("2024-01", "2026-03", freq="M")

# # 17개 시도: (지역 이름, 시청·도청 도로명 주소)
# area_list = [
#     ("서울", "서울특별시 중구 세종대로 110"),               # 서울시청
#     ("부산", "부산광역시 연제구 중앙대로 1001"),             # 부산시청
#     ("대구", "대구광역시 중구 공평로 88"),                   # 대구시청
#     ("인천", "인천광역시 남동구 정각로 29"),                 # 인천시청
#     ("광주", "광주광역시 서구 내방로 111"),                  # 광주시청
#     ("대전", "대전광역시 서구 둔산로 100"),                  # 대전시청
#     ("울산", "울산광역시 남구 중앙로 201"),                  # 울산시청
#     ("세종", "세종특별자치시 한누리대로 2130"),              # 세종시청
#     ("경기", "경기도 수원시 영통구 도청로 30"),              # 경기도청
#     ("강원", "강원특별자치도 춘천시 중앙로 1"),              # 강원도청
#     ("충북", "충청북도 청주시 상당구 상당로 82"),            # 충북도청
#     ("충남", "충청남도 홍성군 홍북읍 충남대로 21"),          # 충남도청
#     ("전북", "전북특별자치도 전주시 완산구 효자로 225"),     # 전북도청
#     ("전남", "전라남도 목포시 양을로 203"),                # 전남도청
#     ("경북", "경상북도 안동시 풍천면 도청대로 455"),         # 경북도청
#     ("경남", "경상남도 창원시 의창구 중앙대로 300"),         # 경남도청
#     ("제주", "제주특별자치도 제주시 문연로 6"),              # 제주도청
# ]


# # 측정소 바꾸기: 주소 검색 팝업 → 측정소 목록 → 첫 번째 측정소 사용
# async def select_station(page, address):
#     # ① 지역명 입력칸 클릭 → 팝업 열림
#     async with page.expect_popup() as popup_info:
#         await page.click("#s_condition_input3")
#     popup = await popup_info.value
#     await popup.wait_for_load_state()
#     await popup.wait_for_timeout(2000)

#     # ② 팝업 검색칸에 주소 입력 후 Enter
#     await popup.fill("#keyword", address)
#     await popup.press("#keyword", "Enter")
#     await popup.wait_for_timeout(2000)

#     # ③ 첫 번째 결과 클릭
#     await popup.locator("#roadAddrTd1 a").click()
#     await popup.wait_for_timeout(1500)

#     # ④ 주소입력 버튼 클릭 → 팝업 닫힘
#     await popup.locator("a.btn-bl").click()
#     await page.wait_for_timeout(2000)

#     # ⑤ 지역명 검색 버튼 클릭 → 측정소 목록
#     await page.locator('button[onclick^="goAreaSearch"]').click()
#     await page.wait_for_timeout(3000)

#     # ⑥ 첫 번째 측정소(기본 선택) 이름만 가져오기
#     first_row = page.locator("tr:has(input[type='radio'])").first
#     chosen_name = (await first_row.locator("td").nth(1).inner_text()).strip()
#     print(f"   → 선택: {chosen_name}")

#     # ⑦ 측정자료 조회 클릭
#     await page.get_by_text("측정자료 조회", exact=True).click()
#     await page.wait_for_timeout(3000)

#     return chosen_name


# # 한 측정소의 27개월 일평균 수집
# async def collect_months(page, area_name, station_name):
#     area_rows = []

#     # 일평균 선택
#     daily_radio = page.get_by_label("일평균")
#     await daily_radio.check()
#     await page.wait_for_timeout(1000)

#     for month in month_list:
#         # 그 달의 첫날, 마지막 날
#         start_date = month.start_time.strftime("%Y-%m-%d")
#         end_date = month.end_time.strftime("%Y-%m-%d")

#         # 날짜 입력 (사이트의 jQuery 달력 기능 사용)
#         await page.evaluate(f"$('#from_date').datepicker('setDate', '{start_date}')")
#         await page.evaluate(f"$('#to_date').datepicker('setDate', '{end_date}')")

#         # 측정 자료 검색 버튼 클릭
#         await page.locator(".btnMoum .btnBlueWhite").click()
#         await page.wait_for_timeout(3000)

#         # 표의 모든 줄
#         rows = await page.query_selector_all("#realTable tbody tr")

#         for row in rows:
#             tds = await row.query_selector_all("td")

#             # 0번 칸: 날짜
#             date_text = await tds[0].inner_text()
#             one_day = {"지역": area_name, "측정소": station_name, "날짜": date_text.strip()}

#             # 1~6번 칸: 항목 이름과 짝지어 저장
#             for i, name in enumerate(item_names, start=1):
#                 value_text = await tds[i].inner_text()
#                 one_day[name] = value_text.strip()

#             area_rows.append(one_day)

#         print(f"  {month}: {len(rows)}일")

#     return area_rows


# # 본 수집: 17개 시도 × 27개월
# async def run():
#     air_list = []

#     async with async_playwright() as p:
#         # 페이지 열기 (처음엔 화면이 안 떠서 새로고침까지)
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()
#         await page.goto(url)
#         await page.wait_for_timeout(3000)
#         await page.reload()
#         await page.wait_for_timeout(10000)

#         for area_name, address in area_list:
#             print(f"\n[{area_name}] {address}")

#             # 측정소 바꾸기
#             station_name = await select_station(page, address)

#             # 27개월 수집
#             area_rows = await collect_months(page, area_name, station_name)
#             air_list.extend(area_rows)

#         await browser.close()

#     return air_list


# # 실행
# air_list = asyncio.run(run())
# print("수집 끝:", len(air_list), "줄")    # 17 × 821 = 13,957이면 빠짐없이 수집

# # 마지막에 한 번에 저장
# os.makedirs("./ABJ", exist_ok=True)
# df_air = pd.DataFrame(air_list)
# df_air.to_csv("./ABJ/대기정보_17개시도_일평균.csv", index=False, encoding="utf-8-sig")
# print("저장 완료")




#==================================================================================

url = "https://www.airkorea.or.kr/web/realSearch?pMENU_NO=97"

# 표의 1~6번 칸 순서대로 항목 이름
item_names = ["PM10", "PM2.5", "오존", "이산화질소", "일산화탄소", "아황산가스"]

# 2024-01 ~ 2026-03, 27개월
month_list = pd.period_range("2024-01", "2026-03", freq="M")

# 저장 위치 (예전 파일과 겹치지 않게 새 이름)
save_path = "./ABJ/대기정보_17개시도_일평균_최종.csv"

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
    ("전북", "전북특별자치도 전주시 완산구 효자로 225"),     # 전북도청
    ("전남", "전라남도 목포시 양을로 203"),                # 전남도청
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
        target_text = str(month)            # 예: "2024-01"
        full_days = month.days_in_month     # 그 달의 날짜 수 (28~31)

        month_rows = []

        # [개선 ③] 날짜 수가 모자라면 최대 3번까지 다시 검색
        for try_count in range(1, 4):
            # 날짜 입력 (사이트의 jQuery 달력 기능 사용)
            await page.evaluate(f"$('#from_date').datepicker('setDate', '{start_date}')")
            await page.evaluate(f"$('#to_date').datepicker('setDate', '{end_date}')")

            # 측정 자료 검색 버튼 클릭
            await page.locator(".btnMoum .btnBlueWhite").click()

            # [개선 ①] 표 첫 칸 날짜가 이번 달로 바뀔 때까지 1초씩 최대 10번 기다리기
            for wait_count in range(10):
                await page.wait_for_timeout(1000)
                first_cell = await page.query_selector("#realTable tbody tr td")
                if first_cell is None:
                    continue
                first_text = (await first_cell.inner_text()).strip()

                # 첫 칸 날짜가 "2024-01" 처럼 이번 달로 시작하면 바뀐 것
                if first_text.startswith(target_text):
                    break

            # 표의 모든 줄
            month_rows = []
            rows = await page.query_selector_all("#realTable tbody tr")

            for row in rows:
                tds = await row.query_selector_all("td")

                # [개선 ④] 7칸이 안 되는 줄(자료 없음 안내 등)은 건너뛰기
                if len(tds) < 7:
                    continue

                # 0번 칸: 날짜
                date_text = (await tds[0].inner_text()).strip()

                # [개선 ②] 이번 달 날짜가 아니면 버리기
                if not date_text.startswith(target_text):
                    continue

                one_day = {"지역": area_name, "측정소": station_name, "날짜": date_text}

                # 1~6번 칸: 항목 이름과 짝지어 저장
                for i, name in enumerate(item_names, start=1):
                    value_text = await tds[i].inner_text()
                    one_day[name] = value_text.strip()

                month_rows.append(one_day)

            # 날짜 수가 다 차면 다시 시도하지 않고 끝
            if len(month_rows) == full_days:
                break

            print(f"  {month}: {len(month_rows)}/{full_days}일 → 다시 시도 ({try_count}/3)")

        area_rows.extend(month_rows)
        print(f"  {month}: {len(month_rows)}일")

    return area_rows


# 본 수집: 17개 시도 × 27개월
async def run():
    # [개선 ⑤] 이미 저장된 파일이 있으면 불러와서, 끝난 지역은 건너뛰기
    if os.path.exists(save_path):
        df_done = pd.read_csv(save_path, encoding="utf-8-sig")
        air_list = df_done.to_dict("records")
        done_areas = list(df_done["지역"].unique())
        print("이미 끝난 지역:", done_areas)
    else:
        air_list = []
        done_areas = []

    async with async_playwright() as p:
        # 페이지 열기 (처음엔 화면이 안 떠서 새로고침까지)
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(3000)
        await page.reload()
        await page.wait_for_timeout(10000)

        for area_name, address in area_list:
            # [개선 ⑤] 끝난 지역은 건너뛰기
            if area_name in done_areas:
                continue

            print(f"\n[{area_name}] {address}")

            # 측정소 바꾸기
            station_name = await select_station(page, address)

            # 27개월 수집
            area_rows = await collect_months(page, area_name, station_name)
            air_list.extend(area_rows)

            # [개선 ⑤] 지역 하나 끝날 때마다 저장
            pd.DataFrame(air_list).to_csv(save_path, index=False, encoding="utf-8-sig")
            print(f"  → {area_name} 저장 완료 (누적 {len(air_list)}줄)")

        await browser.close()

    return air_list


# 실행
os.makedirs("./ABJ", exist_ok=True)
air_list = asyncio.run(run())
print("\n수집 끝:", len(air_list), "줄")    # 17 × 821 = 13,957이면 빠짐없이 수집

# [개선 ⑥] 마지막 확인
df_air = pd.DataFrame(air_list)

# 지역별 날짜 수 (821일이면 정상)
print("\n[지역별 날짜 수] 821일이면 빠짐없음")
print(df_air.groupby("지역")["날짜"].count())

# 중복 줄 수 (0이면 정상)
duplicate_count = df_air.duplicated(subset=["지역", "날짜"]).sum()
print("중복된 줄 수:", duplicate_count)

# 날짜가 모자란 달 목록
df_air["년월"] = pd.to_datetime(df_air["날짜"], format="%Y-%m-%d").dt.to_period("M")
print("\n[날짜가 모자란 달]")
for area_name, address in area_list:
    df_area = df_air[df_air["지역"] == area_name]
    for month in month_list:
        df_month = df_area[df_area["년월"] == month]
        if len(df_month) < month.days_in_month:
            print(f"  {area_name} {month}: {len(df_month)}/{month.days_in_month}일")


#==================================================================================

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



# 1. 기흉 데이터 불러오기
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



# 1. 기흉 데이터 불러오기
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



# 1. 기흉 데이터 불러오기
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



# 1. 기흉 데이터 불러오기
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


# ================================================================================================================

df_air_test = pd.read_csv('./ABJ/에어코리아_17개시도_일평균.csv')
df_air = pd.DataFrame(air_list)

df_air_test.info()

# <class 'pandas.DataFrame'>
# RangeIndex: 13956 entries, 0 to 13955
# Data columns (total 9 columns):
#  #   Column      Non-Null Count  Dtype  
# ---  ------      --------------  -----  
#  0   지역        13956 non-null  str    
#  1   측정소      13956 non-null  str    
#  2   날짜        13956 non-null  str    
#  3   PM10        13895 non-null  float64
#  4   PM2.5       13897 non-null  float64
#  5   오존        13124 non-null  float64
#  6   이산화질소  13907 non-null  float64
#  7   일산화탄소  13797 non-null  float64
#  8   아황산가스  13897 non-null  float64
# dtypes: float64(6), str(3)
# memory usage: 981.4 KB

df_air_test2 = pd.read_csv('./ABJ/대기정보_17개시도_일평균.csv')

df_air_test2.info()

# <class 'pandas.DataFrame'>
# RangeIndex: 13998 entries, 0 to 13997
# Data columns (total 9 columns):
#  #   Column      Non-Null Count  Dtype  
# ---  ------      --------------  -----  
#  0   지역        13998 non-null  str    
#  1   측정소      13998 non-null  str    
#  2   날짜        13998 non-null  str    
#  3   PM10        13896 non-null  float64
#  4   PM2.5       13913 non-null  float64
#  5   오존        13169 non-null  float64
#  6   이산화질소  13957 non-null  float64
#  7   일산화탄소  13840 non-null  float64
#  8   아황산가스  13939 non-null  float64
# dtypes: float64(6), str(3)
# memory usage: 984.4 KB