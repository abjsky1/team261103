import pandas as pd 

lists = []
for i in [2024,2025,2026] :
    last = 12 if i < 2026 else 3    # 질병 데이터가 2026년도 3월까지만 있어서
    for mth in range(1, last + 1) :
        path = f"JHW/{i}/{i}년 {mth}월.xlsx"
        df = pd.read_excel(path)
        df = df[["측정일시", "PM25"]].copy()  # 필요한 열만 읽기
        df["PM25"] = pd.to_numeric(df["PM25"], errors="coerce") # 결측문자 NaN
        lists.append({"연월": i * 100 + mth, "PM25": df["PM25"].mean()})    # mean은 NaN빼고 게산

air = pd.DataFrame(lists)
air.to_csv("JHW/air_monthly.csv", index=False, encoding="utf-8-sig")
print(air)