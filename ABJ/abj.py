<<<<<<< HEAD
# 모기 데이터1 : https://data.seoul.go.kr/dataList/OA-22301/F/1/datasetView.do
# 모기 데이터2 : https://news.seoul.go.kr/welfare/digital_mosquito

=======
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
>>>>>>> 14c8ac9f06e93c9ae9d5518bdfaacb726a4b17f0
