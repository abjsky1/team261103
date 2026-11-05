import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

data = pd.read_csv('KDH\\OBS_ASOS_MNH_20261104175908.csv')


global_data = data.groupby('일시', as_index=False).agg(
    전국평균수증기압=('평균수증기압(hPa)', 'mean'),
    전국평균상대습도=('평균상대습도(%)', 'mean')
)

df_temp = pd.read_csv('./temperature_data/전국월별_기온.csv',
                 encoding='cp949',   # 한국어 인코딩으로 읽기
                 skiprows=7)         # 앞의 설명 7줄 건너뛰기
df_temp['년월'] = pd.to_datetime(df_temp['년월'].str.strip(), format='%m-%y').dt.to_period('M')
df = df_temp[['년월', '평균기온(℃)']]

df = df.rename(columns={'년월':'일시'})
# AH = (216.7 * e) / (T + 273.15) , 이 때 e는 수증기압 , T는 기온
global_data['전국평균절대습도'] = global_data['전국평균수증기압']*216.7 / (df['평균기온(℃)'] + 273.15)
print(global_data)

