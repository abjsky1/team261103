# 모기 데이터1 : https://data.seoul.go.kr/dataList/OA-22301/F/1/datasetView.do
# 모기 데이터2 : https://news.seoul.go.kr/welfare/digital_mosquito

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


# 기온 데이터 불러오기
df_temp = pd.read_csv('./temperature_data/전국월별_기온.csv',
                 encoding='cp949',   # 한국어 인코딩으로 읽기
                 skiprows=7)         # 앞의 설명 7줄 건너뛰기
print(df_temp.head())
print(df_temp.tail())
df_temp.info()

# 1. 기온 데이터가 비어있는 결측치 행(1건) 제거
df_temp = df_temp.dropna(subset=['평균기온(℃)'])

# 2. '월-연도(1-24)' 문자열을 날짜 타입(2024-01-01)으로 변환
df_temp['년월'] = pd.to_datetime(df_temp['년월'].str.strip(), format='%m-%y').dt.to_period('M')

# 3. 결과 확인
print(df_temp.head())
print(df_temp.tail())
df_temp.info()


# 질병 데이터 불러오기
# 엑셀 스타일 관련 불필요한 경고 메시지 숨김
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 1. 질병 데이터 불러오기
df_disease = pd.read_excel('./질병/국민관심질병_성별연령별10세구간별현황_202401_202603(감기).xlsx')

print(df_disease.head())
print(df_disease.tail())
df_disease.info()

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_disease.columns = df_disease.iloc[2]
print(df_disease.head())
print(df_disease.tail())
df_disease.info()

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_disease = df_disease.iloc[3:].reset_index(drop=True)
print(df_disease.head())
print(df_disease.tail())
df_disease.info()

df_list = []
y = 2024
x = 1
for i in range( ( len(df_disease.columns) - 3 ) // 5 ):
    a = 3 + (i * 5)
    b = a + 5

    if x < 10 :
        x = f"0{x}"

    elif x > 12 :
        x = 1
        y += 1

    df_month = df_disease.iloc[:, a:b]
    df_temp = pd.concat([df_disease.iloc[:, 0:3], df_month], axis=1)
    df_temp['년월'] = f'{y}-{x}'
    df_list.append(df_temp)

    x = int(x)
    x += 1

df_disease = pd.concat(df_list, axis=0, ignore_index=True)

print(df_disease.head())
print(df_disease.tail())
df_disease.info()

df_disease['년월'] = pd.to_datetime(df_disease['년월'].str.strip(), format='%Y-%m').dt.to_period('M')

print(df_disease.head())
print(df_disease.tail())
df_disease.info()