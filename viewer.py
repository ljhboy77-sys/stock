import streamlit as st
import pandas as pd
import time
import altair as alt
import os
import json
import urllib.request
import configparser
from datetime import datetime, timedelta

st.set_page_config(page_title="HedgeFund Desk", layout="wide")

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')
try:
    NAVER_CLIENT_ID = config['NAVER']['client_id']
    NAVER_CLIENT_SECRET = config['NAVER']['client_secret']
except:
    NAVER_CLIENT_ID = ""
    NAVER_CLIENT_SECRET = ""

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
    .alert-box { border: 2px solid #ff4b4b; padding: 10px; border-radius: 5px; background-color: #ffeaea; color: #ff4b4b; font-weight: bold; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ 기관용 마켓 스캐너 (Real-time Alert)")

def fetch_live_naver_trend(keyword):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET: return "-"
    try:
        url = "https://openapi.naver.com/v1/datalab/search"
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
        body = json.dumps({"startDate": start, "endDate": end, "timeUnit": "date", "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}]})
        req = urllib.request.Request(url)
        req.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        req.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
        req.add_header("Content-Type", "application/json")
        res = urllib.request.urlopen(req, data=body.encode("utf-8"), timeout=0.5)
        if res.getcode() == 200:
            data = json.loads(res.read().decode('utf-8'))
            if not data['results'][0]['data']: return "데이터부족"
            daily = data['results'][0]['data']
            if len(daily) < 5: return "-"
            recent = sum([x['ratio'] for x in daily[-3:]]) / 3
            past = sum([x['ratio'] for x in daily[:-3]]) / len(daily[:-3])
            if past == 0: return "🔥폭등"
            score = (recent/past) * 100
            if score > 200: return "🔥폭등"
            elif score > 150: return "🔺급증"
            elif score > 110: return "↗️증가"
            else: return "➡️보합"
    except: return "-"
    return "-"

def color_change(val):
    if isinstance(val, str): return ''
    color = '#ff4b4b' if val > 0 else '#4b88ff' if val < 0 else 'white'
    return f'color: {color}; font-weight: bold;'

search_keyword = st.text_input("🔍 종목 검색", key="top_search_bar")
detail_placeholder = st.empty()
alert_placeholder = st.empty() # [NEW] 공시 속보 전광판
main_placeholder = st.empty()

# 팝업 중복 방지용 세션 상태
if 'viewed_alerts' not in st.session_state:
    st.session_state['viewed_alerts'] = set()

while True:
    df_rank = pd.DataFrame()
    df_search = pd.DataFrame()
    df_alert = pd.DataFrame()
    
    if os.path.exists("market_data.csv"):
        try: df_rank = pd.read_csv("market_data.csv")
        except: pass
    if os.path.exists("search_db.csv"):
        try: df_search = pd.read_csv("search_db.csv")
        except: pass
    if os.path.exists("alert_log.csv"): # [NEW] 긴급 알림 파일 읽기
        try: df_alert = pd.read_csv("alert_log.csv")
        except: pass

    # ==========================================
    # [기능 1] 긴급 공시 팝업 (Toast) & 전광판
    # ==========================================
    if not df_alert.empty:
        # 1. 상단 전광판 표시
        with alert_placeholder.container():
            st.error("🚨 [긴급 공시/재료 속보] 실시간 감지 중...")
            cols = st.columns(3)
            for i, row in df_alert.head(3).iterrows(): # 최근 3개만 표시
                with cols[i]:
                    st.markdown(f"**{row['Stock']}** | {row['Keyword']}")
                    st.caption(f"{row['Content']}...")

        # 2. 우측 하단 팝업 (Toast)
        for i, row in df_alert.iterrows():
            unique_id = f"{row['Stock']}_{row['Keyword']}_{row['Time']}"
            if unique_id not in st.session_state['viewed_alerts']:
                # 처음 보는 공시면 팝업 띄움
                st.toast(f"🚨 [긴급] {row['Stock']} - {row['Keyword']} 발생!", icon="🔥")
                st.session_state['viewed_alerts'].add(unique_id)

    # ---------------------------------------------------------
    # A. 상세 정보 함수
    # ---------------------------------------------------------
    def show_details(row):
        with detail_placeholder.container():
            st.markdown("---")
            st.markdown(f"### 📄 [상세분석] {row['Stock']} (Rank #{row['Rank']})")
            trend = str(row.get('Trend', '-'))
            if trend in ["-", "nan", "None"]: trend = fetch_live_naver_trend(row['Stock'])
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("현재가", f"{int(row['Price']):,}원", f"{row['Change']:.2f}%", delta_color="inverse")
                c2.metric("트렌드", trend)
                c3.metric("언급량", f"{row['Buzz']}회")
                c4.metric("키워드", row['Theme'])
                st.markdown("#### 📰 뉴스/공시 원문")
                if 'Context' in row and pd.notna(row['Context']):
                    for i, news in enumerate(str(row['Context']).split(" || "), 1):
                        st.info(f"[{i}] {news}")
            st.markdown("---")

    # ---------------------------------------------------------
    # B. 메인 화면
    # ---------------------------------------------------------
    with main_placeholder.container():
        if df_rank.empty:
            st.info("🔄 데이터 수집 및 공시 감시 중...")
        else:
            if search_keyword:
                if not df_search.empty:
                    filtered = df_search[df_search['Stock'].str.contains(search_keyword, case=False)]
                    if not filtered.empty: show_details(filtered.iloc[0])
                    else: st.error("검색 결과 없음")
            
            try:
                top = df_rank.iloc[0]
                top_gainer = df_rank.sort_values(by='Change', ascending=False).iloc[0]

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("👑 1위", top['Stock'], f"{top['Buzz']}회")
                c2.metric("🚀 급등", top_gainer['Stock'], f"{top_gainer['Change']:.2f}%", delta_color="inverse")
                c3.metric("🔥 트렌드", str(top.get('Trend', '-')))
                c4.metric("🕒 갱신", str(top.get('Time', 'Live')))
                
                col_chart, col_table = st.columns([1, 2])
                with col_chart:
                    st.subheader("📊 Buzz Top 10")
                    chart = alt.Chart(df_rank.head(10)).mark_bar().encode(
                        x=alt.X('Buzz', title=None), y=alt.Y('Stock', sort='-x', title=None),
                        color=alt.Color('Buzz', legend=None), tooltip=['Stock', 'Buzz', 'Price']
                    ).properties(height=500)
                    st.altair_chart(chart, use_container_width=True)

                with col_table:
                    st.subheader("📋 실시간 랭킹 (클릭 시 상세조회)")
                    display_df = df_rank[['Rank', 'Stock', 'Price', 'Change', 'Buzz', 'Theme']].copy()
                    styled_df = display_df.style.map(color_change, subset=['Change']).format({
                        'Price': "{:,.0f}", 'Change': "{:+.2f}%", 'Buzz': "{}회"
                    })
                    event = st.dataframe(
                        styled_df, use_container_width=True, height=500, hide_index=True,
                        on_select="rerun", selection_mode="single-row", key="live_ranking_table",
                        column_config={"Rank": st.column_config.Column("순위", width="small"), "Stock": st.column_config.Column("종목", width="medium"), "Theme": st.column_config.Column("키워드", width="large")}
                    )
                    if len(event.selection.rows) > 0:
                        show_details(df_rank.iloc[event.selection.rows[0]])

            except Exception: pass
    
    time.sleep(1)
