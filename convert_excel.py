import pandas as pd
import json

# 엑셀 파일 읽기
df = pd.read_excel('paps_criteria.xlsx')

# JSON 형식으로 변환
data = {
    "체력요인": df['체력요인'].unique().tolist(),
    "평가기준": []
}

# 각 기준을 JSON 객체로 변환
for _, row in df.iterrows():
    criteria = {
        "체력요인": row['체력요인'],
        "평가종목": row['평가종목'],
        "학년": str(row['학년']),
        "성별": row['성별'],
        "학교과정": row['학교과정'],
        "기록": row['기록 구간'],
        "등급": str(row['등급']),
        "점수": int(row['점수'])
    }
    data["평가기준"].append(criteria)

# JSON 파일로 저장
with open('paps_data.js', 'w', encoding='utf-8') as f:
    f.write('const PAPS_DATA = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';')
