# 가설01. 
# 감기는 기온보다 일교차가 더 큰 영향을 줄 것이다.

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
# print(df_temp.head())
# print(df_temp.tail())
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

# print(df_disease.head())
# print(df_disease.tail())
df_disease.info()

# 1. 2번 행(엑셀 4번 줄)을 컬럼 이름으로 바로 덮어쓰기
df_disease.columns = df_disease.iloc[2]
# print(df_disease.head())
# print(df_disease.tail())
df_disease.info()

# 2. 0~2번 행(엑셀 2~4번 줄)은 건너뛰고, 본문 데이터인 3번 행(엑셀 5번 줄)부터 끝까지 슬라이싱
df_disease = df_disease.iloc[3:].reset_index(drop=True)
# print(df_disease.head())
# print(df_disease.tail())
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
    df_hab = pd.concat([df_disease.iloc[:, 0:3], df_month], axis=1)
    df_hab['년월'] = f'{y}-{x}'
    df_list.append(df_hab)

    x = int(x)
    x += 1

df_disease = pd.concat(df_list, axis=0, ignore_index=True)

# print(df_disease.head())
# print(df_disease.tail())
df_disease.info()

df_disease['년월'] = pd.to_datetime(df_disease['년월'].str.strip(), format='%Y-%m').dt.to_period('M')

df_disease.columns.name = None

print(df_disease.head())
print(df_disease.tail())
df_disease.info()

df_disease.info()
df_disease['환자수'] = pd.to_numeric( df_disease['환자수'] )
df_disease['내원일수'] = pd.to_numeric( df_disease['내원일수'] )
df_disease['청구건수'] = pd.to_numeric( df_disease['청구건수'] )
df_disease['요양급여비용총액'] = pd.to_numeric( df_disease['요양급여비용총액'] )
df_disease['보험자부담금'] = pd.to_numeric( df_disease['보험자부담금'] )
df_disease.info()

print(df_disease['항목'])
print(df_disease['성별구분'])
print(df_disease['연령구분10세'].head(30))

sns.scatterplot(data=df_temp)
sns.scatterplot(data=df_disease)
plt.show()

#--------------------------------------------------------------------------------------------
df_temp.info()

df_temp['일교차'] = df_temp['평균최고기온(℃)'] - df_temp['평균최저기온(℃)']

df_temp.info()
df_temp.head()

total_count = df_disease[(df_disease["성별구분"] == "계") & (df_disease["연령구분10세"] == "계")].reset_index(drop=True)
print(total_count)
df_total = total_count[["년월", "환자수"]]
print(df_total)

df = pd.merge(df_temp, df_total, on="년월", how="inner")
df.info()
df.head()
print(df[ [ "년월" , '평균최저기온(℃)' , "평균기온(℃)" , '평균최고기온(℃)' , "일교차" , "환자수" ] ] )
df = df[ [ "년월" , '평균최저기온(℃)' , "평균기온(℃)" , '평균최고기온(℃)' , "일교차" , "환자수" ] ]
df.info()
df.head()


# 1. 그래프용 날짜로 바꾸기
df["년월_날짜"] = df["년월"].dt.to_timestamp()

# 2. 도화지를 위아래 2칸으로 나누기
fig, axs = plt.subplots(2, 1, figsize=(12, 8))

# 3. 위 칸: 환자수
axs[0].plot(df["년월_날짜"], df["환자수"], color="gray", marker="o", label="환자수")
axs[0].set_title("월별 감기 환자수")
axs[0].set_ylabel("환자수")
axs[0].grid(True, linestyle=":", alpha=0.6)
axs[0].legend()

# 4. 아래 칸: 평균기온, 일교차
axs[1].plot(df["년월_날짜"], df["평균최저기온(℃)"], color="blue", marker="o", label="평균최저기온")
axs[1].plot(df["년월_날짜"], df["평균기온(℃)"], color="orange", marker="o", label="평균기온")
axs[1].plot(df["년월_날짜"], df["평균최고기온(℃)"], color="red", marker="o", label="평균최고기온")
axs[1].plot(df["년월_날짜"], df["일교차"], color="green", linestyle="--", marker="s", label="일교차")
axs[1].set_title("월별 기온과 일교차")
axs[1].set_xlabel("년월")
axs[1].set_ylabel("℃")
axs[1].grid(True, linestyle=":", alpha=0.6)
axs[1].legend()

# 5. 여백 정리 후 출력
plt.tight_layout()
plt.show()



# 1. 세 열을 '평균에서 얼마나 떨어졌나'로 바꾸기 (StandardScaler와 같은 계산)
cols = ["평균최저기온(℃)","평균최고기온(℃)","평균기온(℃)","일교차","환자수"]
df_std = (df[cols] - df[cols].mean()) / df[cols].std()

# 2. 한 그래프에 겹쳐 그리기
plt.figure(figsize=(12, 5))
plt.plot(df["년월_날짜"], df_std["환자수"], color="gray", marker="o", label="환자수")
plt.plot(df["년월_날짜"], df_std["평균최고기온(℃)"], color="red", linestyle="--", marker="o", label="평균최고기온")
plt.plot(df["년월_날짜"], df_std["평균기온(℃)"], color="orange", linestyle="--", marker="o", label="평균기온")
plt.plot(df["년월_날짜"], df_std["평균최저기온(℃)"], color="blue", linestyle="--", marker="o", label="평균최저기온")
plt.plot(df["년월_날짜"], df_std["일교차"], color="green", linestyle="--", marker="s", label="일교차")

plt.title("월별 환자수·평균기온·일교차 (표준화)")
plt.xlabel("년월")
plt.ylabel("표준 점수 (0 = 평균)")
plt.grid(True, linestyle=":", alpha=0.6)
plt.legend()
plt.show()




corr = df[["평균최저기온(℃)","평균최고기온(℃)","평균기온(℃)", "일교차", "환자수"]].corr()
print(corr.round(2))

sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, linewidths=0.5)
plt.title("기온·일교차·환자수 상관관계")
plt.show()




# 1. 월(1~12)만 꺼내기
df["월"] = df["년월"].dt.month

# 2. 월별 평균 환자수
month_mean = df.groupby("월", as_index=False)["환자수"].mean()

# 3. 계절별 색상 정하기
season_colors = {12: "#6baed6", 1: "#6baed6", 2: "#6baed6",     # 겨울: 파랑
                 3: "#74c476", 4: "#74c476", 5: "#74c476",      # 봄: 초록
                 6: "#fd8d3c", 7: "#fd8d3c", 8: "#fd8d3c",      # 여름: 주황
                 9: "#e6550d", 10: "#e6550d", 11: "#e6550d"}    # 가을: 갈색
colors = [season_colors[m] for m in month_mean["월"]]

# 4. 막대그래프
plt.figure(figsize=(10, 5))
plt.bar(month_mean["월"], month_mean["환자수"], color=colors, width=0.7)
plt.title("월별 평균 감기 환자수 (2024-01 ~ 2026-03)")
plt.xlabel("월")
plt.ylabel("평균 환자수")
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.show()



