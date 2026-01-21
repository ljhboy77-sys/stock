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
</style>
""", unsafe_allow_html=True)

st.title("⚡ 기관용 마켓 스캐너 (Data Export)")

# ==========================================
# [기능 추가] 사이드바에 다운로드 버튼 배치
# ==========================================
with st.sidebar:
    st.header("📥 데이터 추출 (Excel)")
    st.caption("서버에 저장된 데이터를 내 PC로 다운로드합니다.")
    
    # 1. 공시/속보 누적 기록 다운로드
    if os.path.exists("alert_history.csv"):
        try:
            with open("alert_history.csv", "rb") as f:
                st.download_button(
                    label="🚨 공시/속보 기록 받기",
                    data=f,
                    file_name=f"공시기록_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        except: pass
    
    # 2. 현재 실시간 랭킹 다운로드
    if os.path.exists("market_data.csv"):
        try:
            with open("market_data.csv", "rb") as f:
                st.download_button(
                    label="📊 실시간 랭킹 받기",
                    data=f,
                    file_name=f"실시간랭킹_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        except: pass
    
    st.markdown("---")
    st.info("💡 팁: 다운로드 받은 파일은 엑셀에서 바로 열립니다.")

# 데이터 로딩
def load_data():
    df_rank = pd.DataFrame()
    df_search = pd.DataFrame()
    df_history = pd.DataFrame()
    if os.path.exists("market_data.csv"):
        try: df_rank = pd.read_csv("market_data.csv")
        except: pass
    if os.path.exists("search_db.csv"):
        try: df_search = pd.read_csv("search_db.csv")
        except: pass
    if os.path.exists("alert_history.csv"): 
        try: df_history = pd.read_csv("alert_history.csv")
        except: pass
    return df_rank, df_search, df_history

def fetch_live_naver_trend(keyword):
    if not NAVER_CLIENT_ID: return "-"
    return "-" 

def color_change(val):
    if isinstance(val, str): return ''
    color = '#ff4b4b' if val > 0 else '#4b88ff' if val < 0 else 'white'
    return f'color: {color}; font-weight: bold;'

tab1, tab2 = st.tabs(["📊 실시간 랭킹 (Main)", "🚨 공시/속보 누적 (History)"])

if 'viewed_alerts' not in st.session_state:
    st.session_state['viewed_alerts'] = set()

while True:
    df_rank, df_search, df_history = load_data()
    
    if not df_history.empty:
        recent_alerts = df_history.head(5)
        for i, row in recent_alerts.iterrows():
            unique_id = f"{row['Stock']}_{row['Keyword']}_{row['Time']}"
            if unique_id not in st.session_state['viewed_alerts']:
                st.toast(f"🚨 [속보] {row['Stock']} : {row['Keyword']}", icon="🔥")
                st.session_state['viewed_alerts'].add(unique_id)

    with tab1:
        search_keyword = st.text_input("🔍 종목 검색 (랭킹 탭)", key="search_tab1")
        detail_placeholder = st.empty()
        
        def show_details(row):
            with detail_placeholder.container():
                st.markdown("---")
                st.markdown(f"### 📄 {row['Stock']} 상세분석")
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("현재가", f"{int(row['Price']):,}원", f"{row['Change']:.2f}%", delta_color="inverse")
                    c2.metric("언급량", f"{row['Buzz']}회")
                    c3.metric("키워드", row['Theme'])
                    c4.metric("갱신", row['Time'])
                    st.info(f"📰 뉴스: {str(row['Context'])[:300]}...")
                st.markdown("---")

        if not df_rank.empty:
            if search_keyword and not df_search.empty:
                filtered = df_search[df_search['Stock'].str.contains(search_keyword, case=False)]
                if not filtered.empty: show_details(filtered.iloc[0])

            c_chart, c_table = st.columns([1, 2])
            with c_chart:
                st.subheader("📊 언급량 Top 10")
                chart = alt.Chart(df_rank.head(10)).mark_bar().encode(
                    x=alt.X('Buzz', title=None), y=alt.Y('Stock', sort='-x', title=None),
                    color=alt.Color('Buzz', legend=None)
                ).properties(height=500)
                st.altair_chart(chart, use_container_width=True)
            
            with c_table:
                st.subheader("📋 실시간 랭킹")
                display_df = df_rank[['Rank', 'Stock', 'Price', 'Change', 'Buzz', 'Theme']].copy()
                styled_df = display_df.style.map(color_change, subset=['Change']).format({
                    'Price': "{:,.0f}", 'Change': "{:+.2f}%"
                })
                event = st.dataframe(
                    styled_df, use_container_width=True, height=500, hide_index=True,
                    on_select="rerun", selection_mode="single-row", key="rank_table_tab1"
                )
                if len(event.selection.rows) > 0:
                    show_details(df_rank.iloc[event.selection.rows[0]])
        else:
            st.info("데이터 수집 중...")

    with tab2:
        st.subheader("🚨 실시간 공시/속보 누적 기록")
        if not df_history.empty:
            st.dataframe(
                df_history[['Time', 'Stock', 'Keyword', 'Content']],
                use_container_width=True, height=800, hide_index=True,
                column_config={
                    "Time": st.column_config.Column("발생시간", width="medium"),
                    "Stock": st.column_config.Column("종목명", width="small"),
                    "Keyword": st.column_config.Column("재료/키워드", width="small"),
                    "Content": st.column_config.Column("내용 요약", width="large"),
                }
            )
        else:
            st.info("아직 감지된 공시가 없습니다. (감시 중...)")

    time.sleep(1)
