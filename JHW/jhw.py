import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

df_temp = pd.read_csv("temperature_data/전국월별_기온.csv", encoding="cp949", skiprows=7)
df_temp = df_temp.dropna(subset=["평균기온(℃)"])
df_temp["년월"] = pd.to_datetime(df_temp["년월"].str.strip(), format="%m-%y").dt.to_period("M")

temp = df_temp[["년월", "평균기온(℃)"]].copy()
temp = temp.rename(columns={"평균기온(℃)": "평균기온"})
temp["월"] = temp["년월"].dt.month

temp["계절"] = "겨울"
temp.loc[(temp["월"] >= 3) & (temp["월"] <= 5), "계절"] = "봄"
temp.loc[(temp["월"] >= 6) & (temp["월"] <= 8), "계절"] = "여름"
temp.loc[(temp["월"] >= 9) & (temp["월"] <= 11), "계절"] = "가을"

# 질병파일 가로 -> 세로
def read_disease(d) :
    raw = pd.read_excel(d, header=None)
    body = raw.iloc[4:, :3].copy()  # 항목,성별,연령
    body.columns = ["질병", "성별", "연령"]

    d_lists = []
    for i in range(3, raw.shape[1], 5) :    # 월마다 5열, 맨 앞이 환자수
        label = raw.iloc[2, i]
        part = body.copy()
        part["년월"] = pd.to_datetime(label[:4] + "-" + label[6:8], format="%Y-%m").to_period("M")
        part["환자수"] = pd.to_numeric(raw.iloc[4:, i])
        d_lists.append(part)
    return pd.concat(d_lists, ignore_index=True)

folder = "질병/국민관심질병_성별연령별10세구간별현황_202401_202603"
pneu = read_disease(folder + "(폐렴).xlsx")
copd = read_disease(folder + "(만성폐쇄성질환COPD).xlsx")
asthma = read_disease(folder + "(천식).xlsx")

# 가설1 : 기온이 내려가면 60세 이상이 20~39세보다 더 늘어난다(폐렴,copd 환자수)
disease = pd.concat([pneu, copd], ignore_index=True)
# 연령대 묶기 (남여합산)
age = disease[(disease["연령"]!="계")&(disease["연령"]!="소계")]    # 연령행만

old_age = (age["연령"]=="60_69세") | (age["연령"]=="70_79세") | (age["연령"]=="80세이상") 
old = age[old_age].groupby(["질병", "년월"], as_index=False)["환자수"].sum()
old = old.rename(columns={"환자수": "60세이상"})

young_age = (age["연령"]=="20_29세") | (age["연령"]=="30_39세")
young = age[young_age].groupby(["질병", "년월"], as_index=False)["환자수"].sum()
young = young.rename(columns={"환자수": "20_39세"}) 

grp = old.merge(young, on=["질병", "년월"])
# 기온+게절
m = grp.merge(temp[["년월", "월", "평균기온", "계절"]], on="년월")

# 질병별 분석 + 시각화
for d in m["질병"].unique() :
    s = m[m["질병"] == d].copy()

    # 지수 = 월 환자수 ÷ 그 그룹의 전체 기간 평균 (1.0 = 평소 수준)
    s["60세이상_지수"] = s["60세이상"] / s["60세이상"].mean()
    s["20_39세_지수"] = s["20_39세"] / s["20_39세"].mean()

    plt.scatter(s["평균기온"], s["60세이상_지수"], label="60세 이상")
    plt.scatter(s["평균기온"], s["20_39세_지수"], label="20~39세")
    plt.title(d)
    plt.xlabel("월평균 기온(℃)")
    plt.ylabel("환자수 지수(1.0 = 평소 수준)")
    plt.legend()
    plt.show()

    numeric_df = s[ ["평균기온", "60세이상_지수", "20_39세_지수"] ]
    corr_matrix = numeric_df.corr()
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm")
    plt.title(d)
    plt.show()

############ 가설2: 기온이 비슷한 달끼리 비교해도 pm2.5가 높은 달에 천식-COPD 환자가 더 많다
disease2 = pd.concat([asthma, copd], ignore_index=True)
total = disease2[(disease2["성별"] == "계") & (disease2["연령"] == "계")].copy()    # 전체 환자수 행만

air = pd.read_csv("JHW/air_monthly.csv")    # PM2.5만 가져오기 
air["년월"] = pd.to_datetime(air["연월"].astype(str), format="%Y%m").dt.to_period("M")

x = total.merge(temp[["년월", "평균기온"]], on="년월")
x = x.merge(air[["년월","PM25"]], on="년월")

x["기온구간"] = "중간"
x.loc[x["평균기온"] < 5, "기온구간"] = "낮음"
x.loc[x["평균기온"] >= 20, "기온구간"] = "높음"

list2 = []
for d in x["질병"].unique():
    s = x[x["질병"]==d].copy()

    for g in ["낮음", "중간", "높음"] :
        sub = s[s["기온구간"]==g].copy()
        med = sub["PM25"].median()  # 이 구간의 PM2.5 중앙값 기준
        sub["PM구분"] = "PM2.5 낮음"
        sub.loc[sub["PM25"] >= med, "PM구분"] = "PM2.5 높음"    
        list2.append(sub)

res = pd.concat(list2, ignore_index=True)

for d in res["질병"].unique():
    sns.barplot(data=res[res["질병"] == d], x="기온구간", y="환자수", hue="PM구분",
                order=["낮음", "중간", "높음"], hue_order=["PM2.5 낮음", "PM2.5 높음"], errorbar=None, width=0.5)
    plt.title(d + ": 기온 구간별 월평균 환자수")
    plt.ylabel("월평균 환자수(명)")
    plt.show()